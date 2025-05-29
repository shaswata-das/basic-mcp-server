"""
Angular Code Scanner for MCP Server

This module provides functionality to scan and analyze Angular codebases.
"""

import os
import re
import json
import logging
import asyncio
from typing import Dict, List, Set, Tuple, Any, Optional
import uuid
import glob

class AngularScannerService:
    """Scanner for Angular codebases"""
    
    def __init__(self):
        """Initialize the Angular scanner service"""
        self.logger = logging.getLogger("mcp_server.services.scanners.angular")
        
        # Regex patterns for Angular code analysis
        self.component_pattern = re.compile(r'@Component\s*\(\s*{([^}]+)}\s*\)')
        self.module_pattern = re.compile(r'@NgModule\s*\(\s*{([^}]+)}\s*\)')
        self.service_pattern = re.compile(r'@Injectable\s*\(\s*{([^}]+)}\s*\)')
        self.directive_pattern = re.compile(r'@Directive\s*\(\s*{([^}]+)}\s*\)')
        self.pipe_pattern = re.compile(r'@Pipe\s*\(\s*{([^}]+)}\s*\)')
        self.class_pattern = re.compile(r'export\s+class\s+([a-zA-Z0-9_]+)(\s+extends\s+([a-zA-Z0-9_]+))?(\s+implements\s+([a-zA-Z0-9_,\s]+))?')
        self.import_pattern = re.compile(r'import\s+{([^}]+)}\s+from\s+[\'"]([^\'"]+)[\'"]')
        self.selector_pattern = re.compile(r'selector\s*:\s*[\'"]([^\'"]+)[\'"]')
        self.providers_pattern = re.compile(r'providers\s*:\s*\[(.*?)\]', re.DOTALL)
        self.declarations_pattern = re.compile(r'declarations\s*:\s*\[(.*?)\]', re.DOTALL)
        self.imports_pattern = re.compile(r'imports\s*:\s*\[(.*?)\]', re.DOTALL)
        self.exports_pattern = re.compile(r'exports\s*:\s*\[(.*?)\]', re.DOTALL)
        self.bootstrap_pattern = re.compile(r'bootstrap\s*:\s*\[(.*?)\]', re.DOTALL)
        self.input_pattern = re.compile(r'@Input\(\)\s+([a-zA-Z0-9_]+)')
        self.output_pattern = re.compile(r'@Output\(\)\s+([a-zA-Z0-9_]+)')
    
    async def scan_repository(
        self,
        repo_path: str,
        exclude_patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Scan an Angular repository and extract structure
        
        Args:
            repo_path: Path to the repository
            exclude_patterns: Patterns to exclude
            
        Returns:
            Repository structure information
        """
        self.logger.info(f"Scanning Angular repository at {repo_path}")
        
        # Set default exclude patterns if none provided
        if exclude_patterns is None:
            exclude_patterns = [
                "*/node_modules/*",
                "*/dist/*",
                "*/e2e/*",
                "*/assets/*",
                "*.min.js",
                "*.min.css"
            ]
        
        # Find all TypeScript files
        typescript_files = await self._find_typescript_files(repo_path, exclude_patterns)
        self.logger.info(f"Found {len(typescript_files)} TypeScript files")
        
        # Process files in batches to avoid memory issues
        batch_size = 50
        batches = [typescript_files[i:i+batch_size] for i in range(0, len(typescript_files), batch_size)]
        
        # Process each batch
        all_results = []
        for batch_idx, batch in enumerate(batches):
            self.logger.info(f"Processing batch {batch_idx+1}/{len(batches)} ({len(batch)} files)")
            
            # Process files in parallel
            tasks = [self.analyze_typescript_file(os.path.join(repo_path, file_path)) for file_path in batch]
            batch_results = await asyncio.gather(*tasks)
            all_results.extend(batch_results)
        
        # Find Angular component templates
        template_files = await self._find_html_template_files(repo_path, exclude_patterns)
        self.logger.info(f"Found {len(template_files)} HTML template files")
        
        # Process template files in batches
        template_batches = [template_files[i:i+batch_size] for i in range(0, len(template_files), batch_size)]
        
        # Process each batch of templates
        template_results = []
        for batch_idx, batch in enumerate(template_batches):
            self.logger.info(f"Processing template batch {batch_idx+1}/{len(template_batches)} ({len(batch)} files)")
            
            # Process template files in parallel
            tasks = [self.analyze_template_file(os.path.join(repo_path, file_path)) for file_path in batch]
            batch_results = await asyncio.gather(*tasks)
            template_results.extend(batch_results)
        
        # Find Angular configuration files
        angular_json = await self._find_angular_config(repo_path)
        
        # Combine results
        structure = {
            "repo_id": str(uuid.uuid4()),
            "repo_path": repo_path,
            "file_count": len(typescript_files) + len(template_files),
            "typescript_files": all_results,
            "template_files": template_results,
            "components": self._extract_components(all_results),
            "services": self._extract_services(all_results),
            "modules": self._extract_modules(all_results),
            "directives": self._extract_directives(all_results),
            "pipes": self._extract_pipes(all_results),
            "dependencies": self._extract_dependencies(all_results)
        }
        
        # Add Angular configuration if found
        if angular_json:
            structure["angular_config"] = angular_json
        
        # Match components with their templates
        structure["component_templates"] = self._match_components_with_templates(
            structure["components"], 
            template_results
        )
        
        # Find module dependencies
        structure["module_dependencies"] = self._extract_module_dependencies(all_results)
        
        return structure
    
    async def _find_typescript_files(
        self,
        repo_path: str,
        exclude_patterns: List[str]
    ) -> List[str]:
        """Find all TypeScript files in the repository
        
        Args:
            repo_path: Path to the repository
            exclude_patterns: Patterns to exclude
            
        Returns:
            List of TypeScript file paths relative to repo_path
        """
        # Get absolute paths to all .ts files
        typescript_files = glob.glob(os.path.join(repo_path, "**", "*.ts"), recursive=True)
        
        # Convert to relative paths
        relative_paths = [os.path.relpath(file_path, repo_path) for file_path in typescript_files]
        
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
    
    async def _find_html_template_files(
        self,
        repo_path: str,
        exclude_patterns: List[str]
    ) -> List[str]:
        """Find all HTML template files in the repository
        
        Args:
            repo_path: Path to the repository
            exclude_patterns: Patterns to exclude
            
        Returns:
            List of HTML file paths relative to repo_path
        """
        # Get absolute paths to all .html files
        html_files = glob.glob(os.path.join(repo_path, "**", "*.html"), recursive=True)
        
        # Convert to relative paths
        relative_paths = [os.path.relpath(file_path, repo_path) for file_path in html_files]
        
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
    
    async def _find_angular_config(self, repo_path: str) -> Optional[Dict[str, Any]]:
        """Find and parse Angular configuration
        
        Args:
            repo_path: Path to the repository
            
        Returns:
            Angular configuration or None if not found
        """
        # Look for angular.json
        angular_json_path = os.path.join(repo_path, "angular.json")
        if os.path.exists(angular_json_path):
            try:
                with open(angular_json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error parsing angular.json: {str(e)}")
        
        # Look for .angular-cli.json (older versions)
        angular_cli_path = os.path.join(repo_path, ".angular-cli.json")
        if os.path.exists(angular_cli_path):
            try:
                with open(angular_cli_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error parsing .angular-cli.json: {str(e)}")
        
        return None
    
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
    
    async def analyze_typescript_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a TypeScript file and extract its structure
        
        Args:
            file_path: Path to the TypeScript file
            
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
            
            # Determine file type based on name
            file_type = "unknown"
            if relative_path.endswith(".component.ts"):
                file_type = "component"
            elif relative_path.endswith(".service.ts"):
                file_type = "service"
            elif relative_path.endswith(".module.ts"):
                file_type = "module"
            elif relative_path.endswith(".directive.ts"):
                file_type = "directive"
            elif relative_path.endswith(".pipe.ts"):
                file_type = "pipe"
            elif relative_path.endswith(".guard.ts"):
                file_type = "guard"
            elif relative_path.endswith(".interceptor.ts"):
                file_type = "interceptor"
            
            # Extract imports
            import_matches = self.import_pattern.finditer(content)
            imports = []
            
            for match in import_matches:
                imported_items = [item.strip() for item in match.group(1).split(',')]
                from_module = match.group(2)
                
                imports.append({
                    "items": imported_items,
                    "from": from_module
                })
            
            # Extract component metadata
            component_match = self.component_pattern.search(content)
            component = None
            
            if component_match:
                component_metadata = component_match.group(1)
                
                # Extract selector
                selector_match = self.selector_pattern.search(component_metadata)
                selector = selector_match.group(1) if selector_match else ""
                
                # Extract template path or inline template
                template_path = None
                inline_template = None
                
                if 'templateUrl' in component_metadata:
                    template_url_match = re.search(r'templateUrl\s*:\s*[\'"]([^\'"]+)[\'"]', component_metadata)
                    if template_url_match:
                        template_path = template_url_match.group(1)
                elif 'template' in component_metadata:
                    template_match = re.search(r'template\s*:\s*[\'"]([^\'"]+)[\'"]', component_metadata)
                    if template_match:
                        inline_template = template_match.group(1)
                
                # Extract style paths or inline styles
                style_paths = []
                inline_styles = []
                
                if 'styleUrls' in component_metadata:
                    style_urls_match = re.search(r'styleUrls\s*:\s*\[(.*?)\]', component_metadata, re.DOTALL)
                    if style_urls_match:
                        style_urls = style_urls_match.group(1)
                        style_paths = [s.strip().strip('\'"') for s in style_urls.split(',') if s.strip()]
                elif 'styles' in component_metadata:
                    styles_match = re.search(r'styles\s*:\s*\[(.*?)\]', component_metadata, re.DOTALL)
                    if styles_match:
                        styles = styles_match.group(1)
                        inline_styles = [s.strip().strip('\'"') for s in styles.split(',') if s.strip()]
                
                component = {
                    "selector": selector,
                    "template_path": template_path,
                    "inline_template": inline_template,
                    "style_paths": style_paths,
                    "inline_styles": inline_styles
                }
            
            # Extract module metadata
            module_match = self.module_pattern.search(content)
            module = None
            
            if module_match:
                module_metadata = module_match.group(1)
                
                # Extract declarations
                declarations = []
                declarations_match = self.declarations_pattern.search(module_metadata)
                if declarations_match:
                    declarations_str = declarations_match.group(1)
                    declarations = [d.strip() for d in re.findall(r'([a-zA-Z0-9_]+)', declarations_str)]
                
                # Extract imports
                module_imports = []
                imports_match = self.imports_pattern.search(module_metadata)
                if imports_match:
                    imports_str = imports_match.group(1)
                    module_imports = [i.strip() for i in re.findall(r'([a-zA-Z0-9_]+)', imports_str)]
                
                # Extract exports
                exports = []
                exports_match = self.exports_pattern.search(module_metadata)
                if exports_match:
                    exports_str = exports_match.group(1)
                    exports = [e.strip() for e in re.findall(r'([a-zA-Z0-9_]+)', exports_str)]
                
                # Extract bootstrap components
                bootstrap = []
                bootstrap_match = self.bootstrap_pattern.search(module_metadata)
                if bootstrap_match:
                    bootstrap_str = bootstrap_match.group(1)
                    bootstrap = [b.strip() for b in re.findall(r'([a-zA-Z0-9_]+)', bootstrap_str)]
                
                # Extract providers
                providers = []
                providers_match = self.providers_pattern.search(module_metadata)
                if providers_match:
                    providers_str = providers_match.group(1)
                    providers = [p.strip() for p in re.findall(r'([a-zA-Z0-9_]+)', providers_str)]
                
                module = {
                    "declarations": declarations,
                    "imports": module_imports,
                    "exports": exports,
                    "bootstrap": bootstrap,
                    "providers": providers
                }
            
            # Extract service metadata
            service_match = self.service_pattern.search(content)
            service = None
            
            if service_match:
                service_metadata = service_match.group(1)
                
                # Extract providedIn
                provided_in = None
                provided_in_match = re.search(r'providedIn\s*:\s*[\'"]([^\'"]+)[\'"]', service_metadata)
                if provided_in_match:
                    provided_in = provided_in_match.group(1)
                
                service = {
                    "provided_in": provided_in
                }
            
            # Extract directive metadata
            directive_match = self.directive_pattern.search(content)
            directive = None
            
            if directive_match:
                directive_metadata = directive_match.group(1)
                
                # Extract selector
                selector_match = self.selector_pattern.search(directive_metadata)
                selector = selector_match.group(1) if selector_match else ""
                
                directive = {
                    "selector": selector
                }
            
            # Extract pipe metadata
            pipe_match = self.pipe_pattern.search(content)
            pipe = None
            
            if pipe_match:
                pipe_metadata = pipe_match.group(1)
                
                # Extract name
                name_match = re.search(r'name\s*:\s*[\'"]([^\'"]+)[\'"]', pipe_metadata)
                name = name_match.group(1) if name_match else ""
                
                # Extract pure
                pure = True
                pure_match = re.search(r'pure\s*:\s*(true|false)', pipe_metadata)
                if pure_match and pure_match.group(1) == "false":
                    pure = False
                
                pipe = {
                    "name": name,
                    "pure": pure
                }
            
            # Extract class declaration
            class_match = self.class_pattern.search(content)
            class_info = None
            
            if class_match:
                class_name = class_match.group(1)
                base_class = class_match.group(3)
                implements = class_match.group(5)
                
                # Extract implemented interfaces
                implemented_interfaces = []
                if implements:
                    implemented_interfaces = [i.strip() for i in implements.split(',')]
                
                # Extract Input decorators
                inputs = []
                input_matches = self.input_pattern.finditer(content)
                for match in input_matches:
                    inputs.append(match.group(1))
                
                # Extract Output decorators
                outputs = []
                output_matches = self.output_pattern.finditer(content)
                for match in output_matches:
                    outputs.append(match.group(1))
                
                class_info = {
                    "name": class_name,
                    "base_class": base_class,
                    "implements": implemented_interfaces,
                    "inputs": inputs,
                    "outputs": outputs
                }
            
            # Assemble result
            result = {
                "file_id": file_id,
                "path": relative_path,
                "type": file_type,
                "imports": imports,
                "class": class_info,
                "component": component,
                "module": module,
                "service": service,
                "directive": directive,
                "pipe": pipe
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing TypeScript file {file_path}: {str(e)}")
            return {
                "file_id": str(uuid.uuid4()),
                "path": os.path.basename(file_path),
                "error": str(e)
            }
    
    async def analyze_template_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze an Angular template file
        
        Args:
            file_path: Path to the template file
            
        Returns:
            Template information
        """
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract basic information
            relative_path = os.path.basename(file_path)
            file_id = str(uuid.uuid4())
            
            # Extract components used in the template
            component_usages = []
            
            # Look for custom elements (component selectors)
            # This is a simplistic approach; a proper parser would be better
            custom_element_pattern = re.compile(r'<([a-z]+-[a-z0-9-]+)[^>]*>')
            for match in custom_element_pattern.finditer(content):
                component_usages.append(match.group(1))
            
            # Extract directives used in the template
            directive_usages = []
            
            # Look for structural directives
            structural_directive_pattern = re.compile(r'\*([a-zA-Z]+)=')
            for match in structural_directive_pattern.finditer(content):
                directive_usages.append(match.group(1))
            
            # Look for attribute directives
            attribute_directive_pattern = re.compile(r'\[([a-zA-Z]+)\]')
            for match in attribute_directive_pattern.finditer(content):
                directive_usages.append(match.group(1))
            
            # Extract pipes used in the template
            pipe_usages = []
            
            # Look for pipes
            pipe_pattern = re.compile(r'\|\s*([a-zA-Z0-9]+)')
            for match in pipe_pattern.finditer(content):
                pipe_usages.append(match.group(1))
            
            # Extract form controls
            form_controls = []
            
            # Look for formControlName
            form_control_pattern = re.compile(r'formControlName=[\'"]([^\'"]+)[\'"]')
            for match in form_control_pattern.finditer(content):
                form_controls.append(match.group(1))
            
            # Assemble result
            result = {
                "file_id": file_id,
                "path": relative_path,
                "component_usages": list(set(component_usages)),
                "directive_usages": list(set(directive_usages)),
                "pipe_usages": list(set(pipe_usages)),
                "form_controls": list(set(form_controls))
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing template file {file_path}: {str(e)}")
            return {
                "file_id": str(uuid.uuid4()),
                "path": os.path.basename(file_path),
                "error": str(e)
            }
    
    def _extract_components(self, file_results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Extract components from file results
        
        Args:
            file_results: List of file analysis results
            
        Returns:
            Mapping of component names to component information
        """
        components = {}
        
        for file_result in file_results:
            component = file_result.get("component")
            class_info = file_result.get("class")
            
            if component and class_info:
                components[class_info["name"]] = {
                    "name": class_info["name"],
                    "selector": component["selector"],
                    "file_path": file_result["path"],
                    "template_path": component["template_path"],
                    "inline_template": component["inline_template"],
                    "style_paths": component["style_paths"],
                    "inputs": class_info.get("inputs", []),
                    "outputs": class_info.get("outputs", [])
                }
        
        return components
    
    def _extract_services(self, file_results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Extract services from file results
        
        Args:
            file_results: List of file analysis results
            
        Returns:
            Mapping of service names to service information
        """
        services = {}
        
        for file_result in file_results:
            service = file_result.get("service")
            class_info = file_result.get("class")
            
            if service and class_info:
                services[class_info["name"]] = {
                    "name": class_info["name"],
                    "file_path": file_result["path"],
                    "provided_in": service["provided_in"],
                    "base_class": class_info.get("base_class"),
                    "implements": class_info.get("implements", [])
                }
        
        return services
    
    def _extract_modules(self, file_results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Extract modules from file results
        
        Args:
            file_results: List of file analysis results
            
        Returns:
            Mapping of module names to module information
        """
        modules = {}
        
        for file_result in file_results:
            module = file_result.get("module")
            class_info = file_result.get("class")
            
            if module and class_info:
                modules[class_info["name"]] = {
                    "name": class_info["name"],
                    "file_path": file_result["path"],
                    "declarations": module["declarations"],
                    "imports": module["imports"],
                    "exports": module["exports"],
                    "bootstrap": module["bootstrap"],
                    "providers": module["providers"]
                }
        
        return modules
    
    def _extract_directives(self, file_results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Extract directives from file results
        
        Args:
            file_results: List of file analysis results
            
        Returns:
            Mapping of directive names to directive information
        """
        directives = {}
        
        for file_result in file_results:
            directive = file_result.get("directive")
            class_info = file_result.get("class")
            
            if directive and class_info:
                directives[class_info["name"]] = {
                    "name": class_info["name"],
                    "selector": directive["selector"],
                    "file_path": file_result["path"],
                    "inputs": class_info.get("inputs", []),
                    "outputs": class_info.get("outputs", [])
                }
        
        return directives
    
    def _extract_pipes(self, file_results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Extract pipes from file results
        
        Args:
            file_results: List of file analysis results
            
        Returns:
            Mapping of pipe names to pipe information
        """
        pipes = {}
        
        for file_result in file_results:
            pipe = file_result.get("pipe")
            class_info = file_result.get("class")
            
            if pipe and class_info:
                pipes[class_info["name"]] = {
                    "name": class_info["name"],
                    "pipe_name": pipe["name"],
                    "file_path": file_result["path"],
                    "pure": pipe["pure"]
                }
        
        return pipes
    
    def _extract_dependencies(self, file_results: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Extract dependencies between components, services, etc.
        
        Args:
            file_results: List of file analysis results
            
        Returns:
            Mapping of class names to dependencies
        """
        dependencies = {}
        
        for file_result in file_results:
            class_info = file_result.get("class")
            imports = file_result.get("imports", [])
            
            if class_info:
                class_name = class_info["name"]
                
                if class_name not in dependencies:
                    dependencies[class_name] = []
                
                # Add dependencies from imports
                for import_info in imports:
                    for item in import_info["items"]:
                        if item != class_name:  # Avoid self-dependencies
                            dependencies[class_name].append(item)
        
        return dependencies
    
    def _extract_module_dependencies(self, file_results: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Extract dependencies between modules
        
        Args:
            file_results: List of file analysis results
            
        Returns:
            Mapping of module names to imported modules
        """
        module_dependencies = {}
        
        for file_result in file_results:
            module = file_result.get("module")
            class_info = file_result.get("class")
            
            if module and class_info:
                module_name = class_info["name"]
                
                if module_name not in module_dependencies:
                    module_dependencies[module_name] = []
                
                # Add imported modules
                for imported_module in module["imports"]:
                    if imported_module != module_name:  # Avoid self-dependencies
                        module_dependencies[module_name].append(imported_module)
        
        return module_dependencies
    
    def _match_components_with_templates(
        self,
        components: Dict[str, Dict[str, Any]],
        template_results: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Match components with their templates
        
        Args:
            components: Mapping of component names to component information
            template_results: List of template analysis results
            
        Returns:
            Mapping of component names to template information
        """
        component_templates = {}
        
        for component_name, component_info in components.items():
            template_path = component_info.get("template_path")
            
            if template_path:
                # Find matching template
                for template in template_results:
                    if template["path"] == os.path.basename(template_path):
                        component_templates[component_name] = {
                            "component": component_name,
                            "template": template
                        }
                        break
            elif component_info.get("inline_template"):
                # Inline template
                component_templates[component_name] = {
                    "component": component_name,
                    "inline": True,
                    "template_content": component_info["inline_template"]
                }
        
        return component_templates
