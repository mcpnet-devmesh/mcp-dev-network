"""follow/unfollow tools."""
from pydantic import BaseModel
from fastapi import HTTPException


class FollowRequest(BaseModel):
    username: str


class FollowResponse(BaseModel):
    success: bool
    message: str


class UnfollowRequest(BaseModel):
    username: str


class UnfollowResponse(BaseModel):
    success: bool
    message: str


class MyFollowingRequest(BaseModel):
    pass


class FollowItem(BaseModel):
    username: str
    stack: list[str]


class MyFollowingResponse(BaseModel):
    following: list[FollowItem]
    followers_count: int
    following_count: int


async def handle_follow(conn, user_id: str, req: FollowRequest) -> FollowResponse:
    """Follow another user."""
    target = await conn.fetchrow("SELECT user_id FROM profiles WHERE username = $1", req.username)
    if not target:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if target["user_id"] == user_id:
        raise HTTPException(status_code=400, detail="No puedes seguirte a ti mismo")

    existing = await conn.fetchrow(
        "SELECT id FROM follows WHERE follower_id = $1 AND following_id = $2",
        user_id, target["user_id"]
    )
    if existing:
        return FollowResponse(success=True, message=f"Ya sigues a {req.username}")

    await conn.execute(
        "INSERT INTO follows (follower_id, following_id) VALUES ($1, $2)",
        user_id, target["user_id"]
    )
    # Notification
    my_profile = await conn.fetchrow("SELECT username FROM profiles WHERE user_id = $1", user_id)
    await conn.execute(
        "INSERT INTO notifications (user_id, type, from_user, message) VALUES ($1, 'follow', $2, $3)",
        target["user_id"], user_id, f"{my_profile['username']} te ha seguido"
    )
    return FollowResponse(success=True, message=f"Ahora sigues a {req.username}")


async def handle_unfollow(conn, user_id: str, req: UnfollowRequest) -> UnfollowResponse:
    """Unfollow a user."""
    target = await conn.fetchrow("SELECT user_id FROM profiles WHERE username = $1", req.username)
    if not target:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    result = await conn.execute(
        "DELETE FROM follows WHERE follower_id = $1 AND following_id = $2",
        user_id, target["user_id"]
    )
    if result == "DELETE 0":
        return UnfollowResponse(success=False, message=f"No seguias a {req.username}")
    return UnfollowResponse(success=True, message=f"Dejaste de seguir a {req.username}")


async def handle_my_following(conn, user_id: str, req: MyFollowingRequest) -> MyFollowingResponse:
    """Get your follow stats and list."""
    followers_count = await conn.fetchval(
        "SELECT COUNT(*) FROM follows WHERE following_id = $1", user_id
    )
    following_count = await conn.fetchval(
        "SELECT COUNT(*) FROM follows WHERE follower_id = $1", user_id
    )
    rows = await conn.fetch("""
        SELECT p.username, p.stack FROM follows f
        JOIN profiles p ON p.user_id = f.following_id
        WHERE f.follower_id = $1 ORDER BY f.created_at DESC LIMIT 50
    """, user_id)
    following = [FollowItem(username=r["username"], stack=r["stack"]) for r in rows]
    return MyFollowingResponse(following=following, followers_count=followers_count, following_count=following_count)
