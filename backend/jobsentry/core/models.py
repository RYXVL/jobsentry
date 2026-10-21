"""Source-independent data models.

Every source converts its site's data into these classes, so storage, the
CLI, the API and the frontend only ever deal with one format. IDs are always
strings because sites use numbers, codes ("R-123") and UUIDs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

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
    remote: bool = False
    employment_type: str | None = None
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Job:
        return cls(**data)

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
    posted_at: str | None = None          # ISO 8601
    salary: Salary | None = None
    apply_url: str | None = None

    @classmethod
    def from_job(cls, job: Job, **details: Any) -> JobDetails:
        """Build details from an existing Job plus the extra fields."""
        return cls(**job.to_dict(), **details)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobDetails:
        data = dict(data)
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
