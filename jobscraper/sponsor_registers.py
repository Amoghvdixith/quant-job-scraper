"""Government lists of employers that can sponsor work visas.

- UK: Home Office register of licensed sponsors (Skilled Worker route)
- US: USCIS H-1B Employer Data Hub (employers with approved H-1B petitions)
- Netherlands: IND public register of recognised sponsors (highly skilled migrants)

`python -m jobscraper.sponsor_registers` downloads them into data/sponsor_registers.json
(the weekly "Find careers sites" workflow does this). The scraper only reads that file.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)
FILE = Path(__file__).resolve().parent.parent / "data" / "sponsor_registers.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"}

_SUFFIXES = re.compile(
    r"\b(limited|ltd|plc|llp|lp|inc|incorporated|llc|l l c|group|holdings?|uk|usa|us|international|the|co|company|"
    r"corporation|corp|services|bank|banking|n a|na|ag|sa|se|nv|n v|bv|b v|gmbh|ltda|pte|branch|of america|and|amp)\b")
COUNTRIES = ("UK", "US", "NL")


def clean(name: str) -> str:
    """Company name reduced to a comparable key: "JPMORGAN CHASE BANK, N.A." -> "jpmorganchase"."""
    name = (name or "").lower().replace("&", " and ")
    name = re.sub(r"\([^)]*\)", " ", name)
    name = re.sub(r"[^a-z0-9 ]+", " ", name)
    name = _SUFFIXES.sub(" ", name)
    return re.sub(r"\s+", "", name)


def _uk() -> set[str]:
    page = requests.get("https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers",
                        headers=HEADERS, timeout=60).text
    link = re.search(r'href="(https://assets\.publishing\.service\.gov\.uk/[^"]+\.csv)"', page).group(1)
    rows = csv.DictReader(io.StringIO(requests.get(link, headers=HEADERS, timeout=300).text))
    return {clean(r.get("Organisation Name", "")) for r in rows
            if "Skilled Worker" in (r.get("Route") or "") or "Global Business Mobility" in (r.get("Route") or "")}


def _us() -> set[str]:
    hub = "https://www.uscis.gov/tools/reports-and-studies/h-1b-employer-data-hub"
    page = requests.get(hub, headers=HEADERS, timeout=60).text
    links = re.findall(r'href="([^"]+\.csv)"', page)
    if not links:
        page = requests.get(hub + "/h-1b-employer-data-hub-files", headers=HEADERS, timeout=60).text
        links = re.findall(r'href="([^"]+\.csv)"', page)
    names: set[str] = set()
    for link in links[:2]:  # the two most recent fiscal years
        url = link if link.startswith("http") else "https://www.uscis.gov" + link
        text = requests.get(url, headers=HEADERS, timeout=300).content.decode("utf-8", "ignore")
        reader = csv.DictReader(io.StringIO(text), delimiter="\t" if text.count("\t") > text.count(",") else ",")
        for row in reader:
            employer = next((v for k, v in row.items() if k and "employer" in k.lower() and v), "")
            approvals = sum(_int(v) for k, v in row.items() if k and "approv" in k.lower())
            if employer and approvals > 0:
                names.add(clean(employer))
    return names


def _int(v) -> int:
    try:
        return int(str(v).replace(",", "").strip() or 0)
    except ValueError:
        return 0


def _nl() -> set[str]:
    url = "https://ind.nl/en/public-register-recognised-sponsors/public-register-regular-labour-and-highly-skilled-migrants"
    soup = BeautifulSoup(requests.get(url, headers=HEADERS, timeout=60).text, "html.parser")
    names = {clean(td.get_text(" ", strip=True)) for tr in soup.select("table tr") for td in tr.select("td")[:1]}
    return {n for n in names if n}


def update() -> None:
    old = json.loads(FILE.read_text()) if FILE.exists() else {}
    out = {}
    for country, fn in (("UK", _uk), ("US", _us), ("NL", _nl)):
        try:
            names = sorted(n for n in fn() if len(n) >= 3)
            if len(names) < 100:
                raise ValueError(f"only {len(names)} names")
            out[country] = names
            log.info("%s sponsor register: %d employers", country, len(names))
        except Exception as e:  # keep last week's list if a download fails
            log.warning("%s sponsor register failed (%s); keeping previous list", country, e)
            out[country] = old.get(country, [])
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(out))


class SponsorRegisters:
    def __init__(self) -> None:
        data = json.loads(FILE.read_text()) if FILE.exists() else {}
        self.lists = {c: set(data.get(c, [])) for c in COUNTRIES}
        self.loaded = {c: bool(self.lists[c]) for c in COUNTRIES}

    def _on(self, country: str, key: str) -> bool:
        names = self.lists[country]
        if key in names:
            return True
        # "goldmansachs" should match "goldmansachsandco" etc.
        return len(key) >= 6 and any(n.startswith(key) for n in names if len(n) - len(key) <= 12)

    def status(self, company: str, location: str) -> str:
        """Which registers list this employer, relative to where the job is."""
        key = clean(company)
        if len(key) < 3:
            return ""
        on = [c for c in COUNTRIES if self.lists[c] and self._on(c, key)]
        if not on:
            return ""
        here = country_of(location)
        if here in on:
            return f"Yes ({here} register)"
        return f"Sponsors in {'/'.join(on)}"


_UK = re.compile(r"united kingdom|\buk\b|england|scotland|wales|northern ireland|london|manchester|birmingham|"
                 r"edinburgh|glasgow|leeds|bristol|cardiff|belfast|reading|cambridge|oxford|liverpool", re.I)
_US = re.compile(r"united states|\busa\b|\bu\.s\.|new york|chicago|boston|san francisco|houston|dallas|charlotte|"
                 r"jersey city|greenwich|stamford|miami|atlanta|philadelphia|seattle|los angeles", re.I)
_US_STATE = re.compile(
    r",\s*(AL|AK|AZ|AR|CA|CO|CT|DE|DC|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|"
    r"NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b")
_NL = re.compile(r"netherlands|amsterdam|rotterdam|utrecht|the hague|den haag|eindhoven", re.I)


def country_of(location: str) -> str:
    loc = location or ""
    if _UK.search(loc):
        return "UK"
    if _NL.search(loc):
        return "NL"
    if _US.search(loc) or _US_STATE.search(loc):
        return "US"
    return ""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    update()
