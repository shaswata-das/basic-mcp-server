"""
Embedding Service for MCP Server

This module provides embedding generation for code using various AI models.
"""

import logging
import asyncio
import time
import os
from typing import List, Dict, Any, Optional, Union

import aiohttp
import numpy as np

class EmbeddingService:
    """Service for generating embeddings from code"""
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        batch_size: int = 10,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        azure_api_url: Optional[str] = None,
        azure_api_key: Optional[str] = None
    ):
        """Initialize the embedding service
        
        Args:
            openai_api_key: OpenAI API key
            anthropic_api_key: Anthropic API key
            model: Embedding model to use
            batch_size: Maximum batch size for embedding requests
            max_retries: Maximum number of retries for failed requests
            retry_delay: Delay between retries in seconds
            azure_api_url: Azure OpenAI API URL
            azure_api_key: Azure OpenAI API key
        """
        self.logger = logging.getLogger("mcp_server.services.embedding")
        self.openai_api_key = openai_api_key
        self.anthropic_api_key = anthropic_api_key
        self.model = model
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.azure_api_url = azure_api_url
        self.azure_api_key = azure_api_key
        
        # Set provider based on model name and configuration
        if model == "text-embedding-3-large" and self.azure_api_url:
            self.provider = "azure"
            # Load from environment if not provided
            if not self.azure_api_url:
                self.azure_api_url = os.environ.get("EMBEDDINGS_3_LARGE_API_URL")
                self.azure_api_key = os.environ.get("EMBEDDINGS_3_LARGE_API_KEY")
        elif model == "text-embedding-3-small" and self.azure_api_url:
            self.provider = "azure"
            # Load from environment if not provided
            if not self.azure_api_url:
                self.azure_api_url = os.environ.get("EMBEDDINGS_3_SMALL_API_URL")
                self.azure_api_key = os.environ.get("EMBEDDINGS_3_SMALL_API_KEY")
        elif model.startswith("text-embedding"):
            self.provider = "openai"
        elif model.startswith("claude"):
            self.provider = "anthropic"
        else:
            self.provider = "openai"  # Default to OpenAI
            
        self.logger.info(f"Initialized embedding service with {self.provider} provider and model {model}")
    
    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        embeddings = await self.get_embeddings([text])
        return embeddings[0]
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        # Process in batches to avoid API limits
        all_embeddings = []
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i+self.batch_size]
            
            # Get embeddings with retry logic
            batch_embeddings = await self._get_embeddings_with_retry(batch)
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    async def _get_embeddings_with_retry(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings with retry logic
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        retries = 0
        
        while retries <= self.max_retries:
            try:
                if self.provider == "openai":
                    return await self._get_openai_embeddings(texts)
                elif self.provider == "anthropic":
                    return await self._get_anthropic_embeddings(texts)
                elif self.provider == "azure":
                    return await self._get_azure_embeddings(texts)
                else:
                    raise ValueError(f"Unknown provider: {self.provider}")
            
            except Exception as e:
                retries += 1
                if retries > self.max_retries:
                    self.logger.error(f"Failed to get embeddings after {self.max_retries} retries: {str(e)}")
                    raise
                
                self.logger.warning(f"Embedding request failed (attempt {retries}/{self.max_retries}): {str(e)}")
                await asyncio.sleep(self.retry_delay * retries)  # Exponential backoff
    
    async def _get_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from OpenAI API
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        
        # Prepare API request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_api_key}"
        }
        
        data = {
            "input": texts,
            "model": self.model,
            "encoding_format": "float"
        }
        
        # Make API request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/embeddings",
                headers=headers,
                json=data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ValueError(f"OpenAI API error ({response.status}): {error_text}")
                
                result = await response.json()
                
                # Extract embeddings
                embeddings = [item["embedding"] for item in result["data"]]
                return embeddings
    
    async def _get_anthropic_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from Anthropic API
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not self.anthropic_api_key:
            raise ValueError("Anthropic API key not configured")
        
        # Anthropic doesn't support batch embedding yet, so we need to process one by one
        embeddings = []
        
        async with aiohttp.ClientSession() as session:
            for text in texts:
                # Prepare API request
                headers = {
                    "Content-Type": "application/json",
                    "x-api-key": self.anthropic_api_key,
                    "anthropic-version": "2023-06-01"
                }
                
                data = {
                    "model": self.model,
                    "input": text
                }
                
                # Make API request
                async with session.post(
                    "https://api.anthropic.com/v1/embeddings",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ValueError(f"Anthropic API error ({response.status}): {error_text}")
                    
                    result = await response.json()
                    
                    # Extract embedding
                    embedding = result["embedding"]
                    embeddings.append(embedding)
        
        return embeddings
    
    async def _get_azure_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from Azure OpenAI API
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not self.azure_api_key or not self.azure_api_url:
            raise ValueError("Azure OpenAI API key or URL not configured")
        
        # Prepare API request
        headers = {
            "Content-Type": "application/json",
            "api-key": self.azure_api_key
        }
        
        data = {
            "input": texts,
            "encoding_format": "float"
        }
        
        # Determine API version and endpoint
        api_version = "2023-05-15"
        deployment_name = self.model.replace("-", "")  # Azure needs deployment name without hyphens
        
        # Make API request
        async with aiohttp.ClientSession() as session:
            endpoint = f"{self.azure_api_url}/openai/deployments/{deployment_name}/embeddings?api-version={api_version}"
            
            async with session.post(
                endpoint,
                headers=headers,
                json=data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ValueError(f"Azure OpenAI API error ({response.status}): {error_text}")
                
                result = await response.json()
                
                # Extract embeddings
                embeddings = [item["embedding"] for item in result["data"]]
                return embeddings
    
    def create_mock_embedding(self, text: str, dimension: int = 1536) -> List[float]:
        """Create a mock embedding for testing
        
        Args:
            text: Text to embed
            dimension: Embedding dimension
            
        Returns:
            Mock embedding vector
        """
        # Create a deterministic but unique embedding based on the text
        import hashlib
        
        # Get hash of the text
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Use the hash to seed a random number generator
        import random
        random.seed(text_hash)
        
        # Generate a random vector
        vector = [random.uniform(-1, 1) for _ in range(dimension)]
        
        # Normalize the vector
        norm = sum(x**2 for x in vector) ** 0.5
        normalized_vector = [x / norm for x in vector]
        
        return normalized_vector
