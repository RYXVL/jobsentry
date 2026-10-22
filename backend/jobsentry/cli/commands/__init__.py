"""The commands the CLI allows. To add a command, create a 
Command subclass in this folder and add it to COMMANDS."""

from .base import Command
from .list_jobs import ListCommand
from .show_job import ShowCommand
from .sources import SourcesCommand

COMMANDS: list[Command] = [SourcesCommand(), ListCommand(), ShowCommand()]

__all__ = ["COMMANDS", "Command"]
