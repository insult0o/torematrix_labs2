# AGENT 4 - SELECTION TOOLS: Integration, Accessibility & Production Readiness

## 🎯 Your Assignment
You are **Agent 4** in the 4-agent parallel development of the **Advanced Document Processing Pipeline Selection Tools Implementation**. Your focus is on **Integration, Accessibility & Production Readiness** - bringing all components together into a production-ready system with full accessibility support.

## 📋 Your Specific Tasks
- [ ] Create comprehensive Event Bus integration in `src/torematrix/ui/viewer/tools/event_integration.py`
- [ ] Implement Overlay System integration in `src/torematrix/ui/viewer/tools/overlay_integration.py`
- [ ] Create accessibility features and keyboard navigation in `src/torematrix/ui/viewer/tools/accessibility.py`
- [ ] Implement comprehensive undo/redo integration in `src/torematrix/ui/viewer/tools/undo_integration.py`
- [ ] Create tool state serialization and persistence in `src/torematrix/ui/viewer/tools/serialization.py`
- [ ] Implement comprehensive testing framework in `tests/integration/tools/`
- [ ] Create performance benchmarking and validation in `tests/performance/tools/`
- [ ] Implement production monitoring and logging in `src/torematrix/ui/viewer/tools/monitoring.py`
- [ ] Create comprehensive documentation and examples in `docs/selection_tools/`
- [ ] Implement final integration testing and quality assurance

## 📁 Files to Create

```
src/torematrix/ui/viewer/tools/
├── event_integration.py            # Event Bus integration
├── overlay_integration.py          # Overlay system integration
├── accessibility.py                # Accessibility features
├── undo_integration.py             # Undo/redo system integration
├── serialization.py                # Tool state serialization
├── monitoring.py                   # Production monitoring
├── quality_assurance.py            # Quality validation
└── production_config.py            # Production configuration

tests/integration/tools/
├── __init__.py
├── test_event_integration.py       # Event Bus integration tests
├── test_overlay_integration.py     # Overlay integration tests
├── test_accessibility.py           # Accessibility tests
├── test_undo_integration.py        # Undo/redo integration tests
├── test_serialization.py           # Serialization tests
├── test_end_to_end.py              # End-to-end workflow tests
└── test_production_scenarios.py    # Production scenario tests

tests/performance/tools/
├── __init__.py
├── test_performance_benchmarks.py  # Performance benchmarking
├── test_memory_usage.py            # Memory usage tests
├── test_scalability.py             # Scalability tests
└── test_stress_testing.py          # Stress testing

docs/selection_tools/
├── README.md                       # Overview and quickstart
├── api_reference.md                # Complete API documentation
├── user_guide.md                   # User interaction guide
├── accessibility_guide.md          # Accessibility features
├── performance_guide.md            # Performance optimization
├── integration_guide.md            # Integration with other systems
└── troubleshooting.md              # Common issues and solutions
```

## 🔧 Technical Implementation Details

