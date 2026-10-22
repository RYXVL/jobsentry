"""FastAPI dependencies: how each request gets its settings and services.

Routes declare what they need (e.g. `service: JobService = Depends(get_job_service)`)
and FastAPI builds it. Tests replace these with app.dependency_overrides.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, Path

from ..config import Settings
from ..core.http import HttpClient
from ..services import JobService

@lru_cache
def get_settings() -> Settings:
    """Load settings once per process (reads backend/.env)."""
    return Settings.from_env()

def get_http_client(settings: Settings = Depends(get_settings)) -> HttpClient:
    return HttpClient(
        timeout=settings.http_timeout,
        retries=settings.http_retries,
        headers={"User-Agent": settings.user_agent},
    )

def get_job_service(
    source: str = Path(..., description="Source name, e.g. `stripe` (see GET /sources)"),
    settings: Settings = Depends(get_settings),
    http: HttpClient = Depends(get_http_client),
) -> JobService:
    """JobService for the `{source}` in the URL. Unknown names raise
    SourceNotFoundError, which errors.py turns into a 404."""
    return JobService.create(source, settings=settings, http=http)
