FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi "uvicorn[standard]" asyncpg pydantic cryptography "python-jose[cryptography]"

# Create package structure: /app/mcp_dev_network/
RUN mkdir -p /app/mcp_dev_network/tools /app/mcp_dev_network/tests

# Copy source files
COPY __init__.py /app/mcp_dev_network/
COPY auth.py /app/mcp_dev_network/
COPY crypto.py /app/mcp_dev_network/
COPY database.py /app/mcp_dev_network/
COPY logger.py /app/mcp_dev_network/
COPY models.py /app/mcp_dev_network/
COPY rate_limit.py /app/mcp_dev_network/
COPY server.py /app/mcp_dev_network/
COPY wrapper.py /app/mcp_dev_network/
COPY tools/ /app/mcp_dev_network/tools/

EXPOSE 8000

CMD ["python", "-c", "import os; import uvicorn; uvicorn.run('mcp_dev_network.server:app', host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))"]
