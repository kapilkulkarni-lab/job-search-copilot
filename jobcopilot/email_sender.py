import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from jobcopilot.models import ScoredJob


class EmailNotConfigured(Exception):
    pass


def _credentials() -> tuple[str, str, str]:
    address = os.environ.get("GMAIL_ADDRESS")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient = os.environ.get("DIGEST_RECIPIENT_EMAIL") or address
    if not address or not app_password or not recipient:
        raise EmailNotConfigured(
            "GMAIL_ADDRESS / GMAIL_APP_PASSWORD / DIGEST_RECIPIENT_EMAIL not fully set"
        )
    return address, app_password, recipient


def build_digest(scored_jobs: list[ScoredJob], warnings: list[str]) -> tuple[str, str]:
    """Returns (subject, html_body) for the morning digest email."""
    if not scored_jobs:
        subject = "Job Search Copilot: no new matches today"
    else:
        subject = f"Job Search Copilot: {len(scored_jobs)} new match(es) today"

    ranked = sorted(scored_jobs, key=lambda sj: sj.score, reverse=True)

    rows = []
    for sj in ranked:
        j = sj.job
        skills = ", ".join(sj.matched_skills) if sj.matched_skills else ""
        skills_html = (
            f"<br><span style='color:#999;font-size:0.85em'>Matches: {skills}</span>"
            if skills else ""
        )
        rows.append(
            "<tr>"
            f"<td style='padding:8px;font-weight:bold'>{sj.score}</td>"
            f"<td style='padding:8px'><a href='{j.url}'>{j.title}</a><br>"
            f"<span style='color:#555'>{j.company} — {j.location}</span><br>"
            f"<span style='color:#777;font-size:0.9em'>{sj.rationale}</span>"
            f"{skills_html}"
            "</td></tr>"
        )

    table = (
        "<table style='border-collapse:collapse;width:100%'>"
        "<tr><th style='text-align:left;padding:8px'>Score</th>"
        "<th style='text-align:left;padding:8px'>Posting</th></tr>"
        + "".join(rows) + "</table>"
    ) if rows else "<p>No postings met the score threshold today.</p>"

    warning_html = ""
    if warnings:
        items = "".join(f"<li>{w}</li>" for w in warnings)
        warning_html = f"<hr><p><b>Warnings:</b></p><ul>{items}</ul>"

    body = f"<html><body>{table}{warning_html}</body></html>"
    return subject, body


def send_digest(scored_jobs: list[ScoredJob], warnings: list[str]) -> None:
    """Send the morning digest via Gmail SMTP. Raises EmailNotConfigured if credentials
    are missing — caller should surface that rather than silently skipping."""
    address, app_password, recipient = _credentials()
    subject, html_body = build_digest(scored_jobs, warnings)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = address
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(address, app_password)
        server.sendmail(address, [recipient], msg.as_string())
