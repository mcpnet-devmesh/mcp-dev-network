"""Tests for OAuth 2.1 middleware (auth.py)."""

import asyncio
import time
from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt

# Generate a test RSA key pair
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_pem = _private_key.public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
).decode()
_private_pem = _private_key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
).decode()

TEST_ISSUER = "https://auth.example.com"


def _make_token(sub: str = "user-123", exp_offset: int = 3600, issuer: str = TEST_ISSUER) -> str:
    payload = {"sub": sub, "iss": issuer, "exp": int(time.time()) + exp_offset}
    return jwt.encode(payload, _private_pem, algorithm="RS256")


def _make_request(auth_value: str | None = None) -> MagicMock:
    request = MagicMock()
    if auth_value is not None:
        request.headers = {"Authorization": auth_value}
    else:
        request.headers = {}
    return request


@pytest.fixture(autouse=True)
def _reset_auth_module(monkeypatch):
    """Reset auth module state and set env vars for each test."""
    import mcp_dev_network.auth as auth_mod

    auth_mod._public_key = None
    auth_mod._jwks = None
    auth_mod._issuer = None
    auth_mod._keys_loaded = False
    monkeypatch.setenv("OAUTH_ISSUER", TEST_ISSUER)
    monkeypatch.setenv("OAUTH_PUBLIC_KEY", _public_pem)
    monkeypatch.delenv("OAUTH_JWKS_URL", raising=False)


def test_valid_token():
    from mcp_dev_network.auth import verify_token

    token = _make_token(sub="user-abc")
    request = _make_request(f"Bearer {token}")
    user_id = asyncio.run(verify_token(request))
    assert user_id == "user-abc"


def test_missing_auth_header():
    from fastapi import HTTPException
    from mcp_dev_network.auth import verify_token

    request = _make_request(None)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(verify_token(request))
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Authentication required"


def test_expired_token():
    from fastapi import HTTPException
    from mcp_dev_network.auth import verify_token

    token = _make_token(exp_offset=-100)
    request = _make_request(f"Bearer {token}")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(verify_token(request))
    assert exc_info.value.status_code == 401


def test_wrong_issuer():
    from fastapi import HTTPException
    from mcp_dev_network.auth import verify_token

    token = _make_token(issuer="https://evil.com")
    request = _make_request(f"Bearer {token}")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(verify_token(request))
    assert exc_info.value.status_code == 401


def test_malformed_token():
    from fastapi import HTTPException
    from mcp_dev_network.auth import verify_token

    request = _make_request("Bearer not.a.valid.jwt")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(verify_token(request))
    assert exc_info.value.status_code == 401


def test_bearer_prefix_required():
    from fastapi import HTTPException
    from mcp_dev_network.auth import verify_token

    token = _make_token()
    request = _make_request(f"Token {token}")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(verify_token(request))
    assert exc_info.value.status_code == 401
