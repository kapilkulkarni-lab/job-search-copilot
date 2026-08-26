from unittest.mock import Mock, patch

import pytest

from jobcopilot import gmail_api_sender


def _set_env(monkeypatch):
    monkeypatch.setenv("GMAIL_CLIENT_ID", "client-id")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setenv("GMAIL_ADDRESS", "me@gmail.com")
    monkeypatch.setenv("DIGEST_RECIPIENT_EMAIL", "me@gmail.com")


def test_send_requires_credentials(monkeypatch):
    for var in ["GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN",
                "GMAIL_ADDRESS", "DIGEST_RECIPIENT_EMAIL"]:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(gmail_api_sender.GmailApiNotConfigured):
        gmail_api_sender.send_digest_via_gmail_api([], [])


def test_send_refreshes_token_and_calls_gmail_api(monkeypatch):
    _set_env(monkeypatch)

    token_resp = Mock()
    token_resp.raise_for_status = Mock()
    token_resp.json.return_value = {"access_token": "abc123"}

    send_resp = Mock()
    send_resp.raise_for_status = Mock()

    with patch("jobcopilot.gmail_api_sender.requests.post",
               side_effect=[token_resp, send_resp]) as post:
        gmail_api_sender.send_digest_via_gmail_api([], [])

    assert post.call_count == 2

    token_call = post.call_args_list[0]
    assert token_call.args[0] == gmail_api_sender.TOKEN_URL
    assert token_call.kwargs["data"]["refresh_token"] == "refresh-token"

    send_call = post.call_args_list[1]
    assert send_call.args[0] == gmail_api_sender.SEND_URL
    assert send_call.kwargs["headers"]["Authorization"] == "Bearer abc123"
    assert "raw" in send_call.kwargs["json"]
