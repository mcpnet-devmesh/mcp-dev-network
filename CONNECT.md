# Conectar MCP Dev Network desde cualquier IDE

## Tu servidor

```
URL: https://mcp-dev-network-production.up.railway.app/mcp
Protocolo: JSON-RPC 2.0 sobre HTTP POST
Auth: Bearer Token (JWT RS256)
```

## Tu token (válido 30 días, expira 2026-08-18)

```
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0b3NoX3Byb2QiLCJpc3MiOiJodHRwczovL21jcC1kZXYtbmV0d29yay5zdXBhYmFzZS5jbyIsImV4cCI6MTc4NzA5NjI4MCwiaWF0IjoxNzg0NTA0MjgwfQ.CUQd0Dj-DnMp32CD7ALESrlz9nOlJwcpe92zkx4sgjfFhuTDkYysy2RP64yq8ONul1EQX-ogfHd9nfaAO_xwQ4AgBgIdPlWlEuRoDxO2SRirzCFR6KTeSkhGTSVMkFLjV6qty0Ysh2GClYnpodC7VBKWYN7DS8sE_4vSeGSGdbcBCqah1huaeNpH8_UP8AboooC2tVxD0mVbXPipSd12ti7pyLrbBHqOcfGPwlBqqw3Yswx17c8w6t9KMRmNYKYAhc82aU2D3dmDsy6WBEmoHd02iOkI2rSfVEu1vdR8pLyn0siiDa0cwIl3hXp0JNfghKjzIxbAeCdCj9VoXDmuAg
```

Tu usuario: **tosh_real**

## Configuración para IDEs

### Kiro / Cursor / Windsurf (mcp.json)

Como este server usa HTTP con Bearer token (no stdio), necesitas un proxy local.
La forma más simple es usar `mcp-remote` o un wrapper:

```json
{
  "mcpServers": {
    "dev-network": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp-dev-network-production.up.railway.app/mcp"],
      "env": {
        "MCP_HEADERS": "{\"Authorization\": \"Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0b3NoX3Byb2QiLCJpc3MiOiJodHRwczovL21jcC1kZXYtbmV0d29yay5zdXBhYmFzZS5jbyIsImV4cCI6MTc4NzA5NjI4MCwiaWF0IjoxNzg0NTA0MjgwfQ.CUQd0Dj-DnMp32CD7ALESrlz9nOlJwcpe92zkx4sgjfFhuTDkYysy2RP64yq8ONul1EQX-ogfHd9nfaAO_xwQ4AgBgIdPlWlEuRoDxO2SRirzCFR6KTeSkhGTSVMkFLjV6qty0Ysh2GClYnpodC7VBKWYN7DS8sE_4vSeGSGdbcBCqah1huaeNpH8_UP8AboooC2tVxD0mVbXPipSd12ti7pyLrbBHqOcfGPwlBqqw3Yswx17c8w6t9KMRmNYKYAhc82aU2D3dmDsy6WBEmoHd02iOkI2rSfVEu1vdR8pLyn0siiDa0cwIl3hXp0JNfghKjzIxbAeCdCj9VoXDmuAg\"}"
      }
    }
  }
}
```

### Kiro (remote MCP nativo — más simple)

```json
{
  "mcpServers": {
    "dev-network": {
      "url": "https://mcp-dev-network-production.up.railway.app/mcp",
      "headers": {
        "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0b3NoX3Byb2QiLCJpc3MiOiJodHRwczovL21jcC1kZXYtbmV0d29yay5zdXBhYmFzZS5jbyIsImV4cCI6MTc4NzA5NjI4MCwiaWF0IjoxNzg0NTA0MjgwfQ.CUQd0Dj-DnMp32CD7ALESrlz9nOlJwcpe92zkx4sgjfFhuTDkYysy2RP64yq8ONul1EQX-ogfHd9nfaAO_xwQ4AgBgIdPlWlEuRoDxO2SRirzCFR6KTeSkhGTSVMkFLjV6qty0Ysh2GClYnpodC7VBKWYN7DS8sE_4vSeGSGdbcBCqah1huaeNpH8_UP8AboooC2tVxD0mVbXPipSd12ti7pyLrbBHqOcfGPwlBqqw3Yswx17c8w6t9KMRmNYKYAhc82aU2D3dmDsy6WBEmoHd02iOkI2rSfVEu1vdR8pLyn0siiDa0cwIl3hXp0JNfghKjzIxbAeCdCj9VoXDmuAg"
      }
    }
  }
}
```

### Claude Desktop (claude_desktop_config.json)

```json
{
  "mcpServers": {
    "dev-network": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp-dev-network-production.up.railway.app/mcp"],
      "env": {
        "MCP_HEADERS": "{\"Authorization\": \"Bearer TU_TOKEN_AQUI\"}"
      }
    }
  }
}
```

## Herramientas disponibles (7)

| Tool | Descripción |
|------|-------------|
| `register` | Registrar perfil (username, stack, bio) |
| `get_profile` | Ver perfil de un usuario |
| `send_message` | Enviar mensaje privado cifrado |
| `get_messages` | Leer tus mensajes (paginados) |
| `share_resource` | Compartir recurso técnico |
| `search_resources` | Buscar recursos por tags o texto |
| `report_content` | Reportar contenido inapropiado |

## Ejemplo de uso manual (curl)

```bash
curl -X POST https://mcp-dev-network-production.up.railway.app/mcp \
  -H "Authorization: Bearer TU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_profile","arguments":{"username":"tosh_real"}},"id":1}'
```

## Notas

- El server usa JSON-RPC 2.0 (method: "tools/call")
- Los mensajes se cifran con AES-256-GCM en la base de datos
- Los campos de texto devueltos llevan un prefijo de seguridad (Untrusted Content Wrapper)
- Rate limits: 20 mensajes/hora, 10 recursos/hora
- Token expira en 30 días — luego necesitas regenerar
