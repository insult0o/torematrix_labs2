"""Type Statistics Dashboard

Analytics and statistics for type usage, distribution, and performance.
Provides insights into type system usage patterns and trends.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QFrame, QPushButton, QComboBox, QProgressBar, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

from torematrix.core.models.types import get_type_registry, TypeRegistry, TypeDefinition


@dataclass
class TypeStatistics:
    """Statistics for a specific type"""
    type_id: str
    type_name: str
    usage_count: int = 0
    creation_count: int = 0
    error_count: int = 0
    last_used: Optional[datetime] = None
    popularity_score: float = 0.0


class StatisticsCard(QFrame):
    """Card widget for displaying a single statistic"""
    
    def __init__(self, title: str, value: str, subtitle: str = "", color: str = "#0078d4", parent=None):
        super().__init__(parent)
        
        self.setup_ui(title, value, subtitle, color)
    
    def setup_ui(self, title: str, value: str, subtitle: str, color: str):
        """Setup the card UI"""
        self.setFixedSize(200, 120)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet(f"""
            QFrame {{
                border: 1px solid #ddd;
                border-radius: 8px;
                background: white;
                padding: 8px;
            }}
            QFrame:hover {{
                border-color: {color};
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)
        
        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("", 9))
        title_label.setStyleSheet("color: #666;")
        layout.addWidget(title_label)
        
        # Value
        value_label = QLabel(value)
        value_label.setFont(QFont("", 18, QFont.Weight.Bold))
        value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(value_label)
        
        # Subtitle
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setFont(QFont("", 8))
            subtitle_label.setStyleSheet("color: #999;")
            layout.addWidget(subtitle_label)
        
        layout.addStretch()


