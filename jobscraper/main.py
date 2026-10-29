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

from . import filters, institutions
from .excel import write_workbook
from .mailer import build_email, send
from .models import Job
from .sources import careers, efinancialcareers, google, indeed, linkedin
from .uk_sponsors import UKSponsorRegister

log = logging.getLogger("jobscraper")
ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "data" / "jobs.json"
MAX_DESCRIPTION_FETCHES = 400
KEEP_STORE_DAYS = 30


def rotate(items: list, per_run: int, slot: int) -> list:
    """A different slice of `items` each run, so everything is covered over a day or two."""
    if not items or per_run <= 0:
        return []
    if per_run >= len(items):
        return list(items)
    start = (slot * per_run) % len(items)
    return (items + items)[start:start + per_run]


def plan(cfg: dict, roles: list[dict], slot: int) -> dict[str, list]:
    """Every search this run will make, grouped by site. Each site's searches run one after another."""
    tasks: dict[str, list] = {}
    sources = cfg["sources"]
    if "linkedin" in sources:
        locations = cfg.get("linkedin_locations", ["Worldwide"]) + rotate(
            cfg.get("linkedin_rotating_locations", []), cfg.get("linkedin_locations_per_run", 2), slot)
        tasks["LinkedIn"] = [
            (f"{role['title']} @ {loc}", lambda st, role=role, loc=loc: linkedin.search(role, cfg, st, loc))
            for loc in locations for role in roles
        ]
        if "careers" in sources or cfg.get("linkedin_target_firms_per_run"):
            have_site = {institutions.norm(x["institution"]) for x in careers.load_sites()}
            firms = [i for i in institutions.load() if i["key"] not in have_site]
            tasks["LinkedIn"] += [
                (f"firm {inst['name']}", lambda st, inst=inst: linkedin.search_company(inst["name"], cfg, st))
                for inst in rotate(firms, cfg.get("linkedin_target_firms_per_run", 80), slot)
            ]
    if "google" in sources:
        tasks["Google Jobs"] = [(role["title"], lambda st, role=role: google.search(role, cfg, st)) for role in roles]
    if "efinancialcareers" in sources:
        tasks["eFinancialCareers"] = [
            (role["title"], lambda st, role=role: efinancialcareers.search(role, cfg, st)) for role in roles]
    if "indeed" in sources:
        countries = rotate(cfg.get("indeed_countries", ["uk"]), cfg.get("indeed_countries_per_run", 3), slot)
        tasks["Indeed"] = [
            (f"{role['title']} @ {c}", lambda st, role=role, c=c: indeed.search(role, cfg, st, c))
            for c in countries for role in roles
        ]
    if "careers" in sources:
        tasks["Careers sites"] = [
            (site["institution"], lambda st, site=site: careers.fetch_site(site, cfg)) for site in careers.load_sites()]
    return tasks


def scrape(cfg: dict, roles: list[dict], slot: int) -> tuple[list[Job], dict]:
    tasks = plan(cfg, roles, slot)
    stats = {label: {"found": 0, "errors": 0} for label in tasks}

    def run(label: str) -> list[Job]:
        out: list[Job] = []
        for name, fn in tasks[label]:
            try:
                found = fn(stats[label])
            except Exception as e:
                log.warning("%s | %s failed: %s", label, name, e)
                stats[label]["errors"] += 1
                continue
            log.info("%s | %s | %d results", label, name, len(found))
            out.extend(found)
        stats[label]["found"] = len(out)
        return out

    def run_careers(label: str) -> list[Job]:
        # Careers sites are all different hosts, so they can run side by side.
        def one(item):
            name, fn = item
            try:
                return fn(stats[label])
            except Exception as e:
                log.warning("%s | %s failed: %s", label, name, e)
                stats[label]["errors"] += 1
                return []
        with ThreadPoolExecutor(max_workers=8) as pool:
            out = [j for batch in pool.map(one, tasks[label]) for j in batch]
        stats[label]["found"] = len(out)
        return out

    with ThreadPoolExecutor(max_workers=max(1, len(tasks))) as pool:
        futures = [pool.submit(run_careers if label == "Careers sites" else run, label) for label in tasks]
        results = [f.result() for f in futures]
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
        job.target_firm = institutions.match(job.company)
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
    raw = json.loads(STORE.read_text()) if STORE.exists() else {}
    # Re-key in case the duplicate-matching rules changed since the jobs were saved.
    store: dict[str, dict] = {}
    for rec in raw.values():
        key = Job.from_dict(rec).key
        if key in store:
            kept = store[key]
            kept["sources"] = sorted(set(kept.get("sources", [])) | set(rec.get("sources", [])))
            kept["emailed"] = kept.get("emailed") or rec.get("emailed")
        else:
            store[key] = rec
    return store


