"""Formatting helpers so commands share one output style."""

from __future__ import annotations

from ..core.models import JobDetails
from ..sources import SourceInfo

#: Display names for core.models.WORK_MODES.
WORK_MODE_LABELS = {"on_site": "On-site", "hybrid": "Hybrid", "remote": "Remote"}

def format_sources(sources: list[SourceInfo]) -> str:
    if not sources:
        return "No sources registered."
    width = max(len(s.name) for s in sources)
    return "\n".join(f"{s.name:<{width}}  {s.company}  ({s.strategy})" for s in sources)

def format_details(d: JobDetails) -> str:
    modes = " or ".join(WORK_MODE_LABELS.get(m, m) for m in d.work_modes)
    lines = [
        f"{d.title}  [{d.id}]  ({d.company})",
        f"Team:      {', '.join(d.teams) or '-'}",
        f"Locations: {', '.join(d.locations) or '-'}",
        f"Countries: {', '.join(d.countries) or '-'}",
        f"Mode:      {modes or '-'}",
        f"Type:      {d.employment_type or '-'}",
        f"Updated:   {d.updated_at or '-'}",
        f"Posted:    {d.posted_at or '-'}",
        f"Apply:     {d.apply_url or d.url}",
    ]
    return "\n".join(lines)