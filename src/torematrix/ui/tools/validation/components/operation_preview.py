"""
Operation Preview Component.

This module provides comprehensive preview functionality for merge/split
operations including statistics, timeline, and result comparison.
"""

from typing import List, Optional, Dict, Any, Tuple
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QLabel, QListWidget, QListWidgetItem, QGroupBox,
    QScrollArea, QFrame, QPushButton, QProgressBar, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

from .....core.models import Element, ElementType


class OperationStatsWidget(QWidget):
    """Widget for displaying operation statistics."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the statistics widget UI."""
        layout = QVBoxLayout(self)
        
        # Statistics table
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.setAlternatingRowColors(True)
        layout.addWidget(self.stats_table)
    
    def set_stats(self, stats: Dict[str, Any]):
        """Set the operation statistics."""
        self.stats_table.setRowCount(len(stats))
        
        for row, (metric, value) in enumerate(stats.items()):
            metric_item = QTableWidgetItem(metric)
            value_item = QTableWidgetItem(str(value))
            
            self.stats_table.setItem(row, 0, metric_item)
            self.stats_table.setItem(row, 1, value_item)
        
        self.stats_table.resizeColumnsToContents()


class OperationTimelineWidget(QWidget):
    """Widget for displaying operation timeline/steps."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._steps: List[Dict[str, Any]] = []
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the timeline widget UI."""
        layout = QVBoxLayout(self)
        
        # Timeline list
        self.timeline_list = QListWidget()
        layout.addWidget(self.timeline_list)
    
    def set_operation_steps(self, operation_type: str, element_count: int, options: Dict[str, Any]):
        """Set the operation steps based on type and options."""
        self._steps.clear()
        self.timeline_list.clear()
        
        if operation_type == "merge":
            self._create_merge_steps(element_count, options)
        elif operation_type == "split":
            self._create_split_steps(element_count, options)
        
        # Populate timeline list
        for i, step in enumerate(self._steps):
            item_text = f"{i+1}. {step['step']}"
            if step.get('details'):
                item_text += f" - {step['details']}"
            
            item = QListWidgetItem(item_text)
            
            # Set status color
            status = step.get('status', 'pending')
            if status == 'completed':
                item.setBackground(QColor("#e8f5e8"))
            elif status == 'in_progress':
                item.setBackground(QColor("#fff3cd"))
            elif status == 'error':
                item.setBackground(QColor("#f8d7da"))
            
            self.timeline_list.addItem(item)
    
    def _create_merge_steps(self, element_count: int, options: Dict[str, Any]):
        """Create steps for merge operation."""
        separator = options.get('separator', ' ')
        preserve_formatting = options.get('preserve_formatting', True)
        
        self._steps = [
            {
                'step': 'Validate source elements',
                'details': f'{element_count} elements selected',
                'status': 'pending'
            },
            {
                'step': 'Check for metadata conflicts',
                'details': 'Analyzing element properties',
                'status': 'pending'
            },
            {
                'step': 'Merge text content',
                'details': f'Using separator: "{separator}"',
                'status': 'pending'
            },
            {
                'step': 'Resolve metadata conflicts',
                'details': 'Applying resolution strategies',
                'status': 'pending'
            },
            {
                'step': 'Create merged element',
                'details': f'Preserve formatting: {preserve_formatting}',
                'status': 'pending'
            },
            {
                'step': 'Update element relationships',
                'details': 'Maintaining document structure',
                'status': 'pending'
            }
        ]
    
    def _create_split_steps(self, element_count: int, options: Dict[str, Any]):
        """Create steps for split operation."""
        split_positions = options.get('split_positions', [])
        element_type = options.get('element_type', 'Text')
        auto_trim = options.get('auto_trim', True)
        
        self._steps = [
            {
                'step': 'Validate split positions',
                'details': f'{len(split_positions)} split points defined',
                'status': 'pending'
            },
            {
                'step': 'Split text content',
                'details': f'Creating {len(split_positions) + 1} segments',
                'status': 'pending'
            },
            {
                'step': 'Create new elements',
                'details': f'Type: {element_type}, Auto-trim: {auto_trim}',
                'status': 'pending'
            },
            {
                'step': 'Copy metadata',
                'details': 'Inheriting from original element',
                'status': 'pending'
            },
            {
                'step': 'Establish relationships',
                'details': 'Creating parent-child hierarchy',
                'status': 'pending'
            },
            {
                'step': 'Update document structure',
                'details': 'Maintaining element order',
                'status': 'pending'
            }
        ]


