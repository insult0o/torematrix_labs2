"""Complete Inline Editing System Integration

Brings together all components of the inline editing system into a unified,
production-ready interface. This module provides the main entry point for
integrating inline editing capabilities into the document viewer.

Key Features:
- Unified API for all editing functionality
- Automatic component initialization and management
- Performance monitoring and optimization
- Comprehensive error handling and recovery
- Accessibility features and keyboard navigation
- Theme integration and customization
- Production-ready configuration management

Integration Points:
- Element list integration for seamless editing workflow
- Document viewer overlay system for visual editing
- Coordinate mapping engine for precise positioning
- Theme framework for consistent styling
- Event bus system for reactive updates
"""

from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
import uuid
import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QPoint, QRect
from PyQt6.QtGui import QFont, QPainter, QPalette

# Import all inline editing components
from .base import BaseInlineEditor, EditorState, EditorConfig
from .integration import ElementEditorBridge, EditorIntegrationManager
from .accessibility import AccessibilityManager, AccessibleInlineEditor
from .recovery import EditorErrorHandler, ErrorSeverity, RecoveryStrategy, ErrorContext


class SystemState(Enum):
    """Overall system state for the inline editing system."""
    INITIALIZING = "initializing"
    READY = "ready"
    EDITING = "editing"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    SHUTDOWN = "shutdown"


@dataclass
class SystemConfiguration:
    """Configuration for the complete inline editing system."""
    
    # Core settings
    enable_inline_editing: bool = True
    auto_save_interval: int = 30  # seconds
    max_concurrent_editors: int = 10
    editor_timeout: int = 300  # seconds
    
    # Performance settings
    enable_performance_monitoring: bool = True
    cache_rendered_editors: bool = True
    lazy_load_components: bool = True
    optimize_for_large_documents: bool = True
    
    # Accessibility settings
    enable_accessibility: bool = True
    screen_reader_support: bool = True
    keyboard_navigation: bool = True
    high_contrast_mode: bool = False
    
    # Error handling settings
    enable_error_recovery: bool = True
    max_retry_attempts: int = 3
    auto_recovery_enabled: bool = True
    show_error_dialogs: bool = True
    
    # Integration settings
    bridge_to_element_list: bool = True
    coordinate_mapping_enabled: bool = True
    theme_integration: bool = True
    event_bus_integration: bool = True
    
    # Debug settings
    debug_mode: bool = False
    performance_logging: bool = False
    error_logging: bool = True
    verbose_output: bool = False


@dataclass
class SystemMetrics:
    """System-wide metrics for monitoring and optimization."""
    
    # Performance metrics
    active_editors: int = 0
    total_edits_started: int = 0
    total_edits_completed: int = 0
    total_edits_cancelled: int = 0
    average_edit_duration: float = 0.0
    
    # Error metrics
    total_errors: int = 0
    errors_recovered: int = 0
    critical_errors: int = 0
    recovery_success_rate: float = 0.0
    
    # Resource metrics
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    cache_hit_rate: float = 0.0
    
    # Accessibility metrics
    accessibility_features_used: int = 0
    keyboard_navigation_events: int = 0
    screen_reader_announcements: int = 0
    
    # System health
    system_health_score: float = 100.0
    last_health_check: float = field(default_factory=time.time)
    uptime_seconds: float = 0.0


