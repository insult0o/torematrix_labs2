"""Complete inline editing system integration

Brings together all inline editing components into a unified system with
configuration management, monitoring, and production-ready deployment.
"""

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
import time

try:
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer
except ImportError:
    # Mock classes for environments without PyQt6
    class QWidget:
        def __init__(self, parent=None):
            pass
        def setLayout(self, layout): pass
        
    class QVBoxLayout:
        def __init__(self): pass
        def addWidget(self, widget): pass
        
    class QHBoxLayout:
        def __init__(self): pass
        def addWidget(self, widget): pass
        
    class QLabel:
        def __init__(self, text=""): pass
        def setText(self, text): pass
        
    class QPushButton:
        def __init__(self, text=""): pass
        def clicked(self): return lambda: None
        
    class QObject:
        def __init__(self, parent=None):
            pass
            
    class QTimer:
        def __init__(self):
            pass
        def start(self, ms): pass
        def stop(self): pass
        def timeout(self): return lambda: None
            
    def pyqtSignal(*args):
        return lambda: None

from .base import BaseEditor, EditorConfig
from .integration import ElementEditorBridge
from .accessibility import AccessibilityManager
from .recovery import EditorErrorHandler


@dataclass
class SystemConfiguration:
    """Configuration for the complete inline editing system"""
    # Editor behavior
    auto_commit_enabled: bool = False
    auto_commit_delay: int = 1000  # milliseconds
    multi_edit_enabled: bool = True
    undo_levels: int = 50
    
    # Performance settings
    max_concurrent_editors: int = 10
    editor_pool_size: int = 20
    cache_editor_instances: bool = True
    lazy_editor_creation: bool = True
    
    # UI settings
    show_validation_indicators: bool = True
    highlight_active_editors: bool = True
    show_editor_tooltips: bool = True
    animation_duration: int = 200
    
    # Accessibility
    accessibility_enabled: bool = True
    screen_reader_support: bool = True
    keyboard_navigation_enhanced: bool = True
    high_contrast_support: bool = True
    
    # Error handling
    error_recovery_enabled: bool = True
    show_error_notifications: bool = True
    auto_retry_on_failure: bool = True
    max_retry_attempts: int = 3
    
    # Monitoring
    performance_monitoring: bool = True
    usage_analytics: bool = False
    debug_logging: bool = False
    
    # Persistence
    save_editor_preferences: bool = True
    restore_editor_state: bool = True
    backup_unsaved_changes: bool = True


@dataclass
class SystemMetrics:
    """System performance and usage metrics"""
    active_editors_count: int = 0
    total_edits_started: int = 0
    total_edits_completed: int = 0
    total_edits_cancelled: int = 0
    total_errors: int = 0
    average_edit_duration: float = 0.0
    peak_concurrent_editors: int = 0
    memory_usage_mb: float = 0.0
    
    def success_rate(self) -> float:
        """Calculate edit success rate"""
        total = self.total_edits_completed + self.total_edits_cancelled
        return (self.total_edits_completed / total) if total > 0 else 0.0


class SystemStatusWidget(QWidget):
    """Widget for displaying system status and metrics"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the status widget UI"""
        layout = QVBoxLayout()
        
        # Status labels
        self.active_editors_label = QLabel("Active Editors: 0")
        self.success_rate_label = QLabel("Success Rate: 0%")
        self.error_count_label = QLabel("Errors: 0")
        
        layout.addWidget(self.active_editors_label)
        layout.addWidget(self.success_rate_label)
        layout.addWidget(self.error_count_label)
        
        self.setLayout(layout)
        
    def update_metrics(self, metrics: SystemMetrics):
        """Update displayed metrics"""
        try:
            self.active_editors_label.setText(f"Active Editors: {metrics.active_editors_count}")
            self.success_rate_label.setText(f"Success Rate: {metrics.success_rate():.1%}")
            self.error_count_label.setText(f"Errors: {metrics.total_errors}")
        except:
            pass  # Graceful degradation if widgets not available


