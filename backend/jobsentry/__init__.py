"""jobsentry: collect job listings from companies' public job boards.

Package layout:
    core/      shared building blocks (models, HTTP client, countries, exceptions)
    sources/   job board platforms (strategies) and the companies on them (catalogs)
    storage/   where job data is persisted (JSON files)
    services/  use cases shared by the CLI and the API: fetching, queries,
               fetch-all, today's jobs, managing sources, the monitor
    api/       the FastAPI app the web frontend talks to
    cli/       the `python -m jobsentry` command line
"""

__version__ = "1.0.0"