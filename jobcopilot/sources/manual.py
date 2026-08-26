import hashlib

from jobcopilot.models import Job


def make_job(title: str, company: str, location: str, url: str, description: str) -> Job:
    """Wrap a manually pasted posting (e.g. from a Workday career page that has no
    public API) into a Job with a stable external_id derived from its URL/title."""
    basis = url or f"{company}:{title}"
    external_id = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
    return Job(
        source="manual",
        external_id=external_id,
        title=title,
        company=company,
        location=location,
        url=url,
        description=description,
    )
