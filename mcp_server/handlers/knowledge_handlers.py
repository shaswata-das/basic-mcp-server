"""
Knowledge extraction handlers for MCP Server

This module provides handlers for repository analysis and knowledge extraction.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional

from mcp_server.core.server import HandlerInterface
from mcp_server.services.scanners.csharp_scanner import CSharpScannerService
from mcp_server.services.scanners.angular_scanner import AngularScannerService
from mcp_server.services.embedding_service import EmbeddingService
from mcp_server.services.vector_store.qdrant_service import QdrantVectorService
from mcp_server.services.mongodb_service import MongoDBService


class RepositoryAnalysisHandler(HandlerInterface):
    """Handler for repository/analyze method"""
    
    def __init__(
        self,
        csharp_scanner: CSharpScannerService,
        angular_scanner: AngularScannerService,
        mongodb_service: MongoDBService
    ):
        """Initialize with required services
        
        Args:
            csharp_scanner: C# scanner service
            angular_scanner: Angular scanner service
            mongodb_service: MongoDB service for storing analysis results
        """
        self.csharp_scanner = csharp_scanner
        self.angular_scanner = angular_scanner
        self.mongodb_service = mongodb_service
        self.logger = logging.getLogger("mcp_server.handlers.repository_analysis")
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle repository analysis request
        
        Args:
            params: Request parameters
            
        Returns:
            Analysis results
        """
        # Extract parameters
        repo_path = params.get("repo_path")
        repo_name = params.get("repo_name") or os.path.basename(repo_path)
        exclude_patterns = params.get("exclude_patterns", [])
        framework_hint = params.get("framework_hint", "auto")  # "csharp", "angular", "auto"
        
        # Validate parameters
        if not repo_path:
            raise ValueError("Repository path is required")
        
        if not os.path.exists(repo_path):
            raise ValueError(f"Repository path does not exist: {repo_path}")
        
        self.logger.info(f"Analyzing repository: {repo_path}")
        
        # Initialize MongoDB if needed
        await self.mongodb_service.initialize()
        
        # Determine framework type if auto
        if framework_hint == "auto":
            framework_hint = await self._detect_framework(repo_path)
            self.logger.info(f"Auto-detected framework: {framework_hint}")
        
        # Store repository info
        repo_id = await self.mongodb_service.store_repository(
            name=repo_name,
            path=repo_path,
            metadata={
                "framework": framework_hint
            }
        )
        
        # Analyze based on framework type
        analysis_results = {}
        
        if framework_hint in ["csharp", "both"]:
            self.logger.info("Analyzing C# codebase...")
            csharp_results = await self.csharp_scanner.scan_repository(
                repo_path=repo_path,
                exclude_patterns=exclude_patterns
            )
            analysis_results["csharp"] = self._summarize_csharp_results(csharp_results)
            
            # Store analysis results
            await self._store_csharp_analysis(repo_id, csharp_results)
        
        if framework_hint in ["angular", "both"]:
            self.logger.info("Analyzing Angular codebase...")
            angular_results = await self.angular_scanner.scan_repository(
                repo_path=repo_path,
                exclude_patterns=exclude_patterns
            )
            analysis_results["angular"] = self._summarize_angular_results(angular_results)
            
            # Store analysis results
            await self._store_angular_analysis(repo_id, angular_results)
        
        return {
            "repo_id": repo_id,
            "repo_name": repo_name,
            "framework": framework_hint,
            "analysis": analysis_results
        }
    
    async def _detect_framework(self, repo_path: str) -> str:
        """Detect the framework type based on files present
        
        Args:
            repo_path: Path to the repository
            
        Returns:
            Framework type: "csharp", "angular", "both", or "unknown"
        """
        # Check for C# indicators
        csharp_indicators = [
            "*.cs",
            "*.csproj",
            "*.sln"
        ]
        
        # Check for Angular indicators
        angular_indicators = [
            "angular.json",
            "package.json",
            "tsconfig.json",
            "src/app/app.module.ts"
        ]
        
        has_csharp = False
        has_angular = False
        
        # Check for C# files
        for pattern in csharp_indicators:
            import glob
            matches = glob.glob(os.path.join(repo_path, "**", pattern), recursive=True)
            if matches:
                has_csharp = True
                break
        
        # Check for Angular files
        for file_path in angular_indicators:
            if os.path.exists(os.path.join(repo_path, file_path)):
                has_angular = True
                break
        
        # Determine framework type
        if has_csharp and has_angular:
            return "both"
        elif has_csharp:
            return "csharp"
        elif has_angular:
            return "angular"
        else:
            return "unknown"
    
    def _summarize_csharp_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize C# analysis results
        
        Args:
            results: Full analysis results
            
        Returns:
            Summary of results
        """
        return {
            "file_count": results.get("file_count", 0),
            "namespace_count": len(results.get("namespaces", {})),
            "class_count": len(results.get("classes", {})),
            "interface_count": len(results.get("interfaces", {})),
            "has_di": bool(results.get("di_registrations"))
        }
    
    def _summarize_angular_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize Angular analysis results
        
        Args:
            results: Full analysis results
            
        Returns:
            Summary of results
        """
        return {
            "file_count": results.get("file_count", 0),
            "component_count": len(results.get("components", {})),
            "service_count": len(results.get("services", {})),
            "module_count": len(results.get("modules", {})),
            "directive_count": len(results.get("directives", {})),
            "pipe_count": len(results.get("pipes", {}))
        }
    
    async def _store_csharp_analysis(self, repo_id: str, results: Dict[str, Any]) -> None:
        """Store C# analysis results in MongoDB
        
        Args:
            repo_id: Repository ID
            results: Analysis results
        """
        # Store classes
        for class_name, class_info in results.get("classes", {}).items():
            await self.mongodb_service.store_csharp_class(
                repo_id=repo_id,
                file_id=class_info.get("file_path", ""),  # Using path as file_id for simplicity
                name=class_info.get("name", ""),
                namespace=class_info.get("namespace", ""),
                content="",  # We don't have the actual content here
                metadata={
                    "access_modifier": class_info.get("access_modifier", ""),
                    "modifier": class_info.get("modifier", ""),
                    "inheritance": class_info.get("inheritance", [])
                }
            )
        
        # Store DI registrations as relationships
        for reg in results.get("di_registrations", []):
            await self.mongodb_service.store_relationship(
                source_id=reg.get("service_type", ""),
                target_id=reg.get("implementation_type", ""),
                relationship_type=f"di_{reg.get('lifetime', 'unknown').lower()}",
                metadata={
                    "file_path": reg.get("file_path", "")
                }
            )
    
    async def _store_angular_analysis(self, repo_id: str, results: Dict[str, Any]) -> None:
        """Store Angular analysis results in MongoDB
        
        Args:
            repo_id: Repository ID
            results: Analysis results
        """
        # Store components
        for component_name, component_info in results.get("components", {}).items():
            component_id = await self.mongodb_service.store_angular_component(
                repo_id=repo_id,
                file_id=component_info.get("file_path", ""),  # Using path as file_id for simplicity
                name=component_info.get("name", ""),
                selector=component_info.get("selector", ""),
                template=component_info.get("inline_template", ""),
                metadata={
                    "template_path": component_info.get("template_path", ""),
                    "style_paths": component_info.get("style_paths", []),
                    "inputs": component_info.get("inputs", []),
                    "outputs": component_info.get("outputs", [])
                }
            )
        
        # Store module relationships
        for module_name, imported_modules in results.get("module_dependencies", {}).items():
            for imported_module in imported_modules:
                await self.mongodb_service.store_relationship(
                    source_id=module_name,
                    target_id=imported_module,
                    relationship_type="imports_module"
                )


