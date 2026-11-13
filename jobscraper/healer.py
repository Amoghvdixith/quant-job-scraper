"""Problem solver: notices what goes wrong during a run, fixes or works around it, and writes it down.

What it handles:
- A search that throws (timeout, connection reset, parse error) is tried once more after a pause.
- A site that keeps failing within a run is "tripped": its remaining searches are skipped so it
  stops eating the time budget, and the run carries on with the other sites.
- A careers site that has failed on several runs in a row is rested for a few days, then tried again.
- A source that suddenly returns nothing when it normally returns plenty is flagged as a likely
  block or page-layout change (code can't rewrite a scraper by itself; this says where to look).
- The email is retried with backoff; if it still fails, the jobs are not marked as emailed, so the
  next run sends them.

Everything is saved to data/health.json (state between runs) and data/HEALTH.md (a readable report,
meant to be synced into the "Performance Analizer" Claude project).
"""
from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

log = logging.getLogger("jobscraper.healer")

KEEP_RUNS = 40
RETRY_PAUSE_SECONDS = 5
TRIP_AFTER_FAILURES = 5           # failures in a row within one run before a site's remaining searches are skipped
REST_AFTER_FAILED_RUNS = 3        # runs in a row a careers site fails before it is rested
REST_DAYS = 3
DROP_ALERT_SHARE = 0.2            # "found" below 20% of the usual figure counts as a sudden drop
MIN_USUAL_FOR_ALERT = 20          # ignore sources that normally find very little


@dataclass
class Event:
    kind: str        # "fixed" (handled, no action needed) or "problem" (needs a look)
    area: str        # e.g. "LinkedIn", "Careers sites | Barclays", "Email"
    what: str
    action: str

    def as_dict(self) -> dict:
        return {"kind": self.kind, "area": self.area, "what": self.what, "action": self.action}


