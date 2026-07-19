"""
Tests para tools/report_content.py — verifica reporte de contenido inapropiado.
Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from mcp_dev_network.models import ReportContentRequest
from mcp_dev_network.tools.report_content import ReportContentError, handle_report_content


def _run(coro):
    return asyncio.run(coro)


def _make_conn(content_exists=True, already_reported=False, inserted_id=1):
    """
    Mock connection with sequential fetchval calls:
    1. content existence check → 1 if exists else None
    2. duplicate check → 1 if already_reported else None
    """
    conn = AsyncMock()
    conn.fetchval = AsyncMock(
        side_effect=[
            1 if content_exists else None,
            1 if already_reported else None,
        ]
    )
    conn.fetchrow = AsyncMock(return_value={"id": inserted_id})
    return conn


class TestSuccessfulReport:
    def test_report_message(self):
        """Req 7.4: reporte exitoso de un mensaje."""
        conn = _make_conn(content_exists=True, already_reported=False, inserted_id=99)
        req = ReportContentRequest(content_id="msg_123", reason="Contenido ofensivo en este mensaje")

        result = _run(handle_report_content(conn, "user-1", req))

        assert result.report_id == 99
        assert result.status == "registrado para revisión humana"
        # INSERT uses parametrized query
        insert_sql = conn.fetchrow.call_args[0][0]
        assert "INSERT INTO reports" in insert_sql
        assert "$1" in insert_sql

    def test_report_resource(self):
        """Req 7.4: reporte exitoso de un recurso."""
        conn = _make_conn(content_exists=True, already_reported=False, inserted_id=55)
        req = ReportContentRequest(content_id="res_456", reason="Enlace malicioso detectado en recurso")

        result = _run(handle_report_content(conn, "user-2", req))

        assert result.report_id == 55


class TestInvalidContentId:
    """Req 7.3: formato de content_id inválido."""

    @pytest.mark.parametrize("bad_id", [
        "invalid", "123", "msg_", "res_", "_msg_1", "message_1",
        "msg_abc", "res_-1", "", "MSG_1", "RES_1",
    ])
    def test_rejects_invalid_format(self, bad_id):
        conn = AsyncMock()
        req = ReportContentRequest(content_id=bad_id, reason="Razón válida con suficientes caracteres")

        with pytest.raises(ReportContentError) as exc_info:
            _run(handle_report_content(conn, "user-1", req))

        assert exc_info.value.mcp_error.code == "VALIDATION_ERROR"
        assert "msg_{id} o res_{id}" in exc_info.value.mcp_error.message
        # No DB queries executed
        conn.fetchval.assert_not_called()


class TestContentNotFound:
    """Req 7.2: contenido referenciado no existe."""

    def test_message_not_found(self):
        conn = _make_conn(content_exists=False)
        req = ReportContentRequest(content_id="msg_999", reason="Esto debería existir pero no existe")

        with pytest.raises(ReportContentError) as exc_info:
            _run(handle_report_content(conn, "user-1", req))

        assert exc_info.value.mcp_error.code == "NOT_FOUND"
        assert "no existe" in exc_info.value.mcp_error.message

    def test_resource_not_found(self):
        conn = _make_conn(content_exists=False)
        req = ReportContentRequest(content_id="res_888", reason="Recurso inexistente para reportar")

        with pytest.raises(ReportContentError) as exc_info:
            _run(handle_report_content(conn, "user-1", req))

        assert exc_info.value.mcp_error.code == "NOT_FOUND"


class TestDuplicateReport:
    """Req 7.5: mismo reporter + content → rechazado."""

    def test_duplicate_rejected(self):
        conn = _make_conn(content_exists=True, already_reported=True)
        req = ReportContentRequest(content_id="msg_1", reason="Ya reporté esto anteriormente")

        with pytest.raises(ReportContentError) as exc_info:
            _run(handle_report_content(conn, "user-1", req))

        assert exc_info.value.mcp_error.code == "DUPLICATE"
        assert "previamente" in exc_info.value.mcp_error.message
        # No INSERT executed
        conn.fetchrow.assert_not_called()


class TestParametrizedQueries:
    """All queries use positional params — never string concat."""

    def test_no_string_interpolation(self):
        conn = _make_conn(content_exists=True, already_reported=False, inserted_id=1)
        req = ReportContentRequest(
            content_id="msg_1", reason="'; DROP TABLE reports-- inyección SQL aquí"
        )

        _run(handle_report_content(conn, "user-1", req))

        for call in conn.fetchval.call_args_list:
            assert "$1" in call[0][0]
        assert "$1" in conn.fetchrow.call_args[0][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
