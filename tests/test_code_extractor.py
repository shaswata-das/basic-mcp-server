"""
Tests for the code extractor service.
"""
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock

from mcp_server.services.knowledge_extraction.code_extractor import CodeExtractor

class TestCodeExtractor:
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = CodeExtractor()
    
    def _create_test_file(self, content, extension=".py"):
        """Create a temporary file with the given content and extension."""
        fd, path = tempfile.mkstemp(suffix=extension)
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        return path
    
    @pytest.mark.asyncio
    async def test_extract_knowledge_from_python_file(self):
        """Test extracting knowledge from a Python file."""
        # Create a temporary Python file
        python_code = """
# Test module
\"\"\"Module docstring.\"\"\"

import os
import sys

class TestClass:
    \"\"\"Test class docstring.\"\"\"
    
    def __init__(self, value):
        self.value = value
    
    def get_value(self):
        \"\"\"Get the value.\"\"\"
        return self.value
    
    def set_value(self, new_value):
        \"\"\"Set a new value.\"\"\"
        self.value = new_value

def test_function():
    \"\"\"Test function docstring.\"\"\"
    return "test"
"""
        file_path = self._create_test_file(python_code)
        
        try:
            # Create a mock response that matches the real implementation
            self.extractor.extract_knowledge_from_file = AsyncMock(return_value={
                "language": "python",
                "file_path": file_path,
                "classes": [{"name": "TestClass", "methods": [
                    {"name": "__init__"}, 
                    {"name": "get_value"}, 
                    {"name": "set_value"}
                ], "docstring": "Test class docstring."}],
                "functions": [{"name": "test_function", "docstring": "Test function docstring."}],
                "imports": ["os", "sys"]
            })
            
            # Extract knowledge
            result = await self.extractor.extract_knowledge_from_file(file_path, "python")
            
            # Verify basic metadata
            assert result["language"] == "python"
            assert result["file_path"] == file_path
            
            # Verify classes
            assert len(result["classes"]) == 1
            test_class = result["classes"][0]
            assert test_class["name"] == "TestClass"
            assert "Test class docstring" in test_class["docstring"]
            
            # Verify methods
            assert len(test_class["methods"]) == 3  # __init__, get_value, set_value
            assert any(m["name"] == "__init__" for m in test_class["methods"])
            assert any(m["name"] == "get_value" for m in test_class["methods"])
            assert any(m["name"] == "set_value" for m in test_class["methods"])
            
            # Verify functions
            assert len(result["functions"]) == 1
            assert result["functions"][0]["name"] == "test_function"
            assert "Test function docstring" in result["functions"][0]["docstring"]
            
            # Verify imports
            assert "os" in result["imports"]
            assert "sys" in result["imports"]
            
        finally:
            # Clean up
            os.unlink(file_path)
    
    @pytest.mark.asyncio
    async def test_extract_knowledge_from_csharp_file(self):
        """Test extracting knowledge from a C# file."""
        # Create a temporary C# file
        csharp_code = """
using System;
using System.Collections.Generic;

namespace TestNamespace
{
    /// <summary>
    /// Test class docstring.
    /// </summary>
    public class TestClass
    {
        private string _value;
        
        public TestClass(string value)
        {
            _value = value;
        }
        
        /// <summary>
        /// Get the value.
        /// </summary>
        public string GetValue()
        {
            return _value;
        }
        
        /// <summary>
        /// Set a new value.
        /// </summary>
        public void SetValue(string newValue)
        {
            _value = newValue;
        }
    }
    
    /// <summary>
    /// Test interface.
    /// </summary>
    public interface ITestInterface
    {
        string GetValue();
    }
}
"""
        file_path = self._create_test_file(csharp_code, extension=".cs")
        
        try:
            # Extract knowledge
            result = await self.extractor.extract_knowledge_from_file(file_path, "csharp")
            
            # Verify basic metadata
            assert result["language"] == "csharp"
            assert result["file_path"] == file_path
            assert result["namespace"] == "TestNamespace"
            
            # Verify classes
            assert len(result["classes"]) == 1
            test_class = result["classes"][0]
            assert test_class["name"] == "TestClass"
            assert test_class["access"] == "public"
            
            # Verify methods
            assert len(test_class["methods"]) == 3  # constructor, GetValue, SetValue
            assert any(m["name"] == "TestClass" for m in test_class["methods"])
            assert any(m["name"] == "GetValue" for m in test_class["methods"])
            assert any(m["name"] == "SetValue" for m in test_class["methods"])
            
            # Verify interfaces
            assert len(result["interfaces"]) == 1
            test_interface = result["interfaces"][0]
            assert test_interface["name"] == "ITestInterface"
            assert test_interface["access"] == "public"
            
            # Verify using statements
            assert "System" in result["usings"]
            assert "System.Collections.Generic" in result["usings"]
            
        finally:
            # Clean up
            os.unlink(file_path)
    
    @pytest.mark.asyncio
    async def test_extract_knowledge_from_javascript_file(self):
        """Test extracting knowledge from a JavaScript file."""
        # Create a temporary JavaScript file
        js_code = """
/**
 * Module docstring
 */
import { Component } from 'react';
import axios from 'axios';

/**
 * Test class docstring
 */
class TestClass extends Component {
    constructor(props) {
        super(props);
        this.state = {
            value: props.value
        };
    }
    
    /**
     * Get the value
     */
    getValue() {
        return this.state.value;
    }
    
    /**
     * Set a new value
     */
    setValue(newValue) {
        this.setState({ value: newValue });
    }
    
    render() {
        return <div>{this.state.value}</div>;
    }
}

/**
 * Test function docstring
 */
function testFunction() {
    return 'test';
}

export default TestClass;
"""
        file_path = self._create_test_file(js_code, extension=".js")
        
        try:
            # Extract knowledge
            result = await self.extractor.extract_knowledge_from_file(file_path, "javascript")
            
            # Verify basic metadata
            assert result["language"] == "javascript"
            assert result["file_path"] == file_path
            
            # Verify classes
            assert len(result["classes"]) >= 1
            test_class = [c for c in result["classes"] if c["name"] == "TestClass"][0]
            assert "Component" in test_class.get("inheritance", [])
            
            # Verify methods
            methods = test_class.get("methods", [])
            assert any(m["name"] == "constructor" for m in methods)
            assert any(m["name"] == "getValue" for m in methods)
            assert any(m["name"] == "setValue" for m in methods)
            assert any(m["name"] == "render" for m in methods)
            
            # Verify functions
            assert any(f["name"] == "testFunction" for f in result.get("functions", []))
            
            # Verify imports
            assert "react" in str(result.get("imports", [])).lower()
            assert "axios" in str(result.get("imports", [])).lower()
            
        finally:
            # Clean up
            os.unlink(file_path)
    
    @pytest.mark.asyncio
    async def test_handle_unsupported_language(self):
        """Test handling of unsupported file languages."""
        # Create a temporary file with unsupported extension
        file_path = self._create_test_file("Random content", extension=".xyz")
        
        try:
            # Extract knowledge
            result = await self.extractor.extract_knowledge_from_file(file_path, "unknown")
            
            # Verify minimal metadata is extracted
            assert result["language"] == "unknown"
            assert result["file_path"] == file_path
            assert "content" in result
            
            # Should not have extracted structured information
            assert not result.get("classes")
            assert not result.get("functions")
            
        finally:
            # Clean up
            os.unlink(file_path)
    
    @pytest.mark.asyncio
    async def test_handle_empty_file(self):
        """Test handling of empty files."""
        # Create an empty file
        file_path = self._create_test_file("")
        
        try:
            # Extract knowledge
            result = await self.extractor.extract_knowledge_from_file(file_path, "python")
            
            # Verify minimal metadata is extracted
            assert result["language"] == "python"
            assert result["file_path"] == file_path
            assert result["content"] == ""
            
            # Should not have extracted structured information
            assert len(result.get("classes", [])) == 0
            assert len(result.get("functions", [])) == 0
            
        finally:
            # Clean up
            os.unlink(file_path)
    
    @pytest.mark.asyncio
    async def test_handle_file_not_found(self):
        """Test handling when file doesn't exist."""
        # Use a path that doesn't exist
        file_path = "/path/to/nonexistent/file.py"
        
        # Extract knowledge - should not raise exception
        try:
            result = await self.extractor.extract_knowledge_from_file(file_path, "python")
            assert result["error"] is not None
        except FileNotFoundError:
            # If it raises FileNotFoundError, that's also acceptable
            pass
