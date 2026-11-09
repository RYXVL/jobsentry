"""Strategy for companies whose job board is hosted on SmartRecruiters.

SmartRecruiters publishes public postings through its Posting API
(https://developers.smartrecruiters.com). Only the list endpoint is used:

    GET <api_base>/<board name>/postings?limit=100&offset=<n>

It returns one page of postings plus the board's total, as
{"offset": 0, "limit": 100, "totalFound": 427, "content": [...]}. A refresh
fetches pages one after another until it has totalFound postings, a page
comes back empty, or max_pages is reached (a warning is logged and the
postings collected so far are kept). No filters are sent; only English
postings (and those without a language) are kept, in our code.

The single-posting endpoint isn't used: each job links to its public page,
<board_base>/<board name>/<id>, so details are built from the saved job
without a request (an empty description, the posting page as the apply link).

Companies aren't written as Python: each is an entry in
catalogs/smartrecruiters-sources.json, and loaders/smartrecruiters_loader.py
builds a subclass of SmartRecruitersSource for it with these class
attributes set: name, company, homepage, board_names, api_base, board_base,
max_pages, country_hints, state_codes.

How a posting's fields map onto Job:

    id, name, releasedDate                 -> id, title, posted_at
    <board_base>/<board name>/<id>         -> url
    location.country (ISO code)            -> countries (CountryFinder on the
                                              location text if there's no code)
    location.fullLocation, gaps removed    -> locations
    location.remote / location.hybrid      -> work_modes: remote, hybrid,
                                              otherwise on-site
    department.label, function.label       -> teams
    typeOfEmployment.label                 -> employment_type

SmartRecruiters gives no updated time, so updated_at is always None. Its
API answers a wrong board name exactly like a board with no jobs (200, with
totalFound 0), so check totalFound in a browser before adding a company;
check_refresh then refuses to replace saved jobs with an empty result.
"""

from __future__ import annotations

import logging
import re
from typing import Any, ClassVar
from urllib.parse import quote

from ...core.countries import CountryFinder
from ...core.exceptions import SourceError
from ...core.models import Job, JobDetails, JobSnapshot, normalize_countries, sort_work_modes
from ..base import JobSource
from ._helpers import get_json, unique_texts

log = logging.getLogger(__name__)

#: Postings per list request (the API's maximum).
PAGE_SIZE = 100

_COUNTRY_CODE = re.compile(r"^[A-Za-z]{2}$")

