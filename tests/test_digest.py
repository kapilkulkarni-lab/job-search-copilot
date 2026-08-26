from unittest.mock import Mock, patch

from jobcopilot import db, pipeline
from jobcopilot.models import Job, ScoredJob


def make_job(key_suffix="1"):
    return Job(
        source="greenhouse", external_id=key_suffix, title=f"Title {key_suffix}",
        company="Co", location="Remote", url=f"https://example.com/{key_suffix}",
        description="desc",
    )


def test_ingest_and_score_new_skips_already_seen_jobs(tmp_path):
    conn = db.get_connection(str(tmp_path / "test.db"))
    job = make_job("1")

    fake_score = ScoredJob(job=job, score=80, rationale="Good fit", matched_skills=["Python"])
    with patch("jobcopilot.pipeline.score_job", return_value=fake_score) as scorer:
        scored, warnings = pipeline.ingest_and_score_new(conn, Mock(), {}, [job])
        assert len(scored) == 1
        assert warnings == []

        # Re-running with the same job should not re-score it — already in the cache.
        scored_again, warnings_again = pipeline.ingest_and_score_new(conn, Mock(), {}, [job])
        assert scored_again == []
        assert warnings_again == []
        scorer.assert_called_once()


def test_ingest_and_score_new_continues_after_one_scoring_failure(tmp_path):
    conn = db.get_connection(str(tmp_path / "test.db"))
    good_job = make_job("1")
    bad_job = make_job("2")

    def fake_score(client, profile_system, job):
        if job.key == bad_job.key:
            raise RuntimeError("API error")
        return ScoredJob(job=job, score=80, rationale="Good fit", matched_skills=[])

    with patch("jobcopilot.pipeline.score_job", side_effect=fake_score):
        scored, warnings = pipeline.ingest_and_score_new(conn, Mock(), {}, [good_job, bad_job])

    assert len(scored) == 1
    assert scored[0].job.key == good_job.key
    assert len(warnings) == 1
    assert "Title 2" in warnings[0]
