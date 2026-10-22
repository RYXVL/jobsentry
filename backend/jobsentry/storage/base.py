"""The interface every storage backend implements."""

from __future__ import annotations

from abc import ABC, abstractmethod

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
