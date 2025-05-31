#!/usr/bin/env python3

"""
MCP Server with Claude API Integration

A modular Model Context Protocol server that communicates with Claude by Anthropic.
Built with SOLID principles for maintainability and extensibility.

Environment variables can be configured in the .env file.
"""

import asyncio
import argparse
import logging
import sys
import os
from pathlib import Path

from mcp_server.config.settings import MCPServerConfig
from mcp_server.models.json_rpc import JSONRPCErrorCode
from mcp_server.services import create_ai_services_from_config, AIServiceRegistry
from mcp_server.core.server import MCPServer
from mcp_server.transports.base import StdioTransport, TCPTransport
from mcp_server.transports.websocket import WebSocketTransport
from mcp_server.handlers.base_handlers import (
    InitializeHandler,
    ToolsListHandler,
    ToolsCallHandler,
    ResourcesListHandler,
    ResourcesReadHandler
)
from mcp_server.handlers.system_handlers import (
    SystemInfoHandler,
    SystemHealthHandler
)
from mcp_server.handlers.knowledge_handlers import (
    RepositoryAnalysisHandler,
    KnowledgeExtractionHandler
)
from mcp_server.handlers.enhanced_knowledge_handlers import (
    EnhancedRepositoryAnalysisHandler,
    EnhancedCodeSearchHandler,
    DependencyAnalysisHandler
)
from mcp_server.handlers.ai_development_handlers import (
    CodebaseAnalysisHandler,
    CodeSearchHandler,
    KnowledgeGraphQueryHandler
)
from mcp_server.services.scanners.csharp_scanner import CSharpScannerService
from mcp_server.services.scanners.angular_scanner import AngularScannerService
from mcp_server.services.vector_store.qdrant_service import QdrantVectorService
from mcp_server.services.mongodb_service import MongoDBService
from mcp_server.services.embedding_service import EmbeddingService


