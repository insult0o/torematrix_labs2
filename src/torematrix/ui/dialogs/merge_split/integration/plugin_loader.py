"""
Plugin System for Merge/Split Operations Engine.

Agent 4 - Integration & Advanced Features (Issue #237)
Provides extensible plugin architecture for custom merge/split operations,
dynamic loading, and plugin lifecycle management.
"""

from typing import Dict, List, Optional, Any, Callable, Union, Type, Protocol
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import asyncio
import importlib
import importlib.util
import inspect
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
import uuid
import traceback

from .....core.events import EventBus
from .....core.state import Store
from .....core.models import Element

logger = logging.getLogger(__name__)


class PluginStatus(Enum):
    """Plugin lifecycle status."""
    UNKNOWN = "unknown"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"
    UNLOADED = "unloaded"


class PluginType(Enum):
    """Types of plugins."""
    MERGE_OPERATION = "merge_operation"
    SPLIT_OPERATION = "split_operation"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    EXPORT = "export"
    IMPORT = "import"
    AUTOMATION = "automation"
    UI_EXTENSION = "ui_extension"


class PluginError(Exception):
    """Exception raised for plugin-related errors."""
    def __init__(self, message: str, plugin_name: str = None, error_code: str = None):
        super().__init__(message)
        self.plugin_name = plugin_name
        self.error_code = error_code


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""
    name: str
    version: str
    plugin_type: PluginType
    description: str = ""
    author: str = ""
    license: str = ""
    dependencies: List[str] = field(default_factory=list)
    api_version: str = "1.0.0"
    min_core_version: str = "1.0.0"
    max_core_version: str = ""
    tags: List[str] = field(default_factory=list)
    homepage: str = ""
    repository: str = ""
    documentation: str = ""
    enabled: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginMetadata':
        """Create metadata from dictionary."""
        plugin_type = PluginType(data.get('plugin_type', 'merge_operation'))
        return cls(
            name=data['name'],
            version=data['version'],
            plugin_type=plugin_type,
            description=data.get('description', ''),
            author=data.get('author', ''),
            license=data.get('license', ''),
            dependencies=data.get('dependencies', []),
            api_version=data.get('api_version', '1.0.0'),
            min_core_version=data.get('min_core_version', '1.0.0'),
            max_core_version=data.get('max_core_version', ''),
            tags=data.get('tags', []),
            homepage=data.get('homepage', ''),
            repository=data.get('repository', ''),
            documentation=data.get('documentation', ''),
            enabled=data.get('enabled', True)
        )


class PluginInterface(Protocol):
    """Protocol that all plugins must implement."""
    
    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        ...
    
    async def initialize(self, context: 'PluginContext') -> None:
        """Initialize the plugin."""
        ...
    
    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        ...


