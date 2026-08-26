"""Write the daily digest as a PDF instead of emailing it — no SMTP/OAuth needed.
One file per day in `data/digests/`, overwritten if run more than once the same day."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from fpdf import FPDF

from jobcopilot.models import ScoredJob


def write_digest_pdf(scored_jobs: list[ScoredJob], warnings: list[str],
                      out_dir: str = "data/digests") -> str:
    ranked = sorted(scored_jobs, key=lambda sj: sj.score, reverse=True)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    filename = str(Path(out_dir) / f"{date.today().isoformat()}.pdf")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Job Search Digest - {date.today().isoformat()}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"{len(ranked)} matching posting(s)", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    if not ranked:
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 8, "No postings met the score threshold today.",
                        new_x="LMARGIN", new_y="NEXT")

    for sj in ranked:
        job = sj.job
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 7, f"{sj.score}  {job.title}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, f"{job.company} - {job.location}", new_x="LMARGIN", new_y="NEXT")
        pdf.multi_cell(0, 6, sj.rationale, new_x="LMARGIN", new_y="NEXT")
        if sj.matched_skills:
            pdf.multi_cell(0, 6, "Matches: " + ", ".join(sj.matched_skills),
                            new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 238)
        pdf.cell(0, 6, job.url, link=job.url, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

    if warnings:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, "Warnings", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for w in warnings:
            pdf.multi_cell(0, 5, f"- {w}", new_x="LMARGIN", new_y="NEXT")

    pdf.output(filename)
    return filename
