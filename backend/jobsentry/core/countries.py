"""Find countries named in free-text locations, for sources whose data has
no country codes (Greenhouse, Lever, Ashby, ...).

    finder = CountryFinder({"Toronto": "CA"})
    finder.find(["London, United Kingdom", "Remote - Canada", "Toronto"])
    -> ["CA", "GB"]

Country names match whole words in any case. A few abbreviations (US, USA,
UK, UAE) match only in capitals, so ordinary words like "us" never count.
A city on its own gives nothing unless a source adds a hint for it.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from .models import normalize_countries

#: Country names as they commonly appear in job locations, with ISO codes.
#: Add to this when a source uses a name that's missing.
COUNTRY_NAMES: dict[str, str] = {
    "United States": "US", "United States of America": "US",
    "United Kingdom": "GB", "Great Britain": "GB", "England": "GB", "Scotland": "GB",
    "Ireland": "IE", "Canada": "CA", "Mexico": "MX", "Brazil": "BR", "Argentina": "AR",
    "Colombia": "CO", "Chile": "CL", "Germany": "DE", "France": "FR", "Netherlands": "NL",
    "Spain": "ES", "Portugal": "PT", "Italy": "IT", "Poland": "PL", "Romania": "RO",
    "Sweden": "SE", "Denmark": "DK", "Norway": "NO", "Finland": "FI", "Switzerland": "CH",
    "Belgium": "BE", "Austria": "AT", "Luxembourg": "LU", "Czech Republic": "CZ",
    "Czechia": "CZ", "Israel": "IL", "United Arab Emirates": "AE", "India": "IN",
    "Singapore": "SG", "Japan": "JP", "South Korea": "KR", "Korea": "KR", "China": "CN",
    "Hong Kong": "HK", "Taiwan": "TW", "Australia": "AU", "New Zealand": "NZ",
    "Indonesia": "ID", "Philippines": "PH", "Thailand": "TH", "Vietnam": "VN",
    "Malaysia": "MY", "South Africa": "ZA", "Nigeria": "NG", "Kenya": "KE",
    "Egypt": "EG", "Turkey": "TR",
}

#: Abbreviations matched only in capitals ("Remote US", "London, UK").
COUNTRY_ABBREVIATIONS: dict[str, str] = {"US": "US", "USA": "US", "UK": "GB", "UAE": "AE"}

def _whole_words(words: Iterable[str], flags: int = 0) -> re.Pattern[str] | None:
    """One regex matching any of `words` as whole words, longest first so
    "United States of America" wins over "United States"."""
    alternatives = sorted({w for w in words if w}, key=len, reverse=True)
    if not alternatives:
        return None
    return re.compile(r"\b(" + "|".join(map(re.escape, alternatives)) + r")\b", flags)

_NAMES_RE = _whole_words(COUNTRY_NAMES, re.IGNORECASE)
_NAMES = {name.lower(): code for name, code in COUNTRY_NAMES.items()}
_ABBREVIATIONS_RE = _whole_words(COUNTRY_ABBREVIATIONS)

class CountryFinder:
    """Finds countries in location text. `hints` adds a source's own matches,
    e.g. {"Toronto": "CA", "SF": "US"} (whole words, any case). Build one per
    refresh and reuse it for every job, since building compiles the patterns."""

    def __init__(self, hints: Mapping[str, str] | None = None):
        self._hints = {text.lower(): code for text, code in (hints or {}).items()}
        self._hints_re = _whole_words(hints or {}, re.IGNORECASE)

    def find(self, texts: Iterable[str]) -> list[str]:
        """ISO codes for every country found in `texts`, sorted, no duplicates."""
        codes: list[str] = []
        for text in texts:
            codes += [_NAMES[m.lower()] for m in _NAMES_RE.findall(text)]
            if _ABBREVIATIONS_RE:
                codes += [COUNTRY_ABBREVIATIONS[m] for m in _ABBREVIATIONS_RE.findall(text)]
            if self._hints_re:
                codes += [self._hints[m.lower()] for m in self._hints_re.findall(text)]
        return normalize_countries(codes)