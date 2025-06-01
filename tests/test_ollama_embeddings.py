"""
Integration tests for Ollama embeddings.
"""
import pytest
import asyncio
import os

from mcp_server.services.embedding_service import EmbeddingService

@pytest.mark.asyncio
async def test_ollama_real_embeddings():
    """Test getting real embeddings from Ollama."""
    # Create embedding service with Ollama configuration
    service = EmbeddingService(
        ollama_url="http://localhost:5656",
        ollama_model="nomic-embed-text"
    )
    
    # Force the provider to be Ollama
    service.provider = "ollama"
    
    # Test with a simple text
    text = "This is a test for Ollama embeddings."
    
    try:
        # Get embedding
        embedding = await service.get_embedding(text)
        
        # Verify embedding
        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) > 0  # Should have some dimensions
        
        # Test batch embeddings
        texts = [
            "First test text for Ollama embeddings.",
            "Second test text for Ollama embeddings.",
            "Third test text for Ollama embeddings."
        ]
        
        # Get batch embeddings
        embeddings = await service.get_embeddings(texts)
        
        # Verify batch embeddings
        assert len(embeddings) == 3
        assert all(isinstance(emb, list) for emb in embeddings)
        assert all(len(emb) > 0 for emb in embeddings)
        
        print(f"✅ Successfully generated embeddings using Ollama at {service.ollama_url}")
        print(f"✅ Embedding dimensions: {len(embedding)}")
        
    except Exception as e:
        print(f"❌ Failed to get embeddings from Ollama: {str(e)}")
        
        # Check if Ollama is available
        if not service._is_ollama_available():
            pytest.skip(f"Ollama is not available at {service.ollama_url}. Skipping test.")
        else:
            raise

if __name__ == "__main__":
    # This allows running this test file directly
    asyncio.run(test_ollama_real_embeddings())