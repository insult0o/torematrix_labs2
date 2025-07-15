"""Property panel integration with main application workspace"""

from typing import Dict, List, Optional, Any, Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QDockWidget, QSplitter,
    QTabWidget, QToolBar, QMenu, QMenuBar, QStatusBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut, QAction

from .models import PropertyMetadata, PropertyChange
from .events import PropertyNotificationCenter, PropertyEventType
from .display import PropertyDisplayWidget
from .editors import PropertyEditorFactory


class PropertyPanelIntegration(QWidget):
    """Handles integration of property panel with main application"""
    
    # Signals for workspace integration
    panel_visibility_changed = pyqtSignal(bool)
    panel_docked_changed = pyqtSignal(bool, str)  # docked, position
    workspace_layout_changed = pyqtSignal(dict)
    element_selection_changed = pyqtSignal(list)  # element_ids
    
    def __init__(self, main_window, notification_center: PropertyNotificationCenter):
        super().__init__()
        self.main_window = main_window
        self.notification_center = notification_center
        
        # Integration state
        self._dock_widget: Optional[QDockWidget] = None
        self._panel_widget: Optional[PropertyDisplayWidget] = None
        self._is_docked = True
        self._dock_position = Qt.DockWidgetArea.RightDockWidgetArea
        
        # Workspace components
        self._splitter: Optional[QSplitter] = None
        self._tab_widget: Optional[QTabWidget] = None
        self._toolbar: Optional[QToolBar] = None
        
        # Configuration
        self.settings = QSettings()
        self.auto_hide_enabled = False
        self.pin_panel = True
        
        # Setup integration
        self._setup_dock_widget()
        self._setup_keyboard_shortcuts()
        self._setup_menu_integration()
        self._restore_workspace_state()
        
        # Connect events
        self._connect_events()
    
    def _setup_dock_widget(self) -> None:
        """Setup dockable property panel widget"""
        # Create dock widget
        self._dock_widget = QDockWidget("Element Properties", self.main_window)
        self._dock_widget.setObjectName("PropertyPanelDock")
        
        # Configure dock widget
        self._dock_widget.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | 
            Qt.DockWidgetArea.RightDockWidgetArea |
            Qt.DockWidgetArea.BottomDockWidgetArea
        )
        
        # Create property panel widget
        self._panel_widget = PropertyDisplayWidget(self.notification_center)
        self._dock_widget.setWidget(self._panel_widget)
        
        # Add to main window
        self.main_window.addDockWidget(self._dock_position, self._dock_widget)
        
        # Connect dock signals
        self._dock_widget.visibilityChanged.connect(self._on_visibility_changed)
        self._dock_widget.dockLocationChanged.connect(self._on_dock_location_changed)
        self._dock_widget.topLevelChanged.connect(self._on_floating_changed)
    
    def _setup_keyboard_shortcuts(self) -> None:
        """Setup keyboard shortcuts for property panel"""
        # Toggle panel visibility
        toggle_shortcut = QShortcut(QKeySequence("F4"), self.main_window)
        toggle_shortcut.activated.connect(self.toggle_panel_visibility)
        
        # Focus property panel
        focus_shortcut = QShortcut(QKeySequence("Ctrl+P"), self.main_window)
        focus_shortcut.activated.connect(self.focus_panel)
        
        # Pin/unpin panel
        pin_shortcut = QShortcut(QKeySequence("Ctrl+Shift+P"), self.main_window)
        pin_shortcut.activated.connect(self.toggle_pin_panel)
        
        # Dock to left
        dock_left_shortcut = QShortcut(QKeySequence("Ctrl+Alt+Left"), self.main_window)
        dock_left_shortcut.activated.connect(lambda: self.dock_panel_to_area(Qt.DockWidgetArea.LeftDockWidgetArea))
        
        # Dock to right  
        dock_right_shortcut = QShortcut(QKeySequence("Ctrl+Alt+Right"), self.main_window)
        dock_right_shortcut.activated.connect(lambda: self.dock_panel_to_area(Qt.DockWidgetArea.RightDockWidgetArea))
        
        # Dock to bottom
        dock_bottom_shortcut = QShortcut(QKeySequence("Ctrl+Alt+Down"), self.main_window)
        dock_bottom_shortcut.activated.connect(lambda: self.dock_panel_to_area(Qt.DockWidgetArea.BottomDockWidgetArea))
        
        # Float panel
        float_shortcut = QShortcut(QKeySequence("Ctrl+Alt+F"), self.main_window)
        float_shortcut.activated.connect(self.float_panel)
    
    def _setup_menu_integration(self) -> None:
        """Setup menu integration for property panel"""
        # Find or create View menu
        menubar = self.main_window.menuBar()
        view_menu = None
        
        for action in menubar.actions():
            menu = action.menu()
            if menu and menu.title() == "&View":
                view_menu = menu
                break
        
        if not view_menu:
            view_menu = menubar.addMenu("&View")
        
        # Add property panel actions
        panel_menu = view_menu.addMenu("&Property Panel")
        
        # Toggle visibility action
        toggle_action = QAction("&Show Property Panel", self.main_window)
        toggle_action.setCheckable(True)
        toggle_action.setChecked(self._dock_widget.isVisible())
        toggle_action.setShortcut(QKeySequence("F4"))
        toggle_action.triggered.connect(self.toggle_panel_visibility)
        panel_menu.addAction(toggle_action)
        
        self._toggle_action = toggle_action
        
        panel_menu.addSeparator()
        
        # Dock position actions
        dock_group = []
        
        # Dock left
        dock_left_action = QAction("Dock &Left", self.main_window)
        dock_left_action.triggered.connect(lambda: self.dock_panel_to_area(Qt.DockWidgetArea.LeftDockWidgetArea))
        panel_menu.addAction(dock_left_action)
        dock_group.append(dock_left_action)
        
        # Dock right
        dock_right_action = QAction("Dock &Right", self.main_window)
        dock_right_action.triggered.connect(lambda: self.dock_panel_to_area(Qt.DockWidgetArea.RightDockWidgetArea))
        panel_menu.addAction(dock_right_action)
        dock_group.append(dock_right_action)
        
        # Dock bottom
        dock_bottom_action = QAction("Dock &Bottom", self.main_window)
        dock_bottom_action.triggered.connect(lambda: self.dock_panel_to_area(Qt.DockWidgetArea.BottomDockWidgetArea))
        panel_menu.addAction(dock_bottom_action)
        dock_group.append(dock_bottom_action)
        
        panel_menu.addSeparator()
        
        # Float action
        float_action = QAction("&Float Panel", self.main_window)
        float_action.triggered.connect(self.float_panel)
        panel_menu.addAction(float_action)
        
        # Pin action
        pin_action = QAction("&Pin Panel", self.main_window)
        pin_action.setCheckable(True)
        pin_action.setChecked(self.pin_panel)
        pin_action.triggered.connect(self.toggle_pin_panel)
        panel_menu.addAction(pin_action)
        
        self._pin_action = pin_action
    
    def _connect_events(self) -> None:
        """Connect property panel events"""
        # Connect to selection changes from element list
        if hasattr(self.main_window, 'element_list_widget'):
            element_list = self.main_window.element_list_widget
            if hasattr(element_list, 'selection_changed'):
                element_list.selection_changed.connect(self._on_element_selection_changed)
        
        # Connect to document changes
        if hasattr(self.main_window, 'document_changed'):
            self.main_window.document_changed.connect(self._on_document_changed)
        
        # Connect notification center events
        self.notification_center.register_listener(
            PropertyEventType.VALUE_CHANGED, 
            self._on_property_value_changed
        )
    
    def _restore_workspace_state(self) -> None:
        """Restore workspace state from settings"""
        # Restore dock widget state
        if self.settings.contains("property_panel/geometry"):
            self._dock_widget.restoreGeometry(self.settings.value("property_panel/geometry"))
        
        # Restore visibility
        visible = self.settings.value("property_panel/visible", True, type=bool)
        self._dock_widget.setVisible(visible)
        if hasattr(self, '_toggle_action'):
            self._toggle_action.setChecked(visible)
        
        # Restore dock position
        dock_area = self.settings.value("property_panel/dock_area", Qt.DockWidgetArea.RightDockWidgetArea, type=int)
        if dock_area in [Qt.DockWidgetArea.LeftDockWidgetArea, Qt.DockWidgetArea.RightDockWidgetArea, Qt.DockWidgetArea.BottomDockWidgetArea]:
            self._dock_position = dock_area
            if self._dock_widget.isFloating():
                self._dock_widget.setFloating(False)
            self.main_window.addDockWidget(self._dock_position, self._dock_widget)
        
        # Restore floating state
        floating = self.settings.value("property_panel/floating", False, type=bool)
        if floating:
            self._dock_widget.setFloating(True)
        
        # Restore pin state
        self.pin_panel = self.settings.value("property_panel/pinned", True, type=bool)
        if hasattr(self, '_pin_action'):
            self._pin_action.setChecked(self.pin_panel)
    
    def save_workspace_state(self) -> None:
        """Save workspace state to settings"""
        self.settings.setValue("property_panel/geometry", self._dock_widget.saveGeometry())
        self.settings.setValue("property_panel/visible", self._dock_widget.isVisible())
        self.settings.setValue("property_panel/dock_area", int(self._dock_position))
        self.settings.setValue("property_panel/floating", self._dock_widget.isFloating())
        self.settings.setValue("property_panel/pinned", self.pin_panel)
        self.settings.sync()
    
    # Public API methods
    def toggle_panel_visibility(self) -> None:
        """Toggle property panel visibility"""
        visible = not self._dock_widget.isVisible()
        self._dock_widget.setVisible(visible)
        
        if hasattr(self, '_toggle_action'):
            self._toggle_action.setChecked(visible)
        
        self.panel_visibility_changed.emit(visible)
    
    def show_panel(self) -> None:
        """Show property panel"""
        self._dock_widget.show()
        if hasattr(self, '_toggle_action'):
            self._toggle_action.setChecked(True)
        self.panel_visibility_changed.emit(True)
    
    def hide_panel(self) -> None:
        """Hide property panel"""
        self._dock_widget.hide()
        if hasattr(self, '_toggle_action'):
            self._toggle_action.setChecked(False)
        self.panel_visibility_changed.emit(False)
    
    def focus_panel(self) -> None:
        """Focus the property panel"""
        if not self._dock_widget.isVisible():
            self.show_panel()
        
        self._dock_widget.raise_()
        self._dock_widget.activateWindow()
        
        if self._panel_widget:
            self._panel_widget.setFocus()
    
    def dock_panel_to_area(self, area: Qt.DockWidgetArea) -> None:
        """Dock panel to specific area"""
        if self._dock_widget.isFloating():
            self._dock_widget.setFloating(False)
        
        self._dock_position = area
        self.main_window.addDockWidget(area, self._dock_widget)
        
        self.panel_docked_changed.emit(True, self._get_area_name(area))
    
    def float_panel(self) -> None:
        """Float the property panel"""
        self._dock_widget.setFloating(True)
        self.panel_docked_changed.emit(False, "floating")
    
    def toggle_pin_panel(self) -> None:
        """Toggle panel pin state"""
        self.pin_panel = not self.pin_panel
        
        if hasattr(self, '_pin_action'):
            self._pin_action.setChecked(self.pin_panel)
        
        # Configure auto-hide behavior
        if self.pin_panel:
            self._dock_widget.setFeatures(
                QDockWidget.DockWidgetFeature.DockWidgetMovable |
                QDockWidget.DockWidgetFeature.DockWidgetClosable
            )
        else:
            self._dock_widget.setFeatures(
                QDockWidget.DockWidgetFeature.DockWidgetMovable |
                QDockWidget.DockWidgetFeature.DockWidgetClosable |
                QDockWidget.DockWidgetFeature.DockWidgetFloatable
            )
    
    def get_panel_widget(self) -> Optional[PropertyDisplayWidget]:
        """Get the property panel widget"""
        return self._panel_widget
    
    def is_panel_visible(self) -> bool:
        """Check if panel is visible"""
        return self._dock_widget.isVisible() if self._dock_widget else False
    
    def is_panel_docked(self) -> bool:
        """Check if panel is docked"""
        return not self._dock_widget.isFloating() if self._dock_widget else True
    
    def get_dock_position(self) -> Qt.DockWidgetArea:
        """Get current dock position"""
        return self._dock_position
    
    # Workspace integration methods
    def integrate_with_element_list(self, element_list_widget) -> None:
        """Integrate with element list widget"""
        if hasattr(element_list_widget, 'selection_changed'):
            element_list_widget.selection_changed.connect(self._on_element_selection_changed)
        
        if hasattr(element_list_widget, 'element_double_clicked'):
            element_list_widget.element_double_clicked.connect(self._on_element_double_clicked)
    
    def integrate_with_document_viewer(self, document_viewer) -> None:
        """Integrate with document viewer"""
        if hasattr(document_viewer, 'element_selected'):
            document_viewer.element_selected.connect(self._on_viewer_element_selected)
        
        if hasattr(document_viewer, 'element_hovered'):
            document_viewer.element_hovered.connect(self._on_viewer_element_hovered)
    
    def integrate_with_workspace(self, workspace_manager) -> None:
        """Integrate with workspace manager"""
        if hasattr(workspace_manager, 'layout_changed'):
            workspace_manager.layout_changed.connect(self._on_workspace_layout_changed)
        
        if hasattr(workspace_manager, 'perspective_changed'):
            workspace_manager.perspective_changed.connect(self._on_perspective_changed)
    
    # Event handlers
    def _on_visibility_changed(self, visible: bool) -> None:
        """Handle dock widget visibility change"""
        if hasattr(self, '_toggle_action'):
            self._toggle_action.setChecked(visible)
        self.panel_visibility_changed.emit(visible)
    
    def _on_dock_location_changed(self, area: Qt.DockWidgetArea) -> None:
        """Handle dock location change"""
        self._dock_position = area
        self.panel_docked_changed.emit(True, self._get_area_name(area))
    
    def _on_floating_changed(self, floating: bool) -> None:
        """Handle floating state change"""
        area_name = "floating" if floating else self._get_area_name(self._dock_position)
        self.panel_docked_changed.emit(not floating, area_name)
    
    def _on_element_selection_changed(self, element_ids: List[str]) -> None:
        """Handle element selection change"""
        if self._panel_widget:
            self._panel_widget.set_selected_elements(element_ids)
        
        self.element_selection_changed.emit(element_ids)
        
        # Auto-show panel if elements are selected and auto-show is enabled
        if element_ids and hasattr(self, 'auto_show_on_selection') and self.auto_show_on_selection:
            if not self._dock_widget.isVisible():
                self.show_panel()
    
    def _on_element_double_clicked(self, element_id: str) -> None:
        """Handle element double-click"""
        if not self._dock_widget.isVisible():
            self.show_panel()
        
        if self._panel_widget:
            self._panel_widget.focus_element(element_id)
    
    def _on_viewer_element_selected(self, element_id: str) -> None:
        """Handle element selection from document viewer"""
        self._on_element_selection_changed([element_id])
    
    def _on_viewer_element_hovered(self, element_id: str) -> None:
        """Handle element hover from document viewer"""
        if self._panel_widget:
            self._panel_widget.preview_element(element_id)
    
    def _on_document_changed(self, document_path: str) -> None:
        """Handle document change"""
        if self._panel_widget:
            self._panel_widget.clear_selection()
    
    def _on_property_value_changed(self, event) -> None:
        """Handle property value change"""
        # Update related UI components
        if hasattr(self.main_window, 'status_bar'):
            status_bar = self.main_window.status_bar
            status_bar.showMessage(f"Property '{event.property_name}' changed", 2000)
    
    def _on_workspace_layout_changed(self, layout_info: Dict[str, Any]) -> None:
        """Handle workspace layout change"""
        self.workspace_layout_changed.emit(layout_info)
    
    def _on_perspective_changed(self, perspective_name: str) -> None:
        """Handle perspective change"""
        # Restore panel state for perspective
        perspective_key = f"perspectives/{perspective_name}/property_panel"
        
        if self.settings.contains(f"{perspective_key}/visible"):
            visible = self.settings.value(f"{perspective_key}/visible", True, type=bool)
            self._dock_widget.setVisible(visible)
        
        if self.settings.contains(f"{perspective_key}/dock_area"):
            dock_area = self.settings.value(f"{perspective_key}/dock_area", type=int)
            self.dock_panel_to_area(dock_area)
    
    # Utility methods
    def _get_area_name(self, area: Qt.DockWidgetArea) -> str:
        """Get area name from dock widget area"""
        area_names = {
            Qt.DockWidgetArea.LeftDockWidgetArea: "left",
            Qt.DockWidgetArea.RightDockWidgetArea: "right",
            Qt.DockWidgetArea.TopDockWidgetArea: "top",
            Qt.DockWidgetArea.BottomDockWidgetArea: "bottom"
        }
        return area_names.get(area, "unknown")
    
    # Configuration methods
    def set_auto_show_on_selection(self, enabled: bool) -> None:
        """Enable/disable auto-show on element selection"""
        self.auto_show_on_selection = enabled
    
    def set_auto_hide_enabled(self, enabled: bool) -> None:
        """Enable/disable auto-hide functionality"""
        self.auto_hide_enabled = enabled
        
        if enabled and not self.pin_panel:
            # Setup auto-hide timer
            if not hasattr(self, '_auto_hide_timer'):
                self._auto_hide_timer = QTimer()
                self._auto_hide_timer.setSingleShot(True)
                self._auto_hide_timer.timeout.connect(self._auto_hide_panel)
            
            # Install event filter for mouse tracking
            self._dock_widget.installEventFilter(self)
    
    def _auto_hide_panel(self) -> None:
        """Auto-hide panel after timeout"""
        if not self.pin_panel and self.auto_hide_enabled:
            self.hide_panel()
    
    def eventFilter(self, obj, event) -> bool:
        """Event filter for auto-hide functionality"""
        if obj == self._dock_widget and self.auto_hide_enabled and not self.pin_panel:
            if event.type() == event.Type.Enter:
                if hasattr(self, '_auto_hide_timer'):
                    self._auto_hide_timer.stop()
            elif event.type() == event.Type.Leave:
                if hasattr(self, '_auto_hide_timer'):
                    self._auto_hide_timer.start(3000)  # 3 second delay
        
        return False


