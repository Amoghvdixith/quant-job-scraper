from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from openpyxl import load_workbook

from jobscraper.excel import write_workbook
from jobscraper.mailer import _table
from jobscraper.models import Job


def _job(desc=""):
    return Job(source="LinkedIn", title="Quant Analyst & Researcher", company="Acme Capital",
               location="London, UK", url="https://www.linkedin.com/jobs/view/1",
               apply_url="https://acme.example/jobs/1?a=1&b=2", posted=date.today(), description=desc)


def _prompt(link):
    assert link.startswith("https://claude.ai/new?q=")
    return parse_qs(urlparse(link).query)["q"][0]


def test_tailor_link_has_job_details():
    q = _prompt(_job().tailor_link())
    assert q.startswith("/cv-tailoring")
    assert "Quant Analyst & Researcher" in q and "Acme Capital" in q and "London, UK" in q
    assert "https://acme.example/jobs/1?a=1&b=2" in q
    assert "https://www.linkedin.com/jobs/view/1" in q


def test_tailor_link_adds_description_within_limit():
    desc = "Build pricing models in Python. " * 400
    for limit in (2000, 6000):
        link = _job(desc).tailor_link(max_len=limit)
        assert len(link) <= limit
        assert "Build pricing models" in _prompt(link)
    assert len(_job(desc).tailor_link(max_len=6000)) > len(_job(desc).tailor_link())


def test_tailor_link_in_email_and_excel(tmp_path: Path):
    job = _job("Some description")
    assert "Tailor CV" in _table([job])
    path = write_workbook([job], {job.key}, {}, tmp_path / "jobs.xlsx")
    ws = load_workbook(path)["Jobs"]
    headers = [c.value for c in ws[1]]
    cell = ws.cell(row=2, column=headers.index("Tailor CV") + 1)
    assert cell.value == "Tailor CV"
    assert cell.hyperlink.target == job.tailor_link()


def test_assist_apply_link():
    job = _job("Build pricing models in Python. " * 400)
    link = job.assist_apply_link()
    assert len(link) <= 2000
    q = _prompt(link)
    assert q.startswith("/apply-assistant")
    assert "stop before Submit" in q
    assert "https://acme.example/jobs/1?a=1&b=2" in q
    assert "Apply with Claude" in _table([job])


def test_assist_apply_link_in_excel(tmp_path: Path):
    job = _job()
    ws = load_workbook(write_workbook([job], set(), {}, tmp_path / "jobs.xlsx"))["Jobs"]
    headers = [c.value for c in ws[1]]
    cell = ws.cell(row=2, column=headers.index("Apply With Claude") + 1)
    assert cell.hyperlink.target == job.assist_apply_link()
    # Columns after the new ones still line up with their headers.
    assert ws.cell(row=2, column=headers.index("Posted By") + 1).value == "Employer"


def test_descriptions_kept_between_runs(tmp_path, monkeypatch):
    from jobscraper import main
    monkeypatch.setattr(main, "DESCRIPTIONS", tmp_path / "descriptions.json")
    assert main.load_descriptions() == {}
    main.save_descriptions({"k": main._clean_description("Price  swaps\n in Python. " * 1000)})
    saved = main.load_descriptions()["k"]
    assert saved.startswith("Price swaps in Python.") and len(saved) == main.DESCRIPTION_CHARS
    assert main._clean_description(f"{main.linkedin.CLOSED_MARKER} gone") == ""
    # A job rebuilt from the saved list gets its ad back, so the link carries it.
    job = _job()
    job.description = saved
    assert "Price swaps in Python." in _prompt(job.tailor_link(max_len=6000))
