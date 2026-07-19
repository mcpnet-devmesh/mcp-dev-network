"""
Tests para rate_limit.py — verifica lógica de ventana deslizante.
Validates: Requirements 3.6, 5.6
"""

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from rate_limit import check_rate_limit


def _run(coro):
    return asyncio.run(coro)


def _make_conn(count_return=0):
    conn = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetchval = AsyncMock(return_value=count_return)
    return conn


def test_allows_when_under_limit():
    """Operación pasa si count < limit."""
    conn = _make_conn(count_return=5)
    _run(check_rate_limit(conn, "user-1", "send_message", 20, 3600))
    # DELETE + INSERT = 2 execute calls
    assert conn.execute.call_count == 2


def test_raises_429_when_at_limit():
    """Rechaza con 429 cuando count >= limit."""
    conn = _make_conn(count_return=20)
    with pytest.raises(HTTPException) as exc_info:
        _run(check_rate_limit(conn, "user-1", "send_message", 20, 3600))
    assert exc_info.value.status_code == 429
    assert "Rate limit excedido" in exc_info.value.detail


def test_raises_429_when_over_limit():
    """Rechaza con 429 cuando count > limit."""
    conn = _make_conn(count_return=25)
    with pytest.raises(HTTPException) as exc_info:
        _run(check_rate_limit(conn, "user-1", "share_resource", 10, 3600))
    assert exc_info.value.status_code == 429


def test_deletes_expired_before_counting():
    """Primero elimina expirados, luego cuenta."""
    conn = _make_conn(count_return=0)
    _run(check_rate_limit(conn, "user-x", "send_message", 20, 3600))
    first_call_sql = conn.execute.call_args_list[0][0][0]
    assert "DELETE FROM rate_limits" in first_call_sql


def test_inserts_record_on_success():
    """Cuando pasa, inserta registro de la operación."""
    conn = _make_conn(count_return=0)
    _run(check_rate_limit(conn, "user-y", "share_resource", 10, 3600))
    last_call = conn.execute.call_args_list[-1]
    assert "INSERT INTO rate_limits" in last_call[0][0]
    assert last_call[0][1] == "user-y"
    assert last_call[0][2] == "share_resource"


def test_no_insert_on_rejection():
    """Cuando rechaza, NO inserta registro nuevo."""
    conn = _make_conn(count_return=20)
    with pytest.raises(HTTPException):
        _run(check_rate_limit(conn, "user-z", "send_message", 20, 3600))
    # Solo 1 execute (el DELETE), no el INSERT
    assert conn.execute.call_count == 1


def test_detail_includes_operation_and_limit():
    """El mensaje de error incluye operación y límite."""
    conn = _make_conn(count_return=10)
    with pytest.raises(HTTPException) as exc_info:
        _run(check_rate_limit(conn, "user-a", "share_resource", 10, 3600))
    assert "share_resource" in exc_info.value.detail
    assert "10" in exc_info.value.detail


if __name__ == "__main__":
    test_allows_when_under_limit()
    test_raises_429_when_at_limit()
    test_raises_429_when_over_limit()
    test_deletes_expired_before_counting()
    test_inserts_record_on_success()
    test_no_insert_on_rejection()
    test_detail_includes_operation_and_limit()
    print("All rate_limit tests passed.")
