"""
OCRDialog - Advanced OCR visualization and confidence highlighting.

Agent 3 implementation for Issue #242 - UI Components & User Experience.
This module provides a sophisticated dialog for OCR text extraction with
confidence highlighting, real-time editing, and quality assessment.
"""

import logging
import re
from enum import Enum, auto
from typing import Optional, Dict, Any, List, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QTextEdit, QPlainTextEdit, QScrollArea, QGroupBox, QSplitter, QTabWidget,
    QProgressBar, QSlider, QCheckBox, QComboBox, QSpinBox, QFrame, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QMutex, QSize
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QPixmap, QTextCharFormat,
    QTextCursor, QTextDocument, QSyntaxHighlighter, QPalette
)

from .drawing_state import DrawingArea
from ....core.models import ElementType


class ConfidenceLevel(Enum):
    """Confidence level categories for highlighting."""
    VERY_HIGH = auto()  # 90-100%
    HIGH = auto()       # 75-89%
    MEDIUM = auto()     # 50-74%
    LOW = auto()        # 25-49%
    VERY_LOW = auto()   # 0-24%


@dataclass
class OCRWord:
    """Individual word with OCR data."""
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    position: Tuple[int, int]        # start, end in full text
    
    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Get confidence level category."""
        if self.confidence >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif self.confidence >= 0.75:
            return ConfidenceLevel.HIGH
        elif self.confidence >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif self.confidence >= 0.25:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW


@dataclass
class OCRResults:
    """Complete OCR analysis results."""
    full_text: str
    overall_confidence: float
    words: List[OCRWord] = field(default_factory=list)
    processing_time: float = 0.0
    engine_used: str = "unknown"
    quality_metrics: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def word_count(self) -> int:
        """Get total word count."""
        return len(self.words)
    
    @property
    def low_confidence_words(self) -> List[OCRWord]:
        """Get words with confidence below threshold."""
        return [word for word in self.words if word.confidence < 0.5]
    
    def get_confidence_distribution(self) -> Dict[ConfidenceLevel, int]:
        """Get distribution of confidence levels."""
        distribution = {level: 0 for level in ConfidenceLevel}
        for word in self.words:
            distribution[word.confidence_level] += 1
        return distribution


class OCRConfidenceHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for confidence-based text coloring."""
    
    def __init__(self, ocr_results: OCRResults, parent=None):
        """Initialize highlighter with OCR results."""
        super().__init__(parent)
        self.ocr_results = ocr_results
        self.logger = logging.getLogger("torematrix.ui.ocr_highlighter")
        
        # Color scheme for confidence levels
        self.confidence_colors = {
            ConfidenceLevel.VERY_HIGH: QColor("#28a745"),  # Green
            ConfidenceLevel.HIGH: QColor("#17a2b8"),       # Cyan
            ConfidenceLevel.MEDIUM: QColor("#ffc107"),     # Yellow
            ConfidenceLevel.LOW: QColor("#fd7e14"),        # Orange
            ConfidenceLevel.VERY_LOW: QColor("#dc3545"),   # Red
        }
        
        # Create text formats
        self.confidence_formats = {}
        for level, color in self.confidence_colors.items():
            fmt = QTextCharFormat()
            fmt.setBackground(color.lighter(160))
            fmt.setForeground(color.darker(150))
            self.confidence_formats[level] = fmt
    
    def highlightBlock(self, text: str):
        """Highlight text block based on confidence levels."""
        if not self.ocr_results.words:
            return
        
        block_start = self.currentBlock().position()
        
        for word in self.ocr_results.words:
            word_start, word_end = word.position
            
            # Check if word overlaps with current block
            if (word_start < block_start + len(text) and 
                word_end > block_start):
                
                # Calculate relative positions within block
                relative_start = max(0, word_start - block_start)
                relative_end = min(len(text), word_end - block_start)
                
                if relative_start < relative_end:
                    fmt = self.confidence_formats[word.confidence_level]
                    self.setFormat(relative_start, relative_end - relative_start, fmt)


