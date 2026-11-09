"""JobService: the operations the CLI and API offer, for one source.

Interfaces never talk to sources or storage directly; they call this, so
behaviour (caching, refreshing, filtering, saving) stays identical everywhere.
The module-level functions at the end (clear_all, query_all) work across
every source at once; services.refresh_runner fetches every source.
"""

from __future__ import annotations

import logging
import threading
from collections import Counter
from collections.abc import Iterable

from ..config import Settings
from ..core.exceptions import JobNotFoundError, RefreshInProgressError
from ..core.http import HttpClient
from ..core.models import Job, JobDetails, JobSnapshot
from ..sources import JobSource, available_sources, create_source
from ..storage import JobStore, JsonJobStore
from . import today_jobs
from .queries import AllJobsPage, FacetValue, JobFacets, JobPage, JobQuery, SourceStatus

log = logging.getLogger(__name__)

# One lock per source name, shared by every JobService in this process, so a
# source is never fetched twice at the same time (e.g. two browser tabs).
_refresh_locks: dict[str, threading.Lock] = {}
_refresh_locks_guard = threading.Lock()

def _lock_for(source_name: str) -> threading.Lock:
    with _refresh_locks_guard:
        return _refresh_locks.setdefault(source_name, threading.Lock())

class JobService:
    def __init__(self, source: JobSource, store: JobStore, timezone: str = "UTC"):
        self.source = source
        self.store = store
        self.timezone = timezone  # "today" for todays-jobs.json

    @classmethod
    def create(
        cls,
        source_name: str,
        settings: Settings | None = None,
        http: HttpClient | None = None,
    ) -> JobService:
        """Build a service for `source_name` with the configured store and client.
        Without `http`, it gets its own client (safe to use from any thread)."""
        settings = settings or Settings.from_env()
        http = http or HttpClient(
            timeout=settings.http_timeout,
            retries=settings.http_retries,
            headers={"User-Agent": settings.user_agent},
        )
        return cls(
            create_source(source_name, http=http),
            JsonJobStore(settings.data_dir),
            timezone=settings.timezone,
        )

    # Fetching ---------------------------------------------------------------

    def refresh_jobs(self) -> tuple[JobSnapshot, str]:
        """Fetch every job from the source and save it (and its part of
        todays-jobs.json). Returns (snapshot, location). Raises
        RefreshInProgressError if this source is already being refreshed.

        Before saving, the source's check_refresh() sees the new jobs and the
        previous save; if it raises, nothing is saved."""
        lock = _lock_for(self.source.name)
        if not lock.acquire(blocking=False):
            raise RefreshInProgressError(
                f"{self.source.company} jobs are already being refreshed; try again shortly"
            )
        try:
            log.info("Fetching job list from %s", self.source.company)
            jobs = self.source.fetch_jobs()
            self.source.check_refresh(jobs, self.store.load_snapshot(self.source.name))
            snapshot = JobSnapshot(source=self.source.name, jobs=jobs)
            location = self.store.save_snapshot(snapshot)
            self._update_today(snapshot)
            return snapshot, location
        finally:
            lock.release()

    def get_jobs(self, refresh: bool = False) -> JobSnapshot:
        """Return saved jobs, fetching them first if none are saved (or refresh=True)."""
        if not refresh:
            snapshot = self.store.load_snapshot(self.source.name)
            if snapshot is not None:
                return snapshot
        snapshot, _ = self.refresh_jobs()
        return snapshot

    def get_job(self, job_id: str) -> Job:
        """Find a job by ID. If it isn't in the saved list, refresh once and retry,
        since the saved list may predate the job being posted."""
        job_id = str(job_id)
        for refresh in (False, True):
            for job in self.get_jobs(refresh=refresh).jobs:
                if job.id == job_id:
                    return job
        raise JobNotFoundError(f"No {self.source.company} job with ID '{job_id}'")

    def get_job_details(self, job_id: str) -> tuple[JobDetails, str]:
        """Fetch a job's full posting and save it. Returns (details, location).
        Used by the CLI `show` command."""
        job = self.get_job(job_id)
        log.info("Fetching details for %s [%s]", job.title, job.id)
        details = self.source.fetch_job_details(job)
        return details, self.store.save_details(details)

    def get_details(self, job_id: str, refresh: bool = False) -> JobDetails:
        """Return saved details if available, otherwise fetch and save them.
        Lets the frontend reopen a job without contacting the source again."""
        if not refresh:
            cached = self.store.load_details(self.source.name, str(job_id))
            if cached is not None:
                return cached
        details, _ = self.get_job_details(job_id)
        return details

    def _update_today(self, snapshot: JobSnapshot) -> None:
        """Keep todays-jobs.json in step with this save. Never fails the
        refresh: the file is only a fast path, and /today falls back to the
        saved jobs if it's missing or out of date."""
        try:
            today_jobs.record(self.store, snapshot, self.source.company, self.timezone)
        except Exception:
            log.exception("Couldn't update todays-jobs.json for %s", self.source.company)

    # Reading saved data -----------------------------------------------------

    def status(self) -> SourceStatus:
        """Describe the source and its last saved snapshot (if any)."""
        snapshot = self.store.load_snapshot(self.source.name)
        return SourceStatus(
            info=self.source.info(),
            fetched_at=snapshot.fetched_at if snapshot else None,
            job_count=len(snapshot.jobs) if snapshot else None,
        )

    def query(self, query: JobQuery) -> JobPage:
        """Filter, sort and paginate saved jobs (fetching them first if none
        are saved). Sorting happens before paging, so pages follow one order."""
        snapshot = self.get_jobs()
        matches = query.sort_jobs([job for job in snapshot.jobs if query.matches(job)])
        return JobPage(
            source=self.source.name,
            fetched_at=snapshot.fetched_at,
            total=len(matches),
            limit=query.limit,
            offset=query.offset,
            jobs=matches[query.offset : query.offset + query.limit],
        )

    def facets(self) -> JobFacets:
        """Distinct teams, locations and countries with counts."""
        jobs = self.get_jobs().jobs
        return JobFacets(
            source=self.source.name,
            teams=_count(team for job in jobs for team in job.teams),
            locations=_count(loc for job in jobs for loc in job.locations),
            countries=_count(code for job in jobs for code in job.countries),
        )


