"""Type Comparison View

Side-by-side comparison of type definitions with difference
highlighting, conversion analysis, and merge capabilities.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QTextEdit, QScrollArea, QFrame, QGroupBox,
    QSplitter, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QHeaderView, QComboBox, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QSyntaxHighlighter, QTextDocument

from torematrix.core.models.types import TypeRegistry, TypeDefinition, get_type_registry
from torematrix.core.models.types.validation import TypeValidationEngine


class DifferenceType(Enum):
    """Types of differences between types"""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    SAME = "same"


@dataclass
class TypeDifference:
    """Represents a difference between two types"""
    field: str
    diff_type: DifferenceType
    left_value: Any = None
    right_value: Any = None
    description: str = ""


class TypeComparisonEngine:
    """Engine for comparing type definitions"""
    
    def compare_types(self, left_type: TypeDefinition, right_type: TypeDefinition) -> List[TypeDifference]:
        """Compare two type definitions and return differences
        
        Args:
            left_type: First type to compare
            right_type: Second type to compare
            
        Returns:
            List of differences found
        """
        differences = []
        
        # Compare basic fields
        basic_fields = [
            ('name', 'Name'),
            ('category', 'Category'),
            ('description', 'Description'),
            ('color', 'Color'),
            ('is_custom', 'Custom Type')
        ]
        
        for field, display_name in basic_fields:
            left_val = getattr(left_type, field, None)
            right_val = getattr(right_type, field, None)
            
            if left_val != right_val:
                differences.append(TypeDifference(
                    field=display_name,
                    diff_type=DifferenceType.MODIFIED,
                    left_value=left_val,
                    right_value=right_val,
                    description=f"{display_name} differs"
                ))
        
        # Compare properties
        prop_diffs = self._compare_properties(left_type.properties, right_type.properties)
        differences.extend(prop_diffs)
        
        # Compare validation rules
        validation_diffs = self._compare_validation_rules(
            left_type.validation_rules, right_type.validation_rules
        )
        differences.extend(validation_diffs)
        
        # Compare relationships
        rel_diffs = self._compare_relationships(left_type, right_type)
        differences.extend(rel_diffs)
        
        # Compare tags
        tag_diffs = self._compare_tags(left_type.tags, right_type.tags)
        differences.extend(tag_diffs)
        
        return differences
    
    def _compare_properties(self, left_props: Dict[str, Any], right_props: Dict[str, Any]) -> List[TypeDifference]:
        """Compare properties between types"""
        differences = []
        
        all_props = set(left_props.keys()) | set(right_props.keys())
        
        for prop_name in all_props:
            if prop_name in left_props and prop_name in right_props:
                # Property exists in both
                if left_props[prop_name] != right_props[prop_name]:
                    differences.append(TypeDifference(
                        field=f"Properties.{prop_name}",
                        diff_type=DifferenceType.MODIFIED,
                        left_value=left_props[prop_name],
                        right_value=right_props[prop_name],
                        description=f"Property '{prop_name}' differs"
                    ))
            elif prop_name in left_props:
                # Property only in left
                differences.append(TypeDifference(
                    field=f"Properties.{prop_name}",
                    diff_type=DifferenceType.REMOVED,
                    left_value=left_props[prop_name],
                    right_value=None,
                    description=f"Property '{prop_name}' removed"
                ))
            else:
                # Property only in right
                differences.append(TypeDifference(
                    field=f"Properties.{prop_name}",
                    diff_type=DifferenceType.ADDED,
                    left_value=None,
                    right_value=right_props[prop_name],
                    description=f"Property '{prop_name}' added"
                ))
        
        return differences
    
    def _compare_validation_rules(self, left_rules: Dict[str, Any], right_rules: Dict[str, Any]) -> List[TypeDifference]:
        """Compare validation rules"""
        differences = []
        
        all_rules = set(left_rules.keys()) | set(right_rules.keys())
        
        for rule_name in all_rules:
            if rule_name in left_rules and rule_name in right_rules:
                if left_rules[rule_name] != right_rules[rule_name]:
                    differences.append(TypeDifference(
                        field=f"Validation.{rule_name}",
                        diff_type=DifferenceType.MODIFIED,
                        left_value=left_rules[rule_name],
                        right_value=right_rules[rule_name],
                        description=f"Validation rule '{rule_name}' differs"
                    ))
            elif rule_name in left_rules:
                differences.append(TypeDifference(
                    field=f"Validation.{rule_name}",
                    diff_type=DifferenceType.REMOVED,
                    left_value=left_rules[rule_name],
                    right_value=None,
                    description=f"Validation rule '{rule_name}' removed"
                ))
            else:
                differences.append(TypeDifference(
                    field=f"Validation.{rule_name}",
                    diff_type=DifferenceType.ADDED,
                    left_value=None,
                    right_value=right_rules[rule_name],
                    description=f"Validation rule '{rule_name}' added"
                ))
        
        return differences
    
    def _compare_relationships(self, left_type: TypeDefinition, right_type: TypeDefinition) -> List[TypeDifference]:
        """Compare type relationships"""
        differences = []
        
        # Compare parent types
        left_parents = set(left_type.parent_types)
        right_parents = set(right_type.parent_types)
        
        added_parents = right_parents - left_parents
        removed_parents = left_parents - right_parents
        
        for parent in added_parents:
            differences.append(TypeDifference(
                field="Relationships.Parents",
                diff_type=DifferenceType.ADDED,
                left_value=None,
                right_value=parent,
                description=f"Parent type '{parent}' added"
            ))
        
        for parent in removed_parents:
            differences.append(TypeDifference(
                field="Relationships.Parents",
                diff_type=DifferenceType.REMOVED,
                left_value=parent,
                right_value=None,
                description=f"Parent type '{parent}' removed"
            ))
        
        # Compare child types
        left_children = set(left_type.child_types)
        right_children = set(right_type.child_types)
        
        added_children = right_children - left_children
        removed_children = left_children - right_children
        
        for child in added_children:
            differences.append(TypeDifference(
                field="Relationships.Children",
                diff_type=DifferenceType.ADDED,
                left_value=None,
                right_value=child,
                description=f"Child type '{child}' added"
            ))
        
        for child in removed_children:
            differences.append(TypeDifference(
                field="Relationships.Children",
                diff_type=DifferenceType.REMOVED,
                left_value=child,
                right_value=None,
                description=f"Child type '{child}' removed"
            ))
        
        return differences
    
    def _compare_tags(self, left_tags: List[str], right_tags: List[str]) -> List[TypeDifference]:
        """Compare tags"""
        differences = []
        
        left_set = set(left_tags)
        right_set = set(right_tags)
        
        added_tags = right_set - left_set
        removed_tags = left_set - right_set
        
        for tag in added_tags:
            differences.append(TypeDifference(
                field="Tags",
                diff_type=DifferenceType.ADDED,
                left_value=None,
                right_value=tag,
                description=f"Tag '{tag}' added"
            ))
        
        for tag in removed_tags:
            differences.append(TypeDifference(
                field="Tags",
                diff_type=DifferenceType.REMOVED,
                left_value=tag,
                right_value=None,
                description=f"Tag '{tag}' removed"
            ))
        
        return differences


class DifferenceHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for showing differences in text"""
    
    def __init__(self, parent: QTextDocument):
        super().__init__(parent)
        
        # Define formats for different difference types
        self.added_format = QTextCharFormat()
        self.added_format.setBackground(QColor(200, 255, 200))  # Light green
        
        self.removed_format = QTextCharFormat()
        self.removed_format.setBackground(QColor(255, 200, 200))  # Light red
        
        self.modified_format = QTextCharFormat()
        self.modified_format.setBackground(QColor(255, 255, 200))  # Light yellow
    
    def highlightBlock(self, text: str):
        """Highlight differences in text block"""
        # This would implement actual diff highlighting
        # For now, just a placeholder
        pass


