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
    # Filled in by the pipeline
    role_id: str = ""
    role_title: str = ""
    category: str = ""
    tier: int = 0
    sponsorship: str = "Not stated"
    sponsorship_evidence: str = ""
    years_required: int | None = None
    uk_licensed_sponsor: str = ""
    target_firm: str = ""
    first_seen: str = ""
    sources: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{_norm(self.title)}|{_norm(self.company)}"

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
