"""Type Card Widget"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal

from torematrix.core.models.types import TypeDefinition


class TypeCardWidget(QWidget):
    """Card widget for displaying type information"""
    
    clicked = pyqtSignal(str)  # type_id
    
    def __init__(self, type_def: TypeDefinition = None, parent=None):
        super().__init__(parent)
        
        self.type_def = type_def
        self.setup_ui()
    
    def setup_ui(self):
        """Setup card UI"""
        layout = QVBoxLayout(self)
        
        if self.type_def:
            # Type name
            name_label = QLabel(self.type_def.name)
            layout.addWidget(name_label)
            
            # Category
            category_label = QLabel(self.type_def.category)
            layout.addWidget(category_label)
    
    def set_type_definition(self, type_def: TypeDefinition):
        """Set type definition"""
        self.type_def = type_def
        self.setup_ui()