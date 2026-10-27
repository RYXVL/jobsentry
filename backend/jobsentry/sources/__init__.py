"""Job sources: one per company, built from catalogs.

    base.py        JobSource, the interface every source implements
    registry.py    finds and creates sources by name
    strategies/    reusable base classes, one per job board platform
    catalogs/      JSON lists of companies, one file per platform
    loaders/       read catalogs/ and register a source for every entry
"""

from .base import JobSource, SourceInfo
from .registry import available_sources, create_source, get_source_class, register

__all__ = [
    "JobSource",
    "SourceInfo",
    "available_sources",
    "create_source",
    "get_source_class",
    "register",
]
