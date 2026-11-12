from __future__ import annotations

import html
from datetime import date
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from .models import Job


def build_email(jobs: list[Job], new_keys: set[str], stats: dict, attachment: Path, sender: str, to: str,
                max_age_days: int = 5, hackathons: list | None = None,
                new_hackathons: set[str] | None = None, startups: list | None = None,
                new_startups: set[str] | None = None) -> EmailMessage:
    new_jobs = [j for j in jobs if j.key in new_keys]
    msg = EmailMessage()
    msg["Subject"] = f"Quant jobs: {len(new_jobs)} new, {len(jobs)} in the last {max_age_days} days"
    msg["From"] = sender
    msg["To"] = to

    source_line = ", ".join(
        f"{name} {s['found']}" + (f" ({s['errors']} failed requests)" if s["errors"] else "")
        for name, s in stats.items()
    )
    remote = [j for j in jobs if j.remote]
    remote_top = sorted(remote, key=lambda j: (j.key not in new_keys, j.tier))[:10]
    grads = [j for j in jobs if j.graduate_scheme]
    grads_top = sorted(grads, key=lambda j: (j.key not in new_keys, -(j.posted or date.min).toordinal()))[:10]
    interns = [j for j in jobs if j.internship]
    interns_top = sorted(interns, key=lambda j: (j.key not in new_keys, -(j.posted or date.min).toordinal()))[:15]
    gov = [j for j in jobs if j.government]
    gov_top = sorted(gov, key=lambda j: (j.key not in new_keys, -(j.posted or date.min).toordinal()))[:15]
    top = sorted(new_jobs, key=lambda j: (j.sponsorship != "Yes", not j.employer_sponsor.startswith("Yes"), j.tier))[:15]
    text = [
        f"{len(new_jobs)} new jobs since the last email, {len(jobs)} matching jobs posted in the last {max_age_days} days.",
        "The full list is in the attached Excel file (new ones are marked NEW).",
        f"Found this run: {source_line}.",
        "",
    ]
    text += [f"- {j.title} | {j.company} | {j.location} | sponsorship: {j.sponsorship} | apply: {j.apply_link}" for j in top]
    text += ["", f"{len(remote)} remote jobs (all in the 'Remote Jobs' sheet):"]
    text += [f"- {j.title} | {j.company} | {j.location} | apply: {j.apply_link}" for j in remote_top]
    text += ["", f"{len(grads)} graduate schemes (all in the 'Graduate Schemes' sheet):"]
    text += [f"- {j.title} | {j.company} | {j.location} | apply: {j.apply_link}" for j in grads_top]
    text += ["", f"{len(interns)} internships (all in the 'Internships' sheet):"]
    text += [f"- {j.title} | {j.company} | {j.location} | apply: {j.apply_link}" for j in interns_top]
    text += ["", f"{len(gov)} UK government jobs, NHS and Civil Service (all in the 'Government Jobs' sheet):"]
    text += [f"- {j.title} | {j.company} | {j.location} | apply: {j.apply_link}" for j in gov_top]
    hacks = hackathons or []
    new_hackathons = new_hackathons or set()
    hacks_top = sorted(hacks, key=lambda h: (h.key not in new_hackathons, h.deadline is None,
                                             h.deadline or date.max))[:15]
    if hackathons is not None:
        text += ["", f"{len(hacks)} quant finance hackathons graduates can enter (all in the 'Hackathons' sheet):"]
        text += [f"- {'NEW ' if h.key in new_hackathons else ''}{h.title} | {h.organiser} | {h.dates} | "
                 f"{h.eligibility} | {h.url}" for h in hacks_top]
    opps = startups or []
    new_startups = new_startups or set()
    opps_top = sorted(opps, key=lambda o: (o.key not in new_startups,
                                           o.graduate_fit not in ("Graduate / junior role", "Welcomes graduates"),
                                           -(o.posted or date.min).toordinal()))[:15]
    if startups is not None:
        text += ["", f"{len(opps)} roles at quant and fintech startups that take graduates (all in the 'Startups' sheet):"]
        text += [f"- {'NEW ' if o.key in new_startups else ''}{o.title} | {o.company} | {o.location} | "
                 f"{o.graduate_fit} | apply: {o.url}" for o in opps_top]
    msg.set_content("\n".join(text))

    table = _table(top) if top else "<p>No new jobs this time.</p>"
    remote_table = (
        f"<p><b>{len(remote)}</b> remote jobs (all in the 'Remote Jobs' sheet):</p>{_table(remote_top)}"
        if remote else "<p>No remote jobs this time.</p>"
    )
    grads_table = (
        f"<p><b>{len(grads)}</b> graduate schemes (all in the 'Graduate Schemes' sheet):</p>{_table(grads_top)}"
        if grads else "<p>No graduate schemes this time.</p>"
    )
    interns_table = (
        f"<p><b>{len(interns)}</b> internships (all in the 'Internships' sheet):</p>{_table(interns_top)}"
        if interns else "<p>No internships this time.</p>"
    )
    gov_table = (
        f"<p><b>{len(gov)}</b> UK government jobs, NHS and Civil Service (all in the 'Government Jobs' sheet):</p>"
        f"{_table(gov_top)}" if gov else "<p>No UK government jobs passed the rules this time.</p>"
    )
    hack_table = ""
    if hackathons is not None:
        hack_table = (
            f"<p><b>{len(hacks)}</b> quant finance hackathons graduates can enter "
            f"(all in the 'Hackathons' sheet):</p>{_hackathon_table(hacks_top, new_hackathons)}"
            if hacks else "<p>No quant finance hackathons open to graduates this time.</p>"
        )
    startup_table = ""
    if startups is not None:
        startup_table = (
            f"<p><b>{len(opps)}</b> roles at quant and fintech startups that take graduates "
            f"(all in the 'Startups' sheet):</p>{_startup_table(opps_top, new_startups)}"
            if opps else "<p>No startup roles open to graduates this time.</p>"
        )
    msg.add_alternative(
        f"<p><b>{len(new_jobs)}</b> new jobs since the last email, <b>{len(jobs)}</b> matching jobs posted in the last {max_age_days} days.</p>"
        f"<p>The full list is in the attached Excel file (new ones are marked NEW).</p>"
        f"{'<p>Top new jobs:</p>' if top else ''}{table}{remote_table}{grads_table}{interns_table}{gov_table}{hack_table}{startup_table}"
        f"<p style='color:#666;font-size:12px'>Found this run: {html.escape(source_line)}.</p>",
        subtype="html",
    )
    msg.add_attachment(
        attachment.read_bytes(),
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=attachment.name,
    )
    return msg


