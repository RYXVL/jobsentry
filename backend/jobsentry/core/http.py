"""Shared HTTP client: one place for headers, timeouts and retries.

Sources receive an HttpClient instead of calling `requests` directly, which
keeps behaviour consistent and lets tests swap in a fake client.

Politeness rules built in here:
  * transient failures (rate limits, server errors) are retried with backoff,
    honouring the server's Retry-After header;
  * a block (401/403) raises SourceBlockedError and is never retried or
    worked around.
"""

from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import SourceBlockedError, SourceError

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

#: Responses worth retrying: rate limiting and temporary server/gateway errors.
#: Client errors (400, 403, 404, ...) are excluded because retrying can't fix them.
RETRY_STATUS_CODES = (429, 500, 502, 503, 504)

#: Methods safe to retry. POST is included because every POST this app sends is
#: a read-only search query (e.g. Workday), so sending it twice has no side effects.
RETRY_METHODS = ("GET", "POST")

#: Responses meaning "we don't want automated access". Never retried or bypassed.
BLOCKED_STATUS_CODES = (401, 403)

class HttpClient:
    def __init__(
        self,
        timeout: float = 30.0,
        retries: int = 3,
        backoff: float = 1.0,
        headers: dict[str, str] | None = None,
        retry_status_codes: tuple[int, ...] = RETRY_STATUS_CODES,
    ):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({**DEFAULT_HEADERS, **(headers or {})})
        retry = Retry(
            total=retries,
            backoff_factor=backoff,
            status_forcelist=retry_status_codes,
            allowed_methods=RETRY_METHODS,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        """Send a request. Network and HTTP errors become SourceError;
        a block (401/403) becomes SourceBlockedError."""
        kwargs.setdefault("timeout", self.timeout)
        try:
            response = self.session.request(method, url, **kwargs)
        except requests.RequestException as e:
            raise SourceError(f"{method} {url} failed: {e}") from e

        if response.status_code in BLOCKED_STATUS_CODES:
            raise SourceBlockedError(
                f"{url} returned {response.status_code}: the site is refusing automated "
                "access. Check its terms or use an official API instead."
            )
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise SourceError(f"{method} {url} failed: {e}") from e
        return response

    def get_text(self, url: str, **kwargs: Any) -> str:
        return self.request("GET", url, **kwargs).text

    def get_json(self, url: str, **kwargs: Any) -> Any:
        return self.request("GET", url, **kwargs).json()

    def post_json(self, url: str, **kwargs: Any) -> Any:
        return self.request("POST", url, **kwargs).json()
