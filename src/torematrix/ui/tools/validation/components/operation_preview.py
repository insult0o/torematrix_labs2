"""
Operation Preview Component for Merge/Split Operations.

This module provides a comprehensive preview widget that shows the before
and after state of merge/split operations with visual indicators and
statistics.
"""

from typing import List, Optional, Dict, Any, Union
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QTextEdit,
    QScrollArea, QFrame, QProgressBar, QListWidget, QListWidgetItem,
    QTabWidget, QTableWidget, QTableWidgetItem, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QTextCharFormat, QPixmap, QPainter

from .....core.models import Element, ElementType


class OperationStatsWidget(QWidget):
    """Widget for displaying operation statistics and metrics."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._stats: Dict[str, Any] = {}
    
    def setup_ui(self):
        """Set up the statistics display UI."""
        layout = QVBoxLayout(self)
        
        # Statistics table
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.stats_table.horizontalHeader().setStretchLastSection(True)
        self.stats_table.setMaximumHeight(200)
        layout.addWidget(self.stats_table)
    
    def set_stats(self, stats: Dict[str, Any]):
        """Set the operation statistics."""
        self._stats = stats
        self.update_stats_display()
    
    def update_stats_display(self):
        """Update the statistics table."""
        self.stats_table.setRowCount(len(self._stats))
        
        for i, (metric, value) in enumerate(self._stats.items()):
            metric_item = QTableWidgetItem(metric.replace("_", " ").title())
            value_item = QTableWidgetItem(str(value))
            
            self.stats_table.setItem(i, 0, metric_item)
            self.stats_table.setItem(i, 1, value_item)


class OperationTimelineWidget(QWidget):
    """Widget for displaying operation timeline and steps."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._steps: List[Dict[str, Any]] = []
    
    def setup_ui(self):
        """Set up the timeline display UI."""
        layout = QVBoxLayout(self)
        
        # Timeline list
        self.timeline_list = QListWidget()
        self.timeline_list.setMaximumHeight(150)
        layout.addWidget(self.timeline_list)
    
    def set_operation_steps(self, operation_type: str, elements_count: int, options: Dict[str, Any]):
        """Set operation steps based on type and parameters."""
        if operation_type == "merge":
            self._steps = [
                {"step": "Validate element selection", "status": "completed"},
                {"step": f"Merge {elements_count} elements", "status": "pending"},
                {"step": "Apply text separator", "status": "pending"},
                {"step": "Resolve metadata conflicts", "status": "pending"},
                {"step": "Create merged element", "status": "pending"},
                {"step": "Update document structure", "status": "pending"}
            ]
        elif operation_type == "split":
            split_count = len(options.get("split_positions", [])) + 1
            self._steps = [
                {"step": "Validate split positions", "status": "completed"},
                {"step": f"Split into {split_count} segments", "status": "pending"},
                {"step": "Apply text processing", "status": "pending"},
                {"step": "Inherit metadata", "status": "pending"},
                {"step": "Create new elements", "status": "pending"},
                {"step": "Update document structure", "status": "pending"}
            ]
        
        self.update_timeline_display()
    
    def update_timeline_display(self):
        """Update the timeline list."""
        self.timeline_list.clear()
        
        for i, step_data in enumerate(self._steps):
            step_text = f"{i+1}. {step_data['step']}"
            status = step_data['status']
            
            item = QListWidgetItem(step_text)
            
            # Set status styling
            if status == "completed":
                item.setText(f"✅ {step_text}")
                item.setForeground(QColor(76, 175, 80))  # Green
            elif status == "in_progress":
                item.setText(f"⏳ {step_text}")
                item.setForeground(QColor(255, 193, 7))  # Yellow
            elif status == "pending":
                item.setText(f"⏸️ {step_text}")
                item.setForeground(QColor(158, 158, 158))  # Gray
            elif status == "error":
                item.setText(f"❌ {step_text}")
                item.setForeground(QColor(244, 67, 54))  # Red
            
            self.timeline_list.addItem(item)


