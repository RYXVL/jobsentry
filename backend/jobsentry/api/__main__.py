"""Run the API locally:

    python -m jobsentry.api            # http://127.0.0.1:8000 (from backend/.env)
    python -m jobsentry.api --reload   # restart automatically when code changes

Interactive docs are served at /docs once it's running.
"""

from __future__ import annotations

import argparse

import uvicorn

from ..config import Settings

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m jobsentry.api", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reload", action="store_true", help="reload on code changes (development)")
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    uvicorn.run(
        "jobsentry.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=args.reload,
    )

if __name__ == "__main__":
    main()
