#!/usr/bin/env python3
"""
Special area validation widget for validating text formatting, positioning, and reading order.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QTextEdit, 
    QTreeWidget, QTreeWidgetItem, QPushButton, QGroupBox, QProgressBar,
    QSplitter, QFrame, QGridLayout, QComboBox, QCheckBox, QSpinBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

from ...core.validation.special_area_validator import SpecialAreaValidator, ValidationSeverity, ValidationIssue
from ...core.specialized_toolsets import (
    TableToolset, ImageToolset, DiagramToolset, ChartToolset, ComplexToolset
)
from ...config.settings import Settings


class SpecialAreaValidationWidget(QWidget):
    """Widget for validating special area extractions."""
    
    # Signals
    validation_updated = pyqtSignal(dict)
    area_selected = pyqtSignal(str)
    validation_completed = pyqtSignal(dict)
    
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Initialize validator and toolsets
        self.validator = SpecialAreaValidator(settings)
        self.toolsets = {
            'TABLE': TableToolset(settings),
            'IMAGE': ImageToolset(settings),
            'DIAGRAM': DiagramToolset(settings),
            'CHART': ChartToolset(settings),
            'COMPLEX': ComplexToolset(settings)
        }
        
        # Data storage
        self.current_areas = []
        self.validation_results = {}
        self.pdf_document = None
        
        # Auto-validation settings
        self.auto_validation_enabled = True
        self.validation_timer = QTimer()
        self.validation_timer.setSingleShot(True)
        self.validation_timer.timeout.connect(self.perform_validation)
        
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
        
        # Left panel - Area list and controls
        left_panel = self.create_left_panel()
        main_splitter.addWidget(left_panel)
        
        # Right panel - Validation details
        right_panel = self.create_right_panel()
        main_splitter.addWidget(right_panel)
        
        main_splitter.setSizes([300, 700])
        layout.addWidget(main_splitter)
        
        # Bottom panel - Summary and actions
        bottom_panel = self.create_bottom_panel()
        layout.addWidget(bottom_panel)
        
        # Status bar
        self.status_label = QLabel("Ready for validation")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.status_label)
        
    def create_header_section(self) -> QHBoxLayout:
        """Create header section with title and controls."""
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("Special Area Validation")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Auto-validation toggle
        self.auto_validation_checkbox = QCheckBox("Auto-validate")
        self.auto_validation_checkbox.setChecked(self.auto_validation_enabled)
        header_layout.addWidget(self.auto_validation_checkbox)
        
        # Validation delay
        delay_label = QLabel("Delay (ms):")
        header_layout.addWidget(delay_label)
        
        self.validation_delay_spinbox = QSpinBox()
        self.validation_delay_spinbox.setRange(100, 5000)
        self.validation_delay_spinbox.setValue(500)
        self.validation_delay_spinbox.setSuffix(" ms")
        header_layout.addWidget(self.validation_delay_spinbox)
        
        # Manual validation button
        self.validate_button = QPushButton("Validate All")
        self.validate_button.setStyleSheet("""
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
        """)
        header_layout.addWidget(self.validate_button)
        
        return header_layout
    
    def create_left_panel(self) -> QWidget:
        """Create left panel with area list and controls."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Area list
        areas_group = QGroupBox("Special Areas")
        areas_layout = QVBoxLayout(areas_group)
        
        self.areas_tree = QTreeWidget()
        self.areas_tree.setHeaderLabels(["Area", "Type", "Status", "Quality"])
        self.areas_tree.setRootIsDecorated(False)
        self.areas_tree.setAlternatingRowColors(True)
        areas_layout.addWidget(self.areas_tree)
        
        # Area actions
        area_actions_layout = QHBoxLayout()
        
        self.revalidate_button = QPushButton("Re-validate")
        self.revalidate_button.setEnabled(False)
        area_actions_layout.addWidget(self.revalidate_button)
        
        self.auto_fix_button = QPushButton("Auto-fix")
        self.auto_fix_button.setEnabled(False)
        area_actions_layout.addWidget(self.auto_fix_button)
        
        area_actions_layout.addStretch()
        areas_layout.addLayout(area_actions_layout)
        
        layout.addWidget(areas_group)
        
        # Reading order validation
        reading_order_group = QGroupBox("Reading Order")
        reading_order_layout = QVBoxLayout(reading_order_group)
        
        self.reading_order_score_label = QLabel("Score: --")
        reading_order_layout.addWidget(self.reading_order_score_label)
        
        self.reading_order_progress = QProgressBar()
        self.reading_order_progress.setRange(0, 100)
        reading_order_layout.addWidget(self.reading_order_progress)
        
        reading_order_actions_layout = QHBoxLayout()
        
        self.validate_reading_order_button = QPushButton("Validate Order")
        reading_order_actions_layout.addWidget(self.validate_reading_order_button)
        
        self.optimize_order_button = QPushButton("Optimize")
        reading_order_actions_layout.addWidget(self.optimize_order_button)
        
        reading_order_layout.addLayout(reading_order_actions_layout)
        
        layout.addWidget(reading_order_group)
        
        # Validation settings
        settings_group = QGroupBox("Validation Settings")
        settings_layout = QGridLayout(settings_group)
        
        # Validation rules
        settings_layout.addWidget(QLabel("Text Formatting:"), 0, 0)
        self.text_formatting_checkbox = QCheckBox("Enabled")
        self.text_formatting_checkbox.setChecked(True)
        settings_layout.addWidget(self.text_formatting_checkbox, 0, 1)
        
        settings_layout.addWidget(QLabel("Positioning:"), 1, 0)
        self.positioning_checkbox = QCheckBox("Enabled")
        self.positioning_checkbox.setChecked(True)
        settings_layout.addWidget(self.positioning_checkbox, 1, 1)
        
        settings_layout.addWidget(QLabel("Reading Order:"), 2, 0)
        self.reading_order_checkbox = QCheckBox("Enabled")
        self.reading_order_checkbox.setChecked(True)
        settings_layout.addWidget(self.reading_order_checkbox, 2, 1)
        
        settings_layout.addWidget(QLabel("Auto-fix:"), 3, 0)
        self.auto_fix_checkbox = QCheckBox("Enabled")
        self.auto_fix_checkbox.setChecked(False)
        settings_layout.addWidget(self.auto_fix_checkbox, 3, 1)
        
        layout.addWidget(settings_group)
        
        layout.addStretch()
        
        return panel
    
    def create_right_panel(self) -> QWidget:
        """Create right panel with validation details."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Validation details tabs
        self.details_tabs = QTabWidget()
        
        # Issues tab
        issues_tab = self.create_issues_tab()
        self.details_tabs.addTab(issues_tab, "Issues")
        
        # Metrics tab
        metrics_tab = self.create_metrics_tab()
        self.details_tabs.addTab(metrics_tab, "Metrics")
        
        # Recommendations tab
        recommendations_tab = self.create_recommendations_tab()
        self.details_tabs.addTab(recommendations_tab, "Recommendations")
        
        # Auto-fixes tab
        auto_fixes_tab = self.create_auto_fixes_tab()
        self.details_tabs.addTab(auto_fixes_tab, "Auto-fixes")
        
        layout.addWidget(self.details_tabs)
        
        return panel
    
    def create_issues_tab(self) -> QWidget:
        """Create issues tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Issues filter
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Filter by severity:"))
        
        self.severity_filter = QComboBox()
        self.severity_filter.addItems(["All", "Critical", "Major", "Minor", "Info"])
        filter_layout.addWidget(self.severity_filter)
        
        filter_layout.addStretch()
        
        # Issues count
        self.issues_count_label = QLabel("Issues: 0")
        filter_layout.addWidget(self.issues_count_label)
        
        layout.addLayout(filter_layout)
        
        # Issues table
        self.issues_table = QTableWidget()
        self.issues_table.setColumnCount(5)
        self.issues_table.setHorizontalHeaderLabels(["Severity", "Type", "Message", "Location", "Suggestion"])
        
        # Set column widths
        header = self.issues_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.issues_table)
        
        # Issue details
        details_group = QGroupBox("Issue Details")
        details_layout = QVBoxLayout(details_group)
        
        self.issue_details_text = QTextEdit()
        self.issue_details_text.setReadOnly(True)
        self.issue_details_text.setMaximumHeight(100)
        details_layout.addWidget(self.issue_details_text)
        
        layout.addWidget(details_group)
        
        return tab
    
    def create_metrics_tab(self) -> QWidget:
        """Create metrics tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Quality metrics
        quality_group = QGroupBox("Quality Metrics")
        quality_layout = QGridLayout(quality_group)
        
        self.overall_quality_label = QLabel("Overall Quality: --")
        quality_layout.addWidget(self.overall_quality_label, 0, 0)
        
        self.overall_quality_progress = QProgressBar()
        self.overall_quality_progress.setRange(0, 100)
        quality_layout.addWidget(self.overall_quality_progress, 0, 1)
        
        self.confidence_label = QLabel("Confidence: --")
        quality_layout.addWidget(self.confidence_label, 1, 0)
        
        self.confidence_progress = QProgressBar()
        self.confidence_progress.setRange(0, 100)
        quality_layout.addWidget(self.confidence_progress, 1, 1)
        
        layout.addWidget(quality_group)
        
        # Validation metrics
        validation_group = QGroupBox("Validation Metrics")
        validation_layout = QGridLayout(validation_group)
        
        self.validations_performed_label = QLabel("Validations Performed: 0")
        validation_layout.addWidget(self.validations_performed_label, 0, 0)
        
        self.issues_found_label = QLabel("Issues Found: 0")
        validation_layout.addWidget(self.issues_found_label, 0, 1)
        
        self.auto_fixes_applied_label = QLabel("Auto-fixes Applied: 0")
        validation_layout.addWidget(self.auto_fixes_applied_label, 1, 0)
        
        self.validation_time_label = QLabel("Validation Time: 0.0s")
        validation_layout.addWidget(self.validation_time_label, 1, 1)
        
        layout.addWidget(validation_group)
        
        # Area-specific metrics
        area_metrics_group = QGroupBox("Area-specific Metrics")
        area_metrics_layout = QVBoxLayout(area_metrics_group)
        
        self.area_metrics_table = QTableWidget()
        self.area_metrics_table.setColumnCount(4)
        self.area_metrics_table.setHorizontalHeaderLabels(["Area", "Quality", "Issues", "Confidence"])
        area_metrics_layout.addWidget(self.area_metrics_table)
        
        layout.addWidget(area_metrics_group)
        
        layout.addStretch()
        
        return tab
    
    def create_recommendations_tab(self) -> QWidget:
        """Create recommendations tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Recommendations list
        recommendations_group = QGroupBox("Recommendations")
        recommendations_layout = QVBoxLayout(recommendations_group)
        
        self.recommendations_text = QTextEdit()
        self.recommendations_text.setReadOnly(True)
        recommendations_layout.addWidget(self.recommendations_text)
        
        layout.addWidget(recommendations_group)
        
        # Action buttons
        actions_layout = QHBoxLayout()
        
        self.apply_recommendations_button = QPushButton("Apply Recommendations")
        self.apply_recommendations_button.setEnabled(False)
        actions_layout.addWidget(self.apply_recommendations_button)
        
        self.export_recommendations_button = QPushButton("Export Report")
        actions_layout.addWidget(self.export_recommendations_button)
        
        actions_layout.addStretch()
        
        layout.addLayout(actions_layout)
        
        return tab
    
    def create_auto_fixes_tab(self) -> QWidget:
        """Create auto-fixes tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Auto-fixes list
        auto_fixes_group = QGroupBox("Applied Auto-fixes")
        auto_fixes_layout = QVBoxLayout(auto_fixes_group)
        
        self.auto_fixes_table = QTableWidget()
        self.auto_fixes_table.setColumnCount(3)
        self.auto_fixes_table.setHorizontalHeaderLabels(["Issue Type", "Fix Description", "Timestamp"])
        auto_fixes_layout.addWidget(self.auto_fixes_table)
        
        layout.addWidget(auto_fixes_group)
        
        # Auto-fix controls
        controls_layout = QHBoxLayout()
        
        self.undo_auto_fix_button = QPushButton("Undo Last Fix")
        self.undo_auto_fix_button.setEnabled(False)
        controls_layout.addWidget(self.undo_auto_fix_button)
        
        self.clear_auto_fixes_button = QPushButton("Clear All")
        controls_layout.addWidget(self.clear_auto_fixes_button)
        
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        return tab
    
    def create_bottom_panel(self) -> QWidget:
        """Create bottom panel with summary and actions."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setStyleSheet("QFrame { background-color: #f5f5f5; }")
        
        layout = QHBoxLayout(panel)
        
        # Summary
        summary_layout = QVBoxLayout()
        
        self.summary_label = QLabel("Validation Summary")
        summary_font = QFont()
        summary_font.setBold(True)
        self.summary_label.setFont(summary_font)
        summary_layout.addWidget(self.summary_label)
        
        self.summary_details_label = QLabel("No areas validated yet")
        summary_layout.addWidget(self.summary_details_label)
        
        layout.addLayout(summary_layout)
        
        layout.addStretch()
        
        # Action buttons
        actions_layout = QHBoxLayout()
        
        self.approve_all_button = QPushButton("Approve All")
        self.approve_all_button.setEnabled(False)
        self.approve_all_button.setStyleSheet("""
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
        actions_layout.addWidget(self.approve_all_button)
        
        self.reject_all_button = QPushButton("Reject All")
        self.reject_all_button.setEnabled(False)
        self.reject_all_button.setStyleSheet("""
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
        actions_layout.addWidget(self.reject_all_button)
        
        self.export_results_button = QPushButton("Export Results")
        actions_layout.addWidget(self.export_results_button)
        
        layout.addLayout(actions_layout)
        
        return panel
    
    def setup_connections(self):
        """Setup signal connections."""
        # Header controls
        self.auto_validation_checkbox.toggled.connect(self.toggle_auto_validation)
        self.validation_delay_spinbox.valueChanged.connect(self.update_validation_delay)
        self.validate_button.clicked.connect(self.perform_validation)
        
        # Area actions
        self.areas_tree.itemSelectionChanged.connect(self.on_area_selection_changed)
        self.revalidate_button.clicked.connect(self.revalidate_selected_area)
        self.auto_fix_button.clicked.connect(self.auto_fix_selected_area)
        
        # Reading order
        self.validate_reading_order_button.clicked.connect(self.validate_reading_order)
        self.optimize_order_button.clicked.connect(self.optimize_reading_order)
        
        # Validation settings
        self.text_formatting_checkbox.toggled.connect(self.update_validation_settings)
        self.positioning_checkbox.toggled.connect(self.update_validation_settings)
        self.reading_order_checkbox.toggled.connect(self.update_validation_settings)
        self.auto_fix_checkbox.toggled.connect(self.update_validation_settings)
        
        # Issues table
        self.severity_filter.currentTextChanged.connect(self.filter_issues)
        self.issues_table.itemSelectionChanged.connect(self.on_issue_selection_changed)
        
        # Action buttons
        self.approve_all_button.clicked.connect(self.approve_all_areas)
        self.reject_all_button.clicked.connect(self.reject_all_areas)
        self.export_results_button.clicked.connect(self.export_validation_results)
        
        # Auto-fixes
        self.undo_auto_fix_button.clicked.connect(self.undo_last_auto_fix)
        self.clear_auto_fixes_button.clicked.connect(self.clear_auto_fixes)
        
        # Recommendations
        self.apply_recommendations_button.clicked.connect(self.apply_recommendations)
        self.export_recommendations_button.clicked.connect(self.export_recommendations)
    
    def set_areas(self, areas: List[Dict], pdf_document=None):
        """Set the areas to validate."""
        self.current_areas = areas
        self.pdf_document = pdf_document
        self.validation_results = {}
        
        # Update UI
        self.update_areas_tree()
        self.clear_validation_display()
        
        # Trigger validation if auto-validation is enabled
        if self.auto_validation_enabled:
            self.schedule_validation()
    
    def update_areas_tree(self):
        """Update the areas tree widget."""
        self.areas_tree.clear()
        
        for i, area in enumerate(self.current_areas):
            item = QTreeWidgetItem(self.areas_tree)
            item.setText(0, area.get('id', f"Area {i+1}"))
            item.setText(1, area.get('type', 'Unknown'))
            item.setText(2, "Pending")
            item.setText(3, "--")
            item.setData(0, Qt.UserRole, area)
            
            # Color coding by type
            area_type = area.get('type', '').upper()
            if area_type == 'TABLE':
                item.setBackground(0, QColor(220, 245, 255))
            elif area_type == 'IMAGE':
                item.setBackground(0, QColor(255, 245, 220))
            elif area_type == 'DIAGRAM':
                item.setBackground(0, QColor(245, 255, 220))
            elif area_type == 'CHART':
                item.setBackground(0, QColor(255, 220, 245))
            elif area_type == 'COMPLEX':
                item.setBackground(0, QColor(245, 220, 255))
    
    def clear_validation_display(self):
        """Clear validation display."""
        self.issues_table.setRowCount(0)
        self.issue_details_text.clear()
        self.recommendations_text.clear()
        self.auto_fixes_table.setRowCount(0)
        self.area_metrics_table.setRowCount(0)
        
        # Reset metrics
        self.overall_quality_progress.setValue(0)
        self.confidence_progress.setValue(0)
        self.reading_order_progress.setValue(0)
        
        # Reset labels
        self.issues_count_label.setText("Issues: 0")
        self.overall_quality_label.setText("Overall Quality: --")
        self.confidence_label.setText("Confidence: --")
        self.reading_order_score_label.setText("Score: --")
        self.summary_details_label.setText("No areas validated yet")
    
    def toggle_auto_validation(self, enabled: bool):
        """Toggle auto-validation."""
        self.auto_validation_enabled = enabled
        if enabled and self.current_areas:
            self.schedule_validation()
    
    def update_validation_delay(self, delay: int):
        """Update validation delay."""
        self.validation_timer.setInterval(delay)
    
    def schedule_validation(self):
        """Schedule validation with delay."""
        if self.auto_validation_enabled:
            delay = self.validation_delay_spinbox.value()
            self.validation_timer.start(delay)
    
    def perform_validation(self):
        """Perform validation on all areas."""
        if not self.current_areas or not self.pdf_document:
            self.status_label.setText("No areas to validate")
            return
        
        self.status_label.setText("Validating areas...")
        self.validate_button.setEnabled(False)
        
        try:
            # Reset results
            self.validation_results = {}
            
            # Validate each area
            for area in self.current_areas:
                area_id = area.get('id', area.get('type', 'unknown'))
                
                # Get extraction result (this would come from the toolset)
                extraction_result = self.get_extraction_result(area)
                
                # Validate the area
                validation_result = self.validator.validate_special_area(
                    area, extraction_result, self.pdf_document
                )
                
                self.validation_results[area_id] = validation_result
                
                # Update tree item
                self.update_area_tree_item(area_id, validation_result)
            
            # Update display
            self.update_validation_display()
            
            # Validate reading order
            self.validate_reading_order()
            
            self.status_label.setText("Validation completed")
            self.validation_completed.emit(self.validation_results)
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            self.status_label.setText(f"Validation failed: {str(e)}")
            QMessageBox.critical(self, "Validation Error", f"Validation failed: {str(e)}")
        
        finally:
            self.validate_button.setEnabled(True)
    
    def get_extraction_result(self, area: Dict) -> Dict:
        """Get extraction result for an area (placeholder)."""
        # This would typically come from the specialized toolsets
        # For now, return a mock result
        area_type = area.get('type', '').upper()
        
        if area_type == 'TABLE':
            return {
                'success': True,
                'content': [{'col1': 'data1', 'col2': 'data2'}],
                'structured_content': {
                    'headers': ['col1', 'col2'],
                    'rows': [['data1', 'data2']]
                },
                'confidence_score': 85.0
            }
        elif area_type == 'IMAGE':
            return {
                'success': True,
                'content': {
                    'description': {'detailed': 'Test image description'},
                    'extracted_text': {'text': 'Sample text', 'confidence': 80.0},
                    'visual_analysis': {'quality_assessment': {'overall_score': 75.0}}
                },
                'confidence_score': 80.0
            }
        else:
            return {
                'success': True,
                'content': {'description': 'Generic content'},
                'confidence_score': 70.0
            }
    
    def update_area_tree_item(self, area_id: str, validation_result: Dict):
        """Update tree item with validation result."""
        for i in range(self.areas_tree.topLevelItemCount()):
            item = self.areas_tree.topLevelItem(i)
            if item.text(0) == area_id or item.data(0, Qt.UserRole).get('id') == area_id:
                # Update status
                if validation_result.get('success', False):
                    quality_score = validation_result.get('quality_score', 0)
                    if quality_score >= 80:
                        item.setText(2, "Excellent")
                        item.setBackground(2, QColor(200, 255, 200))
                    elif quality_score >= 60:
                        item.setText(2, "Good")
                        item.setBackground(2, QColor(255, 255, 200))
                    else:
                        item.setText(2, "Needs Review")
                        item.setBackground(2, QColor(255, 200, 200))
                    
                    item.setText(3, f"{quality_score:.1f}%")
                else:
                    item.setText(2, "Failed")
                    item.setBackground(2, QColor(255, 150, 150))
                    item.setText(3, "0%")
                
                break
    
    def update_validation_display(self):
        """Update validation display with results."""
        if not self.validation_results:
            return
        
        # Calculate overall metrics
        total_areas = len(self.validation_results)
        total_issues = 0
        total_quality = 0
        total_confidence = 0
        
        # Update issues table
        self.issues_table.setRowCount(0)
        
        for area_id, result in self.validation_results.items():
            issues = result.get('issues', [])
            total_issues += len(issues)
            total_quality += result.get('quality_score', 0)
            total_confidence += result.get('confidence', 0)
            
            # Add issues to table
            for issue in issues:
                self.add_issue_to_table(area_id, issue)
        
        # Update metrics
        avg_quality = total_quality / total_areas if total_areas > 0 else 0
        avg_confidence = total_confidence / total_areas if total_areas > 0 else 0
        
        self.overall_quality_progress.setValue(int(avg_quality))
        self.confidence_progress.setValue(int(avg_confidence))
        self.overall_quality_label.setText(f"Overall Quality: {avg_quality:.1f}%")
        self.confidence_label.setText(f"Confidence: {avg_confidence:.1f}%")
        
        # Update issues count
        self.issues_count_label.setText(f"Issues: {total_issues}")
        
        # Update summary
        self.summary_details_label.setText(
            f"Validated {total_areas} areas • {total_issues} issues • "
            f"Quality: {avg_quality:.1f}% • Confidence: {avg_confidence:.1f}%"
        )
        
        # Update area metrics table
        self.update_area_metrics_table()
        
        # Update recommendations
        self.update_recommendations_display()
        
        # Update auto-fixes
        self.update_auto_fixes_display()
        
        # Update validation metrics
        self.update_validation_metrics()
        
        # Enable action buttons
        self.approve_all_button.setEnabled(total_areas > 0)
        self.reject_all_button.setEnabled(total_areas > 0)
    
    def add_issue_to_table(self, area_id: str, issue: ValidationIssue):
        """Add an issue to the issues table."""
        row = self.issues_table.rowCount()
        self.issues_table.insertRow(row)
        
        # Severity
        severity_item = QTableWidgetItem(issue.severity.value.title())
        if issue.severity == ValidationSeverity.CRITICAL:
            severity_item.setBackground(QColor(255, 200, 200))
        elif issue.severity == ValidationSeverity.MAJOR:
            severity_item.setBackground(QColor(255, 230, 200))
        elif issue.severity == ValidationSeverity.MINOR:
            severity_item.setBackground(QColor(255, 255, 200))
        else:
            severity_item.setBackground(QColor(230, 230, 230))
        
        self.issues_table.setItem(row, 0, severity_item)
        
        # Type
        self.issues_table.setItem(row, 1, QTableWidgetItem(issue.type))
        
        # Message
        self.issues_table.setItem(row, 2, QTableWidgetItem(issue.message))
        
        # Location
        location_text = f"Area: {area_id}"
        if issue.location:
            location_text += f" • {issue.location}"
        self.issues_table.setItem(row, 3, QTableWidgetItem(location_text))
        
        # Suggestion
        self.issues_table.setItem(row, 4, QTableWidgetItem(issue.suggestion))
    
    def update_area_metrics_table(self):
        """Update area metrics table."""
        self.area_metrics_table.setRowCount(len(self.validation_results))
        
        row = 0
        for area_id, result in self.validation_results.items():
            self.area_metrics_table.setItem(row, 0, QTableWidgetItem(area_id))
            self.area_metrics_table.setItem(row, 1, QTableWidgetItem(f"{result.get('quality_score', 0):.1f}%"))
            self.area_metrics_table.setItem(row, 2, QTableWidgetItem(str(len(result.get('issues', [])))))
            self.area_metrics_table.setItem(row, 3, QTableWidgetItem(f"{result.get('confidence', 0):.1f}%"))
            row += 1
    
    def update_recommendations_display(self):
        """Update recommendations display."""
        all_recommendations = []
        
        for area_id, result in self.validation_results.items():
            recommendations = result.get('recommendations', [])
            for rec in recommendations:
                all_recommendations.append(f"• {rec}")
        
        if all_recommendations:
            self.recommendations_text.setText('\n'.join(all_recommendations))
            self.apply_recommendations_button.setEnabled(True)
        else:
            self.recommendations_text.setText("No recommendations available.")
            self.apply_recommendations_button.setEnabled(False)
    
    def update_auto_fixes_display(self):
        """Update auto-fixes display."""
        self.auto_fixes_table.setRowCount(0)
        
        for area_id, result in self.validation_results.items():
            auto_fixes = result.get('auto_fixes', [])
            for fix in auto_fixes:
                row = self.auto_fixes_table.rowCount()
                self.auto_fixes_table.insertRow(row)
                
                self.auto_fixes_table.setItem(row, 0, QTableWidgetItem(fix.get('issue_type', '')))
                self.auto_fixes_table.setItem(row, 1, QTableWidgetItem(fix.get('fix_description', '')))
                self.auto_fixes_table.setItem(row, 2, QTableWidgetItem(str(fix.get('timestamp', ''))))
        
        self.undo_auto_fix_button.setEnabled(self.auto_fixes_table.rowCount() > 0)
    
    def update_validation_metrics(self):
        """Update validation metrics display."""
        summary = self.validator.get_validation_summary()
        metrics = summary.get('metrics', {})
        
        self.validations_performed_label.setText(f"Validations Performed: {metrics.get('validations_performed', 0)}")
        self.issues_found_label.setText(f"Issues Found: {metrics.get('issues_found', 0)}")
        self.auto_fixes_applied_label.setText(f"Auto-fixes Applied: {metrics.get('auto_fixes_applied', 0)}")
        self.validation_time_label.setText(f"Validation Time: {metrics.get('validation_time', 0):.2f}s")
    
    def validate_reading_order(self):
        """Validate reading order of areas."""
        if not self.current_areas or not self.pdf_document:
            return
        
        try:
            reading_order_result = self.validator.validate_reading_order(
                self.current_areas, self.pdf_document
            )
            
            if reading_order_result.get('success', False):
                score = reading_order_result.get('reading_order_score', 0)
                self.reading_order_progress.setValue(int(score))
                self.reading_order_score_label.setText(f"Score: {score:.1f}%")
                
                # Add reading order issues to main issues list
                for issue in reading_order_result.get('issues', []):
                    self.add_issue_to_table("Reading Order", issue)
            
        except Exception as e:
            self.logger.error(f"Reading order validation failed: {e}")
    
    def on_area_selection_changed(self):
        """Handle area selection change."""
        current_item = self.areas_tree.currentItem()
        if current_item:
            area_id = current_item.text(0)
            self.area_selected.emit(area_id)
            self.revalidate_button.setEnabled(True)
            self.auto_fix_button.setEnabled(True)
        else:
            self.revalidate_button.setEnabled(False)
            self.auto_fix_button.setEnabled(False)
    
    def on_issue_selection_changed(self):
        """Handle issue selection change."""
        current_row = self.issues_table.currentRow()
        if current_row >= 0:
            # Get issue details
            issue_type = self.issues_table.item(current_row, 1).text()
            message = self.issues_table.item(current_row, 2).text()
            location = self.issues_table.item(current_row, 3).text()
            suggestion = self.issues_table.item(current_row, 4).text()
            
            details = f"Type: {issue_type}\n\n"
            details += f"Message: {message}\n\n"
            details += f"Location: {location}\n\n"
            details += f"Suggestion: {suggestion}"
            
            self.issue_details_text.setText(details)
    
    def filter_issues(self, severity_filter: str):
        """Filter issues by severity."""
        if severity_filter == "All":
            for row in range(self.issues_table.rowCount()):
                self.issues_table.setRowHidden(row, False)
        else:
            for row in range(self.issues_table.rowCount()):
                severity_item = self.issues_table.item(row, 0)
                if severity_item:
                    should_hide = severity_item.text().lower() != severity_filter.lower()
                    self.issues_table.setRowHidden(row, should_hide)
    
    def update_validation_settings(self):
        """Update validation settings."""
        # Update validator settings based on checkboxes
        rules = {
            'text_formatting': {'enabled': self.text_formatting_checkbox.isChecked()},
            'positioning': {'enabled': self.positioning_checkbox.isChecked()},
            'reading_order': {'enabled': self.reading_order_checkbox.isChecked()}
        }
        
        self.validator.update_validation_rules(rules)
        
        # Update auto-fix setting
        self.settings.set('auto_fix_enabled', self.auto_fix_checkbox.isChecked())
    
    def revalidate_selected_area(self):
        """Revalidate the selected area."""
        current_item = self.areas_tree.currentItem()
        if not current_item:
            return
        
        area_data = current_item.data(0, Qt.UserRole)
        area_id = area_data.get('id', current_item.text(0))
        
        try:
            extraction_result = self.get_extraction_result(area_data)
            validation_result = self.validator.validate_special_area(
                area_data, extraction_result, self.pdf_document
            )
            
            self.validation_results[area_id] = validation_result
            self.update_area_tree_item(area_id, validation_result)
            self.update_validation_display()
            
        except Exception as e:
            self.logger.error(f"Revalidation failed: {e}")
            QMessageBox.critical(self, "Revalidation Error", f"Revalidation failed: {str(e)}")
    
    def auto_fix_selected_area(self):
        """Apply auto-fixes to the selected area."""
        current_item = self.areas_tree.currentItem()
        if not current_item:
            return
        
        area_id = current_item.text(0)
        
        try:
            # Re-run validation with auto-fix enabled
            original_setting = self.settings.get('auto_fix_enabled', False)
            self.settings.set('auto_fix_enabled', True)
            
            self.revalidate_selected_area()
            
            # Restore original setting
            self.settings.set('auto_fix_enabled', original_setting)
            
        except Exception as e:
            self.logger.error(f"Auto-fix failed: {e}")
            QMessageBox.critical(self, "Auto-fix Error", f"Auto-fix failed: {str(e)}")
    
    def optimize_reading_order(self):
        """Optimize reading order of areas."""
        if not self.current_areas:
            return
        
        try:
            reading_order_result = self.validator.validate_reading_order(
                self.current_areas, self.pdf_document
            )
            
            if reading_order_result.get('success', False):
                suggested_order = reading_order_result.get('suggested_order', [])
                
                if suggested_order:
                    # Reorder areas based on suggestion
                    area_dict = {area.get('id', f"area_{i}"): area for i, area in enumerate(self.current_areas)}
                    self.current_areas = [area_dict[area_id] for area_id in suggested_order if area_id in area_dict]
                    
                    # Update display
                    self.update_areas_tree()
                    self.validate_reading_order()
                    
                    QMessageBox.information(self, "Reading Order Optimized", 
                                          f"Areas reordered based on optimal reading flow")
            
        except Exception as e:
            self.logger.error(f"Reading order optimization failed: {e}")
            QMessageBox.critical(self, "Optimization Error", f"Reading order optimization failed: {str(e)}")
    
    def approve_all_areas(self):
        """Approve all areas."""
        reply = QMessageBox.question(self, "Approve All Areas", 
                                   "Are you sure you want to approve all areas?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            for area_id in self.validation_results:
                self.validation_results[area_id]['approved'] = True
            
            self.validation_updated.emit(self.validation_results)
            self.status_label.setText("All areas approved")
    
    def reject_all_areas(self):
        """Reject all areas."""
        reply = QMessageBox.question(self, "Reject All Areas", 
                                   "Are you sure you want to reject all areas?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            for area_id in self.validation_results:
                self.validation_results[area_id]['approved'] = False
            
            self.validation_updated.emit(self.validation_results)
            self.status_label.setText("All areas rejected")
    
    def export_validation_results(self):
        """Export validation results."""
        try:
            from PyQt5.QtWidgets import QFileDialog
            import json
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Validation Results", "validation_results.json",
                "JSON Files (*.json);;All Files (*)"
            )
            
            if file_path:
                with open(file_path, 'w') as f:
                    json.dump(self.validation_results, f, indent=2, default=str)
                
                QMessageBox.information(self, "Export Successful", 
                                      f"Validation results exported to {file_path}")
        
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            QMessageBox.critical(self, "Export Error", f"Export failed: {str(e)}")
    
    def apply_recommendations(self):
        """Apply recommendations."""
        # This would implement recommendation application logic
        QMessageBox.information(self, "Recommendations", "Recommendation application not yet implemented")
    
    def export_recommendations(self):
        """Export recommendations."""
        # This would implement recommendation export logic
        QMessageBox.information(self, "Export", "Recommendation export not yet implemented")
    
    def undo_last_auto_fix(self):
        """Undo the last auto-fix."""
        # This would implement auto-fix undo logic
        QMessageBox.information(self, "Undo", "Auto-fix undo not yet implemented")
    
    def clear_auto_fixes(self):
        """Clear all auto-fixes."""
        self.auto_fixes_table.setRowCount(0)
        self.undo_auto_fix_button.setEnabled(False)