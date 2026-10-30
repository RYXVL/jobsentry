"""Builds a source for every company in catalogs/ashby-sources.json.

File format:

    {
      "api_base":   "https://api.ashbyhq.com/posting-api/job-board",
      "board_base": "https://jobs.ashbyhq.com",
      "sources": [
        {
          "name": "supabase",          required. Lowercase; used in URLs and data/<name>/
          "company": "Supabase",       required. Display name
          "board_name": "supabase",    required. The <name> in <board_base>/<name>,
                                       or a list of names for a company with several
                                       boards, merged into one source
          "homepage": "https://...",   optional. Defaults to the first board's page
          "country_hints": {           optional. Hints for this company only; added to
            "SF": "US"                 (and overriding) catalogs/country-hints.json
          },
          "state_codes": true          optional, default false. Read "City, ST" as a
                                       US state or Canadian province when nothing else
                                       matched
        }
      ]
    }

To add a company: check that <api_base>/<name> returns jobs in a browser
(for every name), add an entry, restart the API, then refresh it.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

from ...core.exceptions import ConfigError
from ..registry import register
from ..strategies import AshbySource
from ._catalog import (
    check_keys,
    get_bool,
    get_country_hints,
    get_slug,
    get_str,
    get_token_list,
    get_url,
    make_source_class,
    read_catalog,
    read_country_hints,
)

CATALOG_FILE = "ashby-sources.json"

_TOP_KEYS = ("api_base", "board_base", "sources")
_SOURCE_REQUIRED = ("name", "company", "board_name")
_SOURCE_OPTIONAL = ("homepage", "country_hints", "state_codes")
#: Ashby board names are the last part of the board URL, e.g. "supabase" or "Ramp".
_BOARD_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")

def load() -> list[type[AshbySource]]:
    """Read the catalog and register one source per entry. Both the catalog
    and the shared hints are validated before anything is registered."""
    shared_hints = read_country_hints()
    classes = build_sources(*read_catalog(CATALOG_FILE), shared_hints=shared_hints)
    for cls in classes:
        register(cls)
    return classes

def build_sources(
    filename: str, data: dict[str, Any], shared_hints: dict[str, str] | None = None
) -> list[type[AshbySource]]:
    """Validate a parsed catalog and build (but don't register) its classes.
    Each source's hints are `shared_hints` plus its own, its own winning."""
    check_keys(data, filename, _TOP_KEYS)
    api_base = get_url(data, "api_base", filename)
    board_base = get_url(data, "board_base", filename)
    entries = data["sources"]
    if not isinstance(entries, list):
        raise ConfigError(f"{filename}: 'sources' must be a list")

    classes: list[type[AshbySource]] = []
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
            AshbySource,
            f"{company} jobs from Ashby board(s): {', '.join(board_names)}.",
            name=name,
            company=company,
            board_names=board_names,
            homepage=(
                get_url(entry, "homepage", where)
                if "homepage" in entry
                else f"{board_base}/{quote(board_names[0])}"
            ),
            country_hints={**(shared_hints or {}), **own_hints},
            state_codes=get_bool(entry, "state_codes", where),
            api_base=api_base,
            board_base=board_base,
        ))
    return classes