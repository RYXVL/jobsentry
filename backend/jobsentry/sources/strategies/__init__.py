"""Reusable base classes, one per way a site delivers its job data.

Company sources subclass one of these so they only describe what is unique
about their site. Planned additions as new companies need them:
    json_api.py     REST endpoints returning JSON (Lever, Ashby, ...)
    greenhouse.py   Greenhouse public board API
    workday.py      Workday's POST-based job search
    json_ld.py      schema.org JobPosting blocks in HTML
"""
from .next_data import NextDataSource, extract_next_data

__all__ = ["NextDataSource", "extract_next_data"]
