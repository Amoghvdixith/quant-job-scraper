"""Quant finance hackathons and trading competitions that graduates (non-students) can enter.

Three inputs, all optional in config.yaml under `hackathons`:

- Quant Challenges (quantchallenges.com): an independent registry of quant trading, financial ML
  and alpha research competitions. Each listing's detail page has labelled fields ("Who can
  enter", "Deadline", "Status", "Organizer"...), which are read as text.
- Devpost: its public JSON search (`/api/hackathons`), Fintech theme plus a few search words.
  Devpost is a general hackathon site, so a hackathon is only kept when its title, themes or page
  mention something quant (trading, portfolio, markets, risk, derivatives...). Eligibility comes
  from the "Who can participate" box on the hackathon's page.
- hackathons.yaml: hand-picked, always-open competitions (Numerai, Crunch...).

A hackathon is dropped when it is only for students (see `eligibility`), is not about quant
finance, or its deadline or event has passed.
"""
from __future__ import annotations

import html as htmllib
import logging
import re
from dataclasses import asdict, dataclass
from datetime import date

from bs4 import BeautifulSoup

from ..http import polite_get, session

log = logging.getLogger(__name__)

QC_BASE = "https://quantchallenges.com"
DEVPOST_API = "https://devpost.com/api/hackathons"


@dataclass
class Hackathon:
    title: str
    url: str
    source: str
    organiser: str = ""
    category: str = ""
    eligibility: str = ""          # "Open to graduates", "No student requirement stated", "Not stated"
    eligibility_text: str = ""     # the wording it was decided from
    quant_link: str = ""           # the quant words that matched
    dates: str = ""                # deadline / event dates as published
    deadline: date | None = None   # last date to enter, when one could be read
    format: str = ""               # Online / In person / Hybrid
    prize: str = ""
    status: str = ""
    first_seen: str = ""

    @property
    def key(self) -> str:
        return re.sub(r"[^a-z0-9]+", "", self.title.lower())

    def to_dict(self) -> dict:
        d = asdict(self)
        d["deadline"] = self.deadline.isoformat() if self.deadline else None
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Hackathon":
        d = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        if d.get("deadline"):
            d["deadline"] = date.fromisoformat(d["deadline"])
        return cls(**d)


# --- Eligibility ---------------------------------------------------------------------------

# Wording that says people who have finished their studies can enter.
OPEN_PATTERNS = [
    r"open to (?:all|everyone|anyone|the public|the general public)",
    r"\banyone\b", r"\beveryone\b", r"\bpublic\b",
    r"\bgraduates?\b", r"\balumni\b", r"\bnon-?students?\b", r"\bprofessionals?\b",
    r"\bindustry\b", r"\bpractitioners?\b", r"\bresearchers\b", r"\bindividuals?\b",
    r"\btraders\b", r"\bdata scientists\b", r"\bdevelopers\b",
    r"no (?:stated )?(?:age, )?education(?:al)? (?:or [a-z]+ )?restriction",
    r"company/professional organi[sz]ation",
    r"\bworldwide\b", r"\bglobal\b", r"\bglobally\b",
]
# Wording that limits entry to current students.
STUDENT_ONLY_PATTERNS = [
    r"students? only", r"only (?:open to |for )?(?:current |enrolled )?(?:university |college |undergraduate |high school )?students",
    r"must be (?:a |an )?(?:current(?:ly)? |enrolled |full-time |registered )+(?:university |college )?students?",
    r"currently enrolled", r"\benrolled (?:at|in) (?:a|an) (?:university|college|accredited)",
    r"valid student (?:id|card|email)", r"\.edu email", r"student status",
    r"(?:undergraduate|high school|secondary school|bachelor|master'?s?|phd|university|college) students",
    r"\bstudents?\b",  # in a focused eligibility box, "students" alone means students
]
# Graduates explicitly allowed even though students are mentioned.
GRAD_EXCEPTIONS = [
    r"\b(?:recent )?graduates?\b", r"\balumni\b", r"\bnon-?students?\b", r"\bprofessionals?\b",
    r"open to (?:all|everyone|anyone)", r"\bno (?:stated )?(?:age, )?education", r"\banyone\b",
    r"\bpractitioners?\b", r"\bindustry\b",
]
# Text such as "best student team prize" or "students welcome" doesn't make an event student-only.
STUDENT_INCIDENTAL = [r"student (?:prize|award|category|track)", r"students? (?:are )?(?:also )?welcome",
                      r"including students", r"and students", r"students? and "]