class SystemStatusWidget(QWidget):
    """Status widget showing system health and metrics."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.metrics = SystemMetrics()
        
    def setup_ui(self):
        """Setup the status widget UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        
        # System status indicator
        self.status_label = QLabel("System: Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #28a745;
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 3px;
                background: rgba(40, 167, 69, 0.1);
            }
        """)
        
        # Active editors count
        self.editors_label = QLabel("Editors: 0")
        self.editors_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        
        # Performance indicator
        self.performance_label = QLabel("Performance: Good")
        self.performance_label.setStyleSheet("color: #17a2b8; font-size: 11px;")
        
        # Error indicator
        self.error_label = QLabel("Errors: 0")
        self.error_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        
        layout.addWidget(self.status_label)
        layout.addWidget(QFrame())  # Separator
        layout.addWidget(self.editors_label)
        layout.addWidget(self.performance_label)
        layout.addWidget(self.error_label)
        layout.addStretch()
    
    def update_metrics(self, metrics: SystemMetrics):
        """Update the displayed metrics."""
        self.metrics = metrics
        
        # Update labels
        self.editors_label.setText(f"Editors: {metrics.active_editors}")
        self.error_label.setText(f"Errors: {metrics.total_errors}")
        
        # Update performance indicator
        if metrics.system_health_score >= 90:
            perf_text = "Performance: Excellent"
            perf_color = "#28a745"
        elif metrics.system_health_score >= 70:
            perf_text = "Performance: Good"
            perf_color = "#17a2b8"
        elif metrics.system_health_score >= 50:
            perf_text = "Performance: Fair"
            perf_color = "#ffc107"
        else:
            perf_text = "Performance: Poor"
            perf_color = "#dc3545"
        
        self.performance_label.setText(perf_text)
        self.performance_label.setStyleSheet(f"color: {perf_color}; font-size: 11px;")
    
    def set_system_state(self, state: SystemState):
        """Update system state indicator."""
        state_colors = {
            SystemState.INITIALIZING: "#6c757d",
            SystemState.READY: "#28a745",
            SystemState.EDITING: "#17a2b8",
            SystemState.ERROR: "#dc3545",
            SystemState.MAINTENANCE: "#ffc107",
            SystemState.SHUTDOWN: "#6c757d"
        }
        
        color = state_colors.get(state, "#6c757d")
        self.status_label.setText(f"System: {state.value.title()}")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 3px;
                background: rgba{self._hex_to_rgba(color, 0.1)};
            }}
        """)
    
    def _hex_to_rgba(self, hex_color: str, alpha: float) -> str:
        """Convert hex color to rgba string."""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return f"({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha})"


