"""
MCP Dev Network — FastAPI server (HTTP Streamable transport).

Wiring: Auth (verify_token) → set_user_context → rate limiter (inside handlers) → tool dispatch.
TLS: handled by reverse proxy (nginx/caddy). For dev, pass --ssl-keyfile/--ssl-certfile to uvicorn.

Run: uvicorn mcp_dev_network.server:app --host 0.0.0.0 --port 8000

Requirements: 8.1, 8.4, 10.1, 10.5, 10.6
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from mcp_dev_network.auth import verify_token
from mcp_dev_network.auth_self import router as auth_router
from mcp_dev_network.web import router as web_router
from mcp_dev_network.database import close_pool, get_pool, set_user_context
from mcp_dev_network.logger import log_event
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
from mcp_dev_network.tools.get_messages import InvalidBeforeIdError, handle_get_messages
from mcp_dev_network.tools.get_profile import ProfileNotFoundError, handle_get_profile
from mcp_dev_network.tools.register import RegistrationError, handle_register
from mcp_dev_network.tools.report_content import ReportContentError, handle_report_content
from mcp_dev_network.tools.search_resources import handle_search_resources
from mcp_dev_network.tools.send_message import SendMessageError, handle_send_message
from mcp_dev_network.tools.share_resource import ShareResourceError, handle_share_resource
from mcp_dev_network.tools.search_users import SearchUsersRequest, handle_search_users
from mcp_dev_network.tools.create_post import CreatePostRequest, handle_create_post
from mcp_dev_network.tools.get_feed import GetFeedRequest, handle_get_feed
from mcp_dev_network.tools.list_users import ListUsersRequest, handle_list_users
from mcp_dev_network.tools.get_my_profile import GetMyProfileRequest, handle_get_my_profile
from mcp_dev_network.tools.delete_post import DeletePostRequest, handle_delete_post

# ---------------------------------------------------------------------------
# Tool registry: maps tool name → (request model, handler, needs_user_id)
# ---------------------------------------------------------------------------
_TOOLS: dict[str, dict[str, Any]] = {
    "register": {
        "model": RegisterRequest,
        "handler": handle_register,
        "needs_user_id": True,
    },
    "get_profile": {
        "model": GetProfileRequest,
        "handler": handle_get_profile,
        "needs_user_id": False,  # public lookup, but auth still required for RLS
    },
    "send_message": {
        "model": SendMessageRequest,
        "handler": handle_send_message,
        "needs_user_id": True,
    },
    "get_messages": {
        "model": GetMessagesRequest,
        "handler": handle_get_messages,
        "needs_user_id": True,
    },
    "share_resource": {
        "model": ShareResourceRequest,
        "handler": handle_share_resource,
        "needs_user_id": True,
    },
    "search_resources": {
        "model": SearchResourcesRequest,
        "handler": handle_search_resources,
        "needs_user_id": False,  # public search, auth required for RLS
    },
    "report_content": {
        "model": ReportContentRequest,
        "handler": handle_report_content,
        "needs_user_id": True,
    },
    "search_users": {
        "model": SearchUsersRequest,
        "handler": handle_search_users,
        "needs_user_id": False,
    },
    "create_post": {
        "model": CreatePostRequest,
        "handler": handle_create_post,
        "needs_user_id": True,
    },
    "get_feed": {
        "model": GetFeedRequest,
        "handler": handle_get_feed,
        "needs_user_id": False,
    },
    "list_users": {
        "model": ListUsersRequest,
        "handler": handle_list_users,
        "needs_user_id": False,
    },
    "get_my_profile": {
        "model": GetMyProfileRequest,
        "handler": handle_get_my_profile,
        "needs_user_id": True,
    },
    "delete_post": {
        "model": DeletePostRequest,
        "handler": handle_delete_post,
        "needs_user_id": True,
    },
}


# ---------------------------------------------------------------------------
# Lifespan — startup checks + pool management
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: verify crypto loaded, create PG pool. Shutdown: close pool."""
    # 1. Verify AES key loaded (crypto module crashes on import if missing — Req 10.6)
    #    If we got here, the import succeeded. Explicit sanity check:
    try:
        from mcp_dev_network.crypto import _aesgcm  # noqa: F401
    except Exception as exc:
        raise RuntimeError(f"Crypto module failed to load: {exc}") from exc

    # 2. Verify PG connectivity
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.fetchval("SELECT 1")

    yield

    # Shutdown
    await close_pool()


app = FastAPI(
    title="MCP Dev Network",
    version="0.1.0",
    lifespan=lifespan,
    # ponytail: no docs in production; keep for dev convenience
)

