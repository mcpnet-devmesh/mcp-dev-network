"""
Tool handler: report_content — Reporta contenido inapropiado para revisión humana.
Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from mcp_dev_network.models import MCPError, ReportContentRequest, ReportContentResponse

if TYPE_CHECKING:
    import asyncpg

_CONTENT_ID_RE = re.compile(r"^(msg|res)_(\d+)$")


class ReportContentError(Exception):
    """Raised when report_content fails for a business-logic reason."""

    def __init__(self, mcp_error: MCPError) -> None:
        self.mcp_error = mcp_error
        super().__init__(mcp_error.message)


async def handle_report_content(
    conn: "asyncpg.Connection",
    user_id: str,
    request: ReportContentRequest,
) -> ReportContentResponse:
    """
    Report inappropriate content for human review.

    Preconditions:
    - Input already validated by Pydantic (ReportContentRequest).
    - user_id comes from verified OAuth session.
    - set_user_context(conn, user_id) already called before this handler.

    Raises ReportContentError on invalid content_id, content not found, or duplicate.
    """
    # 1. Parse content_id (Req 7.1, 7.3)
    match = _CONTENT_ID_RE.match(request.content_id)
    if not match:
        raise ReportContentError(
            MCPError(
                code="VALIDATION_ERROR",
                message="Formato de content_id inválido. Use msg_{id} o res_{id}",
                field="content_id",
            )
        )

    prefix, ref_id_str = match.groups()
    content_type = "message" if prefix == "msg" else "resource"
    content_ref_id = int(ref_id_str)

    # 2. Verify content exists (Req 7.2)
    if content_type == "message":
        exists = await conn.fetchval("SELECT 1 FROM messages WHERE id = $1", content_ref_id)
    else:
        exists = await conn.fetchval("SELECT 1 FROM resources WHERE id = $1", content_ref_id)

    if not exists:
        raise ReportContentError(
            MCPError(
                code="NOT_FOUND",
                message="El contenido referenciado no existe",
                field="content_id",
            )
        )

    # 3. Check duplicate report (Req 7.5)
    already_reported = await conn.fetchval(
        "SELECT 1 FROM reports WHERE reporter_id = $1 AND content_type = $2 AND content_ref_id = $3",
        user_id,
        content_type,
        content_ref_id,
    )
    if already_reported:
        raise ReportContentError(
            MCPError(
                code="DUPLICATE",
                message="El contenido ya fue reportado previamente por el mismo usuario",
                field="content_id",
            )
        )

    # 4. Insert report (Req 7.4)
    row = await conn.fetchrow(
        "INSERT INTO reports (reporter_id, content_type, content_ref_id, reason) "
        "VALUES ($1, $2, $3, $4) RETURNING id",
        user_id,
        content_type,
        content_ref_id,
        request.reason,
    )

    return ReportContentResponse(report_id=row["id"])
