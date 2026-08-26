from __future__ import annotations

import json
from typing import TYPE_CHECKING

from jobcopilot.claude_client import MODEL
from jobcopilot.models import Job

if TYPE_CHECKING:
    import anthropic

DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "resume_bullets": {"type": "string"},
        "cover_letter": {"type": "string"},
    },
    "required": ["resume_bullets", "cover_letter"],
    "additionalProperties": False,
}


def draft_materials(client: anthropic.Anthropic, profile_system: list[dict], job: Job) -> dict:
    """Draft tailored resume bullets + a cover letter for one job. Returns
    {"resume_bullets": str, "cover_letter": str} — always shown to the user for review/edit
    before being saved or used anywhere; nothing here is submitted automatically."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=profile_system,
        thinking={"type": "adaptive"},
        output_config={
            "effort": "high",
            "format": {"type": "json_schema", "schema": DRAFT_SCHEMA},
        },
        messages=[{
            "role": "user",
            "content": (
                "Draft application materials tailored to this specific job posting, using "
                "only real experience from the candidate's profile — do not invent "
                "experience, metrics, or skills not present in the profile.\n\n"
                "1. resume_bullets: 3-5 resume bullet points (each starting with a strong "
                "action verb, including real metrics from the profile where relevant) "
                "rewritten to emphasize the parts of the candidate's background most "
                "relevant to this posting.\n"
                "2. cover_letter: a concise (3-4 paragraph) cover letter draft addressed "
                "to the hiring team, connecting the candidate's real background to this "
                "specific role and company.\n\n"
                f"Title: {job.title}\n"
                f"Company: {job.company}\n"
                f"Location: {job.location}\n"
                f"Description:\n{job.description}"
            ),
        }],
    )

    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)
