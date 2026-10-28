"""eFinancialCareers search.

eFinancialCareers has no documented public API. This tries the JSON endpoint its
own website calls, then falls back to reading the job data embedded in the
search results page. Both are parsed loosely so small layout changes don't break it.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timezone

from bs4 import BeautifulSoup

from ..http import polite_get, session
from ..models import Job

log = logging.getLogger(__name__)

API = "https://job-search-api.efinancialcareers.com/v1/efc/jobs/search"
SITE = "https://www.efinancialcareers.com"


def search(role: dict, cfg: dict, stats: dict) -> list[Job]:
    s = session()
    s.headers.update({"Origin": SITE, "Referer": SITE + "/", "Accept": "application/json, text/html;q=0.9"})
    jobs: dict[str, Job] = {}
    for kw in role["keywords"]:
        for page in range(1, cfg.get("efc_max_pages", 2) + 1):
            found = _search_api(s, kw, page) or _search_html(s, kw, page)
            if found is None:
                stats["errors"] += 1
                break
            new = 0
            for raw in found:
                job = _to_job(raw, role)
                if job and job.url not in jobs:
                    jobs[job.url] = job
                    new += 1
            if new == 0 or len(found) < 15:
                break
    return list(jobs.values())


def _search_api(s, kw: str, page: int) -> list[dict] | None:
    params = {
        "q": kw, "page": page, "pageSize": 20, "language": "en",
        "includeRemote": "true", "includeUnspecifiedSalary": "true",
        "sortBy": "POSTED_DATE", "filters.postedDate": "SEVEN",
    }
    r = polite_get(s, API, params=params, retries=1)
    if r is None:
        return None
    try:
        data = r.json()
    except ValueError:
        return None
    found = _find_job_dicts(data)
    return found or None


def _search_html(s, kw: str, page: int) -> list[dict] | None:
    r = polite_get(s, f"{SITE}/jobs", params={"q": kw, "page": page, "filters.postedDate": "SEVEN"}, retries=1)
    if r is None:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    found: list[dict] = []
    for script in soup.find_all("script"):
        text = script.string or script.get_text() or ""
        text = text.strip()
        if not text or text[0] not in "[{":
            continue
        try:
            data = json.loads(text.replace("&q;", '"').replace("&a;", "&").replace("&s;", "'"))
        except ValueError:
            continue
        found.extend(_find_job_dicts(data))
    return found


def _find_job_dicts(data) -> list[dict]:
    """Walk any JSON and collect objects that look like job postings."""
    out: list[dict] = []
    stack = [data]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            keys = set(node)
            if "title" in keys and keys & {"detailsPageUrl", "jobId", "url", "applyUrl", "datePosted", "postedDate"}:
                out.append(node)
                continue
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return out


def _get(d: dict, *paths):
    for path in paths:
        cur = d
        for part in path.split("."):
            cur = cur.get(part) if isinstance(cur, dict) else None
        if cur:
            return cur
    return None


def _to_job(raw: dict, role: dict) -> Job | None:
    title = _get(raw, "title")
    url = _get(raw, "detailsPageUrl", "url", "applyUrl")
    job_id = _get(raw, "id", "jobId")
    if not url and job_id:
        url = f"{SITE}/jobs-{job_id}"
    if not title or not url:
        return None
    if isinstance(url, str) and url.startswith("/"):
        url = SITE + url
    company = _get(raw, "clientBrandName", "companyName", "company.name", "company", "hiringOrganization.name", "client.name")
    location = _get(raw, "jobLocation.displayName", "location.displayName", "displayLocation", "location",
                    "jobLocation.address.addressLocality", "jobLocation.city")
    if isinstance(location, list):
        location = ", ".join(_get(x, "displayName", "city", "address.addressLocality") or str(x) for x in location)
    if isinstance(location, dict):
        location = ", ".join(str(v) for k, v in location.items() if k in ("city", "state", "country") and v)
    if _get(raw, "workArrangementType") in ("REMOTE", "Remote") and "remote" not in str(location or "").lower():
        location = f"{location or ''} (Remote)".strip()
    description = _get(raw, "description", "summary", "jobSummary") or ""
    description = BeautifulSoup(str(description), "html.parser").get_text(" ", strip=True)
    return Job(
        source="eFinancialCareers",
        title=str(title),
        company=str(company or ""),
        location=str(location or ""),
        url=str(url),
        posted=_parse_date(_get(raw, "postedDate", "datePosted", "postedAt", "createdDate")),
        description=description,
        search_term=role["title"],
    )


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, (int, float)):  # epoch millis or seconds
        ts = value / 1000 if value > 1e11 else value
        return datetime.fromtimestamp(ts, timezone.utc).date()
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(value))
    return date.fromisoformat(m.group(1)) if m else None
