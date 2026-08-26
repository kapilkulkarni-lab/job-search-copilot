import html
import re

import requests

from jobcopilot.models import Job

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(raw: str) -> str:
    return html.unescape(_TAG_RE.sub(" ", raw or "")).strip()


def fetch_jobs(slug: str, timeout: float = 15.0) -> list[Job]:
    """Fetch open postings from a Greenhouse job board. `slug` is the board token, e.g.
    the X in boards.greenhouse.io/X — for example "andurilindustries"."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    resp = requests.get(url, params={"content": "true"}, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for item in data.get("jobs", []):
        jobs.append(Job(
            source="greenhouse",
            external_id=str(item["id"]),
            title=item.get("title", ""),
            company=item.get("company_name", slug),
            location=(item.get("location") or {}).get("name", ""),
            url=item.get("absolute_url", ""),
            description=_strip_html(item.get("content", "")),
            posted_at=item.get("first_published", "") or "",
        ))
    return jobs
