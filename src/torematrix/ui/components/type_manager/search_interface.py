"""Type Search Interface

Advanced search interface for finding and filtering types
with multiple criteria and quick filters.
"""

from typing import List, Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QComboBox, QCheckBox, QListWidget, QListWidgetItem,
    QFrame, QGroupBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from torematrix.core.models.types import TypeRegistry, TypeDefinition, get_type_registry


class TypeSearchInterface(QWidget):
    """Advanced type search interface"""
    
    type_selected = pyqtSignal(str)  # type_id
    search_results_changed = pyqtSignal(list)  # List of matching type IDs
    
    def __init__(self, registry: TypeRegistry = None, parent=None):
        super().__init__(parent)
        
        self.registry = registry or get_type_registry()
        self.search_results: List[str] = []
        
        self.setup_ui()
        self.connect_signals()
        self.perform_initial_search()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Search input
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search types...")
        search_layout.addWidget(self.search_input)
        
        clear_btn = QPushButton("✕")
        clear_btn.setFixedSize(24, 24)
        clear_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(clear_btn)
        
        layout.addLayout(search_layout)
        
        # Quick filters
        filters_group = QGroupBox("Quick Filters")
        filters_layout = QHBoxLayout(filters_group)
        
        self.all_btn = QPushButton("All")
        self.all_btn.setCheckable(True)
        self.all_btn.setChecked(True)
        filters_layout.addWidget(self.all_btn)
        
        self.custom_btn = QPushButton("Custom")
        self.custom_btn.setCheckable(True)
        filters_layout.addWidget(self.custom_btn)
        
        self.builtin_btn = QPushButton("Built-in")
        self.builtin_btn.setCheckable(True)
        filters_layout.addWidget(self.builtin_btn)
        
        filters_layout.addStretch()
        layout.addWidget(filters_group)
        
        # Advanced filters
        advanced_group = QGroupBox("Filters")
        advanced_layout = QVBoxLayout(advanced_group)
        
        # Category filter
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories")
        self.populate_categories()
        category_layout.addWidget(self.category_combo)
        advanced_layout.addLayout(category_layout)
        
        # Property filters
        self.has_children_cb = QCheckBox("Has child types")
        advanced_layout.addWidget(self.has_children_cb)
        
        self.has_parents_cb = QCheckBox("Has parent types")
        advanced_layout.addWidget(self.has_parents_cb)
        
        layout.addWidget(advanced_group)
        
        # Results
        results_layout = QVBoxLayout()
        
        # Results header
        results_header = QHBoxLayout()
        results_header.addWidget(QLabel("Search Results"))
        
        self.results_count = QLabel("0 types found")
        self.results_count.setStyleSheet("color: #666; font-style: italic;")
        results_header.addWidget(self.results_count)
        results_header.addStretch()
        
        results_layout.addLayout(results_header)
        
        # Results list
        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.on_result_selected)
        results_layout.addWidget(self.results_list)
        
        layout.addLayout(results_layout)
    
    def populate_categories(self):
        """Populate category combo box"""
        categories = set()
        for type_def in self.registry.list_types().values():
            categories.add(type_def.category)
        
        for category in sorted(categories):
            self.category_combo.addItem(category.title(), category)
    
    def connect_signals(self):
        """Connect UI signals"""
        # Search with debouncing
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        self.search_input.textChanged.connect(lambda: self.search_timer.start(300))
        
        # Quick filter buttons
        self.all_btn.clicked.connect(self.on_filter_changed)
        self.custom_btn.clicked.connect(self.on_filter_changed)
        self.builtin_btn.clicked.connect(self.on_filter_changed)
        
        # Advanced filters
        self.category_combo.currentTextChanged.connect(self.perform_search)
        self.has_children_cb.toggled.connect(self.perform_search)
        self.has_parents_cb.toggled.connect(self.perform_search)
    
    def perform_initial_search(self):
        """Perform initial search to show all types"""
        self.perform_search()
    
    def perform_search(self):
        """Perform search with current criteria"""
        query = self.search_input.text().strip().lower()
        all_types = list(self.registry.list_types().values())
        
        # Filter by search query
        if query:
            filtered_types = [t for t in all_types if self.matches_query(t, query)]
        else:
            filtered_types = all_types
        
        # Apply quick filters
        if self.custom_btn.isChecked() and not self.all_btn.isChecked():
            filtered_types = [t for t in filtered_types if t.is_custom]
        elif self.builtin_btn.isChecked() and not self.all_btn.isChecked():
            filtered_types = [t for t in filtered_types if not t.is_custom]
        
        # Apply category filter
        category = self.category_combo.currentData()
        if category:
            filtered_types = [t for t in filtered_types if t.category == category]
        
        # Apply property filters
        if self.has_children_cb.isChecked():
            filtered_types = [t for t in filtered_types if t.child_types]
        
        if self.has_parents_cb.isChecked():
            filtered_types = [t for t in filtered_types if t.parent_types]
        
        # Update results
        self.search_results = [t.type_id for t in filtered_types]
        self.update_results_display(filtered_types)
        self.search_results_changed.emit(self.search_results)
    
    def matches_query(self, type_def: TypeDefinition, query: str) -> bool:
        """Check if type matches search query"""
        searchable_text = " ".join([
            type_def.name.lower(),
            type_def.category.lower(),
            type_def.description.lower() if type_def.description else "",
            " ".join(type_def.tags).lower()
        ])
        
        # Support multiple search terms
        query_terms = query.split()
        return all(term in searchable_text for term in query_terms)
    
    def update_results_display(self, types: List[TypeDefinition]):
        """Update results display"""
        self.results_list.clear()
        
        # Update count
        count = len(types)
        self.results_count.setText(f"{count} type{'s' if count != 1 else ''} found")
        
        # Add results to list
        for type_def in types:
            item = QListWidgetItem()
            item.setText(type_def.name)
            item.setData(Qt.ItemDataRole.UserRole, type_def.type_id)
            
            # Set tooltip
            tooltip = f"{type_def.name}\n{type_def.description or 'No description'}\nCategory: {type_def.category}"
            if type_def.tags:
                tooltip += f"\nTags: {', '.join(type_def.tags)}"
            item.setToolTip(tooltip)
            
            # Visual indicator for custom types
            if type_def.is_custom:
                item.setForeground(Qt.GlobalColor.blue)
            
            self.results_list.addItem(item)
    
    def on_filter_changed(self):
        """Handle quick filter button changes"""
        sender = self.sender()
        
        # Handle mutual exclusivity
        if sender == self.all_btn and self.all_btn.isChecked():
            self.custom_btn.setChecked(False)
            self.builtin_btn.setChecked(False)
        elif sender in [self.custom_btn, self.builtin_btn]:
            if sender.isChecked():
                self.all_btn.setChecked(False)
            else:
                # If both custom and builtin are unchecked, check all
                if not self.custom_btn.isChecked() and not self.builtin_btn.isChecked():
                    self.all_btn.setChecked(True)
        
        self.perform_search()
    
    def on_result_selected(self, item: QListWidgetItem):
        """Handle result selection"""
        type_id = item.data(Qt.ItemDataRole.UserRole)
        if type_id:
            self.type_selected.emit(type_id)
    
    def clear_search(self):
        """Clear search input"""
        self.search_input.clear()
        self.perform_search()
    
    def get_search_results(self) -> List[str]:
        """Get current search results"""
        return self.search_results.copy()
    
    def refresh(self):
        """Refresh search interface"""
        self.populate_categories()
        self.perform_search()