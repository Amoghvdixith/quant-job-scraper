from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date


@dataclass
class Job:
    source: str
    title: str
    company: str
    location: str
    url: str
    posted: date | None = None
    description: str = ""
    search_term: str = ""
    # Employer's own application page, when the listing points elsewhere (e.g. LinkedIn "Apply on company website").
    apply_url: str = ""
    easy_apply: bool | None = None  # LinkedIn only: applied for on LinkedIn itself
    # Filled in by the pipeline
    role_id: str = ""
    role_title: str = ""
    category: str = ""
    tier: int = 0
    sponsorship: str = "Not stated"
    sponsorship_evidence: str = ""
    years_required: int | None = None
    qualification: str | None = None  # qualification the posting asks for, e.g. "CFA"; None = not checked yet
    employer_sponsor: str = ""
    target_firm: str = ""
    recruiter: bool = False
    description_checked: bool = False
    first_seen: str = ""
    sources: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{_norm(self.title)}|{_company_key(self.company)}"

    @property
    def apply_link(self) -> str:
        """Where to apply: the employer's own page when we found one, otherwise the listing."""
        return self.apply_url or self.url

    @property
    def apply_on(self) -> str:
        if self.apply_url and self.apply_url != self.url:
            return "Employer website"
        if self.source.startswith("Careers site"):
            return "Employer website"
        if self.easy_apply:
            return "LinkedIn Easy Apply"
        if self.easy_apply is False:
            return "Employer website (via LinkedIn)"
        return self.source

    def to_dict(self) -> dict:
        d = asdict(self)
        d["posted"] = self.posted.isoformat() if self.posted else None
        d["description"] = ""  # descriptions are not stored, only what we derived from them
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Job":
        d = dict(d)
        d["posted"] = date.fromisoformat(d["posted"]) if d.get("posted") else None
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


_COMPANY_NOISE = re.compile(
    r"\b(group|holdings?|plc|ltd|limited|llp|llc|inc|corp|corporation|company|co|bank|banking|"
    r"international|securities|the|and)\b")


def _company_key(name: str) -> str:
    """Same employer written differently ("JPMorgan Chase" / "JPMorganChase", "ABN AMRO Bank N.V." / "ABN AMRO NL")."""
    words = _COMPANY_NOISE.sub(" ", _norm(name)).split()
    long_words = [w for w in words if len(w) > 2] or words
    return "".join(long_words)
