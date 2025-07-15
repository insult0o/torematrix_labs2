"""
Plugin Manager for Hierarchical Element List

Provides plugin system for extending element list functionality
with custom element types, actions, and behaviors.
"""

import logging
from typing import Dict, List, Optional, Any, Callable, Type
from dataclasses import dataclass
from abc import ABC, abstractmethod
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """Metadata for element list plugins"""
    name: str
    version: str
    description: str
    author: str
    dependencies: List[str] = None
    priority: int = 50
    enabled: bool = True
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class ElementListPlugin(ABC):
    """Base class for element list plugins"""
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata"""
        pass
    
    @abstractmethod
    def initialize(self, element_list_widget, plugin_manager) -> bool:
        """Initialize the plugin"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup plugin resources"""
        pass
    
    def get_custom_element_types(self) -> Dict[str, Type]:
        """Get custom element types provided by this plugin"""
        return {}
    
    def get_custom_actions(self) -> Dict[str, Callable]:
        """Get custom actions provided by this plugin"""
        return {}
    
    def get_custom_renderers(self) -> Dict[str, Type]:
        """Get custom element renderers provided by this plugin"""
        return {}


class ElementListPluginManager(QObject):
    """
    Plugin manager for hierarchical element list
    
    Manages plugin lifecycle, dependencies, and extension points
    for customizing element list behavior.
    """
    
    # Signals
    plugin_loaded = pyqtSignal(str)  # plugin_name
    plugin_unloaded = pyqtSignal(str)  # plugin_name
    plugin_error = pyqtSignal(str, str)  # plugin_name, error_message
    
    def __init__(self, element_list_widget, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self.element_list = element_list_widget
        
        # Plugin registry
        self._plugins: Dict[str, ElementListPlugin] = {}
        self._plugin_metadata: Dict[str, PluginMetadata] = {}
        self._load_order: List[str] = []
        
        # Extension points
        self._custom_element_types: Dict[str, Type] = {}
        self._custom_actions: Dict[str, Callable] = {}
        self._custom_renderers: Dict[str, Type] = {}
        
        logger.info("ElementListPluginManager initialized")
    
    def load_plugin(self, plugin: ElementListPlugin) -> bool:
        """Load a plugin"""
        try:
            metadata = plugin.get_metadata()
            plugin_name = metadata.name
            
            if plugin_name in self._plugins:
                logger.warning(f"Plugin '{plugin_name}' is already loaded")
                return False
            
            # Check dependencies
            if not self._check_dependencies(metadata.dependencies):
                error_msg = f"Plugin dependencies not met: {metadata.dependencies}"
                self.plugin_error.emit(plugin_name, error_msg)
                return False
            
            # Initialize plugin
            if not plugin.initialize(self.element_list, self):
                error_msg = "Plugin initialization failed"
                self.plugin_error.emit(plugin_name, error_msg)
                return False
            
            # Register plugin
            self._plugins[plugin_name] = plugin
            self._plugin_metadata[plugin_name] = metadata
            self._load_order.append(plugin_name)
            
            # Register extensions
            self._register_plugin_extensions(plugin_name, plugin)
            
            logger.info(f"Loaded plugin: {plugin_name} v{metadata.version}")
            self.plugin_loaded.emit(plugin_name)
            return True
            
        except Exception as e:
            error_msg = f"Failed to load plugin: {str(e)}"
            if hasattr(plugin, 'get_metadata'):
                try:
                    plugin_name = plugin.get_metadata().name
                    self.plugin_error.emit(plugin_name, error_msg)
                except:
                    pass
            logger.error(error_msg)
            return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin"""
        if plugin_name not in self._plugins:
            return False
        
        try:
            plugin = self._plugins[plugin_name]
            
            # Cleanup plugin
            plugin.cleanup()
            
            # Unregister extensions
            self._unregister_plugin_extensions(plugin_name)
            
            # Remove from registry
            del self._plugins[plugin_name]
            del self._plugin_metadata[plugin_name]
            self._load_order.remove(plugin_name)
            
            logger.info(f"Unloaded plugin: {plugin_name}")
            self.plugin_unloaded.emit(plugin_name)
            return True
            
        except Exception as e:
            error_msg = f"Failed to unload plugin '{plugin_name}': {str(e)}"
            self.plugin_error.emit(plugin_name, error_msg)
            logger.error(error_msg)
            return False
    
    def get_loaded_plugins(self) -> List[str]:
        """Get list of loaded plugin names"""
        return list(self._plugins.keys())
    
    def get_plugin_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """Get metadata for a specific plugin"""
        return self._plugin_metadata.get(plugin_name)
    
    def is_plugin_loaded(self, plugin_name: str) -> bool:
        """Check if a plugin is loaded"""
        return plugin_name in self._plugins
    
    def get_custom_element_types(self) -> Dict[str, Type]:
        """Get all custom element types from plugins"""
        return self._custom_element_types.copy()
    
    def get_custom_actions(self) -> Dict[str, Callable]:
        """Get all custom actions from plugins"""
        return self._custom_actions.copy()
    
    def get_custom_renderers(self) -> Dict[str, Type]:
        """Get all custom renderers from plugins"""
        return self._custom_renderers.copy()
    
    def _check_dependencies(self, dependencies: List[str]) -> bool:
        """Check if plugin dependencies are met"""
        for dependency in dependencies:
            if not self.is_plugin_loaded(dependency):
                return False
        return True
    
    def _register_plugin_extensions(self, plugin_name: str, plugin: ElementListPlugin) -> None:
        """Register extensions provided by a plugin"""
        # Register custom element types
        element_types = plugin.get_custom_element_types()
        for type_name, type_class in element_types.items():
            self._custom_element_types[f"{plugin_name}.{type_name}"] = type_class
        
        # Register custom actions
        actions = plugin.get_custom_actions()
        for action_name, action_func in actions.items():
            self._custom_actions[f"{plugin_name}.{action_name}"] = action_func
        
        # Register custom renderers
        renderers = plugin.get_custom_renderers()
        for renderer_name, renderer_class in renderers.items():
            self._custom_renderers[f"{plugin_name}.{renderer_name}"] = renderer_class
    
    def _unregister_plugin_extensions(self, plugin_name: str) -> None:
        """Unregister extensions provided by a plugin"""
        # Remove custom element types
        to_remove = [key for key in self._custom_element_types.keys() 
                    if key.startswith(f"{plugin_name}.")]
        for key in to_remove:
            del self._custom_element_types[key]
        
        # Remove custom actions
        to_remove = [key for key in self._custom_actions.keys() 
                    if key.startswith(f"{plugin_name}.")]
        for key in to_remove:
            del self._custom_actions[key]
        
        # Remove custom renderers
        to_remove = [key for key in self._custom_renderers.keys() 
                    if key.startswith(f"{plugin_name}.")]
        for key in to_remove:
            del self._custom_renderers[key]