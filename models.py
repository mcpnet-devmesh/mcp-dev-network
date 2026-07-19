"""Modelos Pydantic de request/response para MCP Dev Network."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


# --- Error Model ---

class MCPError(BaseModel):
    code: str  # VALIDATION_ERROR, AUTH_REQUIRED, RATE_LIMITED, NOT_FOUND, DUPLICATE
    message: str
    field: str | None = None


# --- Request Models ---

_TAG_RE = re.compile(r"^[a-zA-Z0-9-]{1,30}$")
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,30}$")
_PROFILE_LOOKUP_RE = re.compile(r"^[a-zA-Z0-9_]{1,39}$")


class RegisterRequest(BaseModel):
    username: str = Field(pattern=r"^[a-zA-Z0-9_]{3,30}$")
    stack: list[str] = Field(min_length=1, max_length=20)
    bio: str = Field(default="", max_length=500)

    @field_validator("stack")
    @classmethod
    def validate_stack(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for tag in v:
            if not _TAG_RE.match(tag):
                raise ValueError(f"Tag inválido: {tag}")
            lower = tag.lower()
            if lower in seen:
                raise ValueError(f"Tag duplicado: {tag}")
            seen.add(lower)
            unique.append(tag)
        return unique


class GetProfileRequest(BaseModel):
    username: str = Field(pattern=r"^[a-zA-Z0-9_]{1,39}$")


class SendMessageRequest(BaseModel):
    to_username: str
    content: str = Field(min_length=1, max_length=5000)

    @field_validator("content")
    @classmethod
    def validate_content_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El contenido no puede ser solo espacios en blanco")
        return v


class GetMessagesRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    before_id: int | None = Field(default=None, ge=1)


class ShareResourceRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    url_or_snippet: str = Field(min_length=1, max_length=10000)
    tags: list[str] = Field(min_length=1, max_length=10)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        for tag in v:
            if not _TAG_RE.match(tag):
                raise ValueError(f"Tag inválido: {tag}")
        # ponytail: normalizar a lowercase + dedup preservando orden de primera aparición
        seen: set[str] = set()
        result: list[str] = []
        for tag in v:
            lower = tag.lower()
            if lower not in seen:
                seen.add(lower)
                result.append(lower)
        return result


class SearchResourcesRequest(BaseModel):
    tags: list[str] | None = Field(default=None, max_length=10)
    query: str | None = Field(default=None, max_length=200)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        if v:
            for tag in v:
                if len(tag) > 50:
                    raise ValueError("Cada tag máximo 50 caracteres")
        return v

    @model_validator(mode="after")
    def at_least_one_criterion(self) -> SearchResourcesRequest:
        has_tags = self.tags and len(self.tags) > 0
        has_query = self.query and self.query.strip()
        if not has_tags and not has_query:
            raise ValueError("Se requiere al menos un criterio de búsqueda (tags o query)")
        return self


class ReportContentRequest(BaseModel):
    content_id: str  # formato: "msg_123" o "res_456"
    reason: str = Field(min_length=10, max_length=1000)


# --- Helper Models ---

class MessageItem(BaseModel):
    id: int
    from_username: str
    content: str  # descifrado + wrapper aplicado
    created_at: datetime


class ResourceItem(BaseModel):
    id: int
    author_username: str
    title: str  # con wrapper
    url_or_snippet: str  # con wrapper
    tags: list[str]
    created_at: datetime


# --- Response Models ---

class RegisterResponse(BaseModel):
    username: str
    message: str = "Perfil registrado exitosamente"


class ProfileResponse(BaseModel):
    username: str
    stack: list[str]
    bio: str


class SendMessageResponse(BaseModel):
    message_id: int
    created_at: datetime


class GetMessagesResponse(BaseModel):
    messages: list[MessageItem]


class ShareResourceResponse(BaseModel):
    resource_id: int
    created_at: datetime


class SearchResourcesResponse(BaseModel):
    resources: list[ResourceItem]


class ReportContentResponse(BaseModel):
    report_id: int
    status: str = "registrado para revisión humana"