class SmartRecruitersSource(JobSource):
    """Base for companies with SmartRecruiters-hosted boards. Subclasses are
    built from the catalog; every attribute below is set by the loader."""

    strategy = "smartrecruiters"

    #: The company identifiers: each is the <name> in <board_base>/<name>.
    #: Case-sensitive, e.g. "Wise", "BoschGroup".
    board_names: ClassVar[tuple[str, ...]]
    #: Posting API root, e.g. https://api.smartrecruiters.com/v1/companies
    api_base: ClassVar[str]
    #: Public job page root, e.g. https://jobs.smartrecruiters.com
    board_base: ClassVar[str]
    #: Most list pages (of PAGE_SIZE postings) fetched per board per refresh.
    max_pages: ClassVar[int] = 100
    #: Extra location text to count as a country (see core.countries).
    country_hints: ClassVar[dict[str, str]] = {}
    #: Read "City, ST" as a US state or Canadian province when nothing else matched.
    state_codes: ClassVar[bool] = False

    # URLs -------------------------------------------------------------------

    def postings_api_url(self, board_name: str) -> str:
        return f"{self.api_base}/{quote(board_name)}/postings"

    def posting_page_url(self, board_name: str, posting_id: str) -> str:
        return f"{self.board_base}/{quote(board_name)}/{quote(posting_id)}"

    # JobSource --------------------------------------------------------------

    def fetch_jobs(self) -> list[Job]:
        """Every English posting on every board, PAGE_SIZE per request."""
        finder = CountryFinder(self.country_hints, state_codes=self.state_codes)
        jobs: dict[str, Job] = {}
        for board_name in self.board_names:
            for item in self._board_items(board_name):
                if not _is_english(item):
                    continue
                job = self._to_job(item, board_name, finder)
                jobs.setdefault(job.id, job)  # listed on two boards: keep the first
        return list(jobs.values())

    def fetch_job_details(self, job: Job) -> JobDetails:
        """No request: only the list endpoint is used, and the job's page
        (job.url) shows the full posting. Returns the saved job with an
        empty description and the posting page as the apply link."""
        return JobDetails.from_job(job, description="", description_format="text", apply_url=job.url)

    def check_refresh(self, jobs: list[Job], previous: JobSnapshot | None) -> None:
        """Refuse to replace saved jobs with an empty result. The API answers
        a wrong or broken board name with 0 postings rather than an error,
        so a sudden drop to 0 is treated as a failure, and the saved jobs
        are kept. A first refresh with 0 postings is saved normally."""
        if jobs or previous is None or not previous.jobs:
            return
        raise SourceError(
            f"SmartRecruiters returned no jobs for {self.company} "
            f"(previously {len(previous.jobs)}); keeping the saved jobs. Check the board name."
        )

    # Helpers ----------------------------------------------------------------

    def _board_items(self, board_name: str) -> list[dict[str, Any]]:
        """Every posting on one board, one page at a time, stopping at
        totalFound, an empty page, or max_pages."""
        url = self.postings_api_url(board_name)
        items: list[dict[str, Any]] = []
        offset = 0
        total: int | None = None
        for _ in range(self.max_pages):
            data = get_json(self.http, url, params={"limit": PAGE_SIZE, "offset": offset})
            content = data.get("content") if isinstance(data, dict) else None
            if not isinstance(content, list):
                raise SourceError(f"Unexpected SmartRecruiters response at {url}: no 'content' list")
            if total is None and isinstance(data.get("totalFound"), int):
                total = data["totalFound"]
            if not content:
                break
            items += [item for item in content if isinstance(item, dict) and "id" in item]
            offset += len(content)
            if total is not None and offset >= total:
                break
        else:
            log.warning(
                "%s: stopped at max_pages=%d for board %s (%d of %s postings)",
                self.company, self.max_pages, board_name, offset, total if total is not None else "?",
            )
        return items

    def _to_job(self, item: dict[str, Any], board_name: str, finder: CountryFinder) -> Job:
        """Convert one posting to a Job."""
        posting_id = str(item["id"])
        location = item.get("location") if isinstance(item.get("location"), dict) else {}
        place = _clean_location(location)
        locations = [place] if place else []

        # The posting's own country code is exact; fall back to the text.
        code = str(location.get("country") or "").strip()
        countries = [code.upper()] if _COUNTRY_CODE.match(code) else finder.find(locations)

        if not location:
            modes: list[str] = []  # nothing stated
        elif location.get("remote") is True:
            modes = ["remote"]
        elif location.get("hybrid") is True:
            modes = ["hybrid"]
        else:
            modes = ["on_site"]

        return Job(
            source=self.name,
            id=posting_id,
            title=str(item.get("name") or "").strip(),
            url=self.posting_page_url(board_name, posting_id),
            company=self.company,
            teams=unique_texts([_label(item.get("department")), _label(item.get("function"))]),
            locations=locations,
            countries=normalize_countries(countries),
            work_modes=sort_work_modes(modes),
            employment_type=_label(item.get("typeOfEmployment")) or None,
            posted_at=item.get("releasedDate"),
            extra={"board_name": board_name},
        )

def _is_english(item: dict[str, Any]) -> bool:
    """True for English postings ("en", "en-GB", ...) and for postings
    without a language, which can't be filtered."""
    language = item.get("language")
    code = str(language.get("code") or "").strip().lower() if isinstance(language, dict) else ""
    return not code or code == "en" or code.startswith(("en-", "en_"))

def _clean_location(location: dict[str, Any]) -> str:
    """fullLocation without empty parts ("London, , United Kingdom" becomes
    "London, United Kingdom"), or city and region if there's no fullLocation."""
    parts = [part.strip() for part in str(location.get("fullLocation") or "").split(",")]
    cleaned = ", ".join(part for part in parts if part)
    return cleaned or ", ".join(unique_texts([location.get("city"), location.get("region")]))

def _label(value: Any) -> str:
    """The "label" of a {"id": ..., "label": ...} object, or "" (e.g. for {})."""
    return str(value.get("label") or "").strip() if isinstance(value, dict) else ""