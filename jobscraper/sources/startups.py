"""Open roles at quant and fintech startups and boutique firms that take on recent graduates
("Startups & Boutiques" sheet).

The firms are listed by hand in startups.yaml: `startups` (name, what they do, stage, HQ) and
`boutiques` (small trading firms, hedge funds, advisory banks and risk consultancies). Their open roles
are read from their hiring platform's public job feed (Greenhouse, Lever, Ashby, SmartRecruiters),
the same feeds the careers-site source uses. A startup's job board is found in this order:

1. `board` in startups.yaml, when given;
2. data/careers_sites.json, when the startup is also on institutions.csv;
3. the board found on an earlier run (kept in data/startups.json);
4. a lookup by name on each platform (`discover_careers.probe_apis`), a few startups per run.

A role is kept when a graduate could get it: not senior, not an internship, no more than
`max_years_experience` years asked, and either a graduate/junior title, wording that welcomes
graduates ("new grads", "early career", "0-2 years"...), or no work experience asked at all.
It must also be in one of the role areas in config.yaml (quant, trading, risk, data, engineering,
finance) and not in an excluded country, and the posting must not rule out visa sponsorship.
"""
from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import date, timedelta

from .. import filters, institutions
from ..http import session
from ..models import Job, _company_key, _norm
from . import careers

log = logging.getLogger(__name__)

PLATFORMS = {"greenhouse", "lever", "ashby", "smartrecruiters"}


@dataclass
class Opportunity:
    title: str
    company: str
    location: str
    url: str
    firm_type: str = "Startup"      # "Startup" or "Boutique"
    focus: str = ""                 # what the firm does
    stage: str = ""                 # funding stage, as written in startups.yaml
    hq: str = ""
    area: str = ""                  # role area: Quant & Research, Trading, Risk...
    graduate_fit: str = ""          # "Graduate / junior role", "Welcomes graduates", "No experience asked"
    graduate_evidence: str = ""     # the words it was decided from
    years_required: int | None = None
    sponsorship: str = "Not stated"
    sponsorship_evidence: str = ""
    employer_sponsor: str = ""      # filled in by main.py from the sponsor registers
    remote: bool = False
    posted: date | None = None
    platform: str = ""
    first_seen: str = ""

    @property
    def key(self) -> str:
        from ..sponsor_registers import country_of
        return f"{_norm(self.title)}|{_company_key(self.company)}|{country_of(self.location)}"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["posted"] = self.posted.isoformat() if self.posted else None
        return d


# --- Graduate fit ---------------------------------------------------------------------------

_GRAD_TITLE = re.compile(
    r"\b(?:graduate|grad|new\s+grads?|junior|jr|entry[-\s]level|early[-\s]careers?|trainee|apprentice|"
    r"university\s+(?:hire|graduate|grad)|campus|class\s+of\s+20\d\d|associate|"
    r"(?:analyst|associate)\s+program(?:me)?s?|full[-\s]time\s+analysts?|20\d\d\s+analysts?)\b"
    r"|\b(?:engineer|developer|analyst|researcher|scientist|trader)\s+(?:i|1)\b\s*$",
    re.I,
)
_GRAD_WORDING = re.compile(
    r"\bnew\s+grad(?:uate)?s?\b|\brecent(?:ly)?\s+grad(?:uate)?(?:s|d)?\b|\bgraduates?\s+(?:are\s+)?welcome\b"
    r"|\bfresh\s+graduates?\b|\bearly[-\s]career\b|\bentry[-\s]level\b|\bfirst\s+(?:full[-\s]time\s+)?(?:job|role)\b"
    r"|\b0\s*(?:-|–|to)\s*[12]\+?\s*(?:years?|yrs?)\b|\bno\s+(?:prior\s+|previous\s+|professional\s+|work\s+)?"
    r"experience\s+(?:is\s+)?(?:required|necessary|needed)\b|\bstraight\s+(?:out\s+of|from)\s+(?:university|college|school)\b"
    r"|\b(?:just|recently)\s+(?:graduated|finished\s+(?:your|a)\s+degree)\b|\bclass\s+of\s+20\d\d\b"
    r"|\b(?:graduating|graduated)\s+(?:in|by)\s+20\d\d\b",
    re.I,
)


