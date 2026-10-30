"""Find countries named in free-text locations, for sources whose data has
no country codes (Greenhouse, Lever, Ashby, ...).

    finder = CountryFinder({"Toronto": "CA"})
    finder.find(["London, United Kingdom", "Remote - Canada", "Toronto"])
    -> ["CA", "GB"]

Country names, US state names and Canadian province names match whole
words in any case. A few abbreviations (US, U.S., USA, UK, U.K., UAE) match
only in capitals, so ordinary words like "us" never count. A city on its
own gives nothing unless a hint names it.

With state_codes=True, a location ending in ", ST" or " - ST" that matched
nothing else is read as a US state or Canadian province ("Tempe, AZ" -> US,
"Remote - TX" -> US, "Vancouver, BC" -> CA). It's off by default because
many of those codes are also country codes (CA is California or Canada, IN
is Indiana or India), so only turn it on for boards that write North
American locations this way.
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
    "Ireland": "IE", "Canada": "CA", "Mexico": "MX", "Costa Rica": "CR", "Brazil": "BR",
    "Argentina": "AR", "Uruguay": "UY", "Colombia": "CO", "Chile": "CL",
    "Germany": "DE", "France": "FR", "Netherlands": "NL", "Spain": "ES",
    "Portugal": "PT", "Italy": "IT", "Poland": "PL", "Romania": "RO", "Serbia": "RS",
    "Slovenia": "SI", "Lithuania": "LT", "Sweden": "SE", "Denmark": "DK",
    "Norway": "NO", "Finland": "FI", "Switzerland": "CH", "Belgium": "BE",
    "Austria": "AT", "Luxembourg": "LU", "Czech Republic": "CZ", "Czechia": "CZ",
    "Cyprus": "CY", "Israel": "IL", "United Arab Emirates": "AE", "Saudi Arabia": "SA",
    "India": "IN", "Singapore": "SG", "Japan": "JP", "South Korea": "KR", "Korea": "KR",
    "China": "CN", "Hong Kong": "HK", "Taiwan": "TW", "Australia": "AU",
    "New Zealand": "NZ", "Indonesia": "ID", "Philippines": "PH", "Thailand": "TH",
    "Vietnam": "VN", "Malaysia": "MY", "South Africa": "ZA", "Nigeria": "NG",
    "Kenya": "KE", "Egypt": "EG", "Turkey": "TR",
}

#: US state names, all meaning the US. Georgia is left out because it's
#: also a country (GE); use a company's country_hints for "Georgia".
US_STATE_NAMES: tuple[str, ...] = (
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "District of Columbia", "Florida", "Hawaii",
    "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey",
    "New Mexico", "New York State", "North Carolina", "North Dakota", "Ohio",
    "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina",
    "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia",
    "Washington", "West Virginia", "Wisconsin", "Wyoming",
)

#: Canadian province and territory names, all meaning Canada.
CANADIAN_PROVINCE_NAMES: tuple[str, ...] = (
    "Alberta", "British Columbia", "Manitoba", "New Brunswick",
    "Newfoundland and Labrador", "Northwest Territories", "Nova Scotia",
    "Nunavut", "Ontario", "Prince Edward Island", "Quebec", "Québec",
    "Saskatchewan", "Yukon",
)

#: Postal codes for US states (plus DC), used only with state_codes=True.
US_STATE_CODES: frozenset[str] = frozenset(
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS "
    "MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split()
)

#: Postal codes for Canadian provinces and territories, used only with state_codes=True.
CANADIAN_PROVINCE_CODES: frozenset[str] = frozenset(
    "AB BC MB NB NL NS NT NU ON PE QC SK YT".split()
)

#: Abbreviations matched only in capitals ("Remote US", "London, U.K.").
COUNTRY_ABBREVIATIONS: dict[str, str] = {
    "US": "US", "U.S.": "US", "USA": "US",
    "UK": "GB", "U.K.": "GB",
    "UAE": "AE",
}

#: Every name matched in any case: countries, US states and Canadian provinces.
_ALL_NAMES: dict[str, str] = {
    **COUNTRY_NAMES,
    **{state: "US" for state in US_STATE_NAMES},
    **{province: "CA" for province in CANADIAN_PROVINCE_NAMES},
}

#: A two-letter code at the very end of a location, after a comma ("Tempe, AZ")
#: or a spaced dash ("Remote - TX"). Capitals only; dots allowed ("B.C.").
_STATE_CODE_RE = re.compile(r"(?:,|\s-)\s*((?:[A-Z]\.?){2})\s*$")

def _whole_words(words: Iterable[str], flags: int = 0) -> re.Pattern[str] | None:
    """One regex matching any of `words` as whole words, longest first so
    "United States of America" wins over "United States", and "New Mexico"
    over "Mexico".

    "Whole word" means not directly next to a letter or digit. This is used
    instead of \\b so that words ending in punctuation ("U.S.") still match
    at the end of the text, where \\b would find no boundary."""
    alternatives = sorted({w for w in words if w}, key=len, reverse=True)
    if not alternatives:
        return None
    return re.compile(r"(?<!\w)(" + "|".join(map(re.escape, alternatives)) + r")(?!\w)", flags)

_NAMES_RE = _whole_words(_ALL_NAMES, re.IGNORECASE)
_NAMES = {name.lower(): code for name, code in _ALL_NAMES.items()}
_ABBREVIATIONS_RE = _whole_words(COUNTRY_ABBREVIATIONS)

def _state_code_country(text: str) -> list[str]:
    """["US"] or ["CA"] if `text` ends in a US state or Canadian province
    code ("Tempe, AZ", "Remote - TX", "Vancouver, B.C."); otherwise []."""
    match = _STATE_CODE_RE.search(text)
    if not match:
        return []
    code = match.group(1).replace(".", "")
    if code in US_STATE_CODES:
        return ["US"]
    if code in CANADIAN_PROVINCE_CODES:
        return ["CA"]
    return []

class CountryFinder:
    """Finds countries in location text. `hints` adds a source's own matches,
    e.g. {"Toronto": "CA", "SF": "US"} (whole words, any case). With
    `state_codes`, a location that matched nothing else may still be read as
    "City, ST" (see the module docstring). Build one per refresh and reuse it
    for every job, since building compiles the patterns."""

    def __init__(self, hints: Mapping[str, str] | None = None, state_codes: bool = False):
        self._hints = {text.lower(): code for text, code in (hints or {}).items()}
        self._hints_re = _whole_words(hints or {}, re.IGNORECASE)
        self._state_codes = state_codes

    def find(self, texts: Iterable[str]) -> list[str]:
        """ISO codes for every country found in `texts`, sorted, no duplicates."""
        codes: list[str] = []
        for text in texts:
            found: list[str] = []
            if _NAMES_RE:
                found += [_NAMES[m.lower()] for m in _NAMES_RE.findall(text)]
            if _ABBREVIATIONS_RE:
                found += [COUNTRY_ABBREVIATIONS[m] for m in _ABBREVIATIONS_RE.findall(text)]
            if self._hints_re:
                found += [self._hints[m.lower()] for m in self._hints_re.findall(text)]
            # State codes are a last resort, so a name or hint always wins
            # ("Hyderabad, IN" stays India when Hyderabad is hinted).
            if not found and self._state_codes:
                found = _state_code_country(text)
            codes += found
        return normalize_countries(codes)