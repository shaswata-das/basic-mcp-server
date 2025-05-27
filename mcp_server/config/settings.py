"""
Configuration settings for MCP Server

This module manages server configuration and environment variables.
Loads configuration from .env file and environment variables.
"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any

# Import dotenv for .env file support
try:
    from dotenv import load_dotenv
    # Try to load from .env file
    env_path = Path(__file__).resolve().parents[2] / '.env'
    load_dotenv(dotenv_path=env_path)
    logging.info(f"Loaded environment variables from {env_path}")
except ImportError:
    logging.warning("python-dotenv not installed. Environment variables will only be loaded from system environment.")
    pass


@dataclass
class MCPServerConfig:
    """Configuration for the MCP Server"""
    # Server info
    name: str = "ai-mcp-server"
    version: str = "1.0.0"
    description: str = "MCP Server with multiple AI model integration"
    
    # Transport settings
    transport_type: str = "stdio"  # 'stdio', 'tcp', or 'websocket'
    tcp_host: str = "127.0.0.1"
    tcp_port: int = 9000
    ws_port: int = 8765
    ws_path: str = "/"
    ws_origins: Optional[list] = None
    
    # AI service type
    ai_service_type: str = "claude"  # 'claude', 'openai', or 'mock'
    
    # API keys
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    
    # Claude API settings
    claude_default_model: str = "claude-3-opus-20240229"
    claude_default_max_tokens: int = 4096
    claude_default_temperature: float = 0.7
    
    # OpenAI API settings
    openai_default_model: str = "gpt-4o"
    openai_default_max_tokens: int = 1024
    openai_default_temperature: float = 0.7
    
    # Available models
    claude_models: list = None
    openai_models: list = None
    
    def __post_init__(self):
        # Set default models if not provided
        if self.claude_models is None:
            self.claude_models = [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307"
            ]
        
        if self.openai_models is None:
            self.openai_models = [
                "gpt-4o",
                "gpt-4-turbo",
                "gpt-4",
                "gpt-3.5-turbo"
            ]
    
    @classmethod
    def from_env(cls) -> "MCPServerConfig":
        """Create a configuration from environment variables"""
        config = cls()
        
        # Load environment variables if they exist
        if os.environ.get("MCP_SERVER_NAME"):
            config.name = os.environ.get("MCP_SERVER_NAME")
            
        if os.environ.get("MCP_SERVER_VERSION"):
            config.version = os.environ.get("MCP_SERVER_VERSION")
            
        if os.environ.get("MCP_TRANSPORT_TYPE"):
            config.transport_type = os.environ.get("MCP_TRANSPORT_TYPE")
            
        if os.environ.get("MCP_TCP_HOST"):
            config.tcp_host = os.environ.get("MCP_TCP_HOST")
            
        if os.environ.get("MCP_TCP_PORT"):
            try:
                config.tcp_port = int(os.environ.get("MCP_TCP_PORT"))
            except ValueError:
                pass
        
        # WebSocket settings
        if os.environ.get("MCP_WS_PORT"):
            try:
                config.ws_port = int(os.environ.get("MCP_WS_PORT"))
            except ValueError:
                pass
            
        if os.environ.get("MCP_WS_PATH"):
            config.ws_path = os.environ.get("MCP_WS_PATH")
            
        if os.environ.get("MCP_WS_ORIGINS"):
            try:
                origins = os.environ.get("MCP_WS_ORIGINS")
                config.ws_origins = origins.split(",")
            except Exception:
                pass
        
        # AI service type
        if os.environ.get("AI_SERVICE_TYPE"):
            config.ai_service_type = os.environ.get("AI_SERVICE_TYPE")
            
        # API keys
        config.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        config.openai_api_key = os.environ.get("OPENAI_API_KEY")
        
        # Claude settings
        if os.environ.get("CLAUDE_DEFAULT_MODEL"):
            config.claude_default_model = os.environ.get("CLAUDE_DEFAULT_MODEL")
            
        if os.environ.get("CLAUDE_DEFAULT_MAX_TOKENS"):
            try:
                config.claude_default_max_tokens = int(os.environ.get("CLAUDE_DEFAULT_MAX_TOKENS"))
            except ValueError:
                pass
            
        if os.environ.get("CLAUDE_DEFAULT_TEMPERATURE"):
            try:
                config.claude_default_temperature = float(os.environ.get("CLAUDE_DEFAULT_TEMPERATURE"))
            except ValueError:
                pass
        
        # OpenAI settings
        if os.environ.get("OPENAI_DEFAULT_MODEL"):
            config.openai_default_model = os.environ.get("OPENAI_DEFAULT_MODEL")
            
        if os.environ.get("OPENAI_DEFAULT_MAX_TOKENS"):
            try:
                config.openai_default_max_tokens = int(os.environ.get("OPENAI_DEFAULT_MAX_TOKENS"))
            except ValueError:
                pass
            
        if os.environ.get("OPENAI_DEFAULT_TEMPERATURE"):
            try:
                config.openai_default_temperature = float(os.environ.get("OPENAI_DEFAULT_TEMPERATURE"))
            except ValueError:
                pass
        
        return config
    
    @classmethod
    def from_args(cls, args: Dict[str, Any]) -> "MCPServerConfig":
        """Create a configuration from command line arguments"""
        config = cls.from_env()  # Start with environment variables
        
        # Override with command line arguments if provided
        if args.get("name"):
            config.name = args.get("name")
            
        if args.get("tcp"):
            config.transport_type = "tcp"
            
        if args.get("host"):
            config.tcp_host = args.get("host")
            
        if args.get("port"):
            config.tcp_port = args.get("port")
            
        # AI service type
        if args.get("mock"):
            config.ai_service_type = "mock"
        elif args.get("service_type"):
            config.ai_service_type = args.get("service_type")
            
        # API keys
        if args.get("claude_api_key"):
            config.anthropic_api_key = args.get("claude_api_key")
            
        if args.get("openai_api_key"):
            config.openai_api_key = args.get("openai_api_key")
        
        return config