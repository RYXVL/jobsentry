"""Endpoint for jobs across every source at once, e.g. "jobs posted today".

Reads saved data only and never contacts a job board, so it's always quick.
Sources that have never been fetched are skipped and named in the response.
Route functions are plain `def` so FastAPI runs them in its thread pool.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError

from ...config import Settings
from ...services import MAX_PAGE_SIZE, JobQuery
from ...services.job_service import query_all
from ...services.queries import JobSort
from ..dependencies import get_settings
from ..schemas import AllJobsPageOut, ErrorOut

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get(
    "", response_model=AllJobsPageOut,
    responses={422: {"model": ErrorOut, "description": "Bad parameter, e.g. unknown time zone"}},
    summary="List jobs across every source",
)
def list_all_jobs(
    settings: Settings = Depends(get_settings),
    q: str | None = Query(
        None, description="Keywords: every word must appear in the title or a team name"
    ),
    country: list[str] | None = Query(
        None, description="ISO country code; repeat for several. A job in any of them matches."
    ),
    posted_on: date | None = Query(
        None, description="Only jobs first published on this date (YYYY-MM-DD), in `tz`"
    ),
    tz: str = Query(
        "UTC", description="IANA time zone that posted_on is in, e.g. Asia/Kolkata"
    ),
    sort: JobSort = Query("newest", description="Order by date posted: newest or oldest first"),
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
) -> AllJobsPageOut:
    """Saved jobs from every fetched source matching every filter given.
    For "today's jobs", pass today's date and the viewer's time zone."""
    try:
        query = JobQuery(
            text=q, countries=tuple(country or ()), posted_on=posted_on, tz=tz,
            sort=sort, limit=limit, offset=offset,
        )
    except ValueError as e:  # the only check FastAPI can't do itself: the time zone
        raise RequestValidationError(
            [{"loc": ("query", "tz"), "msg": str(e), "type": "value_error"}]
        ) from None
    return AllJobsPageOut.model_validate(query_all(query, settings=settings))