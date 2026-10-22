"""Maps source names to source classes.

Sources register themselves with @register. Modules in sources/companies/
are imported automatically the first time the registry is used, so adding a
company means adding one file and nothing else.
"""

from __future__ import annotations

import importlib
import pkgutil

from ..core.exceptions import SourceNotFoundError
from ..core.http import HttpClient
from .base import JobSource, SourceInfo

_REGISTRY: dict[str, type[JobSource]] = {}
_discovered = False

def register(cls: type[JobSource]) -> type[JobSource]:
    """Class decorator that makes a source available by its `name`."""
    name = getattr(cls, "name", None)
    if not name or not getattr(cls, "company", None):
        raise TypeError(f"{cls.__name__} must define `name` and `company`")
    if name in _REGISTRY and _REGISTRY[name] is not cls:
        raise ValueError(f"Source name '{name}' is already used by {_REGISTRY[name].__name__}")
    _REGISTRY[name] = cls
    return cls

def _discover() -> None:
    """Import every module in sources/companies/ so their @register runs."""
    global _discovered
    if _discovered:
        return
    from . import companies

    for module in pkgutil.iter_modules(companies.__path__):
        if not module.name.startswith("_"):
            importlib.import_module(f"{companies.__name__}.{module.name}")
    _discovered = True

def get_source_class(name: str) -> type[JobSource]:
    _discover()
    try:
        return _REGISTRY[name.lower()]
    except KeyError:
        available = ", ".join(sorted(_REGISTRY)) or "none"
        raise SourceNotFoundError(f"Unknown source '{name}'. Available: {available}") from None

def create_source(name: str, http: HttpClient | None = None) -> JobSource:
    """Instantiate the source registered under `name`."""
    return get_source_class(name)(http=http)

def available_sources() -> list[SourceInfo]:
    _discover()
    return [_REGISTRY[name].info() for name in sorted(_REGISTRY)]