class TypeStatisticsDashboard(QWidget):
    """Statistics and analytics dashboard for type usage"""
    
    type_selected = pyqtSignal(str)  # type_id
    
    def __init__(self, registry: TypeRegistry = None, parent=None):
        super().__init__(parent)
        
        self.registry = registry or get_type_registry()
        self.statistics_data: Optional[Dict[str, Any]] = None
        
        self.setup_ui()
        self.setup_connections()
        self.refresh_statistics()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("Type Statistics Dashboard")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Refresh button
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_statistics)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Main content tabs
        self.tab_widget = QTabWidget()
        
        # Overview tab
        self.overview_tab = self.create_overview_tab()
        self.tab_widget.addTab(self.overview_tab, "Overview")
        
        # Type details tab
        self.details_tab = self.create_details_tab()
        self.tab_widget.addTab(self.details_tab, "Type Details")
        
        layout.addWidget(self.tab_widget)
    
    def create_overview_tab(self) -> QWidget:
        """Create overview tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # System statistics cards
        self.system_cards_layout = QHBoxLayout()
        layout.addLayout(self.system_cards_layout)
        
        # Category breakdown
        category_group = QGroupBox("Category Breakdown")
        category_layout = QVBoxLayout(category_group)
        
        self.category_table = QTableWidget()
        self.category_table.setColumnCount(3)
        self.category_table.setHorizontalHeaderLabels(["Category", "Count", "Percentage"])
        
        # Configure table
        header = self.category_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        self.category_table.setMaximumHeight(200)
        category_layout.addWidget(self.category_table)
        
        layout.addWidget(category_group)
        
        layout.addStretch()
        return widget
    
    def create_details_tab(self) -> QWidget:
        """Create type details tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        controls_layout.addWidget(QLabel("Sort by:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Name", "Category", "Usage", "Last Used"])
        controls_layout.addWidget(self.sort_combo)
        
        controls_layout.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Types", "Custom Only", "Built-in Only"])
        controls_layout.addWidget(self.filter_combo)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Types table
        self.types_table = QTableWidget()
        self.types_table.setColumnCount(6)
        self.types_table.setHorizontalHeaderLabels([
            "Type", "Category", "Usage", "Created", "Last Used", "Custom"
        ])
        
        # Configure table
        header = self.types_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        self.types_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.types_table.setAlternatingRowColors(True)
        self.types_table.setSortingEnabled(True)
        
        layout.addWidget(self.types_table)
        
        return widget
    
    def setup_connections(self):
        """Setup signal connections"""
        self.sort_combo.currentTextChanged.connect(self.update_type_table)
        self.filter_combo.currentTextChanged.connect(self.update_type_table)
        self.types_table.itemSelectionChanged.connect(self.on_type_selection_changed)
    
    def refresh_statistics(self):
        """Refresh all statistics"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Calculate statistics
        self.calculate_statistics()
        
        # Update displays
        self.update_overview_tab()
        self.update_details_tab()
        
        self.progress_bar.setVisible(False)
    
    def calculate_statistics(self):
        """Calculate statistics from type registry"""
        types = self.registry.list_types()
        
        # Calculate basic stats
        total_types = len(types)
        custom_types = sum(1 for t in types.values() if t.is_custom)
        builtin_types = total_types - custom_types
        
        # Count by category
        categories = {}
        for type_def in types.values():
            cat = type_def.category
            categories[cat] = categories.get(cat, 0) + 1
        
        # Store calculated data
        self.statistics_data = {
            'total_types': total_types,
            'custom_types': custom_types,
            'builtin_types': builtin_types,
            'categories': categories,
            'types': types
        }
    
    def update_overview_tab(self):
        """Update overview tab with new data"""
        if not self.statistics_data:
            return
        
        # Clear existing cards
        for i in reversed(range(self.system_cards_layout.count())):
            item = self.system_cards_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)
        
        # Create system statistics cards
        stats = self.statistics_data
        cards_data = [
            ("Total Types", str(stats['total_types']), "Registered", "#0078d4"),
            ("Custom Types", str(stats['custom_types']), "User-defined", "#107c10"),
            ("Built-in", str(stats['builtin_types']), "System types", "#ff8c00"),
            ("Categories", str(len(stats['categories'])), "Unique", "#5c2d91")
        ]
        
        for title, value, subtitle, color in cards_data:
            card = StatisticsCard(title, value, subtitle, color)
            self.system_cards_layout.addWidget(card)
        
        # Update category breakdown
        self.update_category_table()
    
    def update_category_table(self):
        """Update category breakdown table"""
        if not self.statistics_data:
            return
        
        categories = self.statistics_data['categories']
        total = self.statistics_data['total_types']
        
        self.category_table.setRowCount(len(categories))
        
        for row, (category, count) in enumerate(sorted(categories.items())):
            # Category name
            self.category_table.setItem(row, 0, QTableWidgetItem(category.title()))
            
            # Count
            count_item = QTableWidgetItem()
            count_item.setData(Qt.ItemDataRole.DisplayRole, count)
            self.category_table.setItem(row, 1, count_item)
            
            # Percentage
            percentage = (count / total * 100) if total > 0 else 0
            self.category_table.setItem(row, 2, QTableWidgetItem(f"{percentage:.1f}%"))
    
    def update_details_tab(self):
        """Update type details tab"""
        self.update_type_table()
    
    def update_type_table(self):
        """Update the type details table"""
        if not self.statistics_data:
            return
        
        types = self.statistics_data['types']
        
        # Apply filtering
        filtered_types = self.filter_types(types)
        
        # Apply sorting
        sorted_types = self.sort_types(filtered_types)
        
        # Update table
        self.types_table.setRowCount(len(sorted_types))
        
        for row, type_def in enumerate(sorted_types):
            # Type name
            self.types_table.setItem(row, 0, QTableWidgetItem(type_def.name))
            
            # Category
            self.types_table.setItem(row, 1, QTableWidgetItem(type_def.category.title()))
            
            # Usage (placeholder)
            usage_item = QTableWidgetItem()
            usage_item.setData(Qt.ItemDataRole.DisplayRole, 0)  # Placeholder
            self.types_table.setItem(row, 2, usage_item)
            
            # Created
            created = type_def.created_at.strftime("%Y-%m-%d") if type_def.created_at else "Unknown"
            self.types_table.setItem(row, 3, QTableWidgetItem(created))
            
            # Last used (placeholder)
            self.types_table.setItem(row, 4, QTableWidgetItem("Never"))
            
            # Custom
            custom_text = "Yes" if type_def.is_custom else "No"
            custom_item = QTableWidgetItem(custom_text)
            if type_def.is_custom:
                custom_item.setBackground(QColor(220, 248, 198))  # Light green
            self.types_table.setItem(row, 5, custom_item)
            
            # Store type ID for selection
            self.types_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, type_def.type_id)
    
    def filter_types(self, types: Dict[str, TypeDefinition]) -> List[TypeDefinition]:
        """Filter types based on current filter"""
        filter_type = self.filter_combo.currentText()
        types_list = list(types.values())
        
        if filter_type == "Custom Only":
            return [t for t in types_list if t.is_custom]
        elif filter_type == "Built-in Only":
            return [t for t in types_list if not t.is_custom]
        else:  # "All Types"
            return types_list
    
    def sort_types(self, types_list: List[TypeDefinition]) -> List[TypeDefinition]:
        """Sort types based on current sort option"""
        sort_type = self.sort_combo.currentText()
        
        if sort_type == "Name":
            return sorted(types_list, key=lambda t: t.name.lower())
        elif sort_type == "Category":
            return sorted(types_list, key=lambda t: (t.category, t.name))
        elif sort_type == "Usage":
            # Placeholder sort by usage (would need real usage data)
            return sorted(types_list, key=lambda t: t.name)
        elif sort_type == "Last Used":
            # Placeholder sort by last used
            return sorted(types_list, key=lambda t: t.created_at or datetime.min, reverse=True)
        else:
            return types_list
    
    def on_type_selection_changed(self):
        """Handle type selection in table"""
        current_row = self.types_table.currentRow()
        if current_row >= 0:
            item = self.types_table.item(current_row, 0)
            if item:
                type_id = item.data(Qt.ItemDataRole.UserRole)
                if type_id:
                    self.type_selected.emit(type_id)
    
    def get_statistics_summary(self) -> Optional[Dict[str, Any]]:
        """Get current statistics summary"""
        return self.statistics_data
    
    def refresh(self):
        """Refresh statistics data"""
        self.refresh_statistics()