import os

import requests

from jobcopilot.models import Job


class UsajobsNotConfigured(Exception):
    pass


def fetch_jobs(keyword: str, location: str = "", results_per_page: int = 25,
               timeout: float = 15.0) -> list[Job]:
    """Fetch federal postings matching `keyword` from the USAJobs Search API.
    Requires USAJOBS_API_KEY + USAJOBS_EMAIL env vars (free: https://developer.usajobs.gov/apirequest/).
    Raises UsajobsNotConfigured if either is missing — caller should skip this source, not crash."""
    api_key = os.environ.get("USAJOBS_API_KEY")
    email = os.environ.get("USAJOBS_EMAIL")
    if not api_key or not email:
        raise UsajobsNotConfigured("USAJOBS_API_KEY / USAJOBS_EMAIL not set")

    params = {"Keyword": keyword, "ResultsPerPage": results_per_page}
    if location:
        params["LocationName"] = location

    resp = requests.get(
        "https://data.usajobs.gov/api/search",
        params=params,
        headers={"Host": "data.usajobs.gov", "User-Agent": email, "Authorization-Key": api_key},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for item in data.get("SearchResult", {}).get("SearchResultItems", []):
        d = item.get("MatchedObjectDescriptor", {})
        locations = d.get("PositionLocation", [])
        location_str = ", ".join(loc.get("LocationName", "") for loc in locations) or \
            d.get("PositionLocationDisplay", "")
        summary = d.get("UserArea", {}).get("Details", {}).get("JobSummary", "")
        jobs.append(Job(
            source="usajobs",
            external_id=str(d.get("PositionID", d.get("PositionURI", ""))),
            title=d.get("PositionTitle", ""),
            company=d.get("OrganizationName", ""),
            location=location_str,
            url=d.get("PositionURI", ""),
            description=summary or d.get("QualificationSummary", ""),
            posted_at=d.get("PublicationStartDate", "") or "",
        ))
    return jobs
