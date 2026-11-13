import io
from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook

from jobscraper import sponsor_registers as sr
from jobscraper.excel import write_workbook
from jobscraper.mailer import _table
from jobscraper.models import Job


def _foi_workbook() -> bytes:
    """Same layout as the Home Office annex to FOI 2025/12841."""
    wb = Workbook()
    for i, (title, rows) in enumerate([
        ("FOI Data - Skilled Worker", [
            ("JPMorgan Chase Bank, National Association", 1415, 1930, 1166, 1515, 6026),
            ("Barclays Bank PLC", 175, 152, 191, 241, 759),
            ("Barclays Bank UK PLC", 24, 21, 14, 15, 74),
            ("Tiny Quant Ltd", "*", None, 6, "*", 9),
        ]),
        ("FOI Data - GBM", [("JPMorgan Chase Bank, National Association", 500, 600, 700, 800, 2600)]),
    ]):
        ws = wb.active if i == 0 else wb.create_sheet()
        ws.title = title
        ws["C2"] = "FOI2025/12841"
        ws["C9"] = "Notes"
        ws["B10"], ws["C10"] = "*", "These figures have been taken from a live operational database."
        ws.append([None, None, "Organisation Name", "2021", "2022", "2023", "2024", "Grand Total"])
        for r in rows:
            ws.append([None, None, *r])
        ws.append([None, None, "Grand Total", 1, 2, 3, 4, 10])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_uk_cos():
    data = sr.parse_uk_cos(_foi_workbook())
    assert data["years"] == [2021, 2022, 2023, 2024]
    assert data["SW"]["jpmorganchase"] == [1415, 1930, 1166, 1515]
    assert data["SW"]["barclays"] == [199, 173, 205, 256]           # both Barclays entities added up
    assert data["SW"]["tinyquant"] == [sr.SUPPRESSED, 0, 6, sr.SUPPRESSED]
    assert data["GBM"]["jpmorganchase"] == [500, 600, 700, 800]
    assert "grandtotal" not in data["SW"] and "organisationname" not in data["SW"]


def test_parse_uk_register_and_h1b():
    csv_text = ("Organisation Name,Town/City,County,Type & Rating,Route\n"
                "Goldman Sachs International,London,,Worker (A rating),Skilled Worker\n"
                "Goldman Sachs International,London,,Worker (A rating),Global Business Mobility: Graduate Trainee\n"
                "Some Charity,Leeds,,Temporary Worker (A rating),Charity Worker\n")
    names, details = sr.parse_uk(csv_text)
    assert names == {"goldmansachs"}
    assert details["goldmansachs"] == "A|GBM Graduate Trainee, Skilled Worker"

    names, counts = set(), {}
    sr.parse_us("Fiscal Year\tEmployer (Petitioner) Name\tInitial Approval\tInitial Denial\tContinuing Approval\n"
                "2025\tGOLDMAN SACHS & CO LLC\t120\t3\t300\n"
                "2025\tGOLDMAN SACHS & CO LLC\t5\t0\t10\n"
                "2025\tNOBODY INC\t0\t1\t0\n", names, counts)
    assert names == {"goldmansachs"}
    assert counts["goldmansachs"] == {"2025": [125, 310]}


def _registers():
    return sr.SponsorRegisters(
        data={"UK": ["jpmorganchase", "barclays", "tinyquant", "newfirm"], "US": ["jpmorganchase"], "NL": ["abnamro"]},
        details={"UK": {"jpmorganchase": "A|GBM Senior or Specialist Worker, Skilled Worker"},
                 "US": {"jpmorganchase": [["2025", 2000, 4000], ["2024", 1800, 3900]]}},
        uk_cos={**sr.parse_uk_cos(_foi_workbook()), "sources": ["Home Office FOI 2025/12841"]},
    )


def test_record_gives_real_numbers_only():
    reg = _registers()
    jpm = reg.record("JPMorgan Chase & Co.")
    assert jpm["uk"] == "Licensed sponsor (A rating): GBM Senior or Specialist Worker, Skilled Worker"
    assert jpm["uk_cos"] == ("2024: 1,515; 2021-2024 total: 6,026 (+ GBM/ICT 2,600) "
                             "[Home Office FOI 2025/12841]")
    assert jpm["us"] == "FY2025: 2,000 new + 4,000 extensions approved (FY2024: 1,800 new)"
    assert reg.record("Tiny Quant")["uk_cos"].startswith("2024: 1-4; 2021-2024 total: at least 8")
    # On the register but not in the FOI figures: never shown as zero.
    assert reg.record("New Firm Ltd")["uk_cos"].startswith("Not found in the 2021-2024 figures")
    unknown = reg.record("Unheard Of Capital")
    assert unknown["uk"] == "Not on the register" and unknown["us"] == "No approved H-1B petitions found"
    assert reg.summary("JPMorgan Chase", "London, UK") == \
        "UK: licensed sponsor, 1,515 CoS in 2024, 6,026 since 2021"
    assert reg.summary("JPMorgan Chase", "New York, NY") == "US H-1B: 2,000 new approvals"


def test_columns_and_email(tmp_path: Path):
    reg = _registers()
    job = Job(source="LinkedIn", title="Quant Analyst", company="JPMorgan Chase", location="London, UK",
              url="https://x/1", posted=date.today())
    rec = reg.record(job.company)
    job.uk_licence, job.uk_sponsored, job.us_h1b = rec["uk"], rec["uk_cos"], rec["us"]
    job.sponsor_summary = reg.summary(job.company, job.location)
    ws = load_workbook(write_workbook([job], set(), {}, tmp_path / "x.xlsx"))["Jobs"]
    headers = [c.value for c in ws[1]]
    row = {h: ws.cell(row=2, column=i + 1).value for i, h in enumerate(headers)}
    assert row["UK People Sponsored (CoS)"].startswith("2024: 1,515")
    assert row["US H-1B Approvals"].startswith("FY2025: 2,000 new")
    assert row["UK Sponsor Licence"].startswith("Licensed sponsor (A rating)")
    assert "6,026 since 2021" in _table([job])
