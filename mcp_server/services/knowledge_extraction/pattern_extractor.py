"""
Pattern Extractor for MCP Server

This module provides development pattern extraction capabilities.
It identifies common software design patterns, architectural patterns,
and code organization approaches in the codebase.
"""

import os
import logging
import re
import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
import json

class PatternExtractor:
    """Extracts development patterns from code"""
    
    def __init__(self):
        """Initialize the pattern extractor"""
        self.logger = logging.getLogger("mcp_server.services.knowledge_extraction.pattern_extractor")
        self.patterns_found = {}
    
    async def extract_patterns(
        self,
        repo_path: str,
        files: List[Dict[str, Any]],
        call_graph_results: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract development patterns from a codebase
        
        Args:
            repo_path: Path to the repository
            files: List of file information dictionaries
            call_graph_results: Optional call graph analysis results
            language: Optional language filter
            
        Returns:
            Extracted patterns
        """
        self.logger.info(f"Starting pattern extraction for repository: {repo_path}")
        
        # Reset patterns
        self.patterns_found = {
            "design_patterns": [],
            "architectural_patterns": [],
            "code_organization": [],
            "language_specific": {}
        }
        
        # Filter files by language if specified
        if language:
            files = [f for f in files if f.get("code_language", "").lower() == language.lower()]
        
        # First, analyze all files
        for file_info in files:
            language = file_info.get("code_language", "unknown").lower()
            
            # Extract patterns based on language
            if language in ["csharp", "cs", "c#"]:
                await self._extract_csharp_patterns(file_info)
            elif language in ["typescript", "ts", "javascript", "js"]:
                await self._extract_typescript_patterns(file_info)
            elif language in ["python", "py"]:
                await self._extract_python_patterns(file_info)
        
        # Incorporate call graph results if available
        if call_graph_results:
            self._analyze_call_graph_patterns(call_graph_results)
        
        # Analyze folder structure for code organization patterns
        await self._analyze_folder_structure(repo_path)
        
        # Remove duplicates and calculate confidence
        self._deduplicate_patterns()
        
        return self.patterns_found
    
    async def _extract_csharp_patterns(self, file_info: Dict[str, Any]) -> None:
        """Extract patterns from C# code
        
        Args:
            file_info: File information dictionary
        """
        file_path = file_info.get("file_path")
        content = ""
        
        # Read file content if not already in file_info
        if "content" in file_info:
            content = file_info["content"]
        else:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                self.logger.warning(f"Failed to read file {file_path}: {str(e)}")
                return
        
        # Initialize C# specific patterns if not exists
        if "csharp" not in self.patterns_found["language_specific"]:
            self.patterns_found["language_specific"]["csharp"] = []
        
        # Check for Factory pattern
        if re.search(r'class\s+\w*Factory\b', content, re.IGNORECASE):
            self._add_design_pattern("Factory Pattern", "high", file_path)
        
        # Check for Repository pattern
        if re.search(r'class\s+\w*Repository\b', content, re.IGNORECASE) or re.search(r'interface\s+I\w*Repository\b', content, re.IGNORECASE):
            self._add_design_pattern("Repository Pattern", "high", file_path)
        
        # Check for Unit of Work pattern
        if re.search(r'class\s+\w*UnitOfWork\b', content, re.IGNORECASE) or re.search(r'interface\s+I\w*UnitOfWork\b', content, re.IGNORECASE):
            self._add_design_pattern("Unit of Work Pattern", "high", file_path)
        
        # Check for Dependency Injection
        if (re.search(r'services\.Add\w+<', content) or 
            re.search(r'constructor\s*\(\s*[^)]*\b(?:I\w+)\s+\w+\s*[,)]', content)):
            self._add_design_pattern("Dependency Injection", "high", file_path)
            self._add_architectural_pattern("Inversion of Control", "high", file_path)
        
        # Check for CQRS pattern (Command Query Responsibility Segregation)
        if (re.search(r'class\s+\w*Command\b', content, re.IGNORECASE) or 
            re.search(r'class\s+\w*Query\b', content, re.IGNORECASE) or 
            re.search(r'interface\s+I\w*Handler\b', content, re.IGNORECASE)):
            self._add_architectural_pattern("CQRS", "medium", file_path)
        
        # Check for MVC/MVVM/MVP patterns
        if re.search(r'class\s+\w*Controller\b', content, re.IGNORECASE):
            self._add_architectural_pattern("MVC", "high", file_path)
        
        if re.search(r'class\s+\w*ViewModel\b', content, re.IGNORECASE):
            self._add_architectural_pattern("MVVM", "high", file_path)
        
        # Check for Mediator pattern
        if re.search(r'class\s+\w*Mediator\b', content, re.IGNORECASE) or re.search(r'interface\s+I\w*Mediator\b', content, re.IGNORECASE):
            self._add_design_pattern("Mediator Pattern", "high", file_path)
        
        # Check for Observer pattern
        if re.search(r'event\s+\w+\s+\w+', content) or re.search(r'\.Subscribe\(', content):
            self._add_design_pattern("Observer Pattern", "medium", file_path)
        
        # Check for Strategy pattern
        if re.search(r'interface\s+I\w*Strategy\b', content, re.IGNORECASE):
            self._add_design_pattern("Strategy Pattern", "high", file_path)
        
        # Check for C# specific patterns
        if re.search(r'\.ConfigureAwait\(false\)', content):
            self._add_language_specific_pattern("csharp", "ConfigureAwait Pattern", "high", file_path)
        
        if re.search(r'\.ToList\(\)', content) or re.search(r'\.ToArray\(\)', content):
            self._add_language_specific_pattern("csharp", "LINQ Materialization", "medium", file_path)
        
        if re.search(r'class\s+\w+\s*:\s*DbContext', content):
            self._add_language_specific_pattern("csharp", "Entity Framework", "high", file_path)
        
        if re.search(r'\.Add\(new\s+TypeRegistration\(typeof\(\w+\),\s*typeof\(\w+\),', content):
            self._add_design_pattern("Service Locator Pattern", "high", file_path)
    
    async def _extract_typescript_patterns(self, file_info: Dict[str, Any]) -> None:
        """Extract patterns from TypeScript/JavaScript code
        
        Args:
            file_info: File information dictionary
        """
        file_path = file_info.get("file_path")
        content = ""
        
        # Read file content if not already in file_info
        if "content" in file_info:
            content = file_info["content"]
        else:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                self.logger.warning(f"Failed to read file {file_path}: {str(e)}")
                return
        
        # Initialize TypeScript specific patterns if not exists
        if "typescript" not in self.patterns_found["language_specific"]:
            self.patterns_found["language_specific"]["typescript"] = []
        
        # Check for Angular patterns
        is_angular = file_info.get("is_angular", False) or "@angular" in content
        
        if is_angular:
            # Check for Angular Component
            if re.search(r'@Component\(\s*{', content):
                self._add_language_specific_pattern("typescript", "Angular Component", "high", file_path)
            
            # Check for Angular Service
            if re.search(r'@Injectable\(\s*{', content):
                self._add_language_specific_pattern("typescript", "Angular Service", "high", file_path)
                self._add_design_pattern("Dependency Injection", "high", file_path)
            
            # Check for Angular Module
            if re.search(r'@NgModule\(\s*{', content):
                self._add_language_specific_pattern("typescript", "Angular Module", "high", file_path)
            
            # Check for Angular Routing
            if re.search(r'RouterModule\.forRoot\(', content) or re.search(r'RouterModule\.forChild\(', content):
                self._add_language_specific_pattern("typescript", "Angular Routing", "high", file_path)
            
            # Check for Angular Reactive Forms
            if re.search(r'FormBuilder', content) or re.search(r'FormGroup', content) or re.search(r'FormControl', content):
                self._add_language_specific_pattern("typescript", "Angular Reactive Forms", "high", file_path)
            
            # Check for Angular Template-driven Forms
            if re.search(r'ngModel', content) or re.search(r'ngForm', content):
                self._add_language_specific_pattern("typescript", "Angular Template-driven Forms", "high", file_path)
            
            # Check for Angular HTTP Client
            if re.search(r'HttpClient', content):
                self._add_language_specific_pattern("typescript", "Angular HTTP Client", "high", file_path)
        
        # Check for React patterns
        is_react = "react" in content.lower() or "jsx" in content.lower()
        
        if is_react:
            # Check for React Component
            if re.search(r'class\s+\w+\s+extends\s+(?:React\.)?Component', content) or re.search(r'function\s+\w+\s*\([^)]*\)\s*{[^}]*return\s*\(', content):
                self._add_language_specific_pattern("typescript", "React Component", "high", file_path)
            
            # Check for React Hooks
            if re.search(r'useState\(', content) or re.search(r'useEffect\(', content) or re.search(r'useContext\(', content):
                self._add_language_specific_pattern("typescript", "React Hooks", "high", file_path)
            
            # Check for Redux
            if re.search(r'createStore', content) or re.search(r'combineReducers', content) or re.search(r'useSelector', content) or re.search(r'useDispatch', content):
                self._add_language_specific_pattern("typescript", "Redux", "high", file_path)
                self._add_architectural_pattern("Flux/Redux", "high", file_path)
        
        # Check for general TypeScript/JavaScript patterns
        
        # Factory pattern
        if re.search(r'class\s+\w*Factory\b', content, re.IGNORECASE) or re.search(r'function\s+\w*Factory\b', content, re.IGNORECASE):
            self._add_design_pattern("Factory Pattern", "high", file_path)
        
        # Singleton pattern
        if (re.search(r'static\s+instance', content) or 
            re.search(r'private\s+constructor', content) or 
            re.search(r'getInstance\(\)', content)):
            self._add_design_pattern("Singleton Pattern", "high", file_path)
        
        # Observer pattern
        if re.search(r'\.subscribe\(', content) or re.search(r'\.addEventListener\(', content) or re.search(r'Subject<', content):
            self._add_design_pattern("Observer Pattern", "high", file_path)
        
        # Module pattern
        if re.search(r'export\s+const', content) or re.search(r'export\s+function', content) or re.search(r'export\s+class', content):
            self._add_design_pattern("Module Pattern", "medium", file_path)
        
        # Promise/async-await
        if re.search(r'new\s+Promise\(', content) or re.search(r'async\s+function', content) or re.search(r'await\s+', content):
            self._add_language_specific_pattern("typescript", "Promise/Async-Await", "high", file_path)
    
    async def _extract_python_patterns(self, file_info: Dict[str, Any]) -> None:
        """Extract patterns from Python code
        
        Args:
            file_info: File information dictionary
        """
        file_path = file_info.get("file_path")
        content = ""
        
        # Read file content if not already in file_info
        if "content" in file_info:
            content = file_info["content"]
        else:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                self.logger.warning(f"Failed to read file {file_path}: {str(e)}")
                return
        
        # Initialize Python specific patterns if not exists
        if "python" not in self.patterns_found["language_specific"]:
            self.patterns_found["language_specific"]["python"] = []
        
        # Check for Factory pattern
        if re.search(r'class\s+\w*Factory\b', content, re.IGNORECASE) or re.search(r'def\s+create_\w+\(', content, re.IGNORECASE):
            self._add_design_pattern("Factory Pattern", "high", file_path)
        
        # Check for Singleton pattern
        if re.search(r'__instance\s*=\s*None', content) or re.search(r'instance\s*=\s*None', content) or re.search(r'cls\._\w+\s*=\s*cls\(', content):
            self._add_design_pattern("Singleton Pattern", "high", file_path)
        
        # Check for Decorator pattern
        if re.search(r'def\s+\w+\s*\(\s*\w+\s*\)\s*:\s*\n\s*def\s+wrapper', content) or re.search(r'@\w+', content):
            self._add_design_pattern("Decorator Pattern", "high", file_path)
        
        # Check for Strategy pattern
        if re.search(r'class\s+\w+Strategy\b', content, re.IGNORECASE):
            self._add_design_pattern("Strategy Pattern", "high", file_path)
        
        # Check for Observer pattern
        if re.search(r'def\s+notify\(', content) or re.search(r'def\s+update\(', content) or re.search(r'observers\s*=\s*\[\]', content):
            self._add_design_pattern("Observer Pattern", "medium", file_path)
        
        # Check for Python web frameworks
        if re.search(r'from\s+flask\s+import', content) or re.search(r'app\s*=\s*Flask\(', content):
            self._add_language_specific_pattern("python", "Flask Framework", "high", file_path)
            self._add_architectural_pattern("MVC", "medium", file_path)
        
        if re.search(r'from\s+django', content) or re.search(r'from\s+rest_framework', content):
            self._add_language_specific_pattern("python", "Django Framework", "high", file_path)
            self._add_architectural_pattern("MVT", "high", file_path)  # Model-View-Template
        
        # Check for FastAPI
        if re.search(r'from\s+fastapi\s+import', content) or re.search(r'app\s*=\s*FastAPI\(', content):
            self._add_language_specific_pattern("python", "FastAPI Framework", "high", file_path)
        
        # Check for ORM usage
        if re.search(r'from\s+sqlalchemy', content) or re.search(r'db\.Column', content):
            self._add_language_specific_pattern("python", "SQLAlchemy ORM", "high", file_path)
        
        if re.search(r'from\s+django\.db\s+import\s+models', content) or re.search(r'class\s+\w+\(models\.Model\)', content):
            self._add_language_specific_pattern("python", "Django ORM", "high", file_path)
        
        # Check for async patterns
        if re.search(r'async\s+def', content) or re.search(r'await\s+', content) or re.search(r'asyncio', content):
            self._add_language_specific_pattern("python", "Asyncio", "high", file_path)
        
        # Check for typing
        if re.search(r'from\s+typing\s+import', content):
            self._add_language_specific_pattern("python", "Type Annotations", "high", file_path)
        
        # Check for dataclasses
        if re.search(r'@dataclass', content) or re.search(r'from\s+dataclasses\s+import', content):
            self._add_language_specific_pattern("python", "Dataclasses", "high", file_path)
    
    def _analyze_call_graph_patterns(self, call_graph_results: Dict[str, Any]) -> None:
        """Analyze call graph results for architectural patterns
        
        Args:
            call_graph_results: Call graph analysis results
        """
        # Extract patterns already identified in the call graph
        patterns = call_graph_results.get("patterns", [])
        
        for pattern in patterns:
            pattern_name = pattern.get("name")
            confidence = pattern.get("confidence", "medium")
            
            if "MVC" in pattern_name:
                self._add_architectural_pattern("MVC", confidence, "call_graph_analysis")
            elif "Repository" in pattern_name:
                self._add_design_pattern("Repository Pattern", confidence, "call_graph_analysis")
            elif "Service" in pattern_name:
                self._add_design_pattern("Service Pattern", confidence, "call_graph_analysis")
            elif "Factory" in pattern_name:
                self._add_design_pattern("Factory Pattern", confidence, "call_graph_analysis")
            elif "Dependency Injection" in pattern_name:
                self._add_design_pattern("Dependency Injection", confidence, "call_graph_analysis")
        
        # Analyze graph structure for layered architecture
        nodes = call_graph_results.get("nodes", [])
        
        controllers = sum(1 for node in nodes if "controller" in node.get("id", "").lower())
        services = sum(1 for node in nodes if "service" in node.get("id", "").lower())
        repositories = sum(1 for node in nodes if "repository" in node.get("id", "").lower() or "dao" in node.get("id", "").lower())
        models = sum(1 for node in nodes if "model" in node.get("id", "").lower() or "entity" in node.get("id", "").lower())
        
        # Check for layered architecture
        if controllers > 0 and services > 0 and (repositories > 0 or models > 0):
            self._add_architectural_pattern("Layered Architecture", "high", "call_graph_analysis")
        
        # Check for hexagonal/clean architecture
        interfaces = sum(1 for node in nodes if node.get("type") == "interface")
        implementations = sum(1 for node in nodes if node.get("type") == "class" and "impl" in node.get("id", "").lower())
        
        if interfaces > 5 and implementations > 5:
            self._add_architectural_pattern("Hexagonal/Clean Architecture", "medium", "call_graph_analysis")
    
    async def _analyze_folder_structure(self, repo_path: str) -> None:
        """Analyze repository folder structure for code organization patterns
        
        Args:
            repo_path: Path to the repository
        """
        try:
            # Get all directories in the repository
            directories = []
            for root, dirs, files in os.walk(repo_path):
                rel_path = os.path.relpath(root, repo_path)
                if rel_path != "." and not rel_path.startswith(".git"):
                    directories.append(rel_path)
            
            # Check for feature-based organization
            feature_folders = sum(1 for d in directories if any(keyword in d.lower() for keyword in ["feature", "module", "domain"]))
            if feature_folders > 1:
                self._add_code_organization("Feature-based Organization", "high", "folder_structure")
            
            # Check for layer-based organization
            layer_folders = sum(1 for d in directories if any(keyword in d.lower() for keyword in [
                "controller", "service", "repository", "model", "dao", "api", "view", "ui"
            ]))
            if layer_folders > 2:
                self._add_code_organization("Layer-based Organization", "high", "folder_structure")
            
            # Check for component-based organization
            component_folders = sum(1 for d in directories if any(keyword in d.lower() for keyword in ["component", "widget", "element"]))
            if component_folders > 2:
                self._add_code_organization("Component-based Organization", "high", "folder_structure")
            
            # Check for microservices structure
            service_folders = sum(1 for d in directories if "service" in d.lower() and (
                os.path.exists(os.path.join(repo_path, d, "Dockerfile")) or 
                os.path.exists(os.path.join(repo_path, d, "package.json")) or
                os.path.exists(os.path.join(repo_path, d, "setup.py"))
            ))
            if service_folders > 1:
                self._add_architectural_pattern("Microservices Architecture", "high", "folder_structure")
            
            # Check for monorepo structure
            has_packages = os.path.exists(os.path.join(repo_path, "packages"))
            has_apps = os.path.exists(os.path.join(repo_path, "apps"))
            has_libs = os.path.exists(os.path.join(repo_path, "libs"))
            if has_packages or (has_apps and has_libs):
                self._add_code_organization("Monorepo", "high", "folder_structure")
            
            # Check for specific framework conventions
            if os.path.exists(os.path.join(repo_path, "angular.json")):
                self._add_code_organization("Angular CLI Project", "high", "folder_structure")
            
            if os.path.exists(os.path.join(repo_path, "src", "app", "app.module.ts")):
                self._add_code_organization("Angular Standard Layout", "high", "folder_structure")
            
            if os.path.exists(os.path.join(repo_path, "public", "index.html")) and (
                os.path.exists(os.path.join(repo_path, "src", "App.js")) or
                os.path.exists(os.path.join(repo_path, "src", "App.tsx"))
            ):
                self._add_code_organization("Create React App Layout", "high", "folder_structure")
            
            if os.path.exists(os.path.join(repo_path, "manage.py")) and os.path.exists(os.path.join(repo_path, "requirements.txt")):
                self._add_code_organization("Django Project Layout", "high", "folder_structure")
            
            if os.path.exists(os.path.join(repo_path, "app.py")) and os.path.exists(os.path.join(repo_path, "templates")):
                self._add_code_organization("Flask Project Layout", "high", "folder_structure")
        
        except Exception as e:
            self.logger.warning(f"Error analyzing folder structure: {str(e)}")
    
    def _add_design_pattern(self, pattern: str, confidence: str, source: str) -> None:
        """Add a design pattern to the results
        
        Args:
            pattern: Pattern name
            confidence: Confidence level ("high", "medium", "low")
            source: Source of the pattern (file path or analysis type)
        """
        self.patterns_found["design_patterns"].append({
            "name": pattern,
            "confidence": confidence,
            "source": source
        })
    
    def _add_architectural_pattern(self, pattern: str, confidence: str, source: str) -> None:
        """Add an architectural pattern to the results
        
        Args:
            pattern: Pattern name
            confidence: Confidence level ("high", "medium", "low")
            source: Source of the pattern (file path or analysis type)
        """
        self.patterns_found["architectural_patterns"].append({
            "name": pattern,
            "confidence": confidence,
            "source": source
        })
    
    def _add_code_organization(self, pattern: str, confidence: str, source: str) -> None:
        """Add a code organization pattern to the results
        
        Args:
            pattern: Pattern name
            confidence: Confidence level ("high", "medium", "low")
            source: Source of the pattern (file path or analysis type)
        """
        self.patterns_found["code_organization"].append({
            "name": pattern,
            "confidence": confidence,
            "source": source
        })
    
    def _add_language_specific_pattern(self, language: str, pattern: str, confidence: str, source: str) -> None:
        """Add a language-specific pattern to the results
        
        Args:
            language: Programming language
            pattern: Pattern name
            confidence: Confidence level ("high", "medium", "low")
            source: Source of the pattern (file path or analysis type)
        """
        if language not in self.patterns_found["language_specific"]:
            self.patterns_found["language_specific"][language] = []
        
        self.patterns_found["language_specific"][language].append({
            "name": pattern,
            "confidence": confidence,
            "source": source
        })
    
    def _deduplicate_patterns(self) -> None:
        """Deduplicate patterns and calculate overall confidence"""
        # Deduplicate design patterns
        design_patterns = {}
        for pattern in self.patterns_found["design_patterns"]:
            name = pattern["name"]
            confidence = pattern["confidence"]
            
            if name not in design_patterns:
                design_patterns[name] = {
                    "name": name,
                    "confidence": confidence,
                    "sources": [pattern["source"]],
                    "count": 1
                }
            else:
                design_patterns[name]["sources"].append(pattern["source"])
                design_patterns[name]["count"] += 1
                # Upgrade confidence if found multiple times or with high confidence
                if confidence == "high" or design_patterns[name]["count"] > 2:
                    design_patterns[name]["confidence"] = "high"
        
        # Same for architectural patterns
        arch_patterns = {}
        for pattern in self.patterns_found["architectural_patterns"]:
            name = pattern["name"]
            confidence = pattern["confidence"]
            
            if name not in arch_patterns:
                arch_patterns[name] = {
                    "name": name,
                    "confidence": confidence,
                    "sources": [pattern["source"]],
                    "count": 1
                }
            else:
                arch_patterns[name]["sources"].append(pattern["source"])
                arch_patterns[name]["count"] += 1
                if confidence == "high" or arch_patterns[name]["count"] > 2:
                    arch_patterns[name]["confidence"] = "high"
        
        # Same for code organization
        org_patterns = {}
        for pattern in self.patterns_found["code_organization"]:
            name = pattern["name"]
            confidence = pattern["confidence"]
            
            if name not in org_patterns:
                org_patterns[name] = {
                    "name": name,
                    "confidence": confidence,
                    "sources": [pattern["source"]],
                    "count": 1
                }
            else:
                org_patterns[name]["sources"].append(pattern["source"])
                org_patterns[name]["count"] += 1
                if confidence == "high" or org_patterns[name]["count"] > 2:
                    org_patterns[name]["confidence"] = "high"
        
        # Update the patterns
        self.patterns_found["design_patterns"] = list(design_patterns.values())
        self.patterns_found["architectural_patterns"] = list(arch_patterns.values())
        self.patterns_found["code_organization"] = list(org_patterns.values())
        
        # Sort by confidence and count
        for pattern_type in ["design_patterns", "architectural_patterns", "code_organization"]:
            self.patterns_found[pattern_type].sort(
                key=lambda x: (
                    0 if x["confidence"] == "high" else 1 if x["confidence"] == "medium" else 2,
                    -x["count"]
                )
            )
        
        # Deduplicate language-specific patterns
        for language, patterns in self.patterns_found["language_specific"].items():
            lang_patterns = {}
            for pattern in patterns:
                name = pattern["name"]
                confidence = pattern["confidence"]
                
                if name not in lang_patterns:
                    lang_patterns[name] = {
                        "name": name,
                        "confidence": confidence,
                        "sources": [pattern["source"]],
                        "count": 1
                    }
                else:
                    lang_patterns[name]["sources"].append(pattern["source"])
                    lang_patterns[name]["count"] += 1
                    if confidence == "high" or lang_patterns[name]["count"] > 2:
                        lang_patterns[name]["confidence"] = "high"
            
            self.patterns_found["language_specific"][language] = list(lang_patterns.values())
            
            # Sort by confidence and count
            self.patterns_found["language_specific"][language].sort(
                key=lambda x: (
                    0 if x["confidence"] == "high" else 1 if x["confidence"] == "medium" else 2,
                    -x["count"]
                )
            )
