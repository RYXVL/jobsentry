"""Strategy for companies whose job board is hosted on Ashby.

Ashby publishes every hosted board as a public, read-only JSON API
(https://developers.ashbyhq.com/docs/public-job-posting-api):

    GET <api_base>/<board name>    every listed job, with its description

There's no endpoint for a single job, so details are read from the same
list (still one request). Companies aren't written as Python: each is an
entry in catalogs/ashby-sources.json, and loaders/ashby_loader.py builds a
subclass of AshbySource for it with these class attributes set:
name, company, homepage, board_names, api_base, board_base, country_hints,
state_codes.

A company can have several boards; they're fetched one request each and
merged, and each job records its board in Job.extra["board_name"].

How Ashby's fields map onto Job:

    id, title, jobUrl, publishedAt        -> id, title, url, posted_at
    team, department                      -> teams
    location + secondaryLocations         -> locations
    those, plus each address's country    -> countries (via CountryFinder)
    workplaceType (or isRemote)           -> work_modes
    employmentType ("FullTime", ...)      -> employment_type ("Full time", ...)

Ashby gives no updated time, so updated_at is always None. Descriptions
are HTML; sanitise them before rendering them in the frontend.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, ClassVar
from urllib.parse import quote

from ...core.countries import CountryFinder
from ...core.exceptions import JobNotFoundError, SourceError
from ...core.models import Job, JobDetails, sort_work_modes
from ..base import JobSource

#: Ashby's employment types, as shown in the app.
EMPLOYMENT_TYPES = {
    "FullTime": "Full time",
    "PartTime": "Part time",
    "Intern": "Intern",
    "Contract": "Contract",
    "Temporary": "Temporary",
}

#: Ashby's workplace types, mapped to core.models.WORK_MODES.
WORKPLACE_TYPES = {
    "OnSite": "on_site",
    "Onsite": "on_site",
    "Hybrid": "hybrid",
    "Remote": "remote",
}

class AshbySource(JobSource):
    """Base for companies with Ashby-hosted boards. Subclasses are built
    from the catalog; every attribute below is set by the loader."""

    strategy = "ashby"

    #: The company's board names: each is the <name> in <board_base>/<name>.
    board_names: ClassVar[tuple[str, ...]]
    #: Ashby API root, e.g. https://api.ashbyhq.com/posting-api/job-board
    api_base: ClassVar[str]
    #: Public board site root, e.g. https://jobs.ashbyhq.com
    board_base: ClassVar[str]
    #: Extra location text to count as a country (see core.countries).
    country_hints: ClassVar[dict[str, str]] = {}
    #: Read "City, ST" as a US state or Canadian province when nothing else matched.
    state_codes: ClassVar[bool] = False

    # URLs -------------------------------------------------------------------

    def board_api_url(self, board_name: str) -> str:
        return f"{self.api_base}/{quote(board_name)}"

    def job_page_url(self, board_name: str, job_id: str) -> str:
        return f"{self.board_base}/{quote(board_name)}/{quote(job_id)}"

    # JobSource --------------------------------------------------------------

    def fetch_jobs(self) -> list[Job]:
        """Every listed job on every board, one request per board."""
        finder = CountryFinder(self.country_hints, state_codes=self.state_codes)
        jobs: dict[str, Job] = {}
        for board_name in self.board_names:
            for item in self._board_items(board_name):
                job = self._to_job(item, board_name, finder)
                jobs.setdefault(job.id, job)  # listed on two boards: keep the first
        return list(jobs.values())

    def fetch_job_details(self, job: Job) -> JobDetails:
        """Ashby has no single-job endpoint, so read the job's board and pick
        the job out of it. Raises JobNotFoundError if it's been taken down."""
        board_name = job.extra.get("board_name") or self.board_names[0]
        item = next(
            (item for item in self._board_items(board_name) if str(item["id"]) == job.id),
            None,
        )
        if item is None:
            raise JobNotFoundError(f"{self.company} job '{job.id}' is no longer on its Ashby board")
        return JobDetails.from_job(
            job,
            description=str(item.get("descriptionHtml") or "").strip(),
            description_format="html",
            posted_at=item.get("publishedAt") or job.posted_at,
            apply_url=item.get("applyUrl") or job.url,
        )

    # Helpers ----------------------------------------------------------------

    def _board_items(self, board_name: str) -> list[dict[str, Any]]:
        """Every listed job entry on one board, as Ashby returns it."""
        url = self.board_api_url(board_name)
        data = self._get_json(url)
        items = data.get("jobs") if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise SourceError(f"Unexpected Ashby response at {url}: no 'jobs' list")
        return [
            item
            for item in items
            if isinstance(item, dict) and "id" in item and item.get("isListed", True) is not False
        ]

    def _get_json(self, url: str, **kwargs: Any) -> Any:
        """GET JSON, turning an unreadable body into SourceError."""
        try:
            return self.http.get_json(url, **kwargs)
        except ValueError as e:  # body wasn't valid JSON
            raise SourceError(f"{url} did not return valid JSON: {e}") from e

    def _to_job(self, item: dict[str, Any], board_name: str, finder: CountryFinder) -> Job:
        """Convert one board entry to a Job."""
        job_id = str(item["id"])
        secondary = [s for s in item.get("secondaryLocations") or [] if isinstance(s, dict)]

        locations = _unique([item.get("location"), *(s.get("location") for s in secondary)])
        address_countries = [
            _address_country(address)
            for address in [item.get("address"), *(s.get("address") for s in secondary)]
        ]

        workplace = WORKPLACE_TYPES.get(str(item.get("workplaceType") or ""))
        modes = [workplace] if workplace else (["remote"] if item.get("isRemote") else [])

        employment = item.get("employmentType")
        return Job(
            source=self.name,
            id=job_id,
            title=str(item.get("title") or "").strip(),
            url=item.get("jobUrl") or self.job_page_url(board_name, job_id),
            company=self.company,
            teams=_unique([item.get("team"), item.get("department")]),
            locations=locations,
            countries=finder.find([*locations, *(c for c in address_countries if c)]),
            # Only what Ashby states: its workplace type, or the remote flag.
            work_modes=sort_work_modes(modes),
            employment_type=EMPLOYMENT_TYPES.get(employment, employment) if employment else None,
            posted_at=item.get("publishedAt"),
            extra={"board_name": board_name},
        )

def _address_country(address: Any) -> str:
    """The country text in an Ashby address ("USA", "United Kingdom"), or ""."""
    if not isinstance(address, dict):
        return ""
    postal = address.get("postalAddress")
    return str(postal.get("addressCountry") or "").strip() if isinstance(postal, dict) else ""

def _unique(values: Iterable[Any]) -> list[str]:
    """Non-empty values as stripped text, without duplicates, in order."""
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result