"""
C# Code Scanner for MCP Server

This module provides functionality to scan and analyze C# codebases.
"""

import os
import re
import logging
import asyncio
from typing import Dict, List, Set, Tuple, Any, Optional
import uuid
import glob

class CSharpScannerService:
    """Scanner for C# codebases"""
    
    def __init__(self):
        """Initialize the C# scanner service"""
        self.logger = logging.getLogger("mcp_server.services.scanners.csharp")
        
        # Regex patterns for C# code analysis
        self.namespace_pattern = re.compile(r'namespace\s+([a-zA-Z0-9_.]+)')
        self.class_pattern = re.compile(r'(public|internal|private|protected)?\s*(static|abstract|sealed)?\s*class\s+([a-zA-Z0-9_]+)(\s*:\s*([a-zA-Z0-9_,\s<>]+))?')
        self.interface_pattern = re.compile(r'(public|internal|private|protected)?\s*interface\s+([a-zA-Z0-9_]+)(\s*:\s*([a-zA-Z0-9_,\s<>]+))?')
        self.method_pattern = re.compile(r'(public|internal|private|protected)?\s*(static|virtual|abstract|override)?\s*([a-zA-Z0-9_<>]+)\s+([a-zA-Z0-9_]+)\s*\((.*?)\)')
        self.property_pattern = re.compile(r'(public|internal|private|protected)?\s*(static|virtual|abstract|override)?\s*([a-zA-Z0-9_<>]+)\s+([a-zA-Z0-9_]+)\s*\{')
        self.using_pattern = re.compile(r'using\s+([a-zA-Z0-9_.]+)')
        self.di_pattern = re.compile(r'services\.(AddScoped|AddTransient|AddSingleton)<([a-zA-Z0-9_.<>]+)(?:,\s*([a-zA-Z0-9_.<>]+))?>') 
    
    async def scan_repository(
        self,
        repo_path: str,
        exclude_patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Scan a C# repository and extract structure
        
        Args:
            repo_path: Path to the repository
            exclude_patterns: Patterns to exclude
            
        Returns:
            Repository structure information
        """
        self.logger.info(f"Scanning C# repository at {repo_path}")
        
        # Set default exclude patterns if none provided
        if exclude_patterns is None:
            exclude_patterns = [
                "*/bin/*",
                "*/obj/*",
                "*/node_modules/*",
                "*/dist/*",
                "*/wwwroot/lib/*",
                "*.min.js",
                "*.min.css"
            ]
        
        # Find all C# files
        csharp_files = await self._find_csharp_files(repo_path, exclude_patterns)
        self.logger.info(f"Found {len(csharp_files)} C# files")
        
        # Process files in batches to avoid memory issues
        batch_size = 50
        batches = [csharp_files[i:i+batch_size] for i in range(0, len(csharp_files), batch_size)]
        
        # Process each batch
        all_results = []
        for batch_idx, batch in enumerate(batches):
            self.logger.info(f"Processing batch {batch_idx+1}/{len(batches)} ({len(batch)} files)")
            
            # Process files in parallel
            tasks = [self.analyze_csharp_file(os.path.join(repo_path, file_path)) for file_path in batch]
            batch_results = await asyncio.gather(*tasks)
            all_results.extend(batch_results)
        
        # Combine results
        structure = {
            "repo_id": str(uuid.uuid4()),
            "repo_path": repo_path,
            "file_count": len(csharp_files),
            "files": all_results,
            "namespaces": self._extract_namespaces(all_results),
            "classes": self._extract_classes(all_results),
            "interfaces": self._extract_interfaces(all_results),
            "dependencies": self._extract_dependencies(all_results),
        }
        
        # Find solution files
        solution_files = await self._find_solution_files(repo_path)
        if solution_files:
            structure["solution_files"] = solution_files
            
            # Analyze solution structure
            solution_structure = await self._analyze_solution_structure(repo_path, solution_files[0])
            if solution_structure:
                structure["solution_structure"] = solution_structure
        
        # Find startup classes (Program.cs, Startup.cs)
        startup_files = self._find_startup_files(all_results)
        if startup_files:
            structure["startup_files"] = startup_files
        
        # Find dependency injection registrations
        di_registrations = self._extract_di_registrations(all_results)
        if di_registrations:
            structure["di_registrations"] = di_registrations
        
        return structure
    
    async def _find_csharp_files(
        self,
        repo_path: str,
        exclude_patterns: List[str]
    ) -> List[str]:
        """Find all C# files in the repository
        
        Args:
            repo_path: Path to the repository
            exclude_patterns: Patterns to exclude
            
        Returns:
            List of C# file paths relative to repo_path
        """
        # Get absolute paths to all .cs files
        csharp_files = glob.glob(os.path.join(repo_path, "**", "*.cs"), recursive=True)
        
        # Convert to relative paths
        relative_paths = [os.path.relpath(file_path, repo_path) for file_path in csharp_files]
        
        # Filter out excluded patterns
        filtered_paths = []
        for file_path in relative_paths:
            # Convert path to use forward slashes for glob pattern matching
            normalized_path = file_path.replace("\\", "/")
            
            # Check if file should be excluded
            exclude = False
            for pattern in exclude_patterns:
                if self._matches_glob_pattern(normalized_path, pattern):
                    exclude = True
                    break
            
            if not exclude:
                filtered_paths.append(file_path)
        
        return filtered_paths
    
    def _matches_glob_pattern(self, path: str, pattern: str) -> bool:
        """Check if a path matches a glob pattern
        
        Args:
            path: Path to check
            pattern: Glob pattern
            
        Returns:
            True if the path matches the pattern
        """
        import fnmatch
        return fnmatch.fnmatch(path, pattern)
    
    async def _find_solution_files(self, repo_path: str) -> List[str]:
        """Find solution files (.sln) in the repository
        
        Args:
            repo_path: Path to the repository
            
        Returns:
            List of solution file paths relative to repo_path
        """
        # Get absolute paths to all .sln files
        solution_files = glob.glob(os.path.join(repo_path, "**", "*.sln"), recursive=True)
        
        # Convert to relative paths
        relative_paths = [os.path.relpath(file_path, repo_path) for file_path in solution_files]
        
        return relative_paths
    
    async def _analyze_solution_structure(
        self,
        repo_path: str,
        solution_file: str
    ) -> Optional[Dict[str, Any]]:
        """Analyze the structure of a solution file
        
        Args:
            repo_path: Path to the repository
            solution_file: Path to the solution file relative to repo_path
            
        Returns:
            Solution structure information
        """
        solution_path = os.path.join(repo_path, solution_file)
        
        try:
            # Read solution file
            with open(solution_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract project references
            project_pattern = re.compile(r'Project\("{[^}]+}"\) = "([^"]+)", "([^"]+)", "{([^}]+)}"')
            projects = []
            
            for match in project_pattern.finditer(content):
                project_name = match.group(1)
                project_path = match.group(2)
                project_guid = match.group(3)
                
                # Normalize path
                normalized_path = project_path.replace('\\', '/')
                
                projects.append({
                    "name": project_name,
                    "path": normalized_path,
                    "guid": project_guid
                })
            
            return {
                "solution_name": os.path.basename(solution_file),
                "projects": projects
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing solution file {solution_file}: {str(e)}")
            return None
    
    async def analyze_csharp_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a C# file and extract its structure
        
        Args:
            file_path: Path to the C# file
            
        Returns:
            File structure information
        """
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract basic information
            relative_path = os.path.basename(file_path)
            file_id = str(uuid.uuid4())
            
            # Extract namespace
            namespace_match = self.namespace_pattern.search(content)
            namespace = namespace_match.group(1) if namespace_match else ""
            
            # Extract using statements
            using_matches = self.using_pattern.findall(content)
            usings = [match for match in using_matches]
            
            # Extract classes
            class_matches = self.class_pattern.finditer(content)
            classes = []
            
            for match in class_matches:
                access_modifier = match.group(1) or "internal"  # Default is internal
                modifier = match.group(2) or ""
                class_name = match.group(3)
                inheritance = match.group(5) or ""
                
                # Extract base classes and interfaces
                inheritance_parts = [part.strip() for part in inheritance.split(',')] if inheritance else []
                
                classes.append({
                    "name": class_name,
                    "namespace": namespace,
                    "access_modifier": access_modifier,
                    "modifier": modifier,
                    "inheritance": inheritance_parts
                })
            
            # Extract interfaces
            interface_matches = self.interface_pattern.finditer(content)
            interfaces = []
            
            for match in interface_matches:
                access_modifier = match.group(1) or "internal"  # Default is internal
                interface_name = match.group(2)
                inheritance = match.group(4) or ""
                
                # Extract base interfaces
                inheritance_parts = [part.strip() for part in inheritance.split(',')] if inheritance else []
                
                interfaces.append({
                    "name": interface_name,
                    "namespace": namespace,
                    "access_modifier": access_modifier,
                    "inheritance": inheritance_parts
                })
            
            # Extract methods
            method_matches = self.method_pattern.finditer(content)
            methods = []
            
            for match in method_matches:
                access_modifier = match.group(1) or "private"  # Default is private
                modifier = match.group(2) or ""
                return_type = match.group(3)
                method_name = match.group(4)
                parameters = match.group(5)
                
                methods.append({
                    "name": method_name,
                    "return_type": return_type,
                    "access_modifier": access_modifier,
                    "modifier": modifier,
                    "parameters": parameters
                })
            
            # Extract dependency injection pattern
            constructor_pattern = re.compile(r'public\s+([a-zA-Z0-9_]+)\s*\(([^)]*)\)')
            constructor_match = constructor_pattern.search(content)
            
            di_parameters = []
            if constructor_match:
                constructor_name = constructor_match.group(1)
                parameters_str = constructor_match.group(2)
                
                # Parse parameters
                if parameters_str:
                    parameters = [p.strip() for p in parameters_str.split(',')]
                    for param in parameters:
                        param_parts = param.split()
                        if len(param_parts) >= 2:
                            param_type = param_parts[0]
                            param_name = param_parts[1]
                            
                            di_parameters.append({
                                "type": param_type,
                                "name": param_name
                            })
            
            # Look for DI registrations
            di_matches = self.di_pattern.finditer(content)
            di_registrations = []
            
            for match in di_matches:
                lifetime = match.group(1)  # AddScoped, AddTransient, AddSingleton
                service_type = match.group(2)
                implementation_type = match.group(3) or service_type
                
                di_registrations.append({
                    "lifetime": lifetime,
                    "service_type": service_type,
                    "implementation_type": implementation_type
                })
            
            # Assemble result
            result = {
                "file_id": file_id,
                "path": relative_path,
                "namespace": namespace,
                "usings": usings,
                "classes": classes,
                "interfaces": interfaces,
                "methods": methods,
                "di_parameters": di_parameters if di_parameters else None,
                "di_registrations": di_registrations if di_registrations else None
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing C# file {file_path}: {str(e)}")
            return {
                "file_id": str(uuid.uuid4()),
                "path": os.path.basename(file_path),
                "error": str(e)
            }
    
    def _extract_namespaces(self, file_results: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Extract namespaces from file results
        
        Args:
            file_results: List of file analysis results
            
        Returns:
            Mapping of namespaces to files
        """
        namespaces = {}
        
        for file_result in file_results:
            namespace = file_result.get("namespace")
            if namespace:
                if namespace not in namespaces:
                    namespaces[namespace] = []
                
                namespaces[namespace].append(file_result["path"])
        
        return namespaces
    
    def _extract_classes(self, file_results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Extract classes from file results
        
        Args:
            file_results: List of file analysis results
            
        Returns:
            Mapping of class names to class information
        """
        classes = {}
        
        for file_result in file_results:
            namespace = file_result.get("namespace", "")
            
            for class_info in file_result.get("classes", []):
                # Create a fully qualified name
                fq_name = f"{namespace}.{class_info['name']}" if namespace else class_info['name']
                
                classes[fq_name] = {
                    "name": class_info["name"],
                    "namespace": namespace,
                    "file_path": file_result["path"],
                    "access_modifier": class_info["access_modifier"],
                    "modifier": class_info["modifier"],
                    "inheritance": class_info["inheritance"]
                }
        
        return classes
    
    def _extract_interfaces(self, file_results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Extract interfaces from file results
        
        Args:
            file_results: List of file analysis results
            
        Returns:
            Mapping of interface names to interface information
        """
        interfaces = {}
        
        for file_result in file_results:
            namespace = file_result.get("namespace", "")
            
            for interface_info in file_result.get("interfaces", []):
                # Create a fully qualified name
                fq_name = f"{namespace}.{interface_info['name']}" if namespace else interface_info['name']
                
                interfaces[fq_name] = {
                    "name": interface_info["name"],
                    "namespace": namespace,
                    "file_path": file_result["path"],
                    "access_modifier": interface_info["access_modifier"],
                    "inheritance": interface_info["inheritance"]
                }
        
        return interfaces
    
    def _extract_dependencies(self, file_results: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
        """Extract dependencies between classes and namespaces
        
        Args:
            file_results: List of file analysis results
            
        Returns:
            Mapping of class/namespace to dependencies
        """
        dependencies = {}
        
        for file_result in file_results:
            namespace = file_result.get("namespace", "")
            usings = set(file_result.get("usings", []))
            
            # Add namespace dependencies
            if namespace and usings:
                if namespace not in dependencies:
                    dependencies[namespace] = set()
                
                dependencies[namespace].update(usings)
            
            # Add class dependencies based on inheritance
            for class_info in file_result.get("classes", []):
                class_name = class_info["name"]
                fq_name = f"{namespace}.{class_name}" if namespace else class_name
                
                if fq_name not in dependencies:
                    dependencies[fq_name] = set()
                
                # Add inheritance dependencies
                for inheritance in class_info["inheritance"]:
                    # Try to resolve the dependency
                    if "." in inheritance:
                        # Fully qualified name
                        dependencies[fq_name].add(inheritance)
                    elif namespace:
                        # Try same namespace first
                        dependencies[fq_name].add(f"{namespace}.{inheritance}")
                    
                    # Add using dependencies (might be resolved at a later stage)
                    for using in usings:
                        dependencies[fq_name].add(f"{using}.{inheritance}")
        
        return dependencies
    
    def _find_startup_files(self, file_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find startup files (Program.cs, Startup.cs)
        
        Args:
            file_results: List of file analysis results
            
        Returns:
            List of startup file information
        """
        startup_files = []
        
        for file_result in file_results:
            file_path = file_result["path"]
            
            # Check if this is a startup file
            if os.path.basename(file_path) in ["Program.cs", "Startup.cs"]:
                startup_files.append({
                    "path": file_path,
                    "type": os.path.basename(file_path).replace(".cs", "")
                })
        
        return startup_files
    
    def _extract_di_registrations(self, file_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract dependency injection registrations
        
        Args:
            file_results: List of file analysis results
            
        Returns:
            List of DI registration information
        """
        registrations = []
        
        for file_result in file_results:
            di_regs = file_result.get("di_registrations")
            
            if di_regs:
                for reg in di_regs:
                    registrations.append({
                        "file_path": file_result["path"],
                        "lifetime": reg["lifetime"],
                        "service_type": reg["service_type"],
                        "implementation_type": reg["implementation_type"]
                    })
        
        return registrations