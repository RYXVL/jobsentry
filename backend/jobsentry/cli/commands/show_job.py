from __future__ import annotations

import argparse

from ...config import Settings
from ...services import JobService
from ..output import format_details
from .base import Command


class ShowCommand(Command):
    name = "show"
    help = "fetch full details for one job and save them"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("source", help="source name (see `sources`)")
        parser.add_argument("job_id", help="job ID (see data/<source>/jobs.json)")

    def run(self, args: argparse.Namespace, settings: Settings) -> int:
        service = JobService.create(args.source, settings)
        details, location = service.get_job_details(args.job_id)
        print(format_details(details))
        print(f"\nSaved to {location}")
        return 0
