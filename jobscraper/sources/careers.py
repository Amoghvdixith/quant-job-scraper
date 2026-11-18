"""Institutions' own careers sites, read through their hiring platform's public job feed.

`data/careers_sites.json` lists which platform each institution uses; build it with
`python -m jobscraper.discover_careers` (the "Find careers sites" workflow does this weekly).
"""
from __future__ import annotations

import json
import logging
import random
import re
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from ..http import session
from ..models import Job

log = logging.getLogger(__name__)
SITES_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "careers_sites.json"

# Search terms for Oracle sites; other platforms return every opening in one request.
WORKDAY_TERMS = ["risk", "quant", "valuation", "product control", "derivatives", "trading",
                 "treasury", "model", "analyst", "graduate"]


# Workday rate-limits by client across all the firms it hosts (429 Too Many Requests from
# 16 Nov 2026). Pacing alone (two sites at a time, 1-2s apart, PR #15) was not enough: it let
# roughly one request through every 30 seconds, and the old search made up to 50 requests a site
# (10 terms x 5 pages). So each Workday site now gets ONE request, for its newest postings with no
# search text (titles are matched later, like every other source), and every Workday request in
# the run goes through one gate that keeps them WORKDAY_GAP seconds apart. A 429 is waited out
# once; if the site is still refused, Workday is blocking this run, so the rest fail at once
# instead of each waiting (the problem solver then records it as an outage).
WORKDAY_LIMIT = 20
WORKDAY_GAP = 15.0
WORKDAY_429_TRIES = 2
WORKDAY_429_WAIT = 30
_workday_gate = threading.Lock()
_workday_last = [0.0]
_workday_blocked = threading.Event()


def _workday_wait(sleep=time.sleep, clock=time.monotonic) -> None:
    """Holds the caller until WORKDAY_GAP seconds have passed since the last Workday request."""
    with _workday_gate:
        gap = WORKDAY_GAP - (clock() - _workday_last[0])
        if gap > 0:
            sleep(gap)
        _workday_last[0] = clock()


def _workday_request(send, label: str, sleep=time.sleep, clock=time.monotonic):
    """Sends one Workday request through the gate; waits out a 429 once."""
    if _workday_blocked.is_set():
        # Workday already refused this run: fail at once instead of queueing at the gate.
        raise requests.HTTPError(f"429 Too Many Requests: Workday is refusing this run ({label} not tried)")
    for attempt in range(WORKDAY_429_TRIES):
        _workday_wait(sleep, clock)
        r = send()
        if r.status_code != 429:
            r.raise_for_status()
            return r
        if attempt == WORKDAY_429_TRIES - 1:
            _workday_blocked.set()
            r.raise_for_status()
        try:
            wait = int(r.headers.get("Retry-After", ""))
        except ValueError:
            wait = WORKDAY_429_WAIT
        log.info("Workday 429 for %s, waiting %ss", label, min(wait, WORKDAY_429_WAIT))
        sleep(min(wait, WORKDAY_429_WAIT))


def _workday_post(s, api: str, body: dict, sleep=time.sleep, clock=time.monotonic):
    return _workday_request(lambda: s.post(api, json=body, timeout=60), api.split("/wday/")[0], sleep, clock)


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
               search_term="careers site", apply_url=url or "")


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
    r = _workday_post(s, api, {"appliedFacets": {}, "limit": WORKDAY_LIMIT, "offset": 0, "searchText": ""})
    jobs: dict[str, Job] = {}
    for p in r.json().get("jobPostings", []):
        posted = _workday_posted(p.get("postedOn", ""))
        if posted and (date.today() - posted).days > cfg["max_age_days"]:
            continue
        if posted is None and p.get("postedOn"):
            log.info("%s: unreadable Workday date %r", site["institution"], p.get("postedOn"))
        url = f"{base}/{path}{p.get('externalPath', '')}"
        # No date if it couldn't be read: undated postings are dropped rather than shown as fresh.
        jobs.setdefault(url, _job(site, p.get("title"), p.get("locationsText"), url, posted))
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
    if _workday_blocked.is_set():
        return ""  # Workday is refusing this run; the description is read on a later run
    api = f"https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{path}{ext}"
    try:
        r = _workday_request(lambda: session().get(api, timeout=60), api.split("/wday/")[0])
        return _text(r.json().get("jobPostingInfo", {}).get("jobDescription", ""))
    except Exception as e:
        log.info("Workday description fetch failed for %s: %s", job.url, e)
        return ""
