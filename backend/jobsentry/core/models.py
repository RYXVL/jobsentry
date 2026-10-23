"""Source-independent data models.

Every source converts its site's data into these classes, so storage, the
CLI, the API and the frontend only ever deal with one format. IDs are always
strings because sites use numbers, codes ("R-123") and UUIDs.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from typing import Any

#: How a job can be worked, in display order. A source lists only the modes
#: its site actually states; an empty list means the site doesn't say.
WORK_MODES = ("on_site", "hybrid", "remote")

def sort_work_modes(modes: Iterable[str]) -> list[str]:
    """Return the known modes in `modes`, without duplicates, in WORK_MODES order."""
    wanted = set(modes)
    return [mode for mode in WORK_MODES if mode in wanted]

def _known_fields(cls: type, data: dict[str, Any]) -> dict[str, Any]:
    """Keep only the keys that are fields of dataclass `cls`, so files saved
    by an older or newer version (with extra or removed fields) still load."""
    names = {f.name for f in fields(cls)}
    return {key: value for key, value in data.items() if key in names}

@dataclass
class Job:
    """Summary data for one job, as shown in a site's job list."""

    source: str
    id: str
    title: str
    url: str
    company: str
    teams: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    remote: bool = False                  # True if any location is remote
    work_modes: list[str] = field(default_factory=list)  # see WORK_MODES
    employment_type: str | None = None
    tags: list[str] = field(default_factory=list)
    posted_at: str | None = None          # ISO 8601: when the job was first published
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Job:
        return cls(**_known_fields(cls, data))

@dataclass
class Salary:
    min: float | None = None
    max: float | None = None
    currency: str | None = None
    period: str | None = None  # e.g. "YEAR", "HOUR"

@dataclass
class JobDetails(Job):
    """A Job plus everything from its individual posting page."""

    description: str = ""
    description_format: str = "markdown"  # "markdown", "html" or "text"
    salary: Salary | None = None
    apply_url: str | None = None

    @classmethod
    def from_job(cls, job: Job, **details: Any) -> JobDetails:
        """Build details from an existing Job plus the extra fields. A field
        given in `details` replaces the job's own (e.g. a posting page's
        posted_at replaces the one from the job list)."""
        return cls(**{**job.to_dict(), **details})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobDetails:
        data = _known_fields(cls, data)
        salary = data.pop("salary", None)
        return cls(**data, salary=Salary(**salary) if salary else None)

@dataclass
class JobSnapshot:
    """All jobs from one source at one point in time."""

    source: str
    jobs: list[Job]
    fetched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "fetched_at": self.fetched_at,
            "count": len(self.jobs),
            "jobs": [job.to_dict() for job in self.jobs],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobSnapshot:
        return cls(
            source=data["source"],
            fetched_at=data["fetched_at"],
            jobs=[Job.from_dict(j) for j in data["jobs"]],
        )