"""
Handlers for MCP Server

This package provides request handlers for various RPC methods.
"""

from .base_handlers import InitializeHandler, ToolsListHandler, ToolsCallHandler, ResourcesListHandler, ResourcesReadHandler
from .system_handlers import SystemInfoHandler, SystemHealthHandler
from .knowledge_handlers import RepositoryAnalysisHandler, KnowledgeExtractionHandler
from .enhanced_knowledge_handlers import (
    EnhancedRepositoryAnalysisHandler,
    EnhancedCodeSearchHandler,
    DependencyAnalysisHandler
)

__all__ = [
    'InitializeHandler',
    'ToolsListHandler',
    'ToolsCallHandler',
    'ResourcesListHandler',
    'ResourcesReadHandler',
    'SystemInfoHandler',
    'SystemHealthHandler',
    'RepositoryAnalysisHandler',
    'KnowledgeExtractionHandler',
    'EnhancedRepositoryAnalysisHandler',
    'EnhancedCodeSearchHandler',
    'DependencyAnalysisHandler'
]
