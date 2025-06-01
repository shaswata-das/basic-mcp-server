"""
Documentation Extractor for MCP Server

This module provides enhanced documentation extraction capabilities.
It parses code files to extract comments, docstrings, and documentation
and builds structured representations of the code's documentation.
"""

import os
import re
import logging
import ast
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path

class DocumentationExtractor:
    """Extracts documentation and comments from code files"""
    
    def __init__(self):
        """Initialize the documentation extractor"""
        self.logger = logging.getLogger("mcp_server.services.knowledge_extraction.documentation_extractor")
    
    async def extract_documentation(
        self,
        file_path: str,
        language: str,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract documentation from a code file
        
        Args:
            file_path: Path to the file
            language: Programming language
            content: Optional file content (read from file if not provided)
            
        Returns:
            Extracted documentation
        """
        # Read content if not provided
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                self.logger.error(f"Failed to read file {file_path}: {str(e)}")
                return {"error": f"Failed to read file: {str(e)}"}
        
        # Extract documentation based on language
        if language.lower() in ["csharp", "cs", "c#"]:
            return await self._extract_csharp_documentation(file_path, content)
        elif language.lower() in ["typescript", "ts", "javascript", "js"]:
            return await self._extract_typescript_documentation(file_path, content)
        elif language.lower() in ["python", "py"]:
            return await self._extract_python_documentation(file_path, content)
        else:
            # Generic extraction for unsupported languages
            return await self._extract_generic_documentation(file_path, content, language)
    
    async def _extract_csharp_documentation(
        self, 
        file_path: str, 
        content: str
    ) -> Dict[str, Any]:
        """Extract documentation from C# code
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            Extracted documentation
        """
        # Basic file information
        filename = os.path.basename(file_path)
        
        # Extract file-level documentation
        file_docs = self._extract_csharp_file_docs(content)
        
        # Extract namespace documentation
        namespaces = []
        namespace_matches = re.finditer(
            r'(///\s*<summary>\s*(?:///\s*.*\s*)*///\s*</summary>)?\s*namespace\s+([a-zA-Z0-9_.]+)',
            content, re.MULTILINE
        )
        
        for match in namespace_matches:
            doc_comment = match.group(1) or ""
            namespace_name = match.group(2)
            
            namespaces.append({
                "name": namespace_name,
                "documentation": self._clean_csharp_xml_doc(doc_comment)
            })
        
        # Extract class documentation
        classes = []
        class_matches = re.finditer(
            r'(///\s*<summary>\s*(?:///\s*.*\s*)*///\s*</summary>)?\s*(?:public|private|protected|internal)?\s*(?:static|abstract|sealed)?\s*class\s+([a-zA-Z0-9_]+)',
            content, re.MULTILINE
        )
        
        for match in class_matches:
            doc_comment = match.group(1) or ""
            class_name = match.group(2)
            
            classes.append({
                "name": class_name,
                "documentation": self._clean_csharp_xml_doc(doc_comment)
            })
        
        # Extract method documentation
        methods = []
        method_matches = re.finditer(
            r'(///\s*<summary>\s*(?:///\s*.*\s*)*///\s*</summary>(?:///\s*<param[^>]*>(?:///\s*.*\s*)*///\s*</param>)*(?:///\s*<returns>(?:///\s*.*\s*)*///\s*</returns>)?)?\s*(?:public|private|protected|internal)?\s*(?:static|virtual|abstract|override)?\s*(?:[a-zA-Z0-9_<>]+)\s+([a-zA-Z0-9_]+)\s*\(',
            content, re.MULTILINE
        )
        
        for match in method_matches:
            doc_comment = match.group(1) or ""
            method_name = match.group(2)
            
            # Extract parameter documentation
            param_docs = re.findall(r'<param\s+name="([^"]+)">(.*?)</param>', doc_comment, re.DOTALL)
            parameters = [{"name": name, "description": desc.strip()} for name, desc in param_docs]
            
            # Extract return type documentation
            return_doc_match = re.search(r'<returns>(.*?)</returns>', doc_comment, re.DOTALL)
            return_doc = return_doc_match.group(1).strip() if return_doc_match else ""
            
            # Extract summary
            summary_match = re.search(r'<summary>(.*?)</summary>', doc_comment, re.DOTALL)
            summary = summary_match.group(1).strip() if summary_match else ""
            
            methods.append({
                "name": method_name,
                "summary": summary,
                "parameters": parameters,
                "returns": return_doc
            })
        
        # Extract property documentation
        properties = []
        property_matches = re.finditer(
            r'(///\s*<summary>\s*(?:///\s*.*\s*)*///\s*</summary>)?\s*(?:public|private|protected|internal)?\s*(?:static|virtual|abstract|override)?\s*(?:[a-zA-Z0-9_<>]+)\s+([a-zA-Z0-9_]+)\s*{\s*(?:get;)?\s*(?:set;)?',
            content, re.MULTILINE
        )
        
        for match in property_matches:
            doc_comment = match.group(1) or ""
            property_name = match.group(2)
            
            properties.append({
                "name": property_name,
                "documentation": self._clean_csharp_xml_doc(doc_comment)
            })
        
        # Extract all XML doc comments for additional context
        all_comments = re.findall(r'///.*', content)
        xml_doc_comments = [comment.strip('/ ') for comment in all_comments]
        
        # Extract TODO comments
        todo_comments = re.findall(r'//\s*TODO:?\s*(.*?)(?:\r?\n|$)', content)
        
        return {
            "file_path": file_path,
            "file_name": filename,
            "language": "csharp",
            "file_documentation": file_docs,
            "namespaces": namespaces,
            "classes": classes,
            "methods": methods,
            "properties": properties,
            "xml_doc_comments": xml_doc_comments,
            "todo_comments": todo_comments
        }
    
    def _clean_csharp_xml_doc(self, xml_doc: str) -> str:
        """Clean C# XML documentation comment
        
        Args:
            xml_doc: XML documentation comment
            
        Returns:
            Cleaned documentation string
        """
        if not xml_doc:
            return ""
        
        # Remove comment markers and tags
        doc = re.sub(r'///\s*', '', xml_doc)
        doc = re.sub(r'<summary>', '', doc)
        doc = re.sub(r'</summary>', '', doc)
        
        # Remove other tags but keep their content
        doc = re.sub(r'<[^>]+>', '', doc)
        
        return doc.strip()
    
    def _extract_csharp_file_docs(self, content: str) -> str:
        """Extract file-level documentation from C# file
        
        Args:
            content: File content
            
        Returns:
            File documentation string
        """
        # Look for file header comments
        header_match = re.search(r'/\*\*(.*?)\*/', content, re.DOTALL)
        if header_match:
            return header_match.group(1).strip()
        
        # Look for leading XML doc comments before any namespace or class
        first_namespace = re.search(r'namespace\s+', content)
        first_class = re.search(r'class\s+', content)
        
        # Find the position of the first namespace or class
        first_pos = min(
            first_namespace.start() if first_namespace else len(content),
            first_class.start() if first_class else len(content)
        )
        
        # Extract leading comments
        leading_content = content[:first_pos]
        leading_comments = re.findall(r'///\s*(.*?)(?:\r?\n|$)', leading_content)
        
        if leading_comments:
            return '\n'.join(leading_comments)
        
        return ""
    
    async def _extract_typescript_documentation(
        self, 
        file_path: str, 
        content: str
    ) -> Dict[str, Any]:
        """Extract documentation from TypeScript/JavaScript code
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            Extracted documentation
        """
        # Basic file information
        filename = os.path.basename(file_path)
        
        # Extract file-level JSDoc
        file_docs = self._extract_jsdoc_file_docs(content)
        
        # Extract class documentation
        classes = []
        class_matches = re.finditer(
            r'(/\*\*\s*(?:[^*]|\*[^/])*\*/)?\s*(?:export)?\s*class\s+([a-zA-Z0-9_]+)',
            content, re.MULTILINE
        )
        
        for match in class_matches:
            doc_comment = match.group(1) or ""
            class_name = match.group(2)
            
            classes.append({
                "name": class_name,
                "documentation": self._clean_jsdoc(doc_comment)
            })
        
        # Extract function/method documentation
        functions = []
        function_matches = re.finditer(
            r'(/\*\*\s*(?:[^*]|\*[^/])*\*/)?\s*(?:export\s+)?(?:async\s+)?(?:function\s+)?([a-zA-Z0-9_]+)\s*\(',
            content, re.MULTILINE
        )
        
        for match in function_matches:
            doc_comment = match.group(1) or ""
            function_name = match.group(2)
            
            # Extract parameter documentation
            param_docs = re.findall(r'@param\s+(?:{[^}]+})?\s*(\w+)\s+(.*?)(?=@|\*/|$)', doc_comment, re.DOTALL)
            parameters = [{"name": name, "description": desc.strip()} for name, desc in param_docs]
            
            # Extract return type documentation
            return_doc_match = re.search(r'@returns?\s+(.*?)(?=@|\*/|$)', doc_comment, re.DOTALL)
            return_doc = return_doc_match.group(1).strip() if return_doc_match else ""
            
            # Extract summary (first line of JSDoc)
            lines = doc_comment.split('\n')
            summary = ""
            for line in lines:
                line = line.strip().lstrip('/*').strip()
                if line and not line.startswith('@'):
                    summary = line
                    break
            
            functions.append({
                "name": function_name,
                "summary": summary,
                "parameters": parameters,
                "returns": return_doc
            })
        
        # Extract all JSDoc comments for additional context
        jsdoc_comments = re.findall(r'/\*\*\s*(?:[^*]|\*[^/])*\*/', content)
        cleaned_jsdocs = [self._clean_jsdoc(comment) for comment in jsdoc_comments]
        
        # Extract TODO comments
        todo_comments = re.findall(r'//\s*TODO:?\s*(.*?)(?:\r?\n|$)', content)
        
        # Extract Angular component metadata
        angular_components = []
        component_matches = re.finditer(
            r'@Component\(\s*({[^}]+})\s*\)',
            content, re.MULTILINE
        )
        
        for match in component_matches:
            component_meta = match.group(1)
            
            # Extract selector
            selector_match = re.search(r'selector\s*:\s*[\'"]([^\'"]+)[\'"]', component_meta)
            selector = selector_match.group(1) if selector_match else ""
            
            # Extract template URL
            template_url_match = re.search(r'templateUrl\s*:\s*[\'"]([^\'"]+)[\'"]', component_meta)
            template_url = template_url_match.group(1) if template_url_match else ""
            
            # Extract style URLs
            style_urls_match = re.search(r'styleUrls\s*:\s*\[(.*?)\]', component_meta, re.DOTALL)
            style_urls = []
            if style_urls_match:
                style_urls_str = style_urls_match.group(1)
                style_urls = re.findall(r'[\'"]([^\'"]+)[\'"]', style_urls_str)
            
            angular_components.append({
                "selector": selector,
                "templateUrl": template_url,
                "styleUrls": style_urls
            })
        
        return {
            "file_path": file_path,
            "file_name": filename,
            "language": "typescript" if file_path.endswith(".ts") else "javascript",
            "file_documentation": file_docs,
            "classes": classes,
            "functions": functions,
            "jsdoc_comments": cleaned_jsdocs,
            "todo_comments": todo_comments,
            "angular_components": angular_components if angular_components else None
        }
    
    def _clean_jsdoc(self, jsdoc: str) -> str:
        """Clean JSDoc comment
        
        Args:
            jsdoc: JSDoc comment
            
        Returns:
            Cleaned documentation string
        """
        if not jsdoc:
            return ""
        
        # Remove comment markers
        doc = jsdoc.replace('/**', '').replace('*/', '').replace('*', '')
        
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in doc.split('\n')]
        
        # Remove empty lines from beginning and end
        while lines and not lines[0]:
            lines.pop(0)
        
        while lines and not lines[-1]:
            lines.pop()
        
        return '\n'.join(lines)
    
    def _extract_jsdoc_file_docs(self, content: str) -> str:
        """Extract file-level documentation from JS/TS file
        
        Args:
            content: File content
            
        Returns:
            File documentation string
        """
        # Look for file header JSDoc
        header_match = re.search(r'^/\*\*(.*?)\*/', content, re.DOTALL)
        if header_match:
            return self._clean_jsdoc(header_match.group(0))
        
        return ""
    
    async def _extract_python_documentation(
        self, 
        file_path: str, 
        content: str
    ) -> Dict[str, Any]:
        """Extract documentation from Python code
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            Extracted documentation
        """
        # Basic file information
        filename = os.path.basename(file_path)
        
        # Extract module docstring and other documentation
        try:
            # Parse the code into an AST
            tree = ast.parse(content)
            
            # Extract module docstring
            module_doc = ast.get_docstring(tree) or ""
            
            # Extract class docstrings
            classes = []
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    class_doc = ast.get_docstring(node) or ""
                    
                    # Extract method docstrings
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_doc = ast.get_docstring(item) or ""
                            
                            # Extract parameter info from docstring
                            param_docs = []
                            for line in method_doc.split('\n'):
                                line = line.strip()
                                # Match parameter documentation in various formats
                                param_match = re.search(r'(?:Args|Parameters):\s*(\w+)\s*:\s*(.*?)$', line)
                                if param_match:
                                    param_docs.append({
                                        "name": param_match.group(1),
                                        "description": param_match.group(2).strip()
                                    })
                            
                            # Extract return info from docstring
                            return_doc = ""
                            for line in method_doc.split('\n'):
                                line = line.strip()
                                return_match = re.search(r'(?:Returns|Return):\s*(.*?)$', line)
                                if return_match:
                                    return_doc = return_match.group(1).strip()
                                    break
                            
                            methods.append({
                                "name": item.name,
                                "docstring": method_doc,
                                "parameters": param_docs,
                                "returns": return_doc
                            })
                    
                    classes.append({
                        "name": node.name,
                        "docstring": class_doc,
                        "methods": methods
                    })
            
            # Extract function docstrings
            functions = []
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.FunctionDef):
                    func_doc = ast.get_docstring(node) or ""
                    
                    # Extract parameter info from docstring
                    param_docs = []
                    for line in func_doc.split('\n'):
                        line = line.strip()
                        # Match parameter documentation in various formats
                        param_match = re.search(r'(?:Args|Parameters):\s*(\w+)\s*:\s*(.*?)$', line)
                        if param_match:
                            param_docs.append({
                                "name": param_match.group(1),
                                "description": param_match.group(2).strip()
                            })
                    
                    # Extract return info from docstring
                    return_doc = ""
                    for line in func_doc.split('\n'):
                        line = line.strip()
                        return_match = re.search(r'(?:Returns|Return):\s*(.*?)$', line)
                        if return_match:
                            return_doc = return_match.group(1).strip()
                            break
                    
                    functions.append({
                        "name": node.name,
                        "docstring": func_doc,
                        "parameters": param_docs,
                        "returns": return_doc
                    })
            
            # Extract comments
            comments = []
            for line in content.split('\n'):
                comment_match = re.search(r'^\s*#\s*(.*)$', line)
                if comment_match:
                    comments.append(comment_match.group(1).strip())
            
            # Extract TODO comments
            todo_comments = [c for c in comments if c.lower().startswith('todo')]
            
            return {
                "file_path": file_path,
                "file_name": filename,
                "language": "python",
                "module_docstring": module_doc,
                "classes": classes,
                "functions": functions,
                "comments": comments,
                "todo_comments": todo_comments
            }
        
        except SyntaxError as e:
            self.logger.warning(f"Syntax error in Python file {file_path}: {str(e)}")
            # Fallback to regex-based extraction for files with syntax errors
            return await self._extract_generic_documentation(file_path, content, "python")
    
    async def _extract_generic_documentation(
        self, 
        file_path: str, 
        content: str, 
        language: str
    ) -> Dict[str, Any]:
        """Extract documentation from any code file using generic patterns
        
        Args:
            file_path: Path to the file
            content: File content
            language: Programming language
            
        Returns:
            Extracted documentation
        """
        # Basic file information
        filename = os.path.basename(file_path)
        
        # Extract comments based on language
        comments = []
        
        # Single-line comments
        if language.lower() in ["python", "py", "ruby", "rb", "shell", "bash", "sh"]:
            # Languages that use # for comments
            comment_pattern = r'^\s*#\s*(.*)$'
        elif language.lower() in ["sql"]:
            # SQL uses -- for comments
            comment_pattern = r'^\s*--\s*(.*)$'
        else:
            # Most languages use // for single-line comments
            comment_pattern = r'^\s*//\s*(.*)$'
        
        for line in content.split('\n'):
            comment_match = re.search(comment_pattern, line)
            if comment_match:
                comments.append(comment_match.group(1).strip())
        
        # Extract block comments
        block_comments = []
        
        # Most languages use /* ... */ for block comments
        block_matches = re.finditer(r'/\*\s*(.*?)\s*\*/', content, re.DOTALL)
        for match in block_matches:
            block_comments.append(match.group(1).strip())
        
        # Extract TODO comments
        todo_comments = []
        for comment in comments:
            if comment.lower().startswith('todo'):
                todo_comments.append(comment)
        
        # Block TODO comments
        for comment in block_comments:
            todo_match = re.search(r'TODO:?\s*(.*?)(?:\r?\n|$)', comment)
            if todo_match:
                todo_comments.append(todo_match.group(1).strip())
        
        return {
            "file_path": file_path,
            "file_name": filename,
            "language": language,
            "comments": comments,
            "block_comments": block_comments,
            "todo_comments": todo_comments
        }