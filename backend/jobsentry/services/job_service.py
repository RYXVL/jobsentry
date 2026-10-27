"""JobService: the operations the CLI and API offer, for one source.

Interfaces never talk to sources or storage directly; they call this, so
behaviour (caching, refreshing, filtering, saving) stays identical everywhere.
The module-level functions at the end (refresh_all, clear_all) work across
every source at once.
"""

from __future__ import annotations

import logging
import threading
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from ..config import Settings
from ..core.exceptions import JobNotFoundError, JobsentryError, RefreshInProgressError
from ..core.http import HttpClient
from ..core.models import Job, JobDetails, JobSnapshot
from ..sources import JobSource, available_sources, create_source
from ..storage import JobStore, JsonJobStore
from .queries import FacetValue, JobFacets, JobPage, JobQuery, SourceStatus

log = logging.getLogger(__name__)

# One lock per source name, shared by every JobService in this process, so a
# source is never fetched twice at the same time (e.g. two browser tabs).
_refresh_locks: dict[str, threading.Lock] = {}
_refresh_locks_guard = threading.Lock()

def _lock_for(source_name: str) -> threading.Lock:
    with _refresh_locks_guard:
        return _refresh_locks.setdefault(source_name, threading.Lock())

class JobService:
    def __init__(self, source: JobSource, store: JobStore):
        self.source = source
        self.store = store

    @classmethod
    def create(
        cls,
        source_name: str,
        settings: Settings | None = None,
        http: HttpClient | None = None,
    ) -> JobService:
        """Build a service for `source_name` with the configured store and client."""
        settings = settings or Settings.from_env()
        http = http or HttpClient(
            timeout=settings.http_timeout,
            retries=settings.http_retries,
            headers={"User-Agent": settings.user_agent},
        )
        return cls(create_source(source_name, http=http), JsonJobStore(settings.data_dir))

    # Fetching ---------------------------------------------------------------

    def refresh_jobs(self) -> tuple[JobSnapshot, str]:
        """Fetch every job from the source and save it. Returns (snapshot, location).
        Raises RefreshInProgressError if this source is already being refreshed."""
        lock = _lock_for(self.source.name)
        if not lock.acquire(blocking=False):
            raise RefreshInProgressError(
                f"{self.source.company} jobs are already being refreshed; try again shortly"
            )
        try:
            log.info("Fetching job list from %s", self.source.company)
            snapshot = JobSnapshot(source=self.source.name, jobs=self.source.fetch_jobs())
            return snapshot, self.store.save_snapshot(snapshot)
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


@dataclass(frozen=True)
class RefreshOutcome:
    """What happened when one source was refreshed by refresh_all()."""

    source: str
    company: str
    snapshot: JobSnapshot | None = None
    error: JobsentryError | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def refresh_all(settings: Settings | None = None, http: HttpClient | None = None) -> list[RefreshOutcome]:
    """Refresh every source, one at a time to keep load on job boards low.
    A failing source is recorded and skipped; the rest still run."""
    settings = settings or Settings.from_env()
    outcomes = []
    for info in available_sources():
        try:
            snapshot, _ = JobService.create(info.name, settings=settings, http=http).refresh_jobs()
            outcomes.append(RefreshOutcome(info.name, info.company, snapshot=snapshot))
        except JobsentryError as error:
            log.warning("Refreshing %s failed: %s", info.company, error)
            outcomes.append(RefreshOutcome(info.name, info.company, error=error))
    return outcomes


def clear_all(settings: Settings | None = None) -> int:
    """Delete all saved jobs and details for every source. Returns how many
    sources had data. Refuses while any refresh is running, so a refresh
    never writes into a half-cleared folder."""
    with _refresh_locks_guard:
        busy = sorted(name for name, lock in _refresh_locks.items() if lock.locked())
    if busy:
        raise RefreshInProgressError(
            f"Can't clear while jobs are being refreshed ({', '.join(busy)}); try again shortly"
        )
    settings = settings or Settings.from_env()
    return JsonJobStore(settings.data_dir).clear()