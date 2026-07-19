"""Secure Logger — structured JSON logging without PII.

Validates: Requirements 11.1, 11.2, 11.3, 11.4
"""

import json
import logging
import re
from datetime import datetime, timezone

# ponytail: single compiled regex for emails, covers 99% of real-world cases
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# ponytail: detect tokens/message content — JWT pattern or long base64 blobs (>40 chars)
_TOKEN_RE = re.compile(
    r"eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"  # JWT
    r"|[A-Za-z0-9+/=_\-]{40,}"  # long base64-ish strings
)

# Fields that should be suppressed entirely (message content, tokens)
_SENSITIVE_FIELD_NAMES = {"content", "message_content", "token", "access_token", "bearer", "password", "secret"}

_logger = logging.getLogger("mcp_dev_network")
_logger.setLevel(logging.INFO)

# stdout JSON handler — one line per event
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_handler)


def _mask_email(match: re.Match) -> str:
    """XX***@domain — show first 2 chars of local part."""
    email = match.group(0)
    local, domain = email.rsplit("@", 1)
    masked_local = local[:2] + "***" if len(local) >= 2 else local[0] + "***"
    return f"{masked_local}@{domain}"


def _sanitize_value(value: str) -> tuple[str, bool]:
    """Sanitize a string value. Returns (sanitized, was_redacted)."""
    redacted = False

    # Suppress tokens/long base64
    if _TOKEN_RE.search(value):
        return "[REDACTED]", True

    # Mask emails
    if _EMAIL_RE.search(value):
        value = _EMAIL_RE.sub(_mask_email, value)
        redacted = True

    return value, redacted


def log_event(user_id: str, operation: str, error_type: str | None = None) -> None:
    """Log structured JSON event to stdout. Masks emails, suppresses tokens/content."""
    entry: dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "operation": operation,
    }

    if error_type is not None:
        entry["error_type"] = error_type

    # Sanitize all string fields
    redacted = False
    for key in list(entry.keys()):
        val = entry[key]
        if not isinstance(val, str):
            continue
        # Suppress known sensitive field names
        if key in _SENSITIVE_FIELD_NAMES:
            entry[key] = "[REDACTED]"
            redacted = True
            continue
        sanitized, was_redacted = _sanitize_value(val)
        entry[key] = sanitized
        redacted = redacted or was_redacted

    if redacted:
        entry["redacted"] = True

    _logger.info(json.dumps(entry, ensure_ascii=False))
