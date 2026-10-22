"""The contract every source implements.

A source knows how to read one company's career site and return data in the
shared models from core.models. It does not save anything; that is the
storage layer's job.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from ..core.http import HttpClient
from ..core.models import Job, JobDetails

@dataclass(frozen=True)
class SourceInfo:
    """Public description of a source (shown by `sources`, returned by the API)."""

    name: str
    company: str
    strategy: str
    homepage: str

class JobSource(ABC):
    #: Registry key used on the command line, e.g. "stripe". Lowercase, no spaces.
    name: ClassVar[str]
    #: Display name, e.g. "Stripe".
    company: ClassVar[str]
    #: Careers page URL, for reference.
    homepage: ClassVar[str] = ""
    #: How the site delivers data; set by strategy base classes.
    strategy: ClassVar[str] = "custom"

    def __init__(self, http: HttpClient | None = None):
        self.http = http or HttpClient()

    @classmethod
    def info(cls) -> SourceInfo:
        return SourceInfo(cls.name, cls.company, cls.strategy, cls.homepage)

    @abstractmethod
    def fetch_jobs(self) -> list[Job]:
        """Return every open job (summary data only)."""

    @abstractmethod
    def fetch_job_details(self, job: Job) -> JobDetails:
        """Return full details for a job previously returned by fetch_jobs()."""