### Event Bus Integration
```python
from typing import Dict, Any, Optional, Callable, List
import time
from src.torematrix.core.event_bus import EventBus, Event
from src.torematrix.ui.viewer.tools.base import SelectionTool, SelectionResult, ToolState
from src.torematrix.ui.viewer.tools.manager import AdvancedToolManager
from PyQt6.QtCore import QObject, pyqtSignal

class SelectionToolEventBus(QObject):
    """Integration layer between selection tools and the global event bus"""
    
    # Signals for UI updates
    tool_changed = pyqtSignal(str)  # tool_name
    selection_updated = pyqtSignal(dict)  # selection_data
    performance_alert = pyqtSignal(str, dict)  # alert_type, metrics
    
    def __init__(self, event_bus: EventBus, tool_manager: AdvancedToolManager):
        super().__init__()
        self.event_bus = event_bus
        self.tool_manager = tool_manager
        self.tool_subscriptions: Dict[str, List[str]] = {}
        self.selection_handlers: Dict[str, SelectionTool] = {}
        self.event_history: List[Dict[str, Any]] = []
        self.max_history = 100
        
        # Performance monitoring
        self.event_metrics = {
            'events_processed': 0,
            'events_per_second': 0.0,
            'last_event_time': 0.0,
            'event_types': {}
        }
        
        # Setup event subscriptions
        self._setup_event_subscriptions()
        
        # Start performance monitoring
        self._start_performance_monitoring()
    
    def _setup_event_subscriptions(self) -> None:
        """Setup event subscriptions for tool coordination"""
        # Document events
        self.event_bus.subscribe('document.loaded', self._on_document_loaded)
        self.event_bus.subscribe('document.closed', self._on_document_closed)
        self.event_bus.subscribe('document.page_changed', self._on_page_changed)
        self.event_bus.subscribe('document.elements_updated', self._on_elements_updated)
        
        # View events
        self.event_bus.subscribe('view.zoom_changed', self._on_zoom_changed)
        self.event_bus.subscribe('view.pan_changed', self._on_pan_changed)
        self.event_bus.subscribe('view.resize', self._on_view_resized)
        self.event_bus.subscribe('view.rotation_changed', self._on_rotation_changed)
        
        # Tool events
        self.event_bus.subscribe('tool.switch_requested', self._on_tool_switch_requested)
        self.event_bus.subscribe('tool.configuration_changed', self._on_tool_config_changed)
        self.event_bus.subscribe('tool.shortcut_pressed', self._on_tool_shortcut_pressed)
        
        # Selection events
        self.event_bus.subscribe('selection.clear_requested', self._on_selection_clear_requested)
        self.event_bus.subscribe('selection.select_all_requested', self._on_select_all_requested)
        self.event_bus.subscribe('selection.undo_requested', self._on_undo_requested)
        self.event_bus.subscribe('selection.redo_requested', self._on_redo_requested)
        
        # Performance events
        self.event_bus.subscribe('performance.fps_warning', self._on_performance_warning)
        self.event_bus.subscribe('performance.memory_warning', self._on_memory_warning)
    
    def register_tool(self, tool_name: str, tool: SelectionTool) -> None:
        """Register a tool with event bus integration"""
        # Connect tool signals to event bus
        tool.selection_changed.connect(
            lambda result: self._emit_selection_event(tool_name, result)
        )
        tool.state_changed.connect(
            lambda state: self._emit_state_event(tool_name, state)
        )
        tool.cursor_changed.connect(
            lambda cursor: self._emit_cursor_event(tool_name, cursor)
        )
        
        # Store tool for event handling
        self.selection_handlers[tool_name] = tool
        self.tool_subscriptions[tool_name] = []
    
    def _emit_selection_event(self, tool_name: str, result: SelectionResult) -> None:
        """Emit selection event to global event bus"""
        event_data = {
            'tool_name': tool_name,
            'elements': [self._serialize_element(elem) for elem in result.elements],
            'geometry': {
                'x': result.geometry.x(),
                'y': result.geometry.y(),
                'width': result.geometry.width(),
                'height': result.geometry.height()
            },
            'timestamp': result.timestamp,
            'metadata': result.metadata,
            'selection_id': f"{tool_name}_{int(result.timestamp * 1000)}"
        }
        
        self.event_bus.emit('selection.changed', event_data)
        self.selection_updated.emit(event_data)
        
        # Add to history
        self._add_to_history('selection_changed', event_data)
    
    def _emit_state_event(self, tool_name: str, state: ToolState) -> None:
        """Emit tool state change event"""
        event_data = {
            'tool_name': tool_name,
            'state': state.value,
            'timestamp': time.time(),
            'previous_state': getattr(self.selection_handlers[tool_name], '_previous_state', None)
        }
        
        self.event_bus.emit('tool.state_changed', event_data)
        self._add_to_history('state_changed', event_data)
    
    def _emit_cursor_event(self, tool_name: str, cursor) -> None:
        """Emit cursor change event"""
        event_data = {
            'tool_name': tool_name,
            'cursor_shape': cursor.shape(),
            'timestamp': time.time()
        }
        
        self.event_bus.emit('tool.cursor_changed', event_data)
    
    def _on_document_loaded(self, event_data: Dict[str, Any]) -> None:
        """Handle document loaded event"""
        # Reset all tools when new document loads
        for tool_name, tool in self.selection_handlers.items():
            tool.reset()
        
        # Update coordinate systems
        document_bounds = event_data.get('bounds')
        if document_bounds:
            self._update_coordinate_systems(document_bounds)
        
        # Emit tool reset event
        self.event_bus.emit('tools.document_loaded', {
            'document_id': event_data.get('document_id'),
            'tools_reset': list(self.selection_handlers.keys()),
            'timestamp': time.time()
        })
    
    def _on_document_closed(self, event_data: Dict[str, Any]) -> None:
        """Handle document closed event"""
        # Save current tool states for potential restoration
        tool_states = {}
        for tool_name, tool in self.selection_handlers.items():
            tool_states[tool_name] = {
                'state': tool._state.value if hasattr(tool, '_state') else 'inactive',
                'selection': tool._selection_result if hasattr(tool, '_selection_result') else None
            }
        
        # Clear all tools
        for tool in self.selection_handlers.values():
            tool.deactivate()
        
        self.event_bus.emit('tools.document_closed', {
            'document_id': event_data.get('document_id'),
            'saved_states': tool_states,
            'timestamp': time.time()
        })
    
    def _on_zoom_changed(self, event_data: Dict[str, Any]) -> None:
        """Handle zoom change event"""
        zoom_level = event_data.get('zoom_level', 1.0)
        
        # Update all tools with new zoom level
        for tool_name, tool in self.selection_handlers.items():
            if hasattr(tool, 'update_zoom'):
                tool.update_zoom(zoom_level)
        
        # Update tool manager
        if hasattr(self.tool_manager, 'update_zoom'):
            self.tool_manager.update_zoom(zoom_level)
    
    def _on_tool_switch_requested(self, event_data: Dict[str, Any]) -> None:
        """Handle tool switch request"""
        tool_name = event_data.get('tool_name')
        if tool_name and tool_name in self.selection_handlers:
            success = self.tool_manager.switch_tool(tool_name)
            if success:
                self.tool_changed.emit(tool_name)
                self.event_bus.emit('tool.switched', {
                    'tool_name': tool_name,
                    'timestamp': time.time(),
                    'success': True
                })
            else:
                self.event_bus.emit('tool.switch_failed', {
                    'tool_name': tool_name,
                    'timestamp': time.time(),
                    'reason': 'Tool switch failed'
                })
    
    def _on_selection_clear_requested(self, event_data: Dict[str, Any]) -> None:
        """Handle selection clear request"""
        active_tool = self.tool_manager.get_active_tool()
        if active_tool and hasattr(active_tool, 'clear_selection'):
            active_tool.clear_selection()
            
        self.event_bus.emit('selection.cleared', {
            'timestamp': time.time(),
            'tool_name': getattr(active_tool, 'name', 'unknown') if active_tool else None
        })
    
    def _on_undo_requested(self, event_data: Dict[str, Any]) -> None:
        """Handle undo request"""
        if hasattr(self.tool_manager, 'undo'):
            success = self.tool_manager.undo()
            self.event_bus.emit('selection.undo_performed', {
                'success': success,
                'timestamp': time.time()
            })
    
    def _on_performance_warning(self, event_data: Dict[str, Any]) -> None:
        """Handle performance warning"""
        warning_type = event_data.get('type', 'general')
        metrics = event_data.get('metrics', {})
        
        self.performance_alert.emit(warning_type, metrics)
        
        # Take corrective action if needed
        if warning_type == 'low_fps':
            self._reduce_performance_impact()
        elif warning_type == 'high_memory':
            self._clear_caches()
    
    def _serialize_element(self, element: Any) -> Dict[str, Any]:
        """Serialize element for event data"""
        return {
            'id': getattr(element, 'id', None),
            'type': getattr(element, 'type', 'unknown'),
            'bounds': {
                'x': element.bounding_rect.x(),
                'y': element.bounding_rect.y(),
                'width': element.bounding_rect.width(),
                'height': element.bounding_rect.height()
            } if hasattr(element, 'bounding_rect') else None,
            'content': getattr(element, 'content', None)
        }
    
    def _add_to_history(self, event_type: str, data: Dict[str, Any]) -> None:
        """Add event to history"""
        self.event_history.append({
            'type': event_type,
            'data': data,
            'timestamp': time.time()
        })
        
        # Limit history size
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
    
    def _start_performance_monitoring(self) -> None:
        """Start performance monitoring"""
        self.event_metrics['start_time'] = time.time()
    
    def _update_performance_metrics(self, event_type: str) -> None:
        """Update performance metrics"""
        current_time = time.time()
        
        self.event_metrics['events_processed'] += 1
        self.event_metrics['last_event_time'] = current_time
        
        # Update event type counts
        self.event_metrics['event_types'][event_type] = \
            self.event_metrics['event_types'].get(event_type, 0) + 1
        
        # Calculate events per second
        elapsed = current_time - self.event_metrics['start_time']
        if elapsed > 0:
            self.event_metrics['events_per_second'] = \
                self.event_metrics['events_processed'] / elapsed
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """Get event processing statistics"""
        return {
            'total_events': self.event_metrics['events_processed'],
            'events_per_second': self.event_metrics['events_per_second'],
            'event_types': self.event_metrics['event_types'].copy(),
            'history_size': len(self.event_history),
            'registered_tools': list(self.selection_handlers.keys()),
            'active_tool': self.tool_manager.get_active_tool_name() if hasattr(self.tool_manager, 'get_active_tool_name') else None
        }
    
    def cleanup(self) -> None:
        """Clean up event subscriptions"""
        # Unsubscribe from all events
        for tool_name in self.tool_subscriptions:
            self.tool_subscriptions[tool_name].clear()
        
        self.selection_handlers.clear()
        self.event_history.clear()
```

