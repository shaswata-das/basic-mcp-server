"""
Embedding Service for MCP Server

This module provides embedding generation for code using various AI models.
"""

import logging
import asyncio
import time
import os
import json
from typing import List, Dict, Any, Optional, Union

from mcp_server.services.secrets_manager import get_secrets_manager

import aiohttp
import numpy as np

class EmbeddingService:
    """Service for generating embeddings from code"""
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        model: str = "nomic-embed-text",  # Default to Ollama model
        batch_size: int = 10,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        azure_api_url: Optional[str] = None,
        azure_api_key: Optional[str] = None,
        azure_deployment_name: Optional[str] = None,
        ollama_url: Optional[str] = "http://localhost:5656",  # Default Ollama URL
        ollama_model: Optional[str] = "nomic-embed-text"  # Default Ollama model
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
            azure_deployment_name: Azure deployment name (optional)
            ollama_url: URL for the Ollama API (e.g., http://localhost:5656)
            ollama_model: Model to use with Ollama (e.g., nomic-embed-text)
        """
        self.logger = logging.getLogger("mcp_server.services.embedding")
        secrets = get_secrets_manager()
        self.openai_api_key = openai_api_key or secrets.get("OPENAI_API_KEY")
        self.anthropic_api_key = anthropic_api_key or secrets.get("ANTHROPIC_API_KEY")
        self.model = model
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.azure_api_url = azure_api_url
        self.azure_api_key = azure_api_key
        self.azure_deployment_name = (
            azure_deployment_name
            or os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
            or model.replace("-", "")
        )
        
        # Ollama configuration
        self.ollama_url = ollama_url or os.environ.get("OLLAMA_URL", "http://localhost:5656")
        self.ollama_model = ollama_model or os.environ.get("OLLAMA_MODEL", "nomic-embed-text")
        
        # Load Azure credentials from environment or secrets if not provided
        if model == "text-embedding-3-large":
            self.azure_api_url = self.azure_api_url or os.environ.get(
                "EMBEDDINGS_3_LARGE_API_URL"
            )
            self.azure_api_key = self.azure_api_key or secrets.get(
                "EMBEDDINGS_3_LARGE_API_KEY"
            )
        elif model == "text-embedding-3-small":
            self.azure_api_url = self.azure_api_url or os.environ.get(
                "EMBEDDINGS_3_SMALL_API_URL"
            )
            self.azure_api_key = self.azure_api_key or secrets.get(
                "EMBEDDINGS_3_SMALL_API_KEY"
            )

        # Always set Ollama as the default provider
        self.provider = "ollama"
        
        # Check if Ollama is available and log appropriate message
        if self._is_ollama_available():
            self.logger.info(f"Using Ollama for embeddings with model {self.ollama_model}")
        else:
            self.logger.warning(f"Ollama not available at {self.ollama_url}, but keeping as provider. Will try to use it during execution or fall back to mock embeddings.")
            
        # Only override the provider if explicitly specified
        if model.startswith("text-embedding-3") and self.azure_api_url and self.azure_api_key and os.environ.get("USE_AZURE_EMBEDDINGS") == "true":
            self.provider = "azure"
            self.logger.info(f"Using Azure OpenAI for embeddings with model {model}")
        elif model.startswith("text-embedding") and self.openai_api_key and os.environ.get("USE_OPENAI_EMBEDDINGS") == "true":
            self.provider = "openai"
            self.logger.info(f"Using OpenAI for embeddings with model {model}")
        elif model.startswith("claude") and self.anthropic_api_key and os.environ.get("USE_ANTHROPIC_EMBEDDINGS") == "true":
            self.provider = "anthropic"
            self.logger.info(f"Using Anthropic for embeddings with model {model}")
            self.logger.info("No valid embedding provider found, using mock embeddings")
            
        self.logger.info(f"Initialized embedding service with {self.provider} provider and model {model}")
    
    def _is_ollama_available(self) -> bool:
        """Check if Ollama is available by making a simple request
        
        Returns:
            True if Ollama is available, False otherwise
        """
        import requests
        try:
            # Check if Ollama is available by making a simple ping request
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if resp.status_code == 200:
                self.logger.info("Ollama is available for embeddings")
                return True
            else:
                self.logger.warning(f"Ollama returned unexpected status: {resp.status_code}")
                return False
        except Exception as e:
            self.logger.warning(f"Ollama check failed: {str(e)}")
            return False
    
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
        # Fallback to mock embeddings if required credentials are missing
        if self.provider == "openai" and not self.openai_api_key:
            self.logger.warning("OpenAI API key missing, falling back to mock embeddings")
            return [self.create_mock_embedding(t) for t in texts]
        if self.provider == "anthropic" and not self.anthropic_api_key:
            self.logger.warning("Anthropic API key missing, falling back to mock embeddings")
            return [self.create_mock_embedding(t) for t in texts]
        if self.provider == "azure" and (not self.azure_api_key or not self.azure_api_url):
            self.logger.warning("Azure OpenAI credentials missing, falling back to mock embeddings")
            return [self.create_mock_embedding(t) for t in texts]

        retries = 0

        while retries <= self.max_retries:
            try:
                if self.provider == "ollama":
                    return await self._get_ollama_embeddings(texts)
                elif self.provider == "openai":
                    return await self._get_openai_embeddings(texts)
                elif self.provider == "anthropic":
                    return await self._get_anthropic_embeddings(texts)
                elif self.provider == "azure":
                    return await self._get_azure_embeddings(texts)
                else:
                    self.logger.warning(f"Unknown provider: {self.provider}, falling back to mock embeddings")
                    return [self.create_mock_embedding(t) for t in texts]
            
            except Exception as e:
                retries += 1
                if retries > self.max_retries:
                    self.logger.error(f"Failed to get embeddings after {self.max_retries} retries: {str(e)}")
                    raise
                
            self.logger.warning(f"Embedding request failed (attempt {retries}/{self.max_retries}): {str(e)}")
            await asyncio.sleep(self.retry_delay * retries)  # Exponential backoff
    
    async def _get_ollama_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from Ollama API
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        self.logger.info(f"Getting embeddings from Ollama using model {self.ollama_model}")
        
        embeddings = []
        
        # Process each text separately to get embeddings
        async with aiohttp.ClientSession() as session:
            for text in texts:
                try:
                    # Prepare the request payload
                    payload = {
                        "model": self.ollama_model,
                        "prompt": text
                    }
                    
                    # Make the request to Ollama embedding endpoint
                    async with session.post(
                        f"{self.ollama_url}/api/embeddings",
                        json=payload,
                        timeout=30
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            self.logger.error(f"Ollama API error: {error_text}")
                            # Fall back to mock embeddings
                            embeddings.append(self.create_mock_embedding(text))
                            continue
                        
                        result = await response.json()
                        
                        # Extract the embedding
                        if "embedding" in result:
                            embeddings.append(result["embedding"])
                        else:
                            self.logger.warning(f"No embedding found in Ollama response: {result}")
                            embeddings.append(self.create_mock_embedding(text))
                
                except Exception as e:
                    self.logger.error(f"Error getting embedding from Ollama: {str(e)}")
                    embeddings.append(self.create_mock_embedding(text))
        
        return embeddings
    
    async def _get_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from OpenAI API
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not self.openai_api_key:
            self.logger.warning(
                "OpenAI API key not configured, using mock embeddings"
            )
            return [self.create_mock_embedding(text) for text in texts]
        
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
            try:
                async with session.post(
                    "https://api.openai.com/v1/embeddings",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ValueError(f"OpenAI API error ({response.status}): {error_text}")

                    result = await response.json()

                    embeddings = [item["embedding"] for item in result["data"]]
                    return embeddings
            except aiohttp.ClientError as e:
                raise ValueError(f"OpenAI request failed: {str(e)}")
    
    async def _get_anthropic_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from Anthropic API
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not self.anthropic_api_key:
            self.logger.warning(
                "Anthropic API key not configured, using mock embeddings"
            )
            return [self.create_mock_embedding(text) for text in texts]
        
        # Anthropic doesn't support batch embedding yet, so we need to process one by one
        embeddings = []
        
        async with aiohttp.ClientSession() as session:
            try:
                for text in texts:
                    headers = {
                        "Content-Type": "application/json",
                        "x-api-key": self.anthropic_api_key,
                        "anthropic-version": "2023-06-01"
                    }

                    data = {
                        "model": self.model,
                        "input": text
                    }

                    async with session.post(
                        "https://api.anthropic.com/v1/embeddings",
                        headers=headers,
                        json=data
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise ValueError(f"Anthropic API error ({response.status}): {error_text}")

                        result = await response.json()

                        embedding = result["embedding"]
                        embeddings.append(embedding)
            except aiohttp.ClientError as e:
                raise ValueError(f"Anthropic request failed: {str(e)}")
        
        return embeddings
    
    async def _get_azure_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from Azure OpenAI API
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not self.azure_api_key or not self.azure_api_url:
            self.logger.warning(
                "Azure OpenAI credentials not configured, using mock embeddings"
            )
            return [self.create_mock_embedding(text) for text in texts]
        
        # Prepare API request
        headers = {
            "Content-Type": "application/json",
            "api-key": self.azure_api_key
        }
        
        data = {
            "input": texts,
            "model": self.model,
            "encoding_format": "float",
        }
        
        # Determine API version and endpoint
        api_version = "2023-05-15"
        deployment_name = self.azure_deployment_name
        
        # Make API request
        async with aiohttp.ClientSession() as session:
            endpoint = f"{self.azure_api_url}/openai/deployments/{deployment_name}/embeddings?api-version={api_version}"
            
            # Log the request for debugging
            self.logger.info(f"Sending Azure embedding request to: {endpoint}")
            self.logger.info(f"Using deployment name: {deployment_name}")

            try:
                async with session.post(
                    endpoint,
                    headers=headers,
                    json=data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"Azure API error: {error_text}")
                        # Fall back to mock embeddings
                        self.logger.warning("Falling back to mock embeddings due to API error")
                        return [self.create_mock_embedding(text) for text in texts]

                    result = await response.json()

                    embeddings = [item["embedding"] for item in result["data"]]
                    return embeddings
            except aiohttp.ClientError as e:
                raise ValueError(f"Azure OpenAI request failed: {str(e)}")
    
    def create_mock_embedding(self, text: str, dimension: int = None) -> List[float]:
        """Create a mock embedding for testing
        
        Args:
            text: Text to embed
            dimension: Embedding dimension (defaults to match provider's dimension)
            
        Returns:
            Mock embedding vector
        """
        # Set dimension based on provider if not specified
        if dimension is None:
            if self.provider == "ollama":
                dimension = 768  # Ollama's default dimension
            else:
                dimension = 1536  # OpenAI's default dimension

        self.logger.info(f"Creating mock embedding with dimension {dimension}")
        
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
