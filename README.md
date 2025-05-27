# Model Context Protocol (MCP) Server

A modular Model Context Protocol server for AI services with multiple transport options and dynamic service selection. Built with SOLID principles for maintainability and extensibility.

## Features

- **Multiple AI Services**: Support for Claude, OpenAI, and mock services
- **Dynamic Service Selection**: Choose AI service on a per-request basis
- **Multiple Transports**:
  - **stdio**: For command-line usage and scripting
  - **TCP**: For network-based applications
  - **WebSocket**: For web browsers and real-time applications
- **JSON-RPC 2.0**: Compliant interface for predictable interactions
- **Modular Architecture**: Easy to extend with new services and transports
- **Environment Configuration**: Simple setup via `.env` file
- **Streaming Support**: Real-time response streaming for supported transports

## Repository Structure

```
basic-mcp-server/
├── .env                      # Environment configuration
├── .gitignore                # Git ignore rules
├── README.md                 # Project documentation
├── example_client.py         # Command-line client example
├── examples/                 # Example clients
│   └── websocket_client.html # Browser WebSocket client
├── mcp_server.py             # Main entry point
└── mcp_server/               # Core package
    ├── config/               # Configuration management
    │   ├── settings.py       # Environment and settings handling
    │   └── __init__.py
    ├── core/                 # Core server logic
    │   ├── server.py         # Main server implementation
    │   └── __init__.py
    ├── handlers/             # Method handlers
    │   ├── base_handlers.py  # Standard MCP handlers
    │   ├── system_handlers.py # System info handlers
    │   └── __init__.py
    ├── models/               # Data models
    │   ├── json_rpc.py       # JSON-RPC data structures
    │   └── __init__.py
    ├── services/             # AI service implementations
    │   ├── claude_service.py # Anthropic Claude API
    │   ├── openai_service.py # OpenAI API
    │   └── __init__.py       # Service registry
    ├── transports/           # Communication protocols
    │   ├── base.py           # Transport interfaces
    │   ├── websocket.py      # WebSocket implementation
    │   └── __init__.py
    └── __init__.py
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/shaswata56/basic-mcp-server.git
   cd basic-mcp-server
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install aiohttp python-dotenv websockets psutil
   ```

3. Configure your environment by editing the `.env` file with your API keys and settings.

## Configuration

### Environment Variables

The server can be configured using environment variables in the `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `AI_SERVICE_TYPE` | Default AI service to use ("claude", "openai", "mock") | "claude" |
| `ANTHROPIC_API_KEY` | Your Anthropic API key | None |
| `OPENAI_API_KEY` | Your OpenAI API key | None |
| `MCP_SERVER_NAME` | Name of the server | "ai-mcp-server" |
| `MCP_SERVER_VERSION` | Server version | "1.0.0" |
| `MCP_TRANSPORT_TYPE` | Transport type ("stdio", "tcp", or "websocket") | "stdio" |
| `MCP_TCP_HOST` | TCP/WebSocket host address | "127.0.0.1" |
| `MCP_TCP_PORT` | TCP server port | 9000 |
| `MCP_WS_PORT` | WebSocket server port | 8765 |
| `MCP_WS_PATH` | WebSocket server path | "/" |
| `MCP_WS_ORIGINS` | Comma-separated list of allowed origins | None (all allowed) |
| `CLAUDE_DEFAULT_MODEL` | Default Claude model | "claude-3-opus-20240229" |
| `CLAUDE_DEFAULT_MAX_TOKENS` | Default max tokens for Claude | 4096 |
| `CLAUDE_DEFAULT_TEMPERATURE` | Default temperature for Claude | 0.7 |
| `OPENAI_DEFAULT_MODEL` | Default OpenAI model | "gpt-4o" |
| `OPENAI_DEFAULT_MAX_TOKENS` | Default max tokens for OpenAI | 1024 |
| `OPENAI_DEFAULT_TEMPERATURE` | Default temperature for OpenAI | 0.7 |

## Usage

### Running the Server

#### Standard stdio Mode
```bash
python mcp_server.py
```

#### TCP Server Mode
```bash
python mcp_server.py --tcp --host 127.0.0.1 --port 9000
```

#### WebSocket Server Mode
```bash
python mcp_server.py --websocket --host 127.0.0.1 --port 8765 --ws-path /
```

### Command Line Options

```
usage: mcp_server.py [-h] [--tcp | --websocket] [--host HOST] [--port PORT]
                     [--ws-path WS_PATH] [--service-type {claude,openai,mock}]
                     [--claude-api-key CLAUDE_API_KEY]
                     [--openai-api-key OPENAI_API_KEY] [--mock]
                     [--log-level {DEBUG,INFO,WARNING,ERROR}]
                     [--env-file ENV_FILE]