class ElementComparisonWidget(QWidget):
    """Widget for side-by-side comparison of elements before/after operation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the comparison display UI."""
        layout = QVBoxLayout(self)
        
        # Splitter for before/after
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Before section
        before_group = QGroupBox("Before Operation")
        before_layout = QVBoxLayout(before_group)
        
        self.before_list = QListWidget()
        self.before_list.setMaximumHeight(200)
        before_layout.addWidget(self.before_list)
        
        splitter.addWidget(before_group)
        
        # After section
        after_group = QGroupBox("After Operation")
        after_layout = QVBoxLayout(after_group)
        
        self.after_list = QListWidget()
        self.after_list.setMaximumHeight(200)
        after_layout.addWidget(self.after_list)
        
        splitter.addWidget(after_group)
    
    def set_comparison(self, before_elements: List[Element], after_elements: List[Element]):
        """Set elements for before/after comparison."""
        # Update before list
        self.before_list.clear()
        for i, element in enumerate(before_elements):
            item_text = f"{i+1}. {element.element_type.value}: {element.text[:50]}..."
            item = QListWidgetItem(item_text)
            item.setToolTip(element.text)
            self.before_list.addItem(item)
        
        # Update after list
        self.after_list.clear()
        for i, element in enumerate(after_elements):
            item_text = f"{i+1}. {element.element_type.value}: {element.text[:50]}..."
            item = QListWidgetItem(item_text)
            item.setToolTip(element.text)
            item.setForeground(QColor(76, 175, 80))  # Green for new elements
            self.after_list.addItem(item)


