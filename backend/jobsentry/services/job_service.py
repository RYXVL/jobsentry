"""JobService: the operations the CLI and API offer, for one source.

Interfaces never talk to sources or storage directly; they call this, so
behaviour (caching, refreshing, saving) stays the same everywhere.
"""

from __future__ import annotations

import logging

from ..config import Settings
from ..core.exceptions import JobNotFoundError
from ..core.http import HttpClient
from ..core.models import Job, JobDetails, JobSnapshot
from ..sources import JobSource, create_source
from ..storage import JobStore, JsonJobStore

log = logging.getLogger(__name__)

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
        http = http or HttpClient(timeout=settings.http_timeout, retries=settings.http_retries)
        return cls(create_source(source_name, http=http), JsonJobStore(settings.data_dir))

    def refresh_jobs(self) -> tuple[JobSnapshot, str]:
        """Fetch every job from the site and save it. Returns (snapshot, location)."""
        log.info("Fetching job list from %s", self.source.company)
        snapshot = JobSnapshot(source=self.source.name, jobs=self.source.fetch_jobs())
        return snapshot, self.store.save_snapshot(snapshot)

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
        """Fetch a job's full posting and save it. Returns (details, location)."""
        job = self.get_job(job_id)
        log.info("Fetching details for %s [%s]", job.title, job.id)
        details = self.source.fetch_job_details(job)
        return details, self.store.save_details(details)

    def search(self, query: str) -> list[Job]:
        """Case-insensitive title search over saved jobs (for the API/frontend)."""
        q = query.lower()
        return [job for job in self.get_jobs().jobs if q in job.title.lower()]
