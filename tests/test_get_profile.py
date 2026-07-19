"""Tests for get_profile tool handler."""

import asyncio
import pytest
from unittest.mock import AsyncMock

from mcp_dev_network.models import GetProfileRequest, ProfileResponse
from mcp_dev_network.tools.get_profile import handle_get_profile, ProfileNotFoundError


def test_get_profile_found():
    """Existing profile returns only username, stack, bio (Req 2.1, 2.2)."""
    conn = AsyncMock()
    conn.fetchrow.return_value = {
        "username": "alice_dev",
        "stack": ["python", "fastapi"],
        "bio": "Backend dev",
    }
    request = GetProfileRequest(username="alice_dev")
    result = asyncio.run(handle_get_profile(conn, request))

    assert isinstance(result, ProfileResponse)
    assert result.username == "alice_dev"
    assert result.stack == ["python", "fastapi"]
    assert result.bio == "Backend dev"
    # Verify parametrized query selects ONLY public fields
    conn.fetchrow.assert_called_once_with(
        "SELECT username, stack, bio FROM profiles WHERE username = $1",
        "alice_dev",
    )


def test_get_profile_not_found():
    """Non-existent username raises ProfileNotFoundError (Req 2.3)."""
    conn = AsyncMock()
    conn.fetchrow.return_value = None
    request = GetProfileRequest(username="ghost_user")

    with pytest.raises(ProfileNotFoundError, match="Perfil no encontrado"):
        asyncio.run(handle_get_profile(conn, request))


def test_get_profile_request_validation_rejects_invalid():
    """Invalid usernames are rejected at validation layer (Req 2.4)."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        GetProfileRequest(username="")
    with pytest.raises(Exception):
        GetProfileRequest(username="a" * 40)
    with pytest.raises(Exception):
        GetProfileRequest(username="user!@#")


def test_get_profile_request_validation_accepts_valid():
    """Valid usernames pass Pydantic validation."""
    req = GetProfileRequest(username="valid_user123")
    assert req.username == "valid_user123"
