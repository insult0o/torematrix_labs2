"""
Advanced tool manager for selection tools with state management and optimization.
Coordinates multiple selection tools and provides unified interface.
"""

import time
from typing import Dict, List, Optional, Set, Any, Callable, Type
from dataclasses import dataclass, field
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QPoint, QRect
from PyQt6.QtGui import QPainter, QCursor

from ..coordinates import Point, Rectangle
from ..layers import LayerElement
from .base import SelectionTool, SelectionResult, ToolState
from .hit_testing import SpatialIndex, HitTestOptimizer
from .snapping import MagneticSnapping
from .persistence import SelectionPersistence
from .history import SelectionHistory


class ToolPriority(Enum):
    """Tool priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ToolRegistration:
    """Tool registration information."""
    tool: SelectionTool
    priority: ToolPriority = ToolPriority.NORMAL
    enabled: bool = True
    visible: bool = True
    shortcuts: List[str] = field(default_factory=list)
    context_filters: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolContext:
    """Context information for tool activation."""
    mouse_position: Optional[Point] = None
    viewport_bounds: Optional[Rectangle] = None
    zoom_level: float = 1.0
    selected_elements: List[LayerElement] = field(default_factory=list)
    modifier_keys: Set[str] = field(default_factory=set)
    document_type: str = ""
    performance_mode: bool = False


@dataclass
class ToolTransition:
    """Information about tool transitions."""
    from_tool: Optional[str] = None
    to_tool: Optional[str] = None
    reason: str = ""
    timestamp: float = field(default_factory=time.time)
    context: Optional[ToolContext] = None
    auto_transition: bool = False


class SelectionToolManager(QObject):
    """
    Advanced tool manager for selection tools.
    
    Features:
    - Tool registration and lifecycle management
    - Intelligent tool switching based on context
    - Performance optimization and monitoring
    - Tool state persistence and restoration
    - Conflict resolution between tools
    - Keyboard shortcuts and gesture management
    - Tool-specific optimization settings
    - Analytics and usage tracking
    """
    
    # Signals
    tool_registered = pyqtSignal(str, object)  # name, tool
    tool_unregistered = pyqtSignal(str)        # name
    tool_activated = pyqtSignal(str, object)   # name, tool
    tool_deactivated = pyqtSignal(str, object) # name, tool
    tool_switched = pyqtSignal(object)         # ToolTransition
    selection_changed = pyqtSignal(object)     # SelectionResult
    performance_warning = pyqtSignal(str, dict) # tool_name, metrics
    error_occurred = pyqtSignal(str, str)     # tool_name, error_message
    
    def __init__(self, spatial_index: Optional[SpatialIndex] = None, parent=None):
        super().__init__(parent)
        
        # Tool registry
        self._tools: Dict[str, ToolRegistration] = {}
        self._tool_types: Dict[Type, str] = {}  # Class to name mapping
        
        # Current state
        self._active_tool: Optional[str] = None
        self._previous_tool: Optional[str] = None
        self._tool_context = ToolContext()
        
        # Subsystems
        self.spatial_index = spatial_index or SpatialIndex()
        self.hit_test_optimizer = HitTestOptimizer(self.spatial_index)
        self.magnetic_snapping = MagneticSnapping(self.spatial_index)
        self.persistence = SelectionPersistence()
        self.history = SelectionHistory()
        
        # Performance monitoring
        self._performance_monitor = QTimer()
        self._performance_monitor.timeout.connect(self._monitor_performance)
        self._performance_monitor.start(5000)  # 5 seconds
        
        # Configuration
        self._config = {
            'auto_tool_switching': True,
            'smart_tool_selection': True,
            'performance_monitoring': True,
            'conflict_resolution': True,
            'tool_shortcuts': True,
            'gesture_recognition': True,
            'persistence_enabled': True,
            'history_enabled': True,
            'snapping_enabled': True,
            'hit_test_optimization': True,
            'tool_priority_ordering': True,
            'auto_deactivate_timeout': 300000,  # 5 minutes in ms
            'performance_warning_threshold': 100,  # ms
            'max_tools': 20
        }
        
        # Analytics
        self._analytics = {
            'tool_usage': {},
            'tool_switches': {},
            'performance_data': {},
            'error_counts': {},
            'selection_statistics': {
                'total_selections': 0,
                'average_selection_time': 0.0,
                'selection_accuracy': 0.0
            }
        }
        
        # Keyboard shortcuts
        self._shortcuts: Dict[str, str] = {}  # shortcut -> tool_name
        
        # Auto-deactivation timer
        self._auto_deactivate_timer = QTimer()
        self._auto_deactivate_timer.setSingleShot(True)
        self._auto_deactivate_timer.timeout.connect(self._auto_deactivate_active_tool)
        
        # Tool state cache
        self._tool_state_cache: Dict[str, Dict[str, Any]] = {}
    
    def register_tool(self, name: str, tool: SelectionTool,
                     priority: ToolPriority = ToolPriority.NORMAL,
                     shortcuts: Optional[List[str]] = None,
                     context_filters: Optional[List[str]] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Register a selection tool.
        
        Args:
            name: Unique tool name
            tool: Tool instance
            priority: Tool priority level
            shortcuts: Keyboard shortcuts
            context_filters: Context filters for auto-activation
            metadata: Additional tool metadata
            
        Returns:
            True if registered successfully
        """
        if name in self._tools:
            return False  # Tool already registered
        
        if len(self._tools) >= self._config['max_tools']:
            return False  # Too many tools
        
        # Create registration
        registration = ToolRegistration(
            tool=tool,
            priority=priority,
            shortcuts=shortcuts or [],
            context_filters=context_filters or [],
            metadata=metadata or {}
        )
        
        self._tools[name] = registration
        self._tool_types[type(tool)] = name
        
        # Connect tool signals
        self._connect_tool_signals(name, tool)
        
        # Register shortcuts
        for shortcut in registration.shortcuts:
            self._shortcuts[shortcut] = name
        
        # Initialize analytics
        self._analytics['tool_usage'][name] = {
            'activation_count': 0,
            'total_active_time': 0.0,
            'selection_count': 0,
            'error_count': 0,
            'last_used': 0.0
        }
        
        # Cache tool configuration
        self._save_tool_state(name)
        
        self.tool_registered.emit(name, tool)
        return True
    
    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool."""
        if name not in self._tools:
            return False
        
        registration = self._tools[name]
        
        # Deactivate if currently active
        if self._active_tool == name:
            self.deactivate_tool()
        
        # Disconnect signals
        self._disconnect_tool_signals(name, registration.tool)
        
        # Remove shortcuts
        shortcuts_to_remove = [k for k, v in self._shortcuts.items() if v == name]
        for shortcut in shortcuts_to_remove:
            del self._shortcuts[shortcut]
        
        # Remove from type mapping
        if type(registration.tool) in self._tool_types:
            del self._tool_types[type(registration.tool)]
        
        # Remove from registry
        del self._tools[name]
        
        # Clean up state cache
        if name in self._tool_state_cache:
            del self._tool_state_cache[name]
        
        self.tool_unregistered.emit(name)
        return True
    
    def activate_tool(self, name: str, context: Optional[ToolContext] = None) -> bool:
        """
        Activate a tool.
        
        Args:
            name: Tool name to activate
            context: Tool context information
            
        Returns:
            True if activated successfully
        """
        if name not in self._tools:
            return False
        
        registration = self._tools[name]
        
        if not registration.enabled:
            return False
        
        # Deactivate current tool
        if self._active_tool:
            self.deactivate_tool()
        
        # Update context
        if context:
            self._tool_context = context
        
        # Check context filters
        if not self._check_context_filters(name):
            return False
        
        try:
            # Restore tool state
            self._restore_tool_state(name)
            
            # Activate tool
            registration.tool.activate()
            
            # Update state
            self._previous_tool = self._active_tool
            self._active_tool = name
            
            # Record transition
            transition = ToolTransition(
                from_tool=self._previous_tool,
                to_tool=name,
                reason="manual_activation",
                context=self._tool_context,
                auto_transition=False
            )
            
            # Update analytics
            self._update_tool_usage(name, 'activation')
            
            # Start auto-deactivation timer
            if self._config['auto_deactivate_timeout'] > 0:
                self._auto_deactivate_timer.start(self._config['auto_deactivate_timeout'])
            
            # Record history
            if self._config['history_enabled']:
                self.history.record_action(
                    action_type=HistoryActionType.TOOL_CHANGE,
                    description=f"Activated {name} tool",
                    tool_type=name
                )
            
            self.tool_activated.emit(name, registration.tool)
            self.tool_switched.emit(transition)
            
            return True
            
        except Exception as e:
            self._record_error(name, str(e))
            return False
    
    def deactivate_tool(self, name: Optional[str] = None) -> bool:
        """
        Deactivate a tool.
        
        Args:
            name: Tool name to deactivate (None for current active tool)
            
        Returns:
            True if deactivated successfully
        """
        if name is None:
            name = self._active_tool
        
        if not name or name not in self._tools:
            return False
        
        registration = self._tools[name]
        
        try:
            # Save tool state
            self._save_tool_state(name)
            
            # Deactivate tool
            registration.tool.deactivate()
            
            # Update analytics
            self._update_tool_usage(name, 'deactivation')
            
            # Stop auto-deactivation timer
            self._auto_deactivate_timer.stop()
            
            self.tool_deactivated.emit(name, registration.tool)
            
            if self._active_tool == name:
                self._active_tool = None
            
            return True
            
        except Exception as e:
            self._record_error(name, str(e))
            return False
    
    def get_active_tool(self) -> Optional[SelectionTool]:
        """Get the currently active tool."""
        if self._active_tool:
            registration = self._tools.get(self._active_tool)
            return registration.tool if registration else None
        return None
    
    def get_active_tool_name(self) -> Optional[str]:
        """Get the name of the currently active tool."""
        return self._active_tool
    
    def get_tool(self, name: str) -> Optional[SelectionTool]:
        """Get a tool by name."""
        registration = self._tools.get(name)
        return registration.tool if registration else None
    
    def get_tool_by_type(self, tool_type: Type) -> Optional[SelectionTool]:
        """Get a tool by its type."""
        name = self._tool_types.get(tool_type)
        return self.get_tool(name) if name else None
    
    def list_tools(self, enabled_only: bool = False,
                  visible_only: bool = False) -> List[str]:
        """List tool names with optional filtering."""
        tools = []
        for name, registration in self._tools.items():
            if enabled_only and not registration.enabled:
                continue
            if visible_only and not registration.visible:
                continue
            tools.append(name)
        
        # Sort by priority if enabled
        if self._config['tool_priority_ordering']:
            tools.sort(key=lambda n: self._tools[n].priority.value, reverse=True)
        
        return tools
    
    def set_tool_enabled(self, name: str, enabled: bool) -> bool:
        """Enable or disable a tool."""
        if name not in self._tools:
            return False
        
        registration = self._tools[name]
        registration.enabled = enabled
        
        # Deactivate if currently active and being disabled
        if not enabled and self._active_tool == name:
            self.deactivate_tool()
        
        return True
    
    def set_tool_visible(self, name: str, visible: bool) -> bool:
        """Set tool visibility."""
        if name not in self._tools:
            return False
        
        self._tools[name].visible = visible
        return True
    
    def handle_shortcut(self, shortcut: str) -> bool:
        """Handle keyboard shortcut."""
        if not self._config['tool_shortcuts']:
            return False
        
        tool_name = self._shortcuts.get(shortcut)
        if tool_name:
            return self.activate_tool(tool_name)
        
        return False
    
    def suggest_tool(self, context: ToolContext) -> Optional[str]:
        """Suggest best tool for given context."""
        if not self._config['smart_tool_selection']:
            return None
        
        candidates = []
        
        for name, registration in self._tools.items():
            if not registration.enabled:
                continue
            
            # Calculate suitability score
            score = self._calculate_tool_suitability(name, context)
            if score > 0:
                candidates.append((name, score))
        
        if candidates:
            # Sort by score and return best
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        
        return None
    
    def auto_switch_tool(self, context: ToolContext) -> bool:
        """Automatically switch to best tool for context."""
        if not self._config['auto_tool_switching']:
            return False
        
        suggested_tool = self.suggest_tool(context)
        if suggested_tool and suggested_tool != self._active_tool:
            return self.activate_tool(suggested_tool, context)
        
        return False
    
    def update_context(self, **kwargs) -> None:
        """Update tool context."""
        for key, value in kwargs.items():
            if hasattr(self._tool_context, key):
                setattr(self._tool_context, key, value)
    
    def handle_mouse_press(self, point: QPoint, modifiers) -> bool:
        """Forward mouse press to active tool."""
        if self._active_tool:
            tool = self.get_active_tool()
            if tool:
                return tool.handle_mouse_press(point, modifiers)
        return False
    
    def handle_mouse_move(self, point: QPoint, modifiers) -> bool:
        """Forward mouse move to active tool."""
        if self._active_tool:
            tool = self.get_active_tool()
            if tool:
                return tool.handle_mouse_move(point, modifiers)
        return False
    
    def handle_mouse_release(self, point: QPoint, modifiers) -> bool:
        """Forward mouse release to active tool."""
        if self._active_tool:
            tool = self.get_active_tool()
            if tool:
                return tool.handle_mouse_release(point, modifiers)
        return False
    
    def render_overlays(self, painter: QPainter, viewport_rect: QRect) -> None:
        """Render overlays for all visible tools."""
        for name, registration in self._tools.items():
            if registration.visible and registration.tool.visible:
                try:
                    registration.tool.render_overlay(painter, viewport_rect)
                except Exception as e:
                    self._record_error(name, f"Render error: {e}")
        
        # Render snapping indicators if enabled
        if self._config['snapping_enabled']:
            self.magnetic_snapping.render_snap_indicators(painter, viewport_rect)
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get analytics data."""
        return {
            'tool_usage': self._analytics['tool_usage'].copy(),
            'tool_switches': self._analytics['tool_switches'].copy(),
            'performance_data': self._analytics['performance_data'].copy(),
            'error_counts': self._analytics['error_counts'].copy(),
            'selection_statistics': self._analytics['selection_statistics'].copy(),
            'current_session': {
                'active_tool': self._active_tool,
                'tools_registered': len(self._tools),
                'shortcuts_registered': len(self._shortcuts)
            }
        }
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export tool manager configuration."""
        return {
            'tools': {
                name: {
                    'enabled': reg.enabled,
                    'visible': reg.visible,
                    'priority': reg.priority.value,
                    'shortcuts': reg.shortcuts,
                    'context_filters': reg.context_filters,
                    'metadata': reg.metadata
                }
                for name, reg in self._tools.items()
            },
            'config': self._config.copy(),
            'shortcuts': self._shortcuts.copy(),
            'tool_states': self._tool_state_cache.copy()
        }
    
    def import_configuration(self, config: Dict[str, Any]) -> bool:
        """Import tool manager configuration."""
        try:
            # Update config
            if 'config' in config:
                self._config.update(config['config'])
            
            # Update tool settings
            if 'tools' in config:
                for name, settings in config['tools'].items():
                    if name in self._tools:
                        reg = self._tools[name]
                        reg.enabled = settings.get('enabled', True)
                        reg.visible = settings.get('visible', True)
                        if 'priority' in settings:
                            reg.priority = ToolPriority(settings['priority'])
            
            # Update shortcuts
            if 'shortcuts' in config:
                self._shortcuts.update(config['shortcuts'])
            
            # Restore tool states
            if 'tool_states' in config:
                self._tool_state_cache.update(config['tool_states'])
            
            return True
            
        except Exception as e:
            print(f"Error importing configuration: {e}")
            return False
    
    # Private methods
    
    def _connect_tool_signals(self, name: str, tool: SelectionTool) -> None:
        """Connect tool signals to manager."""
        tool.selection_changed.connect(
            lambda result: self._on_tool_selection_changed(name, result)
        )
        tool.error_occurred.connect(
            lambda error: self._record_error(name, error)
        )
    
    def _disconnect_tool_signals(self, name: str, tool: SelectionTool) -> None:
        """Disconnect tool signals."""
        tool.selection_changed.disconnect()
        tool.error_occurred.disconnect()
    
    def _on_tool_selection_changed(self, tool_name: str, result: SelectionResult) -> None:
        """Handle tool selection change."""
        # Update analytics
        self._update_tool_usage(tool_name, 'selection')
        
        # Record in history
        if self._config['history_enabled']:
            self.history.record_action(
                action_type=HistoryActionType.SELECT,
                description=f"Selection made with {tool_name}",
                after_state=result,
                tool_type=tool_name
            )
        
        # Save to persistence
        if self._config['persistence_enabled']:
            selection_id = f"{tool_name}_{int(time.time())}"
            self.persistence.save_selection(selection_id, result)
        
        self.selection_changed.emit(result)
    
    def _check_context_filters(self, tool_name: str) -> bool:
        """Check if tool context filters are satisfied."""
        registration = self._tools.get(tool_name)
        if not registration or not registration.context_filters:
            return True
        
        # Implement context filter logic here
        # For now, always return True
        return True
    
    def _calculate_tool_suitability(self, tool_name: str, context: ToolContext) -> float:
        """Calculate tool suitability score for context."""
        registration = self._tools.get(tool_name)
        if not registration:
            return 0.0
        
        score = 0.0
        
        # Priority base score
        score += registration.priority.value * 10
        
        # Usage history bonus
        usage = self._analytics['tool_usage'].get(tool_name, {})
        recent_usage = time.time() - usage.get('last_used', 0)
        if recent_usage < 300:  # 5 minutes
            score += 20
        elif recent_usage < 3600:  # 1 hour
            score += 10
        
        # Performance penalty
        performance = self._analytics['performance_data'].get(tool_name, {})
        avg_time = performance.get('average_operation_time', 0)
        if avg_time > self._config['performance_warning_threshold']:
            score -= 15
        
        # Error penalty
        error_count = self._analytics['error_counts'].get(tool_name, 0)
        score -= error_count * 5
        
        return max(0.0, score)
    
    def _save_tool_state(self, tool_name: str) -> None:
        """Save tool state to cache."""
        tool = self.get_tool(tool_name)
        if tool:
            try:
                # Get tool configuration
                state = {}
                for key in ['double_click_threshold', 'drag_threshold', 'click_tolerance']:
                    value = tool.get_config(key)
                    if value is not None:
                        state[key] = value
                
                self._tool_state_cache[tool_name] = state
                
            except Exception as e:
                print(f"Error saving tool state for {tool_name}: {e}")
    
    def _restore_tool_state(self, tool_name: str) -> None:
        """Restore tool state from cache."""
        if tool_name not in self._tool_state_cache:
            return
        
        tool = self.get_tool(tool_name)
        if tool:
            try:
                state = self._tool_state_cache[tool_name]
                for key, value in state.items():
                    tool.set_config(key, value)
                    
            except Exception as e:
                print(f"Error restoring tool state for {tool_name}: {e}")
    
    def _update_tool_usage(self, tool_name: str, action: str) -> None:
        """Update tool usage analytics."""
        if tool_name not in self._analytics['tool_usage']:
            self._analytics['tool_usage'][tool_name] = {
                'activation_count': 0,
                'total_active_time': 0.0,
                'selection_count': 0,
                'error_count': 0,
                'last_used': 0.0
            }
        
        usage = self._analytics['tool_usage'][tool_name]
        usage['last_used'] = time.time()
        
        if action == 'activation':
            usage['activation_count'] += 1
        elif action == 'selection':
            usage['selection_count'] += 1
            self._analytics['selection_statistics']['total_selections'] += 1
    
    def _record_error(self, tool_name: str, error: str) -> None:
        """Record tool error."""
        self._analytics['error_counts'][tool_name] = (
            self._analytics['error_counts'].get(tool_name, 0) + 1
        )
        
        if tool_name in self._analytics['tool_usage']:
            self._analytics['tool_usage'][tool_name]['error_count'] += 1
        
        self.error_occurred.emit(tool_name, error)
    
    def _monitor_performance(self) -> None:
        """Monitor tool performance."""
        if not self._config['performance_monitoring']:
            return
        
        if self._active_tool:
            tool = self.get_active_tool()
            if tool:
                metrics = tool.get_metrics()
                tool_name = self._active_tool
                
                # Store performance data
                if tool_name not in self._analytics['performance_data']:
                    self._analytics['performance_data'][tool_name] = {}
                
                perf_data = self._analytics['performance_data'][tool_name]
                perf_data.update(metrics)
                
                # Check for performance warnings
                avg_time = metrics.get('average_operation_time', 0)
                if avg_time > self._config['performance_warning_threshold']:
                    self.performance_warning.emit(tool_name, metrics)
    
    def _auto_deactivate_active_tool(self) -> None:
        """Auto-deactivate active tool after timeout."""
        if self._active_tool:
            self.deactivate_tool()