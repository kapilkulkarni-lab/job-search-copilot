from datetime import datetime, timezone

import requests

from jobcopilot.models import Job


def fetch_jobs(slug: str, timeout: float = 15.0) -> list[Job]:
    """Fetch open postings from a Lever job board. `slug` is the company token, e.g.
    the X in jobs.lever.co/X — for example "shieldai"."""
    url = f"https://api.lever.co/v0/postings/{slug}"
    resp = requests.get(url, params={"mode": "json"}, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for item in data:
        categories = item.get("categories", {})
        posted_at = ""
        created_ms = item.get("createdAt")
        if created_ms:
            posted_at = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc).isoformat()
        jobs.append(Job(
            source="lever",
            external_id=str(item["id"]),
            title=item.get("text", ""),
            company=slug,
            location=categories.get("location", ""),
            url=item.get("hostedUrl", ""),
            description=item.get("descriptionPlain", "") or item.get("description", ""),
            posted_at=posted_at,
        ))
    return jobs
