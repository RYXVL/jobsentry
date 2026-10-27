"""Value objects used by JobService for filtering, sorting, paging and status.

They are plain dataclasses so the service stays independent of FastAPI;
the API layer converts them to Pydantic response models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from ..core.models import Job, normalize_countries
from ..sources import SourceInfo

#: Upper bound on page size, so one request can't return an enormous list.
MAX_PAGE_SIZE = 200

#: Orders a job list can be sorted in, by date posted.
JobSort = Literal["newest", "oldest"]
JOB_SORTS: tuple[JobSort, ...] = ("newest", "oldest")

@dataclass(frozen=True)
class JobQuery:
    """Filters, order and paging for listing saved jobs. Both filters are
    optional and case-insensitive; a job must satisfy every filter that is
    set. Jobs are sorted before paging, so every page follows one order."""

    text: str | None = None             # keywords: every word must be in the title or a team
    countries: tuple[str, ...] = ()     # ISO codes; a job in ANY of them matches
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
        # Frozen, so normalise through object.__setattr__ ("ca" matches "CA").
        object.__setattr__(self, "countries", tuple(normalize_countries(self.countries)))

    def matches(self, job: Job) -> bool:
        if self.text and not _has_keywords(job, self.text):
            return False
        if self.countries and not set(self.countries) & set(job.countries):
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

def _has_keywords(job: Job, text: str) -> bool:
    """True if every space-separated word in `text` appears in the job's
    title or one of its team names (case-insensitive, partial words count)."""
    fields = [job.title.lower(), *(team.lower() for team in job.teams)]
    return all(any(word in f for f in fields) for word in text.lower().split())

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
    """Values present in the saved jobs, with how many jobs have each.
    `countries` feeds the country filter; `teams` and `locations` help when
    writing a catalog's country_hints."""

    source: str
    teams: list[FacetValue]
    locations: list[FacetValue]
    countries: list[FacetValue]       # ISO codes

@dataclass(frozen=True)
class SourceStatus:
    """A source plus the state of its saved data. fetched_at/job_count are
    None until the source has been fetched at least once."""

    info: SourceInfo
    fetched_at: str | None
    job_count: int | None