def _count(values: Iterable[str]) -> list[FacetValue]:
    """Count values; most common first, ties alphabetical."""
    counts = Counter(values)
    return [FacetValue(v, n) for v, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def clear_all(settings: Settings | None = None) -> int:
    """Delete all saved jobs, details and todays-jobs.json. Returns how many
    sources had data. Refuses while any refresh is running, so a refresh
    never writes into a half-cleared folder. (While a fetch-all is running,
    use refresh_runner.runner.clear_saved, which also checks for the run.)"""
    with _refresh_locks_guard:
        busy = sorted(name for name, lock in _refresh_locks.items() if lock.locked())
    if busy:
        raise RefreshInProgressError(
            f"Can't clear while jobs are being refreshed ({', '.join(busy)}); try again shortly"
        )
    settings = settings or Settings.from_env()
    return JsonJobStore(settings.data_dir).clear()


def query_all(query: JobQuery, settings: Settings | None = None) -> AllJobsPage:
    """Filter, sort and page saved jobs across every source at once.

    Reads saved data only and never contacts a job board: a source that has
    never been fetched is named in `unfetched` instead of being fetched.
    When the query is for the date and time zone todays-jobs.json was built
    for, that one file is read instead of every source's jobs.json."""
    settings = settings or Settings.from_env()
    store = JsonJobStore(settings.data_dir)
    sections = today_jobs.read(store, query.posted_on, query.tz) if query.posted_on else None

    dated: list[Job] = []          # jobs matching the date filter only
    fetched_times: list[str] = []
    unfetched: list[str] = []
    for info in available_sources():
        if sections is not None:
            section = sections.get(info.name)
            if not isinstance(section, dict):
                unfetched.append(info.company)
                continue
            fetched_times.append(str(section.get("fetched_at") or ""))
            jobs = [Job.from_dict(job) for job in section.get("jobs") or []]
        else:
            snapshot = store.load_snapshot(info.name)
            if snapshot is None:
                unfetched.append(info.company)
                continue
            fetched_times.append(snapshot.fetched_at)
            jobs = snapshot.jobs
        dated += [job for job in jobs if query.matches_date(job)]

    matches = query.sort_jobs([job for job in dated if query.matches(job)])
    fetched_times = [time for time in fetched_times if time]
    return AllJobsPage(
        total=len(matches),
        limit=query.limit,
        offset=query.offset,
        # All fetched_at values are UTC ISO strings in one format, so the
        # smallest string is the oldest time.
        fetched_at=min(fetched_times) if fetched_times else None,
        unfetched=unfetched,
        countries=_count(code for job in dated for code in job.countries),
        jobs=matches[query.offset : query.offset + query.limit],
    )