class ElementComparisonWidget(QWidget):
    """Widget for comparing elements before and after operation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the comparison widget UI."""
        layout = QVBoxLayout(self)
        
        # Comparison header
        header_layout = QHBoxLayout()
        
        before_label = QLabel("Before Operation")
        before_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        before_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(before_label)
        
        after_label = QLabel("After Operation")
        after_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        after_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(after_label)
        
        layout.addLayout(header_layout)
        
        # Comparison content
        content_layout = QHBoxLayout()
        
        # Before elements
        before_group = QGroupBox("Source Elements")
        before_layout = QVBoxLayout(before_group)
        self.before_list = QListWidget()
        before_layout.addWidget(self.before_list)
        content_layout.addWidget(before_group)
        
        # After elements
        after_group = QGroupBox("Result Elements")
        after_layout = QVBoxLayout(after_group)
        self.after_list = QListWidget()
        after_layout.addWidget(self.after_list)
        content_layout.addWidget(after_group)
        
        layout.addLayout(content_layout)
    
    def set_comparison(self, before_elements: List[Element], after_elements: List[Element]):
        """Set elements for before/after comparison."""
        # Clear lists
        self.before_list.clear()
        self.after_list.clear()
        
        # Populate before elements
        for i, element in enumerate(before_elements):
            text_preview = element.text[:50] + "..." if len(element.text) > 50 else element.text
            item_text = f"{i+1}. [{element.element_type.value}] {text_preview}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, element)
            self.before_list.addItem(item)
        
        # Populate after elements
        for i, element in enumerate(after_elements):
            text_preview = element.text[:50] + "..." if len(element.text) > 50 else element.text
            item_text = f"{i+1}. [{element.element_type.value}] {text_preview}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, element)
            self.after_list.addItem(item)


