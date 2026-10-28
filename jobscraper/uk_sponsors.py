"""Checks companies against the UK Home Office register of licensed visa sponsors."""
from __future__ import annotations

import csv
import io
import logging
import re

import requests

log = logging.getLogger(__name__)

REGISTER_PAGE = "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers"
_SUFFIXES = r"\b(limited|ltd|plc|llp|lp|inc|incorporated|llc|group|holdings|uk|international|the|co|company|corporation|corp|services|bank|n a|na|ag|sa|se)\b"


def _clean(name: str) -> str:
    name = re.sub(r"[^a-z0-9 ]+", " ", (name or "").lower())
    name = re.sub(_SUFFIXES, " ", name)
    return re.sub(r"\s+", " ", name).strip()


class UKSponsorRegister:
    def __init__(self) -> None:
        self.names: set[str] = set()
        try:
            page = requests.get(REGISTER_PAGE, timeout=30).text
            m = re.search(r'href="(https://assets\.publishing\.service\.gov\.uk/[^"]+\.csv)"', page)
            if not m:
                raise ValueError("CSV link not found on register page")
            rows = csv.DictReader(io.StringIO(requests.get(m.group(1), timeout=120).text))
            for row in rows:
                if "Skilled Worker" in (row.get("Route") or "") or "Worker" in (row.get("Type & Rating") or ""):
                    cleaned = _clean(row.get("Organisation Name", ""))
                    if len(cleaned) >= 3:
                        self.names.add(cleaned)
            log.info("Loaded %d UK licensed sponsors", len(self.names))
        except Exception as e:
            log.warning("Could not load UK sponsor register: %s", e)

    def check(self, company: str, location: str) -> str:
        if not self.names or not company:
            return ""
        if not re.search(r"united kingdom|\buk\b|england|scotland|wales|london|manchester|birmingham|edinburgh|glasgow|leeds|bristol", location.lower()):
            return ""
        return "Yes" if _clean(company) in self.names else "Not found"
