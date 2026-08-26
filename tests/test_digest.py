from unittest.mock import Mock, patch

import pytest

from jobcopilot import db, email_sender, pipeline
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


def test_build_digest_ranks_by_score_and_lists_warnings():
    low = ScoredJob(job=make_job("1"), score=71, rationale="ok", matched_skills=[])
    high = ScoredJob(job=make_job("2"), score=95, rationale="great", matched_skills=["MATLAB"])

    subject, body = email_sender.build_digest([low, high], ["USAJobs skipped: no key"])

    assert "2 new match" in subject
    assert body.index("95") < body.index("71")  # higher score listed first
    assert "USAJobs skipped" in body


def test_build_digest_handles_no_matches():
    subject, body = email_sender.build_digest([], [])
    assert "no new matches" in subject
    assert "No postings met the score threshold" in body


def test_send_digest_requires_credentials(monkeypatch):
    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    monkeypatch.delenv("DIGEST_RECIPIENT_EMAIL", raising=False)

    with pytest.raises(email_sender.EmailNotConfigured):
        email_sender.send_digest([], [])


def test_send_digest_sends_via_smtp(monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", "me@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "app-password")
    monkeypatch.setenv("DIGEST_RECIPIENT_EMAIL", "me@gmail.com")

    with patch("jobcopilot.email_sender.smtplib.SMTP_SSL") as smtp_cls:
        server = smtp_cls.return_value.__enter__.return_value
        email_sender.send_digest([], [])

    smtp_cls.assert_called_once_with("smtp.gmail.com", 465)
    server.login.assert_called_once_with("me@gmail.com", "app-password")
    server.sendmail.assert_called_once()
