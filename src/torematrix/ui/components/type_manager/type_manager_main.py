"""Type Manager Main Interface

Main widget that integrates all type management components into
a comprehensive type administration interface.
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTabWidget,
    QPushButton, QLabel, QToolBar, QMenuBar, QMenu, QMessageBox,
    QStatusBar, QProgressBar, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon, QAction

from torematrix.core.models.types import TypeRegistry, TypeDefinition, get_type_registry
from .selector import TypeSelectorWidget, TypeSelectorPanel
from .hierarchy_view import TypeHierarchyView, TypeHierarchyWidget
from .statistics import TypeStatisticsDashboard
from .icon_manager import TypeIconManager
from .search_interface import TypeSearchInterface
from .info_panel import TypeInfoPanel
from .comparison_view import TypeComparisonView
from .recommendation_ui import TypeRecommendationUI


class TypeManagerMainWidget(QWidget):
    """Main type management interface"""
    
    # Signals
    type_selected = pyqtSignal(str)  # type_id
    type_created = pyqtSignal(TypeDefinition)
    type_modified = pyqtSignal(TypeDefinition)
    type_deleted = pyqtSignal(str)  # type_id
    
    def __init__(self, registry: TypeRegistry = None, parent=None):
        super().__init__(parent)
        
        self.registry = registry or get_type_registry()
        self.current_type_id: Optional[str] = None
        
        # State
        self.auto_save_timer = QTimer()
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.timeout.connect(self.auto_save)
        
        self.setup_ui()
        self.setup_toolbar()
        self.setup_menu_bar()
        self.setup_status_bar()
        self.connect_signals()
        
        # Initialize with data
        self.refresh_all_components()
    
    def setup_ui(self):
        """Setup main user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Main content area
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Navigation and selection
        left_panel = self.create_left_panel()
        self.main_splitter.addWidget(left_panel)
        
        # Center panel - Main content
        center_panel = self.create_center_panel()
        self.main_splitter.addWidget(center_panel)
        
        # Right panel - Details and tools
        right_panel = self.create_right_panel()
        self.main_splitter.addWidget(right_panel)
        
        # Set splitter proportions
        self.main_splitter.setSizes([300, 600, 400])
        
        layout.addWidget(self.main_splitter)
    
    def create_left_panel(self) -> QWidget:
        """Create left navigation panel"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Header
        header = QLabel("Type Browser")
        header.setFont(QFont("", 12, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Tabs for different views
        tabs = QTabWidget()
        
        # Hierarchy tab
        self.hierarchy_widget = TypeHierarchyWidget(self.registry)
        tabs.addTab(self.hierarchy_widget, "Hierarchy")
        
        # Search tab
        self.search_interface = TypeSearchInterface(self.registry)
        tabs.addTab(self.search_interface, "Search")
        
        # Recommendations tab
        self.recommendations_ui = TypeRecommendationUI(self.registry)
        tabs.addTab(self.recommendations_ui, "AI Suggestions")
        
        layout.addWidget(tabs)
        
        return panel
    
    def create_center_panel(self) -> QWidget:
        """Create center content panel"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Main content tabs
        self.content_tabs = QTabWidget()
        
        # Type details tab
        self.info_panel = TypeInfoPanel(self.registry)
        self.content_tabs.addTab(self.info_panel, "Type Details")
        
        # Comparison tab
        self.comparison_view = TypeComparisonView(self.registry)
        self.content_tabs.addTab(self.comparison_view, "Comparison")
        
        # Statistics tab
        self.statistics_dashboard = TypeStatisticsDashboard(self.registry)
        self.content_tabs.addTab(self.statistics_dashboard, "Statistics")
        
        # Icon management tab
        self.icon_manager = TypeIconManager(self.registry)
        self.content_tabs.addTab(self.icon_manager, "Icons")
        
        layout.addWidget(self.content_tabs)
        
        return panel
    
    def create_right_panel(self) -> QWidget:
        """Create right tools panel"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Header
        header = QLabel("Quick Tools")
        header.setFont(QFont("", 12, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Type selector
        selector_group = QFrame()
        selector_group.setFrameStyle(QFrame.Shape.Box)
        selector_layout = QVBoxLayout(selector_group)
        
        selector_label = QLabel("Type Selector")
        selector_label.setFont(QFont("", 10, QFont.Weight.Bold))
        selector_layout.addWidget(selector_label)
        
        self.type_selector = TypeSelectorPanel(self.registry)
        selector_layout.addWidget(self.type_selector)
        
        layout.addWidget(selector_group)
        
        # Quick actions
        actions_group = QFrame()
        actions_group.setFrameStyle(QFrame.Shape.Box)
        actions_layout = QVBoxLayout(actions_group)
        
        actions_label = QLabel("Quick Actions")
        actions_label.setFont(QFont("", 10, QFont.Weight.Bold))
        actions_layout.addWidget(actions_label)
        
        # Action buttons
        self.create_type_btn = QPushButton("➕ Create Type")
        self.create_type_btn.clicked.connect(self.create_new_type)
        actions_layout.addWidget(self.create_type_btn)
        
        self.duplicate_type_btn = QPushButton("🔄 Duplicate Type")
        self.duplicate_type_btn.clicked.connect(self.duplicate_current_type)
        self.duplicate_type_btn.setEnabled(False)
        actions_layout.addWidget(self.duplicate_type_btn)
        
        self.export_type_btn = QPushButton("📤 Export Type")
        self.export_type_btn.clicked.connect(self.export_current_type)
        self.export_type_btn.setEnabled(False)
        actions_layout.addWidget(self.export_type_btn)
        
        self.delete_type_btn = QPushButton("🗑️ Delete Type")
        self.delete_type_btn.clicked.connect(self.delete_current_type)
        self.delete_type_btn.setEnabled(False)
        self.delete_type_btn.setStyleSheet("QPushButton { color: #d13438; }")
        actions_layout.addWidget(self.delete_type_btn)
        
        layout.addWidget(actions_group)
        
        layout.addStretch()
        
        return panel
    
    def setup_toolbar(self):
        """Setup toolbar"""
        self.toolbar = QToolBar("Type Manager Toolbar")
        
        # File operations
        new_action = QAction("➕ New Type", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.create_new_type)
        self.toolbar.addAction(new_action)
        
        save_action = QAction("💾 Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_changes)
        self.toolbar.addAction(save_action)
        
        self.toolbar.addSeparator()
        
        # View operations
        refresh_action = QAction("🔄 Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_all_components)
        self.toolbar.addAction(refresh_action)
        
        self.toolbar.addSeparator()
        
        # Tools
        validate_action = QAction("✅ Validate All", self)
        validate_action.triggered.connect(self.validate_all_types)
        self.toolbar.addAction(validate_action)
        
        optimize_action = QAction("✨ Generate Recommendations", self)
        optimize_action.triggered.connect(self.generate_recommendations)
        self.toolbar.addAction(optimize_action)
    
    def setup_menu_bar(self):
        """Setup menu bar"""
        self.menu_bar = QMenuBar()
        
        # File menu
        file_menu = self.menu_bar.addMenu("File")
        
        file_menu.addAction("➕ New Type", self.create_new_type, "Ctrl+N")
        file_menu.addAction("📁 Open Type...", self.open_type, "Ctrl+O")
        file_menu.addSeparator()
        file_menu.addAction("💾 Save", self.save_changes, "Ctrl+S")
        file_menu.addAction("💾 Save As...", self.save_as, "Ctrl+Shift+S")
        file_menu.addSeparator()
        file_menu.addAction("📤 Import Types...", self.import_types)
        file_menu.addAction("📥 Export Types...", self.export_types)
        file_menu.addSeparator()
        file_menu.addAction("❌ Close", self.close, "Ctrl+W")
        
        # Edit menu
        edit_menu = self.menu_bar.addMenu("Edit")
        
        edit_menu.addAction("↩️ Undo", self.undo, "Ctrl+Z")
        edit_menu.addAction("↪️ Redo", self.redo, "Ctrl+Y")
        edit_menu.addSeparator()
        edit_menu.addAction("🔄 Duplicate Type", self.duplicate_current_type, "Ctrl+D")
        edit_menu.addAction("🗑️ Delete Type", self.delete_current_type, "Delete")
        
        # View menu
        view_menu = self.menu_bar.addMenu("View")
        
        view_menu.addAction("🔄 Refresh All", self.refresh_all_components, "F5")
        view_menu.addSeparator()
        view_menu.addAction("🗺️ Show Hierarchy", lambda: self.focus_tab("hierarchy"))
        view_menu.addAction("🔍 Show Search", lambda: self.focus_tab("search"))
        view_menu.addAction("📊 Show Statistics", lambda: self.focus_tab("statistics"))
        
        # Tools menu
        tools_menu = self.menu_bar.addMenu("Tools")
        
        tools_menu.addAction("✅ Validate All Types", self.validate_all_types)
        tools_menu.addAction("✨ Generate Recommendations", self.generate_recommendations)
        tools_menu.addAction("🔧 Optimize Types", self.optimize_types)
        tools_menu.addSeparator()
        tools_menu.addAction("⚙️ Settings...", self.show_settings)
        
        # Help menu
        help_menu = self.menu_bar.addMenu("Help")
        
        help_menu.addAction("📖 Documentation", self.show_documentation)
        help_menu.addAction("ℹ️ About", self.show_about)
    
    def setup_status_bar(self):
        """Setup status bar"""
        self.status_bar = QStatusBar()
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # Statistics
        self.stats_label = QLabel("0 types loaded")
        self.status_bar.addPermanentWidget(self.stats_label)
        
    def connect_signals(self):
        """Connect component signals"""
        # Hierarchy view
        self.hierarchy_widget.type_selected.connect(self.on_type_selected)
        
        # Search interface
        self.search_interface.type_selected.connect(self.on_type_selected)
        
        # Type selector
        self.type_selector.type_selected.connect(self.on_type_selected)
        
        # Info panel
        self.info_panel.type_modified.connect(self.on_type_modified)
        
        # Statistics dashboard
        self.statistics_dashboard.type_selected.connect(self.on_type_selected)
        
        # Recommendations
        self.recommendations_ui.recommendation_applied.connect(self.on_recommendation_applied)
        
        # Registry changes
        self.registry.add_change_listener(self.on_registry_changed)
    
    def on_type_selected(self, type_id: str):
        """Handle type selection"""
        self.current_type_id = type_id
        
        # Update info panel
        try:
            type_def = self.registry.get_type(type_id)
            self.info_panel.set_type(type_def)
            
            # Update status
            self.status_label.setText(f"Selected: {type_def.name}")
            
            # Enable/disable actions
            self.duplicate_type_btn.setEnabled(True)
            self.export_type_btn.setEnabled(True)
            self.delete_type_btn.setEnabled(True)
            
        except Exception as e:
            self.status_label.setText(f"Error loading type: {e}")
            self.duplicate_type_btn.setEnabled(False)
            self.export_type_btn.setEnabled(False)
            self.delete_type_btn.setEnabled(False)
        
        # Emit signal
        self.type_selected.emit(type_id)
    
    def on_type_modified(self, type_def: TypeDefinition):
        """Handle type modification"""
        # Schedule auto-save
        self.auto_save_timer.start(2000)  # 2 second delay
        
        # Update status
        self.status_label.setText(f"Modified: {type_def.name} (auto-save in 2s)")
        
        # Emit signal
        self.type_modified.emit(type_def)
    
    def on_recommendation_applied(self, recommendation):
        """Handle recommendation application"""
        # Implementation would apply the recommendation
        self.status_label.setText(f"Applied recommendation: {recommendation.title}")
    
    def on_registry_changed(self, action: str, type_id: str, type_def: TypeDefinition):
        """Handle registry changes"""
        # Update statistics
        type_count = len(self.registry.list_types())
        self.stats_label.setText(f"{type_count} types loaded")
        
        # Refresh relevant components
        if action in ["register", "unregister"]:
            self.hierarchy_widget.refresh()
            self.type_selector.refresh()
    
    # Action implementations
    
    def create_new_type(self):
        """Create new type"""
        # Implementation would show type creation dialog
        self.status_label.setText("Creating new type...")
    
    def open_type(self):
        """Open type dialog"""
        # Implementation would show type selection dialog
        pass
    
    def save_changes(self):
        """Save current changes"""
        if self.current_type_id:
            try:
                # Save current type changes
                self.status_label.setText("Changes saved")
            except Exception as e:
                self.status_label.setText(f"Save failed: {e}")
    
    def save_as(self):
        """Save as dialog"""
        pass
    
    def auto_save(self):
        """Perform auto-save"""
        self.save_changes()
        self.status_label.setText("Auto-saved")
    
    def duplicate_current_type(self):
        """Duplicate current type"""
        if self.current_type_id:
            # Implementation would duplicate the type
            self.status_label.setText(f"Duplicating type: {self.current_type_id}")
    
    def export_current_type(self):
        """Export current type"""
        if self.current_type_id:
            # Implementation would export the type
            self.status_label.setText(f"Exporting type: {self.current_type_id}")
    
    def delete_current_type(self):
        """Delete current type"""
        if self.current_type_id:
            try:
                type_def = self.registry.get_type(self.current_type_id)
                
                reply = QMessageBox.question(
                    self,
                    "Delete Type",
                    f"Are you sure you want to delete type '{type_def.name}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.registry.unregister_type(self.current_type_id)
                    self.current_type_id = None
                    self.status_label.setText(f"Deleted type: {type_def.name}")
                    
                    # Clear info panel
                    self.info_panel.set_type(None)
                    
                    # Disable actions
                    self.duplicate_type_btn.setEnabled(False)
                    self.export_type_btn.setEnabled(False)
                    self.delete_type_btn.setEnabled(False)
                    
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to delete type: {e}")
    
    def import_types(self):
        """Import types from file"""
        # Implementation would show import dialog
        pass
    
    def export_types(self):
        """Export types to file"""
        # Implementation would show export dialog
        pass
    
    def undo(self):
        """Undo last action"""
        pass
    
    def redo(self):
        """Redo last action"""
        pass
    
    def validate_all_types(self):
        """Validate all types"""
        self.status_label.setText("Validating all types...")
        # Implementation would validate all types
    
    def generate_recommendations(self):
        """Generate AI recommendations"""
        self.recommendations_ui.generate_recommendations()
        
        # Switch to recommendations tab
        self.focus_tab("recommendations")
    
    def optimize_types(self):
        """Optimize type definitions"""
        self.status_label.setText("Optimizing types...")
        # Implementation would optimize types
    
    def show_settings(self):
        """Show settings dialog"""
        pass
    
    def show_documentation(self):
        """Show documentation"""
        pass
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About Type Manager",
            "Type Manager v1.0\n\nAdvanced type management interface\nfor document processing systems."
        )
    
    def focus_tab(self, tab_name: str):
        """Focus specific tab"""
        tab_map = {
            "hierarchy": 0,
            "search": 1,
            "recommendations": 2,
            "details": 0,
            "comparison": 1,
            "statistics": 2,
            "icons": 3
        }
        
        if tab_name in ["hierarchy", "search", "recommendations"]:
            # Left panel tabs
            left_tabs = self.main_splitter.widget(0).findChild(QTabWidget)
            if left_tabs:
                left_tabs.setCurrentIndex(tab_map[tab_name])
        elif tab_name in ["details", "comparison", "statistics", "icons"]:
            # Center panel tabs
            self.content_tabs.setCurrentIndex(tab_map[tab_name])
    
    def refresh_all_components(self):
        """Refresh all components"""
        self.status_label.setText("Refreshing...")
        
        try:
            # Refresh all components
            self.hierarchy_widget.refresh()
            self.type_selector.refresh()
            self.search_interface.refresh()
            self.statistics_dashboard.refresh()
            self.icon_manager.refresh()
            
            # Update statistics
            type_count = len(self.registry.list_types())
            self.stats_label.setText(f"{type_count} types loaded")
            
            self.status_label.setText("Refreshed")
            
        except Exception as e:
            self.status_label.setText(f"Refresh failed: {e}")
    
    def get_toolbar(self) -> QToolBar:
        """Get toolbar for parent window"""
        return self.toolbar
    
    def get_menu_bar(self) -> QMenuBar:
        """Get menu bar for parent window"""
        return self.menu_bar
    
    def get_status_bar(self) -> QStatusBar:
        """Get status bar for parent window"""
        return self.status_bar
    
    def set_current_type(self, type_id: str):
        """Set current type programmatically"""
        self.on_type_selected(type_id)
    
    def get_current_type(self) -> Optional[str]:
        """Get current type ID"""
        return self.current_type_id
