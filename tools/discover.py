"""discover tool — who to follow + trending tags."""
from pydantic import BaseModel


class DiscoverRequest(BaseModel):
    pass


class SuggestedUser(BaseModel):
    username: str
    stack: list[str]
    followers: int
    reason: str


class TrendingTag(BaseModel):
    tag: str
    count: int


class DiscoverResponse(BaseModel):
    suggested_users: list[SuggestedUser]
    trending_tags: list[TrendingTag]
    network_stats: dict


async def handle_discover(conn, user_id: str, req: DiscoverRequest) -> DiscoverResponse:
    """Discover who to follow and trending content."""
    # Get user's stack for smart suggestions
    my_profile = await conn.fetchrow("SELECT stack FROM profiles WHERE user_id = $1", user_id)
    my_stack = my_profile["stack"] if my_profile else []

    # Users with overlapping stack that you don't follow yet
    already_following = await conn.fetch(
        "SELECT following_id FROM follows WHERE follower_id = $1", user_id
    )
    following_ids = [r["following_id"] for r in already_following] + [user_id]

    if my_stack:
        suggested_rows = await conn.fetch("""
            SELECT p.username, p.stack, p.user_id,
                   (SELECT COUNT(*) FROM follows WHERE following_id = p.user_id) as followers
            FROM profiles p
            WHERE p.user_id != ALL($1::text[]) AND p.stack && $2::text[]
            ORDER BY followers DESC LIMIT 5
        """, following_ids, my_stack)
    else:
        suggested_rows = await conn.fetch("""
            SELECT p.username, p.stack, p.user_id,
                   (SELECT COUNT(*) FROM follows WHERE following_id = p.user_id) as followers
            FROM profiles p
            WHERE p.user_id != ALL($1::text[])
            ORDER BY followers DESC LIMIT 5
        """, following_ids)

    suggested = [
        SuggestedUser(
            username=r["username"], stack=r["stack"], followers=r["followers"],
            reason="Stack similar" if my_stack and set(r["stack"]) & set(my_stack) else "Popular"
        )
        for r in suggested_rows
    ]

    # Trending tags (most used in last 7 days)
    tag_rows = await conn.fetch("""
        SELECT unnest(tags) as tag, COUNT(*) as cnt
        FROM posts WHERE created_at > now() - interval '7 days'
        GROUP BY tag ORDER BY cnt DESC LIMIT 10
    """)
    trending = [TrendingTag(tag=r["tag"], count=r["cnt"]) for r in tag_rows]

    # Network stats
    total_users = await conn.fetchval("SELECT COUNT(*) FROM profiles")
    total_posts = await conn.fetchval("SELECT COUNT(*) FROM posts")
    total_messages = await conn.fetchval("SELECT COUNT(*) FROM messages")

    return DiscoverResponse(
        suggested_users=suggested,
        trending_tags=trending,
        network_stats={"users": total_users, "posts": total_posts, "messages": total_messages},
    )