# Self-service auth endpoints
app.include_router(auth_router)
# Web pages (landing + admin)
app.include_router(web_router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    """Liveness probe — verifies PG connection."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception:
        return JSONResponse({"status": "unhealthy"}, status_code=503)
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# MCP protocol endpoint (JSON-RPC 2.0 over HTTP Streamable)
# ---------------------------------------------------------------------------
@app.post("/mcp")
async def mcp_endpoint(request: Request, user_id: str = Depends(verify_token)):
    """
    Single MCP endpoint — receives JSON-RPC 2.0 tool invocations.

    Expected body:
    {
      "jsonrpc": "2.0",
      "method": "tools/call",
      "params": {"name": "register", "arguments": {...}},
      "id": 1
    }
    """
    try:
        body = await request.json()
    except Exception:
        return _jsonrpc_error(None, -32700, "Parse error")

    req_id = body.get("id")
    method = body.get("method")

    # Only support tools/call
    if method != "tools/call":
        return _jsonrpc_error(req_id, -32601, f"Method not supported: {method}")

    params = body.get("params") or {}
    tool_name = params.get("name")
    arguments = params.get("arguments") or {}

    if tool_name not in _TOOLS:
        return _jsonrpc_error(req_id, -32602, f"Unknown tool: {tool_name}")

    tool = _TOOLS[tool_name]

    # 1. Validate arguments with Pydantic model
    try:
        req_model = tool["model"](**arguments)
    except ValidationError as exc:
        # Extract first error for a clean message
        first = exc.errors()[0]
        field = ".".join(str(loc) for loc in first["loc"]) if first.get("loc") else None
        return _jsonrpc_error(
            req_id,
            -32000,
            first["msg"],
            data={"code": "VALIDATION_ERROR", "field": field},
        )

    # 2. Acquire connection, set user context, dispatch
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Set RLS context (Req 8.4)
            await set_user_context(conn, user_id)

            try:
                handler = tool["handler"]
                if tool["needs_user_id"]:
                    result = await handler(conn, user_id, req_model)
                else:
                    result = await handler(conn, req_model)
            except (RegistrationError, SendMessageError, ShareResourceError, ReportContentError) as exc:
                mcp_err: MCPError = exc.mcp_error
                log_event(user_id, tool_name, error_type=mcp_err.code)
                return _jsonrpc_error(
                    req_id,
                    -32000,
                    mcp_err.message,
                    data={"code": mcp_err.code, "field": mcp_err.field},
                )
            except ProfileNotFoundError:
                log_event(user_id, tool_name, error_type="NOT_FOUND")
                return _jsonrpc_error(
                    req_id,
                    -32000,
                    "Perfil no encontrado",
                    data={"code": "NOT_FOUND"},
                )
            except InvalidBeforeIdError:
                log_event(user_id, tool_name, error_type="VALIDATION_ERROR")
                return _jsonrpc_error(
                    req_id,
                    -32000,
                    "before_id inválido",
                    data={"code": "VALIDATION_ERROR", "field": "before_id"},
                )
            except HTTPException as exc:
                # Rate limiter raises 429 via HTTPException
                log_event(user_id, tool_name, error_type="RATE_LIMITED")
                return _jsonrpc_error(
                    req_id,
                    -32000,
                    exc.detail,
                    data={"code": "RATE_LIMITED"},
                )
            except ValueError as exc:
                # set_user_context raises ValueError on invalid user_id
                log_event(user_id, tool_name, error_type="AUTH_ERROR")
                return _jsonrpc_error(
                    req_id,
                    -32000,
                    "Authentication required",
                    data={"code": "AUTH_REQUIRED"},
                )
            except Exception as exc:
                log_event(user_id, tool_name, error_type="INTERNAL_ERROR")
                return _jsonrpc_error(req_id, -32603, "Internal error")

    # 3. Success — serialize result to MCP response
    log_event(user_id, tool_name)
    content_text = result.model_dump_json()
    return JSONResponse({
        "jsonrpc": "2.0",
        "result": {
            "content": [{"type": "text", "text": content_text}],
        },
        "id": req_id,
    })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _jsonrpc_error(
    req_id: Any,
    code: int,
    message: str,
    data: dict | None = None,
) -> JSONResponse:
    """Build a JSON-RPC 2.0 error response."""
    error: dict[str, Any] = {"code": code, "message": message}
    if data:
        error["data"] = data
    return JSONResponse({"jsonrpc": "2.0", "error": error, "id": req_id})
