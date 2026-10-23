"""Value objects used by JobService for filtering, sorting, paging and status.

They are plain dataclasses so the service stays independent of FastAPI;
the API layer converts them to Pydantic response models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from ..core.models import Job
from ..sources import SourceInfo

#: Upper bound on page size, so one request can't return an enormous list.
MAX_PAGE_SIZE = 200

#: Orders a job list can be sorted in, by date posted.
JobSort = Literal["newest", "oldest"]
JOB_SORTS: tuple[JobSort, ...] = ("newest", "oldest")

@dataclass(frozen=True)
class JobQuery:
    """Filters, order and paging for listing saved jobs. Every filter is
    optional and case-insensitive; a job must satisfy all the filters that
    are set. Jobs are sorted before paging, so every page follows one order."""

    text: str | None = None             # substring of the title
    team: str | None = None             # exact team name
    location: str | None = None         # substring of any location
    remote: bool | None = None          # True = remote only, False = on-site only
    employment_type: str | None = None  # exact, e.g. "Full time"
    tag: str | None = None              # exact tag name
    sort: JobSort = "newest"            # by date posted
    limit: int = 50
    offset: int = 0

    def __post_init__(self) -> None:
        if self.sort not in JOB_SORTS:
            raise ValueError(f"sort must be one of {', '.join(JOB_SORTS)}")
        if not 1 <= self.limit <= MAX_PAGE_SIZE:
            raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}")
        if self.offset < 0:
            raise ValueError("offset must be 0 or more")

    def matches(self, job: Job) -> bool:
        if self.text and self.text.lower() not in job.title.lower():
            return False
        if self.team and not _contains_exact(job.teams, self.team):
            return False
        if self.location and not any(self.location.lower() in loc.lower() for loc in job.locations):
            return False
        if self.remote is not None and job.remote != self.remote:
            return False
        if self.employment_type and (job.employment_type or "").lower() != self.employment_type.lower():
            return False
        if self.tag and not _contains_exact(job.tags, self.tag):
            return False
        return True

    def sort_jobs(self, jobs: list[Job]) -> list[Job]:
        """Order jobs by date posted, newest or oldest first. Jobs without a
        readable date always go last, in their original order."""
        dated: list[tuple[datetime, Job]] = []
        undated: list[Job] = []
        for job in jobs:
            posted = _parse_time(job.posted_at)
            if posted is None:
                undated.append(job)
            else:
                dated.append((posted, job))
        dated.sort(key=lambda pair: pair[0], reverse=self.sort == "newest")
        return [job for _, job in dated] + undated

def _contains_exact(values: list[str], wanted: str) -> bool:
    wanted = wanted.lower()
    return any(v.lower() == wanted for v in values)

def _parse_time(value: str | None) -> datetime | None:
    """Parse an ISO 8601 time so times in different zones compare correctly.
    Times without a zone are taken as UTC; unreadable values give None."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

@dataclass
class JobPage:
    """One page of filtered jobs. `total` counts all matches, not just this page."""

    source: str
    fetched_at: str
    total: int
    limit: int
    offset: int
    jobs: list[Job] = field(default_factory=list)

@dataclass(frozen=True)
class FacetValue:
    value: str
    count: int

@dataclass
class JobFacets:
    """Every filter value present in the saved jobs, with how many jobs have it."""

    source: str
    teams: list[FacetValue]
    locations: list[FacetValue]
    employment_types: list[FacetValue]
    tags: list[FacetValue]

@dataclass(frozen=True)
class SourceStatus:
    """A source plus the state of its saved data. fetched_at/job_count are
    None until the source has been fetched at least once."""

    info: SourceInfo
    fetched_at: str | None
    job_count: int | None