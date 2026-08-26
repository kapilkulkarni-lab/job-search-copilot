from datetime import datetime, timedelta, timezone

from jobcopilot.cloud_fetch import _recent_enough


def test_recent_enough_true_for_missing_timestamp():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=30)
    assert _recent_enough("", cutoff) is True


def test_recent_enough_filters_old_postings():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=30)
    old = (datetime.now(timezone.utc) - timedelta(hours=100)).isoformat()
    recent = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    assert _recent_enough(old, cutoff) is False
    assert _recent_enough(recent, cutoff) is True
