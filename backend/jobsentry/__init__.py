"""jobsentry: collect job listings from company career sites.

Package layout:
    core/      shared building blocks (models, HTTP client, exceptions)
    sources/   one class per company, built on reusable strategies
    storage/   where job data is persisted (JSON files)
    services/  use cases shared by the CLI and the future API
    cli/       the `python -m jobsentry` command line
"""

__version__ = "0.1.0"
