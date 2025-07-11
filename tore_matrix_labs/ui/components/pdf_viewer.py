"""
PDF viewer widget with page navigation and document display.
"""

import logging
import fitz  # PyMuPDF
from pathlib import Path
from typing import Optional

from ..qt_compat import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QSlider, QSpinBox, QGroupBox, QPixmap, 
    QSizePolicy, Qt, QMessageBox, QComboBox, QFrame,
    QPainter, QPen, QBrush, QColor, QRectF, QPointF,
    QMouseEvent, pyqtSignal
)
from .enhanced_pdf_highlighting import create_multiline_highlight, draw_multiline_highlight, MultiLineHighlight
from .enhanced_drag_select import EnhancedDragSelectLabel
from ..highlighting import HighlightingEngine, HighlightStyle


class DragSelectLabel(QLabel):
    """QLabel with drag-to-select functionality."""
    
    area_selected = pyqtSignal(dict)
    area_preview_update = pyqtSignal(dict)  # Real-time preview during dragging
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pdf_viewer = parent
        self.is_selecting = False
        self.selection_start = None
        self.selection_end = None
        self.selection_rect = None
        
    def mousePressEvent(self, event: QMouseEvent):
        """Start area selection."""
        if event.button() == Qt.LeftButton:
            self.is_selecting = True
            self.selection_start = event.pos()
            self.selection_end = event.pos()
            self.selection_rect = QRectF(self.selection_start, self.selection_end)
            self.update()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Update selection rectangle and emit real-time preview."""
        if self.is_selecting:
            self.selection_end = event.pos()
            self.selection_rect = QRectF(self.selection_start, self.selection_end).normalized()
            
            # Emit real-time preview update if rectangle is large enough
            if self.selection_rect.width() > 20 and self.selection_rect.height() > 20:
                self._emit_preview_update()
            
            self.update()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Complete area selection."""
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False
            
            # Check if selection is large enough
            if self.selection_rect and self.selection_rect.width() > 10 and self.selection_rect.height() > 10:
                self._handle_area_selection()
            
            self.selection_rect = None
            self.update()
        super().mouseReleaseEvent(event)
    
    def paintEvent(self, event):
        """Paint the label and selection rectangle."""
        super().paintEvent(event)
        
        if self.is_selecting and self.selection_rect:
            painter = QPainter(self)
            painter.setPen(QPen(QColor(255, 0, 0, 200), 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(255, 0, 0, 50)))
            painter.drawRect(self.selection_rect)
    
    def _handle_area_selection(self):
        """Handle completed area selection."""
        if not self.pdf_viewer or not self.selection_rect:
            return
        
        # Import area type dialog
        from ..dialogs.area_type_dialog import AreaTypeDialog
        
        # Show area type selection dialog
        dialog = AreaTypeDialog(self)
        if dialog.exec_() == dialog.Accepted:
            area_type = dialog.get_selected_type()
            if area_type:
                # Convert selection to PDF coordinates
                bbox = self._convert_to_pdf_coordinates(self.selection_rect)
                
                # Get active document info from PDF viewer
                document_id = None
                document_path = None
                if hasattr(self.pdf_viewer, 'current_document_id'):
                    document_id = self.pdf_viewer.current_document_id
                if hasattr(self.pdf_viewer, 'current_document_path'):
                    document_path = self.pdf_viewer.current_document_path
                    
                if not document_id:
                    print("🔴 DRAG LABEL: Warning - No active document ID found!")
                    # Generate temporary ID based on document path
                    if document_path:
                        import hashlib
                        document_id = f"temp_{hashlib.md5(document_path.encode()).hexdigest()[:8]}"
                    else:
                        document_id = "unknown_document"
                
                # Create area data with document information
                import uuid
                from datetime import datetime
                
                area_data = {
                    'id': f"area_{uuid.uuid4().hex[:8]}",
                    'document_id': document_id,  # Include document ID
                    'document_path': document_path,  # Include document path
                    'type': area_type.value,  # Use enum value
                    'bbox': bbox,
                    'page': self.pdf_viewer.current_page + 1,  # Convert 0-based to 1-based
                    'selection_rect': [
                        int(self.selection_rect.x()),
                        int(self.selection_rect.y()),
                        int(self.selection_rect.width()),
                        int(self.selection_rect.height())
                    ],
                    'created_at': datetime.now().isoformat(),
                    'status': 'selected'
                }
                
                # Emit signal
                print(f"🔴 DRAG LABEL: Emitting area_selected signal for document: {document_id}")
                print(f"🔴 DRAG LABEL: Area data: {area_data}")
                self.area_selected.emit(area_data)
    
    def _convert_to_pdf_coordinates(self, rect):
        """Convert widget coordinates to PDF coordinates using accurate scaling."""
        if not self.pdf_viewer or not self.pdf_viewer.current_document:
            print(f"No PDF viewer or document, using raw coordinates: {rect}")
            return [rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height()]
        
        try:
            # Use stored display state for accurate conversion
            zoom_factor = self.pdf_viewer.current_zoom_factor
            page_rect = self.pdf_viewer.current_page_rect
            pixmap_size = self.pdf_viewer.current_pixmap_size
            
            if not page_rect or not pixmap_size:
                print(f"Missing display state, using fallback")
                return [rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height()]
            
            print(f"Converting coordinates:")
            print(f"  Widget rect: {rect}")
            print(f"  Zoom factor: {zoom_factor}")
            print(f"  Page rect: {page_rect}")
            print(f"  Pixmap size: {pixmap_size}")
            
            # The widget coordinates are relative to the displayed pixmap
            # We need to convert them back to PDF coordinates
            # Since the pixmap is rendered at zoom_factor, we divide by zoom_factor
            x1 = rect.x() / zoom_factor
            y1 = rect.y() / zoom_factor
            x2 = (rect.x() + rect.width()) / zoom_factor
            y2 = (rect.y() + rect.height()) / zoom_factor
            
            converted = [x1, y1, x2, y2]
            print(f"  Converted coordinates: {converted}")
            
            return converted
            
        except Exception as e:
            print(f"Error converting coordinates: {e}")
            import traceback
            traceback.print_exc()
            return [rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height()]
    
    def _emit_preview_update(self):
        """Emit real-time preview update during dragging."""
        if not self.selection_rect or not self.pdf_viewer:
            return
        
        # Create temporary area data for preview
        bbox = self._convert_to_pdf_coordinates(self.selection_rect)
        
        preview_data = {
            'id': 'preview_temp',
            'type': 'PREVIEW',  # Temporary type for real-time preview
            'bbox': bbox,
            'page': self.pdf_viewer.current_page,
            'selection_rect': [
                int(self.selection_rect.x()),
                int(self.selection_rect.y()),
                int(self.selection_rect.width()),
                int(self.selection_rect.height())
            ],
            'is_preview': True  # Flag to indicate this is a temporary preview
        }
        
        # Emit preview update signal
        print(f"🟠 DRAG LABEL: Emitting area_preview_update signal: {preview_data}")
        self.area_preview_update.emit(preview_data)


