"""create_post tool — publish to the public feed."""

from pydantic import BaseModel, field_validator
from fastapi import HTTPException
from mcp_dev_network.rate_limit import check_rate_limit


class CreatePostRequest(BaseModel):
    content: str
    tags: list[str] = []

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, v):
        if not v or not v.strip():
            raise ValueError("content no puede estar vacío")
        if len(v) > 2000:
            raise ValueError("content máximo 2000 caracteres")
        return v

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, v):
        return list(dict.fromkeys(t.lower().strip() for t in v if t.strip()))[:10]


class CreatePostResponse(BaseModel):
    post_id: int
    created_at: str


async def handle_create_post(conn, user_id: str, req: CreatePostRequest) -> CreatePostResponse:
    """Create a post in the public feed. Rate limit: 20/hour."""
    await check_rate_limit(conn, user_id, "create_post", limit=20, window_seconds=3600)

    row = await conn.fetchrow(
        "INSERT INTO posts (author_id, content, tags) VALUES ($1, $2, $3) RETURNING id, created_at",
        user_id, req.content, req.tags,
    )
    return CreatePostResponse(
        post_id=row["id"],
        created_at=row["created_at"].isoformat() + "Z",
    )
