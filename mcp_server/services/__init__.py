"""
AI Services package

This module provides a registry of AI services that can be used by the MCP server.
"""

from typing import Dict, Optional, Type
import logging

from mcp_server.services.claude_service import AIServiceInterface, ClaudeService, MockClaudeService
from mcp_server.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)


class AIServiceRegistry:
    """Registry for AI services that can be dynamically selected"""
    
    def __init__(self):
        """Initialize an empty registry"""
        self.services: Dict[str, AIServiceInterface] = {}
        self.default_service: Optional[str] = None
    
    def register_service(self, service_name: str, service: AIServiceInterface, 
                        make_default: bool = False):
        """Register a service with the registry"""
        self.services[service_name] = service
        logger.info(f"Registered AI service: {service_name}")
        
        if make_default or self.default_service is None:
            self.default_service = service_name
            logger.info(f"Set default AI service to: {service_name}")
    
    def get_service(self, service_name: Optional[str] = None) -> Optional[AIServiceInterface]:
        """Get a service by name, or the default if none specified"""
        # If no service name provided, use the default
        if service_name is None:
            if self.default_service is None:
                logger.warning("No default AI service set")
                return None
            service_name = self.default_service
        
        # Get the requested service
        service = self.services.get(service_name)
        if service is None:
            logger.warning(f"AI service not found: {service_name}")
        
        return service
    
    def list_services(self) -> Dict[str, str]:
        """List available services and their types"""
        return {name: service.__class__.__name__ for name, service in self.services.items()}


def create_ai_services_from_config(config):
    """Create AI services based on configuration"""
    registry = AIServiceRegistry()
    
    # Always register a mock service for testing
    registry.register_service(
        "mock", 
        MockClaudeService(),
        make_default=(config.ai_service_type == "mock")
    )
    
    # Register Claude if configured
    if config.anthropic_api_key:
        claude_service = ClaudeService(
            api_key=config.anthropic_api_key,
            default_model=config.claude_default_model,
            default_max_tokens=config.claude_default_max_tokens,
            default_temperature=config.claude_default_temperature
        )
        registry.register_service(
            "claude", 
            claude_service,
            make_default=(config.ai_service_type == "claude")
        )
    
    # Register OpenAI if configured
    if config.openai_api_key:
        openai_service = OpenAIService(
            api_key=config.openai_api_key,
            default_model=config.openai_default_model,
            default_max_tokens=config.openai_default_max_tokens,
            default_temperature=config.openai_default_temperature
        )
        registry.register_service(
            "openai", 
            openai_service,
            make_default=(config.ai_service_type == "openai")
        )
    
    return registry