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
    """A place ending in "$" only counts as the last part of the location (the country),
    so "Amman, Jordan" is excluded but "Jordan, MN" is not."""
    loc = (location or "").lower()
    last = loc.split(",")[-1].strip()
    for place in excluded:
        if place.endswith("$"):
            if last == place[:-1].lower():
                return True
        elif re.search(rf"\b{re.escape(place.lower())}\b", loc):
            return True
    return False


_YEARS = re.compile(r"(\d{1,2})\s*\+?\s*(?:(?:-|to|–)\s*\d{1,2}\s*\+?\s*)?(?:years?|yrs?)\b", re.I)
_EXPERIENCE = re.compile(r"experience|exp\b|background|track record", re.I)


def years_required(description: str) -> int | None:
    """Smallest 'N years (of) experience' figure in the description, if any."""
    text = description or ""
    found = []
    for m in _YEARS.finditer(text):
        n = int(m.group(1))
        window = text[max(0, m.start() - 60): m.end() + 60]
        if 1 <= n <= 20 and _EXPERIENCE.search(window) and not re.search(r"years? old|year (?:programme|program|contract)", window, re.I):
            found.append(n)
    return min(found) if found else None


# Recruitment agencies: real postings, but the hiring firm is hidden and they often
# re-post the same role many times.
_RECRUITER_WORDS = re.compile(
    r"\b(recruit\w*|staffing|talent|headhunt\w*|search|selection|executive search|resourcing|appointments|"
    r"personnel|employment|careers? agency|hr services)\b", re.I)
_RECRUITERS = {
    "oxford knight", "selby jennings", "mondrian alpha", "gravitas recruitment group", "hays", "michael page",
    "page executive", "robert walters", "robert half", "harnham", "morgan mckinley", "huxley", "durlston partners",
    "hunter bond", "nls", "anson mccade", "caspian one", "pinpoint partners", "odyssey search partners",
    "harrington starr", "joseph harry", "eka finance", "westbourne partners", "venture search", "paragon alpha",
    "stanton chase", "phaidon international", "jefferson frank", "glocomms", "hamlyn williams", "korn ferry",
    "goodman masson", "barclay simpson", "marks sattin", "hudson shribman", "investigo", "sthree",
    "fintech recruiters", "aston carter", "randstad", "adecco", "manpower", "kforce", "teksystems",
    "options group", "proactive appointments", "radley james", "ipsos jobs", "jobot", "cyber talent",
    "dlc partners", "tiro partners", "bruin", "quant capital", "vertex search", "trireme", "ascension",
}


def is_recruiter(company: str) -> bool:
    c = re.sub(r"[^a-z0-9 ]+", " ", (company or "").lower())
    c = re.sub(r"\s+", " ", c).strip()
    return any(c == r or c.startswith(r + " ") for r in _RECRUITERS) or bool(_RECRUITER_WORDS.search(c))


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


# Professional qualifications. Acronyms are matched case-sensitively ("CA" is also a US state,
# so it only counts next to words like "qualified" or another qualification).
_QUAL_ACRONYMS = r"ACA|ACCA|CIMA|CPA|CFA|FRM|PRM|CQF|CAIA|ICAEW|ICAS|CISA|CERA|CIPFA"
_QUALIFICATION = re.compile(
    rf"\b(?:{_QUAL_ACRONYMS})\b"
    r"|\bCA\s*(?:[-/,&]|and|or)\s*(?:ACA|ACCA|CIMA|CPA|CFA)\b|\b(?:ACA|ACCA|CIMA|CPA|CFA)\s*(?:[/,&]|or|and)\s*CA\b"
    r"|\b(?:qualified|newly[- ]qualified|part[- ]qualified)\s+CA\b|\bCA\s+(?:qualified|qualification|certified)\b"
    r"|(?i:\bchartered\s+(?:accountant|accountancy|financial\s+analyst|certified\s+accountant|management\s+accountant)"
    r"|\bcertified\s+public\s+accountant|\bfinancial\s+risk\s+manager|\bcertificate\s+in\s+quantitative\s+finance"
    r"|\bfellow(?:ship)?\s+of\s+the\s+(?:institute|society)\s+of\s+actuaries|\bqualified\s+actuary|\bIFoA\b"
    r"|\bprofessional\s+(?:accounting\s+)?qualification|\baccountancy\s+qualification|\bcharterholder)"
)
# Graduate schemes often pay for the exams: "we will support you to study for the ACA".
_QUAL_TRAINING = re.compile(
    r"support(?:s|ed)?\s+(?:you|your|for)|sponsor(?:s|ed)?\s+(?:you|your)|study(?:ing)?\s+(?:for|towards)|"
    r"fund(?:s|ed|ing)?\s+(?:your|the)|pay(?:s)?\s+for|opportunity\s+to\s+(?:gain|obtain|achieve|pursue|study|complete)|"
    r"(?:will|you'll|you\s+will)\s+(?:gain|obtain|achieve|complete|work\s+towards|study)|work\s+towards|"
    r"training\s+(?:contract|programme|program)|exam\s+support|study\s+leave|tuition",
    re.I,
)


def qualification_asked(description: str, title: str = "") -> str:
    """The professional qualification the posting asks for (e.g. "CFA"), or "" if none.
    Mentions where the employer offers to train you for it don't count."""
    m = _QUALIFICATION.search(title or "")
    if m:
        return m.group(0)
    text = description or ""
    for sentence in re.split(r"(?<=[.;!?•·▪●])\s+|\s[-*]\s|\n", text):
        m = _QUALIFICATION.search(sentence)
        if m and not _QUAL_TRAINING.search(sentence):
            return re.sub(r"\s+", " ", m.group(0))
    return ""