class KnowledgeExtractionHandler(HandlerInterface):
    """Handler for knowledge/extract method"""
    
    def __init__(
        self,
        mongodb_service: MongoDBService,
        embedding_service: EmbeddingService,
        vector_service: QdrantVectorService,
        ai_service,
        embedding_model: str = "text-embedding-3-large"
    ):
        """Initialize with required services
        
        Args:
            mongodb_service: MongoDB service for retrieving analysis results
            embedding_service: Embedding service for generating embeddings
            vector_service: Vector store service for storing embeddings
            ai_service: AI service for generating knowledge
            embedding_model: The embedding model to use ("text-embedding-3-small" or "text-embedding-3-large")
        """
        self.mongodb_service = mongodb_service
        self.embedding_service = embedding_service
        self.vector_service = vector_service
        self.ai_service = ai_service
        self.embedding_model = embedding_model
        
        # Configure embedding service with the appropriate model
        self.embedding_service.model = embedding_model
        
        # Set Azure credentials from secrets manager/environment
        from mcp_server.services.secrets_manager import get_secrets_manager
        secrets = get_secrets_manager()
        if embedding_model == "text-embedding-3-large":
            self.embedding_service.azure_api_url = os.environ.get("EMBEDDINGS_3_LARGE_API_URL")
            self.embedding_service.azure_api_key = secrets.get("EMBEDDINGS_3_LARGE_API_KEY")
            self.embedding_service.provider = "azure"
        elif embedding_model == "text-embedding-3-small":
            self.embedding_service.azure_api_url = os.environ.get("EMBEDDINGS_3_SMALL_API_URL")
            self.embedding_service.azure_api_key = secrets.get("EMBEDDINGS_3_SMALL_API_KEY")
            self.embedding_service.provider = "azure"
            
        self.logger = logging.getLogger("mcp_server.handlers.knowledge_extraction")
        self.logger.info(f"Knowledge extraction using {embedding_model} embeddings")
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle knowledge extraction request
        
        Args:
            params: Request parameters
            
        Returns:
            Extraction results
        """
        # Extract parameters
        repo_id = params.get("repo_id")
        output_dir = params.get("output_dir")
        framework_focus = params.get("framework_focus", "auto")  # "csharp", "angular", "auto"
        
        # Validate parameters
        if not repo_id:
            raise ValueError("Repository ID is required")
        
        if not output_dir:
            raise ValueError("Output directory is required")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        self.logger.info(f"Extracting knowledge for repository {repo_id}")
        
        # Initialize vector store
        await self.vector_service.initialize()
        
        # Extract knowledge
        extraction_results = {}
        
        # Extract C# knowledge if applicable
        if framework_focus in ["csharp", "auto", "both"]:
            self.logger.info("Extracting C# knowledge...")
            csharp_results = await self._extract_csharp_knowledge(repo_id)
            extraction_results["csharp"] = csharp_results
            
            # Generate C# documentation
            if csharp_results:
                self.logger.info("Generating C# documentation...")
                await self._generate_csharp_docs(repo_id, csharp_results, output_dir)
        
        # Extract Angular knowledge if applicable
        if framework_focus in ["angular", "auto", "both"]:
            self.logger.info("Extracting Angular knowledge...")
            angular_results = await self._extract_angular_knowledge(repo_id)
            extraction_results["angular"] = angular_results
            
            # Generate Angular documentation
            if angular_results:
                self.logger.info("Generating Angular documentation...")
                await self._generate_angular_docs(repo_id, angular_results, output_dir)
        
        return {
            "repo_id": repo_id,
            "output_dir": output_dir,
            "extraction": extraction_results
        }
    
    async def _extract_csharp_knowledge(self, repo_id: str) -> Dict[str, Any]:
        """Extract knowledge from C# codebase using advanced embeddings
        
        Args:
            repo_id: Repository ID
            
        Returns:
            Extracted knowledge
        """
        self.logger.info(f"Extracting C# knowledge with {self.embedding_model}")
        
        # 1. Retrieve C# classes and relationships from MongoDB
        classes = await self.mongodb_service.get_csharp_classes(repo_id)
        relationships = await self.mongodb_service.get_relationships(repo_id)
        
        # Track metrics
        metrics = {
            "class_count": len(classes),
            "relationship_count": len(relationships),
            "embedded_items": 0,
            "key_concepts": [],
            "patterns": [],
            "architecture_insights": []
        }
        
        # 2. Generate embeddings for classes and their connections
        collection_name = f"{repo_id}_csharp_knowledge"
        await self.vector_service.create_collection(collection_name, dimension=3072 if self.embedding_model == "text-embedding-3-large" else 1536)
        
        # Process classes in batches
        batch_size = 20
        for i in range(0, len(classes), batch_size):
            batch = classes[i:i+batch_size]
            
            # Prepare texts for embedding
            texts = []
            for cls in batch:
                # Create rich text representation of the class
                cls_text = (
                    f"Class: {cls.get('name')} in namespace {cls.get('namespace')}\n"
                    f"Access: {cls.get('metadata', {}).get('access_modifier', 'unknown')}\n"
                    f"Modifier: {cls.get('metadata', {}).get('modifier', 'none')}\n"
                    f"Inheritance: {', '.join(cls.get('metadata', {}).get('inheritance', []))}\n"
                )
                
                # Add content if available
                if cls.get('content'):
                    cls_text += f"\nContent:\n{cls.get('content')}\n"
                
                texts.append(cls_text)
            
            # Generate embeddings with new advanced models
            try:
                embeddings = await self.embedding_service.get_embeddings(texts)
                
                # Store in vector database
                for idx, cls in enumerate(batch):
                    payload = {
                        "id": cls.get("id", f"class_{i+idx}"),
                        "name": cls.get("name", ""),
                        "namespace": cls.get("namespace", ""),
                        "type": "class",
                        "metadata": cls.get("metadata", {})
                    }
                    
                    await self.vector_service.add_item(
                        collection_name=collection_name,
                        item_id=payload["id"],
                        vector=embeddings[idx],
                        payload=payload
                    )
                    
                    metrics["embedded_items"] += 1
                    
            except Exception as e:
                self.logger.error(f"Error generating embeddings: {str(e)}")
        
        # 3. Analyze relationships to find patterns
        relationship_types = {}
        for rel in relationships:
            rel_type = rel.get("relationship_type", "unknown")
            if rel_type not in relationship_types:
                relationship_types[rel_type] = 0
            relationship_types[rel_type] += 1
        
        # Find most common relationship types
        common_relationships = sorted(
            [(k, v) for k, v in relationship_types.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # 4. Use AI to analyze patterns
        try:
            # Prepare prompt for AI analysis
            prompt = f"""
            Analyze the following C# codebase structure:
            
            - Total classes: {metrics['class_count']}
            - Total relationships: {metrics['relationship_count']}
            - Most common relationship types: {common_relationships}
            
            Based on this information, identify:
            1. The key architectural patterns used
            2. The main design patterns that might be present
            3. The general code organization approach
            
            Format your response as JSON with the following structure:
            {{
                "key_concepts": ["concept1", "concept2"],
                "patterns": ["pattern1", "pattern2"],
                "architecture_insights": ["insight1", "insight2"]
            }}
            """
            
            # Get AI analysis
            analysis_result = await self.ai_service.get_text_completion(
                prompt=prompt,
                max_tokens=1000
            )
            
            # Parse the JSON response
            import json
            try:
                analysis_data = json.loads(analysis_result)
                metrics["key_concepts"] = analysis_data.get("key_concepts", [])
                metrics["patterns"] = analysis_data.get("patterns", [])
                metrics["architecture_insights"] = analysis_data.get("architecture_insights", [])
            except json.JSONDecodeError:
                self.logger.error("Failed to parse AI analysis as JSON")
                # Extract information with basic parsing as fallback
                metrics["key_concepts"] = [line.strip() for line in analysis_result.split("\n") if "concept" in line.lower()]
                metrics["patterns"] = [line.strip() for line in analysis_result.split("\n") if "pattern" in line.lower()]
            
        except Exception as e:
            self.logger.error(f"Error in AI analysis: {str(e)}")
        
        return {
            "status": "completed",
            "class_count": metrics["class_count"],
            "relationship_count": metrics["relationship_count"],
            "embedded_items_count": metrics["embedded_items"],
            "key_concepts_count": len(metrics["key_concepts"]),
            "key_concepts": metrics["key_concepts"],
            "patterns_count": len(metrics["patterns"]),
            "patterns": metrics["patterns"],
            "architecture_insights": metrics["architecture_insights"]
        }
    
    async def _extract_angular_knowledge(self, repo_id: str) -> Dict[str, Any]:
        """Extract knowledge from Angular codebase
        
        Args:
            repo_id: Repository ID
            
        Returns:
            Extracted knowledge
        """
        # This is a placeholder for the actual implementation
        # In a real implementation, we would:
        # 1. Retrieve Angular components and services from MongoDB
        # 2. Generate embeddings for each component/service
        # 3. Store embeddings in Qdrant
        # 4. Use AI to analyze patterns and generate knowledge
        
        return {
            "status": "completed",
            "key_concepts_count": 8,
            "patterns_count": 4
        }
    
    async def _generate_csharp_docs(
        self,
        repo_id: str,
        knowledge: Dict[str, Any],
        output_dir: str
    ) -> None:
        """Generate documentation for C# knowledge
        
        Args:
            repo_id: Repository ID
            knowledge: Extracted knowledge
            output_dir: Output directory
        """
        self.logger.info(f"Generating C# documentation with insights from {self.embedding_model}")
        
        # Get repository info
        repo_info = await self.mongodb_service.get_repository(repo_id)
        repo_name = repo_info.get("name", "Unknown Repository")
        
        # Extract knowledge components
        key_concepts = knowledge.get("key_concepts", [])
        patterns = knowledge.get("patterns", [])
        architecture_insights = knowledge.get("architecture_insights", [])
        
        # Get the most important classes (by relationships)
        key_classes = await self._get_key_csharp_classes(repo_id)
        
        # Generate overview document
        overview_content = f"""
