from datetime import date
from pathlib import Path

from openpyxl import load_workbook

from jobscraper.excel import write_workbook
from jobscraper.mailer import build_email
from jobscraper.sources import hackathons as hk
from jobscraper.sources.hackathons import Hackathon

TODAY = date(2026, 11, 11)


def elig(text):
    return hk.eligibility(text)


def test_eligibility_keeps_graduates():
    assert elig("Open to all industry professionals, academics, and students.") == ("Open to graduates", True)
    assert elig("Global traders; no stated age, education or nationality restriction")[1]
    assert elig("Students and recent graduates (within 2 years) can apply") == ("Open to graduates", True)
    assert elig("Ages 18+ only; Team required; Company/professional organization required")[1]
    assert elig("Worldwide teams of 2–6; no solo entries")[1]
    assert elig("Teams of 2-4; must be 18+") == ("No student requirement stated", True)
    assert elig("") == ("Not stated (check the rules)", True)


def test_eligibility_drops_students_only():
    assert elig("Teams of 2–4 students aged 18+; secondary, bachelor and master students eligible; "
                "PhD conditions apply; acceptance required") == ("Students only", False)
    assert elig("Students only") == ("Students only", False)
    assert elig("Must be currently enrolled at an accredited university") == ("Students only", False)
    assert elig("Open to undergraduate and graduate students") == ("Students only", False)
    assert elig("High school students only; Ages 13+ only") == ("Students only", False)


def test_quant_relevance():
    assert hk.is_quant("Gator Quant Hacks Fintech", strict=True)
    assert hk.is_quant("Build a backtesting engine for stocks", strict=True)
    assert not hk.is_quant("Fintech, Health, Beginner Friendly", strict=True)  # fintech alone is too loose
    assert hk.is_quant("Right! said FRED: Q4 2026 Finance and Economics Challenge", strict=False)
    assert not hk.is_quant("Metaculus Cup Fall 2026 Forecasting", strict=False)


def test_devpost_dates():
    assert hk.devpost_end_date("Oct 16 - 17, 2026") == date(2026, 10, 17)
    assert hk.devpost_end_date("Oct 17, 2026") == date(2026, 10, 17)
    assert hk.devpost_end_date("Jul 18, 2026 - Jan 14, 2027") == date(2027, 1, 14)
    assert hk.devpost_end_date("Oct 30 - Nov 02, 2026") == date(2026, 11, 2)
    assert hk.devpost_end_date("") is None


QC_PAGE = """<html><head><title>Global Quant Trading Challenge | Quant Challenges</title></head><body>
<h1>Global Quant Trading Challenge</h1>
<dl><dt>Category</dt><dd>Algorithmic trading</dd>
<dt>Who / prerequisites</dt><dd>Global traders; no stated age, education or nationality restriction</dd>
<dt>Deadline</dt><dd>15 Dec 2026, 23:59 UTC</dd>
<dt>Status</dt><dd>Open</dd><dt>Entry availability</dt><dd>Accepting entries</dd>
<dt>Organizer</dt><dd>ALGOGENE FINTECH CO. LTD.</dd><dt>Participation</dt><dd>Online</dd>
<dt>Total prize pool</dt><dd>$100K</dd></dl>
<h2>Who can enter</h2><p>Global traders; no stated age, education or nationality restriction</p>
</body></html>"""


def test_parse_quant_challenges_page():
    h = hk.parse_qc_page(QC_PAGE, "https://quantchallenges.com/challenges/x-qc-1", TODAY)
    assert h.title == "Global Quant Trading Challenge"
    assert h.organiser == "ALGOGENE FINTECH CO. LTD."
    assert h.category == "Algorithmic trading"
    assert h.deadline == date(2026, 12, 15)
    assert h.format == "Online" and h.prize == "$100K"
    assert "no stated age" in h.eligibility_text
    assert hk.rule_broken(h, TODAY) is None
    assert h.eligibility == "Open to graduates" and "trading" in h.quant_link


