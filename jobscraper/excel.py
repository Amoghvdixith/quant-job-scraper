from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .models import Job

COLUMNS = [
    ("New", 7), ("Tier", 6), ("Category", 22), ("Matched Role", 30), ("Job Title", 45),
    ("Company", 28), ("On Your Target List", 22), ("Location", 30), ("Work Type", 11), ("Posted", 11), ("Days Old", 9), ("Source", 18),
    ("Visa Sponsorship", 16), ("Employer On Sponsor List", 22), ("Years Exp. Asked", 15), ("Qualification Asked", 16),
    ("Apply Link", 60), ("Apply On", 18), ("Job Listing", 12), ("Tailor CV", 12), ("Apply With Claude", 14), ("Posted By", 18), ("Description Checked", 12), ("Sponsorship Evidence", 60),
]
HEADER_FILL = PatternFill("solid", fgColor="1F3864")
NEW_FILL = PatternFill("solid", fgColor="E2EFDA")
YES_FILL = PatternFill("solid", fgColor="C6EFCE")


HACKATHON_COLUMNS = [
    ("New", 7), ("Hackathon", 45), ("Organiser", 26), ("Focus", 34), ("Quant Link", 28),
    ("Graduates Can Enter", 22), ("Eligibility (organiser's words)", 55), ("Dates / Deadline", 34),
    ("Deadline", 11), ("Days Left", 9), ("Format", 18), ("Prize", 30), ("Status", 26), ("Found On", 16),
    ("Link", 12),
]


STARTUP_COLUMNS = [
    ("New", 7), ("Role", 45), ("Firm", 24), ("Firm Type", 11), ("What They Do", 40), ("Stage", 14), ("HQ", 18),
    ("Area", 20), ("Location", 30), ("Work Type", 11), ("Graduate Fit", 24), ("Why (posting's words)", 50),
    ("Years Exp. Asked", 15), ("Visa Sponsorship", 16), ("Employer On Sponsor List", 22), ("Posted", 11),
    ("Days Old", 9), ("Found On", 16), ("Apply", 12),
]


def write_workbook(jobs: list[Job], new_keys: set[str], stats: dict, path: Path,
                   hackathons: list | None = None, new_hackathons: set[str] | None = None,
                   startups: list | None = None, new_startups: set[str] | None = None) -> Path:
    wb = Workbook()
    _jobs_sheet(wb.active, "Jobs", jobs, new_keys)
    _jobs_sheet(wb.create_sheet("Remote Jobs"), "Remote Jobs", [j for j in jobs if j.remote], new_keys)
    _jobs_sheet(wb.create_sheet("Graduate Schemes"), "Graduate Schemes", [j for j in jobs if j.graduate_scheme], new_keys)
    _jobs_sheet(wb.create_sheet("Internships"), "Internships", [j for j in jobs if j.internship], new_keys)
    _jobs_sheet(wb.create_sheet("Government Jobs"), "Government Jobs", [j for j in jobs if j.government], new_keys)
    if hackathons is not None:
        _hackathons_sheet(wb.create_sheet("Hackathons"), hackathons, new_hackathons or set())
    if startups is not None:
        _startups_sheet(wb.create_sheet("Startups & Boutiques"), startups, new_startups or set())
    _summary_sheet(wb, jobs, new_keys, stats, hackathons, startups)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


