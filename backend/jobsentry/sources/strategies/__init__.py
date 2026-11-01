"""Reusable base classes, one per job board platform. The loaders in
sources/loaders/ build a subclass of one of these for every catalog entry.

    greenhouse.py   Greenhouse's public board API
    ashby.py        Ashby's public job posting API
    lever.py        Lever's public postings API (global and EU instances)

_helpers.py holds small helpers the strategies share.
"""

from .ashby import AshbySource
from .greenhouse import GreenhouseSource
from .lever import LeverSource

__all__ = ["AshbySource", "GreenhouseSource", "LeverSource"]