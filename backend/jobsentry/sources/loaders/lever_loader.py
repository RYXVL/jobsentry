"""Builds a source for every company in catalogs/lever-sources.json.

File format:

    {
      "api_base":      "https://api.lever.co/v0/postings",
      "board_base":    "https://jobs.lever.co",
      "eu_api_base":   "https://api.eu.lever.co/v0/postings",   optional; needed if
      "eu_board_base": "https://jobs.eu.lever.co",               any source is "eu"
      "sources": [
        {
          "name": "spotify",           required. Lowercase; used in URLs and data/<name>/
          "company": "Spotify",        required. Display name
          "board_name": "spotify",     required. The <name> in <board_base>/<name>, or
                                       a list of names merged into one source
          "region": "global",          optional. "global" (default) or "eu" for
                                       companies on Lever's EU instance
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

To add a company: check that <api_base>/<name>?mode=json returns postings
in a browser (try the EU base if the global one gives 404), add an entry,
restart the API, then refresh it.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

from ...core.exceptions import ConfigError
from ..registry import register
from ..strategies import LeverSource
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

CATALOG_FILE = "lever-sources.json"

_TOP_REQUIRED = ("api_base", "board_base", "sources")
_TOP_OPTIONAL = ("eu_api_base", "eu_board_base")
_SOURCE_REQUIRED = ("name", "company", "board_name")
_SOURCE_OPTIONAL = ("region", "homepage", "country_hints", "state_codes")
_REGIONS = ("global", "eu")
#: Lever board names are the last part of the board URL, e.g. "spotify".
_BOARD_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")

def load() -> list[type[LeverSource]]:
    """Read the catalog and register one source per entry. Both the catalog
    and the shared hints are validated before anything is registered."""
    shared_hints = read_country_hints()
    classes = build_sources(*read_catalog(CATALOG_FILE), shared_hints=shared_hints)
    for cls in classes:
        register(cls)
    return classes

def build_sources(
    filename: str, data: dict[str, Any], shared_hints: dict[str, str] | None = None
) -> list[type[LeverSource]]:
    """Validate a parsed catalog and build (but don't register) its classes.
    Each source's hints are `shared_hints` plus its own, its own winning."""
    check_keys(data, filename, _TOP_REQUIRED, _TOP_OPTIONAL)
    bases = {"global": (get_url(data, "api_base", filename), get_url(data, "board_base", filename))}
    if "eu_api_base" in data or "eu_board_base" in data:
        check_keys(
            {k: data[k] for k in _TOP_OPTIONAL if k in data},
            f"{filename} (EU URLs)", _TOP_OPTIONAL,
        )
        bases["eu"] = (get_url(data, "eu_api_base", filename), get_url(data, "eu_board_base", filename))

    entries = data["sources"]
    if not isinstance(entries, list):
        raise ConfigError(f"{filename}: 'sources' must be a list")

    classes: list[type[LeverSource]] = []
    seen: dict[str, int] = {}
    for index, entry in enumerate(entries):
        where = f"{filename} sources[{index}]"
        check_keys(entry, where, _SOURCE_REQUIRED, _SOURCE_OPTIONAL)
        name = get_slug(entry, "name", where)
        where = f"{filename} source '{name}'"
        if name in seen:
            raise ConfigError(f"{where} appears twice (entries {seen[name]} and {index})")
        seen[name] = index

        region = entry.get("region", "global")
        if region not in _REGIONS:
            raise ConfigError(f"{where}: 'region' must be one of {', '.join(_REGIONS)}, got {region!r}")
        if region not in bases:
            raise ConfigError(f"{where} is on the EU region, but {filename} has no EU URLs")
        api_base, board_base = bases[region]

        board_names = get_token_list(
            entry, "board_name", where, _BOARD_NAME, "letters, digits, ., - or _"
        )
        own_hints = get_country_hints(entry, "country_hints", where) if "country_hints" in entry else {}
        company = get_str(entry, "company", where)
        classes.append(make_source_class(
            LeverSource,
            f"{company} jobs from Lever board(s): {', '.join(board_names)} ({region}).",
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