"""get_my_profile tool — view your own profile."""

from pydantic import BaseModel


class GetMyProfileRequest(BaseModel):
    pass


class MyProfileResponse(BaseModel):
    username: str
    stack: list[str]
    bio: str
    created_at: str


async def handle_get_my_profile(conn, user_id: str, req: GetMyProfileRequest) -> MyProfileResponse:
    """Get the authenticated user's own profile."""
    row = await conn.fetchrow(
        "SELECT username, stack, bio, created_at FROM profiles WHERE user_id = $1", user_id
    )
    if not row:
        from mcp_dev_network.models import MCPError
        from mcp_dev_network.tools.register import RegistrationError
        raise RegistrationError(MCPError(code="NOT_FOUND", message="No tienes perfil. Usa 'register' primero."))
    return MyProfileResponse(
        username=row["username"],
        stack=row["stack"],
        bio=row["bio"],
        created_at=row["created_at"].isoformat() + "Z",
    )