@dataclass
class Healer:
    path: Path
    sleep: Callable[[float], None] = time.sleep
    today: date = field(default_factory=date.today)
    state: dict = field(default_factory=dict)
    events: list[Event] = field(default_factory=list)
    _streak: dict[str, int] = field(default_factory=dict)
    _tripped: set[str] = field(default_factory=set)
    _skipped: dict[str, int] = field(default_factory=dict)
    _site_results: dict[str, bool] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @classmethod
    def load(cls, path: Path, **kwargs) -> "Healer":
        h = cls(path=path, **kwargs)
        try:
            h.state = json.loads(path.read_text()) if path.exists() else {}
        except (OSError, ValueError) as e:
            h.state = {}
            h.record("fixed", "Problem solver", f"data/health.json could not be read ({e})", "started a fresh one")
        h.state.setdefault("runs", [])
        h.state.setdefault("sites", {})
        return h

    def record(self, kind: str, area: str, what: str, action: str) -> None:
        with self._lock:
            self.events.append(Event(kind, area, what, action))
        (log.info if kind == "fixed" else log.warning)("problem solver | %s | %s -> %s", area, what, action)

    # ---- searches ---------------------------------------------------------------------------

    def call(self, label: str, name: str, fn: Callable, stat: dict):
        """Runs one search. Returns its results, [] if skipped, or None if it failed even after a retry."""
        if label in self._tripped:
            with self._lock:
                self._skipped[label] = self._skipped.get(label, 0) + 1
            return []
        try:
            out = fn(stat)
        except Exception as first:
            self.sleep(RETRY_PAUSE_SECONDS)
            try:
                out = fn(stat)
            except Exception as second:
                self._failed(label, name, second)
                return None
            self.record("fixed", label, f"'{name}' failed ({_short(first)})", "worked on a second try")
        with self._lock:
            self._streak[label] = 0
        return out

    def _failed(self, label: str, name: str, err: Exception) -> None:
        with self._lock:
            self._streak[label] = self._streak.get(label, 0) + 1
            trip = self._streak[label] >= TRIP_AFTER_FAILURES and label not in self._tripped
            if trip:
                self._tripped.add(label)
        log.warning("%s | %s failed twice: %s", label, name, err)
        if trip:
            self.record("problem", label, f"{TRIP_AFTER_FAILURES} searches in a row failed (last: {_short(err)})",
                        "skipped its remaining searches this run so the other sites still finish in time")

    # ---- careers sites ----------------------------------------------------------------------

    def site_resting(self, site: str) -> bool:
        rec = self.state["sites"].get(site, {})
        until = rec.get("rest_until")
        return bool(until and until > self.today.isoformat())

    def call_site(self, site: str, fn: Callable, stat: dict):
        """One careers site: results, [] if resting, None if it failed. Repeated failures across runs start a rest."""
        if self.site_resting(site):
            with self._lock:
                self._skipped["Careers sites (resting)"] = self._skipped.get("Careers sites (resting)", 0) + 1
            return []
        try:
            out = fn(stat)
        except Exception as first:
            self.sleep(RETRY_PAUSE_SECONDS)
            try:
                out = fn(stat)
            except Exception as second:
                log.warning("Careers sites | %s failed twice: %s", site, second)
                with self._lock:
                    self._site_results[site] = False
                self._site_failed(site, second)
                return None
            self.record("fixed", f"Careers sites | {site}", f"failed ({_short(first)})", "worked on a second try")
        with self._lock:
            self._site_results[site] = True
        return out

    def _site_failed(self, site: str, err: Exception) -> None:
        with self._lock:
            rec = self.state["sites"].setdefault(site, {})
            rec["failed_runs"] = rec.get("failed_runs", 0) + 1
            rec["last_error"] = _short(err)
            rest = rec["failed_runs"] >= REST_AFTER_FAILED_RUNS
            if rest:
                rec["rest_until"] = (self.today + timedelta(days=REST_DAYS)).isoformat()
                rec["failed_runs"] = 0
        if rest:
            self.record("problem", f"Careers sites | {site}",
                        f"failed on {REST_AFTER_FAILED_RUNS} runs in a row (last: {_short(err)})",
                        f"resting it until {rec['rest_until']}, then it is tried again; "
                        "if it keeps failing, check its entry in careers_sites_manual.yaml")

    # ---- after the searches -----------------------------------------------------------------

    def check_sources(self, stats: dict) -> None:
        """Flags sources that suddenly found far less than usual, and notes what was skipped."""
        for label, n in sorted(self._skipped.items()):
            if label == "Careers sites (resting)":
                self.record("fixed", "Careers sites", f"{n} sites are resting after repeated failures",
                            "skipped this run; each is retried when its rest ends")
            else:
                self.record("fixed", label, f"{n} searches skipped after the site kept failing",
                            "they run again next time")
        for site, ok in self._site_results.items():
            rec = self.state["sites"].get(site)
            if ok and rec:
                if rec.get("rest_until") and rec["rest_until"] <= self.today.isoformat():
                    self.record("fixed", f"Careers sites | {site}", "came back after a rest", "back in every run")
                self.state["sites"].pop(site, None)
        for label, s in stats.items():
            usual = self.usual_found(label)
            if usual is None or usual < MIN_USUAL_FOR_ALERT:
                continue
            if s.get("found", 0) < usual * DROP_ALERT_SHARE:
                self.record("problem", label,
                            f"found {s.get('found', 0)} jobs; it usually finds about {usual}",
                            "likely blocked or the site changed its page layout; the run carried on with the "
                            "other sources. If it repeats next run, its scraper in jobscraper/sources needs a fix")

    def usual_found(self, label: str) -> int | None:
        figures = [r["sources"][label]["found"] for r in self.state["runs"][-10:]
                   if label in r.get("sources", {})]
        if len(figures) < 3:
            return None
        figures.sort()
        return figures[len(figures) // 2]

    # ---- email ------------------------------------------------------------------------------

    def send_email(self, send: Callable[[], None], attempts: int = 3) -> bool:
        for i in range(attempts):
            try:
                send()
            except Exception as e:
                if i + 1 < attempts:
                    self.sleep(30 * (i + 1))
                    continue
                self.record("problem", "Email", f"sending failed {attempts} times ({_short(e)})",
                            "jobs were not marked as emailed, so the next run sends them; the Excel file is "
                            "kept on the run page. Check the GMAIL_APP_PASSWORD secret if this repeats")
                return False
            if i:
                self.record("fixed", "Email", f"sending failed {i} time(s)", "sent on a later try")
            return True
        return False

    def guard(self, area: str, fn: Callable, fallback, action: str):
        """Runs one optional step; on failure records it and returns `fallback` so the run continues."""
        try:
            return fn()
        except Exception as e:
            self.record("problem", area, f"failed ({_short(e)})", action)
            return fallback

    # ---- saving -----------------------------------------------------------------------------

    def save(self, stats: dict, summary: dict) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        run = {"utc": now, "sources": stats, "summary": summary, "events": [e.as_dict() for e in self.events]}
        self.state["runs"] = (self.state["runs"] + [run])[-KEEP_RUNS:]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.state, indent=1, sort_keys=True))
        (self.path.parent / "HEALTH.md").write_text(self.report())

    def email_section(self) -> str:
        """Short HTML for the digest email; empty when nothing happened."""
        if not self.events:
            return ""
        import html
        items = "".join(
            f"<li><b>{'Needs a look' if e.kind == 'problem' else 'Fixed'}:</b> {html.escape(e.area)}: "
            f"{html.escape(e.what)}. {html.escape(e.action[0].upper() + e.action[1:])}.</li>"
            for e in sorted(self.events, key=lambda e: e.kind != "problem")[:15])
        return f"<p><b>Run health</b> (full report in data/HEALTH.md):</p><ul style='font-size:13px'>{items}</ul>"

    def report(self) -> str:
        runs = self.state["runs"]
        last = runs[-1] if runs else {"utc": "never", "sources": {}, "summary": {}, "events": []}
        problems = [e for e in last["events"] if e["kind"] == "problem"]
        fixed = [e for e in last["events"] if e["kind"] == "fixed"]
        lines = [
            "# Quant job scraper: health report",
            "",
            "Written by the problem solver (`jobscraper/healer.py`) at the end of every run. "
            "Sync this file into the Performance Analizer Claude project to track it there.",
            "",
            f"Last run: {last['utc']}",
            "",
            "## Status",
            "",
            ("Healthy: nothing went wrong." if not last["events"] else
             f"{len(problems)} problem(s) need a look, {len(fixed)} handled automatically."),
            "",
        ]
        if last.get("summary"):
            s = last["summary"]
            lines += [f"Jobs in email: {s.get('jobs_in_email', '?')}, new: {s.get('new_jobs', '?')}, "
                      f"raw results: {s.get('raw_results', '?')}, emailed: {s.get('emailed', '?')}.", ""]
        lines += ["## Needs a look", ""]
        lines += [f"- **{e['area']}**: {e['what']}. {_cap(e['action'])}." for e in problems] or ["- Nothing."]
        lines += ["", "## Fixed automatically", ""]
        lines += [f"- **{e['area']}**: {e['what']}. {_cap(e['action'])}." for e in fixed] or ["- Nothing."]
        resting = {k: v for k, v in self.state["sites"].items() if v.get("rest_until", "") > self.today.isoformat()}
        lines += ["", "## Careers sites resting", ""]
        lines += [f"- {k}: until {v['rest_until']} (last error: {v.get('last_error', '?')})"
                  for k, v in sorted(resting.items())] or ["- None."]
        labels = sorted({l for r in runs[-10:] for l in r.get("sources", {})})
        if labels:
            recent = runs[-10:]
            lines += ["", "## Jobs found per source, last runs (oldest first)", "",
                      "| Source | " + " | ".join(r["utc"][5:16].replace("T", " ") for r in recent) + " |",
                      "|---|" + "---|" * len(recent)]
            for l in labels:
                cells = []
                for r in recent:
                    s = r.get("sources", {}).get(l)
                    cells.append("-" if s is None else f"{s['found']}" + (f" ({s['errors']} err)" if s.get("errors") else ""))
                lines.append(f"| {l} | " + " | ".join(cells) + " |")
        counts: dict[str, int] = {}
        for r in runs:
            for e in r["events"]:
                if e["kind"] == "problem":
                    counts[e["area"]] = counts.get(e["area"], 0) + 1
        lines += ["", f"## Most frequent problems, last {len(runs)} runs", ""]
        lines += [f"- {a}: {n} run(s)" for a, n in sorted(counts.items(), key=lambda x: -x[1])[:10]] or ["- None."]
        return "\n".join(lines) + "\n"


def _short(e: Exception) -> str:
    text = f"{type(e).__name__}: {e}"
    return text if len(text) <= 160 else text[:157] + "..."


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]
