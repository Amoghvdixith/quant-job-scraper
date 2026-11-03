"""Tests for the fixes in docs/problems_and_fixes.md."""
from datetime import datetime, timezone
from pathlib import Path

import yaml

from jobscraper import schedule
from jobscraper.models import Job
from jobscraper.sponsor_registers import COUNTRIES, SponsorRegisters

ROOT = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((ROOT / "config.yaml").read_text())


def _day_slots(day):
    """Slot numbers of every run that starts on this UTC day."""
    starts = [s for s in schedule.run_starts(CFG, day) if s.date() == day.date()]
    return [schedule.slot_number(CFG, s) for s in starts]


def test_every_run_of_a_day_gets_its_own_slot():
    for day in (datetime(2026, 11, 3, 12, tzinfo=timezone.utc), datetime(2026, 7, 3, 12, tzinfo=timezone.utc)):
        slots = _day_slots(day)
        assert len(slots) == len(set(slots)) == len(CFG["email_times"])
        assert sorted(slots) == list(range(min(slots), min(slots) + len(slots)))


def test_slot_moves_on_by_one_each_run():
    now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
    starts = schedule.run_starts(CFG, now)
    numbers = [schedule.slot_number(CFG, s) for s in starts[3:9]]
    assert numbers == list(range(numbers[0], numbers[0] + 6))


def test_same_job_in_two_countries_is_two_jobs():
    london = Job("LinkedIn", "Market Risk Analyst", "Barclays", "London, England, United Kingdom", "u1")
    new_york = Job("LinkedIn", "Market Risk Analyst", "Barclays", "New York, NY", "u2")
    indeed_london = Job("Indeed", "Market Risk Analyst", "Barclays PLC", "London", "u3")
    assert london.key != new_york.key
    assert london.key == indeed_london.key


def _old_on(regs, country, key):
    names = regs.lists[country]
    return key in names or (len(key) >= 6 and any(n.startswith(key) for n in names if len(n) - len(key) <= 12))


def test_fast_sponsor_lookup_gives_the_same_answers():
    regs = SponsorRegisters.__new__(SponsorRegisters)
    regs.lists = {"UK": {"goldmansachsandco", "barclays", "hsbc", "averyveryverylongnamethatgoeson"},
                  "US": {"goldmansachs", "jpmorganchase"}, "NL": {"abnamro"}}
    regs.loaded = {c: True for c in COUNTRIES}
    for key in ["goldmansachs", "goldma", "barclays", "hsbc", "jpmorgan", "averyvery", "abnamro", "nobody", "abn"]:
        for c in COUNTRIES:
            assert regs._on(c, key) == _old_on(regs, c, key), (c, key)
    assert regs.status("Goldman Sachs", "London, UK") == "Yes (UK register)"
    assert regs.status("Goldman Sachs", "Singapore") == "Sponsors in UK/US"
