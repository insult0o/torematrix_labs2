"""Icon Browser Widget"""

from PyQt6.QtWidgets import QWidget


class IconBrowserWidget(QWidget):
    """Icon browser and selection widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup icon browser UI"""
        pass