def save_store(store: dict[str, dict]) -> None:
    cutoff = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=KEEP_STORE_DAYS)).isoformat()
    store = {k: v for k, v in store.items() if v.get("first_seen", "") >= cutoff}
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(store, indent=1, sort_keys=True))


def fetch_full_description(job: Job) -> str:
    """The job's full text. Search results often only carry a short summary."""
    text = job.description or ""
    if len(text) >= 600:
        return text
    fetched = ""
    if "linkedin.com" in job.url:
        fetched = linkedin.fetch_description(job)
    elif "efinancialcareers" in job.url:
        fetched = efinancialcareers.fetch_description(job)
    elif "myworkdayjobs.com" in job.url:
        fetched = careers.fetch_description(job)
    return fetched if len(fetched) > len(text) else text


def enrich(job: Job, text: str, register: UKSponsorRegister) -> None:
    """Fills in what we learn from the description."""
    job.description_checked = len(text) >= 200
    job.years_required = filters.years_required(text)
    job.sponsorship, job.sponsorship_evidence = filters.sponsorship(text) if text else ("Not checked", "")
    job.uk_licensed_sponsor = register.check(job.company, job.location)
    if text.startswith(linkedin.CLOSED_MARKER):
        job.sponsorship_evidence = "posting closed"


def rule_broken(job: Job, cfg: dict, matcher: filters.RoleMatcher) -> str | None:
    """Every rule a job must pass to be emailed. Checked again on each run, so
    changes to config.yaml or roles.yaml also apply to jobs found earlier."""
    if not matcher.match(job.title):
        return "title doesn't match a target role"
    if filters.is_senior(job.title, cfg["senior_title_words"]):
        return "too senior"
    if filters.is_excluded_location(job.location, cfg["excluded_locations"]):
        return "excluded country"
    if job.years_required is not None and job.years_required > cfg["max_years_experience"]:
        return f"asks for {job.years_required}+ years"
    if cfg.get("drop_no_sponsorship", True) and job.sponsorship == "No":
        return "no sponsorship"
    if job.sponsorship_evidence == "posting closed":
        return "posting closed"
    cutoff = date.today() - timedelta(days=cfg["max_age_days"])
    if (job.posted or date.fromisoformat(job.first_seen[:10])) < cutoff:
        return "older than the age limit"
    return None


