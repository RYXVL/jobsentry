"""Strategy for companies whose job board is hosted on Greenhouse.

Greenhouse publishes every hosted board as a public, read-only JSON API
(https://developers.greenhouse.io/job-board.html):

    GET <api_base>/<token>/jobs?content=true   every job, with description,
                                               departments and offices
    GET <api_base>/<token>/jobs/<id>           one job

Companies aren't written as Python: each is an entry in
catalogs/greenhouse-sources.json, and loaders/greenhouse_loader.py builds a
subclass of GreenhouseSource for it with these class attributes set:
name, company, homepage, board_tokens, api_base, board_base, country_hints,
state_codes.

A company can have several boards (e.g. one per region). A refresh fetches
each board once and merges them; Greenhouse job IDs are unique across all
boards, so a job listed on two boards is kept once. Each job records its
board in Job.extra["board_token"], so details are fetched from the right one.

How Greenhouse's fields map onto Job:

    title, absolute_url                   -> title, url
    first_published, updated_at           -> posted_at, updated_at
    departments[].name                    -> teams
    location.name (free text)             -> locations, split on • ; |
    country names in the locations        -> countries (plus country_hints,
                                             and "City, ST" if state_codes)
    "Remote" / "Hybrid" in the locations  -> work_modes (only when stated)
    metadata "Employment Type" (if set)   -> employment_type

updated_at changes whenever anything in a job's record changes, including
bulk edits across a whole board, so many jobs can share one updated time.

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

#: Location text that means "no location given" (compared lower-case),
#: including placeholders boards leave unfilled, like "LOCATION".
_NO_LOCATION = frozenset({"n/a", "na", "tbd", "-", "location"})

_REMOTE = re.compile(r"\bremote\b", re.IGNORECASE)
_HYBRID = re.compile(r"\bhybrid\b", re.IGNORECASE)

#: Custom-field names boards use for the employment type (compared lower-case).
EMPLOYMENT_TYPE_FIELDS = frozenset({"employment type", "employment_type", "job type", "time type"})

class GreenhouseSource(JobSource):
    """Base for companies with Greenhouse-hosted boards. Subclasses are
    built from the catalog; every attribute below is set by the loader."""

    strategy = "greenhouse"

    #: The company's board tokens: each is the <token> in <board_base>/<token>.
    #: Usually one; several for companies with a board per region.
    board_tokens: ClassVar[tuple[str, ...]]
    #: Greenhouse API root, e.g. https://boards-api.greenhouse.io/v1/boards
    api_base: ClassVar[str]
    #: Public board site root, e.g. https://boards.greenhouse.io
    board_base: ClassVar[str]
    #: Extra location text to count as a country, for places listed without
    #: one, e.g. {"San Francisco": "US", "Toronto": "CA"}. Whole words, any case.
    country_hints: ClassVar[dict[str, str]] = {}
    #: Read "City, ST" as a US state or Canadian province when nothing else
    #: matched. Only for boards that write North American locations this way.
    state_codes: ClassVar[bool] = False

    # URLs -------------------------------------------------------------------

    def jobs_api_url(self, board_token: str) -> str:
        return f"{self.api_base}/{board_token}/jobs"

    def job_api_url(self, board_token: str, job_id: str) -> str:
        return f"{self.api_base}/{board_token}/jobs/{job_id}"

    def job_page_url(self, board_token: str, job_id: str) -> str:
        return f"{self.board_base}/{board_token}/jobs/{job_id}"

    # JobSource --------------------------------------------------------------

    def fetch_jobs(self) -> list[Job]:
        """Every job on every board, one request per board."""
        finder = CountryFinder(self.country_hints, state_codes=self.state_codes)
        jobs: dict[str, Job] = {}
        for board_token in self.board_tokens:
            for item in self._board_items(board_token):
                job = self._to_job(item, board_token, finder)
                jobs.setdefault(job.id, job)  # listed on two boards: keep the first
        return list(jobs.values())

    def fetch_job_details(self, job: Job) -> JobDetails:
        # Jobs saved before boards were recorded fall back to the first board.
        board_token = job.extra.get("board_token") or self.board_tokens[0]
        url = self.job_api_url(board_token, job.id)
        item = self._get_json(url)
        if not isinstance(item, dict) or "id" not in item:
            raise SourceError(f"Unexpected Greenhouse response at {url}: no job")
        return JobDetails.from_job(
            job,
            # Greenhouse sends the description as escaped HTML ("&lt;p&gt;...").
            description=html.unescape(item.get("content") or "").strip(),
            description_format="html",
            posted_at=item.get("first_published") or job.posted_at,
            updated_at=item.get("updated_at") or job.updated_at,
            apply_url=item.get("absolute_url") or job.url,
        )

    # Helpers ----------------------------------------------------------------

    def _board_items(self, board_token: str) -> list[dict[str, Any]]:
        """Every job entry on one board, as Greenhouse returns it."""
        url = self.jobs_api_url(board_token)
        data = self._get_json(url, params={"content": "true"})
        items = data.get("jobs") if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise SourceError(f"Unexpected Greenhouse response at {url}: no 'jobs' list")
        return [item for item in items if isinstance(item, dict) and "id" in item]

    def _get_json(self, url: str, **kwargs: Any) -> Any:
        """GET JSON, turning an unreadable body into SourceError."""
        try:
            return self.http.get_json(url, **kwargs)
        except ValueError as e:  # body wasn't valid JSON
            raise SourceError(f"{url} did not return valid JSON: {e}") from e

    def _to_job(self, item: dict[str, Any], board_token: str, finder: CountryFinder) -> Job:
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
            url=item.get("absolute_url") or self.job_page_url(board_token, job_id),
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
            updated_at=item.get("updated_at"),
            extra={"board_token": board_token},
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