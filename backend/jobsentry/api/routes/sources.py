"""Endpoints about sources as a whole: listing them, fetching every source in
the background (with progress), and clearing saved data."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...config import Settings
from ...core.http import HttpClient
from ...services import JobService
from ...services.refresh_runner import RefreshRun, runner
from ...sources import available_sources
from ..dependencies import get_http_client, get_job_service, get_settings
from ..errors import _lookup
from ..schemas import (
    ClearOut,
    ErrorDetail,
    ErrorOut,
    RefreshItemOut,
    RefreshOut,
    RefreshRunOut,
    SourceOut,
)

router = APIRouter(prefix="/sources", tags=["sources"])

ERRORS = {
    404: {"model": ErrorOut, "description": "Unknown source"},
    409: {"model": ErrorOut, "description": "A refresh is already running"},
    502: {"model": ErrorOut, "description": "The job board failed, changed, or blocked us"},
}

@router.get("", response_model=list[SourceOut], summary="List available sources")
def list_sources(
    settings: Settings = Depends(get_settings),
    http: HttpClient = Depends(get_http_client),
) -> list[SourceOut]:
    """Every registered company, with when it was last refreshed."""
    results = []
    for info in available_sources():
        status = JobService.create(info.name, settings=settings, http=http).status()
        results.append(SourceOut(
            **vars(status.info), fetched_at=status.fetched_at, job_count=status.job_count,
        ))
    return results

@router.post("/refresh", response_model=RefreshRunOut, status_code=202,
             summary="Start fetching every source")
def start_refresh_all(settings: Settings = Depends(get_settings)) -> RefreshRunOut:
    """Start fetching every company in the background, several at a time
    (JOBSENTRY_REFRESH_WORKERS), in platform order (JOBSENTRY_REFRESH_ORDER).
    Returns at once with the run's progress; follow it with GET
    /sources/refresh. If a run is already going, returns that run."""
    return _run_out(runner.start(settings, trigger="manual"))

@router.get("/refresh", response_model=RefreshRunOut,
            summary="Progress of fetching every source")
def refresh_all_status() -> RefreshRunOut:
    """The current run's progress, or the last run's result. state is
    "idle" if none has run since the API started."""
    return _run_out(runner.status())

@router.post("/clear", response_model=ClearOut, responses={409: ERRORS[409]},
             summary="Delete all saved jobs")
def clear_saved_data(settings: Settings = Depends(get_settings)) -> ClearOut:
    """Delete every saved job list, job detail and todays-jobs.json, for
    every source. Refused (409) while a refresh is running. Can't be undone."""
    return ClearOut(cleared_sources=runner.clear_saved(settings))

@router.get("/{source}", response_model=SourceOut, responses={404: ERRORS[404]},
            summary="Get one source")
def get_source(service: JobService = Depends(get_job_service)) -> SourceOut:
    status = service.status()
    return SourceOut(**vars(status.info), fetched_at=status.fetched_at, job_count=status.job_count)

@router.post("/{source}/refresh", response_model=RefreshOut, responses=ERRORS,
             summary="Fetch one source's jobs again")
def refresh_source(service: JobService = Depends(get_job_service)) -> RefreshOut:
    """Fetch every job from the company's job board and save it (same as
    `python -m jobsentry list <source>`). Can take a while for large boards."""
    snapshot, _ = service.refresh_jobs()
    return RefreshOut(source=snapshot.source, fetched_at=snapshot.fetched_at,
                      job_count=len(snapshot.jobs))

def _run_out(run: RefreshRun | None) -> RefreshRunOut:
    """Turn a run (or no run yet) into its response model."""
    if run is None:
        return RefreshRunOut(state="idle")
    results = []
    for result in run.results:
        error = None
        if result.error is not None:
            _, code = _lookup(result.error)
            error = ErrorDetail(code=code, message=str(result.error))
        results.append(RefreshItemOut(
            source=result.source, company=result.company, ok=result.ok,
            fetched_at=result.fetched_at, job_count=result.job_count, error=error,
        ))
    return RefreshRunOut(
        state="running" if run.running else "done",
        trigger=run.trigger if run.trigger in ("manual", "monitor") else None,
        started_at=run.started_at,
        finished_at=run.finished_at,
        total=run.total,
        completed=run.completed,
        succeeded=run.succeeded,
        failed=run.failed,
        jobs_fetched=run.jobs_fetched,
        in_progress=[info.company for info in run.in_progress],
        results=results,
    )