"""Enhanced Type Selector Widget"""

from PyQt6.QtWidgets import QComboBox
from PyQt6.QtCore import pyqtSignal

from torematrix.core.models.types import get_type_registry, TypeRegistry


class EnhancedTypeSelectorWidget(QComboBox):
    """Enhanced type selector with advanced features"""
    
    type_selected = pyqtSignal(str)
    
    def __init__(self, registry: TypeRegistry = None, parent=None):
        super().__init__(parent)
        
        self.registry = registry or get_type_registry()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup enhanced UI"""
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        
        # Load types
        types = self.registry.list_types()
        for type_def in types.values():
            self.addItem(type_def.name, type_def.type_id)