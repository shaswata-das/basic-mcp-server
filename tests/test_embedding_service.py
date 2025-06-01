"""
Tests for the embedding service with Ollama support.
"""
import pytest
import asyncio
import aiohttp
from unittest.mock import patch, MagicMock, AsyncMock

from mcp_server.services.embedding_service import EmbeddingService

class TestEmbeddingService:
    
    def test_init_with_ollama(self):
        """Test initialization with Ollama configuration."""
        service = EmbeddingService(
            ollama_url="http://test-ollama:5656",
            ollama_model="test-model"
        )
        
        assert service.ollama_url == "http://test-ollama:5656"
        assert service.ollama_model == "test-model"
    
    @pytest.mark.asyncio
    @patch('mcp_server.services.embedding_service.EmbeddingService._is_ollama_available')
    @patch('aiohttp.ClientSession')
    async def test_ollama_embeddings(self, mock_session, mock_is_ollama):
        """Test getting embeddings from Ollama."""
        # Setup mocks
        mock_is_ollama.return_value = True
        
        # Mock the aiohttp response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"embedding": [0.1] * 384}
        
        # Mock the session
        mock_context = MagicMock()
        mock_context.__aenter__.return_value = mock_response
        mock_session_instance = MagicMock()
        mock_session_instance.post.return_value = mock_context
        mock_session.return_value = mock_session_instance
        
        # Create service
        service = EmbeddingService(
            ollama_url="http://localhost:5656",
            ollama_model="nomic-embed-text"
        )
        service.provider = "ollama"  # Force provider to ollama
        
        # Test get_embedding
        embedding = await service.get_embedding("Test text")
        
        # Verify the embedding
        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert embedding[0] == 0.1
        
        # Verify the correct API was called
        mock_session_instance.post.assert_called_once_with(
            "http://localhost:5656/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": "Test text"},
            timeout=30
        )
    
    @pytest.mark.asyncio
    async def test_fallback_to_mock(self):
        """Test fallback to mock embeddings when no provider is available."""
        # Create service with no valid provider
        service = EmbeddingService(
            model="test-model",  # Unknown model
            openai_api_key=None,
            anthropic_api_key=None,
            azure_api_url=None,
            azure_api_key=None
        )
        
        # Ensure ollama is not available
        service._is_ollama_available = lambda: False
        service.provider = "mock"
        
        # Test get_embedding
        embedding = await service.get_embedding("Test text")
        
        # Verify it's a mock embedding
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        
        # Test batch embeddings
        embeddings = await service.get_embeddings(["Text 1", "Text 2", "Text 3"])
        
        # Verify batch embeddings
        assert len(embeddings) == 3
        assert all(isinstance(emb, list) for emb in embeddings)
        assert all(len(emb) > 0 for emb in embeddings)
    
    @pytest.mark.asyncio
    @patch('requests.get')
    async def test_ollama_availability_check(self, mock_requests_get):
        """Test the Ollama availability check."""
        # Test when Ollama is available
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests_get.return_value = mock_response
        
        service = EmbeddingService(
            ollama_url="http://localhost:5656",
            ollama_model="nomic-embed-text"
        )
        
        assert service._is_ollama_available() is True
        
        # Test when Ollama returns error
        mock_response.status_code = 500
        assert service._is_ollama_available() is False
        
        # Test when Ollama is unreachable
        mock_requests_get.side_effect = Exception("Connection error")
        assert service._is_ollama_available() is False
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_embedding_error_handling(self, mock_session):
        """Test error handling in embedding generation."""
        # Mock session to raise an exception
        mock_context = MagicMock()
        mock_context.__aenter__.side_effect = aiohttp.ClientError("Connection error")
        mock_session_instance = MagicMock()
        mock_session_instance.post.return_value = mock_context
        mock_session.return_value = mock_session_instance
        
        # Create service
        service = EmbeddingService(ollama_url="http://localhost:5656")
        service.provider = "ollama"
        service._is_ollama_available = lambda: True
        
        # Test get_embedding with error
        embedding = await service._get_ollama_embeddings(["Test text"])
        
        # Should fall back to mock embedding
        assert len(embedding) == 1
        assert isinstance(embedding[0], list)

    @pytest.mark.asyncio
    async def test_create_mock_embedding(self):
        """Test creation of mock embeddings."""
        service = EmbeddingService()
        
        # Create a mock embedding
        embedding = service.create_mock_embedding("Test text")
        
        # Verify properties
        assert isinstance(embedding, list)
        assert len(embedding) == 1536  # Default dimension
        
        # Test with different dimension
        embedding = service.create_mock_embedding("Test text", dimension=384)
        assert len(embedding) == 384
        
        # Test deterministic behavior (same text should give same embedding)
        embedding1 = service.create_mock_embedding("Same text")
        embedding2 = service.create_mock_embedding("Same text")
        assert embedding1 == embedding2
        
        # Different text should give different embedding
        embedding3 = service.create_mock_embedding("Different text")
        assert embedding1 != embedding3
