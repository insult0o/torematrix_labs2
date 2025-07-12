#!/usr/bin/env python3
"""
Manual validation widget for page-by-page IMAGE/TABLE/DIAGRAM classification.
Users drag to select areas and classify them before text extraction.
"""

import logging
import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json
import os
from datetime import datetime

from ..qt_compat import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QComboBox, QFrame, QPixmap, QSizePolicy, 
    Qt, QMessageBox, QDialog, QButtonGroup, QProgressBar,
    QPainter, QPen, QBrush, QColor, QRectF, QPointF,
    QMouseEvent, QKeyEvent, QListWidget, QListWidgetItem,
    QSplitter, QGroupBox, QTextEdit, QLineEdit,
    pyqtSignal
)

from ...config.settings import Settings
from ...models.document_models import Document


class ClassificationDialog(QDialog):
    """Enhanced dialog for classifying selected areas with specialized processing options."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Classify Selected Area - Enhanced Detection")
        self.setModal(True)
        self.setFixedSize(500, 450)
        
        # Result storage
        self.selected_type = None
        self.processing_options = {}
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the enhanced dialog UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("What type of specialized content is this area?")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Enhanced classification buttons with descriptions
        button_layout = QVBoxLayout()
        
        # IMAGE button with description
        image_layout = QHBoxLayout()
        self.image_btn = QPushButton("📷 IMAGE")
        self.image_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 15px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 5px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.image_btn.clicked.connect(lambda: self._select_type("IMAGE"))
        image_layout.addWidget(self.image_btn)
        
        image_desc = QLabel("Photos, illustrations, screenshots, figures with captions")
        image_desc.setStyleSheet("color: #7f8c8d; font-size: 11px; margin-left: 10px;")
        image_layout.addWidget(image_desc)
        button_layout.addLayout(image_layout)
        
        # TABLE button with description
        table_layout = QHBoxLayout()
        self.table_btn = QPushButton("📊 TABLE")
        self.table_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 15px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 5px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.table_btn.clicked.connect(lambda: self._select_type("TABLE"))
        table_layout.addWidget(self.table_btn)
        
        table_desc = QLabel("Data tables, matrices, structured data with headers/footers")
        table_desc.setStyleSheet("color: #7f8c8d; font-size: 11px; margin-left: 10px;")
        table_layout.addWidget(table_desc)
        button_layout.addLayout(table_layout)
        
        # DIAGRAM button with description
        diagram_layout = QHBoxLayout()
        self.diagram_btn = QPushButton("📈 DIAGRAM")
        self.diagram_btn.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                padding: 15px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 5px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        self.diagram_btn.clicked.connect(lambda: self._select_type("DIAGRAM"))
        diagram_layout.addWidget(self.diagram_btn)
        
        diagram_desc = QLabel("Charts, flowcharts, technical drawings, schematic diagrams")
        diagram_desc.setStyleSheet("color: #7f8c8d; font-size: 11px; margin-left: 10px;")
        diagram_layout.addWidget(diagram_desc)
        button_layout.addLayout(diagram_layout)
        
        # CHART button (new specialized type)
        chart_layout = QHBoxLayout()
        self.chart_btn = QPushButton("📊 CHART")
        self.chart_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border: none;
                padding: 15px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 5px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        self.chart_btn.clicked.connect(lambda: self._select_type("CHART"))
        chart_layout.addWidget(self.chart_btn)
        
        chart_desc = QLabel("Graphs, plots, statistical charts, data visualizations")
        chart_desc.setStyleSheet("color: #7f8c8d; font-size: 11px; margin-left: 10px;")
        chart_layout.addWidget(chart_desc)
        button_layout.addLayout(chart_layout)
        
        # COMPLEX button (new specialized type)
        complex_layout = QHBoxLayout()
        self.complex_btn = QPushButton("🔧 COMPLEX")
        self.complex_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                color: white;
                border: none;
                padding: 15px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 5px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #2c3e50;
            }
        """)
        self.complex_btn.clicked.connect(lambda: self._select_type("COMPLEX"))
        complex_layout.addWidget(self.complex_btn)
        
        complex_desc = QLabel("Multi-column layouts, mixed content, special formatting")
        complex_desc.setStyleSheet("color: #7f8c8d; font-size: 11px; margin-left: 10px;")
        complex_layout.addWidget(complex_desc)
        button_layout.addLayout(complex_layout)
        
        layout.addLayout(button_layout)
        
        # Processing options (new section)
        options_group = QGroupBox("Processing Options")
        options_layout = QVBoxLayout(options_group)
        
        # Reading order priority
        self.reading_order_high = QWidget()
        reading_order_layout = QHBoxLayout(self.reading_order_high)
        reading_order_layout.setContentsMargins(0, 0, 0, 0)
        
        from ..qt_compat import QCheckBox
        self.high_priority_check = QCheckBox("High Priority for Reading Order")
        self.high_priority_check.setStyleSheet("font-size: 11px; color: #2c3e50;")
        reading_order_layout.addWidget(self.high_priority_check)
        
        # Include context
        self.include_context_check = QCheckBox("Include Surrounding Context")
        self.include_context_check.setStyleSheet("font-size: 11px; color: #2c3e50;")
        reading_order_layout.addWidget(self.include_context_check)
        
        options_layout.addWidget(self.reading_order_high)
        
        # Special handling notes
        notes_label = QLabel("Special Notes:")
        notes_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #2c3e50; margin-top: 10px;")
        options_layout.addWidget(notes_label)
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(60)
        self.notes_edit.setPlaceholderText("Optional: Notes about special handling requirements...")
        self.notes_edit.setStyleSheet("font-size: 11px; border: 1px solid #bdc3c7; border-radius: 3px;")
        options_layout.addWidget(self.notes_edit)
        
        layout.addWidget(options_group)
        
        # System info
        note_label = QLabel("Area names and IDs are automatically generated by the system.")
        note_label.setStyleSheet("margin-top: 10px; color: #7f8c8d; font-style: italic; font-size: 11px;")
        layout.addWidget(note_label)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        action_layout.addWidget(cancel_btn)
        
        action_layout.addStretch()
        
        layout.addLayout(action_layout)
    
    def _select_type(self, type_name: str):
        """Handle type selection and gather processing options."""
        self.selected_type = type_name
        
        # Gather processing options
        self.processing_options = {
            'high_priority': self.high_priority_check.isChecked(),
            'include_context': self.include_context_check.isChecked(),
            'special_notes': self.notes_edit.toPlainText().strip()
        }
        
        self.accept()


