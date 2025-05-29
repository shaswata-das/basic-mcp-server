"""
Enhanced Knowledge Extraction Handlers for MCP Server

This module provides advanced handlers for repository analysis and knowledge extraction,
including deep code content extraction, function call graphs, pattern extraction,
and environment analysis.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional

from mcp_server.core.server import HandlerInterface
from mcp_server.services.embedding_service import EmbeddingService
from mcp_server.services.vector_store.qdrant_service import QdrantVectorService
from mcp_server.services.mongodb_service import MongoDBService
from mcp_server.services.knowledge_extraction.code_extractor import CodeExtractor
from mcp_server.services.knowledge_extraction.call_graph_analyzer import CallGraphAnalyzer
from mcp_server.services.knowledge_extraction.pattern_extractor import PatternExtractor
from mcp_server.services.knowledge_extraction.environment_analyzer import EnvironmentAnalyzer


class EnhancedRepositoryAnalysisHandler(HandlerInterface):
    """Handler for enhanced repository analysis providing deeper code understanding"""
    
    def __init__(
        self,
        mongodb_service: MongoDBService,
        embedding_service: EmbeddingService,
        vector_service: QdrantVectorService,
        ai_service = None
    ):
        """Initialize with required services
        
        Args:
            mongodb_service: MongoDB service for storing analysis results
            embedding_service: Embedding service for generating embeddings
            vector_service: Vector store service for storing embeddings
            ai_service: Optional AI service for advanced analysis
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
        
        self.logger = logging.getLogger("mcp_server.handlers.enhanced_repository_analysis")
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle enhanced repository analysis request
        
        Args:
            params: Request parameters
            
        Returns:
            Enhanced analysis results
        """
        # Extract parameters
        repo_path = params.get("repo_path")
        repo_name = params.get("repo_name") or os.path.basename(repo_path)
        exclude_patterns = params.get("exclude_patterns", [])
        extract_patterns = params.get("extract_patterns", True)
        extract_call_graphs = params.get("extract_call_graphs", True)
        extract_environment = params.get("extract_environment", True)
        output_dir = params.get("output_dir", os.path.join(repo_path, "analysis_output"))
        
        # Validate parameters
        if not repo_path:
            raise ValueError("Repository path is required")
        
        if not os.path.exists(repo_path):
            raise ValueError(f"Repository path does not exist: {repo_path}")
        
        self.logger.info(f"Starting enhanced analysis for repository: {repo_path}")
        
        # Initialize MongoDB if needed
        await self.mongodb_service.initialize()
        
        # Store repository info
        repo_id = await self.mongodb_service.store_repository(
            name=repo_name,
            path=repo_path,
            metadata={
                "analysis_type": "enhanced"
            }
        )
        
        # Create output directory if needed
        os.makedirs(output_dir, exist_ok=True)
        
        # Analyze files first with code extractor
        self.logger.info("Extracting code content and structure...")
        file_infos = []
        file_count = 0
        
        # Walk through repository and analyze files
        for root, dirs, files in os.walk(repo_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(pat in os.path.join(root, d) for pat in exclude_patterns)]
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repo_path)
                
                # Skip excluded files
                if any(pat in file_path for pat in exclude_patterns):
                    continue
                
                # Skip very large files and binary files
                try:
                    if os.path.getsize(file_path) > 1024 * 1024:  # Skip files larger than 1MB
                        continue
                    
                    # Determine file language
                    language = self._determine_language(file_path)
                    
                    if language:
                        # Extract knowledge from file
                        knowledge = await self.code_extractor.extract_knowledge_from_file(
                            file_path=file_path,
                            language=language
                        )
                        
                        # Store file info for further analysis
                        file_infos.append({
                            "file_path": file_path,
                            "rel_path": rel_path,
                            "language": language,
                            **knowledge
                        })
                        
                        # Store in MongoDB
                        await self.mongodb_service.store_code_file(
                            repo_id=repo_id,
                            path=rel_path,
                            language=language,
                            content="",  # We don't store content for security/privacy
                            metadata=knowledge
                        )
                        
                        file_count += 1
                        
                except Exception as e:
                    self.logger.warning(f"Error processing file {file_path}: {str(e)}")
        
        # Initialize results
        results = {
            "repo_id": repo_id,
            "repo_name": repo_name,
            "file_count": file_count,
            "output_dir": output_dir
        }
        
        # Extract call graphs if requested
        if extract_call_graphs:
            self.logger.info("Analyzing function call graphs and data flow...")
            try:
                call_graph_results = await self.call_graph_analyzer.analyze_codebase(
                    repo_path=repo_path,
                    files=file_infos,
                    exclude_patterns=exclude_patterns
                )
                
                # Store call graph analysis
                call_graph_file = os.path.join(output_dir, "call_graph.json")
                self.call_graph_analyzer.export_graph_to_json(call_graph_file)
                
                results["call_graph"] = {
                    "file": call_graph_file,
                    "node_count": call_graph_results.get("summary", {}).get("node_count", 0),
                    "edge_count": call_graph_results.get("summary", {}).get("edge_count", 0),
                    "central_components": [c.get("id") for c in call_graph_results.get("central_components", [])]
                }
            except Exception as e:
                self.logger.error(f"Error analyzing call graphs: {str(e)}")
                results["call_graph"] = {"error": str(e)}
        
        # Extract patterns if requested
        if extract_patterns:
            self.logger.info("Extracting development patterns...")
            try:
                pattern_results = await self.pattern_extractor.extract_patterns(
                    repo_path=repo_path,
                    files=file_infos,
                    call_graph_results=results.get("call_graph")
                )
                
                # Store pattern analysis
                pattern_file = os.path.join(output_dir, "patterns.json")
                with open(pattern_file, 'w', encoding='utf-8') as f:
                    json.dump(pattern_results, f, indent=2)
                
                # Include summary in results
                results["patterns"] = {
                    "file": pattern_file,
                    "design_patterns": [p.get("name") for p in pattern_results.get("design_patterns", [])],
                    "architectural_patterns": [p.get("name") for p in pattern_results.get("architectural_patterns", [])],
                    "code_organization": [p.get("name") for p in pattern_results.get("code_organization", [])]
                }
            except Exception as e:
                self.logger.error(f"Error extracting patterns: {str(e)}")
                results["patterns"] = {"error": str(e)}
        
        # Analyze environment if requested
        if extract_environment:
            self.logger.info("Analyzing environment and dependencies...")
            try:
                env_results = await self.environment_analyzer.analyze_environment(
                    repo_path=repo_path,
                    repo_languages=list(set(f.get("language") for f in file_infos if f.get("language")))
                )
                
                # Store environment analysis
                env_file = os.path.join(output_dir, "environment.json")
                with open(env_file, 'w', encoding='utf-8') as f:
                    json.dump(env_results, f, indent=2)
                
                # Include summary in results
                results["environment"] = {
                    "file": env_file,
                    "package_managers": env_results.get("package_managers", []),
                    "build_systems": env_results.get("build_systems", []),
                    "frameworks": env_results.get("dependencies", {}).get("frameworks", [])
                }
            except Exception as e:
                self.logger.error(f"Error analyzing environment: {str(e)}")
                results["environment"] = {"error": str(e)}
        
        # Generate report
        await self._generate_report(results, output_dir)
        
        return results
    
    def _determine_language(self, file_path: str) -> Optional[str]:
        """Determine the programming language from file extension
        
        Args:
            file_path: Path to the file
            
        Returns:
            Language name or None if unsupported
        """
        extension = os.path.splitext(file_path)[1].lower()
        
        # Map of extensions to languages
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
        
        return extension_map.get(extension)
    
    async def _generate_report(self, results: Dict[str, Any], output_dir: str) -> None:
        """Generate a summary report of the analysis
        
        Args:
            results: Analysis results
            output_dir: Output directory
        """
        repo_name = results.get("repo_name", "Repository")
        
        # Create report content
        report = f"""# Enhanced Repository Analysis for {repo_name}

