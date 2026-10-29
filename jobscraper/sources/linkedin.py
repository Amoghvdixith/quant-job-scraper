"""LinkedIn public (logged-out) job search."""
from __future__ import annotations

import logging
from datetime import date
import re
from urllib.parse import unquote

from bs4 import BeautifulSoup

from ..http import polite_get, session
from ..models import Job

log = logging.getLogger(__name__)

SEARCH = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
POSTING = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{id}"
WORLDWIDE_GEO_ID = "92000000"


def build_keywords(keywords: list[str]) -> str:
    """One LinkedIn search per role: "A" OR "B" OR "C"."""
    return " OR ".join(f'"{k}"' for k in keywords)


def search(role: dict, cfg: dict, stats: dict, location: str = "Worldwide") -> list[Job]:
    return _search(build_keywords(role["keywords"]), role["title"], cfg, stats, location,
                   cfg.get("linkedin_max_pages", 3))


def search_company(company: str, cfg: dict, stats: dict) -> list[Job]:
    """Entry-level postings at one target institution, any title (the title filter runs later)."""
    return _search(f'"{company}"', f"firm: {company}", cfg, stats, "Worldwide",
                   cfg.get("linkedin_target_firm_pages", 2))


def _search(keywords: str, label: str, cfg: dict, stats: dict, location: str, max_pages: int) -> list[Job]:
    s = session()
    jobs: list[Job] = []
    seen: set[str] = set()
    params = {
        "keywords": keywords,
        "f_TPR": f"r{cfg['max_age_days'] * 86400}",
        "f_E": ",".join(str(x) for x in cfg.get("linkedin_experience_levels", [1, 2, 3])),
        "sortBy": "DD",
    }
    if location.lower() == "worldwide":
        params["geoId"] = WORLDWIDE_GEO_ID
    else:
        params["location"] = location
    for page in range(max_pages):
        r = polite_get(s, SEARCH, params={**params, "start": page * 10})
        if r is None:
            stats["errors"] += 1
            break
        cards = BeautifulSoup(r.text, "html.parser").select("div.base-search-card, div.job-search-card")
        page_jobs = [j for j in (_parse_card(c, label) for c in cards) if j]
        new = [j for j in page_jobs if j.url not in seen]
        if not new:
            break
        for j in new:
            seen.add(j.url)
        jobs.extend(new)
        if len(page_jobs) < 10:
            break
    return jobs


def _parse_card(card, label: str) -> Job | None:
    urn = card.get("data-entity-urn") or ""
    link = card.select_one("a.base-card__full-link, a[href*='/jobs/view/']")
    title = card.select_one(".base-search-card__title")
    if not link or not title:
        return None
    job_id = urn.rsplit(":", 1)[-1] if urn else ""
    url = link["href"].split("?")[0]
    if not job_id:
        job_id = url.rstrip("/").rsplit("-", 1)[-1]
    company = card.select_one(".base-search-card__subtitle")
    location = card.select_one(".job-search-card__location")
    when = card.select_one("time")
    posted = None
    if when and when.get("datetime"):
        try:
            posted = date.fromisoformat(when["datetime"][:10])
        except ValueError:
            pass
    return Job(
        source="LinkedIn",
        title=title.get_text(strip=True),
        company=company.get_text(strip=True) if company else "",
        location=location.get_text(strip=True) if location else "",
        url=f"https://www.linkedin.com/jobs/view/{job_id}" if job_id.isdigit() else url,
        posted=posted,
        search_term=label,
    )


def fetch_description(job: Job) -> str:
    job_id = job.url.rstrip("/").rsplit("/", 1)[-1]
    if not job_id.isdigit():
        return ""
    r = polite_get(session(), POSTING.format(id=job_id), delay=(1.0, 2.5))
    if r is None:
        return ""
    if not job.apply_url:
        find_apply_url(job, r.text)
    soup = BeautifulSoup(r.text, "html.parser")
    body = soup.select_one(".show-more-less-html__markup, .description__text")
    criteria = " ".join(li.get_text(" ", strip=True) for li in soup.select(".description__job-criteria-item"))
    text = ((body.get_text(" ", strip=True) if body else "") + " " + criteria).strip()
    if "no longer accepting applications" in r.text.lower():
        text = f"{CLOSED_MARKER} {text}"
    return text


APPLY_STATS = {"employer link": 0, "easy apply": 0, "employer site, link hidden": 0}


def find_apply_url(job: Job, fragment: str) -> None:
    """Sets job.apply_url for "Apply on company website" jobs. LinkedIn only shows that link
    to signed-in visitors, so usually we can only tell which kind of apply it is."""
    url = external_apply_url(fragment)
    offsite = bool(url) or "offsite" in fragment
    job.easy_apply = not offsite
    job.apply_url = url
    APPLY_STATS["employer link" if url else "employer site, link hidden" if offsite else "easy apply"] += 1


def external_apply_url(page: str) -> str:
    """The employer's application page behind LinkedIn's "Apply on company website" button.
    Empty for Easy Apply jobs, which are applied for on LinkedIn itself."""
    m = re.search(r"externalApply/\d+\?url=([^&\"'\s]+)", page)
    if not m:
        return ""
    url = unquote(m.group(1))
    return url if url.startswith("http") else ""


# Put at the start of a description when the posting has closed.
CLOSED_MARKER = "[POSTING CLOSED]"
