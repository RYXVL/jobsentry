"""Add, edit and delete catalog entries (and their logos) from the API.

Every change is validated by the same loader code that runs at startup,
before anything is written, so the website can't save an entry the
catalogs would later reject. Writes are atomic (temp file, then swap), and
the registry is reloaded afterwards, so changes apply at once; if the reload
fails, the previous files are restored.

Logos are saved as <JOBSENTRY_LOGOS_DIR>/<name>.png, which is where the
frontend looks for them by the source's name.

Changes are refused while "Fetch all jobs" is running or while the source
being changed is refreshing, and when JOBSENTRY_ALLOW_CATALOG_EDITS is off.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from ..config import Settings
from ..core.exceptions import (
    ConfigError,
    JobsentryError,
    RefreshInProgressError,
    SourceBlockedError,
    SourceError,
    SourceNotFoundError,
)
from ..core.http import HttpClient
from ..sources import registry
from ..sources.loaders import ashby_loader, greenhouse_loader, lever_loader, smartrecruiters_loader
from ..sources.loaders._catalog import CATALOG_DIR, read_catalog
from ..storage import JsonJobStore
from . import today_jobs
from .job_service import _lock_for
from .refresh_runner import runner

class CatalogEntryError(JobsentryError):
    """An entry from the website isn't valid (shown as a 422)."""

class CatalogEditsDisabledError(JobsentryError):
    """JOBSENTRY_ALLOW_CATALOG_EDITS is off (shown as a 403)."""

# Platforms --------------------------------------------------------------------

def _count_jobs_key(data: Any) -> int:
    jobs = data["jobs"]
    if not isinstance(jobs, list):
        raise TypeError("'jobs' isn't a list")
    return len(jobs)

def _count_list(data: Any) -> int:
    if not isinstance(data, list):
        raise TypeError("not a list")
    return len(data)

def _count_total_found(data: Any) -> int:
    total = data["totalFound"]
    if not isinstance(total, int):
        raise TypeError("'totalFound' isn't a number")
    return total

@dataclass(frozen=True)
class Platform:
    """A job board platform the website can add sources for."""

    key: str                     # strategy name, e.g. "greenhouse"
    label: str                   # shown in the form, e.g. "Greenhouse"
    loader: ModuleType           # its loader: CATALOG_FILE, build_sources(), allowed keys
    #: (source instance, board name) -> (URL, query params) of the request a
    #: refresh makes, so a check hits exactly what a refresh hits.
    check_request: Callable[[Any, str], tuple[str, dict[str, Any] | None]]
    count_jobs: Callable[[Any], int]  # jobs in that response
    #: True where a wrong board name answers "0 jobs" instead of 404.
    empty_means_missing: bool = False
    has_region: bool = False     # Lever: global or EU instance

    @property
    def catalog_file(self) -> str:
        return self.loader.CATALOG_FILE

    @property
    def allowed_keys(self) -> frozenset[str]:
        return frozenset(self.loader._SOURCE_REQUIRED) | frozenset(self.loader._SOURCE_OPTIONAL)

#: In the order the form lists them.
PLATFORMS: dict[str, Platform] = {
    platform.key: platform
    for platform in (
        Platform("ashby", "Ashby", ashby_loader,
                 lambda source, board: (source.board_api_url(board), None), _count_jobs_key),
        Platform("greenhouse", "Greenhouse", greenhouse_loader,
                 lambda source, board: (source.jobs_api_url(board), None), _count_jobs_key),
        Platform("lever", "Lever", lever_loader,
                 lambda source, board: (source.board_api_url(board), {"mode": "json"}), _count_list,
                 has_region=True),
        Platform("smartrecruiters", "SmartRecruiters", smartrecruiters_loader,
                 lambda source, board: (source.postings_api_url(board), {"limit": 1}),
                 _count_total_found, empty_means_missing=True),
    )
}

