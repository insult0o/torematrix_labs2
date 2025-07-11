#!/usr/bin/env python3
"""
Document Viewer V2 for TORE Matrix Labs V2

A modern document viewer component that replaces the complex viewer
from the original codebase with a simplified, clean interface.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, 
    QPushButton, QSplitter, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QPainter
from typing import Optional, Dict, Any, List
import logging

from ..services.event_bus import EventBus, EventType
from ..services.ui_state_manager import UIStateManager


class DocumentViewerV2(QWidget):
    """Modern document viewer for V2 system."""
    
    # Signals
    page_changed = pyqtSignal(int)
    document_loaded = pyqtSignal(dict)
    area_selected = pyqtSignal(dict)
    
    def __init__(self, 
                 event_bus: EventBus,
                 state_manager: UIStateManager,
                 parent: Optional[QWidget] = None):
        """Initialize the document viewer."""
        super().__init__(parent)
        
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.logger = logging.getLogger(__name__)
        
        self.current_document = None
        self.current_page = 1
        self.total_pages = 0
        self.zoom_level = 1.0
        
        self._setup_ui()
        self._setup_events()
        
        self.logger.info("Document viewer V2 initialized")
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Header with document info and controls
        header_layout = self._create_header()
        layout.addLayout(header_layout)
        
        # Main viewer area
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Document display area
        doc_panel = self._create_document_panel()
        main_splitter.addWidget(doc_panel)
        
        # Info panel
        info_panel = self._create_info_panel()
        main_splitter.addWidget(info_panel)
        
        # Set splitter proportions
        main_splitter.setSizes([700, 300])
        layout.addWidget(main_splitter)
        
        # Status bar
        status_layout = self._create_status_bar()
        layout.addLayout(status_layout)
    
    def _create_header(self) -> QHBoxLayout:
        """Create the header with controls."""
        layout = QHBoxLayout()
        
        # Document title
        self.doc_title_label = QLabel("No document loaded")
        self.doc_title_label.setFont(QFont("", 12, QFont.Bold))
        layout.addWidget(self.doc_title_label)
        
        layout.addStretch()
        
        # Navigation controls
        self.prev_btn = QPushButton("◀ Previous")
        self.prev_btn.clicked.connect(self._previous_page)
        self.prev_btn.setEnabled(False)
        layout.addWidget(self.prev_btn)
        
        self.page_label = QLabel("Page 0 of 0")
        layout.addWidget(self.page_label)
        
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.clicked.connect(self._next_page)
        self.next_btn.setEnabled(False)
        layout.addWidget(self.next_btn)
        
        # Zoom controls
        self.zoom_out_btn = QPushButton("🔍-")
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        layout.addWidget(self.zoom_out_btn)
        
        self.zoom_label = QLabel("100%")
        layout.addWidget(self.zoom_label)
        
        self.zoom_in_btn = QPushButton("🔍+")
        self.zoom_in_btn.clicked.connect(self._zoom_in)
        layout.addWidget(self.zoom_in_btn)
        
        return layout
    
    def _create_document_panel(self) -> QWidget:
        """Create the main document display panel."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # Document content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        self.document_display = QTextEdit()
        self.document_display.setReadOnly(True)
        self.document_display.setPlaceholderText("Load a document to view its content...")
        
        scroll_area.setWidget(self.document_display)
        layout.addWidget(scroll_area)
        
        return panel
    
    def _create_info_panel(self) -> QWidget:
        """Create the information panel."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # Panel title
        info_label = QLabel("Document Information")
        info_label.setFont(QFont("", 11, QFont.Bold))
        layout.addWidget(info_label)
        
        # Document metadata
        self.metadata_display = QTextEdit()
        self.metadata_display.setReadOnly(True)
        self.metadata_display.setMaximumHeight(200)
        self.metadata_display.setPlaceholderText("Document metadata will appear here...")
        layout.addWidget(self.metadata_display)
        
        # Areas and validation info
        areas_label = QLabel("Areas & Validation")
        areas_label.setFont(QFont("", 11, QFont.Bold))
        layout.addWidget(areas_label)
        
        self.areas_display = QTextEdit()
        self.areas_display.setReadOnly(True)
        self.areas_display.setPlaceholderText("Area information will appear here...")
        layout.addWidget(self.areas_display)
        
        return panel
    
    def _create_status_bar(self) -> QHBoxLayout:
        """Create the status bar."""
        layout = QHBoxLayout()
        
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Processing status
        self.processing_label = QLabel("")
        layout.addWidget(self.processing_label)
        
        return layout
    
    def _setup_events(self):
        """Set up event handlers."""
        self.event_bus.subscribe(
            EventType.DOCUMENT_LOADED,
            self._handle_document_loaded
        )
        
        self.event_bus.subscribe(
            EventType.DOCUMENT_PROCESSING_STARTED,
            self._handle_processing_started
        )
        
        self.event_bus.subscribe(
            EventType.DOCUMENT_PROCESSING_COMPLETED,
            self._handle_processing_completed
        )
    
    def load_document(self, document_data: Dict[str, Any]):
        """Load a document for viewing."""
        self.current_document = document_data
        
        # Update document info
        doc_name = document_data.get("name", "Unknown Document")
        self.doc_title_label.setText(doc_name)
        
        # Update page info
        self.total_pages = document_data.get("page_count", 1)
        self.current_page = 1
        self._update_page_info()
        
        # Load document content
        content = document_data.get("content", "No content available")
        self.document_display.setText(content)
        
        # Update metadata
        metadata = document_data.get("metadata", {})
        metadata_text = "Document Metadata:\n\n"
        for key, value in metadata.items():
            metadata_text += f"{key}: {value}\n"
        self.metadata_display.setText(metadata_text)
        
        # Update areas info
        areas = document_data.get("areas", [])
        areas_text = f"Document Areas: {len(areas)}\n\n"
        for i, area in enumerate(areas):
            area_type = area.get("type", "unknown")
            area_text = f"Area {i+1}: {area_type}\n"
            areas_text += area_text
        self.areas_display.setText(areas_text)
        
        # Update status
        self.status_label.setText(f"Document loaded: {doc_name}")
        
        # Enable navigation if multiple pages
        self._update_navigation_buttons()
        
        # Emit signal
        self.document_loaded.emit(document_data)
        
        self.logger.info(f"Document loaded: {doc_name}")
    
    def _update_page_info(self):
        """Update page information display."""
        self.page_label.setText(f"Page {self.current_page} of {self.total_pages}")
    
    def _update_navigation_buttons(self):
        """Update navigation button states."""
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)
    
    def _previous_page(self):
        """Go to previous page."""
        if self.current_page > 1:
            self.current_page -= 1
            self._update_page_info()
            self._update_navigation_buttons()
            self.page_changed.emit(self.current_page)
            self.logger.debug(f"Changed to page {self.current_page}")
    
    def _next_page(self):
        """Go to next page."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._update_page_info()
            self._update_navigation_buttons()
            self.page_changed.emit(self.current_page)
            self.logger.debug(f"Changed to page {self.current_page}")
    
    def _zoom_in(self):
        """Zoom in on the document."""
        self.zoom_level = min(self.zoom_level * 1.2, 3.0)
        self._update_zoom()
    
    def _zoom_out(self):
        """Zoom out of the document."""
        self.zoom_level = max(self.zoom_level / 1.2, 0.5)
        self._update_zoom()
    
    def _update_zoom(self):
        """Update zoom level display and document size."""
        zoom_percent = int(self.zoom_level * 100)
        self.zoom_label.setText(f"{zoom_percent}%")
        
        # Update document display font size
        font = self.document_display.font()
        base_size = 10
        font.setPointSize(int(base_size * self.zoom_level))
        self.document_display.setFont(font)
        
        self.logger.debug(f"Zoom level changed to {zoom_percent}%")
    
    def _handle_document_loaded(self, event):
        """Handle document loaded event."""
        document_data = event.get_data("document_data", {})
        if document_data:
            self.load_document(document_data)
    
    def _handle_processing_started(self, event):
        """Handle processing started event."""
        self.processing_label.setText("Processing...")
        self.status_label.setText("Document processing started")
    
    def _handle_processing_completed(self, event):
        """Handle processing completed event."""
        self.processing_label.setText("")
        self.status_label.setText("Document processing completed")
    
    def get_current_page(self) -> int:
        """Get current page number."""
        return self.current_page
    
    def get_zoom_level(self) -> float:
        """Get current zoom level."""
        return self.zoom_level
    
    def set_page(self, page_number: int):
        """Set current page number."""
        if 1 <= page_number <= self.total_pages:
            self.current_page = page_number
            self._update_page_info()
            self._update_navigation_buttons()
            self.page_changed.emit(self.current_page)
    
    def highlight_area(self, area_data: Dict[str, Any]):
        """Highlight a specific area in the document."""
        # This would implement area highlighting
        area_id = area_data.get("id", "unknown")
        self.status_label.setText(f"Highlighted area: {area_id}")
        self.area_selected.emit(area_data)
        self.logger.debug(f"Area highlighted: {area_id}")
    
    def clear_highlights(self):
        """Clear all area highlights."""
        # This would clear highlighting
        self.status_label.setText("Highlights cleared")
        self.logger.debug("All highlights cleared")