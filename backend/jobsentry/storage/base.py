"""The interface every storage backend implements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..core.models import JobDetails, JobSnapshot

class JobStore(ABC):
    @abstractmethod
    def save_snapshot(self, snapshot: JobSnapshot) -> str:
        """Save all jobs for a source; return where they were saved."""

    @abstractmethod
    def load_snapshot(self, source: str) -> JobSnapshot | None:
        """Return the last saved snapshot, or None if there isn't one."""

    @abstractmethod
    def save_details(self, details: JobDetails) -> str:
        """Save one job's full details; return where they were saved."""

    @abstractmethod
    def load_details(self, source: str, job_id: str) -> JobDetails | None:
        """Return saved details for a job, or None if not saved yet."""

    @abstractmethod
    def save_today(self, data: dict[str, Any]) -> str:
        """Save the today's-jobs index (see services.today_jobs); return where."""

    @abstractmethod
    def load_today(self) -> dict[str, Any] | None:
        """Return the saved today's-jobs index, or None if there isn't one."""

    @abstractmethod
    def delete_source(self, source: str) -> bool:
        """Delete one source's saved snapshot and job details. Return
        whether it had saved data."""

    @abstractmethod
    def clear(self) -> int:
        """Delete every saved snapshot, job detail and the today's-jobs index.
        Return how many sources had saved data."""