class TypeSelectorWidget(QWidget):
    """Widget for selecting types to compare"""
    
    selection_changed = pyqtSignal(str, str)  # left_type_id, right_type_id
    
    def __init__(self, registry: TypeRegistry, parent=None):
        super().__init__(parent)
        
        self.registry = registry
        self.setup_ui()
        self.populate_types()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Left type selector
        layout.addWidget(QLabel("Left:"))
        self.left_combo = QComboBox()
        self.left_combo.setMinimumWidth(200)
        layout.addWidget(self.left_combo)
        
        layout.addWidget(QLabel("vs"))
        
        # Right type selector
        layout.addWidget(QLabel("Right:"))
        self.right_combo = QComboBox()
        self.right_combo.setMinimumWidth(200)
        layout.addWidget(self.right_combo)
        
        # Swap button
        self.swap_btn = QPushButton("⇄ Swap")
        self.swap_btn.clicked.connect(self.swap_types)
        layout.addWidget(self.swap_btn)
        
        layout.addStretch()
    
    def populate_types(self):
        """Populate type combo boxes"""
        types = list(self.registry.list_types())
        types.sort(key=lambda t: t.name)
        
        for combo in [self.left_combo, self.right_combo]:
            combo.clear()
            combo.addItem("[Select Type]", None)
            
            for type_def in types:
                combo.addItem(f"{type_def.name} ({type_def.category})", type_def.type_id)
    
    def connect_signals(self):
        """Connect signals"""
        self.left_combo.currentDataChanged.connect(self.on_selection_changed)
        self.right_combo.currentDataChanged.connect(self.on_selection_changed)
    
    def on_selection_changed(self):
        """Handle selection change"""
        left_id = self.left_combo.currentData()
        right_id = self.right_combo.currentData()
        
        if left_id and right_id:
            self.selection_changed.emit(left_id, right_id)
    
    def swap_types(self):
        """Swap left and right type selections"""
        left_index = self.left_combo.currentIndex()
        right_index = self.right_combo.currentIndex()
        
        self.left_combo.setCurrentIndex(right_index)
        self.right_combo.setCurrentIndex(left_index)
    
    def set_types(self, left_type_id: str, right_type_id: str):
        """Set selected types"""
        # Find and set left type
        for i in range(self.left_combo.count()):
            if self.left_combo.itemData(i) == left_type_id:
                self.left_combo.setCurrentIndex(i)
                break
        
        # Find and set right type
        for i in range(self.right_combo.count()):
            if self.right_combo.itemData(i) == right_type_id:
                self.right_combo.setCurrentIndex(i)
                break