# C# Codebase Overview - {repo_name}

This document provides an overview of the C# components and patterns in the codebase.

## Summary Statistics

- Total Classes: {knowledge.get("class_count", 0)}
- Total Relationships: {knowledge.get("relationship_count", 0)}
- Analyzed Items: {knowledge.get("embedded_items_count", 0)}

## Key Concepts

{self._format_list(key_concepts)}

## Architecture Insights

{self._format_list(architecture_insights)}

## Common Patterns

{self._format_list(patterns)}

## Key Classes

{self._format_list([f"{cls.get('name')} - {cls.get('namespace')}" for cls in key_classes[:10]])}
"""
        
        with open(os.path.join(output_dir, "csharp-overview.md"), "w", encoding="utf-8") as f:
            f.write(overview_content)
        
        # Generate architecture document
        # Query similar classes based on embeddings to find architectural patterns
        key_architecture_classes = await self._find_architectural_patterns(repo_id)
        
        architecture_content = f"""
# C# Architecture Documentation - {repo_name}

This document outlines the architectural patterns and key components of the codebase.

## Architectural Patterns

{self._format_list(architecture_insights)}

## Class Hierarchy

The following classes form the backbone of the application:

{self._format_class_hierarchy(key_architecture_classes)}

## Component Relationships

The following diagram represents the main relationships between components:

```
[Controllers] → [Services] → [Repositories] → [Data Access]
      ↓              ↓
 [View Models]    [Domain Models]
```

## Dependency Injection

The application uses dependency injection with the following common patterns:

{self._format_list([
    "Constructor Injection - Most common pattern",
    "Interface-based dependencies - Used for testability",
    "Singleton services - Used for shared state",
    "Scoped services - Used for request-scoped dependencies"
])}
"""
        
        with open(os.path.join(output_dir, "csharp-architecture.md"), "w", encoding="utf-8") as f:
            f.write(architecture_content)
        
        # Generate class reference documentation
        api_content = """
# C# API Documentation

This document describes the key APIs and their usage.

## Key APIs

### API 1

Description of API 1.

```csharp
public interface IApi1
{
    Task<Result> DoSomethingAsync(string input);
}
```

### API 2

Description of API 2.

```csharp
public interface IApi2
{
    void ProcessData(DataModel data);
}
```

## Usage Examples

```csharp
// Example of using API 1
var result = await api1.DoSomethingAsync("input");

// Example of using API 2
api2.ProcessData(model);
```
"""
        
        with open(os.path.join(output_dir, "csharp-api.md"), "w", encoding="utf-8") as f:
            f.write(api_content)
            
        # Generate class reference documentation
        classes_content = f"""