class InlineEditingSystem(QObject):
    """Complete inline editing system with full integration"""
    
    # Signals
    system_state_changed = pyqtSignal(str)  # state name
    editor_activated = pyqtSignal(str, object)  # element_id, editor
    editor_deactivated = pyqtSignal(str)  # element_id
    system_metrics_updated = pyqtSignal(object)  # SystemMetrics
    
    def __init__(self, parent=None, config: Optional[SystemConfiguration] = None):
        super().__init__(parent)
        
        self.config = config or SystemConfiguration()
        self.metrics = SystemMetrics()
        
        # Core components
        self.editor_bridge = ElementEditorBridge(self)
        self.accessibility_manager = AccessibilityManager(self)
        self.error_handler = EditorErrorHandler(self)
        
        # Editor management
        self.active_editors: Dict[str, BaseEditor] = {}
        self.editor_pool: List[BaseEditor] = []
        self.editor_factory: Optional[Callable] = None
        
        # Performance monitoring
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self._update_metrics)
        
        # Status widget
        self.status_widget = SystemStatusWidget()
        
        # Setup system
        self._setup_system()
        
    def _setup_system(self):
        """Setup the complete system"""
        # Configure editor bridge
        self.editor_bridge.set_editor_factory(self._create_editor_with_error_handling)
        
        # Connect signals
        self.editor_bridge.edit_started.connect(self._on_editor_started)
        self.editor_bridge.edit_completed.connect(self._on_editor_completed)
        self.editor_bridge.edit_cancelled.connect(self._on_editor_cancelled)
        
        self.error_handler.error_occurred.connect(self._on_error_occurred)
        
        # Start monitoring if enabled
        if self.config.performance_monitoring:
            self.performance_timer.start(5000)  # Update every 5 seconds
            
        self.system_state_changed.emit("initialized")
        
    def set_editor_factory(self, factory: Callable):
        """Set the editor factory function"""
        self.editor_factory = factory
        
    def request_edit(self, element_id: str, element_type: str, current_value: Any = None,
                    position: tuple[int, int] = (0, 0), parent_widget: QWidget = None,
                    config: EditorConfig = None) -> bool:
        """Request editing for an element"""
        if len(self.active_editors) >= self.config.max_concurrent_editors:
            return False
            
        return self.editor_bridge.request_edit(
            element_id, element_type, current_value, position, parent_widget, config
        )
        
    def cancel_edit(self, element_id: str) -> bool:
        """Cancel editing for specific element"""
        return self.editor_bridge.cancel_edit(element_id)
        
    def cancel_all_edits(self):
        """Cancel all active edits"""
        self.editor_bridge.cancel_all_edits()
        
    def save_all_edits(self) -> Dict[str, bool]:
        """Save all active edits"""
        return self.editor_bridge.save_all_edits()
        
    def get_active_editor(self, element_id: str) -> Optional[BaseEditor]:
        """Get active editor for element"""
        return self.editor_bridge.get_active_editor(element_id)
        
    def is_editing(self, element_id: str) -> bool:
        """Check if element is being edited"""
        return self.editor_bridge.is_editing(element_id)
        
    def _create_editor_with_error_handling(self, element_id: str, element_type: str, 
                                         parent: QWidget, config: EditorConfig) -> Optional[BaseEditor]:
        """Create editor with error handling wrapper"""
        try:
            if not self.editor_factory:
                return None
                
            # Try to get from pool first
            if self.config.cache_editor_instances and self.editor_pool:
                editor = self.editor_pool.pop()
                # Reconfigure for new use
                if hasattr(editor, 'reconfigure'):
                    editor.reconfigure(element_type, config)
                return editor
                
            # Create new editor
            editor = self.editor_factory(element_id, element_type, parent, config)
            
            if editor and self.config.accessibility_enabled:
                self.accessibility_manager.setup_accessibility(editor)
                
            return editor
            
        except Exception as e:
            context = {
                'element_id': element_id,
                'element_type': element_type,
                'operation': 'create_editor'
            }
            self.error_handler.handle_error(e, 'editor_factory', context)
            return None
            
    def _on_editor_started(self, element_id: str, editor: BaseEditor):
        """Handle editor started"""
        self.active_editors[element_id] = editor
        self.metrics.active_editors_count = len(self.active_editors)
        self.metrics.total_edits_started += 1
        
        # Update peak concurrent editors
        if self.metrics.active_editors_count > self.metrics.peak_concurrent_editors:
            self.metrics.peak_concurrent_editors = self.metrics.active_editors_count
            
        self.editor_activated.emit(element_id, editor)
        
    def _on_editor_completed(self, element_id: str, value: Any, success: bool):
        """Handle editor completed"""
        if element_id in self.active_editors:
            editor = self.active_editors.pop(element_id)
            
            # Return to pool if configured
            if self.config.cache_editor_instances and len(self.editor_pool) < self.config.editor_pool_size:
                if hasattr(editor, 'reset_for_pool'):
                    editor.reset_for_pool()
                self.editor_pool.append(editor)
                
        self.metrics.active_editors_count = len(self.active_editors)
        
        if success:
            self.metrics.total_edits_completed += 1
        else:
            self.metrics.total_edits_cancelled += 1
            
        self.editor_deactivated.emit(element_id)
        
    def _on_editor_cancelled(self, element_id: str):
        """Handle editor cancelled"""
        if element_id in self.active_editors:
            self.active_editors.pop(element_id)
            
        self.metrics.active_editors_count = len(self.active_editors)
        self.metrics.total_edits_cancelled += 1
        self.editor_deactivated.emit(element_id)
        
    def _on_error_occurred(self, error_record):
        """Handle error occurrence"""
        self.metrics.total_errors += 1
        
    def _update_metrics(self):
        """Update system metrics"""
        try:
            import psutil
            import os
            
            # Get memory usage
            process = psutil.Process(os.getpid())
            self.metrics.memory_usage_mb = process.memory_info().rss / 1024 / 1024
            
        except ImportError:
            # psutil not available
            pass
            
        # Emit updated metrics
        self.system_metrics_updated.emit(self.metrics)
        self.status_widget.update_metrics(self.metrics)
        
    # Configuration management
    
    def update_configuration(self, new_config: SystemConfiguration):
        """Update system configuration"""
        old_config = self.config
        self.config = new_config
        
        # Apply configuration changes
        if old_config.performance_monitoring != new_config.performance_monitoring:
            if new_config.performance_monitoring:
                self.performance_timer.start(5000)
            else:
                self.performance_timer.stop()
                
        # Update accessibility
        if old_config.accessibility_enabled != new_config.accessibility_enabled:
            # Reconfigure accessibility for all active editors
            for editor in self.active_editors.values():
                if new_config.accessibility_enabled:
                    self.accessibility_manager.setup_accessibility(editor)
                else:
                    self.accessibility_manager.remove_widget(editor)
                    
        self.system_state_changed.emit("configuration_updated")
        
    def get_configuration(self) -> SystemConfiguration:
        """Get current system configuration"""
        return self.config
        
    def get_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        return self.metrics
        
    def get_status_widget(self) -> SystemStatusWidget:
        """Get status widget for embedding in UI"""
        return self.status_widget
        
    def reset_metrics(self):
        """Reset system metrics"""
        self.metrics = SystemMetrics()
        self.metrics.active_editors_count = len(self.active_editors)
        
    def shutdown(self):
        """Shutdown the system gracefully"""
        self.system_state_changed.emit("shutting_down")
        
        # Cancel all active edits
        self.cancel_all_edits()
        
        # Stop monitoring
        if self.performance_timer.isActive():
            self.performance_timer.stop()
            
        # Clear editor pool
        self.editor_pool.clear()
        
        self.system_state_changed.emit("shutdown_complete")
        
    # Diagnostics and debugging
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'configuration': self.config.__dict__,
            'metrics': self.metrics.__dict__,
            'active_editors': list(self.active_editors.keys()),
            'editor_pool_size': len(self.editor_pool),
            'accessibility_enabled': self.config.accessibility_enabled,
            'error_handler_stats': self.error_handler.get_error_statistics(),
            'bridge_stats': self.editor_bridge.get_edit_statistics()
        }
        
    def export_diagnostics(self) -> Dict[str, Any]:
        """Export diagnostic information"""
        return {
            'timestamp': time.time(),
            'system_status': self.get_system_status(),
            'component_versions': {
                'editor_bridge': '1.0.0',
                'accessibility_manager': '1.0.0', 
                'error_handler': '1.0.0'
            }
        }


# Factory function for easy system creation
def create_inline_editing_system(parent=None, config=None) -> InlineEditingSystem:
    """Create a fully configured inline editing system"""
    return InlineEditingSystem(parent, config)


# Export public API
__all__ = [
    'InlineEditingSystem',
    'SystemConfiguration',
    'SystemMetrics',
    'SystemStatusWidget',
    'create_inline_editing_system'
]