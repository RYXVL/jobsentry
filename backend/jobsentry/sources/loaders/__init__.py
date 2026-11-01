"""Catalog loaders, one per job board platform. Each reads its JSON file
in sources/catalogs/ and registers a source for every entry.

To add a platform: write <platform>_loader.py with a load() function, using
the helpers in _catalog.py, and add it to LOADERS.
"""

from __future__ import annotations

from . import ashby_loader, greenhouse_loader, lever_loader

LOADERS = (greenhouse_loader, ashby_loader, lever_loader)

def load_all() -> None:
    """Run every loader. Called once by the registry."""
    for loader in LOADERS:
        loader.load()