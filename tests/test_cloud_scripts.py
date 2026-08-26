import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from jobcopilot.cloud_fetch import _recent_enough
from jobcopilot.cloud_send import main as cloud_send_main


def test_recent_enough_true_for_missing_timestamp():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=30)
    assert _recent_enough("", cutoff) is True


def test_recent_enough_filters_old_postings():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=30)
    old = (datetime.now(timezone.utc) - timedelta(hours=100)).isoformat()
    recent = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    assert _recent_enough(old, cutoff) is False
    assert _recent_enough(recent, cutoff) is True


def test_cloud_send_parses_and_sends(tmp_path, monkeypatch):
    payload = {
        "scored_jobs": [{
            "title": "GNC Engineer", "company": "Anduril", "location": "CA",
            "url": "https://example.com/1", "score": 90, "rationale": "great fit",
            "matched_skills": ["MATLAB"],
        }],
        "warnings": ["USAJobs skipped: no key"],
    }
    path = tmp_path / "scored.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with patch("jobcopilot.cloud_send.email_sender.send_digest") as send:
        monkeypatch.setattr("sys.argv", ["cloud_send.py", str(path)])
        assert cloud_send_main() == 0

    send.assert_called_once()
    scored_arg, warnings_arg = send.call_args[0]
    assert len(scored_arg) == 1
    assert scored_arg[0].score == 90
    assert warnings_arg == ["USAJobs skipped: no key"]
