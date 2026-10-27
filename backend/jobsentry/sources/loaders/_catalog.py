"""Shared helpers for reading and validating catalog files.

Every problem raises ConfigError naming the file and the entry, so a typo
in a catalog fails loudly at startup instead of silently dropping a source.
Platform loaders (greenhouse_loader.py, later ashby_loader.py) use these.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ...core.exceptions import ConfigError

#: Folder holding the catalog files: backend/jobsentry/sources/catalogs/
CATALOG_DIR = Path(__file__).resolve().parent.parent / "catalogs"

#: Location text -> country code shared by every source (keep it alphabetical).
COUNTRY_HINTS_FILE = "country-hints.json"

#: Source names are used in URLs and as folder names under data/.
_SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_COUNTRY_CODE = re.compile(r"^[A-Z]{2}$")
_URL = re.compile(r"^https?://[^\s/]+(/\S*)?$")

def read_catalog(filename: str) -> tuple[str, dict[str, Any]]:
    """Read catalogs/<filename>. Returns (file name for messages, parsed object)."""
    path = CATALOG_DIR / filename
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"Catalog not found: {path}") from None
    except json.JSONDecodeError as e:
        raise ConfigError(
            f"{filename} is not valid JSON (line {e.lineno}, column {e.colno}): {e.msg}"
        ) from None
    if not isinstance(data, dict):
        raise ConfigError(f"{filename} must contain a JSON object")
    return filename, data

def read_country_hints(filename: str = COUNTRY_HINTS_FILE) -> dict[str, str]:
    """The shared hints every source uses, validated. Loaders merge each
    source's own `country_hints` on top, so a source can add or override."""
    name, data = read_catalog(filename)
    return parse_country_hints(data, name)

def check_keys(
    obj: Any, where: str, required: Iterable[str], optional: Iterable[str] = ()
) -> dict[str, Any]:
    """Require `obj` to be an object with every required key and nothing else."""
    if not isinstance(obj, dict):
        raise ConfigError(f"{where} must be an object")
    required, optional = list(required), list(optional)
    missing = [key for key in required if key not in obj]
    if missing:
        raise ConfigError(f"{where} is missing {', '.join(missing)}")
    unknown = sorted(set(obj) - set(required) - set(optional))
    if unknown:
        allowed = ", ".join(required + optional)
        raise ConfigError(f"{where} has unknown key(s) {', '.join(unknown)} (allowed: {allowed})")
    return obj

def get_str(
    obj: dict[str, Any], key: str, where: str,
    pattern: re.Pattern[str] | None = None, expected: str = "",
) -> str:
    """A non-empty string, optionally matching `pattern`."""
    value = obj[key]
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{where}: '{key}' must be a non-empty string")
    value = value.strip()
    if pattern and not pattern.match(value):
        raise ConfigError(f"{where}: '{key}' must be {expected or pattern.pattern}, got '{value}'")
    return value

def get_slug(obj: dict[str, Any], key: str, where: str) -> str:
    """A lowercase name: letters, digits, - and _ (safe in URLs and folder names)."""
    return get_str(obj, key, where, _SLUG, "lowercase letters, digits, - or _")

def get_url(obj: dict[str, Any], key: str, where: str) -> str:
    """An http(s) URL, without a trailing slash."""
    return get_str(obj, key, where, _URL, "an http(s) URL").rstrip("/")

def get_country_hints(obj: dict[str, Any], key: str, where: str) -> dict[str, str]:
    """A catalog entry's own {"location text": "ISO country code"}."""
    return parse_country_hints(obj[key], f"{where}: '{key}'")

def parse_country_hints(hints: Any, where: str) -> dict[str, str]:
    """Validate {"location text": "ISO country code"}; codes are upper-cased."""
    if not isinstance(hints, dict):
        raise ConfigError(f"{where} must be an object of location text -> country code")
    result: dict[str, str] = {}
    for text, code in hints.items():
        if not text.strip() or not isinstance(code, str) or not _COUNTRY_CODE.match(code.upper()):
            raise ConfigError(
                f"{where} entry '{text}' must map to a two-letter country code, got {code!r}"
            )
        result[text.strip()] = code.upper()
    return result