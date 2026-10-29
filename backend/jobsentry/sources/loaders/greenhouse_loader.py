"""Builds a source for every company in catalogs/greenhouse-sources.json.

File format:

    {
      "api_base":   "https://boards-api.greenhouse.io/v1/boards",
      "board_base": "https://boards.greenhouse.io",
      "sources": [
        {
          "name": "figma",             required. Lowercase; used in URLs and data/<name>/
          "company": "Figma",          required. Display name
          "board_token": "figma",      required. The <token> in <board_base>/<token>,
                                       or a list of tokens for a company with several
                                       boards (e.g. one per region), merged into one source
          "homepage": "https://...",   optional. Defaults to the first board's page
          "country_hints": {           optional. Hints for this company only, e.g.
            "SF": "US"                 its own abbreviations; added to (and
          },                           overriding) catalogs/country-hints.json
          "state_codes": true          optional, default false. Read "City, ST" as a
                                       US state or Canadian province when nothing else
                                       matched; for boards that write locations that way
        }
      ]
    }

To add a company: check that <api_base>/<token>/jobs returns jobs in a
browser (for every token), add an entry, restart the API, then refresh it.
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
_SOURCE_OPTIONAL = ("homepage", "country_hints", "state_codes")
_BOARD_TOKEN = re.compile(r"^[A-Za-z0-9_-]+$")
_BOARD_TOKEN_EXPECTED = "letters, digits, - or _"

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

        board_tokens = _get_board_tokens(entry, where)
        own_hints = get_country_hints(entry, "country_hints", where) if "country_hints" in entry else {}
        state_codes = entry.get("state_codes", False)
        if not isinstance(state_codes, bool):
            raise ConfigError(f"{where}: 'state_codes' must be true or false, got {state_codes!r}")

        classes.append(_make_class(
            name=name,
            company=get_str(entry, "company", where),
            board_tokens=board_tokens,
            homepage=(
                get_url(entry, "homepage", where)
                if "homepage" in entry
                else f"{board_base}/{board_tokens[0]}"
            ),
            country_hints={**(shared_hints or {}), **own_hints},
            state_codes=state_codes,
            api_base=api_base,
            board_base=board_base,
        ))
    return classes

def _get_board_tokens(entry: dict[str, Any], where: str) -> tuple[str, ...]:
    """An entry's boards from "board_token": one token as a string, or
    several as a non-empty list. Tokens must be valid and unique."""
    value = entry["board_token"]
    tokens = [value] if isinstance(value, str) else value
    if not isinstance(tokens, list) or not tokens:
        raise ConfigError(f"{where}: 'board_token' must be a token or a non-empty list of tokens")

    result: list[str] = []
    for token in tokens:
        if not isinstance(token, str) or not _BOARD_TOKEN.match(token.strip()):
            raise ConfigError(
                f"{where}: 'board_token' must be {_BOARD_TOKEN_EXPECTED}, got {token!r}"
            )
        token = token.strip()
        if token in result:
            raise ConfigError(f"{where}: 'board_token' lists '{token}' twice")
        result.append(token)
    return tuple(result)

def _make_class(**settings: Any) -> type[GreenhouseSource]:
    """Create a GreenhouseSource subclass, e.g. FigmaSource, with these settings."""
    class_name = "".join(part.capitalize() for part in re.split(r"[-_]", settings["name"])) + "Source"
    boards = ", ".join(settings["board_tokens"])
    return type(class_name, (GreenhouseSource,), {
        "__module__": __name__,
        "__doc__": f"{settings['company']} jobs from Greenhouse board(s): {boards}.",
        **settings,
    })