class OperationPreview(QWidget):
    """
    Comprehensive operation preview widget for merge/split operations.
    
    Provides detailed preview of operation results including before/after
    comparison, operation timeline, and performance statistics.
    """
    
    preview_updated = pyqtSignal(str, dict)  # operation_type, preview_data
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._operation_type: Optional[str] = None
        self._source_elements: List[Element] = []
        self._result_elements: List[Element] = []
        self._operation_options: Dict[str, Any] = {}
    
    def setup_ui(self):
        """Set up the main preview UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Operation Preview")
        self.title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        self.operation_type_label = QLabel("No operation")
        self.operation_type_label.setStyleSheet("color: #666666; font-style: italic;")
        header_layout.addWidget(self.operation_type_label)
        
        layout.addLayout(header_layout)
        
        # Tab widget for different preview views
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Overview tab
        self.setup_overview_tab()
        
        # Comparison tab
        self.setup_comparison_tab()
        
        # Timeline tab
        self.setup_timeline_tab()
        
        # Statistics tab
        self.setup_statistics_tab()
    
    def setup_overview_tab(self):
        """Set up the overview tab."""
        overview_widget = QWidget()
        overview_layout = QVBoxLayout(overview_widget)
        
        # Operation summary
        summary_group = QGroupBox("Operation Summary")
        summary_layout = QVBoxLayout(summary_group)
        
        self.summary_label = QLabel("No operation configured")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("padding: 8px; background-color: #f5f5f5; border-radius: 4px;")
        summary_layout.addWidget(self.summary_label)
        
        overview_layout.addWidget(summary_group)
        
        # Quick stats
        quick_stats_group = QGroupBox("Quick Statistics")
        quick_stats_layout = QHBoxLayout(quick_stats_group)
        
        self.input_count_label = QLabel("Input: 0")
        self.output_count_label = QLabel("Output: 0")
        self.change_indicator_label = QLabel("Change: None")
        
        quick_stats_layout.addWidget(self.input_count_label)
        quick_stats_layout.addWidget(QFrame())  # Separator
        quick_stats_layout.addWidget(self.output_count_label)
        quick_stats_layout.addWidget(QFrame())  # Separator
        quick_stats_layout.addWidget(self.change_indicator_label)
        quick_stats_layout.addStretch()
        
        overview_layout.addWidget(quick_stats_group)
        
        # Preview area
        preview_group = QGroupBox("Result Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(200)
        self.preview_text.setPlaceholderText("Operation result will be shown here...")
        preview_layout.addWidget(self.preview_text)
        
        overview_layout.addWidget(preview_group)
        
        self.tab_widget.addTab(overview_widget, "Overview")
    
    def setup_comparison_tab(self):
        """Set up the comparison tab."""
        self.comparison_widget = ElementComparisonWidget()
        self.tab_widget.addTab(self.comparison_widget, "Before/After")
    
    def setup_timeline_tab(self):
        """Set up the timeline tab."""
        self.timeline_widget = OperationTimelineWidget()
        self.tab_widget.addTab(self.timeline_widget, "Timeline")
    
    def setup_statistics_tab(self):
        """Set up the statistics tab."""
        self.stats_widget = OperationStatsWidget()
        self.tab_widget.addTab(self.stats_widget, "Statistics")
    
    def set_operation(self, operation_type: str, elements: List[Element], options: Dict[str, Any]):
        """Set the operation to preview."""
        self._operation_type = operation_type
        self._source_elements = elements
        self._operation_options = options
        
        # Generate preview
        self._generate_preview()
        
        # Update display
        self.update_preview_display()
    
    def _generate_preview(self):
        """Generate preview data based on operation type."""
        if self._operation_type == "merge":
            self._generate_merge_preview()
        elif self._operation_type == "split":
            self._generate_split_preview()
    
    def _generate_merge_preview(self):
        """Generate merge operation preview."""
        if not self._source_elements:
            return
        
        # Calculate merged result
        separator = self._operation_options.get("separator", " ")
        merged_text = separator.join(element.text for element in self._source_elements)
        
        # Create result element (simplified)
        result_element = Element(
            element_type=self._source_elements[0].element_type,
            text=merged_text
        )
        
        self._result_elements = [result_element]
    
    def _generate_split_preview(self):
        """Generate split operation preview."""
        if not self._source_elements:
            return
        
        element = self._source_elements[0]
        split_positions = self._operation_options.get("split_positions", [])
        element_type = ElementType(self._operation_options.get("element_type", element.element_type.value))
        
        # Calculate split segments
        text = element.text
        segments = []
        start = 0
        
        for position in split_positions:
            if start < position <= len(text):
                segments.append(text[start:position])
                start = position
        
        # Add remaining text
        if start < len(text):
            segments.append(text[start:])
        
        # Create result elements
        self._result_elements = []
        for i, segment in enumerate(segments):
            if segment.strip():  # Only create elements for non-empty segments
                result_element = Element(
                    element_type=element_type,
                    text=segment.strip() if self._operation_options.get("auto_trim", True) else segment
                )
                self._result_elements.append(result_element)
    
    def update_preview_display(self):
        """Update all preview displays."""
        if not self._operation_type:
            return
        
        # Update header
        self.operation_type_label.setText(f"{self._operation_type.title()} Operation")
        
        if self._operation_type == "merge":
            self.title_label.setText(f"Merge Preview - {len(self._source_elements)} → 1")
        elif self._operation_type == "split":
            self.title_label.setText(f"Split Preview - 1 → {len(self._result_elements)}")
        
        # Update overview
        self.update_overview_display()
        
        # Update comparison
        self.comparison_widget.set_comparison(self._source_elements, self._result_elements)
        
        # Update timeline
        self.timeline_widget.set_operation_steps(
            self._operation_type, 
            len(self._source_elements), 
            self._operation_options
        )
        
        # Update statistics
        self.update_statistics_display()
    
    def update_overview_display(self):
        """Update the overview tab display."""
        if self._operation_type == "merge":
            summary_text = (
                f"Merging {len(self._source_elements)} elements into 1 element.\n"
                f"Text separator: '{self._operation_options.get('separator', ' ')}'\n"
                f"Preserve formatting: {self._operation_options.get('preserve_formatting', True)}"
            )
        elif self._operation_type == "split":
            split_count = len(self._result_elements)
            summary_text = (
                f"Splitting 1 element into {split_count} elements.\n"
                f"Element type: {self._operation_options.get('element_type', 'Original')}\n"
                f"Auto-trim whitespace: {self._operation_options.get('auto_trim', True)}"
            )
        else:
            summary_text = "No operation configured"
        
        self.summary_label.setText(summary_text)
        
        # Update quick stats
        input_count = len(self._source_elements)
        output_count = len(self._result_elements)
        
        self.input_count_label.setText(f"Input: {input_count}")
        self.output_count_label.setText(f"Output: {output_count}")
        
        if output_count > input_count:
            change_text = f"+{output_count - input_count} elements"
            self.change_indicator_label.setStyleSheet("color: #4caf50; font-weight: bold;")
        elif output_count < input_count:
            change_text = f"-{input_count - output_count} elements"
            self.change_indicator_label.setStyleSheet("color: #f44336; font-weight: bold;")
        else:
            change_text = "No change"
            self.change_indicator_label.setStyleSheet("color: #666666;")
        
        self.change_indicator_label.setText(f"Change: {change_text}")
        
        # Update preview text
        if self._result_elements:
            preview_text = "\n\n--- Element Separator ---\n\n".join(
                f"Element {i+1} ({element.element_type.value}):\n{element.text}"
                for i, element in enumerate(self._result_elements)
            )
            self.preview_text.setPlainText(preview_text)
        else:
            self.preview_text.clear()
    
    def update_statistics_display(self):
        """Update the statistics tab display."""
        stats = {}
        
        if self._source_elements:
            # Input statistics
            total_input_chars = sum(len(element.text) for element in self._source_elements)
            avg_input_chars = total_input_chars / len(self._source_elements)
            input_types = set(element.element_type for element in self._source_elements)
            
            stats["Input Elements"] = len(self._source_elements)
            stats["Input Character Count"] = total_input_chars
            stats["Average Input Length"] = f"{avg_input_chars:.1f}"
            stats["Input Element Types"] = len(input_types)
        
        if self._result_elements:
            # Output statistics
            total_output_chars = sum(len(element.text) for element in self._result_elements)
            avg_output_chars = total_output_chars / len(self._result_elements)
            output_types = set(element.element_type for element in self._result_elements)
            
            stats["Output Elements"] = len(self._result_elements)
            stats["Output Character Count"] = total_output_chars
            stats["Average Output Length"] = f"{avg_output_chars:.1f}"
            stats["Output Element Types"] = len(output_types)
        
        # Operation-specific stats
        if self._operation_type == "merge":
            stats["Merge Strategy"] = "Concatenation"
            stats["Text Separator"] = f"'{self._operation_options.get('separator', ' ')}'"
        elif self._operation_type == "split":
            stats["Split Points"] = len(self._operation_options.get("split_positions", []))
            stats["Auto Trim"] = self._operation_options.get("auto_trim", True)
        
        self.stats_widget.set_stats(stats)
    
    def clear_preview(self):
        """Clear the preview display."""
        self._operation_type = None
        self._source_elements = []
        self._result_elements = []
        self._operation_options = {}
        
        self.title_label.setText("Operation Preview")
        self.operation_type_label.setText("No operation")
        self.summary_label.setText("No operation configured")
        self.preview_text.clear()
        
        self.input_count_label.setText("Input: 0")
        self.output_count_label.setText("Output: 0")
        self.change_indicator_label.setText("Change: None")
        self.change_indicator_label.setStyleSheet("color: #666666;")
    
    def get_preview_data(self) -> Dict[str, Any]:
        """Get the current preview data."""
        return {
            "operation_type": self._operation_type,
            "source_elements": [element.to_dict() for element in self._source_elements],
            "result_elements": [element.to_dict() for element in self._result_elements],
            "options": self._operation_options.copy()
        }