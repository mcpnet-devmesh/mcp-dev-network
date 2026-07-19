"""Startup script — reads PORT from env, launches uvicorn."""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("mcp_dev_network.server:app", host="0.0.0.0", port=port)
