"""Tests for Secure Logger — Requirements 11.1, 11.2, 11.3, 11.4."""

import json
import logging

from mcp_dev_network.logger import log_event


def _capture_log(caplog, user_id, operation, error_type=None):
    """Helper: capture log output and parse JSON."""
    with caplog.at_level(logging.INFO, logger="mcp_dev_network"):
        log_event(user_id, operation, error_type)
    raw = caplog.records[-1].message
    return json.loads(raw)


def test_basic_structured_output(caplog):
    """Log entry has required fields in JSON."""
    entry = _capture_log(caplog, "user-123", "register")
    assert entry["user_id"] == "user-123"
    assert entry["operation"] == "register"
    assert "timestamp" in entry
    assert "T" in entry["timestamp"]  # ISO 8601


def test_error_type_included(caplog):
    """error_type appears when provided."""
    entry = _capture_log(caplog, "user-456", "send_message", "RATE_LIMITED")
    assert entry["error_type"] == "RATE_LIMITED"


def test_error_type_absent_when_none(caplog):
    """error_type omitted when not provided."""
    entry = _capture_log(caplog, "user-789", "get_profile")
    assert "error_type" not in entry


def test_email_masking(caplog):
    """Emails in fields are masked to XX***@domain format."""
    entry = _capture_log(caplog, "john.doe@example.com", "register")
    assert entry["user_id"] == "jo***@example.com"
    assert entry["redacted"] is True


def test_email_short_local(caplog):
    """Email with 1-char local part still masks correctly."""
    entry = _capture_log(caplog, "a@x.co", "login")
    assert "@x.co" in entry["user_id"]
    assert "a@x.co" not in entry["user_id"]


def test_token_suppression(caplog):
    """JWT-like tokens in fields are redacted."""
    jwt = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyMSJ9.signature_here_abc"
    entry = _capture_log(caplog, jwt, "auth_check")
    assert entry["user_id"] == "[REDACTED]"
    assert entry["redacted"] is True


def test_long_base64_suppression(caplog):
    """Long base64 strings (potential tokens/keys) are redacted."""
    blob = "A" * 50
    entry = _capture_log(caplog, blob, "some_op")
    assert entry["user_id"] == "[REDACTED]"
    assert entry["redacted"] is True


def test_no_redaction_flag_when_clean(caplog):
    """No 'redacted' field when nothing was sanitized."""
    entry = _capture_log(caplog, "uuid-1234", "get_messages")
    assert "redacted" not in entry
