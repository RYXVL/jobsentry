from __future__ import annotations

import argparse

from ...config import Settings
from ...sources import available_sources
from ..output import format_sources
from .base import Command

class SourcesCommand(Command):
    name = "sources"
    help = "list available sources"

    def run(self, args: argparse.Namespace, settings: Settings) -> int:
        print(format_sources(available_sources()))
        return 0
