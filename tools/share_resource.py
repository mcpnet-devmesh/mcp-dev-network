"""
Tool handler: share_resource — Publica un recurso técnico con tags.
Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp_dev_network.models import MCPError, ShareResourceRequest, ShareResourceResponse
from mcp_dev_network.rate_limit import check_rate_limit

if TYPE_CHECKING:
    import asyncpg


class ShareResourceError(Exception):
    """Raised when share_resource fails for a business-logic reason."""

    def __init__(self, mcp_error: MCPError) -> None:
        self.mcp_error = mcp_error
        super().__init__(mcp_error.message)


async def handle_share_resource(
    conn: "asyncpg.Connection",
    user_id: str,
    request: ShareResourceRequest,
) -> ShareResourceResponse:
    """
    Publish a technical resource with tags.

    Preconditions:
    - Input already validated by Pydantic (ShareResourceRequest — tags normalized to lowercase + deduped).
    - user_id comes from verified OAuth session (Req 5.7).
    - set_user_context(conn, user_id) already called before this handler.

    Raises ShareResourceError if author has no profile.
    Raises HTTPException(429) on rate limit exceeded (Req 5.6).
    """
    # 1. Verify author has a registered profile
    has_profile = await conn.fetchval(
        "SELECT 1 FROM profiles WHERE user_id = $1", user_id
    )
    if has_profile is None:
        raise ShareResourceError(
            MCPError(code="NOT_FOUND", message="Autor no tiene perfil registrado")
        )

    # 2. Rate limit: 10 resources per hour (Req 5.6)
    await check_rate_limit(conn, user_id, "share_resource", 10, 3600)

    # 3. Insert resource — parametrized query (Req 5.8)
    # ponytail: tags already normalized (lowercase + dedup) by Pydantic validator.
    # tsvector updated by PostgreSQL trigger — no computation needed here.
    row = await conn.fetchrow(
        "INSERT INTO resources (author_id, title, url_or_snippet, tags) "
        "VALUES ($1, $2, $3, $4) RETURNING id, created_at",
        user_id,
        request.title,
        request.url_or_snippet,
        request.tags,
    )

    return ShareResourceResponse(resource_id=row["id"], created_at=row["created_at"])