def qc(title, who="Open to anyone", status="Open", deadline=None, category="Algorithmic trading"):
    return Hackathon(title=title, url=f"https://x/{title}", source="Quant Challenges", category=category,
                     eligibility_text=who, status=status, deadline=deadline)


def test_rules():
    assert hk.rule_broken(qc("A", who="Undergraduate students only"), TODAY) == "students only"
    assert hk.rule_broken(qc("B", category="Forecasting"), TODAY) == "not quant finance"
    assert hk.rule_broken(qc("C", status="Applications open · Entries closed · check next cycle"), TODAY) == "closed"
    assert hk.rule_broken(qc("D", deadline=date(2026, 10, 6)), TODAY) == "deadline passed"
    assert hk.rule_broken(qc("E", deadline=date(2026, 12, 1)), TODAY) is None


def test_collect_merges_sources_and_drops(monkeypatch):
    def fake_qc(cfg, stats, cache, today):
        return [qc("Numerai Tournament"), qc("Student Cup", who="University students only"),
                qc("Global Quant Trading Challenge", deadline=date(2027, 1, 31))]

    def fake_devpost(cfg, stats, cache, today):
        h = Hackathon(title="Market Making Hack", url="https://mm.devpost.com/", source="Devpost",
                      eligibility_text="Ages 18+ only", deadline=date(2026, 12, 5))
        h.quant_link = "market making"
        other = Hackathon(title="Health Hack", url="https://hh.devpost.com/", source="Devpost",
                          eligibility_text="Ages 18+ only")
        return [h, other]

    monkeypatch.setattr(hk, "quant_challenges", fake_qc)
    monkeypatch.setattr(hk, "devpost", fake_devpost)
    manual = [{"title": "Numerai Tournament", "url": "https://numer.ai/tournament", "organiser": "Numerai",
               "category": "Hedge fund stock market prediction", "eligibility": "Open to anyone"}]
    stats = {}
    got = hk.collect({"hackathons": {}}, stats, {}, manual, TODAY)
    titles = [h.title for h in got]
    assert titles == ["Market Making Hack", "Global Quant Trading Challenge", "Numerai Tournament"]
    assert stats["dropped"] == {"students only": 1, "not quant finance": 1}
    seen = {}
    assert hk.mark_first_seen(got, seen, "2026-11-11T00:00:00") == {h.key for h in got}
    assert hk.mark_first_seen(got, seen, "2026-11-12T00:00:00") == set()


def test_hackathons_sheet_and_email(tmp_path: Path):
    hacks = [Hackathon(title="Global Quant Trading Challenge", url="https://quantchallenges.com/c/x-qc-1",
                       source="Quant Challenges", organiser="ALGOGENE", eligibility="Open to graduates",
                       eligibility_text="Global traders", quant_link="trading", dates="15 Dec 2026",
                       deadline=date(2026, 12, 15), format="Online", prize="$100K", status="Open")]
    new = {hacks[0].key}
    path = write_workbook([], set(), {}, tmp_path / "x.xlsx", hacks, new)
    wb = load_workbook(path)
    assert "Hackathons" in wb.sheetnames
    ws = wb["Hackathons"]
    assert ws.cell(row=1, column=2).value == "Hackathon"
    assert ws.cell(row=2, column=1).value == "NEW"
    assert ws.cell(row=2, column=2).value == "Global Quant Trading Challenge"
    assert ws.cell(row=2, column=15).hyperlink.target == "https://quantchallenges.com/c/x-qc-1"
    msg = build_email([], set(), {}, path, "a@x", "b@x", 5, hacks, new)
    body = msg.get_body(("html",)).get_content()
    assert "quant finance hackathons graduates can enter" in body
    assert "Global Quant Trading Challenge" in body
    # Without hackathons the workbook has no such sheet (older callers keep working).
    assert "Hackathons" not in load_workbook(write_workbook([], set(), {}, tmp_path / "y.xlsx")).sheetnames