## Summary

- **Repository Name**: {repo_name}
- **Files Analyzed**: {results.get("file_count", 0)}
- **Analysis Date**: {self._get_current_date()}

"""
        
        # Add call graph section if available
        if "call_graph" in results and "error" not in results["call_graph"]:
            report += f"""## Call Graph Analysis

- **Nodes**: {results["call_graph"].get("node_count", 0)}
- **Edges**: {results["call_graph"].get("edge_count", 0)}
- **Central Components**: {", ".join(results["call_graph"].get("central_components", [])[:5])}

"""
        
        # Add patterns section if available
        if "patterns" in results and "error" not in results["patterns"]:
            report += """## Development Patterns

### Design Patterns
"""
            for pattern in results["patterns"].get("design_patterns", []):
                report += f"- {pattern}\n"
            
            report += "\n### Architectural Patterns\n"
            for pattern in results["patterns"].get("architectural_patterns", []):
                report += f"- {pattern}\n"
            
            report += "\n### Code Organization\n"
            for pattern in results["patterns"].get("code_organization", []):
                report += f"- {pattern}\n"
            
            report += "\n"
        
        # Add environment section if available
        if "environment" in results and "error" not in results["environment"]:
            report += """## Environment Analysis

### Package Managers
"""
            for pm in results["environment"].get("package_managers", []):
                report += f"- {pm}\n"
            
            report += "\n### Build Systems\n"
            for build in results["environment"].get("build_systems", []):
                report += f"- {build}\n"
            
            report += "\n### Frameworks\n"
            for fw in results["environment"].get("frameworks", []):
                report += f"- {fw}\n"
            
            report += "\n"
        
        # Write report to file
        report_file = os.path.join(output_dir, "analysis_report.md")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
    
    def _get_current_date(self) -> str:
        """Get the current date as a string
        
        Returns:
            Date string
        """
        import datetime
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class EnhancedCodeSearchHandler(HandlerInterface):
    """Handler for enhanced code search using embeddings and knowledge graph"""
    
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
            vector_service: Vector store service for storing embeddings
        """
        self.mongodb_service = mongodb_service
        self.embedding_service = embedding_service
        self.vector_service = vector_service
        self.logger = logging.getLogger("mcp_server.handlers.enhanced_code_search")
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle enhanced code search request
        
        Args:
            params: Request parameters
            
        Returns:
            Search results
        """
        # Extract parameters
        repo_id = params.get("repo_id")
        query = params.get("query")
        language_filter = params.get("language")
        max_results = params.get("max_results", 10)
        include_code = params.get("include_code", False)
        
        # Validate parameters
        if not repo_id:
            raise ValueError("Repository ID is required")
        
        if not query:
            raise ValueError("Search query is required")
        
        self.logger.info(f"Searching code in repository {repo_id} for query: {query}")
        
        # Initialize vector store if needed
        await self.vector_service.initialize()
        
        # Generate embedding for the query
        query_embedding = await self.embedding_service.get_embedding(query)
        
        # Prepare filter
        filter_params = {"repo_id": repo_id}
        if language_filter:
            filter_params["language"] = language_filter
        
        # Search for similar code
        search_results = await self.vector_service.search_similar_code(
            query_embedding=query_embedding,
            filter_params=filter_params,
            limit=max_results
        )
        
        # Format results
        results = []
        for result in search_results:
            item = {
                "id": result.get("id"),
                "file_path": result.get("file_path", "Unknown"),
                "language": result.get("language", "Unknown"),
                "score": result.get("score", 0.0),
                "type": result.get("type", "Unknown")
            }
            
            # Include code text if requested
            if include_code:
                item["code_text"] = result.get("code_text", "")
            
            results.append(item)
        
        return {
            "repo_id": repo_id,
            "query": query,
            "results": results
        }


class DependencyAnalysisHandler(HandlerInterface):
    """Handler for analyzing dependencies between components"""
    
    def __init__(
        self,
        mongodb_service: MongoDBService,
        call_graph_analyzer: Optional[CallGraphAnalyzer] = None
    ):
        """Initialize with required services
        
        Args:
            mongodb_service: MongoDB service for retrieving analysis results
            call_graph_analyzer: Optional call graph analyzer instance
        """
        self.mongodb_service = mongodb_service
        self.call_graph_analyzer = call_graph_analyzer or CallGraphAnalyzer()
        self.logger = logging.getLogger("mcp_server.handlers.dependency_analysis")
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle dependency analysis request
        
        Args:
            params: Request parameters
            
        Returns:
            Dependency analysis results
        """
        # Extract parameters
        repo_id = params.get("repo_id")
        component_id = params.get("component_id")
        component_type = params.get("component_type")
        include_transitive = params.get("include_transitive", False)
        
        # Validate parameters
        if not repo_id:
            raise ValueError("Repository ID is required")
        
        if not component_id and not component_type:
            raise ValueError("Either component ID or type is required")
        
        self.logger.info(f"Analyzing dependencies for repository {repo_id}")
        
        # If component ID is provided, get dependencies for that component
        if component_id:
            dependencies = await self._get_component_dependencies(repo_id, component_id, include_transitive)
            return {
                "repo_id": repo_id,
                "component_id": component_id,
                "dependencies": dependencies
            }
        
        # If component type is provided, get all components of that type and their dependencies
        else:
            components = await self._get_components_by_type(repo_id, component_type)
            results = []
            
            for component in components:
                component_id = component.get("id")
                dependencies = await self._get_component_dependencies(repo_id, component_id, include_transitive)
                
                results.append({
                    "component": component,
                    "dependencies": dependencies
                })
            
            return {
                "repo_id": repo_id,
                "component_type": component_type,
                "results": results
            }
    
    async def _get_component_dependencies(
        self, 
        repo_id: str, 
        component_id: str, 
        include_transitive: bool
    ) -> Dict[str, Any]:
        """Get dependencies for a specific component
        
        Args:
            repo_id: Repository ID
            component_id: Component ID
            include_transitive: Whether to include transitive dependencies
            
        Returns:
            Component dependencies
        """
        # Get direct dependencies from MongoDB
        direct_dependencies = await self.mongodb_service.get_related_entities(
            entity_id=component_id,
            direction="outgoing"
        )
        
        # Format direct dependencies
        dependencies = {
            "direct": [
                {
                    "id": dep.get("entity", {}).get("id", "unknown"),
                    "name": dep.get("entity", {}).get("name", "unknown"),
                    "type": dep.get("entity", {}).get("type", "unknown"),
                    "relationship": dep.get("relationship", {}).get("type", "unknown")
                }
                for dep in direct_dependencies
            ]
        }
        
        # Include transitive dependencies if requested
        if include_transitive:
            transitive_deps = []
            visited = set([component_id])
            
            # Add all direct dependencies to the queue
            queue = [dep.get("entity", {}).get("id") for dep in direct_dependencies]
            
            while queue:
                current = queue.pop(0)
                
                if current in visited:
                    continue
                
                visited.add(current)
                
                # Get dependencies of the current entity
                current_deps = await self.mongodb_service.get_related_entities(
                    entity_id=current,
                    direction="outgoing"
                )
                
                for dep in current_deps:
                    dep_id = dep.get("entity", {}).get("id")
                    
                    if dep_id not in visited:
                        transitive_deps.append({
                            "id": dep_id,
                            "name": dep.get("entity", {}).get("name", "unknown"),
                            "type": dep.get("entity", {}).get("type", "unknown"),
                            "relationship": dep.get("relationship", {}).get("type", "unknown"),
                            "via": current
                        })
                        
                        queue.append(dep_id)
            
            dependencies["transitive"] = transitive_deps
        
        return dependencies
    
    async def _get_components_by_type(self, repo_id: str, component_type: str) -> List[Dict[str, Any]]:
        """Get all components of a specific type
        
        Args:
            repo_id: Repository ID
            component_type: Component type
            
        Returns:
            List of components
        """
        # Query MongoDB for components of the specified type
        if component_type.lower() == "class":
            return await self.mongodb_service.get_csharp_classes(repo_id)
        elif component_type.lower() == "component":
            return await self.mongodb_service.get_angular_components(repo_id)
        else:
            # Generic query based on type
            return []  # This would need implementation in the MongoDB service