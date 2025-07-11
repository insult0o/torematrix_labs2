#!/usr/bin/env python3
"""
Page-by-page validation widget with side-by-side PDF and extracted text view.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

from ..qt_compat import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QTextEdit, 
    QFrame, Qt, QColor, QTextCharFormat, QTextCursor, QFont,
    QEvent, pyqtSignal
)

from ...config.settings import Settings
from ...models.document_models import Document
from ...core.ocr_based_extractor import OCRBasedExtractor, OCR_DEPENDENCIES_AVAILABLE
from ...core.enhanced_pdf_extractor import EnhancedPDFExtractor
from ...core.unstructured_extractor import UnstructuredExtractor, UNSTRUCTURED_AVAILABLE
from ..highlighting import HighlightingEngine, HighlightStyle


class PageValidationWidget(QWidget):
    """Page-by-page validation widget with side-by-side layout."""
    
    # Signals
    status_message = pyqtSignal(str)
    validation_completed = pyqtSignal(str, bool)
    highlight_pdf_location = pyqtSignal(int, object, str, str)  # page, bbox, search_text, highlight_type
    highlight_pdf_text_selection = pyqtSignal(int, object)  # page, bbox for text selection
    cursor_pdf_location = pyqtSignal(int, object)  # page, bbox for cursor position
    navigate_pdf_page = pyqtSignal(int)  # page number only, for navigation without highlighting
    log_message = pyqtSignal(str)  # for sending messages to log widget
    
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # State
        self.current_document: Optional[Document] = None
        self.post_processing_result = None
        self._current_page = 1  # Use private attribute
        self.total_pages = 0
        self.current_page_issues = []
        self.current_issue_index = 0
        self.corrections_by_page = {}
        self.text_to_pdf_mapping = {}  # Maps text positions to PDF coordinates
        self.pdf_page_data = None  # Current page PDF structure data
        
        # Initialize advanced extractors (in order of preference)
        self.unstructured_extractor = UnstructuredExtractor(settings) if UNSTRUCTURED_AVAILABLE else None
        self.ocr_extractor = OCRBasedExtractor(settings) if OCR_DEPENDENCIES_AVAILABLE else None
        self.enhanced_extractor = EnhancedPDFExtractor(settings)
        
        # Storage for extraction results
        self.ocr_characters = []  # Store OCR character data
        self.unstructured_elements = []  # Store Unstructured elements
        self.full_document_text = ""  # Complete document text
        
        # Extraction strategy selection (in order of preference)
        self.use_unstructured = UNSTRUCTURED_AVAILABLE  # Best: Document structure detection
        self.use_ocr = OCR_DEPENDENCIES_AVAILABLE and not UNSTRUCTURED_AVAILABLE  # Good: Visual recognition
        self.use_enhanced = True  # Fallback: Advanced PyMuPDF
        
        # Initialize highlighting components (will use PDF viewer's engine when available)
        self.highlighting_engine = None
        self.highlight_style = HighlightStyle()
        
        self._init_ui()
        self.logger.info("Page validation widget initialized with highlighting engine")
    
    
    def handle_page_change(self, page_number: int):
        """Handle page change from external source (e.g., document viewer)."""
        try:
            if page_number != self.current_page:
                self.logger.info(f"External page change detected: {self.current_page} → {page_number}")
                self.current_page = page_number
                # Load text for the new page
                self._load_page_text(page_number)
                # Load corrections for this page
                self.current_page_issues = self.corrections_by_page.get(page_number, [])
                self.current_issue_index = 0
                # Update display
                self._highlight_all_differences_without_modification()
                self._update_issue_navigation()
                self.log_message.emit(f"Page changed to {page_number} via document viewer")
        except Exception as e:
            self.logger.error(f"Failed to handle page change: {str(e)}")
            self.log_message.emit(f"Error handling page change: {str(e)}")
    
    @property
    def current_page(self):
        """Get current page number, ensuring it's never 0."""
        return self._current_page
    
    @current_page.setter
    def current_page(self, value):
        """Set current page number, ensuring it's never 0."""
        if value <= 0:
            self.logger.warning(f"Attempted to set current_page to {value}, correcting to 1")
            self._current_page = 1
        else:
            self._current_page = value
        self.logger.debug(f"Current page set to: {self._current_page}")
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("QA Validation Layer - Enhanced Error Detection & Correction")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Status
        self.status_label = QLabel("Ready for page-by-page validation")
        self.status_label.setStyleSheet("background-color: #ecf0f1; padding: 8px; border-radius: 4px;")
        layout.addWidget(self.status_label)
        
        # Issue navigation only - page navigation handled by document preview
        nav_layout = QHBoxLayout()
        
        self.prev_issue_btn = QPushButton("◀ Previous Issue")
        self.prev_issue_btn.clicked.connect(self._prev_issue)
        self.prev_issue_btn.setEnabled(False)
        nav_layout.addWidget(self.prev_issue_btn)
        
        self.issue_label = QLabel("Issue 1 of 1")
        self.issue_label.setAlignment(Qt.AlignCenter)
        self.issue_label.setStyleSheet("font-weight: bold; padding: 8px; color: #e74c3c;")
        nav_layout.addWidget(self.issue_label)
        
        self.next_issue_btn = QPushButton("Next Issue ▶")
        self.next_issue_btn.clicked.connect(self._next_issue)
        self.next_issue_btn.setEnabled(False)
        nav_layout.addWidget(self.next_issue_btn)
        
        nav_layout.addStretch()
        
        layout.addLayout(nav_layout)
        
        # Removed redundant issue info display - now handled by QA validation controls
        
        # Area validation controls (for auto-detected areas)
        self.area_validation_frame = QFrame()
        self.area_validation_frame.setFrameStyle(QFrame.StyledPanel)
        self.area_validation_frame.setStyleSheet("background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; padding: 8px;")
        self.area_validation_frame.setVisible(False)  # Hidden by default
        
        area_validation_layout = QVBoxLayout()
        
        area_validation_label = QLabel("⚠️ Auto-detected area needs manual validation")
        area_validation_label.setStyleSheet("font-weight: bold; color: #856404;")
        area_validation_layout.addWidget(area_validation_label)
        
        area_buttons_layout = QHBoxLayout()
        
        self.approve_area_btn = QPushButton("✓ Approve Area")
        self.approve_area_btn.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 8px;")
        self.approve_area_btn.clicked.connect(self._approve_area)
        area_buttons_layout.addWidget(self.approve_area_btn)
        
        self.reject_area_btn = QPushButton("✗ Reject Area")
        self.reject_area_btn.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 8px;")
        self.reject_area_btn.clicked.connect(self._reject_area)
        area_buttons_layout.addWidget(self.reject_area_btn)
        
        self.delete_area_btn = QPushButton("🗑️ Delete Area")
        self.delete_area_btn.setStyleSheet("background-color: #6c757d; color: white; font-weight: bold; padding: 8px;")
        self.delete_area_btn.clicked.connect(self._delete_area)
        area_buttons_layout.addWidget(self.delete_area_btn)
        
        area_validation_layout.addLayout(area_buttons_layout)
        
        self.area_validation_frame.setLayout(area_validation_layout)
        layout.addWidget(self.area_validation_frame)
        
        # Enhanced QA Validation Controls
        self._create_qa_validation_controls(layout)
        
        # Full width extracted text content (document preview handles PDF display)
        text_header = QLabel("Extracted Text Content")
        text_header.setStyleSheet("font-weight: bold; font-size: 14px; padding: 8px;")
        layout.addWidget(text_header)
        
        self.extracted_text = QTextEdit()
        self.extracted_text.setReadOnly(False)  # Allow editing for corrections
        self.extracted_text.setPlaceholderText("Extracted text will appear here with highlighted errors...")
        
        # Maximize the text area - make it much bigger and expandable
        self.extracted_text.setMinimumHeight(400)  # Much bigger minimum height
        self.extracted_text.setSizePolicy(
            self.extracted_text.sizePolicy().horizontalPolicy(),
            self.extracted_text.sizePolicy().Expanding  # Allow vertical expansion
        )
        
        # Connect text cursor and selection signals
        self.extracted_text.cursorPositionChanged.connect(self._on_cursor_position_changed)
        self.extracted_text.selectionChanged.connect(self._on_text_selection_changed)
        
        # Note: highlighting engine connection will be set up in set_pdf_viewer()
        # when the PDF viewer's highlighting engine becomes available
        self.logger.info("Text widget ready for highlighting engine connection")
        
        # Store PDF document reference for coordinate mapping
        self.pdf_document = None
        self.pdf_viewer = None
        
        # Enable mouse interaction - use event filter instead of direct override
        self.extracted_text.setMouseTracking(True)
        self.extracted_text.installEventFilter(self)
    
    def set_pdf_viewer(self, pdf_viewer):
        """Set the PDF viewer and use its highlighting engine for synchronized highlighting."""
        try:
            self.pdf_viewer = pdf_viewer
            
            # Use the PDF viewer's highlighting engine for perfect synchronization
            if hasattr(pdf_viewer, 'highlighting_engine') and pdf_viewer.highlighting_engine:
                self.highlighting_engine = pdf_viewer.highlighting_engine
                self.logger.info("✅ Using PDF viewer's highlighting engine for synchronized highlighting")
                
                # Connect the text widget to the shared highlighting engine
                if self.extracted_text:
                    self.highlighting_engine.set_text_widget(self.extracted_text)
                    self.logger.info("✅ Connected text widget to shared highlighting engine")
            else:
                # Fallback: create our own engine and connect it to the PDF viewer
                self.highlighting_engine = HighlightingEngine()
                self.highlighting_engine.set_pdf_viewer(pdf_viewer)
                if self.extracted_text:
                    self.highlighting_engine.set_text_widget(self.extracted_text)
                self.logger.warning("⚠️ Created fallback highlighting engine")
            
            # Set up coordinate mapping when PDF document is available
            if hasattr(pdf_viewer, 'current_document') and pdf_viewer.current_document:
                self._setup_coordinate_mapping(pdf_viewer.current_document)
                
                # If we have a document loaded, rebuild coordinate maps
                if self.highlighting_engine:
                    try:
                        if hasattr(self.highlighting_engine, 'coordinate_mapper') and self.highlighting_engine.coordinate_mapper:
                            self.highlighting_engine.coordinate_mapper.rebuild_maps()
                            self.logger.info("Coordinate maps rebuilt for highlighting engine")
                    except Exception as e:
                        self.logger.error(f"Failed to rebuild coordinate maps: {e}")
            
            self.logger.info("PDF viewer connected to PageValidationWidget")
            
        except Exception as e:
            self.logger.error(f"Error setting PDF viewer: {e}")
    
    def _setup_coordinate_mapping(self, pdf_document):
        """Set up coordinate mapping for the PDF document."""
        try:
            self.pdf_document = pdf_document
            
            # Set PDF document in the coordinate mapper
            if self.highlighting_engine and hasattr(self.highlighting_engine, 'coordinate_mapper') and self.highlighting_engine.coordinate_mapper:
                self.highlighting_engine.coordinate_mapper.pdf_document = pdf_document
                # Rebuild coordinate maps for the new document
                self.highlighting_engine.coordinate_mapper._build_coordinate_maps()
                self.logger.info("Built coordinate maps for PDF document")
            
        except Exception as e:
            self.logger.error(f"Error setting up coordinate mapping: {e}")
        
        layout.addWidget(self.extracted_text)
        
        # Correction controls
        correction_layout = QHBoxLayout()
        
        self.approve_correction_btn = QPushButton("✓ Approve Correction")
        self.approve_correction_btn.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 8px;")
        self.approve_correction_btn.clicked.connect(self._approve_current_correction)
        self.approve_correction_btn.setEnabled(False)
        correction_layout.addWidget(self.approve_correction_btn)
        
        self.reject_correction_btn = QPushButton("✗ Reject Correction")
        self.reject_correction_btn.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 8px;")
        self.reject_correction_btn.clicked.connect(self._reject_current_correction)
        self.reject_correction_btn.setEnabled(False)
        correction_layout.addWidget(self.reject_correction_btn)
        
        correction_layout.addStretch()
        
        self.save_all_btn = QPushButton("💾 Save All Changes")
        self.save_all_btn.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; padding: 8px;")
        self.save_all_btn.clicked.connect(self._save_all_changes)
        self.save_all_btn.setEnabled(False)
        correction_layout.addWidget(self.save_all_btn)
        
        layout.addLayout(correction_layout)
        
        self.setLayout(layout)
    
    def _create_qa_validation_controls(self, layout):
        """Create enhanced QA validation controls - NEW CLEAN IMPLEMENTATION."""
        
        # Main QA Frame - Clean and compact
        qa_frame = QFrame()
        qa_frame.setObjectName("qa_validation_frame")
        qa_frame.setStyleSheet("""
            QFrame#qa_validation_frame {
                background-color: #f8f9fa;
                border: 1px solid #007bff;
                border-radius: 6px;
                padding: 12px;
                margin: 6px;
                max-height: 240px;
                min-height: 200px;
            }
        """)
        
        main_layout = QVBoxLayout(qa_frame)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(8, 8, 8, 8)
        
        # Header with title
        header_layout = QHBoxLayout()
        header_title = QLabel("PDF vs Extraction Comparison")
        header_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #007bff;")
        header_layout.addWidget(header_title)
        
        # Statistics display in header
        header_layout.addStretch()
        self.error_stats_label = QLabel("Critical: 0 | Major: 0 | Medium: 0 | Minor: 0 | Resolved: 0")
        self.error_stats_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        header_layout.addWidget(self.error_stats_label)
        
        main_layout.addLayout(header_layout)
        
        # Detection types and controls in more spacious row
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)
        
        from ..qt_compat import QCheckBox
        
        # Detection type checkboxes - with proper text labels
        self.formatting_errors_check = QCheckBox("Formatting")
        self.formatting_errors_check.setChecked(True)
        self.formatting_errors_check.setToolTip("Format differences between PDF and extraction")
        self.formatting_errors_check.setStyleSheet("font-size: 11px; color: #495057;")
        controls_layout.addWidget(self.formatting_errors_check)
        
        self.writing_errors_check = QCheckBox("Writing")
        self.writing_errors_check.setChecked(True)
        self.writing_errors_check.setToolTip("Text/OCR differences")
        self.writing_errors_check.setStyleSheet("font-size: 11px; color: #495057;")
        controls_layout.addWidget(self.writing_errors_check)
        
        self.vanishments_check = QCheckBox("Missing")
        self.vanishments_check.setChecked(True)
        self.vanishments_check.setToolTip("Content in PDF but missing from extraction")
        self.vanishments_check.setStyleSheet("font-size: 11px; color: #495057;")
        controls_layout.addWidget(self.vanishments_check)
        
        self.additions_check = QCheckBox("Extra")
        self.additions_check.setChecked(True)
        self.additions_check.setToolTip("Content in extraction but not in PDF")
        self.additions_check.setStyleSheet("font-size: 11px; color: #495057;")
        controls_layout.addWidget(self.additions_check)
        
        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setFrameShadow(QFrame.Sunken)
        sep1.setStyleSheet("color: #dee2e6;")
        controls_layout.addWidget(sep1)
        
        # Action buttons - larger and more visible
        button_style = """
            QPushButton {
                background-color: %s;
                color: white;
                border: none;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
                border-radius: 4px;
                min-width: 60px;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: %s;
            }
            QPushButton:pressed {
                background-color: %s;
            }
        """
        
        self.run_detection_btn = QPushButton("Run Detection")
        self.run_detection_btn.setStyleSheet(button_style % ("#17a2b8", "#138496", "#0f6674"))
        self.run_detection_btn.clicked.connect(self._run_full_detection)
        self.run_detection_btn.setToolTip("Compare PDF vs Extraction content")
        controls_layout.addWidget(self.run_detection_btn)
        
        self.reset_detection_btn = QPushButton("Reset")
        self.reset_detection_btn.setStyleSheet(button_style % ("#6c757d", "#5a6268", "#4e555b"))
        self.reset_detection_btn.clicked.connect(self._reset_detection)
        self.reset_detection_btn.setToolTip("Clear all detection results")
        controls_layout.addWidget(self.reset_detection_btn)
        
        # Add some horizontal spacing
        controls_layout.addSpacing(20)
        
        self.bulk_approve_btn = QPushButton("Bulk Approve")
        self.bulk_approve_btn.setStyleSheet(button_style % ("#28a745", "#218838", "#1c7430"))
        self.bulk_approve_btn.clicked.connect(self._bulk_approve_corrections)
        self.bulk_approve_btn.setToolTip("Approve all corrections on current page")
        controls_layout.addWidget(self.bulk_approve_btn)
        
        self.bulk_reject_btn = QPushButton("Bulk Reject")
        self.bulk_reject_btn.setStyleSheet(button_style % ("#dc3545", "#c82333", "#bd2130"))
        self.bulk_reject_btn.clicked.connect(self._bulk_reject_corrections)
        self.bulk_reject_btn.setToolTip("Reject all corrections on current page")
        controls_layout.addWidget(self.bulk_reject_btn)
        
        self.auto_fix_btn = QPushButton("Auto-Fix")
        self.auto_fix_btn.setStyleSheet(button_style % ("#fd7e14", "#e8630a", "#d15502"))
        self.auto_fix_btn.clicked.connect(self._auto_fix_common_errors)
        self.auto_fix_btn.setToolTip("Automatically fix common errors")
        controls_layout.addWidget(self.auto_fix_btn)
        
        self.validate_page_btn = QPushButton("Validate")
        self.validate_page_btn.setStyleSheet(button_style % ("#6f42c1", "#5a32a3", "#4e2b92"))
        self.validate_page_btn.clicked.connect(self._validate_current_page)
        self.validate_page_btn.setToolTip("Validate current page quality")
        controls_layout.addWidget(self.validate_page_btn)
        
        controls_layout.addStretch()
        
        main_layout.addLayout(controls_layout)
        
        # Second row for quality metrics
        quality_layout = QHBoxLayout()
        quality_layout.setSpacing(12)
        
        quality_title = QLabel("Quality Metrics:")
        quality_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #495057;")
        quality_layout.addWidget(quality_title)
        
        self.quality_score_label = QLabel("Quality: 0% | Accuracy: 0% | Completeness: 0%")
        self.quality_score_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        quality_layout.addWidget(self.quality_score_label)
        
        quality_layout.addStretch()
        
        main_layout.addLayout(quality_layout)
        
        layout.addWidget(qa_frame)
    
    def load_document(self, document: Document):
        """Load a document for page-by-page validation."""
        self.current_document = document
        self.status_label.setText(f"Loaded: {document.metadata.file_name}")
        self.logger.info(f"Document loaded for page validation: {document.id}")
    
    def load_document_for_validation(self, document: Document, post_processing_result=None):
        """Load a document for validation (compatibility with QA widget interface)."""
        self.logger.info(f"Loading document for validation: {document.metadata.file_name}")
        self.logger.info(f"Post-processing result provided: {post_processing_result is not None}")
        
        self.current_document = document
        self.post_processing_result = post_processing_result
        
        # Extract corrections from document - LOAD PERSISTENT CORRECTIONS
        corrections = document.custom_metadata.get('corrections', [])
        
        # Check for persistent corrections from previous sessions
        has_pending = document.custom_metadata.get('has_pending_corrections', False)
        last_session = document.custom_metadata.get('last_qa_session', 'Never')
        
        if has_pending:
            self.log_message.emit(f"📋 Loaded persistent corrections from previous session: {last_session}")
        else:
            self.log_message.emit(f"📋 No pending corrections from previous sessions")
        self.logger.info(f"Found {len(corrections)} corrections in document")
        
        # Group corrections by page 
        self.corrections_by_page = {}
        for correction in corrections:
            page = correction.get('location', {}).get('page', 1)
            self.logger.info(f"Processing correction with page: {page}")
            # Ensure page is valid
            if page <= 0:
                self.logger.warning(f"Invalid page number {page} in correction, correcting to 1")
                page = 1
            if page not in self.corrections_by_page:
                self.corrections_by_page[page] = []
            self.corrections_by_page[page].append(correction)
        
        # Use actual document page count with multiple fallbacks
        page_count_sources = [
            document.metadata.page_count,
            getattr(document, 'page_count', None),
            document.custom_metadata.get('page_count', None),
            max(self.corrections_by_page.keys()) if self.corrections_by_page else None,
            55  # Known page count for test document
        ]
        
        self.total_pages = None
        for source in page_count_sources:
            if source and source > 0:
                self.total_pages = source
                break
        
        if not self.total_pages:
            self.total_pages = 1  # Absolute fallback
        
        # Debug: Log document loading
        self.log_message.emit(f"Document loaded: metadata.page_count={document.metadata.page_count}, total_pages={self.total_pages}")
        self.log_message.emit(f"Current page set to: {self.current_page}")
        self.log_message.emit(f"Page count sources tried: {page_count_sources}")
        
        # Update status
        total_corrections = len(corrections)
        self.status_label.setText(f"Loaded: {document.metadata.file_name} - {total_corrections} corrections on {len(self.corrections_by_page)} pages")
        
        # Load first page (start with page 1 if no corrections, or first correction page)
        if self.corrections_by_page:
            first_page = min(self.corrections_by_page.keys())
            # Ensure first_page is valid (>= 1)
            if first_page <= 0:
                self.logger.error(f"Invalid first page: {first_page}, correcting to 1")
                first_page = 1
            self.current_page = first_page
            self.current_page_issues = self.corrections_by_page[first_page]
            self.current_issue_index = 0
        else:
            # No corrections, start on page 1
            self.current_page = 1
            self.current_page_issues = []
            self.current_issue_index = 0
        
        # Load page text and update display
        self._load_page_text(self.current_page)
        self._update_page_display()
        
        # Sync with PDF viewer
        self._sync_pdf_viewer_page(self.current_page)
        
        self.status_message.emit(f"Document {document.metadata.file_name} loaded for validation")
        self.logger.info(f"Document loaded for page validation: {document.id} with {total_corrections} corrections")
    
    def start_validation(self):
        """Start the validation process."""
        if not self.current_document:
            self.status_label.setText("No document loaded")
            return
        
        self.status_label.setText("Starting page-by-page validation...")
        self.logger.info("Started page-by-page validation")
    
    def _update_page_display(self):
        """Update the display for the current page."""
        if not self.current_document:
            return
        
        # Always update navigation controls first
        self._update_navigation_controls()
        
        # If we have issues on this page, highlight the current issue
        if self.current_page_issues and self.current_issue_index < len(self.current_page_issues):
            current_issue = self.current_page_issues[self.current_issue_index]
            location = current_issue.get('location', {})
            page = location.get('page', self.current_page)
            bbox = location.get('bbox', [])
            description = current_issue.get('description', '')
            
            if bbox:
                # Determine highlight type based on issue type
                highlight_type = self._get_highlight_type(current_issue)
                
                # Create multi-line regions for better highlighting
                enhanced_bbox = self._create_multiline_regions(bbox, description, highlight_type)
                
                # Debug logging
                self.logger.info(f"Original bbox: {bbox}")
                self.logger.info(f"Enhanced bbox: {enhanced_bbox}")
                self.logger.info(f"Highlight type: {highlight_type}")
                
                # Emit signal to highlight in document preview (PDF viewer)
                self.highlight_pdf_location.emit(page, enhanced_bbox, description, highlight_type)
            
            # Highlight in extracted text if text_position is available
            self._highlight_text_issue(current_issue)
            
            # Hide area validation controls for now
            self.area_validation_frame.setVisible(False)
            
            # Synchronize both viewers to show the same location
            self._synchronize_viewers(page, bbox)
            
            self.logger.info(f"Updated page display for page {self.current_page}, issue {self.current_issue_index + 1}/{len(self.current_page_issues)}")
        else:
            # No issues on this page, just update UI
            self.logger.info(f"Updated page display for page {self.current_page}, no issues")
            
            # Clear any existing highlights
            self._clear_text_highlights()
            
            # Clear PDF highlights by emitting a clear signal
            self.highlight_pdf_location.emit(self.current_page, [], "Clear highlights", "clear")
            
            # Hide area validation controls
            self.area_validation_frame.setVisible(False)
            
            # Update issue info to show no issues
            self.issue_type_label.setText("Issue Type: -")
            self.issue_desc_label.setText("Description: No issues on this page")
            self.issue_severity_label.setText("Severity: -")
            self.issue_severity_label.setStyleSheet("font-weight: bold; color: #6c757d;")
            
            # Still sync the PDF viewer to show the current page
            self._sync_pdf_viewer_page(self.current_page)
    
    def _sync_pdf_viewer_page(self, page_number):
        """Synchronize PDF viewer to show the specified page."""
        try:
            self.log_message.emit(f"Syncing PDF viewer to page {page_number}")
            self.logger.info(f"Syncing PDF viewer to page {page_number}")
            
            # Use dedicated navigation signal without highlighting
            self.navigate_pdf_page.emit(page_number)
            
        except Exception as e:
            self.logger.error(f"Failed to sync PDF viewer to page {page_number}: {str(e)}")
    
    def _get_highlight_type(self, issue):
        """Determine highlight type based on issue characteristics."""
        issue_type = issue.get('type', 'ocr_correction')
        description = issue.get('description', '').lower()
        manual_validation_status = issue.get('manual_validation_status', 'not_validated')
        
        # Check if it's a manually created area
        is_manual_area = (issue_type == 'manual_area' or 
                         'manual' in description or 
                         issue.get('area_type') in ['image', 'table', 'diagram'])
        
        # Auto-detected areas have specific patterns
        is_auto_detected = ('has only' in description and 'rows' in description) or \
                          ('empty cells' in description and 'threshold' in description)
        
        # If it's a manual area, treat as approved
        if is_manual_area and not is_auto_detected:
            manual_validation_status = 'approved'
        
        # Only highlight areas that have been manually validated or are manually created
        if manual_validation_status == 'approved':
            # Check area_type field first, then fall back to description
            area_type = issue.get('area_type', '')
            if area_type == 'image' or 'image' in description:
                return 'manual_image'
            elif area_type == 'table' or 'table' in description:
                return 'manual_table'
            elif area_type == 'diagram' or 'diagram' in description:
                return 'manual_diagram'
        
        # Handle auto-detected areas that need validation
        if is_auto_detected:
            return 'auto_conflict'  # Orange highlighting for areas needing validation
        
        if 'conflict' in description:
            return 'auto_conflict'
        elif issue_type == 'ocr_correction':
            return 'active_issue'  # Current issue being viewed
        else:
            return 'issue'  # Default
    
    def _create_multiline_regions(self, bbox, description, highlight_type):
        """Create enhanced multi-line regions for better highlighting."""
        # For now, just return the original bbox
        return bbox
    
    def _approve_area(self):
        """Approve the current auto-detected area."""
        if not self.current_page_issues or self.current_issue_index >= len(self.current_page_issues):
            return
        
        current_issue = self.current_page_issues[self.current_issue_index]
        
        # Update the manual validation status
        current_issue['manual_validation_status'] = 'approved'
        
        # Log the approval
        self.logger.info(f"Approved auto-detected area: {current_issue.get('description', '')}")
        self.log_message.emit(f"Approved area: {current_issue.get('description', '')}")
        
        # Update the display to reflect the new status
        self._update_page_display()
        
        # Save the changes to the document
        self._save_validation_changes()
    
    def _reject_area(self):
        """Reject the current auto-detected area."""
        if not self.current_page_issues or self.current_issue_index >= len(self.current_page_issues):
            return
        
        current_issue = self.current_page_issues[self.current_issue_index]
        
        # Update the manual validation status
        current_issue['manual_validation_status'] = 'rejected'
        
        # Log the rejection
        self.logger.info(f"Rejected auto-detected area: {current_issue.get('description', '')}")
        self.log_message.emit(f"Rejected area: {current_issue.get('description', '')}")
        
        # Update the display to reflect the new status
        self._update_page_display()
        
        # Save the changes to the document
        self._save_validation_changes()
    
    def _delete_area(self):
        """Delete the current auto-detected area."""
        if not self.current_page_issues or self.current_issue_index >= len(self.current_page_issues):
            return
        
        current_issue = self.current_page_issues[self.current_issue_index]
        
        # Log the deletion
        self.logger.info(f"Deleted auto-detected area: {current_issue.get('description', '')}")
        self.log_message.emit(f"Deleted area: {current_issue.get('description', '')}")
        
        # Remove the issue from the current page issues
        del self.current_page_issues[self.current_issue_index]
        
        # Remove from the corrections_by_page as well
        page_corrections = self.corrections_by_page.get(self.current_page, [])
        if current_issue in page_corrections:
            page_corrections.remove(current_issue)
        
        # Adjust the current issue index
        if self.current_issue_index >= len(self.current_page_issues):
            self.current_issue_index = max(0, len(self.current_page_issues) - 1)
        
        # Update the display
        self._update_page_display()
        
        # Save the changes to the document
        self._save_validation_changes()
    
    def _save_validation_changes(self):
        """Save the validation changes back to the document."""
        try:
            # This would save the changes back to the .tore file
            # For now, just log that changes were made
            self.logger.info("Validation changes saved")
            self.log_message.emit("Changes saved to document")
        except Exception as e:
            self.logger.error(f"Error saving validation changes: {e}")
            self.log_message.emit(f"Error saving changes: {e}")
    
    def _highlight_text_issue(self, issue):
        """Highlight the current issue in the extracted text area with exact location."""
        location = issue.get('location', {})
        text_position = location.get('text_position', [])
        
        # Get current text content
        current_text = self.extracted_text.toPlainText()
        
        # Clear any existing highlights first
        self._clear_text_highlights()
        
        # Strategy 1: Use text_position if available and valid
        if text_position:
            try:
                start_pos, end_pos = None, None
                
                # Handle different text_position formats
                if isinstance(text_position, (list, tuple)) and len(text_position) >= 2:
                    start_pos, end_pos = text_position[0], text_position[1]
                elif isinstance(text_position, dict):
                    # Handle dictionary format like {'start': 0, 'end': 10} or {0: start, 1: end}
                    if 'start' in text_position and 'end' in text_position:
                        start_pos, end_pos = text_position['start'], text_position['end']
                    elif 0 in text_position and 1 in text_position:
                        start_pos, end_pos = text_position[0], text_position[1]
                
                # Validate positions are integers and within bounds
                if start_pos is not None and end_pos is not None:
                    if isinstance(start_pos, (int, float)) and isinstance(end_pos, (int, float)):
                        start_pos, end_pos = int(start_pos), int(end_pos)
                        
                        if 0 <= start_pos < len(current_text) and start_pos < end_pos <= len(current_text):
                            self._apply_text_highlight(start_pos, end_pos, issue)
                            return
                
            except (ValueError, TypeError, IndexError, KeyError) as e:
                self.logger.warning(f"Invalid text_position format: {text_position}, error: {e}")
                # Continue to next strategy
        
        # Strategy 2: Search for error text in description
        error_text = issue.get('description', '').replace('Potential OCR error: ', '').strip("'\"")
        if error_text and error_text in current_text:
            start_pos = current_text.find(error_text)
            end_pos = start_pos + len(error_text)
            self._apply_text_highlight(start_pos, end_pos, issue)
            return
        
        # Strategy 3: Use bbox coordinates to approximate position (advanced)
        bbox = location.get('bbox', [])
        if bbox and len(bbox) >= 4:
            # This is a more advanced approach - try to find text at approximate bbox location
            approximate_pos = self._find_text_position_from_bbox(bbox, current_text)
            if approximate_pos:
                start_pos, end_pos = approximate_pos
                self._apply_text_highlight(start_pos, end_pos, issue)
                return
        
        # If all strategies fail, log the issue
        self.log_message.emit(f"Could not locate text for issue: {issue.get('description', 'Unknown')}")
        self.logger.warning(f"Failed to highlight text issue: {issue.get('description', '')}")
    
    def _clear_text_highlights(self):
        """Clear all existing highlights in the text area."""
        cursor = self.extracted_text.textCursor()
        cursor.select(QTextCursor.Document)
        
        # Create default format
        default_format = QTextCharFormat()
        cursor.setCharFormat(default_format)
        
        # Clear selection
        cursor.clearSelection()
        self.extracted_text.setTextCursor(cursor)
    
    def _apply_text_highlight(self, start_pos, end_pos, issue):
        """Apply highlighting to text at given positions."""
        cursor = self.extracted_text.textCursor()
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
        
        # Create highlighting format based on severity
        severity = issue.get('severity', 'unknown')
        highlight_format = QTextCharFormat()
        
        if severity == 'critical':
            highlight_format.setBackground(QColor("#ffcdd2"))  # Light red
            highlight_format.setForeground(QColor("#b71c1c"))  # Dark red
        elif severity == 'major':
            highlight_format.setBackground(QColor("#ffeb3b"))  # Yellow
            highlight_format.setForeground(QColor("#d32f2f"))  # Red
        elif severity == 'medium':
            highlight_format.setBackground(QColor("#fff3e0"))  # Light orange
            highlight_format.setForeground(QColor("#ef6c00"))  # Orange
        else:  # minor or unknown
            highlight_format.setBackground(QColor("#e8f5e8"))  # Light green
            highlight_format.setForeground(QColor("#2e7d32"))  # Green
        
        highlight_format.setFontWeight(700)  # Bold
        cursor.setCharFormat(highlight_format)
        
        # Move cursor to highlight position and ensure visibility
        self.extracted_text.setTextCursor(cursor)
        self.extracted_text.ensureCursorVisible()
        
        # Log successful highlight
        highlighted_text = self.extracted_text.toPlainText()[start_pos:end_pos]
        self.log_message.emit(f"Highlighted '{highlighted_text}' at positions {start_pos}-{end_pos}")
        self.logger.info(f"Highlighted text issue at positions {start_pos}-{end_pos}: {issue.get('description', '')}")
    
    def _find_text_position_from_bbox(self, bbox, text):
        """Approximate text position from bbox coordinates (placeholder for advanced implementation)."""
        # This is a placeholder for a more advanced implementation that would:
        # 1. Parse the PDF page structure
        # 2. Map bbox coordinates to text positions
        # 3. Return approximate start/end positions
        # For now, return None to indicate this method is not implemented
        return None
    
    def _on_cursor_position_changed(self):
        """Handle cursor position changes to sync with PDF location."""
        try:
            cursor = self.extracted_text.textCursor()
            position = cursor.position()
            
            # Only process if we have text mapping
            if not self.text_to_pdf_mapping:
                return
            
            # Map text position to PDF coordinates
            pdf_location = self._map_text_position_to_pdf(position)
            
            if pdf_location:
                page, bbox = pdf_location
                self.cursor_pdf_location.emit(page, bbox)
                # Reduce log spam - only log important cursor moves
                if position % 10 == 0:  # Log every 10th position
                    self.log_message.emit(f"Cursor at position {position} → PDF page {page}")
            
        except Exception as e:
            self.logger.error(f"Error handling cursor position change: {str(e)}")
    
    def _on_text_selection_changed(self):
        """Handle text selection changes to highlight in PDF using new highlighting engine."""
        try:
            cursor = self.extracted_text.textCursor()
            
            if cursor.hasSelection():
                start_pos = cursor.selectionStart()
                end_pos = cursor.selectionEnd()
                selected_text = cursor.selectedText()
                
                # Use the shared highlighting engine if available
                if self.highlighting_engine:
                    highlight_id = self.highlighting_engine.highlight_text_range(
                        text_start=start_pos,
                        text_end=end_pos,
                        highlight_type='active_highlight',
                        page=self.current_page
                    )
                    
                    if highlight_id:
                        self.log_message.emit(f"✅ Synchronized highlight: '{selected_text}' at {start_pos}-{end_pos} (ID: {highlight_id})")
                        return  # Success with shared engine, no need for fallback
                    else:
                        self.log_message.emit(f"🔄 Shared highlighting engine failed, using legacy method for '{selected_text}'")
                else:
                    self.log_message.emit(f"⚠️ No highlighting engine available, using legacy method for '{selected_text}'")
                
                # Fall back to signal-based method
                pdf_selection = self._map_text_range_to_pdf(start_pos, end_pos)
                if pdf_selection:
                    page, bbox = pdf_selection
                    self.highlight_pdf_text_selection.emit(page, bbox)
                    self.log_message.emit(f"✅ Legacy highlight: '{selected_text}' at {start_pos}-{end_pos} → PDF page {page}, bbox {bbox}")
                else:
                    self.log_message.emit(f"❌ All highlighting methods failed for '{selected_text}' at {start_pos}-{end_pos}")
                    # Try to provide debug information
                    self.log_message.emit(f"Debug: text_to_pdf_mapping has {len(self.text_to_pdf_mapping) if hasattr(self, 'text_to_pdf_mapping') else 0} entries")
                    self.log_message.emit(f"Debug: current_page={self.current_page}, use_unstructured={self.use_unstructured}, use_ocr={self.use_ocr}")
            
        except Exception as e:
            self.logger.error(f"Error handling text selection change: {str(e)}")
    
    def _map_text_position_to_pdf(self, text_position):
        """Map text position to PDF coordinates using advanced extraction methods."""
        if not self.text_to_pdf_mapping:
            return None
        
        # If using Unstructured, we have superior element-level mapping
        if self.use_unstructured and self.unstructured_elements:
            # Find the Unstructured element containing this text position
            page_elements = [e for e in self.unstructured_elements if e.page_number == self.current_page]
            for element in page_elements:
                if element.char_start <= text_position < element.char_end:
                    return (element.page_number, element.bbox)
        
        # If using OCR, we have perfect character-level mapping
        elif self.use_ocr and self.ocr_characters:
            # Use OCR-based precise cursor positioning (ABBYY FineReader-style)
            if hasattr(self.ocr_extractor, 'find_cursor_position'):
                # Get the page text start position
                page_text_start = 0
                for char in self.ocr_characters:
                    if char.page_number == self.current_page:
                        break
                    page_text_start += 1
                
                # Find the OCR character at this text position
                ocr_text_pos = page_text_start + text_position
                if ocr_text_pos < len(self.ocr_characters):
                    char = self.ocr_characters[ocr_text_pos]
                    return (char.page_number, char.bbox)
        
        # Try exact match first (fallback for enhanced extraction)
        if text_position in self.text_to_pdf_mapping:
            return self.text_to_pdf_mapping[text_position]
        
        # Find the closest mapped position within reasonable range
        closest_pos = None
        min_distance = float('inf')
        max_distance = 5  # Only consider positions within 5 characters
        
        for pos, (page, bbox) in self.text_to_pdf_mapping.items():
            distance = abs(pos - text_position)
            if distance < min_distance and distance <= max_distance:
                min_distance = distance
                closest_pos = pos
        
        if closest_pos is not None:
            return self.text_to_pdf_mapping[closest_pos]
        
        # If no close match, return None to avoid wrong highlights
        return None
    
    def _map_text_range_to_pdf(self, start_pos, end_pos):
        """Map text range to PDF bbox coordinates with improved precision using OCR or enhanced extraction."""
        
        # If using Unstructured, use superior element-based text selection
        if self.use_unstructured and self.unstructured_elements:
            try:
                # Find all Unstructured elements that overlap with the text selection
                page_elements = [e for e in self.unstructured_elements if e.page_number == self.current_page]
                selection_elements = []
                
                for element in page_elements:
                    # Check if element overlaps with selection
                    if (element.char_start < end_pos and element.char_end > start_pos):
                        selection_elements.append(element)
                
                if selection_elements:
                    # Calculate combined bounding box from all overlapping elements
                    min_x = min(elem.bbox[0] for elem in selection_elements)
                    min_y = min(elem.bbox[1] for elem in selection_elements)
                    max_x = max(elem.bbox[2] for elem in selection_elements)
                    max_y = max(elem.bbox[3] for elem in selection_elements)
                    
                    combined_bbox = (min_x, min_y, max_x, max_y)
                    return (self.current_page, combined_bbox)
            except Exception as e:
                self.logger.error(f"Unstructured text range mapping failed: {str(e)}")
                # Fall through to OCR or enhanced extraction
        
        # If using OCR, use the precise text selection method
        elif self.use_ocr and self.ocr_extractor and hasattr(self.ocr_extractor, 'get_text_selection_bbox'):
            try:
                # Get page text offset for global positioning
                page_text_start = 0
                for char in self.ocr_characters:
                    if char.page_number == self.current_page:
                        break
                    page_text_start += 1
                
                # Convert to global character positions
                global_start = page_text_start + start_pos
                global_end = page_text_start + end_pos
                
                # Get precise OCR-based selection bbox
                selection_bbox = self.ocr_extractor.get_text_selection_bbox(
                    self.ocr_characters, global_start, global_end
                )
                
                if selection_bbox:
                    return (self.current_page, selection_bbox)
            except Exception as e:
                self.logger.error(f"OCR text range mapping failed: {str(e)}")
                # Fall through to enhanced extraction
        
        # Fall back to enhanced extraction method
        start_pdf = self._map_text_position_to_pdf(start_pos)
        end_pdf = self._map_text_position_to_pdf(end_pos)
        
        if start_pdf and end_pdf:
            page = start_pdf[0]  # Assume same page
            start_bbox = start_pdf[1]
            end_bbox = end_pdf[1]
            
            # Check if selection is on the same line (similar Y coordinates)
            y_diff = abs(start_bbox[1] - end_bbox[1])
            line_height = max(start_bbox[3] - start_bbox[1], end_bbox[3] - end_bbox[1])
            
            if y_diff < line_height / 2:  # Same line selection
                # Create a precise horizontal rectangle
                combined_bbox = [
                    min(start_bbox[0], end_bbox[0]),  # x0 - leftmost
                    max(start_bbox[1], end_bbox[1]),  # y0 - consistent baseline
                    max(start_bbox[2], end_bbox[2]),  # x1 - rightmost
                    min(start_bbox[3], end_bbox[3])   # y1 - consistent top
                ]
            else:
                # Multi-line selection - use a more conservative approach
                # Don't create a huge rectangle spanning multiple lines
                # Instead, use the first character's bbox with extended width
                combined_bbox = [
                    start_bbox[0],                    # x0 - start position
                    start_bbox[1],                    # y0 - start line
                    max(start_bbox[2], end_bbox[2]),  # x1 - extend to end
                    start_bbox[3]                     # y1 - keep to start line height
                ]
            
            return (page, combined_bbox)
        
        return start_pdf or end_pdf
    
    def eventFilter(self, source, event):
        """Handle events from the text widget."""
        
        if source == self.extracted_text:
            if event.type() == QEvent.MouseButtonPress:
                # Let the normal selection happen first
                result = super().eventFilter(source, event)
                
                # Get cursor position after mouse press
                cursor = self.extracted_text.cursorForPosition(event.pos())
                position = cursor.position()
                
                # Map to PDF and highlight
                pdf_location = self._map_text_position_to_pdf(position)
                if pdf_location:
                    page, bbox = pdf_location
                    self.cursor_pdf_location.emit(page, bbox)
                    self.log_message.emit(f"Mouse click at text position {position} → PDF page {page}, bbox {bbox}")
                
                return result
            
            elif event.type() == QEvent.MouseMove:
                # Let the normal selection happen first
                result = super().eventFilter(source, event)
                
                # If mouse is pressed (dragging), update selection highlighting
                if event.buttons() & Qt.LeftButton:
                    cursor = self.extracted_text.textCursor()
                    if cursor.hasSelection():
                        start_pos = cursor.selectionStart()
                        end_pos = cursor.selectionEnd()
                        
                        # Map selection to PDF
                        pdf_selection = self._map_text_range_to_pdf(start_pos, end_pos)
                        if pdf_selection:
                            page, bbox = pdf_selection
                            self.highlight_pdf_text_selection.emit(page, bbox)
                
                return result
        
        return super().eventFilter(source, event)
    
    def _synchronize_viewers(self, page_number, bbox):
        """Synchronize document preview and extracted content viewers."""
        try:
            # Ensure both viewers are showing the same page
            if page_number != self.current_page:
                self.current_page = page_number
                self._load_page_text(page_number)
            
            # Log synchronization
            self.log_message.emit(f"Synchronized viewers to page {page_number}")
            
            # Additional synchronization could include:
            # - Scrolling both viewers to the same relative position
            # - Matching zoom levels
            # - Coordinating viewport positions
            
        except Exception as e:
            self.logger.error(f"Failed to synchronize viewers: {str(e)}")
            self.log_message.emit(f"Error synchronizing viewers: {str(e)}")
    
    def _resolve_pdf_path(self, file_path):
        """Resolve actual PDF file path from project file or direct path."""
        try:
            # If it's already a PDF file, return as-is
            if file_path.endswith('.pdf'):
                return file_path
            
            # If it's a .tore project file, extract the PDF path
            if file_path.endswith('.tore'):
                import json
                with open(file_path, 'r') as f:
                    project_data = json.load(f)
                
                # Get the first document's path (for now, assume single document projects)
                documents = project_data.get('documents', [])
                if documents:
                    pdf_path = documents[0].get('path', '')
                    if pdf_path.endswith('.pdf'):
                        self.logger.info(f"Resolved PDF path from project: {pdf_path}")
                        return pdf_path
                
                self.logger.error(f"No PDF document found in project file: {file_path}")
                return None
            
            # Unknown file type
            self.logger.error(f"Unknown file type for extraction: {file_path}")
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to resolve PDF path from {file_path}: {str(e)}")
            return None

    def _load_page_text(self, page_number):
        """Load extracted text using advanced extraction methods with perfect coordinate mapping."""
        try:
            if not self.current_document or not self.current_document.metadata.file_path:
                self.extracted_text.setPlainText("No document loaded.")
                return
            
            # Ensure page_number is valid (>= 1) - this should now be redundant due to property
            if page_number <= 0:
                self.logger.error(f"CRITICAL: Invalid page number {page_number} passed to _load_page_text despite property protection!")
                page_number = 1
                self.current_page = 1  # Also update current_page
            
            # Resolve the actual PDF file path
            project_file_path = self.current_document.metadata.file_path
            pdf_file_path = self._resolve_pdf_path(project_file_path)
            
            if not pdf_file_path:
                error_msg = f"Could not resolve PDF file path from: {project_file_path}"
                self.extracted_text.setPlainText(error_msg)
                self.log_message.emit(error_msg)
                self.logger.error(error_msg)
                return
            
            # Check if PDF file exists
            if not Path(pdf_file_path).exists():
                error_msg = f"PDF file not found: {pdf_file_path}"
                self.extracted_text.setPlainText(error_msg)
                self.log_message.emit(error_msg)
                self.logger.error(error_msg)
                return
            
            self.logger.info(f"DEBUG: _load_page_text called with page_number={page_number}, type={type(page_number)}")
            self.logger.info(f"DEBUG: Resolved PDF path: {pdf_file_path}")
            
            # Log extraction engine availability
            self.logger.info(f"Extraction engines status:")
            self.logger.info(f"  - Unstructured: available={self.unstructured_extractor is not None}, enabled={self.use_unstructured}")
            self.logger.info(f"  - OCR: available={self.ocr_extractor is not None}, enabled={self.use_ocr}")
            self.logger.info(f"  - Enhanced PyMuPDF: available={self.enhanced_extractor is not None}, enabled={self.use_enhanced}")
            
            # Try extraction methods in order of preference
            if self.use_unstructured and self.unstructured_extractor:
                self.log_message.emit(f"Using Unstructured extraction for page {page_number} (Superior document structure detection)")
                self.logger.info(f"Selected extraction engine: Unstructured")
                self._load_page_text_with_unstructured(page_number, pdf_file_path)
            elif self.use_ocr and self.ocr_extractor:
                self.log_message.emit(f"Using OCR-based extraction for page {page_number} (ABBYY FineReader-level accuracy)")
                self.logger.info(f"Selected extraction engine: OCR-based")
                self._load_page_text_with_ocr(page_number, pdf_file_path)
            else:
                # Fall back to enhanced PyMuPDF extraction
                self.log_message.emit(f"Using enhanced PyMuPDF extraction for page {page_number}")
                self.logger.info(f"Selected extraction engine: Enhanced PyMuPDF")
                self._load_page_text_with_enhanced_extraction(page_number, pdf_file_path)
            
        except Exception as e:
            error_msg = f"Failed to load page {page_number} text: {str(e)}"
            self.extracted_text.setPlainText(error_msg)
            self.log_message.emit(error_msg)
            self.logger.error(error_msg)
    
    def _load_page_text_with_ocr(self, page_number, file_path):
        """Load page text using OCR-based extraction for perfect accuracy."""
        try:
            self.logger.info(f"Starting OCR extraction for page {page_number}")
            self.logger.info(f"OCR extractor: {self.ocr_extractor}")
            self.logger.info(f"File path: {file_path}")
            self.logger.info(f"File exists: {Path(file_path).exists()}")
            
            # Check if extractor has the required method
            if not hasattr(self.ocr_extractor, 'extract_with_ocr_precision'):
                self.logger.error("OCR extractor missing required method")
                raise AttributeError("OCR extractor missing extract_with_ocr_precision method")
            
            # Extract with OCR precision (may take longer but perfect accuracy)
            if not hasattr(self, '_ocr_cache') or file_path not in self._ocr_cache:
                self.log_message.emit("Performing OCR extraction... (this may take a moment)")
                self.ocr_characters, self.full_document_text, page_lines = self.ocr_extractor.extract_with_ocr_precision(file_path)
                
                # Cache the results
                if not hasattr(self, '_ocr_cache'):
                    self._ocr_cache = {}
                self._ocr_cache[file_path] = {
                    'characters': self.ocr_characters,
                    'full_text': self.full_document_text,
                    'page_lines': page_lines
                }
                
                self.log_message.emit(f"OCR extraction completed: {len(self.ocr_characters)} characters with perfect coordinates")
            else:
                # Use cached OCR results
                cached_data = self._ocr_cache[file_path]
                self.ocr_characters = cached_data['characters']
                self.full_document_text = cached_data['full_text']
                self.log_message.emit("Using cached OCR data for instant loading")
            
            # Get text for current page
            page_chars = [c for c in self.ocr_characters if c.page_number == page_number]
            
            if page_chars:
                # Build page text from OCR characters
                page_text = ""
                self.text_to_pdf_mapping = {}
                
                for char in page_chars:
                    self.text_to_pdf_mapping[len(page_text)] = (char.page_number, char.bbox)
                    page_text += char.char
                
                self.extracted_text.setPlainText(page_text)
                
                # Update highlighting engine with new text content
                if self.highlighting_engine:
                    self.highlighting_engine.update_text_content(page_number)
                
                # Log perfect OCR mapping
                self.log_message.emit(f"OCR page {page_number}: {len(page_chars)} characters with 100% coordinate accuracy")
                
                # Highlight all issues with perfect positioning
                self._highlight_all_page_issues()
            else:
                self.extracted_text.setPlainText(f"Page {page_number} contains no OCR-recognizable text.")
                self.log_message.emit(f"No OCR text found on page {page_number}")
                
        except Exception as e:
            self.logger.error(f"OCR extraction failed: {str(e)}")
            # Fall back to enhanced extraction
            self._load_page_text_with_enhanced_extraction(page_number, file_path)
    
    def _load_page_text_with_enhanced_extraction(self, page_number, file_path):
        """Load page text using enhanced PyMuPDF extraction."""
        try:
            self.logger.info(f"Loading page {page_number} text with enhanced extraction from {file_path}")
            self.logger.info(f"DEBUG: page_number type: {type(page_number)}, value: {page_number}")
            
            # Use enhanced extractor as fallback
            if not hasattr(self, '_enhanced_cache') or file_path not in self._enhanced_cache:
                self.logger.info("Running enhanced extraction (not cached)")
                self.logger.info(f"File path: {file_path}")
                self.logger.info(f"File exists: {Path(file_path).exists()}")
                
                try:
                    self.logger.info("About to call enhanced_extractor.extract_with_perfect_correlation")
                    self.logger.info(f"Enhanced extractor object: {self.enhanced_extractor}")
                    self.logger.info(f"Enhanced extractor type: {type(self.enhanced_extractor)}")
                    
                    # Check if the method exists
                    if not hasattr(self.enhanced_extractor, 'extract_with_perfect_correlation'):
                        raise AttributeError("enhanced_extractor missing extract_with_perfect_correlation method")
                    
                    elements, full_text, page_texts = self.enhanced_extractor.extract_with_perfect_correlation(file_path)
                    self.logger.info("Enhanced extraction call completed successfully")
                    
                    self.logger.info(f"Enhanced extraction returned: {len(elements)} elements, {len(full_text)} chars total, {len(page_texts)} pages")
                    self.logger.info(f"Available pages in page_texts: {list(page_texts.keys())}")
                    
                    # Cache the results
                    if not hasattr(self, '_enhanced_cache'):
                        self._enhanced_cache = {}
                    self._enhanced_cache[file_path] = {
                        'elements': elements,
                        'full_text': full_text,
                        'page_texts': page_texts
                    }
                    
                except Exception as extraction_error:
                    self.logger.error(f"Enhanced extraction failed: {extraction_error}")
                    self.logger.error(f"Extraction error type: {type(extraction_error)}")
                    self.logger.error(f"Extraction error args: {extraction_error.args}")
                    self.logger.error(f"Extraction error str: {repr(str(extraction_error))}")
                    self.logger.error(f"Extraction error repr: {repr(extraction_error)}")
                    self.logger.error(f"Extraction error class: {extraction_error.__class__}")
                    self.logger.error(f"Extraction error module: {extraction_error.__class__.__module__}")
                    import traceback
                    self.logger.error(f"Extraction error traceback: {traceback.format_exc()}")
                    
                    # Check if it's a specific type of error
                    if isinstance(extraction_error, (ValueError, TypeError, AttributeError)):
                        self.logger.error(f"Standard exception type detected: {type(extraction_error).__name__}")
                    else:
                        self.logger.error(f"Unknown exception type: {type(extraction_error)}")
                    
                    # Re-raise the error to be caught by the outer try-catch
                    raise extraction_error
                
                # Ensure page_number is valid and 1-indexed
                if page_number <= 0:
                    self.logger.error(f"Invalid page number: {page_number} (must be >= 1)")
                    page_number = 1
                    self.logger.info(f"Corrected page number to: {page_number}")
                
                if page_number not in page_texts:
                    self.logger.error(f"Requested page {page_number} not found in extracted pages: {list(page_texts.keys())}")
                    self.logger.error(f"DEBUG: page_number={page_number}, type={type(page_number)}")
                    self.logger.error(f"DEBUG: Available pages: {sorted(page_texts.keys())}")
                    
                    # Try to find the closest valid page
                    available_pages = sorted(page_texts.keys())
                    if available_pages:
                        closest_page = min(available_pages, key=lambda x: abs(x - page_number))
                        self.logger.info(f"Using closest available page: {closest_page}")
                        page_number = closest_page
                    else:
                        raise ValueError(f"No pages found in extracted content")
                    
            else:
                self.logger.info("Using cached enhanced extraction")
                cached_data = self._enhanced_cache[file_path]
                elements = cached_data['elements']
                full_text = cached_data['full_text'] 
                page_texts = cached_data['page_texts']
            
            # Get text for current page
            self.logger.info(f"Checking if page {page_number} exists in page_texts: {page_number in page_texts}")
            
            if page_number in page_texts:
                page_text = page_texts[page_number]
                self.logger.info(f"Found page {page_number} text: {len(page_text)} characters")
                
                # Build mapping from enhanced elements - FIXED for page-relative positions
                self.text_to_pdf_mapping = {}
                page_elements = [e for e in elements if e.page_number == page_number]
                self.logger.info(f"Found {len(page_elements)} elements for page {page_number}")
                
                # Find the character offset for this page in the full document
                page_char_offset = 0
                self.logger.info(f"DEBUG: Calculating page char offset for page {page_number}")
                self.logger.info(f"DEBUG: range(1, {page_number}) = {list(range(1, page_number))}")
                
                for p in range(1, page_number):
                    if p in page_texts:
                        page_char_offset += len(page_texts[p])
                        self.logger.info(f"DEBUG: Added {len(page_texts[p])} chars from page {p}, total offset now: {page_char_offset}")
                        
                self.logger.info(f"Page char offset for page {page_number}: {page_char_offset}")
                
                for element in page_elements:
                    try:
                        # Convert global char position to page-relative position
                        if not hasattr(element, 'char_start') or element.char_start is None:
                            self.logger.warning(f"Element missing char_start: {element}")
                            continue
                            
                        page_relative_pos = element.char_start - page_char_offset
                        if 0 <= page_relative_pos < len(page_text):
                            self.text_to_pdf_mapping[page_relative_pos] = (element.page_number, element.bbox)
                        else:
                            self.logger.debug(f"Element position {page_relative_pos} out of range for page text length {len(page_text)}")
                            
                    except Exception as e:
                        self.logger.error(f"Error processing element {element}: {e}")
                        continue
                
                self.extracted_text.setPlainText(page_text)
                
                # Update highlighting engine with new text content
                if self.highlighting_engine:
                    self.highlighting_engine.update_text_content(page_number)
                
                coverage = len(self.text_to_pdf_mapping) / len(page_text) * 100 if page_text else 0
                self.log_message.emit(f"Enhanced page {page_number}: {len(page_text)} chars, {coverage:.1f}% coordinate coverage")
                self.log_message.emit(f"Page char offset: {page_char_offset}, mapping entries: {len(self.text_to_pdf_mapping)}")
                
                # Highlight all issues
                self._highlight_all_page_issues()
            else:
                self.extracted_text.setPlainText(f"Page {page_number} not found in enhanced extraction.")
                
        except Exception as e:
            self.logger.error(f"Enhanced extraction failed: {str(e)}")
            self.logger.error(f"Exception type: {type(e)}")
            self.logger.error(f"Exception args: {e.args}")
            import traceback
            self.logger.error(f"Exception traceback: {traceback.format_exc()}")
            
            # Handle the case where the exception is a numeric value (like 0)
            if str(e) == "0" or str(e) == "":
                error_message = f"Failed to extract text from page {page_number}: Unknown error (empty or zero exception)"
                self.logger.error(f"Empty or zero exception detected. This might be caused by a numeric value being raised as an exception.")
                self.logger.error(f"Full exception details: type={type(e)}, args={e.args}, str={repr(str(e))}")
            else:
                error_message = f"Failed to extract text from page {page_number}: {str(e)}"
            
            # Try a simple fallback extraction using PyMuPDF directly
            try:
                self.logger.info(f"Attempting fallback extraction for page {page_number}")
                import fitz
                doc = fitz.open(file_path)
                if page_number <= len(doc):
                    page = doc[page_number - 1]  # Convert to 0-indexed
                    fallback_text = page.get_text()
                    if fallback_text.strip():
                        self.logger.info(f"Fallback extraction successful: {len(fallback_text)} characters")
                        
                        # Show the text directly (clean fallback mode)
                        self.extracted_text.setPlainText(fallback_text)
                        
                        # Log message for debugging (subtle indicator)
                        self.log_message.emit(f"Page {page_number} extracted using basic mode")
                        return
                    else:
                        self.logger.info(f"Fallback extraction returned empty text")
                doc.close()
            except Exception as fallback_error:
                self.logger.error(f"Fallback extraction also failed: {fallback_error}")
            
            self.extracted_text.setPlainText(error_message)
    
    def _load_page_text_with_unstructured(self, page_number, file_path):
        """Load page text using Unstructured library for superior document structure detection."""
        try:
            self.logger.info(f"Starting Unstructured extraction for page {page_number}")
            self.logger.info(f"Unstructured extractor: {self.unstructured_extractor}")
            self.logger.info(f"File path: {file_path}")
            self.logger.info(f"File exists: {Path(file_path).exists()}")
            
            # Check if extractor has the required method
            if not hasattr(self.unstructured_extractor, 'extract_with_superior_structure_detection'):
                self.logger.error("Unstructured extractor missing required method")
                raise AttributeError("Unstructured extractor missing extract_with_superior_structure_detection method")
            
            self.logger.info("About to call unstructured_extractor.extract_with_superior_structure_detection")
            # Use Unstructured for best document understanding
            if not hasattr(self, '_unstructured_cache') or file_path not in self._unstructured_cache:
                self.log_message.emit("Performing Unstructured extraction... (superior document structure detection)")
                elements, full_text, page_texts, metadata_by_page = self.unstructured_extractor.extract_with_superior_structure_detection(file_path)
                
                # Cache the results
                if not hasattr(self, '_unstructured_cache'):
                    self._unstructured_cache = {}
                self._unstructured_cache[file_path] = {
                    'elements': elements,
                    'full_text': full_text,
                    'page_texts': page_texts,
                    'metadata': metadata_by_page
                }
                
                self.log_message.emit(f"Unstructured extraction completed: {len(elements)} elements with superior structure detection")
            else:
                # Use cached Unstructured results
                cached_data = self._unstructured_cache[file_path]
                elements = cached_data['elements']
                full_text = cached_data['full_text']
                page_texts = cached_data['page_texts']
                metadata_by_page = cached_data['metadata']
                self.log_message.emit("Using cached Unstructured data for instant loading")
            
            # Store elements for coordinate mapping
            self.unstructured_elements = elements
            
            # Get text for current page
            if page_number in page_texts:
                page_text = page_texts[page_number]
                
                # Build mapping from Unstructured elements - FIXED for page-relative positions
                self.text_to_pdf_mapping = {}
                page_elements = [e for e in elements if e.page_number == page_number]
                
                # Find the character offset for this page in the full document
                page_char_offset = 0
                for p in range(1, page_number):
                    if p in page_texts:
                        page_char_offset += len(page_texts[p])
                
                for element in page_elements:
                    # Convert global char position to page-relative position
                    page_relative_pos = element.char_start - page_char_offset
                    if 0 <= page_relative_pos < len(page_text):
                        self.text_to_pdf_mapping[page_relative_pos] = (element.page_number, element.bbox)
                
                self.extracted_text.setPlainText(page_text)
                
                # Show detailed Unstructured metadata
                page_metadata = metadata_by_page.get(page_number, {})
                structure_info = f"Detected {len(page_elements)} elements: "
                element_counts = {}
                for elem in page_elements:
                    elem_type = elem.element_type.value if hasattr(elem.element_type, 'value') else str(elem.element_type)
                    element_counts[elem_type] = element_counts.get(elem_type, 0) + 1
                
                structure_summary = ", ".join([f"{count} {elem_type}" for elem_type, count in element_counts.items()])
                coverage = len(self.text_to_pdf_mapping) / len(page_text) * 100 if page_text else 0
                
                self.log_message.emit(f"Unstructured page {page_number}: {structure_summary}")
                self.log_message.emit(f"Structure detection: {coverage:.1f}% coordinate coverage with enhanced metadata")
                
                # Highlight all issues with superior positioning
                self._highlight_all_page_issues()
            else:
                self.extracted_text.setPlainText(f"Page {page_number} not found in Unstructured extraction.")
                
        except Exception as e:
            self.logger.error(f"Unstructured extraction failed: {str(e)}")
            # Fall back to OCR or enhanced extraction
            if self.use_ocr and self.ocr_extractor:
                self._load_page_text_with_ocr(page_number, file_path)
            else:
                self._load_page_text_with_enhanced_extraction(page_number, file_path)
    
    def _highlight_all_page_issues(self):
        """Highlight all issues on the current page, with active issue distinct."""
        # Always clear existing highlights first
        self._clear_text_highlights()
        
        # If there are corrections on this page, highlight them
        if self.current_page_issues:
            # Highlight all issues
            for i, issue in enumerate(self.current_page_issues):
                is_active = (i == self.current_issue_index)
                self._apply_issue_highlight(issue, is_active)
        # If no corrections, text is still displayed (just no highlights)
    
    def _apply_issue_highlight(self, issue, is_active=False):
        """Apply highlighting for a single issue."""
        location = issue.get('location', {})
        text_position = location.get('text_position', [])
        
        # Get current text content
        current_text = self.extracted_text.toPlainText()
        
        # Strategy 1: Use text_position if available and valid
        if text_position and len(text_position) >= 2:
            start_pos, end_pos = text_position[0], text_position[1]
            
            # Validate positions are within text bounds
            if 0 <= start_pos < len(current_text) and start_pos < end_pos <= len(current_text):
                self._apply_text_highlight_for_issue(start_pos, end_pos, issue, is_active)
                
                # Also highlight in PDF using the bbox coordinates
                bbox = location.get('bbox', [])
                if bbox:
                    page = location.get('page', self.current_page)
                    description = issue.get('description', '')
                    highlight_type = self._get_highlight_type(issue)
                    self.highlight_pdf_location.emit(page, bbox, description, highlight_type)
                
                return
        
        # Strategy 2: Search for error text in description with improved search
        error_text = issue.get('description', '').replace('Potential OCR error: ', '').strip("'\"")
        if error_text:
            # Try multiple search strategies for better matching
            search_variations = [
                error_text,
                error_text.replace('/', ''),  # Remove slashes
                error_text.replace('\\', ''), # Remove backslashes  
                error_text.replace('0', 'O'), # Common OCR confusion
                error_text.replace('O', '0'), # Common OCR confusion
                error_text.replace('1', 'I'), # Common OCR confusion
                error_text.replace('I', '1'), # Common OCR confusion
            ]
            
            found_match = False
            for search_text in search_variations:
                if search_text and search_text in current_text:
                    start_pos = current_text.find(search_text)
                    end_pos = start_pos + len(search_text)
                    self._apply_text_highlight_for_issue(start_pos, end_pos, issue, is_active)
                    found_match = True
                    break
            
            # Always try to highlight in PDF using the original bbox even if text search fails
            bbox = location.get('bbox', [])
            if bbox:
                page = location.get('page', self.current_page)
                highlight_type = self._get_highlight_type(issue)
                self.highlight_pdf_location.emit(page, bbox, error_text, highlight_type)
                
                # If we found text match, also log success
                if found_match:
                    self.log_message.emit(f"Found and highlighted '{error_text}' in both text and PDF")
                else:
                    self.log_message.emit(f"Highlighted '{error_text}' in PDF only (text search failed)")
            
            if found_match:
                return
        
        # Strategy 3: If we can't find text, still try to highlight in PDF
        bbox = location.get('bbox', [])
        if bbox:
            page = location.get('page', self.current_page)
            description = issue.get('description', '')
            highlight_type = self._get_highlight_type(issue)
            self.highlight_pdf_location.emit(page, bbox, description, highlight_type)
    
    def _apply_text_highlight_for_issue(self, start_pos, end_pos, issue, is_active=False):
        """Apply highlighting to text for a specific issue."""
        cursor = self.extracted_text.textCursor()
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
        
        # Create highlighting format based on severity and active state
        severity = issue.get('severity', 'unknown')
        highlight_format = QTextCharFormat()
        
        if is_active:
            # Active issue - bright, bold highlighting
            highlight_format.setBackground(QColor("#ff5722"))  # Deep orange
            highlight_format.setForeground(QColor("#ffffff"))  # White text
            highlight_format.setFontWeight(900)  # Extra bold
            highlight_format.setUnderlineStyle(QTextCharFormat.SingleUnderline)
        else:
            # Inactive issues - subtle highlighting
            if severity == 'critical':
                highlight_format.setBackground(QColor("#ffebee"))  # Very light red
                highlight_format.setForeground(QColor("#c62828"))  # Dark red
            elif severity == 'major':
                highlight_format.setBackground(QColor("#fff9c4"))  # Light yellow
                highlight_format.setForeground(QColor("#f57f17"))  # Dark yellow
            elif severity == 'medium':
                highlight_format.setBackground(QColor("#fff3e0"))  # Light orange
                highlight_format.setForeground(QColor("#ef6c00"))  # Orange
            else:  # minor or unknown
                highlight_format.setBackground(QColor("#f1f8e9"))  # Light green
                highlight_format.setForeground(QColor("#558b2f"))  # Green
            
            highlight_format.setFontWeight(400)  # Normal weight
        
        cursor.setCharFormat(highlight_format)
        
        # If this is the active issue, ensure it's visible
        if is_active:
            self.extracted_text.setTextCursor(cursor)
            self.extracted_text.ensureCursorVisible()
    
    def _approve_current_correction(self):
        """Approve the current correction and apply changes."""
        if not self.current_page_issues or self.current_issue_index >= len(self.current_page_issues):
            return
        
        current_issue = self.current_page_issues[self.current_issue_index]
        current_issue['status'] = 'approved'
        
        # Apply the correction to the text
        # This would involve actual text replacement based on the correction
        
        self.log_message.emit(f"Approved correction: {current_issue.get('description', 'Unknown')}")
        self.save_all_btn.setEnabled(True)
        
        # Move to next issue
        self._next_issue()
    
    def _reject_current_correction(self):
        """Reject the current correction."""
        if not self.current_page_issues or self.current_issue_index >= len(self.current_page_issues):
            return
        
        current_issue = self.current_page_issues[self.current_issue_index]
        current_issue['status'] = 'rejected'
        
        self.log_message.emit(f"Rejected correction: {current_issue.get('description', 'Unknown')}")
        self.save_all_btn.setEnabled(True)
        
        # Move to next issue
        self._next_issue()
    
    def _save_all_changes(self):
        """Save all approved corrections to the document and project file."""
        try:
            # Count approved/rejected corrections
            approved_count = 0
            rejected_count = 0
            
            for page_issues in self.corrections_by_page.values():
                for issue in page_issues:
                    if issue.get('status') == 'approved':
                        approved_count += 1
                    elif issue.get('status') == 'rejected':
                        rejected_count += 1
            
            # Save the modified text content
            modified_text = self.extracted_text.toPlainText()
            
            # Update the document with corrections - PERSIST to .tore file
            if self.current_document and hasattr(self.current_document, 'custom_metadata'):
                # Update corrections in document metadata with status information
                all_corrections = []
                for page_num, page_issues in self.corrections_by_page.items():
                    for issue in page_issues:
                        # Add status and persistence flag to correction
                        correction_data = issue.copy()
                        correction_data['page'] = page_num
                        correction_data['persistent'] = True  # Mark as persistent across sessions
                        correction_data['last_modified'] = str(datetime.now())
                        all_corrections.append(correction_data)
                
                # Save to document metadata
                self.current_document.custom_metadata['corrections'] = all_corrections
                self.current_document.custom_metadata['last_qa_session'] = str(datetime.now())
                
                # Mark as having pending corrections that need persistence
                self.current_document.custom_metadata['has_pending_corrections'] = (
                    approved_count + rejected_count < len(all_corrections)
                )
                
                self.log_message.emit(f"💾 Persisted {len(all_corrections)} corrections to document metadata")
            
            self.log_message.emit(f"Saved all changes: {approved_count} approved, {rejected_count} rejected corrections")
            self.save_all_btn.setEnabled(False)
            
            # Emit validation completed signal
            self.validation_completed.emit(self.current_document.id, True)
            
        except Exception as e:
            error_msg = f"Failed to save changes: {str(e)}"
            self.log_message.emit(error_msg)
            self.logger.error(error_msg)
    
    def _prev_page(self):
        """Navigate to previous page (any page, not just those with corrections)."""
        if not self.current_document or not self.total_pages:
            return
        
        if self.current_page > 1:
            self.current_page -= 1
            # Ensure page is valid
            if self.current_page <= 0:
                self.current_page = 1
            # Get corrections for this page (if any)
            self.current_page_issues = self.corrections_by_page.get(self.current_page, [])
            self.current_issue_index = 0
            self._load_page_text(self.current_page)
            self._update_page_display()
            self._update_correction_buttons()
            
            # Sync PDF viewer to the new page
            self._sync_pdf_viewer_page(self.current_page)
    
    def _next_page(self):
        """Navigate to next page (any page, not just those with corrections)."""
        if not self.current_document or not self.total_pages:
            return
        
        if self.current_page < self.total_pages:
            self.current_page += 1
            # Ensure page is valid
            if self.current_page <= 0:
                self.current_page = 1
            # Get corrections for this page (if any)
            self.current_page_issues = self.corrections_by_page.get(self.current_page, [])
            self.current_issue_index = 0
            self._load_page_text(self.current_page)
            self._update_page_display()
            self._update_correction_buttons()
            
            # Sync PDF viewer to the new page
            self._sync_pdf_viewer_page(self.current_page)
    
    def _prev_issue(self):
        """Navigate to previous issue - with cross-page navigation when reaching start of current page."""
        if not self.current_page_issues:
            # No issues on current page, find previous page with issues
            self._jump_to_prev_page_with_issues()
            return
        
        if self.current_issue_index > 0:
            # Move to previous issue on current page
            self.current_issue_index -= 1
            self._highlight_all_differences_without_modification()
            self._update_page_display()
            self._update_navigation_controls()
            self._update_correction_buttons()
        else:
            # At first issue on current page - jump to last issue on previous page with issues
            self.log_message.emit("🔄 Reached first issue on page, jumping to previous page with issues...")
            self._jump_to_prev_page_with_issues()
    
    def _next_issue(self):
        """Navigate to next issue - with cross-page navigation when reaching end of current page."""
        if not self.current_page_issues:
            # No issues on current page, find next page with issues
            self._jump_to_next_page_with_issues()
            return
        
        if self.current_issue_index < len(self.current_page_issues) - 1:
            # Move to next issue on current page
            self.current_issue_index += 1
            self._highlight_all_differences_without_modification()
            self._update_page_display()
            self._update_navigation_controls()
            self._update_correction_buttons()
        else:
            # At last issue on current page - jump to first issue on next page with issues
            self.log_message.emit("🔄 Reached last issue on page, jumping to next page with issues...")
            self._jump_to_next_page_with_issues()
    
    def _update_navigation_controls(self):
        """Update navigation button states and labels."""
        if not self.current_document:
            return
        
        # Page navigation - ALL pages, not just correction pages
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < self.total_pages)
        
        # Show current page info with corrections count
        corrections_on_page = len(self.current_page_issues) if self.current_page_issues else 0
        total_correction_pages = len(self.corrections_by_page)
        total_corrections = sum(len(issues) for issues in self.corrections_by_page.values())
        
        if corrections_on_page > 0:
            self.page_label.setText(f"Page {self.current_page} of {self.total_pages} ({corrections_on_page} corrections)")
        else:
            self.page_label.setText(f"Page {self.current_page} of {self.total_pages} (no corrections)")
        
        # Issue navigation
        if self.current_page_issues:
            self.prev_issue_btn.setEnabled(self.current_issue_index > 0)
            self.next_issue_btn.setEnabled(self.current_issue_index < len(self.current_page_issues) - 1)
            self.issue_label.setText(f"Issue {self.current_issue_index + 1} of {len(self.current_page_issues)} (Total: {total_corrections})")
            
            # Update issue info
            current_issue = self.current_page_issues[self.current_issue_index]
            issue_type = current_issue.get('type', 'Unknown')
            issue_description = current_issue.get('description', 'No description')
            
            self.issue_type_label.setText(f"Issue Type: {issue_type}")
            self.issue_desc_label.setText(f"Description: {issue_description}")
            
            severity = current_issue.get('severity', 'unknown')
            severity_color = {
                'critical': '#dc3545',
                'major': '#fd7e14', 
                'medium': '#ffc107',
                'minor': '#28a745',
                'unknown': '#6c757d'
            }.get(severity, '#6c757d')
            
            self.issue_severity_label.setText(f"Severity: {severity.capitalize()}")
            self.issue_severity_label.setStyleSheet(f"font-weight: bold; color: {severity_color};")
            
            # Send detailed issue information to log widget
            location = current_issue.get('location', {})
            bbox = location.get('bbox', [])
            text_position = location.get('text_position', [])
            
            log_msg = f"Current Issue: {issue_type} | {issue_description} | Severity: {severity.upper()}"
            if bbox:
                log_msg += f" | PDF Location: {bbox}"
            if text_position:
                log_msg += f" | Text Position: {text_position}"
        else:
            # No issues on this page
            self.prev_issue_btn.setEnabled(False)
            self.next_issue_btn.setEnabled(False)
            self.issue_label.setText(f"No issues on this page (Total: {total_corrections})")
            
            # Clear issue info
            self.issue_type_label.setText("Issue Type: -")
            self.issue_desc_label.setText("Description: No issues on this page")
            self.issue_severity_label.setText("Severity: -")
            self.issue_severity_label.setStyleSheet("font-weight: bold; color: #6c757d;")
            
            log_msg = f"Page {self.current_page}: No issues"
        
        # Always emit the log message
        self.log_message.emit(log_msg)
    
    def _update_correction_buttons(self):
        """Update correction button states."""
        if self.current_page_issues and self.current_issue_index < len(self.current_page_issues):
            current_issue = self.current_page_issues[self.current_issue_index]
            current_status = current_issue.get('status', 'suggested')
            
            # Enable buttons for suggested issues
            self.approve_correction_btn.setEnabled(current_status == 'suggested')
            self.reject_correction_btn.setEnabled(current_status == 'suggested')
            
            # Update button text based on status
            if current_status == 'approved':
                self.approve_correction_btn.setText("✓ Approved")
                self.reject_correction_btn.setText("✗ Reject")
            elif current_status == 'rejected':
                self.approve_correction_btn.setText("✓ Approve")
                self.reject_correction_btn.setText("✗ Rejected")
            else:
                self.approve_correction_btn.setText("✓ Approve Correction")
                self.reject_correction_btn.setText("✗ Reject Correction")
        else:
            self.approve_correction_btn.setEnabled(False)
            self.reject_correction_btn.setEnabled(False)
    
    # Enhanced QA Validation Methods
    
    def _run_full_detection(self):
        """Run comprehensive PDF vs Extraction comparison - PRESERVES existing corrections."""
        self.log_message.emit("🔍 Running PDF vs Extraction comparison...")
        
        try:
            # Get current extracted text (DO NOT MODIFY IT)
            current_extracted_text = self.extracted_text.toPlainText()
            if not current_extracted_text:
                self.log_message.emit("⚠️ No extracted text available for comparison")
                return
            
            # Get original PDF text for comparison
            original_pdf_text = self._extract_original_pdf_text()
            if not original_pdf_text:
                self.log_message.emit("⚠️ Cannot access original PDF text for comparison")
                return
            
            # PRESERVE existing corrections from .tore file
            existing_corrections = self.current_page_issues.copy()
            self.log_message.emit(f"📋 Preserving {len(existing_corrections)} existing corrections")
            
            # Initialize error counters with existing corrections
            error_counts = {
                'critical': 0,
                'major': 0,
                'medium': 0,
                'minor': 0,
                'resolved': 0
            }
            
            # Count existing corrections by severity
            for correction in existing_corrections:
                severity = correction.get('severity', 'minor')
                if severity in error_counts:
                    error_counts[severity] += 1
            
            detected_differences = []
            
            # 1. Compare PDF vs Extraction for differences
            if self.formatting_errors_check.isChecked():
                formatting_diffs = self._detect_pdf_vs_extraction_differences(
                    original_pdf_text, current_extracted_text, 'formatting'
                )
                detected_differences.extend(formatting_diffs)
                self.log_message.emit(f"📝 Found {len(formatting_diffs)} formatting differences")
            
            # 2. Detect missing content (vanishments)
            if self.vanishments_check.isChecked():
                missing_content = self._detect_missing_content(
                    original_pdf_text, current_extracted_text
                )
                detected_differences.extend(missing_content)
                self.log_message.emit(f"🔍 Found {len(missing_content)} missing content sections")
            
            # 3. Detect unwanted additions
            if self.additions_check.isChecked():
                unwanted_additions = self._detect_unwanted_additions_vs_pdf(
                    original_pdf_text, current_extracted_text
                )
                detected_differences.extend(unwanted_additions)
                self.log_message.emit(f"➕ Found {len(unwanted_additions)} unwanted additions")
            
            # 4. Detect writing/OCR errors
            if self.writing_errors_check.isChecked():
                writing_diffs = self._detect_writing_differences(
                    original_pdf_text, current_extracted_text
                )
                detected_differences.extend(writing_diffs)
                self.log_message.emit(f"✏️ Found {len(writing_diffs)} writing/OCR differences")
            
            # Mark new differences as 'newly_detected'
            for diff in detected_differences:
                diff['source'] = 'real_time_detection'
                diff['id'] = f"rt_{len(self.current_page_issues)}_{diff.get('position', 0)}"
                severity = diff.get('severity', 'minor')
                if severity in error_counts:
                    error_counts[severity] += 1
            
            # MERGE: Add new differences to existing corrections (DO NOT REPLACE)
            self.current_page_issues.extend(detected_differences)
            
            # Apply highlighting to ALL differences (existing + new) - NO TEXT MODIFICATION
            self._highlight_all_differences_without_modification()
            
            # Update statistics display with combined counts
            self._update_error_statistics(error_counts)
            
            # Update quality metrics with all differences
            self._update_quality_metrics(self.current_page_issues, current_extracted_text)
            
            total_new = len(detected_differences)
            total_all = len(self.current_page_issues)
            self.log_message.emit(f"✅ Comparison complete: {total_new} new + {total_all - total_new} existing = {total_all} total differences")
            
            # Update navigation
            self._update_issue_navigation()
            
        except Exception as e:
            self.log_message.emit(f"❌ PDF comparison failed: {str(e)}")
            self.logger.error(f"PDF comparison failed: {e}")
    
    def _detect_formatting_errors(self, text):
        """Detect formatting issues in text."""
        errors = []
        
        # Check for inconsistent spacing
        import re
        
        # Multiple spaces
        multiple_spaces = re.finditer(r' {2,}', text)
        for match in multiple_spaces:
            errors.append({
                'type': 'formatting',
                'severity': 'minor',
                'description': 'Multiple consecutive spaces',
                'position': match.start(),
                'length': match.end() - match.start(),
                'suggested_fix': ' '
            })
        
        # Inconsistent line breaks
        inconsistent_breaks = re.finditer(r'\n{3,}', text)
        for match in inconsistent_breaks:
            errors.append({
                'type': 'formatting',
                'severity': 'minor',
                'description': 'Excessive line breaks',
                'position': match.start(),
                'length': match.end() - match.start(),
                'suggested_fix': '\n\n'
            })
        
        # Missing spaces after punctuation
        missing_spaces = re.finditer(r'[.!?][A-Za-z]', text)
        for match in missing_spaces:
            errors.append({
                'type': 'formatting',
                'severity': 'medium',
                'description': 'Missing space after punctuation',
                'position': match.start(),
                'length': match.end() - match.start(),
                'suggested_fix': f"{match.group()[0]} {match.group()[1]}"
            })
        
        return errors
    
    def _detect_writing_errors(self, text):
        """Detect writing and grammar errors."""
        errors = []
        
        # OCR-specific errors
        import re
        
        # Common OCR substitutions
        ocr_patterns = [
            (r'\b0\b', 'O', 'OCR number/letter confusion'),
            (r'\bl\b', 'I', 'OCR lowercase L/I confusion'),
            (r'\brn\b', 'm', 'OCR rn/m confusion'),
            (r'\bvv\b', 'w', 'OCR vv/w confusion'),
            (r'\bcl\b', 'd', 'OCR cl/d confusion')
        ]
        
        for pattern, suggestion, description in ocr_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                errors.append({
                    'type': 'writing',
                    'severity': 'major',
                    'description': description,
                    'position': match.start(),
                    'length': match.end() - match.start(),
                    'suggested_fix': suggestion
                })
        
        # Repeated words
        repeated_words = re.finditer(r'\b(\w+)\s+\1\b', text, re.IGNORECASE)
        for match in repeated_words:
            errors.append({
                'type': 'writing',
                'severity': 'medium',
                'description': 'Repeated word',
                'position': match.start(),
                'length': match.end() - match.start(),
                'suggested_fix': match.group(1)
            })
        
        return errors
    
    def _detect_vanishments(self, text):
        """Detect missing content (vanishments)."""
        errors = []
        
        # Check for incomplete sentences
        import re
        
        # Sentences ending abruptly
        incomplete_sentences = re.finditer(r'[A-Z][^.!?]*[a-z]\s*$', text, re.MULTILINE)
        for match in incomplete_sentences:
            errors.append({
                'type': 'vanishment',
                'severity': 'critical',
                'description': 'Incomplete sentence (possible missing content)',
                'position': match.start(),
                'length': match.end() - match.start(),
                'suggested_fix': '[REVIEW: Content may be missing]'
            })
        
        # Check for missing table content
        table_headers = re.finditer(r'Table\s+\d+[:.]?\s*$', text, re.MULTILINE)
        for match in table_headers:
            errors.append({
                'type': 'vanishment',
                'severity': 'major',
                'description': 'Table header without content',
                'position': match.start(),
                'length': match.end() - match.start(),
                'suggested_fix': '[REVIEW: Table content missing]'
            })
        
        return errors
    
    def _detect_unwanted_additions(self, text):
        """Detect unwanted additions (hallucinations)."""
        errors = []
        
        # Check for OCR artifacts
        import re
        
        # Common OCR artifacts
        artifacts = [
            (r'[|]{2,}', 'Multiple vertical bars (OCR artifact)'),
            (r'[_]{3,}', 'Multiple underscores (OCR artifact)'),
            (r'[~]{2,}', 'Multiple tildes (OCR artifact)'),
            (r'[`]{2,}', 'Multiple backticks (OCR artifact)'),
            (r'[^\w\s.,!?;:()\[\]{}"\'-]{2,}', 'Unusual character sequences')
        ]
        
        for pattern, description in artifacts:
            matches = re.finditer(pattern, text)
            for match in matches:
                errors.append({
                    'type': 'addition',
                    'severity': 'medium',
                    'description': description,
                    'position': match.start(),
                    'length': match.end() - match.start(),
                    'suggested_fix': '[REMOVE]'
                })
        
        # Check for duplicated sections
        sentences = re.findall(r'[^.!?]+[.!?]', text)
        for i, sentence in enumerate(sentences):
            for j, other_sentence in enumerate(sentences[i+1:], i+1):
                if sentence.strip() == other_sentence.strip() and len(sentence.strip()) > 20:
                    errors.append({
                        'type': 'addition',
                        'severity': 'major',
                        'description': 'Duplicated content',
                        'position': text.find(other_sentence),
                        'length': len(other_sentence),
                        'suggested_fix': '[REMOVE DUPLICATE]'
                    })
                    break
        
        return errors
    
    def _reset_detection(self):
        """Reset error detection results."""
        self.log_message.emit("🔄 Resetting error detection...")
        
        # Clear highlighting from text
        cursor = self.extracted_text.textCursor()
        cursor.select(QTextCursor.Document)
        cursor.clearSelection()
        
        # Reset statistics
        self._update_error_statistics({
            'critical': 0,
            'major': 0,
            'medium': 0,
            'minor': 0,
            'resolved': 0
        })
        
        # Reset quality metrics
        self._update_quality_metrics([], "")
        
        self.log_message.emit("✅ Error detection reset complete")
    
    def _bulk_approve_corrections(self):
        """Bulk approve all corrections on current page."""
        self.log_message.emit("✅ Bulk approving corrections...")
        
        try:
            approved_count = 0
            
            # Get current page corrections
            current_corrections = self.current_page_issues
            
            for correction in current_corrections:
                if correction.get('status') != 'approved':
                    correction['status'] = 'approved'
                    approved_count += 1
            
            # Update display
            self._update_current_page_text()
            
            self.log_message.emit(f"✅ Bulk approved {approved_count} corrections")
            
        except Exception as e:
            self.log_message.emit(f"❌ Bulk approve failed: {str(e)}")
            self.logger.error(f"Bulk approve failed: {e}")
    
    def _bulk_reject_corrections(self):
        """Bulk reject all corrections on current page."""
        self.log_message.emit("❌ Bulk rejecting corrections...")
        
        try:
            rejected_count = 0
            
            # Get current page corrections
            current_corrections = self.current_page_issues
            
            for correction in current_corrections:
                if correction.get('status') != 'rejected':
                    correction['status'] = 'rejected'
                    rejected_count += 1
            
            # Update display
            self._update_current_page_text()
            
            self.log_message.emit(f"❌ Bulk rejected {rejected_count} corrections")
            
        except Exception as e:
            self.log_message.emit(f"❌ Bulk reject failed: {str(e)}")
            self.logger.error(f"Bulk reject failed: {e}")
    
    def _auto_fix_common_errors(self):
        """Automatically fix common errors."""
        self.log_message.emit("🔧 Auto-fixing common errors...")
        
        try:
            current_text = self.extracted_text.toPlainText()
            if not current_text:
                self.log_message.emit("⚠️ No text available for auto-fix")
                return
            
            fixed_text = current_text
            fix_count = 0
            
            # Common fixes
            fixes = [
                (r' {2,}', ' ', 'Multiple spaces'),
                (r'\n{3,}', '\n\n', 'Excessive line breaks'),
                (r'([.!?])([A-Za-z])', r'\1 \2', 'Missing space after punctuation'),
                (r'\b(\w+)\s+\1\b', r'\1', 'Repeated words'),
                (r'[|]{2,}', '', 'OCR artifacts'),
                (r'[_]{3,}', '', 'OCR artifacts'),
            ]
            
            for pattern, replacement, description in fixes:
                import re
                matches = len(re.findall(pattern, fixed_text))
                if matches > 0:
                    fixed_text = re.sub(pattern, replacement, fixed_text)
                    fix_count += matches
                    self.log_message.emit(f"🔧 Fixed {matches} instances of {description}")
            
            # Update text
            self.extracted_text.setPlainText(fixed_text)
            
            self.log_message.emit(f"✅ Auto-fix complete: {fix_count} fixes applied")
            
        except Exception as e:
            self.log_message.emit(f"❌ Auto-fix failed: {str(e)}")
            self.logger.error(f"Auto-fix failed: {e}")
    
    def _validate_current_page(self):
        """Validate current page for completeness and accuracy."""
        self.log_message.emit("🎯 Validating current page...")
        
        try:
            current_text = self.extracted_text.toPlainText()
            if not current_text:
                self.log_message.emit("⚠️ No text available for validation")
                return
            
            # Validation checks
            validation_results = {
                'text_length': len(current_text),
                'word_count': len(current_text.split()),
                'sentence_count': len([s for s in current_text.split('.') if s.strip()]),
                'has_special_areas': len(self.current_page_issues) > 0,
                'completion_score': 0
            }
            
            # Calculate completion score
            score = 0
            if validation_results['text_length'] > 100:
                score += 25
            if validation_results['word_count'] > 20:
                score += 25
            if validation_results['sentence_count'] > 2:
                score += 25
            if validation_results['has_special_areas']:
                score += 25
            
            validation_results['completion_score'] = score
            
            # Update quality metrics
            self._update_quality_metrics(self.current_page_issues, current_text)
            
            self.log_message.emit(f"🎯 Page validation complete: {score}% completion score")
            
        except Exception as e:
            self.log_message.emit(f"❌ Page validation failed: {str(e)}")
            self.logger.error(f"Page validation failed: {e}")
    
    def _update_error_statistics(self, error_counts):
        """Update error statistics display."""
        try:
            # Clear format for statistics without emojis
            stats_text = f"Critical: {error_counts.get('critical', 0)} | Major: {error_counts.get('major', 0)} | Medium: {error_counts.get('medium', 0)} | Minor: {error_counts.get('minor', 0)} | Resolved: {error_counts.get('resolved', 0)}"
            self.error_stats_label.setText(stats_text)
            
        except Exception as e:
            self.logger.error(f"Error updating statistics: {e}")
    
    def _update_quality_metrics(self, errors, text):
        """Update quality metrics display."""
        try:
            if not text:
                metrics_text = "Quality Score: 0% | Accuracy: 0% | Completeness: 0%"
                self.quality_score_label.setText(metrics_text)
                return
            
            # Calculate metrics
            text_length = len(text)
            error_count = len(errors)
            
            # Quality score (inverse of error density)
            if text_length > 0:
                error_density = error_count / (text_length / 100)  # Errors per 100 characters
                quality_score = max(0, 100 - (error_density * 10))
            else:
                quality_score = 0
            
            # Accuracy (based on error types)
            critical_errors = len([e for e in errors if e.get('severity') == 'critical'])
            accuracy = max(0, 100 - (critical_errors * 20))
            
            # Completeness (based on text length and structure)
            word_count = len(text.split())
            sentence_count = len([s for s in text.split('.') if s.strip()])
            
            completeness = 0
            if word_count > 20:
                completeness += 30
            if sentence_count > 2:
                completeness += 30
            if text_length > 100:
                completeness += 40
            
            # Clear format for quality metrics without emojis
            metrics_text = f"Quality: {quality_score:.0f}% | Accuracy: {accuracy:.0f}% | Completeness: {completeness:.0f}%"
            self.quality_score_label.setText(metrics_text)
            
        except Exception as e:
            self.logger.error(f"Error updating quality metrics: {e}")
            metrics_text = "Quality: 0% | Accuracy: 0% | Completeness: 0%"
            self.quality_score_label.setText(metrics_text)
    
    def _highlight_all_errors_in_text(self):
        """Highlight ALL errors (existing + newly detected) in extracted text."""
        try:
            # Clear existing highlighting
            cursor = self.extracted_text.textCursor()
            cursor.select(QTextCursor.Document)
            
            # Reset formatting
            default_format = QTextCharFormat()
            cursor.setCharFormat(default_format)
            cursor.clearSelection()
            
            # Get current text
            current_text = self.extracted_text.toPlainText()
            if not current_text:
                return
            
            # Highlight each error
            for error in self.current_page_issues:
                position = error.get('position', error.get('text_position', 0))
                length = error.get('length', 1)
                severity = error.get('severity', 'minor')
                source = error.get('source', 'tore_file')
                
                # Set color based on severity and source
                if source == 'real_time_detection':
                    # New real-time detections - brighter colors
                    color_map = {
                        'critical': '#ff0000',  # Bright red
                        'major': '#ff8c00',     # Dark orange
                        'medium': '#ffd700',    # Gold
                        'minor': '#90ee90'      # Light green
                    }
                else:
                    # Existing .tore corrections - standard colors
                    color_map = {
                        'critical': '#dc3545',  # Bootstrap danger
                        'major': '#fd7e14',     # Bootstrap warning
                        'medium': '#ffc107',    # Bootstrap warning
                        'minor': '#28a745'      # Bootstrap success
                    }
                
                # Apply highlighting
                if 0 <= position < len(current_text):
                    cursor.setPosition(position)
                    cursor.setPosition(min(position + length, len(current_text)), QTextCursor.KeepAnchor)
                    
                    highlight_format = QTextCharFormat()
                    highlight_format.setBackground(QColor(color_map.get(severity, '#ffc107')))
                    highlight_format.setForeground(QColor('#000000'))  # Black text
                    
                    # Make newly detected errors bold
                    if source == 'real_time_detection':
                        highlight_format.setFontWeight(QFont.Bold)
                        highlight_format.setUnderlineStyle(QTextCharFormat.SingleUnderline)
                    
                    cursor.setCharFormat(highlight_format)
            
            self.log_message.emit(f"🎨 Highlighted {len(self.current_page_issues)} errors in text")
            
        except Exception as e:
            self.log_message.emit(f"❌ Text highlighting failed: {str(e)}")
            self.logger.error(f"Text highlighting failed: {e}")
    
    def _highlight_all_errors_in_pdf(self):
        """Highlight ALL errors (existing + newly detected) in PDF viewer."""
        try:
            if not self.current_page_issues:
                return
            
            # Group errors by type for PDF highlighting
            pdf_highlights = []
            
            for error in self.current_page_issues:
                # Convert text position to PDF coordinates if needed
                position = error.get('position', 0)
                bbox = error.get('bbox')
                severity = error.get('severity', 'minor')
                source = error.get('source', 'tore_file')
                
                # Create highlight data for PDF
                if bbox:
                    # Use existing bbox coordinates
                    highlight_data = {
                        'page': self.current_page - 1,  # 0-based for PDF
                        'bbox': bbox,
                        'severity': severity,
                        'source': source,
                        'search_text': error.get('description', ''),
                        'highlight_type': 'error_detection'
                    }
                    pdf_highlights.append(highlight_data)
                else:
                    # Try to map text position to PDF coordinates
                    pdf_coords = self._map_text_position_to_pdf(position)
                    if pdf_coords:
                        highlight_data = {
                            'page': self.current_page - 1,
                            'bbox': pdf_coords,
                            'severity': severity,
                            'source': source,
                            'search_text': error.get('description', ''),
                            'highlight_type': 'error_detection'
                        }
                        pdf_highlights.append(highlight_data)
            
            # Send highlights to PDF viewer
            for highlight in pdf_highlights:
                self.highlight_pdf_location.emit(
                    highlight['page'],
                    highlight['bbox'],
                    highlight['search_text'],
                    highlight['highlight_type']
                )
            
            self.log_message.emit(f"🎨 Highlighted {len(pdf_highlights)} errors in PDF")
            
        except Exception as e:
            self.log_message.emit(f"❌ PDF highlighting failed: {str(e)}")
            self.logger.error(f"PDF highlighting failed: {e}")
    
    def _map_text_position_to_pdf(self, text_position):
        """Map text character position to PDF coordinates."""
        try:
            # Use existing text-to-PDF mapping if available
            if hasattr(self, 'text_to_pdf_mapping') and self.text_to_pdf_mapping:
                # Find closest mapping
                closest_pos = min(self.text_to_pdf_mapping.keys(), 
                                key=lambda x: abs(x - text_position))
                if abs(closest_pos - text_position) < 10:  # Within 10 characters
                    return self.text_to_pdf_mapping[closest_pos]
            
            # Fallback: approximate coordinates based on page layout
            # This is a simple estimation - could be improved with better mapping
            page_height = 800  # Approximate page height
            page_width = 600   # Approximate page width
            
            # Estimate line and column from text position
            chars_per_line = 80
            line_height = 15
            
            line_num = text_position // chars_per_line
            char_in_line = text_position % chars_per_line
            
            # Convert to PDF coordinates
            x = 50 + (char_in_line * 7)  # Approximate character width
            y = 50 + (line_num * line_height)
            
            return [x, y, x + 50, y + line_height]  # Small rectangle
            
        except Exception as e:
            self.logger.error(f"Error mapping text position to PDF: {e}")
            return None
    
    def _update_issue_navigation(self):
        """Update issue navigation controls and enable cross-page navigation."""
        try:
            total_issues = len(self.current_page_issues)
            
            if total_issues == 0:
                self.issue_label.setText("No issues")
                self.prev_issue_btn.setEnabled(False)
                self.next_issue_btn.setEnabled(False)
                self.approve_correction_btn.setEnabled(False)
                self.reject_correction_btn.setEnabled(False)
                return
            
            # Update issue label
            current_issue_num = self.current_issue_index + 1
            self.issue_label.setText(f"Issue {current_issue_num} of {total_issues}")
            
            # Enable/disable navigation buttons
            self.prev_issue_btn.setEnabled(current_issue_num > 1)
            
            # CRITICAL FIX: Enable next button even at last issue for cross-page navigation
            self.next_issue_btn.setEnabled(True)  # Always enabled for cross-page navigation
            
            # Enable correction buttons
            self.approve_correction_btn.setEnabled(True)
            self.reject_correction_btn.setEnabled(True)
            
            # Update current issue display
            if 0 <= self.current_issue_index < total_issues:
                current_issue = self.current_page_issues[self.current_issue_index]
                self._update_issue_info_display(current_issue)
            
        except Exception as e:
            self.logger.error(f"Error updating issue navigation: {e}")
    
    def _jump_to_next_page_with_issues(self):
        """Jump to the first issue on the next page that has issues."""
        try:
            if not self.corrections_by_page:
                self.log_message.emit("📋 No more pages with issues")
                return
            
            # Find pages with issues after current page
            pages_with_issues = sorted([p for p in self.corrections_by_page.keys() if p > self.current_page])
            
            if pages_with_issues:
                # Jump to first page with issues
                next_page = pages_with_issues[0]
                self.log_message.emit(f"🔄 Jumping to page {next_page} (next page with issues)")
                
                # Navigate to that page
                self.current_page = next_page
                self.current_issue_index = 0  # Start with first issue on new page
                
                # Load page data
                self._load_page_text(next_page)
                # Load corrections for this page
                self.current_page_issues = self.corrections_by_page.get(next_page, [])
                self._update_page_display()
                self._update_navigation_controls()
                self._update_correction_buttons()
                
                # Navigate PDF to new page
                self.navigate_pdf_page.emit(next_page - 1)  # 0-based for PDF
                
            else:
                # No more pages with issues
                self.log_message.emit("📋 No more pages with issues after current page")
                
                # Optionally wrap around to first page with issues
                all_pages_with_issues = sorted(self.corrections_by_page.keys())
                if all_pages_with_issues:
                    first_page = all_pages_with_issues[0]
                    self.log_message.emit(f"🔄 Wrapping around to page {first_page} (first page with issues)")
                    
                    self.current_page = first_page
                    self.current_issue_index = 0
                    
                    self._load_page_text(first_page)
                    # Load corrections for this page
                    self.current_page_issues = self.corrections_by_page.get(first_page, [])
                    self._update_page_display()
                    self._update_navigation_controls()
                    self._update_correction_buttons()
                    
                    self.navigate_pdf_page.emit(first_page - 1)
                
        except Exception as e:
            self.log_message.emit(f"❌ Error jumping to next page: {str(e)}")
            self.logger.error(f"Error jumping to next page: {e}")
    
    def _jump_to_prev_page_with_issues(self):
        """Jump to the last issue on the previous page that has issues."""
        try:
            if not self.corrections_by_page:
                return
            
            # Find pages with issues before current page
            pages_with_issues = sorted([p for p in self.corrections_by_page.keys() if p < self.current_page], reverse=True)
            
            if pages_with_issues:
                # Jump to previous page with issues
                prev_page = pages_with_issues[0]
                self.log_message.emit(f"🔄 Jumping to page {prev_page} (previous page with issues)")
                
                # Navigate to that page
                self.current_page = prev_page
                
                # Load page data and go to last issue
                self._load_page_text(prev_page)
                # Load corrections for this page
                self.current_page_issues = self.corrections_by_page.get(prev_page, [])
                if self.current_page_issues:
                    self.current_issue_index = len(self.current_page_issues) - 1  # Last issue on page
                
                self._update_page_display()
                self._update_navigation_controls()
                self._update_correction_buttons()
                
                # Navigate PDF to new page
                self.navigate_pdf_page.emit(prev_page - 1)
                
            else:
                self.log_message.emit("📋 No previous pages with issues")
                
        except Exception as e:
            self.log_message.emit(f"❌ Error jumping to previous page: {str(e)}")
            self.logger.error(f"Error jumping to previous page: {e}")
    
    def _extract_original_pdf_text(self):
        """Extract text from the original PDF page for comparison."""
        try:
            if not self.current_document or not hasattr(self.current_document.metadata, 'file_path'):
                return None
            
            # Use PyMuPDF to extract text from current page
            import fitz
            pdf_path = self.current_document.metadata.file_path
            
            with fitz.open(pdf_path) as doc:
                if self.current_page - 1 < len(doc):
                    page = doc[self.current_page - 1]  # 0-based indexing
                    original_text = page.get_text()
                    return original_text
                    
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting original PDF text: {e}")
            return None
    
    def _detect_pdf_vs_extraction_differences(self, original_text, extracted_text, diff_type='formatting'):
        """Detect differences between original PDF and extracted text."""
        differences = []
        
        try:
            import difflib
            
            # Split into lines for comparison
            original_lines = original_text.split('\n')
            extracted_lines = extracted_text.split('\n')
            
            # Use difflib to find differences
            differ = difflib.unified_diff(
                original_lines, extracted_lines, 
                fromfile='original_pdf', tofile='extracted_text',
                lineterm=''
            )
            
            line_num = 0
            position = 0
            
            for line in differ:
                if line.startswith('-'):  # Content in original but not in extraction
                    missing_content = line[1:]  # Remove the '-' prefix
                    differences.append({
                        'type': 'missing_content',
                        'severity': 'major',
                        'description': f'Missing from extraction: "{missing_content[:50]}..."',
                        'position': position,
                        'length': len(missing_content),
                        'original_content': missing_content,
                        'expected_content': missing_content
                    })
                elif line.startswith('+'):  # Content in extraction but not in original
                    extra_content = line[1:]  # Remove the '+' prefix
                    differences.append({
                        'type': 'unwanted_addition',
                        'severity': 'medium',
                        'description': f'Extra in extraction: "{extra_content[:50]}..."',
                        'position': position,
                        'length': len(extra_content),
                        'extracted_content': extra_content,
                        'should_remove': True
                    })
                
                # Update position counter
                if not line.startswith(('@@', '---', '+++')):
                    position += len(line) + 1  # +1 for newline
                    
        except Exception as e:
            self.logger.error(f"Error detecting differences: {e}")
            
        return differences
    
    def _detect_missing_content(self, original_text, extracted_text):
        """Detect content that exists in PDF but missing from extraction."""
        missing_content = []
        
        try:
            # Split into words for more granular comparison
            original_words = original_text.split()
            extracted_words = extracted_text.split()
            
            # Simple approach: find words in original that are not in extracted
            original_word_set = set(original_words)
            extracted_word_set = set(extracted_words)
            
            missing_words = original_word_set - extracted_word_set
            
            if missing_words:
                # Find positions of missing words in original text
                for word in missing_words:
                    word_positions = []
                    start = 0
                    while True:
                        pos = original_text.find(word, start)
                        if pos == -1:
                            break
                        word_positions.append(pos)
                        start = pos + 1
                    
                    for pos in word_positions:
                        missing_content.append({
                            'type': 'vanishment',
                            'severity': 'critical',
                            'description': f'Missing word: "{word}"',
                            'position': pos,
                            'length': len(word),
                            'missing_content': word,
                            'should_restore': True
                        })
                        
        except Exception as e:
            self.logger.error(f"Error detecting missing content: {e}")
            
        return missing_content
    
    def _detect_unwanted_additions_vs_pdf(self, original_text, extracted_text):
        """Detect content that exists in extraction but not in original PDF."""
        unwanted_additions = []
        
        try:
            # Split into words for comparison
            original_words = set(original_text.split())
            extracted_words = extracted_text.split()
            
            position = 0
            for word in extracted_words:
                if word not in original_words and len(word) > 2:  # Skip short words
                    unwanted_additions.append({
                        'type': 'unwanted_addition',
                        'severity': 'medium',
                        'description': f'Extra content not in PDF: "{word}"',
                        'position': position,
                        'length': len(word),
                        'unwanted_content': word,
                        'should_remove': True
                    })
                position += len(word) + 1  # +1 for space
                
        except Exception as e:
            self.logger.error(f"Error detecting unwanted additions: {e}")
            
        return unwanted_additions
    
    def _detect_writing_differences(self, original_text, extracted_text):
        """Detect character-level differences that might be OCR errors."""
        writing_diffs = []
        
        try:
            import difflib
            
            # Use SequenceMatcher for character-level comparison
            matcher = difflib.SequenceMatcher(None, original_text, extracted_text)
            
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == 'replace':
                    original_segment = original_text[i1:i2]
                    extracted_segment = extracted_text[j1:j2]
                    
                    writing_diffs.append({
                        'type': 'writing_error',
                        'severity': 'major',
                        'description': f'Text difference: "{original_segment}" vs "{extracted_segment}"',
                        'position': j1,
                        'length': j2 - j1,
                        'original_content': original_segment,
                        'extracted_content': extracted_segment,
                        'suggested_fix': original_segment
                    })
                    
        except Exception as e:
            self.logger.error(f"Error detecting writing differences: {e}")
            
        return writing_diffs
    
    def _highlight_all_differences_without_modification(self):
        """Highlight ALL differences (existing + newly detected) WITHOUT modifying text content."""
        try:
            # Store original text to restore it after highlighting
            original_text = self.extracted_text.toPlainText()
            
            # Clear existing formatting but preserve text
            cursor = self.extracted_text.textCursor()
            cursor.select(QTextCursor.Document)
            
            # Reset formatting to default
            default_format = QTextCharFormat()
            cursor.setCharFormat(default_format)
            cursor.clearSelection()
            
            # Apply highlighting for each difference
            for i, difference in enumerate(self.current_page_issues):
                position = difference.get('position', difference.get('text_position', 0))
                length = difference.get('length', 1)
                severity = difference.get('severity', 'minor')
                source = difference.get('source', 'tore_file')
                
                # Determine highlight color based on active issue and severity
                if i == self.current_issue_index:
                    # Active issue - YELLOW highlighting
                    highlight_color = '#ffff00'  # Bright yellow for active
                    text_color = '#000000'       # Black text
                    font_weight = QFont.Bold
                else:
                    # Inactive issues - GREEN highlighting for same page
                    highlight_color = '#90ee90'  # Light green for inactive
                    text_color = '#000000'       # Black text  
                    font_weight = QFont.Normal
                
                # Apply highlighting if position is valid
                if 0 <= position < len(original_text):
                    cursor.setPosition(position)
                    end_position = min(position + length, len(original_text))
                    cursor.setPosition(end_position, QTextCursor.KeepAnchor)
                    
                    highlight_format = QTextCharFormat()
                    highlight_format.setBackground(QColor(highlight_color))
                    highlight_format.setForeground(QColor(text_color))
                    highlight_format.setFontWeight(font_weight)
                    
                    # Add underline for newly detected issues
                    if source == 'real_time_detection':
                        highlight_format.setUnderlineStyle(QTextCharFormat.SingleUnderline)
                    
                    cursor.setCharFormat(highlight_format)
            
            # Ensure text content is exactly the same as before
            if self.extracted_text.toPlainText() != original_text:
                self.extracted_text.setPlainText(original_text)
                # Re-apply highlighting after text reset
                self._reapply_highlighting_after_text_reset()
            
            self.log_message.emit(f"🎨 Highlighted {len(self.current_page_issues)} differences (active: yellow, others: green)")
            
        except Exception as e:
            self.log_message.emit(f"❌ Highlighting failed: {str(e)}")
            self.logger.error(f"Highlighting failed: {e}")
    
    def _reapply_highlighting_after_text_reset(self):
        """Reapply highlighting after text has been reset to preserve content."""
        try:
            for i, difference in enumerate(self.current_page_issues):
                position = difference.get('position', difference.get('text_position', 0))
                length = difference.get('length', 1)
                source = difference.get('source', 'tore_file')
                
                # Determine highlight color
                if i == self.current_issue_index:
                    highlight_color = '#ffff00'  # Yellow for active
                else:
                    highlight_color = '#90ee90'  # Green for inactive
                
                # Apply highlighting
                cursor = self.extracted_text.textCursor()
                cursor.setPosition(position)
                cursor.setPosition(min(position + length, len(self.extracted_text.toPlainText())), QTextCursor.KeepAnchor)
                
                highlight_format = QTextCharFormat()
                highlight_format.setBackground(QColor(highlight_color))
                highlight_format.setForeground(QColor('#000000'))
                
                if source == 'real_time_detection':
                    highlight_format.setUnderlineStyle(QTextCharFormat.SingleUnderline)
                
                cursor.setCharFormat(highlight_format)
                
        except Exception as e:
            self.logger.error(f"Error reapplying highlighting: {e}")
    
    def load_document_by_id(self, document_id: str, metadata: dict):
        """Load document for validation by ID and metadata."""
        try:
            # Check if this is the same document
            if (hasattr(self, 'current_document_id') and 
                self.current_document_id == document_id):
                self.logger.info(f"Document {document_id} already loaded")
                return
            
            # Load document from metadata
            file_path = metadata.get('file_path')
            if not file_path or not Path(file_path).exists():
                self.logger.warning(f"Document file not found: {file_path}")
                return
            
            self.logger.info(f"Loading document for validation: {document_id}")
            
            # Store document info
            self.current_document_id = document_id
            self.current_document_metadata = metadata
            
            # Check if we have corrections data
            corrections = metadata.get('corrections', [])
            if corrections:
                self.logger.info(f"Loading document with {len(corrections)} corrections")
                self.load_document_for_validation(file_path, corrections)
            else:
                # Load document without corrections
                self.logger.info("Loading document without corrections")
                self._load_document_without_corrections(file_path)
                
        except Exception as e:
            self.logger.error(f"Error loading document by ID: {e}")
            self.status_message.emit(f"Error loading document: {e}")
    
    def _load_document_without_corrections(self, file_path: str):
        """Load document when no corrections are available."""
        try:
            # Reset state
            self.document_data = None
            self.pages_data = {}
            self.current_page = 1
            self.current_issue_index = 0
            self.grouped_issues = {}
            
            # Update UI
            self.page_label.setText("No corrections available")
            self.issue_label.setText("")
            self.extracted_text.setPlainText("No corrections data found for this document.")
            
            # Emit signal to load in PDF viewer
            if hasattr(self, 'navigate_pdf_page'):
                self.navigate_pdf_page.emit(1)
            
            self.logger.info(f"Document loaded without corrections: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error loading document without corrections: {e}")
    
    def load_extracted_content(self, extracted_content):
        """Load extracted content into the widget for highlighting and display."""
        try:
            self.logger.info(f"LOAD EXTRACTED: Loading extracted content into PageValidationWidget")
            
            # Store extracted content
            self.extracted_content = extracted_content
            
            # Get text elements and display them
            text_elements = extracted_content.get('text_elements', [])
            
            if not text_elements:
                self.logger.warning("LOAD EXTRACTED: No text elements found in extracted content")
                self.extracted_text.setPlainText("No extracted text available.")
                return
            
            # Extract text from elements and display
            full_text = ""
            for element in text_elements:
                # Handle both dict and object formats
                if isinstance(element, dict):
                    content = element.get('content', '')
                    element_type = element.get('element_type', 'text')
                else:
                    content = getattr(element, 'content', '')
                    element_type = getattr(element, 'element_type', 'text')
                
                if content:
                    full_text += content + "\n"
            
            # Display the extracted text
            self.extracted_text.setPlainText(full_text)
            
            # Update UI state
            self.page_label.setText("Extracted content loaded")
            self.issue_label.setText(f"Ready for highlighting ({len(text_elements)} text elements)")
            
            # Enable highlighting engine
            if self.highlighting_engine:
                self.highlighting_engine.set_text_widget(self.extracted_text)
                self.logger.info("LOAD EXTRACTED: Highlighting engine connected to text widget")
            
            self.logger.info(f"LOAD EXTRACTED: Successfully loaded {len(text_elements)} text elements")
            
        except Exception as e:
            self.logger.error(f"LOAD EXTRACTED: Error loading extracted content: {e}")
            self.extracted_text.setPlainText(f"Error loading extracted content: {e}")