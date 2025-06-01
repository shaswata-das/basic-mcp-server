"""
Configuration for pytest fixtures and utilities.
"""
import os
import sys
import pytest
import asyncio
import shutil
import tempfile
from dotenv import load_dotenv

# Add project root to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

# Configure pytest for asyncio
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Real service fixtures
from mcp_server.services.mongodb_service import MongoDBService
from mcp_server.services.embedding_service import EmbeddingService
from mcp_server.services.vector_store.qdrant_service import QdrantVectorService
from mcp_server.services.knowledge_extraction.code_extractor import CodeExtractor
from mcp_server.services.knowledge_extraction.pattern_extractor import PatternExtractor

@pytest.fixture
async def mongodb_service():
    """Return a real MongoDB service."""
    # Create a unique database name for testing to avoid conflicts
    test_db_name = f"mcp_test_{os.urandom(4).hex()}"
    
    # Create service with real MongoDB at localhost:27017
    service = MongoDBService(uri="mongodb://localhost:27017", db_name=test_db_name)
    
    # Initialize the service
    await service.initialize()
    
    yield service
    
    # Cleanup: Drop the test database after tests
    await service.client.drop_database(test_db_name)

@pytest.fixture
def embedding_service():
    """Return a real embedding service using Ollama."""
    # Use Ollama at the specified port
    service = EmbeddingService(
        model="text-embedding-3-small",  # Fallback model
        ollama_url="http://localhost:5656",
        ollama_model="nomic-embed-text"  # You can change this to any model you have pulled
    )
    
    return service

@pytest.fixture
async def qdrant_service():
    """Return a real Qdrant vector service using in-memory storage."""
    # Use in-memory Qdrant for tests
    service = QdrantVectorService(collection_name=f"test_collection_{os.urandom(4).hex()}")
    
    # Initialize the service
    await service.initialize()
    
    yield service
    
    # Cleanup: Delete the test collection
    try:
        await service.clear_collection()
    except:
        pass

@pytest.fixture
def code_extractor():
    """Return a real code extractor service."""
    return CodeExtractor()

@pytest.fixture
def pattern_extractor():
    """Return a real pattern extractor service."""
    return PatternExtractor()

# Test data fixtures
@pytest.fixture
def test_code_file():
    """Return a sample code file for testing."""
    return """
class TestClass:
    def __init__(self, value):
        self.value = value
        
    def get_value(self):
        return self.value
    
    def set_value(self, new_value):
        self.value = new_value
"""

@pytest.fixture
def test_repository_path():
    """Create a temporary repository structure for testing."""
    repo_dir = tempfile.mkdtemp()
    
    # Create directory structure
    os.makedirs(os.path.join(repo_dir, "src", "controllers"), exist_ok=True)
    os.makedirs(os.path.join(repo_dir, "src", "models"), exist_ok=True)
    os.makedirs(os.path.join(repo_dir, "src", "views"), exist_ok=True)
    
    # Create Python file
    with open(os.path.join(repo_dir, "src", "models", "test_model.py"), "w") as f:
        f.write("""
class TestModel:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        
    def to_dict(self):
        return {"id": self.id, "name": self.name}
""")
    
    # Create a controller file
    with open(os.path.join(repo_dir, "src", "controllers", "test_controller.py"), "w") as f:
        f.write("""
from src.models.test_model import TestModel

class TestController:
    def __init__(self):
        self.models = {}
        
    def get_model(self, id):
        return self.models.get(id)
        
    def create_model(self, id, name):
        model = TestModel(id, name)
        self.models[id] = model
        return model
""")
    
    yield repo_dir
    
    # Clean up
    shutil.rmtree(repo_dir)
