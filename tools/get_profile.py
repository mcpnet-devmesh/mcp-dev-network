"""
get_profile tool handler.
Requirements: 2.1, 2.2, 2.3, 2.4
"""

import asyncpg

from mcp_dev_network.models import GetProfileRequest, MCPError, ProfileResponse


class ProfileNotFoundError(Exception):
    """Raised when the requested profile does not exist."""

    def __init__(self) -> None:
        super().__init__("Perfil no encontrado")


async def handle_get_profile(
    conn: asyncpg.Connection, request: GetProfileRequest
) -> ProfileResponse:
    """
    Consulta el perfil público de un desarrollador.

    - Input validation handled by Pydantic (GetProfileRequest).
    - ONLY selects username, stack, bio — never id, user_id, timestamps, etc. (Req 2.2)
    - Parametrized query only (Req 2.4 / security).
    - Generic error on not found — no internal info leaked (Req 2.3).
    """
    # ponytail: single parametrized query, selecting only public fields
    row = await conn.fetchrow(
        "SELECT username, stack, bio FROM profiles WHERE username = $1",
        request.username,
    )

    if row is None:
        raise ProfileNotFoundError()

    return ProfileResponse(
        username=row["username"],
        stack=row["stack"],
        bio=row["bio"],
    )
