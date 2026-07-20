"""like/unlike post tools."""
from pydantic import BaseModel
from fastapi import HTTPException


class LikePostRequest(BaseModel):
    post_id: int


class LikePostResponse(BaseModel):
    liked: bool
    total_likes: int


async def handle_like_post(conn, user_id: str, req: LikePostRequest) -> LikePostResponse:
    """Like a post. Toggle: if already liked, unlike it."""
    # Check post exists
    post = await conn.fetchrow("SELECT id, author_id FROM posts WHERE id = $1", req.post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado")

    existing = await conn.fetchrow(
        "SELECT id FROM post_likes WHERE user_id = $1 AND post_id = $2", user_id, req.post_id
    )
    if existing:
        await conn.execute("DELETE FROM post_likes WHERE user_id = $1 AND post_id = $2", user_id, req.post_id)
        liked = False
    else:
        await conn.execute(
            "INSERT INTO post_likes (user_id, post_id) VALUES ($1, $2)", user_id, req.post_id
        )
        liked = True
        # Notification to post author (only on like, not unlike)
        if post["author_id"] != user_id:
            my_profile = await conn.fetchrow("SELECT username FROM profiles WHERE user_id = $1", user_id)
            await conn.execute(
                "INSERT INTO notifications (user_id, type, from_user, ref_id, message) VALUES ($1, 'like', $2, $3, $4)",
                post["author_id"], user_id, req.post_id,
                f"{my_profile['username']} le dio like a tu post"
            )

    total = await conn.fetchval("SELECT COUNT(*) FROM post_likes WHERE post_id = $1", req.post_id)
    return LikePostResponse(liked=liked, total_likes=total)
