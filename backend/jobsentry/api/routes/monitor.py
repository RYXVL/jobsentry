"""Endpoints for the monitor: its settings and status, starting and
stopping it, the website's 15-second poll, and verifying email.
The logic lives in services.monitor."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query

from ...config import Settings
from ...services.monitor import MonitorSettings, MonitorStatus, monitor
from ..dependencies import get_settings
from ..schemas import (
    ConfirmEmailIn,
    ErrorOut,
    LastEmailOut,
    MessageOut,
    MonitorEventOut,
    MonitorOut,
    MonitorPollOut,
    MonitorSettingsBody,
    TestEmailIn,
)

router = APIRouter(prefix="/monitor", tags=["monitor"])

ERRORS = {
    422: {"model": ErrorOut, "description": "Settings aren't valid"},
    502: {"model": ErrorOut, "description": "The email couldn't be sent"},
}

@router.get("", response_model=MonitorOut, summary="The monitor's settings and status")
def get_monitor(settings: Settings = Depends(get_settings)) -> MonitorOut:
    return _out(monitor.status(settings))

@router.put("/settings", response_model=MonitorOut, responses=ERRORS, summary="Save the monitor's settings")
def save_settings(body: MonitorSettingsBody, settings: Settings = Depends(get_settings)) -> MonitorOut:
    return _out(monitor.save_settings(settings, MonitorSettings(**body.model_dump())))

@router.post("/start", response_model=MonitorOut, responses=ERRORS, summary="Start monitoring")
def start(settings: Settings = Depends(get_settings)) -> MonitorOut:
    """Fetch every source now, then every interval, alerting about new jobs."""
    return _out(monitor.start(settings))

@router.post("/stop", response_model=MonitorOut, summary="Stop monitoring")
def stop(settings: Settings = Depends(get_settings)) -> MonitorOut:
    monitor.stop()
    return _out(monitor.status(settings))

@router.get("/poll", response_model=MonitorPollOut, summary="For open Job Sentry tabs")
def poll(
    after: int | None = Query(None, ge=0, description="Return alerts with a higher ID"),
    settings: Settings = Depends(get_settings),
) -> MonitorPollOut:
    """Every open tab calls this every 15 seconds. It tells the backend a
    tab is open (so the tab plays the chime) and returns new alerts."""
    status, events = monitor.poll(settings, after)
    return MonitorPollOut(monitor=_out(status), events=[MonitorEventOut(**event) for event in events])

@router.post("/test-email", response_model=MessageOut, responses=ERRORS, summary="Send a test email")
def test_email(body: TestEmailIn, settings: Settings = Depends(get_settings)) -> MessageOut:
    """Step 1 of verifying an address. Then confirm with /confirm-email."""
    return MessageOut(message=monitor.send_test_email(settings, body.email_to))

@router.post("/confirm-email", response_model=MonitorOut, responses=ERRORS,
             summary="Confirm whether the test email arrived")
def confirm_email(body: ConfirmEmailIn, settings: Settings = Depends(get_settings)) -> MonitorOut:
    return _out(monitor.confirm_email(settings, body.email_to, body.received))

def _out(status: MonitorStatus) -> MonitorOut:
    return MonitorOut(
        settings=MonitorSettingsBody(**asdict(status.settings)),
        active=status.active,
        started_at=status.started_at,
        next_fetch_at=status.next_fetch_at,
        fetching=status.fetching,
        last_fetch_started_at=status.last_fetch_started_at,
        email_configured=status.email_configured,
        email_verified=status.email_verified,
        last_email=LastEmailOut(**status.last_email) if status.last_email else None,
        latest_event_id=status.latest_event_id,
    )