from __future__ import annotations

import re
from urllib.parse import quote
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
    experience: str | None = None  # wording that asks for work experience; None = not checked yet
    remote: bool = False
    government: str = ""  # "NHS" or "Civil Service" for UK public-sector jobs
    qualification: str | None = None  # qualification the posting asks for, e.g. "CFA"; None = not checked yet
    employer_sponsor: str = ""
    # Filled in by main.py from the government lists (see sponsor_registers.SponsorRegisters.record)
    uk_licence: str = ""
    uk_sponsored: str = ""   # certificates of sponsorship per year, with its source
    us_h1b: str = ""         # H-1B petitions approved, with fiscal year
    sponsor_summary: str = ""
    target_firm: str = ""
    recruiter: bool = False
    description_checked: bool = False
    first_seen: str = ""
    sources: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        # Country included so the same title at the same firm in London and New York stays two jobs.
        from .sponsor_registers import country_of
        return f"{_norm(self.title)}|{_company_key(self.company)}|{country_of(self.location)}"

    @property
    def graduate_scheme(self) -> bool:
        from .filters import is_graduate_scheme
        return self.role_id == "GS" or is_graduate_scheme(self.title)

    @property
    def internship(self) -> bool:
        from .filters import is_internship
        return self.role_id == "INT" or is_internship(self.title)

    @property
    def apply_link(self) -> str:
        """Where to apply: the employer's own page when we found one, otherwise the listing."""
        return self.apply_url or self.url

    def tailor_link(self, max_len: int = 2000) -> str:
        """Link that opens claude.ai with a cv-tailoring request for this job already typed in.

        Includes as much of the description as fits in max_len (Excel ignores hyperlinks longer
        than about 2,000 characters). Jobs loaded from data/jobs.json have no description, so
        those links carry only the title, company, location and job link.
        """
        return self._claude_link(
            "/cv-tailoring Use my cv-tailoring skill to tailor my CV to this job.", max_len)

    def assist_apply_link(self, max_len: int = 2000) -> str:
        """Link that opens claude.ai with an apply-assistant request for this job typed in.

        The apply-assistant skill tailors the CV, then uses Claude in Chrome to fill the
        application form from the apply profile and stops before Submit. Nothing is sent
        until the person presses send in Claude, and nothing is submitted until they press
        Submit on the employer's form.
        """
        return self._claude_link(
            "/apply-assistant Use my apply-assistant skill to help me apply for this job. "
            "Tailor my CV first, then fill the application form in Chrome and stop before Submit.",
            max_len)

    def _claude_link(self, request: str, max_len: int) -> str:
        head = (f"{request}\n"
                f"Job title: {self.title}\nCompany: {self.company}\nLocation: {self.location}\n"
                f"Job ad: {self.apply_link}")
        if self.url and self.url != self.apply_link:
            head += f"\nListing: {self.url}"
        link = _CLAUDE_NEW + quote(head, safe="")
        desc = re.sub(r"\s+", " ", self.description or "").strip()
        if desc:
            prefix = "\n\nJob description (from the listing, may be cut short):\n"
            room = max_len - len(link) - len(quote(prefix, safe="")) - len(quote("...", safe=""))
            # Each character can grow up to 9 when encoded; trim until it fits.
            n = min(len(desc), max(room, 0))
            while n > 200 and len(quote(desc[:n], safe="")) > room:
                n = int(n * 0.8)
            if n > 200:
                cut = desc[:n] + ("..." if n < len(desc) else "")
                extra = quote(prefix + cut, safe="")
                if len(link) + len(extra) <= max_len:
                    link += extra
        return link

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


_CLAUDE_NEW = "https://claude.ai/new?q="


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
