"""
Tool handler: send_message — Envía un mensaje privado cifrado.
Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp_dev_network.crypto import encrypt_message
from mcp_dev_network.models import MCPError, SendMessageRequest, SendMessageResponse
from mcp_dev_network.rate_limit import check_rate_limit

if TYPE_CHECKING:
    import asyncpg


class SendMessageError(Exception):
    """Raised when send_message fails for a business-logic reason."""

    def __init__(self, mcp_error: MCPError) -> None:
        self.mcp_error = mcp_error
        super().__init__(mcp_error.message)


async def handle_send_message(
    conn: "asyncpg.Connection",
    user_id: str,
    request: SendMessageRequest,
) -> SendMessageResponse:
    """
    Send an encrypted private message to another developer.

    Preconditions:
    - Input already validated by Pydantic (SendMessageRequest).
    - user_id comes from verified OAuth session.
    - set_user_context(conn, user_id) already called before this handler.

    Raises SendMessageError on recipient not found or self-send.
    Raises HTTPException(429) on rate limit exceeded.
    """
    # 1. Resolve sender's username
    sender_username = await conn.fetchval(
        "SELECT username FROM profiles WHERE user_id = $1", user_id
    )
    if sender_username is None:
        raise SendMessageError(
            MCPError(code="NOT_FOUND", message="Remitente no tiene perfil registrado")
        )

    # 2. Check self-send (Req 3.8)
    if request.to_username == sender_username:
        raise SendMessageError(
            MCPError(
                code="VALIDATION_ERROR",
                message="No se permite enviar mensajes a uno mismo",
                field="to_username",
            )
        )

    # 3. Resolve recipient
    recipient_id = await conn.fetchval(
        "SELECT user_id FROM profiles WHERE username = $1", request.to_username
    )
    if recipient_id is None:
        raise SendMessageError(
            MCPError(code="NOT_FOUND", message="Destinatario no encontrado", field="to_username")
        )

    # 4. Rate limit: 20 messages per hour (Req 3.6)
    await check_rate_limit(conn, user_id, "send_message", 20, 3600)

    # 5. Encrypt content (Req 3.5)
    content_encrypted = encrypt_message(request.content)

    # 6. Insert message (Req 3.7)
    row = await conn.fetchrow(
        "INSERT INTO messages (sender_id, recipient_id, content_encrypted) "
        "VALUES ($1, $2, $3) RETURNING id, created_at",
        user_id,
        recipient_id,
        content_encrypted,
    )

    return SendMessageResponse(message_id=row["id"], created_at=row["created_at"])
