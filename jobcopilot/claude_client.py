from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import anthropic

MODEL = "claude-opus-5"


def get_client() -> "anthropic.Anthropic":
    import anthropic
    return anthropic.Anthropic()


def build_profile_system_block(profile: dict) -> list[dict]:
    """Stable system prompt describing the candidate. Cached since it's reused across
    every scoring/tailoring call in a run."""
    text = (
        "You are a job-search assistant helping a specific candidate evaluate and apply "
        "to job postings. Candidate profile:\n\n"
        f"Name: {profile.get('name', '')}\n"
        f"Clearance: {profile.get('clearance', '')}\n"
        f"Education: {profile.get('education', '')}\n"
        f"Target roles: {', '.join(profile.get('target_roles', []))}\n"
        f"Skills: {', '.join(profile.get('skills', []))}\n\n"
        f"Background summary:\n{profile.get('summary', '')}\n"
    )
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]
