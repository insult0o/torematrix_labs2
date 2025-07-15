"""Type Plugin Architecture

Extensible plugin system for custom types allowing third-party extensions
and specialized type implementations.
"""

import logging
import importlib
import inspect
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Set, Type, Callable
import threading

logger = logging.getLogger(__name__)


class PluginStatus(Enum):
    """Status of plugin operations"""
    UNKNOWN = "unknown"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    DISABLED = "disabled"


class PluginCapabilityType(Enum):
    """Types of plugin capabilities"""
    TYPE_CREATION = "type_creation"
    TYPE_VALIDATION = "type_validation"
    TYPE_CONVERSION = "type_conversion"
    DATA_PROCESSING = "data_processing"
    UI_EXTENSION = "ui_extension"
    API_EXTENSION = "api_extension"
    IMPORT_EXPORT = "import_export"
    CUSTOM_RENDERER = "custom_renderer"


@dataclass
class PluginCapabilities:
    """Describes what a plugin can do"""
    capabilities: Set[PluginCapabilityType]
    supported_types: Set[str] = field(default_factory=set)
    input_formats: Set[str] = field(default_factory=set)
    output_formats: Set[str] = field(default_factory=set)
    version_requirements: Dict[str, str] = field(default_factory=dict)
    dependencies: Set[str] = field(default_factory=set)
    configuration_schema: Optional[Dict[str, Any]] = None
    
    def supports_capability(self, capability: PluginCapabilityType) -> bool:
        """Check if plugin supports a specific capability"""
        return capability in self.capabilities
    
    def supports_type(self, type_id: str) -> bool:
        """Check if plugin supports a specific type"""
        return type_id in self.supported_types or len(self.supported_types) == 0


@dataclass
class PluginMetadata:
    """Metadata for a plugin"""
    plugin_id: str
    name: str
    description: str
    version: str
    author: str = ""
    homepage: str = ""
    license: str = ""
    keywords: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class PluginConfiguration:
    """Configuration for a plugin instance"""
    plugin_id: str
    enabled: bool = True
    settings: Dict[str, Any] = field(default_factory=dict)
    priority: int = 100
    auto_load: bool = True
    configuration_version: str = "1.0.0"


