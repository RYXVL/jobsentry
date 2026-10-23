"""Stripe careers (https://stripe.com/careers). Next.js site backed by Greenhouse.

  /careers/search               pageProps.jobIndexData: every job. Teams,
                                locations and tags are stored as indexes into
                                lookup lists in jobIndexData.filters.
  /careers/listing/<slug>/<id>  pageProps.listing: one job with description
                                (Markdown), salary and posting date.

Locations form a tree through parentLocationIndex: regions ("Americas") at
the top, then countries, then cities and "Remote in ..." entries. Every
entry has a countryCode, but a region's is only a representative one
("Americas" says US), so countries are taken from non-region entries only.

The search index has no dates, so fetch_jobs() also makes one request to
Stripe's public Greenhouse board for every job's posting date, matched by
job ID (the index's greenhouseId). That request is optional: if it fails,
the jobs are still returned, just without dates.
"""

from __future__ import annotations

import logging
from typing import Any

from ...core.exceptions import SourceError
from ...core.models import Job, JobDetails, Salary, normalize_countries, sort_work_modes
from ..greenhouse_api import apply_posted_dates, fetch_posted_dates
from ..registry import register
from ..strategies import NextDataSource

logger = logging.getLogger(__name__)

BASE_URL = "https://stripe.com"

#: Stripe's board on Greenhouse: boards-api.greenhouse.io/v1/boards/<token>/jobs
GREENHOUSE_BOARD = "stripe"

@register
class StripeSource(NextDataSource):
    name = "stripe"
    company = "Stripe"
    homepage = f"{BASE_URL}/careers/search"

    def fetch_jobs(self) -> list[Job]:
        props = self.get_page_props(f"{BASE_URL}/careers/search")
        try:
            index = props["jobIndexData"]
            filters, listings = index["filters"], index["listings"]
        except KeyError as e:
            raise SourceError(f"Stripe job index missing {e}") from e
        jobs = [self._to_job(item, filters) for item in listings]
        return self._add_posted_dates(jobs)

    def fetch_job_details(self, job: Job) -> JobDetails:
        listing = self.get_page_props(job.url).get("listing")
        if not listing:
            raise SourceError(f"No listing data at {job.url}")

        salary = None
        if listing.get("salaryMin") is not None:
            salary = Salary(
                min=listing["salaryMin"],
                max=listing.get("salaryMax"),
                currency=listing.get("salaryCurrency"),
                period="YEAR",
            )

        slug = job.extra.get("slug") or listing.get("slug")
        return JobDetails.from_job(
            job,
            description=(listing.get("contentMarkdown") or "").strip(),
            description_format="markdown",
            posted_at=listing.get("postedAt") or job.posted_at,
            salary=salary,
            apply_url=f"{BASE_URL}/careers/apply/{slug}/{job.id}",
        )

    def _add_posted_dates(self, jobs: list[Job]) -> list[Job]:
        """Copy posting dates from Greenhouse onto `jobs`.
        On any failure (including a block, which is never retried), log it
        and return the jobs without dates rather than failing the refresh."""
        try:
            dates = fetch_posted_dates(self.http, GREENHOUSE_BOARD)
        except SourceError as e:
            logger.warning("Stripe: posting dates unavailable from Greenhouse: %s", e)
            return jobs
        return apply_posted_dates(jobs, dates)

    def _to_job(self, item: dict[str, Any], filters: dict[str, Any]) -> Job:
        """Convert one index entry, resolving its index numbers into names."""
        locations = [filters["locations"][i] for i in item.get("locationIndices", [])]
        job_id = str(item["greenhouseId"])
        return Job(
            source=self.name,
            id=job_id,
            title=item["title"],
            url=f"{BASE_URL}/careers/listing/{item['slug']}/{job_id}",
            company=self.company,
            teams=[filters["teams"][i]["name"] for i in item.get("teamIndices", [])],
            locations=[loc["name"] for loc in locations],
            # Regions have no parent and only a representative code; skip them.
            countries=normalize_countries(
                loc.get("countryCode") for loc in locations if "parentLocationIndex" in loc
            ),
            remote=any(loc.get("remote") for loc in locations),
            # Each location is flagged remote or not; Stripe never says hybrid.
            work_modes=sort_work_modes(
                "remote" if loc.get("remote") else "on_site" for loc in locations
            ),
            employment_type=item.get("employmentType"),
            tags=[filters["tags"][i]["name"] for i in item.get("tagIndices", [])],
            extra={"slug": item["slug"]},
        )