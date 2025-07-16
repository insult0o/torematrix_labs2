"""
Operation Preview Component for Agent 2 - Issue #235.

This module provides UI components for previewing merge/split operations
with timeline, statistics, and comparison views.
"""

from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QTableWidget, QTableWidgetItem, QListWidget, QListWidgetItem,
    QGroupBox, QTextEdit, QProgressBar, QPushButton, QSplitter,
    QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette

from src.torematrix.core.models import Element, ElementType


class OperationStatsWidget(QWidget):
    """Widget for displaying operation statistics."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the statistics display UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Operation Statistics")
        title_label.setFont(QFont("", 11, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # Stats table
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.stats_table.horizontalHeader().setStretchLastSection(True)
        self.stats_table.setAlternatingRowColors(True)
        layout.addWidget(self.stats_table)
        
    def set_stats(self, stats: Dict[str, Any]):
        """Set the statistics to display."""
        self.stats_table.setRowCount(len(stats))
        
        for row, (metric, value) in enumerate(stats.items()):
            metric_item = QTableWidgetItem(metric)
            value_item = QTableWidgetItem(str(value))
            
            self.stats_table.setItem(row, 0, metric_item)
            self.stats_table.setItem(row, 1, value_item)
            
        self.stats_table.resizeRowsToContents()


class OperationTimelineWidget(QWidget):
    """Widget for displaying operation timeline/steps."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._steps = []
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the timeline display UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Operation Timeline")
        title_label.setFont(QFont("", 11, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # Timeline list
        self.timeline_list = QListWidget()
        layout.addWidget(self.timeline_list)
        
    def set_operation_steps(self, operation_type: str, element_count: int, options: Dict[str, Any]):
        """Set operation steps based on type and options."""
        self._steps.clear()
        self.timeline_list.clear()
        
        if operation_type == "merge":
            self._steps = [
                {"step": f"Validate {element_count} selected elements", "status": "pending"},
                {"step": "Check metadata compatibility", "status": "pending"},
                {"step": "Resolve metadata conflicts", "status": "pending"},
                {"step": f"Merge texts with separator: '{options.get('separator', ' ')}'", "status": "pending"},
                {"step": "Apply formatting options", "status": "pending"},
                {"step": "Create merged element", "status": "pending"},
                {"step": "Update element relationships", "status": "pending"}
            ]
        elif operation_type == "split":
            split_positions = options.get("split_positions", [])
            self._steps = [
                {"step": "Validate split positions", "status": "pending"},
                {"step": f"Split text at {len(split_positions)} position(s)", "status": "pending"},
                {"step": "Create segment elements", "status": "pending"},
                {"step": "Apply metadata inheritance", "status": "pending"},
                {"step": "Validate resulting elements", "status": "pending"}
            ]
            
        # Populate timeline list
        for i, step_data in enumerate(self._steps):
            item = QListWidgetItem(f"{i+1}. {step_data['step']}")
            if step_data["status"] == "completed":
                item.setBackground(QColor(200, 255, 200))  # Light green
            elif step_data["status"] == "in_progress":
                item.setBackground(QColor(255, 255, 200))  # Light yellow
            else:
                item.setBackground(QColor(240, 240, 240))  # Light gray
                
            self.timeline_list.addItem(item)


class ElementComparisonWidget(QWidget):
    """Widget for comparing elements before and after operations."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the comparison UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Before/After Comparison")
        title_label.setFont(QFont("", 11, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # Comparison panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Before panel
        before_group = QGroupBox("Before Operation")
        before_layout = QVBoxLayout(before_group)
        
        self.before_text = QTextEdit()
        self.before_text.setReadOnly(True)
        self.before_text.setMaximumHeight(200)
        before_layout.addWidget(self.before_text)
        
        self.before_count_label = QLabel("0 elements")
        before_layout.addWidget(self.before_count_label)
        
        splitter.addWidget(before_group)
        
        # After panel
        after_group = QGroupBox("After Operation")
        after_layout = QVBoxLayout(after_group)
        
        self.after_text = QTextEdit()
        self.after_text.setReadOnly(True)
        self.after_text.setMaximumHeight(200)
        after_layout.addWidget(self.after_text)
        
        self.after_count_label = QLabel("0 elements")
        after_layout.addWidget(self.after_count_label)
        
        splitter.addWidget(after_group)
        
        layout.addWidget(splitter)
        
    def set_comparison(self, before_elements: List[Element], after_elements: List[Element]):
        """Set elements for before/after comparison."""
        # Before text
        before_texts = [elem.text for elem in before_elements]
        self.before_text.setPlainText("\n---\n".join(before_texts))
        self.before_count_label.setText(f"{len(before_elements)} element{'s' if len(before_elements) != 1 else ''}")
        
        # After text
        after_texts = [elem.text for elem in after_elements]
        self.after_text.setPlainText("\n---\n".join(after_texts))
        self.after_count_label.setText(f"{len(after_elements)} element{'s' if len(after_elements) != 1 else ''}")


class OperationPreview(QWidget):
    """Main operation preview widget with tabbed interface."""
    
    preview_updated = pyqtSignal(str, list, list, dict)  # operation_type, source_elements, result_elements, options
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._operation_type = None
        self._source_elements = []
        self._result_elements = []
        self._options = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the preview UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.operation_type_label = QLabel("No operation")
        self.operation_type_label.setFont(QFont("", 12, QFont.Weight.Bold))
        header_layout.addWidget(self.operation_type_label)
        
        header_layout.addStretch()
        
        self.refresh_button = QPushButton("Refresh Preview")
        self.refresh_button.clicked.connect(self.refresh_preview)
        header_layout.addWidget(self.refresh_button)
        
        layout.addLayout(header_layout)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Overview tab
        self.overview_widget = self.create_overview_tab()
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
        
    def create_overview_tab(self) -> QWidget:
        """Create the overview tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Operation summary
        summary_group = QGroupBox("Operation Summary")
        summary_layout = QVBoxLayout(summary_group)
        
        self.summary_text = QTextEdit()
        self.summary_text.setMaximumHeight(100)
        self.summary_text.setReadOnly(True)
        summary_layout.addWidget(self.summary_text)
        
        layout.addWidget(summary_group)
        
        # Progress indicator
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Ready to execute operation")
        progress_layout.addWidget(self.progress_label)
        
        layout.addWidget(progress_group)
        
        layout.addStretch()
        
        return widget
        
    def set_operation(self, operation_type: str, source_elements: List[Element], options: Dict[str, Any]):
        """Set the operation to preview."""
        self._operation_type = operation_type
        self._source_elements = source_elements
        self._options = options
        
        # Generate result elements preview
        self._result_elements = self.generate_result_preview(operation_type, source_elements, options)
        
        # Update UI
        self.update_display()
        
    def generate_result_preview(self, operation_type: str, source_elements: List[Element], options: Dict[str, Any]) -> List[Element]:
        """Generate preview of result elements."""
        if operation_type == "merge":
            # Create merged element
            separator = options.get("separator", " ")
            merged_text = separator.join([elem.text for elem in source_elements])
            
            result_type = ElementType(options.get("result_type", source_elements[0].element_type.value))
            merged_element = Element(
                element_type=result_type,
                text=merged_text
            )
            return [merged_element]
            
        elif operation_type == "split":
            # Create split elements
            if source_elements:
                source_element = source_elements[0]
                split_positions = options.get("split_positions", [])
                
                if split_positions:
                    text = source_element.text
                    positions = [0] + sorted(split_positions) + [len(text)]
                    
                    result_elements = []
                    for i in range(len(positions) - 1):
                        start = positions[i]
                        end = positions[i + 1]
                        segment_text = text[start:end]
                        
                        if options.get("auto_trim", True):
                            segment_text = segment_text.strip()
                            
                        if segment_text:  # Only create non-empty segments
                            segment_element = Element(
                                element_type=ElementType(options.get("element_type", source_element.element_type.value)),
                                text=segment_text
                            )
                            result_elements.append(segment_element)
                            
                    return result_elements
                    
        return []
        
    def update_display(self):
        """Update the display with current operation data."""
        if not self._operation_type:
            self.operation_type_label.setText("No operation")
            self.summary_text.setPlainText("No operation selected")
            return
            
        # Update operation type label
        self.operation_type_label.setText(f"{self._operation_type.title()} Operation Preview")
        
        # Update summary
        source_count = len(self._source_elements)
        result_count = len(self._result_elements)
        
        summary = f"Operation: {self._operation_type.title()}\n"
        summary += f"Input: {source_count} element{'s' if source_count != 1 else ''}\n"
        summary += f"Output: {result_count} element{'s' if result_count != 1 else ''}\n"
        
        if self._operation_type == "merge":
            separator = self._options.get("separator", " ")
            summary += f"Separator: '{separator}'\n"
        elif self._operation_type == "split":
            split_positions = self._options.get("split_positions", [])
            summary += f"Split points: {len(split_positions)}\n"
            
        self.summary_text.setPlainText(summary)
        
        # Update comparison
        self.comparison_widget.set_comparison(self._source_elements, self._result_elements)
        
        # Update timeline
        self.timeline_widget.set_operation_steps(self._operation_type, len(self._source_elements), self._options)
        
        # Update statistics
        stats = {
            "Input Elements": len(self._source_elements),
            "Output Elements": len(self._result_elements),
            "Total Input Characters": sum(len(elem.text) for elem in self._source_elements),
            "Total Output Characters": sum(len(elem.text) for elem in self._result_elements)
        }
        
        if self._operation_type == "merge":
            stats["Merge Ratio"] = f"1:{len(self._source_elements)}"
        elif self._operation_type == "split":
            stats["Split Ratio"] = f"{len(self._result_elements)}:1"
            
        self.stats_widget.set_stats(stats)
        
        # Emit preview updated signal
        self.preview_updated.emit(self._operation_type, self._source_elements, self._result_elements, self._options)
        
    def clear_preview(self):
        """Clear the preview."""
        self._operation_type = None
        self._source_elements = []
        self._result_elements = []
        self._options = {}
        self.update_display()
        
    def refresh_preview(self):
        """Refresh the preview with current data."""
        if self._operation_type and self._source_elements:
            self.set_operation(self._operation_type, self._source_elements, self._options)
            
    def get_preview_data(self) -> Dict[str, Any]:
        """Get current preview data."""
        return {
            "operation_type": self._operation_type,
            "source_elements": self._source_elements,
            "result_elements": self._result_elements,
            "options": self._options
        }
        
    def simulate_progress(self):
        """Simulate operation progress."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        
        # Simulate progress updates
        self.progress_timer = QTimer()
        self.progress_value = 0
        
        def update_progress():
            self.progress_value += 10
            self.progress_bar.setValue(self.progress_value)
            self.progress_label.setText(f"Processing... {self.progress_value}%")
            
            if self.progress_value >= 100:
                self.progress_timer.stop()
                self.progress_bar.setVisible(False)
                self.progress_label.setText("Operation completed")
                
        self.progress_timer.timeout.connect(update_progress)
        self.progress_timer.start(200)  # Update every 200ms