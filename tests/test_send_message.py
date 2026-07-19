"""
Tests para tools/send_message.py — verifica envío de mensajes privados cifrados.
Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from mcp_dev_network.models import SendMessageRequest
from mcp_dev_network.tools.send_message import SendMessageError, handle_send_message


def _run(coro):
    return asyncio.run(coro)


def _make_conn(sender_username="alice", recipient_id="recipient-uid"):
    """
    Mock connection:
    - fetchval calls: 1st → sender_username, 2nd → recipient_id
    - fetchrow: returns inserted message row
    """
    conn = AsyncMock()
    conn.fetchval = AsyncMock(side_effect=[sender_username, recipient_id])
    conn.fetchrow = AsyncMock(
        return_value={"id": 42, "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc)}
    )
    conn.execute = AsyncMock()
    return conn


@patch("mcp_dev_network.tools.send_message.check_rate_limit", new_callable=AsyncMock)
@patch("mcp_dev_network.tools.send_message.encrypt_message", return_value="encrypted_base64")
def test_successful_send(mock_encrypt, mock_rate_limit):
    """Envío exitoso: destinatario existe, no es auto-envío, dentro del rate limit."""
    conn = _make_conn(sender_username="alice", recipient_id="bob-uid")
    req = SendMessageRequest(to_username="bob", content="Hola Bob")

    result = _run(handle_send_message(conn, "alice-uid", req))

    assert result.message_id == 42
    assert result.created_at == datetime(2025, 1, 1, tzinfo=timezone.utc)
    # Verify encryption was called with plaintext
    mock_encrypt.assert_called_once_with("Hola Bob")
    # Verify INSERT used parametrized query
    insert_sql = conn.fetchrow.call_args[0][0]
    assert "INSERT INTO messages" in insert_sql
    assert "$1" in insert_sql and "$2" in insert_sql and "$3" in insert_sql


@patch("mcp_dev_network.tools.send_message.check_rate_limit", new_callable=AsyncMock)
@patch("mcp_dev_network.tools.send_message.encrypt_message", return_value="enc")
def test_rejects_self_send(mock_encrypt, mock_rate_limit):
    """Req 3.8: no se permite enviar mensajes a uno mismo."""
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value="alice")  # sender is alice
    req = SendMessageRequest(to_username="alice", content="Hola yo")

    with pytest.raises(SendMessageError) as exc_info:
        _run(handle_send_message(conn, "alice-uid", req))

    assert exc_info.value.mcp_error.code == "VALIDATION_ERROR"
    assert "uno mismo" in exc_info.value.mcp_error.message
    # No message inserted
    conn.fetchrow.assert_not_called()
    mock_encrypt.assert_not_called()


@patch("mcp_dev_network.tools.send_message.check_rate_limit", new_callable=AsyncMock)
@patch("mcp_dev_network.tools.send_message.encrypt_message", return_value="enc")
def test_rejects_recipient_not_found(mock_encrypt, mock_rate_limit):
    """Req 3.3: destinatario no encontrado → error NOT_FOUND."""
    conn = AsyncMock()
    conn.fetchval = AsyncMock(side_effect=["alice", None])  # recipient not found
    req = SendMessageRequest(to_username="ghost", content="Hola?")

    with pytest.raises(SendMessageError) as exc_info:
        _run(handle_send_message(conn, "alice-uid", req))

    assert exc_info.value.mcp_error.code == "NOT_FOUND"
    assert "Destinatario no encontrado" in exc_info.value.mcp_error.message
    conn.fetchrow.assert_not_called()


@patch("mcp_dev_network.tools.send_message.check_rate_limit", new_callable=AsyncMock)
@patch("mcp_dev_network.tools.send_message.encrypt_message", return_value="enc")
def test_rejects_sender_without_profile(mock_encrypt, mock_rate_limit):
    """Remitente sin perfil registrado → error NOT_FOUND."""
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=None)  # sender has no profile
    req = SendMessageRequest(to_username="bob", content="Hola")

    with pytest.raises(SendMessageError) as exc_info:
        _run(handle_send_message(conn, "no-profile-uid", req))

    assert exc_info.value.mcp_error.code == "NOT_FOUND"
    assert "Remitente" in exc_info.value.mcp_error.message


@patch("mcp_dev_network.tools.send_message.check_rate_limit", new_callable=AsyncMock)
@patch("mcp_dev_network.tools.send_message.encrypt_message", return_value="enc")
def test_rate_limit_called_correctly(mock_encrypt, mock_rate_limit):
    """Req 3.6: rate limit de 20 mensajes por hora."""
    conn = _make_conn(sender_username="alice", recipient_id="bob-uid")
    req = SendMessageRequest(to_username="bob", content="Msg")

    _run(handle_send_message(conn, "alice-uid", req))

    mock_rate_limit.assert_called_once_with(conn, "alice-uid", "send_message", 20, 3600)


@patch("mcp_dev_network.tools.send_message.check_rate_limit", new_callable=AsyncMock)
@patch("mcp_dev_network.tools.send_message.encrypt_message", return_value="enc")
def test_rate_limit_exceeded_propagates(mock_encrypt, mock_rate_limit):
    """Rate limit excedido → HTTPException(429) propagates."""
    mock_rate_limit.side_effect = HTTPException(status_code=429, detail="Rate limit")
    conn = _make_conn(sender_username="alice", recipient_id="bob-uid")
    req = SendMessageRequest(to_username="bob", content="Msg")

    with pytest.raises(HTTPException) as exc_info:
        _run(handle_send_message(conn, "alice-uid", req))

    assert exc_info.value.status_code == 429


@patch("mcp_dev_network.tools.send_message.check_rate_limit", new_callable=AsyncMock)
@patch("mcp_dev_network.tools.send_message.encrypt_message", return_value="enc")
def test_parametrized_queries(mock_encrypt, mock_rate_limit):
    """All queries use positional params — never string concat."""
    conn = _make_conn(sender_username="alice", recipient_id="bob-uid")
    req = SendMessageRequest(to_username="bob", content="'; DROP TABLE messages--")

    _run(handle_send_message(conn, "alice-uid", req))

    for call in conn.fetchval.call_args_list:
        assert "$1" in call[0][0]
    assert "$1" in conn.fetchrow.call_args[0][0]


if __name__ == "__main__":
    test_successful_send()
    test_rejects_self_send()
    test_rejects_recipient_not_found()
    test_rejects_sender_without_profile()
    test_rate_limit_called_correctly()
    test_rate_limit_exceeded_propagates()
    test_parametrized_queries()
    print("All send_message tests passed.")
