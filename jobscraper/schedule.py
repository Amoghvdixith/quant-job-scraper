"""When runs should start, from email_times in config.yaml.

  python -m jobscraper.schedule due    prints "true" if no email has gone out for the latest slot
  python -m jobscraper.schedule wait   prints the seconds until the next run should start
                                       (at most MAX_WAIT_SECONDS)
"""
from __future__ import annotations

import sys
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parent.parent
LAST_EMAIL = ROOT / "data" / "last_email_utc"
# A GitHub job is stopped after 6 hours, and the timer job allows itself 355 minutes. Slots can
# be up to 12 hours apart, so the timer never waits longer than this: when it wakes early, the
# run it starts finds no email due, skips the scrape, and its own timer waits the rest.
MAX_WAIT_SECONDS = 5 * 3600 + 30 * 60


def run_starts(cfg: dict, around: datetime) -> list[datetime]:
    """Run start times (UTC) from yesterday to tomorrow."""
    tz = ZoneInfo(cfg.get("email_timezone", "UTC"))
    lead = timedelta(minutes=cfg.get("run_lead_minutes", 40))
    local_day = around.astimezone(tz).date()
    starts = []
    for offset in (-1, 0, 1):
        day = local_day + timedelta(days=offset)
        for hhmm in cfg["email_times"]:
            h, m = map(int, hhmm.split(":"))
            starts.append(datetime.combine(day, time(h, m), tz).astimezone(timezone.utc) - lead)
    return sorted(starts)


def latest_start(cfg: dict, now: datetime) -> datetime:
    return max(s for s in run_starts(cfg, now) if s <= now)


def next_start(cfg: dict, now: datetime) -> datetime:
    return min(s for s in run_starts(cfg, now) if s > now)


def slot_number(cfg: dict, now: datetime) -> int:
    """A different number for every email slot (day * slots per day + slot index), so each of
    the day's runs searches a different part of the rotation."""
    tz = ZoneInfo(cfg.get("email_timezone", "UTC"))
    lead = timedelta(minutes=cfg.get("run_lead_minutes", 40))
    email = (latest_start(cfg, now) + lead).astimezone(tz)
    times = sorted(cfg["email_times"])
    return email.date().toordinal() * len(times) + times.index(email.strftime("%H:%M"))


def wait_seconds(cfg: dict, now: datetime) -> int:
    return min(int((next_start(cfg, now) - now).total_seconds()) + 5, MAX_WAIT_SECONDS)


def is_due(cfg: dict, now: datetime, last_email: datetime | None) -> bool:
    return last_email is None or last_email < latest_start(cfg, now)


def _last_email() -> datetime | None:
    try:
        return datetime.fromisoformat(LAST_EMAIL.read_text().strip().replace("Z", "+00:00"))
    except (OSError, ValueError):
        return None


def main() -> None:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    now = datetime.now(timezone.utc)
    if sys.argv[1:] == ["due"]:
        print("true" if is_due(cfg, now, _last_email()) else "false")
    elif sys.argv[1:] == ["wait"]:
        print(wait_seconds(cfg, now))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
