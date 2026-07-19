"""
Database connection pool and user context helper.
Requirements: 8.4, 8.5, 9.7
"""

import os

import asyncpg

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Return (or create) the asyncpg connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=os.environ["DATABASE_URL"],
            min_size=2,
            max_size=10,
        )
    return _pool


async def close_pool() -> None:
    """Graceful shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def set_user_context(conn: asyncpg.Connection, user_id: str) -> None:
    """
    Set app.current_user_id on the PG connection for RLS enforcement.

    Raises ValueError if user_id is None, empty, or whitespace-only,
    aborting the operation before any query runs (Req 8.5, 9.7).
    """
    if not user_id or not user_id.strip():
        raise ValueError("user_id must not be empty — aborting DB operation")
    # ponytail: SET LOCAL doesn't support $1 placeholders in PG,
    # so we validate strictly above and use format. The value is from
    # the verified OAuth token (never client-supplied), plus we reject
    # anything that could break out (single quotes, semicolons).
    _validate_user_id_safe(user_id)
    await conn.execute(
        f"SET LOCAL app.current_user_id = '{user_id}'"
    )


def _validate_user_id_safe(user_id: str) -> None:
    """
    Guard against injection in the SET LOCAL statement.
    user_id comes from a verified JWT sub claim — typically a UUID or opaque ID.
    Reject anything with characters that could escape the SQL literal.
    """
    forbidden = ("'", ";", "--", "/*", "\\")
    for ch in forbidden:
        if ch in user_id:
            raise ValueError(f"user_id contains forbidden character sequence: {ch!r}")
