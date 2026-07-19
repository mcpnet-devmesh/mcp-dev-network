"""Tests unitarios para models.py — verifican validadores custom."""

import pytest
from pydantic import ValidationError

from mcp_dev_network.models import (
    GetMessagesRequest,
    GetProfileRequest,
    MCPError,
    RegisterRequest,
    ReportContentRequest,
    SearchResourcesRequest,
    SendMessageRequest,
    ShareResourceRequest,
)


class TestRegisterRequest:
    def test_valid(self):
        r = RegisterRequest(username="dev_user", stack=["Python", "FastAPI"], bio="Hello")
        assert r.username == "dev_user"
        assert r.stack == ["Python", "FastAPI"]
        assert r.bio == "Hello"

    def test_bio_defaults_empty(self):
        r = RegisterRequest(username="dev", stack=["go"])
        assert r.bio == ""

    def test_rejects_duplicate_tags_case_insensitive(self):
        with pytest.raises(ValidationError, match="[Dd]uplicado"):
            RegisterRequest(username="dev", stack=["Python", "python"])

    def test_rejects_invalid_tag_format(self):
        with pytest.raises(ValidationError, match="[Ii]nválido"):
            RegisterRequest(username="dev", stack=["invalid tag!"])

    def test_rejects_empty_stack(self):
        with pytest.raises(ValidationError):
            RegisterRequest(username="dev", stack=[])

    def test_rejects_invalid_username(self):
        with pytest.raises(ValidationError):
            RegisterRequest(username="ab", stack=["python"])  # too short

    def test_rejects_username_special_chars(self):
        with pytest.raises(ValidationError):
            RegisterRequest(username="dev@user", stack=["python"])


class TestSendMessageRequest:
    def test_valid(self):
        m = SendMessageRequest(to_username="other", content="Hola mundo")
        assert m.content == "Hola mundo"

    def test_rejects_whitespace_only(self):
        with pytest.raises(ValidationError, match="blanco"):
            SendMessageRequest(to_username="other", content="   \t\n  ")

    def test_rejects_empty(self):
        with pytest.raises(ValidationError):
            SendMessageRequest(to_username="other", content="")


class TestShareResourceRequest:
    def test_normalizes_tags_lowercase(self):
        sr = ShareResourceRequest(
            title="My Resource", url_or_snippet="http://x.com", tags=["Python", "FASTAPI"]
        )
        assert sr.tags == ["python", "fastapi"]

    def test_dedups_tags(self):
        sr = ShareResourceRequest(
            title="My Resource", url_or_snippet="http://x.com", tags=["Python", "PYTHON", "Go"]
        )
        assert sr.tags == ["python", "go"]

    def test_rejects_invalid_tag(self):
        with pytest.raises(ValidationError, match="[Ii]nválido"):
            ShareResourceRequest(
                title="Res", url_or_snippet="http://x.com", tags=["bad tag!"]
            )

    def test_rejects_empty_tags(self):
        with pytest.raises(ValidationError):
            ShareResourceRequest(title="Res", url_or_snippet="http://x.com", tags=[])


class TestSearchResourcesRequest:
    def test_valid_with_tags(self):
        s = SearchResourcesRequest(tags=["python"])
        assert s.tags == ["python"]

    def test_valid_with_query(self):
        s = SearchResourcesRequest(query="fastapi tutorial")
        assert s.query == "fastapi tutorial"

    def test_valid_with_both(self):
        s = SearchResourcesRequest(tags=["python"], query="async")
        assert s.tags == ["python"]

    def test_rejects_no_criteria(self):
        with pytest.raises(ValidationError, match="criterio"):
            SearchResourcesRequest()

    def test_rejects_empty_tags_no_query(self):
        with pytest.raises(ValidationError, match="criterio"):
            SearchResourcesRequest(tags=[], query="")

    def test_rejects_whitespace_only_query_no_tags(self):
        with pytest.raises(ValidationError, match="criterio"):
            SearchResourcesRequest(tags=None, query="   ")

    def test_rejects_tag_over_50_chars(self):
        with pytest.raises(ValidationError, match="50"):
            SearchResourcesRequest(tags=["a" * 51])


class TestGetMessagesRequest:
    def test_defaults(self):
        gm = GetMessagesRequest()
        assert gm.limit == 20
        assert gm.before_id is None

    def test_rejects_limit_over_100(self):
        with pytest.raises(ValidationError):
            GetMessagesRequest(limit=101)

    def test_rejects_limit_zero(self):
        with pytest.raises(ValidationError):
            GetMessagesRequest(limit=0)


class TestGetProfileRequest:
    def test_valid(self):
        p = GetProfileRequest(username="dev_123")
        assert p.username == "dev_123"

    def test_rejects_too_long(self):
        with pytest.raises(ValidationError):
            GetProfileRequest(username="a" * 40)

    def test_rejects_special_chars(self):
        with pytest.raises(ValidationError):
            GetProfileRequest(username="user@name")


class TestReportContentRequest:
    def test_valid(self):
        r = ReportContentRequest(content_id="msg_123", reason="Spam repetitivo y abusivo")
        assert r.content_id == "msg_123"

    def test_rejects_short_reason(self):
        with pytest.raises(ValidationError):
            ReportContentRequest(content_id="res_1", reason="corto")


class TestMCPError:
    def test_with_field(self):
        e = MCPError(code="VALIDATION_ERROR", message="Campo inválido", field="username")
        assert e.field == "username"

    def test_without_field(self):
        e = MCPError(code="NOT_FOUND", message="No encontrado")
        assert e.field is None
