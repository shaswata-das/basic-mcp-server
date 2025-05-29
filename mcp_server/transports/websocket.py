"""
WebSocket Transport for MCP Server

This module provides a WebSocket transport implementation for the MCP server,
allowing browser clients and other WebSocket-capable applications to connect.
"""

import asyncio
import json
import logging
import ssl
import websockets
from typing import Optional, Dict, Any, Set
from websockets.server import WebSocketServerProtocol

from mcp_server.core.server import MCPServer
from mcp_server.transports.base import Transport
from mcp_server.models.json_rpc import JSONRPCErrorCode, MCPResponse, StreamChunk


class WebSocketTransport(Transport):
    """Transport using WebSockets"""
    
    def __init__(self, server: MCPServer, host: str = "127.0.0.1", port: int = 8765,
                 ssl_context: Optional[ssl.SSLContext] = None, 
                 path: str = "/", origins: Optional[Set[str]] = None):
        """Initialize with server and network settings
        
        Args:
            server: MCP server instance
            host: Host to bind WebSocket server
            port: Port for WebSocket server
            ssl_context: Optional SSL context for secure WebSockets (wss://)
            path: URL path to serve WebSockets on
            origins: Set of allowed origins for CORS (None = allow all)
        """
        super().__init__(server)
        self.host = host
        self.port = port
        self.ssl_context = ssl_context
        self.path = path
        self.origins = origins
        self.server_instance = None
        self.active_connections: Set[WebSocketServerProtocol] = set()
        
        # For streaming responses
        self.streaming_clients: Dict[str, WebSocketServerProtocol] = {}
    
    async def start(self):
        """Start the WebSocket server"""
        self.logger.info(f"Starting MCP Server WebSocket transport on ws://{self.host}:{self.port}{self.path}")
        
        # Create WebSocket server
        self.server_instance = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ssl=self.ssl_context,
            process_request=self.process_request,
            ping_interval=30,  # Send ping frames every 30 seconds
            ping_timeout=10    # Wait 10 seconds for pong response
        )
        
        self.logger.info(f"WebSocket server running on {'wss' if self.ssl_context else 'ws'}://{self.host}:{self.port}{self.path}")
        
        # Keep server running
        await self.server_instance.wait_closed()
    
    async def process_request(self, path, headers):
        """Process HTTP request for WebSocket upgrade
        
        Used for path routing and CORS handling
        """
        # Check if the path matches
        if path != self.path:
            return (404, {}, b"Not Found")
        
        # Handle CORS if origins are specified
        if self.origins:
            origin = headers.get("Origin", "")
            if origin not in self.origins:
                return (403, {}, b"Forbidden")
        
        # Let the WebSocket handler proceed
        return None
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle a WebSocket client connection"""
        # Track active connections
        self.active_connections.add(websocket)
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.logger.info(f"New WebSocket client connected: {client_id}")
        
        try:
            async for message in websocket:
                # Parse JSON-RPC message
                try:
                    request_data = json.loads(message)
                except json.JSONDecodeError:
                    # Send error response for parse error
                    error_response = MCPResponse.error_response(
                        JSONRPCErrorCode.PARSE_ERROR,
                        "Parse error: invalid JSON",
                        None
                    )
                    await websocket.send(json.dumps(error_response.to_dict()))
                    continue
                
                # Special handling for streaming
                is_streaming_request = False
                if isinstance(request_data, dict):
                    method = request_data.get("method")
                    params = request_data.get("params", {})
                    
                    if method == "tools/call":
                        tool_name = params.get("name")
                        if tool_name in ["ai/stream", "claude/stream", "openai/stream"]:
                            is_streaming_request = True
                            request_id = request_data.get("id")
                            # Register this websocket for streaming responses
                            stream_id = f"{client_id}:{request_id}"
                            self.streaming_clients[stream_id] = websocket
                            # We'll handle streaming separately - response will be sent
                            # incrementally through the websocket
                
                # Process the message
                response = await self.server.process_jsonrpc_message(request_data)
                
                # Send response if any (non-streaming case)
                if response is not None and not is_streaming_request:
                    await websocket.send(json.dumps(response))
        
        except websockets.exceptions.ConnectionClosed as e:
            self.logger.info(f"WebSocket connection closed with {client_id}: {e}")
        except Exception as e:
            self.logger.exception(f"Error handling WebSocket client {client_id}: {e}")
        finally:
            # Clean up
            self.active_connections.discard(websocket)
            # Remove from streaming clients if present
            for key in list(self.streaming_clients.keys()):
                if self.streaming_clients[key] == websocket:
                    del self.streaming_clients[key]
            
            self.logger.info(f"WebSocket client disconnected: {client_id}")
    
    async def send_stream_chunk(self, stream_id: str, chunk: Dict[str, Any]):
        """Send a stream chunk to a specific client
        
        This method is called by streaming handlers to send incremental updates.
        """
        websocket = self.streaming_clients.get(stream_id)
        if websocket and websocket.open:
            try:
                await websocket.send(json.dumps(chunk))
                return True
            except Exception as e:
                self.logger.error(f"Error sending stream chunk to {stream_id}: {e}")
                return False
        return False
    
    async def stop(self):
        """Stop the WebSocket server"""
        if self.server_instance:
            self.logger.info("Stopping WebSocket server")
            
            # Close all active connections
            close_tasks = [ws.close() for ws in self.active_connections]
            if close_tasks:
                await asyncio.gather(*close_tasks, return_exceptions=True)
            
            # Clear streaming clients
            self.streaming_clients.clear()
            
            # Close server
            self.server_instance.close()
            await self.server_instance.wait_closed()
            self.server_instance = None
            
            self.logger.info("WebSocket server stopped")
