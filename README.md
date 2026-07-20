# MCP Dev Network

A social network for developers, built as an MCP server. Connect your AI-powered IDE and interact with other devs — send messages, share resources, post to a public feed, and discover people by stack.

Una red social para desarrolladores, construida como servidor MCP. Conecta tu IDE con IA e interactúa con otros devs — envía mensajes, comparte recursos, publica en un feed público y descubre gente por tecnología.

---

## 🚀 Quick Start / Inicio Rápido

### 1. Sign up / Registrarse

```bash
curl -X POST https://mcp-dev-network-production.up.railway.app/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"you@email.com","password":"yourpassword"}'
```

You'll get back a token and user_id. Save the token.

Recibirás un token y user_id. Guarda el token.

### 2. Connect your IDE / Conectar tu IDE

#### Kiro

Edit `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "dev-network": {
      "url": "https://mcp-dev-network-production.up.railway.app/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

#### Cursor

Edit `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "dev-network": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp-dev-network-production.up.railway.app/mcp", "--header", "Authorization: Bearer YOUR_TOKEN"]
    }
  }
}
```

#### Antigravity (Google)

Edit `~/.gemini/antigravity/mcp_config.json`:

```json
{
  "mcpServers": {
    "dev-network": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp-dev-network-production.up.railway.app/mcp", "--header", "Authorization: Bearer YOUR_TOKEN"]
    }
  }
}
```

#### Claude Desktop

Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "dev-network": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp-dev-network-production.up.railway.app/mcp", "--header", "Authorization: Bearer YOUR_TOKEN"]
    }
  }
}
```

### 3. Register your profile / Registrar tu perfil

Once connected, ask your AI assistant:

> "Register my profile with username `yourname` and stack `[python, typescript, react]`"

Una vez conectado, pide a tu asistente IA:

> "Registra mi perfil con username `tunombre` y stack `[python, typescript, react]`"

---

## 🛠️ Available Tools / Herramientas Disponibles (10)

### Profiles / Perfiles

| Tool | Description / Descripción | Arguments |
|------|---------------------------|-----------|
| `register` | Create your profile / Crear tu perfil | `username`, `stack[]`, `bio` |
| `get_profile` | View a user's profile / Ver perfil de un usuario | `username` |
| `search_users` | Find devs by stack or name / Buscar devs por stack o nombre | `query?`, `stack?[]` |

### Messaging / Mensajería

| Tool | Description / Descripción | Arguments |
|------|---------------------------|-----------|
| `send_message` | Send encrypted private message / Enviar mensaje privado cifrado | `to_username`, `content` |
| `get_messages` | Read your inbox / Leer tu bandeja de entrada | `limit?`, `before_id?` |

### Feed

| Tool | Description / Descripción | Arguments |
|------|---------------------------|-----------|
| `create_post` | Publish to public feed / Publicar en el feed público | `content`, `tags?[]` |
| `get_feed` | Read recent posts / Leer posts recientes | `limit?`, `before_id?`, `tag?` |

### Resources / Recursos

| Tool | Description / Descripción | Arguments |
|------|---------------------------|-----------|
| `share_resource` | Share a link, snippet or tutorial / Compartir link o tutorial | `title`, `url_or_snippet`, `tags[]` |
| `search_resources` | Search by tags or full-text / Buscar por tags o texto | `tags?[]`, `query?` |

### Moderation / Moderación

| Tool | Description / Descripción | Arguments |
|------|---------------------------|-----------|
| `report_content` | Report inappropriate content / Reportar contenido | `content_id` (msg_N/res_N), `reason` |

---

## 💬 Usage Examples / Ejemplos de Uso

Once connected, just talk to your AI assistant naturally:

Una vez conectado, habla con tu asistente IA de forma natural:

| What you say / Lo que dices | Tool used |
|-----------------------------|-----------|
| "Find developers who know Rust" | `search_users` |
| "Send a message to luis saying hi" | `send_message` |
| "Check my messages" | `get_messages` |
| "Post: just deployed my first MCP server!" | `create_post` |
| "Show me the latest posts" | `get_feed` |
| "Share this tutorial about FastAPI" | `share_resource` |
| "Search resources about typescript" | `search_resources` |

---

## 🔒 Security / Seguridad

- **AES-256-GCM** encryption for all private messages / Cifrado para mensajes privados
- **JWT RS256** authentication (OAuth 2.1 compatible)
- **Row-Level Security** in PostgreSQL — each user can only access their own data / Cada usuario solo accede a sus datos
- **Rate limiting** — 20 messages/hour, 20 posts/hour, 10 resources/hour
- **Untrusted Content Wrapper** — protects against prompt injection / Protege contra inyección de prompts

---

## 📡 API Details / Detalles de la API

**Base URL:** `https://mcp-dev-network-production.up.railway.app`

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check |
| `/auth/signup` | POST | No | Create account, get token |
| `/auth/login` | POST | No | Login, get fresh token |
| `/mcp` | POST | Bearer JWT | MCP tool invocations (JSON-RPC 2.0) |

### MCP Request Format / Formato de petición MCP

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": { ... }
  },
  "id": 1
}
```

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.11 + FastAPI + uvicorn |
| Database | PostgreSQL (Supabase) with RLS |
| Encryption | AES-256-GCM (cryptography) |
| Auth | JWT RS256 (python-jose) |
| Deploy | Railway |
| Protocol | MCP over HTTP Streamable (JSON-RPC 2.0) |

---

## 🤝 Contributing / Contribuir

This is an open project. If you want to contribute:

1. Fork the repo
2. Create a feature branch
3. Submit a PR

Ideas for contributions:
- Groups / Grupos
- Reactions to posts / Reacciones a posts
- Follow system / Sistema de seguimiento
- Web frontend dashboard

---

## 📄 License / Licencia

MIT
