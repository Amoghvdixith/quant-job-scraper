"""UK government jobs.

NHS Jobs: its public XML search feed (newest first), with the advert page read for the full text.
Civil Service: Civil Service Jobs puts a "prove you're human" check in front of every page and
Find a Job (DWP) blocks GitHub's servers, so civil service roles are found where the
departments also post them: their LinkedIn pages (see linkedin.search_company).
Civil Service Careers and the Government Recruitment Service are guidance sites with no listings.
"""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from datetime import date, timedelta

from bs4 import BeautifulSoup

from ..http import polite_get, session
from ..models import Job
from . import linkedin

log = logging.getLogger(__name__)

NHS_FEED = "https://www.jobs.nhs.uk/api/v1/search_xml"
NHS_ADVERT = "https://www.jobs.nhs.uk/candidate/jobadvert/{ref}"


def nhs_search(keyword: str, cfg: dict, stats: dict) -> list[Job]:
    s = session()
    cutoff = date.today() - timedelta(days=cfg["max_age_days"])
    jobs: list[Job] = []
    for page in range(1, cfg.get("government", {}).get("nhs_max_pages", 15) + 1):
        r = polite_get(s, NHS_FEED, params={"keyword": keyword, "sort": "publicationDateDesc", "page": page},
                       delay=(0.5, 1.5), retries=2)
        if r is None:
            stats["errors"] += 1
            break
        try:
            root = ET.fromstring(r.content)
        except ET.ParseError:
            stats["errors"] += 1
            break
        rows = root.findall("vacancyDetails")
        old = 0
        for v in rows:
            job = _nhs_job(v, keyword)
            if job is None:
                continue
            if job.posted and job.posted < cutoff:
                old += 1
                continue
            jobs.append(job)
        total_pages = int(root.findtext("totalPages") or 0)
        if not rows or old or page >= total_pages:
            break
    return jobs


def _nhs_job(v, keyword: str) -> Job | None:
    ref = (v.findtext("reference") or "").strip()
    title = (v.findtext("title") or "").strip()
    if not ref or not title:
        return None
    posted = None
    try:
        posted = date.fromisoformat((v.findtext("postDate") or "")[:10])
    except ValueError:
        pass
    places = [p.text.strip() for p in v.iter("location") if p.text]
    location = "; ".join(places[:2]) or "England"
    url = NHS_ADVERT.format(ref=ref)
    return Job(
        source="NHS Jobs", title=title, company=(v.findtext("employer") or "NHS").strip(),
        location=f"{location}, United Kingdom", url=url, apply_url=url, posted=posted,
        description=(v.findtext("description") or "").strip(), search_term=f"NHS: {keyword}",
        government="NHS",
    )


def fetch_nhs_description(job: Job) -> str:
    r = polite_get(session(), job.url, delay=(0.5, 1.5), retries=2)
    if r is None:
        return ""
    soup = BeautifulSoup(r.text, "html.parser")
    for t in soup(["script", "style", "nav", "header", "footer", "form"]):
        t.decompose()
    main = soup.find("main") or soup.body or soup
    return re.sub(r"\s+", " ", main.get_text(" ", strip=True))


def civil_service_search(department: str, cfg: dict, stats: dict) -> list[Job]:
    """One department's entry-level postings on LinkedIn, kept when the employer is that department."""
    jobs = linkedin.search_company(department, cfg, stats)
    want = _words(department)
    out = []
    for j in jobs:
        if want <= _words(j.company) or _words(j.company) and _words(j.company) <= want:
            j.government = "Civil Service"
            out.append(j)
    return out


def _words(s: str) -> set[str]:
    return {w for w in re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower().replace("&", " and ")).split()
            if w not in {"the", "and", "of", "for", "hm", "uk"}}
