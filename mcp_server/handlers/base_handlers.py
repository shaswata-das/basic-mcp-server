"""
Base handlers for MCP Server methods

This module provides implementations of standard MCP method handlers.
"""

import json
from typing import Any, Dict, List, Optional

from mcp_server.core.server import HandlerInterface
from mcp_server.services import AIServiceRegistry, AIServiceInterface


class InitializeHandler(HandlerInterface):
    """Handler for the initialize method"""
    
    def __init__(self, server_name: str, server_version: str):
        """Initialize with server information"""
        self.server_name = server_name
        self.server_version = server_version
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request"""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {
                    "listChanged": False
                },
                "resources": {
                    "subscribe": False,
                    "listChanged": False
                }
            },
            "serverInfo": {
                "name": self.server_name,
                "version": self.server_version
            }
        }


class ToolsListHandler(HandlerInterface):
    """Handler for the tools/list method"""
    
    def __init__(self, tools: Dict[str, Dict[str, Any]]):
        """Initialize with tools registry"""
        self.tools = tools
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        return {
            "tools": list(self.tools.values())
        }


class ResourcesListHandler(HandlerInterface):
    """Handler for the resources/list method"""
    
    def __init__(self, resources: Dict[str, Dict[str, Any]]):
        """Initialize with resources registry"""
        self.resources = resources
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/list request"""
        return {
            "resources": list(self.resources.values())
        }


