"""Scrape, filter, export to Excel and email. Run with: python -m jobscraper.main"""
from __future__ import annotations

import argparse
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from . import filters
from .excel import write_workbook
from .mailer import build_email, send
from .models import Job
from .sources import efinancialcareers, google, linkedin
from .uk_sponsors import UKSponsorRegister

log = logging.getLogger("jobscraper")
ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "data" / "jobs.json"
SOURCES = {"linkedin": ("LinkedIn", linkedin), "google": ("Google Jobs", google),
           "efinancialcareers": ("eFinancialCareers", efinancialcareers)}
MAX_DESCRIPTION_FETCHES = 300
KEEP_STORE_DAYS = 30


def scrape(cfg: dict, roles: list[dict]) -> tuple[list[Job], dict]:
    stats = {SOURCES[s][0]: {"found": 0, "errors": 0} for s in cfg["sources"]}

    def run_source(name: str) -> list[Job]:
        label, module = SOURCES[name]
        out: list[Job] = []
        for role in roles:
            try:
                found = module.search(role, cfg, stats[label])
            except Exception:
                log.exception("%s search for %s crashed", label, role["title"])
                stats[label]["errors"] += 1
                continue
            log.info("%s | %s | %d results", label, role["title"], len(found))
            out.extend(found)
        stats[label]["found"] = len(out)
        return out

    # Each source runs in its own thread; requests to one site stay sequential and paced.
    with ThreadPoolExecutor(max_workers=len(cfg["sources"])) as pool:
        results = list(pool.map(run_source, cfg["sources"]))
    return [j for batch in results for j in batch], stats


def apply_filters(jobs: list[Job], cfg: dict, matcher: filters.RoleMatcher) -> dict[str, Job]:
    cutoff = date.today() - timedelta(days=cfg["max_age_days"])
    kept: dict[str, Job] = {}
    for job in jobs:
        if not job.title or not job.url:
            continue
        if job.posted is None and job.source != "LinkedIn":  # LinkedIn already filters by date server-side
            continue
        if job.posted and job.posted < cutoff:
            continue
        match = matcher.match(job.title)
        if not match:
            continue
        if filters.is_senior(job.title, cfg["senior_title_words"]):
            continue
        if filters.is_excluded_location(job.location, cfg["excluded_locations"]):
            continue
        role, _ = match
        job.role_id, job.role_title, job.category, job.tier = role["id"], role["title"], role["category"], role["tier"]
        if job.key in kept:
            existing = kept[job.key]
            if job.source not in existing.sources:
                existing.sources.append(job.source)
            if not existing.description and job.description:
                existing.description = job.description
            existing.posted = existing.posted or job.posted
        else:
            job.sources = [job.source]
            kept[job.key] = job
    return kept


def load_store() -> dict[str, dict]:
    return json.loads(STORE.read_text()) if STORE.exists() else {}


def save_store(store: dict[str, dict]) -> None:
    cutoff = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=KEEP_STORE_DAYS)).isoformat()
    store = {k: v for k, v in store.items() if v.get("first_seen", "") >= cutoff}
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(store, indent=1, sort_keys=True))


def enrich(job: Job, cfg: dict, register: UKSponsorRegister) -> str | None:
    """Reads the description; returns a reason if the job should be dropped."""
    text = job.description
    if not text and "LinkedIn" in job.sources:
        text = linkedin.fetch_description(job)
    job.years_required = filters.years_required(text)
    job.sponsorship, job.sponsorship_evidence = filters.sponsorship(text) if text else ("Not checked", "")
    job.uk_licensed_sponsor = register.check(job.company, job.location)
    if job.years_required is not None and job.years_required > cfg["max_years_experience"]:
        return f"asks for {job.years_required}+ years"
    if cfg.get("drop_no_sponsorship", True) and job.sponsorship == "No":
        return "no sponsorship"
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-email", action="store_true", help="write the Excel file but don't send it")
    parser.add_argument("--roles", help="comma-separated role ids to search (for testing)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    roles = yaml.safe_load((ROOT / "roles.yaml").read_text())["roles"]
    if args.roles:
        wanted = set(args.roles.split(","))
        roles = [r for r in roles if r["id"] in wanted]

    raw, stats = scrape(cfg, roles)
    candidates = apply_filters(raw, cfg, filters.RoleMatcher(roles))
    log.info("%d raw results, %d after title/seniority/location/date filters", len(raw), len(candidates))

    store = load_store()
    register = UKSponsorRegister()
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
    fetched = 0
    for key, job in candidates.items():
        prev = store.get(key)
        if prev and prev.get("sponsorship") != "Not checked":
            # Seen before: keep what we learned, but record any new source.
            prev["sources"] = sorted(set(prev.get("sources", [])) | set(job.sources))
            continue
        if fetched >= MAX_DESCRIPTION_FETCHES and not job.description:
            job.sponsorship = "Not checked"
        else:
            fetched += not job.description
            reason = enrich(job, cfg, register)
            job.first_seen = prev["first_seen"] if prev else now
            record = job.to_dict()
            record["excluded"] = reason
            record["emailed"] = bool(prev and prev.get("emailed"))
            store[key] = record
            continue
        job.first_seen = now
        store[key] = {**job.to_dict(), "excluded": None, "emailed": False}

    cutoff = date.today() - timedelta(days=cfg["max_age_days"])
    current = []
    for key, rec in store.items():
        if rec.get("excluded"):
            continue
        job = Job.from_dict(rec)
        posted = job.posted or date.fromisoformat(rec["first_seen"][:10])
        if posted >= cutoff:
            current.append(job)
    new_keys = {j.key for j in current if not store[j.key].get("emailed")}
    current.sort(key=lambda j: (
        j.key not in new_keys, j.sponsorship != "Yes", j.uk_licensed_sponsor != "Yes",
        j.tier, -(j.posted or date.min).toordinal(),
    ))

    stamp = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d_%H%M")
    path = write_workbook(current, new_keys, stats, ROOT / "out" / f"quant_jobs_{stamp}.xlsx")
    log.info("Wrote %s: %d jobs, %d new", path, len(current), len(new_keys))

    if not args.no_email:
        sender = os.environ["GMAIL_USER"]
        to = os.environ.get("MAIL_TO", sender)
        send(build_email(current, new_keys, stats, path, sender, to))
        log.info("Emailed %s", to)
        for key in new_keys:
            store[key]["emailed"] = True
    save_store(store)


if __name__ == "__main__":
    main()