### Overlay System Integration
```python
from typing import Dict, Any, List, Optional
from PyQt6.QtCore import QPoint, QRect, QObject, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPolygonF
from src.torematrix.ui.viewer.overlay import OverlayEngine, OverlayElement
from src.torematrix.ui.viewer.coordinates import Rectangle, Point
from src.torematrix.ui.viewer.tools.base import SelectionResult, ToolState

class SelectionOverlayElement(OverlayElement):
    """Overlay element for selection visualization"""
    
    def __init__(self, selection_result: SelectionResult, tool_name: str):
        self.selection_result = selection_result
        self.tool_name = tool_name
        self.visible = True
        self.z_index = 100  # High z-index for selections
        self.animation_progress = 0.0
        self.fade_alpha = 255
        
        # Visual properties
        self.border_color = QColor(0, 120, 215)
        self.fill_color = QColor(0, 120, 215, 50)
        self.border_width = 2
        self.corner_radius = 0
        
        # Animation properties
        self.pulse_animation = False
        self.pulse_speed = 2.0
        self.pulse_min_alpha = 100
        self.pulse_max_alpha = 255
        
        # Tool-specific styling
        self._apply_tool_styling()
    
    def _apply_tool_styling(self) -> None:
        """Apply tool-specific visual styling"""
        tool_styles = {
            'pointer': {
                'border_color': QColor(0, 120, 215),
                'fill_color': QColor(0, 120, 215, 50),
                'border_width': 2,
                'corner_radius': 2,
                'pulse_animation': False
            },
            'rectangle': {
                'border_color': QColor(255, 140, 0),
                'fill_color': QColor(255, 140, 0, 30),
                'border_width': 1,
                'corner_radius': 0,
                'pulse_animation': True
            },
            'lasso': {
                'border_color': QColor(50, 205, 50),
                'fill_color': QColor(50, 205, 50, 40),
                'border_width': 2,
                'corner_radius': 0,
                'pulse_animation': True
            },
            'element_aware': {
                'border_color': QColor(138, 43, 226),
                'fill_color': QColor(138, 43, 226, 60),
                'border_width': 3,
                'corner_radius': 4,
                'pulse_animation': False
            }
        }
        
        if self.tool_name in tool_styles:
            style = tool_styles[self.tool_name]
            self.border_color = style['border_color']
            self.fill_color = style['fill_color']
            self.border_width = style['border_width']
            self.corner_radius = style['corner_radius']
            self.pulse_animation = style['pulse_animation']
    
    def get_bounds(self) -> Rectangle:
        """Get the bounding rectangle of the selection"""
        qrect = self.selection_result.geometry
        return Rectangle(
            x=qrect.x(),
            y=qrect.y(),
            width=qrect.width(),
            height=qrect.height()
        )
    
    def get_style(self) -> Dict[str, Any]:
        """Get the style properties"""
        return {
            'border_color': self.border_color,
            'fill_color': self.fill_color,
            'border_width': self.border_width,
            'corner_radius': self.corner_radius,
            'tool_name': self.tool_name,
            'fade_alpha': self.fade_alpha,
            'pulse_animation': self.pulse_animation
        }
    
    def is_visible(self) -> bool:
        """Check if the element is visible"""
        return self.visible and self.fade_alpha > 0
    
    def get_z_index(self) -> int:
        """Get the z-index for layering"""
        return self.z_index
    
    def update_animation(self, delta_time: float) -> None:
        """Update animation state"""
        if self.pulse_animation:
            self.animation_progress += delta_time * self.pulse_speed
            
            # Calculate pulse alpha
            pulse_factor = (math.sin(self.animation_progress) + 1) / 2
            self.fade_alpha = int(
                self.pulse_min_alpha + 
                (self.pulse_max_alpha - self.pulse_min_alpha) * pulse_factor
            )
            
            # Update colors with new alpha
            self.fill_color.setAlpha(self.fade_alpha // 3)
            self.border_color.setAlpha(self.fade_alpha)
    
    def set_highlight_mode(self, enabled: bool) -> None:
        """Set highlight mode for enhanced visibility"""
        if enabled:
            self.border_width = max(self.border_width, 3)
            self.z_index = 200
            self.pulse_animation = True
        else:
            self.border_width = 2
            self.z_index = 100
            self.pulse_animation = False

class SelectionOverlayIntegration(QObject):
    """Integration between selection tools and overlay system"""
    
    # Signals
    selection_rendered = pyqtSignal(str)  # selection_id
    overlay_updated = pyqtSignal()
    
    def __init__(self, overlay_engine: OverlayEngine):
        super().__init__()
        self.overlay_engine = overlay_engine
        self.selection_layer = None
        self.preview_layer = None
        self.current_selections: Dict[str, SelectionOverlayElement] = {}
        self.preview_elements: Dict[str, SelectionOverlayElement] = {}
        
        # Animation management
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_animations)
        self.animation_timer.start(16)  # ~60fps
        self.last_animation_time = time.time()
        
        # Performance tracking
        self.render_metrics = {
            'selections_rendered': 0,
            'avg_render_time': 0.0,
            'overlay_updates': 0
        }
        
        # Create overlay layers
        self._create_overlay_layers()
    
    def _create_overlay_layers(self) -> None:
        """Create the selection overlay layers"""
        # Main selection layer
        self.selection_layer = self.overlay_engine.create_layer('selections', z_index=100)
        
        # Preview layer for hover/preview selections
        self.preview_layer = self.overlay_engine.create_layer('selection_previews', z_index=90)
        
        # Highlight layer for emphasized selections
        self.highlight_layer = self.overlay_engine.create_layer('selection_highlights', z_index=110)
    
    def show_selection(self, selection_id: str, tool_name: str, selection_result: SelectionResult) -> None:
        """Show selection in overlay"""
        start_time = time.time()
        
        # Remove existing selection for this ID
        self.hide_selection(selection_id)
        
        # Create new selection element
        selection_element = SelectionOverlayElement(selection_result, tool_name)
        self.current_selections[selection_id] = selection_element
        
        # Add to overlay
        self.overlay_engine.add_element('selections', selection_element)
        
        # Update performance metrics
        render_time = (time.time() - start_time) * 1000
        self._update_render_metrics(render_time)
        
        self.selection_rendered.emit(selection_id)
        self.overlay_updated.emit()
    
    def hide_selection(self, selection_id: str) -> None:
        """Hide selection for specific ID"""
        if selection_id in self.current_selections:
            element = self.current_selections[selection_id]
            self.overlay_engine.remove_element('selections', element)
            del self.current_selections[selection_id]
            self.overlay_updated.emit()
    
    def show_preview_selection(self, preview_id: str, tool_name: str, selection_result: SelectionResult) -> None:
        """Show preview selection in overlay"""
        # Remove existing preview
        self.hide_preview_selection(preview_id)
        
        # Create preview element with different styling
        preview_element = SelectionOverlayElement(selection_result, tool_name)
        preview_element.z_index = 90
        preview_element.fade_alpha = 150
        preview_element.border_width = 1
        preview_element.fill_color.setAlpha(20)
        
        self.preview_elements[preview_id] = preview_element
        self.overlay_engine.add_element('selection_previews', preview_element)
        
        self.overlay_updated.emit()
    
    def hide_preview_selection(self, preview_id: str) -> None:
        """Hide preview selection"""
        if preview_id in self.preview_elements:
            element = self.preview_elements[preview_id]
            self.overlay_engine.remove_element('selection_previews', element)
            del self.preview_elements[preview_id]
            self.overlay_updated.emit()
    
    def highlight_selection(self, selection_id: str, highlighted: bool = True) -> None:
        """Highlight or unhighlight a selection"""
        if selection_id in self.current_selections:
            element = self.current_selections[selection_id]
            
            if highlighted:
                # Move to highlight layer
                self.overlay_engine.remove_element('selections', element)
                element.set_highlight_mode(True)
                self.overlay_engine.add_element('selection_highlights', element)
            else:
                # Move back to selection layer
                self.overlay_engine.remove_element('selection_highlights', element)
                element.set_highlight_mode(False)
                self.overlay_engine.add_element('selections', element)
            
            self.overlay_updated.emit()
    
    def clear_all_selections(self) -> None:
        """Clear all selections from overlay"""
        self.overlay_engine.clear_layer('selections')
        self.overlay_engine.clear_layer('selection_previews')
        self.overlay_engine.clear_layer('selection_highlights')
        
        self.current_selections.clear()
        self.preview_elements.clear()
        
        self.overlay_updated.emit()
    
    def update_selection_visibility(self, selection_id: str, visible: bool) -> None:
        """Update selection visibility"""
        if selection_id in self.current_selections:
            element = self.current_selections[selection_id]
            element.visible = visible
            self.overlay_engine.invalidate_element(element)
            self.overlay_updated.emit()
    
    def set_selection_style(self, selection_id: str, style: Dict[str, Any]) -> None:
        """Update selection styling"""
        if selection_id in self.current_selections:
            element = self.current_selections[selection_id]
            
            if 'border_color' in style:
                element.border_color = QColor(style['border_color'])
            if 'fill_color' in style:
                element.fill_color = QColor(style['fill_color'])
            if 'border_width' in style:
                element.border_width = style['border_width']
            if 'corner_radius' in style:
                element.corner_radius = style['corner_radius']
            
            self.overlay_engine.invalidate_element(element)
            self.overlay_updated.emit()
    
    def _update_animations(self) -> None:
        """Update animation state for all elements"""
        current_time = time.time()
        delta_time = current_time - self.last_animation_time
        self.last_animation_time = current_time
        
        # Update selection animations
        for element in self.current_selections.values():
            element.update_animation(delta_time)
        
        # Update preview animations
        for element in self.preview_elements.values():
            element.update_animation(delta_time)
        
        # Trigger overlay refresh if needed
        if self.current_selections or self.preview_elements:
            self.overlay_engine.schedule_render()
    
    def _update_render_metrics(self, render_time: float) -> None:
        """Update rendering performance metrics"""
        self.render_metrics['selections_rendered'] += 1
        self.render_metrics['overlay_updates'] += 1
        
        # Update average render time
        current_avg = self.render_metrics['avg_render_time']
        count = self.render_metrics['selections_rendered']
        self.render_metrics['avg_render_time'] = (current_avg * (count - 1) + render_time) / count
    
    def get_render_statistics(self) -> Dict[str, Any]:
        """Get rendering statistics"""
        return {
            'current_selections': len(self.current_selections),
            'preview_elements': len(self.preview_elements),
            'total_rendered': self.render_metrics['selections_rendered'],
            'avg_render_time_ms': self.render_metrics['avg_render_time'],
            'overlay_updates': self.render_metrics['overlay_updates'],
            'layers': {
                'selections': len(self.selection_layer.get_elements()) if self.selection_layer else 0,
                'previews': len(self.preview_layer.get_elements()) if self.preview_layer else 0,
                'highlights': len(self.highlight_layer.get_elements()) if self.highlight_layer else 0
            }
        }
    
    def cleanup(self) -> None:
        """Clean up overlay integration"""
        self.animation_timer.stop()
        self.clear_all_selections()
        
        # Remove layers
        if self.selection_layer:
            self.overlay_engine.remove_layer('selections')
        if self.preview_layer:
            self.overlay_engine.remove_layer('selection_previews')
        if self.highlight_layer:
            self.overlay_engine.remove_layer('selection_highlights')
```

