# Architecture Overview

The MCP server exposes a JSON-RPC 2.0 interface and supports multiple transports including **stdio**, **TCP**, and **WebSocket**. The main entry point is [`mcp_server.py`](../../mcp_server.py) which initializes services, registers method handlers, and configures tools for interacting with various AI models.

Core components include:

- **Config**: `mcp_server/config/settings.py` loads environment variables and provides defaults for API keys and model choices.
- **Core Server**: `mcp_server/core/server.py` implements the request/response loop and transport management.
- **Handlers**: Located under `mcp_server/handlers/`, these map JSON-RPC methods to Python functions.
- **Services**: Under `mcp_server/services/`, providing integrations such as OpenAI and Claude APIs, MongoDB, and vector storage.
- **Transports**: Implemented in `mcp_server/transports/` for stdio, TCP, and WebSocket communication.
