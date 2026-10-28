from __future__ import annotations

import html
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from .models import Job


def build_email(jobs: list[Job], new_keys: set[str], stats: dict, attachment: Path, sender: str, to: str) -> EmailMessage:
    new_jobs = [j for j in jobs if j.key in new_keys]
    msg = EmailMessage()
    msg["Subject"] = f"Quant jobs: {len(new_jobs)} new, {len(jobs)} in the last 5 days"
    msg["From"] = sender
    msg["To"] = to

    source_line = ", ".join(
        f"{name} {s['found']}" + (f" ({s['errors']} failed requests)" if s["errors"] else "")
        for name, s in stats.items()
    )
    top = sorted(new_jobs, key=lambda j: (j.sponsorship != "Yes", j.uk_licensed_sponsor != "Yes", j.tier))[:15]
    text = [
        f"{len(new_jobs)} new jobs since the last email, {len(jobs)} matching jobs posted in the last 5 days.",
        "The full list is in the attached Excel file (new ones are marked NEW).",
        f"Found this run: {source_line}.",
        "",
    ]
    text += [f"- {j.title} | {j.company} | {j.location} | sponsorship: {j.sponsorship} | {j.url}" for j in top]
    msg.set_content("\n".join(text))

    rows = "".join(
        f"<tr><td><a href='{html.escape(j.url)}'>{html.escape(j.title)}</a></td>"
        f"<td>{html.escape(j.company)}</td><td>{html.escape(j.location)}</td>"
        f"<td>{html.escape(j.sponsorship)}</td><td>{j.posted or ''}</td></tr>"
        for j in top
    )
    table = (
        "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse:collapse;font-size:13px'>"
        "<tr style='background:#1F3864;color:#fff'><th>Role</th><th>Company</th><th>Location</th>"
        f"<th>Visa sponsorship</th><th>Posted</th></tr>{rows}</table>"
        if top else "<p>No new jobs this time.</p>"
    )
    msg.add_alternative(
        f"<p><b>{len(new_jobs)}</b> new jobs since the last email, <b>{len(jobs)}</b> matching jobs posted in the last 5 days.</p>"
        f"<p>The full list is in the attached Excel file (new ones are marked NEW).</p>"
        f"{'<p>Top new jobs:</p>' if top else ''}{table}"
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
