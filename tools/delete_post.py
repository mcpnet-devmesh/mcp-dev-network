"""delete_post tool — delete your own post."""

from pydantic import BaseModel
from fastapi import HTTPException


class DeletePostRequest(BaseModel):
    post_id: int


class DeletePostResponse(BaseModel):
    deleted: bool
    message: str


async def handle_delete_post(conn, user_id: str, req: DeletePostRequest) -> DeletePostResponse:
    """Delete a post you authored. RLS enforces ownership."""
    result = await conn.execute(
        "DELETE FROM posts WHERE id = $1 AND author_id = $2", req.post_id, user_id
    )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Post no encontrado o no eres el autor")
    return DeletePostResponse(deleted=True, message="Post eliminado")
