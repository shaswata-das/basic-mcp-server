"""
AI Development Handlers for MCP Server

This module provides handlers for AI-assisted development capabilities.
It integrates knowledge extraction, documentation generation, and vector storage
for semantic search, allowing AIs to better understand and work with codebases.
"""

import os
import json
import logging
import asyncio
import datetime
import uuid
import time
from typing import Dict, List, Any, Optional, Tuple

from mcp_server.core.server import HandlerInterface
from mcp_server.services.embedding_service import EmbeddingService
from mcp_server.services.vector_store.qdrant_service import QdrantVectorService
from mcp_server.services.mongodb_service import MongoDBService
from mcp_server.services.knowledge_extraction.code_extractor import CodeExtractor
from mcp_server.services.knowledge_extraction.call_graph_analyzer import CallGraphAnalyzer
from mcp_server.services.knowledge_extraction.pattern_extractor import PatternExtractor
from mcp_server.services.knowledge_extraction.environment_analyzer import EnvironmentAnalyzer
from mcp_server.services.knowledge_extraction.md_builder import MarkdownBuilder


class CodebaseAnalysisHandler(HandlerInterface):
    """Handler for codebase/analyze method which extracts and stores knowledge for AI development"""
    
    def __init__(
        self,
        mongodb_service: MongoDBService,
        embedding_service: EmbeddingService,
        vector_service: QdrantVectorService,
        ai_service = None
    ):
        """Initialize with required services
        
        Args:
            mongodb_service: MongoDB service for storing knowledge
            embedding_service: Embedding service for generating embeddings
            vector_service: Vector store service for semantic search
            ai_service: Optional AI service for additional analysis
        """
        self.mongodb_service = mongodb_service
        self.embedding_service = embedding_service
        self.vector_service = vector_service
        self.ai_service = ai_service
        
        # Initialize extraction services
        self.code_extractor = CodeExtractor()
        self.call_graph_analyzer = CallGraphAnalyzer()
        self.pattern_extractor = PatternExtractor()
        self.environment_analyzer = EnvironmentAnalyzer()
        self.md_builder = MarkdownBuilder()
        
        self.logger = logging.getLogger("mcp_server.handlers.codebase_analysis")
    
    def _save_intermediate_results(
        self,
        file_count: int,
        file_results: List[Dict],
        output_dir: str,
        error_files: List[Dict]
    ) -> None:
        """Save intermediate results to allow for recovery in case of failure
        
        Args:
            file_count: Number of files processed
            file_results: Results of file processing
            output_dir: Directory to save intermediate results
            error_files: Files that failed to process
        """
        try:
            # Create a checkpoint directory if it doesn't exist
            checkpoint_dir = os.path.join(output_dir, "checkpoints")
            os.makedirs(checkpoint_dir, exist_ok=True)
            
            # Save checkpoint with timestamp
            timestamp = int(time.time())
            checkpoint_file = os.path.join(checkpoint_dir, f"checkpoint_{file_count}_{timestamp}.json")
            
            # Create a summary of results (don't save full content to keep file size reasonable)
            summary = {
                "file_count": file_count,
                "timestamp": timestamp,
                "files": [
                    {
                        "file_path": item["file_path"],
                        "code_language": item["code_language"],
                        "file_id": item.get("file_id", ""),
                        "class_count": len(item["result"].get("classes", [])),
                        "interface_count": len(item["result"].get("interfaces", [])),
                        "namespace": item["result"].get("namespace", "Unknown")
                    }
                    for item in file_results[-100:]  # Only save the last 100 files for efficiency
                ],
                "errors": error_files[-100:]
            }
            
            with open(checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
                
            self.logger.info(f"Saved checkpoint at {file_count} files")
        except Exception as e:
            self.logger.warning(f"Failed to save checkpoint: {str(e)}")
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle codebase analysis request
        
        Args:
            params: Request parameters
            
        Returns:
            Analysis results
        """
        # Extract parameters
        repo_path = params.get("repo_path")
        repo_name = params.get("repo_name") or os.path.basename(repo_path)
        exclude_patterns = params.get("exclude_patterns", [])
        file_limit = params.get("file_limit", 1000)  # Limit number of files to analyze
        output_dir = params.get("output_dir")
        
        # If output_dir not specified, create one in the repo
        if not output_dir:
            output_dir = os.path.join(repo_path, "ai_knowledge")
        
        # Validate parameters
        if not repo_path:
            raise ValueError("Repository path is required")
        
        if not os.path.exists(repo_path):
            raise ValueError(f"Repository path does not exist: {repo_path}")
        
        self.logger.info(f"Starting codebase analysis for repository: {repo_path}")
        
        # Initialize MongoDB
        try:
            await self.mongodb_service.initialize()
            
            # Store repository info
            repo_id = str(uuid.uuid4())  # Generate a UUID for the repository
            try:
                # Use MongoDB's native methods for storing data
                await self.mongodb_service.repos.update_one(
                    {"repo_id": repo_id},
                    {"$set": {
                        "repo_id": repo_id,
                        "name": repo_name,
                        "path": repo_path,
                        "metadata": {
                            "analysis_type": "ai_development"
                        },
                        "created_at": datetime.datetime.now()
                    }},
                    upsert=True
                )
                self.logger.info(f"Repository registered with ID: {repo_id}")
            except Exception as e:
                self.logger.warning(f"Could not store repository in MongoDB: {str(e)}")
        except Exception as e:
            self.logger.warning(f"Could not initialize MongoDB: {str(e)}")
            repo_id = str(uuid.uuid4())  # Still use a UUID even if MongoDB fails
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Analyze environment first
        self.logger.info("Analyzing environment and dependencies...")
        env_results = await self.environment_analyzer.analyze_environment(repo_path)
        
        # Save environment results
        with open(os.path.join(output_dir, "environment.json"), "w", encoding="utf-8") as f:
            json.dump(env_results, f, indent=2)
        
        # Extract code patterns
        self.logger.info("Extracting development patterns...")
        pattern_results = await self.pattern_extractor.extract_patterns(repo_path, [])
        
        # Save pattern results
        with open(os.path.join(output_dir, "patterns.json"), "w", encoding="utf-8") as f:
            json.dump(pattern_results, f, indent=2)
        
        # Extract code content
        self.logger.info("Extracting code content...")
        file_results = []
        error_files = []
        file_count = 0
        
        # Check for existing checkpoint to resume processing
        resume_from_checkpoint = params.get("resume_from_checkpoint", False)
        processed_files = set()
        
        if resume_from_checkpoint:
            checkpoint_dir = os.path.join(output_dir, "checkpoints")
            if os.path.exists(checkpoint_dir):
                # Find the latest checkpoint
                checkpoint_files = [f for f in os.listdir(checkpoint_dir) if f.startswith("checkpoint_")]
                if checkpoint_files:
                    latest_checkpoint = sorted(checkpoint_files)[-1]
                    checkpoint_path = os.path.join(checkpoint_dir, latest_checkpoint)
                    
                    try:
                        with open(checkpoint_path, "r", encoding="utf-8") as f:
                            checkpoint_data = json.load(f)
                            
                        # Get processed files from checkpoint
                        for file_info in checkpoint_data.get("files", []):
                            processed_files.add(file_info.get("file_path", ""))

                        for error in checkpoint_data.get("errors", []):
                            processed_files.add(error.get("file_path", ""))
                            
                        file_count = checkpoint_data.get("file_count", 0)
                        self.logger.info(f"Resuming from checkpoint with {file_count} files already processed")
                    except Exception as e:
                        self.logger.warning(f"Failed to load checkpoint: {str(e)}")
        
        # Create list of files to process
        all_files_to_process = []
        
        # Find all supported code files
        supported_extensions = [".cs", ".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".hpp"]
        for root, _, files in os.walk(repo_path):
            # Skip excluded directories
            if any(exclude in root for exclude in exclude_patterns):
                continue
                
            for file in files:
                # Skip excluded files
                if any(exclude in file for exclude in exclude_patterns):
                    continue
                    
                # Check if file extension is supported
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext not in supported_extensions:
                    continue
                
                file_path = os.path.join(root, file)
                
                # Skip already processed files if resuming
                if resume_from_checkpoint and file_path in processed_files:
                    continue
                    
                # Skip very large files
                try:
                    if os.path.getsize(file_path) > 1024 * 1024:  # Skip files larger than 1MB
                        continue
                    
                    # Determine file language
                    language = self._determine_language(file_ext)
                    
                    if language:
                        all_files_to_process.append((file_path, language))
                except Exception as e:
                    self.logger.warning(f"Error checking file {file_path}: {str(e)}")
        
        # Process files in batches for better memory management
        self.logger.info(f"Found {len(all_files_to_process)} files to process")
        batch_size = 100  # Process files in batches of 100
        
        for i in range(0, len(all_files_to_process), batch_size):
            batch = all_files_to_process[i:i+batch_size]
            self.logger.info(f"Processing batch {i//batch_size + 1}/{(len(all_files_to_process) + batch_size - 1)//batch_size}")
            
            for file_path, language in batch:

                # Extract knowledge from file
                try:
                    result = await self.code_extractor.extract_knowledge_from_file(file_path, language)

                    # Store in MongoDB
                    try:
                        # Create a sanitized version of metadata for MongoDB
                        # This prevents issues with unsupported language overrides
                        sanitized_metadata = {}
                        for key, value in result.items():
                            sanitized_metadata[key] = value
                        
                        # Use direct MongoDB collection access
                        file_id = str(uuid.uuid4())
                        await self.mongodb_service.code_files.update_one(
                            {"repo_id": repo_id, "path": os.path.relpath(file_path, repo_path)},
                            {"$set": {
                                "file_id": file_id,
                                "repo_id": repo_id,
                                "path": os.path.relpath(file_path, repo_path),
                                "code_language": effective_language,
                                "size": os.path.getsize(file_path),
                                "metadata": sanitized_metadata,
                                "updated_at": datetime.datetime.now()
                            }},
                            upsert=True
                        )
                    except Exception as mongo_err:
                        self.logger.warning(f"MongoDB error for file {file_path}: {str(mongo_err)}")
                        file_id = str(uuid.uuid4())  # Generate ID even if storage fails
                    
                    # Add to results
                    file_results.append({
                        "file_path": file_path,
                        "code_language": language,
                        "result": result,
                        "file_id": file_id
                    })
                    
                    file_count += 1
                    
                    # Log progress periodically
                    if file_count % 50 == 0:
                        self.logger.info(f"Processed {file_count} files...")
                        # Save intermediate results to allow for recovery
                        self._save_intermediate_results(file_count, file_results, output_dir, error_files)
                    
                    # Check file limit
                    if file_count >= file_limit:
                        self.logger.info(f"Reached file limit of {file_limit} files")
                        break
                
                except Exception as e:
                    self.logger.warning(f"Error processing file {file_path}: {str(e)}")
                    error_files.append({"file_path": file_path, "error": str(e)})
                    # Continue processing other files despite errors
            
            # Check file limit
            if file_count >= file_limit:
                break
        
        # Save code extraction results
        with open(os.path.join(output_dir, "code_content.json"), "w", encoding="utf-8") as f:
            # We don't save the full results to avoid large files
            summary = {
                "file_count": file_count,
                "languages": list(set(item["code_language"] for item in file_results if "code_language" in item)),
                "files": [
                    {
                        "file_path": item["file_path"],
                        "code_language": item["code_language"],
                        "class_count": len(item["result"].get("classes", [])),
                        "interface_count": len(item["result"].get("interfaces", [])),
                        "namespace": item["result"].get("namespace", "Unknown")
                    }
                    for item in file_results
                ]
            }
            json.dump(summary, f, indent=2)

        # Save final checkpoint
        self._save_intermediate_results(file_count, file_results, output_dir, error_files)
        
        # Build knowledge structure
        knowledge = {
            "repo_id": repo_id,
            "repo_name": repo_name,
            "file_count": file_count,
            "patterns": pattern_results,
            "environment": env_results,
            "files": [item["result"] for item in file_results]
        }
        
        # Generate Markdown documentation
        self.logger.info("Generating documentation...")
        docs_result = await self.md_builder.generate_documentation(
            repo_id=repo_id,
            extracted_knowledge=knowledge,
            output_dir=output_dir
        )
        
        # Store vector embeddings if services are available
        if self.embedding_service and self.vector_service:
            self.logger.info("Storing vector embeddings for semantic search...")
            await self._store_embeddings(repo_id, knowledge, output_dir)
        
        return {
            "status": "success",
            "repo_id": repo_id,
            "repo_name": repo_name,
            "file_count": file_count,
            "output_dir": output_dir,
            "patterns_found": {
                "design_patterns": len(pattern_results.get("design_patterns", [])),
                "architectural_patterns": len(pattern_results.get("architectural_patterns", [])),
                "code_organization": len(pattern_results.get("code_organization", []))
            },
            "documentation_dir": os.path.join(output_dir, "docs")
        }
    
    def _determine_language(self, file_extension: str) -> str:
        """Determine the programming language from file extension
        
        Args:
            file_extension: File extension including the dot
            
        Returns:
            Language name
        """
        extension_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".cs": "csharp",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".go": "go",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".rs": "rust",
            ".sql": "sql",
            ".sh": "shell",
            ".ps1": "powershell",
            ".bat": "batch",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".xml": "xml",
            ".md": "markdown"
        }
        
        return extension_map.get(file_extension.lower(), "unknown")
    
    async def _store_embeddings(
        self, 
        repo_id: str, 
        knowledge: Dict[str, Any],
        output_dir: str
    ) -> None:
        """Store vector embeddings for semantic search
        
        Args:
            repo_id: Repository ID
            knowledge: Extracted knowledge
            output_dir: Output directory
        """
        # Initialize vector service
        await self.vector_service.initialize()
        
        # Create collection for this repository
        collection_name = f"repo_{repo_id}_knowledge"
        
        # Determine vector size based on embedding model
        vector_size = 1536  # Default for OpenAI embeddings
        if hasattr(self.embedding_service, "model") and self.embedding_service.model == "text-embedding-3-large":
            vector_size = 3072
        
        # Set the collection name for the vector service and initialize
        self.vector_service.collection_name = collection_name
        self.vector_service.vector_size = vector_size
        await self.vector_service.initialize()
        
        # Store embeddings for documentation pages
        docs_dir = os.path.join(output_dir, "docs")
        if os.path.exists(docs_dir):
            # Store main README
            readme_path = os.path.join(docs_dir, "README.md")
            if os.path.exists(readme_path):
                with open(readme_path, "r", encoding="utf-8") as f:
                    readme_content = f.read()
                
                # Generate embedding
                readme_embedding = await self.embedding_service.get_embedding(readme_content)
                
                # Store in vector database
                await self.vector_service.store_code_chunk(
                    embedding=readme_embedding,
                    code_text=readme_content,
                    metadata={
                        "repo_id": repo_id,
                        "type": "documentation",
                        "title": "Repository Overview",
                        "path": "docs/README.md"
                    }
                )
            
            # Store structure documentation
            structure_dir = os.path.join(docs_dir, "structure")
            if os.path.exists(structure_dir):
                for file_name in os.listdir(structure_dir):
                    if file_name.endswith(".md"):
                        file_path = os.path.join(structure_dir, file_name)
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        
                        # Generate embedding
                        embedding = await self.embedding_service.get_embedding(content)
                        
                        # Determine title
                        title = "Code Structure"
                        if file_name != "README.md":
                            title = f"Structure: {os.path.splitext(file_name)[0]}"
                        
                        # Store in vector database
                        await self.vector_service.store_code_chunk(
                            embedding=embedding,
                            code_text=content,
                            metadata={
                                "repo_id": repo_id,
                                "type": "documentation",
                                "category": "structure",
                                "title": title,
                                "path": f"docs/structure/{file_name}"
                            }
                        )
            
            # Store pattern documentation
            patterns_dir = os.path.join(docs_dir, "patterns")
            if os.path.exists(patterns_dir):
                for file_name in os.listdir(patterns_dir):
                    if file_name.endswith(".md"):
                        file_path = os.path.join(patterns_dir, file_name)
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        
                        # Generate embedding
                        embedding = await self.embedding_service.get_embedding(content)
                        
                        # Store in vector database
                        await self.vector_service.store_code_chunk(
                            embedding=embedding,
                            code_text=content,
                            metadata={
                                "repo_id": repo_id,
                                "type": "documentation",
                                "category": "patterns",
                                "title": "Design and Architecture Patterns",
                                "path": f"docs/patterns/{file_name}"
                            }
                        )
        
        # Store embeddings for code files
        for file_info in knowledge.get("files", [])[:100]:  # Limit to 100 files for performance
            file_path = file_info.get("file_path")
            if not file_path:
                continue
                
            language = file_info.get("code_language", "unknown")
            namespace = file_info.get("namespace", "unknown")
            
            # Create text representation for embedding
            file_text = f"""
File: {file_path}
Language: {language}
Namespace: {namespace}

Classes:
{self._format_classes_for_embedding(file_info.get("classes", []))}

Interfaces:
{self._format_interfaces_for_embedding(file_info.get("interfaces", []))}
"""
            
            # Generate embedding
            embedding = await self.embedding_service.get_embedding(file_text)
            
            # Store in vector database
            file_id = f"{repo_id}:{file_path}"
            # Use the correct method from QdrantVectorService
            await self.vector_service.store_code_chunk(
                embedding=embedding,
                code_text=file_text,
                metadata={
                    "id": file_id,
                    "file_path": file_path,
                    "code_language": language,
                    "namespace": namespace,
                    "type": "file",
                    "repo_id": repo_id
                },
                chunk_id=file_id
            )
    
    def _format_classes_for_embedding(self, classes: List[Dict[str, Any]]) -> str:
        """Format classes for embedding
        
        Args:
            classes: List of class information
            
        Returns:
            Formatted string
        """
        if not classes:
            return "No classes found."
        
        result = ""
        for cls in classes:
            result += f"- {cls.get('name')}: {len(cls.get('methods', []))} methods, {len(cls.get('properties', []))} properties\n"
        
        return result
    
    def _format_interfaces_for_embedding(self, interfaces: List[Dict[str, Any]]) -> str:
        """Format interfaces for embedding
        
        Args:
            interfaces: List of interface information
            
        Returns:
            Formatted string
        """
        if not interfaces:
            return "No interfaces found."
        
        result = ""
        for interface in interfaces:
            result += f"- {interface.get('name')}\n"
        
        return result


class CodeSearchHandler(HandlerInterface):
    """Handler for code/search method which enables semantic search for AI development"""
    
    def __init__(
        self,
        mongodb_service: MongoDBService,
        embedding_service: EmbeddingService,
        vector_service: QdrantVectorService
    ):
        """Initialize with required services
        
        Args:
            mongodb_service: MongoDB service for retrieving analysis results
            embedding_service: Embedding service for generating embeddings
            vector_service: Vector store service for semantic search
        """
        self.mongodb_service = mongodb_service
        self.embedding_service = embedding_service
        self.vector_service = vector_service
        self.logger = logging.getLogger("mcp_server.handlers.code_search")
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code search request
        
        Args:
            params: Request parameters
            
        Returns:
            Search results
        """
        # Extract parameters
        repo_id = params.get("repo_id")
        query = params.get("query")
        search_type = params.get("search_type", "all")  # "all", "code", "documentation"
        language = params.get("language")  # Optional language filter
        limit = params.get("limit", 10)
        
        # Validate parameters
        if not repo_id:
            raise ValueError("Repository ID is required")
        
        if not query:
            raise ValueError("Search query is required")
        
        self.logger.info(f"Searching repository {repo_id} for: {query}")
        
        # Initialize vector service
        await self.vector_service.initialize()
        
        # Generate embedding for the query
        embedding = await self.embedding_service.get_embedding(query)
        
        # Prepare search filter
        filter_params = {"repo_id": repo_id}
        
        if search_type == "code":
            filter_params["type"] = "file"
        elif search_type == "documentation":
            filter_params["type"] = "documentation"
        
        if language:
            filter_params["code_language"] = language
        
        # Search vector database
        collection_name = f"repo_{repo_id}_knowledge"
        search_results = await self.vector_service.search_similar_code(
            query_embedding=embedding,
            filter_params=filter_params,
            limit=limit
        )
        
        # Format results
        results = []
        for result in search_results:
            item = {
                "score": result.get("score", 0),
                "type": result.get("type", "unknown"),
                "file_path": result.get("file_path", ""),
                "title": result.get("title", ""),
                "code_language": result.get("code_language", ""),
                "namespace": result.get("namespace", ""),
                "category": result.get("category", ""),
                "content_preview": self._create_content_preview(result.get("code_text", ""))
            }
            
            results.append(item)
        
        return {
            "repo_id": repo_id,
            "query": query,
            "results_count": len(results),
            "results": results
        }
    
    def _create_content_preview(self, content: str, max_length: int = 200) -> str:
        """Create a preview of content
        
        Args:
            content: Content to preview
            max_length: Maximum length of preview
            
        Returns:
            Content preview
        """
        if not content:
            return ""
        
        # Remove extra whitespace
        content = " ".join(content.split())
        
        if len(content) <= max_length:
            return content
        
        return content[:max_length] + "..."


class KnowledgeGraphQueryHandler(HandlerInterface):
    """Handler for knowledge/query method which provides knowledge graph query capabilities"""
    
    def __init__(
        self,
        mongodb_service: MongoDBService,
        ai_service = None
    ):
        """Initialize with required services
        
        Args:
            mongodb_service: MongoDB service for retrieving knowledge
            ai_service: Optional AI service for generating responses
        """
        self.mongodb_service = mongodb_service
        self.ai_service = ai_service
        self.logger = logging.getLogger("mcp_server.handlers.knowledge_graph_query")
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle knowledge graph query request
        
        Args:
            params: Request parameters
            
        Returns:
            Query results
        """
        # Extract parameters
        repo_id = params.get("repo_id")
        query_type = params.get("query_type", "general")  # "general", "component", "pattern"
        component_name = params.get("component_name")  # For component queries
        pattern_name = params.get("pattern_name")  # For pattern queries
        
        # Validate parameters
        if not repo_id:
            raise ValueError("Repository ID is required")
        
        self.logger.info(f"Querying knowledge graph for repository {repo_id}")
        
        # Initialize MongoDB
        await self.mongodb_service.initialize()
        
        # Get repository info
        repo_info = await self.mongodb_service.get_repository(repo_id)
        if not repo_info:
            raise ValueError(f"Repository with ID {repo_id} not found")
        
        if query_type == "component" and component_name:
            # Query for specific component
            return await self._query_component(repo_id, component_name)
        elif query_type == "pattern" and pattern_name:
            # Query for specific pattern
            return await self._query_pattern(repo_id, pattern_name)
        else:
            # General repository query
            return await self._query_general(repo_id)
    
    async def _query_component(self, repo_id: str, component_name: str) -> Dict[str, Any]:
        """Query knowledge graph for component information
        
        Args:
            repo_id: Repository ID
            component_name: Name of the component to query
            
        Returns:
            Component information
        """
        # Look for the component in the code files
        components = []
        
        # Try different approaches to find the component
        # 1. Exact match by name
        component = await self.mongodb_service.find_one(
            collection="code_files",
            query={
                "repo_id": repo_id,
                "$or": [
                    {"metadata.classes.name": component_name},
                    {"metadata.interfaces.name": component_name}
                ]
            }
        )
        
        if component:
            components.append(component)
        
        # 2. Partial match by name
        if not components:
            partial_matches = await self.mongodb_service.find(
                collection="code_files",
                query={
                    "repo_id": repo_id,
                    "$or": [
                        {"metadata.classes.name": {"$regex": component_name, "$options": "i"}},
                        {"metadata.interfaces.name": {"$regex": component_name, "$options": "i"}}
                    ]
                },
                limit=5
            )
            
            components.extend(partial_matches)
        
        if not components:
            return {
                "status": "not_found",
                "message": f"Component '{component_name}' not found in repository {repo_id}"
            }
        
        # Extract component information
        component_info = []
        for component in components:
            file_path = component.get("path", "Unknown")
            language = component.get("code_language", "Unknown")
            namespace = component.get("metadata", {}).get("namespace", "Unknown")
            
            # Look for the class in the component
            classes = component.get("metadata", {}).get("classes", [])
            for cls in classes:
                if component_name.lower() in cls.get("name", "").lower():
                    component_info.append({
                        "name": cls.get("name"),
                        "type": "class",
                        "file_path": file_path,
                        "code_language": language,
                        "namespace": namespace,
                        "inheritance": cls.get("inheritance", []),
                        "methods": cls.get("methods", []),
                        "properties": cls.get("properties", [])
                    })
            
            # Look for the interface in the component
            interfaces = component.get("metadata", {}).get("interfaces", [])
            for interface in interfaces:
                if component_name.lower() in interface.get("name", "").lower():
                    component_info.append({
                        "name": interface.get("name"),
                        "type": "interface",
                        "file_path": file_path,
                        "code_language": language,
                        "namespace": namespace,
                        "inheritance": interface.get("inheritance", [])
                    })
        
        return {
            "status": "success",
            "component_name": component_name,
            "matches": component_info
        }
    
    async def _query_pattern(self, repo_id: str, pattern_name: str) -> Dict[str, Any]:
        """Query knowledge graph for pattern information
        
        Args:
            repo_id: Repository ID
            pattern_name: Name of the pattern to query
            
        Returns:
            Pattern information
        """
        # Get repository info
        repo = await self.mongodb_service.get_repository(repo_id)
        
        # Look for the pattern in the repository metadata
        patterns_data = repo.get("metadata", {}).get("knowledge", {}).get("patterns", {})
        
        # Check different pattern types
        design_patterns = patterns_data.get("design_patterns", [])
        arch_patterns = patterns_data.get("architectural_patterns", [])
        org_patterns = patterns_data.get("code_organization", [])
        
        # Search for the pattern
        pattern_info = None
        
        # Check design patterns
        for pattern in design_patterns:
            if pattern_name.lower() in pattern.get("name", "").lower():
                pattern_info = {
                    "name": pattern.get("name"),
                    "type": "design_pattern",
                    "confidence": pattern.get("confidence"),
                    "sources": pattern.get("sources", []),
                    "count": pattern.get("count", 1)
                }
                break
        
        # Check architectural patterns if not found
        if not pattern_info:
            for pattern in arch_patterns:
                if pattern_name.lower() in pattern.get("name", "").lower():
                    pattern_info = {
                        "name": pattern.get("name"),
                        "type": "architectural_pattern",
                        "confidence": pattern.get("confidence"),
                        "sources": pattern.get("sources", []),
                        "count": pattern.get("count", 1)
                    }
                    break
        
        # Check code organization patterns if not found
        if not pattern_info:
            for pattern in org_patterns:
                if pattern_name.lower() in pattern.get("name", "").lower():
                    pattern_info = {
                        "name": pattern.get("name"),
                        "type": "code_organization",
                        "confidence": pattern.get("confidence"),
                        "sources": pattern.get("sources", []),
                        "count": pattern.get("count", 1)
                    }
                    break
        
        if not pattern_info:
            return {
                "status": "not_found",
                "message": f"Pattern '{pattern_name}' not found in repository {repo_id}"
            }
        
        return {
            "status": "success",
            "pattern_name": pattern_name,
            "pattern_info": pattern_info
        }
    
    async def _query_general(self, repo_id: str) -> Dict[str, Any]:
        """Query knowledge graph for general repository information
        
        Args:
            repo_id: Repository ID
            
        Returns:
            Repository information
        """
        # Get repository info
        repo = await self.mongodb_service.get_repository(repo_id)
        
        # Get code file count
        file_count = await self.mongodb_service.count(
            collection="code_files",
            query={"repo_id": repo_id}
        )
        
        # Get knowledge information
        knowledge = repo.get("metadata", {}).get("knowledge", {})
        
        # Get patterns
        patterns = knowledge.get("patterns", {})
        design_patterns = patterns.get("design_patterns", [])
        arch_patterns = patterns.get("architectural_patterns", [])
        org_patterns = patterns.get("code_organization", [])
        
        # Get environment
        environment = knowledge.get("environment", {})
        
        return {
            "status": "success",
            "repo_id": repo_id,
            "repo_name": repo.get("name"),
            "file_count": file_count,
            "patterns": {
                "design_patterns": [p.get("name") for p in design_patterns],
                "architectural_patterns": [p.get("name") for p in arch_patterns],
                "code_organization": [p.get("name") for p in org_patterns]
            },
            "environment": {
                "package_managers": environment.get("package_managers", []),
                "build_systems": environment.get("build_systems", []),
                "frameworks": environment.get("frameworks", [])
            }
        }