class InlineEditingSystem(QObject):
    """Main inline editing system coordinator.
    
    This is the primary interface for integrating inline editing functionality
    into the document viewer. It coordinates all components and provides a
    unified API for editing operations.
    """
    
    # Signals
    system_state_changed = pyqtSignal(str)  # SystemState
    editor_activated = pyqtSignal(str, object)  # editor_id, element
    editor_deactivated = pyqtSignal(str, bool)  # editor_id, success
    system_metrics_updated = pyqtSignal(object)  # SystemMetrics
    error_occurred = pyqtSignal(str, str)  # error_id, message
    
    def __init__(self, parent_widget: QWidget, config: Optional[SystemConfiguration] = None):
        super().__init__(parent_widget)
        
        self.parent_widget = parent_widget
        self.config = config or SystemConfiguration()
        self.system_state = SystemState.INITIALIZING
        self.system_id = str(uuid.uuid4())
        
        # Core components
        self.integration_manager: Optional[EditorIntegrationManager] = None
        self.accessibility_manager: Optional[AccessibilityManager] = None
        self.error_handler: Optional[EditorErrorHandler] = None
        
        # System management
        self.active_editors: Dict[str, BaseInlineEditor] = {}
        self.editor_registry: Dict[str, type] = {}
        self.system_metrics = SystemMetrics()
        self.status_widget: Optional[SystemStatusWidget] = None
        
        # Performance monitoring
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self._update_system_metrics)
        
        # Auto-save timer
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self._auto_save_editors)
        
        # Health monitoring
        self.health_check_timer = QTimer()
        self.health_check_timer.timeout.connect(self._perform_health_check)
        
        # System initialization
        self._initialize_system()
    
    def _initialize_system(self):
        """Initialize the complete inline editing system."""
        try:
            self._set_system_state(SystemState.INITIALIZING)
            
            # Initialize core components
            self._initialize_error_handling()
            self._initialize_accessibility()
            self._initialize_integration_manager()
            self._initialize_status_widget()
            
            # Setup monitoring
            if self.config.enable_performance_monitoring:
                self._start_performance_monitoring()
            
            # Start auto-save if enabled
            if self.config.auto_save_interval > 0:
                self.auto_save_timer.start(self.config.auto_save_interval * 1000)
            
            # Start health monitoring
            self.health_check_timer.start(30000)  # Every 30 seconds
            
            # Register default editor types
            self._register_default_editors()
            
            self._set_system_state(SystemState.READY)
            logging.info(f"Inline editing system initialized successfully: {self.system_id}")
            
        except Exception as e:
            self._set_system_state(SystemState.ERROR)
            logging.error(f"Failed to initialize inline editing system: {e}")
            if self.error_handler:
                context = ErrorContext(component="InlineEditingSystem", operation="initialize")
                self.error_handler.handle_error(e, None, context)
    
    def _initialize_error_handling(self):
        """Initialize error handling system."""
        if self.config.enable_error_recovery:
            self.error_handler = EditorErrorHandler(self)
            self.error_handler.error_occurred.connect(self._on_system_error)
            self.error_handler.recovery_completed.connect(self._on_recovery_completed)
    
    def _initialize_accessibility(self):
        """Initialize accessibility features."""
        if self.config.enable_accessibility:
            self.accessibility_manager = AccessibilityManager(self)
            # Configure accessibility settings
            settings = self.accessibility_manager.settings
            settings.screen_reader_enabled = self.config.screen_reader_support
            settings.keyboard_navigation_enabled = self.config.keyboard_navigation
            settings.high_contrast_enabled = self.config.high_contrast_mode
    
    def _initialize_integration_manager(self):
        """Initialize integration manager."""
        if self.config.bridge_to_element_list:
            self.integration_manager = EditorIntegrationManager(self.parent_widget, self)
            self.integration_manager.editor_requested.connect(self.create_editor)
            self.integration_manager.editor_closed.connect(self.close_editor)
    
    def _initialize_status_widget(self):
        """Initialize status widget."""
        self.status_widget = SystemStatusWidget()
        self.status_widget.set_system_state(self.system_state)
    
    def _register_default_editors(self):
        """Register default editor types."""
        # This would register all available editor types
        # For now, register the base editor
        self.register_editor_type("text", BaseInlineEditor)
    
    def _set_system_state(self, state: SystemState):
        """Set system state and emit signal."""
        if state != self.system_state:
            self.system_state = state
            self.system_state_changed.emit(state.value)
            if self.status_widget:
                self.status_widget.set_system_state(state)
            logging.debug(f"System state changed to: {state.value}")
    
    def _start_performance_monitoring(self):
        """Start performance monitoring."""
        update_interval = 5000 if self.config.debug_mode else 30000  # 5s debug, 30s normal
        self.performance_timer.start(update_interval)
    
    # Public API Methods
    
    def register_editor_type(self, editor_type: str, editor_class: type):
        """Register an editor type for use with specific elements."""
        self.editor_registry[editor_type] = editor_class
        logging.debug(f"Registered editor type: {editor_type}")
    
    def create_editor(self, element_id: str, element_data: Dict[str, Any], 
                     editor_type: str = "text", position: Optional[QPoint] = None) -> Optional[str]:
        """Create a new inline editor for an element.
        
        Args:
            element_id: Unique identifier for the element
            element_data: Element data including text, metadata, etc.
            editor_type: Type of editor to create
            position: Position for the editor (optional)
            
        Returns:
            Editor ID if successful, None if failed
        """
        try:
            # Check system limits
            if len(self.active_editors) >= self.config.max_concurrent_editors:
                logging.warning("Maximum concurrent editors reached")
                return None
            
            # Check if element is already being edited
            for editor_id, editor in self.active_editors.items():
                if hasattr(editor, 'element_id') and editor.element_id == element_id:
                    logging.warning(f"Element {element_id} is already being edited")
                    return None
            
            # Get editor class
            editor_class = self.editor_registry.get(editor_type, BaseInlineEditor)
            
            # Create editor configuration
            editor_config = EditorConfig(
                auto_save=self.config.auto_save_interval > 0,
                timeout=self.config.editor_timeout,
                enable_accessibility=self.config.enable_accessibility
            )
            
            # Create editor instance
            editor_id = str(uuid.uuid4())
            editor = editor_class(self.parent_widget, editor_config)
            editor.element_id = element_id
            
            # Setup editor
            self._setup_editor(editor, element_data, position)
            
            # Register editor
            self.active_editors[editor_id] = editor
            
            # Update metrics
            self.system_metrics.active_editors = len(self.active_editors)
            self.system_metrics.total_edits_started += 1
            
            # Setup accessibility if enabled
            if self.accessibility_manager:
                self.accessibility_manager.setup_accessibility(editor)
            
            # Take state snapshot for recovery
            if self.error_handler:
                self.error_handler.take_editor_snapshot(editor, editor_id)
            
            # Set system state
            if self.system_state == SystemState.READY:
                self._set_system_state(SystemState.EDITING)
            
            # Emit signal
            self.editor_activated.emit(editor_id, element_data)
            
            logging.debug(f"Created editor {editor_id} for element {element_id}")
            return editor_id
            
        except Exception as e:
            logging.error(f"Failed to create editor: {e}")
            if self.error_handler:
                context = ErrorContext(
                    component="InlineEditingSystem",
                    operation="create_editor",
                    user_data={"element_id": element_id, "editor_type": editor_type}
                )
                self.error_handler.handle_error(e, None, context)
            return None
    
    def _setup_editor(self, editor: BaseInlineEditor, element_data: Dict[str, Any], 
                     position: Optional[QPoint]):
        """Setup editor with element data and positioning."""
        # Set element data
        if hasattr(editor, 'set_element_data'):
            editor.set_element_data(element_data)
        
        # Set position if provided
        if position and hasattr(editor, 'move'):
            editor.move(position)
        
        # Connect editor signals
        editor.editing_finished.connect(
            lambda success: self._on_editor_finished(editor, success)
        )
        editor.editing_cancelled.connect(
            lambda: self._on_editor_cancelled(editor)
        )
        
        if hasattr(editor, 'content_changed'):
            editor.content_changed.connect(
                lambda: self._on_editor_content_changed(editor)
            )
    
    def close_editor(self, editor_id: str, save_changes: bool = True) -> bool:
        """Close an active editor.
        
        Args:
            editor_id: ID of the editor to close
            save_changes: Whether to save changes before closing
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if editor_id not in self.active_editors:
                logging.warning(f"Editor {editor_id} not found")
                return False
            
            editor = self.active_editors[editor_id]
            
            # Save changes if requested
            if save_changes and hasattr(editor, 'save'):
                try:
                    editor.save()
                except Exception as e:
                    logging.error(f"Failed to save editor changes: {e}")
                    if self.error_handler:
                        context = ErrorContext(
                            component="InlineEditingSystem",
                            operation="save_editor",
                            user_data={"editor_id": editor_id}
                        )
                        self.error_handler.handle_error(e, editor, context)
            
            # Close editor
            if hasattr(editor, 'close'):
                editor.close()
            
            # Remove from active editors
            del self.active_editors[editor_id]
            
            # Update metrics
            self.system_metrics.active_editors = len(self.active_editors)
            if save_changes:
                self.system_metrics.total_edits_completed += 1
            else:
                self.system_metrics.total_edits_cancelled += 1
            
            # Update system state
            if len(self.active_editors) == 0 and self.system_state == SystemState.EDITING:
                self._set_system_state(SystemState.READY)
            
            # Emit signal
            self.editor_deactivated.emit(editor_id, save_changes)
            
            logging.debug(f"Closed editor {editor_id}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to close editor {editor_id}: {e}")
            if self.error_handler:
                context = ErrorContext(
                    component="InlineEditingSystem",
                    operation="close_editor",
                    user_data={"editor_id": editor_id}
                )
                self.error_handler.handle_error(e, None, context)
            return False
    
    def close_all_editors(self, save_changes: bool = True):
        """Close all active editors."""
        editor_ids = list(self.active_editors.keys())
        for editor_id in editor_ids:
            self.close_editor(editor_id, save_changes)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            'system_id': self.system_id,
            'state': self.system_state.value,
            'active_editors': len(self.active_editors),
            'registered_editor_types': list(self.editor_registry.keys()),
            'configuration': self.config.__dict__,
            'metrics': self.system_metrics.__dict__,
            'components': {
                'error_handler': self.error_handler is not None,
                'accessibility_manager': self.accessibility_manager is not None,
                'integration_manager': self.integration_manager is not None,
                'status_widget': self.status_widget is not None
            }
        }
    
    def get_status_widget(self) -> Optional[SystemStatusWidget]:
        """Get the system status widget for UI integration."""
        return self.status_widget
    
    def shutdown(self):
        """Shutdown the inline editing system."""
        try:
            self._set_system_state(SystemState.SHUTDOWN)
            
            # Close all editors
            self.close_all_editors(save_changes=True)
            
            # Stop timers
            self.performance_timer.stop()
            self.auto_save_timer.stop()
            self.health_check_timer.stop()
            
            # Cleanup components
            if self.accessibility_manager:
                # Cleanup accessibility manager
                pass
            
            if self.error_handler:
                # Cleanup error handler
                pass
            
            if self.integration_manager:
                # Cleanup integration manager
                pass
            
            logging.info(f"Inline editing system shutdown complete: {self.system_id}")
            
        except Exception as e:
            logging.error(f"Error during system shutdown: {e}")
    
    # Event Handlers
    
    def _on_editor_finished(self, editor: BaseInlineEditor, success: bool):
        """Handle editor finished event."""
        editor_id = None
        for eid, e in self.active_editors.items():
            if e == editor:
                editor_id = eid
                break
        
        if editor_id:
            self.close_editor(editor_id, success)
    
    def _on_editor_cancelled(self, editor: BaseInlineEditor):
        """Handle editor cancelled event."""
        self._on_editor_finished(editor, False)
    
    def _on_editor_content_changed(self, editor: BaseInlineEditor):
        """Handle editor content changed event."""
        # Update metrics or perform auto-save logic
        pass
    
    def _on_system_error(self, error_record):
        """Handle system error event."""
        self.system_metrics.total_errors += 1
        if error_record.context.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
            self.system_metrics.critical_errors += 1
        
        self.error_occurred.emit(error_record.context.error_id, error_record.user_message)
    
    def _on_recovery_completed(self, error_id: str, successful: bool):
        """Handle recovery completed event."""
        if successful:
            self.system_metrics.errors_recovered += 1
        
        # Update recovery success rate
        total_recoveries = self.system_metrics.errors_recovered
        if self.system_metrics.total_errors > 0:
            self.system_metrics.recovery_success_rate = (total_recoveries / self.system_metrics.total_errors) * 100
    
    # Background Tasks
    
    def _update_system_metrics(self):
        """Update system performance metrics."""
        try:
            # Update basic metrics
            self.system_metrics.active_editors = len(self.active_editors)
            self.system_metrics.uptime_seconds = time.time() - self.system_metrics.last_health_check
            
            # Calculate system health score
            health_factors = []
            
            # Factor 1: Error rate (lower is better)
            if self.system_metrics.total_edits_started > 0:
                error_rate = (self.system_metrics.total_errors / self.system_metrics.total_edits_started) * 100
                health_factors.append(max(0, 100 - error_rate))
            else:
                health_factors.append(100)
            
            # Factor 2: Recovery success rate
            health_factors.append(self.system_metrics.recovery_success_rate)
            
            # Factor 3: Component availability
            components_active = sum([
                self.error_handler is not None,
                self.accessibility_manager is not None,
                self.integration_manager is not None
            ])
            component_health = (components_active / 3) * 100
            health_factors.append(component_health)
            
            # Calculate overall health
            self.system_metrics.system_health_score = sum(health_factors) / len(health_factors)
            
            # Emit metrics update
            self.system_metrics_updated.emit(self.system_metrics)
            
            # Update status widget
            if self.status_widget:
                self.status_widget.update_metrics(self.system_metrics)
            
        except Exception as e:
            logging.error(f"Failed to update system metrics: {e}")
    
    def _auto_save_editors(self):
        """Auto-save all active editors."""
        if not self.config.auto_save_interval:
            return
        
        for editor_id, editor in self.active_editors.items():
            try:
                if hasattr(editor, 'is_dirty') and editor.is_dirty():
                    if hasattr(editor, 'save'):
                        editor.save()
                        logging.debug(f"Auto-saved editor {editor_id}")
            except Exception as e:
                logging.error(f"Auto-save failed for editor {editor_id}: {e}")
                if self.error_handler:
                    context = ErrorContext(
                        component="InlineEditingSystem",
                        operation="auto_save",
                        user_data={"editor_id": editor_id}
                    )
                    self.error_handler.handle_error(e, editor, context)
    
    def _perform_health_check(self):
        """Perform system health check."""
        try:
            self.system_metrics.last_health_check = time.time()
            
            # Check component health
            if self.error_handler:
                error_stats = self.error_handler.get_error_statistics()
                system_health = error_stats.get('system_health', {})
                if system_health.get('overall_health', 0) < 70:
                    logging.warning("System health below 70%")
            
            # Check memory usage (simplified)
            active_editor_count = len(self.active_editors)
            if active_editor_count > self.config.max_concurrent_editors * 0.8:
                logging.warning(f"High editor usage: {active_editor_count}/{self.config.max_concurrent_editors}")
            
            # Check for stale editors
            current_time = time.time()
            for editor_id, editor in list(self.active_editors.items()):
                if hasattr(editor, 'created_at'):
                    age = current_time - editor.created_at
                    if age > self.config.editor_timeout:
                        logging.warning(f"Editor {editor_id} exceeded timeout, closing")
                        self.close_editor(editor_id, save_changes=True)
            
        except Exception as e:
            logging.error(f"Health check failed: {e}")


# Factory function for easy system creation
def create_inline_editing_system(parent_widget: QWidget, 
                                config: Optional[SystemConfiguration] = None) -> InlineEditingSystem:
    """Factory function to create and initialize the inline editing system.
    
    Args:
        parent_widget: Parent widget for the editing system
        config: Optional configuration (uses defaults if not provided)
        
    Returns:
        Configured and initialized InlineEditingSystem instance
    """
    system = InlineEditingSystem(parent_widget, config)
    return system


# Export public API
__all__ = [
    'InlineEditingSystem',
    'SystemConfiguration',
    'SystemMetrics',
    'SystemState',
    'SystemStatusWidget',
    'create_inline_editing_system'
]