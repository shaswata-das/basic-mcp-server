"""
Call Graph Analyzer for MCP Server

This module provides function call graph and data flow analysis capabilities.
It builds call graphs and analyzes data flow between components, helping
understand code structure and dependencies.
"""

import os
import logging
import re
import ast
import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
import json
import networkx as nx

class CallGraphAnalyzer:
    """Analyzes function call graphs and data flow in code"""
    
    def __init__(self):
        """Initialize the call graph analyzer"""
        self.logger = logging.getLogger("mcp_server.services.knowledge_extraction.call_graph_analyzer")
        self.call_graph = nx.DiGraph()
        self.data_flow_graph = nx.DiGraph()
    
    async def analyze_codebase(
        self,
        repo_path: str,
        files: List[Dict[str, Any]],
        language: Optional[str] = None,
        exclude_patterns: List[str] = []
    ) -> Dict[str, Any]:
        """Analyze call graphs and data flow for an entire codebase
        
        Args:
            repo_path: Path to the repository
            files: List of file information dictionaries
            language: Optional language filter
            exclude_patterns: Patterns to exclude from analysis
            
        Returns:
            Analysis results
        """
        self.logger.info(f"Starting call graph analysis for repository: {repo_path}")
        
        # Clear any previous graphs
        self.call_graph.clear()
        self.data_flow_graph.clear()
        
        # Filter files by language if specified
        if language:
            files = [f for f in files if f.get("code_language", "").lower() == language.lower()]
        
        # Filter out excluded files
        for pattern in exclude_patterns:
            files = [f for f in files if pattern not in f.get("file_path", "")]
        
        # Analyze each file based on its language
        for file_info in files:
            file_path = file_info.get("file_path")
            file_language = file_info.get("code_language", "unknown")
            
            if file_language.lower() in ["csharp", "cs", "c#"]:
                await self._analyze_csharp_file(file_info)
            elif file_language.lower() in ["typescript", "ts"]:
                await self._analyze_typescript_file(file_info)
            elif file_language.lower() in ["javascript", "js"]:
                await self._analyze_javascript_file(file_info)
            elif file_language.lower() in ["python", "py"]:
                await self._analyze_python_file(file_info)
        
        # Build relationships between components
        self._build_cross_file_relationships(files)
        
        # Generate analysis results
        return self._generate_analysis_results()
    
    async def _analyze_csharp_file(self, file_info: Dict[str, Any]) -> None:
        """Analyze C# file for call graph and data flow
        
        Args:
            file_info: File information dictionary
        """
        file_path = file_info.get("file_path")
        namespace = file_info.get("namespace", "Unknown")
        
        # Add nodes for classes
        for cls in file_info.get("classes", []):
            class_name = cls.get("name")
            class_node = f"{namespace}.{class_name}"
            
            # Add class node to call graph
            self.call_graph.add_node(
                class_node,
                type="class",
                language="csharp",
                file_path=file_path,
                namespace=namespace
            )
            
            # Add method nodes and edges
            for method in cls.get("methods", []):
                method_name = method.get("name")
                method_node = f"{class_node}.{method_name}"
                
                # Add method node
                self.call_graph.add_node(
                    method_node,
                    type="method",
                    language="csharp",
                    file_path=file_path,
                    class_name=class_name,
                    namespace=namespace
                )
                
                # Connect class to method
                self.call_graph.add_edge(
                    class_node,
                    method_node,
                    type="contains"
                )
        
        # Add nodes for interfaces
        for interface in file_info.get("interfaces", []):
            interface_name = interface.get("name")
            interface_node = f"{namespace}.{interface_name}"
            
            # Add interface node to call graph
            self.call_graph.add_node(
                interface_node,
                type="interface",
                language="csharp",
                file_path=file_path,
                namespace=namespace
            )
        
        # Add dependency injection relationships
        for di in file_info.get("di_registrations", []):
            service_type = di.get("service_type")
            implementation_type = di.get("implementation_type")
            lifetime = di.get("lifetime", "unknown")
            
            # Add DI relationship
            if service_type and implementation_type:
                # Add nodes if they don't exist
                if not self.call_graph.has_node(service_type):
                    self.call_graph.add_node(
                        service_type,
                        type="interface",
                        language="csharp",
                        file_path=file_path
                    )
                
                if not self.call_graph.has_node(implementation_type):
                    self.call_graph.add_node(
                        implementation_type,
                        type="class",
                        language="csharp",
                        file_path=file_path
                    )
                
                # Add DI edge
                self.call_graph.add_edge(
                    service_type,
                    implementation_type,
                    type="di_registration",
                    lifetime=lifetime
                )
    
    async def _analyze_typescript_file(self, file_info: Dict[str, Any]) -> None:
        """Analyze TypeScript file for call graph and data flow
        
        Args:
            file_info: File information dictionary
        """
        file_path = file_info.get("file_path")
        is_angular = file_info.get("is_angular", False)
        
        # Add nodes for classes
        for cls in file_info.get("classes", []):
            class_name = cls.get("name")
            is_component = cls.get("is_component", False)
            is_service = cls.get("is_service", False)
            is_module = cls.get("is_module", False)
            
            # Determine node type
            node_type = "class"
            if is_component:
                node_type = "component"
            elif is_service:
                node_type = "service"
            elif is_module:
                node_type = "module"
            
            # Add class node to call graph
            self.call_graph.add_node(
                class_name,
                type=node_type,
                language="typescript",
                file_path=file_path,
                is_angular=is_angular
            )
            
            # Add method nodes and edges
            for method in cls.get("methods", []):
                method_name = method.get("name")
                method_node = f"{class_name}.{method_name}"
                
                # Add method node
                self.call_graph.add_node(
                    method_node,
                    type="method",
                    language="typescript",
                    file_path=file_path,
                    class_name=class_name
                )
                
                # Connect class to method
                self.call_graph.add_edge(
                    class_name,
                    method_node,
                    type="contains"
                )
        
        # Add import relationships
        for imp in file_info.get("imports", []):
            source = imp.get("source")
            imported_items = imp.get("imported_items", [])
            
            for item in imported_items:
                # Skip Angular core imports
                if source.startswith("@angular/"):
                    continue
                
                # Add import relationship
                if not self.call_graph.has_node(item):
                    self.call_graph.add_node(
                        item,
                        type="import",
                        language="typescript",
                        file_path="unknown"  # We don't know the file path of the imported item
                    )
                
                # For each class, add dependency on imported item
                for cls in file_info.get("classes", []):
                    class_name = cls.get("name")
                    
                    self.call_graph.add_edge(
                        class_name,
                        item,
                        type="imports",
                        source=source
                    )
    
    async def _analyze_javascript_file(self, file_info: Dict[str, Any]) -> None:
        """Analyze JavaScript file for call graph and data flow
        
        Args:
            file_info: File information dictionary
        """
        # For JavaScript, we'll use the same approach as TypeScript
        await self._analyze_typescript_file(file_info)
    
    async def _analyze_python_file(self, file_info: Dict[str, Any]) -> None:
        """Analyze Python file for call graph and data flow
        
        Args:
            file_info: File information dictionary
        """
        file_path = file_info.get("file_path")
        
        # Add nodes for classes
        for cls in file_info.get("classes", []):
            class_name = cls.get("name")
            bases = cls.get("bases", [])
            
            # Add class node to call graph
            self.call_graph.add_node(
                class_name,
                type="class",
                language="python",
                file_path=file_path
            )
            
            # Add inheritance relationships
            for base in bases:
                if not self.call_graph.has_node(base):
                    self.call_graph.add_node(
                        base,
                        type="class",
                        language="python",
                        file_path="unknown"  # We don't know the file path of the base class
                    )
                
                self.call_graph.add_edge(
                    class_name,
                    base,
                    type="inherits"
                )
            
            # Add method nodes and edges
            for method in cls.get("methods", []):
                method_name = method.get("name")
                is_async = method.get("is_async", False)
                method_node = f"{class_name}.{method_name}"
                
                # Add method node
                self.call_graph.add_node(
                    method_node,
                    type="method",
                    language="python",
                    file_path=file_path,
                    class_name=class_name,
                    is_async=is_async
                )
                
                # Connect class to method
                self.call_graph.add_edge(
                    class_name,
                    method_node,
                    type="contains"
                )
        
        # Add nodes for top-level functions
        for func in file_info.get("functions", []):
            func_name = func.get("name")
            is_async = func.get("is_async", False)
            
            # Add function node
            self.call_graph.add_node(
                func_name,
                type="function",
                language="python",
                file_path=file_path,
                is_async=is_async
            )
        
        # Add import relationships
        for imp in file_info.get("imports", []):
            module = imp.get("module")
            
            if not module:
                continue
                
            # Add import relationship
            if not self.call_graph.has_node(module):
                self.call_graph.add_node(
                    module,
                    type="module",
                    language="python",
                    file_path="unknown"  # We don't know the file path of the imported module
                )
            
            # For each class and top-level function, add dependency on imported module
            for cls in file_info.get("classes", []):
                class_name = cls.get("name")
                
                self.call_graph.add_edge(
                    class_name,
                    module,
                    type="imports"
                )
            
            for func in file_info.get("functions", []):
                func_name = func.get("name")
                
                self.call_graph.add_edge(
                    func_name,
                    module,
                    type="imports"
                )
    
    def _build_cross_file_relationships(self, files: List[Dict[str, Any]]) -> None:
        """Build relationships between components across files
        
        Args:
            files: List of file information dictionaries
        """
        # Match classes and interfaces between files
        class_map = {}  # Map of class name to node ID
        interface_map = {}  # Map of interface name to node ID
        
        # Build maps of classes and interfaces
        for node_id in self.call_graph.nodes():
            node_data = self.call_graph.nodes[node_id]
            node_type = node_data.get("type")
            
            if node_type == "class":
                # Extract class name from node ID (handle namespace.ClassName format)
                if "." in node_id:
                    class_name = node_id.split(".")[-1]
                else:
                    class_name = node_id
                
                if class_name not in class_map:
                    class_map[class_name] = []
                    
                class_map[class_name].append(node_id)
            
            elif node_type == "interface":
                # Extract interface name from node ID
                if "." in node_id:
                    interface_name = node_id.split(".")[-1]
                else:
                    interface_name = node_id
                
                if interface_name not in interface_map:
                    interface_map[interface_name] = []
                    
                interface_map[interface_name].append(node_id)
        
        # Find relationships between classes and interfaces
        for class_name, class_nodes in class_map.items():
            # Check if this class implements any interfaces
            for interface_name, interface_nodes in interface_map.items():
                for class_node in class_nodes:
                    class_data = self.call_graph.nodes[class_node]
                    
                    # Find related interfaces in the same namespace
                    for interface_node in interface_nodes:
                        interface_data = self.call_graph.nodes[interface_node]
                        
                        # Check if they're in the same namespace (for C#)
                        if (class_data.get("namespace") and 
                            interface_data.get("namespace") and 
                            class_data.get("namespace") == interface_data.get("namespace")):
                            
                            # Check inheritance relationships
                            if class_node in self.call_graph and interface_node in self.call_graph:
                                # Look for inheritance in C# files
                                file_path = class_data.get("file_path")
                                if file_path:
                                    try:
                                        with open(file_path, 'r', encoding='utf-8') as f:
                                            content = f.read()
                                            
                                            # Check if class implements interface
                                            pattern = f"class\\s+{class_name}\\s*:\\s*.*{interface_name}"
                                            if re.search(pattern, content):
                                                self.call_graph.add_edge(
                                                    class_node,
                                                    interface_node,
                                                    type="implements"
                                                )
                                    except Exception as e:
                                        self.logger.warning(f"Error reading file {file_path}: {str(e)}")
    
    def _generate_analysis_results(self) -> Dict[str, Any]:
        """Generate analysis results from call and data flow graphs
        
        Returns:
            Analysis results
        """
        # Basic statistics
        node_count = self.call_graph.number_of_nodes()
        edge_count = self.call_graph.number_of_edges()
        
        # Count node types
        node_types = {}
        for node_id in self.call_graph.nodes():
            node_data = self.call_graph.nodes[node_id]
            node_type = node_data.get("type", "unknown")
            
            if node_type not in node_types:
                node_types[node_type] = 0
                
            node_types[node_type] += 1
        
        # Count edge types
        edge_types = {}
        for src, dst, data in self.call_graph.edges(data=True):
            edge_type = data.get("type", "unknown")
            
            if edge_type not in edge_types:
                edge_types[edge_type] = 0
                
            edge_types[edge_type] += 1
        
        # Find central components (high degree centrality)
        centrality = nx.degree_centrality(self.call_graph)
        central_components = sorted(
            [(node, score) for node, score in centrality.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]  # Top 10 central components
        
        # Generate node and edge representations
        nodes = []
        for node_id in self.call_graph.nodes():
            node_data = self.call_graph.nodes[node_id]
            nodes.append({
                "id": node_id,
                "type": node_data.get("type", "unknown"),
                "code_language": node_data.get("code_language", "unknown"),
                "file_path": node_data.get("file_path", "unknown"),
                "degree": self.call_graph.degree(node_id)
            })
        
        edges = []
        for src, dst, data in self.call_graph.edges(data=True):
            edges.append({
                "source": src,
                "target": dst,
                "type": data.get("type", "unknown")
            })
        
        # Find potential architectural patterns
        patterns = self._identify_architectural_patterns()
        
        return {
            "summary": {
                "node_count": node_count,
                "edge_count": edge_count,
                "node_types": node_types,
                "edge_types": edge_types
            },
            "central_components": [
                {"id": node, "centrality": score} for node, score in central_components
            ],
            "patterns": patterns,
            "nodes": nodes,
            "edges": edges
        }
    
    def _identify_architectural_patterns(self) -> List[Dict[str, Any]]:
        """Identify architectural patterns in the call graph
        
        Returns:
            List of identified patterns
        """
        patterns = []
        
        # Check for MVC pattern
        mvc_sets = {
            "controllers": set(),
            "models": set(),
            "views": set()
        }

        for node_id in self.call_graph.nodes():
            node_data = self.call_graph.nodes[node_id]

            node_name = node_id.lower()
            class_name = str(node_data.get("class_name", "")).lower()
            file_path = str(node_data.get("file_path", "")).lower()

            # Determine if this node represents a controller, model, or view
            if (
                "controller" in node_name
                or "controller" in class_name
                or "controllers" in file_path
            ):
                mvc_sets["controllers"].add(node_id)
            elif (
                "model" in node_name
                or "model" in class_name
                or "models" in file_path
            ):
                mvc_sets["models"].add(node_id)
            elif (
                "view" in node_name
                or "view" in class_name
                or "views" in file_path
            ):
                mvc_sets["views"].add(node_id)

        mvc_components = {k: len(v) for k, v in mvc_sets.items()}
        
        # If we have all three MVC components, it's likely an MVC pattern
        if all(count > 0 for count in mvc_components.values()):
            patterns.append({
                "name": "MVC (Model-View-Controller)",
                "confidence": "high" if min(mvc_components.values()) > 2 else "medium",
                "components": mvc_components
            })
        
        # Check for Repository pattern
        repository_count = sum(1 for node_id in self.call_graph.nodes() if "repository" in node_id.lower())
        if repository_count > 0:
            patterns.append({
                "name": "Repository Pattern",
                "confidence": "high" if repository_count > 2 else "medium",
                "components": {"repositories": repository_count}
            })
        
        # Check for Service pattern
        service_count = sum(1 for node_id in self.call_graph.nodes() if "service" in node_id.lower())
        if service_count > 0:
            patterns.append({
                "name": "Service Pattern",
                "confidence": "high" if service_count > 2 else "medium",
                "components": {"services": service_count}
            })
        
        # Check for Factory pattern
        factory_count = sum(1 for node_id in self.call_graph.nodes() if "factory" in node_id.lower())
        if factory_count > 0:
            patterns.append({
                "name": "Factory Pattern",
                "confidence": "medium",
                "components": {"factories": factory_count}
            })
        
        # Check for Dependency Injection
        di_edges = [
            (src, dst) for src, dst, data in self.call_graph.edges(data=True)
            if data.get("type") == "di_registration"
        ]
        
        if di_edges:
            patterns.append({
                "name": "Dependency Injection",
                "confidence": "high",
                "components": {"di_registrations": len(di_edges)}
            })
        
        return patterns

    def export_graph_to_json(self, output_path: str) -> str:
        """Export the call graph to a JSON file for visualization
        
        Args:
            output_path: Path to save the JSON file
            
        Returns:
            Path to the saved file
        """
        # Convert graph to a format suitable for visualization
        data = {
            "nodes": [],
            "links": []
        }
        
        # Add nodes
        for node_id in self.call_graph.nodes():
            node_data = self.call_graph.nodes[node_id]
            data["nodes"].append({
                "id": node_id,
                "type": node_data.get("type", "unknown"),
                "code_language": node_data.get("code_language", "unknown"),
                "file_path": node_data.get("file_path", "unknown")
            })
        
        # Add edges (links)
        for src, dst, edge_data in self.call_graph.edges(data=True):
            data["links"].append({
                "source": src,
                "target": dst,
                "type": edge_data.get("type", "unknown")
            })
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return output_path

    def get_component_dependencies(self, component_id: str) -> Dict[str, Any]:
        """Get dependencies for a specific component
        
        Args:
            component_id: ID of the component
            
        Returns:
            Dependencies information
        """
        if component_id not in self.call_graph:
            return {
                "error": f"Component {component_id} not found in the call graph"
            }
        
        # Get incoming edges (things that depend on this component)
        incoming = []
        for src, dst in self.call_graph.in_edges(component_id):
            edge_data = self.call_graph.get_edge_data(src, dst)
            incoming.append({
                "component": src,
                "type": edge_data.get("type", "unknown")
            })
        
        # Get outgoing edges (things this component depends on)
        outgoing = []
        for src, dst in self.call_graph.out_edges(component_id):
            edge_data = self.call_graph.get_edge_data(src, dst)
            outgoing.append({
                "component": dst,
                "type": edge_data.get("type", "unknown")
            })
        
        return {
            "component": component_id,
            "type": self.call_graph.nodes[component_id].get("type", "unknown"),
            "code_language": self.call_graph.nodes[component_id].get("code_language", "unknown"),
            "file_path": self.call_graph.nodes[component_id].get("file_path", "unknown"),
            "dependencies": {
                "incoming": incoming,
                "outgoing": outgoing
            }
        }
