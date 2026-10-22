"""Formatting helpers so commands share one output style."""

from __future__ import annotations

from ..core.models import JobDetails
from ..sources import SourceInfo

def format_sources(sources: list[SourceInfo]) -> str:
    if not sources:
        return "No sources registered."
    width = max(len(s.name) for s in sources)
    return "\n".join(f"{s.name:<{width}}  {s.company}  ({s.strategy})" for s in sources)

def format_details(d: JobDetails) -> str:
    lines = [
        f"{d.title}  [{d.id}]  ({d.company})",
        f"Team:      {', '.join(d.teams) or '-'}",
        f"Locations: {', '.join(d.locations) or '-'}",
        f"Type:      {d.employment_type or '-'}",
        f"Posted:    {d.posted_at or '-'}",
    ]
    if d.salary and d.salary.min is not None:
        top = f" - {d.salary.max:,.0f}" if d.salary.max is not None else ""
        lines.append(f"Salary:    {d.salary.currency or ''} {d.salary.min:,.0f}{top}".rstrip())
    lines.append(f"Apply:     {d.apply_url or d.url}")
    return "\n".join(lines)
