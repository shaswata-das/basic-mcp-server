"""
Code Extraction Service for MCP Server

This module provides deep code analysis and extraction capabilities.
It parses code files to extract semantic information including:
- Function/method definitions and relationships
- Data structures and schemas
- Call graphs and data flow
- Code patterns and architectural insights
"""

import os
import logging
import re
import ast
import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
import json

class CodeExtractor:
    """Base class for extracting knowledge from code"""
    
    def __init__(self):
        """Initialize the code extractor"""
        self.logger = logging.getLogger("mcp_server.services.knowledge_extraction.code_extractor")
    
    async def extract_knowledge_from_file(
        self,
        file_path: str,
        language: str,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract knowledge from a single file
        
        Args:
            file_path: Path to the file
            language: Programming language
            content: Optional file content (read from file if not provided)
            
        Returns:
            Extracted knowledge
        """
        # Read content if not provided
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                self.logger.error(f"Failed to read file {file_path}: {str(e)}")
                return {"error": f"Failed to read file: {str(e)}"}
        
        # Extract knowledge based on language
        if language.lower() in ["csharp", "cs", "c#"]:
            return await self.extract_csharp_knowledge(file_path, content)
        elif language.lower() in ["typescript", "ts", "javascript", "js"]:
            return await self.extract_typescript_knowledge(file_path, content)
        elif language.lower() in ["python", "py"]:
            return await self.extract_python_knowledge(file_path, content)
        else:
            # Generic extraction for unsupported languages
            return await self.extract_generic_knowledge(file_path, content, language)
    
    async def extract_csharp_knowledge(self, file_path: str, content: str) -> Dict[str, Any]:
        """Extract knowledge from C# code
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            Extracted knowledge
        """
        # Basic info
        filename = os.path.basename(file_path)
        
        # Find namespace
        namespace_match = re.search(r'namespace\s+([a-zA-Z0-9_.]+)', content)
        namespace = namespace_match.group(1) if namespace_match else "Unknown"
        
        # Find classes
        classes = []
        class_matches = re.finditer(
            r'(?:public|private|protected|internal)?\s*(?:static|abstract|sealed)?\s*class\s+([a-zA-Z0-9_]+)(?:\s*:\s*([^{]+))?\s*{',
            content
        )
        
        for match in class_matches:
            class_name = match.group(1)
            inheritance = match.group(2).strip().split(',') if match.group(2) else []
            inheritance = [i.strip() for i in inheritance]
            
            # Extract the class content
            start_pos = match.end()
            # Find matching closing brace
            brace_count = 1
            end_pos = start_pos
            for i in range(start_pos, len(content)):
                if content[i] == '{':
                    brace_count += 1
                elif content[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i
                        break
            
            class_content = content[start_pos:end_pos]
            
            # Extract methods with a pattern that captures return types
            methods = []
            
            # This pattern captures access modifiers, return type, method name, and parameters
            method_pattern = r'^\s*((?:public|private|protected|internal)\s+(?:static|virtual|abstract|override|async)?\s*([a-zA-Z0-9_<>\[\].]+)\s+([a-zA-Z0-9_]+)\s*\(([^)]*)\))'
            
            # Find method declarations
            method_matches = re.finditer(method_pattern, class_content, re.MULTILINE)
            
            for m_match in method_matches:
                method_signature = m_match.group(1)
                return_type = m_match.group(2)
                method_name = m_match.group(3)
                parameters_str = m_match.group(4)
                
                # Skip if method name is a C# keyword
                if method_name.lower() in ["if", "for", "while", "switch", "foreach", "using", "return", "throw"]:
                    continue
                
                # Properly extract parameter list with types
                parameters = []
                if parameters_str.strip():
                    # Extract typed parameters like "int foo, string bar"
                    param_parts = parameters_str.split(',')
                    for part in param_parts:
                        part = part.strip()
                        if part:
                            parameters.append(part)
                
                methods.append({
                    "name": method_name,
                    "return_type": return_type,
                    "parameters": parameters,
                    "signature": method_signature
                })
                
            # If no methods found with strict pattern, try a more lenient one
            if not methods:
                method_pattern = r'(?:public|private|protected|internal)\s+(?:static|virtual|abstract|override|async)?\s*([a-zA-Z0-9_<>\[\].]+)\s+([a-zA-Z0-9_]+)\s*\(([^)]*)\)'
                method_matches = re.finditer(method_pattern, class_content)
                
                for m_match in method_matches:
                    return_type = m_match.group(1)
                    method_name = m_match.group(2)
                    parameters_str = m_match.group(3)
                    
                    # Skip if method name is a C# keyword
                    if method_name.lower() in ["if", "for", "while", "switch", "foreach", "using", "return", "throw"]:
                        continue
                    
                    # Properly extract parameter list
                    parameters = []
                    if parameters_str.strip():
                        param_parts = parameters_str.split(',')
                        for part in param_parts:
                            part = part.strip()
                            if part:
                                parameters.append(part)
                    
                    methods.append({
                        "name": method_name,
                        "return_type": return_type,
                        "parameters": parameters
                    })
            
            # Find properties with improved pattern that actually matches C# properties
            properties = []
            # This pattern matches standard property declarations with get/set
            property_matches = re.finditer(
                r'(?:public|private|protected|internal)\s+(?:virtual|abstract|override|static|readonly)?\s*(?:[a-zA-Z0-9_<>\.]+)\s+([a-zA-Z0-9_]+)\s*{\s*(?:get|set)', 
                class_content
            )
            
            for p_match in property_matches:
                property_name = p_match.group(1)
                # Skip if it's clearly not a property (e.g., a method that has "get" in its name)
                if property_name.lower() in ["if", "for", "while", "switch", "foreach", "return"]:
                    continue
                    
                properties.append({
                    "name": property_name
                })
                
            # Also look for auto-implemented properties (newer C# syntax)
            auto_property_matches = re.finditer(
                r'(?:public|private|protected|internal)\s+(?:virtual|abstract|override|static|readonly)?\s*(?:[a-zA-Z0-9_<>\.]+)\s+([a-zA-Z0-9_]+)\s*{\s*(?:get;|set;)',
                class_content
            )
            
            for p_match in auto_property_matches:
                property_name = p_match.group(1)
                if property_name not in [p["name"] for p in properties]:  # Avoid duplicates
                    properties.append({
                        "name": property_name
                    })
                    
            # Also capture fields with any order of modifiers
            field_matches = re.finditer(
                r'(?:public|private|protected|internal)\s+(?:(?:static|readonly|const)\s+)*(?:[a-zA-Z0-9_<>\.]+)\s+([a-zA-Z0-9_]+)\s*(?:=\s*[^;]+)?;',
                class_content
            )
            
            for f_match in field_matches:
                field_name = f_match.group(1)
                # Skip if it's a common temporary variable name
                if field_name.lower() in ["i", "j", "k", "temp", "tmp", "value", "index"]:
                    continue
                    
                # Add as a field-based property
                if field_name not in [p["name"] for p in properties]:  # Avoid duplicates
                    properties.append({
                        "name": field_name,
                        "is_field": True
                    })
                    
            # Also match const fields with any modifier order
            const_matches = re.finditer(
                r'(?:public|private|protected|internal)?\s+(?:static\s+)?const\s+(?:[a-zA-Z0-9_<>\.]+)\s+([a-zA-Z0-9_]+)\s*=',
                class_content
            )
            
            for c_match in const_matches:
                const_name = c_match.group(1)
                # Add as a constant field
                if const_name not in [p["name"] for p in properties]:  # Avoid duplicates
                    properties.append({
                        "name": const_name,
                        "is_constant": True
                    })
                    
            # Match static readonly fields (like Log instances)
            readonly_matches = re.finditer(
                r'(?:public|private|protected|internal)?\s+static\s+readonly\s+(?:[a-zA-Z0-9_<>\.]+)\s+([a-zA-Z0-9_]+)\s*=',
                class_content
            )
            
            for r_match in readonly_matches:
                readonly_name = r_match.group(1)
                if readonly_name not in [p["name"] for p in properties]:  # Avoid duplicates
                    properties.append({
                        "name": readonly_name,
                        "is_readonly": True
                    })
            
            classes.append({
                "name": class_name,
                "inheritance": inheritance,
                "methods": methods,
                "properties": properties
            })
        
        # Find interfaces
        interfaces = []
        interface_matches = re.finditer(
            r'(?:public|private|protected|internal)?\s*interface\s+([a-zA-Z0-9_]+)(?:\s*:\s*([^{]+))?\s*{',
            content
        )
        
        for match in interface_matches:
            interface_name = match.group(1)
            inheritance = match.group(2).strip().split(',') if match.group(2) else []
            inheritance = [i.strip() for i in inheritance]
            
            interfaces.append({
                "name": interface_name,
                "inheritance": inheritance
            })
        
        # Find dependency injection registrations
        di_registrations = []
        di_matches = re.finditer(
            r'services\.(?:AddScoped|AddSingleton|AddTransient)<([^,>]+)(?:,\s*([^>]+))?>',
            content
        )
        
        for match in di_matches:
            service_type = match.group(1).strip()
            implementation_type = match.group(2).strip() if match.group(2) else service_type
            lifetime = "Scoped" if "AddScoped" in match.group(0) else "Singleton" if "AddSingleton" in match.group(0) else "Transient"
            
            di_registrations.append({
                "service_type": service_type,
                "implementation_type": implementation_type,
                "lifetime": lifetime
            })
        
        # Extract using directives for dependency analysis
        using_directives = []
        using_matches = re.finditer(r'using\s+([a-zA-Z0-9_.]+);', content)
        for match in using_matches:
            using_directives.append(match.group(1).strip())
        
        return {
            "file_path": file_path,
            "code_language": "csharp",
            "namespace": namespace,
            "classes": classes,
            "interfaces": interfaces,
            "di_registrations": di_registrations,
            "using_directives": using_directives,
            "content_length": len(content),
            "file_name": filename
        }
    
    async def extract_typescript_knowledge(self, file_path: str, content: str) -> Dict[str, Any]:
        """Extract knowledge from TypeScript/JavaScript code
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            Extracted knowledge
        """
        # Basic info
        filename = os.path.basename(file_path)
        is_angular = self._is_angular_file(file_path, content)
        
        # Find classes
        classes = []
        class_matches = re.finditer(
            r'(?:export)?\s*class\s+([a-zA-Z0-9_]+)(?:\s+extends\s+([a-zA-Z0-9_]+))?(?:\s+implements\s+([^{]+))?\s*{',
            content
        )
        
        for match in class_matches:
            class_name = match.group(1)
            extends = match.group(2) if match.group(2) else None
            implements = match.group(3).strip().split(',') if match.group(3) else []
            implements = [i.strip() for i in implements]
            
            # Check if this is an Angular component
            is_component = bool(re.search(r'@Component\s*\(', content))
            is_service = bool(re.search(r'@Injectable\s*\(', content))
            is_pipe = bool(re.search(r'@Pipe\s*\(', content))
            is_directive = bool(re.search(r'@Directive\s*\(', content))
            is_module = bool(re.search(r'@NgModule\s*\(', content))
            
            # Extract selector if it's a component
            selector = ""
            if is_component:
                selector_match = re.search(r'selector\s*:\s*[\'"]([^\'"]+)[\'"]', content)
                if selector_match:
                    selector = selector_match.group(1)
            
            # Find methods with more comprehensive pattern for actual method declarations
            methods = []
            
            # This pattern matches class methods with proper context
            # It looks for methods within class definition and ensures it's not a method call
            class_method_pattern = r'(?:\/\/.*\n|\/\*.*?\*\/\s*)*(?:public|private|protected)?\s*(?:static|async)?\s*([a-zA-Z0-9_]+)\s*\(([^)]*)\)\s*(?:{|=>)'
            method_matches = re.finditer(class_method_pattern, content)
            
            for m_match in method_matches:
                method_name = m_match.group(1)
                full_match = m_match.group(0)
                
                # Skip if method name is a JavaScript/TypeScript keyword or common function call
                if method_name in ["if", "for", "while", "switch", "function", "return", "throw", "constructor"]:
                    continue
                
                # Skip if it looks like a function call rather than declaration (check indentation)
                if re.search(r'^\s{4,}', full_match, re.MULTILINE):
                    # It's likely a method call inside another method
                    continue
                
                parameters_str = m_match.group(2)
                parameters = []
                
                # Process parameters more carefully
                if parameters_str.strip():
                    # Split by commas but handle complex cases better
                    param_parts = []
                    in_object = 0
                    in_array = 0
                    in_generic = 0
                    current_part = ""
                    
                    for char in parameters_str:
                        if char == '{': in_object += 1
                        elif char == '}': in_object -= 1
                        elif char == '[': in_array += 1
                        elif char == ']': in_array -= 1
                        elif char == '<': in_generic += 1
                        elif char == '>': in_generic -= 1
                        elif char == ',' and in_object == 0 and in_array == 0 and in_generic == 0:
                            param_parts.append(current_part.strip())
                            current_part = ""
                            continue
                            
                        current_part += char
                    
                    if current_part.strip():
                        param_parts.append(current_part.strip())
                    
                    # Process each parameter part
                    for part in param_parts:
                        # Extract parameter name and type (TypeScript)
                        param_match = re.search(r'(?:readonly)?\s*([a-zA-Z0-9_]+)\s*(?::\s*([^=]+))?(?:\s*=\s*([^,]+))?', part)
                        if param_match:
                            param_name = param_match.group(1)
                            param_type = param_match.group(2).strip() if param_match.group(2) else "any"
                            parameters.append(f"{param_name}: {param_type}")
                        else:
                            # Fallback for complex cases
                            parameters.append(part)
                
                methods.append({
                    "name": method_name,
                    "parameters": parameters,
                    "full_signature": full_match.strip()
                })
                
            # Also look for standalone functions
            function_pattern = r'(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)\s*\(([^)]*)\)\s*{'
            function_matches = re.finditer(function_pattern, content)
            
            for m_match in function_matches:
                function_name = m_match.group(1)
                full_match = m_match.group(0)
                
                # Skip if nested function inside another function (check indentation)
                if re.search(r'^\s{4,}', full_match, re.MULTILINE):
                    continue
                    
                parameters_str = m_match.group(2)
                parameters = [p.strip() for p in parameters_str.split(',')] if parameters_str else []
                
                methods.append({
                    "name": function_name,
                    "parameters": parameters,
                    "is_function": True,
                    "full_signature": full_match.strip()
                })
            
            # Find properties with decorators (for Angular)
            properties = []
            property_matches = re.finditer(
                r'(?:@Input\(\)|@Output\(\)|@ViewChild\([^)]+\)|@HostBinding\([^)]+\))?\s*(?:public|private|protected)?\s*([a-zA-Z0-9_]+)\s*(?::\s*([a-zA-Z0-9_<>]+))?',
                content
            )
            
            for p_match in property_matches:
                property_name = p_match.group(1)
                property_type = p_match.group(2) if p_match.group(2) else "any"
                
                # Determine if it's an Angular decorator
                is_input = bool(re.search(r'@Input\(\)', p_match.group(0)))
                is_output = bool(re.search(r'@Output\(\)', p_match.group(0)))
                
                properties.append({
                    "name": property_name,
                    "type": property_type,
                    "is_input": is_input,
                    "is_output": is_output
                })
            
            classes.append({
                "name": class_name,
                "extends": extends,
                "implements": implements,
                "methods": methods,
                "properties": properties,
                "is_component": is_component,
                "is_service": is_service,
                "is_pipe": is_pipe,
                "is_directive": is_directive,
                "is_module": is_module,
                "selector": selector if is_component else ""
            })
        
        # Find imports for dependency analysis
        imports = []
        import_matches = re.finditer(r'import\s*{([^}]+)}\s*from\s*[\'"]([^\'"]+)[\'"]', content)
        for match in import_matches:
            imported_items = [item.strip() for item in match.group(1).split(',')]
            source = match.group(2).strip()
            
            imports.append({
                "imported_items": imported_items,
                "source": source
            })
        
        return {
            "file_path": file_path,
            "code_language": "typescript" if file_path.endswith(".ts") else "javascript",
            "is_angular": is_angular,
            "classes": classes,
            "imports": imports,
            "content_length": len(content),
            "file_name": filename
        }
    
    def _is_angular_file(self, file_path: str, content: str) -> bool:
        """Determine if a file is part of an Angular project
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            True if it's an Angular file, False otherwise
        """
        # Check filename patterns
        if any(pattern in file_path for pattern in [
            ".component.ts",
            ".service.ts",
            ".directive.ts",
            ".pipe.ts",
            ".module.ts"
        ]):
            return True
        
        # Check for Angular imports or decorators
        angular_patterns = [
            "@Component",
            "@Injectable",
            "@NgModule",
            "@Directive",
            "@Pipe",
            "from '@angular/core'",
            "from '@angular/common'",
            "from '@angular/router'"
        ]
        
        return any(pattern in content for pattern in angular_patterns)
    
    async def extract_python_knowledge(self, file_path: str, content: str) -> Dict[str, Any]:
        """Extract knowledge from Python code
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            Extracted knowledge
        """
        # Basic info
        filename = os.path.basename(file_path)
        
        try:
            # Parse the code into an AST
            tree = ast.parse(content)
            
            # Extract imports
            imports = []
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append({
                            "module": name.name,
                            "alias": name.asname
                        })
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for name in node.names:
                        imports.append({
                            "module": f"{module}.{name.name}" if module else name.name,
                            "from_module": module,
                            "name": name.name,
                            "alias": name.asname
                        })
            
            # Extract classes
            classes = []
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    base_classes = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_classes.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            parts = []
                            current = base
                            while isinstance(current, ast.Attribute):
                                parts.insert(0, current.attr)
                                current = current.value
                            if isinstance(current, ast.Name):
                                parts.insert(0, current.id)
                            base_classes.append('.'.join(parts))
                    
                    methods = []
                    class_variables = []
                    
                    # Process class body
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            # Check if it's a method and extract parameters
                            parameters = []
                            for arg in item.args.args:
                                arg_name = arg.arg
                                # Skip 'self' parameter
                                if arg_name != 'self':
                                    parameters.append(arg_name)
                            
                            methods.append({
                                "name": item.name,
                                "parameters": parameters,
                                "is_async": isinstance(item, ast.AsyncFunctionDef),
                                "decorators": [d.id for d in item.decorator_list if isinstance(d, ast.Name)]
                            })
                        
                        elif isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name):
                                    class_variables.append({
                                        "name": target.id
                                    })
                    
                    classes.append({
                        "name": node.name,
                        "bases": base_classes,
                        "methods": methods,
                        "class_variables": class_variables,
                        "decorators": [d.id for d in node.decorator_list if isinstance(d, ast.Name)]
                    })
            
            # Extract top-level functions
            functions = []
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    parameters = []
                    for arg in node.args.args:
                        arg_name = arg.arg
                        parameters.append(arg_name)
                    
                    functions.append({
                        "name": node.name,
                        "parameters": parameters,
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "decorators": [d.id for d in node.decorator_list if isinstance(d, ast.Name)]
                    })
            
            return {
                "file_path": file_path,
                "code_language": "python",
                "imports": imports,
                "classes": classes,
                "functions": functions,
                "content_length": len(content),
                "file_name": filename
            }
        
        except SyntaxError as e:
            self.logger.warning(f"Syntax error in Python file {file_path}: {str(e)}")
            # Fallback to regex-based extraction
            return await self.extract_generic_knowledge(file_path, content, "python")
    
    async def extract_generic_knowledge(
        self, 
        file_path: str, 
        content: str, 
        language: str
    ) -> Dict[str, Any]:
        """Extract basic knowledge from any code file
        
        Args:
            file_path: Path to the file
            content: File content
            language: Programming language
            
        Returns:
            Extracted knowledge
        """
        # Basic info
        filename = os.path.basename(file_path)
        
        # Analyze the file structure
        lines = content.split('\n')
        line_count = len(lines)
        empty_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(1 for line in lines if line.strip().startswith(('#', '//', '/*', '*', '*/')))
        
        # Find likely function definitions using regex (works for many languages)
        functions = []
        
        # Generic function pattern that works for many languages
        function_pattern = r'(?:function|def|public|private|protected)\s+([a-zA-Z0-9_]+)\s*\(([^)]*)\)'
        function_matches = re.finditer(function_pattern, content)
        
        for match in function_matches:
            function_name = match.group(1)
            parameters_str = match.group(2)
            parameters = [p.strip() for p in parameters_str.split(',')] if parameters_str else []
            
            functions.append({
                "name": function_name,
                "parameters": parameters
            })
        
        # Find class-like structures
        classes = []
        class_pattern = r'(?:class|interface|struct|enum)\s+([a-zA-Z0-9_]+)'
        class_matches = re.finditer(class_pattern, content)
        
        for match in class_matches:
            class_name = match.group(1)
            classes.append({
                "name": class_name
            })
        
        # Detect imports and dependencies
        imports = []
        import_patterns = [
            r'import\s+([a-zA-Z0-9_.]+)',  # Python, Java, TypeScript
            r'#include\s+[<"]([^>"]+)[>"]',  # C/C++
            r'using\s+([a-zA-Z0-9_.]+);',  # C#
            r'require\s*\([\'"]([^\'"]+)[\'"]\)',  # JavaScript/Node
            r'from\s+[\'"]([^\'"]+)[\'"]\s+import',  # Python specific
            r'@import\s+[\'"]([^\'"]+)[\'"]'  # CSS/SCSS
        ]
        
        for pattern in import_patterns:
            import_matches = re.finditer(pattern, content)
            for match in import_matches:
                imports.append(match.group(1))
        
        return {
            "file_path": file_path,
            "code_language": language,
            "line_count": line_count,
            "empty_line_count": empty_lines,
            "comment_line_count": comment_lines,
            "functions": functions,
            "classes": classes,
            "imports": list(set(imports)),  # Deduplicate imports
            "content_length": len(content),
            "file_name": filename
        

        }