class OCRDialog(QDialog):
    """
    Advanced OCR visualization dialog with confidence highlighting.
    
    Provides comprehensive OCR text review, editing capabilities,
    and quality assessment tools for manual validation workflows.
    """
    
    # Signals for dialog interactions
    text_accepted = pyqtSignal(str)           # Final accepted text
    text_rejected = pyqtSignal()              # User rejected OCR
    reprocess_requested = pyqtSignal(dict)    # Reprocess with new settings
    word_selected = pyqtSignal(OCRWord)       # Word clicked for details
    
    def __init__(self, area: DrawingArea, ocr_results: OCRResults, parent=None):
        """Initialize OCR dialog."""
        super().__init__(parent)
        
        self.logger = logging.getLogger("torematrix.ui.ocr_dialog")
        self.area = area
        self.ocr_results = ocr_results
        
        # Dialog state
        self._modified = False
        self._confidence_threshold = 0.5
        self._show_confidence = True
        self._auto_correct = False
        
        # UI components
        self.highlighter: Optional[OCRConfidenceHighlighter] = None
        self.original_text_edit: Optional[QTextEdit] = None
        self.edited_text_edit: Optional[QPlainTextEdit] = None
        self.confidence_table: Optional[QTableWidget] = None
        self.quality_tree: Optional[QTreeWidget] = None
        
        # Performance optimization
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._delayed_update)
        
        # Setup dialog
        self._setup_dialog()
        self._create_layout()
        self._populate_content()
        self._connect_signals()
        
        self.logger.info(f"OCRDialog initialized for area {area.area_id}")
    
    def _setup_dialog(self):
        """Configure dialog properties."""
        self.setWindowTitle("OCR Text Review & Editing")
        self.setModal(True)
        self.resize(1000, 700)
        self.setMinimumSize(800, 600)
        
        # Professional styling
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTextEdit, QPlainTextEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px;
                background-color: white;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
    
    def _create_layout(self):
        """Create the dialog layout."""
        main_layout = QVBoxLayout(self)
        
        # Header with area info
        header_group = QGroupBox("Selected Area Information")
        header_layout = QGridLayout()
        
        header_layout.addWidget(QLabel("Area ID:"), 0, 0)
        header_layout.addWidget(QLabel(self.area.area_id), 0, 1)
        header_layout.addWidget(QLabel("Position:"), 0, 2)
        header_layout.addWidget(QLabel(f"{self.area.x}, {self.area.y}"), 0, 3)
        header_layout.addWidget(QLabel("Size:"), 1, 0)
        header_layout.addWidget(QLabel(f"{self.area.width} × {self.area.height}"), 1, 1)
        header_layout.addWidget(QLabel("Page:"), 1, 2)
        header_layout.addWidget(QLabel(str(self.area.page_number)), 1, 3)
        
        header_group.setLayout(header_layout)
        main_layout.addWidget(header_group)
        
        # Main content area with tabs
        self.tab_widget = QTabWidget()
        
        # Text editing tab
        self._create_text_tab()
        
        # Analysis tab
        self._create_analysis_tab()
        
        # Settings tab
        self._create_settings_tab()
        
        main_layout.addWidget(self.tab_widget)
        
        # Button bar
        button_layout = QHBoxLayout()
        
        self.reprocess_btn = QPushButton("Reprocess OCR")
        self.reprocess_btn.clicked.connect(self._reprocess_ocr)
        
        self.reset_btn = QPushButton("Reset Changes")
        self.reset_btn.clicked.connect(self._reset_changes)
        
        button_layout.addWidget(self.reprocess_btn)
        button_layout.addWidget(self.reset_btn)
        button_layout.addStretch()
        
        self.reject_btn = QPushButton("Reject")
        self.reject_btn.clicked.connect(self.reject)
        
        self.accept_btn = QPushButton("Accept")
        self.accept_btn.clicked.connect(self.accept)
        self.accept_btn.setDefault(True)
        
        button_layout.addWidget(self.reject_btn)
        button_layout.addWidget(self.accept_btn)
        
        main_layout.addLayout(button_layout)
    
    def _create_text_tab(self):
        """Create text editing tab."""
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.confidence_checkbox = QCheckBox("Show Confidence Highlighting")
        self.confidence_checkbox.setChecked(self._show_confidence)
        self.confidence_checkbox.toggled.connect(self._toggle_confidence_highlighting)
        
        self.threshold_label = QLabel("Threshold:")
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(int(self._confidence_threshold * 100))
        self.threshold_slider.valueChanged.connect(self._threshold_changed)
        
        self.threshold_value_label = QLabel(f"{int(self._confidence_threshold * 100)}%")
        
        controls_layout.addWidget(self.confidence_checkbox)
        controls_layout.addStretch()
        controls_layout.addWidget(self.threshold_label)
        controls_layout.addWidget(self.threshold_slider)
        controls_layout.addWidget(self.threshold_value_label)
        
        text_layout.addLayout(controls_layout)
        
        # Text editors in splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Original text (read-only with highlighting)
        original_group = QGroupBox("Original OCR Text")
        original_layout = QVBoxLayout()
        
        self.original_text_edit = QTextEdit()
        self.original_text_edit.setReadOnly(True)
        self.original_text_edit.setFont(QFont("Consolas", 10))
        
        original_layout.addWidget(self.original_text_edit)
        original_group.setLayout(original_layout)
        splitter.addWidget(original_group)
        
        # Edited text
        edited_group = QGroupBox("Edited Text")
        edited_layout = QVBoxLayout()
        
        self.edited_text_edit = QPlainTextEdit()
        self.edited_text_edit.setFont(QFont("Consolas", 10))
        self.edited_text_edit.textChanged.connect(self._text_modified)
        
        edited_layout.addWidget(self.edited_text_edit)
        edited_group.setLayout(edited_layout)
        splitter.addWidget(edited_group)
        
        splitter.setSizes([500, 500])
        text_layout.addWidget(splitter)
        
        self.tab_widget.addTab(text_widget, "Text Editing")
    
    def _create_analysis_tab(self):
        """Create OCR analysis tab."""
        analysis_widget = QWidget()
        analysis_layout = QVBoxLayout(analysis_widget)
        
        # Statistics summary
        stats_group = QGroupBox("OCR Statistics")
        stats_layout = QGridLayout()
        
        stats_layout.addWidget(QLabel("Overall Confidence:"), 0, 0)
        confidence_label = QLabel(f"{self.ocr_results.overall_confidence:.1%}")
        confidence_label.setStyleSheet(f"color: {self._get_confidence_color(self.ocr_results.overall_confidence)};")
        stats_layout.addWidget(confidence_label, 0, 1)
        
        stats_layout.addWidget(QLabel("Word Count:"), 0, 2)
        stats_layout.addWidget(QLabel(str(self.ocr_results.word_count)), 0, 3)
        
        stats_layout.addWidget(QLabel("Processing Time:"), 1, 0)
        stats_layout.addWidget(QLabel(f"{self.ocr_results.processing_time:.3f}s"), 1, 1)
        
        stats_layout.addWidget(QLabel("OCR Engine:"), 1, 2)
        stats_layout.addWidget(QLabel(self.ocr_results.engine_used), 1, 3)
        
        low_confidence_count = len(self.ocr_results.low_confidence_words)
        stats_layout.addWidget(QLabel("Low Confidence Words:"), 2, 0)
        low_conf_label = QLabel(str(low_confidence_count))
        if low_confidence_count > 0:
            low_conf_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        stats_layout.addWidget(low_conf_label, 2, 1)
        
        stats_group.setLayout(stats_layout)
        analysis_layout.addWidget(stats_group)
        
        # Word-by-word analysis table
        words_group = QGroupBox("Word Analysis")
        words_layout = QVBoxLayout()
        
        self.confidence_table = QTableWidget()
        self.confidence_table.setColumnCount(4)
        self.confidence_table.setHorizontalHeaderLabels(["Word", "Confidence", "Position", "Bounding Box"])
        
        header = self.confidence_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        self.confidence_table.itemClicked.connect(self._word_table_clicked)
        
        words_layout.addWidget(self.confidence_table)
        words_group.setLayout(words_layout)
        analysis_layout.addWidget(words_group)
        
        # Quality metrics tree
        quality_group = QGroupBox("Quality Metrics")
        quality_layout = QVBoxLayout()
        
        self.quality_tree = QTreeWidget()
        self.quality_tree.setHeaderLabels(["Metric", "Value", "Assessment"])
        
        quality_layout.addWidget(self.quality_tree)
        quality_group.setLayout(quality_layout)
        analysis_layout.addWidget(quality_group)
        
        self.tab_widget.addTab(analysis_widget, "Analysis")
    
    def _create_settings_tab(self):
        """Create OCR settings tab."""
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        
        # Reprocessing options
        reprocess_group = QGroupBox("Reprocessing Options")
        reprocess_layout = QGridLayout()
        
        reprocess_layout.addWidget(QLabel("OCR Engine:"), 0, 0)
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["Auto", "Tesseract", "EasyOCR", "Azure", "Google"])
        reprocess_layout.addWidget(self.engine_combo, 0, 1)
        
        reprocess_layout.addWidget(QLabel("Language:"), 1, 0)
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Spanish", "French", "German", "Auto-detect"])
        reprocess_layout.addWidget(self.language_combo, 1, 1)
        
        self.preprocessing_checkbox = QCheckBox("Apply Image Preprocessing")
        self.preprocessing_checkbox.setChecked(True)
        reprocess_layout.addWidget(self.preprocessing_checkbox, 2, 0, 1, 2)
        
        reprocess_group.setLayout(reprocess_layout)
        settings_layout.addWidget(reprocess_group)
        
        # Enhancement options
        enhancement_group = QGroupBox("Text Enhancement")
        enhancement_layout = QVBoxLayout()
        
        self.auto_correct_checkbox = QCheckBox("Enable Auto-correction")
        self.auto_correct_checkbox.toggled.connect(self._toggle_auto_correct)
        enhancement_layout.addWidget(self.auto_correct_checkbox)
        
        self.spell_check_checkbox = QCheckBox("Enable Spell Check")
        enhancement_layout.addWidget(self.spell_check_checkbox)
        
        self.format_text_checkbox = QCheckBox("Auto-format Text")
        enhancement_layout.addWidget(self.format_text_checkbox)
        
        enhancement_group.setLayout(enhancement_layout)
        settings_layout.addWidget(enhancement_group)
        
        settings_layout.addStretch()
        
        self.tab_widget.addTab(settings_widget, "Settings")
    
    def _populate_content(self):
        """Populate dialog with OCR results."""
        # Set original text with highlighting
        self.original_text_edit.setPlainText(self.ocr_results.full_text)
        
        # Initialize highlighter
        if self._show_confidence:
            self.highlighter = OCRConfidenceHighlighter(self.ocr_results, self.original_text_edit.document())
        
        # Set edited text
        self.edited_text_edit.setPlainText(self.ocr_results.full_text)
        
        # Populate word analysis table
        self._populate_word_table()
        
        # Populate quality metrics
        self._populate_quality_metrics()
    
    def _populate_word_table(self):
        """Populate word analysis table."""
        self.confidence_table.setRowCount(len(self.ocr_results.words))
        
        for row, word in enumerate(self.ocr_results.words):
            # Word text
            word_item = QTableWidgetItem(word.text)
            word_item.setData(Qt.ItemDataRole.UserRole, word)
            self.confidence_table.setItem(row, 0, word_item)
            
            # Confidence with color coding
            confidence_item = QTableWidgetItem(f"{word.confidence:.1%}")
            confidence_item.setBackground(QColor(self._get_confidence_color(word.confidence)).lighter(180))
            self.confidence_table.setItem(row, 1, confidence_item)
            
            # Position
            pos_item = QTableWidgetItem(f"{word.position[0]}-{word.position[1]}")
            self.confidence_table.setItem(row, 2, pos_item)
            
            # Bounding box
            bbox_item = QTableWidgetItem(f"({word.bbox[0]}, {word.bbox[1]}, {word.bbox[2]}, {word.bbox[3]})")
            self.confidence_table.setItem(row, 3, bbox_item)
    
    def _populate_quality_metrics(self):
        """Populate quality metrics tree."""
        self.quality_tree.clear()
        
        # Basic metrics
        basic_item = QTreeWidgetItem(["Basic Metrics", "", ""])
        
        char_count = len(self.ocr_results.full_text)
        basic_item.addChild(QTreeWidgetItem(["Character Count", str(char_count), self._assess_char_count(char_count)]))
        
        word_count = self.ocr_results.word_count
        basic_item.addChild(QTreeWidgetItem(["Word Count", str(word_count), self._assess_word_count(word_count)]))
        
        avg_confidence = sum(w.confidence for w in self.ocr_results.words) / len(self.ocr_results.words) if self.ocr_results.words else 0
        basic_item.addChild(QTreeWidgetItem(["Average Confidence", f"{avg_confidence:.1%}", self._assess_confidence(avg_confidence)]))
        
        self.quality_tree.addTopLevelItem(basic_item)
        basic_item.setExpanded(True)
        
        # Confidence distribution
        dist_item = QTreeWidgetItem(["Confidence Distribution", "", ""])
        distribution = self.ocr_results.get_confidence_distribution()
        
        for level, count in distribution.items():
            percentage = (count / self.ocr_results.word_count * 100) if self.ocr_results.word_count > 0 else 0
            dist_item.addChild(QTreeWidgetItem([level.name.title(), f"{count} ({percentage:.1f}%)", ""]))
        
        self.quality_tree.addTopLevelItem(dist_item)
        dist_item.setExpanded(True)
    
    def _connect_signals(self):
        """Connect dialog signals."""
        pass  # Signals are connected in the UI creation methods
    
    def _toggle_confidence_highlighting(self, enabled: bool):
        """Toggle confidence highlighting on/off."""
        self._show_confidence = enabled
        
        if enabled and not self.highlighter:
            self.highlighter = OCRConfidenceHighlighter(self.ocr_results, self.original_text_edit.document())
        elif not enabled and self.highlighter:
            # Remove highlighting by setting a blank highlighter
            self.highlighter.setParent(None)
            self.highlighter = None
            # Re-render text without highlighting
            self.original_text_edit.setPlainText(self.ocr_results.full_text)
    
    def _threshold_changed(self, value: int):
        """Handle confidence threshold change."""
        self._confidence_threshold = value / 100.0
        self.threshold_value_label.setText(f"{value}%")
        
        # Update highlighting based on new threshold
        if self.highlighter:
            self.highlighter.rehighlight()
    
    def _text_modified(self):
        """Handle text modification."""
        self._modified = True
        self.setWindowTitle("OCR Text Review & Editing*")  # Add asterisk for modified
    
    def _toggle_auto_correct(self, enabled: bool):
        """Toggle auto-correction feature."""
        self._auto_correct = enabled
        
        if enabled:
            # Apply auto-corrections
            self._apply_auto_corrections()
    
    def _apply_auto_corrections(self):
        """Apply automatic text corrections."""
        text = self.edited_text_edit.toPlainText()
        
        # Simple auto-corrections (in real implementation, use proper spell check)
        corrections = {
            r'\b(\w+)\1+\b': r'\1',  # Remove repeated words
            r'\s+': ' ',             # Multiple spaces to single
            r'([.!?])\s*([a-z])': r'\1 \2'.upper(),  # Capitalize after punctuation
        }
        
        for pattern, replacement in corrections.items():
            text = re.sub(pattern, replacement, text)
        
        self.edited_text_edit.setPlainText(text)
    
    def _word_table_clicked(self, item):
        """Handle word table item click."""
        if item.column() == 0:  # Word column
            word = item.data(Qt.ItemDataRole.UserRole)
            if word:
                self.word_selected.emit(word)
                # Highlight word in text editors
                self._highlight_word_in_text(word)
    
    def _highlight_word_in_text(self, word: OCRWord):
        """Highlight selected word in text editors."""
        # Highlight in original text
        cursor = self.original_text_edit.textCursor()
        cursor.setPosition(word.position[0])
        cursor.setPosition(word.position[1], QTextCursor.MoveMode.KeepAnchor)
        self.original_text_edit.setTextCursor(cursor)
        
        # Highlight in edited text
        cursor = self.edited_text_edit.textCursor()
        cursor.setPosition(word.position[0])
        cursor.setPosition(word.position[1], QTextCursor.MoveMode.KeepAnchor)
        self.edited_text_edit.setTextCursor(cursor)
    
    def _reprocess_ocr(self):
        """Request OCR reprocessing with new settings."""
        settings = {
            "engine": self.engine_combo.currentText(),
            "language": self.language_combo.currentText(),
            "preprocessing": self.preprocessing_checkbox.isChecked(),
        }
        self.reprocess_requested.emit(settings)
    
    def _reset_changes(self):
        """Reset edited text to original."""
        self.edited_text_edit.setPlainText(self.ocr_results.full_text)
        self._modified = False
        self.setWindowTitle("OCR Text Review & Editing")
    
    def _delayed_update(self):
        """Delayed update for performance optimization."""
        # Batch UI updates for better performance
        pass
    
    def _get_confidence_color(self, confidence: float) -> str:
        """Get color for confidence level."""
        if confidence >= 0.9:
            return "#28a745"  # Green
        elif confidence >= 0.75:
            return "#17a2b8"  # Cyan  
        elif confidence >= 0.5:
            return "#ffc107"  # Yellow
        elif confidence >= 0.25:
            return "#fd7e14"  # Orange
        else:
            return "#dc3545"  # Red
    
    def _assess_char_count(self, count: int) -> str:
        """Assess character count quality."""
        if count < 10:
            return "Too short"
        elif count > 1000:
            return "Very long"
        else:
            return "Good"
    
    def _assess_word_count(self, count: int) -> str:
        """Assess word count quality."""
        if count < 3:
            return "Too few"
        elif count > 200:
            return "Very many"
        else:
            return "Good"
    
    def _assess_confidence(self, confidence: float) -> str:
        """Assess overall confidence."""
        if confidence >= 0.9:
            return "Excellent"
        elif confidence >= 0.75:
            return "Good"
        elif confidence >= 0.5:
            return "Fair"
        else:
            return "Poor"
    
    def get_final_text(self) -> str:
        """Get the final edited text."""
        return self.edited_text_edit.toPlainText()
    
    def accept(self):
        """Accept the OCR results."""
        final_text = self.get_final_text()
        self.text_accepted.emit(final_text)
        super().accept()
    
    def reject(self):
        """Reject the OCR results."""
        self.text_rejected.emit()
        super().reject()