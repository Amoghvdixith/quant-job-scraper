"""Finds which hiring platform each institution in institutions.csv uses.

Writes data/careers_sites.json. Entries in careers_sites_manual.yaml always win,
so a wrong or missing guess can be fixed by hand.

    python -m jobscraper.discover_careers
"""
from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import yaml

from . import institutions
from .http import session

log = logging.getLogger("discover")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "careers_sites.json"
MANUAL = ROOT / "careers_sites_manual.yaml"
CANDIDATES = ROOT / "careers_candidates.yaml"
REPORT = ROOT / "data" / "careers_report.json"


def slugs(name: str) -> list[str]:
    base = re.sub(r"\(.*?\)", "", name.lower()).replace("&", "and")
    words = re.findall(r"[a-z0-9]+", base)
    core = [w for w in words if w not in {"the", "plc", "ltd", "llp", "lp", "inc", "group", "uk", "limited"}]
    out = []
    key_words = [w for w in core if w not in {"of", "and", "s"}]
    variants = [core, words] + ([key_words[:2]] if len(key_words) > 2 else [])
    for ws in variants:
        if not ws:
            continue
        for sep in ("", "-"):
            s = sep.join(ws)
            if len(s) >= 3 and s not in out:
                out.append(s)
    return out[:6]


def probe_apis(s, name: str) -> dict | None:
    for slug in slugs(name):
        try:
            r = s.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", timeout=20)
            if r.status_code == 200 and r.json().get("jobs") is not None:
                return {"platform": "greenhouse", "id": slug}
            r = s.get(f"https://api.lever.co/v0/postings/{slug}", params={"mode": "json", "limit": 1}, timeout=20)
            if r.status_code == 200 and isinstance(r.json(), list):
                return {"platform": "lever", "id": slug}
            r = s.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", timeout=20)
            if r.status_code == 200 and "jobs" in r.json():
                return {"platform": "ashby", "id": slug}
            r = s.get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings", params={"limit": 1}, timeout=20)
            if r.status_code == 200 and r.json().get("totalFound", 0) > 0:
                return {"platform": "smartrecruiters", "id": slug}
        except Exception as e:
            log.debug("probe %s failed: %s", slug, e)
    return None


_WD = re.compile(r"https?://([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([A-Za-z0-9_-]+)")
_ORACLE = re.compile(r"https?://([a-z0-9-]+\.fa(?:\.[a-z0-9-]+)?\.oraclecloud\.com)/hcmUI/CandidateExperience/[a-z-]+/sites/([A-Za-z0-9_]+)")


def search_web(s, name: str) -> dict | None:
    """Looks the institution up on DuckDuckGo for a Workday or Oracle careers page."""
    for query in (f'"{name}" careers site:myworkdayjobs.com', f'"{name}" careers site:oraclecloud.com'):
        try:
            r = s.get("https://html.duckduckgo.com/html/", params={"q": query}, timeout=30)
        except Exception as e:
            log.info("search failed for %s: %s", name, e)
            continue
        time.sleep(2.5)
        if r.status_code != 200:
            log.info("search for %s -> %s", name, r.status_code)
            continue
        links = re.findall(r'href="([^"]+)"', r.text)
        for link in links:
            if "uddg=" in link:
                link = unquote(parse_qs(urlparse(link).query).get("uddg", [""])[0])
            m = _WD.match(link)
            if m and m.group(3).lower() not in {"wday", "login", "en-us"}:
                return {"platform": "workday", "id": f"{m.group(1)}.{m.group(2)}/{m.group(3)}"}
            m = _ORACLE.match(link)
            if m:
                return {"platform": "oracle", "id": f"{m.group(1)}/{m.group(2)}"}
    return None


def verify(s, site: dict) -> bool:
    try:
        if site["platform"] == "workday":
            host, path = site["id"].split("/", 1)
            tenant = host.split(".")[0]
            r = s.post(f"https://{host}.myworkdayjobs.com/wday/cxs/{tenant}/{path}/jobs",
                       json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""}, timeout=30)
            return r.status_code == 200 and "jobPostings" in r.json()
        if site["platform"] == "oracle":
            host, num = site["id"].split("/", 1)
            r = s.get(f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions",
                      params={"onlyData": "true", "finder": f"findReqs;siteNumber={num},limit=1"}, timeout=30)
            return r.status_code == 200
    except Exception:
        return False
    return True


