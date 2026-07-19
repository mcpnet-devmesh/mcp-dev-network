"""
Rate limiter basado en PostgreSQL — ventana deslizante.

ponytail: PG-based; ceiling ~100 req/s per user. Upgrade path: Redis sorted sets.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException

if TYPE_CHECKING:
    import asyncpg


async def check_rate_limit(
    conn: "asyncpg.Connection",
    user_id: str,
    operation: str,
    limit: int,
    window_seconds: int,
) -> None:
    """
    Verifica rate limit para user_id + operation.
    Raise HTTPException(429) si se excede el límite.
    Si pasa, inserta un nuevo registro en la ventana.

    Validates: Requirements 3.6, 5.6
    """
    # 1. Limpiar registros expirados
    await conn.execute(
        "DELETE FROM rate_limits WHERE user_id = $1 AND operation = $2 "
        "AND created_at < now() - make_interval(secs => $3)",
        user_id,
        operation,
        float(window_seconds),
    )

    # 2. Contar registros en la ventana actual
    count = await conn.fetchval(
        "SELECT count(*) FROM rate_limits WHERE user_id = $1 AND operation = $2 "
        "AND created_at >= now() - make_interval(secs => $3)",
        user_id,
        operation,
        float(window_seconds),
    )

    # 3. Rechazar si excede el límite
    if count >= limit:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Rate limit excedido: máximo {limit} operaciones de '{operation}' "
                f"por cada {window_seconds} segundos."
            ),
        )

    # 4. Registrar la operación actual
    await conn.execute(
        "INSERT INTO rate_limits (user_id, operation) VALUES ($1, $2)",
        user_id,
        operation,
    )