class OperationPreview(QWidget):
    """
    Main operation preview widget with tabbed interface.
    
    Provides overview, comparison, timeline, and statistics for operations.
    """
    
    preview_updated = pyqtSignal(dict)  # preview_data
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._operation_type: Optional[str] = None
        self._source_elements: List[Element] = []
        self._result_elements: List[Element] = []
        self._options: Dict[str, Any] = {}
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the main preview widget UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.operation_type_label = QLabel("Operation Preview")
        self.operation_type_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header_layout.addWidget(self.operation_type_label)
        
        header_layout.addStretch()
        
        self.element_count_label = QLabel("No operation")
        self.element_count_label.setStyleSheet("color: #666666;")
        header_layout.addWidget(self.element_count_label)
        
        layout.addLayout(header_layout)
        
        # Tab widget for different views
        self.tab_widget = QTabWidget()
        
        # Overview tab
        self.overview_widget = self._create_overview_tab()
        self.tab_widget.addTab(self.overview_widget, "Overview")
        
        # Comparison tab
        self.comparison_widget = ElementComparisonWidget()
        self.tab_widget.addTab(self.comparison_widget, "Comparison")
        
        # Timeline tab
        self.timeline_widget = OperationTimelineWidget()
        self.tab_widget.addTab(self.timeline_widget, "Timeline")
        
        # Statistics tab
        self.stats_widget = OperationStatsWidget()
        self.tab_widget.addTab(self.stats_widget, "Statistics")
        
        layout.addWidget(self.tab_widget)
    
    def _create_overview_tab(self) -> QWidget:
        """Create the overview tab widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Operation summary
        summary_group = QGroupBox("Operation Summary")
        summary_layout = QVBoxLayout(summary_group)
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(100)
        summary_layout.addWidget(self.summary_text)
        
        layout.addWidget(summary_group)
        
        # Quick stats
        stats_group = QGroupBox("Quick Statistics")
        stats_layout = QVBoxLayout(stats_group)
        
        self.quick_stats_label = QLabel("No operation configured")
        stats_layout.addWidget(self.quick_stats_label)
        
        layout.addWidget(stats_group)
        
        # Options display
        options_group = QGroupBox("Operation Options")
        options_layout = QVBoxLayout(options_group)
        
        self.options_text = QTextEdit()
        self.options_text.setReadOnly(True)
        self.options_text.setMaximumHeight(100)
        options_layout.addWidget(self.options_text)
        
        layout.addWidget(options_group)
        
        return widget
    
    def set_operation(self, operation_type: str, source_elements: List[Element], options: Dict[str, Any]):
        """Set the operation to preview."""
        self._operation_type = operation_type
        self._source_elements = source_elements
        self._options = options
        
        # Simulate result elements based on operation
        if operation_type == "merge":
            self._result_elements = self._simulate_merge_result(source_elements, options)
        elif operation_type == "split":
            self._result_elements = self._simulate_split_result(source_elements, options)
        else:
            self._result_elements = []
        
        self._update_preview()
    
    def clear_preview(self):
        """Clear the preview."""
        self._operation_type = None
        self._source_elements = []
        self._result_elements = []
        self._options = {}
        self._update_preview()
    
    def _simulate_merge_result(self, elements: List[Element], options: Dict[str, Any]) -> List[Element]:
        """Simulate merge operation result."""
        if not elements:
            return []
        
        separator = options.get('separator', ' ')
        merged_text = separator.join(element.text for element in elements)
        
        # Create merged element
        merged_element = Element(
            element_type=elements[0].element_type,
            text=merged_text
        )
        
        return [merged_element]
    
    def _simulate_split_result(self, elements: List[Element], options: Dict[str, Any]) -> List[Element]:
        """Simulate split operation result."""
        if not elements:
            return []
        
        element = elements[0]
        split_positions = options.get('split_positions', [])
        element_type = ElementType(options.get('element_type', element.element_type.value))
        
        if not split_positions:
            return [element]
        
        # Split text
        text = element.text
        segments = []
        start = 0
        
        for position in sorted(split_positions):
            if start < position <= len(text):
                segments.append(text[start:position])
                start = position
        
        if start < len(text):
            segments.append(text[start:])
        
        # Create split elements
        result_elements = []
        for segment in segments:
            if segment.strip():
                split_element = Element(
                    element_type=element_type,
                    text=segment.strip() if options.get('auto_trim', True) else segment
                )
                result_elements.append(split_element)
        
        return result_elements
    
    def _update_preview(self):
        """Update all preview components."""
        if self._operation_type is None:
            self.operation_type_label.setText("Operation Preview")
            self.element_count_label.setText("No operation")
            self.summary_text.setPlainText("No operation configured.")
            self.quick_stats_label.setText("No operation configured")
            self.options_text.setPlainText("")
            return
        
        # Update header
        op_name = self._operation_type.capitalize()
        self.operation_type_label.setText(f"{op_name} Operation Preview")
        
        source_count = len(self._source_elements)
        result_count = len(self._result_elements)
        self.element_count_label.setText(f"{source_count} → {result_count} elements")
        
        # Update overview
        self._update_overview()
        
        # Update comparison
        self.comparison_widget.set_comparison(self._source_elements, self._result_elements)
        
        # Update timeline
        self.timeline_widget.set_operation_steps(self._operation_type, len(self._source_elements), self._options)
        
        # Update statistics
        self._update_statistics()
        
        # Emit preview update signal
        preview_data = self.get_preview_data()
        self.preview_updated.emit(preview_data)
    
    def _update_overview(self):
        """Update the overview tab content."""
        if self._operation_type == "merge":
            summary = (
                f"Merging {len(self._source_elements)} elements into 1 element.\n"
                f"Total input characters: {sum(len(e.text) for e in self._source_elements)}\n"
                f"Result characters: {sum(len(e.text) for e in self._result_elements)}"
            )
        elif self._operation_type == "split":
            summary = (
                f"Splitting 1 element into {len(self._result_elements)} elements.\n"
                f"Input characters: {len(self._source_elements[0].text) if self._source_elements else 0}\n"
                f"Total result characters: {sum(len(e.text) for e in self._result_elements)}"
            )
        else:
            summary = "No operation configured."
        
        self.summary_text.setPlainText(summary)
        
        # Quick stats
        if self._operation_type:
            stats_text = (
                f"Source Elements: {len(self._source_elements)}\n"
                f"Result Elements: {len(self._result_elements)}\n"
                f"Operation: {self._operation_type.capitalize()}"
            )
        else:
            stats_text = "No operation configured"
        
        self.quick_stats_label.setText(stats_text)
        
        # Options
        if self._options:
            options_text = "\n".join(f"{key}: {value}" for key, value in self._options.items())
        else:
            options_text = "No options configured"
        
        self.options_text.setPlainText(options_text)
    
    def _update_statistics(self):
        """Update the statistics tab content."""
        if not self._operation_type:
            self.stats_widget.set_stats({})
            return
        
        stats = {
            "Operation Type": self._operation_type.capitalize(),
            "Input Elements": len(self._source_elements),
            "Output Elements": len(self._result_elements),
            "Input Characters": sum(len(e.text) for e in self._source_elements),
            "Output Characters": sum(len(e.text) for e in self._result_elements)
        }
        
        if self._operation_type == "merge":
            separator = self._options.get('separator', ' ')
            stats["Text Separator"] = repr(separator)
            stats["Preserve Formatting"] = self._options.get('preserve_formatting', True)
        
        elif self._operation_type == "split":
            split_positions = self._options.get('split_positions', [])
            stats["Split Points"] = len(split_positions)
            stats["Auto Trim"] = self._options.get('auto_trim', True)
            if split_positions:
                stats["Split Positions"] = ", ".join(map(str, split_positions[:5]))
                if len(split_positions) > 5:
                    stats["Split Positions"] += "..."
        
        self.stats_widget.set_stats(stats)
    
    def get_preview_data(self) -> Dict[str, Any]:
        """Get all preview data."""
        return {
            "operation_type": self._operation_type,
            "source_elements": self._source_elements,
            "result_elements": self._result_elements,
            "options": self._options,
            "stats": {
                "source_count": len(self._source_elements),
                "result_count": len(self._result_elements),
                "input_chars": sum(len(e.text) for e in self._source_elements),
                "output_chars": sum(len(e.text) for e in self._result_elements)
            }
        }