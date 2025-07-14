"""
UI Integration Utilities for Reactive Components.
This module provides seamless integration between reactive components and existing
PyQt6 UI framework components, enabling gradual migration and interoperability.
"""
from __future__ import annotations

import weakref
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union
from functools import wraps

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QEvent
from PyQt6.QtWidgets import (
    QWidget, QMainWindow, QDialog, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QFormLayout, QStackedWidget, QTabWidget,
    QSplitter, QScrollArea, QFrame, QGroupBox
)

from .reactive import ReactiveWidget
from .mixins import AsyncMixin, LoadingStateMixin
from .boundaries import ErrorBoundary, GlobalErrorBoundary
from .monitoring import PerformanceMonitor
from ..state.manager import StateManager


T = TypeVar('T', bound=QWidget)


class IntegrationSignals(QObject):
    """Signals for integration events."""
    component_integrated = pyqtSignal(object)  # QWidget
    component_removed = pyqtSignal(object)  # QWidget
    layout_changed = pyqtSignal(object)  # QWidget
    migration_completed = pyqtSignal(object)  # QWidget


class ReactiveContainer(QWidget):
    """Container that provides reactive capabilities to non-reactive widgets."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.signals = IntegrationSignals()
        self.child_components: Dict[str, QWidget] = {}
        self.reactive_wrappers: Dict[QWidget, ReactiveWrapper] = {}
        self.state_bindings: Dict[str, List[Callable]] = {}
        self.monitor = PerformanceMonitor()
        
        # Initialize state management
        self.state_manager = StateManager()
        
        # Setup error boundary
        self.error_boundary = ErrorBoundary(self)
        
        # Setup layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
    
    def add_component(self, component: QWidget, name: str = None, reactive: bool = True) -> str:
        """Add a component to the container."""
        if name is None:
            name = f"component_{len(self.child_components)}"
        
        # Store component
        self.child_components[name] = component
        
        # Make reactive if requested
        if reactive and not isinstance(component, ReactiveWidget):
            wrapper = ReactiveWrapper(component)
            self.reactive_wrappers[component] = wrapper
        
        # Add to layout
        self.main_layout.addWidget(component)
        
        # Register with error boundary
        if hasattr(component, 'error_boundary'):
            component.error_boundary.signals.error_caught.connect(
                self.error_boundary.handle_error
            )
        
        # Emit signal
        self.signals.component_integrated.emit(component)
        
        return name
    
    def remove_component(self, name: str):
        """Remove a component from the container."""
        if name in self.child_components:
            component = self.child_components[name]
            
            # Remove from layout
            self.main_layout.removeWidget(component)
            
            # Cleanup reactive wrapper
            if component in self.reactive_wrappers:
                wrapper = self.reactive_wrappers[component]
                wrapper.cleanup()
                del self.reactive_wrappers[component]
            
            # Remove from storage
            del self.child_components[name]
            
            # Emit signal
            self.signals.component_removed.emit(component)
    
    def get_component(self, name: str) -> Optional[QWidget]:
        """Get a component by name."""
        return self.child_components.get(name)
    
    def bind_state(self, component_name: str, state_key: str, callback: Callable[[Any], None]):
        """Bind a state change to a component callback."""
        if state_key not in self.state_bindings:
            self.state_bindings[state_key] = []
        
        self.state_bindings[state_key].append(callback)
        
        # Connect to state manager
        self.state_manager.subscribe(state_key, callback)
    
    def update_state(self, state_key: str, value: Any):
        """Update state and notify bound components."""
        self.state_manager.set_state(state_key, value)


class ReactiveWrapper:
    """Wrapper that adds reactive capabilities to existing widgets."""
    
    def __init__(self, widget: QWidget):
        self.widget = widget
        self.signals = IntegrationSignals()
        self.state_subscriptions: Dict[str, List[Callable]] = {}
        self.property_bindings: Dict[str, str] = {}
        self.event_handlers: Dict[str, Callable] = {}
        self.monitor = PerformanceMonitor()
        
        # Setup error boundary
        self.error_boundary = ErrorBoundary(widget)
        
        # Setup state management
        self.state_manager = StateManager()
        
        # Install event filter
        self.widget.installEventFilter(self)
        
        # Wrap common methods
        self._wrap_methods()
    
    def _wrap_methods(self):
        """Wrap widget methods to add reactive behavior."""
        methods_to_wrap = [
            'setVisible', 'setEnabled', 'setText', 'setValue',
            'setStyleSheet', 'setToolTip', 'setWhatsThis'
        ]
        
        for method_name in methods_to_wrap:
            if hasattr(self.widget, method_name):
                original_method = getattr(self.widget, method_name)
                wrapped_method = self._wrap_method(original_method, method_name)
                setattr(self.widget, method_name, wrapped_method)
    
    def _wrap_method(self, method: Callable, method_name: str):
        """Wrap a method to add reactive behavior."""
        @wraps(method)
        def wrapper(*args, **kwargs):
            try:
                # Record performance
                start_time = self.monitor.current_time()
                
                # Call original method
                result = method(*args, **kwargs)
                
                # Record performance
                end_time = self.monitor.current_time()
                self.monitor.record_method_call(
                    method_name, 
                    end_time - start_time,
                    success=True
                )
                
                # Trigger state update if bound
                if method_name in self.property_bindings:
                    state_key = self.property_bindings[method_name]
                    if args:
                        self.state_manager.set_state(state_key, args[0])
                
                return result
                
            except Exception as e:
                # Record error
                self.monitor.record_method_call(
                    method_name,
                    0,
                    success=False
                )
                
                # Handle through error boundary
                self.error_boundary.handle_error(e, {
                    'method': method_name,
                    'args': args,
                    'kwargs': kwargs
                })
                
                raise
        
        return wrapper
    
    def bind_property(self, property_name: str, state_key: str):
        """Bind a widget property to a state key."""
        self.property_bindings[property_name] = state_key
        
        # Subscribe to state changes
        self.state_manager.subscribe(state_key, 
            lambda value: self._update_property(property_name, value))
    
    def _update_property(self, property_name: str, value: Any):
        """Update a widget property."""
        if property_name == 'text' and hasattr(self.widget, 'setText'):
            self.widget.setText(str(value))
        elif property_name == 'value' and hasattr(self.widget, 'setValue'):
            self.widget.setValue(value)
        elif property_name == 'visible' and hasattr(self.widget, 'setVisible'):
            self.widget.setVisible(bool(value))
        elif property_name == 'enabled' and hasattr(self.widget, 'setEnabled'):
            self.widget.setEnabled(bool(value))
        elif property_name == 'styleSheet' and hasattr(self.widget, 'setStyleSheet'):
            self.widget.setStyleSheet(str(value))
    
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter events to add reactive behavior."""
        if obj == self.widget:
            event_type = event.type()
            
            # Handle common events
            if event_type in self.event_handlers:
                try:
                    handler = self.event_handlers[event_type]
                    handler(event)
                except Exception as e:
                    self.error_boundary.handle_error(e, {
                        'event_type': event_type,
                        'event': event
                    })
        
        return False
    
    def add_event_handler(self, event_type: QEvent.Type, handler: Callable[[QEvent], None]):
        """Add an event handler."""
        self.event_handlers[event_type] = handler
    
    def cleanup(self):
        """Cleanup the wrapper."""
        # Remove event filter
        if self.widget:
            self.widget.removeEventFilter(self)
        
        # Clear subscriptions
        for state_key, callbacks in self.state_subscriptions.items():
            for callback in callbacks:
                self.state_manager.unsubscribe(state_key, callback)
        
        # Clear references
        self.state_subscriptions.clear()
        self.property_bindings.clear()
        self.event_handlers.clear()


