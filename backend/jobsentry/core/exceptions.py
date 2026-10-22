"""Exception hierarchy.

Everything raised on purpose inherits from JobsentryError, so callers can
catch one type. The CLI turns these into error messages; the API maps each
one to an HTTP status code in api/errors.py.
"""

class JobsentryError(Exception):
    """Base class for all expected jobsentry errors."""

class ConfigError(JobsentryError):
    """A setting (e.g. in backend/.env) has an invalid value."""

class SourceNotFoundError(JobsentryError):
    """No source is registered under the requested name."""

class SourceError(JobsentryError):
    """A source could not fetch or understand a site's data
    (network failure, unexpected page structure, etc.)."""

class SourceBlockedError(SourceError):
    """The site refused automated access (e.g. 401/403).
    Never retried or worked around: check the site's terms or use an official API."""

class JobNotFoundError(JobsentryError):
    """The requested job ID does not exist in a source's listings."""

class RefreshInProgressError(JobsentryError):
    """A refresh for this source is already running in this process."""
