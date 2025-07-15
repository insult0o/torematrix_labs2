"""Type Search Interface

Advanced search and filtering interface for type discovery.
Provides powerful search capabilities with multiple filter options.
"""

from typing import Dict, List, Optional, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QPushButton, QListWidget, QLabel
)
from PyQt6.QtCore import pyqtSignal, QTimer

from torematrix.core.models.types import get_type_registry, TypeRegistry


class TypeSearchInterface(QWidget):
    """Advanced type search interface"""
    
    search_results_changed = pyqtSignal(list)  # List of type_ids
    type_selected = pyqtSignal(str)  # type_id
    
    def __init__(self, registry: TypeRegistry = None, parent=None):
        super().__init__(parent)
        
        self.registry = registry or get_type_registry()
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)
        
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        
        # Search input
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search types...")
        search_layout.addWidget(self.search_input)
        
        # Category filter
        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories", None)
        search_layout.addWidget(self.category_filter)
        
        # Search button
        self.search_btn = QPushButton("Search")
        search_layout.addWidget(self.search_btn)
        
        layout.addLayout(search_layout)
        
        # Results
        self.results_list = QListWidget()
        layout.addWidget(self.results_list)
    
    def setup_connections(self):
        """Setup signal connections"""
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_btn.clicked.connect(self._perform_search)
        self.results_list.itemClicked.connect(self._on_item_clicked)
    
    def _on_search_changed(self, text: str):
        """Handle search text change"""
        self.search_timer.stop()
        self.search_timer.start(300)  # 300ms debounce
    
    def _perform_search(self):
        """Perform search"""
        query = self.search_input.text()
        # Implementation would perform actual search
        results = []
        self.search_results_changed.emit(results)
    
    def _on_item_clicked(self, item):
        """Handle item click"""
        type_id = item.data(0x100)  # UserRole
        if type_id:
            self.type_selected.emit(type_id)