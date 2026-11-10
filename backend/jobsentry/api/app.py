"""Builds the FastAPI application.

`app` is what uvicorn serves. create_app() exists so tests (and
any future entry point) can build an app with their own Settings.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .. import __version__
from ..config import Settings
from ..services.refresh_runner import runner
from .dependencies import get_settings
from .errors import register_error_handlers
from .routes import ROUTERS

#: Every endpoint lives under this prefix, so a v2 can coexist later.
API_PREFIX = "/api/v1"

DESCRIPTION = """
Local API for jobsentry. It reads companies' public job boards and serves
the saved results to the frontend.

* **GET** endpoints read saved data (and fetch it once if nothing is saved yet).
* **POST** `/sources/{source}/refresh` fetches one company's jobs again.
* **POST** `/sources/refresh` starts fetching every company in the background;
  **GET** `/sources/refresh` shows its progress.
* `/catalog/...` adds, edits and deletes sources and their logos (when
  JOBSENTRY_ALLOW_CATALOG_EDITS is on).
"""

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """On shutdown, cancel any sources still queued by a fetch-all."""
    yield
    runner.shutdown()

def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app. If `settings` is given, every request uses it instead
    of the values from backend/.env (handy for tests)."""
    app = FastAPI(
        title="jobsentry API", version=__version__, description=DESCRIPTION, lifespan=lifespan
    )

    if settings is None:
        settings = get_settings()
    else:
        app.dependency_overrides[get_settings] = lambda: settings

    # The frontend runs on a different port, so browsers need CORS permission.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    register_error_handlers(app)
    for router in ROUTERS:
        app.include_router(router, prefix=API_PREFIX)
    return app

app = create_app()