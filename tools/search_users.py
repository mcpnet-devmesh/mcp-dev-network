"""search_users tool — find developers by stack, username, or bio."""

from pydantic import BaseModel, field_validator
from mcp_dev_network.wrapper import wrap_field


class SearchUsersRequest(BaseModel):
    query: str | None = None
    stack: list[str] | None = None

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError("query no puede estar vacío")
        return v

    def model_post_init(self, __context):
        if not self.query and not self.stack:
            raise ValueError("Debes proporcionar query o stack (o ambos)")


class UserResult(BaseModel):
    username: str
    stack: list[str]
    bio: str


class SearchUsersResponse(BaseModel):
    users: list[UserResult]


async def handle_search_users(conn, req: SearchUsersRequest) -> SearchUsersResponse:
    """Search users by username/bio text or by stack overlap."""
    conditions = []
    params = []
    idx = 1

    if req.query:
        conditions.append(f"(username ILIKE ${idx} OR bio ILIKE ${idx})")
        params.append(f"%{req.query}%")
        idx += 1

    if req.stack:
        # Find users whose stack overlaps with requested stack
        conditions.append(f"stack && ${idx}::text[]")
        params.append(req.stack)
        idx += 1

    where = " AND ".join(conditions) if conditions else "TRUE"
    sql = f"SELECT username, stack, bio FROM profiles WHERE {where} ORDER BY created_at DESC LIMIT 50"

    rows = await conn.fetch(sql, *params)
    users = [
        UserResult(
            username=row["username"],
            stack=row["stack"],
            bio=wrap_field(row["bio"]) or "",
        )
        for row in rows
    ]
    return SearchUsersResponse(users=users)
