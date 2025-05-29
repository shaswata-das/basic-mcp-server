"""
JSON-RPC Models for MCP Server

This module defines the data structures for JSON-RPC communication.
"""

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Union


class JSONRPCErrorCode:
    """Standard JSON-RPC 2.0 error codes"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    # Server specific errors
    SERVER_ERROR_START = -32000
    SERVER_ERROR_END = -32099


@dataclass
class MCPRequest:
    """Represents an MCP request"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: str = ""
    params: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPRequest":
        """Create a request object from a dictionary"""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data.get("method", ""),
            params=data.get("params")
        )


@dataclass
class MCPResponse:
    """Represents an MCP response"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to a dictionary, removing None values"""
        response_dict = asdict(self)
        return {k: v for k, v in response_dict.items() if v is not None}
    
    @classmethod
    def error_response(cls, error_code: int, message: str, 
                      id_: Optional[Union[str, int]] = None, 
                      data: Optional[Dict[str, Any]] = None) -> "MCPResponse":
        """Create an error response"""
        error = {
            "code": error_code,
            "message": message
        }
        if data:
            error["data"] = data
        
        return cls(
            jsonrpc="2.0",
            id=id_,
            error=error
        )
    
    @classmethod
    def result_response(cls, result: Dict[str, Any], 
                        id_: Optional[Union[str, int]]) -> "MCPResponse":
        """Create a success response"""
        return cls(
            jsonrpc="2.0",
            id=id_,
            result=result
        )


@dataclass
class StreamChunk:
    """Represents a streaming chunk response"""
    jsonrpc: str = "2.0"
    method: str = "stream/chunk"
    params: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def text_chunk(cls, text: str) -> Dict[str, Any]:
        """Create a text chunk response"""
        chunk = cls(
            method="claude/stream/chunk",
            params={"text": text}
        )
        return asdict(chunk)
    
    @classmethod
    def end_chunk(cls, status: str, message: Optional[str] = None) -> Dict[str, Any]:
        """Create an end of stream chunk"""
        params = {"status": status}
        if message:
            params["message"] = message
            
        chunk = cls(
            method="claude/stream/end",
            params=params
        )
        return asdict(chunk)