def workday_root_site(s, tenant: str, wd: str) -> str | None:
    """The default site a Workday tenant redirects to, if any."""
    try:
        r = s.get(f"https://{tenant}.{wd}.myworkdayjobs.com/", timeout=30, allow_redirects=True)
    except Exception:
        return None
    m = re.search(rf"/wday/cxs/{re.escape(tenant)}/([A-Za-z0-9_-]+)", r.text) or \
        re.match(rf"https://{re.escape(tenant)}\.{wd}\.myworkdayjobs\.com/(?:[a-z]{{2}}-[A-Z]{{2}}/)?([A-Za-z0-9_-]+)", r.url)
    return m.group(1) if m else None


def try_candidate(s, cand: dict, platform: str) -> dict | None:
    if platform == "oracle":
        for num in cand["sites"]:
            site = {"platform": "oracle", "id": f"{cand['host']}/{num}"}
            if verify(s, site):
                return site
        return None
    wds = [f"wd{n}" for n in cand.get("wd", [])] + [w for w in ("wd1", "wd3", "wd5", "wd12", "wd103")
                                                  if w not in {f"wd{n}" for n in cand.get("wd", [])}]
    for i, wd in enumerate(wds):
        sites = list(cand.get("sites", [])) if i < len(cand.get("wd", [])) or i == 0 else []
        root = workday_root_site(s, cand["tenant"], wd)
        if root and root not in sites:
            sites.append(root)
        for name in sites:
            site = {"platform": "workday", "id": f"{cand['tenant']}.{wd}/{name}"}
            if verify(s, site):
                return site
    return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    manual_cfg = (yaml.safe_load(MANUAL.read_text()) or {}) if MANUAL.exists() else {}
    manual = manual_cfg.get("sites") or []
    excluded = {(x["platform"], x["id"]) for x in manual_cfg.get("exclude") or []}
    manual_names = {institutions.norm(m["institution"]) for m in manual}
    cands = yaml.safe_load(CANDIDATES.read_text()) if CANDIDATES.exists() else {}
    cand_by_name = {}
    for platform in ("workday", "oracle"):
        for c in cands.get(platform) or []:
            cand_by_name.setdefault(institutions.norm(c["institution"]), []).append((platform, c))
    previous = {institutions.norm(x["institution"]): x for x in json.loads(OUT.read_text())} if OUT.exists() else {}
    todo = [i for i in institutions.load() if i["key"] not in manual_names]

    def find(inst):
        s = session()
        site = None
        for platform, cand in cand_by_name.get(inst["key"], []):
            site = try_candidate(s, cand, platform)
            if site:
                break
        if not site:
            site = probe_apis(s, inst["name"])
        if site and (site["platform"], site["id"]) in excluded:
            site = None
        if not site:
            site = search_web(s, inst["name"])
            if site and not verify(s, site):
                site = None
        prev = previous.get(inst["key"])
        if not site and prev and (prev["platform"], prev["id"]) not in excluded:
            return prev  # keep last week's answer if today's lookup failed
        if site:
            site["institution"] = inst["name"]
            log.info("%s -> %s %s", inst["name"], site["platform"], site["id"])
        return site

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(find, todo))
    found = [x for x in results if x]
    missing = [inst["name"] for inst, x in zip(todo, results) if not x]
    sites = manual + found
    # The same careers site can serve several names on the list (e.g. "LSEG" and "London Stock Exchange Group").
    unique = {}
    for x in sites:
        unique.setdefault((x["platform"], x["id"]), x)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(sorted(unique.values(), key=lambda x: x["institution"]), indent=1))
    by = {}
    for x in unique.values():
        by[x["platform"]] = by.get(x["platform"], 0) + 1
    log.info("Found careers sites for %d institutions: %s", len(unique), by)
    REPORT.write_text(json.dumps({"found": len(unique), "by_platform": by,
                                  "not_found (searched on LinkedIn by name instead)": missing}, indent=1))


if __name__ == "__main__":
    main()
