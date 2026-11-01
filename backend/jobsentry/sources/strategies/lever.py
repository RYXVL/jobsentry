"""Strategy for companies whose job board is hosted on Lever.

Lever publishes every hosted board as a public, read-only JSON API
(https://github.com/lever/postings-api), on a global and an EU instance:

    GET <api_base>/<board name>?mode=json          every published posting
    GET <api_base>/<board name>/<id>?mode=json     one posting

Companies aren't written as Python: each is an entry in
catalogs/lever-sources.json, and loaders/lever_loader.py builds a subclass
of LeverSource for it with these class attributes set: name, company,
homepage, board_names, api_base, board_base, country_hints, state_codes.

A company can have several boards; they're fetched one request each and
merged, and each job records its board in Job.extra["board_name"].

How Lever's fields map onto Job:

    id, text, hostedUrl                       -> id, title, url
    categories.team, categories.department    -> teams
    categories.location, .allLocations        -> locations
    country (ISO code), plus those locations  -> countries
    workplaceType                             -> work_modes ("unspecified" -> none)
    categories.commitment                     -> employment_type
    createdAt (epoch milliseconds)            -> posted_at (ISO 8601, UTC)

createdAt is when the posting was created in Lever, normally close to when
it was published. Lever gives no updated time, so updated_at is always None.
Descriptions are HTML; sanitise them before rendering them in the frontend.
"""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Any, ClassVar
from urllib.parse import quote

from ...core.countries import CountryFinder
from ...core.exceptions import SourceError
from ...core.models import Job, JobDetails, normalize_countries, sort_work_modes
from ..base import JobSource
from ._helpers import get_json, unique_texts

#: Lever's workplace types, mapped to core.models.WORK_MODES.
WORKPLACE_TYPES = {
    "onsite": "on_site",
    "on-site": "on_site",
    "hybrid": "hybrid",
    "remote": "remote",
}

_COUNTRY_CODE = re.compile(r"^[A-Z]{2}$")

class LeverSource(JobSource):
    """Base for companies with Lever-hosted boards. Subclasses are built
    from the catalog; every attribute below is set by the loader."""

    strategy = "lever"

    #: The company's boards: each is the <name> in <board_base>/<name>.
    board_names: ClassVar[tuple[str, ...]]
    #: Lever API root for the company's region, e.g. https://api.lever.co/v0/postings
    api_base: ClassVar[str]
    #: Public board site root for the company's region, e.g. https://jobs.lever.co
    board_base: ClassVar[str]
    #: Extra location text to count as a country (see core.countries).
    country_hints: ClassVar[dict[str, str]] = {}
    #: Read "City, ST" as a US state or Canadian province when nothing else matched.
    state_codes: ClassVar[bool] = False

    # URLs -------------------------------------------------------------------

    def board_api_url(self, board_name: str) -> str:
        return f"{self.api_base}/{quote(board_name)}"

    def posting_api_url(self, board_name: str, posting_id: str) -> str:
        return f"{self.api_base}/{quote(board_name)}/{quote(posting_id)}"

    def posting_page_url(self, board_name: str, posting_id: str) -> str:
        return f"{self.board_base}/{quote(board_name)}/{quote(posting_id)}"

    # JobSource --------------------------------------------------------------

    def fetch_jobs(self) -> list[Job]:
        """Every published posting on every board, one request per board."""
        finder = CountryFinder(self.country_hints, state_codes=self.state_codes)
        jobs: dict[str, Job] = {}
        for board_name in self.board_names:
            for item in self._board_items(board_name):
                job = self._to_job(item, board_name, finder)
                jobs.setdefault(job.id, job)  # listed on two boards: keep the first
        return list(jobs.values())

    def fetch_job_details(self, job: Job) -> JobDetails:
        # "site" is the key jobs saved by an earlier version recorded.
        board_name = job.extra.get("board_name") or job.extra.get("site") or self.board_names[0]
        url = self.posting_api_url(board_name, job.id)
        item = get_json(self.http, url, params={"mode": "json"})
        if not isinstance(item, dict) or "id" not in item:
            raise SourceError(f"Unexpected Lever response at {url}: no posting")
        return JobDetails.from_job(
            job,
            description=_full_description(item),
            description_format="html",
            posted_at=_iso_from_millis(item.get("createdAt")) or job.posted_at,
            apply_url=item.get("applyUrl") or job.url,
        )

    # Helpers ----------------------------------------------------------------

    def _board_items(self, board_name: str) -> list[dict[str, Any]]:
        """Every published posting on one board, as Lever returns it (a list)."""
        url = self.board_api_url(board_name)
        data = get_json(self.http, url, params={"mode": "json"})
        if not isinstance(data, list):
            raise SourceError(f"Unexpected Lever response at {url}: expected a list of postings")
        return [item for item in data if isinstance(item, dict) and "id" in item]

    def _to_job(self, item: dict[str, Any], board_name: str, finder: CountryFinder) -> Job:
        """Convert one posting to a Job."""
        posting_id = str(item["id"])
        categories = item.get("categories") if isinstance(item.get("categories"), dict) else {}
        locations = unique_texts(
            [categories.get("location"), *(categories.get("allLocations") or [])]
        )

        # Lever's own country code is exact; the location text adds any others.
        code = str(item.get("country") or "").strip().upper()
        stated = [code] if _COUNTRY_CODE.match(code) else []

        mode = WORKPLACE_TYPES.get(str(item.get("workplaceType") or "").lower())
        return Job(
            source=self.name,
            id=posting_id,
            title=str(item.get("text") or "").strip(),
            url=item.get("hostedUrl") or self.posting_page_url(board_name, posting_id),
            company=self.company,
            teams=unique_texts([categories.get("team"), categories.get("department")]),
            locations=locations,
            countries=normalize_countries([*stated, *finder.find(locations)]),
            # Only what Lever states; "unspecified" gives no mode.
            work_modes=sort_work_modes([mode] if mode else []),
            employment_type=str(categories.get("commitment") or "").strip() or None,
            posted_at=_iso_from_millis(item.get("createdAt")),
            extra={"board_name": board_name},
        )

def _iso_from_millis(value: Any) -> str | None:
    """Lever's epoch milliseconds as ISO 8601 in UTC, or None if unreadable."""
    if isinstance(value, bool):
        return None
    try:
        seconds = float(value) / 1000
        return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError, OverflowError, OSError):
        return None

def _full_description(item: dict[str, Any]) -> str:
    """Lever splits a posting into `description`, titled `lists` (e.g.
    Responsibilities, each with <li> items) and `additional`. Join them back
    into one HTML document, in that order."""
    parts = [str(item.get("description") or "").strip()]
    for section in item.get("lists") or []:
        if not isinstance(section, dict):
            continue
        heading = html.escape(str(section.get("text") or "").strip())
        items = str(section.get("content") or "").strip()
        if heading:
            parts.append(f"<h3>{heading}</h3>")
        if items:
            parts.append(f"<ul>{items}</ul>")
    parts.append(str(item.get("additional") or "").strip())
    return "\n".join(part for part in parts if part)