#: Entry keys the website edits; any other key in an entry is kept as it is.
FORM_KEYS = frozenset({"name", "company", "board_name", "homepage", "region"})

@dataclass(frozen=True)
class EntryForm:
    """What the website's form sends."""

    platform: str
    name: str
    company: str
    board_names: Sequence[str]
    homepage: str | None = None
    region: str | None = None   # Lever only: "global" or "eu"

@dataclass(frozen=True)
class BoardCheck:
    """The result of checking one board name."""

    board_name: str
    ok: bool
    status: int | None       # HTTP status, when known
    job_count: int | None
    message: str
    url: str

_edit_lock = threading.Lock()   # one change at a time
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
LOGO_MAX_BYTES = 2_000_000
_SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_STATUS = re.compile(r"\b(\d{3}) (?:Client|Server) Error|returned (\d{3})")

def platforms() -> list[Platform]:
    return list(PLATFORMS.values())

# Reading ----------------------------------------------------------------------

def get_entry(name: str) -> tuple[Platform, dict[str, Any]]:
    """A source's platform and its entry, exactly as in its catalog file."""
    for platform in PLATFORMS.values():
        _, data = read_catalog(platform.catalog_file)
        for entry in data.get("sources") or []:
            if isinstance(entry, dict) and entry.get("name") == name:
                return platform, dict(entry)
    raise SourceNotFoundError(f"No source named '{name}' in any catalog")

# Checking ---------------------------------------------------------------------

def check_boards(
    platform_key: str, board_names: Sequence[str], region: str | None, settings: Settings
) -> list[BoardCheck]:
    """Request each board the way a refresh would (one request per board)
    and report what came back. Board names are validated first, like a save."""
    platform = _platform(platform_key)
    form = EntryForm(platform.key, "board-check", "Board check", board_names, None, region)
    source_cls = _build_one(platform, _entry_dict(platform, form, {}))
    source = source_cls(http=HttpClient(
        timeout=settings.http_timeout,
        retries=settings.http_retries,
        headers={"User-Agent": settings.user_agent},
    ))
    return [_check_one(platform, source, board) for board in source_cls.board_names]

def _check_one(platform: Platform, source: Any, board_name: str) -> BoardCheck:
    url, params = platform.check_request(source, board_name)
    try:
        data = source.http.get_json(url, params=params)
    except SourceBlockedError as e:
        return BoardCheck(board_name, False, _status_of(e), None,
                          "Blocked: the job board refused automated access.", url)
    except SourceError as e:
        status = _status_of(e)
        if status == 404:
            what = "board name and region" if platform.has_region else "board name"
            message = f"Not found (404). Check the {what}."
        else:
            message = f"Request failed{f' ({status})' if status else ''}: {e}"
        return BoardCheck(board_name, False, status, None, message, url)
    except ValueError:
        return BoardCheck(board_name, False, 200, None,
                          "The response wasn't JSON. Is this the right platform?", url)

    try:
        count = platform.count_jobs(data)
    except (KeyError, TypeError, IndexError):
        return BoardCheck(board_name, False, 200, None,
                          f"Unexpected response: this doesn't look like a {platform.label} board.", url)

    if count == 0 and platform.empty_means_missing:
        return BoardCheck(board_name, False, 200, 0,
                          f"0 jobs found. {platform.label} answers a wrong board name this way, "
                          "so check it (names are case-sensitive).", url)
    if count == 0:
        return BoardCheck(board_name, True, 200, 0, "OK, but no open jobs right now.", url)
    return BoardCheck(board_name, True, 200, count,
                      f"OK, {count} {'job' if count == 1 else 'jobs'} found.", url)

# Changing ---------------------------------------------------------------------

def add_source(form: EntryForm, settings: Settings) -> tuple[Platform, dict[str, Any]]:
    """Add a new entry to its platform's catalog."""
    with _edit_lock:
        _guard(settings)
        platform = _platform(form.platform)
        _ensure_name_free(form.name.strip())
        filename, data = read_catalog(platform.catalog_file)
        entry = _entry_dict(platform, form, {})
        data["sources"] = [*_entries(data), entry]
        _validate(platform, filename, data)
        _commit({platform.key: (platform, data)})
        return platform, entry

