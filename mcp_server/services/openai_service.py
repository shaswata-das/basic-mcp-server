"""
OpenAI API Service

This module provides an interface for interacting with OpenAI's API.
"""

import json
import aiohttp
from typing import Any, Dict, Optional
import logging

from mcp_server.services.claude_service import AIServiceInterface


class OpenAIService(AIServiceInterface):
    """Service for interacting with OpenAI API"""
    
    def __init__(self, api_key: str, default_model: str = "gpt-4o",
                 default_max_tokens: int = 1024, default_temperature: float = 0.7):
        """Initialize the OpenAI service with API key and defaults"""
        self.api_key = api_key
        self.default_model = default_model
        self.default_max_tokens = default_max_tokens
        self.default_temperature = default_temperature
        self.api_url_chat = "https://api.openai.com/v1/chat/completions"
        self.logger = logging.getLogger("mcp_server.services.openai")
    
    async def generate_text(self, prompt: str, model: Optional[str] = None, 
                            max_tokens: Optional[int] = None, 
                            temperature: Optional[float] = None,
                            system: Optional[str] = None) -> str:
        """Generate text from OpenAI API"""
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")
        
        response = await self._call_api(
            prompt=prompt,
            model=model or self.default_model,
            max_tokens=max_tokens or self.default_max_tokens,
            temperature=temperature or self.default_temperature,
            system=system,
            stream=False
        )
        
        # Extract the response text from the completion
        if 'choices' in response and len(response['choices']) > 0:
            if 'message' in response['choices'][0]:
                return response['choices'][0]['message']['content']
            else:
                self.logger.error(f"Unexpected response format: {response}")
                return "Error: Unexpected response format from OpenAI API"
        else:
            self.logger.error(f"No choices in response: {response}")
            return "Error: No response generated from OpenAI API"
    
    async def generate_stream(self, prompt: str, model: Optional[str] = None,
                            max_tokens: Optional[int] = None,
                            temperature: Optional[float] = None,
                            system: Optional[str] = None) -> tuple[aiohttp.ClientSession, aiohttp.ClientResponse]:
        """Generate a streaming response from OpenAI API

        Returns a tuple of ``(session, response)`` with the underlying
        ``aiohttp.ClientSession`` and ``aiohttp.ClientResponse`` left open.
        Callers are responsible for closing both when finished.
        """
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")
        
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
        """Make the API call to OpenAI"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Prepare messages in the format OpenAI expects
        messages = []
        
        # Add system message if provided
        if system:
            messages.append({
                "role": "system", 
                "content": system
            })
        
        # Add user message (the prompt)
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Prepare the payload
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream
        }
        
        self.logger.debug(f"Calling OpenAI API with model: {model}")
        
        session = aiohttp.ClientSession()
        try:
            response = await session.post(self.api_url_chat, headers=headers, json=payload)
            if response.status != 200:
                error_text = await response.text()
                error_msg = f"API error (status {response.status}): {error_text}"
                self.logger.error(error_msg)
                await session.close()
                raise ValueError(error_msg)

            if stream:
                # Leave session and response open so caller can read the stream
                return session, response
            else:
                data = await response.json()
                await session.close()
                return data
        except Exception:
            await session.close()
            raise