class DragSelectPDFViewer(QWidget):
    """PDF viewer with drag-to-select rectangular areas functionality."""
    
    # Signals
    area_selected = pyqtSignal(dict)  # Emitted when area is selected and classified
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        
        # Document state
        self.current_document: Optional[fitz.Document] = None
        self.current_page = 1  # Start from page 1, not 0
        self.total_pages = 0
        self.zoom_level = 1.0
        self.current_file_path: Optional[str] = None
        
        # Selection state
        self.is_selecting = False
        self.selection_start: Optional[QPointF] = None
        self.selection_end: Optional[QPointF] = None
        self.current_selections: List[Dict] = []  # Current page selections
        
        # UI components
        self.page_label = None
        self.scroll_area = None
        
        self._init_ui()
        self.logger.info("Drag-select PDF viewer initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Create header with controls
        self._create_header(layout)
        
        # Create main viewing area
        self._create_viewer_area(layout)
        
        # Create navigation footer
        self._create_navigation_footer(layout)
        
        # Initially show empty state
        self._show_empty_state()
    
    def _create_header(self, parent_layout):
        """Create header with document info and controls."""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_layout = QVBoxLayout()
        
        # Document title
        self.doc_title_label = QLabel("Manual Validation - Drag to Select Areas")
        self.doc_title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(self.doc_title_label)
        
        # Controls row
        controls_layout = QHBoxLayout()
        
        # Zoom controls
        zoom_label = QLabel("Zoom:")
        controls_layout.addWidget(zoom_label)
        
        self.zoom_combo = QComboBox()
        self.zoom_combo.addItems(["50%", "75%", "100%", "125%", "150%", "200%", "Fit Width", "Fit Page"])
        self.zoom_combo.setCurrentText("100%")
        self.zoom_combo.currentTextChanged.connect(self._on_zoom_changed)
        controls_layout.addWidget(self.zoom_combo)
        
        controls_layout.addStretch()
        
        # Page info
        self.page_info_label = QLabel("No document")
        controls_layout.addWidget(self.page_info_label)
        
        header_layout.addLayout(controls_layout)
        header_frame.setLayout(header_layout)
        parent_layout.addWidget(header_frame)
    
    def _create_viewer_area(self, parent_layout):
        """Create main viewing area with scrollbars."""
        # Create scroll area for page display
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        
        # Create page display label
        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setStyleSheet("border: 1px solid #bdc3c7; background-color: white;")
        self.page_label.setMinimumSize(400, 500)
        self.page_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Enable mouse tracking for selection
        self.page_label.setMouseTracking(True)
        self.page_label.mousePressEvent = self._on_mouse_press
        self.page_label.mouseMoveEvent = self._on_mouse_move
        self.page_label.mouseReleaseEvent = self._on_mouse_release
        self.page_label.paintEvent = self._on_paint_event
        
        self.scroll_area.setWidget(self.page_label)
        parent_layout.addWidget(self.scroll_area)
    
    def _create_navigation_footer(self, parent_layout):
        """Create navigation footer with page controls."""
        footer_frame = QFrame()
        footer_frame.setFrameStyle(QFrame.StyledPanel)
        footer_layout = QHBoxLayout()
        
        # Previous page button
        self.prev_btn = QPushButton("◀ Previous")
        self.prev_btn.clicked.connect(self._prev_page)
        self.prev_btn.setEnabled(False)
        footer_layout.addWidget(self.prev_btn)
        
        # Page indicator
        self.page_indicator = QLabel("Page 1 of 1")
        self.page_indicator.setAlignment(Qt.AlignCenter)
        self.page_indicator.setStyleSheet("font-weight: bold; padding: 5px;")
        footer_layout.addWidget(self.page_indicator)
        
        # Next page button
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.clicked.connect(self._next_page)
        self.next_btn.setEnabled(False)
        footer_layout.addWidget(self.next_btn)
        
        footer_layout.addStretch()
        
        # Selection info
        self.selection_info = QLabel("0 areas selected")
        self.selection_info.setStyleSheet("color: #7f8c8d; font-style: italic;")
        footer_layout.addWidget(self.selection_info)
        
        footer_frame.setLayout(footer_layout)
        parent_layout.addWidget(footer_frame)
    
    def _show_empty_state(self):
        """Show empty state when no document is loaded."""
        self.page_label.setText("No document loaded\n\nLoad a document to begin manual validation")
        self.page_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #bdc3c7;
                background-color: #f8f9fa;
                color: #7f8c8d;
                font-size: 14px;
                padding: 40px;
            }
        """)
    
    def load_document(self, file_path: str):
        """Load a PDF document for manual validation."""
        try:
            self.current_file_path = file_path
            self.current_document = fitz.open(file_path)
            self.total_pages = len(self.current_document)
            self.current_page = 1  # Start from page 1
            self.current_selections = []
            
            # Update UI
            self.doc_title_label.setText(f"Manual Validation - {Path(file_path).name}")
            self.page_info_label.setText(f"Page {self.current_page} of {self.total_pages}")
            
            # Enable navigation
            self._update_navigation_buttons()
            
            # Load first page
            self._load_current_page()
            
            self.logger.info(f"Loaded document: {file_path} ({self.total_pages} pages)")
            
        except Exception as e:
            self.logger.error(f"Error loading document: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load document: {e}")
    
    def _load_current_page(self):
        """Load and display the current page."""
        if not self.current_document:
            return
        
        try:
            # Get page (convert 1-based to 0-based for PyMuPDF)
            page = self.current_document[self.current_page - 1]
            
            # Calculate zoom
            zoom_matrix = fitz.Matrix(self.zoom_level, self.zoom_level)
            
            # Render page
            pix = page.get_pixmap(matrix=zoom_matrix)
            img_data = pix.tobytes("ppm")
            
            # Create QPixmap
            pixmap = QPixmap()
            pixmap.loadFromData(img_data)
            
            # Set pixmap
            self.page_label.setPixmap(pixmap)
            self.page_label.setFixedSize(pixmap.size())
            
            # Update page indicator
            self.page_indicator.setText(f"Page {self.current_page} of {self.total_pages}")
            
            # Update selection info
            self._update_selection_info()
            
        except Exception as e:
            self.logger.error(f"Error loading page: {e}")
    
    def _on_zoom_changed(self, zoom_text: str):
        """Handle zoom level changes."""
        try:
            if zoom_text.endswith('%'):
                self.zoom_level = float(zoom_text[:-1]) / 100.0
            elif zoom_text == "Fit Width":
                self.zoom_level = 1.0  # TODO: Calculate based on widget width
            elif zoom_text == "Fit Page":
                self.zoom_level = 0.8  # TODO: Calculate based on widget size
            
            self._load_current_page()
            
        except Exception as e:
            self.logger.error(f"Error changing zoom: {e}")
    
    def _prev_page(self):
        """Go to previous page."""
        if self.current_page > 1:
            self.current_page -= 1
            self._load_current_page()
            self._load_page_areas()  # Load persistent areas for this page
            self._update_navigation_buttons()
    
    def _next_page(self):
        """Go to next page."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._load_current_page()
            self._load_page_areas()  # Load persistent areas for this page
            self._update_navigation_buttons()
    
    def _load_page_areas(self):
        """Load persistent areas for the current page."""
        try:
            if hasattr(self, 'area_storage_manager') and self.area_storage_manager and hasattr(self, 'current_document_id'):
                # Get areas for current page
                page_areas = self.area_storage_manager.get_areas_for_page(self.current_document_id, self.current_page)
                
                # Convert to current_selections format
                self.current_selections = []
                for area_id, area_data in page_areas.items():
                    # Convert area data to selection format
                    selection = {
                        'id': area_id,
                        'bbox': area_data.get('bbox', {}),
                        'page': self.current_page,
                        'type': area_data.get('type', 'unknown'),
                        'content': area_data.get('content', ''),
                        'name': area_data.get('name', f'Area {area_id}')
                    }
                    self.current_selections.append(selection)
                
                self.logger.info(f"MANUAL VALIDATION: Loaded {len(self.current_selections)} areas for page {self.current_page}")
                self._update_selection_info()
            else:
                # Clear selections if no storage manager or document
                self.current_selections = []
                self._update_selection_info()
                
        except Exception as e:
            self.logger.error(f"Error loading page areas: {e}")
            self.current_selections = []
            self._update_selection_info()
    
    def _update_navigation_buttons(self):
        """Update navigation button states."""
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)
    
    def _update_selection_info(self):
        """Update selection information display."""
        count = len(self.current_selections)
        if count == 0:
            self.selection_info.setText("0 areas selected - Drag to select IMAGE/TABLE/DIAGRAM areas")
        elif count == 1:
            self.selection_info.setText("1 area selected")
        else:
            self.selection_info.setText(f"{count} areas selected")
    
    def _on_mouse_press(self, event: QMouseEvent):
        """Handle mouse press for selection start."""
        if event.button() == Qt.LeftButton:
            self.is_selecting = True
            self.selection_start = QPointF(event.pos())
            self.selection_end = QPointF(event.pos())
    
    def _on_mouse_move(self, event: QMouseEvent):
        """Handle mouse move for selection update."""
        if self.is_selecting:
            self.selection_end = QPointF(event.pos())
            self.page_label.update()  # Trigger repaint
    
    def _on_mouse_release(self, event: QMouseEvent):
        """Handle mouse release for selection completion."""
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False
            self.selection_end = QPointF(event.pos())
            
            # Check if selection is large enough
            if (abs(self.selection_end.x() - self.selection_start.x()) > 10 and
                abs(self.selection_end.y() - self.selection_start.y()) > 10):
                
                # Show classification dialog
                self._show_classification_dialog()
            else:
                # Selection too small, clear it
                self.selection_start = None
                self.selection_end = None
                self.page_label.update()
    
    def _on_paint_event(self, event):
        """Handle paint event to draw selections."""
        # Call original paint event
        QLabel.paintEvent(self.page_label, event)
        
        # Draw current selection
        if self.is_selecting and self.selection_start and self.selection_end:
            painter = QPainter(self.page_label)
            painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(255, 0, 0, 50)))
            
            rect = QRectF(self.selection_start, self.selection_end).normalized()
            painter.drawRect(rect)
            
            painter.end()
        
        # Draw saved selections
        if self.current_selections:
            painter = QPainter(self.page_label)
            
            for selection in self.current_selections:
                # Enhanced color based on type
                if selection['type'] == 'IMAGE':
                    color = QColor(52, 152, 219)  # Blue
                elif selection['type'] == 'TABLE':
                    color = QColor(231, 76, 60)  # Red
                elif selection['type'] == 'DIAGRAM':
                    color = QColor(243, 156, 18)  # Orange
                elif selection['type'] == 'CHART':
                    color = QColor(155, 89, 182)  # Purple
                elif selection['type'] == 'COMPLEX':
                    color = QColor(52, 73, 94)  # Dark blue-gray
                else:
                    color = QColor(128, 128, 128)  # Gray
                
                # Enhance visual feedback for high priority items
                line_width = 3 if selection.get('high_priority', False) else 2
                line_style = Qt.SolidLine if selection.get('high_priority', False) else Qt.DashLine
                
                painter.setPen(QPen(color, line_width, line_style))
                painter.setBrush(QBrush(color.lighter(180)))
                
                rect = QRectF(selection['ui_rect']['x'], selection['ui_rect']['y'],
                            selection['ui_rect']['width'], selection['ui_rect']['height'])
                painter.drawRect(rect)
                
                # Draw type label with priority indicator
                painter.setPen(QPen(QColor(255, 255, 255), 1))
                type_text = selection['type']
                if selection.get('high_priority', False):
                    type_text = f"⚡ {type_text}"
                painter.drawText(rect.topLeft() + QPointF(5, 15), type_text)
                
                # Draw special notes indicator if present
                if selection.get('special_notes'):
                    painter.setPen(QPen(QColor(255, 255, 0), 1))
                    painter.drawText(rect.topLeft() + QPointF(5, 30), "📝 Notes")
            
            painter.end()
    
    def _show_classification_dialog(self):
        """Show enhanced dialog to classify the selected area."""
        dialog = ClassificationDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # Convert selection to PDF coordinates
            pdf_rect = self._ui_to_pdf_coords(self.selection_start, self.selection_end)
            
            # Create enhanced selection data with processing options
            selection_data = {
                'id': f"snippet_{self.current_page}_{len(self.current_selections)}_{int(datetime.now().timestamp())}",
                'type': dialog.selected_type,
                'page': self.current_page,  # Already 1-based page numbering
                'bbox': pdf_rect,
                'ui_rect': {
                    'x': min(self.selection_start.x(), self.selection_end.x()),
                    'y': min(self.selection_start.y(), self.selection_end.y()),
                    'width': abs(self.selection_end.x() - self.selection_start.x()),
                    'height': abs(self.selection_end.y() - self.selection_start.y())
                },
                # Enhanced processing options
                'processing_options': dialog.processing_options,
                'high_priority': dialog.processing_options.get('high_priority', False),
                'include_context': dialog.processing_options.get('include_context', False),
                'special_notes': dialog.processing_options.get('special_notes', ''),
                # System generated metadata
                'created_at': datetime.now().isoformat(),
                'specialized_type': dialog.selected_type  # For new types like CHART, COMPLEX
            }
            
            # Add to current selections
            self.current_selections.append(selection_data)
            
            # Update display
            self._update_selection_info()
            self.page_label.update()
            
            # Emit signal
            self.area_selected.emit(selection_data)
            
            self.logger.info(f"Enhanced area classified as {dialog.selected_type} on page {self.current_page}")
            if dialog.processing_options.get('special_notes'):
                self.logger.info(f"Special notes: {dialog.processing_options['special_notes']}")
        
        # Clear selection
        self.selection_start = None
        self.selection_end = None
        self.page_label.update()
    
    def _ui_to_pdf_coords(self, start_point: QPointF, end_point: QPointF) -> List[float]:
        """Convert UI coordinates to PDF coordinates."""
        if not self.current_document:
            return [0, 0, 0, 0]
        
        try:
            # Get page dimensions (convert 1-based to 0-based for PyMuPDF)
            page = self.current_document[self.current_page - 1]
            page_rect = page.rect
            
            # Get UI dimensions
            pixmap = self.page_label.pixmap()
            if not pixmap:
                return [0, 0, 0, 0]
            
            ui_width = pixmap.width()
            ui_height = pixmap.height()
            
            # Calculate scale factors
            scale_x = page_rect.width / ui_width
            scale_y = page_rect.height / ui_height
            
            # Convert coordinates
            x1 = min(start_point.x(), end_point.x()) * scale_x
            y1 = min(start_point.y(), end_point.y()) * scale_y
            x2 = max(start_point.x(), end_point.x()) * scale_x
            y2 = max(start_point.y(), end_point.y()) * scale_y
            
            return [x1, y1, x2, y2]
            
        except Exception as e:
            self.logger.error(f"Error converting coordinates: {e}")
            return [0, 0, 0, 0]


