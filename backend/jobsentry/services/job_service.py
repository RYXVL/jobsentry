"""JobService: the operations the CLI and API offer, for one source.

Interfaces never talk to sources or storage directly; they call this, so
behaviour (caching, refreshing, filtering, saving) stays identical everywhere.
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
from ..sources import JobSource, create_source
from ..storage import JobStore, JsonJobStore
from .queries import FacetValue, JobFacets, JobPage, JobQuery, SourceStatus

log = logging.getLogger(__name__)

# One lock per source name, shared by every JobService in this process, so a
# site is never scraped twice at the same time (e.g. two browser tabs).
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
        """Fetch every job from the site and save it. Returns (snapshot, location).
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
        """Fetch a job's full posting from the site and save it.
        Returns (details, location). Used by the CLI `show` command."""
        job = self.get_job(job_id)
        log.info("Fetching details for %s [%s]", job.title, job.id)
        details = self.source.fetch_job_details(job)
        return details, self.store.save_details(details)

    def get_details(self, job_id: str, refresh: bool = False) -> JobDetails:
        """Return saved details if available, otherwise fetch and save them.
        Lets the frontend reopen a job without hitting the career site again."""
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
        """Filter and paginate saved jobs (fetching them first if none are saved)."""
        snapshot = self.get_jobs()
        matches = [job for job in snapshot.jobs if query.matches(job)]
        return JobPage(
            source=self.source.name,
            fetched_at=snapshot.fetched_at,
            total=len(matches),
            limit=query.limit,
            offset=query.offset,
            jobs=matches[query.offset : query.offset + query.limit],
        )

    def facets(self) -> JobFacets:
        """Distinct teams, locations, etc. with counts, for building UI filters."""
        jobs = self.get_jobs().jobs
        return JobFacets(
            source=self.source.name,
            teams=_count(team for job in jobs for team in job.teams),
            locations=_count(loc for job in jobs for loc in job.locations),
            employment_types=_count(job.employment_type for job in jobs if job.employment_type),
            tags=_count(tag for job in jobs for tag in job.tags),
        )

    def search(self, text: str) -> list[Job]:
        """Case-insensitive title search over all saved jobs (no paging)."""
        query = JobQuery(text=text)
        return [job for job in self.get_jobs().jobs if query.matches(job)]


def _count(values: Iterable[str]) -> list[FacetValue]:
    """Count values; most common first, ties alphabetical."""
    counts = Counter(values)
    return [FacetValue(v, n) for v, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
