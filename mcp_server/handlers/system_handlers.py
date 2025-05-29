"""
System-related handlers for MCP Server

This module provides handlers for system-related methods like system information,
health checks, and diagnostics.
"""

import os
import sys
import platform
import psutil
import datetime
from typing import Any, Dict

from mcp_server.core.server import HandlerInterface


class SystemInfoHandler(HandlerInterface):
    """Handler for the system/info method which returns system resource information"""
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system/info request
        
        Returns information about the system resources, memory usage,
        CPU info, etc.
        """
        try:
            # Get memory information
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Build the response
            info = {
                "system": {
                    "platform": platform.platform(),
                    "python_version": sys.version,
                    "processor": platform.processor(),
                    "cpu_count": psutil.cpu_count(logical=False),
                    "logical_cpu_count": psutil.cpu_count(logical=True),
                    "hostname": platform.node()
                },
                "memory": {
                    "total": self._format_bytes(memory.total),
                    "available": self._format_bytes(memory.available),
                    "percent_used": memory.percent
                },
                "disk": {
                    "total": self._format_bytes(disk.total),
                    "free": self._format_bytes(disk.free),
                    "percent_used": disk.percent
                },
                "cpu": {
                    "percent": psutil.cpu_percent(interval=0.1),
                    "per_cpu": psutil.cpu_percent(interval=0.1, percpu=True)
                },
                "time": {
                    "server_time": datetime.datetime.now().isoformat(),
                    "boot_time": datetime.datetime.fromtimestamp(
                        psutil.boot_time()).isoformat()
                }
            }
            
            return {
                "info": info,
                "status": "ok"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human-readable string"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024
        return f"{bytes_value:.2f} PB"


class SystemHealthHandler(HandlerInterface):
    """Handler for the system/health method which returns health status"""
    
    def __init__(self, service_dependencies=None):
        """Initialize with optional service dependencies to check"""
        self.service_dependencies = service_dependencies or []
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system/health request
        
        Returns health status of the server and its dependencies
        """
        health_status = {
            "status": "healthy",
            "uptime": self._get_uptime(),
            "timestamp": datetime.datetime.now().isoformat(),
            "services": {}
        }
        
        # Check service dependencies if any
        for service in self.service_dependencies:
            try:
                # This would be implemented to check each service
                # For now, we'll just set all to healthy
                health_status["services"][service] = {
                    "status": "healthy"
                }
            except Exception as e:
                health_status["services"][service] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health_status["status"] = "degraded"
        
        return health_status
    
    def _get_uptime(self) -> str:
        """Get system uptime as a formatted string"""
        uptime_seconds = datetime.datetime.now().timestamp() - psutil.boot_time()
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