def update_source(name: str, form: EntryForm, settings: Settings) -> tuple[Platform, dict[str, Any]]:
    """Replace a source's form fields, keeping its other keys (e.g.
    country_hints). A new platform moves it to that platform's catalog,
    dropping keys the new platform doesn't allow. The name can't change."""
    with _edit_lock:
        _guard(settings, name)
        old_platform, old_entry = get_entry(name)
        new_platform = _platform(form.platform)
        kept = {
            key: value for key, value in old_entry.items()
            if key not in FORM_KEYS and key in new_platform.allowed_keys
        }
        entry = _entry_dict(new_platform, EntryForm(**{**vars(form), "name": name}), kept)

        old_file, old_data = read_catalog(old_platform.catalog_file)
        if new_platform.key == old_platform.key:
            old_data["sources"] = [entry if _is(e, name) else e for e in _entries(old_data)]
            _validate(old_platform, old_file, old_data)
            _commit({old_platform.key: (old_platform, old_data)})
        else:
            new_file, new_data = read_catalog(new_platform.catalog_file)
            old_data["sources"] = [e for e in _entries(old_data) if not _is(e, name)]
            new_data["sources"] = [*_entries(new_data), entry]
            _validate(old_platform, old_file, old_data)
            _validate(new_platform, new_file, new_data)
            _commit({
                old_platform.key: (old_platform, old_data),
                new_platform.key: (new_platform, new_data),
            })
        return new_platform, entry

def delete_source(name: str, settings: Settings) -> None:
    """Delete a source completely: its catalog entry, its saved jobs and
    details, its part of todays-jobs.json, and its logo. Can't be undone."""
    with _edit_lock:
        _guard(settings, name)
        platform, _ = get_entry(name)
        filename, data = read_catalog(platform.catalog_file)
        data["sources"] = [e for e in _entries(data) if not _is(e, name)]
        _validate(platform, filename, data)
        _commit({platform.key: (platform, data)})

        store = JsonJobStore(settings.data_dir)
        store.delete_source(name)
        today_jobs.remove(store, name)
        _remove_logo_files(name, settings)

def save_logo(name: str, content: bytes, settings: Settings) -> Path:
    """Save a PNG as <logos dir>/<name>.png (replacing any .jpg for the
    same name, so there's only one logo)."""
    with _edit_lock:
        _require_edits(settings)
        get_entry(name)  # the source must exist; also makes `name` a safe file name
        if not content:
            raise CatalogEntryError("The logo file is empty.")
        if len(content) > LOGO_MAX_BYTES:
            raise CatalogEntryError(f"The logo must be at most {LOGO_MAX_BYTES // 1_000_000} MB.")
        if not content.startswith(_PNG_SIGNATURE):
            raise CatalogEntryError("The logo must be a PNG image.")
        path = _logo_path(name, settings, "png")
        _write_bytes(path, content)
        _logo_path(name, settings, "jpg").unlink(missing_ok=True)
        return path

def delete_logo(name: str, settings: Settings) -> bool:
    """Remove a source's logo (.png and any .jpg). Returns whether one existed."""
    with _edit_lock:
        _require_edits(settings)
        get_entry(name)
        return _remove_logo_files(name, settings)

# Helpers ----------------------------------------------------------------------

def _platform(key: str) -> Platform:
    try:
        return PLATFORMS[key]
    except KeyError:
        raise CatalogEntryError(
            f"Unknown platform '{key}'. Choose one of: {', '.join(PLATFORMS)}"
        ) from None

def _require_edits(settings: Settings) -> None:
    if not settings.allow_catalog_edits:
        raise CatalogEditsDisabledError(
            "Editing sources is turned off (JOBSENTRY_ALLOW_CATALOG_EDITS=false)."
        )

