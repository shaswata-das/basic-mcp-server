"""
Run Enhanced Knowledge Extraction directly without starting the server

This script uses the AI Development handlers to extract knowledge from a codebase,
generate documentation, and store knowledge in MongoDB and vector database.
"""

import argparse
import asyncio
import os
import logging
import datetime
import json
import time

from mcp_server.services.mongodb_service import MongoDBService
from mcp_server.services.embedding_service import EmbeddingService
from mcp_server.services.vector_store.qdrant_service import QdrantVectorService
from mcp_server.handlers.ai_development_handlers import CodebaseAnalysisHandler


async def analyze_repository(repo_path, output_dir, file_limit=1000):
    """
    Analyze a repository and extract knowledge using enhanced AI development handlers
    
    Args:
        repo_path: Path to the repository
        output_dir: Path to save output
        file_limit: Maximum number of files to analyze
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create services
    mongodb_service = MongoDBService(uri="mongodb://localhost:27017", db_name="mcp-server")
    embedding_service = EmbeddingService(model="text-embedding-3-small")
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    vector_service = QdrantVectorService(url=qdrant_url, api_key=qdrant_api_key)
    
    # Create handler
    codebase_analyzer = CodebaseAnalysisHandler(
        mongodb_service=mongodb_service,
        embedding_service=embedding_service,
        vector_service=vector_service
    )
    
    # Create directory for output if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Starting enhanced analysis of {repo_path}...")
    start_time = time.time()
    
    # Run the analysis
    try:
        result = await codebase_analyzer.handle({
            "repo_path": repo_path,
            "repo_name": os.path.basename(repo_path),
            "exclude_patterns": [
                "*/bin/*",
                "*/obj/*",
                "*/node_modules/*",
                "*/dist/*",
                "*/packages/*",
                "*.min.js",
                "*.min.css"
            ],
            "file_limit": file_limit,
            "output_dir": output_dir
        })
        
        # Save result to file
        with open(os.path.join(output_dir, "analysis_result.json"), "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        
        print(f"Analysis completed in {time.time() - start_time:.2f} seconds")
        print(f"Analyzed {result.get('file_count', 0)} files")
        print(f"Found patterns: {result.get('patterns_found', {})}")
        print(f"Documentation saved to {result.get('documentation_dir')}")
        
        return result.get("repo_id")
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def search_code(repo_id, query, search_type="all", limit=10):
    """
    Search code using the semantic search capabilities
    
    Args:
        repo_id: Repository ID
        query: Search query
        search_type: Type of search ("all", "code", "documentation")
        limit: Maximum number of results
    """
    # Create services
    mongodb_service = MongoDBService(uri="mongodb://localhost:27017", db_name="mcp-server")
    embedding_service = EmbeddingService(model="text-embedding-3-small")
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    vector_service = QdrantVectorService(url=qdrant_url, api_key=qdrant_api_key)
    
    # Create handler
    code_search = CodeSearchHandler(
        mongodb_service=mongodb_service,
        embedding_service=embedding_service,
        vector_service=vector_service
    )
    
    print(f"Searching for: {query}")
    
    # Run the search
    try:
        results = await code_search.handle({
            "repo_id": repo_id,
            "query": query,
            "search_type": search_type,
            "limit": limit
        })
        
        print(f"Found {results.get('results_count', 0)} results:")
        
        for i, result in enumerate(results.get("results", [])):
            print(f"\n[{i+1}] Score: {result.get('score', 0):.2f}")
            print(f"Type: {result.get('type')}")
            
            if result.get("type") == "file":
                print(f"File: {result.get('file_path')}")
                print(f"Language: {result.get('code_language')}")
                print(f"Namespace: {result.get('namespace')}")
            else:
                print(f"Title: {result.get('title')}")
                print(f"Category: {result.get('category')}")
            
            print(f"Preview: {result.get('content_preview')}")
        
        return results
        
    except Exception as e:
        print(f"Error during search: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Analyze a repository and build documentation")
    parser.add_argument("--repo-path", "--repo", dest="repo_path", default=os.environ.get("REPO_PATH"),
                        help="Path to the repository to analyze")
    parser.add_argument("--output-dir", "--output", dest="output_dir",
                        default=os.environ.get("OUTPUT_DIR", os.path.join(os.path.dirname(__file__), "analysis_output")),
                        help="Directory to store analysis results")
    parser.add_argument("--file-limit", dest="file_limit", type=int,
                        default=int(os.environ.get("FILE_LIMIT", 500)),
                        help="Maximum number of files to analyze")

    args = parser.parse_args()

    repo_path = args.repo_path
    if not repo_path:
        parser.error("Repository path must be provided via --repo-path or REPO_PATH environment variable")

    output_dir = args.output_dir
    file_limit = args.file_limit
    
    # Run analysis
    print(f"=== ANALYZING REPOSITORY: {repo_path} ===")
    repo_id = await analyze_repository(repo_path, output_dir, file_limit)
    
    if repo_id:
        print(f"\n=== REPOSITORY ANALYSIS COMPLETE ===")
        print(f"Repository ID: {repo_id}")
        
        # Wait a moment to make sure vector database is ready
        await asyncio.sleep(2)
        
        # Run some example searches
        print(f"\n=== SEARCHING FOR PATTERNS ===")
        await search_code(repo_id, "What design patterns are used in this codebase?", "documentation")
        
        print(f"\n=== SEARCHING FOR KEY CLASSES ===")
        await search_code(repo_id, "Find main controller classes", "code")
        
        print(f"\n=== SEARCHING FOR ARCHITECTURE ===")
        await search_code(repo_id, "Explain the architecture of this system", "documentation")


# Add import for search handler if needed
from mcp_server.handlers.ai_development_handlers import CodeSearchHandler

if __name__ == "__main__":
    asyncio.run(main())
