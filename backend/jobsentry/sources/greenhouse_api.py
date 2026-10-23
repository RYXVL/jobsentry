"""Greenhouse's public Job Board API (https://developers.greenhouse.io/job-board.html).

Many companies host their job board on Greenhouse, which publishes it as a
read-only JSON API intended for public use:

    GET https://boards-api.greenhouse.io/v1/boards/<board token>/jobs

For now this module adds posting dates to sources whose own site leaves them
out (see companies/stripe.py). The planned Greenhouse strategy
(strategies/greenhouse.py) can build on the same helpers.

Only `first_published` is used. Greenhouse's `updated_at` changes whenever
anything in a job's record changes, including bulk edits across a whole
board, so it doesn't reliably mean the posting itself changed.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from ..core.exceptions import SourceError
from ..core.http import HttpClient
from ..core.models import Job

BOARDS_API = "https://boards-api.greenhouse.io/v1/boards"

def board_jobs_url(board_token: str) -> str:
    """URL listing every job on a board, e.g. board_jobs_url("stripe")."""
    return f"{BOARDS_API}/{board_token}/jobs"

def fetch_posted_dates(http: HttpClient, board_token: str) -> dict[str, str | None]:
    """Return {job id: first published time (ISO 8601) or None} for every job
    on the board, in one request.

    Raises SourceError (or SourceBlockedError) if the request fails or the
    response isn't the expected shape."""
    url = board_jobs_url(board_token)
    try:
        data: Any = http.get_json(url)
    except ValueError as e:  # body wasn't valid JSON
        raise SourceError(f"{url} did not return valid JSON: {e}") from e

    items = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise SourceError(f"Unexpected Greenhouse response at {url}: no 'jobs' list")

    return {
        str(item["id"]): item.get("first_published")
        for item in items
        if isinstance(item, dict) and "id" in item
    }

def apply_posted_dates(jobs: list[Job], dates: dict[str, str | None]) -> list[Job]:
    """Return copies of `jobs` with posted_at filled in, matched by job ID.
    Jobs missing from `dates` are returned unchanged."""
    return [
        replace(job, posted_at=dates[job.id]) if job.id in dates else job
        for job in jobs
    ]