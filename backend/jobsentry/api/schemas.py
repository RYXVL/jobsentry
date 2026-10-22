"""Pydantic response models: the API's public contract with the frontend.

They mirror core.models and services.queries but only expose fields the
frontend should rely on (e.g. a Job's internal `extra` dict is left out).
`from_attributes=True` lets each model be built straight from the dataclasses.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class HealthOut(Schema):
    status: str = "ok"
    version: str

class SourceOut(Schema):
    name: str = Field(examples=["stripe"])
    company: str = Field(examples=["Stripe"])
    strategy: str = Field(description="How the site delivers data, e.g. next_data")
    homepage: str
    fetched_at: str | None = Field(None, description="Last refresh (ISO 8601), null if never")
    job_count: int | None = Field(None, description="Jobs in the last refresh, null if never")

class JobOut(Schema):
    source: str
    id: str
    title: str
    url: str
    company: str
    teams: list[str]
    locations: list[str]
    remote: bool
    employment_type: str | None
    tags: list[str]

class SalaryOut(Schema):
    min: float | None
    max: float | None
    currency: str | None
    period: str | None

class JobDetailsOut(JobOut):
    description: str
    description_format: str = Field(description="markdown, html or text")
    posted_at: str | None
    salary: SalaryOut | None
    apply_url: str | None

class JobPageOut(Schema):
    source: str
    fetched_at: str
    total: int = Field(description="All matching jobs, not just this page")
    limit: int
    offset: int
    jobs: list[JobOut]

class FacetValueOut(Schema):
    value: str
    count: int

class JobFacetsOut(Schema):
    source: str
    teams: list[FacetValueOut]
    locations: list[FacetValueOut]
    employment_types: list[FacetValueOut]
    tags: list[FacetValueOut]

class RefreshOut(Schema):
    source: str
    fetched_at: str
    job_count: int

class ErrorDetail(Schema):
    code: str = Field(examples=["job_not_found"])
    message: str
    details: list[dict] | None = Field(None, description="Per-field problems (422 only)")

class ErrorOut(Schema):
    error: ErrorDetail

class RefreshItemOut(Schema):
    """One source's result inside a refresh-all."""
    source: str
    company: str
    ok: bool
    fetched_at: str | None = None
    job_count: int | None = None
    error: ErrorDetail | None = Field(None, description="Why it failed; null when ok")

class RefreshAllOut(Schema):
    results: list[RefreshItemOut]
    succeeded: int
    failed: int

class ClearOut(Schema):
    cleared_sources: int = Field(description="How many sources had saved data")