def _jobs_sheet(ws, title: str, jobs: list[Job], new_keys: set[str]) -> None:
    ws.title = title
    ws.append([c for c, _ in COLUMNS])
    for i, (_, width) in enumerate(COLUMNS, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
        cell = ws.cell(row=1, column=i)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    today = date.today()
    for job in jobs:
        is_new = job.key in new_keys
        ws.append([
            "NEW" if is_new else "",
            job.tier,
            job.category,
            job.role_title,
            job.title,
            job.company,
            job.target_firm,
            job.location,
            "Remote" if job.remote else "",
            job.posted,
            (today - job.posted).days if job.posted else None,
            ", ".join(job.sources or [job.source]),
            job.sponsorship,
            job.employer_sponsor or "Not found",
            job.years_required,
            job.qualification or "",
            job.apply_link,
            job.apply_on,
            "View",
            "Tailor CV",
            "Apply with Claude",
            "Recruitment agency" if job.recruiter else "Employer",
            "Yes" if job.description_checked else "No",
            job.sponsorship_evidence,
        ])
        row = ws.max_row
        link = ws.cell(row=row, column=17)
        link.hyperlink = job.apply_link
        link.font = Font(color="0563C1", underline="single")
        listing = ws.cell(row=row, column=19)
        listing.hyperlink = job.url
        listing.font = Font(color="0563C1", underline="single")
        tailor = ws.cell(row=row, column=20)
        tailor.hyperlink = job.tailor_link()
        tailor.font = Font(color="0563C1", underline="single")
        assist = ws.cell(row=row, column=21)
        assist.hyperlink = job.assist_apply_link()
        assist.font = Font(color="0563C1", underline="single")
        ws.cell(row=row, column=10).number_format = "yyyy-mm-dd"
        if is_new:
            ws.cell(row=row, column=1).fill = NEW_FILL
        if job.sponsorship == "Yes":
            ws.cell(row=row, column=13).fill = YES_FILL
        if job.employer_sponsor:
            ws.cell(row=row, column=14).fill = YES_FILL
        if job.target_firm:
            ws.cell(row=row, column=7).fill = YES_FILL
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def _hackathons_sheet(ws, hackathons: list, new_keys: set[str]) -> None:
    """Quant finance hackathons graduates can enter: a page of its own, not a job list."""
    ws.title = "Hackathons"
    ws.append([c for c, _ in HACKATHON_COLUMNS])
    for i, (_, width) in enumerate(HACKATHON_COLUMNS, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
        cell = ws.cell(row=1, column=i)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    today = date.today()
    for h in hackathons:
        is_new = h.key in new_keys
        ws.append([
            "NEW" if is_new else "", h.title, h.organiser, h.category, h.quant_link,
            h.eligibility, h.eligibility_text, h.dates, h.deadline,
            (h.deadline - today).days if h.deadline else None,
            h.format, h.prize, h.status, h.source, "Open",
        ])
        row = ws.max_row
        link = ws.cell(row=row, column=15)
        link.hyperlink = h.url
        link.font = Font(color="0563C1", underline="single")
        ws.cell(row=row, column=9).number_format = "yyyy-mm-dd"
        if is_new:
            ws.cell(row=row, column=1).fill = NEW_FILL
        if h.eligibility == "Open to graduates":
            ws.cell(row=row, column=6).fill = YES_FILL
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def _startups_sheet(ws, opps: list, new_keys: set[str]) -> None:
    """Open roles at quant and fintech startups and boutique firms that a recent graduate could get."""
    ws.title = "Startups & Boutiques"
    ws.append([c for c, _ in STARTUP_COLUMNS])
    for i, (_, width) in enumerate(STARTUP_COLUMNS, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
        cell = ws.cell(row=1, column=i)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    col = {name: i for i, (name, _) in enumerate(STARTUP_COLUMNS, 1)}
    today = date.today()
    for o in opps:
        is_new = o.key in new_keys
        ws.append([
            "NEW" if is_new else "", o.title, o.company, o.firm_type, o.focus, o.stage, o.hq, o.area, o.location,
            "Remote" if o.remote else "On-site/Hybrid", o.graduate_fit, o.graduate_evidence,
            o.years_required, o.sponsorship, o.employer_sponsor, o.posted,
            (today - o.posted).days if o.posted else None, o.platform, "Apply",
        ])
        row = ws.max_row
        link = ws.cell(row=row, column=col["Apply"])
        link.hyperlink = o.url
        link.font = Font(color="0563C1", underline="single")
        ws.cell(row=row, column=col["Posted"]).number_format = "yyyy-mm-dd"
        if is_new:
            ws.cell(row=row, column=1).fill = NEW_FILL
        if o.graduate_fit in ("Graduate / junior role", "Welcomes graduates"):
            ws.cell(row=row, column=col["Graduate Fit"]).fill = YES_FILL
        if o.sponsorship == "Yes":
            ws.cell(row=row, column=col["Visa Sponsorship"]).fill = YES_FILL
        if (o.employer_sponsor or "").startswith("Yes"):
            ws.cell(row=row, column=col["Employer On Sponsor List"]).fill = YES_FILL
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def _summary_sheet(wb, jobs: list[Job], new_keys: set[str], stats: dict, hackathons: list | None = None,
                   startups: list | None = None) -> None:
    summary = wb.create_sheet("Run Summary")
    summary.column_dimensions["A"].width = 34
    summary.column_dimensions["B"].width = 18
    rows = [
        ("Run time (UTC)", datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M")),
        ("Jobs in this sheet", len(jobs)),
        ("New since last email", len(new_keys)),
        ("Offer visa sponsorship", sum(j.sponsorship == "Yes" for j in jobs)),
        ("At your target institutions", sum(bool(j.target_firm) for j in jobs)),
        ("Remote", sum(j.remote for j in jobs)),
        ("Graduate schemes", sum(j.graduate_scheme for j in jobs)),
        ("Internships", sum(j.internship for j in jobs)),
        ("UK government (NHS / Civil Service)", sum(bool(j.government) for j in jobs)),
        ("Posted by recruitment agencies", sum(j.recruiter for j in jobs)),
        ("Quant hackathons open to graduates", len(hackathons) if hackathons is not None else "not searched"),
        ("Startup & boutique roles for graduates", len(startups) if startups is not None else "not searched"),
        ("", ""),
        ("Source", "Jobs found this run"),
    ]
    rows += [(name, s["found"]) for name, s in stats.items()]
    rows += [("", ""), ("Source", "Failed requests")]
    rows += [(name, s["errors"]) for name, s in stats.items()]
    for r in rows:
        summary.append(list(r))
        if r[0] == "Source":
            for cell in summary[summary.max_row]:
                cell.font = Font(bold=True)
