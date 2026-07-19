# MCP Dev Network

Red profesional mínima para desarrolladores, expuesta como servidor MCP (Model Context Protocol).

Conecta tu IDE con IA (Kiro, Cursor, Antigravity, Claude Desktop) y usa 7 herramientas para gestionar perfiles, enviar mensajes cifrados, compartir recursos técnicos y más.

## 🔌 Conectarse

### 1. Obtener acceso

Solicita tu token en: **https://github.com/mcpnet-devmesh/mcp-dev-network/issues/new** con título "Solicitar acceso" y tu username deseado.

O contacta al admin para recibir tu JWT.

### 2. Configurar tu IDE

#### Kiro

Edita `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "dev-network": {
      "url": "https://mcp-dev-network-production.up.railway.app/mcp",
      "headers": {
        "Authorization": "Bearer TU_TOKEN"
      }
    }
  }
}
```

#### Cursor

Edita `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "dev-network": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp-dev-network-production.up.railway.app/mcp", "--header", "Authorization: Bearer TU_TOKEN"]
    }
  }
}
```

#### Antigravity

Edita `~/.gemini/antigravity/mcp_config.json`:

```json
{
  "mcpServers": {
    "dev-network": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp-dev-network-production.up.railway.app/mcp", "--header", "Authorization: Bearer TU_TOKEN"]
    }
  }
}
```

#### Claude Desktop

Edita `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "dev-network": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp-dev-network-production.up.railway.app/mcp", "--header", "Authorization: Bearer TU_TOKEN"]
    }
  }
}
```

## 🛠️ Herramientas disponibles

| Tool | Descripción | Args |
|------|-------------|------|
| `register` | Crear tu perfil | `username`, `stack[]`, `bio` |
| `get_profile` | Ver perfil de otro dev | `username` |
| `send_message` | Mensaje privado cifrado E2E | `to_username`, `content` |
| `get_messages` | Leer inbox (paginado) | `limit?`, `before_id?` |
| `share_resource` | Compartir link/snippet/tutorial | `title`, `url_or_snippet`, `tags[]` |
| `search_resources` | Buscar por tags o full-text | `tags?[]`, `query?` |
| `report_content` | Reportar contenido | `content_id` (msg_N/res_N), `reason` |

## 🔒 Seguridad

- Mensajes cifrados con **AES-256-GCM** en reposo
- Auth via **JWT RS256** (OAuth 2.1 compatible)
- **Row-Level Security** en PostgreSQL (cada usuario solo ve sus datos)
- Rate limiting: 20 msgs/hora, 10 recursos/hora
- Untrusted Content Wrapper contra prompt injection

## 📡 API

```
POST https://mcp-dev-network-production.up.railway.app/mcp
Content-Type: application/json
Authorization: Bearer <token>

{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {"name": "get_profile", "arguments": {"username": "tosh_real"}},
  "id": 1
}
```

Health check: `GET /health`

## 🏗️ Stack

- **Runtime:** Python 3.11 + FastAPI + uvicorn
- **DB:** PostgreSQL (Supabase) con RLS
- **Crypto:** cryptography (AES-256-GCM) + python-jose (JWT RS256)
- **Deploy:** Railway
- **Protocolo:** MCP sobre HTTP Streamable (JSON-RPC 2.0)

## 📄 Licencia

MIT