def eligibility(text: str) -> tuple[str, bool]:
    """(label, keep). `text` should be just the eligibility wording, not the whole page."""
    t = " ".join((text or "").lower().split())
    # "graduate students" / "graduate programme" are students, not people who have graduated.
    t = re.sub(r"\bgraduate (students?|programs?|programmes?|degrees?|school)", r"grad \1", t)
    if not t:
        return "Not stated (check the rules)", True
    grads_ok = any(re.search(p, t) for p in GRAD_EXCEPTIONS)
    stripped = t
    for p in STUDENT_INCIDENTAL:
        stripped = re.sub(p, " ", stripped)
    students_only = any(re.search(p, stripped) for p in STUDENT_ONLY_PATTERNS)
    if students_only and not grads_ok:
        return "Students only", False
    if grads_ok or any(re.search(p, t) for p in OPEN_PATTERNS):
        return "Open to graduates", True
    return "No student requirement stated", True


# --- Quant relevance -----------------------------------------------------------------------

QUANT_WORDS = [
    "quant", "quantitative", "trading", "trader", "algorithmic", "algo trading", "algotrading", "backtest",
    "portfolio", "stock", "equities", "equity market", "market making", "market maker", "order book",
    "derivative", "options pricing", "option pricing", "volatility", "hedge fund", "alpha", "asset pricing",
    "asset management", "investment", "investing", "financial market", "capital market", "market data",
    "market prediction", "returns prediction", "return prediction", "price prediction", "risk model",
    "risk management", "credit risk", "market risk", "fixed income", "bond", "yield curve", "forex", "fx ",
    "crypto trading", "defi", "prediction market", "financial forecasting", "financial machine learning",
    "financial ml", "econometric", "time series", "factor model", "signals", "fintech", "finance",
]
# Single words that are too loose on their own outside a dedicated quant registry.
LOOSE = {"fintech", "finance", "signals", "time series", "alpha", "investment", "investing", "bond", "fx"}


def quant_words(text: str) -> list[str]:
    t = (text or "").lower()
    return [w for w in QUANT_WORDS if re.search(r"(?<![a-z])" + re.escape(w) + r"(?:s|es)?(?![a-z])", t)]


def is_quant(text: str, strict: bool) -> list[str]:
    """Matched words if `text` is about quantitative finance, else []. Strict needs a non-loose word."""
    found = quant_words(text)
    if strict and not any(w not in LOOSE for w in found):
        return []
    return found


# --- Dates -----------------------------------------------------------------------------------

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_DMY = re.compile(r"\b(\d{1,2})\s+([A-Za-z]{3})[a-z]*\.?,?\s+(\d{4})\b")
_MDY = re.compile(r"\b([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})\b")
_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


def dates_in(text: str) -> list[date]:
    out = []
    for d, m, y in _DMY.findall(text or ""):
        if m.lower() in MONTHS:
            out.append(_safe_date(int(y), MONTHS[m.lower()], int(d)))
    for m, d, y in _MDY.findall(text or ""):
        if m.lower() in MONTHS:
            out.append(_safe_date(int(y), MONTHS[m.lower()], int(d)))
    for y, m, d in _ISO.findall(text or ""):
        out.append(_safe_date(int(y), int(m), int(d)))
    return [d for d in out if d]


