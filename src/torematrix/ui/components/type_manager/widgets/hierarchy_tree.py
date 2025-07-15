"""Hierarchy Tree Widget"""

from PyQt6.QtWidgets import QTreeWidget
from PyQt6.QtCore import pyqtSignal

from torematrix.core.models.types import get_type_registry, TypeRegistry


class HierarchyTreeWidget(QTreeWidget):
    """Specialized hierarchy tree widget"""
    
    type_selected = pyqtSignal(str)
    
    def __init__(self, registry: TypeRegistry = None, parent=None):
        super().__init__(parent)
        
        self.registry = registry or get_type_registry()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup tree widget"""
        self.setHeaderLabels(["Type", "Category"])
        self.setAlternatingRowColors(True)