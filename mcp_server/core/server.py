"""
Core MCP Server functionality

This module provides the central server implementation with dependency injection
for handlers and transports.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union, Callable, Type
from abc import ABC, abstractmethod

from mcp_server.models.json_rpc import MCPRequest, MCPResponse, JSONRPCErrorCode
from mcp_server.config.settings import MCPServerConfig
from mcp_server.services.claude_service import AIServiceInterface


class HandlerInterface(ABC):
    """Interface for method handlers"""
    
    @abstractmethod
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a method call with parameters"""
        pass


class MCPServer:
    """Core MCP Server implementation with dependency injection"""
    
    def __init__(self, config: MCPServerConfig, ai_service: Optional[AIServiceInterface] = None):
        """Initialize the server with configuration and optional services"""
        self.config = config
        self.ai_service = ai_service
        self.name = config.name
        self.version = config.version
        self.description = config.description
        
        # Registry for method handlers
        self.method_handlers = {}
        
        # Tools and resources
        self.tools = {}
        self.resources = {}
        
        # Setup logger
        self.logger = logging.getLogger("mcp_server")
        
        # Initialize server components
        self.initialize()
    
    def initialize(self):
        """Initialize server components"""
        # This will be implemented by subclasses to register handlers
        pass
    
    def register_method_handler(self, method: str, handler: HandlerInterface):
        """Register a handler for a specific method"""
        self.logger.debug(f"Registering handler for method: {method}")
        self.method_handlers[method] = handler
    
    def register_tool(self, tool_name: str, tool_config: Dict[str, Any]):
        """Register a tool with the server"""
        self.tools[tool_name] = tool_config
    
    def register_resource(self, resource_uri: str, resource_config: Dict[str, Any]):
        """Register a resource with the server"""
        self.resources[resource_uri] = resource_config
    
    async def process_request(self, request: MCPRequest) -> MCPResponse:
        """Process a single request and return a response"""
        try:
            # Validate JSON-RPC version
            if request.jsonrpc != "2.0":
                return MCPResponse.error_response(
                    JSONRPCErrorCode.INVALID_REQUEST,
                    "Invalid JSON-RPC version, expected '2.0'",
                    request.id
                )
            
            # Find the handler for this method
            method = request.method
            handler = self.method_handlers.get(method)
            
            if not handler:
                return MCPResponse.error_response(
                    JSONRPCErrorCode.METHOD_NOT_FOUND,
                    f"Method not found: {method}",
                    request.id
                )
            
            # Execute the handler
            try:
                result = await handler.handle(request.params or {})
                return MCPResponse.result_response(result, request.id)
            except ValueError as e:
                return MCPResponse.error_response(
                    JSONRPCErrorCode.INVALID_PARAMS,
                    str(e),
                    request.id
                )
            except Exception as e:
                self.logger.exception(f"Error processing method {method}")
                return MCPResponse.error_response(
                    JSONRPCErrorCode.INTERNAL_ERROR,
                    f"Internal server error: {str(e)}",
                    request.id
                )
        
        except Exception as e:
            self.logger.exception("Unexpected error processing request")
            return MCPResponse.error_response(
                JSONRPCErrorCode.INTERNAL_ERROR,
                f"Server error: {str(e)}",
                request.id if hasattr(request, 'id') else None
            )
    
    async def process_jsonrpc_message(self, data: Union[Dict, List]) -> Union[Dict, List, None]:
        """Process a JSON-RPC message which can be a batch or single request"""
        if isinstance(data, list):
            # Handle batch request
            if not data:
                # Empty batch is invalid
                return MCPResponse.error_response(
                    JSONRPCErrorCode.INVALID_REQUEST,
                    "Invalid Request: empty batch",
                    None
                ).to_dict()
            
            responses = []
            for req_data in data:
                try:
                    request = MCPRequest.from_dict(req_data)
                    response = await self.process_request(request)
                    
                    # Only include responses for non-notifications (requests with id)
                    if request.id is not None:
                        responses.append(response.to_dict())
                except Exception as e:
                    if req_data.get("id") is not None:
                        error_response = MCPResponse.error_response(
                            JSONRPCErrorCode.INTERNAL_ERROR,
                            f"Internal error: {str(e)}",
                            req_data.get("id")
                        )
                        responses.append(error_response.to_dict())
            
            return responses if responses else None
        
        elif isinstance(data, dict):
            # Handle single request
            try:
                request = MCPRequest.from_dict(data)
                response = await self.process_request(request)
                
                # Don't return anything for notifications (requests without id)
                if request.id is None:
                    return None
                
                return response.to_dict()
            except Exception as e:
                if data.get("id") is not None:
                    error_response = MCPResponse.error_response(
                        JSONRPCErrorCode.INTERNAL_ERROR,
                        f"Internal error: {str(e)}",
                        data.get("id")
                    )
                    return error_response.to_dict()
                return None
        
        else:
            # Invalid request
            error_response = MCPResponse.error_response(
                JSONRPCErrorCode.INVALID_REQUEST,
                "Invalid Request: expected object or array",
                None
            )
            return error_response.to_dict()