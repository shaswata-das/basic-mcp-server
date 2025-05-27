"""
Claude API Service

This module provides an interface for interacting with Claude API.
"""

import json
import aiohttp
from typing import Any, Dict, Optional
from abc import ABC, abstractmethod


class AIServiceInterface(ABC):
    """Interface for AI services like Claude"""
    
    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text from a prompt"""
        pass
    
    @abstractmethod
    async def generate_stream(self, prompt: str, **kwargs) -> Any:
        """Generate a streaming response"""
        pass


class ClaudeService(AIServiceInterface):
    """Service for interacting with Claude API"""
    
    def __init__(self, api_key: str, default_model: str = "claude-3-opus-20240229",
                 default_max_tokens: int = 4096, default_temperature: float = 0.7):
        """Initialize the Claude service with API key and defaults"""
        self.api_key = api_key
        self.default_model = default_model
        self.default_max_tokens = default_max_tokens
        self.default_temperature = default_temperature
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.api_version = "2023-06-01"
    
    async def generate_text(self, prompt: str, model: Optional[str] = None, 
                            max_tokens: Optional[int] = None, 
                            temperature: Optional[float] = None,
                            system: Optional[str] = None) -> str:
        """Generate text from Claude API"""
        if not self.api_key:
            raise ValueError("Anthropic API key not configured")
        
        response = await self._call_api(
            prompt=prompt,
            model=model or self.default_model,
            max_tokens=max_tokens or self.default_max_tokens,
            temperature=temperature or self.default_temperature,
            system=system,
            stream=False
        )
        
        return response["content"][0]["text"]
    
    async def generate_stream(self, prompt: str, model: Optional[str] = None, 
                            max_tokens: Optional[int] = None, 
                            temperature: Optional[float] = None,
                            system: Optional[str] = None) -> aiohttp.ClientResponse:
        """Generate a streaming response from Claude API"""
        if not self.api_key:
            raise ValueError("Anthropic API key not configured")
        
        return await self._call_api(
            prompt=prompt,
            model=model or self.default_model,
            max_tokens=max_tokens or self.default_max_tokens,
            temperature=temperature or self.default_temperature,
            system=system,
            stream=True
        )
    
    async def _call_api(self, prompt: str, model: str, max_tokens: int, 
                      temperature: float, system: Optional[str], stream: bool) -> Any:
        """Make the API call to Claude"""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "content-type": "application/json"
        }
        
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        if system:
            payload["system"] = system
        
        if stream:
            payload["stream"] = True
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ValueError(f"API error (status {response.status}): {error_text}")
                
                if stream:
                    return response  # Return the response object for streaming
                else:
                    return await response.json()


class MockClaudeService(AIServiceInterface):
    """Mock service for testing without API keys"""
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate mock text response"""
        return f"Mock Claude response to: {prompt}"
    
    async def generate_stream(self, prompt: str, **kwargs) -> Any:
        """Generate a mock streaming response"""
        # This is a simplified mock that doesn't actually stream
        return f"Mock Claude streaming response to: {prompt}"