def enrich_all(jobs: list[Job], register: UKSponsorRegister) -> None:
    """Reads descriptions: LinkedIn one at a time (it blocks fast readers), other sites in parallel."""
    slow = [j for j in jobs if "linkedin.com" in j.url and len(j.description or "") < 600]
    fast = [j for j in jobs if j not in slow]

    def one(job: Job) -> None:
        try:
            enrich(job, fetch_full_description(job), register)
        except Exception as e:
            log.info("description for %s failed: %s", job.url, e)
            enrich(job, job.description or "", register)

    def run_slow() -> None:
        for job in slow[:MAX_DESCRIPTION_FETCHES]:
            one(job)
        for job in slow[MAX_DESCRIPTION_FETCHES:]:  # the rest are read on the next run
            enrich(job, job.description or "", register)
            job.sponsorship = "Not checked"

    with ThreadPoolExecutor(max_workers=6) as pool:
        slow_done = pool.submit(run_slow)
        list(pool.map(one, fast))
        slow_done.result()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-email", action="store_true", help="write the Excel file but don't send it")
    parser.add_argument("--roles", help="comma-separated role ids to search (for testing)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger().addHandler(WARNINGS)
    WARNINGS.setFormatter(logging.Formatter("%(asctime)s %(name)s: %(message)s"))

    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    roles = yaml.safe_load((ROOT / "roles.yaml").read_text())["roles"]
    if args.roles:
        wanted = set(args.roles.split(","))
        roles = [r for r in roles if r["id"] in wanted]

    now_utc = datetime.now(timezone.utc)
    slot = now_utc.toordinal() * 6 + now_utc.hour // 4
    raw, stats = scrape(cfg, roles, slot)
    matcher = filters.RoleMatcher(roles)
    candidates = apply_filters(raw, cfg, matcher)
    log.info("%d raw results, %d after title/seniority/location/date filters", len(raw), len(candidates))

    store = load_store()
    register = UKSponsorRegister()
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
    to_read = []
    for key, job in candidates.items():
        prev = store.get(key)
        if prev and prev.get("sponsorship") != "Not checked" and "description_checked" in prev:
            # Seen before and already read: keep what we learned, but record any new source.
            prev["sources"] = sorted(set(prev.get("sources", [])) | set(job.sources))
            continue
        job.first_seen = prev["first_seen"] if prev else now
        to_read.append((key, job, bool(prev and prev.get("emailed"))))
    # Jobs saved by older versions that never had their description read.
    for key, rec in store.items():
        if "description_checked" not in rec and key not in candidates and not rec.get("excluded"):
            to_read.append((key, Job.from_dict(rec), bool(rec.get("emailed"))))
    log.info("Reading %d job descriptions", len(to_read))
    enrich_all([job for _, job, _ in to_read], register)
    for key, job, emailed in to_read:
        store[key] = {**job.to_dict(), "excluded": None, "emailed": emailed}

    current = []
    dropped: dict[str, int] = {}
    for key, rec in store.items():
        job = Job.from_dict(rec)
        job.target_firm = institutions.match(job.company)
        job.recruiter = filters.is_recruiter(job.company)
        reason = rule_broken(job, cfg, matcher)
        rec["excluded"] = reason
        if reason:
            dropped[reason] = dropped.get(reason, 0) + 1
        else:
            current.append(job)
    log.info("Dropped from the saved list: %s", dropped)
    new_keys = {j.key for j in current if not store[j.key].get("emailed")}
    current.sort(key=lambda j: (
        j.key not in new_keys, j.recruiter, j.sponsorship != "Yes", j.uk_licensed_sponsor != "Yes",
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
    write_report(stats, len(raw), len(candidates), current, new_keys, slot, dropped)


class _WarningBuffer(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        if len(self.lines) < 200:
            self.lines.append(self.format(record))


WARNINGS = _WarningBuffer()


def write_report(stats, raw_count, candidate_count, current, new_keys, slot, dropped) -> None:
    """data/last_run.json: what the last run found, readable without the Actions logs."""
    report = {
        "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rotation_slot": slot,
        "sources": stats,
        "raw_results": raw_count,
        "after_filters": candidate_count,
        "jobs_in_email": len(current),
        "new_jobs": len(new_keys),
        "descriptions_read": sum(j.description_checked for j in current),
        "posted_by_recruiters": sum(j.recruiter for j in current),
        "saved_jobs_dropped_by_rule": dropped,
        "warnings": WARNINGS.lines,
    }
    (ROOT / "data" / "last_run.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
