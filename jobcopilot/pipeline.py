from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

from jobcopilot import db
from jobcopilot.claude_client import build_profile_system_block
from jobcopilot.models import Job, ScoredJob
from jobcopilot.prefilter import passes_prefilter
from jobcopilot.scoring import score_job
from jobcopilot.sources import greenhouse, lever, usajobs

if TYPE_CHECKING:
    import anthropic

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def db_path_for(config: dict) -> str:
    return str(Path(config.get("data_dir", "data")) / "jobcopilot.db")


def fetch_all_jobs(config: dict) -> tuple[list[Job], list[str]]:
    """Fetch postings from every configured source. Returns (jobs, warnings) — a source
    failing (network error, missing USAJobs credentials, bad slug) produces a warning and
    is skipped rather than aborting the whole run."""
    jobs: list[Job] = []
    warnings: list[str] = []

    for slug in config.get("greenhouse_slugs", []):
        try:
            jobs.extend(greenhouse.fetch_jobs(slug))
        except Exception as e:
            warnings.append(f"Greenhouse source '{slug}' failed: {e}")

    for slug in config.get("lever_slugs", []):
        try:
            jobs.extend(lever.fetch_jobs(slug))
        except Exception as e:
            warnings.append(f"Lever source '{slug}' failed: {e}")

    location = config.get("usajobs_location", "")
    for keyword in config.get("usajobs_keywords", []):
        try:
            jobs.extend(usajobs.fetch_jobs(keyword, location=location))
        except usajobs.UsajobsNotConfigured:
            warnings.append("USAJobs skipped: USAJOBS_API_KEY/USAJOBS_EMAIL not set.")
        except Exception as e:
            warnings.append(f"USAJobs keyword '{keyword}' failed: {e}")

    return jobs, warnings


def ingest_and_score_new(conn: sqlite3.Connection, client: anthropic.Anthropic,
                          profile: dict, jobs: list[Job]) -> tuple[list[ScoredJob], list[str]]:
    """Upsert every fetched job (dedup on source+external_id), then score only the ones
    that are genuinely new AND pass the free keyword prefilter — large company boards list
    hundreds of postings with no relevance to the candidate, and there's no reason to spend
    a Claude call ruling those out one at a time. Jobs that fail the prefilter stay cached
    with no score (so they're never re-considered) but are silently omitted, not scored as
    a rejection. Returns (newly_scored, warnings) — a scoring failure on one job is logged
    and skipped so one bad posting doesn't abort the whole batch."""
    profile_system = build_profile_system_block(profile)
    warnings: list[str] = []
    new_jobs: list[Job] = [j for j in jobs if db.upsert_job(conn, j)]
    candidates = [j for j in new_jobs if passes_prefilter(j, profile)]

    scored: list[ScoredJob] = []
    for job in candidates:
        try:
            result = score_job(client, profile_system, job)
        except Exception as e:
            warnings.append(f"Scoring failed for '{job.title}' at {job.company}: {e}")
            continue
        db.set_job_score(conn, job.key, result.score, result.rationale, result.matched_skills)
        scored.append(result)

    return scored, warnings


def get_connection(config: dict) -> sqlite3.Connection:
    return db.get_connection(db_path_for(config))
