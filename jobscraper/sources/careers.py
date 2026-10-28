"""Institutions' own careers sites, read through their hiring platform's public job feed.

`data/careers_sites.json` lists which platform each institution uses; build it with
`python -m jobscraper.discover_careers` (the "Find careers sites" workflow does this weekly).
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from ..http import session
from ..models import Job

log = logging.getLogger(__name__)
SITES_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "careers_sites.json"

# Workday search terms; other platforms return every opening in one request.
WORKDAY_TERMS = ["risk", "quant", "valuation", "product control", "derivatives", "trading",
                 "treasury", "model", "analyst", "graduate"]


def load_sites() -> list[dict]:
    return json.loads(SITES_FILE.read_text()) if SITES_FILE.exists() else []


def fetch_site(site: dict, cfg: dict) -> list[Job]:
    platform = site["platform"]
    s = session()
    try:
        if platform == "greenhouse":
            return _greenhouse(s, site)
        if platform == "lever":
            return _lever(s, site)
        if platform == "ashby":
            return _ashby(s, site)
        if platform == "smartrecruiters":
            return _smartrecruiters(s, site, cfg)
        if platform == "workday":
            return _workday(s, site, cfg)
        if platform == "oracle":
            return _oracle(s, site, cfg)
    except Exception as e:
        log.warning("%s (%s) failed: %s", site["institution"], platform, e)
        raise
    return []


def _job(site, title, location, url, posted, description="") -> Job:
    return Job(source=f"Careers site ({site['platform'].title()})", title=title or "", company=site["institution"],
               location=location or "", url=url or "", posted=posted, description=description,
               search_term="careers site")


def _date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000 if value > 1e11 else value, timezone.utc).date()
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(value))
    return date.fromisoformat(m.group(1)) if m else None


def _text(html: str) -> str:
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


def _greenhouse(s, site):
    r = s.get(f"https://boards-api.greenhouse.io/v1/boards/{site['id']}/jobs", params={"content": "true"}, timeout=60)
    r.raise_for_status()
    return [_job(site, j["title"], (j.get("location") or {}).get("name"), j["absolute_url"],
                 _date(j.get("first_published") or j.get("updated_at")), _text(_unescape(j.get("content", ""))))
            for j in r.json().get("jobs", [])]


def _unescape(s: str) -> str:
    import html
    return html.unescape(s or "")


def _lever(s, site):
    r = s.get(f"https://api.lever.co/v0/postings/{site['id']}", params={"mode": "json"}, timeout=60)
    r.raise_for_status()
    return [_job(site, j["text"], (j.get("categories") or {}).get("location"), j["hostedUrl"],
                 _date(j.get("createdAt")), j.get("descriptionPlain", "") + " " + j.get("additionalPlain", ""))
            for j in r.json()]


def _ashby(s, site):
    r = s.get(f"https://api.ashbyhq.com/posting-api/job-board/{site['id']}", timeout=60)
    r.raise_for_status()
    return [_job(site, j["title"], j.get("location"), j.get("jobUrl"), _date(j.get("publishedAt")),
                 j.get("descriptionPlain", ""))
            for j in r.json().get("jobs", [])]


def _smartrecruiters(s, site, cfg):
    jobs, offset = [], 0
    while offset < 1000:
        r = s.get(f"https://api.smartrecruiters.com/v1/companies/{site['id']}/postings",
                  params={"limit": 100, "offset": offset}, timeout=60)
        r.raise_for_status()
        data = r.json()
        for j in data.get("content", []):
            loc = j.get("location") or {}
            jobs.append(_job(site, j.get("name"), ", ".join(x for x in (loc.get("city"), loc.get("country")) if x),
                             f"https://jobs.smartrecruiters.com/{site['id']}/{j['id']}", _date(j.get("releasedDate"))))
        offset += 100
        if offset >= data.get("totalFound", 0):
            break
    return jobs


_WD_AGO = re.compile(r"(\d+)\+?\s+days?\s+ago", re.I)


def _workday_posted(text: str) -> date | None:
    t = (text or "").lower()
    today = date.today()
    if "today" in t:
        return today
    if "yesterday" in t:
        return today - timedelta(days=1)
    m = _WD_AGO.search(t)
    if m:
        return today - timedelta(days=int(m.group(1))) if "+" not in t else today - timedelta(days=31)
    return None


def _workday(s, site, cfg):
    # site["id"] looks like "barclays.wd3/External_Career_Site_Barclays"
    host_part, path = site["id"].split("/", 1)
    tenant = host_part.split(".")[0]
    base = f"https://{host_part}.myworkdayjobs.com"
    api = f"{base}/wday/cxs/{tenant}/{path}/jobs"
    jobs: dict[str, Job] = {}
    for term in WORKDAY_TERMS:
        for offset in range(0, 100, 20):
            r = s.post(api, json={"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": term}, timeout=60)
            r.raise_for_status()
            postings = r.json().get("jobPostings", [])
            stop = False
            for p in postings:
                posted = _workday_posted(p.get("postedOn", ""))
                if posted and (date.today() - posted).days > cfg["max_age_days"]:
                    stop = True  # results are newest first only sometimes; keep scanning this page
                    continue
                url = f"{base}/{path}{p.get('externalPath', '')}"
                jobs.setdefault(url, _job(site, p.get("title"), p.get("locationsText"), url, posted or date.today()))
            if len(postings) < 20 or stop:
                break
    return list(jobs.values())


def _oracle(s, site, cfg):
    # site["id"] looks like "jpmc.fa.oraclecloud.com/CX_1001"
    host, site_number = site["id"].split("/", 1)
    api = f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    jobs: dict[str, Job] = {}
    for term in WORKDAY_TERMS:
        finder = (f'findReqs;siteNumber={site_number},keyword="{term}",limit=50,'
                  f'sortBy=POSTING_DATES_DESC,lastSelectedFacet=POSTING_DATES,selectedPostingDatesFacet=7')
        r = s.get(api, params={"onlyData": "true", "expand": "requisitionList", "finder": finder}, timeout=60)
        r.raise_for_status()
        for item in r.json().get("items", []):
            for req in item.get("requisitionList", []):
                url = f"https://{host}/hcmUI/CandidateExperience/en/sites/{site_number}/job/{req['Id']}"
                jobs.setdefault(url, _job(site, req.get("Title"), req.get("PrimaryLocation"), url,
                                          _date(req.get("PostedDate")), req.get("ShortDescriptionStr") or ""))
    return list(jobs.values())


def fetch_description(job: Job) -> str:
    """Full description for Workday postings (the search results don't include it)."""
    m = re.match(r"https://([^.]+)\.(wd\d+)\.myworkdayjobs\.com/(.+?)(/job/.+)$", job.url)
    if not m:
        return ""
    tenant, wd, path, ext = m.groups()
    try:
        r = session().get(f"https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{path}{ext}", timeout=60)
        r.raise_for_status()
        return _text(r.json().get("jobPostingInfo", {}).get("jobDescription", ""))
    except Exception as e:
        log.info("Workday description fetch failed for %s: %s", job.url, e)
        return ""