class DifferenceListWidget(QWidget):
    """Widget for showing list of differences"""
    
    difference_selected = pyqtSignal(TypeDifference)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.differences: List[TypeDifference] = []
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("Differences")
        title.setFont(QFont("", 10, QFont.Weight.Bold))
        header_layout.addWidget(title)
        
        self.count_label = QLabel("0 differences")
        self.count_label.setStyleSheet("color: #666; font-style: italic;")
        header_layout.addWidget(self.count_label)
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Differences tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Field", "Change", "Left Value", "Right Value"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(False)
        
        # Configure columns
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        self.tree.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.tree)
    
    def set_differences(self, differences: List[TypeDifference]):
        """Set differences to display"""
        self.differences = differences
        self.update_display()
    
    def update_display(self):
        """Update differences display"""
        self.tree.clear()
        
        # Update count
        count = len(self.differences)
        self.count_label.setText(f"{count} difference{'s' if count != 1 else ''}")
        
        # Add differences to tree
        for diff in self.differences:
            item = QTreeWidgetItem()
            item.setText(0, diff.field)
            item.setText(1, diff.diff_type.value.title())
            item.setText(2, str(diff.left_value) if diff.left_value is not None else "")
            item.setText(3, str(diff.right_value) if diff.right_value is not None else "")
            
            # Store difference object
            item.setData(0, Qt.ItemDataRole.UserRole, diff)
            
            # Color code by difference type
            if diff.diff_type == DifferenceType.ADDED:
                item.setBackground(1, QColor(200, 255, 200))  # Light green
            elif diff.diff_type == DifferenceType.REMOVED:
                item.setBackground(1, QColor(255, 200, 200))  # Light red
            elif diff.diff_type == DifferenceType.MODIFIED:
                item.setBackground(1, QColor(255, 255, 200))  # Light yellow
            
            self.tree.addTopLevelItem(item)
    
    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item click"""
        diff = item.data(0, Qt.ItemDataRole.UserRole)
        if diff:
            self.difference_selected.emit(diff)


class SideBySideComparisonWidget(QWidget):
    """Widget for side-by-side type comparison"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.left_type: Optional[TypeDefinition] = None
        self.right_type: Optional[TypeDefinition] = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Left side
        left_group = QGroupBox("Left Type")
        left_layout = QVBoxLayout(left_group)
        
        self.left_text = QTextEdit()
        self.left_text.setReadOnly(True)
        self.left_text.setFont(QFont("Consolas", 9))
        left_layout.addWidget(self.left_text)
        
        layout.addWidget(left_group)
        
        # Right side
        right_group = QGroupBox("Right Type")
        right_layout = QVBoxLayout(right_group)
        
        self.right_text = QTextEdit()
        self.right_text.setReadOnly(True)
        self.right_text.setFont(QFont("Consolas", 9))
        right_layout.addWidget(self.right_text)
        
        layout.addWidget(right_group)
    
    def set_types(self, left_type: TypeDefinition, right_type: TypeDefinition):
        """Set types to compare"""
        self.left_type = left_type
        self.right_type = right_type
        
        self.update_display()
    
    def update_display(self):
        """Update comparison display"""
        if self.left_type:
            left_text = self.format_type_for_display(self.left_type)
            self.left_text.setPlainText(left_text)
        else:
            self.left_text.clear()
        
        if self.right_type:
            right_text = self.format_type_for_display(self.right_type)
            self.right_text.setPlainText(right_text)
        else:
            self.right_text.clear()
    
    def format_type_for_display(self, type_def: TypeDefinition) -> str:
        """Format type definition for display"""
        lines = []
        
        lines.append(f"Name: {type_def.name}")
        lines.append(f"ID: {type_def.type_id}")
        lines.append(f"Category: {type_def.category}")
        lines.append(f"Description: {type_def.description}")
        lines.append(f"Custom: {type_def.is_custom}")
        lines.append(f"Color: {type_def.color or 'None'}")
        lines.append(f"Created: {type_def.created_at.strftime('%Y-%m-%d %H:%M')}")
        lines.append("")
        
        # Properties
        lines.append("Properties:")
        if type_def.properties:
            for prop_name, prop_data in type_def.properties.items():
                lines.append(f"  {prop_name}: {prop_data}")
        else:
            lines.append("  (none)")
        lines.append("")
        
        # Validation rules
        lines.append("Validation Rules:")
        if type_def.validation_rules:
            for rule_name, rule_value in type_def.validation_rules.items():
                lines.append(f"  {rule_name}: {rule_value}")
        else:
            lines.append("  (none)")
        lines.append("")
        
        # Relationships
        lines.append("Parent Types:")
        if type_def.parent_types:
            for parent in type_def.parent_types:
                lines.append(f"  {parent}")
        else:
            lines.append("  (none)")
        lines.append("")
        
        lines.append("Child Types:")
        if type_def.child_types:
            for child in type_def.child_types:
                lines.append(f"  {child}")
        else:
            lines.append("  (none)")
        lines.append("")
        
        # Tags
        lines.append("Tags:")
        if type_def.tags:
            lines.append(f"  {', '.join(type_def.tags)}")
        else:
            lines.append("  (none)")
        
        return "\n".join(lines)


