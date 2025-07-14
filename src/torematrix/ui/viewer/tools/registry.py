"""
Enhanced tool registry system for selection tools.

This module provides advanced tool discovery, registration, lifecycle management,
and plugin-like capabilities for selection tools.
"""

import importlib
import inspect
import time
from typing import Dict, List, Optional, Set, Type, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal

from .base import SelectionTool, ToolState
from .state import ToolStateManager
from .cursor import CursorManager
from .events import EventDispatcher, AnyToolEvent


class ToolCategory(Enum):
    """Tool categories for organization."""
    BASIC = "basic"
    SELECTION = "selection"
    DRAWING = "drawing"
    MEASUREMENT = "measurement"
    ANNOTATION = "annotation"
    CUSTOM = "custom"


class ToolCapability(Enum):
    """Tool capabilities."""
    POINT_SELECTION = "point_selection"
    AREA_SELECTION = "area_selection"
    MULTI_SELECTION = "multi_selection"
    KEYBOARD_SHORTCUTS = "keyboard_shortcuts"
    CONTEXT_MENU = "context_menu"
    DRAG_AND_DROP = "drag_and_drop"
    UNDO_REDO = "undo_redo"
    PERSISTENCE = "persistence"
    ANIMATION = "animation"
    CUSTOM_CURSOR = "custom_cursor"


@dataclass
class ToolMetadata:
    """Metadata for registered tools."""
    name: str
    display_name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    category: ToolCategory = ToolCategory.CUSTOM
    capabilities: Set[ToolCapability] = field(default_factory=set)
    icon_path: str = ""
    keywords: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    registration_time: float = field(default_factory=time.time)
    enabled: bool = True
    
    def matches_search(self, query: str) -> bool:
        """Check if tool matches search query."""
        query_lower = query.lower()
        return (
            query_lower in self.name.lower() or
            query_lower in self.display_name.lower() or
            query_lower in self.description.lower() or
            any(query_lower in keyword.lower() for keyword in self.keywords)
        )


@dataclass
class ToolInstance:
    """Wrapper for tool instances with metadata and state."""
    tool: SelectionTool
    metadata: ToolMetadata
    state_manager: Optional[ToolStateManager] = None
    created_time: float = field(default_factory=time.time)
    last_used_time: Optional[float] = None
    usage_count: int = 0
    
    def mark_used(self) -> None:
        """Mark tool as used."""
        self.last_used_time = time.time()
        self.usage_count += 1


class ToolFactory:
    """Factory for creating tool instances."""
    
    def __init__(self, tool_class: Type[SelectionTool], metadata: ToolMetadata):
        self.tool_class = tool_class
        self.metadata = metadata
        self._creation_count = 0
    
    def create_instance(self, parent: Optional[QObject] = None, **kwargs) -> ToolInstance:
        """Create new tool instance."""
        tool = self.tool_class(parent, **kwargs)
        
        # Create state manager if tool supports it
        state_manager = None
        if hasattr(tool, 'state_manager') or ToolCapability.PERSISTENCE in self.metadata.capabilities:
            state_manager = ToolStateManager(self.metadata.name)
        
        instance = ToolInstance(
            tool=tool,
            metadata=self.metadata,
            state_manager=state_manager
        )
        
        self._creation_count += 1
        return instance
    
    def get_creation_count(self) -> int:
        """Get number of instances created."""
        return self._creation_count


