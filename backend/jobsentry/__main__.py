"""Entry point for `python -m jobsentry`."""

from .cli import main

# SystemExit() exits the Python process using the value returned by main() as the exit status.
raise SystemExit(main())