class ManualValidationWidget(QWidget):
    """Main manual validation widget with PDF viewer and controls."""
    
    # Signals
    validation_completed = pyqtSignal(dict)  # Emitted when validation is complete
    status_message = pyqtSignal(str)
    
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # State
        self.current_document: Optional[Document] = None
        self.current_file_path: Optional[str] = None
        self.all_selections: Dict[int, List[Dict]] = {}  # Page -> selections mapping
        self.validation_complete = False
        
        self._init_ui()
        self.logger.info("Manual validation widget initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Manual Page Verification - Enhanced Special Areas Detection")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Progress info
        self.progress_label = QLabel("No document loaded")
        self.progress_label.setStyleSheet("color: #7f8c8d;")
        header_layout.addWidget(self.progress_label)
        
        layout.addLayout(header_layout)
        
        # Removed enhanced special areas detection section - space now available for area preview
        
        # Area image preview (expanded - takes space from removed page navigation)
        self._create_area_preview_section(layout)
        
        # Selection management panel (enhanced)
        self._create_selection_panel(layout)
        
        # Footer with validation controls
        self._create_validation_footer(layout)
    
    
    def _create_selection_panel(self, parent_layout):
        """Create the selection management panel."""
        # Selected Areas Section
        areas_group = QGroupBox("Selected Areas")
        areas_layout = QVBoxLayout(areas_group)
        
        # Area navigation and statistics
        nav_layout = QHBoxLayout()
        
        # Area navigation controls (replaces page navigation)
        self.prev_area_btn = QPushButton("◀ Previous Area")
        self.prev_area_btn.setEnabled(False)
        nav_layout.addWidget(self.prev_area_btn)
        
        self.area_info_label = QLabel("0 areas selected")
        self.area_info_label.setAlignment(Qt.AlignCenter)
        self.area_info_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        nav_layout.addWidget(self.area_info_label)
        
        self.next_area_btn = QPushButton("Next Area ▶")
        self.next_area_btn.setEnabled(False)
        nav_layout.addWidget(self.next_area_btn)
        
        areas_layout.addLayout(nav_layout)
        
        # Statistics
        self.stats_label = QLabel("No selections yet")
        self.stats_label.setStyleSheet("color: #7f8c8d; margin: 5px; text-align: center;")
        self.stats_label.setAlignment(Qt.AlignCenter)
        areas_layout.addWidget(self.stats_label)
        
        # Selection list with delete functionality
        list_layout = QVBoxLayout()
        
        list_header = QLabel("Area List:")
        list_header.setStyleSheet("font-weight: bold; margin-top: 10px;")
        list_layout.addWidget(list_header)
        
        self.selection_list = QListWidget()
        self.selection_list.setMaximumHeight(120)  # Shortened to make room for preview
        self.selection_list.setMinimumHeight(80)
        self.selection_list.itemClicked.connect(self._on_area_clicked)
        list_layout.addWidget(self.selection_list)
        
        # Area management controls
        area_controls_layout = QHBoxLayout()
        
        self.delete_area_btn = QPushButton("🗑️ Delete Selected Area")
        self.delete_area_btn.setEnabled(False)
        self.delete_area_btn.clicked.connect(self._delete_selected_area)
        area_controls_layout.addWidget(self.delete_area_btn)
        
        area_controls_layout.addStretch()
        
        self.clear_all_btn = QPushButton("Clear All Special Areas")
        self.clear_all_btn.setEnabled(False)
        self.clear_all_btn.clicked.connect(self._clear_all_areas)
        area_controls_layout.addWidget(self.clear_all_btn)
        
        list_layout.addLayout(area_controls_layout)
        areas_layout.addLayout(list_layout)
        
        parent_layout.addWidget(areas_group)
        
        # Connect navigation buttons
        self.prev_area_btn.clicked.connect(self._navigate_previous_area)
        self.next_area_btn.clicked.connect(self._navigate_next_area)
    
    def _create_area_preview_section(self, parent_layout):
        """Create the area image preview section (most prominent)."""
        preview_group = QGroupBox("📷 Enhanced Area Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        # Preview image display (MAXIMIZED - using space from removed page navigation section)
        self.area_preview_label = QLabel()
        self.area_preview_label.setMinimumHeight(650)  # Expanded from 550 to 650
        self.area_preview_label.setMaximumHeight(850)  # Expanded from 750 to 850
        self.area_preview_label.setStyleSheet("""
            QLabel {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                background-color: #ecf0f1;
                text-align: center;
                color: #7f8c8d;
                font-size: 14px;
            }
        """)
        self.area_preview_label.setAlignment(Qt.AlignCenter)
        self.area_preview_label.setText("No area selected\n\nSelect an area from the list below\nor drag to select a new area")
        self.area_preview_label.setScaledContents(True)
        preview_layout.addWidget(self.area_preview_label)
        
        # Area info below preview
        self.preview_info_label = QLabel("Area: None selected")
        self.preview_info_label.setStyleSheet("font-weight: bold; color: #2c3e50; text-align: center; margin: 5px;")
        self.preview_info_label.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.preview_info_label)
        
        parent_layout.addWidget(preview_group)
    
    def _create_validation_footer(self, parent_layout):
        """Create validation footer with completion controls."""
        footer_frame = QFrame()
        footer_frame.setFrameStyle(QFrame.StyledPanel)
        footer_layout = QHBoxLayout()
        
        # Validation progress
        self.validation_progress = QProgressBar()
        self.validation_progress.setVisible(False)
        footer_layout.addWidget(self.validation_progress)
        
        footer_layout.addStretch()
        
        # Action buttons
        self.clear_page_btn = QPushButton("Clear Page Selections")
        self.clear_page_btn.clicked.connect(self._clear_current_page)
        self.clear_page_btn.setEnabled(False)
        footer_layout.addWidget(self.clear_page_btn)
        
        # Add Save Progress button
        self.save_progress_btn = QPushButton("💾 Save Progress")
        self.save_progress_btn.clicked.connect(self._save_progress)
        self.save_progress_btn.setEnabled(False)
        self.save_progress_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        footer_layout.addWidget(self.save_progress_btn)
        
        # Add manual "Add to Project" button as fallback
        self.add_to_project_btn = QPushButton("➕ Add to Project")
        self.add_to_project_btn.clicked.connect(self._add_current_document_to_project)
        self.add_to_project_btn.setEnabled(False)
        self.add_to_project_btn.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                border: none;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        footer_layout.addWidget(self.add_to_project_btn)
        
        self.complete_btn = QPushButton("Complete Validation")
        self.complete_btn.clicked.connect(self._complete_validation)
        self.complete_btn.setEnabled(False)
        print(f"🔧 BUTTON: Complete Validation button created and connected to _complete_validation")
        self.complete_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        footer_layout.addWidget(self.complete_btn)
        
        footer_frame.setLayout(footer_layout)
        parent_layout.addWidget(footer_frame)
    
    def load_document(self, document: Document, file_path: str = None):
        """Load a document for manual validation."""
        self.logger.info(f"load_document called with document={document}, file_path={file_path}")
        
        self.current_document = document
        # Use provided file_path or fall back to document metadata
        self.current_file_path = file_path or (document.metadata.file_path if hasattr(document, 'metadata') and document.metadata else None)
        self.all_selections = {}
        self.validation_complete = False
        
        self.logger.info(f"Document set: current_document={self.current_document}")
        self.logger.info(f"File path set: current_file_path={self.current_file_path}")
        
        # Ensure document has a proper ID for project consistency
        if self.current_document and self.current_file_path:
            self._ensure_document_id_consistency()
        
        if not self.current_file_path:
            self.logger.error("No valid file path found!")
            self.status_message.emit("Error: No valid file path found")
            return
        
        # Update UI
        self.progress_label.setText(f"Document loaded: {Path(self.current_file_path).name}")
        
        # Set default UI state
        if hasattr(self, 'complete_btn'):
            self.complete_btn.setText("Complete Validation")  # Reset to default text
            self.complete_btn.setEnabled(True)
        if hasattr(self, 'clear_page_btn'):
            self.clear_page_btn.setEnabled(True)
        if hasattr(self, 'save_progress_btn'):
            self.save_progress_btn.setEnabled(True)
        if hasattr(self, 'add_to_project_btn'):
            self.add_to_project_btn.setEnabled(True)
        
        # Update statistics
        self._update_statistics()
        
        # Load existing selections for this document
        print(f"🔵 DOCUMENT LOADED: About to load persistent selections")
        self._load_persistent_selections()
        
        # Also load existing areas from project storage (new functionality)
        print(f"🔵 DOCUMENT LOADED: About to load existing areas from project")
        self.load_existing_areas_from_project()
        
        # Load validation state (if document was previously validated)
        print(f"🔵 DOCUMENT LOADED: About to load validation state")
        self._load_validation_state()
        
        self.status_message.emit("Document loaded for manual validation")
        self.logger.info(f"Document successfully loaded for manual validation: {self.current_file_path}")
    
    def on_documents_available(self, document_ids: List[str]):
        """Handle signal from document state manager when documents are available."""
        print(f"🔵 MANUAL VALIDATION: Received documents available signal: {document_ids}")
        
        if not document_ids:
            print("🟡 MANUAL VALIDATION: No documents available")
            return
            
        try:
            # Get main window and document state manager
            main_window = self._get_main_window()
            if not main_window or not hasattr(main_window, 'document_state_manager'):
                print("🔴 MANUAL VALIDATION: No document state manager available")
                return
                
            document_state = main_window.document_state_manager
            
            # Find the first document with visual areas
            for doc_id in document_ids:
                doc_metadata = document_state.get_document_metadata(doc_id)
                if doc_metadata and doc_metadata.get('visual_areas'):
                    visual_areas = doc_metadata['visual_areas']
                    if visual_areas:
                        print(f"🔵 MANUAL VALIDATION: Found document {doc_id} with {len(visual_areas)} areas")
                        
                        # Auto-load this document if we don't have one loaded
                        if not self.current_document or not self.current_file_path:
                            doc_path = doc_metadata.get('path') or doc_metadata.get('file_path')
                            if doc_path and Path(doc_path).exists():
                                print(f"🔵 MANUAL VALIDATION: Auto-loading document from state manager: {doc_path}")
                                
                                # Create document object
                                from ..models.document_models import Document, DocumentMetadata
                                from ..config.constants import DocumentType, ProcessingStatus, QualityLevel
                                from ..models.document_models import ProcessingConfiguration
                                from datetime import datetime
                                
                                metadata = DocumentMetadata(
                                    file_path=doc_path,
                                    file_name=Path(doc_path).name,
                                    file_size=doc_metadata.get('file_size', 0),
                                    creation_date=datetime.now(),
                                    modification_date=datetime.now(),
                                    page_count=doc_metadata.get('page_count', 0)
                                )
                                
                                document = Document(
                                    id=doc_id,
                                    metadata=metadata,
                                    document_type=DocumentType.ICAO,
                                    processing_status=ProcessingStatus.COMPLETED,
                                    processing_config=ProcessingConfiguration(),
                                    quality_level=QualityLevel.HIGH,
                                    quality_score=0.95
                                )
                                
                                # Load the document
                                self.load_document(document, doc_path)
                                print(f"🟢 MANUAL VALIDATION: Successfully auto-loaded document with areas!")
                                break
                        
        except Exception as e:
            print(f"🔴 MANUAL VALIDATION: Error handling documents available: {e}")
            self.logger.error(f"Error handling documents available: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_area_selected(self, selection_data: Dict):
        """Handle area selection from PDF viewer."""
        print(f"🟢 MANUAL VALIDATION: Received area selected signal: {selection_data}")
        page = selection_data['page']
        area_type = selection_data['type']
        
        # Generate system-appropriate area name
        area_name = self._generate_area_name(area_type, page, selection_data.get('id', ''))
        selection_data['name'] = area_name
        
        # Add to all selections
        if page not in self.all_selections:
            self.all_selections[page] = []
        self.all_selections[page].append(selection_data)
        
        print(f"🟢 MANUAL VALIDATION: Added area to selections - page {page}, total areas: {len(self.all_selections[page])}")
        print(f"🟢 MANUAL VALIDATION: Total selections across all pages: {sum(len(selections) for selections in self.all_selections.values())}")
        
        # Update UI displays
        self._update_statistics()
        self._update_selection_list()
        
        # Show preview of the selected area immediately
        self._show_preview_image(selection_data)
        
        # Extract and store original resolution image data
        self._extract_original_resolution_data(selection_data)
        
        # Save selections to persist between sessions
        print(f"🔵 AREA SELECTED: About to save persistent selections")
        self._save_persistent_selections()
        
        self.status_message.emit(f"Area '{area_name}' classified as {area_type} on page {page + 1}")
    
    def _on_area_preview_update(self, preview_data: dict):
        """Handle real-time area preview updates during dragging."""
        print(f"🟢 MANUAL VALIDATION: Received preview update signal: {preview_data}")
        self.logger.info(f"Received preview update: {preview_data}")
        if preview_data.get('is_preview', False):
            # Update preview immediately with dragged area
            self._show_preview_image(preview_data)
            
            # Update info label to show this is a live preview
            area_type = preview_data.get('type', 'PREVIEW')
            page_num = preview_data.get('page', 1)  # Default to page 1, not 0
            self.preview_info_label.setText(f"Live Preview: Dragging area on Page {page_num}")
    
    def _show_preview_image(self, area_data):
        """Show preview image for area data (both temporary and permanent)."""
        try:
            # Always try to recover document context first for area previews
            if not self.current_document or not self.current_file_path:
                self.logger.info(f"Missing document context, attempting recovery...")
                
                # Try to recover document context from main window
                if self._try_recover_document_context():
                    self.logger.info("✅ Successfully recovered document context, proceeding with preview")
                else:
                    # Try alternative recovery methods
                    if self._try_alternative_document_recovery():
                        self.logger.info("✅ Successfully recovered document via alternative method")
                    else:
                        self.logger.warning("❌ Could not recover document context for area preview")
                        self.area_preview_label.setText(f"📄 No document loaded\n\nPlease load a document to view area previews.\n\nTip: Switch to the Project tab and\nopen a document first.")
                        return
            
            self.logger.info(f"Showing preview for area: {area_data}")
            
            # Get area coordinates and validate
            bbox = area_data.get('bbox', [0, 0, 100, 100])
            page_num_1based = area_data.get('page', 1)  # This is 1-based from storage
            page_num_0based = page_num_1based - 1  # Convert to 0-based for PyMuPDF
            
            self.logger.info(f"Preview bbox: {bbox}, page: {page_num_1based} (1-based) → {page_num_0based} (0-based for PyMuPDF)")
            
            # Open PDF document
            doc = fitz.open(self.current_file_path)
            
            if page_num_0based >= len(doc) or page_num_0based < 0:
                self.logger.error(f"Invalid page number: {page_num_0based} (0-based) not in range 0-{len(doc)-1}")
                doc.close()
                return
            
            page = doc[page_num_0based]  # Use 0-based index for PyMuPDF
            area_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
            
            self.logger.info(f"PDF page size: {page.rect}, area rect: {area_rect}")
            
            # Check if area rect is valid
            if area_rect.width <= 0 or area_rect.height <= 0:
                self.logger.error(f"Invalid area rectangle: {area_rect}")
                doc.close()
                return
            
            # Extract area as image at original PDF resolution (not display zoom)
            # Use high resolution matrix for crisp extraction regardless of display zoom
            original_dpi = 300  # High quality DPI for extraction
            zoom_for_extraction = original_dpi / 72.0  # PDF default is 72 DPI
            mat = fitz.Matrix(zoom_for_extraction, zoom_for_extraction)
            pix = page.get_pixmap(matrix=mat, clip=area_rect)
            
            self.logger.info(f"Extracted pixmap size: {pix.width}x{pix.height}")
            
            # Convert to QPixmap
            img_data = pix.tobytes("png")
            pixmap = QPixmap()
            success = pixmap.loadFromData(img_data, "PNG")
            
            self.logger.info(f"QPixmap load success: {success}, size: {pixmap.width()}x{pixmap.height()}")
            
            # Scale to fit preview while maintaining aspect ratio
            if pixmap.width() > 0 and pixmap.height() > 0:
                preview_size = self.area_preview_label.size()
                self.logger.info(f"Preview label size: {preview_size.width()}x{preview_size.height()}")
                
                scaled_pixmap = pixmap.scaled(
                    preview_size,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                
                self.logger.info(f"Scaled pixmap size: {scaled_pixmap.width()}x{scaled_pixmap.height()}")
                
                self.area_preview_label.setPixmap(scaled_pixmap)
                self.logger.info("Preview image set successfully!")
            else:
                self.logger.error(f"Invalid pixmap dimensions: {pixmap.width()}x{pixmap.height()}")
            
            doc.close()
            
        except Exception as e:
            self.logger.error(f"Error showing preview image: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            # Don't show error for temporary previews to avoid spam
    
    def _extract_original_resolution_data(self, area_data):
        """Extract and store original resolution image data for the selected area."""
        try:
            if not self.current_document or not self.current_file_path:
                self.logger.error("Cannot extract original resolution: no document loaded")
                return
            
            bbox = area_data.get('bbox', [0, 0, 100, 100])
            page_num = area_data.get('page', 1)  # Default to page 1, not 0
            area_name = area_data.get('name', 'unknown_area')
            
            self.logger.info(f"Extracting original resolution data for {area_name}")
            
            # Open PDF document
            doc = fitz.open(self.current_file_path)
            
            if page_num >= len(doc):
                doc.close()
                return
            
            page = doc[page_num]
            area_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
            
            # Extract at original high resolution (300 DPI)
            original_dpi = 300
            zoom_for_extraction = original_dpi / 72.0
            mat = fitz.Matrix(zoom_for_extraction, zoom_for_extraction)
            
            # Get high-resolution pixmap
            pix = page.get_pixmap(matrix=mat, clip=area_rect)
            
            # Convert to bytes for storage
            img_data = pix.tobytes("png")
            
            # Store in area data
            area_data['original_image_data'] = img_data
            area_data['original_resolution'] = {
                'dpi': original_dpi,
                'width': pix.width,
                'height': pix.height,
                'format': 'png'
            }
            
            # Also create a file path for saving if needed
            output_dir = Path("output") / "extracted_areas"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            doc_name = Path(self.current_file_path).stem
            filename = f"{doc_name}_page{page_num + 1}_{area_name}.png"
            file_path = output_dir / filename
            
            # Save original resolution image
            with open(file_path, 'wb') as f:
                f.write(img_data)
            
            area_data['saved_file_path'] = str(file_path)
            
            doc.close()
            
            self.logger.info(f"Original resolution data extracted: {pix.width}x{pix.height} at {original_dpi} DPI")
            self.logger.info(f"Saved to: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error extracting original resolution data: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _export_original_resolution_areas(self):
        """Export summary of all extracted original resolution areas."""
        try:
            if not self.all_selections:
                self.logger.info("No areas to export")
                return
            
            # Create export summary
            export_summary = {
                'document_path': self.current_file_path,
                'document_name': Path(self.current_file_path).name if self.current_file_path else 'unknown',
                'export_timestamp': datetime.now().isoformat(),
                'total_areas': sum(len(selections) for selections in self.all_selections.values()),
                'pages_with_areas': len(self.all_selections),
                'areas': []
            }
            
            # Add area details
            for page, selections in self.all_selections.items():
                for selection in selections:
                    area_info = {
                        'name': selection.get('name', 'unknown'),
                        'type': selection.get('type', 'unknown'),
                        'page': page + 1,  # 1-indexed for humans
                        'bbox': selection.get('bbox', [0, 0, 0, 0]),
                        'saved_file_path': selection.get('saved_file_path', ''),
                        'original_resolution': selection.get('original_resolution', {})
                    }
                    export_summary['areas'].append(area_info)
            
            # Save export summary
            output_dir = Path("output") / "extracted_areas"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            doc_name = Path(self.current_file_path).stem if self.current_file_path else 'unknown'
            summary_file = output_dir / f"{doc_name}_extraction_summary.json"
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(export_summary, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Exported {export_summary['total_areas']} original resolution areas")
            self.logger.info(f"Export summary saved to: {summary_file}")
            
            # Show completion message
            self.status_message.emit(f"Exported {export_summary['total_areas']} areas at original resolution")
            
        except Exception as e:
            self.logger.error(f"Error exporting original resolution areas: {e}")
    
    def _get_persistence_file_path(self):
        """Get the file path for storing persistent selections (PROJECT-SPECIFIC)."""
        print(f"🔵 GET PERSISTENCE PATH: current_file_path = {self.current_file_path}")
        
        if not self.current_file_path:
            print(f"🔴 GET PERSISTENCE PATH: No current_file_path")
            return None
        
        # Get current project information
        project_info = self._get_current_project_info()
        print(f"🔵 GET PERSISTENCE PATH: project_info = {project_info}")
        
        if not project_info:
            print(f"🔴 GET PERSISTENCE PATH: No active project - NOT using document-based fallback")
            print(f"🔴 GET PERSISTENCE PATH: Persistence is ONLY allowed within project context")
            return None
        
        # Create project-specific persistence directory
        project_dir = Path(project_info['project_path']).parent if project_info['project_path'] else Path.cwd()
        persistence_dir = project_dir / ".tore_project_selections" / project_info['project_name']
        
        print(f"🔵 GET PERSISTENCE PATH: project_dir = {project_dir}")
        print(f"🔵 GET PERSISTENCE PATH: persistence_dir = {persistence_dir}")
        
        try:
            persistence_dir.mkdir(parents=True, exist_ok=True)
            print(f"🟢 GET PERSISTENCE PATH: Project directory created/exists: {persistence_dir}")
        except Exception as e:
            print(f"🔴 GET PERSISTENCE PATH: Error creating project directory: {e}")
            return None
        
        # Generate persistence file name based on document within project context
        doc_name = Path(self.current_file_path).stem
        persistence_file = persistence_dir / f"{doc_name}_selections.json"
        
        print(f"🔵 GET PERSISTENCE PATH: doc_name = {doc_name}")
        print(f"🔵 GET PERSISTENCE PATH: project_persistence_file = {persistence_file}")
        
        return persistence_file
    
    def _get_current_project_info(self):
        """Get current project information from main window."""
        try:
            print(f"🔵 PROJECT INFO: Starting project info retrieval...")
            
            # Access main window through parent hierarchy
            main_window = self.parent()
            depth = 0
            while main_window and not hasattr(main_window, 'project_widget') and depth < 10:
                print(f"🔵 PROJECT INFO: Checking parent level {depth}: {type(main_window).__name__}")
                main_window = main_window.parent()
                depth += 1
            
            if not main_window:
                print(f"🔴 PROJECT INFO: Could not find main window (traversed {depth} levels)")
                return None
                
            if not hasattr(main_window, 'project_widget'):
                print(f"🔴 PROJECT INFO: Main window found but no project_widget attribute")
                print(f"🔴 PROJECT INFO: Main window type: {type(main_window).__name__}")
                print(f"🔴 PROJECT INFO: Main window attributes: {[attr for attr in dir(main_window) if not attr.startswith('_')][:10]}")
                return None
            
            print(f"🟢 PROJECT INFO: Found main window with project_widget")
            
            project_widget = main_window.project_widget
            print(f"🔵 PROJECT INFO: Project widget type: {type(project_widget).__name__}")
            
            if not hasattr(project_widget, 'get_current_project'):
                print(f"🔴 PROJECT INFO: Project widget has no get_current_project method")
                return None
            
            current_project = project_widget.get_current_project()
            print(f"🔵 PROJECT INFO: get_current_project() returned: {current_project}")
            
            if not current_project:
                print(f"🔴 PROJECT INFO: No current project active (returned None)")
                return None
            
            project_info = {
                'project_name': current_project.get('name', 'default_project'),
                'project_path': current_project.get('path', ''),
                'project_id': current_project.get('id', 'unknown')
            }
            
            print(f"🟢 PROJECT INFO: Successfully extracted project info:")
            print(f"🟢 PROJECT INFO:   project_name = {project_info['project_name']}")
            print(f"🟢 PROJECT INFO:   project_path = {project_info['project_path']}")
            print(f"🟢 PROJECT INFO:   project_id = {project_info['project_id']}")
            
            return project_info
            
        except Exception as e:
            print(f"🔴 PROJECT INFO: Error getting project info: {e}")
            import traceback
            print(f"🔴 PROJECT INFO: Traceback: {traceback.format_exc()}")
            return None
    
    def _get_document_based_persistence_path(self):
        """DEPRECATED: Document-based persistence is no longer supported."""
        print(f"🔴 DEPRECATED: Document-based persistence is no longer supported")
        print(f"🔴 DEPRECATED: Persistence is ONLY allowed within project context")
        return None
    
    def _save_persistent_selections(self):
        """Save current selections to persistent storage."""
        try:
            print(f"🔵 PERSISTENCE: _save_persistent_selections called")
            print(f"🔵 PERSISTENCE: current_file_path = {self.current_file_path}")
            print(f"🔵 PERSISTENCE: all_selections = {self.all_selections}")
            
            # Check if we have an active project
            project_info = self._get_current_project_info()
            if not project_info:
                print(f"🔴 PERSISTENCE: No active project - not saving selections")
                print(f"🔴 PERSISTENCE: Selections are only saved within project context")
                return
            
            print(f"🟢 PERSISTENCE: Active project found: {project_info['project_name']}")
            
            persistence_file = self._get_persistence_file_path()
            print(f"🔵 PERSISTENCE: persistence_file = {persistence_file}")
            
            if not persistence_file:
                print(f"🔴 PERSISTENCE: No persistence file path, returning")
                return
            
            # Prepare data for serialization (exclude non-serializable items)
            serializable_selections = {}
            
            for page, selections in self.all_selections.items():
                serializable_selections[str(page)] = []
                for selection in selections:
                    # Create serializable copy without binary data
                    serializable_selection = {
                        'id': selection.get('id', ''),
                        'name': selection.get('name', ''),
                        'type': selection.get('type', ''),
                        'bbox': selection.get('bbox', []),
                        'page': selection.get('page', 1),  # Default to page 1, not 0
                        'selection_rect': selection.get('selection_rect', []),
                        'saved_file_path': selection.get('saved_file_path', ''),
                        'original_resolution': selection.get('original_resolution', {}),
                        'created_at': selection.get('created_at', datetime.now().isoformat())
                    }
                    # Add timestamp if not present
                    if 'created_at' not in selection:
                        selection['created_at'] = datetime.now().isoformat()
                        serializable_selection['created_at'] = selection['created_at']
                    
                    serializable_selections[str(page)].append(serializable_selection)
            
            # Get project context for metadata
            project_info = self._get_current_project_info()
            
            # Create metadata with project context
            metadata = {
                'document_path': self.current_file_path,
                'document_name': Path(self.current_file_path).name if self.current_file_path else 'unknown',
                'project_name': project_info['project_name'] if project_info else 'no_project',
                'project_path': project_info['project_path'] if project_info else '',
                'project_id': project_info['project_id'] if project_info else 'unknown',
                'last_modified': datetime.now().isoformat(),
                'total_selections': sum(len(selections) for selections in self.all_selections.values()),
                'persistence_type': 'project_specific' if project_info else 'document_fallback',
                'selections': serializable_selections
            }
            
            # Save to file
            print(f"🔵 PERSISTENCE: Saving to file: {persistence_file}")
            print(f"🔵 PERSISTENCE: Metadata: {metadata}")
            
            with open(persistence_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            print(f"🟢 PERSISTENCE: Successfully saved {metadata['total_selections']} selections to {persistence_file}")
            self.logger.info(f"Saved selections to: {persistence_file}")
            
            # If using project-specific persistence, optionally clean up old document-based persistence
            if project_info:
                self._cleanup_old_document_persistence()
            
        except Exception as e:
            print(f"🔴 PERSISTENCE: Error saving: {e}")
            self.logger.error(f"Error saving persistent selections: {e}")
            import traceback
            traceback.print_exc()
    
    def _cleanup_old_document_persistence(self):
        """Clean up old document-based persistence files when using project-based persistence."""
        try:
            old_persistence_file = self._get_document_based_persistence_path()
            if old_persistence_file and old_persistence_file.exists():
                print(f"🟡 CLEANUP: Removing old document-based persistence: {old_persistence_file}")
                old_persistence_file.unlink()
                
                # Also try to remove empty .tore_selections directory
                old_dir = old_persistence_file.parent
                if old_dir.exists() and not any(old_dir.iterdir()):
                    old_dir.rmdir()
                    print(f"🟡 CLEANUP: Removed empty directory: {old_dir}")
                    
        except Exception as e:
            print(f"🔴 CLEANUP: Error cleaning up old persistence: {e}")
            # Don't fail the main operation if cleanup fails
    
    def _load_persistent_selections(self):
        """Load selections from persistent storage."""
        try:
            print(f"🔵 PERSISTENCE: _load_persistent_selections called")
            print(f"🔵 PERSISTENCE: current_file_path = {self.current_file_path}")
            
            persistence_file = self._get_persistence_file_path()
            print(f"🔵 PERSISTENCE: persistence_file = {persistence_file}")
            
            if not persistence_file:
                print(f"🔴 PERSISTENCE: No persistence file path")
                return
                
            if not persistence_file.exists():
                print(f"🔴 PERSISTENCE: File does not exist: {persistence_file}")
                self.logger.info("No persistent selections file found")
                return
            
            # Load metadata
            with open(persistence_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Validate project context (ensure we're loading the right project's selections)
            project_info = self._get_current_project_info()
            file_project = metadata.get('project_name', 'unknown')
            current_project = project_info['project_name'] if project_info else 'no_project'
            
            print(f"🔵 PERSISTENCE: File project: {file_project}, Current project: {current_project}")
            
            # STRICT project validation - only load if exact project match
            if not project_info:
                print(f"🔴 PERSISTENCE: No active project - not loading any selections")
                return
            
            if file_project != current_project:
                print(f"🟡 PERSISTENCE: Project mismatch - not loading selections from different project")
                print(f"🟡 PERSISTENCE: File belongs to project '{file_project}', current project is '{current_project}'")
                self.logger.info(f"Skipping selections from different project: {file_project}")
                return
            
            print(f"🟢 PERSISTENCE: Project match confirmed - loading selections for project '{current_project}'")
            
            selections_data = metadata.get('selections', {})
            loaded_count = 0
            persistence_type = metadata.get('persistence_type', 'unknown')
            
            # Restore selections
            self.all_selections = {}
            for page_str, selections in selections_data.items():
                page = int(page_str)
                # Convert old 0-based page keys to 1-based
                if page == 0:
                    page = 1
                    self.logger.info(f"Converting old 0-based page key to 1-based: {page_str} → {page}")
                
                if page not in self.all_selections:
                    self.all_selections[page] = []
                
                for selection_data in selections:
                    # Get page number and fix 0-based to 1-based conversion for old data
                    saved_page = selection_data.get('page', page)
                    # Convert old 0-based page numbers to 1-based
                    if saved_page == 0:
                        saved_page = 1
                        self.logger.info(f"Converting old 0-based page number to 1-based for area: {selection_data.get('name', 'unnamed')}")
                    
                    # Restore selection with all metadata
                    restored_selection = {
                        'id': selection_data.get('id', ''),
                        'name': selection_data.get('name', ''),
                        'type': selection_data.get('type', ''),
                        'bbox': selection_data.get('bbox', []),
                        'page': saved_page,
                        'selection_rect': selection_data.get('selection_rect', []),
                        'saved_file_path': selection_data.get('saved_file_path', ''),
                        'original_resolution': selection_data.get('original_resolution', {}),
                        'created_at': selection_data.get('created_at', datetime.now().isoformat())
                    }
                    
                    # Re-load original image data if file exists
                    file_path = restored_selection.get('saved_file_path', '')
                    if file_path and Path(file_path).exists():
                        try:
                            with open(file_path, 'rb') as img_file:
                                restored_selection['original_image_data'] = img_file.read()
                        except Exception as e:
                            self.logger.warning(f"Could not reload image data from {file_path}: {e}")
                    
                    self.all_selections[page].append(restored_selection)
                    loaded_count += 1
            
            # Update UI
            self._update_statistics()
            self._update_selection_list()
            
            # Update preview if there are selections
            if self.all_selections and self.selection_list.count() > 0:
                # Auto-select first item
                first_item = self.selection_list.item(0)
                self.selection_list.setCurrentItem(first_item)
                self._update_area_preview()
            
            print(f"🟢 PERSISTENCE: Successfully loaded {loaded_count} selections from {persistence_file}")
            print(f"🟢 PERSISTENCE: Persistence type: {persistence_type}, Project: {current_project}")
            self.logger.info(f"Loaded {loaded_count} persistent selections from {persistence_file}")
            
            if project_info:
                self.status_message.emit(f"Restored {loaded_count} areas from project '{current_project}'")
            else:
                self.status_message.emit(f"Restored {loaded_count} previously selected areas")
            
        except Exception as e:
            print(f"🔴 PERSISTENCE: Error loading: {e}")
            self.logger.error(f"Error loading persistent selections: {e}")
            import traceback
            print(f"🔴 PERSISTENCE: Traceback: {traceback.format_exc()}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _update_statistics(self):
        """Update selection statistics display."""
        if not self.all_selections:
            self.stats_label.setText("No selections yet")
            return
        
        total_selections = sum(len(selections) for selections in self.all_selections.values())
        pages_with_selections = len(self.all_selections)
        
        # Count by type (enhanced with new types)
        type_counts = {'IMAGE': 0, 'TABLE': 0, 'DIAGRAM': 0, 'CHART': 0, 'COMPLEX': 0}
        high_priority_count = 0
        notes_count = 0
        
        for selections in self.all_selections.values():
            for selection in selections:
                selection_type = selection.get('type', 'UNKNOWN')
                if selection_type in type_counts:
                    type_counts[selection_type] += 1
                if selection.get('high_priority', False):
                    high_priority_count += 1
                if selection.get('special_notes', ''):
                    notes_count += 1
        
        stats_text = f"""
        Total selections: {total_selections} | Pages: {pages_with_selections} | High Priority: {high_priority_count}
        🖼️ Images: {type_counts['IMAGE']} | 📊 Tables: {type_counts['TABLE']} | 📈 Diagrams: {type_counts['DIAGRAM']}
        📊 Charts: {type_counts['CHART']} | 🔧 Complex: {type_counts['COMPLEX']} | 📝 With Notes: {notes_count}
        """
        self.stats_label.setText(stats_text.strip())
    
    def _update_selection_list(self):
        """Update the selection list display."""
        try:
            self.logger.info(f"UPDATE_SELECTION_LIST: Starting update with {len(self.all_selections)} pages")
            
            self.selection_list.clear()
            
            total_areas = sum(len(selections) for selections in self.all_selections.values())
            self.logger.info(f"UPDATE_SELECTION_LIST: Total areas to add: {total_areas}")
            
            for page, selections in sorted(self.all_selections.items()):
                self.logger.info(f"UPDATE_SELECTION_LIST: Processing page {page} with {len(selections)} selections")
                
                for selection in selections:
                    # Create display text
                    name = selection.get('name', f"{selection.get('type', 'AREA')}_AUTO")
                    if not name:
                        name = f"{selection['type']} area"
                    
                    item_text = f"Page {page}: {selection['type']} - {name}"
                    
                    # Create list item
                    item = QListWidgetItem(item_text)
                    
                    # Enhanced color based on type
                    if selection['type'] == 'IMAGE':
                        item.setBackground(QColor(52, 152, 219, 50))  # Blue
                    elif selection['type'] == 'TABLE':
                        item.setBackground(QColor(231, 76, 60, 50))  # Red
                    elif selection['type'] == 'DIAGRAM':
                        item.setBackground(QColor(243, 156, 18, 50))  # Orange
                    elif selection['type'] == 'CHART':
                        item.setBackground(QColor(155, 89, 182, 50))  # Purple
                    elif selection['type'] == 'COMPLEX':
                        item.setBackground(QColor(52, 73, 94, 50))  # Dark blue-gray
                    
                    # Store area data in item
                    item.setData(Qt.UserRole, selection)
                    
                    self.selection_list.addItem(item)
                    self.logger.debug(f"UPDATE_SELECTION_LIST: Added item '{item_text}' to list")
        
            # Auto-select the last added item to show its preview
            if self.selection_list.count() > 0:
                last_item = self.selection_list.item(self.selection_list.count() - 1)
                self.selection_list.setCurrentItem(last_item)
                self.logger.info(f"UPDATE_SELECTION_LIST: Auto-selected last item")
            
            # Update navigation buttons
            self._update_navigation_buttons()
            
            self.logger.info(f"UPDATE_SELECTION_LIST: Successfully updated selection list with {self.selection_list.count()} items")
            
        except Exception as e:
            self.logger.error(f"UPDATE_SELECTION_LIST: Error updating selection list: {e}")
            import traceback
            self.logger.error(f"UPDATE_SELECTION_LIST: Traceback: {traceback.format_exc()}")
    
    def _clear_current_page(self):
        """Clear selections for the current page."""
        # Note: Page management is now handled by the main PDF viewer
        # This method is kept for compatibility but functionality is limited
        if self.all_selections:
            # Clear all selections for now (could be enhanced to track current page)
            self.all_selections.clear()
            self._update_statistics()
            self._update_selection_list()
            self._clear_area_preview()
            self.status_message.emit("Cleared all selections")
    
    def _complete_validation(self):
        """Complete the manual validation process."""
        print(f"🔵 VALIDATION: _complete_validation called!")
        print(f"🔵 VALIDATION: current_document exists: {self.current_document is not None}")
        print(f"🔵 VALIDATION: self.all_selections = {self.all_selections}")
        print(f"🔵 VALIDATION: Total selections: {sum(len(selections) for selections in self.all_selections.values())}")
        
        if not self.current_document:
            print(f"🔴 VALIDATION: No current document - cannot complete validation")
            return
        
        # Prepare validation result
        validation_result = {
            'document_id': self.current_document.id,
            'file_path': self.current_file_path,
            'validation_completed': True,
            'selections': self.all_selections,
            'total_selections': sum(len(selections) for selections in self.all_selections.values()),
            'pages_with_selections': len(self.all_selections),
            'completed_at': datetime.now().isoformat()
        }
        
        # Export all original resolution areas
        self._export_original_resolution_areas()
        
        # Update state
        self.validation_complete = True
        self.complete_btn.setText("✅ Re-validate")
        self.complete_btn.setEnabled(True)  # Keep enabled for re-validation
        self.clear_page_btn.setEnabled(True)  # Keep enabled for modifications
        
        # Save validation state to project (new functionality)
        print(f"🔵 VALIDATION: Saving validation state to project...")
        self._save_validation_state()
        
        # Emit completion signal
        print(f"🔵 VALIDATION: Emitting validation_completed signal...")
        print(f"🔵 VALIDATION: Validation result: {validation_result}")
        self.validation_completed.emit(validation_result)
        print(f"🟢 VALIDATION: Signal emitted successfully!")
        
        self.status_message.emit("Manual validation completed successfully")
        self.logger.info(f"Manual validation completed for {self.current_file_path}")
    
    def _save_progress(self):
        """Save current validation progress without completing validation."""
        print(f"🔵 SAVE PROGRESS: _save_progress called!")
        
        if not self.current_document:
            print(f"🔴 SAVE PROGRESS: No current document")
            return
        
        try:
            # Save current selections to persistence
            print(f"🔵 SAVE PROGRESS: Saving selections to persistence...")
            self._save_persistent_selections()
            
            # Save current validation state (including partial progress)
            print(f"🔵 SAVE PROGRESS: Saving validation state...")
            self._save_validation_state()
            
            # Emit signal to save project (this will trigger auto-save)
            self.status_message.emit("💾 Progress saved! You can safely close the application.")
            print(f"🟢 SAVE PROGRESS: Progress saved successfully!")
            
            # Optional: Emit a custom signal to main window to update document status
            self._notify_progress_saved()
            
        except Exception as e:
            print(f"🔴 SAVE PROGRESS: Error saving progress: {e}")
            self.status_message.emit(f"Error saving progress: {e}")
            self.logger.error(f"Error saving validation progress: {e}")
    
    def _notify_progress_saved(self):
        """Notify main window that progress has been saved."""
        try:
            # Find main window and trigger project save
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'project_widget'):
                main_window = main_window.parent()
            
            if main_window and hasattr(main_window, 'project_widget'):
                # Trigger project save to ensure document state is persisted
                print(f"🔵 SAVE PROGRESS: Triggering project save...")
                main_window.project_widget.save_current_project()
                print(f"🟢 SAVE PROGRESS: Project saved with current progress!")
            
        except Exception as e:
            print(f"🔴 SAVE PROGRESS: Error notifying main window: {e}")
    
    def _add_current_document_to_project(self):
        """Manually add the current document to the project (fallback method)."""
        print(f"🔵 ADD TO PROJECT: Manual add button clicked!")
        
        if not self.current_document or not self.current_file_path:
            print(f"🔴 ADD TO PROJECT: No current document loaded")
            self.status_message.emit("No document loaded to add to project")
            return
        
        try:
            # Create document data for project
            from datetime import datetime
            
            document_data = {
                'id': self.current_document.id,
                'file_path': self.current_file_path,
                'file_name': Path(self.current_file_path).name,
                'file_size': self.current_document.metadata.file_size,
                'file_type': self.current_document.metadata.file_type,
                'page_count': self.current_document.metadata.page_count,
                'processing_status': 'IN_VALIDATION',
                'quality_level': self.current_document.quality_level,
                'quality_score': self.current_document.quality_score,
                'document_type': self.current_document.document_type,
                'validation_status': 'in_progress',
                'selections_count': sum(len(selections) for selections in self.all_selections.values()),
                'added_at': datetime.now().isoformat(),
                'last_modified': datetime.now().isoformat()
            }
            
            print(f"🔵 ADD TO PROJECT: Document data prepared: {document_data}")
            
            # Find main window and add to project
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'project_widget'):
                main_window = main_window.parent()
            
            if main_window and hasattr(main_window, 'project_widget'):
                print(f"🔵 ADD TO PROJECT: Found main window, calling add_processed_document...")
                main_window.project_widget.add_processed_document(document_data)
                print(f"🟢 ADD TO PROJECT: Document added to project successfully!")
                
                self.status_message.emit(f"✅ Document '{document_data['file_name']}' added to project!")
                
                # Disable the button since document is now in project
                self.add_to_project_btn.setEnabled(False)
                self.add_to_project_btn.setText("✅ Added to Project")
                
            else:
                print(f"🔴 ADD TO PROJECT: Could not find main window or project widget")
                self.status_message.emit("Error: Could not access project")
                
        except Exception as e:
            print(f"🔴 ADD TO PROJECT: Error adding document: {e}")
            import traceback
            print(f"🔴 ADD TO PROJECT: Traceback: {traceback.format_exc()}")
            self.status_message.emit(f"Error adding document to project: {e}")
    
    def get_validation_result(self) -> Optional[Dict]:
        """Get the current validation result."""
        if not self.validation_complete or not self.current_document:
            return None
        
        return {
            'document_id': self.current_document.id,
            'file_path': self.current_file_path,
            'validation_completed': True,
            'selections': self.all_selections,
            'total_selections': sum(len(selections) for selections in self.all_selections.values()),
            'pages_with_selections': len(self.all_selections),
            'completed_at': datetime.now().isoformat()
        }
    
    def _navigate_previous_area(self):
        """Navigate to previous selected area."""
        current_row = self.selection_list.currentRow()
        if current_row > 0:
            self.selection_list.setCurrentRow(current_row - 1)
            self._highlight_current_area()
            self._update_area_preview()
    
    def _navigate_next_area(self):
        """Navigate to next selected area."""
        current_row = self.selection_list.currentRow()
        if current_row < self.selection_list.count() - 1:
            self.selection_list.setCurrentRow(current_row + 1)
            self._highlight_current_area()
            self._update_area_preview()
    
    def _on_area_clicked(self, item):
        """Handle area list item clicked."""
        self._highlight_current_area()
        self._update_navigation_buttons()
        self._update_area_preview()
    
    def _highlight_current_area(self):
        """Highlight the currently selected area in the PDF viewer."""
        current_item = self.selection_list.currentItem()
        if current_item:
            area_data = current_item.data(Qt.UserRole)
            if area_data:
                self.logger.info(f"LIST_SELECT: Highlighting area {area_data.get('id', 'unknown')}")
                
                # Get the main window's PDF viewer
                main_window = self.parent()
                while main_window and not hasattr(main_window, 'pdf_viewer'):
                    main_window = main_window.parent()
                
                if main_window and hasattr(main_window, 'pdf_viewer'):
                    pdf_viewer = main_window.pdf_viewer
                    
                    # Navigate to the correct page first
                    page_1based = area_data.get('page', 1)
                    current_page_0based = getattr(pdf_viewer, 'current_page', 0)
                    current_page_1based = current_page_0based + 1
                    
                    self.logger.info(f"LIST_SELECT: Area on page {page_1based}, PDF viewer on page {current_page_1based}")
                    
                    if page_1based != current_page_1based:
                        self.logger.info(f"LIST_SELECT: Navigating from page {current_page_1based} to page {page_1based}")
                        # Navigate to correct page using PDF viewer's internal method
                        if hasattr(pdf_viewer, '_go_to_page'):
                            pdf_viewer._go_to_page(page_1based)
                            self.logger.info(f"LIST_SELECT: Called _go_to_page({page_1based})")
                        else:
                            self.logger.warning("LIST_SELECT: PDF viewer has no _go_to_page method")
                    
                    # Ensure areas are loaded and then highlight the specific area
                    if hasattr(pdf_viewer, 'page_label') and hasattr(pdf_viewer.page_label, 'load_persistent_areas'):
                        cutting_tool = pdf_viewer.page_label
                        document_id = getattr(pdf_viewer, 'current_document_id', None)
                        
                        if document_id:
                            # Force reload areas for the current page
                            cutting_tool.load_persistent_areas(document_id, page_1based)
                            self.logger.info(f"LIST_SELECT: Forced reload of areas for page {page_1based}")
                            
                            # Now set this area as active
                            area_id = area_data.get('id')
                            if area_id and area_id in cutting_tool.persistent_areas:
                                cutting_tool.active_area_id = area_id
                                cutting_tool.update()  # Force repaint to show highlight
                                self.logger.info(f"LIST_SELECT: Set area {area_id} as active (found in {len(cutting_tool.persistent_areas)} loaded areas)")
                            else:
                                self.logger.warning(f"LIST_SELECT: Area {area_id} not found in persistent_areas: {list(cutting_tool.persistent_areas.keys())}")
                        else:
                            self.logger.warning("LIST_SELECT: No document ID available for area loading")
                    else:
                        self.logger.warning("LIST_SELECT: Could not access PDF viewer cutting tool or load_persistent_areas method")
                        
                else:
                    self.logger.warning("LIST_SELECT: Could not find main window PDF viewer")
                
                # Emit signal to main window
                self.status_message.emit(f"Viewing area: {area_data.get('name', 'Unknown')}")
            else:
                self.logger.warning("LIST_SELECT: No area data found in selected item")
    
    def _update_area_preview(self):
        """Update the area preview image."""
        try:
            self.logger.info("UPDATE_AREA_PREVIEW: Starting area preview update")
            
            current_item = self.selection_list.currentItem()
            self.logger.info(f"UPDATE_AREA_PREVIEW: Current item: {current_item is not None}")
            
            if current_item:
                area_data = current_item.data(Qt.UserRole)
                self.logger.info(f"UPDATE_AREA_PREVIEW: Area data: {area_data is not None}")
                
                if area_data:
                    area_name = area_data.get('name', 'Unknown')
                    area_type = area_data.get('type', 'Unknown')
                    page_num = area_data.get('page', 1)  # Default to page 1, not 0
                    
                    self.logger.info(f"UPDATE_AREA_PREVIEW: Showing preview for '{area_name}' ({area_type}) on page {page_num}")
                    
                    # Update preview info
                    self.preview_info_label.setText(f"Area: {area_name} ({area_type}) - Page {page_num}")
                    
                    # Extract and display area image
                    self._extract_and_display_area_image(area_data)
                else:
                    self.logger.warning("UPDATE_AREA_PREVIEW: No area data found in current item")
                    self._clear_area_preview()
            else:
                self.logger.info("UPDATE_AREA_PREVIEW: No current item selected")
                self._clear_area_preview()
                
        except Exception as e:
            self.logger.error(f"UPDATE_AREA_PREVIEW: Error updating area preview: {e}")
            import traceback
            self.logger.error(f"UPDATE_AREA_PREVIEW: Traceback: {traceback.format_exc()}")
            self._clear_area_preview()
    
    def _clear_area_preview(self):
        """Clear the area preview."""
        self.area_preview_label.setText("No area selected\n\nSelect an area from the list below\nor drag to select a new area")
        self.area_preview_label.setPixmap(QPixmap())  # Clear any image
        self.preview_info_label.setText("Area: None selected")
    
    def _extract_and_display_area_image(self, area_data):
        """Extract area image from PDF and display in preview."""
        if not area_data:
            self.area_preview_label.setText("No document loaded")
            return
        
        # Use the common preview image method
        self._show_preview_image(area_data)
    
    def _delete_selected_area(self):
        """Delete the currently selected area."""
        current_row = self.selection_list.currentRow()
        if current_row >= 0:
            item = self.selection_list.takeItem(current_row)
            if item:
                area_data = item.data(Qt.UserRole)
                area_name = area_data.get('name', 'Unknown') if area_data else 'Unknown'
                area_id = area_data.get('id') if area_data else None
                page = area_data.get('page', 1) if area_data else 1
                
                # Remove from internal storage
                if area_data:
                    if page in self.all_selections:
                        # Find and remove the specific selection
                        self.all_selections[page] = [
                            sel for sel in self.all_selections[page] 
                            if sel.get('id') != area_id
                        ]
                        # Remove page entry if no selections left
                        if not self.all_selections[page]:
                            del self.all_selections[page]
                
                # Remove from persistent storage (area storage manager)
                if area_id and area_data:
                    main_window = self._get_main_window()
                    if main_window and hasattr(main_window, 'area_storage_manager'):
                        area_storage = main_window.area_storage_manager
                        document_id = self._get_current_document_id()
                        if document_id and area_storage:
                            success = area_storage.delete_area(document_id, area_id)
                            self.logger.info(f"AREA DELETE: Removed area {area_id} from storage: {success}")
                
                # Force refresh PDF viewer areas for current page
                self._refresh_pdf_viewer_areas(page)
                
                # Update UI
                self._update_statistics()
                self._update_selection_list()
                self._clear_area_preview()
                
                # Save updated selections
                self._save_persistent_selections()
                
                self.status_message.emit(f"Deleted area: {area_name}")
                self._update_navigation_buttons()
    
    def _clear_all_areas(self):
        """Clear all selected areas."""
        if self.all_selections:
            # Confirm with user
            reply = QMessageBox.question(
                self, 
                "Clear All Special Areas",
                f"Are you sure you want to delete all {sum(len(selections) for selections in self.all_selections.values())} selected areas?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Delete all areas from persistent storage first
                main_window = self._get_main_window()
                document_id = self._get_current_document_id()
                if main_window and hasattr(main_window, 'area_storage_manager') and document_id:
                    area_storage = main_window.area_storage_manager
                    all_areas = area_storage.load_areas(document_id)
                    for area_id in all_areas.keys():
                        area_storage.delete_area(document_id, area_id)
                    self.logger.info(f"CLEAR ALL: Deleted {len(all_areas)} areas from persistent storage")
                
                # Get all pages that had areas for refresh
                pages_to_refresh = list(self.all_selections.keys())
                
                # Clear all selections
                self.all_selections.clear()
                
                # Force refresh PDF viewer for all affected pages
                for page in pages_to_refresh:
                    self._refresh_pdf_viewer_areas(page)
                
                # Update UI
                self.selection_list.clear()
                self._update_statistics()
                self._clear_area_preview()
                
                # Save updated (empty) selections
                self._save_persistent_selections()
                
                self.status_message.emit("Cleared all selected areas")
                self._update_navigation_buttons()
    
    def _update_navigation_buttons(self):
        """Update navigation button states."""
        has_items = self.selection_list.count() > 0
        current_row = self.selection_list.currentRow()
        
        self.prev_area_btn.setEnabled(has_items and current_row > 0)
        self.next_area_btn.setEnabled(has_items and current_row < self.selection_list.count() - 1)
        self.delete_area_btn.setEnabled(has_items and current_row >= 0)
        self.clear_all_btn.setEnabled(has_items)
        
        # Update area info label
        if has_items:
            self.area_info_label.setText(f"Area {current_row + 1} of {self.selection_list.count()}")
        else:
            self.area_info_label.setText("0 Special Areas selected")
    
    def _generate_area_name(self, area_type: str, page_num: int, area_id: str) -> str:
        """Generate system-appropriate area name with 1-based page numbering."""
        # Count existing areas of this type on this page
        existing_areas = self.all_selections.get(page_num, [])
        type_count = len([a for a in existing_areas if a.get('type') == area_type]) + 1
        
        # Ensure page_num is 1-based for naming
        display_page = page_num if page_num >= 1 else 1
        return f"{area_type}_{display_page}_{type_count:02d}"
    
    def _update_stats(self):
        """Update area statistics and navigation buttons."""
        self._update_statistics()
        self._update_selection_list()
        self._update_navigation_buttons()
        self._update_area_preview()
    
    
    def _mark_current_page_verified(self):
        """Mark the current page as verified."""
        # TODO: Implement page verification logic
        # This will track which pages have been completely verified
        self.status_message.emit("Mark current page as verified (to be implemented)")
    
    def _update_verification_progress(self):
        """Update the verification progress bar and status."""
        # TODO: Calculate and display verification progress
        # Based on pages verified vs total pages
        pass
    
    def _get_current_page_number(self):
        """Get the current page number from the main PDF viewer."""
        # TODO: Implement communication with main PDF viewer
        return 1
    
    def _get_total_pages(self):
        """Get the total number of pages in the document."""
        # TODO: Implement communication with main PDF viewer
        return getattr(self, 'total_pages', 1)
    
    def _get_main_window(self):
        """Get reference to main window."""
        parent = self.parent()
        while parent and not hasattr(parent, 'area_storage_manager'):
            parent = parent.parent()
        return parent
    
    def _get_current_document_id(self):
        """Get the current document ID with enhanced resolution."""
        try:
            # Method 1: Direct document ID
            if hasattr(self, 'current_document') and self.current_document:
                doc_id = getattr(self.current_document, 'id', None)
                if doc_id:
                    self.logger.debug(f"GET_DOC_ID: Found document ID via direct access: {doc_id}")
                    return doc_id
            
            # Method 2: Try from document metadata
            if hasattr(self, 'current_document') and self.current_document:
                if hasattr(self.current_document, 'metadata') and self.current_document.metadata:
                    doc_id = getattr(self.current_document.metadata, 'document_id', None)
                    if doc_id:
                        self.logger.debug(f"GET_DOC_ID: Found document ID via metadata: {doc_id}")
                        return doc_id
            
            # Method 3: Generate from file path if available
            if hasattr(self, 'current_file_path') and self.current_file_path:
                from pathlib import Path
                file_name = Path(self.current_file_path).stem
                # Try to match the document ID format used in project files
                main_window = self._get_main_window()
                if main_window and hasattr(main_window, 'project_widget'):
                    project_docs = main_window.project_widget.get_project_documents()
                    for doc in project_docs:
                        if doc.get('path') == self.current_file_path or doc.get('name') == file_name + '.pdf':
                            doc_id = doc.get('id')
                            if doc_id:
                                self.logger.info(f"GET_DOC_ID: Found document ID via project lookup: {doc_id}")
                                return doc_id
            
            self.logger.warning("GET_DOC_ID: Could not resolve document ID")
            return None
            
        except Exception as e:
            self.logger.error(f"GET_DOC_ID: Error resolving document ID: {e}")
            return None
    
    def _ensure_document_id_consistency(self):
        """Ensure the current document has a consistent ID that matches the project."""
        try:
            # Check if document already has a valid ID
            current_id = getattr(self.current_document, 'id', None)
            if current_id:
                self.logger.debug(f"ENSURE_ID: Document already has ID: {current_id}")
                return
            
            # Try to find the matching document ID from project
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, 'project_widget'):
                project_docs = main_window.project_widget.get_project_documents()
                for doc in project_docs:
                    if (doc.get('path') == self.current_file_path or 
                        doc.get('name') == Path(self.current_file_path).name):
                        doc_id = doc.get('id')
                        if doc_id:
                            # Set the ID on the current document
                            self.current_document.id = doc_id
                            self.logger.info(f"ENSURE_ID: Set document ID to {doc_id}")
                            return
            
            self.logger.warning(f"ENSURE_ID: Could not find matching document ID in project")
            
        except Exception as e:
            self.logger.error(f"ENSURE_ID: Error ensuring document ID consistency: {e}")
    
    def _save_validation_state(self):
        """Save the current validation state to project storage."""
        try:
            document_id = self._get_current_document_id()
            if not document_id:
                self.logger.warning("SAVE_VALIDATION_STATE: Cannot save - missing document_id")
                return
            
            main_window = self._get_main_window()
            if not main_window or not hasattr(main_window, 'project_widget'):
                self.logger.warning("SAVE_VALIDATION_STATE: Cannot save - missing project widget")
                return
            
            # Get current project data
            project_data = main_window.project_widget.get_current_project()
            if not project_data:
                self.logger.warning("SAVE_VALIDATION_STATE: Cannot save - no active project")
                return
            
            # Find document in project
            documents = project_data.get('documents', [])
            for doc in documents:
                if doc.get('id') == document_id:
                    # Save validation state in the document
                    if 'validation_state' not in doc:
                        doc['validation_state'] = {}
                    
                    doc['validation_state'] = {
                        'is_complete': self.validation_complete,
                        'completed_at': datetime.now().isoformat() if self.validation_complete else None,
                        'total_selections': sum(len(selections) for selections in self.all_selections.values()),
                        'pages_with_selections': len(self.all_selections)
                    }
                    
                    # CRITICAL FIX: Save visual areas to the project
                    print(f"🔵 SAVE_VALIDATION_STATE: self.all_selections = {self.all_selections}")
                    print(f"🔵 SAVE_VALIDATION_STATE: Total selections: {sum(len(selections) for selections in self.all_selections.values())}")
                    
                    if self.all_selections:
                        # Convert area selections to the format expected by the project
                        visual_areas = {}
                        for page_num, selections in self.all_selections.items():
                            print(f"🔵 SAVE_VALIDATION_STATE: Processing page {page_num} with {len(selections)} selections")
                            for i, selection in enumerate(selections):
                                area_id = f"page_{page_num}_area_{i}"
                                visual_areas[area_id] = {
                                    'page': page_num,
                                    'bbox': selection.get('bbox', [0, 0, 0, 0]),
                                    'text': selection.get('text', ''),
                                    'selection_type': selection.get('type', 'manual'),
                                    'created_at': datetime.now().isoformat()
                                }
                                print(f"🔵 SAVE_VALIDATION_STATE: Created area {area_id}: {visual_areas[area_id]}")
                        
                        # Save visual areas to document
                        doc['visual_areas'] = visual_areas
                        print(f"🟢 SAVE_VALIDATION_STATE: ✅ Saved {len(visual_areas)} visual areas to project")
                        self.logger.info(f"SAVE_VALIDATION_STATE: ✅ Saved {len(visual_areas)} visual areas to project")
                    else:
                        print(f"🔴 SAVE_VALIDATION_STATE: ❌ No visual areas to save - self.all_selections is empty!")
                        self.logger.warning("SAVE_VALIDATION_STATE: No visual areas to save")
                    
                    # Auto-save project
                    if hasattr(main_window.project_widget, 'save_current_project'):
                        save_result = main_window.project_widget.save_current_project()
                        if save_result:
                            self.logger.info(f"SAVE_VALIDATION_STATE: ✅ Saved validation state for document {document_id}")
                        else:
                            self.logger.error(f"SAVE_VALIDATION_STATE: ❌ Failed to save project with validation state")
                    break
            
        except Exception as e:
            self.logger.error(f"SAVE_VALIDATION_STATE: Error saving validation state: {e}")
    
    def _load_validation_state(self):
        """Load the validation state from project storage."""
        try:
            document_id = self._get_current_document_id()
            if not document_id:
                self.logger.warning("LOAD_VALIDATION_STATE: Cannot load - missing document_id")
                return
            
            main_window = self._get_main_window()
            if not main_window or not hasattr(main_window, 'project_widget'):
                self.logger.warning("LOAD_VALIDATION_STATE: Cannot load - missing project widget")
                return
            
            # Get current project data
            project_data = main_window.project_widget.get_current_project()
            if not project_data:
                self.logger.warning("LOAD_VALIDATION_STATE: Cannot load - no active project")
                return
            
            # Find document in project
            documents = project_data.get('documents', [])
            for doc in documents:
                if doc.get('id') == document_id:
                    validation_state = doc.get('validation_state', {})
                    
                    if validation_state:
                        is_complete = validation_state.get('is_complete', False)
                        completed_at = validation_state.get('completed_at')
                        
                        self.logger.info(f"LOAD_VALIDATION_STATE: Found validation state - complete: {is_complete}, completed_at: {completed_at}")
                        
                        # Restore validation state
                        self.validation_complete = is_complete
                        
                        # Update UI based on validation state
                        if self.validation_complete:
                            # Keep UI functional but show completion status
                            self.complete_btn.setText("✅ Re-validate")
                            self.complete_btn.setEnabled(True)  # Allow re-validation
                            self.clear_page_btn.setEnabled(True)  # Allow clearing
                            self.status_message.emit(f"Document validation completed at {completed_at} - Areas loaded and ready")
                            self.logger.info(f"LOAD_VALIDATION_STATE: ✅ Restored completed validation state for document {document_id}")
                        else:
                            # Standard validation UI
                            self.complete_btn.setText("Complete Validation")
                            self.complete_btn.setEnabled(True)
                            self.clear_page_btn.setEnabled(True)
                            self.logger.info(f"LOAD_VALIDATION_STATE: ✅ Restored incomplete validation state for document {document_id}")
                    else:
                        self.logger.info(f"LOAD_VALIDATION_STATE: No validation state found for document {document_id}")
                    break
            
        except Exception as e:
            self.logger.error(f"LOAD_VALIDATION_STATE: Error loading validation state: {e}")
    
    def _refresh_pdf_viewer_areas(self, page: int):
        """Force refresh of PDF viewer areas for a specific page."""
        try:
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, 'pdf_viewer'):
                pdf_viewer = main_window.pdf_viewer
                if hasattr(pdf_viewer, 'page_label') and hasattr(pdf_viewer.page_label, 'load_persistent_areas'):
                    page_label = pdf_viewer.page_label
                    document_id = self._get_current_document_id()
                    if document_id:
                        # Force reload areas for the page
                        page_label.load_persistent_areas(document_id, page)
                        page_label.update()  # Force visual refresh
                        self.logger.info(f"REFRESH: Forced refresh of PDF viewer areas for page {page}")
                    else:
                        self.logger.warning("REFRESH: No document ID available for area refresh")
                else:
                    self.logger.warning("REFRESH: PDF viewer doesn't support area refresh")
            else:
                self.logger.warning("REFRESH: No PDF viewer available")
        except Exception as e:
            self.logger.error(f"REFRESH: Error refreshing PDF viewer areas: {e}")
            import traceback
            self.logger.error(f"REFRESH: Traceback: {traceback.format_exc()}")
    
    def load_extracted_content_from_project(self):
        """Load extracted content from project storage when document is loaded."""
        try:
            self.logger.info("LOAD EXTRACTED: Starting load_extracted_content_from_project")
            
            document_id = self._get_current_document_id()
            self.logger.info(f"LOAD EXTRACTED: Retrieved document_id = {document_id}")
            
            if not document_id:
                self.logger.warning("LOAD EXTRACTED: Cannot load content - missing document_id")
                return
            
            # Get main window to access project data
            main_window = self._get_main_window()
            if not main_window:
                self.logger.warning("LOAD EXTRACTED: Cannot load content - missing main_window")
                return
            
            # Try to get project manager
            if hasattr(main_window, 'project_widget') and main_window.project_widget:
                project_manager = main_window.project_widget
                
                # Look for document in project
                for document in project_manager.documents:
                    if document.get('id') == document_id:
                        extracted_content = document.get('extracted_content', {})
                        if extracted_content:
                            self.logger.info(f"LOAD EXTRACTED: Found extracted content with {len(extracted_content.get('text_elements', []))} text elements")
                            
                            # Display extracted content (this should be implemented in the UI)
                            self._display_extracted_content(extracted_content)
                            return
                        else:
                            self.logger.info("LOAD EXTRACTED: No extracted content found in document")
                            return
                
                self.logger.warning("LOAD EXTRACTED: Document not found in project")
            else:
                self.logger.warning("LOAD EXTRACTED: Project manager not available")
                
        except Exception as e:
            self.logger.error(f"LOAD EXTRACTED: Error loading extracted content: {e}")
            import traceback
            self.logger.error(f"LOAD EXTRACTED: Traceback: {traceback.format_exc()}")
    
    def load_extracted_content_directly(self, extracted_content):
        """Load extracted content directly into this widget (called from main window)."""
        try:
            self.logger.info(f"LOAD EXTRACTED DIRECTLY: Loading {len(extracted_content)} content keys")
            self._display_extracted_content(extracted_content)
        except Exception as e:
            self.logger.error(f"LOAD EXTRACTED DIRECTLY: Error: {e}")
    
    def _display_extracted_content(self, extracted_content):
        """Display extracted content in the UI."""
        try:
            text_elements = extracted_content.get('text_elements', [])
            self.logger.info(f"DISPLAY EXTRACTED: Displaying {len(text_elements)} text elements")
            
            # Get the main window to access PageValidationWidget
            main_window = self._get_main_window()
            if not main_window:
                self.logger.warning("DISPLAY EXTRACTED: Cannot find main window")
                return
            
            # Check if we have a PageValidationWidget (QA widget)
            if hasattr(main_window, 'qa_widget') and main_window.qa_widget:
                page_validation_widget = main_window.qa_widget
                
                # Load extracted content into PageValidationWidget
                if hasattr(page_validation_widget, 'load_extracted_content'):
                    page_validation_widget.load_extracted_content(extracted_content)
                    self.logger.info("DISPLAY EXTRACTED: Loaded extracted content into PageValidationWidget")
                else:
                    self.logger.warning("DISPLAY EXTRACTED: PageValidationWidget doesn't have load_extracted_content method")
            else:
                self.logger.warning("DISPLAY EXTRACTED: No PageValidationWidget available")
            
        except Exception as e:
            self.logger.error(f"DISPLAY EXTRACTED: Error displaying content: {e}")
    
    def load_existing_areas_from_project(self):
        """Load existing areas from project storage when document is loaded."""
        try:
            self.logger.info("LOAD EXISTING: Starting load_existing_areas_from_project")
            
            # Also load extracted content
            self.load_extracted_content_from_project()
            
            document_id = self._get_current_document_id()
            self.logger.info(f"LOAD EXISTING: Retrieved document_id = {document_id}")
            
            if not document_id:
                self.logger.warning("LOAD EXISTING: Cannot load areas - missing document_id")
                return
            
            # Try to get area storage manager - first check if it's set directly on this widget
            area_storage = None
            if hasattr(self, 'area_storage_manager') and self.area_storage_manager:
                area_storage = self.area_storage_manager
                self.logger.info("LOAD EXISTING: Found area_storage_manager on widget itself")
            else:
                # Fall back to finding it through main window
                main_window = self._get_main_window()
                self.logger.info(f"LOAD EXISTING: Retrieved main_window = {main_window is not None}")
                
                if not main_window:
                    self.logger.warning("LOAD EXISTING: Cannot load areas - missing main_window")
                    return
                    
                if not hasattr(main_window, 'area_storage_manager'):
                    self.logger.warning("LOAD EXISTING: Cannot load areas - missing area_storage_manager")
                    return
                
                area_storage = main_window.area_storage_manager
                self.logger.info("LOAD EXISTING: Found area_storage_manager on main window")
            
            if not area_storage:
                self.logger.warning("LOAD EXISTING: Cannot load areas - no area_storage_manager found")
                return
                
            self.logger.info(f"LOAD EXISTING: Got area_storage_manager = {area_storage is not None}")
            
            all_areas = area_storage.load_areas(document_id)
            self.logger.info(f"LOAD EXISTING: area_storage.load_areas returned {len(all_areas) if all_areas else 0} areas")
            
            if not all_areas:
                self.logger.info("LOAD EXISTING: No existing areas found in project")
                return
            
            self.logger.info(f"LOAD EXISTING: Loading {len(all_areas)} existing areas from project")
            
            # Clear current selections first
            self.all_selections.clear()
            
            # Group areas by page for proper naming
            areas_by_page = {}
            for area_id, area in all_areas.items():
                page = area.page
                if page not in areas_by_page:
                    areas_by_page[page] = []
                areas_by_page[page].append((area_id, area))
            
            # Process each page to ensure proper sequential naming
            for page, page_areas in areas_by_page.items():
                # Sort areas by creation time to maintain original order
                page_areas.sort(key=lambda x: x[1].created_at if x[1].created_at else datetime.min)
                
                # Track type counters for this page
                type_counters = {}
                
                for area_id, area in page_areas:
                    area_type = area.area_type.value
                    
                    # Generate proper sequential name
                    if area_type not in type_counters:
                        type_counters[area_type] = 0
                    type_counters[area_type] += 1
                    
                    # Use the same naming convention as new areas
                    display_page = page if page >= 1 else 1
                    area_name = f"{area_type}_{display_page}_{type_counters[area_type]:02d}"
                    
                    area_dict = {
                        'id': area.id,
                        'name': area_name,  # Use proper sequential naming
                        'page': area.page,
                        'bbox': area.bbox,
                        'type': area.area_type.value,
                        'color': area.color,
                        'widget_rect': area.widget_rect,
                        'created_at': area.created_at.isoformat() if area.created_at else '',
                        'user_notes': area.user_notes
                    }
                    
                    # Add to internal storage
                    if page not in self.all_selections:
                        self.all_selections[page] = []
                    self.all_selections[page].append(area_dict)
            
            # Update UI to show loaded areas
            self._update_selection_list()
            self._update_statistics()
            self._update_navigation_buttons()
            
            # Auto-select first area if available and show preview
            if self.selection_list.count() > 0:
                print(f"🔵 LOAD EXISTING: Auto-selecting first area for preview...")
                first_item = self.selection_list.item(0)
                self.selection_list.setCurrentItem(first_item)
                self._update_area_preview()
                self._highlight_current_area()
                print(f"🟢 LOAD EXISTING: First area selected and highlighted")
            
            total_loaded = sum(len(selections) for selections in self.all_selections.values())
            self.status_message.emit(f"Loaded {total_loaded} existing areas from project - ready for validation")
            self.logger.info(f"LOAD EXISTING: Successfully loaded {total_loaded} areas with proper naming and UI updates")
            
        except Exception as e:
            self.logger.error(f"LOAD EXISTING: Error loading existing areas: {e}")
            import traceback
            self.logger.error(f"LOAD EXISTING: Traceback: {traceback.format_exc()}")
    
    def _try_recover_document_context(self) -> bool:
        """Try to recover document context from main window/PDF viewer."""
        try:
            main_window = self._get_main_window()
            if not main_window:
                return False
            
            # Try to get the currently loaded document from PDF viewer
            if hasattr(main_window, 'pdf_viewer') and main_window.pdf_viewer:
                pdf_viewer = main_window.pdf_viewer
                current_document_path = getattr(pdf_viewer, 'current_document_path', None)
                current_document_id = getattr(pdf_viewer, 'current_document_id', None)
                
                if current_document_path and Path(current_document_path).exists():
                    self.logger.info(f"RECOVER: Found document in PDF viewer: {current_document_path}")
                    
                    # Create a document object
                    from ..models.document_models import Document, DocumentMetadata
                    from ..config.constants import DocumentType, ProcessingStatus, QualityLevel
                    from ..models.document_models import ProcessingConfiguration
                    from datetime import datetime
                    
                    # Create metadata
                    file_stat = Path(current_document_path).stat()
                    metadata = DocumentMetadata(
                        file_path=current_document_path,
                        file_name=Path(current_document_path).name,
                        file_size=file_stat.st_size,
                        creation_date=datetime.fromtimestamp(file_stat.st_ctime),
                        modification_date=datetime.fromtimestamp(file_stat.st_mtime),
                        page_count=getattr(pdf_viewer, 'total_pages', 0)
                    )
                    
                    # Create document object
                    document_id = current_document_id or Path(current_document_path).stem
                    document = Document(
                        id=document_id,
                        metadata=metadata,
                        document_type=DocumentType.ICAO,
                        processing_status=ProcessingStatus.COMPLETED,
                        processing_config=ProcessingConfiguration(),
                        quality_level=QualityLevel.HIGH,
                        quality_score=0.95
                    )
                    
                    # Set the document context
                    self.current_document = document
                    self.current_file_path = current_document_path
                    
                    self.logger.info(f"RECOVER: Successfully recovered document context for {Path(current_document_path).name}")
                    return True
            
            # Try to get document from document state manager
            if hasattr(main_window, 'document_state_manager'):
                doc_state = main_window.document_state_manager
                active_doc = doc_state.get_active_document()
                if active_doc:
                    doc_id, doc_metadata = active_doc
                    doc_path = doc_metadata.get('path') or doc_metadata.get('file_path')
                    
                    if doc_path and Path(doc_path).exists():
                        self.logger.info(f"RECOVER: Found document in state manager: {doc_path}")
                        
                        # Create document object from state manager data
                        from ..models.document_models import Document, DocumentMetadata
                        from ..config.constants import DocumentType, ProcessingStatus, QualityLevel
                        from ..models.document_models import ProcessingConfiguration
                        from datetime import datetime
                        
                        metadata = DocumentMetadata(
                            file_path=doc_path,
                            file_name=Path(doc_path).name,
                            file_size=doc_metadata.get('file_size', 0),
                            creation_date=datetime.now(),
                            modification_date=datetime.now(),
                            page_count=doc_metadata.get('page_count', 0)
                        )
                        
                        document = Document(
                            id=doc_id,
                            metadata=metadata,
                            document_type=DocumentType.ICAO,
                            processing_status=ProcessingStatus.COMPLETED,
                            processing_config=ProcessingConfiguration(),
                            quality_level=QualityLevel.HIGH,
                            quality_score=0.95
                        )
                        
                        # Set the document context
                        self.current_document = document
                        self.current_file_path = doc_path
                        
                        self.logger.info(f"RECOVER: Successfully recovered document context from state manager")
                        return True
            
            self.logger.warning("RECOVER: Could not recover document context")
            return False
            
        except Exception as e:
            self.logger.error(f"RECOVER: Error recovering document context: {e}")
            return False
    
    def _try_alternative_document_recovery(self) -> bool:
        """Try alternative methods to recover document context for area preview."""
        try:
            # Method 1: Try to find document files in current directory
            current_dir = Path.cwd()
            for pdf_file in current_dir.glob("*.pdf"):
                self.logger.info(f"ALT_RECOVER: Found PDF file: {pdf_file}")
                
                # Check if this PDF might be related to our current project
                document_id = self._get_current_document_id()
                if document_id and pdf_file.stem == document_id:
                    self.logger.info(f"ALT_RECOVER: PDF matches document ID: {document_id}")
                    self.current_file_path = str(pdf_file)
                    
                    # Create minimal document object for preview purposes
                    self.current_document = type('MockDocument', (), {
                        'id': document_id,
                        'file_path': str(pdf_file)
                    })()
                    
                    return True
            
            # Method 2: Try to find .tore files and look for associated PDFs
            for tore_file in current_dir.glob("*.tore"):
                pdf_file = tore_file.with_suffix('.pdf')
                if pdf_file.exists():
                    self.logger.info(f"ALT_RECOVER: Found associated PDF for {tore_file.name}: {pdf_file}")
                    self.current_file_path = str(pdf_file)
                    
                    # Create minimal document object
                    self.current_document = type('MockDocument', (), {
                        'id': tore_file.stem,
                        'file_path': str(pdf_file)
                    })()
                    
                    return True
            
            # Method 3: Check if we can get document path from project data
            try:
                main_window = self._get_main_window()
                if main_window and hasattr(main_window, 'project_widget'):
                    project_widget = main_window.project_widget
                    if hasattr(project_widget, 'current_project') and project_widget.current_project:
                        project_path = getattr(project_widget, 'project_file_path', None)
                        if project_path:
                            project_dir = Path(project_path).parent
                            project_stem = Path(project_path).stem
                            
                            # Look for PDF with same name as project
                            pdf_file = project_dir / f"{project_stem}.pdf"
                            if pdf_file.exists():
                                self.logger.info(f"ALT_RECOVER: Found project PDF: {pdf_file}")
                                self.current_file_path = str(pdf_file)
                                
                                self.current_document = type('MockDocument', (), {
                                    'id': project_stem,
                                    'file_path': str(pdf_file)
                                })()
                                
                                return True
            except Exception as e:
                self.logger.debug(f"ALT_RECOVER: Project method failed: {e}")
            
            self.logger.warning("ALT_RECOVER: All alternative recovery methods failed")
            return False
            
        except Exception as e:
            self.logger.error(f"ALT_RECOVER: Error in alternative document recovery: {e}")
            return False