class AdvancedToolRegistry(QObject):
    """
    Advanced tool registry with plugin support, lifecycle management,
    and comprehensive tool discovery capabilities.
    """
    
    # Signals
    tool_registered = pyqtSignal(str)  # tool name
    tool_unregistered = pyqtSignal(str)  # tool name
    tool_activated = pyqtSignal(str)  # tool name
    tool_deactivated = pyqtSignal(str)  # tool name
    active_tool_changed = pyqtSignal(str, str)  # old tool, new tool
    registry_changed = pyqtSignal()  # general registry change
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        # Tool storage
        self._factories: Dict[str, ToolFactory] = {}
        self._instances: Dict[str, ToolInstance] = {}
        self._active_tool_name: Optional[str] = None
        
        # Tool discovery
        self._search_paths: List[str] = []
        self._discovered_tools: Dict[str, Type[SelectionTool]] = {}
        
        # Lifecycle management
        self._initialization_callbacks: Dict[str, List[Callable[[SelectionTool], None]]] = {}
        self._cleanup_callbacks: Dict[str, List[Callable[[SelectionTool], None]]] = {}
        
        # Dependencies
        self._cursor_manager: Optional[CursorManager] = None
        self._event_dispatcher: Optional[EventDispatcher] = None
        
        # Configuration
        self._auto_cleanup = True
        self._max_instances_per_tool = 1
        self._allow_duplicates = False
        
        # Statistics
        self._stats = {
            'total_registrations': 0,
            'total_activations': 0,
            'total_instances_created': 0,
            'failed_registrations': 0
        }
    
    def set_cursor_manager(self, cursor_manager: CursorManager) -> None:
        """Set cursor manager for tools."""
        self._cursor_manager = cursor_manager
    
    def set_event_dispatcher(self, event_dispatcher: EventDispatcher) -> None:
        """Set event dispatcher for tools."""
        self._event_dispatcher = event_dispatcher
    
    def register_tool_class(self, tool_class: Type[SelectionTool], metadata: ToolMetadata) -> bool:
        """
        Register a tool class with metadata.
        
        Args:
            tool_class: Tool class to register
            metadata: Tool metadata
            
        Returns:
            True if registration successful
        """
        try:
            # Validate tool class
            if not issubclass(tool_class, SelectionTool):
                raise ValueError(f"Tool class must inherit from SelectionTool")
            
            # Check for duplicate names
            if metadata.name in self._factories and not self._allow_duplicates:
                raise ValueError(f"Tool '{metadata.name}' is already registered")
            
            # Validate dependencies
            if not self._validate_dependencies(metadata.dependencies):
                raise ValueError(f"Dependencies not satisfied for tool '{metadata.name}'")
            
            # Create factory
            factory = ToolFactory(tool_class, metadata)
            self._factories[metadata.name] = factory
            
            self._stats['total_registrations'] += 1
            self.tool_registered.emit(metadata.name)
            self.registry_changed.emit()
            
            return True
            
        except Exception as e:
            self._stats['failed_registrations'] += 1
            return False
    
    def register_tool_from_module(self, module_path: str, tool_name: str) -> bool:
        """Register tool from module path."""
        try:
            module = importlib.import_module(module_path)
            
            # Find tool class in module
            tool_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, SelectionTool) and 
                    obj != SelectionTool and
                    getattr(obj, '__name__', '') == tool_name):
                    tool_class = obj
                    break
            
            if not tool_class:
                return False
            
            # Try to get metadata from class
            metadata = self._extract_metadata_from_class(tool_class)
            if not metadata:
                return False
            
            return self.register_tool_class(tool_class, metadata)
            
        except Exception:
            return False
    
    def _extract_metadata_from_class(self, tool_class: Type[SelectionTool]) -> Optional[ToolMetadata]:
        """Extract metadata from tool class attributes/docstring."""
        try:
            name = getattr(tool_class, 'TOOL_NAME', tool_class.__name__)
            display_name = getattr(tool_class, 'TOOL_DISPLAY_NAME', name)
            description = getattr(tool_class, 'TOOL_DESCRIPTION', tool_class.__doc__ or "")
            version = getattr(tool_class, 'TOOL_VERSION', "1.0.0")
            author = getattr(tool_class, 'TOOL_AUTHOR', "")
            category_str = getattr(tool_class, 'TOOL_CATEGORY', 'custom')
            capabilities_list = getattr(tool_class, 'TOOL_CAPABILITIES', [])
            
            # Convert strings to enums
            try:
                category = ToolCategory(category_str)
            except ValueError:
                category = ToolCategory.CUSTOM
            
            capabilities = set()
            for cap_str in capabilities_list:
                try:
                    capabilities.add(ToolCapability(cap_str))
                except ValueError:
                    pass
            
            return ToolMetadata(
                name=name,
                display_name=display_name,
                description=description,
                version=version,
                author=author,
                category=category,
                capabilities=capabilities
            )
            
        except Exception:
            return None
    
    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister tool."""
        if tool_name not in self._factories:
            return False
        
        # Deactivate if active
        if self._active_tool_name == tool_name:
            self.deactivate_tool()
        
        # Clean up instance
        if tool_name in self._instances:
            instance = self._instances[tool_name]
            self._cleanup_tool_instance(instance)
            del self._instances[tool_name]
        
        # Remove factory
        del self._factories[tool_name]
        
        self.tool_unregistered.emit(tool_name)
        self.registry_changed.emit()
        return True
    
    def get_tool_instance(self, tool_name: str, create_if_needed: bool = True) -> Optional[ToolInstance]:
        """Get or create tool instance."""
        # Return existing instance
        if tool_name in self._instances:
            return self._instances[tool_name]
        
        # Create new instance if requested and factory exists
        if create_if_needed and tool_name in self._factories:
            factory = self._factories[tool_name]
            
            # Check instance limit
            if self._max_instances_per_tool > 0:
                existing_count = sum(1 for instance in self._instances.values() 
                                   if instance.metadata.name == tool_name)
                if existing_count >= self._max_instances_per_tool:
                    return None
            
            # Create instance
            instance = factory.create_instance(self)
            self._instances[tool_name] = instance
            
            # Initialize instance
            self._initialize_tool_instance(instance)
            
            self._stats['total_instances_created'] += 1
            return instance
        
        return None
    
    def _initialize_tool_instance(self, instance: ToolInstance) -> None:
        """Initialize tool instance with dependencies."""
        tool = instance.tool
        
        # Set cursor manager
        if self._cursor_manager and hasattr(tool, 'set_cursor_manager'):
            tool.set_cursor_manager(self._cursor_manager)
        
        # Set event dispatcher
        if self._event_dispatcher and hasattr(tool, 'set_event_dispatcher'):
            tool.set_event_dispatcher(self._event_dispatcher)
        
        # Connect state manager
        if instance.state_manager and hasattr(tool, 'set_state_manager'):
            tool.set_state_manager(instance.state_manager)
        
        # Run initialization callbacks
        callbacks = self._initialization_callbacks.get(instance.metadata.name, [])
        for callback in callbacks:
            try:
                callback(tool)
            except Exception:
                pass
    
    def _cleanup_tool_instance(self, instance: ToolInstance) -> None:
        """Clean up tool instance."""
        tool = instance.tool
        
        # Run cleanup callbacks
        callbacks = self._cleanup_callbacks.get(instance.metadata.name, [])
        for callback in callbacks:
            try:
                callback(tool)
            except Exception:
                pass
        
        # Deactivate tool
        if hasattr(tool, 'deactivate'):
            tool.deactivate()
        
        # Clean up state manager
        if instance.state_manager:
            instance.state_manager.deleteLater()
    
    def activate_tool(self, tool_name: str) -> bool:
        """Activate tool by name."""
        if tool_name not in self._factories:
            return False
        
        # Deactivate current tool
        if self._active_tool_name:
            self.deactivate_tool()
        
        # Get or create instance
        instance = self.get_tool_instance(tool_name)
        if not instance:
            return False
        
        # Activate tool
        try:
            instance.tool.activate()
            instance.mark_used()
            
            old_tool = self._active_tool_name
            self._active_tool_name = tool_name
            
            self._stats['total_activations'] += 1
            self.tool_activated.emit(tool_name)
            if old_tool != tool_name:
                self.active_tool_changed.emit(old_tool or "", tool_name)
            
            return True
            
        except Exception:
            return False
    
    def deactivate_tool(self) -> bool:
        """Deactivate current tool."""
        if not self._active_tool_name:
            return False
        
        tool_name = self._active_tool_name
        
        # Get instance
        instance = self._instances.get(tool_name)
        if instance:
            try:
                instance.tool.deactivate()
            except Exception:
                pass
        
        self._active_tool_name = None
        self.tool_deactivated.emit(tool_name)
        
        return True
    
    def get_active_tool(self) -> Optional[ToolInstance]:
        """Get active tool instance."""
        if self._active_tool_name:
            return self._instances.get(self._active_tool_name)
        return None
    
    def get_active_tool_name(self) -> Optional[str]:
        """Get active tool name."""
        return self._active_tool_name
    
    def get_registered_tools(self) -> List[str]:
        """Get list of registered tool names."""
        return list(self._factories.keys())
    
    def get_tool_metadata(self, tool_name: str) -> Optional[ToolMetadata]:
        """Get tool metadata."""
        factory = self._factories.get(tool_name)
        return factory.metadata if factory else None
    
    def search_tools(self, query: str, category: Optional[ToolCategory] = None,
                    capabilities: Optional[Set[ToolCapability]] = None) -> List[ToolMetadata]:
        """Search tools by query, category, and capabilities."""
        results = []
        
        for factory in self._factories.values():
            metadata = factory.metadata
            
            # Check if enabled
            if not metadata.enabled:
                continue
            
            # Check category filter
            if category and metadata.category != category:
                continue
            
            # Check capabilities filter
            if capabilities and not capabilities.issubset(metadata.capabilities):
                continue
            
            # Check search query
            if query and not metadata.matches_search(query):
                continue
            
            results.append(metadata)
        
        # Sort by relevance (simple scoring)
        if query:
            def score_relevance(metadata: ToolMetadata) -> int:
                score = 0
                query_lower = query.lower()
                
                if query_lower in metadata.name.lower():
                    score += 10
                if query_lower in metadata.display_name.lower():
                    score += 8
                if query_lower in metadata.description.lower():
                    score += 5
                
                for keyword in metadata.keywords:
                    if query_lower in keyword.lower():
                        score += 3
                
                return score
            
            results.sort(key=score_relevance, reverse=True)
        
        return results
    
    def get_tools_by_category(self, category: ToolCategory) -> List[ToolMetadata]:
        """Get tools by category."""
        return [factory.metadata for factory in self._factories.values() 
                if factory.metadata.category == category and factory.metadata.enabled]
    
    def get_tools_by_capability(self, capability: ToolCapability) -> List[ToolMetadata]:
        """Get tools by capability."""
        return [factory.metadata for factory in self._factories.values() 
                if capability in factory.metadata.capabilities and factory.metadata.enabled]
    
    def add_initialization_callback(self, tool_name: str, callback: Callable[[SelectionTool], None]) -> None:
        """Add initialization callback for tool."""
        if tool_name not in self._initialization_callbacks:
            self._initialization_callbacks[tool_name] = []
        self._initialization_callbacks[tool_name].append(callback)
    
    def add_cleanup_callback(self, tool_name: str, callback: Callable[[SelectionTool], None]) -> None:
        """Add cleanup callback for tool."""
        if tool_name not in self._cleanup_callbacks:
            self._cleanup_callbacks[tool_name] = []
        self._cleanup_callbacks[tool_name].append(callback)
    
    def _validate_dependencies(self, dependencies: List[str]) -> bool:
        """Validate tool dependencies."""
        for dependency in dependencies:
            if dependency not in self._factories:
                return False
        return True
    
    def enable_tool(self, tool_name: str) -> bool:
        """Enable tool."""
        factory = self._factories.get(tool_name)
        if factory:
            factory.metadata.enabled = True
            self.registry_changed.emit()
            return True
        return False
    
    def disable_tool(self, tool_name: str) -> bool:
        """Disable tool."""
        factory = self._factories.get(tool_name)
        if factory:
            # Deactivate if active
            if self._active_tool_name == tool_name:
                self.deactivate_tool()
            
            factory.metadata.enabled = False
            self.registry_changed.emit()
            return True
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        stats = self._stats.copy()
        stats.update({
            'registered_tools': len(self._factories),
            'active_instances': len(self._instances),
            'active_tool': self._active_tool_name,
            'enabled_tools': sum(1 for f in self._factories.values() if f.metadata.enabled),
            'disabled_tools': sum(1 for f in self._factories.values() if not f.metadata.enabled)
        })
        return stats
    
    def cleanup_unused_instances(self) -> int:
        """Clean up unused tool instances."""
        if not self._auto_cleanup:
            return 0
        
        cleaned = 0
        current_time = time.time()
        
        # Find instances to clean up
        to_remove = []
        for name, instance in self._instances.items():
            # Skip active tool
            if name == self._active_tool_name:
                continue
            
            # Check if unused for a while
            if (instance.last_used_time and 
                current_time - instance.last_used_time > 300):  # 5 minutes
                to_remove.append(name)
        
        # Clean up instances
        for name in to_remove:
            instance = self._instances[name]
            self._cleanup_tool_instance(instance)
            del self._instances[name]
            cleaned += 1
        
        return cleaned
    
    def clear_all_instances(self) -> None:
        """Clear all tool instances."""
        # Deactivate active tool
        self.deactivate_tool()
        
        # Clean up all instances
        for instance in self._instances.values():
            self._cleanup_tool_instance(instance)
        
        self._instances.clear()


# Global registry instance
_global_tool_registry: Optional[AdvancedToolRegistry] = None


def get_global_tool_registry() -> AdvancedToolRegistry:
    """Get global tool registry instance."""
    global _global_tool_registry
    if _global_tool_registry is None:
        _global_tool_registry = AdvancedToolRegistry()
    return _global_tool_registry