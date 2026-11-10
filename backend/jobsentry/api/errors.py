"""Turns jobsentry exceptions into consistent JSON error responses.

Every error body has the same shape, so the frontend can handle them in one place:

    {"error": {"code": "job_not_found", "message": "No Stripe job with ID '1'"}}

Request validation errors (422) add a `details` list describing each bad field.
"""

from __future__ import annotations

import logging

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..core.exceptions import (
    ConfigError,
    JobNotFoundError,
    JobsentryError,
    RefreshInProgressError,
    SourceBlockedError,
    SourceError,
    SourceNotFoundError,
)
from ..services.catalog_editor import CatalogEditsDisabledError, CatalogEntryError
from ..services.email_sender import EmailError
from ..services.monitor import MonitorSettingsError

log = logging.getLogger(__name__)

#: Exception class -> (HTTP status, machine-readable code). The most specific
#: class wins, so SourceBlockedError is matched before its parent SourceError.
ERROR_MAP: dict[type[JobsentryError], tuple[int, str]] = {
    SourceNotFoundError: (404, "source_not_found"),
    JobNotFoundError: (404, "job_not_found"),
    RefreshInProgressError: (409, "refresh_in_progress"),
    CatalogEntryError: (422, "invalid_entry"),             # a bad entry from the website
    CatalogEditsDisabledError: (403, "catalog_edits_disabled"),
    MonitorSettingsError: (422, "invalid_monitor_settings"),
    EmailError: (502, "email_error"),              # the mail server failed or refused
    SourceBlockedError: (502, "source_blocked"),   # the career site refused us
    SourceError: (502, "source_error"),            # the career site failed or changed
    ConfigError: (500, "config_error"),
    JobsentryError: (500, "internal_error"),
}

def error_body(code: str, message: str, details: Any = None) -> dict:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}

def _lookup(exc: JobsentryError) -> tuple[int, str]:
    for cls in type(exc).__mro__:
        if cls in ERROR_MAP:
            return ERROR_MAP[cls]
    return 500, "internal_error"

async def handle_jobsentry_error(request: Request, exc: JobsentryError) -> JSONResponse:
    status, code = _lookup(exc)
    if status >= 500:
        log.warning("%s %s -> %s: %s", request.method, request.url.path, code, exc)
    return JSONResponse(status_code=status, content=error_body(code, str(exc)))

async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Bad query/path parameters, e.g. limit=0 or remote=maybe."""
    return JSONResponse(
        status_code=422,
        content=error_body("invalid_request", "Invalid request parameters",
                           details=jsonable_encoder(exc.errors())),
    )

async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """FastAPI's own errors, e.g. 404 for an unknown URL or 405 wrong method."""
    code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
    return JSONResponse(status_code=exc.status_code, content=error_body(code, str(exc.detail)),
                        headers=getattr(exc, "headers", None))

def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(JobsentryError, handle_jobsentry_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)