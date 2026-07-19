"""
get_messages tool handler.
Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
"""

import asyncpg

from mcp_dev_network.crypto import decrypt_message
from mcp_dev_network.models import GetMessagesRequest, GetMessagesResponse, MessageItem
from mcp_dev_network.wrapper import wrap_field


class InvalidBeforeIdError(Exception):
    """Raised when before_id doesn't exist in the user's inbox."""

    def __init__(self) -> None:
        super().__init__("before_id inválido")


async def handle_get_messages(
    conn: asyncpg.Connection, user_id: str, request: GetMessagesRequest
) -> GetMessagesResponse:
    """
    Lee mensajes recibidos del usuario autenticado, paginados por cursor.

    - Input validation handled by Pydantic (GetMessagesRequest) (Req 4.3)
    - user_id comes from OAuth session, never from client (Req 4.7)
    - RLS filters by recipient_id = current_setting (Req 4.2), explicit filter for clarity
    - Decrypts content with AES-256-GCM (Req 4.1)
    - Wraps decrypted content with Untrusted Content Wrapper (Req 4.6)
    - Cursor pagination via before_id (Req 4.4, 4.5)
    - Order by created_at DESC (Req 4.1)
    """
    # Validate before_id exists in user's inbox (Req 4.5)
    if request.before_id is not None:
        exists = await conn.fetchval(
            "SELECT 1 FROM messages WHERE id = $1 AND recipient_id = $2",
            request.before_id,
            user_id,
        )
        if not exists:
            raise InvalidBeforeIdError()

    # Build query — parametrized only (Req 4.2)
    if request.before_id is not None:
        rows = await conn.fetch(
            """
            SELECT m.id, p.username AS from_username, m.content_encrypted, m.created_at
            FROM messages m
            JOIN profiles p ON p.user_id = m.sender_id
            WHERE m.recipient_id = $1 AND m.id < $2
            ORDER BY m.created_at DESC
            LIMIT $3
            """,
            user_id,
            request.before_id,
            request.limit,
        )
    else:
        rows = await conn.fetch(
            """
            SELECT m.id, p.username AS from_username, m.content_encrypted, m.created_at
            FROM messages m
            JOIN profiles p ON p.user_id = m.sender_id
            WHERE m.recipient_id = $1
            ORDER BY m.created_at DESC
            LIMIT $2
            """,
            user_id,
            request.limit,
        )

    # Decrypt + wrap each message (Req 4.1, 4.6)
    messages = [
        MessageItem(
            id=row["id"],
            from_username=row["from_username"],
            content=wrap_field(decrypt_message(row["content_encrypted"])),
            created_at=row["created_at"],
        )
        for row in rows
    ]

    return GetMessagesResponse(messages=messages)
