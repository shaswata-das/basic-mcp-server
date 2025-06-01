"""
Tests for the AI Development Handlers.
"""
import pytest
import os
import tempfile
import shutil
import asyncio
import uuid
from unittest.mock import patch, MagicMock, AsyncMock

from mcp_server.handlers.ai_development_handlers import (
    CodebaseAnalysisHandler,
    CodeSearchHandler,
    KnowledgeGraphQueryHandler
)

class TestCodebaseAnalysisHandler:
    
    @pytest.fixture
    def mock_services(self):
        """Set up mock services for testing."""
        mongodb_service = MagicMock()
        mongodb_service.initialize = AsyncMock(return_value=True)
        mongodb_service.repos = MagicMock()
        mongodb_service.repos.update_one = AsyncMock(return_value=None)
        mongodb_service.code_files = MagicMock()
        mongodb_service.code_files.update_one = AsyncMock(return_value=None)
        
        embedding_service = MagicMock()
        embedding_service.get_embedding = AsyncMock(return_value=[0.1] * 384)
        
        vector_service = MagicMock()
        vector_service.initialize = AsyncMock(return_value=True)
        vector_service.store_code_chunk = AsyncMock(return_value="test-id")
        
        code_extractor = MagicMock()
        code_extractor.extract_knowledge_from_file = AsyncMock(return_value={
            "language": "python",
            "file_path": "test.py",
            "classes": [{"name": "TestClass", "methods": []}],
            "functions": [{"name": "test_function"}],
            "imports": ["os", "sys"]
        })
        
        pattern_extractor = MagicMock()
        pattern_extractor.extract_patterns = AsyncMock(return_value={
            "design_patterns": [{"name": "Factory", "confidence": 0.8, "sources": ["test.py"]}],
            "architectural_patterns": [{"name": "MVC", "confidence": 0.7, "sources": ["app/"]}],
            "code_organization": [{"name": "Layer-based Organization", "confidence": 0.9, "sources": ["folder_structure"]}]
        })
        
        md_builder = MagicMock()
        md_builder.generate_documentation = AsyncMock(return_value={
            "docs_dir": "/path/to/docs",
            "readme_path": "/path/to/docs/README.md",
            "sections": ["structure", "patterns", "architecture"]
        })
        
        return {
            "mongodb_service": mongodb_service,
            "embedding_service": embedding_service,
            "vector_service": vector_service,
            "code_extractor": code_extractor,
            "pattern_extractor": pattern_extractor,
            "md_builder": md_builder
        }
    
    @pytest.fixture
    def test_repo_dir(self):
        """Create a temporary repository for testing."""
        repo_dir = tempfile.mkdtemp()
        
        # Create some test files
        os.makedirs(os.path.join(repo_dir, "app", "controllers"), exist_ok=True)
        os.makedirs(os.path.join(repo_dir, "app", "models"), exist_ok=True)
        os.makedirs(os.path.join(repo_dir, "app", "views"), exist_ok=True)
        
        # Create Python file
        with open(os.path.join(repo_dir, "app", "controllers", "test_controller.py"), "w") as f:
            f.write("""
class TestController:
    def index(self):
        return "Hello, World!"
""")
        
        # Create output directory
        output_dir = os.path.join(repo_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        yield repo_dir, output_dir
        
        # Clean up
        shutil.rmtree(repo_dir)
    
    @pytest.mark.asyncio
    async def test_codebase_analysis_handler(self, mock_services, test_repo_dir):
        """Test the CodebaseAnalysisHandler."""
        repo_dir, output_dir = test_repo_dir
        
        # Patch the handler's services
        with patch('mcp_server.handlers.ai_development_handlers.CodeExtractor', return_value=mock_services["code_extractor"]), \
             patch('mcp_server.handlers.ai_development_handlers.PatternExtractor', return_value=mock_services["pattern_extractor"]), \
             patch('mcp_server.handlers.ai_development_handlers.MarkdownBuilder', return_value=mock_services["md_builder"]), \
             patch('uuid.uuid4', return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            
            # Create handler
            handler = CodebaseAnalysisHandler(
                mongodb_service=mock_services["mongodb_service"],
                embedding_service=mock_services["embedding_service"],
                vector_service=mock_services["vector_service"]
            )
            
            # Handle request
            result = await handler.handle({
                "repo_path": repo_dir,
                "repo_name": "test-repo",
                "exclude_patterns": ["node_modules/*", "*.min.js"],
                "file_limit": 10,
                "output_dir": output_dir,
                "skip_embeddings": True  # Skip embeddings for testing
            })
            
            # Verify result
            assert result["status"] == "success"
            assert result["repo_id"] == "12345678-1234-5678-1234-567812345678"
            assert result["repo_name"] == "test-repo"
            assert result["output_dir"] == output_dir
            assert "patterns_found" in result
            assert "documentation_dir" in result
            
            # Verify MongoDB was initialized
            mock_services["mongodb_service"].initialize.assert_called_once()
            
            # Verify repo was stored
            mock_services["mongodb_service"].repos.update_one.assert_called_once()
            
            # Verify pattern extractor was called
            mock_services["pattern_extractor"].extract_patterns.assert_called_once()
            
            # Verify MD builder was called
            mock_services["md_builder"].generate_documentation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_mongodb_error(self, mock_services, test_repo_dir):
        """Test handling MongoDB initialization error."""
        repo_dir, output_dir = test_repo_dir
        
        # Make MongoDB initialization fail
        mock_services["mongodb_service"].initialize.return_value = False
        
        # Patch the handler's services
        with patch('mcp_server.handlers.ai_development_handlers.CodeExtractor', return_value=mock_services["code_extractor"]), \
             patch('mcp_server.handlers.ai_development_handlers.PatternExtractor', return_value=mock_services["pattern_extractor"]), \
             patch('mcp_server.handlers.ai_development_handlers.MarkdownBuilder', return_value=mock_services["md_builder"]):
            
            # Create handler
            handler = CodebaseAnalysisHandler(
                mongodb_service=mock_services["mongodb_service"],
                embedding_service=mock_services["embedding_service"],
                vector_service=mock_services["vector_service"]
            )
            
            # Handle request - should still work even if MongoDB fails
            result = await handler.handle({
                "repo_path": repo_dir,
                "repo_name": "test-repo",
                "exclude_patterns": [],
                "file_limit": 10,
                "output_dir": output_dir,
                "skip_embeddings": True
            })
            
            # Verify result
            assert result["status"] == "success"
            assert "repo_id" in result
            
            # Should still try to generate documentation
            mock_services["md_builder"].generate_documentation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_missing_repo_path(self, mock_services):
        """Test handling missing repository path."""
        # Create handler
        handler = CodebaseAnalysisHandler(
            mongodb_service=mock_services["mongodb_service"],
            embedding_service=mock_services["embedding_service"],
            vector_service=mock_services["vector_service"]
        )
        
        # Handle request with missing repo_path
        with pytest.raises(ValueError, match="Repository path is required"):
            await handler.handle({
                "repo_name": "test-repo",
                "exclude_patterns": [],
                "file_limit": 10
            })
    
    @pytest.mark.asyncio
    async def test_handle_nonexistent_repo_path(self, mock_services):
        """Test handling nonexistent repository path."""
        # Create handler
        handler = CodebaseAnalysisHandler(
            mongodb_service=mock_services["mongodb_service"],
            embedding_service=mock_services["embedding_service"],
            vector_service=mock_services["vector_service"]
        )
        
        # Handle request with nonexistent repo_path
        with pytest.raises(ValueError, match="Repository path does not exist"):
            await handler.handle({
                "repo_path": "/nonexistent/path",
                "repo_name": "test-repo",
                "exclude_patterns": [],
                "file_limit": 10
            })


class TestCodeSearchHandler:
    
    @pytest.fixture
    def mock_services(self):
        """Set up mock services for testing."""
        mongodb_service = MagicMock()
        mongodb_service.initialize = AsyncMock(return_value=True)
        
        embedding_service = MagicMock()
        embedding_service.get_embedding = AsyncMock(return_value=[0.1] * 384)
        
        vector_service = MagicMock()
        vector_service.initialize = AsyncMock(return_value=True)
        vector_service.search_similar_code = AsyncMock(return_value=[
            {
                "id": "id1",
                "score": 0.95,
                "code_text": "def test_function(): pass",
                "file_path": "file1.py",
                "type": "file",
                "language": "python",
                "namespace": "test_namespace"
            },
            {
                "id": "id2",
                "score": 0.85,
                "code_text": "class TestClass: pass",
                "file_path": "file2.py",
                "type": "file",
                "language": "python",
                "namespace": "test_namespace"
            }
        ])
        
        return {
            "mongodb_service": mongodb_service,
            "embedding_service": embedding_service,
            "vector_service": vector_service
        }
    
    @pytest.mark.asyncio
    async def test_code_search_handler(self, mock_services):
        """Test the CodeSearchHandler."""
        # Create handler
        handler = CodeSearchHandler(
            mongodb_service=mock_services["mongodb_service"],
            embedding_service=mock_services["embedding_service"],
            vector_service=mock_services["vector_service"]
        )
        
        # Handle request
        result = await handler.handle({
            "repo_id": "test-repo-id",
            "query": "test query",
            "search_type": "code",
            "language": "python",
            "limit": 5
        })
        
        # Verify result
        assert result["repo_id"] == "test-repo-id"
        assert result["query"] == "test query"
        assert result["results_count"] == 2
        assert len(result["results"]) == 2
        
        # Check first result
        assert result["results"][0]["score"] == 0.95
        assert result["results"][0]["type"] == "file"
        assert result["results"][0]["file_path"] == "file1.py"
        assert result["results"][0]["language"] == "python"
        assert "content_preview" in result["results"][0]
        
        # Verify services were called correctly
        mock_services["vector_service"].initialize.assert_called_once()
        mock_services["embedding_service"].get_embedding.assert_called_once_with("test query")
        mock_services["vector_service"].search_similar_code.assert_called_once()
        
        # Verify search parameters
        call_args = mock_services["vector_service"].search_similar_code.call_args[1]
        assert call_args["filter_params"]["repo_id"] == "test-repo-id"
        assert call_args["filter_params"]["type"] == "file"
        assert call_args["filter_params"]["language"] == "python"
        assert call_args["limit"] == 5
    
    @pytest.mark.asyncio
    async def test_code_search_documentation(self, mock_services):
        """Test searching for documentation."""
        # Override the search result for documentation
        mock_services["vector_service"].search_similar_code = AsyncMock(return_value=[
            {
                "id": "doc1",
                "score": 0.95,
                "code_text": "# Design Patterns\n\nThis document describes the design patterns used in the project.",
                "file_path": "docs/patterns.md",
                "type": "documentation",
                "category": "patterns",
                "title": "Design Patterns"
            }
        ])
        
        # Create handler
        handler = CodeSearchHandler(
            mongodb_service=mock_services["mongodb_service"],
            embedding_service=mock_services["embedding_service"],
            vector_service=mock_services["vector_service"]
        )
        
        # Handle request
        result = await handler.handle({
            "repo_id": "test-repo-id",
            "query": "design patterns",
            "search_type": "documentation",
            "limit": 5
        })
        
        # Verify result
        assert result["results_count"] == 1
        assert result["results"][0]["type"] == "documentation"
        assert result["results"][0]["title"] == "Design Patterns"
        assert result["results"][0]["category"] == "patterns"
        
        # Verify filter parameters
        call_args = mock_services["vector_service"].search_similar_code.call_args[1]
        assert call_args["filter_params"]["type"] == "documentation"
    
    @pytest.mark.asyncio
    async def test_code_search_error_handling(self, mock_services):
        """Test error handling in code search."""
        # Create handler
        handler = CodeSearchHandler(
            mongodb_service=mock_services["mongodb_service"],
            embedding_service=mock_services["embedding_service"],
            vector_service=mock_services["vector_service"]
        )
        
        # Test missing repo_id
        with pytest.raises(ValueError, match="Repository ID is required"):
            await handler.handle({
                "query": "test query"
            })
        
        # Test missing query
        with pytest.raises(ValueError, match="Search query is required"):
            await handler.handle({
                "repo_id": "test-repo-id"
            })


class TestKnowledgeGraphQueryHandler:
    
    @pytest.fixture
    def mock_mongodb_service(self):
        """Set up mock MongoDB service for testing."""
        service = MagicMock()
        service.initialize = AsyncMock(return_value=True)
        
        # Mock repository information
        service.get_repository = AsyncMock(return_value={
            "repo_id": "test-repo-id",
            "name": "test-repo",
            "metadata": {
                "knowledge": {
                    "patterns": {
                        "design_patterns": [
                            {"name": "Factory", "confidence": 0.8, "sources": ["src/factories/UserFactory.java"]}
                        ],
                        "architectural_patterns": [
                            {"name": "MVC", "confidence": 0.7, "sources": ["app/"]}
                        ],
                        "code_organization": [
                            {"name": "Layer-based Organization", "confidence": 0.9, "sources": ["folder_structure"]}
                        ]
                    },
                    "environment": {
                        "package_managers": ["npm"],
                        "build_systems": ["webpack"],
                        "frameworks": ["react"]
                    }
                }
            }
        })
        
        # Mock component query
        service.find_one = AsyncMock(return_value={
            "file_id": "file1",
            "path": "src/components/UserComponent.jsx",
            "language": "javascript",
            "metadata": {
                "classes": [
                    {
                        "name": "UserComponent",
                        "methods": [
                            {"name": "render", "params": [], "return_type": "JSX.Element"}
                        ],
                        "properties": [
                            {"name": "state", "type": "object"}
                        ]
                    }
                ],
                "namespace": "components"
            }
        })
        
        # Mock file count
        service.count = AsyncMock(return_value=120)
        
        return service
    
    @pytest.mark.asyncio
    async def test_general_query(self, mock_mongodb_service):
        """Test general knowledge graph query."""
        # Create handler
        handler = KnowledgeGraphQueryHandler(
            mongodb_service=mock_mongodb_service
        )
        
        # Handle request
        result = await handler.handle({
            "repo_id": "test-repo-id",
            "query_type": "general"
        })
        
        # Verify result
        assert result["status"] == "success"
        assert result["repo_id"] == "test-repo-id"
        assert result["repo_name"] == "test-repo"
        assert result["file_count"] == 120
        
        # Check patterns
        assert "Factory" in result["patterns"]["design_patterns"]
        assert "MVC" in result["patterns"]["architectural_patterns"]
        assert "Layer-based Organization" in result["patterns"]["code_organization"]
        
        # Check environment
        assert "npm" in result["environment"]["package_managers"]
        assert "webpack" in result["environment"]["build_systems"]
        assert "react" in result["environment"]["frameworks"]
        
        # Verify services were called correctly
        mock_mongodb_service.initialize.assert_called_once()
        mock_mongodb_service.get_repository.assert_called_once_with("test-repo-id")
        mock_mongodb_service.count.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_component_query(self, mock_mongodb_service):
        """Test component-specific knowledge graph query."""
        # Create handler
        handler = KnowledgeGraphQueryHandler(
            mongodb_service=mock_mongodb_service
        )
        
        # Handle request
        result = await handler.handle({
            "repo_id": "test-repo-id",
            "query_type": "component",
            "component_name": "UserComponent"
        })
        
        # Verify result
        assert result["status"] == "success"
        assert result["component_name"] == "UserComponent"
        assert len(result["matches"]) > 0
        
        # Check component info
        component = result["matches"][0]
        assert component["name"] == "UserComponent"
        assert component["file_path"] == "src/components/UserComponent.jsx"
        assert component["language"] == "javascript"
        assert component["namespace"] == "components"
        assert len(component["methods"]) > 0
        assert "render" in [m["name"] for m in component["methods"]]
        
        # Verify services were called correctly
        mock_mongodb_service.get_repository.assert_called_once_with("test-repo-id")
        mock_mongodb_service.find_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_pattern_query(self, mock_mongodb_service):
        """Test pattern-specific knowledge graph query."""
        # Create handler
        handler = KnowledgeGraphQueryHandler(
            mongodb_service=mock_mongodb_service
        )
        
        # Handle request
        result = await handler.handle({
            "repo_id": "test-repo-id",
            "query_type": "pattern",
            "pattern_name": "Factory"
        })
        
        # Verify result
        assert result["status"] == "success"
        assert result["pattern_name"] == "Factory"
        assert result["pattern_info"]["name"] == "Factory"
        assert result["pattern_info"]["confidence"] == 0.8
        assert "src/factories/UserFactory.java" in result["pattern_info"]["sources"]
        
        # Verify services were called correctly
        mock_mongodb_service.get_repository.assert_called_once_with("test-repo-id")
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_mongodb_service):
        """Test error handling in knowledge graph query."""
        # Create handler
        handler = KnowledgeGraphQueryHandler(
            mongodb_service=mock_mongodb_service
        )
        
        # Test missing repo_id
        with pytest.raises(ValueError, match="Repository ID is required"):
            await handler.handle({
                "query_type": "general"
            })
        
        # Test component not found
        mock_mongodb_service.find_one.return_value = None
        result = await handler.handle({
            "repo_id": "test-repo-id",
            "query_type": "component",
            "component_name": "NonExistentComponent"
        })
        assert result["status"] == "not_found"
        
        # Test pattern not found
        result = await handler.handle({
            "repo_id": "test-repo-id",
            "query_type": "pattern",
            "pattern_name": "NonExistentPattern"
        })
        assert result["status"] == "not_found"
