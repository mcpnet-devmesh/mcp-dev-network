"""list_users tool — browse all registered developers."""

from pydantic import BaseModel, field_validator
from mcp_dev_network.wrapper import wrap_field


class ListUsersRequest(BaseModel):
    limit: int = 20
    offset: int = 0

    @field_validator("limit")
    @classmethod
    def limit_range(cls, v):
        return max(1, min(v, 50))


class UserItem(BaseModel):
    username: str
    stack: list[str]
    bio: str


class ListUsersResponse(BaseModel):
    users: list[UserItem]
    total: int


async def handle_list_users(conn, req: ListUsersRequest) -> ListUsersResponse:
    """List all registered users, newest first."""
    total = await conn.fetchval("SELECT COUNT(*) FROM profiles")
    rows = await conn.fetch(
        "SELECT username, stack, bio FROM profiles ORDER BY created_at DESC LIMIT $1 OFFSET $2",
        req.limit, req.offset,
    )
    users = [
        UserItem(username=row["username"], stack=row["stack"], bio=wrap_field(row["bio"]) or "")
        for row in rows
    ]
    return ListUsersResponse(users=users, total=total)