### Accessibility Features
```python
from typing import Dict, List, Optional, Callable, Any
from PyQt6.QtCore import QObject, pyqtSignal, QEvent, QTimer, Qt
from PyQt6.QtGui import QKeyEvent, QFocusEvent, QAccessible, QAccessibleInterface
from PyQt6.QtWidgets import QWidget, QApplication

class AccessibilityManager(QObject):
    """Accessibility support for selection tools"""
    
    # Accessibility signals
    selection_announced = pyqtSignal(str)  # Screen reader announcements
    navigation_changed = pyqtSignal(str)   # Navigation state changes
    shortcut_activated = pyqtSignal(str)   # Keyboard shortcut activation
    focus_changed = pyqtSignal(str)        # Focus element changed
    
    def __init__(self, parent_widget: QWidget):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget
        self.current_focus_element = None
        self.focus_ring: List[Any] = []
        self.focus_index = 0
        self.screen_reader_enabled = False
        
        # Keyboard navigation
        self.keyboard_shortcuts = {
            'Ctrl+A': 'select_all',
            'Escape': 'clear_selection',
            'Tab': 'next_element',
            'Shift+Tab': 'previous_element',
            'Space': 'toggle_selection',
            'Enter': 'confirm_selection',
            'F2': 'rename_element',
            'Delete': 'delete_selection',
            'Ctrl+Z': 'undo',
            'Ctrl+Y': 'redo',
            'Ctrl+Shift+Z': 'redo',
            'F1': 'help',
            'F3': 'find_next',
            'Shift+F3': 'find_previous',
            'Home': 'first_element',
            'End': 'last_element',
            'PageUp': 'previous_page',
            'PageDown': 'next_page',
            'Arrow_Up': 'navigate_up',
            'Arrow_Down': 'navigate_down',
            'Arrow_Left': 'navigate_left',
            'Arrow_Right': 'navigate_right'
        }
        
        # Voice announcements
        self.voice_enabled = False
        self.voice_queue = []
        self.voice_timer = QTimer()
        self.voice_timer.timeout.connect(self._process_voice_queue)
        self.voice_timer.start(500)  # Process voice queue every 500ms
        
        # High contrast mode
        self.high_contrast_enabled = False
        self.high_contrast_colors = {
            'background': '#000000',
            'foreground': '#FFFFFF',
            'selection': '#FFFF00',
            'focus': '#FF0000',
            'disabled': '#808080'
        }
        
        # Screen reader detection and setup
        self.screen_reader_enabled = self._detect_screen_reader()
        
        # Setup accessibility features
        self._setup_accessibility()
    
    def _detect_screen_reader(self) -> bool:
        """Detect if screen reader is active"""
        try:
            # Check for common screen readers
            import platform
            if platform.system() == "Windows":
                import winreg
                # Check for NVDA, JAWS, or other screen readers
                return self._check_windows_screen_reader()
            elif platform.system() == "Darwin":
                # Check for VoiceOver on macOS
                return self._check_macos_screen_reader()
            elif platform.system() == "Linux":
                # Check for Orca or other Linux screen readers
                return self._check_linux_screen_reader()
        except Exception:
            pass
        
        # Fallback: check Qt accessibility
        return QApplication.instance().testAttribute(Qt.ApplicationAttribute.AA_UseDesktopSettings)
    
    def _setup_accessibility(self) -> None:
        """Setup accessibility features"""
        # Install event filter for keyboard navigation
        self.parent_widget.installEventFilter(self)
        
        # Set up widget accessibility properties
        self.parent_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.parent_widget.setAccessibleName("Document Selection Interface")
        self.parent_widget.setAccessibleDescription("Use Tab to navigate, Space to select, Enter to confirm")
        
        # Enable keyboard focus
        self.parent_widget.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        
        # Setup focus management
        self._setup_focus_management()
        
        # Configure screen reader support
        if self.screen_reader_enabled:
            self._setup_screen_reader_support()
    
    def _setup_focus_management(self) -> None:
        """Setup focus management for keyboard navigation"""
        # Focus ring timer for visible focus indicator
        self.focus_timer = QTimer(self)
        self.focus_timer.setSingleShot(True)
        self.focus_timer.timeout.connect(self._update_focus_ring)
        
        # Focus announcement timer
        self.focus_announcement_timer = QTimer(self)
        self.focus_announcement_timer.setSingleShot(True)
        self.focus_announcement_timer.timeout.connect(self._announce_focus_change)
    
    def _setup_screen_reader_support(self) -> None:
        """Setup screen reader specific features"""
        # Create accessible interface
        self.accessible_interface = SelectionAccessibleInterface(self.parent_widget)
        
        # Enable live regions for dynamic content
        self.parent_widget.setAccessibleName("Selection Tools Live Region")
        
        # Setup ARIA-like attributes
        self._setup_aria_attributes()
    
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Handle keyboard and accessibility events"""
        if event.type() == QEvent.Type.KeyPress:
            key_event = QKeyEvent(event)
            return self._handle_key_press(key_event)
        elif event.type() == QEvent.Type.FocusIn:
            self._handle_focus_in(event)
        elif event.type() == QEvent.Type.FocusOut:
            self._handle_focus_out(event)
        elif event.type() == QEvent.Type.AccessibilityHelp:
            self._handle_accessibility_help(event)
        
        return super().eventFilter(obj, event)
    
    def _handle_key_press(self, event: QKeyEvent) -> bool:
        """Handle keyboard shortcuts and navigation"""
        key_combo = self._get_key_combination(event)
        
        if key_combo in self.keyboard_shortcuts:
            action = self.keyboard_shortcuts[key_combo]
            success = self._execute_accessibility_action(action)
            
            if success:
                self.shortcut_activated.emit(action)
                
                # Announce action to screen reader
                if self.screen_reader_enabled:
                    self._announce_action(action)
                
                return True
        
        return False
    
    def _get_key_combination(self, event: QKeyEvent) -> str:
        """Get key combination string from key event"""
        modifiers = []
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            modifiers.append('Ctrl')
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            modifiers.append('Shift')
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            modifiers.append('Alt')
        if event.modifiers() & Qt.KeyboardModifier.MetaModifier:
            modifiers.append('Meta')
        
        # Map key codes to names
        key_name = self._get_key_name(event.key())
        
        if key_name:
            return '+'.join(modifiers + [key_name])
        
        return event.text().upper() if event.text() else ''
    
    def _get_key_name(self, key_code: int) -> Optional[str]:
        """Get key name from key code"""
        key_map = {
            Qt.Key.Key_Tab: 'Tab',
            Qt.Key.Key_Space: 'Space',
            Qt.Key.Key_Enter: 'Enter',
            Qt.Key.Key_Return: 'Enter',
            Qt.Key.Key_Escape: 'Escape',
            Qt.Key.Key_Delete: 'Delete',
            Qt.Key.Key_Backspace: 'Backspace',
            Qt.Key.Key_F1: 'F1',
            Qt.Key.Key_F2: 'F2',
            Qt.Key.Key_F3: 'F3',
            Qt.Key.Key_Home: 'Home',
            Qt.Key.Key_End: 'End',
            Qt.Key.Key_PageUp: 'PageUp',
            Qt.Key.Key_PageDown: 'PageDown',
            Qt.Key.Key_Up: 'Arrow_Up',
            Qt.Key.Key_Down: 'Arrow_Down',
            Qt.Key.Key_Left: 'Arrow_Left',
            Qt.Key.Key_Right: 'Arrow_Right'
        }
        
        return key_map.get(key_code)
    
    def _execute_accessibility_action(self, action: str) -> bool:
        """Execute accessibility-specific actions"""
        try:
            if action == 'select_all':
                self._select_all_elements()
            elif action == 'clear_selection':
                self._clear_selection()
            elif action == 'next_element':
                self._navigate_to_next_element()
            elif action == 'previous_element':
                self._navigate_to_previous_element()
            elif action == 'toggle_selection':
                self._toggle_current_selection()
            elif action == 'confirm_selection':
                self._confirm_selection()
            elif action == 'undo':
                self._undo_action()
            elif action == 'redo':
                self._redo_action()
            elif action == 'help':
                self._show_help()
            elif action == 'first_element':
                self._navigate_to_first_element()
            elif action == 'last_element':
                self._navigate_to_last_element()
            elif action.startswith('navigate_'):
                direction = action.split('_')[1]
                self._navigate_directional(direction)
            else:
                return False
            
            return True
        except Exception as e:
            print(f"Accessibility action '{action}' failed: {e}")
            return False
    
    def _navigate_to_next_element(self) -> None:
        """Navigate to next element in focus ring"""
        if self.focus_ring:
            self.focus_index = (self.focus_index + 1) % len(self.focus_ring)
            self._update_focus_to_current_element()
    
    def _navigate_to_previous_element(self) -> None:
        """Navigate to previous element in focus ring"""
        if self.focus_ring:
            self.focus_index = (self.focus_index - 1) % len(self.focus_ring)
            self._update_focus_to_current_element()
    
    def _navigate_to_first_element(self) -> None:
        """Navigate to first element in focus ring"""
        if self.focus_ring:
            self.focus_index = 0
            self._update_focus_to_current_element()
    
    def _navigate_to_last_element(self) -> None:
        """Navigate to last element in focus ring"""
        if self.focus_ring:
            self.focus_index = len(self.focus_ring) - 1
            self._update_focus_to_current_element()
    
    def _navigate_directional(self, direction: str) -> None:
        """Navigate in specified direction"""
        if not self.focus_ring or not self.current_focus_element:
            return
        
        current_pos = self._get_element_position(self.current_focus_element)
        best_element = None
        best_distance = float('inf')
        
        for element in self.focus_ring:
            if element == self.current_focus_element:
                continue
            
            element_pos = self._get_element_position(element)
            
            # Check if element is in the correct direction
            if direction == 'up' and element_pos.y >= current_pos.y:
                continue
            elif direction == 'down' and element_pos.y <= current_pos.y:
                continue
            elif direction == 'left' and element_pos.x >= current_pos.x:
                continue
            elif direction == 'right' and element_pos.x <= current_pos.x:
                continue
            
            # Calculate distance
            distance = ((element_pos.x - current_pos.x) ** 2 + 
                       (element_pos.y - current_pos.y) ** 2) ** 0.5
            
            if distance < best_distance:
                best_distance = distance
                best_element = element
        
        if best_element:
            self.focus_index = self.focus_ring.index(best_element)
            self._update_focus_to_current_element()
    
    def _update_focus_to_current_element(self) -> None:
        """Update focus to current element and announce to screen reader"""
        if self.focus_ring and 0 <= self.focus_index < len(self.focus_ring):
            element = self.focus_ring[self.focus_index]
            self.current_focus_element = element
            
            # Announce to screen reader
            description = self._get_element_description(element)
            self._queue_announcement(description)
            
            self.focus_changed.emit(description)
            self.navigation_changed.emit(f"Focus on {description}")
            
            # Start announcement timer
            self.focus_announcement_timer.start(100)
    
    def _get_element_description(self, element: Any) -> str:
        """Get accessible description for element"""
        if hasattr(element, 'accessible_name'):
            return element.accessible_name
        elif hasattr(element, 'type') and hasattr(element, 'content'):
            content = element.content[:50] + "..." if len(element.content) > 50 else element.content
            return f"{element.type}: {content}"
        elif hasattr(element, 'type'):
            return f"{element.type} element"
        else:
            return "Document element"
    
    def _queue_announcement(self, message: str) -> None:
        """Queue message for screen reader announcement"""
        self.voice_queue.append({
            'message': message,
            'timestamp': time.time(),
            'priority': 'normal'
        })
        
        # Limit queue size
        if len(self.voice_queue) > 10:
            self.voice_queue.pop(0)
    
    def _process_voice_queue(self) -> None:
        """Process voice announcement queue"""
        if not self.voice_queue or not self.screen_reader_enabled:
            return
        
        # Get next announcement
        announcement = self.voice_queue.pop(0)
        message = announcement['message']
        
        # Emit signal for screen reader
        self.selection_announced.emit(message)
        
        # Platform-specific screen reader integration
        self._announce_to_screen_reader(message)
    
    def _announce_to_screen_reader(self, message: str) -> None:
        """Announce message to screen reader"""
        try:
            # Use QAccessible to announce
            QAccessible.updateAccessibility(
                self.parent_widget,
                0,  # child index
                QAccessible.Event.Alert
            )
            
            # Set accessible description for live region
            self.parent_widget.setAccessibleDescription(message)
            
        except Exception as e:
            print(f"Screen reader announcement failed: {e}")
    
    def update_focus_ring(self, elements: List[Any]) -> None:
        """Update the focus ring with new elements"""
        self.focus_ring = elements
        self.focus_index = 0
        
        if elements:
            self._update_focus_to_current_element()
    
    def announce_selection(self, selection_result) -> None:
        """Announce selection to screen reader"""
        if not self.screen_reader_enabled:
            return
        
        count = len(selection_result.elements)
        if count == 1:
            element = selection_result.elements[0]
            description = self._get_element_description(element)
            announcement = f"Selected {description}"
        else:
            announcement = f"Selected {count} elements"
        
        self._queue_announcement(announcement)
    
    def set_high_contrast_mode(self, enabled: bool) -> None:
        """Enable or disable high contrast mode"""
        self.high_contrast_enabled = enabled
        
        if enabled:
            self._apply_high_contrast_colors()
        else:
            self._restore_normal_colors()
    
    def get_accessibility_status(self) -> Dict[str, Any]:
        """Get accessibility status and settings"""
        return {
            'screen_reader_enabled': self.screen_reader_enabled,
            'high_contrast_enabled': self.high_contrast_enabled,
            'voice_enabled': self.voice_enabled,
            'focus_ring_size': len(self.focus_ring),
            'current_focus_index': self.focus_index,
            'voice_queue_size': len(self.voice_queue),
            'shortcuts_available': len(self.keyboard_shortcuts)
        }
```

