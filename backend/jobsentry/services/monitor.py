"""The monitor: fetch every source on a schedule, and alert about new jobs.

While it's on, a background thread starts a normal fetch-all (the
refresh_runner queue) straight away, then every interval (15, 30 or 45
minutes, or 1 to 24 hours), measured from the start of each fetch.

After EVERY fetch-all finishes, whoever started it, the monitor:
  1. collects today's jobs (in Settings.timezone) matching its keyword
     filter (the same matching as Today's jobs) that were posted after the
     previous fetch-all started (the "watermark"). The first fetch after
     Start takes all of today's matching jobs;
  2. if it's on and there are any not announced before, records an alert:
     a chime (played by an open Job Sentry tab if one checked in during the
     last 30 seconds, otherwise by this computer) and/or one email;
  3. moves the watermark to this fetch's start.

The monitor is off whenever the API starts. Its settings, the watermark,
email verification and recent alerts are kept in data/monitor.json, which
"Clear saved jobs" doesn't touch.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, fields, replace
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from typing import Any

from ..config import Settings
from ..core.exceptions import JobsentryError
from ..core.models import Job
from ..storage.json_store import JsonJobStore
from . import email_sender, sound
from .job_service import query_all
from .keep_awake import KeepAwake
from .queries import MAX_PAGE_SIZE, JobQuery, _parse_time
from .refresh_runner import RefreshRun, runner
from .today_jobs import local_today

log = logging.getLogger(__name__)

MONITOR_FILE = "monitor.json"
MINUTE_CHOICES = (15, 30, 45)
HOUR_CHOICES = tuple(range(1, 25))
#: A tab that checked in this recently plays the chime itself.
HEARTBEAT_SECONDS = 30
#: Alerts kept for the website to pick up.
MAX_EVENTS = 50

class MonitorSettingsError(JobsentryError):
    """The monitor's settings aren't valid (shown as a 422)."""

@dataclass(frozen=True)
class MonitorSettings:
    every: int = 30
    unit: str = "minutes"      # "minutes" or "hours"
    keywords: str = ""         # same matching as Today's jobs; empty = every new job
    sound: bool = True
    email: bool = False
    email_to: str = ""

    @property
    def interval(self) -> timedelta:
        return timedelta(minutes=self.every) if self.unit == "minutes" else timedelta(hours=self.every)

    def validated(self) -> MonitorSettings:
        """These settings, tidied, or MonitorSettingsError."""
        if self.unit == "minutes":
            if self.every not in MINUTE_CHOICES:
                raise MonitorSettingsError("Every must be 15, 30 or 45 minutes.")
        elif self.unit == "hours":
            if self.every not in HOUR_CHOICES:
                raise MonitorSettingsError("Every must be between 1 and 24 hours.")
        else:
            raise MonitorSettingsError("The unit must be minutes or hours.")
        email_to = self.email_to.strip()
        if self.email and "@" not in email_to:
            raise MonitorSettingsError("Enter the email address to send alerts to.")
        if not self.sound and not self.email:
            raise MonitorSettingsError("Choose at least one way to be alerted: sound or email.")
        return replace(self, keywords=" ".join(self.keywords.split()), email_to=email_to)

@dataclass(frozen=True)
class MonitorStatus:
    settings: MonitorSettings
    active: bool
    started_at: str | None
    next_fetch_at: str | None
    fetching: bool
    last_fetch_started_at: str | None  # the watermark
    email_configured: bool
    email_verified: bool               # for settings.email_to
    last_email: dict[str, Any] | None  # {"at", "ok", "error"}
    latest_event_id: int

class Monitor:
    """The one monitor for this process; use the module's `monitor`."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._keep_awake = KeepAwake()
        self._generation = 0              # bumped by every Start, so old threads exit
        self._active = False
        self._app: Settings | None = None
        self._started_at: str | None = None
        self._next_fetch_at: datetime | None = None
        self._last_fetch_base: datetime | None = None
        self._first_fetch = False
        self._last_heartbeat = float("-inf")

    # Settings and status ------------------------------------------------------

    def status(self, app: Settings) -> MonitorStatus:
        with self._lock:
            data = self._load(app)
            settings = self._settings_from(data)
            return MonitorStatus(
                settings=settings,
                active=self._active,
                started_at=self._started_at,
                next_fetch_at=_iso(self._next_fetch_at) if self._active else None,
                fetching=runner.is_running(),
                last_fetch_started_at=data.get("watermark"),
                email_configured=email_sender.is_configured(app),
                email_verified=self._verified(app, data, settings.email_to),
                last_email=(data.get("email") or {}).get("last"),
                latest_event_id=int(data.get("next_event_id", 1)) - 1,
            )

    def save_settings(self, app: Settings, new: MonitorSettings) -> MonitorStatus:
        """Save new settings. While running, the next fetch moves to match
        the new interval (from the start of the last fetch)."""
        new = new.validated()
        with self._lock:
            data = self._load(app)
            if new.email and not self._verified(app, data, new.email_to):
                raise MonitorSettingsError(
                    "Email alerts need a verified address: send a test email and confirm it first."
                )
            data["settings"] = _settings_dict(new)
            self._save(app, data)
            if self._active and self._last_fetch_base is not None:
                self._next_fetch_at = max(_now(), self._last_fetch_base + new.interval)
                self._wake.set()
        return self.status(app)

    # Start and stop -----------------------------------------------------------

    def start(self, app: Settings) -> MonitorStatus:
        """Start monitoring: fetch now, then every interval."""
        with self._lock:
            if not self._active:
                data = self._load(app)
                settings = self._settings_from(data).validated()
                if settings.email and not self._verified(app, data, settings.email_to):
                    raise MonitorSettingsError(
                        "Email alerts need a verified address: send a test email and confirm it first."
                    )
                self._generation += 1
                self._active = True
                self._app = app
                self._started_at = _iso(_now())
                self._next_fetch_at = _now()
                self._last_fetch_base = None
                self._first_fetch = True
                self._wake.clear()
                threading.Thread(
                    target=self._loop, args=(self._generation,), name="monitor", daemon=True,
                ).start()
                self._keep_awake.start()
        return self.status(app)

    def stop(self) -> None:
        """Stop monitoring. A fetch already running finishes, but no alert
        is sent for it."""
        with self._lock:
            self._active = False
            self._generation += 1
            self._started_at = None
            self._next_fetch_at = None
            self._first_fetch = False
            self._wake.set()
        self._keep_awake.stop()

    # The website --------------------------------------------------------------

    def poll(self, app: Settings, after: int | None) -> tuple[MonitorStatus, list[dict[str, Any]]]:
        """Called by every open Job Sentry tab (every 15 seconds): records
        that a tab is open, and returns alerts newer than `after`. With
        `after` None, no alerts are returned (the tab only learns the
        latest ID, so it won't replay old alerts)."""
        with self._lock:
            self._last_heartbeat = time.monotonic()
            events = self._load(app).get("events") or []
        new = [event for event in events if after is not None and event.get("id", 0) > after]
        return self.status(app), new

    def send_test_email(self, app: Settings, email_to: str) -> str:
        """Step 1 of verifying an address: send a test email."""
        email_to = email_to.strip()
        if "@" not in email_to:
            raise MonitorSettingsError("Enter a valid email address.")
        email_sender.send_email(
            app, email_to,
            "Job Sentry: test email",
            "This is a test email from Job Sentry.\n\n"
            "If you can read this, go back to the Monitor page and confirm you received it.",
        )
        with self._lock:
            data = self._load(app)
            data.setdefault("email", {})["pending"] = email_sender.fingerprint(app, email_to)
            self._save(app, data)
        return f"Sent: the mail server accepted the test email to {email_to}."

    def confirm_email(self, app: Settings, email_to: str, received: bool) -> MonitorStatus:
        """Step 2: you confirm whether the test email arrived. Only "yes"
        after a successful send to this address (with these mail settings)
        verifies it, and saves it as the alert address."""
        email_to = email_to.strip()
        with self._lock:
            data = self._load(app)
            email = data.setdefault("email", {})
            print_ = email_sender.fingerprint(app, email_to)
            if received:
                if email.get("pending") != print_:
                    raise MonitorSettingsError(
                        "Send a test email to this address first (the mail settings may have changed)."
                    )
                email["verified"] = print_
                settings = self._settings_from(data)
                data["settings"] = _settings_dict(replace(settings, email_to=email_to))
            email.pop("pending", None)
            self._save(app, data)
        return self.status(app)

    # The schedule -------------------------------------------------------------

    def _loop(self, generation: int) -> None:
        """Wait until the next fetch is due, start it, schedule the next one."""
        while True:
            with self._lock:
                if not self._active or generation != self._generation:
                    return
                due, app = self._next_fetch_at, self._app
            wait = (due - _now()).total_seconds() if due else 0
            if wait > 0:
                self._wake.wait(timeout=wait)
                self._wake.clear()
                continue

            started = _now()
            try:
                run = runner.start(app, trigger="monitor")  # returns a running one if a fetch is going
                started = _parse_time(run.started_at) or started
            except Exception:
                log.exception("The monitor couldn't start a fetch")

            with self._lock:
                if generation != self._generation:
                    return
                interval = self._settings_from(self._load(app)).interval
                self._last_fetch_base = started
                self._next_fetch_at = max(started + interval, _now() + timedelta(seconds=1))

    # After every fetch-all ----------------------------------------------------

    def on_run_finished(self, run: RefreshRun) -> None:
        """Look for new jobs, alert if monitoring, and move the watermark."""
        app = run.settings
        if app is None:
            return
        event: dict[str, Any] | None = None
        settings: MonitorSettings | None = None
        send_email = False
        with self._lock:
            data = self._load(app)
            since = data.get("watermark")
            if self._active:
                first, self._first_fetch = self._first_fetch, False
                settings = self._settings_from(data)
                jobs = self._new_jobs(app, settings.keywords, None if first else since)
                jobs = self._not_announced(data, app, jobs)
                if jobs:
                    event = self._record_event(data, jobs, settings.sound and self._tab_open())
                    send_email = settings.email and self._verified(app, data, settings.email_to)
            data["watermark"] = run.started_at
            self._save(app, data)

        if event is None or settings is None:
            return
        if settings.sound and not event["play_in_browser"]:
            sound.play_chime()
        if send_email:
            self._email_alert(app, settings.email_to, event)

    def _new_jobs(self, app: Settings, keywords: str, since: str | None) -> list[Job]:
        """Today's jobs matching `keywords` (newest first), posted after
        `since` (or all of today's, when `since` is None)."""
        query = JobQuery(
            text=keywords or None, posted_on=local_today(app.timezone), tz=app.timezone,
            limit=MAX_PAGE_SIZE,
        )
        jobs: list[Job] = []
        while True:
            page = query_all(replace(query, offset=len(jobs)), settings=app)
            jobs += page.jobs
            if not page.jobs or len(jobs) >= page.total:
                break
        cutoff = _parse_time(since) if since else None
        if cutoff is None:
            return jobs
        return [job for job in jobs if (posted := _parse_time(job.posted_at)) and posted > cutoff]

    def _not_announced(self, data: dict[str, Any], app: Settings, jobs: list[Job]) -> list[Job]:
        """Drop jobs already in an alert today, and remember the rest."""
        today = local_today(app.timezone).isoformat()
        seen = data.get("announced") or {}
        if seen.get("date") != today:
            seen = {"date": today, "ids": []}
        ids = set(seen["ids"])
        fresh = [job for job in jobs if f"{job.source}:{job.id}" not in ids]
        seen["ids"] = [*seen["ids"], *(f"{job.source}:{job.id}" for job in fresh)]
        data["announced"] = seen
        return fresh

    def _record_event(self, data: dict[str, Any], jobs: list[Job], play_in_browser: bool) -> dict[str, Any]:
        event_id = int(data.get("next_event_id", 1))
        event = {
            "id": event_id,
            "at": _iso(_now()),
            "count": len(jobs),
            "play_in_browser": play_in_browser,
            "jobs": [
                {
                    "source": job.source, "id": job.id, "title": job.title,
                    "company": job.company, "url": job.url,
                    "locations": job.locations, "posted_at": job.posted_at,
                }
                for job in jobs
            ],
        }
        data["events"] = [*(data.get("events") or []), event][-MAX_EVENTS:]
        data["next_event_id"] = event_id + 1
        return event

    def _email_alert(self, app: Settings, email_to: str, event: dict[str, Any]) -> None:
        """Send one email listing the alert's jobs, and record the result."""
        count = event["count"]
        subject = f"Job Sentry: {count} new {'job' if count == 1 else 'jobs'}"
        lines, items = [], []
        for job in event["jobs"]:
            where = ", ".join(job["locations"]) or "Location not listed"
            lines.append(f"{job['title']} at {job['company']} ({where})\n{job['url']}")
            items.append(
                f'<li><a href="{escape(job["url"])}">{escape(job["title"])}</a>'
                f" at {escape(job['company'])} <small>({escape(where)})</small></li>"
            )
        text = f"{count} new {'job' if count == 1 else 'jobs'} posted today:\n\n" + "\n\n".join(lines)
        html = f"<p>{count} new {'job' if count == 1 else 'jobs'} posted today:</p><ul>{''.join(items)}</ul>"
        result: dict[str, Any] = {"at": _iso(_now()), "ok": True, "error": None}
        try:
            email_sender.send_email(app, email_to, subject, text, html)
        except email_sender.EmailError as e:
            log.warning("Monitor email failed: %s", e)
            result = {"at": result["at"], "ok": False, "error": str(e)}
        with self._lock:
            data = self._load(app)
            data.setdefault("email", {})["last"] = result
            self._save(app, data)

    # Helpers ------------------------------------------------------------------

    def _tab_open(self) -> bool:
        return time.monotonic() - self._last_heartbeat <= HEARTBEAT_SECONDS

    def _verified(self, app: Settings, data: dict[str, Any], email_to: str) -> bool:
        if not email_to or not email_sender.is_configured(app):
            return False
        return (data.get("email") or {}).get("verified") == email_sender.fingerprint(app, email_to)

    @staticmethod
    def _settings_from(data: dict[str, Any]) -> MonitorSettings:
        raw = data.get("settings") or {}
        known = {f.name for f in fields(MonitorSettings)}
        try:
            return MonitorSettings(**{key: value for key, value in raw.items() if key in known})
        except TypeError:
            return MonitorSettings()

    @staticmethod
    def _path(app: Settings) -> Path:
        return Path(app.data_dir) / MONITOR_FILE

    def _load(self, app: Settings) -> dict[str, Any]:
        try:
            data = JsonJobStore._read(self._path(app))
        except (ValueError, OSError) as e:
            log.warning("Ignoring unreadable %s: %s", MONITOR_FILE, e)
            data = None
        return data if isinstance(data, dict) else {}

    def _save(self, app: Settings, data: dict[str, Any]) -> None:
        JsonJobStore._write(self._path(app), data)

def _settings_dict(settings: MonitorSettings) -> dict[str, Any]:
    return {f.name: getattr(settings, f.name) for f in fields(MonitorSettings)}

def _now() -> datetime:
    return datetime.now(timezone.utc)

def _iso(moment: datetime | None) -> str | None:
    return moment.isoformat(timespec="seconds") if moment else None

#: The one monitor for this process. It hears about every finished fetch-all.
monitor = Monitor()
runner.add_finished_listener(monitor.on_run_finished)