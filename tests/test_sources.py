from unittest.mock import Mock, patch

from jobcopilot.sources import greenhouse, lever, manual


def test_greenhouse_parses_jobs():
    payload = {
        "jobs": [{
            "id": 123,
            "title": "Autonomy Engineer",
            "company_name": "Anduril Industries",
            "location": {"name": "Costa Mesa, CA"},
            "absolute_url": "https://boards.greenhouse.io/andurilindustries/jobs/123",
            "content": "<div><p>Build &amp; test autonomy stacks.</p></div>",
            "first_published": "2026-01-01T00:00:00-05:00",
        }]
    }
    mock_resp = Mock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status = Mock()

    with patch("jobcopilot.sources.greenhouse.requests.get", return_value=mock_resp) as get:
        jobs = greenhouse.fetch_jobs("andurilindustries")

    get.assert_called_once()
    assert len(jobs) == 1
    job = jobs[0]
    assert job.source == "greenhouse"
    assert job.external_id == "123"
    assert job.title == "Autonomy Engineer"
    assert job.company == "Anduril Industries"
    assert job.location == "Costa Mesa, CA"
    assert "Build & test autonomy stacks." in job.description
    assert "<" not in job.description
    assert job.key == "greenhouse:123"


def test_lever_parses_jobs():
    payload = [{
        "id": "abc-123",
        "text": "Controls Engineer",
        "hostedUrl": "https://jobs.lever.co/shieldai/abc-123",
        "categories": {"location": "Seattle, WA"},
        "descriptionPlain": "Design flight control laws.",
        "createdAt": 1750000000000,
    }]
    mock_resp = Mock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status = Mock()

    with patch("jobcopilot.sources.lever.requests.get", return_value=mock_resp):
        jobs = lever.fetch_jobs("shieldai")

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source == "lever"
    assert job.external_id == "abc-123"
    assert job.title == "Controls Engineer"
    assert job.location == "Seattle, WA"
    assert job.description == "Design flight control laws."
    assert job.posted_at != ""


def test_manual_job_is_stable_across_calls():
    job1 = manual.make_job("Title", "Company", "Loc", "https://example.com/job/1", "desc")
    job2 = manual.make_job("Title", "Company", "Loc", "https://example.com/job/1", "desc")
    assert job1.key == job2.key
    assert job1.source == "manual"
