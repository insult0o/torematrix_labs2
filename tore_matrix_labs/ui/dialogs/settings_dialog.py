"""
Settings dialog (stub implementation).
"""

from ..qt_compat import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from ...config.settings import Settings


class SettingsDialog(QDialog):
    """Settings dialog (stub)."""
    
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Settings Dialog - Coming Soon"))
        
        # Buttons
        button_layout = QHBoxLayout()
        
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)