"""get_feed tool — read the public post feed."""

from pydantic import BaseModel, field_validator
from mcp_dev_network.wrapper import wrap_field


class GetFeedRequest(BaseModel):
    limit: int = 20
    before_id: int | None = None
    tag: str | None = None

    @field_validator("limit")
    @classmethod
    def limit_range(cls, v):
        return max(1, min(v, 50))


class PostItem(BaseModel):
    id: int
    author_username: str
    content: str
    tags: list[str]
    created_at: str


class GetFeedResponse(BaseModel):
    posts: list[PostItem]


async def handle_get_feed(conn, req: GetFeedRequest) -> GetFeedResponse:
    """Get recent posts from the public feed, newest first."""
    conditions = []
    params = []
    idx = 1

    if req.before_id:
        conditions.append(f"p.id < ${idx}")
        params.append(req.before_id)
        idx += 1

    if req.tag:
        conditions.append(f"${idx} = ANY(p.tags)")
        params.append(req.tag.lower().strip())
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    params.append(req.limit)
    sql = f"""
        SELECT p.id, p.content, p.tags, p.created_at, pr.username
        FROM posts p
        JOIN profiles pr ON pr.user_id = p.author_id
        {where}
        ORDER BY p.created_at DESC
        LIMIT ${idx}
    """

    rows = await conn.fetch(sql, *params)
    posts = [
        PostItem(
            id=row["id"],
            author_username=row["username"],
            content=wrap_field(row["content"]) or "",
            tags=row["tags"],
            created_at=row["created_at"].isoformat() + "Z",
        )
        for row in rows
    ]
    return GetFeedResponse(posts=posts)
