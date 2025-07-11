"""
Qt compatibility layer for TORE Matrix Labs.
Supports both PyQt5 and PySide6.
"""

import sys

# Try to import Qt framework
try:
    # Try PyQt5 first
    from PyQt5.QtWidgets import *
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    QT_FRAMEWORK = "PyQt5"
    
    # PyQt5 specific signals
    pyqtSignal = pyqtSignal
    
except ImportError:
    try:
        # Fallback to PySide6
        from PySide6.QtWidgets import *
        from PySide6.QtCore import *
        from PySide6.QtGui import *
        QT_FRAMEWORK = "PySide6"
        
        # PySide6 uses Signal instead of pyqtSignal
        pyqtSignal = Signal
        
    except ImportError:
        raise ImportError("No Qt framework found. Please install PyQt5 or PySide6.")

# Framework-specific compatibility
if QT_FRAMEWORK == "PyQt5":
    def exec_app(app):
        """Execute Qt application."""
        return app.exec_()
elif QT_FRAMEWORK == "PySide6":
    def exec_app(app):
        """Execute Qt application."""
        return app.exec()

# Export commonly used classes
__all__ = [
    'QApplication', 'QMainWindow', 'QWidget', 'QVBoxLayout', 'QHBoxLayout',
    'QGridLayout', 'QSplitter', 'QTabWidget', 'QStatusBar', 'QMenuBar',
    'QAction', 'QToolBar', 'QDockWidget', 'QTreeWidget', 'QTreeWidgetItem',
    'QTextEdit', 'QLabel', 'QPushButton', 'QProgressBar', 'QMessageBox',
    'QFileDialog', 'QDialog', 'QGroupBox', 'QCheckBox', 'QComboBox',
    'QSpinBox', 'QDoubleSpinBox', 'QListWidget', 'QListWidgetItem',
    'QFrame', 'QTimer', 'Qt', 'QThread', 'QIcon', 'QKeySequence',
    'QPixmap', 'QFont', 'QColor', 'QCoreApplication', 'pyqtSignal', 'exec_app',
    'QT_FRAMEWORK'
]