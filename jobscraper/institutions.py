"""Your target list of financial institutions (institutions.csv)."""
from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_SUFFIXES = re.compile(
    r"\b(plc|ltd|limited|llp|lp|llc|inc|corp|corporation|group|holdings|the|co|company|& co|sa|se|ag|nv|n a|uk|"
    r"international|management|partners|asset management|investment management|investments?|capital|financial|"
    r"services|securities|bank|banking)\b"
)


def norm(name: str) -> str:
    name = (name or "").lower().replace("&", " and ").replace("’", "'")
    name = re.sub(r"[^a-z0-9 ]+", " ", name)
    name = _SUFFIXES.sub(" ", name)
    return re.sub(r"\s+", " ", name).strip()


@lru_cache(maxsize=1)
def load() -> list[dict]:
    with open(ROOT / "institutions.csv", newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r.get("Institution")]
    seen, out = set(), []
    for r in rows:
        key = norm(r["Institution"])
        if key and key not in seen:
            seen.add(key)
            out.append({"name": r["Institution"].strip(), "sector": r.get("Sector", "").strip(), "key": key})
    return out


@lru_cache(maxsize=4096)
def match(company: str) -> str:
    """Name of the target institution this employer belongs to, or ""."""
    c = norm(company)
    if not c:
        return ""
    best = ""
    for inst in load():
        k = inst["key"]
        if c == k or re.search(rf"(^| ){re.escape(k)}( |$)", c) and len(k) >= 3:
            if len(k) > len(norm(best)):
                best = inst["name"]
    return best