def _guard(settings: Settings, name: str | None = None) -> None:
    """Refuse a change while edits are off, while fetching every source, or
    while the source being changed is refreshing."""
    _require_edits(settings)
    if runner.is_running():
        raise RefreshInProgressError(
            "Can't change sources while all jobs are being fetched; try again when it finishes"
        )
    if name is not None and _lock_for(name).locked():
        raise RefreshInProgressError(f"'{name}' is being refreshed; try again shortly")

def _entries(data: dict[str, Any]) -> list[Any]:
    sources = data.get("sources")
    return list(sources) if isinstance(sources, list) else []

def _is(entry: Any, name: str) -> bool:
    return isinstance(entry, dict) and entry.get("name") == name

def _ensure_name_free(name: str) -> None:
    """Source names must be unique across every catalog."""
    for platform in PLATFORMS.values():
        _, data = read_catalog(platform.catalog_file)
        if any(_is(entry, name) for entry in _entries(data)):
            raise CatalogEntryError(
                f"A source named '{name}' already exists (in {platform.catalog_file})."
            )

def _entry_dict(platform: Platform, form: EntryForm, kept: dict[str, Any]) -> dict[str, Any]:
    """A catalog entry from the form: form keys first, then the kept keys.
    One board name is written as a string, several as a list."""
    names = [str(n).strip() for n in form.board_names if str(n).strip()]
    entry: dict[str, Any] = {
        "name": form.name.strip(),
        "company": form.company.strip(),
        "board_name": names[0] if len(names) == 1 else names,
    }
    if form.homepage and form.homepage.strip():
        entry["homepage"] = form.homepage.strip()
    if platform.has_region and form.region and form.region != "global":
        entry["region"] = form.region
    return {**entry, **kept}

def _build_one(platform: Platform, entry: dict[str, Any]) -> type:
    """Validate a single entry with the platform's loader, and build its class."""
    filename, data = read_catalog(platform.catalog_file)
    try:
        return platform.loader.build_sources(filename, {**data, "sources": [entry]}, shared_hints={})[0]
    except ConfigError as e:
        raise CatalogEntryError(str(e)) from None

def _validate(platform: Platform, filename: str, data: dict[str, Any]) -> None:
    """Run the platform's loader over the whole changed catalog."""
    try:
        platform.loader.build_sources(filename, data, shared_hints={})
    except ConfigError as e:
        raise CatalogEntryError(str(e)) from None

def _commit(changes: dict[str, tuple[Platform, dict[str, Any]]]) -> None:
    """Write the changed catalogs, then reload the registry. If the reload
    fails, put the previous files back and reload them."""
    backups: dict[Path, str] = {}
    for platform, data in changes.values():
        path = CATALOG_DIR / platform.catalog_file
        backups[path] = path.read_text(encoding="utf-8")
        _write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    try:
        registry.reload()
    except Exception:
        for path, text in backups.items():
            _write_text(path, text)
        registry.reload()
        raise

def _logo_path(name: str, settings: Settings, extension: str) -> Path:
    if not _SLUG.match(name):  # never build a path from anything but a source name
        raise CatalogEntryError(f"'{name}' isn't a valid source name")
    return Path(settings.logos_dir) / f"{name}.{extension}"

def _remove_logo_files(name: str, settings: Settings) -> bool:
    removed = False
    for extension in ("png", "jpg"):
        path = _logo_path(name, settings, extension)
        if path.exists():
            path.unlink()
            removed = True
    return removed

def _status_of(error: Exception) -> int | None:
    """The HTTP status in an HttpClient error message, if there is one."""
    match = _STATUS.search(str(error))
    return int(match.group(1) or match.group(2)) if match else None

def _write_text(path: Path, text: str) -> None:
    _write_bytes(path, text.encode("utf-8"))

def _write_bytes(path: Path, content: bytes) -> None:
    """Write via a temp file so a crash never leaves a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise