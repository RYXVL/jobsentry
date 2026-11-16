"""All routers, in the order they appear in /docs. To add a group of
endpoints, create a module here with a `router` and add it to ROUTERS."""

from . import all_jobs, catalog, health, jobs, monitor, sources

ROUTERS = [
    health.router, sources.router, jobs.router, all_jobs.router, catalog.router, monitor.router,
]