"""
Knowledge Extraction package for MCP Server.

This package provides enhanced knowledge extraction capabilities including:
- Deep Code Content Extraction
- Function Call Graphs and Data Flow Analysis
- Development Pattern Extraction
- Environment and Dependency Analysis
- Documentation Extraction
- Context-Aware Code Chunking
"""

# Import all extraction modules
from .code_extractor import CodeExtractor
from .pattern_extractor import PatternExtractor
from .call_graph_analyzer import CallGraphAnalyzer
from .environment_analyzer import EnvironmentAnalyzer
from .documentation_extractor import DocumentationExtractor
from .code_chunker import CodeChunker
from .md_builder import MarkdownBuilder

# Expose the classes for easier imports
__all__ = [
    'CodeExtractor',
    'PatternExtractor',
    'CallGraphAnalyzer',
    'EnvironmentAnalyzer',
    'DocumentationExtractor',
    'CodeChunker',
    'MarkdownBuilder'
]
