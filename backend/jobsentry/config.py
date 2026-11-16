"""Application settings.

Values come from, in order of priority:
    1. Real environment variables set on the machine
    2. backend/.env (see backend/.env.example)
    3. The defaults below

Scraping
    JOBSENTRY_DATA_DIR      where JSON is written (default: backend/data;
                            relative paths are resolved against backend/)
    JOBSENTRY_HTTP_TIMEOUT  seconds per request (default: 30)
    JOBSENTRY_HTTP_RETRIES  retries on 429/5xx and connection errors (default: 3)
    JOBSENTRY_USER_AGENT    User-Agent header sent to job boards

Fetch all jobs
    JOBSENTRY_REFRESH_WORKERS  companies fetched at the same time (default: 5)
    JOBSENTRY_REFRESH_ORDER    platforms in fetch order
                               (default: ashby,greenhouse,lever,smartrecruiters)
    JOBSENTRY_TIMEZONE         IANA time zone for "today" (default: this computer's)

Managing sources from the website
    JOBSENTRY_ALLOW_CATALOG_EDITS  allow adding/editing/deleting sources (default: true)
    JOBSENTRY_LOGOS_DIR            where uploaded logos are saved
                                   (default: ../frontend/public/logos)

Monitor email alerts
    JOBSENTRY_SMTP_HOST      mail server; empty turns email off (default: empty)
    JOBSENTRY_SMTP_PORT      port (default: 587)
    JOBSENTRY_SMTP_SECURITY  starttls, ssl or none (default: starttls)
    JOBSENTRY_SMTP_USERNAME  login, if the server needs one
    JOBSENTRY_SMTP_PASSWORD  password (an app password for Gmail and Outlook)
    JOBSENTRY_SMTP_FROM      sender address

API
    JOBSENTRY_API_HOST      interface to bind (default: 127.0.0.1, this machine only)
    JOBSENTRY_API_PORT      port to listen on (default: 8000)
    JOBSENTRY_CORS_ORIGINS  comma-separated frontend URLs allowed to call the API

The CLI and the API both call Settings.from_env(), so they always share the
same configuration. Invalid values raise ConfigError.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

from .core.exceptions import ConfigError

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"

#: Common local dev-server URLs
DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)

#: Platforms (source strategies) in the order "Fetch all jobs" works through them.
DEFAULT_REFRESH_ORDER = ("ashby", "greenhouse", "lever", "smartrecruiters")

#: Upper bound on refresh workers, so a typo can't start hundreds of threads.
MAX_REFRESH_WORKERS = 32

#: Where the frontend serves company logos from, next to backend/.
DEFAULT_LOGOS_DIR = (BACKEND_DIR.parent / "frontend" / "public" / "logos").resolve()

#: How alert emails connect to the mail server.
SMTP_SECURITY_CHOICES = ("starttls", "ssl", "none")

def load_env_file(path: Path = ENV_FILE) -> None:
    """Load `path` into os.environ without overriding variables already set.
    A missing file is fine; defaults are used instead."""
    load_dotenv(path, override=False)

def _get_number(
    name: str, default: float, kind: type, minimum: float, maximum: float | None = None
) -> float:
    """Read a numeric variable, raising ConfigError if it is invalid."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = kind(raw.strip())
    except ValueError:
        expected = "a whole number" if kind is int else "a number"
        raise ConfigError(f"{name} must be {expected}, got '{raw}'") from None
    if value < minimum or (maximum is not None and value > maximum):
        bounds = f"between {minimum} and {maximum}" if maximum is not None else f"at least {minimum}"
        raise ConfigError(f"{name} must be {bounds}, got {value}")
    return value

def _get_bool(name: str, default: bool) -> bool:
    """Read a true/false variable (true/false, yes/no, on/off, 1/0)."""
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    raise ConfigError(f"{name} must be true or false, got '{raw}'")

def _get_choice(name: str, default: str, choices: tuple[str, ...]) -> str:
    """Read a variable that must be one of `choices` (any case)."""
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    if raw not in choices:
        raise ConfigError(f"{name} must be one of {', '.join(choices)}, got '{raw}'")
    return raw

def _get_str(name: str) -> str:
    return (os.getenv(name) or "").strip()

