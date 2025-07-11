#!/usr/bin/env python3
"""
Final validation widget with reading order indicators and flexible editing tools.
Provides the final review and editing interface for integrated content.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json
import re

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QTextEdit, 
    QTreeWidget, QTreeWidgetItem, QPushButton, QGroupBox, QProgressBar,
    QSplitter, QFrame, QGridLayout, QComboBox, QCheckBox, QSpinBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QListWidget, QListWidgetItem, QSlider, QLineEdit, QPlainTextEdit,
    QApplication, QAction, QMenu, QToolBar, QStatusBar, QFileDialog
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QMimeData, QPoint, QRect
from PyQt5.QtGui import (
    QFont, QColor, QPalette, QIcon, QTextCursor, QTextCharFormat, 
    QTextDocument, QTextOption, QPainter, QBrush, QPen, QDrag, QPixmap
)

from ...core.integration.content_integrator import (
    ContentIntegrator, IntegrationResult, IntegrationPoint, ContentType
)
from ...config.settings import Settings


class ReadingOrderIndicator(QWidget):
    """Widget to show reading order indicators."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.integration_points = []
        self.reading_order = []
        self.selected_point = None
        self.setMinimumSize(300, 200)
        
    def set_integration_data(self, integration_points: List[IntegrationPoint], reading_order: List[str]):
        """Set integration data for visualization."""
        self.integration_points = integration_points
        self.reading_order = reading_order
        self.update()
    
    def paintEvent(self, event):
        """Paint reading order visualization."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if not self.integration_points:
            painter.drawText(self.rect(), Qt.AlignCenter, "No integration points")
            return
        
        # Draw reading order flow
        self.draw_reading_order_flow(painter)
        
        # Draw integration points
        self.draw_integration_points(painter)
        
        painter.end()
    
    def draw_reading_order_flow(self, painter: QPainter):
        """Draw reading order flow lines."""
        if len(self.reading_order) < 2:
            return
        
        # Create point mapping
        point_map = {point.area_id: point for point in self.integration_points}
        
        # Draw flow lines
        painter.setPen(QPen(QColor(100, 150, 255), 2))
        
        for i in range(len(self.reading_order) - 1):
            current_id = self.reading_order[i]
            next_id = self.reading_order[i + 1]
            
            if current_id in point_map and next_id in point_map:
                current_point = point_map[current_id]
                next_point = point_map[next_id]
                
                # Convert positions to widget coordinates
                current_pos = self.position_to_widget_coords(current_point.position)
                next_pos = self.position_to_widget_coords(next_point.position)
                
                # Draw arrow
                painter.drawLine(current_pos, next_pos)
                
                # Draw arrowhead
                self.draw_arrowhead(painter, current_pos, next_pos)
    
    def draw_integration_points(self, painter: QPainter):
        """Draw integration points as colored circles."""
        point_map = {point.area_id: point for point in self.integration_points}
        
        for i, area_id in enumerate(self.reading_order):
            if area_id not in point_map:
                continue
                
            point = point_map[area_id]
            pos = self.position_to_widget_coords(point.position)
            
            # Color based on content type
            color = self.get_content_type_color(point.content_type)
            
            # Draw circle
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(Qt.black, 1))
            painter.drawEllipse(pos, 20, 20)
            
            # Draw order number
            painter.setPen(QPen(Qt.white))
            painter.drawText(pos.x() - 5, pos.y() + 5, str(i + 1))
    
    def position_to_widget_coords(self, position: Tuple[float, float, float, float]) -> QPoint:
        """Convert document position to widget coordinates."""
        # Simple mapping - in real implementation, this would consider page layout
        x = int((position[0] + position[2]) / 2 * self.width() / 1000)
        y = int((position[1] + position[3]) / 2 * self.height() / 1000)
        return QPoint(x, y)
    
    def get_content_type_color(self, content_type: ContentType) -> QColor:
        """Get color for content type."""
        color_map = {
            ContentType.TEXT: QColor(150, 150, 150),
            ContentType.TABLE: QColor(100, 150, 255),
            ContentType.IMAGE: QColor(255, 150, 100),
            ContentType.DIAGRAM: QColor(150, 255, 100),
            ContentType.CHART: QColor(255, 100, 150),
            ContentType.COMPLEX: QColor(200, 100, 255)
        }
        return color_map.get(content_type, QColor(100, 100, 100))
    
    def draw_arrowhead(self, painter: QPainter, start: QPoint, end: QPoint):
        """Draw arrowhead at end of line."""
        # Calculate arrow direction
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = (dx * dx + dy * dy) ** 0.5
        
        if length == 0:
            return
        
        # Normalize direction
        dx /= length
        dy /= length
        
        # Arrow parameters
        arrow_length = 10
        arrow_angle = 0.5
        
        # Calculate arrow points
        x1 = end.x() - arrow_length * (dx * 0.866 - dy * 0.5)
        y1 = end.y() - arrow_length * (dy * 0.866 + dx * 0.5)
        x2 = end.x() - arrow_length * (dx * 0.866 + dy * 0.5)
        y2 = end.y() - arrow_length * (dy * 0.866 - dx * 0.5)
        
        # Draw arrowhead
        painter.drawLine(end, QPoint(int(x1), int(y1)))
        painter.drawLine(end, QPoint(int(x2), int(y2)))
    
    def mousePressEvent(self, event):
        """Handle mouse press for point selection."""
        # Find clicked integration point
        for point in self.integration_points:
            pos = self.position_to_widget_coords(point.position)
            if (event.pos() - pos).manhattanLength() < 25:
                self.selected_point = point
                self.update()
                break


class EditableContentWidget(QPlainTextEdit):
    """Enhanced text editor with integration point highlighting."""
    
    content_changed = pyqtSignal(str)
    integration_point_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.integration_points = []
        self.reading_order = []
        self.highlighted_ranges = {}
        
        # Setup editor
        self.setup_editor()
        
        # Connect signals
        self.textChanged.connect(self.on_text_changed)
        self.cursorPositionChanged.connect(self.on_cursor_position_changed)
    
    def setup_editor(self):
        """Setup the editor appearance and behavior."""
        # Font
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)
        
        # Line wrapping
        self.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        
        # Tab width
        self.setTabStopWidth(40)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
    
    def set_integration_data(self, integration_points: List[IntegrationPoint], reading_order: List[str]):
        """Set integration data for highlighting."""
        self.integration_points = integration_points
        self.reading_order = reading_order
        self.update_highlighting()
    
    def update_highlighting(self):
        """Update integration point highlighting."""
        if not self.integration_points:
            return
        
        # Clear existing highlights
        self.highlighted_ranges.clear()
        
        # Create highlights for each integration point
        content = self.toPlainText()
        
        for i, point in enumerate(self.integration_points):
            # Find point content in text
            if point.original_text and point.original_text in content:
                start_pos = content.find(point.original_text)
                if start_pos != -1:
                    end_pos = start_pos + len(point.original_text)
                    
                    # Store highlight range
                    self.highlighted_ranges[point.area_id] = {
                        'start': start_pos,
                        'end': end_pos,
                        'point': point,
                        'order': i + 1
                    }
        
        # Apply highlighting
        self.apply_highlighting()
    
    def apply_highlighting(self):
        """Apply highlighting to integration points."""
        cursor = self.textCursor()
        
        for area_id, range_info in self.highlighted_ranges.items():
            point = range_info['point']
            start_pos = range_info['start']
            end_pos = range_info['end']
            order = range_info['order']
            
            # Create highlight format
            format = QTextCharFormat()
            color = self.get_content_type_color(point.content_type)
            format.setBackground(QBrush(color.lighter(160)))
            format.setForeground(QBrush(Qt.black))
            
            # Apply highlight
            cursor.setPosition(start_pos)
            cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
            cursor.mergeCharFormat(format)
    
    def get_content_type_color(self, content_type: ContentType) -> QColor:
        """Get color for content type."""
        color_map = {
            ContentType.TEXT: QColor(200, 200, 200),
            ContentType.TABLE: QColor(173, 216, 230),
            ContentType.IMAGE: QColor(255, 218, 185),
            ContentType.DIAGRAM: QColor(144, 238, 144),
            ContentType.CHART: QColor(255, 182, 193),
            ContentType.COMPLEX: QColor(221, 160, 221)
        }
        return color_map.get(content_type, QColor(220, 220, 220))
    
    def on_text_changed(self):
        """Handle text changes."""
        self.content_changed.emit(self.toPlainText())
    
    def on_cursor_position_changed(self):
        """Handle cursor position changes."""
        cursor_pos = self.textCursor().position()
        
        # Check if cursor is in an integration point
        for area_id, range_info in self.highlighted_ranges.items():
            if range_info['start'] <= cursor_pos <= range_info['end']:
                self.integration_point_clicked.emit(area_id)
                break
    
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        super().mousePressEvent(event)
        
        # Check for integration point clicks
        cursor = self.cursorForPosition(event.pos())
        cursor_pos = cursor.position()
        
        for area_id, range_info in self.highlighted_ranges.items():
            if range_info['start'] <= cursor_pos <= range_info['end']:
                self.integration_point_clicked.emit(area_id)
                break


class FinalValidationWidget(QWidget):
    """Final validation widget with reading order indicators and editing tools."""
    
    # Signals
    content_approved = pyqtSignal(dict)
    content_rejected = pyqtSignal(dict)
    content_modified = pyqtSignal(str)
    validation_completed = pyqtSignal(dict)
    
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Initialize integrator
        self.integrator = ContentIntegrator(settings)
        
        # Data storage
        self.integration_result = None
        self.original_content = ""
        self.modified_content = ""
        
        # Editing state
        self.is_editing = False
        self.changes_made = False
        self.auto_save_timer = QTimer()
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.timeout.connect(self.auto_save_changes)
        
        self.init_ui()
        self.setup_connections()
        
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Header section
        header_layout = self.create_header_section()
        layout.addLayout(header_layout)
        
        # Main content area
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Content editor
        left_panel = self.create_content_editor_panel()
        main_splitter.addWidget(left_panel)
        
        # Right panel - Reading order and tools
        right_panel = self.create_tools_panel()
        main_splitter.addWidget(right_panel)
        
        main_splitter.setSizes([600, 400])
        layout.addWidget(main_splitter)
        
        # Bottom panel - Actions and status
        bottom_panel = self.create_bottom_panel()
        layout.addWidget(bottom_panel)
        
        # Status bar
        self.status_label = QLabel("Ready for final validation")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.status_label)
        
    def create_header_section(self) -> QHBoxLayout:
        """Create header section with title and controls."""
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("Final Content Validation")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Edit mode toggle
        self.edit_mode_checkbox = QCheckBox("Edit Mode")
        self.edit_mode_checkbox.setChecked(False)
        header_layout.addWidget(self.edit_mode_checkbox)
        
        # Auto-save toggle
        self.auto_save_checkbox = QCheckBox("Auto-save")
        self.auto_save_checkbox.setChecked(True)
        header_layout.addWidget(self.auto_save_checkbox)
        
        # Auto-save delay
        delay_label = QLabel("Delay (s):")
        header_layout.addWidget(delay_label)
        
        self.auto_save_delay_spinbox = QSpinBox()
        self.auto_save_delay_spinbox.setRange(1, 60)
        self.auto_save_delay_spinbox.setValue(5)
        self.auto_save_delay_spinbox.setSuffix(" s")
        header_layout.addWidget(self.auto_save_delay_spinbox)
        
        # Validation button
        self.validate_button = QPushButton("Validate Content")
        self.validate_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        header_layout.addWidget(self.validate_button)
        
        return header_layout
    
    def create_content_editor_panel(self) -> QWidget:
        """Create content editor panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Editor toolbar
        toolbar_layout = QHBoxLayout()
        
        # Format tools
        self.bold_button = QPushButton("B")
        self.bold_button.setCheckable(True)
        self.bold_button.setMaximumWidth(30)
        toolbar_layout.addWidget(self.bold_button)
        
        self.italic_button = QPushButton("I")
        self.italic_button.setCheckable(True)
        self.italic_button.setMaximumWidth(30)
        toolbar_layout.addWidget(self.italic_button)
        
        toolbar_layout.addWidget(QLabel("|"))
        
        # Search and replace
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setMaximumWidth(150)
        toolbar_layout.addWidget(self.search_input)
        
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace...")
        self.replace_input.setMaximumWidth(150)
        toolbar_layout.addWidget(self.replace_input)
        
        self.replace_button = QPushButton("Replace")
        toolbar_layout.addWidget(self.replace_button)
        
        toolbar_layout.addStretch()
        
        # Zoom controls
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(50, 200)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setMaximumWidth(100)
        toolbar_layout.addWidget(self.zoom_slider)
        
        self.zoom_label = QLabel("100%")
        toolbar_layout.addWidget(self.zoom_label)
        
        layout.addLayout(toolbar_layout)
        
        # Content editor
        editor_group = QGroupBox("Integrated Content")
        editor_layout = QVBoxLayout(editor_group)
        
        self.content_editor = EditableContentWidget()
        self.content_editor.setReadOnly(True)  # Initially read-only
        editor_layout.addWidget(self.content_editor)
        
        # Editor status
        editor_status_layout = QHBoxLayout()
        
        self.word_count_label = QLabel("Words: 0")
        editor_status_layout.addWidget(self.word_count_label)
        
        self.char_count_label = QLabel("Characters: 0")
        editor_status_layout.addWidget(self.char_count_label)
        
        self.changes_indicator = QLabel("No changes")
        self.changes_indicator.setStyleSheet("color: #666;")
        editor_status_layout.addWidget(self.changes_indicator)
        
        editor_status_layout.addStretch()
        
        editor_layout.addLayout(editor_status_layout)
        
        layout.addWidget(editor_group)
        
        return panel
    
    def create_tools_panel(self) -> QWidget:
        """Create tools panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Tools tabs
        self.tools_tabs = QTabWidget()
        
        # Reading order tab
        reading_order_tab = self.create_reading_order_tab()
        self.tools_tabs.addTab(reading_order_tab, "Reading Order")
        
        # Integration points tab
        integration_points_tab = self.create_integration_points_tab()
        self.tools_tabs.addTab(integration_points_tab, "Integration Points")
        
        # Quality metrics tab
        quality_tab = self.create_quality_tab()
        self.tools_tabs.addTab(quality_tab, "Quality")
        
        # Export options tab
        export_tab = self.create_export_tab()
        self.tools_tabs.addTab(export_tab, "Export")
        
        layout.addWidget(self.tools_tabs)
        
        return panel
    
    def create_reading_order_tab(self) -> QWidget:
        """Create reading order tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Reading order visualization
        visualization_group = QGroupBox("Reading Order Visualization")
        visualization_layout = QVBoxLayout(visualization_group)
        
        self.reading_order_indicator = ReadingOrderIndicator()
        visualization_layout.addWidget(self.reading_order_indicator)
        
        layout.addWidget(visualization_group)
        
        # Reading order controls
        controls_group = QGroupBox("Reading Order Controls")
        controls_layout = QVBoxLayout(controls_group)
        
        # Order list
        self.reading_order_list = QListWidget()
        self.reading_order_list.setDragDropMode(QListWidget.InternalMove)
        controls_layout.addWidget(self.reading_order_list)
        
        # Order actions
        order_actions_layout = QHBoxLayout()
        
        self.move_up_button = QPushButton("Move Up")
        self.move_up_button.setEnabled(False)
        order_actions_layout.addWidget(self.move_up_button)
        
        self.move_down_button = QPushButton("Move Down")
        self.move_down_button.setEnabled(False)
        order_actions_layout.addWidget(self.move_down_button)
        
        order_actions_layout.addStretch()
        
        self.auto_order_button = QPushButton("Auto-order")
        order_actions_layout.addWidget(self.auto_order_button)
        
        controls_layout.addLayout(order_actions_layout)
        
        layout.addWidget(controls_group)
        
        return tab
    
    def create_integration_points_tab(self) -> QWidget:
        """Create integration points tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Integration points list
        points_group = QGroupBox("Integration Points")
        points_layout = QVBoxLayout(points_group)
        
        self.integration_points_table = QTableWidget()
        self.integration_points_table.setColumnCount(5)
        self.integration_points_table.setHorizontalHeaderLabels([
            "Area ID", "Type", "Method", "Priority", "Status"
        ])
        self.integration_points_table.setSelectionBehavior(QTableWidget.SelectRows)
        points_layout.addWidget(self.integration_points_table)
        
        # Point actions
        point_actions_layout = QHBoxLayout()
        
        self.edit_point_button = QPushButton("Edit Point")
        self.edit_point_button.setEnabled(False)
        point_actions_layout.addWidget(self.edit_point_button)
        
        self.remove_point_button = QPushButton("Remove Point")
        self.remove_point_button.setEnabled(False)
        point_actions_layout.addWidget(self.remove_point_button)
        
        point_actions_layout.addStretch()
        
        self.refresh_points_button = QPushButton("Refresh")
        point_actions_layout.addWidget(self.refresh_points_button)
        
        points_layout.addLayout(point_actions_layout)
        
        layout.addWidget(points_group)
        
        # Point details
        details_group = QGroupBox("Point Details")
        details_layout = QVBoxLayout(details_group)
        
        self.point_details_text = QTextEdit()
        self.point_details_text.setReadOnly(True)
        self.point_details_text.setMaximumHeight(150)
        details_layout.addWidget(self.point_details_text)
        
        layout.addWidget(details_group)
        
        return tab
    
    def create_quality_tab(self) -> QWidget:
        """Create quality metrics tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Quality metrics
        metrics_group = QGroupBox("Quality Metrics")
        metrics_layout = QGridLayout(metrics_group)
        
        self.overall_quality_label = QLabel("Overall Quality: --")
        metrics_layout.addWidget(self.overall_quality_label, 0, 0)
        
        self.overall_quality_progress = QProgressBar()
        self.overall_quality_progress.setRange(0, 100)
        metrics_layout.addWidget(self.overall_quality_progress, 0, 1)
        
        self.content_preservation_label = QLabel("Content Preservation: --")
        metrics_layout.addWidget(self.content_preservation_label, 1, 0)
        
        self.content_preservation_progress = QProgressBar()
        self.content_preservation_progress.setRange(0, 100)
        metrics_layout.addWidget(self.content_preservation_progress, 1, 1)
        
        self.integration_completeness_label = QLabel("Integration Completeness: --")
        metrics_layout.addWidget(self.integration_completeness_label, 2, 0)
        
        self.integration_completeness_progress = QProgressBar()
        self.integration_completeness_progress.setRange(0, 100)
        metrics_layout.addWidget(self.integration_completeness_progress, 2, 1)
        
        layout.addWidget(metrics_group)
        
        # Quality issues
        issues_group = QGroupBox("Quality Issues")
        issues_layout = QVBoxLayout(issues_group)
        
        self.quality_issues_list = QListWidget()
        issues_layout.addWidget(self.quality_issues_list)
        
        layout.addWidget(issues_group)
        
        layout.addStretch()
        
        return tab
    
    def create_export_tab(self) -> QWidget:
        """Create export options tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Export formats
        formats_group = QGroupBox("Export Formats")
        formats_layout = QVBoxLayout(formats_group)
        
        self.export_text_checkbox = QCheckBox("Plain Text (.txt)")
        self.export_text_checkbox.setChecked(True)
        formats_layout.addWidget(self.export_text_checkbox)
        
        self.export_markdown_checkbox = QCheckBox("Markdown (.md)")
        self.export_markdown_checkbox.setChecked(True)
        formats_layout.addWidget(self.export_markdown_checkbox)
        
        self.export_html_checkbox = QCheckBox("HTML (.html)")
        self.export_html_checkbox.setChecked(False)
        formats_layout.addWidget(self.export_html_checkbox)
        
        self.export_json_checkbox = QCheckBox("JSON (.json)")
        self.export_json_checkbox.setChecked(False)
        formats_layout.addWidget(self.export_json_checkbox)
        
        layout.addWidget(formats_group)
        
        # Export options
        options_group = QGroupBox("Export Options")
        options_layout = QVBoxLayout(options_group)
        
        self.include_metadata_checkbox = QCheckBox("Include metadata")
        self.include_metadata_checkbox.setChecked(False)
        options_layout.addWidget(self.include_metadata_checkbox)
        
        self.include_integration_info_checkbox = QCheckBox("Include integration info")
        self.include_integration_info_checkbox.setChecked(False)
        options_layout.addWidget(self.include_integration_info_checkbox)
        
        layout.addWidget(options_group)
        
        # Export actions
        export_actions_layout = QHBoxLayout()
        
        self.export_button = QPushButton("Export All")
        self.export_button.setEnabled(False)
        export_actions_layout.addWidget(self.export_button)
        
        self.export_current_button = QPushButton("Export Current")
        self.export_current_button.setEnabled(False)
        export_actions_layout.addWidget(self.export_current_button)
        
        layout.addLayout(export_actions_layout)
        
        layout.addStretch()
        
        return tab
    
    def create_bottom_panel(self) -> QWidget:
        """Create bottom panel with actions."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setStyleSheet("QFrame { background-color: #f5f5f5; }")
        
        layout = QHBoxLayout(panel)
        
        # Status summary
        summary_layout = QVBoxLayout()
        
        self.summary_label = QLabel("Content Status")
        summary_font = QFont()
        summary_font.setBold(True)
        self.summary_label.setFont(summary_font)
        summary_layout.addWidget(self.summary_label)
        
        self.summary_details_label = QLabel("No content loaded")
        summary_layout.addWidget(self.summary_details_label)
        
        layout.addLayout(summary_layout)
        
        layout.addStretch()
        
        # Action buttons
        actions_layout = QHBoxLayout()
        
        self.save_button = QPushButton("Save Changes")
        self.save_button.setEnabled(False)
        actions_layout.addWidget(self.save_button)
        
        self.revert_button = QPushButton("Revert Changes")
        self.revert_button.setEnabled(False)
        actions_layout.addWidget(self.revert_button)
        
        self.approve_button = QPushButton("Approve Content")
        self.approve_button.setEnabled(False)
        self.approve_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        actions_layout.addWidget(self.approve_button)
        
        self.reject_button = QPushButton("Reject Content")
        self.reject_button.setEnabled(False)
        self.reject_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        actions_layout.addWidget(self.reject_button)
        
        layout.addLayout(actions_layout)
        
        return panel
    
    def setup_connections(self):
        """Setup signal connections."""
        # Header controls
        self.edit_mode_checkbox.toggled.connect(self.toggle_edit_mode)
        self.auto_save_checkbox.toggled.connect(self.toggle_auto_save)
        self.auto_save_delay_spinbox.valueChanged.connect(self.update_auto_save_delay)
        self.validate_button.clicked.connect(self.validate_content)
        
        # Editor toolbar
        self.bold_button.clicked.connect(self.toggle_bold)
        self.italic_button.clicked.connect(self.toggle_italic)
        self.replace_button.clicked.connect(self.replace_text)
        self.zoom_slider.valueChanged.connect(self.update_zoom)
        
        # Content editor
        self.content_editor.content_changed.connect(self.on_content_changed)
        self.content_editor.integration_point_clicked.connect(self.on_integration_point_clicked)
        
        # Reading order
        self.reading_order_list.itemSelectionChanged.connect(self.on_reading_order_selection_changed)
        self.move_up_button.clicked.connect(self.move_item_up)
        self.move_down_button.clicked.connect(self.move_item_down)
        self.auto_order_button.clicked.connect(self.auto_order_items)
        
        # Integration points
        self.integration_points_table.itemSelectionChanged.connect(self.on_integration_point_selection_changed)
        self.edit_point_button.clicked.connect(self.edit_integration_point)
        self.remove_point_button.clicked.connect(self.remove_integration_point)
        self.refresh_points_button.clicked.connect(self.refresh_integration_points)
        
        # Export
        self.export_button.clicked.connect(self.export_all_formats)
        self.export_current_button.clicked.connect(self.export_current_format)
        
        # Bottom actions
        self.save_button.clicked.connect(self.save_changes)
        self.revert_button.clicked.connect(self.revert_changes)
        self.approve_button.clicked.connect(self.approve_content)
        self.reject_button.clicked.connect(self.reject_content)
    
    def set_integration_result(self, integration_result: IntegrationResult):
        """Set the integration result to validate."""
        self.integration_result = integration_result
        self.original_content = integration_result.integrated_content
        self.modified_content = integration_result.integrated_content
        
        # Update UI
        self.update_content_display()
        self.update_reading_order_display()
        self.update_integration_points_display()
        self.update_quality_display()
        self.update_summary()
        
        # Enable buttons
        self.validate_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.export_current_button.setEnabled(True)
        self.approve_button.setEnabled(True)
        self.reject_button.setEnabled(True)
        
        self.status_label.setText("Content loaded and ready for validation")
    
    def update_content_display(self):
        """Update content display."""
        if not self.integration_result:
            return
        
        # Set content
        self.content_editor.setPlainText(self.integration_result.integrated_content)
        
        # Set integration data for highlighting
        self.content_editor.set_integration_data(
            self.integration_result.integration_points,
            self.integration_result.reading_order
        )
        
        # Update word/character counts
        self.update_content_statistics()
    
    def update_reading_order_display(self):
        """Update reading order display."""
        if not self.integration_result:
            return
        
        # Update visualization
        self.reading_order_indicator.set_integration_data(
            self.integration_result.integration_points,
            self.integration_result.reading_order
        )
        
        # Update list
        self.reading_order_list.clear()
        point_map = {point.area_id: point for point in self.integration_result.integration_points}
        
        for area_id in self.integration_result.reading_order:
            if area_id in point_map:
                point = point_map[area_id]
                item = QListWidgetItem(f"{area_id} ({point.content_type.value})")
                item.setData(Qt.UserRole, area_id)
                self.reading_order_list.addItem(item)
    
    def update_integration_points_display(self):
        """Update integration points display."""
        if not self.integration_result:
            return
        
        # Update table
        points = self.integration_result.integration_points
        self.integration_points_table.setRowCount(len(points))
        
        for i, point in enumerate(points):
            self.integration_points_table.setItem(i, 0, QTableWidgetItem(point.area_id))
            self.integration_points_table.setItem(i, 1, QTableWidgetItem(point.content_type.value))
            self.integration_points_table.setItem(i, 2, QTableWidgetItem(point.integration_method.value))
            self.integration_points_table.setItem(i, 3, QTableWidgetItem(str(point.priority)))
            self.integration_points_table.setItem(i, 4, QTableWidgetItem("Integrated"))
    
    def update_quality_display(self):
        """Update quality metrics display."""
        if not self.integration_result:
            return
        
        # Overall quality
        quality_score = self.integration_result.quality_score
        self.overall_quality_progress.setValue(int(quality_score))
        self.overall_quality_label.setText(f"Overall Quality: {quality_score:.1f}%")
        
        # Content preservation and integration completeness
        metadata = self.integration_result.metadata
        validation_details = metadata.get('validation_details', {})
        
        preservation = validation_details.get('content_preservation', 0.0) * 100
        self.content_preservation_progress.setValue(int(preservation))
        self.content_preservation_label.setText(f"Content Preservation: {preservation:.1f}%")
        
        completeness = validation_details.get('integration_completeness', 0.0) * 100
        self.integration_completeness_progress.setValue(int(completeness))
        self.integration_completeness_label.setText(f"Integration Completeness: {completeness:.1f}%")
        
        # Quality issues
        self.quality_issues_list.clear()
        for issue in self.integration_result.issues:
            self.quality_issues_list.addItem(issue)
    
    def update_summary(self):
        """Update summary display."""
        if not self.integration_result:
            return
        
        num_points = len(self.integration_result.integration_points)
        quality_score = self.integration_result.quality_score
        
        self.summary_details_label.setText(
            f"Content loaded • {num_points} integration points • "
            f"Quality: {quality_score:.1f}% • "
            f"Status: {'Ready' if self.integration_result.success else 'Needs Review'}"
        )
    
    def update_content_statistics(self):
        """Update content statistics."""
        content = self.content_editor.toPlainText()
        word_count = len(content.split())
        char_count = len(content)
        
        self.word_count_label.setText(f"Words: {word_count}")
        self.char_count_label.setText(f"Characters: {char_count}")
    
    def toggle_edit_mode(self, enabled: bool):
        """Toggle edit mode."""
        self.is_editing = enabled
        self.content_editor.setReadOnly(not enabled)
        
        if enabled:
            self.changes_indicator.setText("Edit mode enabled")
            self.changes_indicator.setStyleSheet("color: #FF9800;")
        else:
            self.changes_indicator.setText("Read-only mode")
            self.changes_indicator.setStyleSheet("color: #666;")
    
    def toggle_auto_save(self, enabled: bool):
        """Toggle auto-save."""
        if enabled:
            self.auto_save_timer.start(self.auto_save_delay_spinbox.value() * 1000)
        else:
            self.auto_save_timer.stop()
    
    def update_auto_save_delay(self, delay: int):
        """Update auto-save delay."""
        if self.auto_save_checkbox.isChecked():
            self.auto_save_timer.start(delay * 1000)
    
    def on_content_changed(self, content: str):
        """Handle content changes."""
        self.modified_content = content
        self.changes_made = True
        
        # Update statistics
        self.update_content_statistics()
        
        # Update changes indicator
        self.changes_indicator.setText("Changes made")
        self.changes_indicator.setStyleSheet("color: #FF5722;")
        
        # Enable save/revert buttons
        self.save_button.setEnabled(True)
        self.revert_button.setEnabled(True)
        
        # Schedule auto-save
        if self.auto_save_checkbox.isChecked():
            self.auto_save_timer.start(self.auto_save_delay_spinbox.value() * 1000)
        
        # Emit signal
        self.content_modified.emit(content)
    
    def on_integration_point_clicked(self, area_id: str):
        """Handle integration point clicks."""
        # Find and select the point in the table
        for row in range(self.integration_points_table.rowCount()):
            item = self.integration_points_table.item(row, 0)
            if item and item.text() == area_id:
                self.integration_points_table.selectRow(row)
                self.tools_tabs.setCurrentIndex(1)  # Switch to integration points tab
                break
    
    def on_reading_order_selection_changed(self):
        """Handle reading order selection changes."""
        current_item = self.reading_order_list.currentItem()
        if current_item:
            self.move_up_button.setEnabled(self.reading_order_list.currentRow() > 0)
            self.move_down_button.setEnabled(
                self.reading_order_list.currentRow() < self.reading_order_list.count() - 1
            )
        else:
            self.move_up_button.setEnabled(False)
            self.move_down_button.setEnabled(False)
    
    def on_integration_point_selection_changed(self):
        """Handle integration point selection changes."""
        current_row = self.integration_points_table.currentRow()
        if current_row >= 0:
            self.edit_point_button.setEnabled(True)
            self.remove_point_button.setEnabled(True)
            
            # Show point details
            if self.integration_result and current_row < len(self.integration_result.integration_points):
                point = self.integration_result.integration_points[current_row]
                details = f"Area ID: {point.area_id}\n"
                details += f"Content Type: {point.content_type.value}\n"
                details += f"Integration Method: {point.integration_method.value}\n"
                details += f"Page: {point.page_number}\n"
                details += f"Position: {point.position}\n"
                details += f"Priority: {point.priority}\n"
                details += f"Original Text: {point.original_text[:200]}..."
                
                self.point_details_text.setText(details)
        else:
            self.edit_point_button.setEnabled(False)
            self.remove_point_button.setEnabled(False)
            self.point_details_text.clear()
    
    def auto_save_changes(self):
        """Auto-save changes."""
        if self.changes_made:
            self.save_changes()
    
    def save_changes(self):
        """Save changes."""
        if not self.changes_made:
            return
        
        # Update integration result
        if self.integration_result:
            self.integration_result.integrated_content = self.modified_content
            self.original_content = self.modified_content
        
        # Reset change tracking
        self.changes_made = False
        self.changes_indicator.setText("Changes saved")
        self.changes_indicator.setStyleSheet("color: #4CAF50;")
        
        # Disable save/revert buttons
        self.save_button.setEnabled(False)
        self.revert_button.setEnabled(False)
        
        self.status_label.setText("Changes saved")
        
        # Reset timer
        QTimer.singleShot(3000, lambda: self.changes_indicator.setText("No changes"))
    
    def revert_changes(self):
        """Revert changes."""
        if not self.changes_made:
            return
        
        # Revert content
        self.content_editor.setPlainText(self.original_content)
        self.modified_content = self.original_content
        
        # Reset change tracking
        self.changes_made = False
        self.changes_indicator.setText("Changes reverted")
        self.changes_indicator.setStyleSheet("color: #FF9800;")
        
        # Disable save/revert buttons
        self.save_button.setEnabled(False)
        self.revert_button.setEnabled(False)
        
        self.status_label.setText("Changes reverted")
        
        # Reset timer
        QTimer.singleShot(3000, lambda: self.changes_indicator.setText("No changes"))
    
    def validate_content(self):
        """Validate current content."""
        if not self.integration_result:
            return
        
        try:
            # Create new integration result with current content
            validated_result = IntegrationResult(
                success=True,
                integrated_content=self.modified_content,
                integration_points=self.integration_result.integration_points,
                reading_order=self.integration_result.reading_order,
                quality_score=self.integration_result.quality_score,
                metadata=self.integration_result.metadata
            )
            
            # Emit validation completed signal
            self.validation_completed.emit({
                'integration_result': validated_result,
                'changes_made': self.changes_made,
                'word_count': len(self.modified_content.split()),
                'char_count': len(self.modified_content)
            })
            
            self.status_label.setText("Content validation completed")
            
        except Exception as e:
            self.logger.error(f"Content validation failed: {e}")
            QMessageBox.critical(self, "Validation Error", f"Content validation failed: {str(e)}")
    
    def approve_content(self):
        """Approve the content."""
        if not self.integration_result:
            return
        
        reply = QMessageBox.question(
            self, "Approve Content",
            "Are you sure you want to approve this content?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Save any pending changes
            if self.changes_made:
                self.save_changes()
            
            # Emit approval signal
            self.content_approved.emit({
                'integration_result': self.integration_result,
                'final_content': self.modified_content,
                'timestamp': time.time()
            })
            
            self.status_label.setText("Content approved")
    
    def reject_content(self):
        """Reject the content."""
        if not self.integration_result:
            return
        
        reply = QMessageBox.question(
            self, "Reject Content",
            "Are you sure you want to reject this content?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Emit rejection signal
            self.content_rejected.emit({
                'integration_result': self.integration_result,
                'rejection_reason': 'Manual rejection',
                'timestamp': time.time()
            })
            
            self.status_label.setText("Content rejected")
    
    def export_all_formats(self):
        """Export content in all selected formats."""
        if not self.integration_result:
            return
        
        try:
            # Get export directory
            export_dir = QFileDialog.getExistingDirectory(
                self, "Select Export Directory", str(Path.home())
            )
            
            if not export_dir:
                return
            
            export_path = Path(export_dir)
            
            # Generate formats
            formats = self.integrator.generate_output_formats(self.integration_result)
            
            # Export selected formats
            exported_files = []
            
            if self.export_text_checkbox.isChecked():
                text_file = export_path / "content.txt"
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(formats.get('text', self.modified_content))
                exported_files.append(text_file)
            
            if self.export_markdown_checkbox.isChecked():
                md_file = export_path / "content.md"
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(formats.get('markdown', self.modified_content))
                exported_files.append(md_file)
            
            if self.export_html_checkbox.isChecked():
                html_file = export_path / "content.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(formats.get('html', self.modified_content))
                exported_files.append(html_file)
            
            if self.export_json_checkbox.isChecked():
                json_file = export_path / "content.json"
                with open(json_file, 'w', encoding='utf-8') as f:
                    f.write(formats.get('json', '{}'))
                exported_files.append(json_file)
            
            # Show success message
            files_list = '\n'.join(str(f) for f in exported_files)
            QMessageBox.information(
                self, "Export Successful",
                f"Content exported to:\n{files_list}"
            )
            
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            QMessageBox.critical(self, "Export Error", f"Export failed: {str(e)}")
    
    def export_current_format(self):
        """Export content in current format."""
        if not self.integration_result:
            return
        
        try:
            # Get export file
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Content", "content.txt",
                "Text Files (*.txt);;Markdown Files (*.md);;HTML Files (*.html);;JSON Files (*.json);;All Files (*)"
            )
            
            if not file_path:
                return
            
            # Determine format from extension
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.md':
                formats = self.integrator.generate_output_formats(self.integration_result)
                content = formats.get('markdown', self.modified_content)
            elif file_ext == '.html':
                formats = self.integrator.generate_output_formats(self.integration_result)
                content = formats.get('html', self.modified_content)
            elif file_ext == '.json':
                formats = self.integrator.generate_output_formats(self.integration_result)
                content = formats.get('json', '{}')
            else:
                content = self.modified_content
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            QMessageBox.information(
                self, "Export Successful",
                f"Content exported to {file_path}"
            )
            
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            QMessageBox.critical(self, "Export Error", f"Export failed: {str(e)}")
    
    def move_item_up(self):
        """Move selected item up in reading order."""
        current_row = self.reading_order_list.currentRow()
        if current_row > 0:
            item = self.reading_order_list.takeItem(current_row)
            self.reading_order_list.insertItem(current_row - 1, item)
            self.reading_order_list.setCurrentRow(current_row - 1)
            self.update_reading_order_from_list()
    
    def move_item_down(self):
        """Move selected item down in reading order."""
        current_row = self.reading_order_list.currentRow()
        if current_row < self.reading_order_list.count() - 1:
            item = self.reading_order_list.takeItem(current_row)
            self.reading_order_list.insertItem(current_row + 1, item)
            self.reading_order_list.setCurrentRow(current_row + 1)
            self.update_reading_order_from_list()
    
    def auto_order_items(self):
        """Automatically order items based on position."""
        if not self.integration_result:
            return
        
        # Re-determine reading order
        integration_points = self.integration_result.integration_points
        reading_order = self.integrator._determine_reading_order(integration_points)
        
        # Update integration result
        self.integration_result.reading_order = reading_order
        
        # Update displays
        self.update_reading_order_display()
        self.content_editor.set_integration_data(integration_points, reading_order)
        self.reading_order_indicator.set_integration_data(integration_points, reading_order)
    
    def update_reading_order_from_list(self):
        """Update reading order from list widget."""
        if not self.integration_result:
            return
        
        # Get new order from list
        new_order = []
        for i in range(self.reading_order_list.count()):
            item = self.reading_order_list.item(i)
            area_id = item.data(Qt.UserRole)
            new_order.append(area_id)
        
        # Update integration result
        self.integration_result.reading_order = new_order
        
        # Update displays
        self.content_editor.set_integration_data(
            self.integration_result.integration_points, new_order
        )
        self.reading_order_indicator.set_integration_data(
            self.integration_result.integration_points, new_order
        )
    
    def edit_integration_point(self):
        """Edit selected integration point."""
        # This would open a dialog to edit the integration point
        QMessageBox.information(self, "Edit Point", "Integration point editing not yet implemented")
    
    def remove_integration_point(self):
        """Remove selected integration point."""
        current_row = self.integration_points_table.currentRow()
        if current_row >= 0 and self.integration_result:
            reply = QMessageBox.question(
                self, "Remove Integration Point",
                "Are you sure you want to remove this integration point?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Remove from integration result
                self.integration_result.integration_points.pop(current_row)
                
                # Update displays
                self.update_integration_points_display()
                self.update_reading_order_display()
                self.content_editor.set_integration_data(
                    self.integration_result.integration_points,
                    self.integration_result.reading_order
                )
    
    def refresh_integration_points(self):
        """Refresh integration points display."""
        self.update_integration_points_display()
        self.update_reading_order_display()
        if self.integration_result:
            self.content_editor.set_integration_data(
                self.integration_result.integration_points,
                self.integration_result.reading_order
            )
    
    def toggle_bold(self):
        """Toggle bold formatting."""
        if not self.is_editing:
            return
        
        cursor = self.content_editor.textCursor()
        format = cursor.charFormat()
        
        if format.fontWeight() == QFont.Bold:
            format.setFontWeight(QFont.Normal)
        else:
            format.setFontWeight(QFont.Bold)
        
        cursor.mergeCharFormat(format)
        self.content_editor.setTextCursor(cursor)
    
    def toggle_italic(self):
        """Toggle italic formatting."""
        if not self.is_editing:
            return
        
        cursor = self.content_editor.textCursor()
        format = cursor.charFormat()
        format.setFontItalic(not format.fontItalic())
        cursor.mergeCharFormat(format)
        self.content_editor.setTextCursor(cursor)
    
    def replace_text(self):
        """Replace text."""
        if not self.is_editing:
            return
        
        search_text = self.search_input.text()
        replace_text = self.replace_input.text()
        
        if not search_text:
            return
        
        content = self.content_editor.toPlainText()
        new_content = content.replace(search_text, replace_text)
        self.content_editor.setPlainText(new_content)
    
    def update_zoom(self, value: int):
        """Update zoom level."""
        self.zoom_label.setText(f"{value}%")
        
        # Update font size
        font = self.content_editor.font()
        base_size = 11
        new_size = int(base_size * value / 100)
        font.setPointSize(new_size)
        self.content_editor.setFont(font)