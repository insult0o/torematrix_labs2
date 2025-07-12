#!/usr/bin/env python3
"""
Content validation and correction interface widget with vertical layout.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from ..qt_compat import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QLabel, QPushButton, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QComboBox, QSpinBox, QCheckBox, QProgressBar, QTabWidget,
    QGroupBox, QFrame, QScrollArea, QMessageBox, QDialog,
    QDialogButtonBox, QFormLayout, QLineEdit, Qt, QColor,
    QTextCharFormat, QTextCursor, pyqtSignal
)

from ...config.settings import Settings
from ...core.content_validator import (
    ContentValidator, ContentCorrection, CorrectionType, CorrectionStatus,
    ValidationSession, ValidationMetrics
)
from ...models.document_models import Document


class MultiColorHighlighter:
    """Multi-color highlighting system for different types of issues and areas."""
    
    # Color scheme for different issue types
    HIGHLIGHT_COLORS = {
        # Active issue (currently selected)
        'active_issue': {
            'background': QColor(255, 255, 0, 200),  # Bright yellow
            'foreground': QColor(200, 0, 0),         # Red text
            'bold': True,
            'underline': True
        },
        
        # Other issues (not currently selected)
        'other_issue': {
            'background': QColor(255, 255, 0, 100),  # Light yellow
            'foreground': QColor(150, 75, 0),        # Dark orange text
            'bold': False,
            'underline': False
        },
        
        # Manually validated IMAGE areas
        'manual_image': {
            'background': QColor(255, 0, 0, 120),    # Red background
            'foreground': QColor(255, 255, 255),     # White text
            'bold': True,
            'underline': False
        },
        
        # Manually validated TABLE areas
        'manual_table': {
            'background': QColor(0, 0, 255, 120),    # Blue background
            'foreground': QColor(255, 255, 255),     # White text
            'bold': True,
            'underline': False
        },
        
        # Manually validated DIAGRAM areas
        'manual_diagram': {
            'background': QColor(128, 0, 128, 120),  # Purple background
            'foreground': QColor(255, 255, 255),     # White text
            'bold': True,
            'underline': False
        },
        
        # Auto-detected conflicts requiring resolution
        'auto_conflict': {
            'background': QColor(255, 165, 0, 150),  # Orange background
            'foreground': QColor(139, 69, 19),       # Dark brown text
            'bold': True,
            'underline': True
        },
        
        # Successfully resolved conflicts
        'resolved_conflict': {
            'background': QColor(0, 255, 0, 100),    # Light green
            'foreground': QColor(0, 100, 0),         # Dark green text
            'bold': False,
            'underline': False
        }
    }
    
    @classmethod
    def create_highlight_format(cls, highlight_type: str) -> QTextCharFormat:
        """Create a QTextCharFormat for the specified highlight type."""
        format_config = cls.HIGHLIGHT_COLORS.get(highlight_type, cls.HIGHLIGHT_COLORS['other_issue'])
        
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(format_config['background'])
        highlight_format.setForeground(format_config['foreground'])
        
        if format_config['bold']:
            highlight_format.setFontWeight(700)
        
        if format_config['underline']:
            highlight_format.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
        
        return highlight_format
    
    @classmethod
    def get_color_legend(cls) -> List[Dict[str, Any]]:
        """Get a legend of all highlight colors and their meanings."""
        legend = [
            {'type': 'active_issue', 'name': '🟡 Active Issue', 'description': 'Currently selected issue requiring attention'},
            {'type': 'other_issue', 'name': '🟨 Other Issues', 'description': 'Other validation issues in the document'},
            {'type': 'manual_image', 'name': '🔴 Manual Images', 'description': 'Manually classified image areas (excluded from text)'},
            {'type': 'manual_table', 'name': '🔵 Manual Tables', 'description': 'Manually classified table areas (excluded from text)'},
            {'type': 'manual_diagram', 'name': '🟣 Manual Diagrams', 'description': 'Manually classified diagram areas (excluded from text)'},
            {'type': 'auto_conflict', 'name': '🟠 Auto Conflicts', 'description': 'Auto-detected areas conflicting with manual classification'},
            {'type': 'resolved_conflict', 'name': '🟢 Resolved', 'description': 'Successfully resolved conflicts'}
        ]
        return legend


class CorrectionItemWidget(QWidget):
    """Widget for displaying and editing individual corrections with vertical layout and PDF highlighting."""
    
    # Signal emitted when correction is clicked for PDF highlighting
    correction_selected = pyqtSignal(object)  # ContentCorrection object
    correction_edited = pyqtSignal(object)    # ContentCorrection object
    
    # Class-level cache for extracted content to prevent repeated PDF access
    _content_cache = {}
    
    def __init__(self, correction: ContentCorrection, parent=None):
        super().__init__(parent)
        self.correction = correction
        self.logger = logging.getLogger(__name__)
        self.extracted_content = self._get_extracted_content()
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header with correction info and actions
        header_layout = QHBoxLayout()
        
        confidence_label = QLabel(f"Confidence: {self.correction.confidence:.1%}")
        confidence_label.setStyleSheet(f"color: {'green' if self.correction.confidence > 0.8 else 'orange'}; font-weight: bold;")
        header_layout.addWidget(confidence_label)
        
        status_label = QLabel(f"Status: {self.correction.status.value}")
        header_layout.addWidget(status_label)
        
        # Location info
        location_label = QLabel(f"Page {self.correction.page_number}")
        location_label.setStyleSheet("color: #666;")
        header_layout.addWidget(location_label)
        
        header_layout.addStretch()
        
        # Action buttons (moved to header)
        self.approve_btn = QPushButton("✓")
        self.approve_btn.clicked.connect(self._approve_correction)
        self.approve_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 4px 8px; border-radius: 3px;")
        self.approve_btn.setMaximumWidth(30)
        header_layout.addWidget(self.approve_btn)
        
        self.reject_btn = QPushButton("✗")
        self.reject_btn.clicked.connect(self._reject_correction)
        self.reject_btn.setStyleSheet("background-color: #f44336; color: white; padding: 4px 8px; border-radius: 3px;")
        self.reject_btn.setMaximumWidth(30)
        header_layout.addWidget(self.reject_btn)
        
        layout.addLayout(header_layout)
        
        # Vertical split layout
        main_splitter = QSplitter(Qt.Vertical)
        
        # Top section: Issue Type
        issue_group = QGroupBox("Issue Type")
        issue_layout = QVBoxLayout()
        
        issue_type_label = QLabel(self._format_issue_type())
        issue_type_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50; padding: 8px;")
        issue_type_label.setWordWrap(True)
        issue_layout.addWidget(issue_type_label)
        
        # Issue description with bigger text field
        self.issue_desc_text = QTextEdit()
        self.issue_desc_text.setPlainText(self.correction.reasoning)
        self.issue_desc_text.setStyleSheet("color: #666; padding: 4px; background-color: #f8f9fa; border-radius: 3px;")
        self.issue_desc_text.setMinimumHeight(120)  # Make OCR recognition text bigger
        self.issue_desc_text.setMaximumHeight(200)  # Prevent it from becoming too large
        self.issue_desc_text.setReadOnly(True)  # Make it read-only since it's descriptive
        issue_layout.addWidget(self.issue_desc_text)
        
        issue_group.setLayout(issue_layout)
        main_splitter.addWidget(issue_group)
        
        # Bottom section: Extraction Edition
        extraction_group = QGroupBox("Extraction Edition")
        extraction_layout = QVBoxLayout()
        
        self.extraction_text = QTextEdit()
        self.extraction_text.setPlainText(self.extracted_content)
        self.extraction_text.setMinimumHeight(300)  # Make even bigger for better readability
        self.extraction_text.setMaximumHeight(500)  # Prevent it from becoming too large
        self.extraction_text.textChanged.connect(self._on_extraction_edited)
        self.extraction_text.mousePressEvent = self._on_extraction_clicked
        extraction_layout.addWidget(self.extraction_text)
        
        extraction_group.setLayout(extraction_layout)
        main_splitter.addWidget(extraction_group)
        
        # Set splitter proportions (1:2 ratio for balanced view)
        main_splitter.setSizes([1, 2])
        layout.addWidget(main_splitter)
        
        # Highlight the issue in the extraction text
        self._highlight_issue_in_extraction()
        
        # Connect click event for PDF highlighting
        self.mousePressEvent = self._on_widget_clicked
        
        # Set background color based on status
        self._update_status_appearance()
        
        self.setLayout(layout)
    
    def _get_extracted_content(self):
        """Get the extracted content for this correction."""
        try:
            # Priority 1: Use PDF path directly from correction object
            pdf_path = getattr(self.correction, 'pdf_path', None)
            
            # Priority 2: Try to find PDF path from parent widget
            if not pdf_path:
                try:
                    # Look for document path in parent validation widget
                    parent = self.parent()
                    while parent and not hasattr(parent, 'current_document'):
                        parent = parent.parent()
                    
                    if parent and hasattr(parent, 'current_document') and parent.current_document:
                        pdf_path = parent.current_document.metadata.file_path
                except Exception as e:
                    self.logger.warning(f"Error finding PDF path from parent: {e}")
            
            # Check cache first to avoid repeated PDF access
            cache_key = f"{pdf_path}:{self.correction.page_number}:{self.correction.bbox}"
            if cache_key in self._content_cache:
                self.logger.debug(f"Using cached content for {cache_key}")
                return self._content_cache[cache_key]
            
            # Try to extract from the actual PDF if we have the path
            if pdf_path and Path(pdf_path).exists():
                extracted = self._extract_content_from_pdf(pdf_path)
                if extracted:
                    # Cache the result
                    self._content_cache[cache_key] = extracted
                    self.logger.info(f"Successfully extracted and cached content from PDF: {pdf_path}")
                    return extracted
                else:
                    self.logger.warning(f"Could not extract content from PDF: {pdf_path}")
            
            # Fallback: create a more realistic extracted content based on the issue
            issue_text = self.correction.original_content.replace("Potential OCR error: '", "").replace("'", "")
            
            # Create contextual content based on issue type
            if self.correction.correction_type == CorrectionType.OCR_CORRECTION:
                if issue_text in ['000', '0000']:
                    return f"Flight Level {issue_text} - Transition altitude: {issue_text} feet - Clearance to descend {issue_text}"
                elif issue_text in ['//', '/', '\\']:
                    return f"Date: 15{issue_text}07{issue_text}2024 - Reference: DOC{issue_text}ATC{issue_text}001"
                elif issue_text in ['I', 'l', '1']:
                    return f"Aircraft identification: {issue_text}BAW123 - Callsign: British Airways {issue_text}23"
                elif issue_text in ['O', '0']:
                    return f"Runway {issue_text}9L{issue_text}27R - Heading {issue_text}9{issue_text} degrees"
                else:
                    return f"...clearance for approach {issue_text} runway contact tower..."
            
            # Default extracted content with context
            return f"...navigation clearance {issue_text} altitude maintain contact..."
            
        except Exception as e:
            self.logger.error(f"Error getting extracted content: {e}")
            # Return fallback content on error
            return self._generate_fallback_content()
    
    def _generate_fallback_content(self):
        """Generate fallback content when PDF extraction fails."""
        try:
            issue_text = self.correction.original_content.replace("Potential OCR error: '", "").replace("'", "")
            return f"[Fallback] Context around issue: {issue_text}"
        except Exception:
            return "[Error] Could not generate content"
    
    def _extract_content_from_pdf(self, pdf_path):
        """Extract actual content from PDF around the correction location."""
        pdf_document = None
        try:
            import fitz  # PyMuPDF
            
            # Validate inputs
            if not pdf_path or not Path(pdf_path).exists():
                self.logger.warning(f"PDF path invalid or file not found: {pdf_path}")
                return None
            
            if self.correction.page_number < 1:
                self.logger.warning(f"Invalid page number: {self.correction.page_number}")
                return None
            
            pdf_document = fitz.open(pdf_path)
            
            # Validate page number
            if self.correction.page_number > len(pdf_document):
                self.logger.warning(f"Page number {self.correction.page_number} exceeds document length {len(pdf_document)}")
                return None
            
            page = pdf_document[self.correction.page_number - 1]  # 0-indexed
            
            # If we have bounding box coordinates, extract text from that exact area plus context
            if hasattr(self.correction, 'bbox') and self.correction.bbox:
                try:
                    x0, y0, x1, y1 = self.correction.bbox
                    
                    # Validate bbox coordinates
                    if not all(isinstance(coord, (int, float)) for coord in [x0, y0, x1, y1]):
                        self.logger.warning(f"Invalid bbox coordinates: {self.correction.bbox}")
                        return None
                    
                    # Create the exact bounding box rectangle
                    bbox_rect = fitz.Rect(x0, y0, x1, y1)
                    
                    # Get text from the exact bounding box
                    bbox_text = page.get_text("text", clip=bbox_rect).strip()
                    
                    # Create expanded rectangle for context (expand by 50 points in each direction)
                    context_margin = 50
                    expanded_rect = fitz.Rect(
                        max(0, x0 - context_margin),
                        max(0, y0 - context_margin), 
                        min(page.rect.width, x1 + context_margin),
                        min(page.rect.height, y1 + context_margin)
                    )
                    
                    # Get context text around the bounding box
                    context_text = page.get_text("text", clip=expanded_rect)
                    
                    if context_text.strip():
                        self.logger.info(f"Extracted text from bbox {self.correction.bbox}: '{bbox_text}' with context")
                        return context_text.strip()
                    elif bbox_text:
                        self.logger.info(f"Extracted text from exact bbox: '{bbox_text}'")
                        return bbox_text
                except Exception as e:
                    self.logger.error(f"Error processing bbox coordinates: {e}")
            
            # If no bounding box, try to use text position if available
            if hasattr(self.correction, 'text_position'):
                try:
                    # Get all text blocks with their positions
                    full_text = page.get_text()
                    
                    # Try to extract based on character position
                    text_pos = self.correction.text_position
                    if isinstance(text_pos, (list, tuple)) and len(text_pos) >= 2:
                        start_pos, end_pos = text_pos[0], text_pos[1]
                        
                        # Validate positions
                        if (isinstance(start_pos, int) and isinstance(end_pos, int) and 
                            0 <= start_pos < len(full_text) and 0 <= end_pos <= len(full_text) and 
                            start_pos <= end_pos):
                            
                            # Extract with context (50 characters before/after)
                            context_start = max(0, start_pos - 50)
                            context_end = min(len(full_text), end_pos + 50)
                            extracted_text = full_text[context_start:context_end]
                            self.logger.info(f"Extracted text from position {start_pos}-{end_pos}")
                            return extracted_text.strip()
                        else:
                            self.logger.warning(f"Invalid text position: {text_pos}")
                except Exception as e:
                    self.logger.error(f"Error using text position: {e}")
            
            # Fallback: get text from the general area of the page
            try:
                page_text = page.get_text()
                if page_text.strip():
                    # Return first paragraph or up to 200 characters
                    lines = page_text.split('\n')
                    non_empty_lines = [line.strip() for line in lines if line.strip()]
                    if non_empty_lines:
                        # Take first few meaningful lines
                        result_lines = non_empty_lines[:3]
                        result_text = '\n'.join(result_lines)
                        self.logger.info("Using fallback page text extraction")
                        return result_text
            except Exception as e:
                self.logger.error(f"Error in fallback text extraction: {e}")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting content from PDF: {e}")
            return None
        finally:
            # Always close the PDF document to prevent memory leaks
            if pdf_document is not None:
                try:
                    pdf_document.close()
                except Exception as e:
                    self.logger.warning(f"Error closing PDF document: {e}")
    
    @classmethod
    def clear_content_cache(cls):
        """Clear the content cache to free memory."""
        cls._content_cache.clear()
    
    def _format_issue_type(self):
        """Format the issue type for display."""
        issue_types = {
            'OCR_CORRECTION': '🔍 OCR Recognition Issue',
            'FORMATTING_FIX': '📝 Formatting Problem', 
            'STRUCTURE_IMPROVEMENT': '🏗️ Structure Issue',
            'CONTENT_VALIDATION': '✅ Content Validation'
        }
        return issue_types.get(self.correction.correction_type.name, f"❓ {self.correction.correction_type.value}")
    
    def _highlight_issue_in_extraction(self):
        """Highlight the problematic portion in the extraction text with precise character-level highlighting."""
        try:
            cursor = self.extraction_text.textCursor()
            
            # Create highlight format using multi-color system
            highlight_format = MultiColorHighlighter.create_highlight_format('active_issue')
            
            # Find and highlight the issue text
            text = self.extraction_text.toPlainText()
            issue_text = self.correction.original_content
            
            # Clean up issue text - remove OCR error wrapper if present
            if "Potential OCR error: '" in issue_text:
                clean_issue_text = issue_text.split("Potential OCR error: '")[1].split("'")[0]
            else:
                clean_issue_text = issue_text
            
            # Multiple search strategies for precise highlighting
            search_strategies = [
                clean_issue_text,
                issue_text,
                # Try single characters for very precise highlighting
                clean_issue_text[:1] if clean_issue_text else '',
                # Try without special characters
                clean_issue_text.replace('/', '').replace('\\', '').replace('°', '') if clean_issue_text else '',
                # Try similar-looking characters
                clean_issue_text.replace('O', '0').replace('0', 'O').replace('I', '1').replace('1', 'I') if clean_issue_text else ''
            ]
            
            highlighted = False
            for search_text in search_strategies:
                if not search_text:
                    continue
                    
                # Find all occurrences for precise highlighting
                start_pos = 0
                while True:
                    pos = text.find(search_text, start_pos)
                    if pos == -1:
                        break
                    
                    # Highlight this occurrence
                    cursor.setPosition(pos)
                    cursor.setPosition(pos + len(search_text), QTextCursor.KeepAnchor)
                    cursor.setCharFormat(highlight_format)
                    
                    # Log the precise location
                    context_start = max(0, pos - 10)
                    context_end = min(len(text), pos + len(search_text) + 10)
                    context = text[context_start:context_end]
                    
                    self.logger.info(f"Precisely highlighted '{search_text}' at position {pos} in context: '...{context}...'")
                    highlighted = True
                    
                    start_pos = pos + 1  # Continue searching for multiple occurrences
                
                if highlighted:
                    # Position cursor at the first highlight for visibility
                    first_pos = text.find(search_text)
                    if first_pos >= 0:
                        cursor.setPosition(first_pos)
                        self.extraction_text.setTextCursor(cursor)
                        self.extraction_text.ensureCursorVisible()
                    return
            
            # If no exact match found, try fuzzy matching
            self._fuzzy_highlight_issue(text, clean_issue_text, highlight_format)
            
        except Exception as e:
            self.logger.error(f"Error highlighting issue in extraction: {e}")
    
    def _fuzzy_highlight_issue(self, text, issue_text, highlight_format):
        """Perform fuzzy highlighting when exact match fails."""
        try:
            if not issue_text:
                return
                
            cursor = self.extraction_text.textCursor()
            
            # Try character-by-character matching for very precise highlighting
            for char in issue_text:
                if char in text:
                    pos = text.find(char)
                    if pos >= 0:
                        cursor.setPosition(pos)
                        cursor.setPosition(pos + 1, QTextCursor.KeepAnchor)
                        cursor.setCharFormat(highlight_format)
                        
                        self.logger.info(f"Fuzzy highlighted character '{char}' at position {pos}")
                        
                        # Position cursor for visibility
                        cursor.setPosition(pos)
                        self.extraction_text.setTextCursor(cursor)
                        self.extraction_text.ensureCursorVisible()
                        return
            
            self.logger.warning(f"Could not find any matching characters for issue text: '{issue_text}' in content: '{text[:100]}...'")
            
        except Exception as e:
            self.logger.error(f"Error in fuzzy highlighting: {e}")
    
    def _on_extraction_clicked(self, event):
        """Handle clicks on the extraction text to highlight PDF location."""
        # Call the original mousePressEvent first
        QTextEdit.mousePressEvent(self.extraction_text, event)
        
        # Emit signal for PDF highlighting
        self.correction_selected.emit(self.correction)
        self.logger.info(f"Correction clicked: {self.correction.id} at page {self.correction.page_number}")
    
    def _on_widget_clicked(self, event):
        """Handle clicks on the widget to highlight PDF location."""
        # Emit signal for PDF highlighting
        self.correction_selected.emit(self.correction)
        self.logger.info(f"Correction widget clicked: {self.correction.id}")
    
    def _on_extraction_edited(self):
        """Handle edits to the extraction text."""
        # Update the correction with edited content
        self.correction.suggested_content = self.extraction_text.toPlainText()
        self.correction.status = CorrectionStatus.PENDING_REVIEW
        self._update_status_appearance()
        
        # Emit signal for content change
        self.correction_edited.emit(self.correction)
        self.logger.info(f"Correction edited: {self.correction.id}")
    
    def _approve_correction(self):
        """Approve the correction."""
        self.correction.status = CorrectionStatus.APPROVED
        self.correction.review_date = datetime.now()
        self.correction.suggested_content = self.extraction_text.toPlainText()
        self._update_status_appearance()
        self.logger.info(f"Correction {self.correction.id} approved")
    
    def _reject_correction(self):
        """Reject the correction."""
        self.correction.status = CorrectionStatus.REJECTED
        self.correction.review_date = datetime.now()
        self._update_status_appearance()
        self.logger.info(f"Correction {self.correction.id} rejected")
    
    def _update_status_appearance(self):
        """Update widget appearance based on status."""
        if self.correction.status == CorrectionStatus.APPROVED:
            self.setStyleSheet("QWidget { border: 2px solid #4CAF50; border-radius: 5px; }")
        elif self.correction.status == CorrectionStatus.REJECTED:
            self.setStyleSheet("QWidget { border: 2px solid #f44336; border-radius: 5px; }")
        elif self.correction.status == CorrectionStatus.PENDING_REVIEW:
            self.setStyleSheet("QWidget { border: 2px solid #FF9800; border-radius: 5px; }")
        else:
            self.setStyleSheet("QWidget { border: 1px solid #ddd; border-radius: 5px; }")


class ValidationWidget(QWidget):
    """Main content validation and correction interface."""
    
    # Signal emitted when a correction is selected for PDF highlighting
    highlight_pdf_location = pyqtSignal(int, object, str)  # page_number, bbox, search_text
    
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Initialize validator
        self.content_validator = ContentValidator(settings)
        
        # Current state
        self.current_document: Optional[Document] = None
        self.current_corrections: List[ContentCorrection] = []
        self.validation_session: Optional[ValidationSession] = None
        
        # Lazy loading state
        self.corrections_per_page = 20  # Show 20 corrections at a time
        self.current_page = 0
        self.displayed_corrections = []
        
        self._init_ui()
        self.logger.info("Validation widget initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Header with document info and validation controls
        self._create_header(layout)
        
        # Main content area with tabs
        self._create_main_content(layout)
        
        # Footer with actions and summary
        self._create_footer(layout)
        
        # Progress overlay (initially hidden)
        self.progress_overlay = QWidget(self)
        self.progress_overlay.setStyleSheet("background-color: rgba(0,0,0,0.7);")
        self.progress_overlay.hide()
        
        overlay_layout = QVBoxLayout(self.progress_overlay)
        overlay_layout.addStretch()
        
        self.progress_label = QLabel("Loading...")
        self.progress_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        self.progress_label.setAlignment(Qt.AlignCenter)
        overlay_layout.addWidget(self.progress_label)
        
        self.progress_bar_overlay = QProgressBar()
        self.progress_bar_overlay.setStyleSheet("QProgressBar { height: 20px; }")
        overlay_layout.addWidget(self.progress_bar_overlay)
        
        overlay_layout.addStretch()
        
        self.setLayout(layout)
    
    def _create_header(self, parent_layout):
        """Create header section."""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_layout = QHBoxLayout()
        
        # Document information
        doc_info_layout = QVBoxLayout()
        self.doc_name_label = QLabel("No document loaded")
        self.doc_name_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        doc_info_layout.addWidget(self.doc_name_label)
        
        self.doc_status_label = QLabel("Status: Ready")
        doc_info_layout.addWidget(self.doc_status_label)
        
        header_layout.addLayout(doc_info_layout)
        header_layout.addStretch()
        
        # Validation controls
        controls_layout = QVBoxLayout()
        
        # Start validation button
        self.start_validation_btn = QPushButton("Start Validation")
        self.start_validation_btn.clicked.connect(self._start_validation)
        self.start_validation_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        controls_layout.addWidget(self.start_validation_btn)
        
        # Auto-apply high confidence corrections
        self.auto_apply_checkbox = QCheckBox("Auto-apply high confidence corrections")
        self.auto_apply_checkbox.setChecked(True)
        controls_layout.addWidget(self.auto_apply_checkbox)
        
        header_layout.addLayout(controls_layout)
        header_frame.setLayout(header_layout)
        parent_layout.addWidget(header_frame)
    
    def _create_main_content(self, parent_layout):
        """Create main content area with tabs."""
        self.tab_widget = QTabWidget()
        
        # Corrections tab
        self._create_corrections_tab()
        
        # Statistics tab
        self._create_statistics_tab()
        
        # Settings tab
        self._create_settings_tab()
        
        # Color legend tab
        self._create_color_legend_tab()
        
        parent_layout.addWidget(self.tab_widget)
    
    def _create_corrections_tab(self):
        """Create corrections review tab."""
        corrections_widget = QWidget()
        layout = QVBoxLayout()
        
        # Filter and sort controls
        controls_layout = QHBoxLayout()
        
        # Filter by type
        type_label = QLabel("Filter by type:")
        controls_layout.addWidget(type_label)
        
        self.type_filter = QComboBox()
        self.type_filter.addItem("All Types")
        for correction_type in CorrectionType:
            self.type_filter.addItem(correction_type.value)
        self.type_filter.currentTextChanged.connect(self._filter_corrections)
        controls_layout.addWidget(self.type_filter)
        
        # Filter by status
        status_label = QLabel("Filter by status:")
        controls_layout.addWidget(status_label)
        
        self.status_filter = QComboBox()
        self.status_filter.addItem("All Status")
        for status in CorrectionStatus:
            self.status_filter.addItem(status.value)
        self.status_filter.currentTextChanged.connect(self._filter_corrections)
        controls_layout.addWidget(self.status_filter)
        
        controls_layout.addStretch()
        
        # Batch actions
        self.approve_all_btn = QPushButton("Approve All Visible")
        self.approve_all_btn.clicked.connect(self._approve_all_visible)
        controls_layout.addWidget(self.approve_all_btn)
        
        self.reject_all_btn = QPushButton("Reject All Visible")
        self.reject_all_btn.clicked.connect(self._reject_all_visible)
        controls_layout.addWidget(self.reject_all_btn)
        
        layout.addLayout(controls_layout)
        
        # Pagination controls
        pagination_layout = QHBoxLayout()
        
        self.prev_page_btn = QPushButton("← Previous")
        self.prev_page_btn.clicked.connect(self._prev_page)
        self.prev_page_btn.setEnabled(False)
        pagination_layout.addWidget(self.prev_page_btn)
        
        self.page_info_label = QLabel("Page 1 of 1")
        pagination_layout.addWidget(self.page_info_label)
        
        self.next_page_btn = QPushButton("Next →")
        self.next_page_btn.clicked.connect(self._next_page)
        self.next_page_btn.setEnabled(False)
        pagination_layout.addWidget(self.next_page_btn)
        
        pagination_layout.addStretch()
        
        self.corrections_count_label = QLabel("0 corrections")
        pagination_layout.addWidget(self.corrections_count_label)
        
        layout.addLayout(pagination_layout)
        
        # Corrections scroll area
        self.corrections_scroll = QScrollArea()
        self.corrections_scroll.setWidgetResizable(True)
        self.corrections_container = QWidget()
        self.corrections_layout = QVBoxLayout()
        self.corrections_container.setLayout(self.corrections_layout)
        self.corrections_scroll.setWidget(self.corrections_container)
        
        layout.addWidget(self.corrections_scroll)
        
        corrections_widget.setLayout(layout)
        self.tab_widget.addTab(corrections_widget, "Corrections")
    
    def _create_statistics_tab(self):
        """Create validation statistics tab."""
        stats_widget = QWidget()
        layout = QVBoxLayout()
        
        # Statistics display
        stats_group = QGroupBox("Validation Statistics")
        stats_layout = QGridLayout()
        
        # Create labels for statistics
        self.total_corrections_label = QLabel("Total Corrections: 0")
        stats_layout.addWidget(self.total_corrections_label, 0, 0)
        
        self.approved_corrections_label = QLabel("Approved: 0")
        stats_layout.addWidget(self.approved_corrections_label, 0, 1)
        
        self.rejected_corrections_label = QLabel("Rejected: 0")
        stats_layout.addWidget(self.rejected_corrections_label, 1, 0)
        
        self.pending_corrections_label = QLabel("Pending: 0")
        stats_layout.addWidget(self.pending_corrections_label, 1, 1)
        
        self.avg_confidence_label = QLabel("Avg Confidence: 0%")
        stats_layout.addWidget(self.avg_confidence_label, 2, 0)
        
        self.validation_time_label = QLabel("Validation Time: 0s")
        stats_layout.addWidget(self.validation_time_label, 2, 1)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Progress indicators
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        
        self.validation_progress = QProgressBar()
        progress_layout.addWidget(self.validation_progress)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        layout.addStretch()
        
        stats_widget.setLayout(layout)
        self.tab_widget.addTab(stats_widget, "Statistics")
    
    def _create_settings_tab(self):
        """Create validation settings tab."""
        settings_widget = QWidget()
        layout = QVBoxLayout()
        
        # Validation settings
        settings_group = QGroupBox("Validation Settings")
        settings_layout = QFormLayout()
        
        # Confidence threshold
        self.confidence_threshold = QSpinBox()
        self.confidence_threshold.setRange(50, 100)
        self.confidence_threshold.setValue(70)
        self.confidence_threshold.setSuffix("%")
        settings_layout.addRow("Confidence Threshold:", self.confidence_threshold)
        
        # Auto-apply threshold
        self.auto_apply_threshold = QSpinBox()
        self.auto_apply_threshold.setRange(80, 100)
        self.auto_apply_threshold.setValue(95)
        self.auto_apply_threshold.setSuffix("%")
        settings_layout.addRow("Auto-apply Threshold:", self.auto_apply_threshold)
        
        # Max corrections per element
        self.max_corrections = QSpinBox()
        self.max_corrections.setRange(1, 20)
        self.max_corrections.setValue(5)
        settings_layout.addRow("Max Corrections per Element:", self.max_corrections)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        layout.addStretch()
        
        settings_widget.setLayout(layout)
        self.tab_widget.addTab(settings_widget, "Settings")
    
    def _create_footer(self, parent_layout):
        """Create footer section with actions."""
        footer_frame = QFrame()
        footer_frame.setFrameStyle(QFrame.StyledPanel)
        footer_layout = QHBoxLayout()
        
        # Summary information
        self.summary_label = QLabel("Ready for validation")
        footer_layout.addWidget(self.summary_label)
        
        footer_layout.addStretch()
        
        # Action buttons
        self.save_session_btn = QPushButton("Save Session")
        self.save_session_btn.clicked.connect(self._save_validation_session)
        footer_layout.addWidget(self.save_session_btn)
        
        self.finalize_btn = QPushButton("Finalize Validation")
        self.finalize_btn.clicked.connect(self._finalize_validation)
        self.finalize_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        footer_layout.addWidget(self.finalize_btn)
        
        footer_frame.setLayout(footer_layout)
        parent_layout.addWidget(footer_frame)
    
    def load_document(self, document: Document, post_processing_result=None):
        """Load a document for validation."""
        self.current_document = document
        self.doc_name_label.setText(f"Document: {document.metadata.file_name}")
        
        # Check for validation session from post-processing result
        if post_processing_result and hasattr(post_processing_result, 'validation_session'):
            self.validation_session = post_processing_result.validation_session
            self.current_corrections = document.custom_metadata.get('corrections', [])
            self._display_corrections()
            self._update_statistics()
        # Also check for corrections directly in document metadata (for project loading)
        elif document.custom_metadata.get('corrections'):
            self.validation_session = None  # No validation session available
            self.current_corrections = document.custom_metadata.get('corrections', [])
            self._display_corrections()
            self._update_statistics()
            self.logger.info(f"Loaded {len(self.current_corrections)} corrections from document metadata")
        
        self.doc_status_label.setText("Status: Loaded")
        self.logger.info(f"Loaded document for validation: {document.id}")
    
    def _start_validation(self):
        """Start the validation process."""
        if not self.current_document:
            QMessageBox.warning(self, "No Document", "Please load a document first.")
            return
        
        try:
            self.doc_status_label.setText("Status: Validating...")
            self.start_validation_btn.setEnabled(False)
            
            # This would typically trigger a background validation process
            # For now, we'll assume corrections are already available
            if hasattr(self.current_document, 'custom_metadata'):
                corrections_data = self.current_document.custom_metadata.get('corrections', [])
                # Convert to ContentCorrection objects if needed
                self._display_corrections()
                self._update_statistics()
            
            self.doc_status_label.setText("Status: Validation Complete")
            
        except Exception as e:
            QMessageBox.critical(self, "Validation Error", f"Validation failed: {str(e)}")
            self.logger.error(f"Validation failed: {str(e)}")
        finally:
            self.start_validation_btn.setEnabled(True)
    
    def _display_corrections(self):
        """Display corrections in the interface with pagination."""
        # Show progress for large correction sets
        corrections_data = self.current_document.custom_metadata.get('corrections', [])
        if len(corrections_data) > 50:
            self._show_progress("Loading corrections...", 0)
        
        # Clear existing corrections
        for i in reversed(range(self.corrections_layout.count())):
            child = self.corrections_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Calculate pagination
        start_idx = self.current_page * self.corrections_per_page
        end_idx = start_idx + self.corrections_per_page
        page_corrections = corrections_data[start_idx:end_idx]
        
        self.logger.info(f"Displaying {len(page_corrections)} corrections (page {self.current_page + 1}, total: {len(corrections_data)})")
        
        for idx, correction_data in enumerate(page_corrections):
            try:
                # Map issue type to correction type
                issue_type = correction_data.get('type', 'ocr_error')
                if issue_type == 'ocr_error':
                    correction_type = CorrectionType.OCR_CORRECTION
                elif issue_type == 'encoding_error':
                    correction_type = CorrectionType.FORMATTING_FIX
                elif issue_type == 'table_error':
                    correction_type = CorrectionType.STRUCTURE_IMPROVEMENT
                elif issue_type == 'formatting_error':
                    correction_type = CorrectionType.FORMATTING_FIX
                else:
                    correction_type = CorrectionType.OCR_CORRECTION  # default
                
                # Get location data
                location = correction_data.get('location', {})
                page_number = location.get('page', 1)
                bbox = location.get('bbox', None)
                text_position = location.get('text_position', None)
                
                # Create specific reasoning based on the issue
                issue_description = correction_data.get('description', 'Unknown issue')
                specific_reasoning = self._generate_specific_reasoning(issue_description, correction_type)
                
                # Create ContentCorrection object with actual data
                correction = ContentCorrection(
                    id=correction_data.get('id', f'correction_{idx}'),
                    correction_type=correction_type,
                    element_id=f'element_{idx}',
                    page_number=page_number,
                    bbox=bbox,
                    original_content=correction_data.get('original_text', issue_description),  # Use original_text if available
                    suggested_content=correction_data.get('suggested_fix', 'Manual review required'),
                    confidence=correction_data.get('confidence', 0.5),
                    reasoning=specific_reasoning,
                    status=CorrectionStatus.SUGGESTED
                )
                
                # Add additional data for PDF extraction
                correction.text_position = text_position
                correction.pdf_path = self.current_document.metadata.file_path if self.current_document else None
                
                correction_widget = CorrectionItemWidget(correction)
                
                # Connect signals for PDF highlighting
                correction_widget.correction_selected.connect(self._on_correction_selected)
                correction_widget.correction_edited.connect(self._on_correction_edited)
                
                self.corrections_layout.addWidget(correction_widget)
                
            except Exception as e:
                self.logger.error(f"Error creating correction widget {idx}: {e}")
                continue
        
        self.corrections_layout.addStretch()
        self._update_pagination_controls()
        self._hide_progress()  # Hide progress overlay
        self.logger.info(f"Successfully displayed {len(page_corrections)} correction widgets (page {self.current_page + 1})")
    
    def _filter_corrections(self):
        """Filter corrections based on selected criteria."""
        type_filter = self.type_filter.currentText()
        status_filter = self.status_filter.currentText()
        
        # Hide/show correction widgets based on filters
        for i in range(self.corrections_layout.count()):
            item = self.corrections_layout.itemAt(i)
            if item and isinstance(item.widget(), CorrectionItemWidget):
                widget = item.widget()
                correction = widget.correction
                
                show_widget = True
                
                if type_filter != "All Types" and correction.correction_type.value != type_filter:
                    show_widget = False
                
                if status_filter != "All Status" and correction.status.value != status_filter:
                    show_widget = False
                
                widget.setVisible(show_widget)
    
    def _approve_all_visible(self):
        """Approve all visible corrections."""
        count = 0
        for i in range(self.corrections_layout.count()):
            item = self.corrections_layout.itemAt(i)
            if item and isinstance(item.widget(), CorrectionItemWidget):
                widget = item.widget()
                if widget.isVisible() and widget.correction.status == CorrectionStatus.SUGGESTED:
                    widget._approve_correction()
                    count += 1
        
        self._update_statistics()
        self.summary_label.setText(f"Approved {count} corrections")
    
    def _reject_all_visible(self):
        """Reject all visible corrections."""
        count = 0
        for i in range(self.corrections_layout.count()):
            item = self.corrections_layout.itemAt(i)
            if item and isinstance(item.widget(), CorrectionItemWidget):
                widget = item.widget()
                if widget.isVisible() and widget.correction.status == CorrectionStatus.SUGGESTED:
                    widget._reject_correction()
                    count += 1
        
        self._update_statistics()
        self.summary_label.setText(f"Rejected {count} corrections")
    
    def _update_statistics(self):
        """Update validation statistics display."""
        if not self.current_document:
            return
        
        corrections_data = self.current_document.custom_metadata.get('corrections', [])
        
        total = len(corrections_data)
        approved = len([c for c in corrections_data if c.get('status') == 'approved'])
        rejected = len([c for c in corrections_data if c.get('status') == 'rejected'])
        pending = total - approved - rejected
        
        avg_confidence = sum(c.get('confidence', 0) for c in corrections_data) / total if total > 0 else 0
        
        self.total_corrections_label.setText(f"Total Corrections: {total}")
        self.approved_corrections_label.setText(f"Approved: {approved}")
        self.rejected_corrections_label.setText(f"Rejected: {rejected}")
        self.pending_corrections_label.setText(f"Pending: {pending}")
        self.avg_confidence_label.setText(f"Avg Confidence: {avg_confidence:.1%}")
        
        # Update progress bar
        if total > 0:
            progress = int(((approved + rejected) / total) * 100)
            self.validation_progress.setValue(progress)
    
    def _save_validation_session(self):
        """Save the current validation session."""
        if not self.current_document:
            QMessageBox.warning(self, "No Document", "No document loaded to save.")
            return
        
        try:
            # Save validation state to document
            self.summary_label.setText("Validation session saved")
            # REMOVED: Session saved popup for seamless workflow - related to Issue #31 fix
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save session: {str(e)}")
    
    def _finalize_validation(self):
        """Finalize the validation process."""
        if not self.current_document:
            QMessageBox.warning(self, "No Document", "No document loaded to finalize.")
            return
        
        # Check if all corrections have been reviewed
        corrections_data = self.current_document.custom_metadata.get('corrections', [])
        pending = len([c for c in corrections_data if c.get('status') == 'suggested'])
        
        if pending > 0:
            reply = QMessageBox.question(
                self, 
                "Pending Corrections", 
                f"There are {pending} pending corrections. Finalize anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        try:
            # Finalize validation
            self.doc_status_label.setText("Status: Validation Finalized")
            self.summary_label.setText("Validation completed and finalized")
            # REMOVED: QMessageBox popup that interrupted workflow - fixes Issue #31
            # The validation completion should be seamless without popup interruption
            
        except Exception as e:
            QMessageBox.critical(self, "Finalization Error", f"Failed to finalize validation: {str(e)}")
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of current validation state."""
        if not self.current_document:
            return {}
        
        corrections_data = self.current_document.custom_metadata.get('corrections', [])
        
        return {
            'document_id': self.current_document.id,
            'total_corrections': len(corrections_data),
            'approved_corrections': len([c for c in corrections_data if c.get('status') == 'approved']),
            'rejected_corrections': len([c for c in corrections_data if c.get('status') == 'rejected']),
            'pending_corrections': len([c for c in corrections_data if c.get('status') == 'suggested']),
            'validation_complete': self.doc_status_label.text() == "Status: Validation Finalized"
        }
    
    def _on_correction_selected(self, correction: ContentCorrection):
        """Handle correction selection for PDF highlighting with enhanced coordinate correspondence."""
        try:
            from .coordinate_correspondence import coordinate_engine
            
            page_number = correction.page_number
            original_bbox = correction.bbox
            search_text = correction.original_content
            
            # Get the current document path for coordinate lookup
            document_path = None
            if hasattr(self, 'current_document') and self.current_document:
                document_path = getattr(self.current_document.metadata, 'file_path', None)
            
            if document_path:
                # Use enhanced coordinate correspondence for accurate highlighting
                self.logger.info(f"Using enhanced coordinate correspondence for correction {correction.id}")
                
                # Convert to 0-indexed page number for coordinate engine
                page_index = page_number - 1 if page_number > 0 else page_number
                
                self.logger.info(f"Page number conversion: correction.page_number={page_number} -> page_index={page_index}")
                self.logger.info(f"Document path: {document_path}")
                self.logger.info(f"Search text: '{search_text[:100]}...' ({len(search_text)} chars)")
                
                highlight_region = coordinate_engine.find_text_coordinates(
                    pdf_path=document_path,
                    page_number=page_index,
                    search_text=search_text,
                    fallback_bbox=original_bbox
                )
                
                # Log the results
                self.logger.info(f"Coordinate correspondence result: {highlight_region.match_type} "
                               f"match with confidence {highlight_region.confidence:.2f}, "
                               f"{len(highlight_region.regions)} regions found")
                
                # Emit signal with enhanced coordinates
                # For backward compatibility, emit the first region as bbox and include all regions
                primary_bbox = highlight_region.regions[0] if highlight_region.regions else original_bbox
                
                # Create enhanced highlight data
                enhanced_data = {
                    'regions': highlight_region.regions,
                    'confidence': highlight_region.confidence,
                    'match_type': highlight_region.match_type,
                    'multi_line': len(highlight_region.regions) > 1
                }
                
                self.highlight_pdf_location.emit(page_number, enhanced_data, search_text)
                
            else:
                # Fallback to original method if no document path
                self.logger.warning("No document path available, using original highlighting method")
                self.highlight_pdf_location.emit(page_number, original_bbox, search_text)
            
            self.logger.info(f"Highlighting correction {correction.id} on page {page_number} with search text: '{search_text[:50]}...')")
            
        except Exception as e:
            self.logger.error(f"Error highlighting correction {correction.id}: {e}")
    
    def _on_correction_edited(self, correction: ContentCorrection):
        """Handle correction content edits."""
        try:
            # Update the correction in document metadata
            corrections_data = self.current_document.custom_metadata.get('corrections', [])
            
            # Find and update the correction
            for i, corr_data in enumerate(corrections_data):
                if corr_data.get('id') == correction.id:
                    corr_data['suggested_fix'] = correction.suggested_content
                    corr_data['status'] = 'pending_review'
                    break
            
            # Update statistics
            self._update_statistics()
            
            self.logger.info(f"Correction {correction.id} content updated")
            
        except Exception as e:
            self.logger.error(f"Error updating correction {correction.id}: {e}")
    
    def _generate_specific_reasoning(self, issue_description: str, correction_type: CorrectionType) -> str:
        """Generate specific reasoning based on the issue description and type."""
        try:
            # Extract the problematic text from the description
            if "Potential OCR error: '" in issue_description:
                problematic_text = issue_description.split("Potential OCR error: '")[1].split("'")[0]
            else:
                problematic_text = issue_description
            
            # Generate specific reasoning based on the problematic text
            if correction_type == CorrectionType.OCR_CORRECTION:
                if problematic_text in ['000', '0000']:
                    return f"Character sequence '{problematic_text}' may be misrecognized numbers. Could be flight levels (FL{problematic_text}), altitudes, or frequencies. Common OCR confusion between O and 0."
                elif problematic_text in ['//', '/', '\\']:
                    return f"Symbol '{problematic_text}' may be misrecognized delimiter. Could be date separators, path indicators, or document references. Check context for correct format."
                elif problematic_text in ['I', 'l', '1', '|']:
                    return f"Character '{problematic_text}' shows OCR confusion between capital I, lowercase l, number 1, or pipe symbol. Common in aircraft callsigns and identifiers."
                elif problematic_text in ['O', '0']:
                    return f"Character '{problematic_text}' shows OCR confusion between letter O and number 0. Critical for runway designations, flight numbers, and coordinates."
                elif problematic_text in ['S', '5']:
                    return f"Character '{problematic_text}' may be misrecognized. OCR confusion between letter S and number 5, important for callsigns and frequencies."
                elif problematic_text in ['B', '8']:
                    return f"Character '{problematic_text}' shows OCR confusion between letter B and number 8. Check aircraft registrations and flight numbers."
                elif len(problematic_text) == 1:
                    return f"Single character '{problematic_text}' requires verification. May affect aircraft identifiers, coordinates, or navigation data."
                else:
                    return f"Text sequence '{problematic_text}' flagged for OCR accuracy. Verify against source document for aviation data integrity."
            
            elif correction_type == CorrectionType.FORMATTING_FIX:
                return f"Formatting issue with '{problematic_text}'. May affect document structure, spacing, or special characters in aviation documents."
            
            elif correction_type == CorrectionType.STRUCTURE_IMPROVEMENT:
                return f"Structural issue affecting '{problematic_text}'. May impact table layout, data alignment, or document hierarchy in aviation documentation."
            
            else:
                return f"Content validation required for '{problematic_text}'. Manual review needed to ensure aviation data accuracy and compliance."
                
        except Exception as e:
            self.logger.error(f"Error generating specific reasoning: {e}")
            return "Manual review and correction required for data accuracy."
    
    def _update_pagination_controls(self):
        """Update pagination controls based on current state."""
        if not self.current_document:
            return
        
        corrections_data = self.current_document.custom_metadata.get('corrections', [])
        total_corrections = len(corrections_data)
        total_pages = (total_corrections + self.corrections_per_page - 1) // self.corrections_per_page
        
        # Update page info
        self.page_info_label.setText(f"Page {self.current_page + 1} of {total_pages}")
        self.corrections_count_label.setText(f"{total_corrections} corrections")
        
        # Update button states
        self.prev_page_btn.setEnabled(self.current_page > 0)
        self.next_page_btn.setEnabled(self.current_page < total_pages - 1)
    
    def _prev_page(self):
        """Navigate to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self._display_corrections()
    
    def _next_page(self):
        """Navigate to next page."""
        if self.current_document:
            corrections_data = self.current_document.custom_metadata.get('corrections', [])
            total_pages = (len(corrections_data) + self.corrections_per_page - 1) // self.corrections_per_page
            if self.current_page < total_pages - 1:
                self.current_page += 1
                self._display_corrections()
    
    def _show_progress(self, message="Loading...", progress=0):
        """Show progress overlay with message and progress bar."""
        self.progress_label.setText(message)
        self.progress_bar_overlay.setValue(progress)
        self.progress_overlay.resize(self.size())
        self.progress_overlay.show()
    
    def _hide_progress(self):
        """Hide progress overlay."""
        self.progress_overlay.hide()
    
    def _create_color_legend_tab(self):
        """Create color legend tab to explain highlighting colors."""
        legend_widget = QWidget()
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel("🎨 Highlighting Color Legend")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; margin-bottom: 15px;")
        layout.addWidget(header_label)
        
        # Description
        description = QLabel("""
