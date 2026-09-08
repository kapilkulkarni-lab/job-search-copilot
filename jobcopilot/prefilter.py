import re

from jobcopilot.models import Job


def _normalize(text: str) -> str:
    """Fold punctuation variants (",", "&") that separate real postings ("Guidance,
    Navigation & Control") from the plain-English phrasing in config.json target_roles
    ("guidance navigation and control") down to the same comparable form."""
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def passes_prefilter(job: Job, profile: dict) -> bool:
    """Cheap, free, deterministic gate before spending a Claude call on scoring. Job
    boards for large companies list hundreds of totally unrelated roles (recruiting,
    finance, legal, ...) — skip those without ever calling the API. A job only needs to
    plausibly relate to the candidate's target roles/skills; the LLM scoring step still
    does the real relevance judgment for everything that passes."""
    terms = [_normalize(t) for t in (profile.get("target_roles", []) + profile.get("skills", []))]
    terms = [t for t in terms if t]
    if not terms:
        return True
    haystack = _normalize(f"{job.title} {job.description[:1000]}")
    return any(term in haystack for term in terms)
