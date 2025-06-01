"""
Code Chunker for MCP Server

This module provides intelligent code chunking capabilities.
It breaks down code files into semantically meaningful chunks
for better vector search and knowledge extraction.
"""

import os
import re
import logging
import ast
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path

class CodeChunker:
    """Chunks code files into semantically meaningful segments"""
    
    def __init__(self):
        """Initialize the code chunker"""
        self.logger = logging.getLogger("mcp_server.services.knowledge_extraction.code_chunker")
        self.min_chunk_size = 100  # Minimum characters per chunk
        self.max_chunk_size = 2000  # Maximum characters per chunk
        self.overlap_size = 50  # Number of characters to overlap between chunks
    
    async def chunk_file(
        self,
        file_path: str,
        language: str,
        content: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Chunk a file into semantically meaningful segments
        
        Args:
            file_path: Path to the file
            language: Programming language
            content: Optional file content (read from file if not provided)
            
        Returns:
            List of code chunks with metadata
        """
        # Read content if not provided
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                self.logger.error(f"Failed to read file {file_path}: {str(e)}")
                return [{"error": f"Failed to read file: {str(e)}"}]
        
        # Chunk based on language
        if language.lower() in ["csharp", "cs", "c#"]:
            return await self._chunk_csharp(file_path, content)
        elif language.lower() in ["typescript", "ts", "javascript", "js"]:
            return await self._chunk_typescript(file_path, content)
        elif language.lower() in ["python", "py"]:
            return await self._chunk_python(file_path, content)
        else:
            # Generic chunking for unsupported languages
            return await self._chunk_generic(file_path, content, language)
    
    async def _chunk_csharp(
        self, 
        file_path: str, 
        content: str
    ) -> List[Dict[str, Any]]:
        """Chunk C# code into semantically meaningful segments
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            List of code chunks with metadata
        """
        chunks = []
        filename = os.path.basename(file_path)
        
        # First chunk: file header and namespace declarations
        namespace_match = re.search(r'namespace\s+([a-zA-Z0-9_.]+)', content)
        if namespace_match:
            namespace_pos = namespace_match.start()
            header = content[:namespace_pos].strip()
            
            if len(header) > self.min_chunk_size:
                chunks.append({
                    "content": header,
                    "type": "file_header",
                    "file_path": file_path,
                    "language": "csharp",
                    "metadata": {
                        "filename": filename
                    }
                })
        
        # Find class definitions
        class_matches = re.finditer(
            r'(?:public|private|protected|internal)?\s*(?:static|abstract|sealed)?\s*class\s+([a-zA-Z0-9_]+)(?:\s*:\s*([^{]+))?\s*{',
            content
        )
        
        for match in class_matches:
            class_name = match.group(1)
            inheritance = match.group(2).strip().split(',') if match.group(2) else []
            
            # Extract the class content with opening and closing braces
            start_pos = match.start()
            # Find matching closing brace
            brace_count = 0
            in_class = False
            end_pos = start_pos
            
            for i in range(start_pos, len(content)):
                if content[i] == '{':
                    brace_count += 1
                    in_class = True
                elif content[i] == '}':
                    brace_count -= 1
                    if in_class and brace_count == 0:
                        end_pos = i + 1  # Include the closing brace
                        break
            
            class_content = content[start_pos:end_pos]
            
            # If class is too large, split into smaller chunks
            if len(class_content) > self.max_chunk_size:
                # First chunk: class declaration and first part
                declaration_end = class_content.find('{') + 1
                first_chunk = class_content[:declaration_end + self.max_chunk_size - declaration_end]
                
                chunks.append({
                    "content": first_chunk,
                    "type": "class_declaration",
                    "file_path": file_path,
                    "language": "csharp",
                    "metadata": {
                        "filename": filename,
                        "class_name": class_name,
                        "inheritance": inheritance
                    }
                })
                
                # Find methods within the class
                method_matches = re.finditer(
                    r'(?:public|private|protected|internal)?\s*(?:static|virtual|abstract|override)?\s*(?:[a-zA-Z0-9_<>]+)\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*(?:=>[^;]+;|{[^}]*}|{)',
                    class_content
                )
                
                for m_match in method_matches:
                    method_name = m_match.group(1)
                    method_start = m_match.start()
                    
                    # Find method end - either at semicolon for expression bodied members
                    # or matching closing brace for block bodied members
                    if '=>' in m_match.group(0) and ';' in m_match.group(0):
                        # Expression bodied member
                        method_end = m_match.group(0).find(';', m_match.group(0).find('=>')) + method_start + 1
                    else:
                        # Block bodied member
                        brace_count = 0
                        in_method = False
                        method_end = method_start
                        
                        for i in range(method_start, len(class_content)):
                            if class_content[i] == '{':
                                brace_count += 1
                                in_method = True
                            elif class_content[i] == '}':
                                brace_count -= 1
                                if in_method and brace_count == 0:
                                    method_end = i + 1  # Include the closing brace
                                    break
                    
                    method_content = class_content[method_start:method_end]
                    
                    if len(method_content) > self.min_chunk_size:
                        chunks.append({
                            "content": method_content,
                            "type": "method",
                            "file_path": file_path,
                            "language": "csharp",
                            "metadata": {
                                "filename": filename,
                                "class_name": class_name,
                                "method_name": method_name
                            }
                        })
            else:
                # Class is small enough to be a single chunk
                chunks.append({
                    "content": class_content,
                    "type": "class",
                    "file_path": file_path,
                    "language": "csharp",
                    "metadata": {
                        "filename": filename,
                        "class_name": class_name,
                        "inheritance": inheritance
                    }
                })
        
        # Find interface definitions
        interface_matches = re.finditer(
            r'(?:public|private|protected|internal)?\s*interface\s+([a-zA-Z0-9_]+)(?:\s*:\s*([^{]+))?\s*{',
            content
        )
        
        for match in interface_matches:
            interface_name = match.group(1)
            inheritance = match.group(2).strip().split(',') if match.group(2) else []
            
            # Extract the interface content with opening and closing braces
            start_pos = match.start()
            # Find matching closing brace
            brace_count = 0
            in_interface = False
            end_pos = start_pos
            
            for i in range(start_pos, len(content)):
                if content[i] == '{':
                    brace_count += 1
                    in_interface = True
                elif content[i] == '}':
                    brace_count -= 1
                    if in_interface and brace_count == 0:
                        end_pos = i + 1  # Include the closing brace
                        break
            
            interface_content = content[start_pos:end_pos]
            
            chunks.append({
                "content": interface_content,
                "type": "interface",
                "file_path": file_path,
                "language": "csharp",
                "metadata": {
                    "filename": filename,
                    "interface_name": interface_name,
                    "inheritance": inheritance
                }
            })
        
        # If no semantic chunks were found, fall back to generic chunking
        if not chunks:
            generic_chunks = await self._chunk_generic(file_path, content, "csharp")
            chunks.extend(generic_chunks)
        
        return chunks
    
    async def _chunk_typescript(
        self, 
        file_path: str, 
        content: str
    ) -> List[Dict[str, Any]]:
        """Chunk TypeScript/JavaScript code into semantically meaningful segments
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            List of code chunks with metadata
        """
        chunks = []
        filename = os.path.basename(file_path)
        language = "typescript" if file_path.endswith(".ts") else "javascript"
        
        # First chunk: file header and imports
        import_section_end = 0
        import_lines = re.finditer(r'import\s+.+\s+from\s+[\'"]', content)
        for match in import_lines:
            import_section_end = max(import_section_end, match.end())
        
        if import_section_end > 0:
            header = content[:import_section_end].strip()
            
            if len(header) > self.min_chunk_size:
                chunks.append({
                    "content": header,
                    "type": "imports",
                    "file_path": file_path,
                    "language": language,
                    "metadata": {
                        "filename": filename
                    }
                })
        
        # Check for Angular components
        is_angular = "@Component" in content
        if is_angular:
            component_matches = re.finditer(
                r'@Component\(\s*({[^}]+})\s*\)\s*export\s*class\s*([a-zA-Z0-9_]+)',
                content
            )
            
            for match in component_matches:
                component_meta = match.group(1)
                component_name = match.group(2)
                
                # Find component class content
                start_pos = match.start()
                class_start = match.end()
                
                # Find matching closing brace for class
                brace_count = 0
                in_class = False
                end_pos = class_start
                
                for i in range(class_start, len(content)):
                    if content[i] == '{':
                        brace_count += 1
                        in_class = True
                    elif content[i] == '}':
                        brace_count -= 1
                        if in_class and brace_count == 0:
                            end_pos = i + 1  # Include the closing brace
                            break
                
                component_content = content[start_pos:end_pos]
                
                chunks.append({
                    "content": component_content,
                    "type": "angular_component",
                    "file_path": file_path,
                    "language": language,
                    "metadata": {
                        "filename": filename,
                        "component_name": component_name,
                        "is_angular": True
                    }
                })
        
        # Find class definitions
        class_matches = re.finditer(
            r'(?:export)?\s*class\s+([a-zA-Z0-9_]+)(?:\s+extends\s+([a-zA-Z0-9_]+))?(?:\s+implements\s+([^{]+))?\s*{',
            content
        )
        
        for match in class_matches:
            class_name = match.group(1)
            extends = match.group(2) if match.group(2) else None
            implements = match.group(3).strip().split(',') if match.group(3) else []
            
            # Extract the class content with opening and closing braces
            start_pos = match.start()
            # Find matching closing brace
            brace_count = 0
            in_class = False
            end_pos = start_pos
            
            for i in range(start_pos, len(content)):
                if content[i] == '{':
                    brace_count += 1
                    in_class = True
                elif content[i] == '}':
                    brace_count -= 1
                    if in_class and brace_count == 0:
                        end_pos = i + 1  # Include the closing brace
                        break
            
            class_content = content[start_pos:end_pos]
            
            # If class is too large, split into smaller chunks
            if len(class_content) > self.max_chunk_size:
                # First chunk: class declaration and first part
                declaration_end = class_content.find('{') + 1
                first_chunk = class_content[:declaration_end + self.max_chunk_size - declaration_end]
                
                chunks.append({
                    "content": first_chunk,
                    "type": "class_declaration",
                    "file_path": file_path,
                    "language": language,
                    "metadata": {
                        "filename": filename,
                        "class_name": class_name,
                        "extends": extends,
                        "implements": implements
                    }
                })
                
                # Find methods within the class
                method_matches = re.finditer(
                    r'(?:public|private|protected)?\s*(?:static|async)?\s*([a-zA-Z0-9_]+)\s*\([^)]*\)',
                    class_content
                )
                
                for m_match in method_matches:
                    method_name = m_match.group(1)
                    method_start = m_match.start()
                    
                    # Find method end - matching closing brace
                    brace_count = 0
                    in_method = False
                    method_end = method_start
                    
                    # Find opening brace
                    opening_brace_pos = class_content.find('{', method_start)
                    if opening_brace_pos == -1:
                        continue  # Skip if no opening brace (might be arrow function)
                    
                    for i in range(opening_brace_pos, len(class_content)):
                        if class_content[i] == '{':
                            brace_count += 1
                            in_method = True
                        elif class_content[i] == '}':
                            brace_count -= 1
                            if in_method and brace_count == 0:
                                method_end = i + 1  # Include the closing brace
                                break
                    
                    method_content = class_content[method_start:method_end]
                    
                    if len(method_content) > self.min_chunk_size:
                        chunks.append({
                            "content": method_content,
                            "type": "method",
                            "file_path": file_path,
                            "language": language,
                            "metadata": {
                                "filename": filename,
                                "class_name": class_name,
                                "method_name": method_name
                            }
                        })
            else:
                # Class is small enough to be a single chunk
                chunks.append({
                    "content": class_content,
                    "type": "class",
                    "file_path": file_path,
                    "language": language,
                    "metadata": {
                        "filename": filename,
                        "class_name": class_name,
                        "extends": extends,
                        "implements": implements
                    }
                })
        
        # Find standalone functions
        function_matches = re.finditer(
            r'(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)\s*\([^)]*\)',
            content
        )
        
        for match in function_matches:
            function_name = match.group(1)
            function_start = match.start()
            
            # Find function end - matching closing brace
            brace_count = 0
            in_function = False
            function_end = function_start
            
            # Find opening brace
            opening_brace_pos = content.find('{', function_start)
            if opening_brace_pos == -1:
                continue  # Skip if no opening brace
            
            for i in range(opening_brace_pos, len(content)):
                if content[i] == '{':
                    brace_count += 1
                    in_function = True
                elif content[i] == '}':
                    brace_count -= 1
                    if in_function and brace_count == 0:
                        function_end = i + 1  # Include the closing brace
                        break
            
            function_content = content[function_start:function_end]
            
            if len(function_content) > self.min_chunk_size:
                chunks.append({
                    "content": function_content,
                    "type": "function",
                    "file_path": file_path,
                    "language": language,
                    "metadata": {
                        "filename": filename,
                        "function_name": function_name
                    }
                })
        
        # If no semantic chunks were found, fall back to generic chunking
        if not chunks:
            generic_chunks = await self._chunk_generic(file_path, content, language)
            chunks.extend(generic_chunks)
        
        return chunks
    
    async def _chunk_python(
        self, 
        file_path: str, 
        content: str
    ) -> List[Dict[str, Any]]:
        """Chunk Python code into semantically meaningful segments
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            List of code chunks with metadata
        """
        chunks = []
        filename = os.path.basename(file_path)
        
        try:
            # Parse the code into an AST
            tree = ast.parse(content)
            
            # First chunk: module docstring and imports
            module_doc = ast.get_docstring(tree) or ""
            
            # Find import statements
            imports = []
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    imports.append(node)
            
            if module_doc or imports:
                # Calculate end line of imports
                max_import_lineno = 0
                for imp in imports:
                    max_import_lineno = max(max_import_lineno, imp.lineno)
                
                # Find end character position
                end_pos = 0
                for i, line in enumerate(content.split('\n')):
                    if i <= max_import_lineno:
                        end_pos += len(line) + 1  # +1 for newline
                
                header = content[:end_pos].strip()
                
                if len(header) > self.min_chunk_size:
                    chunks.append({
                        "content": header,
                        "type": "module_header",
                        "file_path": file_path,
                        "language": "python",
                        "metadata": {
                            "filename": filename,
                            "has_docstring": bool(module_doc)
                        }
                    })
            
            # Process classes
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    
                    # Get source lines for the class
                    class_start = node.lineno - 1  # AST line numbers are 1-indexed
                    class_end = max(n.lineno if hasattr(n, "lineno") else class_start for n in ast.walk(node))
                    
                    # Extract class content from source
                    lines = content.split('\n')
                    class_lines = lines[class_start:class_end + 1]
                    class_content = '\n'.join(class_lines)
                    
                    # If class is too large, split into methods
                    if len(class_content) > self.max_chunk_size:
                        # First chunk: class declaration and docstring
                        class_doc = ast.get_docstring(node) or ""
                        docstring_lines = len(class_doc.split('\n')) if class_doc else 0
                        declaration_end = class_start + 1 + docstring_lines + 2  # class def + docstring + extra lines
                        first_chunk = '\n'.join(lines[class_start:min(declaration_end, len(lines))])
                        
                        chunks.append({
                            "content": first_chunk,
                            "type": "class_declaration",
                            "file_path": file_path,
                            "language": "python",
                            "metadata": {
                                "filename": filename,
                                "class_name": class_name
                            }
                        })
                        
                        # Process methods
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                method_name = item.name
                                
                                # Get source lines for the method
                                method_start = item.lineno - 1
                                method_end = max(n.lineno if hasattr(n, "lineno") else method_start for n in ast.walk(item))
                                
                                # Extract method content
                                method_lines = lines[method_start:method_end + 1]
                                method_content = '\n'.join(method_lines)
                                
                                if len(method_content) > self.min_chunk_size:
                                    chunks.append({
                                        "content": method_content,
                                        "type": "method",
                                        "file_path": file_path,
                                        "language": "python",
                                        "metadata": {
                                            "filename": filename,
                                            "class_name": class_name,
                                            "method_name": method_name
                                        }
                                    })
                    else:
                        # Class is small enough to be a single chunk
                        chunks.append({
                            "content": class_content,
                            "type": "class",
                            "file_path": file_path,
                            "language": "python",
                            "metadata": {
                                "filename": filename,
                                "class_name": class_name
                            }
                        })
            
            # Process standalone functions
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.FunctionDef) and not isinstance(node.parent, ast.ClassDef):
                    function_name = node.name
                    
                    # Get source lines for the function
                    function_start = node.lineno - 1
                    function_end = max(n.lineno if hasattr(n, "lineno") else function_start for n in ast.walk(node))
                    
                    # Extract function content
                    lines = content.split('\n')
                    function_lines = lines[function_start:function_end + 1]
                    function_content = '\n'.join(function_lines)
                    
                    if len(function_content) > self.min_chunk_size:
                        chunks.append({
                            "content": function_content,
                            "type": "function",
                            "file_path": file_path,
                            "language": "python",
                            "metadata": {
                                "filename": filename,
                                "function_name": function_name
                            }
                        })
        
        except SyntaxError as e:
            self.logger.warning(f"Syntax error in Python file {file_path}: {str(e)}")
            # Fall back to generic chunking for files with syntax errors
            chunks = await self._chunk_generic(file_path, content, "python")
        
        # If no semantic chunks were found, fall back to generic chunking
        if not chunks:
            generic_chunks = await self._chunk_generic(file_path, content, "python")
            chunks.extend(generic_chunks)
        
        return chunks
    
    async def _chunk_generic(
        self, 
        file_path: str, 
        content: str, 
        language: str
    ) -> List[Dict[str, Any]]:
        """Chunk any code file into segments of appropriate size
        
        Args:
            file_path: Path to the file
            content: File content
            language: Programming language
            
        Returns:
            List of code chunks with metadata
        """
        chunks = []
        filename = os.path.basename(file_path)
        
        # If content is small enough, return as a single chunk
        if len(content) <= self.max_chunk_size:
            chunks.append({
                "content": content,
                "type": "file",
                "file_path": file_path,
                "language": language,
                "metadata": {
                    "filename": filename
                }
            })
            return chunks
        
        # Split by blank lines for more natural chunks
        lines = content.split('\n')
        current_chunk = []
        current_size = 0
        
        for line in lines:
            line_size = len(line) + 1  # +1 for newline
            
            # If adding this line would exceed max size, store current chunk and start new one
            if current_size + line_size > self.max_chunk_size and current_size > self.min_chunk_size:
                chunk_content = '\n'.join(current_chunk)
                chunks.append({
                    "content": chunk_content,
                    "type": "code_segment",
                    "file_path": file_path,
                    "language": language,
                    "metadata": {
                        "filename": filename,
                        "line_count": len(current_chunk)
                    }
                })
                
                # Start new chunk with overlap
                overlap_lines = min(len(current_chunk), 5)  # Use last 5 lines for context
                current_chunk = current_chunk[-overlap_lines:] + [line]
                current_size = sum(len(l) + 1 for l in current_chunk)
            else:
                current_chunk.append(line)
                current_size += line_size
        
        # Add the last chunk if it's not empty and meets minimum size
        if current_chunk and current_size > self.min_chunk_size:
            chunk_content = '\n'.join(current_chunk)
            chunks.append({
                "content": chunk_content,
                "type": "code_segment",
                "file_path": file_path,
                "language": language,
                "metadata": {
                    "filename": filename,
                    "line_count": len(current_chunk)
                }
            })
        
        return chunks