class PDFViewer(QWidget):
    """PDF viewer widget with full page navigation and drag-to-select."""
    
    # Signals
    area_selected = pyqtSignal(dict)  # Emitted when user drags to select an area
    area_preview_update = pyqtSignal(dict)  # Emitted during dragging for real-time preview
    page_changed = pyqtSignal(int)  # Emitted when page changes
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Document state
        self.current_document: Optional[fitz.Document] = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom_level = 1.0
        self.current_file_path: Optional[str] = None
        
        # Display state for accurate coordinate conversion
        self.current_zoom_factor = 1.0
        self.current_page_rect = None
        self.current_pixmap_size = None
        
        # Highlighting state (NEW SYSTEM)
        self.highlighting_engine = HighlightingEngine()
        self.highlighting_engine.set_pdf_viewer(self)
        self.highlight_style = HighlightStyle()
        
        # Legacy highlighting state (to be removed)
        self.highlight_bbox = None  # Current highlight bounding box
        self.highlight_search_text = None  # Text being highlighted for precise location
        self.highlight_color = QColor(255, 255, 0, 120)  # Brighter yellow with transparency
        self.current_multiline_highlight = None  # Current multi-line highlight object
        
        # Drag-to-select state
        self.is_selecting = False
        self.selection_start = None
        self.selection_end = None
        self.selection_rect = None
        
        self._init_ui()
        self.logger.info("PDF viewer initialized")
    
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
        self.doc_title_label = QLabel("Document Preview")
        self.doc_title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(self.doc_title_label)
        
        # Controls row
        controls_layout = QHBoxLayout()
        
        # Zoom controls
        zoom_label = QLabel("Zoom:")
        controls_layout.addWidget(zoom_label)
        
        self.zoom_combo = QComboBox()
        self.zoom_combo.addItems(["50%", "75%", "100%", "125%", "150%", "200%", "Fit Width", "Fit Page"])
        self.zoom_combo.setCurrentText("Fit Width")  # Better default for accurate selection
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
        self.scroll_area.setWidgetResizable(False)  # Important: Don't auto-resize widget
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Create page display label with drag-to-select
        self.page_label = EnhancedDragSelectLabel(self)
        self.drag_label = self.page_label  # Alias for compatibility
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setMinimumSize(400, 300)
        self.page_label.setStyleSheet("border: 1px solid #ddd; background-color: white;")
        # Don't use expanding policy - let it be its natural size
        self.page_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        # Connect drag-select signals with debugging
        self.page_label.area_selected.connect(self._on_area_selected_debug)
        self.page_label.area_preview_update.connect(self._on_area_preview_update_debug)
        
        self.scroll_area.setWidget(self.page_label)
        parent_layout.addWidget(self.scroll_area)
    
    def _create_navigation_footer(self, parent_layout):
        """Create navigation controls at the bottom."""
        nav_frame = QFrame()
        nav_frame.setFrameStyle(QFrame.StyledPanel)
        nav_layout = QHBoxLayout()
        
        # Previous page button
        self.prev_btn = QPushButton("◀ Previous")
        self.prev_btn.clicked.connect(self._previous_page)
        self.prev_btn.setEnabled(False)
        nav_layout.addWidget(self.prev_btn)
        
        # Page number input
        page_layout = QHBoxLayout()
        page_layout.addWidget(QLabel("Page:"))
        
        self.page_spinbox = QSpinBox()
        self.page_spinbox.setMinimum(1)
        self.page_spinbox.valueChanged.connect(self._go_to_page)
        page_layout.addWidget(self.page_spinbox)
        
        self.total_pages_label = QLabel("of 0")
        page_layout.addWidget(self.total_pages_label)
        
        nav_layout.addLayout(page_layout)
        
        # Page slider for quick navigation
        self.page_slider = QSlider(Qt.Horizontal)
        self.page_slider.setMinimum(1)
        self.page_slider.valueChanged.connect(self._slider_changed)
        nav_layout.addWidget(self.page_slider)
        
        # Next page button
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.clicked.connect(self._next_page)
        self.next_btn.setEnabled(False)
        nav_layout.addWidget(self.next_btn)
        
        nav_frame.setLayout(nav_layout)
        parent_layout.addWidget(nav_frame)
    
    def load_document(self, file_path: str):
        """Load document for viewing."""
        try:
            # Check if file exists
            if not Path(file_path).exists():
                self._show_error(f"File not found: {file_path}")
                return
            
            # Close current document if any
            if self.current_document:
                self.current_document.close()
            
            # Open new document
            self.current_document = fitz.open(file_path)
            self.current_file_path = file_path
            self.current_document_path = file_path  # Store for cutting tool access
            self.total_pages = len(self.current_document)
            self.current_page = 0
            
            # Update UI
            self.doc_title_label.setText(f"Document: {Path(file_path).name}")
            self.page_info_label.setText(f"Page 1 of {self.total_pages}")
            self.total_pages_label.setText(f"of {self.total_pages}")
            
            # Update controls
            self.page_spinbox.setMaximum(self.total_pages)
            self.page_spinbox.setValue(1)
            self.page_slider.setMaximum(self.total_pages)
            self.page_slider.setValue(1)
            
            # Enable navigation if multi-page
            self._update_navigation_state()
            
            # Display first page
            self._display_current_page()
            
            self.logger.info(f"Loaded document: {file_path} ({self.total_pages} pages)")
            
        except Exception as e:
            self._show_error(f"Failed to load document: {str(e)}")
            self.logger.error(f"Failed to load document {file_path}: {str(e)}")
    
    def _on_area_selected_debug(self, area_data):
        """Debug wrapper for area selected signal."""
        print(f"🔴 PDF VIEWER: Area selected signal emitted: {area_data}")
        self.area_selected.emit(area_data)
    
    def _on_area_preview_update_debug(self, preview_data):
        """Debug wrapper for area preview update signal."""
        print(f"🟡 PDF VIEWER: Area preview update signal emitted: {preview_data}")
        self.area_preview_update.emit(preview_data)
    
    def _display_current_page(self):
        """Display the current page."""
        if not self.current_document or self.current_page >= self.total_pages:
            return
        
        try:
            # Get page
            page = self.current_document[self.current_page]
            
            # Calculate zoom matrix
            zoom_factor = self._get_zoom_factor()
            mat = fitz.Matrix(zoom_factor, zoom_factor)
            
            # Store current display state for coordinate conversion
            self.current_zoom_factor = zoom_factor
            self.current_page_rect = page.rect
            
            # Render page as pixmap
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to QPixmap
            img_data = pix.tobytes("ppm")
            qpixmap = QPixmap()
            qpixmap.loadFromData(img_data)
            
            # Store current pixmap size for coordinate conversion
            self.current_pixmap_size = qpixmap.size()
            
            # Update highlighting engine current page (convert to 1-based)
            if hasattr(self, 'highlighting_engine'):
                self.highlighting_engine.update_current_page(self.current_page + 1)
            
            # Add highlighting if available
            if self.highlight_bbox or self.current_multiline_highlight:
                qpixmap = self._add_highlight_to_pixmap(qpixmap, zoom_factor)
            
            # Display in label with exact sizing for accurate coordinates
            self.page_label.setPixmap(qpixmap)
            self.page_label.setFixedSize(qpixmap.size())  # Exact size, no scaling
            
            # Update page info
            self.page_info_label.setText(f"Page {self.current_page + 1} of {self.total_pages}")
            
            print(f"📄 PDF Display: zoom={zoom_factor:.2f}, page_rect={page.rect}, pixmap_size={qpixmap.size()}")
            
        except Exception as e:
            self._show_error(f"Failed to display page: {str(e)}")
            self.logger.error(f"Failed to display page {self.current_page}: {str(e)}")
    
    def _get_zoom_factor(self) -> float:
        """Get current zoom factor."""
        zoom_text = self.zoom_combo.currentText()
        
        if zoom_text == "Fit Width":
            # Calculate zoom to fit width
            if self.current_document:
                page = self.current_document[self.current_page]
                page_width = page.rect.width
                available_width = self.scroll_area.width() - 20  # Account for scrollbar
                return available_width / page_width
            return 1.0
        elif zoom_text == "Fit Page":
            # Calculate zoom to fit entire page
            if self.current_document:
                page = self.current_document[self.current_page]
                page_rect = page.rect
                available_width = self.scroll_area.width() - 20
                available_height = self.scroll_area.height() - 20
                width_zoom = available_width / page_rect.width
                height_zoom = available_height / page_rect.height
                return min(width_zoom, height_zoom)
            return 1.0
        else:
            # Parse percentage
            try:
                percent = int(zoom_text.replace('%', ''))
                return percent / 100.0
            except:
                return 1.0
    
    def _previous_page(self):
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self._display_current_page()
            self._update_navigation_state()
            self._update_controls()
            self.page_changed.emit(self.current_page + 1)  # Emit 1-based page number
    
    def _next_page(self):
        """Go to next page."""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._display_current_page()
            self._update_navigation_state()
            self._update_controls()
            self.page_changed.emit(self.current_page + 1)  # Emit 1-based page number
    
    def _go_to_page(self, page_number: int):
        """Go to specific page number (1-indexed)."""
        if 1 <= page_number <= self.total_pages:
            self.current_page = page_number - 1
            self._display_current_page()
            self._update_navigation_state()
            # Update slider without triggering signal
            self.page_slider.blockSignals(True)
            self.page_slider.setValue(page_number)
            self.page_slider.blockSignals(False)
            # Update spinbox without triggering signal
            self.page_spinbox.blockSignals(True)
            self.page_spinbox.setValue(page_number)
            self.page_spinbox.blockSignals(False)
            self.page_changed.emit(page_number)  # Emit 1-based page number
    
    def _slider_changed(self, value: int):
        """Handle slider value change."""
        if self.current_document and 1 <= value <= self.total_pages:
            self.current_page = value - 1
            self._display_current_page()
            self._update_navigation_state()
            # Update spinbox without triggering signal
            self.page_spinbox.blockSignals(True)
            self.page_spinbox.setValue(value)
            self.page_spinbox.blockSignals(False)
            self.page_changed.emit(value)  # Emit 1-based page number
    
    def _on_zoom_changed(self, zoom_text: str):
        """Handle zoom level change."""
        if self.current_document:
            self._display_current_page()
    
    def _update_navigation_state(self):
        """Update navigation button states."""
        if not self.current_document:
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            return
        
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(self.current_page < self.total_pages - 1)
    
    def _update_controls(self):
        """Update control values."""
        if self.current_document:
            # Update page info
            self.page_info_label.setText(f"Page {self.current_page + 1} of {self.total_pages}")
    
    def _show_empty_state(self):
        """Show empty state when no document is loaded."""
        self.page_label.setText("No document loaded\n\nSelect a document from the project tree to preview")
        self.page_label.setPixmap(QPixmap())  # Clear any existing pixmap
        self.doc_title_label.setText("Document Preview")
        self.page_info_label.setText("No document")
        self.total_pages_label.setText("of 0")
        self.page_spinbox.setMaximum(1)
        self.page_slider.setMaximum(1)
        self._update_navigation_state()
    
    def _show_error(self, message: str):
        """Show error message."""
        self.page_label.setText(f"Error loading document:\n{message}")
        self.page_label.setPixmap(QPixmap())
        self.logger.error(message)
    
    def clear(self):
        """Clear viewer."""
        if self.current_document:
            self.current_document.close()
            self.current_document = None
        
        self.current_file_path = None
        self.current_page = 0
        self.total_pages = 0
        self._show_empty_state()
    
    def _get_highlight_colors(self, highlight_type, search_text=None):
        """Get color scheme for different highlight types."""
        
        # Color schemes for different highlight types
        color_schemes = {
            'issue': {
                'fill': (255, 255, 0, 180),      # Yellow background
                'border': (255, 0, 0, 255),      # Red border
                'border_width': 2
            },
            'active_issue': {
                'fill': (255, 255, 0, 220),      # Bright yellow background
                'border': (255, 0, 0, 255),      # Red border
                'border_width': 3
            },
            'manual_image': {
                'fill': (255, 0, 0, 120),        # Red background
                'border': (139, 0, 0, 255),      # Dark red border
                'border_width': 2
            },
            'manual_table': {
                'fill': (0, 0, 255, 120),        # Blue background
                'border': (0, 0, 139, 255),      # Dark blue border
                'border_width': 2
            },
            'manual_diagram': {
                'fill': (128, 0, 128, 120),      # Purple background
                'border': (75, 0, 130, 255),     # Indigo border
                'border_width': 2
            },
            'auto_conflict': {
                'fill': (255, 165, 0, 150),      # Orange background
                'border': (255, 140, 0, 255),    # Dark orange border
                'border_width': 2
            },
            'text_selection': {
                'fill': (0, 255, 0, 100),        # Light green background
                'border': (0, 128, 0, 255),      # Green border
                'border_width': 1
            },
            'cursor': {
                'fill': (255, 0, 255, 50),       # Magenta background
                'border': (255, 0, 255, 255),    # Magenta border
                'border_width': 1
            },
            'navigation': {
                'fill': (0, 255, 255, 30),       # Light cyan background
                'border': (0, 255, 255, 100),    # Cyan border
                'border_width': 1
            },
            'clear': {
                'fill': (0, 0, 0, 0),            # Transparent
                'border': (0, 0, 0, 0),          # Transparent
                'border_width': 0
            },
            'auto_detected_table': {
                'fill': (255, 165, 0, 60),       # Light orange background (needs validation)
                'border': (255, 140, 0, 200),    # Orange border (dashed style)
                'border_width': 2
            },
            'auto_detected_image': {
                'fill': (255, 192, 203, 60),     # Light pink background (needs validation)
                'border': (255, 105, 180, 200),  # Pink border (dashed style)
                'border_width': 2
            },
            'auto_detected_diagram': {
                'fill': (221, 160, 221, 60),     # Light plum background (needs validation)
                'border': (186, 85, 211, 200),   # Medium orchid border (dashed style)
                'border_width': 2
            }
        }
        
        # Auto-detect type from search text if not explicitly specified
        if highlight_type == "issue" and search_text:
            if "image" in search_text.lower():
                highlight_type = "manual_image"
            elif "table" in search_text.lower():
                highlight_type = "manual_table"
            elif "diagram" in search_text.lower():
                highlight_type = "manual_diagram"
        
        return color_schemes.get(highlight_type, color_schemes['issue'])
    
    def _clear_highlights(self):
        """Clear all highlights from the current page."""
        try:
            if hasattr(self, 'current_highlights'):
                self.current_highlights.clear()
            # Clear highlight bbox and multiline highlight data
            self.highlight_bbox = None
            self.current_multiline_highlight = None
            self.highlight_search_text = None
            self.highlight_type = None
            self._display_current_page()
            self.logger.info("Cleared all highlights")
        except Exception as e:
            self.logger.error(f"Error clearing highlights: {e}")
    
    def closeEvent(self, event):
        """Handle widget close event."""
        if self.current_document:
            self.current_document.close()
        super().closeEvent(event)
    
    def highlight_area(self, page_number, bbox, search_text=None, highlight_type="issue"):
        """Highlight a specific area on a specific page using the new advanced highlighting system."""
        try:
            if not self.current_document:
                self.logger.warning("No document loaded for highlighting")
                return
            
            # Debug logging
            self.logger.info(f"PDF Viewer highlight_area called: page={page_number}, bbox={bbox}, type={highlight_type}")
            
            # Handle clear highlighting - clear all highlights and just navigate to page
            if highlight_type == "clear" or (isinstance(bbox, list) and len(bbox) == 0):
                self._go_to_page(page_number)
                self.highlighting_engine.clear_highlights()
                return
            
            # Navigate to the page first
            self._go_to_page(page_number)
            
            # Use the new highlighting engine
            self.highlighting_engine.highlight_area(
                page_number=page_number,
                bbox=bbox,
                search_text=search_text,
                highlight_type=highlight_type
            )
            
            # Update the display
            self._display_current_page()
            
        except Exception as e:
            self.logger.error(f"Error highlighting area: {e}")
            import traceback
            traceback.print_exc()
    
    def _find_precise_text_location(self, page_number, search_text):
        """Find the precise bounding box of specific text on a page."""
        try:
            if not self.current_document or not search_text:
                return None
            
            page = self.current_document[page_number - 1]  # 0-indexed
            
            # Clean up search text - remove OCR error wrapper if present
            if "Potential OCR error: '" in search_text:
                clean_search_text = search_text.split("Potential OCR error: '")[1].split("'")[0]
            else:
                clean_search_text = search_text
            
            # Multiple search strategies for precise text location
            search_strategies = [
                clean_search_text,
                search_text,
                # Try single characters for very precise highlighting
                clean_search_text[:1] if clean_search_text else '',
                # Try without special characters
                clean_search_text.replace('/', '').replace('\\', '').replace('°', '') if clean_search_text else '',
                # Try similar-looking characters
                clean_search_text.replace('O', '0').replace('0', 'O').replace('I', '1').replace('1', 'I') if clean_search_text else ''
            ]
            
            for strategy_text in search_strategies:
                if not strategy_text:
                    continue
                    
                # Search for text instances on the page
                text_instances = page.search_for(strategy_text)
                
                if text_instances:
                    # Use the first instance for highlighting
                    rect = text_instances[0]
                    precise_bbox = [rect.x0, rect.y0, rect.x1, rect.y1]
                    
                    self.logger.info(f"Found precise text '{strategy_text}' at bbox: {precise_bbox}")
                    return precise_bbox
            
            # If no exact text found, try character-by-character search
            return self._character_level_search(page, clean_search_text)
            
        except Exception as e:
            self.logger.error(f"Error finding precise text location: {e}")
            return None
    
    def _character_level_search(self, page, search_text):
        """Perform character-level search for very precise highlighting."""
        try:
            if not search_text:
                return None
            
            # Try each character in the search text
            for char in search_text:
                if char.strip():  # Skip whitespace
                    char_instances = page.search_for(char)
                    if char_instances:
                        # Use the first character instance
                        rect = char_instances[0]
                        char_bbox = [rect.x0, rect.y0, rect.x1, rect.y1]
                        
                        self.logger.info(f"Found character '{char}' at bbox: {char_bbox}")
                        return char_bbox
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in character-level search: {e}")
            return None
    
    def clear_highlight(self):
        """Clear any current highlighting using the new system."""
        # Clear using new highlighting engine
        self.highlighting_engine.clear_highlights()
        
        # Clear legacy highlighting state
        self.highlight_bbox = None
        self.highlight_search_text = None
        self.current_multiline_highlight = None
        
        # Re-render without highlighting
        self._display_current_page()
    
    def _add_highlight_to_pixmap(self, qpixmap: QPixmap, zoom_factor: float) -> QPixmap:
        """Add highlighting overlay to the pixmap using the new highlighting system."""
        try:
            # Use the new highlighting engine
            if self.highlighting_engine.has_highlights():
                self.logger.info(f"PDF_VIEWER: Applying highlights to pixmap (page={self.current_page + 1}, zoom={zoom_factor})")
                return self.highlighting_engine.apply_highlights_to_pixmap(qpixmap, zoom_factor)
            else:
                self.logger.debug(f"PDF_VIEWER: No highlights to apply (page={self.current_page + 1})")
            
            # Legacy fallback - use old system if still needed
            if self.current_multiline_highlight:
                return draw_multiline_highlight(qpixmap, self.current_multiline_highlight, zoom_factor)
            
            # Original single-rectangle highlighting as final fallback
            painter = QPainter(qpixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Set up highlight pen and brush with better visibility
            pen = QPen(QColor(255, 0, 0), 3)  # Thicker red border
            brush = QBrush(QColor(255, 255, 0, 80))  # More transparent yellow highlight
            painter.setPen(pen)
            painter.setBrush(brush)
            
            # Convert bbox coordinates to pixmap coordinates
            if isinstance(self.highlight_bbox, (list, tuple)) and len(self.highlight_bbox) >= 4:
                x0, y0, x1, y1 = self.highlight_bbox[:4]
                
                # Validate coordinates
                if not all(isinstance(coord, (int, float)) for coord in [x0, y0, x1, y1]):
                    self.logger.warning(f"Invalid bbox coordinates: {self.highlight_bbox}")
                    painter.end()
                    return qpixmap
                
                # Get current page for coordinate conversion
                if self.current_document:
                    page = self.current_document[self.current_page]
                    page_rect = page.rect
                    
                    # Ensure bbox coordinates are within page bounds
                    x0 = max(0, min(page_rect.width, x0))
                    y0 = max(0, min(page_rect.height, y0))
                    x1 = max(0, min(page_rect.width, x1))
                    y1 = max(0, min(page_rect.height, y1))
                    
                    # Convert coordinates to pixmap coordinates
                    # TESTING: No Y-axis flipping - extraction coordinates may already be in screen system
                    pixmap_x0 = x0 * zoom_factor
                    pixmap_y0 = y0 * zoom_factor  # Direct Y coordinate
                    pixmap_x1 = x1 * zoom_factor
                    pixmap_y1 = y1 * zoom_factor  # Direct Y coordinate
                    
                    # Debug coordinate conversion
                    self.logger.info(f"Converting coordinates: PDF({x0},{y0},{x1},{y1}) -> Pixmap({pixmap_x0},{pixmap_y0},{pixmap_x1},{pixmap_y1})")
                    
                    # Ensure coordinates are within pixmap bounds
                    pixmap_x0 = max(0, min(qpixmap.width(), pixmap_x0))
                    pixmap_y0 = max(0, min(qpixmap.height(), pixmap_y0))
                    pixmap_x1 = max(0, min(qpixmap.width(), pixmap_x1))
                    pixmap_y1 = max(0, min(qpixmap.height(), pixmap_y1))
                    
                    # Ensure coordinates are in correct order for drawing
                    # Top-left and bottom-right corners
                    rect_x = min(pixmap_x0, pixmap_x1)
                    rect_y = min(pixmap_y0, pixmap_y1)
                    rect_width = abs(pixmap_x1 - pixmap_x0)
                    rect_height = abs(pixmap_y1 - pixmap_y0)
                    
                    # Ensure minimum size for visibility
                    min_size = 10
                    if rect_width < min_size:
                        center_x = rect_x + rect_width / 2
                        rect_x = center_x - min_size / 2
                        rect_width = min_size
                    
                    if rect_height < min_size:
                        center_y = rect_y + rect_height / 2
                        rect_y = center_y - min_size / 2
                        rect_height = min_size
                    
                    # Draw highlight rectangle with corrected positioning
                    if rect_width > 2 and rect_height > 2:  # Only draw if rectangle is visible
                        painter.drawRect(int(rect_x), int(rect_y), int(rect_width), int(rect_height))
                        self.logger.info(f"Drew highlight at ({rect_x:.1f}, {rect_y:.1f}) size ({rect_width:.1f}, {rect_height:.1f})")
                        
                        # Also draw an outline for better visibility
                        outline_pen = QPen(QColor(0, 0, 0), 1)  # Black outline
                        painter.setPen(outline_pen)
                        painter.setBrush(QBrush())  # No fill
                        painter.drawRect(int(rect_x - 1), int(rect_y - 1), int(rect_width + 2), int(rect_height + 2))
                else:
                    # Fallback to simple scaling without coordinate conversion
                    x0 *= zoom_factor
                    y0 *= zoom_factor  
                    x1 *= zoom_factor
                    y1 *= zoom_factor
                    
                    rect_width = abs(x1 - x0)
                    rect_height = abs(y1 - y0)
                    
                    if rect_width > 2 and rect_height > 2:
                        painter.drawRect(int(x0), int(y0), int(rect_width), int(rect_height))
                        self.logger.info(f"Drew fallback highlight at ({x0:.1f}, {y0:.1f}) size ({rect_width:.1f}, {rect_height:.1f})")
            
            painter.end()
            return qpixmap
            
        except Exception as e:
            self.logger.error(f"Failed to add highlight to pixmap: {str(e)}")
            painter.end()
            return qpixmap
    
    def _render_page(self):
        """Public method to re-render the current page (for external access)."""
        self._display_current_page()
    
    def highlight_selection(self, page_number: int, bbox):
        """Highlight a text selection in the PDF viewer."""
        try:
            # Use the existing highlight_area method with a different style
            self.highlight_area(page_number, bbox, "text_selection")
            self.logger.info(f"Highlighted text selection on page {page_number}: {bbox}")
        except Exception as e:
            self.logger.error(f"Failed to highlight selection: {str(e)}")
    
    def show_cursor_location(self, page_number: int, bbox):
        """Show cursor location indicator in PDF viewer."""
        try:
            # For now, use a small highlight to show cursor location
            if bbox and len(bbox) >= 4:
                # Create a small cursor indicator
                cursor_bbox = [bbox[0], bbox[1], bbox[0] + 2, bbox[3]]  # Thin vertical line
                self.highlight_area(page_number, cursor_bbox, "cursor")
                self.logger.info(f"Showed cursor location on page {page_number}: {cursor_bbox}")
        except Exception as e:
            self.logger.error(f"Failed to show cursor location: {str(e)}")
    
    def load_document_by_id(self, document_id: str, metadata: dict):
        """Load document by ID and metadata (for document state manager)."""
        try:
            file_path = metadata.get('file_path')
            if not file_path:
                self.logger.warning(f"No file path in metadata for document {document_id}")
                return
                
            if not Path(file_path).exists():
                self.logger.warning(f"Document file not found: {file_path}")
                return
            
            # Check if already loaded
            if (hasattr(self, 'current_document_path') and 
                self.current_document_path == file_path):
                self.logger.info(f"Document {document_id} already loaded in PDF viewer")
                return
            
            self.logger.info(f"Loading document in PDF viewer: {document_id}")
            
            # Store document info
            self.current_document_id = document_id
            self.current_document_metadata = metadata
            
            # Load the document
            self.load_document(file_path)
            
        except Exception as e:
            self.logger.error(f"Error loading document by ID in PDF viewer: {e}")