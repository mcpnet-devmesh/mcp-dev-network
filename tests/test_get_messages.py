"""
Tests para tools/get_messages.py — verifica lectura de bandeja de mensajes.
Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from mcp_dev_network.models import GetMessagesRequest
from mcp_dev_network.tools.get_messages import InvalidBeforeIdError, handle_get_messages
from mcp_dev_network.wrapper import PREFIX


def _run(coro):
    return asyncio.run(coro)


def _make_rows(count=2):
    """Fake message rows as returned by asyncpg."""
    return [
        {
            "id": 100 - i,
            "from_username": f"sender{i}",
            "content_encrypted": "encrypted_b64",
            "created_at": datetime(2025, 1, 1 + i, tzinfo=timezone.utc),
        }
        for i in range(count)
    ]


@patch("mcp_dev_network.tools.get_messages.decrypt_message", return_value="Hola mundo")
def test_returns_messages_decrypted_and_wrapped(mock_decrypt):
    """Req 4.1, 4.6: mensajes descifrados + wrapper aplicado."""
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=_make_rows(2))
    req = GetMessagesRequest()

    result = _run(handle_get_messages(conn, "user-1", req))

    assert len(result.messages) == 2
    for msg in result.messages:
        assert msg.content.startswith(PREFIX)
        assert "Hola mundo" in msg.content
    mock_decrypt.assert_called_with("encrypted_b64")


@patch("mcp_dev_network.tools.get_messages.decrypt_message", return_value="text")
def test_empty_inbox_returns_empty_list(mock_decrypt):
    """Req 4.1: si no hay mensajes, devuelve lista vacía."""
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    req = GetMessagesRequest()

    result = _run(handle_get_messages(conn, "user-1", req))

    assert result.messages == []


@patch("mcp_dev_network.tools.get_messages.decrypt_message", return_value="text")
def test_before_id_valid(mock_decrypt):
    """Req 4.4: before_id válido filtra correctamente."""
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=1)  # before_id exists
    conn.fetch = AsyncMock(return_value=_make_rows(1))
    req = GetMessagesRequest(before_id=50)

    result = _run(handle_get_messages(conn, "user-1", req))

    # Validate before_id check query
    validate_query = conn.fetchval.call_args[0][0]
    assert "messages" in validate_query
    assert "$1" in validate_query and "$2" in validate_query
    # Validate main query uses before_id filter
    main_query = conn.fetch.call_args[0][0]
    assert "m.id < $2" in main_query
    assert len(result.messages) == 1


@patch("mcp_dev_network.tools.get_messages.decrypt_message", return_value="text")
def test_before_id_invalid_raises(mock_decrypt):
    """Req 4.5: before_id inexistente → error."""
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=None)  # not found
    req = GetMessagesRequest(before_id=9999)

    with pytest.raises(InvalidBeforeIdError, match="before_id inválido"):
        _run(handle_get_messages(conn, "user-1", req))

    conn.fetch.assert_not_called()


@patch("mcp_dev_network.tools.get_messages.decrypt_message", return_value="text")
def test_uses_parametrized_queries(mock_decrypt):
    """Req 4.2: todas las queries son parametrizadas."""
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=_make_rows(1))
    req = GetMessagesRequest(limit=10)

    _run(handle_get_messages(conn, "user-1", req))

    query = conn.fetch.call_args[0][0]
    assert "$1" in query
    assert "recipient_id" in query


@patch("mcp_dev_network.tools.get_messages.decrypt_message", return_value="text")
def test_respects_limit(mock_decrypt):
    """Req 4.3: limit se pasa a la query."""
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    req = GetMessagesRequest(limit=5)

    _run(handle_get_messages(conn, "user-1", req))

    # The limit param is passed to the query
    args = conn.fetch.call_args[0]
    assert 5 in args  # limit is in positional args


@patch("mcp_dev_network.tools.get_messages.decrypt_message", return_value="text")
def test_order_by_created_at_desc(mock_decrypt):
    """Req 4.1: query ordena por created_at DESC."""
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    req = GetMessagesRequest()

    _run(handle_get_messages(conn, "user-1", req))

    query = conn.fetch.call_args[0][0]
    assert "ORDER BY m.created_at DESC" in query


def test_request_validation_defaults():
    """Req 4.3: default limit = 20, before_id = None."""
    req = GetMessagesRequest()
    assert req.limit == 20
    assert req.before_id is None


def test_request_validation_rejects_out_of_range():
    """Req 4.3: limit fuera de rango 1-100 rechazado por Pydantic."""
    with pytest.raises(Exception):
        GetMessagesRequest(limit=0)
    with pytest.raises(Exception):
        GetMessagesRequest(limit=101)
    with pytest.raises(Exception):
        GetMessagesRequest(before_id=0)


if __name__ == "__main__":
    test_returns_messages_decrypted_and_wrapped()
    test_empty_inbox_returns_empty_list()
    test_before_id_valid()
    test_before_id_invalid_raises()
    test_uses_parametrized_queries()
    test_respects_limit()
    test_order_by_created_at_desc()
    test_request_validation_defaults()
    test_request_validation_rejects_out_of_range()
    print("All get_messages tests passed.")
