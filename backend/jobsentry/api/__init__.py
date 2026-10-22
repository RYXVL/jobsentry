"""HTTP API for the frontend (stage 2), built with FastAPI.

    app.py           create_app(): builds the FastAPI app
    __main__.py      `python -m jobsentry.api` runs it with uvicorn
    dependencies.py  shared settings, HTTP client and JobService per request
    errors.py        maps JobsentryError subclasses to HTTP responses
    schemas.py       Pydantic response models (the API's public contract)
    routes/          one module per group of endpoints

Every route is a thin wrapper around JobService, so the API and the CLI
always behave the same way.
"""

from .app import create_app

__all__ = ["create_app"]