def graduate_fit(title: str, description: str, max_years: int) -> tuple[str, str] | None:
    """(label, evidence) when a graduate could get this role, None when it wants experience."""
    years = filters.years_required(description)
    if years is not None and years > max_years:
        return None
    m = _GRAD_TITLE.search(title or "")
    if m:
        return "Graduate / junior role", m.group(0).strip()
    m = _GRAD_WORDING.search(description or "")
    if m:
        text = " ".join((description or "").split())
        i = text.lower().find(" ".join(m.group(0).split()).lower())
        return "Welcomes graduates", text[max(0, i - 50): i + len(m.group(0)) + 50].strip() if i >= 0 else m.group(0)
    if years is None and not filters.experience_asked(description):
        if len(description or "") < 200:
            return "No experience asked (check the posting)", "description not available"
        return "No experience asked", ""
    return None


# --- Role area ----------------------------------------------------------------------------

def role_area(title: str, areas: dict[str, list[str]], exclude: list[str]) -> str:
    t = " " + " ".join(re.findall(r"[a-z0-9]+", (title or "").lower().replace("&", " and "))) + " "
    if any(f" {w.lower()} " in t for w in exclude):
        return ""
    for area, words in areas.items():
        if any(f" {w.lower()} " in t for w in words):
            return area
    return ""


# --- Finding each startup's job board ------------------------------------------------------

def known_sites() -> dict[str, dict]:
    """Boards already found for institutions.csv, by normalised name."""
    return {institutions.norm(x["institution"]): x for x in careers.load_sites()}


def resolve_board(startup: dict, sites: dict[str, dict], boards: dict, today: date, probe_budget: list[int],
                  retry_days: int) -> dict | None:
    name = startup["name"]
    b = startup.get("board")
    if isinstance(b, dict) and b.get("platform") in PLATFORMS and b.get("id"):
        return {"platform": b["platform"], "id": str(b["id"]), "institution": name}
    if b in ("none", False):
        return None
    site = sites.get(institutions.norm(name))
    if site and site["platform"] in PLATFORMS | {"workday", "oracle"}:
        return {**site, "institution": name}
    prev = boards.get(name)
    if prev and prev.get("platform"):
        return {"platform": prev["platform"], "id": prev["id"], "institution": name}
    if prev and (today - date.fromisoformat(prev["checked"])).days < retry_days:
        return None  # not found recently: try again later
    if probe_budget[0] <= 0:
        return None
    probe_budget[0] -= 1
    from ..discover_careers import probe_apis  # imported here: discover_careers pulls in more modules
    found = probe_apis(session(), name)
    boards[name] = {"checked": today.isoformat(), **(found or {})}
    if found:
        log.info("Startups | %s -> %s %s", name, found["platform"], found["id"])
        return {**found, "institution": name}
    log.info("Startups | no job board found for %s", name)
    return None


# --- Putting it together -------------------------------------------------------------------

DEFAULT_AREAS = {
    "Quant & Research": ["quant", "quantitative", "research", "researcher", "alpha", "strategist", "modelling",
                         "modeling", "pricing"],
    "Trading": ["trading", "trader", "execution", "market making", "market maker"],
    "Risk": ["risk", "credit", "fraud", "underwriting", "underwriter", "actuarial", "actuary"],
    "Data & ML": ["data", "machine learning", "ml", "ai", "analytics", "statistician", "scientist"],
    "Finance & Investment": ["finance", "financial", "investment", "investments", "portfolio", "valuation",
                             "treasury", "economist", "fp and a", "capital markets", "investment banking",
                             "m and a", "restructuring", "advisory"],
    "Engineering": ["engineer", "engineering", "developer", "software", "programmer"],
    "Analyst": ["analyst", "consultant"],
}
DEFAULT_EXCLUDE = ["sales", "marketing", "recruiter", "recruiting", "talent", "legal", "counsel", "designer",
                   "customer", "account executive", "business development", "partnerships",
                   "executive assistant", "office manager", "community", "people", "hr", "content", "copywriter"]