## 🧪 Testing Requirements
- [ ] **Event Integration** - Event Bus communication and coordination
- [ ] **Overlay Integration** - Visual rendering and overlay management
- [ ] **Accessibility** - Screen reader support and keyboard navigation
- [ ] **Undo/Redo** - History management and state restoration
- [ ] **Serialization** - Tool state persistence and restoration
- [ ] **End-to-End** - Complete workflow testing
- [ ] **Performance** - Benchmarking and optimization validation
- [ ] **Production** - Real-world scenario testing
- [ ] **Memory Usage** - Memory leak detection and optimization
- [ ] **Scalability** - Large document handling

**Target:** 40+ comprehensive tests with >95% coverage

## 🔗 Integration Points

### Dependencies (From All Previous Agents)
- ✅ **Base Tool Interface** - Foundation from Agent 1
- ✅ **Tool Implementations** - Working tools from Agent 2
- ✅ **Optimization Features** - Advanced capabilities from Agent 3
- ✅ **Event Bus System** - Global event coordination
- ✅ **Overlay System** - Visual rendering infrastructure

### Provides (Final System)
- **Complete Selection Tools** - Production-ready selection system
- **Accessibility Support** - Full keyboard navigation and screen reader support
- **System Integration** - Seamless integration with all existing systems
- **Production Monitoring** - Performance metrics and quality assurance
- **Comprehensive Documentation** - User guides and API documentation

