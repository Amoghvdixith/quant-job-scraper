"""When runs should start, from email_times in config.yaml.

  python -m jobscraper.schedule due    prints "true" if no email has gone out for the latest slot
  python -m jobscraper.schedule wait   prints the seconds until the next run should start
"""
from __future__ import annotations

import sys
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parent.parent
LAST_EMAIL = ROOT / "data" / "last_email_utc"


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
        print(int((next_start(cfg, now) - now).total_seconds()) + 5)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
