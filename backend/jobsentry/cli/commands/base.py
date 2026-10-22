"""Base class for CLI commands."""

from __future__ import annotations

import argparse
from abc import ABC, abstractmethod
from typing import ClassVar

from ...config import Settings

class Command(ABC):
    #: Word typed after `python -m jobsentry`.
    name: ClassVar[str]
    #: One-line description shown in --help.
    help: ClassVar[str]

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Declare this command's arguments. Default: none."""

    @abstractmethod
    def run(self, args: argparse.Namespace, settings: Settings) -> int:
        """Do the work and return an exit code (0 = success). Raise
        JobsentryError subclasses for expected failures."""
