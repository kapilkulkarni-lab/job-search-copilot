import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from jobcopilot.models import Application, Job, ScoredJob

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    key TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT NOT NULL,
    url TEXT NOT NULL,
    description TEXT NOT NULL,
    posted_at TEXT NOT NULL DEFAULT '',
    score INTEGER,
    rationale TEXT,
    matched_skills TEXT,
    first_seen_at TEXT NOT NULL,
    scored_at TEXT
);

CREATE TABLE IF NOT EXISTS applications (
    job_key TEXT PRIMARY KEY REFERENCES jobs(key),
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Not Applied',
    applied_date TEXT NOT NULL DEFAULT '',
    follow_up_date TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    resume_bullets TEXT NOT NULL DEFAULT '',
    cover_letter TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_job(conn: sqlite3.Connection, job: Job) -> bool:
    """Insert a job if new. Returns True if it was newly inserted, False if it already existed."""
    existing = conn.execute("SELECT 1 FROM jobs WHERE key = ?", (job.key,)).fetchone()
    if existing:
        return False
    conn.execute(
        """INSERT INTO jobs (key, source, external_id, title, company, location, url,
                              description, posted_at, first_seen_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (job.key, job.source, job.external_id, job.title, job.company, job.location,
         job.url, job.description, job.posted_at, _now()),
    )
    conn.commit()
    return True


def get_unscored_jobs(conn: sqlite3.Connection) -> list[Job]:
    rows = conn.execute("SELECT * FROM jobs WHERE score IS NULL").fetchall()
    return [_row_to_job(r) for r in rows]


def set_job_score(conn: sqlite3.Connection, key: str, score: int, rationale: str,
                   matched_skills: list[str]) -> None:
    conn.execute(
        "UPDATE jobs SET score = ?, rationale = ?, matched_skills = ?, scored_at = ? WHERE key = ?",
        (score, rationale, json.dumps(matched_skills), _now(), key),
    )
    conn.commit()


def get_scored_jobs(conn: sqlite3.Connection, min_score: int | None = None) -> list[ScoredJob]:
    query = "SELECT * FROM jobs WHERE score IS NOT NULL"
    params: tuple = ()
    if min_score is not None:
        query += " AND score >= ?"
        params = (min_score,)
    query += " ORDER BY score DESC"
    rows = conn.execute(query, params).fetchall()
    return [_row_to_scored_job(r) for r in rows]


def get_job(conn: sqlite3.Connection, key: str) -> Job | None:
    row = conn.execute("SELECT * FROM jobs WHERE key = ?", (key,)).fetchone()
    return _row_to_job(row) if row else None


def get_scored_job(conn: sqlite3.Connection, key: str) -> ScoredJob | None:
    row = conn.execute("SELECT * FROM jobs WHERE key = ? AND score IS NOT NULL", (key,)).fetchone()
    return _row_to_scored_job(row) if row else None


def _row_to_job(row: sqlite3.Row) -> Job:
    return Job(
        source=row["source"], external_id=row["external_id"], title=row["title"],
        company=row["company"], location=row["location"], url=row["url"],
        description=row["description"], posted_at=row["posted_at"],
    )


def _row_to_scored_job(row: sqlite3.Row) -> ScoredJob:
    return ScoredJob(
        job=_row_to_job(row),
        score=row["score"],
        rationale=row["rationale"] or "",
        matched_skills=json.loads(row["matched_skills"]) if row["matched_skills"] else [],
    )


def upsert_application(conn: sqlite3.Connection, app: Application) -> None:
    conn.execute(
        """INSERT INTO applications (job_key, company, title, status, applied_date,
                                      follow_up_date, notes, resume_bullets, cover_letter, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(job_key) DO UPDATE SET
               status=excluded.status, applied_date=excluded.applied_date,
               follow_up_date=excluded.follow_up_date, notes=excluded.notes,
               resume_bullets=excluded.resume_bullets, cover_letter=excluded.cover_letter,
               updated_at=excluded.updated_at""",
        (app.job_key, app.company, app.title, app.status, app.applied_date,
         app.follow_up_date, app.notes, app.resume_bullets, app.cover_letter, _now()),
    )
    conn.commit()


def get_applications(conn: sqlite3.Connection) -> list[Application]:
    rows = conn.execute("SELECT * FROM applications ORDER BY updated_at DESC").fetchall()
    return [
        Application(
            job_key=r["job_key"], company=r["company"], title=r["title"], status=r["status"],
            applied_date=r["applied_date"], follow_up_date=r["follow_up_date"], notes=r["notes"],
            resume_bullets=r["resume_bullets"], cover_letter=r["cover_letter"],
        )
        for r in rows
    ]


def get_application(conn: sqlite3.Connection, job_key: str) -> Application | None:
    row = conn.execute("SELECT * FROM applications WHERE job_key = ?", (job_key,)).fetchone()
    if not row:
        return None
    return Application(
        job_key=row["job_key"], company=row["company"], title=row["title"], status=row["status"],
        applied_date=row["applied_date"], follow_up_date=row["follow_up_date"], notes=row["notes"],
        resume_bullets=row["resume_bullets"], cover_letter=row["cover_letter"],
    )
