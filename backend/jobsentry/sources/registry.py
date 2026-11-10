"""Maps source names to source classes.

Sources come from catalogs: JSON files in sources/catalogs/, one per job
board platform, read by the loaders in sources/loaders/. Each catalog entry
becomes a source class registered here, so adding a company means adding
one catalog entry and nothing else. Catalogs are loaded the first time the
registry is used, and again by reload() after a catalog is edited.
"""

from __future__ import annotations

import threading
from collections.abc import Iterable

from ..core.exceptions import SourceNotFoundError
from ..core.http import HttpClient
from .base import JobSource, SourceInfo

# Kept in registration order: loaders in LOADERS order, then catalog order.
_REGISTRY: dict[str, type[JobSource]] = {}
_discovered = False
# The API serves requests on several threads; loading twice at once would
# register every source twice and fail.
_discover_lock = threading.Lock()

def register(cls: type[JobSource]) -> type[JobSource]:
    """Make a source available by its `name`. Used by the loaders, and usable
    as a class decorator for a hand-written source."""
    name = getattr(cls, "name", None)
    if not name or not getattr(cls, "company", None):
        raise TypeError(f"{cls.__name__} must define `name` and `company`")
    if name in _REGISTRY and _REGISTRY[name] is not cls:
        raise ValueError(f"Source name '{name}' is already used by {_REGISTRY[name].__name__}")
    _REGISTRY[name] = cls
    return cls

def _load_all_locked() -> None:
    """(Re)load every catalog into an empty registry. Call with the lock
    held. If loading fails, the registry is left empty and marked not
    loaded, so the next use reports the same error again."""
    global _discovered
    from .loaders import load_all

    _REGISTRY.clear()
    try:
        load_all()
    except Exception:
        _REGISTRY.clear()
        _discovered = False
        raise
    _discovered = True

def _discover() -> None:
    """Load every catalog, once."""
    if _discovered:
        return
    with _discover_lock:
        if not _discovered:
            _load_all_locked()

def reload() -> None:
    """Load every catalog again, e.g. after one was edited from the API.
    Sources already created keep working; new lookups see the new catalogs."""
    with _discover_lock:
        _load_all_locked()

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
    """Every source, sorted by name (for listings)."""
    _discover()
    return [_REGISTRY[name].info() for name in sorted(_REGISTRY)]

def sources_in_order(platform_order: Iterable[str]) -> list[SourceInfo]:
    """Every source grouped by platform (strategy) in `platform_order`,
    keeping catalog order within each platform. Platforms not listed come
    last. Used to queue a fetch-all."""
    _discover()
    rank = {platform: index for index, platform in enumerate(platform_order)}
    infos = [cls.info() for cls in _REGISTRY.values()]
    # sorted() is stable, so catalog order is kept within each platform.
    return sorted(infos, key=lambda info: rank.get(info.strategy, len(rank)))