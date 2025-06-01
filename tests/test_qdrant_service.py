"""
Tests for the Qdrant vector service.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock

from mcp_server.services.vector_store.qdrant_service import QdrantVectorService

class TestQdrantVectorService:
    
    def test_init(self):
        """Test initialization of Qdrant vector service."""
        # Test with URL
        service = QdrantVectorService(
            url="http://localhost:6333",
            api_key="test-key",
            collection_name="test-collection",
            vector_size=384,
            distance="cosine"
        )
        
        assert service.collection_name == "test-collection"
        # Default provider is ollama which uses 768 dimensions regardless of input
        assert service.vector_size == 768
        
        # Test without URL (in-memory)
        service = QdrantVectorService()
        assert service.vector_size == 768  # Default for Ollama embeddings
    
    @pytest.mark.asyncio
    @patch('qdrant_client.QdrantClient')
    async def test_initialize(self, mock_client):
        """Test initializing the Qdrant service and creating collection."""
        # Setup mocks
        client_instance = MagicMock()
        mock_client.return_value = client_instance
        
        # Mock get_collections
        collection = MagicMock()
        collection.name = "other-collection"
        client_instance.get_collections.return_value = MagicMock(collections=[collection])
        
        # Create service
        service = QdrantVectorService(collection_name="test-collection", vector_size=384)
        service.client = client_instance
        
        # Initialize
        result = await service.initialize()
        
        # Verify
        assert result is True
        client_instance.create_collection.assert_called_once()
        
        # Test when collection already exists
        client_instance.reset_mock()
        collection.name = "test-collection"
        result = await service.initialize()
        
        # Verify collection not created again
        assert result is True
        client_instance.create_collection.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('qdrant_client.QdrantClient')
    async def test_store_code_chunk(self, mock_client):
        """Test storing a code chunk with embedding."""
        # Setup mocks
        client_instance = MagicMock()
        mock_client.return_value = client_instance
        
        # Create service
        service = QdrantVectorService(collection_name="test-collection", vector_size=384)
        service.client = client_instance
        
        # Store code chunk
        chunk_id = await service.store_code_chunk(
            embedding=[0.1] * 768,  # Test embedding
            code_text="def test_function():\n    return 'test'",
            metadata={
                "file_path": "test.py",
                "language": "python",
                "repo_id": "test-repo"
            }
        )
        
        # Verify
        assert isinstance(chunk_id, str)
        client_instance.upsert.assert_called_once()
        
        # Test with custom ID
        client_instance.reset_mock()
        custom_id = "custom-id"
        chunk_id = await service.store_code_chunk(
            embedding=[0.1] * 768,
            code_text="test code",
            metadata={"file_path": "test.py"},
            chunk_id=custom_id
        )
        
        # Verify custom ID was used
        assert chunk_id == custom_id
        client_instance.upsert.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('qdrant_client.QdrantClient')
    async def test_search_similar_code(self, mock_client):
        """Test searching for similar code chunks."""
        # Setup mocks
        client_instance = MagicMock()
        mock_client.return_value = client_instance
        
        # Mock search results
        scored_point1 = MagicMock()
        scored_point1.id = "id1"
        scored_point1.score = 0.95
        scored_point1.payload = {
            "code_text": "def function1(): pass",
            "file_path": "file1.py",
            "language": "python"
        }
        
        scored_point2 = MagicMock()
        scored_point2.id = "id2"
        scored_point2.score = 0.85
        scored_point2.payload = {
            "code_text": "def function2(): pass",
            "file_path": "file2.py",
            "language": "python"
        }
        
        client_instance.search.return_value = [scored_point1, scored_point2]
        
        # Create service
        service = QdrantVectorService(collection_name="test-collection", vector_size=384)
        service.client = client_instance
        
        # Search for similar code
        results = await service.search_similar_code(
            query_embedding=[0.1] * 768,
            filter_params={"language": "python", "repo_id": "test-repo"},
            limit=5
        )
        
        # Verify
        assert len(results) == 2
        assert results[0]["id"] == "id1"
        assert results[0]["score"] == 0.95
        assert results[0]["code_text"] == "def function1(): pass"
        assert results[0]["file_path"] == "file1.py"
        assert results[0]["language"] == "python"
        
        assert results[1]["id"] == "id2"
        assert results[1]["score"] == 0.85
        
        # Verify search was called with correct parameters
        client_instance.search.assert_called_once()
        call_args = client_instance.search.call_args
        assert call_args[1]["collection_name"] == "test-collection"
        assert call_args[1]["query_vector"] == [0.1] * 768
        assert call_args[1]["limit"] == 5
        # Filter should have been passed
        assert call_args[1]["query_filter"] is not None
    
    @pytest.mark.asyncio
    @patch('qdrant_client.QdrantClient')
    async def test_delete_by_filter(self, mock_client):
        """Test deleting points matching a filter."""
        # Setup mocks
        client_instance = MagicMock()
        mock_client.return_value = client_instance
        
        # Mock delete result
        delete_result = MagicMock()
        delete_result.status = "ok"
        client_instance.delete.return_value = delete_result
        
        # Create service
        service = QdrantVectorService(collection_name="test-collection", vector_size=384)
        service.client = client_instance
        
        # Delete by filter
        result = await service.delete_by_filter(
            filter_params={"repo_id": "test-repo", "language": "python"}
        )
        
        # Verify
        assert result == "ok"
        client_instance.delete.assert_called_once()
        
        # Ensure the filter was built properly
        call_args = client_instance.delete.call_args
        assert call_args[1]["collection_name"] == "test-collection"
        assert "points_selector" in call_args[1]
    
    @pytest.mark.asyncio
    @patch('qdrant_client.QdrantClient')
    async def test_build_filter(self, mock_client):
        """Test building a Qdrant filter from parameters."""
        # Create service
        service = QdrantVectorService()
        
        # Test single value filter
        filter_params = {"language": "python"}
        filter_obj = service._build_filter(filter_params)
        
        # Verify
        assert len(filter_obj.must) == 1
        assert filter_obj.must[0].key == "language"
        
        # Test multiple values filter
        filter_params = {
            "language": "python",
            "repo_id": "test-repo",
            "tags": ["tag1", "tag2"]
        }
        filter_obj = service._build_filter(filter_params)
        
        # Verify
        assert len(filter_obj.must) == 3
        # The tags field should use MatchAny for multiple values
        tags_condition = [c for c in filter_obj.must if c.key == "tags"][0]
        assert hasattr(tags_condition.match, "any")
        assert tags_condition.match.any == ["tag1", "tag2"]