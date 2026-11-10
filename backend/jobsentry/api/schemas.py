"""Pydantic response models: the API's public contract with the frontend.

They mirror core.models and services.queries but only expose fields the
frontend should rely on (e.g. a Job's internal `extra` dict is left out).
`from_attributes=True` lets each model be built straight from the dataclasses.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class HealthOut(Schema):
    status: str = "ok"
    version: str

class SourceOut(Schema):
    name: str = Field(examples=["stripe"])
    company: str = Field(examples=["Stripe"])
    strategy: str = Field(description="Which platform the jobs come from, e.g. greenhouse")
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
    countries: list[str] = Field(description="ISO 3166-1 alpha-2 codes, e.g. CA, US")
    work_modes: list[str] = Field(
        description="Any of on_site, hybrid, remote; empty if the source doesn't say"
    )
    employment_type: str | None
    posted_at: str | None = Field(description="When the job was first published (ISO 8601)")
    updated_at: str | None = Field(
        description="When the platform last changed the job (ISO 8601); can reflect bulk edits"
    )

class JobDetailsOut(JobOut):
    description: str
    description_format: str = Field(description="markdown, html or text")
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

class AllJobsPageOut(Schema):
    total: int = Field(description="All matching jobs across every source, not just this page")
    limit: int
    offset: int
    fetched_at: str | None = Field(
        description="Oldest last refresh among the sources included (ISO 8601); null if none"
    )
    unfetched: list[str] = Field(description="Companies never fetched, so not included")
    countries: list[FacetValueOut] = Field(
        description="Countries among jobs matching the date filter only, with counts"
    )
    jobs: list[JobOut]

class JobFacetsOut(Schema):
    source: str
    teams: list[FacetValueOut]
    locations: list[FacetValueOut]
    countries: list[FacetValueOut] = Field(description="ISO country codes with job counts")

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
    """One source's result inside a fetch-all run."""
    source: str
    company: str
    ok: bool
    fetched_at: str | None = None
    job_count: int | None = None
    error: ErrorDetail | None = Field(None, description="Why it failed; null when ok")

class RefreshRunOut(Schema):
    """Progress of the current (or last) fetch of every source."""
    state: Literal["idle", "running", "done"] = Field(
        description="idle: none has run since the API started"
    )
    trigger: Literal["manual", "monitor"] | None = Field(
        None, description="What started the run: the button or the monitor"
    )
    started_at: str | None = None
    finished_at: str | None = None
    total: int = Field(0, description="Sources in this run")
    completed: int = Field(0, description="Sources finished, successfully or not")
    succeeded: int = 0
    failed: int = 0
    jobs_fetched: int = Field(0, description="Jobs saved so far, across finished sources")
    in_progress: list[str] = Field(
        default_factory=list, description="Companies being fetched right now"
    )
    results: list[RefreshItemOut] = Field(
        default_factory=list, description="One per finished source, in finishing order"
    )

class ClearOut(Schema):
    cleared_sources: int = Field(description="How many sources had saved data")

# Managing sources ---------------------------------------------------------

class PlatformOut(Schema):
    key: str = Field(examples=["greenhouse"])
    label: str = Field(examples=["Greenhouse"])
    has_region: bool = Field(description="True for Lever: global or EU instance")

class CatalogOut(Schema):
    edits_allowed: bool = Field(description="JOBSENTRY_ALLOW_CATALOG_EDITS")
    platforms: list[PlatformOut]

class CatalogEntryIn(Schema):
    platform: str = Field(examples=["greenhouse"])
    name: str = Field("", description="Ignored when editing: a name can't change")
    company: str
    board_names: list[str] = Field(min_length=1)
    homepage: str | None = None
    region: Literal["global", "eu"] | None = Field(None, description="Lever only")

class CatalogEntryOut(Schema):
    platform: str
    name: str
    company: str
    board_names: list[str]
    homepage: str | None
    region: str | None
    extra_keys: list[str] = Field(
        description="Keys the form doesn't edit, kept as they are (e.g. country_hints)"
    )

class CheckIn(Schema):
    platform: str
    board_names: list[str] = Field(min_length=1)
    region: Literal["global", "eu"] | None = None

class BoardCheckOut(Schema):
    board_name: str
    ok: bool
    status: int | None = Field(description="HTTP status, when known")
    job_count: int | None
    message: str
    url: str = Field(description="The request that was made")

class CheckOut(Schema):
    ok: bool = Field(description="True when every board passed")
    boards: list[BoardCheckOut]

class DeletedOut(Schema):
    name: str

class LogoOut(Schema):
    name: str
    file: str | None = Field(description="The saved file's name, e.g. wise.png")
    removed: bool = Field(description="On delete: whether a logo existed")

# Monitor ------------------------------------------------------------------

class MonitorSettingsBody(Schema):
    every: int = Field(description="15, 30 or 45 (minutes), or 1 to 24 (hours)")
    unit: Literal["minutes", "hours"]
    keywords: str = Field("", description="Same matching as Today's jobs; empty = every new job")
    sound: bool = True
    email: bool = False
    email_to: str = ""

class LastEmailOut(Schema):
    at: str
    ok: bool
    error: str | None = None

class MonitorOut(Schema):
    settings: MonitorSettingsBody
    active: bool
    started_at: str | None
    next_fetch_at: str | None
    fetching: bool = Field(description="A fetch of every source is running")
    last_fetch_started_at: str | None = Field(
        description="When the last fetch of every source started (the watermark)"
    )
    email_configured: bool = Field(description="JOBSENTRY_SMTP_* is set in backend/.env")
    email_verified: bool = Field(description="A test email to settings.email_to was confirmed")
    last_email: LastEmailOut | None
    latest_event_id: int

class MonitorJobOut(Schema):
    source: str
    id: str
    title: str
    company: str
    url: str
    locations: list[str]
    posted_at: str | None

class MonitorEventOut(Schema):
    """One alert: new jobs found by one fetch."""
    id: int
    at: str
    count: int
    play_in_browser: bool = Field(description="An open tab plays the chime (else the computer did)")
    jobs: list[MonitorJobOut]

class MonitorPollOut(Schema):
    monitor: MonitorOut
    events: list[MonitorEventOut]

class TestEmailIn(Schema):
    email_to: str

class ConfirmEmailIn(Schema):
    email_to: str
    received: bool

class MessageOut(Schema):
    message: str