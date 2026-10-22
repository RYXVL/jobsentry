"""Strategy for Next.js sites (Pages Router).

These pages embed their data as JSON in <script id="__NEXT_DATA__">, so a
subclass only needs to know which URLs to load and how to map the JSON.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ...core.exceptions import SourceError
from ..base import JobSource

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>', re.S
)

def extract_next_data(html: str) -> dict[str, Any]:
    """Return the parsed __NEXT_DATA__ JSON from a page's HTML."""
    match = _NEXT_DATA_RE.search(html)
    if not match:
        raise SourceError("No __NEXT_DATA__ script found; the site may have changed.")
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        raise SourceError(f"__NEXT_DATA__ is not valid JSON: {e}") from e

class NextDataSource(JobSource):
    """Base for sources whose pages carry their data in __NEXT_DATA__.
    Subclasses still implement fetch_jobs() and fetch_job_details()."""

    strategy = "next_data"

    def get_page_props(self, url: str) -> dict[str, Any]:
        """Fetch `url` and return props.pageProps from its __NEXT_DATA__."""
        data = extract_next_data(self.http.get_text(url))
        try:
            return data["props"]["pageProps"]
        except KeyError as e:
            raise SourceError(f"Unexpected __NEXT_DATA__ shape at {url}: missing {e}") from e
