"""Government lists of employers that can sponsor work visas.

- UK: Home Office register of licensed sponsors (Skilled Worker route)
- US: USCIS H-1B Employer Data Hub (employers with approved H-1B petitions)
- Netherlands: IND public register of recognised sponsors (highly skilled migrants)

`python -m jobscraper.sponsor_registers` downloads them into data/sponsor_registers.json
(the weekly "Find careers sites" workflow does this). The scraper only reads that file.

data/sponsor_details.json keeps what each list says beyond "on the list":
- UK: licence rating and visa routes from the register.
- UK numbers: certificates of sponsorship (CoS) each firm was assigned per year, from Home Office
  Freedom of Information releases listed in UK_COS_SOURCES (FOI 2025/12841 covers every sponsor,
  2021-2024, Skilled Worker and Global Business Mobility). One CoS is one sponsored job offer.
  The Home Office hides figures from 1 to 4 ("*"). Saved in data/uk_cos.json.
- US: H-1B petitions approved per fiscal year, split into new employment ("initial") and
  extensions or transfers ("continuing"). Each approval is one worker's petition.
- Netherlands: the IND register publishes names only.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import re
from bisect import bisect_left
from pathlib import Path

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)
FILE = Path(__file__).resolve().parent.parent / "data" / "sponsor_registers.json"
DETAILS_FILE = FILE.with_name("sponsor_details.json")
UK_COS_FILE = FILE.with_name("uk_cos.json")
FOI_DIR = FILE.parent / "foi"
# Home Office FOI releases of certificates of sponsorship assigned per sponsor. Add newer ones here
# (e.g. a 2025 release) and the next update picks them up; a later release wins for the same year.
UK_COS_SOURCES = [
    {
        "ref": "Home Office FOI 2025/12841",
        "file": "FOI 2025 12841 Annex.xlsx",
        "page": "https://www.whatdotheyknow.com/request/request_for_certificate_of_spons_2",
        "url": "https://www.whatdotheyknow.com/request/request_for_certificate_of_spons_2/response/3258743/"
               "attach/4/FOI%202025%2012841%20J%20Reddy%20Annex.xlsx",
    },
]
SUPPRESSED = -1  # the Home Office's "*": between 1 and 4
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"}

_SUFFIXES = re.compile(
    r"\b(limited|ltd|plc|llp|lp|inc|incorporated|llc|l l c|group|holdings?|uk|usa|us|international|the|co|company|"
    r"corporation|corp|services|bank|banking|national association|n a|na|ag|sa|se|nv|n v|bv|b v|gmbh|ltda|pte|branch|of america|and|amp)\b")
COUNTRIES = ("UK", "US", "NL")


def clean(name: str) -> str:
    """Company name reduced to a comparable key: "JPMORGAN CHASE BANK, N.A." -> "jpmorganchase"."""
    name = (name or "").lower().replace("&", " and ")
    name = re.sub(r"\([^)]*\)", " ", name)
    name = re.sub(r"[^a-z0-9 ]+", " ", name)
    name = _SUFFIXES.sub(" ", name)
    return re.sub(r"\s+", "", name)


def _uk() -> tuple[set[str], dict[str, str]]:
    page = requests.get("https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers",
                        headers=HEADERS, timeout=60).text
    link = re.search(r'href="(https://assets\.publishing\.service\.gov\.uk/[^"]+\.csv)"', page).group(1)
    return parse_uk(requests.get(link, headers=HEADERS, timeout=300).text)


def parse_uk(text: str) -> tuple[set[str], dict[str, str]]:
    """(names on a work route, {name: "rating|route, route"}) from the register CSV."""
    names: set[str] = set()
    ratings: dict[str, str] = {}
    routes: dict[str, list[str]] = {}
    for r in csv.DictReader(io.StringIO(text)):
        route = (r.get("Route") or "").strip()
        if "Skilled Worker" not in route and "Global Business Mobility" not in route and "Scale-up" not in route:
            continue
        key = clean(r.get("Organisation Name", ""))
        if len(key) < 3:
            continue
        names.add(key)
        rating = _rating(r.get("Type & Rating") or "")
        if rating and (key not in ratings or rating.startswith("A")):
            ratings[key] = rating
        short = route.replace("Global Business Mobility: ", "GBM ")
        if short not in routes.setdefault(key, []):
            routes[key].append(short)
    return names, {k: f"{ratings.get(k, '')}|{', '.join(sorted(routes[k]))}" for k in names}


def _rating(text: str) -> str:
    """"Worker (A rating)" -> "A", "Worker (A (Premium))" -> "A (Premium)"."""
    m = re.search(r"\((.*)\)\s*$", text.strip())
    return m.group(1).replace(" rating", "").strip() if m else ""


def _us() -> tuple[set[str], dict[str, list]]:
    hub = "https://www.uscis.gov/tools/reports-and-studies/h-1b-employer-data-hub"
    page = requests.get(hub, headers=HEADERS, timeout=60).text
    links = re.findall(r'href="([^"]+\.csv)"', page)
    if not links:
        page = requests.get(hub + "/h-1b-employer-data-hub-files", headers=HEADERS, timeout=60).text
        links = re.findall(r'href="([^"]+\.csv)"', page)
    names: set[str] = set()
    counts: dict[str, dict[str, list[int]]] = {}
    for link in links[:2]:  # the two most recent fiscal years
        url = link if link.startswith("http") else "https://www.uscis.gov" + link
        parse_us(_decode(requests.get(url, headers=HEADERS, timeout=300).content), names, counts)
    return names, {k: sorted(([fy] + v for fy, v in by_year.items()), reverse=True) for k, by_year in counts.items()}


def _decode(raw: bytes) -> str:
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", "ignore")
    return raw.decode("utf-8-sig", "ignore")


def parse_us(text: str, names: set[str], counts: dict) -> None:
    """Adds employers with approved petitions to names, and {name: {fiscal year: [new, continuing]}} to counts.
    An employer has several rows (one per tax ID / office), so they are added up."""
    reader = csv.DictReader(io.StringIO(text), delimiter="\t" if text.count("\t") > text.count(",") else ",")
    for row in reader:
        row = {(k or "").strip().lower(): v for k, v in row.items()}
        employer = next((v for k, v in row.items() if "employer" in k and v), "")
        initial = sum(_int(v) for k, v in row.items() if "approv" in k and "initial" in k)
        continuing = sum(_int(v) for k, v in row.items() if "approv" in k and "continu" in k)
        if not employer or initial + continuing <= 0:
            continue
        key = clean(employer)
        names.add(key)
        fy = next((str(v).strip() for k, v in row.items() if "fiscal" in k and v), "")
        if fy:
            year = counts.setdefault(key, {}).setdefault(fy, [0, 0])
            year[0] += initial
            year[1] += continuing


def _int(v) -> int:
    try:
        return int(str(v).replace(",", "").strip() or 0)
    except ValueError:
        return 0


def parse_uk_cos(raw: bytes) -> dict:
    """{"years": [...], "SW": {name: [count per year]}, "GBM": {...}} from a Home Office FOI workbook.

    Each sheet has notes, then a header row "Organisation Name | 2021 | 2022 | ... | Grand Total",
    one row per sponsor, and a "Grand Total" row. Firms whose names reduce to the same key
    (e.g. "Barclays Bank PLC" and "Barclays Bank UK PLC") are added together."""
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    out: dict = {"years": []}
    for ws in wb.worksheets:
        route = "GBM" if "gbm" in ws.title.lower() or "mobility" in ws.title.lower() else "SW"
        name_col, year_cols = None, []
        table: dict[str, list[int]] = {}
        for row in ws.iter_rows(values_only=True):
            cells = ["" if v is None else str(v).strip() for v in row]
            if name_col is None:
                if "Organisation Name" in cells:
                    name_col = cells.index("Organisation Name")
                    year_cols = [(i, int(v)) for i, v in enumerate(cells) if re.fullmatch(r"20\d\d", v)]
                continue
            name = cells[name_col] if name_col < len(cells) else ""
            if not name or name.lower() == "grand total":
                continue
            key = clean(name)
            if len(key) < 3:
                continue
            counts = [_cos(cells[i]) if i < len(cells) else 0 for i, _ in year_cols]
            if key in table:
                table[key] = [_add(a, b) for a, b in zip(table[key], counts)]
            else:
                table[key] = counts
        if name_col is not None:
            out["years"] = [y for _, y in year_cols]
            out[route] = table
    return out


def _cos(v: str) -> int:
    if v == "*":
        return SUPPRESSED
    return _int(v)


def _add(a: int, b: int) -> int:
    if SUPPRESSED in (a, b):
        known = max(a, 0) + max(b, 0)
        return known + 1 if known else SUPPRESSED  # at least one more than the known part
    return a + b


def update_uk_cos(force: bool = False) -> None:
    """Builds data/uk_cos.json from the FOI workbooks. They don't change, so only when missing or new.

    Each workbook is read from data/foi/ when a copy is committed there (file name in "file"),
    otherwise downloaded. WhatDoTheyKnow serves GitHub's servers a web page instead of the file,
    so the committed copy is the reliable route. Raises if a source can't be read, so the
    problem solver records it."""
    have = json.loads(UK_COS_FILE.read_text()) if UK_COS_FILE.exists() else {}
    refs = [s["ref"] for s in UK_COS_SOURCES]
    if have.get("sources") == refs and not force:
        return
    merged: dict = {"sources": [], "source_pages": [], "years": [], "SW": {}, "GBM": {}}
    for src in UK_COS_SOURCES:
        try:
            data = parse_uk_cos(_foi_bytes(src))
            if len(data.get("SW", {})) < 1000:
                raise ValueError(f"only {len(data.get('SW', {}))} sponsors")
        except Exception as e:
            raise RuntimeError(f"UK CoS figures from {src['ref']} could not be read ({e}). "
                               f"Save the workbook from {src['page']} as data/foi/{src['file']}") from e
        _merge_years(merged, data)
        merged["sources"].append(src["ref"])
        merged["source_pages"].append(src["page"])
    UK_COS_FILE.write_text(json.dumps(merged, separators=(",", ":"), sort_keys=True))
    log.info("UK CoS figures: %d sponsors, years %s", len(merged["SW"]), merged["years"])


def _foi_bytes(src: dict) -> bytes:
    local = FOI_DIR / src["file"]
    if local.exists():
        return local.read_bytes()
    r = requests.get(src["url"], headers={**HEADERS, "Accept": "*/*"}, timeout=300)
    r.raise_for_status()
    if not r.content.startswith(b"PK"):
        raise ValueError(f"got {r.headers.get('content-type', 'a web page')} instead of the workbook")
    return r.content


def _merge_years(into: dict, data: dict) -> None:
    years = sorted(set(into["years"]) | set(data["years"]))
    for route in ("SW", "GBM"):
        table = {}
        for key in set(into.get(route, {})) | set(data.get(route, {})):
            old = dict(zip(into["years"], into.get(route, {}).get(key, [0] * len(into["years"]))))
            new = dict(zip(data["years"], data.get(route, {}).get(key, [])))
            # A later release wins for a year it covers.
            table[key] = [new[y] if y in new and key in data.get(route, {}) else old.get(y, 0) for y in years]
        into[route] = table
    into["years"] = years


def _nl() -> set[str]:
    url = "https://ind.nl/en/public-register-recognised-sponsors/public-register-regular-labour-and-highly-skilled-migrants"
    soup = BeautifulSoup(requests.get(url, headers=HEADERS, timeout=60).text, "html.parser")
    names = {clean(td.get_text(" ", strip=True)) for tr in soup.select("table tr") for td in tr.select("td")[:1]}
    return {n for n in names if n}


def update() -> None:
    old = json.loads(FILE.read_text()) if FILE.exists() else {}
    old_details = json.loads(DETAILS_FILE.read_text()) if DETAILS_FILE.exists() else {}
    out, details = {}, {}
    for country, fn in (("UK", _uk), ("US", _us), ("NL", _nl)):
        try:
            got = fn()
            names, extra = got if isinstance(got, tuple) else (got, {})
            names = sorted(n for n in names if len(n) >= 3)
            if len(names) < 100:
                raise ValueError(f"only {len(names)} names")
            out[country] = names
            if extra:
                details[country] = extra
            log.info("%s sponsor register: %d employers", country, len(names))
        except Exception as e:  # keep last week's list if a download fails
            log.warning("%s sponsor register failed (%s); keeping previous list", country, e)
            out[country] = old.get(country, [])
            if old_details.get(country):
                details[country] = old_details[country]
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(out))
    DETAILS_FILE.write_text(json.dumps(details, separators=(",", ":"), sort_keys=True))
    try:
        update_uk_cos()
    except Exception as e:
        log.warning("%s", e)


class SponsorRegisters:
    def __init__(self, data: dict | None = None, details: dict | None = None, uk_cos: dict | None = None) -> None:
        if data is None:
            data = json.loads(FILE.read_text()) if FILE.exists() else {}
        if details is None:
            details = json.loads(DETAILS_FILE.read_text()) if DETAILS_FILE.exists() else {}
        if uk_cos is None:
            uk_cos = json.loads(UK_COS_FILE.read_text()) if UK_COS_FILE.exists() else {}
        self.uk_cos = uk_cos
        self.lists = {c: set(data.get(c, [])) for c in COUNTRIES}
        self.loaded = {c: bool(self.lists[c]) for c in COUNTRIES}
        self.details = details

    def _on(self, country: str, key: str) -> bool:
        return self._find(country, key) is not None

    def _find(self, country: str, key: str) -> str | None:
        """The register's name for this employer, matched exactly or as a close prefix."""
        if key in self.lists[country]:
            return key
        # "goldmansachs" should match "goldmansachsandco" etc.
        if len(key) < 6:
            return None
        # A sorted copy, made on first use, so a prefix lookup is a binary search
        # instead of a scan of ~200k names.
        sorted_lists = self.__dict__.setdefault("_sorted", {})
        if country not in sorted_lists:
            sorted_lists[country] = sorted(self.lists[country])
        names = sorted_lists[country]
        i = bisect_left(names, key)
        while i < len(names) and names[i].startswith(key):
            if len(names[i]) - len(key) <= 12:
                return names[i]
            i += 1
        return None

    def _keys(self, company: str) -> list[str]:
        key = clean(company)
        if len(key) < 3:
            return []
        # NHS Jobs often writes "X NHS Trust" for the register's "X NHS Foundation Trust".
        return [key, key.replace("nhsfoundationtrust", "nhstrust"), key.replace("nhstrust", "nhsfoundationtrust")]

    def record(self, company: str) -> dict:
        """What the government lists say about this employer's sponsorship. Numbers only where published.

        {"uk": "Licensed sponsor (A rating): Skilled Worker, GBM Graduate Trainee" or "Not on the register",
         "us": "FY2025: 145 new + 320 extensions approved" or "No approved H-1B petitions found",
         "us_new": 145 or None, "nl": "Recognised sponsor" or ""}
        """
        cache = self.__dict__.setdefault("_record_cache", {})
        if company in cache:
            return cache[company]
        keys = self._keys(company)
        out = {"uk": "", "uk_cos": "", "uk_short": "", "us": "", "us_new": None, "nl": ""}

        def first(country):
            return next((m for k in keys if (m := self._find(country, k))), None) if self.lists[country] else None

        if self.loaded["UK"]:
            m = first("UK")
            if m:
                rating, _, routes = self.details.get("UK", {}).get(m, "|").partition("|")
                out["uk"] = "Licensed sponsor" + (f" ({rating} rating)" if rating else "") + \
                    (f": {routes}" if routes else "")
            else:
                out["uk"] = "Not on the register"
        if self.uk_cos.get("SW"):
            m = next((m for k in keys if (m := self._find_in(self.uk_cos["SW"], k))), None)
            out["uk_cos"], out["uk_short"] = self._uk_cos_text(m)
        if self.loaded["US"]:
            m = first("US")
            years = self.details.get("US", {}).get(m) if m else None
            if years:
                fy, new, cont = years[0]
                out["us"] = f"FY{fy}: {new:,} new + {cont:,} extensions approved"
                out["us_new"] = new
                if len(years) > 1:
                    out["us"] += f" (FY{years[1][0]}: {years[1][1]:,} new)"
            elif m:
                out["us"] = "Has approved H-1B petitions (numbers after the next weekly update)"
            else:
                out["us"] = "No approved H-1B petitions found"
        if self.loaded["NL"] and first("NL"):
            out["nl"] = "Recognised sponsor"
        cache[company] = out
        return out

    def _find_in(self, table: dict, key: str) -> str | None:
        if key in table:
            return key
        if len(key) < 6:
            return None
        sorted_keys = self.__dict__.setdefault("_sorted_cos", sorted(table))
        i = bisect_left(sorted_keys, key)
        while i < len(sorted_keys) and sorted_keys[i].startswith(key):
            if len(sorted_keys[i]) - len(key) <= 12:
                return sorted_keys[i]
            i += 1
        return None

    def _uk_cos_text(self, key: str | None) -> tuple[str, str]:
        """Full text with its source, and a short version for the email.
        ("2024: 1,515; 2021-2024 total: 6,026 (+ GBM/ICT 2,407) [Home Office FOI 2025/12841]",
         "1,515 CoS in 2024, 6,026 since 2021")"""
        years = self.uk_cos.get("years") or []
        src = "; ".join(self.uk_cos.get("sources") or [])
        if not years:
            return "", ""
        span = f"{years[0]}-{years[-1]}"
        if not key:
            # Could be a firm licensed after the figures end, or a name written differently: never "0".
            return f"Not found in the {span} figures [{src}]", ""
        sw = self.uk_cos["SW"][key]
        gbm = self.uk_cos.get("GBM", {}).get(key)
        text = f"{years[-1]}: {_fmt(sw[-1])}; {span} total: {_fmt_total(sw)}"
        if gbm and any(gbm):
            text += f" (+ GBM/ICT {_fmt_total(gbm)})"
        return f"{text} [{src}]", f"{_fmt(sw[-1])} CoS in {years[-1]}, {_fmt_total(sw)} since {years[0]}"

    def summary(self, company: str, location: str) -> str:
        """One short line for the email, about the job's own country where we can tell it."""
        if not company:
            return ""
        rec = self.record(company)
        here = country_of(location)
        parts = []
        if rec["uk"] and here in ("UK", ""):
            uk = "licensed sponsor" if rec["uk"].startswith("Licensed") else "not on register"
            if rec["uk_short"]:
                uk += f", {rec['uk_short']}"
            parts.append("UK: " + uk)
        if rec["us"] and here in ("US", ""):
            parts.append("US H-1B: " + (f"{rec['us_new']:,} new approvals" if rec["us_new"] is not None
                                       else "none found" if rec["us"].startswith("No") else "approved petitions"))
        if rec["nl"] and here in ("NL", ""):
            parts.append("NL: recognised sponsor")
        return "; ".join(parts)

    def status(self, company: str, location: str) -> str:
        """Which registers list this employer, relative to where the job is."""
        keys = self._keys(company)
        if not keys:
            return ""
        key = keys[0]
        cache = self.__dict__.setdefault("_cache", {})  # same answer for every job at this employer
        if key not in cache:
            cache[key] = [c for c in COUNTRIES if self.lists[c] and any(self._on(c, k) for k in set(keys))]
        on = cache[key]
        if not on:
            return ""
        here = country_of(location)
        if here in on:
            return f"Yes ({here} register)"
        return f"Sponsors in {'/'.join(on)}"


def _fmt(n: int | None) -> str:
    if n is None:
        return "?"
    return "1-4" if n == SUPPRESSED else f"{n:,}"


def _fmt_total(counts: list[int]) -> str:
    known = sum(max(c, 0) for c in counts)
    hidden = counts.count(SUPPRESSED)  # each hidden figure is at least 1
    return f"at least {known + hidden:,}" if hidden else f"{known:,}"


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