class TypePlugin(ABC):
    """Base class for type plugins
    
    All type plugins must inherit from this class and implement
    the required abstract methods.
    """
    
    def __init__(self, plugin_id: str):
        """Initialize plugin
        
        Args:
            plugin_id: Unique identifier for this plugin
        """
        self.plugin_id = plugin_id
        self._status = PluginStatus.UNKNOWN
        self._configuration: Optional[PluginConfiguration] = None
        self._error_message: Optional[str] = None
        
    @property
    def status(self) -> PluginStatus:
        """Get current plugin status"""
        return self._status
    
    @property
    def error_message(self) -> Optional[str]:
        """Get last error message if any"""
        return self._error_message
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> PluginCapabilities:
        """Get plugin capabilities"""
        pass
    
    @abstractmethod
    def initialize(self, configuration: PluginConfiguration) -> bool:
        """Initialize the plugin with configuration
        
        Args:
            configuration: Plugin configuration
            
        Returns:
            True if initialization succeeded
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """Shutdown the plugin
        
        Returns:
            True if shutdown succeeded
        """
        pass
    
    def configure(self, settings: Dict[str, Any]) -> bool:
        """Configure plugin with new settings
        
        Args:
            settings: Configuration settings
            
        Returns:
            True if configuration succeeded
        """
        if self._configuration:
            self._configuration.settings.update(settings)
            return True
        return False
    
    def get_configuration(self) -> Optional[PluginConfiguration]:
        """Get current plugin configuration"""
        return self._configuration
    
    def validate_configuration(self, settings: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate configuration settings
        
        Args:
            settings: Settings to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        # Default implementation - override in subclasses for custom validation
        return True, []
    
    def execute_operation(self, operation: str, **kwargs) -> Any:
        """Execute a plugin operation
        
        Args:
            operation: Operation name
            **kwargs: Operation parameters
            
        Returns:
            Operation result
            
        Raises:
            NotImplementedError: If operation is not supported
        """
        if hasattr(self, f"_execute_{operation}"):
            method = getattr(self, f"_execute_{operation}")
            return method(**kwargs)
        else:
            raise NotImplementedError(f"Operation '{operation}' not supported by plugin {self.plugin_id}")
    
    def _set_status(self, status: PluginStatus, error_message: Optional[str] = None) -> None:
        """Set plugin status"""
        self._status = status
        self._error_message = error_message
        if error_message:
            logger.error(f"Plugin {self.plugin_id} error: {error_message}")


class PluginLoader:
    """Loads plugins from various sources"""
    
    def __init__(self):
        """Initialize plugin loader"""
        self._loaded_modules: Dict[str, Any] = {}
        self._lock = threading.RLock()
    
    def load_plugin_from_file(self, plugin_file: Path) -> Optional[Type[TypePlugin]]:
        """Load a plugin from a Python file
        
        Args:
            plugin_file: Path to plugin file
            
        Returns:
            Plugin class if successful, None otherwise
        """
        try:
            with self._lock:
                # Import the module
                spec = importlib.util.spec_from_file_location(
                    f"plugin_{plugin_file.stem}", 
                    plugin_file
                )
                if not spec or not spec.loader:
                    logger.error(f"Failed to create spec for plugin file: {plugin_file}")
                    return None
                
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find TypePlugin subclasses
                plugin_classes = []
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, TypePlugin) and 
                        obj != TypePlugin and 
                        obj.__module__ == module.__name__):
                        plugin_classes.append(obj)
                
                if not plugin_classes:
                    logger.warning(f"No TypePlugin subclasses found in {plugin_file}")
                    return None
                
                if len(plugin_classes) > 1:
                    logger.warning(f"Multiple TypePlugin subclasses found in {plugin_file}, using first one")
                
                plugin_class = plugin_classes[0]
                self._loaded_modules[plugin_file.stem] = module
                
                logger.info(f"Successfully loaded plugin class from {plugin_file}")
                return plugin_class
                
        except Exception as e:
            logger.error(f"Failed to load plugin from {plugin_file}: {e}")
            return None
    
    def load_plugins_from_directory(self, plugin_dir: Path) -> List[Type[TypePlugin]]:
        """Load all plugins from a directory
        
        Args:
            plugin_dir: Directory containing plugin files
            
        Returns:
            List of plugin classes
        """
        plugin_classes = []
        
        if not plugin_dir.exists() or not plugin_dir.is_dir():
            logger.warning(f"Plugin directory does not exist: {plugin_dir}")
            return plugin_classes
        
        for plugin_file in plugin_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue  # Skip private files
            
            plugin_class = self.load_plugin_from_file(plugin_file)
            if plugin_class:
                plugin_classes.append(plugin_class)
        
        logger.info(f"Loaded {len(plugin_classes)} plugins from {plugin_dir}")
        return plugin_classes
    
    def load_plugin_from_package(self, package_name: str, plugin_class_name: str) -> Optional[Type[TypePlugin]]:
        """Load a plugin from an installed package
        
        Args:
            package_name: Name of the package
            plugin_class_name: Name of the plugin class
            
        Returns:
            Plugin class if successful, None otherwise
        """
        try:
            module = importlib.import_module(package_name)
            plugin_class = getattr(module, plugin_class_name)
            
            if not issubclass(plugin_class, TypePlugin):
                logger.error(f"Class {plugin_class_name} is not a TypePlugin subclass")
                return None
            
            logger.info(f"Successfully loaded plugin {plugin_class_name} from package {package_name}")
            return plugin_class
            
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_class_name} from package {package_name}: {e}")
            return None


class TypePluginManager:
    """Extensible plugin system for custom types
    
    Manages the loading, configuration, and execution of type plugins.
    Provides a centralized system for extending type functionality.
    """
    
    def __init__(self):
        """Initialize plugin manager"""
        self.plugins: Dict[str, TypePlugin] = {}
        self.plugin_loader = PluginLoader()
        self.configurations: Dict[str, PluginConfiguration] = {}
        self._lock = threading.RLock()
        
        logger.info("TypePluginManager initialized")
    
    def register_plugin(self, plugin: TypePlugin) -> bool:
        """Register a plugin instance
        
        Args:
            plugin: Plugin instance to register
            
        Returns:
            True if registration succeeded
        """
        try:
            with self._lock:
                if plugin.plugin_id in self.plugins:
                    logger.warning(f"Plugin {plugin.plugin_id} already registered, replacing")
                
                # Validate plugin
                metadata = plugin.get_metadata()
                capabilities = plugin.get_capabilities()
                
                if not metadata.plugin_id or not metadata.name:
                    logger.error("Plugin metadata incomplete")
                    return False
                
                # Store plugin
                self.plugins[plugin.plugin_id] = plugin
                plugin._set_status(PluginStatus.LOADED)
                
                logger.info(f"Successfully registered plugin: {plugin.plugin_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to register plugin {plugin.plugin_id}: {e}")
            plugin._set_status(PluginStatus.ERROR, str(e))
            return False
    
    def unregister_plugin(self, plugin_id: str) -> bool:
        """Unregister a plugin
        
        Args:
            plugin_id: ID of plugin to unregister
            
        Returns:
            True if unregistration succeeded
        """
        with self._lock:
            if plugin_id not in self.plugins:
                logger.warning(f"Plugin {plugin_id} not found for unregistration")
                return False
            
            plugin = self.plugins[plugin_id]
            
            try:
                # Shutdown plugin
                if plugin.status == PluginStatus.ACTIVE:
                    plugin.shutdown()
                
                # Remove from registry
                del self.plugins[plugin_id]
                self.configurations.pop(plugin_id, None)
                
                logger.info(f"Successfully unregistered plugin: {plugin_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to unregister plugin {plugin_id}: {e}")
                return False
    
    def load_plugins_from_directory(self, directory: Path) -> List[str]:
        """Load plugins from a directory
        
        Args:
            directory: Directory containing plugin files
            
        Returns:
            List of successfully loaded plugin IDs
        """
        loaded_plugin_ids = []
        
        plugin_classes = self.plugin_loader.load_plugins_from_directory(directory)
        
        for plugin_class in plugin_classes:
            try:
                # Create plugin instance
                plugin_id = f"{plugin_class.__module__}.{plugin_class.__name__}"
                plugin_instance = plugin_class(plugin_id)
                
                if self.register_plugin(plugin_instance):
                    loaded_plugin_ids.append(plugin_id)
                
            except Exception as e:
                logger.error(f"Failed to instantiate plugin class {plugin_class}: {e}")
        
        logger.info(f"Loaded {len(loaded_plugin_ids)} plugins from {directory}")
        return loaded_plugin_ids
    
    def configure_plugin(self, plugin_id: str, configuration: PluginConfiguration) -> bool:
        """Configure a plugin
        
        Args:
            plugin_id: ID of plugin to configure
            configuration: Plugin configuration
            
        Returns:
            True if configuration succeeded
        """
        with self._lock:
            if plugin_id not in self.plugins:
                logger.error(f"Plugin {plugin_id} not found for configuration")
                return False
            
            plugin = self.plugins[plugin_id]
            
            try:
                # Validate configuration
                is_valid, errors = plugin.validate_configuration(configuration.settings)
                if not is_valid:
                    logger.error(f"Invalid configuration for plugin {plugin_id}: {errors}")
                    return False
                
                # Initialize plugin with configuration
                if plugin.initialize(configuration):
                    self.configurations[plugin_id] = configuration
                    plugin._configuration = configuration
                    plugin._set_status(PluginStatus.ACTIVE if configuration.enabled else PluginStatus.INACTIVE)
                    
                    logger.info(f"Successfully configured plugin: {plugin_id}")
                    return True
                else:
                    plugin._set_status(PluginStatus.ERROR, "Initialization failed")
                    return False
                
            except Exception as e:
                logger.error(f"Failed to configure plugin {plugin_id}: {e}")
                plugin._set_status(PluginStatus.ERROR, str(e))
                return False
    
    def get_plugin_capabilities(self, plugin_id: str) -> Optional[PluginCapabilities]:
        """Get capabilities of a plugin
        
        Args:
            plugin_id: ID of plugin
            
        Returns:
            Plugin capabilities if found
        """
        with self._lock:
            if plugin_id not in self.plugins:
                return None
            
            try:
                return self.plugins[plugin_id].get_capabilities()
            except Exception as e:
                logger.error(f"Failed to get capabilities for plugin {plugin_id}: {e}")
                return None
    
    def execute_plugin_operation(self, 
                                plugin_id: str, 
                                operation: str, 
                                **kwargs) -> Optional[Any]:
        """Execute an operation on a plugin
        
        Args:
            plugin_id: ID of plugin
            operation: Operation name
            **kwargs: Operation parameters
            
        Returns:
            Operation result if successful
        """
        with self._lock:
            if plugin_id not in self.plugins:
                logger.error(f"Plugin {plugin_id} not found for operation execution")
                return None
            
            plugin = self.plugins[plugin_id]
            
            if plugin.status != PluginStatus.ACTIVE:
                logger.error(f"Plugin {plugin_id} is not active (status: {plugin.status})")
                return None
            
            try:
                result = plugin.execute_operation(operation, **kwargs)
                logger.debug(f"Successfully executed operation {operation} on plugin {plugin_id}")
                return result
                
            except Exception as e:
                logger.error(f"Failed to execute operation {operation} on plugin {plugin_id}: {e}")
                return None
    
    def find_plugins_by_capability(self, capability: PluginCapabilityType) -> List[str]:
        """Find plugins that support a specific capability
        
        Args:
            capability: Capability to search for
            
        Returns:
            List of plugin IDs that support the capability
        """
        matching_plugins = []
        
        with self._lock:
            for plugin_id, plugin in self.plugins.items():
                if plugin.status != PluginStatus.ACTIVE:
                    continue
                
                try:
                    capabilities = plugin.get_capabilities()
                    if capabilities.supports_capability(capability):
                        matching_plugins.append(plugin_id)
                except Exception as e:
                    logger.error(f"Failed to check capabilities for plugin {plugin_id}: {e}")
        
        return matching_plugins
    
    def find_plugins_by_type(self, type_id: str) -> List[str]:
        """Find plugins that support a specific type
        
        Args:
            type_id: Type ID to search for
            
        Returns:
            List of plugin IDs that support the type
        """
        matching_plugins = []
        
        with self._lock:
            for plugin_id, plugin in self.plugins.items():
                if plugin.status != PluginStatus.ACTIVE:
                    continue
                
                try:
                    capabilities = plugin.get_capabilities()
                    if capabilities.supports_type(type_id):
                        matching_plugins.append(plugin_id)
                except Exception as e:
                    logger.error(f"Failed to check type support for plugin {plugin_id}: {e}")
        
        return matching_plugins
    
    def list_plugins(self, status_filter: Optional[PluginStatus] = None) -> List[Dict[str, Any]]:
        """List all registered plugins
        
        Args:
            status_filter: Optional status filter
            
        Returns:
            List of plugin information dictionaries
        """
        plugin_list = []
        
        with self._lock:
            for plugin_id, plugin in self.plugins.items():
                if status_filter and plugin.status != status_filter:
                    continue
                
                try:
                    metadata = plugin.get_metadata()
                    capabilities = plugin.get_capabilities()
                    
                    plugin_info = {
                        'plugin_id': plugin_id,
                        'name': metadata.name,
                        'description': metadata.description,
                        'version': metadata.version,
                        'author': metadata.author,
                        'status': plugin.status.value,
                        'capabilities': [cap.value for cap in capabilities.capabilities],
                        'supported_types': list(capabilities.supported_types),
                        'error_message': plugin.error_message
                    }
                    plugin_list.append(plugin_info)
                    
                except Exception as e:
                    logger.error(f"Failed to get info for plugin {plugin_id}: {e}")
                    plugin_list.append({
                        'plugin_id': plugin_id,
                        'status': plugin.status.value,
                        'error_message': f"Failed to get plugin info: {e}"
                    })
        
        return sorted(plugin_list, key=lambda p: p.get('name', p['plugin_id']))
    
    def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a plugin
        
        Args:
            plugin_id: ID of plugin to enable
            
        Returns:
            True if plugin was enabled successfully
        """
        with self._lock:
            if plugin_id not in self.plugins:
                return False
            
            plugin = self.plugins[plugin_id]
            configuration = self.configurations.get(plugin_id)
            
            if not configuration:
                # Create default configuration
                configuration = PluginConfiguration(plugin_id=plugin_id, enabled=True)
            else:
                configuration.enabled = True
            
            return self.configure_plugin(plugin_id, configuration)
    
    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin
        
        Args:
            plugin_id: ID of plugin to disable
            
        Returns:
            True if plugin was disabled successfully
        """
        with self._lock:
            if plugin_id not in self.plugins:
                return False
            
            plugin = self.plugins[plugin_id]
            
            try:
                plugin.shutdown()
                plugin._set_status(PluginStatus.DISABLED)
                
                if plugin_id in self.configurations:
                    self.configurations[plugin_id].enabled = False
                
                logger.info(f"Disabled plugin: {plugin_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to disable plugin {plugin_id}: {e}")
                return False
    
    def get_plugin_configuration(self, plugin_id: str) -> Optional[PluginConfiguration]:
        """Get configuration for a plugin
        
        Args:
            plugin_id: ID of plugin
            
        Returns:
            Plugin configuration if found
        """
        return self.configurations.get(plugin_id)
    
    def save_configurations(self, config_file: Path) -> bool:
        """Save all plugin configurations to file
        
        Args:
            config_file: File to save configurations to
            
        Returns:
            True if save succeeded
        """
        try:
            config_data = {}
            
            with self._lock:
                for plugin_id, config in self.configurations.items():
                    config_data[plugin_id] = {
                        'enabled': config.enabled,
                        'settings': config.settings,
                        'priority': config.priority,
                        'auto_load': config.auto_load,
                        'configuration_version': config.configuration_version
                    }
            
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"Saved plugin configurations to {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save plugin configurations: {e}")
            return False
    
    def load_configurations(self, config_file: Path) -> bool:
        """Load plugin configurations from file
        
        Args:
            config_file: File to load configurations from
            
        Returns:
            True if load succeeded
        """
        try:
            if not config_file.exists():
                logger.info(f"Configuration file {config_file} does not exist")
                return True
            
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            with self._lock:
                for plugin_id, config_dict in config_data.items():
                    config = PluginConfiguration(
                        plugin_id=plugin_id,
                        enabled=config_dict.get('enabled', True),
                        settings=config_dict.get('settings', {}),
                        priority=config_dict.get('priority', 100),
                        auto_load=config_dict.get('auto_load', True),
                        configuration_version=config_dict.get('configuration_version', '1.0.0')
                    )
                    
                    # Apply configuration if plugin is loaded
                    if plugin_id in self.plugins:
                        self.configure_plugin(plugin_id, config)
                    else:
                        # Store for when plugin is loaded
                        self.configurations[plugin_id] = config
            
            logger.info(f"Loaded plugin configurations from {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load plugin configurations: {e}")
            return False