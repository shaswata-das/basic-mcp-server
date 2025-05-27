# Modular MCP Server with Claude Integration

A modular Model Context Protocol (MCP) server that communicates with Claude by Anthropic.
Built with SOLID principles for maintainability and extensibility.

## Features

- JSON-RPC 2.0 compliant interface
- Integration with multiple AI models (Claude, OpenAI)
- Dynamic service selection on a per-request basis
- Multiple transport options (stdio, TCP)
- Modular architecture for easy extension
- Streaming responses in TCP mode
- Environment variable configuration via .env file

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/basic-mcp-server.git
   cd basic-mcp-server
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install aiohttp python-dotenv
   ```

3. Configure your environment variables by copying the example .env file:
   ```bash
   cp .env.example .env
   ```

4. Edit the .env file with your Anthropic API key and desired settings.

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
| `MCP_TRANSPORT_TYPE` | Transport type ("stdio" or "tcp") | "stdio" |
| `MCP_TCP_HOST` | TCP server host address | "127.0.0.1" |
| `MCP_TCP_PORT` | TCP server port | 9000 |
| `CLAUDE_DEFAULT_MODEL` | Default Claude model | "claude-3-opus-20240229" |
| `CLAUDE_DEFAULT_MAX_TOKENS` | Default max tokens for Claude | 4096 |
| `CLAUDE_DEFAULT_TEMPERATURE` | Default temperature for Claude | 0.7 |
| `OPENAI_DEFAULT_MODEL` | Default OpenAI model | "gpt-4o" |
| `OPENAI_DEFAULT_MAX_TOKENS` | Default max tokens for OpenAI | 1024 |
| `OPENAI_DEFAULT_TEMPERATURE` | Default temperature for OpenAI | 0.7 |

## Usage

### Basic Usage

```bash
# Using stdio with configuration from .env file
python mcp_server.py

# Using TCP explicitly (overrides .env setting)
python mcp_server.py --tcp

# Using mock service for testing (no API key needed)
python mcp_server.py --mock

# With custom settings
python mcp_server.py --tcp --host 0.0.0.0 --port 8080 --api-key your_key_here

# With custom .env file
python mcp_server.py --env-file /path/to/custom/.env
```

### JSON-RPC Interface

The server accepts JSON-RPC 2.0 requests. Here are some example requests:

#### Initialize

```json
{
  "jsonrpc": "2.0",
  "method": "initialize",
  "id": 1
}
```

#### List Available Tools

```json
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "id": 2
}
```

#### Call Echo Tool

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "echo",
    "arguments": {
      "text": "Hello, world!"
    }
  },
  "id": 3
}
```

#### Call Any AI Service (Dynamic Selection)

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "ai/message",
    "arguments": {
      "prompt": "What is the capital of France?",
      "service_name": "claude"  // can be "claude", "openai", "mock", or omitted to use default
      // No need to specify model, max_tokens, or temperature - defaults from .env will be used
    }
  },
  "id": 4
}
```

#### Call with Custom Model (Overriding Defaults)

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "ai/message",
    "arguments": {
      "prompt": "What is the capital of France?",
      "service_name": "claude",
      "model": "claude-3-haiku-20240307",  // Override default model
      "temperature": 0.7  // Override default temperature
    }
  },
  "id": 5
}
```

#### Call Claude Specifically

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "claude/message",
    "arguments": {
      "prompt": "What is the capital of France?",
      "model": "claude-3-haiku-20240307",
      "temperature": 0.7
    }
  },
  "id": 5
}
```

#### Call OpenAI Specifically

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "openai/message",
    "arguments": {
      "prompt": "What is the capital of France?",
      "model": "gpt-4o",
      "temperature": 0.7
    }
  },
  "id": 6
}
```

#### Stream from Claude (TCP mode only)

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "claude/stream",
    "arguments": {
      "prompt": "Write a short poem about AI",
      "model": "claude-3-sonnet-20240229"
    }
  },
  "id": 5
}
```

## Project Structure

The project follows SOLID principles with a modular architecture:

```
mcp_server/
├── config/           # Configuration management
│   └── settings.py   # Server settings from .env/environment
├── core/             # Core server logic
│   └── server.py     # Main server implementation
├── handlers/         # Method handlers
│   └── base_handlers.py  # Handler implementations
├── models/           # Data models
│   └── json_rpc.py   # JSON-RPC models
├── services/         # External services
│   └── claude_service.py  # Claude API interface
├── transports/       # Communication protocols
│   └── base.py       # Transport interfaces
└── __init__.py
.env                  # Environment variables
mcp_server.py         # Main entry point
```

## Extending the Server

### Adding a New Method Handler

1. Create a new handler class implementing the `HandlerInterface` in the handlers directory
2. Register it in the `ClaudeMCPServerApp.initialize()` method

### Adding a New AI Service

1. Create a new service class implementing the `AIServiceInterface` in the services directory
2. Modify the main function to use your new service

### Adding a New Transport

1. Create a new transport class extending the `Transport` class in the transports directory
2. Update the main function to use your new transport

## License

[MIT License](LICENSE)

## Acknowledgements

- [Claude API by Anthropic](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)