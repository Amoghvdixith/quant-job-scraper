"""Google Jobs, through the python-jobspy library (MIT licensed)."""
from __future__ import annotations

import logging
from datetime import date

from ..models import Job

log = logging.getLogger(__name__)


def search(role: dict, cfg: dict, stats: dict) -> list[Job]:
    from jobspy import scrape_jobs

    # Google's own filter only goes down to "in the last week"; the pipeline
    # trims anything older than max_age_days afterwards.
    query = f'{role["title"].replace(" / ", " OR ")} entry level jobs in the last week'
    try:
        df = scrape_jobs(
            site_name=["google"],
            search_term=role["title"],
            google_search_term=query,
            results_wanted=cfg.get("google_results_per_search", 20),
            verbose=0,
        )
    except Exception as e:  # jobspy raises on blocks / layout changes
        log.warning("Google search for %r failed: %s", role["title"], e)
        stats["errors"] += 1
        return []
    jobs = []
    for row in df.to_dict("records"):
        posted = row.get("date_posted")
        jobs.append(Job(
            source="Google Jobs",
            title=_s(row.get("title")),
            company=_s(row.get("company")),
            location=_s(row.get("location")),
            url=_s(row.get("job_url")),
            posted=posted if isinstance(posted, date) else None,
            description=_s(row.get("description")),
            search_term=role["title"],
        ))
    return jobs


def _s(v) -> str:
    if v is None or v != v:  # None or NaN
        return ""
    return str(v)
