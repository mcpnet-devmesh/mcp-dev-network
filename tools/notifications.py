"""notifications tool — check your notifications."""
from pydantic import BaseModel


class GetNotificationsRequest(BaseModel):
    unread_only: bool = True
    limit: int = 20


class NotificationItem(BaseModel):
    id: int
    type: str
    message: str
    read: bool
    created_at: str


class GetNotificationsResponse(BaseModel):
    notifications: list[NotificationItem]
    unread_count: int


class MarkReadRequest(BaseModel):
    notification_id: int | None = None  # None = mark all as read


class MarkReadResponse(BaseModel):
    marked: int


async def handle_get_notifications(conn, user_id: str, req: GetNotificationsRequest) -> GetNotificationsResponse:
    """Get your notifications."""
    unread_count = await conn.fetchval(
        "SELECT COUNT(*) FROM notifications WHERE user_id = $1 AND read = false", user_id
    )
    if req.unread_only:
        rows = await conn.fetch(
            "SELECT id, type, message, read, created_at FROM notifications WHERE user_id = $1 AND read = false ORDER BY created_at DESC LIMIT $2",
            user_id, req.limit
        )
    else:
        rows = await conn.fetch(
            "SELECT id, type, message, read, created_at FROM notifications WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
            user_id, req.limit
        )
    notifications = [
        NotificationItem(id=r["id"], type=r["type"], message=r["message"], read=r["read"], created_at=r["created_at"].isoformat() + "Z")
        for r in rows
    ]
    return GetNotificationsResponse(notifications=notifications, unread_count=unread_count)


async def handle_mark_read(conn, user_id: str, req: MarkReadRequest) -> MarkReadResponse:
    """Mark notifications as read."""
    if req.notification_id:
        result = await conn.execute(
            "UPDATE notifications SET read = true WHERE id = $1 AND user_id = $2 AND read = false",
            req.notification_id, user_id
        )
        marked = int(result.split()[-1]) if "UPDATE" in result else 0
    else:
        result = await conn.execute(
            "UPDATE notifications SET read = true WHERE user_id = $1 AND read = false", user_id
        )
        marked = int(result.split()[-1]) if "UPDATE" in result else 0
    return MarkReadResponse(marked=marked)
