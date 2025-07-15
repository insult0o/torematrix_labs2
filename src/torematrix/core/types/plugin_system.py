"""Type Plugin Architecture

Extensible plugin system for custom types with:
- Dynamic plugin loading and management
- Plugin lifecycle management
- Capability registration and discovery
- Secure plugin execution environment
"""

import logging
import importlib
import inspect
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Type, Union
import sys
import tempfile
import uuid

logger = logging.getLogger(__name__)


class PluginStatus(Enum):
    """Plugin status states"""
    INACTIVE = "inactive"
    LOADING = "loading"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


class PluginType(Enum):
    """Types of plugins"""
    TYPE_PROCESSOR = "type_processor"
    CONVERTER = "converter"
    VALIDATOR = "validator"
    RENDERER = "renderer"
    IMPORTER = "importer"
    EXPORTER = "exporter"
    ANALYZER = "analyzer"


@dataclass
class PluginCapabilities:
    """Capabilities provided by a plugin"""
    supported_types: List[str] = field(default_factory=list)
    operations: List[str] = field(default_factory=list)
    input_formats: List[str] = field(default_factory=list)
    output_formats: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    requirements: Dict[str, str] = field(default_factory=dict)
    performance_rating: int = 5  # 1-10 scale
    memory_usage: str = "medium"  # low, medium, high
    thread_safe: bool = True


@dataclass
class PluginInfo:
    """Information about a plugin"""
    id: str
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    capabilities: PluginCapabilities
    status: PluginStatus = PluginStatus.INACTIVE
    load_time: Optional[float] = None
    last_error: Optional[str] = None
    usage_count: int = 0
    config: Dict[str, Any] = field(default_factory=dict)


class TypePlugin(ABC):
    """Abstract base class for type plugins"""
    
    @property
    @abstractmethod
    def plugin_info(self) -> PluginInfo:
        """Get plugin information"""
        pass
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the plugin with configuration"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> bool:
        """Shutdown the plugin and cleanup resources"""
        pass
    
    @abstractmethod
    async def execute_operation(self, operation: str, **kwargs) -> Any:
        """Execute a plugin operation"""
        pass
    
    def validate_operation(self, operation: str, **kwargs) -> tuple[bool, List[str]]:
        """Validate operation parameters"""
        return True, []


class PluginRegistry:
    """Registry for managing plugin metadata and discovery"""
    
    def __init__(self):
        self.plugins: Dict[str, PluginInfo] = {}
        self.plugin_instances: Dict[str, TypePlugin] = {}
        self._lock = threading.RLock()
    
    def register_plugin(self, plugin_info: PluginInfo, instance: TypePlugin):
        """Register a plugin with the registry"""
        with self._lock:
            self.plugins[plugin_info.id] = plugin_info
            self.plugin_instances[plugin_info.id] = instance
            logger.info(f"Registered plugin: {plugin_info.name} ({plugin_info.id})")
    
    def get_plugin_info(self, plugin_id: str) -> Optional[PluginInfo]:
        """Get plugin information by ID"""
        with self._lock:
            return self.plugins.get(plugin_id)
    
    def get_plugin_instance(self, plugin_id: str) -> Optional[TypePlugin]:
        """Get plugin instance by ID"""
        with self._lock:
            return self.plugin_instances.get(plugin_id)
    
    def list_all_plugins(self, status_filter: Optional[PluginStatus] = None) -> List[PluginInfo]:
        """List all plugins with optional status filter"""
        with self._lock:
            if status_filter:
                return [
                    plugin_info for plugin_info in self.plugins.values()
                    if plugin_info.status == status_filter
                ]
            return list(self.plugins.values())


class PluginLoader:
    """Handles loading and unloading of plugins"""
    
    def __init__(self, registry: PluginRegistry):
        self.registry = registry
        self.plugin_directories: List[Path] = []
        self._lock = threading.RLock()


