"""Strategy for companies whose job board is hosted on Greenhouse.

Greenhouse publishes every hosted board as a public, read-only JSON API
(https://developers.greenhouse.io/job-board.html):

    GET <api_base>/<token>/jobs?content=true   every job, with description,
                                               departments and offices
    GET <api_base>/<token>/jobs/<id>           one job

Companies aren't written as Python: each is an entry in
catalogs/greenhouse-sources.json, and loaders/greenhouse_loader.py builds a
subclass of GreenhouseSource for it with these class attributes set:
name, company, homepage, board_token, api_base, board_base, country_hints.

A refresh is one request. How Greenhouse's fields map onto Job:

    title, absolute_url, first_published  -> title, url, posted_at
    departments[].name                    -> teams
    location.name (free text)             -> locations, split on • ; |
    country names in the locations        -> countries (plus country_hints)
    "Remote" / "Hybrid" in the locations  -> work_modes (only when stated)
    metadata "Employment Type" (if set)   -> employment_type

Only first_published is used for dates. Greenhouse's updated_at changes
whenever anything in a job's record changes, including bulk edits across a
whole board, so it doesn't reliably mean the posting itself changed.

Descriptions are HTML. Sanitise them before rendering them in the frontend.
"""

from __future__ import annotations

import html
import re
from typing import Any, ClassVar

from ...core.countries import CountryFinder
from ...core.exceptions import SourceError
from ...core.models import Job, JobDetails, sort_work_modes
from ..base import JobSource

#: Separators boards put between several places in one location field
#: ("San Francisco, CA • New York, NY"). Commas aren't split on, because they
#: usually separate a city from its state or country.
_LOCATION_SEPARATORS = re.compile(r"\s*(?:•|;|\|)\s*")

#: Location text that means "no location given".
_NO_LOCATION = frozenset({"n/a", "na", "tbd", "-"})

_REMOTE = re.compile(r"\bremote\b", re.IGNORECASE)
_HYBRID = re.compile(r"\bhybrid\b", re.IGNORECASE)

#: Custom-field names boards use for the employment type (compared lower-case).
EMPLOYMENT_TYPE_FIELDS = frozenset({"employment type", "employment_type", "job type", "time type"})

class GreenhouseSource(JobSource):
    """Base for companies with a Greenhouse-hosted board. Subclasses are
    built from the catalog; every attribute below is set by the loader."""

    strategy = "greenhouse"

    #: The board's token: the <token> in <board_base>/<token>.
    board_token: ClassVar[str]
    #: Greenhouse API root, e.g. https://boards-api.greenhouse.io/v1/boards
    api_base: ClassVar[str]
    #: Public board site root, e.g. https://boards.greenhouse.io
    board_base: ClassVar[str]
    #: Extra location text to count as a country, for places listed without
    #: one, e.g. {"San Francisco": "US", "Toronto": "CA"}. Whole words, any case.
    country_hints: ClassVar[dict[str, str]] = {}

    # URLs -------------------------------------------------------------------

    def jobs_api_url(self) -> str:
        return f"{self.api_base}/{self.board_token}/jobs"

    def job_api_url(self, job_id: str) -> str:
        return f"{self.api_base}/{self.board_token}/jobs/{job_id}"

    def job_page_url(self, job_id: str) -> str:
        return f"{self.board_base}/{self.board_token}/jobs/{job_id}"

    # JobSource --------------------------------------------------------------

    def fetch_jobs(self) -> list[Job]:
        """Every job on the board, in one request."""
        url = self.jobs_api_url()
        data = self._get_json(url, params={"content": "true"})
        items = data.get("jobs") if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise SourceError(f"Unexpected Greenhouse response at {url}: no 'jobs' list")
        finder = CountryFinder(self.country_hints)
        return [
            self._to_job(item, finder)
            for item in items
            if isinstance(item, dict) and "id" in item
        ]

    def fetch_job_details(self, job: Job) -> JobDetails:
        url = self.job_api_url(job.id)
        item = self._get_json(url)
        if not isinstance(item, dict) or "id" not in item:
            raise SourceError(f"Unexpected Greenhouse response at {url}: no job")
        return JobDetails.from_job(
            job,
            # Greenhouse sends the description as escaped HTML ("&lt;p&gt;...").
            description=html.unescape(item.get("content") or "").strip(),
            description_format="html",
            posted_at=item.get("first_published") or job.posted_at,
            apply_url=item.get("absolute_url") or job.url,
        )

    # Helpers ----------------------------------------------------------------

    def _get_json(self, url: str, **kwargs: Any) -> Any:
        """GET JSON, turning an unreadable body into SourceError."""
        try:
            return self.http.get_json(url, **kwargs)
        except ValueError as e:  # body wasn't valid JSON
            raise SourceError(f"{url} did not return valid JSON: {e}") from e

    def _to_job(self, item: dict[str, Any], finder: CountryFinder) -> Job:
        """Convert one board entry to a Job."""
        job_id = str(item["id"])
        location_text = str((item.get("location") or {}).get("name") or "").strip()
        locations = [
            part
            for part in _LOCATION_SEPARATORS.split(location_text)
            if part and part.lower() not in _NO_LOCATION
        ]

        modes = []
        if _REMOTE.search(location_text):
            modes.append("remote")
        if _HYBRID.search(location_text):
            modes.append("hybrid")

        return Job(
            source=self.name,
            id=job_id,
            title=str(item.get("title") or "").strip(),
            url=item.get("absolute_url") or self.job_page_url(job_id),
            company=self.company,
            teams=[
                str(d["name"]).strip()
                for d in item.get("departments") or []
                if isinstance(d, dict) and d.get("name")
            ],
            locations=locations,
            countries=finder.find(locations),
            # Only what the location text states; Greenhouse has no field for this.
            work_modes=sort_work_modes(modes),
            employment_type=_metadata_value(item, EMPLOYMENT_TYPE_FIELDS),
            posted_at=item.get("first_published"),
        )

def _metadata_value(item: dict[str, Any], names: frozenset[str]) -> str | None:
    """The value of the first custom field whose name is in `names`, as text.
    Boards define their own fields, so most have none of these."""
    for field in item.get("metadata") or []:
        if not isinstance(field, dict):
            continue
        if str(field.get("name") or "").strip().lower() not in names:
            continue
        value = field.get("value")
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value if v)
        text = str(value).strip() if value is not None else ""
        return text or None
    return None