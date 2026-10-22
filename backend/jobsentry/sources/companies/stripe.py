"""Stripe careers (https://stripe.com/careers). Next.js site backed by Greenhouse.

  /careers/search               pageProps.jobIndexData: every job. Teams,
                                locations and tags are stored as indexes into
                                lookup lists in jobIndexData.filters.
  /careers/listing/<slug>/<id>  pageProps.listing: one job with description
                                (Markdown), salary and posting date.
"""

from __future__ import annotations

from typing import Any

from ...core.exceptions import SourceError
from ...core.models import Job, JobDetails, Salary
from ..registry import register
from ..strategies import NextDataSource

BASE_URL = "https://stripe.com"

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
        return [self._to_job(item, filters) for item in listings]

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
            posted_at=listing.get("postedAt"),
            salary=salary,
            apply_url=f"{BASE_URL}/careers/apply/{slug}/{job.id}",
        )

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
            remote=any(loc.get("remote") for loc in locations),
            employment_type=item.get("employmentType"),
            tags=[filters["tags"][i]["name"] for i in item.get("tagIndices", [])],
            extra={"slug": item["slug"]},
        )
