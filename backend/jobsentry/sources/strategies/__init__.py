"""Reusable base classes, one per job board platform. The loaders in
sources/loaders/ build a subclass of one of these for every catalog entry.

    greenhouse.py   Greenhouse's public board API

Planned: ashby.py (Ashby's public job board API), lever.py (Lever's postings API).
"""

from .greenhouse import GreenhouseSource

__all__ = ["GreenhouseSource"]