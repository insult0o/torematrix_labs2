"""
Metadata Conflict Resolver Component

Agent 2 implementation providing UI for resolving metadata conflicts
during merge operations with strategy selection and preview.
"""

from typing import List, Dict, Any, Optional
from enum import Enum
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from torematrix.core.models.element import Element
from torematrix.core.operations.merge_split.algorithms.metadata_merge import (
    ConflictResolution, MetadataConflict, MetadataMergeEngine
)

logger = logging.getLogger(__name__)


class MetadataConflictResolver(QWidget):
    """
    Widget for resolving metadata conflicts during merge operations.
    
    Agent 2 implementation with:
    - Interactive conflict resolution
    - Strategy selection per conflict
    - Visual conflict preview
    - Batch resolution options
    """
    
    # Signals
    strategies_changed = pyqtSignal(dict)
    conflict_resolved = pyqtSignal(str, object)
    
    def __init__(self, parent=None):
        """Initialize metadata conflict resolver."""
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__ + ".MetadataConflictResolver")
        self.elements: List[Element] = []
        self.conflicts: List[MetadataConflict] = []
        self.strategies: Dict[str, ConflictResolution] = {}
        self.merge_engine = MetadataMergeEngine()
        
        self._setup_ui()
        self._update_display()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Metadata Conflicts")
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Conflict count
        self.conflict_count_label = QLabel("0 conflicts")
        self.conflict_count_label.setStyleSheet("color: #666666; font-size: 10px;")
        header_layout.addWidget(self.conflict_count_label)
        
        layout.addLayout(header_layout)
        
        # Global strategy controls
        global_group = QGroupBox("Global Strategy")
        global_layout = QHBoxLayout(global_group)
        
        global_layout.addWidget(QLabel("Apply to all:"))
        
        self.global_strategy_combo = QComboBox()
        self.global_strategy_combo.addItems([
            "Keep First",
            "Keep Last", 
            "Merge Values",
            "Custom Choice"
        ])
        self.global_strategy_combo.currentTextChanged.connect(self._on_global_strategy_changed)
        global_layout.addWidget(self.global_strategy_combo)
        
        apply_global_btn = QPushButton("Apply Global")
        apply_global_btn.clicked.connect(self._apply_global_strategy)
        global_layout.addWidget(apply_global_btn)
        
        global_layout.addStretch()
        
        layout.addWidget(global_group)
        
        # Conflicts table
        self.conflicts_table = QTableWidget()
        self.conflicts_table.setColumnCount(4)
        self.conflicts_table.setHorizontalHeaderLabels([
            "Key", "Conflicting Values", "Resolution", "Preview"
        ])
        
        # Configure table
        header = self.conflicts_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        self.conflicts_table.setAlternatingRowColors(True)
        self.conflicts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        layout.addWidget(self.conflicts_table)
        
        # Initially hidden
        self.setVisible(False)
    
    def set_elements(self, elements: List[Element]):
        """Set elements and detect metadata conflicts."""
        self.elements = elements
        self.conflicts = []
        self.strategies = {}
        
        if len(elements) < 2:
            self.setVisible(False)
            return
        
        # Detect conflicts
        self._detect_conflicts()
        self._update_display()
        
        # Show if there are conflicts
        self.setVisible(len(self.conflicts) > 0)
    
    def _detect_conflicts(self):
        """Detect metadata conflicts between elements."""
        if len(self.elements) < 2:
            return
        
        try:
            # Use merge engine to detect conflicts
            self.conflicts = self.merge_engine.detect_conflicts(self.elements)
            
            # Initialize default strategies
            for conflict in self.conflicts:
                self.strategies[conflict.key] = ConflictResolution.KEEP_FIRST
            
            self.logger.info(f"Detected {len(self.conflicts)} metadata conflicts")
            
        except Exception as e:
            self.logger.error(f"Error detecting conflicts: {e}")
            self.conflicts = []
    
    def _update_display(self):
        """Update the conflicts display."""
        # Update conflict count
        self.conflict_count_label.setText(f"{len(self.conflicts)} conflicts")
        
        # Clear and populate table
        self.conflicts_table.setRowCount(len(self.conflicts))
        
        for row, conflict in enumerate(self.conflicts):
            # Key column
            key_item = QTableWidgetItem(conflict.key)
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.conflicts_table.setItem(row, 0, key_item)
            
            # Conflicting values column
            values_text = self._format_conflict_values(conflict)
            values_item = QTableWidgetItem(values_text)
            values_item.setFlags(values_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.conflicts_table.setItem(row, 1, values_item)
            
            # Resolution strategy column
            strategy_combo = QComboBox()
            strategy_combo.addItems([
                "Keep First",
                "Keep Last",
                "Merge Values",
                "Custom Choice"
            ])
            strategy_combo.setCurrentText(self._strategy_to_text(
                self.strategies.get(conflict.key, ConflictResolution.KEEP_FIRST)
            ))
            strategy_combo.currentTextChanged.connect(
                lambda text, key=conflict.key: self._on_strategy_changed(key, text)
            )\n            self.conflicts_table.setCellWidget(row, 2, strategy_combo)
            
            # Preview column
            preview_text = self._get_resolution_preview(conflict)
            preview_item = QTableWidgetItem(preview_text)
            preview_item.setFlags(preview_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Color code by conflict severity
            if conflict.severity == "high":
                preview_item.setBackground(QColor(255, 235, 235))  # Light red
            elif conflict.severity == "medium":
                preview_item.setBackground(QColor(255, 248, 220))  # Light yellow
            
            self.conflicts_table.setItem(row, 3, preview_item)
    
    def _format_conflict_values(self, conflict: MetadataConflict) -> str:
        """Format conflicting values for display."""
        values = []
        for i, value in enumerate(conflict.values):
            element_id = self.elements[i].id or f"Element {i+1}"
            values.append(f"{element_id}: {value}")
        
        return " | ".join(values)
    
    def _strategy_to_text(self, strategy: ConflictResolution) -> str:
        """Convert strategy enum to display text."""
        strategy_map = {
            ConflictResolution.KEEP_FIRST: "Keep First",
            ConflictResolution.KEEP_LAST: "Keep Last",
            ConflictResolution.MERGE_VALUES: "Merge Values",
            ConflictResolution.CUSTOM_CHOICE: "Custom Choice"
        }
        return strategy_map.get(strategy, "Keep First")
    
    def _text_to_strategy(self, text: str) -> ConflictResolution:
        """Convert display text to strategy enum."""
        text_map = {
            "Keep First": ConflictResolution.KEEP_FIRST,
            "Keep Last": ConflictResolution.KEEP_LAST,
            "Merge Values": ConflictResolution.MERGE_VALUES,
            "Custom Choice": ConflictResolution.CUSTOM_CHOICE
        }
        return text_map.get(text, ConflictResolution.KEEP_FIRST)
    
    def _get_resolution_preview(self, conflict: MetadataConflict) -> str:
        """Get preview of resolution result."""
        strategy = self.strategies.get(conflict.key, ConflictResolution.KEEP_FIRST)
        
        try:
            # Use merge engine to get preview
            preview_value = self.merge_engine.resolve_conflict(conflict, strategy)
            return str(preview_value)[:50]  # Truncate for display
        except Exception as e:
            self.logger.error(f"Error getting resolution preview: {e}")
            return "Error"
    
    def _on_strategy_changed(self, key: str, strategy_text: str):
        """Handle strategy change for a specific conflict."""
        strategy = self._text_to_strategy(strategy_text)
        self.strategies[key] = strategy
        
        # Update preview for this conflict
        self._update_conflict_preview(key)
        
        # Emit signal
        self.strategies_changed.emit(self.strategies)
        self.conflict_resolved.emit(key, strategy)
    
    def _update_conflict_preview(self, key: str):
        """Update preview for a specific conflict."""
        # Find the conflict and update its preview
        for row, conflict in enumerate(self.conflicts):
            if conflict.key == key:
                preview_text = self._get_resolution_preview(conflict)
                preview_item = self.conflicts_table.item(row, 3)
                if preview_item:
                    preview_item.setText(preview_text)
                break
    
    def _on_global_strategy_changed(self, strategy_text: str):
        """Handle global strategy change."""
        # This is just for UI feedback, actual application happens on button click
        pass
    
    def _apply_global_strategy(self):
        """Apply global strategy to all conflicts."""
        global_strategy_text = self.global_strategy_combo.currentText()
        global_strategy = self._text_to_strategy(global_strategy_text)
        
        # Apply to all conflicts
        for conflict in self.conflicts:
            self.strategies[conflict.key] = global_strategy
        
        # Update all combo boxes in the table
        for row in range(self.conflicts_table.rowCount()):
            combo = self.conflicts_table.cellWidget(row, 2)
            if isinstance(combo, QComboBox):
                combo.setCurrentText(global_strategy_text)
        
        # Update all previews
        self._update_display()
        
        # Emit signal
        self.strategies_changed.emit(self.strategies)
        
        self.logger.info(f"Applied global strategy: {global_strategy_text}")
    
    def get_strategies(self) -> Dict[str, ConflictResolution]:
        """Get current resolution strategies."""
        return self.strategies.copy()
    
    def set_strategy(self, key: str, strategy: ConflictResolution):
        """Set strategy for a specific conflict."""
        self.strategies[key] = strategy
        self._update_conflict_preview(key)
        self.strategies_changed.emit(self.strategies)
    
    def has_conflicts(self) -> bool:
        """Check if there are any conflicts."""
        return len(self.conflicts) > 0
    
    def get_conflicts(self) -> List[MetadataConflict]:
        """Get list of detected conflicts."""
        return self.conflicts.copy()
    
    def clear_conflicts(self):
        """Clear all conflicts."""
        self.conflicts = []
        self.strategies = {}
        self._update_display()
        self.setVisible(False)