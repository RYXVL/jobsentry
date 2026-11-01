"""Small helpers shared by the platform strategies.

Modules starting with "_" are internal to this package; strategies import
from here rather than from each other.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ...core.exceptions import SourceError
from ...core.http import HttpClient

def get_json(http: HttpClient, url: str, **kwargs: Any) -> Any:
    """GET JSON, turning an unreadable body into SourceError. Network and
    HTTP errors (including blocks) already raise from HttpClient itself."""
    try:
        return http.get_json(url, **kwargs)
    except ValueError as e:  # body wasn't valid JSON
        raise SourceError(f"{url} did not return valid JSON: {e}") from e

def unique_texts(values: Iterable[Any]) -> list[str]:
    """Non-empty values as stripped text, without duplicates, in order."""
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result