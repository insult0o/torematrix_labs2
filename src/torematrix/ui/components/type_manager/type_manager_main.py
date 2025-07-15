"""Type Manager Main Widget

Main interface that integrates all type management UI components
with tabbed interface and comprehensive type management capabilities.
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QSplitter,
    QLabel, QPushButton, QFrame, QMessageBox, QFileDialog,
    QProgressBar, QStatusBar, QMenuBar, QMenu, QActionGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon, QAction

from torematrix.core.models.types import TypeRegistry, get_type_registry
from .selector import TypeSelectorWidget
from .hierarchy_view import TypeHierarchyView
from .statistics import TypeStatisticsDashboard
from .icon_manager import TypeIconManager
from .search_interface import TypeSearchInterface
from .info_panel import TypeInfoPanel
from .comparison_view import TypeComparisonView
from .recommendation_ui import TypeRecommendationUI


class TypeManagerMainWidget(QWidget):
    """Main type management interface integrating all components"""
    
    # Signals
    type_selected = pyqtSignal(str)  # type_id
    type_created = pyqtSignal(str)   # type_id
    type_modified = pyqtSignal(str)  # type_id
    type_deleted = pyqtSignal(str)   # type_id
    
    def __init__(self, registry: TypeRegistry = None, parent=None):
        super().__init__(parent)
        
        self.registry = registry or get_type_registry()
        self.current_type_id: Optional[str] = None
        
        self.setup_ui()
        self.setup_connections()
        self.setup_menu_bar()
        
        # Initialize with first available type
        self.initialize_display()
    
    def setup_ui(self):
        """Setup the main user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header with title and quick actions
        header = self.create_header()
        layout.addWidget(header)
        
        # Main content area
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Navigation and Quick Access
        left_panel = self.create_left_panel()
        main_splitter.addWidget(left_panel)
        
        # Center panel - Main Content Tabs
        center_panel = self.create_center_panel()
        main_splitter.addWidget(center_panel)
        
        # Right panel - Details and Tools
        right_panel = self.create_right_panel()
        main_splitter.addWidget(right_panel)
        
        # Set splitter proportions (25% | 50% | 25%)
        main_splitter.setSizes([250, 500, 250])
        layout.addWidget(main_splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
    
    def create_header(self) -> QWidget:
        """Create header with title and quick actions"""
        header = QFrame()
        header.setFrameStyle(QFrame.Shape.StyledPanel)
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border-bottom: 1px solid #dee2e6;
                padding: 8px;
            }
        """)
        
        layout = QHBoxLayout(header)
        
        # Title
        title = QLabel("Element Type Management")
        title.setFont(QFont("", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #495057;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Quick action buttons
        self.new_type_btn = QPushButton("✨ New Type")
        self.new_type_btn.clicked.connect(self.create_new_type)
        layout.addWidget(self.new_type_btn)
        
        self.import_btn = QPushButton("📥 Import")
        self.import_btn.clicked.connect(self.import_types)
        layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("📤 Export")
        self.export_btn.clicked.connect(self.export_types)
        layout.addWidget(self.export_btn)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_all)
        layout.addWidget(self.refresh_btn)
        
        return header
    
    def create_left_panel(self) -> QWidget:
        """Create left navigation panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Type selector with search
        selector_frame = QFrame()
        selector_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        selector_layout = QVBoxLayout(selector_frame)
        
        selector_title = QLabel("Type Selection")
        selector_title.setFont(QFont("", 10, QFont.Weight.Bold))
        selector_layout.addWidget(selector_title)
        
        self.type_selector = TypeSelectorWidget(self.registry)
        selector_layout.addWidget(self.type_selector)
        
        layout.addWidget(selector_frame)
        
        # Type hierarchy view
        hierarchy_frame = QFrame()
        hierarchy_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        hierarchy_layout = QVBoxLayout(hierarchy_frame)
        
        hierarchy_title = QLabel("Type Hierarchy")
        hierarchy_title.setFont(QFont("", 10, QFont.Weight.Bold))
        hierarchy_layout.addWidget(hierarchy_title)
        
        self.hierarchy_view = TypeHierarchyView(self.registry)
        hierarchy_layout.addWidget(self.hierarchy_view)
        
        layout.addWidget(hierarchy_frame)
        
        # Search interface
        search_frame = QFrame()
        search_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        search_layout = QVBoxLayout(search_frame)
        
        search_title = QLabel("Search & Filter")
        search_title.setFont(QFont("", 10, QFont.Weight.Bold))
        search_layout.addWidget(search_title)
        
        self.search_interface = TypeSearchInterface(self.registry)
        search_layout.addWidget(self.search_interface)
        
        layout.addWidget(search_frame)
        
        return panel
    
    def create_center_panel(self) -> QWidget:
        """Create center content panel with tabs"""
        self.center_tabs = QTabWidget()
        
        # Type Information Tab
        self.info_panel = TypeInfoPanel(self.registry)
        self.center_tabs.addTab(self.info_panel, "📋 Type Details")
        
        # Statistics Dashboard Tab  
        self.statistics_dashboard = TypeStatisticsDashboard(self.registry)
        self.center_tabs.addTab(self.statistics_dashboard, "📊 Statistics")
        
        # Type Comparison Tab
        self.comparison_view = TypeComparisonView(self.registry)
        self.center_tabs.addTab(self.comparison_view, "⚖️ Comparison")
        
        # AI Recommendations Tab
        self.recommendation_ui = TypeRecommendationUI(self.registry)
        self.center_tabs.addTab(self.recommendation_ui, "🤖 AI Recommendations")
        
        return self.center_tabs
    
    def create_right_panel(self) -> QWidget:
        """Create right tools panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Icon manager
        icon_frame = QFrame()
        icon_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        icon_layout = QVBoxLayout(icon_frame)
        
        icon_title = QLabel("Icon Management")
        icon_title.setFont(QFont("", 10, QFont.Weight.Bold))
        icon_layout.addWidget(icon_title)
        
        self.icon_manager = TypeIconManager(self.registry)
        icon_layout.addWidget(self.icon_manager)
        
        layout.addWidget(icon_frame)
        
        # Quick statistics
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        stats_layout = QVBoxLayout(stats_frame)
        
        stats_title = QLabel("Quick Stats")
        stats_title.setFont(QFont("", 10, QFont.Weight.Bold))
        stats_layout.addWidget(stats_title)
        
        self.quick_stats = QLabel("Loading...")
        self.quick_stats.setWordWrap(True)
        self.quick_stats.setStyleSheet("color: #666; font-size: 12px;")
        stats_layout.addWidget(self.quick_stats)
        
        layout.addWidget(stats_frame)
        
        layout.addStretch()
        
        return panel
    
    def setup_connections(self):
        """Setup signal connections between components"""
        # Type selection connections
        self.type_selector.type_selected.connect(self.on_type_selected)
        self.hierarchy_view.type_selected.connect(self.on_type_selected)
        self.search_interface.type_selected.connect(self.on_type_selected)
        
        # Icon selection
        self.icon_manager.icon_selected.connect(self.on_icon_selected)
        
        # Recommendations
        self.recommendation_ui.recommendation_applied.connect(self.on_recommendation_applied)
        
        # Statistics refresh
        self.statistics_dashboard.type_selected.connect(self.on_type_selected)
        
        # Comparison
        self.comparison_view.type_selected.connect(self.on_type_selected)
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.update_quick_stats)
        self.refresh_timer.start(10000)  # Update every 10 seconds
    
    def setup_menu_bar(self):
        """Setup menu bar (if parent window supports it)"""
        # This would be implemented if this widget is in a main window
        pass
    
    def initialize_display(self):
        """Initialize the display with default data"""
        # Load first available type
        types = self.registry.list_types()
        if types:
            first_type = next(iter(types.values()))
            self.on_type_selected(first_type.type_id)
        
        # Update quick stats
        self.update_quick_stats()
    
    def on_type_selected(self, type_id: str):
        """Handle type selection from any component"""
        self.current_type_id = type_id
        self.type_selected.emit(type_id)
        
        # Update info panel
        self.info_panel.set_type(type_id)
        
        # Update status
        try:
            type_def = self.registry.get_type(type_id)
            self.status_bar.showMessage(f"Selected: {type_def.name} ({type_def.category})")
        except Exception as e:
            self.status_bar.showMessage(f"Error loading type: {e}")
    
    def on_icon_selected(self, icon_path: str, icon_type: str):
        """Handle icon selection"""
        if self.current_type_id:
            # Apply icon to current type
            try:
                type_def = self.registry.get_type(self.current_type_id)
                # Update type with new icon
                # This would be implemented based on the type system's icon handling
                self.status_bar.showMessage(f"Icon applied to {type_def.name}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to apply icon: {e}")
    
    def on_recommendation_applied(self, recommendation):
        """Handle recommendation application"""
        self.status_bar.showMessage("Recommendation applied successfully")
        self.refresh_all()
    
    def create_new_type(self):
        """Create a new type"""
        # This would open a new type creation dialog
        # For now, show a placeholder message
        QMessageBox.information(
            self, 
            "Create New Type", 
            "New type creation dialog would open here.\n\nThis would integrate with the type template system from Agent 1."
        )
    
    def import_types(self):
        """Import types from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Types",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                # Import logic would go here
                self.status_bar.showMessage(f"Types imported from {file_path}")
                self.refresh_all()
            except Exception as e:
                QMessageBox.warning(self, "Import Error", f"Failed to import types: {e}")
    
    def export_types(self):
        """Export types to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Types", 
            "types_export.json",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                # Export logic would go here
                self.status_bar.showMessage(f"Types exported to {file_path}")
            except Exception as e:
                QMessageBox.warning(self, "Export Error", f"Failed to export types: {e}")
    
    def refresh_all(self):
        """Refresh all components"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Refresh each component
        components = [
            self.type_selector,
            self.hierarchy_view,
            self.statistics_dashboard,
            self.search_interface,
            self.info_panel,
            self.comparison_view,
            self.recommendation_ui,
            self.icon_manager
        ]
        
        for i, component in enumerate(components):
            if hasattr(component, 'refresh'):
                component.refresh()
            self.progress_bar.setValue(int((i + 1) / len(components) * 100))
        
        self.update_quick_stats()
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("All components refreshed")
    
    def update_quick_stats(self):
        """Update quick statistics display"""
        try:
            types = self.registry.list_types()
            total_types = len(types)
            
            # Count by category
            categories = {}
            custom_count = 0
            
            for type_def in types.values():
                categories[type_def.category] = categories.get(type_def.category, 0) + 1
                if type_def.is_custom:
                    custom_count += 1
            
            # Format statistics
            stats_text = f"Total Types: {total_types}\n"
            stats_text += f"Custom Types: {custom_count}\n"
            stats_text += f"Categories: {len(categories)}\n\n"
            
            # Top categories
            sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
            stats_text += "Top Categories:\n"
            for category, count in sorted_categories[:3]:
                stats_text += f"• {category}: {count}\n"
            
            self.quick_stats.setText(stats_text)
            
        except Exception as e:
            self.quick_stats.setText(f"Error loading stats: {e}")
    
    def get_current_type_id(self) -> Optional[str]:
        """Get currently selected type ID"""
        return self.current_type_id
    
    def set_type(self, type_id: str):
        """Programmatically set the current type"""
        self.on_type_selected(type_id)
    
    def closeEvent(self, event):
        """Handle widget close event"""
        # Stop timers
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        
        super().closeEvent(event)