class MergeOperationPlugin(PluginInterface, Protocol):
    """Protocol for merge operation plugins."""
    
    async def can_merge(self, elements: List[Element]) -> bool:
        """Check if this plugin can merge the given elements."""
        ...
    
    async def merge_elements(
        self, 
        elements: List[Element], 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge elements using this plugin."""
        ...
    
    def get_merge_options(self) -> Dict[str, Any]:
        """Get available merge options for this plugin."""
        ...


class SplitOperationPlugin(PluginInterface, Protocol):
    """Protocol for split operation plugins."""
    
    async def can_split(self, element: Element) -> bool:
        """Check if this plugin can split the given element."""
        ...
    
    async def split_element(
        self, 
        element: Element, 
        split_points: List[int], 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Split element using this plugin."""
        ...
    
    def get_split_options(self) -> Dict[str, Any]:
        """Get available split options for this plugin."""
        ...


class CustomOperationPlugin(PluginInterface, Protocol):
    """Protocol for custom operation plugins."""
    
    async def execute_operation(
        self, 
        operation_type: str, 
        elements: List[Element], 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a custom operation."""
        ...
    
    def get_supported_operations(self) -> List[str]:
        """Get list of supported operations."""
        ...


@dataclass
class PluginContext:
    """Context provided to plugins during initialization."""
    event_bus: EventBus
    store: Store
    plugin_directory: Path
    config: Dict[str, Any] = field(default_factory=dict)
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger(__name__))


@dataclass
class LoadedPlugin:
    """Information about a loaded plugin."""
    metadata: PluginMetadata
    instance: PluginInterface
    module: Any
    file_path: Path
    status: PluginStatus = PluginStatus.LOADED
    load_time: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    context: Optional[PluginContext] = None


class PluginRegistry:
    """Registry for managing loaded plugins."""
    
    def __init__(self):
        self._plugins: Dict[str, LoadedPlugin] = {}
        self._plugins_by_type: Dict[PluginType, List[str]] = {}
        self._plugin_dependencies: Dict[str, Set[str]] = {}
    
    def register_plugin(self, plugin: LoadedPlugin) -> None:
        """Register a loaded plugin."""
        name = plugin.metadata.name
        self._plugins[name] = plugin
        
        # Track by type
        plugin_type = plugin.metadata.plugin_type
        if plugin_type not in self._plugins_by_type:
            self._plugins_by_type[plugin_type] = []
        self._plugins_by_type[plugin_type].append(name)
        
        # Track dependencies
        self._plugin_dependencies[name] = set(plugin.metadata.dependencies)
        
        logger.info(f"Registered plugin: {name} v{plugin.metadata.version}")
    
    def unregister_plugin(self, name: str) -> Optional[LoadedPlugin]:
        """Unregister a plugin."""
        plugin = self._plugins.pop(name, None)
        if plugin:
            # Remove from type tracking
            plugin_type = plugin.metadata.plugin_type
            if plugin_type in self._plugins_by_type:
                self._plugins_by_type[plugin_type].remove(name)
            
            # Remove dependencies
            self._plugin_dependencies.pop(name, None)
            
            logger.info(f"Unregistered plugin: {name}")
        
        return plugin
    
    def get_plugin(self, name: str) -> Optional[LoadedPlugin]:
        """Get plugin by name."""
        return self._plugins.get(name)
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[LoadedPlugin]:
        """Get all plugins of a specific type."""
        plugin_names = self._plugins_by_type.get(plugin_type, [])
        return [self._plugins[name] for name in plugin_names if name in self._plugins]
    
    def get_active_plugins(self) -> List[LoadedPlugin]:
        """Get all active plugins."""
        return [plugin for plugin in self._plugins.values() 
                if plugin.status == PluginStatus.ACTIVE]
    
    def get_plugin_dependency_order(self) -> List[str]:
        """Get plugins in dependency order for initialization."""
        visited = set()
        temp_mark = set()
        result = []
        
        def visit(name: str):
            if name in temp_mark:
                raise PluginError(f"Circular dependency detected involving plugin {name}")
            if name in visited:
                return
            
            temp_mark.add(name)
            for dep in self._plugin_dependencies.get(name, set()):
                if dep in self._plugin_dependencies:  # Only visit if dependency is loaded
                    visit(dep)
            temp_mark.remove(name)
            visited.add(name)
            result.append(name)
        
        for name in self._plugins:
            if name not in visited:
                visit(name)
        
        return result
    
    def update_plugin_status(self, name: str, status: PluginStatus, error: str = None) -> None:
        """Update plugin status."""
        if name in self._plugins:
            self._plugins[name].status = status
            if error:
                self._plugins[name].error = error
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all registered plugins with their info."""
        return [
            {
                'name': plugin.metadata.name,
                'version': plugin.metadata.version,
                'type': plugin.metadata.plugin_type.value,
                'description': plugin.metadata.description,
                'author': plugin.metadata.author,
                'status': plugin.status.value,
                'enabled': plugin.metadata.enabled,
                'load_time': plugin.load_time.isoformat(),
                'error': plugin.error
            }
            for plugin in self._plugins.values()
        ]


class PluginLoader:
    """Dynamic plugin loader and manager."""
    
    def __init__(self, event_bus: EventBus, store: Store):
        self.event_bus = event_bus
        self.store = store
        self._registry = PluginRegistry()
        self._plugin_directories: List[Path] = []
        self._auto_reload = False
        self._initialized = False
    
    @property
    def registry(self) -> PluginRegistry:
        """Get plugin registry."""
        return self._registry
    
    def add_plugin_directory(self, directory: Union[str, Path]) -> None:
        """Add a directory to search for plugins."""
        path = Path(directory)
        if path.exists() and path.is_dir():
            self._plugin_directories.append(path)
            logger.info(f"Added plugin directory: {path}")
        else:
            logger.warning(f"Plugin directory does not exist: {path}")
    
    async def initialize(self) -> None:
        """Initialize the plugin loader."""
        if self._initialized:
            logger.warning("PluginLoader already initialized")
            return
        
        logger.info("Initializing PluginLoader...")
        
        # Add default plugin directories
        self._add_default_plugin_directories()
        
        # Load plugins from all directories
        await self._discover_and_load_plugins()
        
        # Initialize plugins in dependency order
        await self._initialize_plugins()
        
        self._initialized = True
        logger.info("PluginLoader initialization completed")
    
    def _add_default_plugin_directories(self) -> None:
        """Add default plugin directories."""
        # Add standard plugin directories
        default_dirs = [
            Path(__file__).parent.parent / "plugins",
            Path.home() / ".torematrix" / "plugins",
            Path("/etc/torematrix/plugins") if os.name == 'posix' else None
        ]
        
        for directory in default_dirs:
            if directory and directory.exists():
                self.add_plugin_directory(directory)
    
    async def _discover_and_load_plugins(self) -> None:
        """Discover and load plugins from all directories."""
        for directory in self._plugin_directories:
            await self._load_plugins_from_directory(directory)
    
    async def _load_plugins_from_directory(self, directory: Path) -> None:
        """Load plugins from a specific directory."""
        logger.info(f"Loading plugins from: {directory}")
        
        # Look for plugin.json files
        for plugin_file in directory.rglob("plugin.json"):
            plugin_dir = plugin_file.parent
            await self._load_plugin_from_directory(plugin_dir)
    
    async def _load_plugin_from_directory(self, plugin_dir: Path) -> None:
        """Load a plugin from its directory."""
        plugin_json = plugin_dir / "plugin.json"
        
        if not plugin_json.exists():
            logger.warning(f"No plugin.json found in {plugin_dir}")
            return
        
        try:
            # Load plugin metadata
            with open(plugin_json, 'r') as f:
                metadata_dict = json.load(f)
            
            metadata = PluginMetadata.from_dict(metadata_dict)
            
            if not metadata.enabled:
                logger.info(f"Plugin {metadata.name} is disabled, skipping")
                return
            
            # Load plugin module
            plugin_module = metadata_dict.get('module', 'plugin.py')
            plugin_file = plugin_dir / plugin_module
            
            if not plugin_file.exists():
                raise PluginError(f"Plugin module not found: {plugin_file}", metadata.name)
            
            # Import plugin module
            spec = importlib.util.spec_from_file_location(
                f"plugin_{metadata.name}",
                plugin_file
            )
            
            if not spec or not spec.loader:
                raise PluginError(f"Could not create module spec for {plugin_file}", metadata.name)
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin class
            plugin_class = self._find_plugin_class(module, metadata)
            if not plugin_class:
                raise PluginError(f"No valid plugin class found in {plugin_file}", metadata.name)
            
            # Create plugin instance
            plugin_instance = plugin_class()
            
            # Verify plugin implements required interface
            if not isinstance(plugin_instance, PluginInterface):
                raise PluginError(f"Plugin does not implement PluginInterface", metadata.name)
            
            # Create loaded plugin object
            loaded_plugin = LoadedPlugin(
                metadata=metadata,
                instance=plugin_instance,
                module=module,
                file_path=plugin_file,
                status=PluginStatus.LOADED
            )
            
            # Register plugin
            self._registry.register_plugin(loaded_plugin)
            
            logger.info(f"Loaded plugin: {metadata.name} v{metadata.version}")
            
        except Exception as e:
            logger.error(f"Failed to load plugin from {plugin_dir}: {e}")
            logger.debug(traceback.format_exc())
    
    def _find_plugin_class(self, module: Any, metadata: PluginMetadata) -> Optional[Type]:
        """Find the plugin class in a module."""
        # Look for classes that implement the appropriate protocol
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ == module.__name__:
                # Check if it's a plugin class based on metadata type
                if metadata.plugin_type == PluginType.MERGE_OPERATION:
                    if self._implements_protocol(obj, MergeOperationPlugin):
                        return obj
                elif metadata.plugin_type == PluginType.SPLIT_OPERATION:
                    if self._implements_protocol(obj, SplitOperationPlugin):
                        return obj
                elif self._implements_protocol(obj, CustomOperationPlugin):
                    return obj
                elif self._implements_protocol(obj, PluginInterface):
                    return obj
        
        return None
    
    def _implements_protocol(self, cls: Type, protocol: Type) -> bool:
        """Check if a class implements a protocol."""
        try:
            # Check if all required methods exist
            protocol_methods = [
                name for name, method in inspect.getmembers(protocol, inspect.isfunction)
                if not name.startswith('_')
            ]
            
            for method_name in protocol_methods:
                if not hasattr(cls, method_name):
                    return False
            
            return True
        except Exception:
            return False
    
    async def _initialize_plugins(self) -> None:
        """Initialize plugins in dependency order."""
        dependency_order = self._registry.get_plugin_dependency_order()
        
        for plugin_name in dependency_order:
            plugin = self._registry.get_plugin(plugin_name)
            if plugin and plugin.status == PluginStatus.LOADED:
                try:
                    # Create plugin context
                    context = PluginContext(
                        event_bus=self.event_bus,
                        store=self.store,
                        plugin_directory=plugin.file_path.parent,
                        logger=logging.getLogger(f"plugin.{plugin.metadata.name}")
                    )
                    
                    plugin.context = context
                    
                    # Initialize plugin
                    await plugin.instance.initialize(context)
                    
                    self._registry.update_plugin_status(plugin_name, PluginStatus.ACTIVE)
                    logger.info(f"Initialized plugin: {plugin_name}")
                    
                except Exception as e:
                    error_msg = f"Failed to initialize plugin {plugin_name}: {e}"
                    self._registry.update_plugin_status(plugin_name, PluginStatus.ERROR, error_msg)
                    logger.error(error_msg)
                    logger.debug(traceback.format_exc())
    
    async def get_merge_plugins(self) -> List[LoadedPlugin]:
        """Get all active merge operation plugins."""
        return [
            plugin for plugin in self._registry.get_plugins_by_type(PluginType.MERGE_OPERATION)
            if plugin.status == PluginStatus.ACTIVE
        ]
    
    async def get_split_plugins(self) -> List[LoadedPlugin]:
        """Get all active split operation plugins."""
        return [
            plugin for plugin in self._registry.get_plugins_by_type(PluginType.SPLIT_OPERATION)
            if plugin.status == PluginStatus.ACTIVE
        ]
    
    async def find_merge_plugins_for_elements(self, elements: List[Element]) -> List[LoadedPlugin]:
        """Find merge plugins that can handle the given elements."""
        merge_plugins = await self.get_merge_plugins()
        compatible_plugins = []
        
        for plugin in merge_plugins:
            try:
                if hasattr(plugin.instance, 'can_merge'):
                    if await plugin.instance.can_merge(elements):
                        compatible_plugins.append(plugin)
            except Exception as e:
                logger.error(f"Error checking plugin {plugin.metadata.name} compatibility: {e}")
        
        return compatible_plugins
    
    async def find_split_plugins_for_element(self, element: Element) -> List[LoadedPlugin]:
        """Find split plugins that can handle the given element."""
        split_plugins = await self.get_split_plugins()
        compatible_plugins = []
        
        for plugin in split_plugins:
            try:
                if hasattr(plugin.instance, 'can_split'):
                    if await plugin.instance.can_split(element):
                        compatible_plugins.append(plugin)
            except Exception as e:
                logger.error(f"Error checking plugin {plugin.metadata.name} compatibility: {e}")
        
        return compatible_plugins
    
    async def execute_merge_with_plugin(
        self, 
        plugin_name: str, 
        elements: List[Element], 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute merge operation with a specific plugin."""
        plugin = self._registry.get_plugin(plugin_name)
        if not plugin or plugin.status != PluginStatus.ACTIVE:
            raise PluginError(f"Plugin {plugin_name} not available", plugin_name)
        
        if not hasattr(plugin.instance, 'merge_elements'):
            raise PluginError(f"Plugin {plugin_name} does not support merge operations", plugin_name)
        
        try:
            result = await plugin.instance.merge_elements(elements, options)
            logger.info(f"Merge operation completed with plugin {plugin_name}")
            return result
        except Exception as e:
            logger.error(f"Merge operation failed with plugin {plugin_name}: {e}")
            raise
    
    async def execute_split_with_plugin(
        self, 
        plugin_name: str, 
        element: Element, 
        split_points: List[int], 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute split operation with a specific plugin."""
        plugin = self._registry.get_plugin(plugin_name)
        if not plugin or plugin.status != PluginStatus.ACTIVE:
            raise PluginError(f"Plugin {plugin_name} not available", plugin_name)
        
        if not hasattr(plugin.instance, 'split_element'):
            raise PluginError(f"Plugin {plugin_name} does not support split operations", plugin_name)
        
        try:
            result = await plugin.instance.split_element(element, split_points, options)
            logger.info(f"Split operation completed with plugin {plugin_name}")
            return result
        except Exception as e:
            logger.error(f"Split operation failed with plugin {plugin_name}: {e}")
            raise
    
    async def reload_plugin(self, plugin_name: str) -> bool:
        """Reload a specific plugin."""
        plugin = self._registry.get_plugin(plugin_name)
        if not plugin:
            logger.warning(f"Plugin {plugin_name} not found for reload")
            return False
        
        try:
            # Shutdown existing plugin
            if plugin.instance and hasattr(plugin.instance, 'shutdown'):
                await plugin.instance.shutdown()
            
            # Unregister plugin
            self._registry.unregister_plugin(plugin_name)
            
            # Reload from directory
            await self._load_plugin_from_directory(plugin.file_path.parent)
            
            # Re-initialize if successful
            new_plugin = self._registry.get_plugin(plugin_name)
            if new_plugin:
                await self._initialize_plugins()
                logger.info(f"Plugin {plugin_name} reloaded successfully")
                return True
            
        except Exception as e:
            logger.error(f"Failed to reload plugin {plugin_name}: {e}")
        
        return False
    
    async def shutdown(self) -> None:
        """Shutdown the plugin loader and all plugins."""
        logger.info("Shutting down PluginLoader...")
        
        # Shutdown all plugins in reverse dependency order
        dependency_order = self._registry.get_plugin_dependency_order()
        for plugin_name in reversed(dependency_order):
            plugin = self._registry.get_plugin(plugin_name)
            if plugin and plugin.instance:
                try:
                    if hasattr(plugin.instance, 'shutdown'):
                        await plugin.instance.shutdown()
                    self._registry.update_plugin_status(plugin_name, PluginStatus.UNLOADED)
                except Exception as e:
                    logger.error(f"Error shutting down plugin {plugin_name}: {e}")
        
        self._initialized = False
        logger.info("PluginLoader shutdown completed")


# Convenience factory function
async def create_plugin_loader(event_bus: EventBus, store: Store) -> PluginLoader:
    """Create and initialize a plugin loader."""
    loader = PluginLoader(event_bus, store)
    await loader.initialize()
    return loader