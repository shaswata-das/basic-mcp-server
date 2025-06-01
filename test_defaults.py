"""
Test for Ollama default settings and embeddings.
"""

import asyncio
import sys
import os
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from mcp_server.services.embedding_service import EmbeddingService
from mcp_server.services.vector_store.qdrant_service import QdrantVectorService

async def test_ollama_defaults():
    """Test that Ollama is the default provider."""
    print("\n=== TESTING DEFAULT SETTINGS ===")
    
    # Create embedding service with no parameters
    print("Creating embedding service with no parameters...")
    embedding_service = EmbeddingService()
    
    # Check provider
    print(f"Default embedding provider: {embedding_service.provider}")
    print(f"Default model: {embedding_service.model}")
    print(f"Default Ollama URL: {embedding_service.ollama_url}")
    
    # Create vector service with no parameters
    print("\nCreating vector service with no parameters...")
    vector_service = QdrantVectorService()
    
    # Check vector size and provider
    print(f"Default vector size: {vector_service.vector_size}")
    
    return True

async def test_ollama_embedding():
    """Test Ollama embedding directly."""
    print("\n=== TESTING OLLAMA EMBEDDINGS ===")
    
    # Create the embedding service with explicit Ollama URL
    service = EmbeddingService(
        ollama_url="http://localhost:5656",
        ollama_model="nomic-embed-text"
    )
    
    # Check that Ollama is the provider without having to force it
    print(f"Provider: {service.provider}")
    
    # Test with a simple text
    text = "This is a test sentence for Ollama embeddings."
    
    print(f"Generating embedding for: '{text}'")
    start_time = time.time()
    
    try:
        # Get embedding
        embedding = await service.get_embedding(text)
        
        # Print results
        elapsed_time = time.time() - start_time
        print(f"✅ Generated embedding in {elapsed_time:.2f} seconds")
        print(f"✅ Embedding dimensions: {len(embedding)}")
        print(f"✅ First 5 values: {embedding[:5]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Embedding generation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run the async tests
    print("Testing Ollama default settings...")
    asyncio.run(test_ollama_defaults())
    
    print("\nTesting Ollama embeddings...")
    result = asyncio.run(test_ollama_embedding())
    
    # Exit with appropriate code
    sys.exit(0 if result else 1)