class WorkspaceLayoutManager:
    """Manages property panel integration with workspace layouts"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.layouts: Dict[str, Dict[str, Any]] = {}
        self.current_layout = "default"
    
    def save_layout(self, name: str) -> None:
        """Save current workspace layout"""
        layout_data = {
            'window_geometry': self.main_window.saveGeometry(),
            'window_state': self.main_window.saveState(),
            'splitter_states': self._save_splitter_states(),
            'dock_positions': self._save_dock_positions(),
        }
        
        self.layouts[name] = layout_data
        
        # Save to settings
        settings = QSettings()
        settings.setValue(f"layouts/{name}", layout_data)
    
    def load_layout(self, name: str) -> bool:
        """Load workspace layout"""
        if name not in self.layouts:
            # Try to load from settings
            settings = QSettings()
            if settings.contains(f"layouts/{name}"):
                self.layouts[name] = settings.value(f"layouts/{name}")
            else:
                return False
        
        layout_data = self.layouts[name]
        
        # Restore window geometry and state
        self.main_window.restoreGeometry(layout_data.get('window_geometry', b''))
        self.main_window.restoreState(layout_data.get('window_state', b''))
        
        # Restore splitter states
        self._restore_splitter_states(layout_data.get('splitter_states', {}))
        
        # Restore dock positions
        self._restore_dock_positions(layout_data.get('dock_positions', {}))
        
        self.current_layout = name
        return True
    
    def get_available_layouts(self) -> List[str]:
        """Get list of available layouts"""
        # Load from settings
        settings = QSettings()
        settings.beginGroup("layouts")
        layout_names = settings.childGroups()
        settings.endGroup()
        
        # Merge with in-memory layouts
        all_layouts = set(layout_names) | set(self.layouts.keys())
        return sorted(list(all_layouts))
    
    def delete_layout(self, name: str) -> bool:
        """Delete a layout"""
        if name in self.layouts:
            del self.layouts[name]
        
        settings = QSettings()
        if settings.contains(f"layouts/{name}"):
            settings.remove(f"layouts/{name}")
            return True
        
        return False
    
    def _save_splitter_states(self) -> Dict[str, Any]:
        """Save splitter states"""
        splitter_states = {}
        
        # Find all splitters in the main window
        splitters = self.main_window.findChildren(QSplitter)
        for i, splitter in enumerate(splitters):
            if splitter.objectName():
                splitter_states[splitter.objectName()] = splitter.saveState()
            else:
                splitter_states[f"splitter_{i}"] = splitter.saveState()
        
        return splitter_states
    
    def _restore_splitter_states(self, splitter_states: Dict[str, Any]) -> None:
        """Restore splitter states"""
        splitters = self.main_window.findChildren(QSplitter)
        for splitter in splitters:
            name = splitter.objectName() or f"splitter_{splitters.index(splitter)}"
            if name in splitter_states:
                splitter.restoreState(splitter_states[name])
    
    def _save_dock_positions(self) -> Dict[str, Any]:
        """Save dock widget positions"""
        dock_positions = {}
        
        dock_widgets = self.main_window.findChildren(QDockWidget)
        for dock in dock_widgets:
            if dock.objectName():
                dock_positions[dock.objectName()] = {
                    'area': self.main_window.dockWidgetArea(dock),
                    'floating': dock.isFloating(),
                    'visible': dock.isVisible(),
                    'geometry': dock.saveGeometry()
                }
        
        return dock_positions
    
    def _restore_dock_positions(self, dock_positions: Dict[str, Any]) -> None:
        """Restore dock widget positions"""
        dock_widgets = self.main_window.findChildren(QDockWidget)
        for dock in dock_widgets:
            name = dock.objectName()
            if name and name in dock_positions:
                pos_data = dock_positions[name]
                
                # Restore area and floating state
                if not pos_data.get('floating', False):
                    area = pos_data.get('area', Qt.DockWidgetArea.RightDockWidgetArea)
                    self.main_window.addDockWidget(area, dock)
                else:
                    dock.setFloating(True)
                
                # Restore visibility and geometry
                dock.setVisible(pos_data.get('visible', True))
                dock.restoreGeometry(pos_data.get('geometry', b''))


# Export main integration class
__all__ = ['PropertyPanelIntegration', 'WorkspaceLayoutManager']