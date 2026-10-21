"""Application settings.

Values come from environment variables either using the defaults below or variables set inside backend/.env 

    JOBSENTRY_DATA_DIR      where JSON is written (default: backend/data; relative paths are resolved against backend/)
    JOBSENTRY_HTTP_TIMEOUT  seconds per request (default: 30)
    JOBSENTRY_HTTP_RETRIES  retries on 429/5xx and connection errors (default: 3)

Invalid environment variable values raise ConfigError.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .core.exceptions import ConfigError

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"

def load_env_file(path: Path = ENV_FILE) -> None:
    """Load `path` into os.environ without overriding variables already set.
    A missing file is fine; defaults are used instead."""
    load_dotenv(path, override=False)

def _get_number(name: str, default: float, kind: type, minimum: float) -> float:
    """Read a numeric variable, raising ConfigError if it is invalid."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = kind(raw.strip())
    except ValueError:
        expected = "a whole number" if kind is int else "a number"
        raise ConfigError(f"{name} must be {expected}, got '{raw}'") from None
    if value < minimum:
        raise ConfigError(f"{name} must be at least {minimum}, got {value}")
    return value

def _resolve_path(value: str | Path) -> Path:
    """Make relative paths relative to backend/, not the current directory."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else BACKEND_DIR / path

@dataclass(frozen=True)
class Settings:
    data_dir: Path = BACKEND_DIR / "data"
    http_timeout: float = 30.0
    http_retries: int = 3

    @classmethod
    def from_env(cls, env_file: Path = ENV_FILE) -> Settings:
        """Build settings from the environment, loading `env_file` first."""
        load_env_file(env_file)
        defaults = cls()
        return cls(
            data_dir=_resolve_path(os.getenv("JOBSENTRY_DATA_DIR") or defaults.data_dir),
            http_timeout=_get_number("JOBSENTRY_HTTP_TIMEOUT", defaults.http_timeout, float, 0.1),
            http_retries=_get_number("JOBSENTRY_HTTP_RETRIES", defaults.http_retries, int, 0),
        )