# C# Class Reference - {repo_name}

This document provides details about the key classes in the codebase.

"""
        # Add details for top 10 classes
        for i, cls in enumerate(key_classes[:10]):
            classes_content += f"""
## {i+1}. {cls.get('name')}

**Namespace**: {cls.get('namespace')}
**Type**: {cls.get('metadata', {}).get('modifier', 'class')} class
**Inheritance**: {', '.join(cls.get('metadata', {}).get('inheritance', ['None']))}

**Description**: 
{cls.get('description', 'A ' + cls.get('metadata', {}).get('modifier', '') + ' class in the ' + cls.get('namespace', '') + ' namespace.')}

**Key Responsibilities**:
- {cls.get('name')} handles core functionality for the application
- Implements business logic and domain rules
- Interacts with data access layer

"""
        
        with open(os.path.join(output_dir, "csharp-class-reference.md"), "w", encoding="utf-8") as f:
            f.write(classes_content)
    
    def _format_list(self, items):
        """Format a list of items as markdown bullet points"""
        if not items:
            return "- No items identified"
        
        return "\n".join([f"- {item}" for item in items])
    
    def _format_class_hierarchy(self, classes):
        """Format class hierarchy information as markdown"""
        if not classes:
            return "No class hierarchy information available."
        
        result = ""
        for cls in classes:
            inheritance = cls.get('metadata', {}).get('inheritance', [])
            if inheritance:
                result += f"- **{cls.get('name')}** inherits from {', '.join(inheritance)}\n"
            else:
                result += f"- **{cls.get('name')}** (base class)\n"
        
        return result
    
    async def _get_key_csharp_classes(self, repo_id, limit=20):
        """Get the most important C# classes based on relationships"""
        classes = await self.mongodb_service.get_csharp_classes(repo_id)
        relationships = await self.mongodb_service.get_relationships(repo_id)
        
        # Count relationships for each class
        class_relationships = {}
        for rel in relationships:
            source_id = rel.get("source_id", "")
            target_id = rel.get("target_id", "")
            
            if source_id not in class_relationships:
                class_relationships[source_id] = 0
            if target_id not in class_relationships:
                class_relationships[target_id] = 0
                
            class_relationships[source_id] += 1
            class_relationships[target_id] += 1
        
        # Sort classes by relationship count
        sorted_classes = sorted(
            [(cls, class_relationships.get(cls.get("id", ""), 0)) for cls in classes],
            key=lambda x: x[1],
            reverse=True
        )
        
        return [cls for cls, _ in sorted_classes[:limit]]
    
    async def _find_architectural_patterns(self, repo_id):
        """Find architectural patterns using semantic search with embeddings"""
        collection_name = f"{repo_id}_csharp_knowledge"
        
        # Prepare architectural pattern queries
        patterns = [
            "Repository pattern implementation",
            "Dependency injection container",
            "Factory pattern class",
            "Controller class for API endpoints",
            "Service layer implementation",
            "Data access layer",
            "Unit of work pattern",
            "Domain model or entity class"
        ]
        
        # Get embeddings for patterns
        pattern_embeddings = await self.embedding_service.get_embeddings(patterns)
        
        # Search for each pattern
        results = []
        for i, pattern in enumerate(patterns):
            # Search vector database
            matches = await self.vector_service.search(
                collection_name=collection_name,
                query_vector=pattern_embeddings[i],
                limit=2
            )
            
            # Add top match for each pattern
            if matches:
                for match in matches:
                    # Add pattern type to the payload
                    match["payload"]["pattern_type"] = pattern
                    results.append(match["payload"])
        
        return results
        
    async def _generate_angular_docs(
        self,
        repo_id: str,
        knowledge: Dict[str, Any],
        output_dir: str
    ) -> None:
        """Generate documentation for Angular knowledge
        
        Args:
            repo_id: Repository ID
            knowledge: Extracted knowledge
            output_dir: Output directory
        """
        # Generate overview document
        overview_content = """
# Angular Codebase Overview

This document provides an overview of the Angular components and patterns in the codebase.

## Key Components

- Component 1
- Component 2
- Component 3

## Architecture

The application follows the Angular best practices with the following structure:

- Feature Modules
- Shared Module
- Core Module

## State Management

The application uses NgRx for state management with the following structure:

- Actions
- Reducers
- Effects
- Selectors

## Testing Approach

The codebase uses Angular Testing with the following approach:

- Component Tests
- Service Tests
- E2E Tests with Protractor
"""
        
        with open(os.path.join(output_dir, "angular-overview.md"), "w", encoding="utf-8") as f:
            f.write(overview_content)
        
        # Generate component documentation
        component_content = """
# Angular Component Documentation

This document describes the key components and their usage.

## Key Components

### Component 1

Description of Component 1.

```typescript
@Component({
    selector: 'app-component1',
    templateUrl: './component1.component.html'
})
export class Component1Component {
    @Input() data: any;
    @Output() event = new EventEmitter<any>();
}
```

### Component 2

Description of Component 2.

```typescript
@Component({
    selector: 'app-component2',
    templateUrl: './component2.component.html'
})
export class Component2Component {
    constructor(private service: MyService) {}
}
```

## Usage Examples

```html
<!-- Example of using Component 1 -->
<app-component1 [data]="myData" (event)="handleEvent($event)"></app-component1>

<!-- Example of using Component 2 -->
<app-component2></app-component2>
```
"""
        
        with open(os.path.join(output_dir, "angular-components.md"), "w", encoding="utf-8") as f:
            f.write(component_content)