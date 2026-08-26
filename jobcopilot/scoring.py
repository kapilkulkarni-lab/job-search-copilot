from __future__ import annotations

import json
from typing import TYPE_CHECKING

from jobcopilot.claude_client import MODEL
from jobcopilot.models import Job, ScoredJob

if TYPE_CHECKING:
    import anthropic

SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "rationale": {"type": "string"},
        "matched_skills": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["score", "rationale", "matched_skills"],
    "additionalProperties": False,
}


def score_job(client: anthropic.Anthropic, profile_system: list[dict], job: Job) -> ScoredJob:
    """Score one job posting against the cached candidate profile. Raises on API/parse
    failure — caller decides whether to skip or abort."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=profile_system,
        thinking={"type": "adaptive"},
        output_config={
            "effort": "low",
            "format": {"type": "json_schema", "schema": SCORE_SCHEMA},
        },
        messages=[{
            "role": "user",
            "content": (
                "Score this job posting's fit for the candidate from 0-100 (100 = ideal "
                "fit), a one-sentence rationale, and which of the candidate's listed skills "
                "it draws on.\n\n"
                f"Title: {job.title}\n"
                f"Company: {job.company}\n"
                f"Location: {job.location}\n"
                f"Description:\n{job.description}"
            ),
        }],
    )

    text = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text)
    score = max(0, min(100, int(data["score"])))
    return ScoredJob(
        job=job,
        score=score,
        rationale=data["rationale"],
        matched_skills=list(data.get("matched_skills", [])),
    )