def _table(jobs: list[Job]) -> str:
    rows = "".join(
        f"<tr><td><a href='{html.escape(j.url)}'>{html.escape(j.title)}</a></td>"
        f"<td>{html.escape(j.company)}</td><td>{html.escape(j.location)}</td>"
        f"<td>{html.escape(j.sponsorship)}</td><td>{j.posted or ''}</td>"
        f"<td><a href='{html.escape(j.apply_link)}'>Apply</a> ({html.escape(j.apply_on)})</td></tr>"
        for j in jobs
    )
    return (
        "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse:collapse;font-size:13px'>"
        "<tr style='background:#1F3864;color:#fff'><th>Role</th><th>Company</th><th>Location</th>"
        f"<th>Visa sponsorship</th><th>Posted</th><th>Apply</th></tr>{rows}</table>"
    )


def _hackathon_table(hacks: list, new_keys: set[str]) -> str:
    rows = "".join(
        f"<tr><td>{'<b>NEW</b> ' if h.key in new_keys else ''}<a href='{html.escape(h.url)}'>{html.escape(h.title)}</a></td>"
        f"<td>{html.escape(h.organiser)}</td><td>{html.escape(h.dates)}</td>"
        f"<td>{html.escape(h.eligibility)}</td><td>{html.escape(h.format)}</td><td>{html.escape(h.prize)}</td></tr>"
        for h in hacks
    )
    return (
        "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse:collapse;font-size:13px'>"
        "<tr style='background:#1F3864;color:#fff'><th>Hackathon</th><th>Organiser</th><th>Dates / deadline</th>"
        f"<th>Graduates</th><th>Format</th><th>Prize</th></tr>{rows}</table>"
    )


def _startup_table(opps: list, new_keys: set[str]) -> str:
    rows = "".join(
        f"<tr><td>{'<b>NEW</b> ' if o.key in new_keys else ''}<a href='{html.escape(o.url)}'>{html.escape(o.title)}</a></td>"
        f"<td>{html.escape(o.company)}</td><td>{html.escape(o.focus)}</td><td>{html.escape(o.location)}</td>"
        f"<td>{html.escape(o.graduate_fit)}</td><td>{html.escape(o.sponsorship)}</td></tr>"
        for o in opps
    )
    return (
        "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse:collapse;font-size:13px'>"
        "<tr style='background:#1F3864;color:#fff'><th>Role</th><th>Startup</th><th>What they do</th>"
        f"<th>Location</th><th>Graduate fit</th><th>Visa sponsorship</th></tr>{rows}</table>"
    )


def send(msg: EmailMessage) -> None:
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ["GMAIL_USER"]
    password = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "")
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=60) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=60) as smtp:
            if os.environ.get("SMTP_STARTTLS", "1") == "1":
                smtp.starttls()
            if password:
                smtp.login(user, password)
            smtp.send_message(msg)