def _get_list(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    """Read a comma-separated variable into a tuple of non-empty strings."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return tuple(item.strip() for item in raw.split(",") if item.strip())

def _resolve_path(value: str | Path) -> Path:
    """Make relative paths relative to backend/, not the current directory."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else (BACKEND_DIR / path).resolve()

def _is_timezone(name: str) -> bool:
    try:
        ZoneInfo(name)
        return True
    except (ZoneInfoNotFoundError, ValueError):
        return False

def system_timezone() -> str:
    """This computer's IANA time zone (e.g. "Asia/Kolkata"), from the TZ
    variable or the /etc/localtime link on macOS and Linux. Falls back to
    UTC where neither is available (e.g. Windows): set JOBSENTRY_TIMEZONE."""
    candidates = [os.getenv("TZ", "").strip().lstrip(":")]
    try:
        target = os.path.realpath("/etc/localtime")
        if "zoneinfo/" in target:
            candidates.append(target.split("zoneinfo/", 1)[1])
    except OSError:
        pass
    for name in candidates:
        if name and _is_timezone(name):
            return name
    return "UTC"

def _get_timezone(name: str, default: str) -> str:
    """Read an IANA time zone variable, raising ConfigError if it's unknown."""
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    if not _is_timezone(raw):
        raise ConfigError(f"{name} must be an IANA time zone like Asia/Kolkata, got '{raw}'")
    return raw

@dataclass(frozen=True)
class Settings:
    data_dir: Path = BACKEND_DIR / "data"
    http_timeout: float = 30.0
    http_retries: int = 3
    user_agent: str = "Mozilla/5.0"
    refresh_workers: int = 5
    refresh_order: tuple[str, ...] = DEFAULT_REFRESH_ORDER
    timezone: str = "UTC"
    allow_catalog_edits: bool = True
    logos_dir: Path = DEFAULT_LOGOS_DIR
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_security: str = "starttls"
    smtp_username: str = ""
    # Kept out of repr() so the password never ends up in a log.
    smtp_password: str = field(default="", repr=False)
    smtp_from: str = ""
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS

    @classmethod
    def from_env(cls, env_file: Path = ENV_FILE) -> Settings:
        """Build settings from the environment, loading `env_file` first."""
        load_env_file(env_file)
        d = cls()
        return cls(
            data_dir=_resolve_path(os.getenv("JOBSENTRY_DATA_DIR") or d.data_dir),
            http_timeout=_get_number("JOBSENTRY_HTTP_TIMEOUT", d.http_timeout, float, 0.1),
            http_retries=_get_number("JOBSENTRY_HTTP_RETRIES", d.http_retries, int, 0),
            user_agent=_get_str("JOBSENTRY_USER_AGENT") or d.user_agent,
            refresh_workers=_get_number(
                "JOBSENTRY_REFRESH_WORKERS", d.refresh_workers, int, 1, MAX_REFRESH_WORKERS
            ),
            refresh_order=tuple(
                platform.lower()
                for platform in _get_list("JOBSENTRY_REFRESH_ORDER", d.refresh_order)
            ),
            timezone=_get_timezone("JOBSENTRY_TIMEZONE", system_timezone()),
            allow_catalog_edits=_get_bool("JOBSENTRY_ALLOW_CATALOG_EDITS", d.allow_catalog_edits),
            logos_dir=_resolve_path(os.getenv("JOBSENTRY_LOGOS_DIR") or d.logos_dir),
            smtp_host=_get_str("JOBSENTRY_SMTP_HOST"),
            smtp_port=_get_number("JOBSENTRY_SMTP_PORT", d.smtp_port, int, 1, 65535),
            smtp_security=_get_choice("JOBSENTRY_SMTP_SECURITY", d.smtp_security, SMTP_SECURITY_CHOICES),
            smtp_username=_get_str("JOBSENTRY_SMTP_USERNAME"),
            smtp_password=os.getenv("JOBSENTRY_SMTP_PASSWORD") or "",
            smtp_from=_get_str("JOBSENTRY_SMTP_FROM"),
            api_host=_get_str("JOBSENTRY_API_HOST") or d.api_host,
            api_port=_get_number("JOBSENTRY_API_PORT", d.api_port, int, 1, 65535),
            cors_origins=_get_list("JOBSENTRY_CORS_ORIGINS", d.cors_origins),
        )