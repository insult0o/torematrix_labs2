"""Advanced Search Bar Widget"""

from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtCore import pyqtSignal


class AdvancedSearchBar(QLineEdit):
    """Advanced search bar with filtering"""
    
    search_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup search bar UI"""
        self.setPlaceholderText("Search types...")
        self.textChanged.connect(self.search_changed.emit)