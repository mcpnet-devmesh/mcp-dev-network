"""
search_resources tool handler.
Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8
"""

import asyncpg

from mcp_dev_network.models import (
    ResourceItem,
    SearchResourcesRequest,
    SearchResourcesResponse,
)
from mcp_dev_network.wrapper import wrap_field


async def handle_search_resources(
    conn: asyncpg.Connection, request: SearchResourcesRequest
) -> SearchResourcesResponse:
    """
    Busca recursos por tags exactos (OR) y/o full-text (tsvector/tsquery).

    - Input validation (at_least_one_criterion) handled by Pydantic model_validator.
    - Tags normalized to lowercase for case-insensitive match.
    - Max 50 results, ordered by created_at DESC (Req 6.2).
    - Untrusted Content Wrapper on title and url_or_snippet (Req 6.4).
    - Parametrized queries only (Req 6.6).
    - Empty result → empty list, no error (Req 6.7).
    """
    has_tags = request.tags and len(request.tags) > 0
    has_query = request.query and request.query.strip()

    # ponytail: build query dynamically based on criteria provided
    conditions: list[str] = []
    params: list[object] = []
    idx = 1

    if has_tags:
        # Normalize tags to lowercase for case-insensitive matching
        normalized_tags = [t.lower() for t in request.tags]  # type: ignore[union-attr]
        conditions.append(f"r.tags && ${idx}::text[]")
        params.append(normalized_tags)
        idx += 1

    if has_query:
        conditions.append(
            f"r.search_vector @@ plainto_tsquery('spanish', ${idx})"
        )
        params.append(request.query.strip())  # type: ignore[union-attr]
        idx += 1

    where_clause = " OR ".join(conditions)

    sql = (
        "SELECT r.id, p.username AS author_username, r.title, r.url_or_snippet, "
        "r.tags, r.created_at "
        "FROM resources r "
        "JOIN profiles p ON p.user_id = r.author_id "
        f"WHERE {where_clause} "
        "ORDER BY r.created_at DESC "
        "LIMIT 50"
    )

    rows = await conn.fetch(sql, *params)

    resources = [
        ResourceItem(
            id=row["id"],
            author_username=row["author_username"],
            title=wrap_field(row["title"]),  # type: ignore[arg-type]
            url_or_snippet=wrap_field(row["url_or_snippet"]),  # type: ignore[arg-type]
            tags=row["tags"],
            created_at=row["created_at"],
        )
        for row in rows
    ]

    return SearchResourcesResponse(resources=resources)