def _safe_date(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def devpost_end_date(period: str) -> date | None:
    """'Oct 16 - 17, 2026', 'Oct 17, 2026', 'Jul 18, 2026 - Jan 14, 2027', 'Oct 30 - Nov 02, 2026'."""
    p = (period or "").strip()
    if not p:
        return None
    end = p.split(" - ")[-1].strip()
    year = re.search(r"(\d{4})", p)
    if not year:
        return None
    m = re.match(r"([A-Za-z]{3})[a-z]*\s+(\d{1,2}),?\s*(\d{4})?", end)
    if m:
        return _safe_date(int(m.group(3) or year.group(1)), MONTHS.get(m.group(1).lower(), 0), int(m.group(2)))
    m = re.match(r"(\d{1,2}),?\s*(\d{4})", end)  # "17, 2026": same month as the start
    start = re.match(r"([A-Za-z]{3})", p)
    if m and start:
        return _safe_date(int(m.group(2)), MONTHS.get(start.group(1).lower(), 0), int(m.group(1)))
    return None


# --- Quant Challenges ---------------------------------------------------------------------

QC_FIELDS = ["Who can enter", "Who / prerequisites", "Deadline", "Entry date / cadence", "Status",
             "Entry availability", "Organizer", "Participation", "Category", "Total prize pool", "Prize"]
CLOSED_WORDS = ("entries closed", "closed", "ended", "finished", "watch next cycle", "archived")


def qc_listing_urls(s, pages: int, stats: dict) -> list[str]:
    """Detail page links from the "Open now" list, then the main list's first pages."""
    urls: list[str] = []
    listing_pages = [f"{QC_BASE}/challenges/open"] + [
        f"{QC_BASE}/challenges" + (f"?page={n}" if n > 1 else "") for n in range(1, pages + 1)]
    for page in listing_pages:
        r = polite_get(s, page, delay=(0.5, 1.5), retries=2)
        if r is None:
            stats["errors"] += 1
            continue
        for a in BeautifulSoup(r.text, "html.parser").find_all("a", href=True):
            href = a["href"].split("#")[0].split("?")[0]
            if re.search(r"/challenges/[a-z0-9-]+-qc-\d+/?$", href):
                url = href if href.startswith("http") else QC_BASE + href
                if url not in urls:
                    urls.append(url)
    return urls


def page_lines(markup: str) -> list[str]:
    soup = BeautifulSoup(markup, "html.parser")
    for t in soup(["script", "style", "noscript", "svg"]):
        t.decompose()
    return [" ".join(line.split()) for line in soup.get_text("\n").split("\n") if line.strip()]


def labelled_fields(lines: list[str], labels: list[str]) -> dict[str, str]:
    """For "Label" on its own line (or "Label: value"), the value that follows. First one wins."""
    out: dict[str, str] = {}
    lower = [l.lower().rstrip(":") for l in lines]
    for label in labels:
        lab = label.lower()
        for i, l in enumerate(lower):
            if l == lab and i + 1 < len(lines):
                out[label] = lines[i + 1]
                break
            if l.startswith(lab + ":"):
                out[label] = lines[i].split(":", 1)[1].strip()
                break
    return out


def parse_qc_page(markup: str, url: str, today: date) -> Hackathon | None:
    lines = page_lines(markup)
    soup = BeautifulSoup(markup, "html.parser")
    h1 = soup.find("h1")
    title = " ".join((h1.get_text(" ") if h1 else (soup.title.string if soup.title else "")).split())
    title = re.sub(r"\s*[|·–-]\s*Quant Challenges\s*$", "", title)
    if not title:
        return None
    f = labelled_fields(lines, QC_FIELDS)
    who = f.get("Who can enter") or f.get("Who / prerequisites", "")
    dates = f.get("Deadline") or f.get("Entry date / cadence", "")
    status = " · ".join(x for x in (f.get("Status"), f.get("Entry availability")) if x)
    return Hackathon(
        title=title, url=url, source="Quant Challenges", organiser=f.get("Organizer", ""),
        category=f.get("Category", ""), eligibility_text=who, dates=dates,
        deadline=_deadline(dates, today), format=f.get("Participation", ""),
        prize=f.get("Total prize pool") or f.get("Prize", ""), status=status,
    )


def _deadline(text: str, today: date) -> date | None:
    """The last date mentioned (deadline or final event day); None when there is none."""
    found = dates_in(text)
    return max(found) if found else None


def quant_challenges(cfg: dict, stats: dict, cache: dict, today: date) -> list[Hackathon]:
    s = session()
    urls = qc_listing_urls(s, cfg.get("quant_challenges_pages", 3), stats)
    max_reads = cfg.get("quant_challenges_max_reads", 80)
    reread_days = cfg.get("reread_days", 3)
    out, reads = [], 0
    for url in urls:
        prev = cache.get(url)
        if prev and prev.get("checked") and \
                (today - date.fromisoformat(prev["checked"])).days < reread_days:
            out.append(Hackathon.from_dict(prev["hackathon"]))
            continue
        if reads >= max_reads:
            continue
        reads += 1
        r = polite_get(s, url, delay=(0.5, 1.5), retries=2)
        if r is None:
            stats["errors"] += 1
            continue
        h = parse_qc_page(r.text, url, today)
        if h:
            cache[url] = {"checked": today.isoformat(), "hackathon": h.to_dict()}
            out.append(h)
    return out


# --- Devpost ---------------------------------------------------------------------------------

def devpost(cfg: dict, stats: dict, cache: dict, today: date) -> list[Hackathon]:
    s = session()
    found: dict[str, dict] = {}
    queries = [{"themes[]": t} for t in cfg.get("devpost_themes", ["Fintech"])]
    queries += [{"search": w} for w in cfg.get("devpost_search", [])]
    for q in queries:
        for page in range(1, cfg.get("devpost_pages", 2) + 1):
            params = {**q, "status[]": ["upcoming", "open"], "page": page}
            r = polite_get(s, DEVPOST_API, params=params, delay=(0.5, 1.5), retries=2)
            if r is None:
                stats["errors"] += 1
                break
            try:
                rows = r.json().get("hackathons", [])
            except ValueError:
                stats["errors"] += 1
                break
            for h in rows:
                if h.get("url") and not h.get("invite_only"):
                    found.setdefault(h["url"], h)
            if len(rows) < 9:
                break
    out = []
    for url, h in found.items():
        end = devpost_end_date(h.get("submission_period_dates", ""))
        if end and end < today:
            continue  # the API keeps listing some finished hackathons as "upcoming"
        themes = ", ".join(t.get("name", "") for t in h.get("themes", []))
        prev = cache.get(url)
        if prev and prev.get("checked") and (today - date.fromisoformat(prev["checked"])).days < cfg.get("reread_days", 3):
            who, page_text = prev.get("who", ""), prev.get("page_text", "")
        else:
            who, page_text = _devpost_page(s, url, stats)
            cache[url] = {"checked": today.isoformat(), "who": who, "page_text": page_text[:3000]}
        hack = Hackathon(
            title=(h.get("title") or "").strip(), url=url, source="Devpost",
            organiser=(h.get("organization_name") or "").strip(), category=themes,
            eligibility_text=who, dates=h.get("submission_period_dates", ""), deadline=end,
            format=(h.get("displayed_location") or {}).get("location", ""),
            prize=_prize(h), status=(h.get("open_state") or "").capitalize(),
        )
        hack.quant_link = ", ".join(is_quant(f"{hack.title} {themes} {page_text}", strict=True))
        out.append(hack)
    return out


def _prize(h: dict) -> str:
    raw = htmllib.unescape(re.sub(r"<[^>]+>", "", h.get("prize_amount") or ""))
    return "" if re.fullmatch(r"\D*0", raw.strip()) else raw.strip()


def _devpost_page(s, url: str, stats: dict) -> tuple[str, str]:
    """('Who can participate' wording, the page's text) for one Devpost hackathon."""
    r = polite_get(s, url, delay=(0.5, 1.5), retries=2)
    if r is None:
        stats["errors"] += 1
        return "", ""
    lines = page_lines(r.text)
    who = []
    for i, l in enumerate(lines):
        if l.lower().startswith("who can participate"):
            for nxt in lines[i + 1:i + 10]:
                if nxt.lower().startswith(("view full rules", "view schedule", "participants", "join hackathon")):
                    break
                who.append(nxt)
            break
    return "; ".join(who), " ".join(lines)


# --- Putting it together -------------------------------------------------------------------

def collect(cfg: dict, stats: dict, cache: dict, manual: list[dict], today: date | None = None) -> list[Hackathon]:
    """Every hackathon that passes the rules, keyed by title so one listed twice shows once."""
    today = today or date.today()
    hcfg = cfg.get("hackathons", {}) or {}
    sources = hcfg.get("sources", ["quant_challenges", "devpost", "manual"])
    raw: list[Hackathon] = []
    if "manual" in sources:
        for m in manual:
            raw.append(Hackathon(
                title=m["title"], url=m["url"], source="Hand-picked", organiser=m.get("organiser", ""),
                category=m.get("category", ""), eligibility_text=m.get("eligibility", ""),
                dates=m.get("dates", "Ongoing"), deadline=_deadline(m.get("dates", ""), today),
                format=m.get("format", "Online"), prize=m.get("prize", ""), status="Open",
            ))
    for name, fn in (("quant_challenges", quant_challenges), ("devpost", devpost)):
        if name in sources:
            st = stats.setdefault(name, {"found": 0, "errors": 0})
            try:
                got = fn(hcfg, st, cache.setdefault(name, {}), today)
            except Exception as e:
                log.warning("Hackathons | %s failed: %s", name, e)
                st["errors"] += 1
                continue
            st["found"] = len(got)
            raw.extend(got)

    kept: dict[str, Hackathon] = {}
    dropped: dict[str, int] = {}
    for h in raw:
        reason = rule_broken(h, today)
        if reason:
            dropped[reason] = dropped.get(reason, 0) + 1
            continue
        if h.key not in kept or kept[h.key].source == "Devpost":
            kept[h.key] = h
    log.info("Hackathons: %d found, %d kept, dropped %s", len(raw), len(kept), dropped)
    stats["dropped"] = dropped
    return sorted(kept.values(), key=lambda h: (h.deadline is None, h.deadline or date.max, h.title))


def rule_broken(h: Hackathon, today: date) -> str | None:
    label, keep = eligibility(h.eligibility_text)
    h.eligibility = label
    if not keep:
        return "students only"
    if h.source == "Quant Challenges":
        h.quant_link = h.quant_link or ", ".join(is_quant(f"{h.title} {h.category}", strict=False))
    elif h.source == "Hand-picked":
        h.quant_link = h.quant_link or h.category
    if not h.quant_link:
        return "not quant finance"
    status = h.status.lower()
    if any(w in status for w in CLOSED_WORDS) and not any(w in status for w in ("accepting", "open")):
        return "closed"
    if "entries closed" in status:
        return "closed"
    if h.deadline and h.deadline < today:
        return "deadline passed"
    return None


def mark_first_seen(hacks: list[Hackathon], seen: dict, now: str) -> set[str]:
    """Record when each hackathon was first listed; returns the keys new this run."""
    new = set()
    for h in hacks:
        if h.key not in seen:
            seen[h.key] = now
            new.add(h.key)
        h.first_seen = seen[h.key]
    return new