### Integration Notes
- **Event Coordination:** All tools must integrate with global event bus
- **Visual Consistency:** Overlay integration must maintain visual standards
- **Performance:** All features must maintain real-time performance
- **Accessibility:** Full compliance with accessibility standards

## 🎯 Success Metrics
- **Integration:** 100% compatibility with existing systems
- **Accessibility:** Full WCAG 2.1 AA compliance
- **Performance:** All optimizations maintain <16ms response
- **Quality:** Zero critical bugs in production scenarios
- **Documentation:** Complete user and developer guides

## 🚀 Getting Started

### Step 1: Create Feature Branch
```bash
git checkout main
git pull origin main
git checkout -b feature/selection-tools-agent4-issue160
```

### Step 2: Wait for All Dependencies
- Monitor all previous agents' progress
- Ensure all interfaces are stable
- Begin integration work

### Step 3: Implement Integration
1. Start with Event Bus integration
2. Add Overlay System integration
3. Implement accessibility features
4. Add comprehensive testing
5. Create documentation

### Step 4: Production Validation
1. Test all integration points
2. Validate accessibility compliance
3. Benchmark performance
4. Stress test the system

**Related Issues:**
- Main Issue: #19 - Advanced Document Processing Pipeline Selection Tools
- Sub-Issue: #160 - Integration, Accessibility & Production Readiness
- Dependencies: #157 (Agent 1), #158 (Agent 2), #159 (Agent 3)
- Completes: Full selection tools system

**Timeline:** 2-3 days for complete integration and production readiness.