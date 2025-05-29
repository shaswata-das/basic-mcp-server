"""
Markdown Documentation Builder for MCP Server

This module provides documentation generation capabilities from extracted code knowledge.
It creates Markdown files for AI-assisted development and documentation.
"""

import os
import logging
import json
import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path

class MarkdownBuilder:
    """Builds Markdown documentation from extracted code knowledge"""
    
    def __init__(self):
        """Initialize the Markdown builder"""
        self.logger = logging.getLogger("mcp_server.services.knowledge_extraction.md_builder")
    
    async def generate_documentation(
        self, 
        repo_id: str, 
        extracted_knowledge: Dict[str, Any],
        output_dir: str
    ) -> Dict[str, Any]:
        """Generate Markdown documentation from extracted knowledge
        
        Args:
            repo_id: Repository ID
            extracted_knowledge: Extracted knowledge from code analysis
            output_dir: Directory to store generated documentation
            
        Returns:
            Information about generated documentation
        """
        self.logger.info(f"Generating documentation for repository {repo_id}")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Create directory structure for documentation
        docs_dir = os.path.join(output_dir, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        
        structure_dir = os.path.join(docs_dir, "structure")
        architecture_dir = os.path.join(docs_dir, "architecture")
        patterns_dir = os.path.join(docs_dir, "patterns")
        dependencies_dir = os.path.join(docs_dir, "dependencies")
        
        os.makedirs(structure_dir, exist_ok=True)
        os.makedirs(architecture_dir, exist_ok=True)
        os.makedirs(patterns_dir, exist_ok=True)
        os.makedirs(dependencies_dir, exist_ok=True)
        
        # Generate documentation files
        await self._generate_overview(extracted_knowledge, docs_dir)
        await self._generate_structure_docs(extracted_knowledge, structure_dir)
        await self._generate_pattern_docs(extracted_knowledge, patterns_dir)
        await self._generate_architecture_docs(extracted_knowledge, architecture_dir)
        await self._generate_dependencies_docs(extracted_knowledge, dependencies_dir)
        
        return {
            "status": "success",
            "repository_id": repo_id,
            "documentation_dir": docs_dir,
            "files_generated": 5  # Base number of files generated
        }
    
    async def _generate_overview(
        self, 
        knowledge: Dict[str, Any],
        docs_dir: str
    ) -> None:
        """Generate overview documentation
        
        Args:
            knowledge: Extracted knowledge
            docs_dir: Directory to store documentation
        """
        # Extract repository name and high-level info
        repo_name = knowledge.get("repo_name", "Repository")
        
        # Create README.md with repository overview
        readme_content = f"""# {repo_name}

## Repository Overview

This documentation provides an AI-friendly overview of the {repo_name} codebase.

### Key Statistics

- **Files Analyzed**: {knowledge.get("file_count", 0)}
"""

        # Add pattern info if available
        patterns = knowledge.get("patterns", {})
        if patterns:
            code_org = patterns.get("code_organization", [])
            if code_org:
                readme_content += f"- **Code Organization**: {', '.join([p.get('name') for p in code_org])}\n"

        # Add environment info if available
        env = knowledge.get("environment", {})
        if env:
            frameworks = env.get("frameworks", [])
            if frameworks:
                readme_content += f"- **Main Frameworks**: {', '.join(frameworks)}\n"
            
            package_managers = env.get("package_managers", [])
            if package_managers:
                readme_content += f"- **Package Managers**: {', '.join(package_managers)}\n"

        readme_content += """
### Documentation Sections

- [Code Structure](./structure/README.md) - Overview of code organization and key components
- [Architecture](./architecture/README.md) - Architectural patterns and system design
- [Patterns](./patterns/README.md) - Design patterns and code patterns used
- [Dependencies](./dependencies/README.md) - External dependencies and frameworks

### How to Use This Documentation

This documentation is structured to help AI tools understand the codebase quickly. Each section provides information about different aspects of the code, including structure, patterns, and dependencies.
"""
        
        with open(os.path.join(docs_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write(readme_content)
    
    async def _generate_structure_docs(
        self, 
        knowledge: Dict[str, Any],
        structure_dir: str
    ) -> None:
        """Generate code structure documentation
        
        Args:
            knowledge: Extracted knowledge
            structure_dir: Directory to store structure documentation
        """
        # Create README for structure directory
        structure_readme = """# Code Structure

This section documents the code structure, including key components, namespaces, and their relationships.

## Key Components

The codebase is organized into the following main components:

"""
        
        # Add information about extracted files
        files = knowledge.get("files", [])
        if files:
            # Collect namespaces
            namespaces = {}
            for file in files:
                namespace = file.get("namespace", "Unknown")
                if namespace not in namespaces:
                    namespaces[namespace] = []
                
                namespaces[namespace].append({
                    "file_path": file.get("file_path", ""),
                    "classes": file.get("classes", []),
                    "interfaces": file.get("interfaces", [])
                })
            
            # Add namespaces to documentation
            structure_readme += "### Namespaces\n\n"
            for namespace, ns_files in namespaces.items():
                structure_readme += f"#### {namespace}\n\n"
                
                class_count = sum(len(f.get("classes", [])) for f in ns_files)
                interface_count = sum(len(f.get("interfaces", [])) for f in ns_files)
                
                structure_readme += f"- Files: {len(ns_files)}\n"
                structure_readme += f"- Classes: {class_count}\n"
                structure_readme += f"- Interfaces: {interface_count}\n\n"
                
                # Add detailed namespace page if there are classes
                if class_count > 0:
                    namespace_file = os.path.join(structure_dir, f"{namespace.replace('.', '_')}.md")
                    with open(namespace_file, "w", encoding="utf-8") as f:
                        f.write(f"# Namespace: {namespace}\n\n")
                        
                        f.write("## Classes\n\n")
                        for ns_file in ns_files:
                            for cls in ns_file.get("classes", []):
                                f.write(f"### {cls.get('name')}\n\n")
                                
                                # Add inheritance
                                inheritance = cls.get("inheritance", [])
                                if inheritance:
                                    f.write(f"**Inherits from**: {', '.join(inheritance)}\n\n")
                                else:
                                    f.write("**No inheritance**\n\n")
                                
                                # Add methods
                                methods = cls.get("methods", [])
                                if methods:
                                    f.write("#### Methods\n\n")
                                    for method in methods:
                                        params = method.get("parameters", [])
                                        f.write(f"- `{method.get('name')}({', '.join(params)})`\n")
                                    f.write("\n")
                                
                                # Add properties
                                properties = cls.get("properties", [])
                                if properties:
                                    f.write("#### Properties\n\n")
                                    for prop in properties:
                                        f.write(f"- `{prop.get('name')}`\n")
                                    f.write("\n")
                                
                                f.write(f"**File**: {ns_file.get('file_path')}\n\n")
                        
                        # Add interfaces
                        if interface_count > 0:
                            f.write("## Interfaces\n\n")
                            for ns_file in ns_files:
                                for interface in ns_file.get("interfaces", []):
                                    f.write(f"### {interface.get('name')}\n\n")
                                    f.write(f"**File**: {ns_file.get('file_path')}\n\n")
                    
                    # Link to the namespace file
                    structure_readme += f"[View {namespace} details](./{namespace.replace('.', '_')}.md)\n\n"
        else:
            structure_readme += "No detailed structure information available.\n"
        
        # Write structure README
        with open(os.path.join(structure_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write(structure_readme)
    
    async def _generate_pattern_docs(
        self, 
        knowledge: Dict[str, Any],
        patterns_dir: str
    ) -> None:
        """Generate pattern documentation
        
        Args:
            knowledge: Extracted knowledge
            patterns_dir: Directory to store pattern documentation
        """
        patterns = knowledge.get("patterns", {})
        
        # Create README for patterns directory
        patterns_readme = """# Design and Architecture Patterns

This section documents the design patterns, architectural patterns, and code organization patterns used in the codebase.

"""
        
        # Add design patterns
        patterns_readme += "## Design Patterns\n\n"
        design_patterns = patterns.get("design_patterns", [])
        if design_patterns:
            for pattern in design_patterns:
                patterns_readme += f"### {pattern.get('name')}\n\n"
                patterns_readme += f"**Confidence**: {pattern.get('confidence')}\n\n"
                patterns_readme += f"**Sources**: {', '.join(pattern.get('sources', []))}\n\n"
        else:
            patterns_readme += "No specific design patterns were detected in the codebase.\n\n"
        
        # Add architectural patterns
        patterns_readme += "## Architectural Patterns\n\n"
        arch_patterns = patterns.get("architectural_patterns", [])
        if arch_patterns:
            for pattern in arch_patterns:
                patterns_readme += f"### {pattern.get('name')}\n\n"
                patterns_readme += f"**Confidence**: {pattern.get('confidence')}\n\n"
                patterns_readme += f"**Sources**: {', '.join(pattern.get('sources', []))}\n\n"
        else:
            patterns_readme += "No specific architectural patterns were detected in the codebase.\n\n"
        
        # Add code organization patterns
        patterns_readme += "## Code Organization\n\n"
        org_patterns = patterns.get("code_organization", [])
        if org_patterns:
            for pattern in org_patterns:
                patterns_readme += f"### {pattern.get('name')}\n\n"
                patterns_readme += f"**Confidence**: {pattern.get('confidence')}\n\n"
                patterns_readme += f"**Sources**: {', '.join(pattern.get('sources', []))}\n\n"
                
                # Add descriptions based on pattern type
                if pattern.get('name') == "Feature-based Organization":
                    patterns_readme += """**Description**: The code is organized around features or business capabilities, with each feature having its own directory containing all related components. This promotes high cohesion within features and clear boundaries between them.\n\n"""
                elif pattern.get('name') == "Layer-based Organization":
                    patterns_readme += """**Description**: The code is organized in horizontal layers (e.g., presentation, business logic, data access). This separation promotes a clear distinction of responsibilities and allows for easier maintenance and testing of each layer.\n\n"""
                elif pattern.get('name') == "Component-based Organization":
                    patterns_readme += """**Description**: The code is organized around reusable components, each with a specific responsibility. Components can be composed to build features, promoting reusability and separation of concerns.\n\n"""
        else:
            patterns_readme += "No specific code organization patterns were detected in the codebase.\n\n"
        
        # Add language-specific patterns
        lang_patterns = patterns.get("language_specific", {})
        if lang_patterns:
            patterns_readme += "## Language-Specific Patterns\n\n"
            
            for language, language_patterns in lang_patterns.items():
                patterns_readme += f"### {language.capitalize()} Patterns\n\n"
                
                if language_patterns:
                    for pattern in language_patterns:
                        patterns_readme += f"#### {pattern.get('name')}\n\n"
                        patterns_readme += f"**Confidence**: {pattern.get('confidence')}\n\n"
                        patterns_readme += f"**Sources**: {', '.join(pattern.get('sources', []))}\n\n"
                else:
                    patterns_readme += f"No specific {language} patterns were detected.\n\n"
        
        # Write patterns README
        with open(os.path.join(patterns_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write(patterns_readme)
    
    async def _generate_architecture_docs(
        self, 
        knowledge: Dict[str, Any],
        architecture_dir: str
    ) -> None:
        """Generate architecture documentation
        
        Args:
            knowledge: Extracted knowledge
            architecture_dir: Directory to store architecture documentation
        """
        # Create README for architecture directory
        architecture_readme = """# Architecture Overview

This section documents the overall architecture of the system, including layers, components, and their interactions.

## System Architecture

"""
        
        # Add information about architecture based on call graphs and patterns
        call_graph = knowledge.get("call_graph", {})
        if call_graph:
            architecture_readme += f"""### Component Relationships

The system has {call_graph.get("node_count", 0)} components with {call_graph.get("edge_count", 0)} relationships between them.

#### Central Components

The following components are central to the system architecture:

"""
            
            for component in call_graph.get("central_components", [])[:5]:
                architecture_readme += f"- {component}\n"
        
        # Add information from patterns
        patterns = knowledge.get("patterns", {})
        arch_patterns = patterns.get("architectural_patterns", [])
        
        if arch_patterns:
            architecture_readme += "\n## Architectural Patterns\n\n"
            
            for pattern in arch_patterns:
                architecture_readme += f"### {pattern.get('name')}\n\n"
                architecture_readme += f"**Confidence**: {pattern.get('confidence')}\n\n"
                
                # Add descriptions based on pattern type
                if pattern.get('name') == "Layered Architecture":
                    architecture_readme += """**Description**: The application is divided into horizontal layers, each with a specific responsibility. Layers typically include presentation, business logic, and data access.\n\n"""
                    architecture_readme += """
```
┌─────────────────────┐
│  Presentation Layer │
├─────────────────────┤
│  Business Layer     │
├─────────────────────┤
│  Data Access Layer  │
└─────────────────────┘
```
"""
                elif pattern.get('name') == "Microservices":
                    architecture_readme += """**Description**: The application is divided into small, independently deployable services, each focused on a specific business capability.\n\n"""
                    architecture_readme += """
```
┌─────────┐   ┌─────────┐   ┌─────────┐
│ Service │   │ Service │   │ Service │
│    A    │   │    B    │   │    C    │
└─────────┘   └─────────┘   └─────────┘
      │            │             │
      └────────────┼─────────────┘
                   │
            ┌─────────────┐
            │    API      │
            │   Gateway   │
            └─────────────┘
```
"""
                elif pattern.get('name') == "MVC":
                    architecture_readme += """**Description**: The Model-View-Controller pattern separates the application into three components: Model (data), View (user interface), and Controller (handles user input).\n\n"""
                    architecture_readme += """
```
┌─────────────┐       ┌─────────────┐
│             │       │             │
│    Model    │◄─────►│ Controller  │
│             │       │             │
└─────────────┘       └──────┬──────┘
                             │
                             ▼
                      ┌─────────────┐
                      │             │
                      │    View     │
                      │             │
                      └─────────────┘
```
"""
        else:
            architecture_readme += "\nNo specific architectural patterns were detected in the codebase.\n"
        
        # Write architecture README
        with open(os.path.join(architecture_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write(architecture_readme)
    
    async def _generate_dependencies_docs(
        self, 
        knowledge: Dict[str, Any],
        dependencies_dir: str
    ) -> None:
        """Generate dependencies documentation
        
        Args:
            knowledge: Extracted knowledge
            dependencies_dir: Directory to store dependencies documentation
        """
        # Create README for dependencies directory
        dependencies_readme = """# Dependencies and Environment

This section documents the dependencies, frameworks, and environment requirements of the codebase.

"""
        
        # Add information about environment
        env = knowledge.get("environment", {})
        if env:
            dependencies_readme += "## Package Managers\n\n"
            
            package_managers = env.get("package_managers", [])
            if package_managers:
                for pm in package_managers:
                    dependencies_readme += f"- {pm}\n"
            else:
                dependencies_readme += "No package managers detected.\n"
            
            # Add build systems
            dependencies_readme += "\n## Build Systems\n\n"
            
            build_systems = env.get("build_systems", [])
            if build_systems:
                for bs in build_systems:
                    dependencies_readme += f"- {bs}\n"
            else:
                dependencies_readme += "No build systems detected.\n"
            
            # Add frameworks
            dependencies_readme += "\n## Frameworks\n\n"
            
            frameworks = env.get("frameworks", [])
            if frameworks:
                for fw in frameworks:
                    dependencies_readme += f"- {fw}\n"
            else:
                dependencies_readme += "No frameworks detected.\n"
            
            # Add dependencies details
            dependencies = env.get("dependencies", {})
            if dependencies:
                dependencies_readme += "\n## Dependencies Details\n\n"
                
                for dep_type, deps in dependencies.items():
                    dependencies_readme += f"### {dep_type.capitalize()} Dependencies\n\n"
                    
                    if isinstance(deps, dict):
                        # Format package dependencies
                        if dep_type == "dotnet" and "packages" in deps:
                            dependencies_readme += "| Package | Version |\n"
                            dependencies_readme += "|---------|--------|\n"
                            
                            packages = deps.get("packages", {})
                            for package, version in list(packages.items())[:20]:  # Limit to 20 for readability
                                dependencies_readme += f"| {package} | {version} |\n"
                            
                            if len(packages) > 20:
                                dependencies_readme += f"\n*... and {len(packages) - 20} more packages*\n"
                        else:
                            # Generic formatting for other dependency types
                            for key, value in deps.items():
                                dependencies_readme += f"- **{key}**: {value}\n"
                    elif isinstance(deps, list):
                        # Format list of dependencies
                        for dep in deps:
                            dependencies_readme += f"- {dep}\n"
                    
                    dependencies_readme += "\n"
            
            # Add container configurations
            container_configs = env.get("container_configs", [])
            if container_configs:
                dependencies_readme += "## Container Configurations\n\n"
                
                for config in container_configs:
                    config_type = config.get("type", "unknown")
                    dependencies_readme += f"- {config_type.capitalize()}: {config.get('file', '')}\n"
                    
                    if config_type == "docker" and "base_image" in config:
                        dependencies_readme += f"  - Base image: {config.get('base_image')}\n"
        else:
            dependencies_readme += "No environment information available.\n"
        
        # Write dependencies README
        with open(os.path.join(dependencies_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write(dependencies_readme)
