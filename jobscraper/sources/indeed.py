"""Indeed, through the python-jobspy library (MIT licensed)."""
from __future__ import annotations

import logging
from datetime import date

from ..models import Job
from .google import _s

log = logging.getLogger(__name__)


def search(role: dict, cfg: dict, stats: dict, country: str) -> list[Job]:
    from jobspy import scrape_jobs

    query = " OR ".join(f'"{k}"' for k in role["keywords"])
    try:
        df = scrape_jobs(
            site_name=["indeed"],
            search_term=query,
            country_indeed=country,
            hours_old=cfg["max_age_days"] * 24,
            results_wanted=cfg.get("indeed_results_per_search", 30),
            description_format="markdown",
            verbose=0,
        )
    except Exception as e:
        log.warning("Indeed %s search for %r failed: %s", country, role["title"], e)
        stats["errors"] += 1
        return []
    jobs = []
    for row in df.to_dict("records"):
        posted = row.get("date_posted")
        jobs.append(Job(
            source="Indeed",
            title=_s(row.get("title")),
            company=_s(row.get("company")),
            location=_s(row.get("location")) or country.title(),
            url=_s(row.get("job_url")),
            posted=posted if isinstance(posted, date) else None,
            description=_s(row.get("description")),
            search_term=role["title"],
        ))
    return jobs
