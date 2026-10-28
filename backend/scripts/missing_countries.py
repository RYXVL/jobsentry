"""List a source's saved locations that match no country.

Checks every location in a source's saved jobs against its current country
hints (catalogs/country-hints.json plus the source's own country_hints) and
prints the ones that match nothing, most-used first. Hints are read fresh
from the catalogs, so edit them and run this again without refreshing.

Usage, from backend/:

    python scripts/missing_countries.py stripe
    python scripts/missing_countries.py stripe --file path/to/jobs.json

Where to add a hint for each location it prints:
    a city ("Lisbon")                 -> catalogs/country-hints.json
    a company's shorthand ("CHI")     -> that source's country_hints
    a shared hint wrong for a company -> that source's country_hints (overrides)
    not a place ("Remote", "Anywhere") -> leave it; no single country fits
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

# Make `jobsentry` importable when this file is run directly as a script.
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from jobsentry.config import Settings  # noqa: E402
from jobsentry.core.countries import CountryFinder  # noqa: E402
from jobsentry.core.exceptions import JobsentryError  # noqa: E402
from jobsentry.sources import get_source_class  # noqa: E402

def missing_locations(jobs: Iterable[dict[str, Any]], finder: CountryFinder) -> Counter[str]:
    """Count, per location, the jobs listing it, for locations that match no country."""
    return Counter(
        location
        for job in jobs
        for location in job.get("locations") or []
        if not finder.find([location])
    )

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="List a source's saved locations that match no country."
    )
    parser.add_argument("source", help="source name, e.g. stripe (see `python -m jobsentry sources`)")
    parser.add_argument(
        "--file", type=Path,
        help="jobs.json to check (default: data/<source>/jobs.json)",
    )
    args = parser.parse_args(argv)

    try:
        source = get_source_class(args.source)
        path = args.file or Settings.from_env().data_dir / source.name / "jobs.json"
    except JobsentryError as e:  # unknown source, bad catalog, bad settings
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not path.exists():
        print(
            f"No saved jobs at {path}. Fetch them first: python -m jobsentry list {source.name}",
            file=sys.stderr,
        )
        return 1
    try:
        jobs = json.loads(path.read_text(encoding="utf-8"))["jobs"]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"Error: {path} isn't a saved jobs file ({e})", file=sys.stderr)
        return 1

    finder = CountryFinder(getattr(source, "country_hints", {}))
    missing = missing_locations(jobs, finder)
    total = len({location for job in jobs for location in job.get("locations") or []})

    if not missing:
        print(f"{source.company}: all {total} locations match a country.")
        return 0

    print(f"{source.company}: {len(missing)} of {total} locations match no country\n")
    width = len(str(max(missing.values())))
    for location, count in missing.most_common():
        print(f"  {count:>{width}} {'job ' if count == 1 else 'jobs'}  {location}")
    return 0

if __name__ == "__main__":
    sys.exit(main())