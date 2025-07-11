"""
About dialog (stub implementation).
"""

from ..qt_compat import QDialog, QVBoxLayout, QLabel, QPushButton, Qt


class AboutDialog(QDialog):
    """About dialog (stub)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("About TORE Matrix Labs")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        title = QLabel("TORE Matrix Labs")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        version = QLabel("Version 1.0.0")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
        
        description = QLabel("Ultimate AI Document Processing Pipeline\nfor ICAO/ATC Procedural Documents")
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("margin: 20px;")
        layout.addWidget(description)
        
        copyright_label = QLabel("© 2024 TORE AI")
        copyright_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_label)
        
        # OK button
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)