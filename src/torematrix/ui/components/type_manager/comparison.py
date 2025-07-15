"""Type Comparison View

Side-by-side comparison of multiple types for analysis.
"""

from typing import List
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal

from torematrix.core.models.types import get_type_registry, TypeRegistry


class TypeComparisonView(QWidget):
    """Type comparison interface"""
    
    comparison_changed = pyqtSignal(list)  # List of type_ids
    
    def __init__(self, registry: TypeRegistry = None, parent=None):
        super().__init__(parent)
        
        self.registry = registry or get_type_registry()
        self.compared_types: List[str] = []
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Type Comparison")
        layout.addWidget(header)
        
        # Comparison area
        self.comparison_layout = QHBoxLayout()
        layout.addLayout(self.comparison_layout)
    
    def compare_types(self, type_ids: List[str]):
        """Compare specified types"""
        self.compared_types = type_ids
        self._update_comparison()
    
    def _update_comparison(self):
        """Update comparison display"""
        # Clear existing
        while self.comparison_layout.count():
            child = self.comparison_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Add type comparison panels
        for type_id in self.compared_types:
            panel = self._create_type_panel(type_id)
            self.comparison_layout.addWidget(panel)
    
    def _create_type_panel(self, type_id: str) -> QWidget:
        """Create comparison panel for type"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        try:
            type_def = self.registry.get_type(type_id)
            layout.addWidget(QLabel(type_def.name))
            layout.addWidget(QLabel(f"Category: {type_def.category}"))
            layout.addWidget(QLabel(f"Properties: {len(type_def.properties)}"))
        except:
            layout.addWidget(QLabel(f"Error loading {type_id}"))
        
        return panel