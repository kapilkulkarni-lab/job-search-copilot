from jobcopilot.models import Job


def passes_prefilter(job: Job, profile: dict) -> bool:
    """Cheap, free, deterministic gate before spending a Claude call on scoring. Job
    boards for large companies list hundreds of totally unrelated roles (recruiting,
    finance, legal, ...) — skip those without ever calling the API. A job only needs to
    plausibly relate to the candidate's target roles/skills; the LLM scoring step still
    does the real relevance judgment for everything that passes."""
    terms = [t.lower() for t in (profile.get("target_roles", []) + profile.get("skills", []))]
    if not terms:
        return True
    haystack = f"{job.title} {job.description[:1000]}".lower()
    return any(term in haystack for term in terms)
