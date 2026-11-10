"""Endpoints for managing sources from the website: the platforms, checking
board names, and adding, editing and deleting catalog entries and logos.

The logic lives in services.catalog_editor; these routes only translate
between HTTP and it.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from ...config import Settings
from ...services import catalog_editor
from ...services.catalog_editor import EntryForm, Platform
from ..dependencies import get_settings
from ..schemas import (
    BoardCheckOut,
    CatalogEntryIn,
    CatalogEntryOut,
    CatalogOut,
    CheckIn,
    CheckOut,
    DeletedOut,
    ErrorOut,
    LogoOut,
    PlatformOut,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])

ERRORS = {
    403: {"model": ErrorOut, "description": "Editing sources is turned off"},
    404: {"model": ErrorOut, "description": "Unknown source"},
    409: {"model": ErrorOut, "description": "Jobs are being fetched"},
    422: {"model": ErrorOut, "description": "The entry isn't valid"},
}

@router.get("", response_model=CatalogOut, summary="Platforms, and whether editing is allowed")
def get_catalog(settings: Settings = Depends(get_settings)) -> CatalogOut:
    return CatalogOut(
        edits_allowed=settings.allow_catalog_edits,
        platforms=[
            PlatformOut(key=p.key, label=p.label, has_region=p.has_region)
            for p in catalog_editor.platforms()
        ],
    )

@router.get("/sources/{name}", response_model=CatalogEntryOut, responses=ERRORS,
            summary="One source's catalog entry")
def get_entry(name: str) -> CatalogEntryOut:
    platform, entry = catalog_editor.get_entry(name)
    return _entry_out(platform, entry)

@router.post("/check", response_model=CheckOut, responses=ERRORS,
             summary="Check board names before saving")
def check_boards(body: CheckIn, settings: Settings = Depends(get_settings)) -> CheckOut:
    """Request each board once, as a refresh would, and report what came back."""
    checks = catalog_editor.check_boards(body.platform, body.board_names, body.region, settings)
    return CheckOut(
        ok=bool(checks) and all(check.ok for check in checks),
        boards=[BoardCheckOut(**vars(check)) for check in checks],
    )

@router.post("/sources", response_model=CatalogEntryOut, status_code=201, responses=ERRORS,
             summary="Add a source")
def add_source(body: CatalogEntryIn, settings: Settings = Depends(get_settings)) -> CatalogEntryOut:
    platform, entry = catalog_editor.add_source(_form(body), settings)
    return _entry_out(platform, entry)

@router.put("/sources/{name}", response_model=CatalogEntryOut, responses=ERRORS,
            summary="Edit a source")
def update_source(
    name: str, body: CatalogEntryIn, settings: Settings = Depends(get_settings)
) -> CatalogEntryOut:
    """Replace the form fields; other keys are kept. `name` in the body is ignored."""
    platform, entry = catalog_editor.update_source(name, _form(body, name), settings)
    return _entry_out(platform, entry)

@router.delete("/sources/{name}", response_model=DeletedOut, responses=ERRORS,
               summary="Delete a source, its saved jobs and its logo")
def delete_source(name: str, settings: Settings = Depends(get_settings)) -> DeletedOut:
    catalog_editor.delete_source(name, settings)
    return DeletedOut(name=name)

@router.put("/sources/{name}/logo", response_model=LogoOut, responses=ERRORS,
            summary="Upload a source's logo (PNG)")
async def upload_logo(
    name: str, request: Request, settings: Settings = Depends(get_settings)
) -> LogoOut:
    """Send the PNG file itself as the request body (Content-Type: image/png).
    It's saved as <JOBSENTRY_LOGOS_DIR>/<name>.png."""
    path = catalog_editor.save_logo(name, await request.body(), settings)
    return LogoOut(name=name, file=path.name, removed=False)

@router.delete("/sources/{name}/logo", response_model=LogoOut, responses=ERRORS,
               summary="Remove a source's logo")
def delete_logo(name: str, settings: Settings = Depends(get_settings)) -> LogoOut:
    removed = catalog_editor.delete_logo(name, settings)
    return LogoOut(name=name, file=None, removed=removed)

def _form(body: CatalogEntryIn, name: str | None = None) -> EntryForm:
    return EntryForm(
        platform=body.platform,
        name=name or body.name,
        company=body.company,
        board_names=tuple(body.board_names),
        homepage=body.homepage,
        region=body.region,
    )

def _entry_out(platform: Platform, entry: dict[str, Any]) -> CatalogEntryOut:
    names = entry.get("board_name")
    board_names = [names] if isinstance(names, str) else list(names or [])
    return CatalogEntryOut(
        platform=platform.key,
        name=str(entry.get("name") or ""),
        company=str(entry.get("company") or ""),
        board_names=[str(n) for n in board_names],
        homepage=entry.get("homepage"),
        region=entry.get("region"),
        extra_keys=sorted(key for key in entry if key not in catalog_editor.FORM_KEYS),
    )