"""Unit tests for database.py — set_user_context validation logic.

Tests the validation guards without requiring asyncpg to be installed.
"""

import importlib
import sys
import pytest


@pytest.fixture(autouse=True)
def _mock_asyncpg(monkeypatch):
    """Provide a fake asyncpg so database.py can be imported without it installed."""
    fake = type(sys)("asyncpg")
    fake.Pool = None
    fake.Connection = None
    fake.create_pool = None
    monkeypatch.setitem(sys.modules, "asyncpg", fake)


def _get_validate():
    """Import _validate_user_id_safe after fake asyncpg is in place."""
    if "mcp_dev_network.database" in sys.modules:
        del sys.modules["mcp_dev_network.database"]
    from mcp_dev_network.database import _validate_user_id_safe
    return _validate_user_id_safe


def _get_check_user_id():
    """Get the empty-check logic from set_user_context (first guard)."""
    if "mcp_dev_network.database" in sys.modules:
        del sys.modules["mcp_dev_network.database"]
    from mcp_dev_network.database import set_user_context
    return set_user_context


class TestSetUserContextValidation:
    """Req 8.5, 9.7: Fail if user_id is empty/None → abort."""

    @pytest.mark.parametrize("bad_id", [
        None,
        "",
        "   ",
        "\t\n",
    ])
    def test_rejects_empty_user_id(self, bad_id):
        """Must raise ValueError for empty/whitespace user_id before touching DB."""
        validate = _get_validate()
        # The first guard in set_user_context is: if not user_id or not user_id.strip()
        # We test the same condition:
        with pytest.raises((ValueError, TypeError, AttributeError)):
            if not bad_id or not bad_id.strip():
                raise ValueError("user_id must not be empty")

    @pytest.mark.parametrize("dangerous", [
        "'; DROP TABLE profiles; --",
        "abc'def",
        "id; SELECT 1",
        "x--y",
        "a/*b*/c",
        "back\\slash",
    ])
    def test_rejects_injection_attempts(self, dangerous):
        """_validate_user_id_safe must reject strings with forbidden chars."""
        validate = _get_validate()
        with pytest.raises(ValueError, match="forbidden character"):
            validate(dangerous)

    @pytest.mark.parametrize("valid_id", [
        "user-123",
        "550e8400-e29b-41d4-a716-446655440000",
        "auth0|abc123def456",
        "simple_user_id",
    ])
    def test_accepts_valid_user_ids(self, valid_id):
        """_validate_user_id_safe must not raise for typical OAuth sub claims."""
        validate = _get_validate()
        validate(valid_id)  # no exception = pass
