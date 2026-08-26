"""Send the digest email for the cloud routine, given the scores the routine's own
reasoning already produced. Reuses the same tested build_digest HTML logic the local
digest.py uses, but sends via the Gmail API over HTTPS (jobcopilot.gmail_api_sender)
instead of raw SMTP — the cloud sandbox's network policy allows outbound HTTPS to
allowlisted domains but blocks SMTP (port 465) entirely. No Claude API call here.

Usage: python -m jobcopilot.cloud_send scored.json
Input JSON shape:
{
  "scored_jobs": [
    {"title": "...", "company": "...", "location": "...", "url": "...",
     "score": 87, "rationale": "...", "matched_skills": ["..."]}
  ],
  "warnings": ["..."]
}
"""
from __future__ import annotations

import json
import sys

from jobcopilot import gmail_api_sender
from jobcopilot.models import Job, ScoredJob


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python -m jobcopilot.cloud_send <scored.json>", file=sys.stderr)
        return 1

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)

    scored = []
    for item in data.get("scored_jobs", []):
        job = Job(
            source=item.get("source", "cloud"),
            external_id=item.get("external_id") or item["url"],
            title=item["title"], company=item["company"], location=item.get("location", ""),
            url=item["url"], description="",
        )
        scored.append(ScoredJob(
            job=job, score=int(item["score"]), rationale=item.get("rationale", ""),
            matched_skills=item.get("matched_skills", []),
        ))

    gmail_api_sender.send_digest_via_gmail_api(scored, data.get("warnings", []))
    print(f"Sent digest with {len(scored)} posting(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
