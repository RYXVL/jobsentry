"""Builds the argument parser from the registered commands and runs one.

    python -m jobsentry sources
    python -m jobsentry list <company_id>
    python -m jobsentry show <company_id> <job_id>
"""
from __future__ import annotations

import argparse
import logging
import sys

from ..config import Settings
from ..core.exceptions import JobsentryError
from .commands import COMMANDS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m jobsentry",
        description="Collect job listings from company career sites.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="show progress logs")
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="command")
    for command in COMMANDS:
        sub = subparsers.add_parser(command.name, help=command.help, description=command.help)
        command.add_arguments(sub)
        sub.set_defaults(handler=command)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Returns a process exit code."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        return args.handler.run(args, Settings.from_env())
    except JobsentryError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