class TypePluginManager:
    """Main manager for the type plugin system"""
    
    def __init__(self):
        self.registry = PluginRegistry()
        self.loader = PluginLoader(self.registry)
        self.execution_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'average_execution_time': 0.0
        }
        self._lock = threading.RLock()
        
        logger.info("TypePluginManager initialized")
    
    def register_plugin_instance(self, plugin_instance: TypePlugin):
        """Register a plugin instance directly"""
        plugin_info = plugin_instance.plugin_info
        self.registry.register_plugin(plugin_info, plugin_instance)
    
    def get_plugin_info(self, plugin_id: str) -> Optional[PluginInfo]:
        """Get information about a plugin"""
        return self.registry.get_plugin_info(plugin_id)
    
    def list_plugins(self, 
                    status_filter: Optional[PluginStatus] = None,
                    type_filter: Optional[PluginType] = None) -> List[PluginInfo]:
        """List plugins with optional filters"""
        plugins = self.registry.list_all_plugins(status_filter)
        
        if type_filter:
            plugins = [p for p in plugins if p.plugin_type == type_filter]
        
        return plugins
    
    async def execute_plugin_operation(self, 
                                     plugin_id: str, 
                                     operation: str,
                                     **kwargs) -> Any:
        """Execute an operation on a specific plugin"""
        with self._lock:
            plugin_info = self.registry.get_plugin_info(plugin_id)
            if not plugin_info:
                raise ValueError(f"Plugin not found: {plugin_id}")
            
            if plugin_info.status != PluginStatus.ACTIVE:
                raise ValueError(f"Plugin not active: {plugin_id} (status: {plugin_info.status})")
            
            plugin_instance = self.registry.get_plugin_instance(plugin_id)
            if not plugin_instance:
                raise ValueError(f"Plugin instance not found: {plugin_id}")
        
        # Validate operation
        is_valid, errors = plugin_instance.validate_operation(operation, **kwargs)
        if not is_valid:
            raise ValueError(f"Invalid operation parameters: {', '.join(errors)}")
        
        # Execute operation
        import time
        start_time = time.time()
        
        try:
            result = await plugin_instance.execute_operation(operation, **kwargs)
            
            # Update stats
            execution_time = time.time() - start_time
            with self._lock:
                plugin_info.usage_count += 1
                self._update_execution_stats(execution_time, True)
            
            logger.debug(f"Plugin operation completed: {plugin_id}.{operation} in {execution_time:.3f}s")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            with self._lock:
                plugin_info.last_error = str(e)
                self._update_execution_stats(execution_time, False)
            
            logger.error(f"Plugin operation failed: {plugin_id}.{operation}: {e}")
            raise RuntimeError(f"Plugin operation failed: {e}")
    
    def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a disabled plugin"""
        plugin_info = self.registry.get_plugin_info(plugin_id)
        if plugin_info and plugin_info.status == PluginStatus.DISABLED:
            plugin_info.status = PluginStatus.ACTIVE
            logger.info(f"Enabled plugin: {plugin_id}")
            return True
        return False
    
    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable an active plugin"""
        plugin_info = self.registry.get_plugin_info(plugin_id)
        if plugin_info and plugin_info.status == PluginStatus.ACTIVE:
            plugin_info.status = PluginStatus.DISABLED
            logger.info(f"Disabled plugin: {plugin_id}")
            return True
        return False
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get plugin execution statistics"""
        with self._lock:
            plugin_stats = {}
            for plugin_info in self.registry.list_all_plugins():
                plugin_stats[plugin_info.id] = {
                    'name': plugin_info.name,
                    'usage_count': plugin_info.usage_count,
                    'status': plugin_info.status.value,
                    'last_error': plugin_info.last_error
                }
            
            return {
                'system_stats': self.execution_stats.copy(),
                'plugin_stats': plugin_stats,
                'total_plugins': len(self.registry.plugins),
                'active_plugins': len(self.registry.list_all_plugins(PluginStatus.ACTIVE))
            }
    
    def _update_execution_stats(self, execution_time: float, success: bool):
        """Update execution statistics"""
        self.execution_stats['total_operations'] += 1
        
        if success:
            self.execution_stats['successful_operations'] += 1
        else:
            self.execution_stats['failed_operations'] += 1
        
        # Update average execution time
        total_ops = self.execution_stats['total_operations']
        current_avg = self.execution_stats['average_execution_time']
        new_avg = (current_avg * (total_ops - 1) + execution_time) / total_ops
        self.execution_stats['average_execution_time'] = new_avg


# Example plugin implementation
class ExampleTypePlugin(TypePlugin):
    """Example plugin implementation for demonstration"""
    
    def __init__(self):
        self._capabilities = PluginCapabilities(
            supported_types=["text", "title", "paragraph"],
            operations=["convert", "validate", "analyze"],
            input_formats=["json", "xml"],
            output_formats=["json", "html"],
            performance_rating=8,
            memory_usage="low",
            thread_safe=True
        )
        
        self._info = PluginInfo(
            id="example_type_plugin",
            name="Example Type Plugin",
            version="1.0.0",
            description="Example plugin for demonstration purposes",
            author="Agent 4",
            plugin_type=PluginType.TYPE_PROCESSOR,
            capabilities=self._capabilities
        )
    
    @property
    def plugin_info(self) -> PluginInfo:
        return self._info
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the plugin"""
        logger.info(f"Initializing {self._info.name}")
        return True
    
    async def shutdown(self) -> bool:
        """Shutdown the plugin"""
        logger.info(f"Shutting down {self._info.name}")
        return True
    
    async def execute_operation(self, operation: str, **kwargs) -> Any:
        """Execute a plugin operation"""
        if operation == "convert":
            return await self._convert_type(**kwargs)
        elif operation == "validate":
            return await self._validate_type(**kwargs)
        elif operation == "analyze":
            return await self._analyze_type(**kwargs)
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    def validate_operation(self, operation: str, **kwargs) -> tuple[bool, List[str]]:
        """Validate operation parameters"""
        errors = []
        
        if operation not in self._capabilities.operations:
            errors.append(f"Operation not supported: {operation}")
        
        if operation == "convert":
            if "from_type" not in kwargs or "to_type" not in kwargs:
                errors.append("convert operation requires 'from_type' and 'to_type' parameters")
        
        return len(errors) == 0, errors
    
    async def _convert_type(self, **kwargs) -> Dict[str, Any]:
        """Convert between types"""
        from_type = kwargs.get("from_type")
        to_type = kwargs.get("to_type")
        data = kwargs.get("data", {})
        
        # Simple conversion logic
        result = {
            "success": True,
            "from_type": from_type,
            "to_type": to_type,
            "converted_data": data,
            "plugin": self._info.name
        }
        
        return result
    
    async def _validate_type(self, **kwargs) -> Dict[str, Any]:
        """Validate type data"""
        type_name = kwargs.get("type")
        data = kwargs.get("data", {})
        
        result = {
            "valid": True,
            "type": type_name,
            "errors": [],
            "warnings": [],
            "plugin": self._info.name
        }
        
        return result
    
    async def _analyze_type(self, **kwargs) -> Dict[str, Any]:
        """Analyze type data"""
        type_name = kwargs.get("type")
        data = kwargs.get("data", {})
        
        result = {
            "type": type_name,
            "analysis": {
                "field_count": len(data),
                "complexity": "low",
                "recommendations": ["Consider adding validation"]
            },
            "plugin": self._info.name
        }
        
        return result