class TypeComparisonView(QWidget):
    """Complete type comparison view"""
    
    # Signals
    merge_requested = pyqtSignal(str, str)  # from_type_id, to_type_id
    type_selected = pyqtSignal(str)  # type_id
    
    def __init__(self, registry: TypeRegistry = None, parent=None):
        super().__init__(parent)
        
        self.registry = registry or get_type_registry()
        self.comparison_engine = TypeComparisonEngine()
        self.validation_engine = TypeValidationEngine()
        
        # State
        self.current_left_type: Optional[TypeDefinition] = None
        self.current_right_type: Optional[TypeDefinition] = None
        self.current_differences: List[TypeDifference] = []
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header with type selectors
        header_layout = QVBoxLayout()
        
        title = QLabel("Type Comparison")
        title.setFont(QFont("", 12, QFont.Weight.Bold))
        header_layout.addWidget(title)
        
        self.type_selector = TypeSelectorWidget(self.registry)
        header_layout.addWidget(self.type_selector)
        
        layout.addLayout(header_layout)
        
        # Main content in splitter
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Top section - side-by-side comparison
        self.comparison_widget = SideBySideComparisonWidget()
        main_splitter.addWidget(self.comparison_widget)
        
        # Bottom section - differences and actions
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # Differences list
        self.differences_widget = DifferenceListWidget()
        bottom_layout.addWidget(self.differences_widget)
        
        # Action buttons
        actions_layout = QHBoxLayout()
        
        self.merge_left_btn = QPushButton("← Merge Right to Left")
        self.merge_left_btn.clicked.connect(self.merge_right_to_left)
        self.merge_left_btn.setEnabled(False)
        actions_layout.addWidget(self.merge_left_btn)
        
        self.merge_right_btn = QPushButton("→ Merge Left to Right")
        self.merge_right_btn.clicked.connect(self.merge_left_to_right)
        self.merge_right_btn.setEnabled(False)
        actions_layout.addWidget(self.merge_right_btn)
        
        actions_layout.addStretch()
        
        self.analyze_conversion_btn = QPushButton("🔍 Analyze Conversion")
        self.analyze_conversion_btn.clicked.connect(self.analyze_conversion)
        self.analyze_conversion_btn.setEnabled(False)
        actions_layout.addWidget(self.analyze_conversion_btn)
        
        bottom_layout.addLayout(actions_layout)
        
        main_splitter.addWidget(bottom_widget)
        
        # Set splitter proportions
        main_splitter.setSizes([400, 300])
        layout.addWidget(main_splitter)
        
        # Empty state
        self.empty_label = QLabel("Select two types to compare")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #999; font-style: italic; font-size: 14px;")
        layout.addWidget(self.empty_label)
        
        # Initially show empty state
        self.show_empty_state()
    
    def connect_signals(self):
        """Connect signals"""
        self.type_selector.selection_changed.connect(self.on_types_selected)
        self.differences_widget.difference_selected.connect(self.on_difference_selected)
    
    def on_types_selected(self, left_type_id: str, right_type_id: str):
        """Handle type selection"""
        try:
            self.current_left_type = self.registry.get_type(left_type_id)
            self.current_right_type = self.registry.get_type(right_type_id)
            
            # Perform comparison
            self.current_differences = self.comparison_engine.compare_types(
                self.current_left_type, self.current_right_type
            )
            
            # Update display
            self.show_comparison()
            self.update_display()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load types: {e}")
    
    def show_comparison(self):
        """Show comparison widgets"""
        self.empty_label.setVisible(False)
        self.comparison_widget.setVisible(True)
        self.differences_widget.setVisible(True)
        
        # Enable action buttons
        self.merge_left_btn.setEnabled(True)
        self.merge_right_btn.setEnabled(True)
        self.analyze_conversion_btn.setEnabled(True)
    
    def show_empty_state(self):
        """Show empty state"""
        self.empty_label.setVisible(True)
        self.comparison_widget.setVisible(False)
        self.differences_widget.setVisible(False)
        
        # Disable action buttons
        self.merge_left_btn.setEnabled(False)
        self.merge_right_btn.setEnabled(False)
        self.analyze_conversion_btn.setEnabled(False)
    
    def update_display(self):
        """Update comparison display"""
        if self.current_left_type and self.current_right_type:
            self.comparison_widget.set_types(self.current_left_type, self.current_right_type)
            self.differences_widget.set_differences(self.current_differences)
    
    def on_difference_selected(self, difference: TypeDifference):
        """Handle difference selection"""
        # Could highlight the difference in the side-by-side view
        pass
    
    def merge_left_to_right(self):
        """Merge left type into right type"""
        if self.current_left_type and self.current_right_type:
            self.merge_requested.emit(self.current_left_type.type_id, self.current_right_type.type_id)
    
    def merge_right_to_left(self):
        """Merge right type into left type"""
        if self.current_left_type and self.current_right_type:
            self.merge_requested.emit(self.current_right_type.type_id, self.current_left_type.type_id)
    
    def analyze_conversion(self):
        """Analyze conversion between types"""
        if not self.current_left_type or not self.current_right_type:
            return
        
        # Analyze conversion from left to right
        try:
            warnings = self.validation_engine.get_conversion_warnings(
                self.current_left_type.type_id,
                self.current_right_type.type_id,
                self.registry
            )
            
            if warnings:
                warning_text = "\n".join([f"• {warning}" for warning in warnings])
                message = f"Conversion from '{self.current_left_type.name}' to '{self.current_right_type.name}' has these warnings:\n\n{warning_text}"
            else:
                message = f"Conversion from '{self.current_left_type.name}' to '{self.current_right_type.name}' should be safe."
            
            QMessageBox.information(self, "Conversion Analysis", message)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to analyze conversion: {e}")
    
    def set_types_to_compare(self, left_type_id: str, right_type_id: str):
        """Set types to compare"""
        self.type_selector.set_types(left_type_id, right_type_id)
    
    def refresh(self):
        """Refresh the comparison"""
        # Repopulate type selectors
        self.type_selector.populate_types()
        
        # Re-run comparison if types are selected
        if self.current_left_type and self.current_right_type:
            self.current_differences = self.comparison_engine.compare_types(
                self.current_left_type, self.current_right_type
            )
            self.update_display()
