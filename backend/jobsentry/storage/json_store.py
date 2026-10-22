"""JSON-file storage, one folder per source:

    <data_dir>/<source>/jobs.json         all jobs from the last `list`
    <data_dir>/<source>/jobs/<id>.json    full details from `show`
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..core.models import JobDetails, JobSnapshot
from .base import JobStore

class JsonJobStore(JobStore):
    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)

    def snapshot_path(self, source: str) -> Path:
        return self.data_dir / source / "jobs.json"

    def details_path(self, source: str, job_id: str) -> Path:
        return self.data_dir / source / "jobs" / f"{job_id}.json"

    def save_snapshot(self, snapshot: JobSnapshot) -> str:
        path = self.snapshot_path(snapshot.source)
        self._write(path, snapshot.to_dict())
        return str(path)

    def load_snapshot(self, source: str) -> JobSnapshot | None:
        data = self._read(self.snapshot_path(source))
        return JobSnapshot.from_dict(data) if data else None

    def save_details(self, details: JobDetails) -> str:
        path = self.details_path(details.source, details.id)
        self._write(path, asdict(details))
        return str(path)

    def load_details(self, source: str, job_id: str) -> JobDetails | None:
        data = self._read(self.details_path(source, job_id))
        return JobDetails.from_dict(data) if data else None

    # Helpers
    @staticmethod
    def _read(path: Path) -> Any:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write(path: Path, data: Any) -> None:
        """Write via a temp file so a crash never leaves a half-written file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, path)
        except BaseException:
            os.unlink(tmp)
            raise
