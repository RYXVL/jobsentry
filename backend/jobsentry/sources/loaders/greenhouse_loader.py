"""Builds a source for every company in catalogs/greenhouse-sources.json.

File format:

    {
      "api_base":   "https://boards-api.greenhouse.io/v1/boards",
      "board_base": "https://boards.greenhouse.io",
      "sources": [
        {
          "name": "figma",             required. Lowercase; used in URLs and data/<name>/
          "company": "Figma",          required. Display name
          "board_token": "figma",      required. The <token> in <board_base>/<token>
          "homepage": "https://...",   optional. Defaults to the board page
          "country_hints": {           optional. Hints for this company only, e.g.
            "SF": "US"                 its own abbreviations; added to (and
          }                            overriding) catalogs/country-hints.json
        }
      ]
    }

To add a company: check that <api_base>/<token>/jobs returns jobs in a
browser, add an entry, restart the API, then refresh the new source.
"""

from __future__ import annotations

import re
from typing import Any

from ...core.exceptions import ConfigError
from ..registry import register
from ..strategies import GreenhouseSource
from ._catalog import (
    check_keys,
    get_country_hints,
    get_slug,
    get_str,
    get_url,
    read_catalog,
    read_country_hints,
)

CATALOG_FILE = "greenhouse-sources.json"

_TOP_KEYS = ("api_base", "board_base", "sources")
_SOURCE_REQUIRED = ("name", "company", "board_token")
_SOURCE_OPTIONAL = ("homepage", "country_hints")
_BOARD_TOKEN = re.compile(r"^[A-Za-z0-9_-]+$")

def load() -> list[type[GreenhouseSource]]:
    """Read the catalog and register one source per entry. Both the catalog
    and the shared hints are validated before anything is registered."""
    shared_hints = read_country_hints()
    classes = build_sources(*read_catalog(CATALOG_FILE), shared_hints=shared_hints)
    for cls in classes:
        register(cls)
    return classes

def build_sources(
    filename: str, data: dict[str, Any], shared_hints: dict[str, str] | None = None
) -> list[type[GreenhouseSource]]:
    """Validate a parsed catalog and build (but don't register) its classes.
    Each source's hints are `shared_hints` plus its own, its own winning."""
    check_keys(data, filename, _TOP_KEYS)
    api_base = get_url(data, "api_base", filename)
    board_base = get_url(data, "board_base", filename)
    entries = data["sources"]
    if not isinstance(entries, list):
        raise ConfigError(f"{filename}: 'sources' must be a list")

    classes: list[type[GreenhouseSource]] = []
    seen: dict[str, int] = {}
    for index, entry in enumerate(entries):
        where = f"{filename} sources[{index}]"
        check_keys(entry, where, _SOURCE_REQUIRED, _SOURCE_OPTIONAL)
        name = get_slug(entry, "name", where)
        where = f"{filename} source '{name}'"
        if name in seen:
            raise ConfigError(f"{where} appears twice (entries {seen[name]} and {index})")
        seen[name] = index

        board_token = get_str(entry, "board_token", where, _BOARD_TOKEN, "letters, digits, - or _")
        own_hints = get_country_hints(entry, "country_hints", where) if "country_hints" in entry else {}
        classes.append(_make_class(
            name=name,
            company=get_str(entry, "company", where),
            board_token=board_token,
            homepage=(
                get_url(entry, "homepage", where)
                if "homepage" in entry
                else f"{board_base}/{board_token}"
            ),
            country_hints={**(shared_hints or {}), **own_hints},
            api_base=api_base,
            board_base=board_base,
        ))
    return classes

def _make_class(**settings: Any) -> type[GreenhouseSource]:
    """Create a GreenhouseSource subclass, e.g. FigmaSource, with these settings."""
    class_name = "".join(part.capitalize() for part in re.split(r"[-_]", settings["name"])) + "Source"
    return type(class_name, (GreenhouseSource,), {
        "__module__": __name__,
        "__doc__": f"{settings['company']} jobs from Greenhouse board '{settings['board_token']}'.",
        **settings,
    })