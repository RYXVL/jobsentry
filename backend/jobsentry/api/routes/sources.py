"""Endpoints about sources as a whole: listing them and refreshing one."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...config import Settings
from ...core.http import HttpClient
from ...services import JobService
from ...sources import available_sources
from ..dependencies import get_http_client, get_job_service, get_settings
from ..schemas import ErrorOut, RefreshOut, SourceOut

router = APIRouter(prefix="/sources", tags=["sources"])

ERRORS = {
    404: {"model": ErrorOut, "description": "Unknown source"},
    409: {"model": ErrorOut, "description": "A refresh is already running"},
    502: {"model": ErrorOut, "description": "The career site failed, changed, or blocked us"},
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

@router.get("/{source}", response_model=SourceOut, responses={404: ERRORS[404]},
            summary="Get one source")
def get_source(service: JobService = Depends(get_job_service)) -> SourceOut:
    status = service.status()
    return SourceOut(**vars(status.info), fetched_at=status.fetched_at, job_count=status.job_count)

@router.post("/{source}/refresh", response_model=RefreshOut, responses=ERRORS,
             summary="Re-scrape a source's career site")
def refresh_source(service: JobService = Depends(get_job_service)) -> RefreshOut:
    """Fetch every job from the company's site and save it (same as
    `python -m jobsentry list <source>`). Can take a while for large sites."""
    snapshot, _ = service.refresh_jobs()
    return RefreshOut(source=snapshot.source, fetched_at=snapshot.fetched_at,
                      job_count=len(snapshot.jobs))