def collect(cfg: dict, stats: dict, store: dict, startups: list[dict], today: date | None = None,
            fetch=None) -> list[Opportunity]:
    """Graduate-friendly roles at the startups in startups.yaml, sorted with the clearest
    graduate roles first. `fetch(site)` returns Jobs (tests pass a fake)."""
    today = today or date.today()
    scfg = cfg.get("startups", {}) or {}
    fetch = fetch or (lambda site: careers.fetch_site(site, cfg))
    boards = store.setdefault("boards", {})
    sites = known_sites()
    probe_budget = [scfg.get("max_board_lookups_per_run", 25)]
    retry_days = scfg.get("board_lookup_retry_days", 14)

    resolved = []
    for s in startups:
        if not s.get("name"):
            continue
        try:
            site = resolve_board(s, sites, boards, today, probe_budget, retry_days)
        except Exception as e:
            log.warning("Startups | board lookup for %s failed: %s", s["name"], e)
            site = None
        if site:
            resolved.append((s, site))
    stats["startups_listed"] = len(startups)
    stats["boards_known"] = len(resolved)
    stats["errors"] = 0

    def one(pair):
        s, site = pair
        try:
            return s, site, fetch(site)
        except Exception as e:
            log.warning("Startups | %s (%s %s) failed: %s", s["name"], site["platform"], site["id"], e)
            # A board from an earlier lookup that no longer works is looked up again next time.
            if boards.get(s["name"], {}).get("id") == site["id"]:
                boards.pop(s["name"], None)
            return s, site, None

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(one, resolved))

    max_years = scfg.get("max_years_experience", 2)
    areas = scfg.get("role_areas") or DEFAULT_AREAS
    exclude = scfg.get("exclude_title_words") or DEFAULT_EXCLUDE
    senior = cfg.get("senior_title_words", [])
    excluded_places = cfg.get("excluded_locations", [])
    max_age = scfg.get("max_posting_age_days", 0)
    kept: dict[str, Opportunity] = {}
    dropped: dict[str, int] = {}
    roles_read = 0
    if resolved and all(jobs is None for _, _, jobs in results):
        # Every board failed, so the network was probably down: don't trust this run's "not found"s.
        for name in [n for n, rec in boards.items() if rec.get("checked") == today.isoformat() and not rec.get("id")]:
            del boards[name]
    for s, site, jobs in results:
        if jobs is None:
            stats["errors"] += 1
            continue
        roles_read += len(jobs)
        for job in jobs:
            opp, reason = judge(job, s, site, max_years, areas, exclude, senior, excluded_places, max_age, today)
            if reason:
                dropped[reason] = dropped.get(reason, 0) + 1
            elif opp.key not in kept:
                kept[opp.key] = opp
    stats["roles_read"] = roles_read
    stats["kept"] = len(kept)
    stats["dropped"] = dropped
    log.info("Startups: %d boards read, %d roles, %d kept, dropped %s", len(resolved), roles_read, len(kept), dropped)
    order = {"Graduate / junior role": 0, "Welcomes graduates": 1}
    return sorted(kept.values(), key=lambda o: (order.get(o.graduate_fit, 2), o.company.lower(),
                                                -(o.posted or date.min).toordinal(), o.title))


def judge(job: Job, startup: dict, site: dict, max_years: int, areas: dict, exclude: list[str],
          senior: list[str], excluded_places: list[str], max_age: int, today: date) -> tuple[Opportunity | None, str | None]:
    """(opportunity, None) when the role is kept, (None, reason) when it isn't."""
    title = (job.title or "").strip()
    if not title or not job.url:
        return None, "no title or link"
    if filters.is_internship(title):
        return None, "internship"
    if filters.is_senior(title, senior):
        return None, "too senior"
    area = role_area(title, areas, exclude)
    if not area:
        return None, "not a quant, finance, data or engineering role"
    if filters.is_excluded_location(job.location, excluded_places):
        return None, "excluded country"
    if max_age and job.posted and (today - job.posted).days > max_age:
        return None, "posted too long ago"
    fit = graduate_fit(title, job.description, max_years)
    if not fit:
        return None, "asks for experience"
    sponsor, evidence = filters.sponsorship(job.description)
    if sponsor == "No":
        return None, "no sponsorship"
    return Opportunity(
        title=title, company=startup["name"], location=(job.location or "").strip(), url=job.url,
        firm_type=startup.get("type", "Startup"),
        focus=startup.get("focus", ""), stage=startup.get("stage", ""), hq=startup.get("hq", ""), area=area,
        graduate_fit=fit[0], graduate_evidence=fit[1], years_required=filters.years_required(job.description),
        sponsorship=sponsor, sponsorship_evidence=evidence, remote=filters.is_remote(job.location, title),
        posted=job.posted, platform=site["platform"].title(),
    ), None


def mark_first_seen(opps: list[Opportunity], seen: dict, now: str) -> set[str]:
    """Record when each role was first listed; returns the keys new this run."""
    new = set()
    for o in opps:
        if o.key not in seen:
            seen[o.key] = now
            new.add(o.key)
        o.first_seen = seen[o.key]
    return new


def forget_old(store: dict, listed: set[str], keep_days: int, today: date | None = None) -> None:
    """Drop first-seen dates of roles no longer listed, so the file doesn't grow forever."""
    cutoff = ((today or date.today()) - timedelta(days=keep_days)).isoformat()
    seen = store.get("first_seen", {})
    for key in [k for k, t in seen.items() if t < cutoff and k not in listed]:
        del seen[key]
