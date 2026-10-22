"""All routers, in the order they appear in /docs. To add a group of
endpoints, create a module here with a `router` and add it to ROUTERS."""

from . import health, jobs, sources

ROUTERS = [health.router, sources.router, jobs.router]
