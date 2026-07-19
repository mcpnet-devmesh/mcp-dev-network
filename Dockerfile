FROM python:3.11-slim

WORKDIR /app

# ponytail: single-stage, no build deps needed for this stack
COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

EXPOSE 8000

CMD ["uvicorn", "mcp_dev_network.server:app", "--host", "0.0.0.0", "--port", "8000"]
