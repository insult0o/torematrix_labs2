#!/usr/bin/env python3
"""
Conflict resolution widget for handling auto-detected special areas that conflict with manual validation.
Allows users to resolve conflicts between manual classifications and auto-detected areas.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from ..qt_compat import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QComboBox, QFrame, QPixmap, QSizePolicy, 
    Qt, QMessageBox, QDialog, QButtonGroup, QProgressBar,
    QPainter, QPen, QBrush, QColor, QRectF, QPointF,
    QListWidget, QListWidgetItem, QSplitter, QGroupBox, 
    QTextEdit, pyqtSignal
)

from ...config.settings import Settings
from ...models.document_models import Document


class ConflictItem(QFrame):
    """Widget representing a single auto-detected conflict."""
    
    # Signals
    conflict_resolved = pyqtSignal(str, str)  # conflict_id, resolution
    
    def __init__(self, conflict_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.conflict_data = conflict_data
        self.resolution = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the conflict item UI."""
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            QFrame {
                border: 2px solid #e74c3c;
                border-radius: 8px;
                background-color: #fdf2f2;
                margin: 5px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Header with conflict type and location
        header_layout = QHBoxLayout()
        
        conflict_icon = "⚠️"
        if self.conflict_data['type'] == 'TABLE':
            conflict_icon = "📊"
        elif self.conflict_data['type'] == 'IMAGE':
            conflict_icon = "📷"
        
        header_label = QLabel(f"{conflict_icon} Auto-detected {self.conflict_data['type']} Conflict")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #c0392b;")
        header_layout.addWidget(header_label)
        
        page_label = QLabel(f"Page {self.conflict_data['page'] + 1}")
        page_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        header_layout.addWidget(page_label)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Conflict description
        description = QLabel(self.conflict_data.get('suggestion', 'Conflict detected'))
        description.setWordWrap(True)
        description.setStyleSheet("color: #2c3e50; margin: 5px 0px;")
        layout.addWidget(description)
        
        # Confidence information
        confidence_text = f"Auto-detection confidence: {self.conflict_data.get('auto_confidence', 0.0):.1%}"
        confidence_label = QLabel(confidence_text)
        confidence_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        layout.addWidget(confidence_label)
        
        # Resolution buttons
        resolution_layout = QHBoxLayout()
        
        # Keep manual classification
        self.keep_manual_btn = QPushButton(f"✅ Keep Manual ({self.conflict_data['conflict_with']})")
        self.keep_manual_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.keep_manual_btn.clicked.connect(lambda: self._resolve_conflict('keep_manual'))
        resolution_layout.addWidget(self.keep_manual_btn)
        
        # Use auto-detection
        self.use_auto_btn = QPushButton(f"🔄 Use Auto-detected ({self.conflict_data['type']})")
        self.use_auto_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.use_auto_btn.clicked.connect(lambda: self._resolve_conflict('use_auto'))
        resolution_layout.addWidget(self.use_auto_btn)
        
        # Force text extraction
        self.force_text_btn = QPushButton("📝 Force Text Extraction")
        self.force_text_btn.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        self.force_text_btn.clicked.connect(lambda: self._resolve_conflict('force_text'))
        resolution_layout.addWidget(self.force_text_btn)
        
        layout.addLayout(resolution_layout)
    
    def _resolve_conflict(self, resolution: str):
        """Resolve the conflict with the given resolution."""
        self.resolution = resolution
        
        # Update UI to show resolution
        self.setStyleSheet("""
            QFrame {
                border: 2px solid #27ae60;
                border-radius: 8px;
                background-color: #d5f4e6;
                margin: 5px;
                padding: 10px;
            }
        """)
        
        # Disable buttons
        self.keep_manual_btn.setEnabled(False)
        self.use_auto_btn.setEnabled(False)
        self.force_text_btn.setEnabled(False)
        
        # Add resolution indicator
        resolution_texts = {
            'keep_manual': f"✅ Keeping manual classification: {self.conflict_data['conflict_with']}",
            'use_auto': f"🔄 Using auto-detected: {self.conflict_data['type']}",
            'force_text': "📝 Forcing text extraction (ignoring classifications)"
        }
        
        resolution_label = QLabel(resolution_texts.get(resolution, 'Resolved'))
        resolution_label.setStyleSheet("color: #27ae60; font-weight: bold; margin-top: 5px;")
        self.layout().addWidget(resolution_label)
        
        # Emit signal
        conflict_id = f"{self.conflict_data['page']}_{self.conflict_data['type']}_{id(self.conflict_data)}"
        self.conflict_resolved.emit(conflict_id, resolution)
    
    def get_conflict_data(self) -> Dict[str, Any]:
        """Get the conflict data."""
        return self.conflict_data
    
    def get_resolution(self) -> Optional[str]:
        """Get the current resolution."""
        return self.resolution


class ConflictResolutionWidget(QWidget):
    """Widget for resolving conflicts between manual validation and auto-detection."""
    
    # Signals
    all_conflicts_resolved = pyqtSignal(dict)  # resolutions_dict
    
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # State
        self.conflicts = []
        self.resolutions = {}
        self.current_document = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("🔧 Conflict Resolution")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #e74c3c; margin-bottom: 10px;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Complete button
        self.complete_btn = QPushButton("✅ Complete Resolution")
        self.complete_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.complete_btn.clicked.connect(self._complete_resolution)
        self.complete_btn.setEnabled(False)
        header_layout.addWidget(self.complete_btn)
        
        layout.addLayout(header_layout)
        
        # Instructions
        instructions = QLabel("""
<b>Instructions:</b> Auto-detection found areas that conflict with your manual classifications. 
Please resolve each conflict by choosing the correct classification or forcing text extraction.
        """)
        instructions.setWordWrap(True)
        instructions.setStyleSheet("background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 4px; margin-bottom: 15px;")
        layout.addWidget(instructions)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Conflict list area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: 1px solid #bdc3c7; border-radius: 4px;")
        
        self.conflicts_widget = QWidget()
        self.conflicts_layout = QVBoxLayout(self.conflicts_widget)
        self.conflicts_layout.addStretch()
        
        scroll_area.setWidget(self.conflicts_widget)
        layout.addWidget(scroll_area)
        
        # Status label
        self.status_label = QLabel("No conflicts to resolve")
        self.status_label.setStyleSheet("color: #7f8c8d; font-style: italic; margin-top: 10px;")
        layout.addWidget(self.status_label)
    
    def load_conflicts(self, conflicts: List[Dict[str, Any]], document: Document):
        """Load conflicts for resolution."""
        self.conflicts = conflicts
        self.current_document = document
        self.resolutions = {}
        
        # Clear existing conflict widgets
        for i in reversed(range(self.conflicts_layout.count())):
            child = self.conflicts_layout.itemAt(i).widget()
            if child and isinstance(child, ConflictItem):
                child.deleteLater()
        
        if not conflicts:
            self.status_label.setText("No conflicts detected - manual validation matches auto-detection!")
            self.complete_btn.setEnabled(True)
            self.progress_bar.setValue(100)
            return
        
        self.logger.info(f"Loading {len(conflicts)} conflicts for resolution")
        
        # Create conflict items
        for conflict in conflicts:
            conflict_item = ConflictItem(conflict)
            conflict_item.conflict_resolved.connect(self._on_conflict_resolved)
            
            # Insert before the stretch
            self.conflicts_layout.insertWidget(self.conflicts_layout.count() - 1, conflict_item)
        
        # Update UI
        self.status_label.setText(f"{len(conflicts)} conflicts require resolution")
        self.progress_bar.setMaximum(len(conflicts))
        self.progress_bar.setValue(0)
        self.complete_btn.setEnabled(False)
        
        self.logger.info(f"Conflict resolution interface loaded with {len(conflicts)} conflicts")
    
    def _on_conflict_resolved(self, conflict_id: str, resolution: str):
        """Handle a conflict being resolved."""
        self.resolutions[conflict_id] = resolution
        
        # Update progress
        resolved_count = len(self.resolutions)
        total_count = len(self.conflicts)
        
        self.progress_bar.setValue(resolved_count)
        
        if resolved_count == total_count:
            self.status_label.setText(f"All {total_count} conflicts resolved! ✅")
            self.complete_btn.setEnabled(True)
            self.logger.info(f"All {total_count} conflicts have been resolved")
        else:
            self.status_label.setText(f"{resolved_count}/{total_count} conflicts resolved")
    
    def _complete_resolution(self):
        """Complete the conflict resolution process."""
        if len(self.resolutions) != len(self.conflicts):
            QMessageBox.warning(self, "Incomplete Resolution", 
                              "Please resolve all conflicts before completing.")
            return
        
        # Build resolution data
        resolution_data = {
            'document_id': self.current_document.id if self.current_document else 'unknown',
            'total_conflicts': len(self.conflicts),
            'resolutions': self.resolutions,
            'resolution_summary': {
                'keep_manual': sum(1 for r in self.resolutions.values() if r == 'keep_manual'),
                'use_auto': sum(1 for r in self.resolutions.values() if r == 'use_auto'),
                'force_text': sum(1 for r in self.resolutions.values() if r == 'force_text')
            }
        }
        
        self.logger.info(f"Conflict resolution completed: {resolution_data['resolution_summary']}")
        
        # Emit signal
        self.all_conflicts_resolved.emit(resolution_data)
        
        # Show success message
        QMessageBox.information(self, "Resolution Complete", 
                              f"All {len(self.conflicts)} conflicts have been resolved successfully!")
    
    def get_current_resolutions(self) -> Dict[str, str]:
        """Get current resolutions."""
        return self.resolutions.copy()
    
    def is_resolution_complete(self) -> bool:
        """Check if all conflicts have been resolved."""
        return len(self.resolutions) == len(self.conflicts)


class ConflictResolutionDialog(QDialog):
    """Dialog for conflict resolution."""
    
    def __init__(self, conflicts: List[Dict[str, Any]], document: Document, 
                 settings: Settings, parent=None):
        super().__init__(parent)
        self.conflicts = conflicts
        self.document = document
        self.settings = settings
        self.resolutions = {}
        
        self.setWindowTitle("Resolve Auto-Detection Conflicts")
        self.setModal(True)
        self.setMinimumSize(800, 600)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize dialog UI."""
        layout = QVBoxLayout(self)
        
        # Conflict resolution widget
        self.resolution_widget = ConflictResolutionWidget(self.settings)
        self.resolution_widget.all_conflicts_resolved.connect(self._on_resolution_complete)
        layout.addWidget(self.resolution_widget)
        
        # Load conflicts
        self.resolution_widget.load_conflicts(self.conflicts, self.document)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _on_resolution_complete(self, resolution_data: Dict[str, Any]):
        """Handle resolution completion."""
        self.resolutions = resolution_data
        self.accept()
    
    def get_resolutions(self) -> Dict[str, Any]:
        """Get the resolution results."""
        return self.resolutions