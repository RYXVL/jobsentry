"""Endpoints for a source's jobs: filtered listing, filter options, details.

Route functions are plain `def` (not `async def`) on purpose: scraping uses
blocking network calls, and FastAPI runs plain functions in a thread pool so
one slow site doesn't freeze the whole API.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query

from ...services import MAX_PAGE_SIZE, JobQuery, JobService
from ...services.queries import JobSort
from ..dependencies import get_job_service
from ..schemas import ErrorOut, JobDetailsOut, JobFacetsOut, JobPageOut

router = APIRouter(prefix="/sources/{source}/jobs", tags=["jobs"])

ERRORS = {
    404: {"model": ErrorOut, "description": "Unknown source or job"},
    409: {"model": ErrorOut, "description": "A refresh is already running"},
    502: {"model": ErrorOut, "description": "The career site failed, changed, or blocked us"},
}

@router.get("", response_model=JobPageOut, responses=ERRORS, summary="List and filter jobs")
def list_jobs(
    service: JobService = Depends(get_job_service),
    q: str | None = Query(None, description="Text to find in the job title"),
    team: str | None = Query(None, description="Exact team name (see /facets)"),
    location: str | None = Query(None, description="Text to find in any location"),
    remote: bool | None = Query(None, description="true = remote only, false = on-site only"),
    employment_type: str | None = Query(None, description="e.g. Full time"),
    tag: str | None = Query(None, description="Exact tag (see /facets)"),
    sort: JobSort = Query(
        "newest",
        description="Order by date posted: newest or oldest first. Jobs without a date go last.",
    ),
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
) -> JobPageOut:
    """Saved jobs matching every filter given, in the order asked for. If the
    source has never been fetched, it is fetched first (which can take a while)."""
    page = service.query(JobQuery(
        text=q, team=team, location=location, remote=remote,
        employment_type=employment_type, tag=tag, sort=sort, limit=limit, offset=offset,
    ))
    return JobPageOut.model_validate(page)


@router.get("/facets", response_model=JobFacetsOut, responses=ERRORS,
            summary="Filter options with counts")
def job_facets(service: JobService = Depends(get_job_service)) -> JobFacetsOut:
    """Every team, location, employment type and tag in the saved jobs, with
    how many jobs have each. Use these to build filter dropdowns."""
    return JobFacetsOut.model_validate(service.facets())


@router.get("/{job_id}", response_model=JobDetailsOut, responses=ERRORS,
            summary="Get one job's full details")
def get_job(
    job_id: str = Path(..., description="Job ID from the job list"),
    refresh: bool = Query(False, description="Re-fetch from the site even if saved"),
    service: JobService = Depends(get_job_service),
) -> JobDetailsOut:
    """Full posting (description, salary, apply link). Saved details are
    returned if available; otherwise they're fetched from the site and saved."""
    return JobDetailsOut.model_validate(service.get_details(job_id, refresh=refresh))