# Deploy — MCP Dev Network

## Variables de entorno requeridas

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | Connection string PostgreSQL |
| `ENCRYPTION_KEY` | 32 bytes base64 para AES-256-GCM |
| `OAUTH_ISSUER` | Issuer URL del proveedor OAuth |
| `OAUTH_PUBLIC_KEY` | PEM del public key RS256 (o usar OAUTH_JWKS_URL) |

## Generar ENCRYPTION_KEY

```bash
python -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

## Opción A: Railway (recomendada, más fácil)

1. Crea proyecto en [railway.app](https://railway.app)
2. Agrega servicio **PostgreSQL** (te da DATABASE_URL automáticamente)
3. Agrega servicio desde tu repo/carpeta `mcp_dev_network/`
4. En Variables del servicio Python, agrega: `ENCRYPTION_KEY`, `OAUTH_ISSUER`, `OAUTH_PUBLIC_KEY`
5. Railway detecta el Dockerfile y despliega automáticamente
6. Ejecuta `schema.sql` en la consola PG de Railway para crear las tablas

## Opción B: Render

1. Crea Web Service en [render.com](https://render.com)
2. Runtime: Docker, apuntar a este directorio
3. Crea PostgreSQL managed, copia DATABASE_URL
4. Agrega env vars
5. Deploy automático

## Opción C: Fly.io

```bash
cd mcp_dev_network
fly launch --no-deploy
fly postgres create --name mcp-dev-db
fly postgres attach mcp-dev-db
fly secrets set ENCRYPTION_KEY="..." OAUTH_ISSUER="..." OAUTH_PUBLIC_KEY="..."
fly deploy
```

Luego ejecuta el schema:
```bash
fly postgres connect -a mcp-dev-db
\i schema.sql
```

## Inicializar la base de datos

En cualquier opción, después del primer deploy necesitas ejecutar `schema.sql` contra la base de datos para crear tablas + RLS policies.

## Verificar que funciona

```bash
curl https://tu-app.up.railway.app/health
# → {"status": "ok"}
```

## Notas

- TLS lo maneja el reverse proxy de la plataforma (Railway/Render/Fly)
- El Dockerfile expone puerto 8000, pero Railway/Render asignan $PORT dinámicamente
- Rate limiting está en PG — para >100 req/s por usuario, migrar a Redis
