"""
Tool handler: register — Registra un perfil de desarrollador.
Requirements: 1.1, 1.2, 1.6, 1.8, 1.9
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp_dev_network.models import MCPError, RegisterRequest, RegisterResponse

if TYPE_CHECKING:
    import asyncpg


class RegistrationError(Exception):
    """Raised when registration fails for a business-logic reason."""

    def __init__(self, mcp_error: MCPError) -> None:
        self.mcp_error = mcp_error
        super().__init__(mcp_error.message)


async def handle_register(
    conn: "asyncpg.Connection",
    user_id: str,
    request: RegisterRequest,
) -> RegisterResponse:
    """
    Register a developer profile.

    Preconditions:
    - Input already validated by Pydantic (RegisterRequest).
    - user_id comes from verified OAuth session (never from client request).
    - set_user_context(conn, user_id) already called before this handler.

    Raises RegistrationError on duplicate user_id or username.
    """
    # 1. Check if user_id already has a profile (Req 1.9)
    existing = await conn.fetchval(
        "SELECT 1 FROM profiles WHERE user_id = $1", user_id
    )
    if existing is not None:
        raise RegistrationError(
            MCPError(code="DUPLICATE", message="El usuario ya posee un perfil")
        )

    # 2. Check if username is taken (Req 1.2)
    taken = await conn.fetchval(
        "SELECT 1 FROM profiles WHERE username = $1", request.username
    )
    if taken is not None:
        raise RegistrationError(
            MCPError(code="DUPLICATE", message="Username no disponible", field="username")
        )

    # 3. Insert profile (Req 1.1, 1.6) — user_id from OAuth, never from client
    await conn.execute(
        """
        INSERT INTO profiles (user_id, username, stack, bio)
        VALUES ($1, $2, $3, $4)
        """,
        user_id,
        request.username,
        request.stack,
        request.bio,
    )

    return RegisterResponse(username=request.username)
