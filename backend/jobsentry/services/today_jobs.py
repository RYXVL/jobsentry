"""data/todays-jobs.json: the jobs posted today, ready for /today.

Every time a source's jobs are saved (fetch-all, a single refresh, or a
first fetch), that source's section of this file is rewritten. /today
(GET /jobs?posted_on=<today>) then reads one small file instead of every
company's jobs.json.

"Today" is the local date in Settings.timezone, the computer running Job
Sentry. The file:

    {"date": "2026-11-01", "timezone": "Asia/Kolkata", "updated_at": "...",
     "sources": {"stripe": {"company": "Stripe", "fetched_at": "...", "jobs": [...]}}}

It only counts for the date and time zone it was built for. On a new day,
the first save rebuilds it from every saved source; until then, and for any
other time zone, callers fall back to reading the jobs.json files.
"""

from __future__ import annotations

import logging
import threading
from datetime import date, datetime, timezone as dt_timezone
from typing import Any
from zoneinfo import ZoneInfo

from ..core.models import JobSnapshot
from ..sources import available_sources
from ..storage import JobStore
from .queries import JobQuery

log = logging.getLogger(__name__)

# Several refresh threads may save at once; they take turns updating the file.
_lock = threading.Lock()

def local_today(timezone: str) -> date:
    """Today's date in `timezone` (an IANA name)."""
    return datetime.now(ZoneInfo(timezone)).date()

def record(store: JobStore, snapshot: JobSnapshot, company: str, timezone: str) -> None:
    """Update `snapshot`'s section of the file. If the file is missing,
    unreadable, or for another day or time zone, rebuild it first from every
    saved source, so it always covers all of them."""
    today = local_today(timezone)
    with _lock:
        data = _load(store)
        if not _is_for(data, today, timezone):
            data = _rebuild(store, today, timezone)
        data["sources"][snapshot.source] = _section(snapshot, company, today, timezone)
        data["updated_at"] = _now()
        store.save_today(data)

def read(store: JobStore, posted_on: date, timezone: str) -> dict[str, dict[str, Any]] | None:
    """The file's sections ({source name: {company, fetched_at, jobs}}) if
    it's for `posted_on` in `timezone`; otherwise None, so the caller reads
    the saved jobs instead. A source with no section has never been fetched."""
    data = _load(store)
    return data["sources"] if _is_for(data, posted_on, timezone) else None

def _rebuild(store: JobStore, today: date, timezone: str) -> dict[str, Any]:
    """A fresh file for `today`, from every source's saved jobs."""
    data: dict[str, Any] = {
        "date": today.isoformat(),
        "timezone": timezone,
        "updated_at": _now(),
        "sources": {},
    }
    for info in available_sources():
        snapshot = store.load_snapshot(info.name)
        if snapshot is not None:
            data["sources"][info.name] = _section(snapshot, info.company, today, timezone)
    return data

def _section(snapshot: JobSnapshot, company: str, today: date, timezone: str) -> dict[str, Any]:
    """One source's entry: its jobs first published on `today` in `timezone`."""
    query = JobQuery(posted_on=today, tz=timezone)
    return {
        "company": company,
        "fetched_at": snapshot.fetched_at,
        "jobs": [job.to_dict() for job in snapshot.jobs if query.matches_date(job)],
    }

def _load(store: JobStore) -> Any:
    """The saved file, or None if it's missing or unreadable (it's only a
    fast path, so a damaged file is ignored and rebuilt on the next save)."""
    try:
        return store.load_today()
    except (ValueError, OSError) as e:
        log.warning("Ignoring unreadable todays-jobs.json: %s", e)
        return None

def _is_for(data: Any, day: date, timezone: str) -> bool:
    return (
        isinstance(data, dict)
        and data.get("date") == day.isoformat()
        and data.get("timezone") == timezone
        and isinstance(data.get("sources"), dict)
    )

def _now() -> str:
    return datetime.now(dt_timezone.utc).isoformat(timespec="seconds")