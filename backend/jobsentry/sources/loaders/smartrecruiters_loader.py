"""Builds a source for every company in catalogs/smartrecruiters-sources.json.

File format:

    {
      "api_base":   "https://api.smartrecruiters.com/v1/companies",
      "board_base": "https://jobs.smartrecruiters.com",
      "max_pages": 100,                 optional, default 100. Most list pages
                                        (100 postings each) per board per refresh
      "sources": [
        {
          "name": "wise",               required. Lowercase; used in URLs and data/<name>/
          "company": "Wise",            required. Display name
          "board_name": "Wise",         required. The company identifier, the <name> in
                                        <board_base>/<name>; case-sensitive. Or a list
          "homepage": "https://...",    optional. Defaults to the first board's page
          "max_pages": 200,             optional. Overrides the default above
          "country_hints": {...},       optional. As for the other platforms
          "state_codes": true           optional, default false
        }
      ]
    }

To add a company: open <api_base>/<name>/postings?limit=1 in a browser and
check totalFound is above 0. SmartRecruiters answers a wrong name with 0
postings rather than an error, so this check is the only way to catch a typo
before the first refresh.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

from ...core.exceptions import ConfigError
from ..registry import register
from ..strategies import SmartRecruitersSource
from ._catalog import (
    check_keys,
    get_bool,
    get_country_hints,
    get_int,
    get_slug,
    get_str,
    get_token_list,
    get_url,
    make_source_class,
    read_catalog,
    read_country_hints,
)

CATALOG_FILE = "smartrecruiters-sources.json"

_TOP_REQUIRED = ("api_base", "board_base", "sources")
_TOP_OPTIONAL = ("max_pages",)
_SOURCE_REQUIRED = ("name", "company", "board_name")
_SOURCE_OPTIONAL = ("homepage", "max_pages", "country_hints", "state_codes")
#: SmartRecruiters company identifiers, e.g. "Wise", "BoschGroup".
_BOARD_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")

#: Default and allowed range for max_pages (pages of 100 postings).
DEFAULT_MAX_PAGES = 100
MAX_PAGES_LIMIT = 1000

def load() -> list[type[SmartRecruitersSource]]:
    """Read the catalog and register one source per entry. Both the catalog
    and the shared hints are validated before anything is registered."""
    shared_hints = read_country_hints()
    classes = build_sources(*read_catalog(CATALOG_FILE), shared_hints=shared_hints)
    for cls in classes:
        register(cls)
    return classes

def build_sources(
    filename: str, data: dict[str, Any], shared_hints: dict[str, str] | None = None
) -> list[type[SmartRecruitersSource]]:
    """Validate a parsed catalog and build (but don't register) its classes.
    Each source's hints are `shared_hints` plus its own, its own winning."""
    check_keys(data, filename, _TOP_REQUIRED, _TOP_OPTIONAL)
    api_base = get_url(data, "api_base", filename)
    board_base = get_url(data, "board_base", filename)
    default_max_pages = (
        get_int(data, "max_pages", filename, 1, MAX_PAGES_LIMIT)
        if "max_pages" in data
        else DEFAULT_MAX_PAGES
    )
    entries = data["sources"]
    if not isinstance(entries, list):
        raise ConfigError(f"{filename}: 'sources' must be a list")

    classes: list[type[SmartRecruitersSource]] = []
    seen: dict[str, int] = {}
    for index, entry in enumerate(entries):
        where = f"{filename} sources[{index}]"
        check_keys(entry, where, _SOURCE_REQUIRED, _SOURCE_OPTIONAL)
        name = get_slug(entry, "name", where)
        where = f"{filename} source '{name}'"
        if name in seen:
            raise ConfigError(f"{where} appears twice (entries {seen[name]} and {index})")
        seen[name] = index

        board_names = get_token_list(
            entry, "board_name", where, _BOARD_NAME, "letters, digits, ., - or _"
        )
        own_hints = get_country_hints(entry, "country_hints", where) if "country_hints" in entry else {}
        company = get_str(entry, "company", where)
        classes.append(make_source_class(
            SmartRecruitersSource,
            f"{company} jobs from SmartRecruiters board(s): {', '.join(board_names)}.",
            name=name,
            company=company,
            board_names=board_names,
            homepage=(
                get_url(entry, "homepage", where)
                if "homepage" in entry
                else f"{board_base}/{quote(board_names[0])}"
            ),
            max_pages=(
                get_int(entry, "max_pages", where, 1, MAX_PAGES_LIMIT)
                if "max_pages" in entry
                else default_max_pages
            ),
            country_hints={**(shared_hints or {}), **own_hints},
            state_codes=get_bool(entry, "state_codes", where),
            api_base=api_base,
            board_base=board_base,
        ))
    return classes