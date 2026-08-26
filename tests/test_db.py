from jobcopilot import db
from jobcopilot.models import Application, Job


def make_job(key_suffix="1"):
    return Job(
        source="greenhouse", external_id=key_suffix, title=f"Title {key_suffix}",
        company="Co", location="Remote", url=f"https://example.com/{key_suffix}",
        description="desc",
    )


def test_upsert_job_dedupes(tmp_path):
    conn = db.get_connection(str(tmp_path / "test.db"))
    job = make_job("1")

    assert db.upsert_job(conn, job) is True
    assert db.upsert_job(conn, job) is False  # already present, no duplicate

    assert db.get_job(conn, job.key) is not None
    assert len(db.get_unscored_jobs(conn)) == 1


def test_score_roundtrip(tmp_path):
    conn = db.get_connection(str(tmp_path / "test.db"))
    job = make_job("1")
    db.upsert_job(conn, job)

    db.set_job_score(conn, job.key, 85, "Strong fit.", ["Python", "MATLAB"])

    scored = db.get_scored_job(conn, job.key)
    assert scored.score == 85
    assert scored.rationale == "Strong fit."
    assert scored.matched_skills == ["Python", "MATLAB"]
    assert db.get_unscored_jobs(conn) == []


def test_get_scored_jobs_sorted_and_filtered(tmp_path):
    conn = db.get_connection(str(tmp_path / "test.db"))
    for i, score in enumerate([50, 90, 70]):
        job = make_job(str(i))
        db.upsert_job(conn, job)
        db.set_job_score(conn, job.key, score, "r", [])

    all_scored = db.get_scored_jobs(conn)
    assert [sj.score for sj in all_scored] == [90, 70, 50]

    filtered = db.get_scored_jobs(conn, min_score=70)
    assert [sj.score for sj in filtered] == [90, 70]


def test_application_crud(tmp_path):
    conn = db.get_connection(str(tmp_path / "test.db"))
    job = make_job("1")
    db.upsert_job(conn, job)

    app = Application(job_key=job.key, company="Co", title="Title 1", status="Applied")
    db.upsert_application(conn, app)

    fetched = db.get_application(conn, job.key)
    assert fetched.status == "Applied"

    fetched.status = "Interview"
    db.upsert_application(conn, fetched)

    apps = db.get_applications(conn)
    assert len(apps) == 1
    assert apps[0].status == "Interview"
