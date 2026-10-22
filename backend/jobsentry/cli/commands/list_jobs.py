from __future__ import annotations

import argparse

from ...config import Settings
from ...services import JobService
from .base import Command


class ListCommand(Command):
    name = "list"
    help = "fetch all jobs from a source and save them"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("source", help="source name (see `sources`)")

    def run(self, args: argparse.Namespace, settings: Settings) -> int:
        service = JobService.create(args.source, settings)
        snapshot, location = service.refresh_jobs()
        print(f"Saved {len(snapshot.jobs)} {service.source.company} jobs to {location}")
        return 0
