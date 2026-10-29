"""Relevance, seniority, location, experience and visa sponsorship checks."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Job

# Words ignored when matching a keyword against a job title.
GENERIC = {
    "analyst", "associate", "junior", "graduate", "grad", "entry", "level", "trainee",
    "intern", "internship", "officer", "specialist", "the", "and", "of", "for", "in",
    "programme", "program", "scheme", "i", "ii",
}
# Different spellings that should count as the same word.
SYNONYMS = {
    "quantitative": "quant", "quants": "quant",
    "commodity": "commodities",
    "derivative": "derivatives",
    "controller": "control", "controllers": "control",
    "valuations": "valuation",
}


# One-word keywords that only count when the full keyword phrase is in the title.
LOOSE_WORDS = {"credit", "options", "rates", "bond", "margin", "collateral", "exposure", "desk",
               "pricing", "valuation", "trading", "volatility"}


def tokens(text: str) -> list[str]:
    text = (text or "").lower().replace("p&l", " pnl ").replace("p & l", " pnl ")
    words = re.findall(r"[a-z0-9]+", text)
    return [SYNONYMS.get(w, w) for w in words]


@dataclass
class RoleMatcher:
    roles: list[dict]

    def __post_init__(self) -> None:
        self._rules: list[tuple[frozenset[str], dict, str]] = []
        for role in self.roles:
            for kw in role["keywords"]:
                core = frozenset(t for t in tokens(kw) if t not in GENERIC)
                if core:
                    self._rules.append((core, role, kw))
        # Most specific keywords first, so "Market Risk Analyst" wins over "Risk Analyst".
        self._rules.sort(key=lambda r: (-len(r[0]), r[1]["tier"]))

    def match(self, title: str) -> tuple[dict, str] | None:
        title_list = tokens(title)
        title_tokens = set(title_list)
        title_text = " " + " ".join(title_list) + " "
        for core, role, kw in self._rules:
            if not core <= title_tokens:
                continue
            # A few one-word keywords ("Credit Analyst", "Options Analyst") are too loose on
            # their own, so for those the whole phrase has to appear in the title.
            if len(core) == 1 and core <= LOOSE_WORDS and f" {' '.join(tokens(kw))} " not in title_text:
                continue
            return role, kw
        return None


def is_senior(title: str, senior_words: list[str]) -> bool:
    t = " " + " ".join(re.findall(r"[a-z0-9]+", title.lower())) + " "
    return any(f" {w} " in t for w in senior_words)


def is_excluded_location(location: str, excluded: list[str]) -> bool:
    loc = (location or "").lower()
    return any(re.search(rf"\b{re.escape(place.lower())}\b", loc) for place in excluded)


_YEARS = re.compile(
    r"(?:minimum of |at least |min\.? )?(\d{1,2})\s*(?:\+|plus)?\s*(?:-|to|–)?\s*(\d{1,2})?\s*\+?\s*"
    r"(?:years?|yrs?)(?:'|’)?\s*(?:of\s+)?(?:relevant\s+|professional\s+|work\s+|industry\s+|proven\s+)?"
    r"(?:experience|exp\b)",
    re.I,
)


def years_required(description: str) -> int | None:
    """Smallest 'N years experience' figure in the description, if any."""
    found = [int(m.group(1)) for m in _YEARS.finditer(description or "") if int(m.group(1)) <= 20]
    return min(found) if found else None


_NO_SPONSOR = [
    r"(?:no|not|n't|unable to|cannot|can ?not|will not|won't|do not|does not|don't|doesn't|are not able to|is not able to|aren't able to)"
    r"\s+(?:\w+\s+){0,4}(?:offer|provide|support|sponsor|consider)\w*\s+(?:\w+\s+){0,3}(?:visa|sponsor|work permit)",
    r"(?:visa |immigration |work )?sponsorship (?:is |will )?(?:not|unavailable|isn't)",
    r"not (?:be )?(?:able|eligible) (?:to|for) (?:\w+\s+){0,3}sponsor",
    r"without (?:the )?(?:need for |requiring |requirement for )?(?:\w+\s+){0,2}sponsorship",
    r"must (?:already )?(?:have|hold|possess) (?:the |a |full |valid |existing |current )*(?:right|authori[sz]ation|eligibility|permission) to work",
    r"(?:only|unable to) consider (?:\w+\s+){0,4}(?:right to work|work authori[sz]ation|citizens)",
    r"(?:us|u\.s\.) citizenship (?:is )?required",
    r"no (?:visa )?sponsorship",
    r"(?:not|n't|cannot|unable to) (?:\w+\s+){0,2}sponsor",
    r"sponsorship (?:is )?not (?:available|offered|provided|possible)",
]
_YES_SPONSOR = [
    r"(?:visa|immigration|work permit|h-?1b|skilled worker) sponsorship (?:is |will be |can be )?(?:available|provided|offered|possible|supported)",
    r"sponsorship (?:is |will be |can be )?(?:available|provided|offered|considered)",
    r"(?:we|will|can|able to|happy to|willing to|are able to) (?:\w+\s+){0,2}sponsor",
    r"(?:offer|provide|support)s? (?:\w+\s+){0,3}(?:visa|sponsorship|work permit)",
    r"open to (?:visa )?sponsorship",
    r"sponsorship (?:for|of) (?:the )?(?:right|visa|work)",
    r"relocation (?:and|&) visa",
    r"visa (?:support|assistance)",
]


def sponsorship(description: str) -> tuple[str, str]:
    """Returns ("Yes" | "No" | "Not stated", the sentence that decided it)."""
    text = re.sub(r"\s+", " ", (description or "").lower())
    for pattern in _NO_SPONSOR:
        m = re.search(pattern, text)
        if m:
            return "No", _snippet(text, m)
    for pattern in _YES_SPONSOR:
        m = re.search(pattern, text)
        if m:
            return "Yes", _snippet(text, m)
    return "Not stated", ""


def _snippet(text: str, m: re.Match) -> str:
    return text[max(0, m.start() - 60): m.end() + 60].strip()