class MainWindowIntegration:
    """Integration utilities for main window and reactive components."""
    
    def __init__(self, main_window: QMainWindow):
        self.main_window = main_window
        self.signals = IntegrationSignals()
        self.reactive_areas: Dict[str, ReactiveContainer] = {}
        self.menu_integrations: Dict[str, Callable] = {}
        self.toolbar_integrations: Dict[str, Callable] = {}
        self.status_bar_integrations: Dict[str, Callable] = {}
        self.monitor = PerformanceMonitor()
        
        # Setup global error boundary
        self.global_boundary = GlobalErrorBoundary()
        
        # Setup state management
        self.state_manager = StateManager()
    
    def create_reactive_area(self, name: str, parent: QWidget = None) -> ReactiveContainer:
        """Create a reactive area in the main window."""
        if parent is None:
            parent = self.main_window.centralWidget()
        
        container = ReactiveContainer(parent)
        self.reactive_areas[name] = container
        
        # Connect to global error boundary
        container.error_boundary.signals.error_caught.connect(
            self.global_boundary.handle_global_error
        )
        
        return container
    
    def integrate_menu_action(self, action_name: str, callback: Callable):
        """Integrate a menu action with reactive components."""
        self.menu_integrations[action_name] = callback
        
        # Find and connect menu action
        for action in self.main_window.menuBar().actions():
            if action.text() == action_name or action.objectName() == action_name:
                action.triggered.connect(callback)
                break
    
    def integrate_toolbar_action(self, action_name: str, callback: Callable):
        """Integrate a toolbar action with reactive components."""
        self.toolbar_integrations[action_name] = callback
        
        # Find and connect toolbar action
        for toolbar in self.main_window.findChildren(QWidget):
            if hasattr(toolbar, 'actions'):
                for action in toolbar.actions():
                    if action.text() == action_name or action.objectName() == action_name:
                        action.triggered.connect(callback)
                        break
    
    def integrate_status_bar(self, callback: Callable):
        """Integrate status bar with reactive components."""
        if self.main_window.statusBar():
            self.status_bar_integrations['default'] = callback
    
    def get_reactive_area(self, name: str) -> Optional[ReactiveContainer]:
        """Get a reactive area by name."""
        return self.reactive_areas.get(name)
    
    def broadcast_state_change(self, state_key: str, value: Any):
        """Broadcast state change to all reactive areas."""
        self.state_manager.set_state(state_key, value)
        
        # Notify all reactive areas
        for area in self.reactive_areas.values():
            area.update_state(state_key, value)