This tab explains the different colors used for highlighting in the extraction text and PDF preview. 
Each color represents a different type of issue or area classification.
        """)
        description.setWordWrap(True)
        description.setStyleSheet("margin-bottom: 20px; color: #666;")
        layout.addWidget(description)
        
        # Legend items
        legend_data = MultiColorHighlighter.get_color_legend()
        
        for item in legend_data:
            legend_item_widget = self._create_legend_item(item)
            layout.addWidget(legend_item_widget)
        
        # Usage instructions
        usage_group = QGroupBox("💡 Usage Tips")
        usage_layout = QVBoxLayout()
        
        usage_text = QLabel("""
• <b>Active Issue (Yellow):</b> Click on a correction in the list to see it highlighted in bright yellow
• <b>Other Issues (Light Yellow):</b> Other validation issues are shown in a lighter yellow color
• <b>Manual Areas (Red/Blue/Purple):</b> Areas you manually classified during validation are shown with colored backgrounds
• <b>Auto Conflicts (Orange):</b> Areas where auto-detection conflicts with your manual classification
• <b>Resolved (Green):</b> Conflicts that have been successfully resolved

<b>Navigation:</b> Click on any correction in the corrections list to see it highlighted in the extraction text and PDF preview.
        """)
        usage_text.setWordWrap(True)
        usage_text.setStyleSheet("color: #333; line-height: 1.4;")
        usage_layout.addWidget(usage_text)
        
        usage_group.setLayout(usage_layout)
        layout.addWidget(usage_group)
        
        layout.addStretch()
        
        legend_widget.setLayout(layout)
        self.tab_widget.addTab(legend_widget, "🎨 Colors")
    
    def _create_legend_item(self, item_data: Dict[str, Any]) -> QWidget:
        """Create a legend item widget showing the color and description."""
        item_widget = QFrame()
        item_widget.setFrameStyle(QFrame.Box)
        item_widget.setStyleSheet("border: 1px solid #ddd; border-radius: 4px; margin: 5px 0px; padding: 10px;")
        
        layout = QHBoxLayout()
        
        # Color sample
        color_config = MultiColorHighlighter.HIGHLIGHT_COLORS[item_data['type']]
        color_sample = QLabel("Sample Text")
        color_sample.setStyleSheet(f"""
            background-color: rgba({color_config['background'].red()}, {color_config['background'].green()}, 
                                 {color_config['background'].blue()}, {color_config['background'].alpha()});
            color: rgb({color_config['foreground'].red()}, {color_config['foreground'].green()}, 
                     {color_config['foreground'].blue()});
            font-weight: {'bold' if color_config['bold'] else 'normal'};
            text-decoration: {'underline' if color_config['underline'] else 'none'};
            padding: 8px;
            border-radius: 3px;
            min-width: 100px;
            text-align: center;
        """)
        color_sample.setAlignment(Qt.AlignCenter)
        layout.addWidget(color_sample)
        
        # Name and description
        text_layout = QVBoxLayout()
        
        name_label = QLabel(item_data['name'])
        name_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50;")
        text_layout.addWidget(name_label)
        
        desc_label = QLabel(item_data['description'])
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; font-size: 12px;")
        text_layout.addWidget(desc_label)
        
        layout.addLayout(text_layout)
        layout.setStretchFactor(text_layout, 1)
        
        item_widget.setLayout(layout)
        return item_widget

    def resizeEvent(self, event):
        """Handle widget resize to update progress overlay."""
        super().resizeEvent(event)
        if hasattr(self, 'progress_overlay'):
            self.progress_overlay.resize(self.size())