AI MCP Server with JSON-RPC

options:
  -h, --help            show this help message and exit
  --log-level {DEBUG,INFO,WARNING,ERROR}
                        Logging level
  --env-file ENV_FILE   Path to .env file (default: .env in project root)

Transport Options:
  --tcp                 Run as TCP server
  --websocket           Run as WebSocket server
  --host HOST           Host to bind server
  --port PORT           Port for server
  --ws-path WS_PATH     URL path for WebSocket server (default: /)

AI Service Options:
  --service-type {claude,openai,mock}
                        AI service to use
  --claude-api-key CLAUDE_API_KEY
                        Anthropic API key
  --openai-api-key OPENAI_API_KEY
                        OpenAI API key
  --mock                Use mock AI service (for testing)
```

## Client Examples

### Command Line Client

The `example_client.py` provides a simple way to interact with the server:

```bash
# Initialize connection
python example_client.py initialize

# List available tools
python example_client.py list-tools

# Echo text
python example_client.py echo "Hello, world!"

# Calculate expression
python example_client.py calculate "2 + 3 * 4"

# Ask AI with dynamic service selection
python example_client.py ask "What is the capital of France?" --service claude

# System information
python example_client.py system-info
```

### WebSocket Browser Client

For WebSocket transport, open `examples/websocket_client.html` in a browser:

1. Enter the WebSocket URL (e.g., `ws://localhost:8765/`)
2. Click "Connect"
3. Use the interface to send requests to the server

## JSON-RPC Interface

### Unified AI Message Request

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "ai/message",
    "arguments": {
      "prompt": "What is the capital of France?",
      "service_name": "claude"  // Optional: "claude", "openai", "mock" or omit for default
    }
  },
  "id": 1
}
```

### Service-Specific Requests (for backward compatibility)

Claude:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "claude/message",
    "arguments": {
      "prompt": "What is the capital of France?"
    }
  },
  "id": 2
}
```

OpenAI:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "openai/message",
    "arguments": {
      "prompt": "What is the capital of France?"
    }
  },
  "id": 3
}
```

### Available Methods

| Method | Description |
|--------|-------------|
| `initialize` | Initialize the server connection |
| `tools/list` | List available tools |
| `tools/call` | Call a tool with arguments |
| `resources/list` | List available resources |
| `resources/read` | Read a resource |
| `system/info` | Get system information |
| `system/health` | Check system health |

## Extending the Server

### Adding a New Method Handler

1. Create a new handler class implementing the `HandlerInterface` in the handlers directory
2. Register it in the `AIMCPServerApp.initialize()` method

### Adding a New AI Service

1. Create a new service class implementing the `AIServiceInterface` in the services directory
2. Add it to the service registry in `create_ai_services_from_config()`

### Adding a New Transport

1. Create a new transport class extending the `Transport` class in the transports directory
2. Update the main function to use your new transport

## WebSocket and Load Balancers

When using a TLS/SSL-terminating load balancer (like AWS ELB) in front of this server:

- Clients connect to the load balancer using secure WebSockets (`wss://`)
- The load balancer handles TLS/SSL termination
- The load balancer forwards traffic to the MCP server using regular WebSockets (`ws://`)
- No need to implement WSS in the application itself

## License

[MIT License](LICENSE)

## Acknowledgements

- [Claude API by Anthropic](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)
- [OpenAI API](https://platform.openai.com/docs/api-reference)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [WebSockets Protocol](https://datatracker.ietf.org/doc/html/rfc6455)