class LayoutIntegration:
    """Integration utilities for layouts and reactive components."""
    
    @staticmethod
    def convert_layout_to_reactive(layout: QWidget) -> ReactiveContainer:
        """Convert a traditional layout to a reactive container."""
        container = ReactiveContainer()
        
        # Copy layout properties
        if hasattr(layout, 'layout') and layout.layout():
            original_layout = layout.layout()
            
            # Move all widgets to reactive container
            while original_layout.count():
                item = original_layout.takeAt(0)
                if item.widget():
                    container.add_component(item.widget())
        
        return container
    
    @staticmethod
    def create_responsive_layout(components: List[QWidget]) -> QWidget:
        """Create a responsive layout for components."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Create reactive container for each component
        for component in components:
            reactive_container = ReactiveContainer()
            reactive_container.add_component(component)
            layout.addWidget(reactive_container)
        
        return container


class MigrationHelper:
    """Helper utilities for migrating existing components to reactive."""
    
    @staticmethod
    def migrate_widget_to_reactive(widget: QWidget) -> ReactiveWidget:
        """Migrate a widget to reactive widget."""
        # Create reactive widget with same properties
        reactive_widget = ReactiveWidget(widget.parent())
        
        # Copy properties
        reactive_widget.setObjectName(widget.objectName())
        reactive_widget.setGeometry(widget.geometry())
        reactive_widget.setVisible(widget.isVisible())
        reactive_widget.setEnabled(widget.isEnabled())
        reactive_widget.setStyleSheet(widget.styleSheet())
        reactive_widget.setToolTip(widget.toolTip())
        reactive_widget.setWhatsThis(widget.whatsThis())
        
        # Copy layout if exists
        if widget.layout():
            reactive_widget.setLayout(widget.layout())
        
        # Replace in parent
        if widget.parent():
            parent = widget.parent()
            if hasattr(parent, 'layout') and parent.layout():
                parent.layout().replaceWidget(widget, reactive_widget)
        
        return reactive_widget
    
    @staticmethod
    def create_migration_plan(root_widget: QWidget) -> Dict[str, Any]:
        """Create a migration plan for converting widgets to reactive."""
        plan = {
            'widgets_to_migrate': [],
            'reactive_candidates': [],
            'integration_points': [],
            'estimated_effort': 0
        }
        
        # Analyze widget tree
        def analyze_widget(widget: QWidget, depth: int = 0):
            info = {
                'widget': widget,
                'type': widget.__class__.__name__,
                'depth': depth,
                'children': [],
                'is_reactive_candidate': MigrationHelper._is_reactive_candidate(widget)
            }
            
            if info['is_reactive_candidate']:
                plan['reactive_candidates'].append(info)
            
            # Analyze children
            for child in widget.findChildren(QWidget, options=widget.FindDirectChildrenOnly):
                child_info = analyze_widget(child, depth + 1)
                info['children'].append(child_info)
            
            return info
        
        # Analyze from root
        analyze_widget(root_widget)
        
        # Calculate estimated effort
        plan['estimated_effort'] = len(plan['reactive_candidates']) * 2  # 2 hours per component
        
        return plan
    
    @staticmethod
    def _is_reactive_candidate(widget: QWidget) -> bool:
        """Check if a widget is a good candidate for reactive conversion."""
        # Widgets with complex state management
        if hasattr(widget, 'state') or hasattr(widget, 'data'):
            return True
        
        # Widgets with many event handlers
        if len(widget.findChildren(QWidget)) > 5:
            return True
        
        # Custom widgets
        if widget.__class__.__module__ != 'PyQt6.QtWidgets':
            return True
        
        return False


def reactive_integration(auto_migrate: bool = False):
    """Decorator to add reactive integration to existing widgets."""
    def decorator(widget_class: Type[QWidget]):
        
        class ReactiveIntegratedWidget(widget_class):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                
                # Add reactive wrapper
                self.reactive_wrapper = ReactiveWrapper(self)
                
                # Add integration signals
                self.integration_signals = IntegrationSignals()
                
                # Auto-migrate if requested
                if auto_migrate:
                    self._auto_migrate()
            
            def _auto_migrate(self):
                """Automatically migrate to reactive patterns."""
                # Add error boundary
                self.error_boundary = ErrorBoundary(self)
                
                # Add state management
                self.state_manager = StateManager()
                
                # Connect common signals to state updates
                if hasattr(self, 'clicked'):
                    self.clicked.connect(lambda: self.state_manager.set_state('clicked', True))
                
                if hasattr(self, 'textChanged'):
                    self.textChanged.connect(lambda text: self.state_manager.set_state('text', text))
                
                if hasattr(self, 'valueChanged'):
                    self.valueChanged.connect(lambda value: self.state_manager.set_state('value', value))
        
        return ReactiveIntegratedWidget
    
    return decorator


class AsyncIntegration:
    """Integration utilities for async operations in main window."""
    
    def __init__(self, main_window: QMainWindow):
        self.main_window = main_window
        self.async_components: Dict[str, AsyncMixin] = {}
        self.global_loading_state = False
        self.monitor = PerformanceMonitor()
    
    def register_async_component(self, name: str, component: AsyncMixin):
        """Register an async component."""
        self.async_components[name] = component
        
        # Connect to global loading state
        component.async_signals.operation_started.connect(
            lambda op: self._update_global_loading_state()
        )
        component.async_signals.operation_completed.connect(
            lambda op, result: self._update_global_loading_state()
        )
        component.async_signals.operation_failed.connect(
            lambda op, error: self._update_global_loading_state()
        )
    
    def _update_global_loading_state(self):
        """Update global loading state based on all components."""
        is_loading = any(
            comp.is_loading() for comp in self.async_components.values()
        )
        
        if is_loading != self.global_loading_state:
            self.global_loading_state = is_loading
            self._update_main_window_loading_state(is_loading)
    
    def _update_main_window_loading_state(self, is_loading: bool):
        """Update main window loading state."""
        # Update cursor
        if is_loading:
            self.main_window.setCursor(Qt.CursorShape.WaitCursor)
        else:
            self.main_window.unsetCursor()
        
        # Update status bar
        if self.main_window.statusBar():
            if is_loading:
                self.main_window.statusBar().showMessage("Loading...")
            else:
                self.main_window.statusBar().clearMessage()
    
    def cancel_all_operations(self):
        """Cancel all async operations."""
        for component in self.async_components.values():
            component.cancel_all_operations()


# Global integration instance
_global_integration = None


def get_global_integration() -> Optional[MainWindowIntegration]:
    """Get the global integration instance."""
    return _global_integration


def set_global_integration(integration: MainWindowIntegration):
    """Set the global integration instance."""
    global _global_integration
    _global_integration = integration