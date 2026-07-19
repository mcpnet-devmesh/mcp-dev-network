"""
Tests para tools/register.py — verifica lógica de registro de perfiles.
Validates: Requirements 1.1, 1.2, 1.6, 1.8, 1.9
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from mcp_dev_network.models import RegisterRequest
from mcp_dev_network.tools.register import RegistrationError, handle_register


def _run(coro):
    return asyncio.run(coro)


def _make_conn(user_exists=None, username_taken=None):
    """
    Mock connection where fetchval returns:
    - First call: user_exists (check user_id has profile)
    - Second call: username_taken (check username availability)
    """
    conn = AsyncMock()
    conn.fetchval = AsyncMock(side_effect=[user_exists, username_taken])
    conn.execute = AsyncMock()
    return conn


def test_successful_registration():
    """Registro exitoso: user_id nuevo, username disponible."""
    conn = _make_conn(user_exists=None, username_taken=None)
    req = RegisterRequest(username="dev_user", stack=["python", "fastapi"], bio="Hola")

    result = _run(handle_register(conn, "oauth-user-123", req))

    assert result.username == "dev_user"
    assert result.message == "Perfil registrado exitosamente"
    # Verify INSERT was called with parametrized values
    conn.execute.assert_called_once()
    sql, uid, uname, stack, bio = conn.execute.call_args[0]
    assert "INSERT INTO profiles" in sql
    assert uid == "oauth-user-123"
    assert uname == "dev_user"
    assert stack == ["python", "fastapi"]
    assert bio == "Hola"


def test_rejects_duplicate_user_id():
    """Req 1.9: user_id ya tiene perfil → error DUPLICATE."""
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=1)  # first check returns existing
    req = RegisterRequest(username="new_user", stack=["rust"])

    with pytest.raises(RegistrationError) as exc_info:
        _run(handle_register(conn, "existing-user", req))

    assert exc_info.value.mcp_error.code == "DUPLICATE"
    assert "ya posee un perfil" in exc_info.value.mcp_error.message
    conn.execute.assert_not_called()


def test_rejects_duplicate_username():
    """Req 1.2: username ya tomado → error DUPLICATE."""
    conn = AsyncMock()
    # First call (user_id check) → None; second (username check) → exists
    conn.fetchval = AsyncMock(side_effect=[None, 1])
    conn.execute = AsyncMock()
    req = RegisterRequest(username="taken_name", stack=["go"])

    with pytest.raises(RegistrationError) as exc_info:
        _run(handle_register(conn, "new-user-id", req))

    assert exc_info.value.mcp_error.code == "DUPLICATE"
    assert "Username no disponible" in exc_info.value.mcp_error.message
    assert exc_info.value.mcp_error.field == "username"
    conn.execute.assert_not_called()


def test_user_id_from_param_not_request():
    """Req 1.6: user_id comes from OAuth (parameter), never from request body."""
    conn = _make_conn(user_exists=None, username_taken=None)
    req = RegisterRequest(username="abc_user", stack=["node"])

    _run(handle_register(conn, "oauth-provided-id", req))

    # The INSERT uses the oauth-provided user_id
    _, uid, *_ = conn.execute.call_args[0]
    assert uid == "oauth-provided-id"


def test_bio_defaults_to_empty():
    """Req 1.5: bio opcional, defaults to empty string."""
    conn = _make_conn(user_exists=None, username_taken=None)
    req = RegisterRequest(username="dev123", stack=["typescript"])

    _run(handle_register(conn, "user-456", req))

    _, _, _, _, bio = conn.execute.call_args[0]
    assert bio == ""


def test_parametrized_queries():
    """All queries use $1, $2 etc. placeholders — never string concat."""
    conn = _make_conn(user_exists=None, username_taken=None)
    req = RegisterRequest(username="safe_user", stack=["sql"], bio="'; DROP TABLE--")

    _run(handle_register(conn, "user-safe", req))

    # Verify all fetchval calls used positional params
    for c in conn.fetchval.call_args_list:
        sql = c[0][0]
        assert "$1" in sql

    # Verify INSERT used positional params
    insert_sql = conn.execute.call_args[0][0]
    assert "$1" in insert_sql and "$2" in insert_sql


if __name__ == "__main__":
    test_successful_registration()
    test_rejects_duplicate_user_id()
    test_rejects_duplicate_username()
    test_user_id_from_param_not_request()
    test_bio_defaults_to_empty()
    test_parametrized_queries()
    print("All register tests passed.")
