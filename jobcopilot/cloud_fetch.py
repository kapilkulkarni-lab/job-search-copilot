"""Fetch + prefilter postings for the cloud scheduled routine. Deliberately makes no
Claude API call — the routine session itself (an agentic Claude Code run) does the
actual relevance scoring inline as part of executing its prompt, not via a subprocess
call back to the API. Only needs `requests` installed, not the `anthropic` package.

Since the cloud sandbox has no persistent database to dedupe against previous runs
(unlike the local digest, which uses SQLite), this instead filters to postings
posted/updated within --max-age-hours, with generous overlap over the daily cadence.

Usage: python -m jobcopilot.cloud_fetch [--max-age-hours 30]
Prints JSON to stdout: {"profile": {...}, "score_threshold": int, "warnings": [...], "jobs": [...]}
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from jobcopilot import pipeline
from jobcopilot.prefilter import passes_prefilter


def _recent_enough(posted_at: str, cutoff: datetime) -> bool:
    if not posted_at:
        return True  # no timestamp from the source — keep it rather than silently drop it
    try:
        dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt >= cutoff


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-age-hours", type=int, default=30)
    args = parser.parse_args()

    config = pipeline.load_config()
    jobs, warnings = pipeline.fetch_all_jobs(config)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.max_age_hours)
    candidates = [
        j for j in jobs
        if _recent_enough(j.posted_at, cutoff) and passes_prefilter(j, config["profile"])
    ]

    print(json.dumps({
        "profile": config["profile"],
        "score_threshold": config.get("score_threshold", 70),
        "warnings": warnings,
        "jobs": [asdict(j) for j in candidates],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
