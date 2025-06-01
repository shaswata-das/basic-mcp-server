#!/usr/bin/env python
"""
Full integration test for basic-mcp-server
"""

import os
import sys
import time
import asyncio
import tempfile
import shutil
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Constants
MONGODB_URI = "mongodb://localhost:27017"
OLLAMA_URL = "http://localhost:5656"
OLLAMA_MODEL = "nomic-embed-text"
TEST_REPO_PATH = "C:\\workstation\\orbitax-platform-api-fork"

# Import all services
try:
    from mcp_server.services.embedding_service import EmbeddingService
    from mcp_server.services.mongodb_service import MongoDBService
    from mcp_server.services.vector_store.qdrant_service import QdrantVectorService
    from mcp_server.handlers.ai_development_handlers import CodebaseAnalysisHandler
    
    print("✅ Successfully imported all required services")
    
    async def test_ollama_embeddings():
        """Test Ollama embeddings"""
        print("\n=== TESTING OLLAMA EMBEDDINGS ===")
        
        service = EmbeddingService(
            ollama_url=OLLAMA_URL,
            ollama_model=OLLAMA_MODEL
        )
        
        # Force provider to be Ollama
        service.provider = "ollama"
        
        # Check if Ollama is available
        is_available = service._is_ollama_available()
        print(f"Ollama available: {is_available}")
        
        if not is_available:
            print("⚠️ Ollama is not available, skipping embedding tests")
            return False
        
        # Generate embedding
        text = "This is a test sentence for embedding."
        print(f"Generating embedding for: '{text}'")
        
        start_time = time.time()
        embedding = await service.get_embedding(text)
        elapsed_time = time.time() - start_time
        
        print(f"✅ Generated embedding in {elapsed_time:.2f} seconds")
        print(f"✅ Embedding dimensions: {len(embedding)}")
        print(f"✅ First 5 values: {embedding[:5]}")
        
        # Now try a batch
        print("\nTrying batch embeddings...")
        texts = ["First test", "Second test", "Third test"]
        
        start_time = time.time()
        embeddings = await service.get_embeddings(texts)
        elapsed_time = time.time() - start_time
        
        print(f"✅ Generated {len(embeddings)} embeddings in {elapsed_time:.2f} seconds")
        print(f"✅ All have same dimensions: {all(len(e) == len(embedding) for e in embeddings)}")
        
        return True
    
    async def test_mongodb():
        """Test MongoDB connection"""
        print("\n=== TESTING MONGODB CONNECTION ===")
        
        # Create test database name
        test_db_name = f"mcp_test_{int(time.time())}"
        print(f"Using test database: {test_db_name}")
        
        # Create MongoDB service
        mongodb_service = MongoDBService(uri=MONGODB_URI, db_name=test_db_name)
        
        try:
            # Initialize
            print("Initializing MongoDB...")
            initialized = await mongodb_service.initialize()
            
            if not initialized:
                print("⚠️ MongoDB initialization failed")
                return False
                
            print("✅ MongoDB initialized successfully")
            
            # Check collections
            collections = await mongodb_service.db.list_collection_names()
            print(f"✅ Created collections: {', '.join(collections)}")
            
            # Create test repository
            repo_id = await mongodb_service.store_repository(
                name="test-integration-repo",
                path="/path/to/test",
                metadata={"test": True}
            )
            
            print(f"✅ Created test repository with ID: {repo_id}")
            
            # Clean up
            print("Cleaning up test database...")
            await mongodb_service.client.drop_database(test_db_name)
            print("✅ Test database cleaned up")
            
            return True
            
        except Exception as e:
            print(f"❌ MongoDB test failed: {str(e)}")
            
            # Try to clean up
            try:
                await mongodb_service.client.drop_database(test_db_name)
            except:
                pass
                
            return False
    
    async def test_codebase_analysis():
        """Test codebase analysis"""
        print(f"\n=== TESTING CODEBASE ANALYSIS ===")
        print(f"Repository path: {TEST_REPO_PATH}")
        
        if not os.path.exists(TEST_REPO_PATH):
            print(f"⚠️ Repository path {TEST_REPO_PATH} does not exist")
            return False
        
        # Create temporary output directory
        output_dir = tempfile.mkdtemp()
        print(f"Output directory: {output_dir}")
        
        try:
            # Create services
            mongodb_service = MongoDBService(uri=MONGODB_URI, db_name=f"mcp_test_{int(time.time())}")
            embedding_service = EmbeddingService(
                ollama_url=OLLAMA_URL,
                ollama_model=OLLAMA_MODEL
            )
            vector_service = QdrantVectorService()
            
            # Initialize services
            await mongodb_service.initialize()
            await vector_service.initialize()
            
            # Create handler
            handler = CodebaseAnalysisHandler(
                mongodb_service=mongodb_service,
                embedding_service=embedding_service,
                vector_service=vector_service
            )
            
            # Run analysis with limited scope
            print("Starting analysis with 30 file limit...")
            start_time = time.time()
            
            result = await handler.handle({
                "repo_path": TEST_REPO_PATH,
                "repo_name": "orbitax-platform-api-fork",
                "exclude_patterns": [
                    "*/bin/*",
                    "*/obj/*",
                    "*/node_modules/*",
                    "*.min.js"
                ],
                "file_limit": 30,  # Limit to 30 files for quicker testing
                "output_dir": output_dir
            })
            
            elapsed_time = time.time() - start_time
            
            print(f"✅ Analysis completed in {elapsed_time:.2f} seconds")
            print(f"✅ Repository ID: {result.get('repo_id')}")
            print(f"✅ Files analyzed: {result.get('file_count')}")
            
            # Check documentation
            docs_dir = os.path.join(output_dir, "docs")
            if os.path.exists(docs_dir):
                print("✅ Documentation generated successfully")
                
                # List key documentation files
                readme_path = os.path.join(docs_dir, "README.md")
                if os.path.exists(readme_path):
                    print("✅ README.md generated")
                
                structure_dir = os.path.join(docs_dir, "structure")
                if os.path.exists(structure_dir):
                    structure_files = os.listdir(structure_dir)
                    print(f"✅ Structure documentation: {len(structure_files)} files")
            
            # Clean up
            print("Cleaning up...")
            await mongodb_service.client.drop_database(mongodb_service.db_name)
            shutil.rmtree(output_dir)
            print("✅ Cleanup completed")
            
            return True
            
        except Exception as e:
            print(f"❌ Codebase analysis failed: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Try to clean up
            try:
                shutil.rmtree(output_dir)
            except:
                pass
                
            return False
    
    async def run_all_tests():
        """Run all integration tests"""
        print(f"=== STARTING INTEGRATION TESTS AT {datetime.now().strftime('%H:%M:%S')} ===\n")
        start_time = time.time()
        
        # Run tests
        ollama_ok = await test_ollama_embeddings()
        mongodb_ok = await test_mongodb()
        analysis_ok = await test_codebase_analysis()
        
        # Print summary
        elapsed_time = time.time() - start_time
        print(f"\n=== TEST SUMMARY (completed in {elapsed_time:.2f} seconds) ===")
        print(f"Ollama embeddings: {'✅ PASSED' if ollama_ok else '❌ FAILED'}")
        print(f"MongoDB connection: {'✅ PASSED' if mongodb_ok else '❌ FAILED'}")
        print(f"Codebase analysis: {'✅ PASSED' if analysis_ok else '❌ FAILED'}")
        
        all_passed = ollama_ok and mongodb_ok and analysis_ok
        print(f"\nOverall result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
        
        return all_passed
    
    if __name__ == "__main__":
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
        
except ImportError as e:
    print(f"Import error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()