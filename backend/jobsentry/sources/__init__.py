"""Job sources: one class per company.

    base.py        JobSource, the interface every source implements
    registry.py    finds and creates sources by name
    strategies/    reusable base classes, one per way a site delivers data
    companies/     concrete sources; any module here is loaded automatically
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
