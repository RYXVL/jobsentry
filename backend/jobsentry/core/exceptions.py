"""Exception hierarchy.

Everything raised on purpose inherits from JobsentryError, so callers can
catch one type. The CLI turns these into error messages; the API will turn
them into HTTP status codes (e.g. SourceNotFoundError -> 404).
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

class JobNotFoundError(JobsentryError):
    """The requested job ID does not exist in a source's listings."""
    