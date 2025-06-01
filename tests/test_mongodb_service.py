"""
Tests for the MongoDB service.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from mcp_server.services.mongodb_service import MongoDBService

class TestMongoDBService:
    
    @pytest.mark.asyncio
    @patch('motor.motor_asyncio.AsyncIOMotorClient')
    async def test_initialize(self, mock_motor_client):
        """Test initializing the MongoDB service and creating indexes."""
        # Setup mocks
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_motor_client.return_value = mock_client
        
        # Mock collections
        mock_repos = MagicMock()
        mock_code_files = MagicMock()
        mock_classes = MagicMock()
        mock_components = MagicMock()
        mock_relationships = MagicMock()
        mock_chunks = MagicMock()
        
        # Set up the collections dict
        mock_db.__getitem__.side_effect = {
            "repositories": mock_repos,
            "code_files": mock_code_files,
            "classes": mock_classes,
            "components": mock_components,
            "relationships": mock_relationships,
            "chunks": mock_chunks
        }.__getitem__
        
        # Set up successful index creation
        mock_repos.create_index = AsyncMock(return_value=None)
        mock_code_files.create_index = AsyncMock(return_value=None)
        mock_classes.create_index = AsyncMock(return_value=None)
        mock_components.create_index = AsyncMock(return_value=None)
        mock_relationships.create_index = AsyncMock(return_value=None)
        mock_chunks.create_index = AsyncMock(return_value=None)
        
        # Create service
        service = MongoDBService(uri="mongodb://localhost:27017", db_name="test-db")
        
        # Initialize
        result = await service.initialize()
        
        # Verify
        assert result is True
        mock_motor_client.assert_called_once_with("mongodb://localhost:27017")
        
        # Verify index creation was called
        assert mock_repos.create_index.called
        assert mock_code_files.create_index.called
        assert mock_classes.create_index.called
        assert mock_components.create_index.called
        assert mock_relationships.create_index.called
        assert mock_chunks.create_index.called
    
    @pytest.mark.asyncio
    @patch('motor.motor_asyncio.AsyncIOMotorClient')
    async def test_initialize_error_handling(self, mock_motor_client):
        """Test error handling during initialization."""
        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_motor_client.return_value = mock_client
        
        # Mock repos collection to raise exception on create_index
        mock_repos = MagicMock()
        mock_repos.create_index = AsyncMock(side_effect=Exception("Test error"))
        mock_db.__getitem__.return_value = mock_repos
        
        # Create service
        service = MongoDBService(uri="mongodb://localhost:27017", db_name="test-db")
        
        # Initialize should handle the exception and return False
        result = await service.initialize()
        assert result is False
    
    @pytest.mark.asyncio
    @patch('motor.motor_asyncio.AsyncIOMotorClient')
    async def test_store_repository(self, mock_motor_client):
        """Test storing repository information."""
        # Setup mocks
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_motor_client.return_value = mock_client
        
        # Mock repos collection
        mock_repos = MagicMock()
        mock_repos.update_one = AsyncMock(return_value=None)
        mock_db.__getitem__.return_value = mock_repos
        
        # Create service
        service = MongoDBService(uri="mongodb://localhost:27017", db_name="test-db")
        service.repos = mock_repos
        
        # Store repository
        repo_id = await service.store_repository(
            name="test-repo",
            path="/path/to/repo",
            metadata={"key": "value"},
            repo_id="test-id"
        )
        
        # Verify
        assert repo_id == "test-id"
        mock_repos.update_one.assert_called_once()
        
        # Call with generated ID
        with patch('uuid.uuid4', return_value="generated-id"):
            repo_id = await service.store_repository(
                name="test-repo",
                path="/path/to/repo"
            )
            assert repo_id == "generated-id"
    
    @pytest.mark.asyncio
    @patch('motor.motor_asyncio.AsyncIOMotorClient')
    async def test_store_code_file(self, mock_motor_client):
        """Test storing code file information."""
        # Setup mocks
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_motor_client.return_value = mock_client
        
        # Mock code_files collection
        mock_code_files = MagicMock()
        mock_code_files.update_one = AsyncMock(return_value=None)
        mock_db.__getitem__.return_value = mock_code_files
        
        # Create service
        service = MongoDBService(uri="mongodb://localhost:27017", db_name="test-db")
        service.code_files = mock_code_files
        
        # Store code file
        file_id = await service.store_code_file(
            repo_id="test-repo",
            path="file.py",
            language="python",
            content="# Test code",
            metadata={"key": "value"},
            file_id="test-file-id"
        )
        
        # Verify
        assert file_id == "test-file-id"
        mock_code_files.update_one.assert_called_once()
        
        # Call with generated ID
        with patch('uuid.uuid4', return_value="generated-file-id"):
            file_id = await service.store_code_file(
                repo_id="test-repo",
                path="file.py",
                language="python",
                content="# Test code"
            )
            assert file_id == "generated-file-id"
    
    @pytest.mark.asyncio
    @patch('motor.motor_asyncio.AsyncIOMotorClient')
    async def test_store_relationship(self, mock_motor_client):
        """Test storing relationship between entities."""
        # Setup mocks
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_motor_client.return_value = mock_client
        
        # Mock relationships collection
        mock_relationships = MagicMock()
        mock_relationships.insert_one = AsyncMock(return_value=None)
        mock_db.__getitem__.return_value = mock_relationships
        
        # Create service
        service = MongoDBService(uri="mongodb://localhost:27017", db_name="test-db")
        service.relationships = mock_relationships
        
        # Store relationship
        with patch('uuid.uuid4', return_value="rel-id"):
            rel_id = await service.store_relationship(
                source_id="source-id",
                target_id="target-id",
                relationship_type="inheritance",
                metadata={"key": "value"}
            )
            
            # Verify
            assert rel_id == "rel-id"
            mock_relationships.insert_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_code_files(self):
        """Test searching code files by content."""
        # Mock results data
        mock_results = [
            {"file_id": "file1", "path": "file1.py", "language": "python"},
            {"file_id": "file2", "path": "file2.py", "language": "python"}
        ]
        
        # Create a service with a patched search_code_files method
        with patch('mcp_server.services.mongodb_service.MongoDBService.search_code_files', 
                  new_callable=AsyncMock, return_value=mock_results):
            
            service = MongoDBService(uri="mongodb://localhost:27017", db_name="test-db")
            
            # Call the patched method
            results = await service.search_code_files(
                query="test query",
                repo_id="test-repo",
                language="python",
                limit=10
            )
            
            # Verify the results
            assert len(results) == 2
            assert results[0]["file_id"] == "file1"
            assert results[1]["file_id"] == "file2"