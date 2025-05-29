"""
Transport interfaces for MCP Server

This module defines the abstract interfaces for different transport mechanisms
(stdio, TCP, etc.) used by the MCP server.
"""

import asyncio
import json
import sys
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union, List

from mcp_server.core.server import MCPServer
from mcp_server.models.json_rpc import JSONRPCErrorCode, MCPResponse


class Transport(ABC):
    """Base interface for transport mechanisms"""
    
    def __init__(self, server: MCPServer):
        """Initialize with reference to the MCP server"""
        self.server = server
        self.logger = logging.getLogger(f"mcp_server.transport.{self.__class__.__name__}")
    
    @abstractmethod
    async def start(self):
        """Start the transport"""
        pass
    
    @abstractmethod
    async def stop(self):
        """Stop the transport"""
        pass


class StdioTransport(Transport):
    """Transport using standard input/output"""
    
    async def start(self):
        """Start listening on stdio"""
        self.logger.info("Starting MCP Server on stdio")
        
        try:
            while True:
                # Read line from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # Parse JSON-RPC request
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    # Send error response for parse error
                    error_response = MCPResponse.error_response(
                        JSONRPCErrorCode.PARSE_ERROR,
                        "Parse error: invalid JSON",
                        None
                    )
                    print(json.dumps(error_response.to_dict()))
                    sys.stdout.flush()
                    continue
                
                # Process the message
                response = await self.server.process_jsonrpc_message(data)
                
                # Send response if any
                if response is not None:
                    print(json.dumps(response))
                    sys.stdout.flush()
        
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt, shutting down")
        except Exception as e:
            self.logger.exception(f"Error in stdio transport: {e}")
    
    async def stop(self):
        """Stop the stdio transport"""
        # Nothing to do for stdio
        self.logger.info("Stopping stdio transport")


class TCPTransport(Transport):
    """Transport using TCP sockets"""
    
    def __init__(self, server: MCPServer, host: str = "127.0.0.1", port: int = 9000):
        """Initialize with server and network settings"""
        super().__init__(server)
        self.host = host
        self.port = port
        self.server_instance = None
    
    async def handle_client(self, reader, writer):
        """Handle a TCP client connection"""
        addr = writer.get_extra_info('peername')
        self.logger.info(f"New client connected: {addr}")
        
        try:
            while not reader.at_eof():
                data = await reader.readline()
                if not data:
                    break
                
                line = data.decode('utf-8').strip()
                if not line:
                    continue
                
                # Parse JSON-RPC request
                try:
                    request_data = json.loads(line)
                except json.JSONDecodeError:
                    # Send error response for parse error
                    error_response = MCPResponse.error_response(
                        JSONRPCErrorCode.PARSE_ERROR,
                        "Parse error: invalid JSON",
                        None
                    )
                    writer.write(json.dumps(error_response.to_dict()).encode('utf-8') + b'\n')
                    await writer.drain()
                    continue
                
                # Process the message - special handling for streaming would go here
                response = await self.server.process_jsonrpc_message(request_data)
                
                # Send response if any
                if response is not None:
                    writer.write(json.dumps(response).encode('utf-8') + b'\n')
                    await writer.drain()
        
        except Exception as e:
            self.logger.exception(f"Error handling client {addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            self.logger.info(f"Client disconnected: {addr}")
    
    async def start(self):
        """Start the TCP server"""
        self.logger.info(f"Starting MCP Server on {self.host}:{self.port}")
        
        self.server_instance = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        
        addr = self.server_instance.sockets[0].getsockname()
        self.logger.info(f"Server running on {addr}")
        
        async with self.server_instance:
            await self.server_instance.serve_forever()
    
    async def stop(self):
        """Stop the TCP server"""
        if self.server_instance:
            self.logger.info("Stopping TCP server")
            self.server_instance.close()
            await self.server_instance.wait_closed()
            self.server_instance = None