class AIMCPServerApp(MCPServer):
    """MCP Server Application with AI model integration"""
    
    def __init__(self, config: MCPServerConfig, ai_services: AIServiceRegistry):
        """Initialize with configuration and AI service registry"""
        self.config = config
        self.ai_services = ai_services  # Store the registry
        super().__init__(config, None)  # Don't pass ai_service to parent, we use ai_services instead
    
    def initialize(self):
        """Initialize server components"""
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Setup tools
        self._setup_default_tools()
        self._setup_ai_tools()  # Unified AI tools
        self._setup_system_tools()  # Add system tools
        self._setup_knowledge_tools()  # Add knowledge extraction tools
        self._setup_default_resources()
        
        # Register method handlers
        self.register_method_handler("initialize", 
            InitializeHandler(self.name, self.version))
        
        self.register_method_handler("tools/list", 
            ToolsListHandler(self.tools))
        
        self.register_method_handler("tools/call", 
            ToolsCallHandler(self.tools, self.ai_services))
        
        self.register_method_handler("resources/list", 
            ResourcesListHandler(self.resources))
        
        self.register_method_handler("resources/read", 
            ResourcesReadHandler(self.name, self.version, self.tools, self.resources))
        
        # Create required services for knowledge extraction
        csharp_scanner = CSharpScannerService()
        angular_scanner = AngularScannerService()
        
        # Get API keys from config
        openai_api_key = self.config.openai_api_key
        anthropic_api_key = self.config.anthropic_api_key
        
        # Create embedding service - prefer OpenAI for embeddings if available
        embedding_service = EmbeddingService(
            openai_api_key=openai_api_key,
            anthropic_api_key=anthropic_api_key,
            model="text-embedding-3-small" if openai_api_key else "claude-3-haiku-20240307"
        )
        
        # Create vector store service
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        vector_service = QdrantVectorService(url=qdrant_url, api_key=qdrant_api_key)
        
        # Create MongoDB service
        mongodb_service = MongoDBService(
            uri="mongodb://localhost:27017",
            db_name="mcp-server"
        )
        
        # Register system handlers
        self.register_method_handler("system/info", SystemInfoHandler())
        self.register_method_handler("system/health", SystemHealthHandler(
            service_dependencies=["claude_api"] if self.ai_service else []
        ))
        
        # Register knowledge handlers
        self.register_method_handler("repository/analyze", RepositoryAnalysisHandler(
            csharp_scanner=csharp_scanner,
            angular_scanner=angular_scanner,
            mongodb_service=mongodb_service
        ))
        
        # Get AI service, handling the case where ai_services might not be available
        ai_service = None
        if hasattr(self, 'ai_services') and self.ai_services:
            ai_service = self.ai_services.get_service()
        
        self.register_method_handler("knowledge/extract", KnowledgeExtractionHandler(
            mongodb_service=mongodb_service,
            embedding_service=embedding_service,
            vector_service=vector_service,
            ai_service=ai_service
        ))
        
        # Register enhanced knowledge handlers
        self.register_method_handler("repository/enhanced_analyze", EnhancedRepositoryAnalysisHandler(
            mongodb_service=mongodb_service,
            embedding_service=embedding_service,
            vector_service=vector_service,
            ai_service=ai_service
        ))
        
        self.register_method_handler("knowledge/search", EnhancedCodeSearchHandler(
            mongodb_service=mongodb_service,
            embedding_service=embedding_service,
            vector_service=vector_service
        ))
        
        self.register_method_handler("knowledge/dependencies", DependencyAnalysisHandler(
            mongodb_service=mongodb_service
        ))
        
        # Register AI development handlers
        self.register_method_handler("codebase/analyze", CodebaseAnalysisHandler(
            mongodb_service=mongodb_service,
            embedding_service=embedding_service,
            vector_service=vector_service,
            ai_service=ai_service
        ))
        
        self.register_method_handler("code/search", CodeSearchHandler(
            mongodb_service=mongodb_service,
            embedding_service=embedding_service,
            vector_service=vector_service
        ))
        
        self.register_method_handler("knowledge/query", KnowledgeGraphQueryHandler(
            mongodb_service=mongodb_service,
            ai_service=ai_service
        ))
    
    def _setup_default_tools(self):
        """Setup default tools the server provides"""
        self.register_tool("echo", {
            "name": "echo",
            "description": "Echo back the provided text",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to echo back"
                    }
                },
                "required": ["text"]
            }
        })
        
        self.register_tool("calculate", {
            "name": "calculate",
            "description": "Perform basic arithmetic calculations",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate (e.g., '2 + 3 * 4')"
                    }
                },
                "required": ["expression"]
            }
        })
    
    def _setup_ai_tools(self):
        """Setup AI tools with dynamic service selection"""
        # Get available services
        if hasattr(self, 'ai_services') and self.ai_services:
            available_services = list(self.ai_services.list_services().keys())
        else:
            available_services = ["mock"]
        
        # Get default models for each service
        default_models = {
            "claude": self.config.claude_default_model if hasattr(self.config, 'claude_default_model') else "claude-3-opus-20240229",
            "openai": self.config.openai_default_model if hasattr(self.config, 'openai_default_model') else "gpt-4o",
            "mock": "mock-model"
        }
        
        # Register the unified AI message tool
        self.register_tool("ai/message", {
            "name": "ai/message",
            "description": "Send a message to any configured AI service and get a response",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The message to send to the AI"
                    },
                    "service_name": {
                        "type": "string",
                        "description": "AI service to use (defaults to server configuration)",
                        "enum": available_services
                    },
                    "model": {
                        "type": "string",
                        "description": "Model to use (optional - each service will use its default model if not specified)"
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum number of tokens in response (optional - uses service defaults)"
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Temperature for response generation (optional - uses service defaults)"
                    },
                    "system": {
                        "type": "string",
                        "description": "Optional system prompt to guide the model's behavior"
                    }
                },
                "required": ["prompt"]
            }
        })
        
        # Register the unified AI streaming tool
        self.register_tool("ai/stream", {
            "name": "ai/stream",
            "description": "Stream a response from any configured AI service (TCP mode only)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The message to send to the AI"
                    },
                    "service_name": {
                        "type": "string",
                        "description": "AI service to use (defaults to server configuration)",
                        "enum": available_services
                    },
                    "model": {
                        "type": "string",
                        "description": "Model to use (specific to the service)"
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum number of tokens in response"
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Temperature for response generation"
                    },
                    "system": {
                        "type": "string",
                        "description": "Optional system prompt to guide the model's behavior"
                    }
                },
                "required": ["prompt"]
            }
        })
        
        # For backward compatibility, we would setup service-specific tools,
        # but they are now handled by the unified tools
        # self._setup_claude_tools()
        # self._setup_openai_tools()
    
    def _setup_system_tools(self):
        """Setup system-related tools"""
        self.register_tool("system/info", {
            "name": "system/info",
            "description": "Get detailed system information including CPU, memory, and disk usage",
            "inputSchema": {
                "type": "object",
                "properties": {}  # No parameters needed
            }
        })
        
        self.register_tool("system/health", {
            "name": "system/health",
            "description": "Check the health status of the server and its dependencies",
            "inputSchema": {
                "type": "object",
                "properties": {}  # No parameters needed
            }
        })
    
    def _setup_knowledge_tools(self):
        """Setup knowledge extraction tools"""
        self.register_tool("repository/analyze", {
            "name": "repository/analyze",
            "description": "Analyze a repository to extract structure and key components",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Path to the repository"
                    },
                    "repo_name": {
                        "type": "string",
                        "description": "Name of the repository (defaults to directory name)"
                    },
                    "exclude_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Patterns to ignore (glob format)"
                    },
                    "framework_hint": {
                        "type": "string",
                        "description": "Framework hint ('csharp', 'angular', 'both', or 'auto')",
                        "enum": ["csharp", "angular", "both", "auto"]
                    }
                },
                "required": ["repo_path"]
            }
        })
        
        self.register_tool("knowledge/extract", {
            "name": "knowledge/extract",
            "description": "Extract knowledge from a repository and generate documentation",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "Repository ID from repository/analyze"
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Directory to store generated documentation"
                    },
                    "framework_focus": {
                        "type": "string",
                        "description": "Framework to focus on ('csharp', 'angular', 'both', or 'auto')",
                        "enum": ["csharp", "angular", "both", "auto"]
                    }
                },
                "required": ["repo_id", "output_dir"]
            }
        })
        
        # Enhanced knowledge tools
        self.register_tool("repository/enhanced_analyze", {
            "name": "repository/enhanced_analyze",
            "description": "Perform deep code analysis with call graphs, patterns, and environment analysis",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Path to the repository"
                    },
                    "repo_name": {
                        "type": "string",
                        "description": "Name of the repository (defaults to directory name)"
                    },
                    "exclude_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Patterns to ignore (glob format)"
                    },
                    "extract_patterns": {
                        "type": "boolean",
                        "description": "Whether to extract code patterns"
                    },
                    "extract_call_graphs": {
                        "type": "boolean",
                        "description": "Whether to extract function call graphs"
                    },
                    "extract_environment": {
                        "type": "boolean",
                        "description": "Whether to analyze environment and dependencies"
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Directory to store analysis output"
                    }
                },
                "required": ["repo_path"]
            }
        })
        
        self.register_tool("knowledge/search", {
            "name": "knowledge/search",
            "description": "Search for code using semantic embeddings",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "Repository ID from repository/analyze"
                    },
                    "query": {
                        "type": "string",
                        "description": "Natural language search query"
                    },
                    "language": {
                        "type": "string",
                        "description": "Optional language filter"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return"
                    },
                    "include_code": {
                        "type": "boolean",
                        "description": "Whether to include code snippets in results"
                    }
                },
                "required": ["repo_id", "query"]
            }
        })
        
        self.register_tool("knowledge/dependencies", {
            "name": "knowledge/dependencies",
            "description": "Analyze dependencies between components",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "Repository ID from repository/analyze"
                    },
                    "component_id": {
                        "type": "string",
                        "description": "Component ID to analyze dependencies for"
                    },
                    "component_type": {
                        "type": "string",
                        "description": "Component type to analyze dependencies for"
                    },
                    "include_transitive": {
                        "type": "boolean",
                        "description": "Whether to include transitive dependencies"
                    }
                },
                "required": ["repo_id"]
            }
        })
        
        # AI Development Tools
        self.register_tool("codebase/analyze", {
            "name": "codebase/analyze",
            "description": "Analyze a codebase and generate AI-friendly documentation and knowledge",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Path to the repository"
                    },
                    "repo_name": {
                        "type": "string",
                        "description": "Name of the repository (defaults to directory name)"
                    },
                    "exclude_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Patterns to ignore (glob format)"
                    },
                    "file_limit": {
                        "type": "integer",
                        "description": "Maximum number of files to analyze"
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Directory to store analysis output"
                    }
                },
                "required": ["repo_path"]
            }
        })
        
        self.register_tool("code/search", {
            "name": "code/search",
            "description": "Search code and documentation using natural language queries",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "Repository ID from codebase/analyze"
                    },
                    "query": {
                        "type": "string",
                        "description": "Natural language query"
                    },
                    "search_type": {
                        "type": "string",
                        "description": "Type of search",
                        "enum": ["all", "code", "documentation"]
                    },
                    "language": {
                        "type": "string",
                        "description": "Language to filter results by"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return"
                    }
                },
                "required": ["repo_id", "query"]
            }
        })
        
        self.register_tool("knowledge/query", {
            "name": "knowledge/query",
            "description": "Query the knowledge graph for information about a codebase",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "Repository ID from codebase/analyze"
                    },
                    "query_type": {
                        "type": "string",
                        "description": "Type of query",
                        "enum": ["general", "component", "pattern"]
                    },
                    "component_name": {
                        "type": "string",
                        "description": "Name of the component to query"
                    },
                    "pattern_name": {
                        "type": "string",
                        "description": "Name of the pattern to query"
                    }
                },
                "required": ["repo_id"]
            }
        })
    
    def _setup_default_resources(self):
        """Setup default resources the server provides"""
        self.register_resource("mcp://server/info", {
            "uri": "mcp://server/info",
            "name": "Server Information",
            "description": "Information about this MCP server",
            "mimeType": "application/json"
        })


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='AI MCP Server with JSON-RPC')
    
    # Transport options
    transport_group = parser.add_argument_group('Transport Options')
    transport_type = transport_group.add_mutually_exclusive_group()
    transport_type.add_argument('--tcp', action='store_true', 
                              help='Run as TCP server (can also set MCP_TRANSPORT_TYPE=tcp in .env)')
    transport_type.add_argument('--websocket', action='store_true',
                              help='Run as WebSocket server (can also set MCP_TRANSPORT_TYPE=websocket in .env)')
    transport_group.add_argument('--host', help='Host to bind server (can also set MCP_TCP_HOST in .env)')
    transport_group.add_argument('--port', type=int, help='Port for server (can also set MCP_TCP_PORT for TCP or MCP_WS_PORT for WebSocket)')
    transport_group.add_argument('--ws-path', help='URL path for WebSocket server (default: /)')
    
    # AI service options
    service_group = parser.add_argument_group('AI Service Options')
    service_group.add_argument('--service-type', choices=['claude', 'openai', 'mock'], 
                            help='AI service to use (can also set AI_SERVICE_TYPE in .env)')
    service_group.add_argument('--claude-api-key', help='Anthropic API key (can also set ANTHROPIC_API_KEY in .env)')
    service_group.add_argument('--openai-api-key', help='OpenAI API key (can also set OPENAI_API_KEY in .env)')
    service_group.add_argument('--mock', action='store_true', help='Use mock AI service (for testing)')
    
    # Other options
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    parser.add_argument('--env-file', help='Path to .env file (default: .env in project root)')
    args = parser.parse_args()
    
    # Load custom .env file if specified
    if args.env_file:
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=args.env_file)
            logging.info(f"Loaded environment variables from {args.env_file}")
        except ImportError:
            logging.error("--env-file specified but python-dotenv not installed. Please install with: pip install python-dotenv")
            sys.exit(1)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )
    
    # Create configuration from environment and command line args
    config = MCPServerConfig.from_args(vars(args))
    
    # Create the AI service registry
    ai_services = create_ai_services_from_config(config)
    
    # Log the available services
    available_services = ai_services.list_services()
    if available_services:
        logging.info(f"Available AI services: {', '.join(available_services.keys())}")
        logging.info(f"Default AI service: {ai_services.default_service}")
    else:
        logging.warning("No AI services configured. AI functionality will be unavailable.")
    
    # Create server with service registry
    server = AIMCPServerApp(config, ai_services)
    
    # Set host and port
    host = args.host or config.tcp_host
    
    # Create transports based on configuration
    transports = []
    
    # Check if stdio is enabled
    if 'stdio' in config.transport_types:
        logging.info("Setting up stdio transport")
        transports.append(StdioTransport(server))
    
    # Check if TCP is enabled
    if 'tcp' in config.transport_types:
        port = args.port or config.tcp_port
        logging.info(f"Setting up TCP transport on {host}:{port}")
        transports.append(TCPTransport(server, host, port))
    
    # Check if WebSocket is enabled
    if 'websocket' in config.transport_types:
        port = args.port or config.ws_port
        ws_path = args.ws_path or config.ws_path
        logging.info(f"Setting up WebSocket transport on {host}:{port}{ws_path}")
        transports.append(WebSocketTransport(server, host, port, path=ws_path))
    
    if not transports:
        logging.warning("No transports configured. Defaulting to stdio.")
        transports.append(StdioTransport(server))
    
    # Start all transports
    if len(transports) == 1:
        # Simple case - just one transport
        await transports[0].start()
    else:
        # Multiple transports - run them concurrently
        logging.info(f"Starting {len(transports)} transports")
        
        # Create tasks for each transport
        transport_tasks = [asyncio.create_task(transport.start()) for transport in transports]
        
        # Wait for any transport to complete (or all if all complete normally)
        done, pending = await asyncio.wait(
            transport_tasks, 
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # If any transport ended, cancel the others
        for task in pending:
            task.cancel()
        
        # Wait for the cancellations to complete
        if pending:
            await asyncio.wait(pending, return_when=asyncio.ALL_COMPLETED)


if __name__ == "__main__":
    try:
        # Display info about configuration
        env_file = Path(__file__).resolve().parent / '.env'
        if env_file.exists():
            print(f"Using configuration from .env file: {env_file}", file=sys.stderr)
        else:
            print("No .env file found. Using environment variables or defaults.", file=sys.stderr)
            
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    except Exception as e:
        logging.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)