class ResourcesReadHandler(HandlerInterface):
    """Handler for the resources/read method"""
    
    def __init__(self, server_name: str, server_version: str, tools: Dict[str, Dict[str, Any]], 
                 resources: Dict[str, Dict[str, Any]]):
        """Initialize with server resources"""
        self.server_name = server_name
        self.server_version = server_version
        self.tools = tools
        self.resources = resources
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request"""
        uri = params.get("uri")
        
        if uri == "mcp://server/info":
            info = {
                "name": self.server_name,
                "version": self.server_version,
                "description": "MCP server with Claude API integration",
                "tools_count": len(self.tools),
                "resources_count": len(self.resources)
            }
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(info, indent=2)
                    }
                ]
            }
        else:
            raise ValueError(f"Unknown resource: {uri}")


class ToolsCallHandler(HandlerInterface):
    """Handler for the tools/call method"""
    
    def __init__(self, tools: Dict[str, Dict[str, Any]], 
                 ai_services: AIServiceRegistry):
        """Initialize with tools registry and AI service registry"""
        self.tools = tools
        self.ai_services = ai_services
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        # Verify tool exists
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        # Handle tools based on their name
        if tool_name == "echo":
            return await self._handle_echo(arguments)
        elif tool_name == "calculate":
            return await self._handle_calculate(arguments)
        elif tool_name == "ai/message":
            # New unified AI message handler
            return await self._handle_ai_message(arguments)
        elif tool_name == "ai/stream":
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Streaming is only supported in TCP mode with direct connection"
                    }
                ],
                "isError": True
            }
        elif tool_name == "claude/message":
            # For backward compatibility
            return await self._handle_claude_message(arguments)
        elif tool_name == "claude/stream":
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Streaming is only supported in TCP mode with direct connection"
                    }
                ],
                "isError": True
            }
        elif tool_name == "openai/message":
            # For backward compatibility
            return await self._handle_openai_message(arguments)
        elif tool_name == "openai/stream":
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Streaming is only supported in TCP mode with direct connection"
                    }
                ],
                "isError": True
            }
        elif tool_name.startswith("system/"):
            # System tools are handled directly by their specific handlers
            # This is just a placeholder since system methods are called directly
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"System tool '{tool_name}' should be accessed via the '{tool_name}' method, not through tools/call"
                    }
                ]
            }
        else:
            raise ValueError(f"Tool {tool_name} is registered but not implemented")
    
    async def _handle_ai_message(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Unified handler for AI messages that can dynamically select the service"""
        # Get the service type from the arguments or use the default
        service_name = arguments.get("service_name")
        ai_service = self.ai_services.get_service(service_name)
        
        if not ai_service:
            available_services = ", ".join(self.ai_services.list_services().keys())
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: AI service '{service_name}' not configured. Available services: {available_services}"
                    }
                ],
                "isError": True
            }
        
        try:
            prompt = arguments.get("prompt")
            model = arguments.get("model")  # This is optional - will use service default if not provided
            max_tokens = arguments.get("max_tokens")
            temperature = arguments.get("temperature")
            system = arguments.get("system")
            
            if not prompt:
                raise ValueError("Prompt is required")
            
            # Convert types if needed
            if max_tokens:
                max_tokens = int(max_tokens)
            if temperature:
                temperature = float(temperature)
            
            # Call the AI service - using the unified interface
            # Note: Each service already handles using its default model if model=None
            response = await ai_service.generate_text(
                prompt=prompt,
                model=model,  # This will use the service's default model if None
                max_tokens=max_tokens,
                temperature=temperature,
                system=system
            )
            
            # Include the service used and model info in the response
            service_info = {
                "service_used": service_name or self.ai_services.default_service,
                "model_used": model or "default"  # Would be nice to know the actual default model used
            }
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": response
                    }
                ],
                **service_info  # Include service info in response
            }
        except Exception as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error calling AI service '{service_name}': {str(e)}"
                    }
                ],
                "isError": True
            }
    
    async def _handle_echo(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle echo tool"""
        text = arguments.get("text", "")
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Echo: {text}"
                }
            ]
        }
    
    async def _handle_calculate(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle calculate tool"""
        expression = arguments.get("expression", "")
        try:
            # Simple safe evaluation for basic arithmetic
            allowed_chars = set("0123456789+-*/.() ")
            if all(c in allowed_chars for c in expression):
                result = eval(expression)
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Result: {result}"
                        }
                    ]
                }
            else:
                raise ValueError("Invalid characters in expression")
        except Exception as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: {str(e)}"
                    }
                ],
                "isError": True
            }
    
    async def _handle_claude_message(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle claude/message tool"""
        # Get the service type from the arguments or use "claude" by default
        service_name = arguments.get("service_name", "claude")
        ai_service = self.ai_services.get_service(service_name)
        
        if not ai_service:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: AI service '{service_name}' not configured"
                    }
                ],
                "isError": True
            }
        
        try:
            prompt = arguments.get("prompt")
            model = arguments.get("model")
            max_tokens = arguments.get("max_tokens")
            temperature = arguments.get("temperature")
            system = arguments.get("system")
            
            if not prompt:
                raise ValueError("Prompt is required")
            
            # Convert types if needed
            if max_tokens:
                max_tokens = int(max_tokens)
            if temperature:
                temperature = float(temperature)
            
            # Call the AI service
            response = await ai_service.generate_text(
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system
            )
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": response
                    }
                ]
            }
        except Exception as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error calling AI service: {str(e)}"
                    }
                ],
                "isError": True
            }
    
    async def _handle_openai_message(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle openai/message tool"""
        # Get the service type from the arguments or use "openai" by default
        service_name = arguments.get("service_name", "openai")
        ai_service = self.ai_services.get_service(service_name)
        
        if not ai_service:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: AI service '{service_name}' not configured"
                    }
                ],
                "isError": True
            }
        
        try:
            prompt = arguments.get("prompt")
            model = arguments.get("model")
            max_tokens = arguments.get("max_tokens")
            temperature = arguments.get("temperature")
            system = arguments.get("system")
            
            if not prompt:
                raise ValueError("Prompt is required")
            
            # Convert types if needed
            if max_tokens:
                max_tokens = int(max_tokens)
            if temperature:
                temperature = float(temperature)
            
            # Call the AI service - using the same interface as Claude
            response = await ai_service.generate_text(
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system
            )
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": response
                    }
                ]
            }
        except Exception as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error calling AI service: {str(e)}"
                    }
                ],
                "isError": True
            }
