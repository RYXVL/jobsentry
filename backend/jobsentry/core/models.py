"""Source-independent data models.

Every source converts its platform's data into these classes, so storage,
the CLI, the API and the frontend only ever deal with one format. IDs are
always strings because platforms use numbers, codes ("R-123") and UUIDs.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from typing import Any

#: How a job can be worked, in display order. A source lists only the modes
#: its platform actually states; an empty list means it doesn't say.
WORK_MODES = ("on_site", "hybrid", "remote")

def sort_work_modes(modes: Iterable[str]) -> list[str]:
    """Return the known modes in `modes`, without duplicates, in WORK_MODES order."""
    wanted = set(modes)
    return [mode for mode in WORK_MODES if mode in wanted]

def normalize_countries(codes: Iterable[str | None]) -> list[str]:
    """Return ISO 3166-1 alpha-2 codes upper-cased, without blanks or
    duplicates, sorted: e.g. ["us", "CA", None, "US"] becomes ["CA", "US"]."""
    return sorted({code.strip().upper() for code in codes if code and code.strip()})

def _known_fields(cls: type, data: dict[str, Any]) -> dict[str, Any]:
    """Keep only the keys that are fields of dataclass `cls`, so files saved
    by an older or newer version (with extra or removed fields) still load."""
    names = {f.name for f in fields(cls)}
    return {key: value for key, value in data.items() if key in names}

@dataclass
class Job:
    """Summary data for one job, as shown in a job list."""

    source: str
    id: str
    title: str
    url: str
    company: str
    teams: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)   # ISO codes, e.g. ["CA", "US"]
    work_modes: list[str] = field(default_factory=list)  # see WORK_MODES
    employment_type: str | None = None
    posted_at: str | None = None          # ISO 8601: when the job was first published
    extra: dict[str, Any] = field(default_factory=dict)  # platform-specific values

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Job:
        """Build from saved data; works for subclasses too (cls is used)."""
        return cls(**_known_fields(cls, data))

@dataclass
class JobDetails(Job):
    """A Job plus everything from its individual posting."""

    description: str = ""
    description_format: str = "markdown"  # "markdown", "html" or "text"
    apply_url: str | None = None

    @classmethod
    def from_job(cls, job: Job, **details: Any) -> JobDetails:
        """Build details from an existing Job plus the extra fields. A field
        given in `details` replaces the job's own (e.g. a posting's
        posted_at replaces the one from the job list)."""
        return cls(**{**job.to_dict(), **details})

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