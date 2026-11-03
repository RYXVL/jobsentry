"""Fetch every source in the background, several at a time.

POST /sources/refresh calls runner.start(); GET /sources/refresh calls
runner.status().

Each run builds one queue: sources grouped by platform in
Settings.refresh_order, in catalog order within each platform. A pool of
Settings.refresh_workers threads takes sources from the front of the queue;
when a worker finishes a source, it takes the next, until the queue is
empty. Each source is saved the moment it finishes (which also updates
todays-jobs.json), so data appears as it arrives. A failing source is
recorded and the rest carry on.

Only one run happens at a time: starting while one is running returns it.
Runs live in this process's memory, so restarting the API forgets the
current run; sources it already finished stay saved.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone

from ..config import Settings
from ..core.exceptions import JobsentryError, RefreshInProgressError
from ..sources import SourceInfo, sources_in_order
from .job_service import JobService, clear_all

log = logging.getLogger(__name__)

@dataclass(frozen=True)
class SourceResult:
    """What happened to one source in a run."""

    source: str
    company: str
    ok: bool
    fetched_at: str | None = None
    job_count: int | None = None
    error: JobsentryError | None = None

@dataclass
class RefreshRun:
    """Progress of one fetch-all run."""

    started_at: str
    total: int
    results: list[SourceResult] = field(default_factory=list)  # in completion order
    in_progress: list[SourceInfo] = field(default_factory=list)  # being fetched now
    finished_at: str | None = None

    @property
    def running(self) -> bool:
        return self.finished_at is None

    @property
    def completed(self) -> int:
        return len(self.results)

    @property
    def succeeded(self) -> int:
        return sum(result.ok for result in self.results)

    @property
    def failed(self) -> int:
        return self.completed - self.succeeded

    @property
    def jobs_fetched(self) -> int:
        return sum(result.job_count or 0 for result in self.results)

class RefreshRunner:
    """Owns the current (or last) run. Thread-safe; use the module's `runner`."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._run: RefreshRun | None = None
        self._executor: ThreadPoolExecutor | None = None

    def start(self, settings: Settings) -> RefreshRun:
        """Start a run, or return the one already running. Returns at once."""
        with self._lock:
            if self._run is not None and self._run.running:
                return self._copy()

            queue = sources_in_order(settings.refresh_order)
            run = RefreshRun(started_at=_now(), total=len(queue))
            self._run = run
            if not queue:
                run.finished_at = _now()
                return self._copy()

            executor = ThreadPoolExecutor(
                max_workers=settings.refresh_workers, thread_name_prefix="refresh"
            )
            self._executor = executor
            # The executor's queue is first in, first out: workers take
            # sources from the front, in the order submitted.
            for info in queue:
                executor.submit(self._refresh_one, run, info, settings)
            executor.shutdown(wait=False)  # no more work; threads exit once the queue is done
            return self._copy()

    def status(self) -> RefreshRun | None:
        """A copy of the current or last run, or None if none has run yet."""
        with self._lock:
            return self._copy()

    def is_running(self) -> bool:
        with self._lock:
            return self._run is not None and self._run.running

    def clear_saved(self, settings: Settings) -> int:
        """Delete all saved data (see job_service.clear_all), refusing while
        a run is going, so a run never saves into a half-cleared folder."""
        with self._lock:
            if self._run is not None and self._run.running:
                raise RefreshInProgressError(
                    "Can't clear while all jobs are being fetched; try again when it finishes"
                )
            return clear_all(settings=settings)

    def shutdown(self) -> None:
        """Cancel sources still waiting in the queue (called when the API
        stops). Sources being fetched finish their current request."""
        with self._lock:
            if self._executor is not None:
                self._executor.shutdown(wait=False, cancel_futures=True)

    # Worker -----------------------------------------------------------------

    def _refresh_one(self, run: RefreshRun, info: SourceInfo, settings: Settings) -> None:
        """Fetch and save one source (in a worker thread), then record it.
        JobService.create gives each source its own HTTP client, since
        requests sessions aren't safe to share between threads."""
        with self._lock:
            run.in_progress.append(info)
        try:
            snapshot, _ = JobService.create(info.name, settings=settings).refresh_jobs()
            result = SourceResult(
                info.name, info.company, ok=True,
                fetched_at=snapshot.fetched_at, job_count=len(snapshot.jobs),
            )
        except JobsentryError as error:
            log.warning("Refreshing %s failed: %s", info.company, error)
            result = SourceResult(info.name, info.company, ok=False, error=error)
        except Exception as error:  # a bug, not a job board problem: keep going
            log.exception("Refreshing %s failed unexpectedly", info.company)
            result = SourceResult(
                info.name, info.company, ok=False,
                error=JobsentryError(f"Unexpected error: {error}"),
            )
        with self._lock:
            run.in_progress.remove(info)
            run.results.append(result)
            if run.completed == run.total:
                run.finished_at = _now()

    def _copy(self) -> RefreshRun | None:
        """A snapshot of the run that won't change while it's read. Call
        with the lock held."""
        if self._run is None:
            return None
        return replace(
            self._run, results=list(self._run.results), in_progress=list(self._run.in_progress)
        )

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

#: The one runner for this process.
runner = RefreshRunner()