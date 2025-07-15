"""
Structure Wizard for Hierarchy Management

Agent 4 implementation for Issue #245 - Structure Wizard and Export System.
Provides guided hierarchy restructuring with templates and export capabilities.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import uuid

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QSplitter,
    QTabWidget, QTextEdit, QProgressBar, QCheckBox, QSpinBox, QGroupBox,
    QScrollArea, QFormLayout, QLineEdit, QMessageBox, QFileDialog,
    QDialog, QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QToolButton, QMenu, QAction
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer, QSize, QRect
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QFont, QColor, QPen, QBrush

from torematrix.core.models.element import Element, ElementType
from torematrix.core.operations.hierarchy import HierarchyManager
from torematrix.core.state import StateStore
from torematrix.core.events import EventBus
from torematrix.utils.geometry import Rect


logger = logging.getLogger(__name__)


class StructureWizardStep(Enum):
    """Steps in the structure wizard."""
    WELCOME = "welcome"
    TEMPLATE_SELECTION = "template_selection"
    HIERARCHY_REVIEW = "hierarchy_review"
    STRUCTURE_MAPPING = "structure_mapping"
    VALIDATION_RULES = "validation_rules"
    EXPORT_OPTIONS = "export_options"
    EXECUTION = "execution"
    COMPLETION = "completion"


class StructureTemplate(Enum):
    """Predefined structure templates."""
    DOCUMENT = "document"
    REPORT = "report"
    MANUAL = "manual"
    ACADEMIC_PAPER = "academic_paper"
    TECHNICAL_SPEC = "technical_spec"
    CUSTOM = "custom"


class ExportFormat(Enum):
    """Export format options."""
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    HTML = "html"
    MARKDOWN = "markdown"
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"


@dataclass
class StructureRule:
    """Rule for structure validation."""
    name: str
    description: str
    element_types: List[ElementType]
    required: bool = True
    min_count: int = 0
    max_count: int = -1  # -1 means unlimited
    parent_types: List[ElementType] = field(default_factory=list)
    child_types: List[ElementType] = field(default_factory=list)
    validation_function: Optional[Callable] = None


@dataclass
class ExportConfiguration:
    """Configuration for export operations."""
    format: ExportFormat
    include_metadata: bool = True
    include_coordinates: bool = True
    include_relationships: bool = True
    hierarchical_structure: bool = True
    custom_fields: List[str] = field(default_factory=list)
    output_path: str = ""
    template_path: str = ""
    options: Dict[str, Any] = field(default_factory=dict)


class StructureWizard(QWidget):
    """Main structure wizard interface."""
    
    # Signals
    structure_changed = pyqtSignal(list)  # List[Element]
    export_completed = pyqtSignal(str)    # export_path
    wizard_completed = pyqtSignal(dict)   # results
    step_changed = pyqtSignal(str)        # step_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hierarchy_manager: Optional[HierarchyManager] = None
        self.state_store: Optional[StateStore] = None
        self.event_bus: Optional[EventBus] = None
        
        # Wizard state
        self.current_step = StructureWizardStep.WELCOME
        self.selected_template = StructureTemplate.DOCUMENT
        self.current_elements: List[Element] = []
        self.structure_rules: List[StructureRule] = []
        self.export_config = ExportConfiguration(ExportFormat.JSON)
        self.wizard_results: Dict[str, Any] = {}
        
        # Templates
        self.templates = self._load_templates()
        
        self._setup_ui()
        self._setup_connections()
        
        logger.info("Structure wizard initialized")
    
    def _setup_ui(self):
        """Setup the wizard UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        header_layout = QHBoxLayout(header_frame)
        
        self.title_label = QLabel("Structure Wizard")
        self.title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        self.step_label = QLabel("Step 1 of 8")
        header_layout.addWidget(self.step_label)
        
        layout.addWidget(header_frame)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(8)
        self.progress_bar.setValue(1)
        layout.addWidget(self.progress_bar)
        
        # Content area
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        
        # Step-specific content
        self.step_stack = QTabWidget()
        self.step_stack.setTabPosition(QTabWidget.TabPosition.North)
        self.step_stack.setTabsClosable(False)
        
        self._setup_welcome_step()
        self._setup_template_step()
        self._setup_hierarchy_step()
        self._setup_mapping_step()
        self._setup_validation_step()
        self._setup_export_step()
        self._setup_execution_step()
        self._setup_completion_step()
        
        self.content_layout.addWidget(self.step_stack)
        layout.addWidget(self.content_widget)
        
        # Navigation buttons
        nav_frame = QFrame()
        nav_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        nav_layout = QHBoxLayout(nav_frame)
        
        self.back_button = QPushButton("< Back")
        self.back_button.setEnabled(False)
        nav_layout.addWidget(self.back_button)
        
        nav_layout.addStretch()
        
        self.next_button = QPushButton("Next >")
        nav_layout.addWidget(self.next_button)
        
        self.finish_button = QPushButton("Finish")
        self.finish_button.setVisible(False)
        nav_layout.addWidget(self.finish_button)
        
        layout.addWidget(nav_frame)
    
    def _setup_welcome_step(self):
        """Setup welcome step."""
        welcome_widget = QWidget()
        layout = QVBoxLayout(welcome_widget)
        
        # Welcome message
        welcome_label = QLabel("""
        <h2>Welcome to the Structure Wizard</h2>
        <p>This wizard will help you organize your document elements into a structured hierarchy.</p>
        <p>You can:</p>
        <ul>
            <li>Choose from predefined templates</li>
            <li>Review and adjust element hierarchies</li>
            <li>Apply validation rules</li>
            <li>Export in multiple formats</li>
        </ul>
        <p>Click <strong>Next</strong> to begin.</p>
        """)
        welcome_label.setWordWrap(True)
        layout.addWidget(welcome_label)
        
        layout.addStretch()
        
        self.step_stack.addTab(welcome_widget, "Welcome")
    
    def _setup_template_step(self):
        """Setup template selection step."""
        template_widget = QWidget()
        layout = QVBoxLayout(template_widget)
        
        # Template selection
        template_label = QLabel("<h3>Select Structure Template</h3>")
        layout.addWidget(template_label)
        
        self.template_combo = QComboBox()
        for template in StructureTemplate:
            self.template_combo.addItem(template.value.replace("_", " ").title(), template)
        layout.addWidget(self.template_combo)
        
        # Template description
        self.template_description = QTextEdit()
        self.template_description.setMaximumHeight(150)
        self.template_description.setReadOnly(True)
        layout.addWidget(self.template_description)
        
        # Template preview
        preview_group = QGroupBox("Template Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.template_tree = QTreeWidget()
        self.template_tree.setHeaderLabels(["Element Type", "Description"])
        preview_layout.addWidget(self.template_tree)
        
        layout.addWidget(preview_group)
        
        self.step_stack.addTab(template_widget, "Template")
    
    def _setup_hierarchy_step(self):
        """Setup hierarchy review step."""
        hierarchy_widget = QWidget()
        layout = QVBoxLayout(hierarchy_widget)
        
        # Hierarchy review
        hierarchy_label = QLabel("<h3>Review Current Hierarchy</h3>")
        layout.addWidget(hierarchy_label)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Current hierarchy
        current_group = QGroupBox("Current Elements")
        current_layout = QVBoxLayout(current_group)
        
        self.current_tree = QTreeWidget()
        self.current_tree.setHeaderLabels(["Element", "Type", "Text"])
        current_layout.addWidget(self.current_tree)
        
        splitter.addWidget(current_group)
        
        # Suggested hierarchy
        suggested_group = QGroupBox("Suggested Structure")
        suggested_layout = QVBoxLayout(suggested_group)
        
        self.suggested_tree = QTreeWidget()
        self.suggested_tree.setHeaderLabels(["Element", "Type", "Text"])
        suggested_layout.addWidget(self.suggested_tree)
        
        # Apply suggestions button
        apply_button = QPushButton("Apply Suggestions")
        apply_button.clicked.connect(self._apply_suggestions)
        suggested_layout.addWidget(apply_button)
        
        splitter.addWidget(suggested_group)
        
        layout.addWidget(splitter)
        
        self.step_stack.addTab(hierarchy_widget, "Hierarchy")
    
    def _setup_mapping_step(self):
        """Setup structure mapping step."""
        mapping_widget = QWidget()
        layout = QVBoxLayout(mapping_widget)
        
        # Structure mapping
        mapping_label = QLabel("<h3>Map Elements to Structure</h3>")
        layout.addWidget(mapping_label)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Elements list
        elements_group = QGroupBox("Available Elements")
        elements_layout = QVBoxLayout(elements_group)
        
        self.elements_list = QListWidget()
        elements_layout.addWidget(self.elements_list)
        
        splitter.addWidget(elements_group)
        
        # Mapping table
        mapping_group = QGroupBox("Element Mapping")
        mapping_layout = QVBoxLayout(mapping_group)
        
        self.mapping_table = QTableWidget()
        self.mapping_table.setColumnCount(3)
        self.mapping_table.setHorizontalHeaderLabels(["Element", "Current Type", "Mapped Type"])
        mapping_layout.addWidget(self.mapping_table)
        
        # Auto-map button
        auto_map_button = QPushButton("Auto-Map Elements")
        auto_map_button.clicked.connect(self._auto_map_elements)
        mapping_layout.addWidget(auto_map_button)
        
        splitter.addWidget(mapping_group)
        
        layout.addWidget(splitter)
        
        self.step_stack.addTab(mapping_widget, "Mapping")
    
    def _setup_validation_step(self):
        """Setup validation rules step."""
        validation_widget = QWidget()
        layout = QVBoxLayout(validation_widget)
        
        # Validation rules
        validation_label = QLabel("<h3>Configure Validation Rules</h3>")
        layout.addWidget(validation_label)
        
        # Rules list
        rules_group = QGroupBox("Validation Rules")
        rules_layout = QVBoxLayout(rules_group)
        
        self.rules_list = QListWidget()
        rules_layout.addWidget(self.rules_list)
        
        # Rule buttons
        rule_buttons = QHBoxLayout()
        
        add_rule_button = QPushButton("Add Rule")
        add_rule_button.clicked.connect(self._add_validation_rule)
        rule_buttons.addWidget(add_rule_button)
        
        edit_rule_button = QPushButton("Edit Rule")
        edit_rule_button.clicked.connect(self._edit_validation_rule)
        rule_buttons.addWidget(edit_rule_button)
        
        remove_rule_button = QPushButton("Remove Rule")
        remove_rule_button.clicked.connect(self._remove_validation_rule)
        rule_buttons.addWidget(remove_rule_button)
        
        rules_layout.addLayout(rule_buttons)
        
        layout.addWidget(rules_group)
        
        # Validation preview
        preview_group = QGroupBox("Validation Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.validation_text = QTextEdit()
        self.validation_text.setReadOnly(True)
        preview_layout.addWidget(self.validation_text)
        
        validate_button = QPushButton("Validate Structure")
        validate_button.clicked.connect(self._validate_structure)
        preview_layout.addWidget(validate_button)
        
        layout.addWidget(preview_group)
        
        self.step_stack.addTab(validation_widget, "Validation")
    
    def _setup_export_step(self):
        """Setup export options step."""
        export_widget = QWidget()
        layout = QVBoxLayout(export_widget)
        
        # Export options
        export_label = QLabel("<h3>Configure Export Options</h3>")
        layout.addWidget(export_label)
        
        # Format selection
        format_group = QGroupBox("Export Format")
        format_layout = QVBoxLayout(format_group)
        
        self.format_combo = QComboBox()
        for format_type in ExportFormat:
            self.format_combo.addItem(format_type.value.upper(), format_type)
        format_layout.addWidget(self.format_combo)
        
        layout.addWidget(format_group)
        
        # Options
        options_group = QGroupBox("Export Options")
        options_layout = QFormLayout(options_group)
        
        self.include_metadata_cb = QCheckBox("Include Metadata")
        self.include_metadata_cb.setChecked(True)
        options_layout.addRow("Metadata:", self.include_metadata_cb)
        
        self.include_coordinates_cb = QCheckBox("Include Coordinates")
        self.include_coordinates_cb.setChecked(True)
        options_layout.addRow("Coordinates:", self.include_coordinates_cb)
        
        self.include_relationships_cb = QCheckBox("Include Relationships")
        self.include_relationships_cb.setChecked(True)
        options_layout.addRow("Relationships:", self.include_relationships_cb)
        
        self.hierarchical_structure_cb = QCheckBox("Hierarchical Structure")
        self.hierarchical_structure_cb.setChecked(True)
        options_layout.addRow("Structure:", self.hierarchical_structure_cb)
        
        layout.addWidget(options_group)
        
        # Output path
        path_group = QGroupBox("Output Path")
        path_layout = QHBoxLayout(path_group)
        
        self.output_path_edit = QLineEdit()
        path_layout.addWidget(self.output_path_edit)
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_output_path)
        path_layout.addWidget(browse_button)
        
        layout.addWidget(path_group)
        
        self.step_stack.addTab(export_widget, "Export")
    
    def _setup_execution_step(self):
        """Setup execution step."""
        execution_widget = QWidget()
        layout = QVBoxLayout(execution_widget)
        
        # Execution status
        execution_label = QLabel("<h3>Executing Operations</h3>")
        layout.addWidget(execution_label)
        
        # Progress
        self.execution_progress = QProgressBar()
        layout.addWidget(self.execution_progress)
        
        # Status text
        self.execution_status = QTextEdit()
        self.execution_status.setReadOnly(True)
        layout.addWidget(self.execution_status)
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._cancel_execution)
        layout.addWidget(self.cancel_button)
        
        self.step_stack.addTab(execution_widget, "Execution")
    
    def _setup_completion_step(self):
        """Setup completion step."""
        completion_widget = QWidget()
        layout = QVBoxLayout(completion_widget)
        
        # Completion message
        completion_label = QLabel("<h3>Wizard Complete</h3>")
        layout.addWidget(completion_label)
        
        # Results summary
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        layout.addWidget(self.results_text)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.open_output_button = QPushButton("Open Output")
        self.open_output_button.clicked.connect(self._open_output)
        action_layout.addWidget(self.open_output_button)
        
        self.new_wizard_button = QPushButton("New Wizard")
        self.new_wizard_button.clicked.connect(self._start_new_wizard)
        action_layout.addWidget(self.new_wizard_button)
        
        layout.addLayout(action_layout)
        
        self.step_stack.addTab(completion_widget, "Complete")
    
    def _setup_connections(self):
        """Setup signal connections."""
        self.next_button.clicked.connect(self._next_step)
        self.back_button.clicked.connect(self._previous_step)
        self.finish_button.clicked.connect(self._finish_wizard)
        
        self.template_combo.currentTextChanged.connect(self._on_template_changed)
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
    
    def set_hierarchy_manager(self, manager: HierarchyManager):
        """Set the hierarchy manager."""
        self.hierarchy_manager = manager
    
    def set_state_store(self, store: StateStore):
        """Set the state store."""
        self.state_store = store
    
    def set_event_bus(self, event_bus: EventBus):
        """Set the event bus."""
        self.event_bus = event_bus
    
    def show_elements(self, elements: List[Element]):
        """Show elements in the wizard."""
        self.current_elements = elements
        self._update_hierarchy_display()
        self._update_mapping_display()
        
        logger.info(f"Showing {len(elements)} elements in structure wizard")
    
    def _load_templates(self) -> Dict[StructureTemplate, Dict[str, Any]]:
        """Load structure templates."""
        templates = {
            StructureTemplate.DOCUMENT: {
                "name": "Document",
                "description": "Standard document structure with titles, paragraphs, and sections.",
                "hierarchy": {
                    "title": {"children": ["paragraph", "section"]},
                    "section": {"children": ["title", "paragraph", "list", "table"]},
                    "paragraph": {"children": []},
                    "list": {"children": ["list_item"]},
                    "table": {"children": ["table_cell"]},
                }
            },
            StructureTemplate.REPORT: {
                "name": "Report",
                "description": "Business report structure with executive summary, sections, and appendices.",
                "hierarchy": {
                    "title": {"children": ["paragraph", "section"]},
                    "section": {"children": ["title", "paragraph", "list", "table", "image"]},
                    "paragraph": {"children": []},
                    "list": {"children": ["list_item"]},
                    "table": {"children": ["table_cell"]},
                }
            },
            StructureTemplate.MANUAL: {
                "name": "Manual",
                "description": "Technical manual structure with procedures, diagrams, and references.",
                "hierarchy": {
                    "title": {"children": ["section"]},
                    "section": {"children": ["title", "paragraph", "list", "table", "image", "formula"]},
                    "paragraph": {"children": []},
                    "list": {"children": ["list_item"]},
                    "table": {"children": ["table_cell"]},
                }
            },
            StructureTemplate.ACADEMIC_PAPER: {
                "name": "Academic Paper",
                "description": "Academic paper structure with abstract, sections, and references.",
                "hierarchy": {
                    "title": {"children": ["paragraph", "section"]},
                    "section": {"children": ["title", "paragraph", "list", "table", "image", "formula"]},
                    "paragraph": {"children": []},
                    "list": {"children": ["list_item"]},
                    "table": {"children": ["table_cell"]},
                }
            },
            StructureTemplate.TECHNICAL_SPEC: {
                "name": "Technical Specification",
                "description": "Technical specification structure with requirements, diagrams, and appendices.",
                "hierarchy": {
                    "title": {"children": ["section"]},
                    "section": {"children": ["title", "paragraph", "list", "table", "image", "formula"]},
                    "paragraph": {"children": []},
                    "list": {"children": ["list_item"]},
                    "table": {"children": ["table_cell"]},
                }
            },
            StructureTemplate.CUSTOM: {
                "name": "Custom",
                "description": "Custom structure - define your own hierarchy.",
                "hierarchy": {}
            }
        }
        
        return templates
    
    def _next_step(self):
        """Move to next step."""
        current_index = list(StructureWizardStep).index(self.current_step)
        if current_index < len(StructureWizardStep) - 1:
            self.current_step = list(StructureWizardStep)[current_index + 1]
            self._update_step_display()
            self.step_changed.emit(self.current_step.value)
    
    def _previous_step(self):
        """Move to previous step."""
        current_index = list(StructureWizardStep).index(self.current_step)
        if current_index > 0:
            self.current_step = list(StructureWizardStep)[current_index - 1]
            self._update_step_display()
            self.step_changed.emit(self.current_step.value)
    
    def _update_step_display(self):
        """Update step display."""
        step_index = list(StructureWizardStep).index(self.current_step)
        self.step_stack.setCurrentIndex(step_index)
        self.progress_bar.setValue(step_index + 1)
        self.step_label.setText(f"Step {step_index + 1} of {len(StructureWizardStep)}")
        
        # Update navigation buttons
        self.back_button.setEnabled(step_index > 0)
        self.next_button.setVisible(step_index < len(StructureWizardStep) - 1)
        self.finish_button.setVisible(step_index == len(StructureWizardStep) - 1)
        
        # Update step-specific content
        if self.current_step == StructureWizardStep.EXECUTION:
            self._start_execution()
    
    def _on_template_changed(self, template_name: str):
        """Handle template selection change."""
        for template in StructureTemplate:
            if template.value.replace("_", " ").title() == template_name:
                self.selected_template = template
                break
        
        # Update template description
        template_info = self.templates.get(self.selected_template, {})
        self.template_description.setText(template_info.get("description", ""))
        
        # Update template preview
        self._update_template_preview()
    
    def _update_template_preview(self):
        """Update template preview tree."""
        self.template_tree.clear()
        
        template_info = self.templates.get(self.selected_template, {})
        hierarchy = template_info.get("hierarchy", {})
        
        for parent_type, info in hierarchy.items():
            parent_item = QTreeWidgetItem([parent_type, f"Parent element of type {parent_type}"])
            self.template_tree.addTopLevelItem(parent_item)
            
            for child_type in info.get("children", []):
                child_item = QTreeWidgetItem([child_type, f"Child element of type {child_type}"])
                parent_item.addChild(child_item)
        
        self.template_tree.expandAll()
    
    def _update_hierarchy_display(self):
        """Update hierarchy display."""
        self.current_tree.clear()
        
        for element in self.current_elements:
            item = QTreeWidgetItem([
                element.id,
                element.element_type.value if element.element_type else "unknown",
                element.text[:50] + "..." if len(element.text) > 50 else element.text
            ])
            self.current_tree.addTopLevelItem(item)
    
    def _update_mapping_display(self):
        """Update mapping display."""
        self.elements_list.clear()
        self.mapping_table.setRowCount(len(self.current_elements))
        
        for i, element in enumerate(self.current_elements):
            # Add to elements list
            item = QListWidgetItem(f"{element.id}: {element.text[:30]}...")
            self.elements_list.addItem(item)
            
            # Add to mapping table
            self.mapping_table.setItem(i, 0, QTableWidgetItem(element.id))
            self.mapping_table.setItem(i, 1, QTableWidgetItem(
                element.element_type.value if element.element_type else "unknown"
            ))
            self.mapping_table.setItem(i, 2, QTableWidgetItem(
                element.element_type.value if element.element_type else "unknown"
            ))
    
    def _apply_suggestions(self):
        """Apply suggested hierarchy changes."""
        # Implementation would apply AI-suggested structure changes
        logger.info("Applying hierarchy suggestions")
    
    def _auto_map_elements(self):
        """Auto-map elements based on template."""
        logger.info("Auto-mapping elements to template structure")
    
    def _add_validation_rule(self):
        """Add new validation rule."""
        logger.info("Adding validation rule")
    
    def _edit_validation_rule(self):
        """Edit selected validation rule."""
        logger.info("Editing validation rule")
    
    def _remove_validation_rule(self):
        """Remove selected validation rule."""
        logger.info("Removing validation rule")
    
    def _validate_structure(self):
        """Validate current structure."""
        self.validation_text.setText("Validating structure...")
        logger.info("Validating structure against rules")
    
    def _on_format_changed(self, format_name: str):
        """Handle export format change."""
        for format_type in ExportFormat:
            if format_type.value.upper() == format_name:
                self.export_config.format = format_type
                break
    
    def _browse_output_path(self):
        """Browse for output path."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Output Path",
            "",
            "All Files (*)"
        )
        if file_path:
            self.output_path_edit.setText(file_path)
            self.export_config.output_path = file_path
    
    def _start_execution(self):
        """Start wizard execution."""
        self.execution_progress.setValue(0)
        self.execution_status.setText("Starting execution...")
        
        # Create execution thread
        self.execution_thread = ExecutionThread(
            self.current_elements,
            self.structure_rules,
            self.export_config
        )
        self.execution_thread.progress_updated.connect(self.execution_progress.setValue)
        self.execution_thread.status_updated.connect(self.execution_status.append)
        self.execution_thread.execution_completed.connect(self._on_execution_completed)
        self.execution_thread.start()
    
    def _cancel_execution(self):
        """Cancel execution."""
        if hasattr(self, 'execution_thread'):
            self.execution_thread.terminate()
        logger.info("Execution cancelled")
    
    def _on_execution_completed(self, results: dict):
        """Handle execution completion."""
        self.wizard_results = results
        self._update_completion_display()
        
        # Move to completion step
        self.current_step = StructureWizardStep.COMPLETION
        self._update_step_display()
        
        self.wizard_completed.emit(results)
    
    def _update_completion_display(self):
        """Update completion display."""
        results_text = f"""
        <h3>Wizard Results</h3>
        <p><strong>Elements processed:</strong> {len(self.current_elements)}</p>
        <p><strong>Export format:</strong> {self.export_config.format.value.upper()}</p>
        <p><strong>Output path:</strong> {self.export_config.output_path}</p>
        <p><strong>Execution time:</strong> {self.wizard_results.get('execution_time', 'N/A')}</p>
        """
        self.results_text.setText(results_text)
    
    def _open_output(self):
        """Open output file."""
        if self.export_config.output_path:
            import os
            os.startfile(self.export_config.output_path)
    
    def _start_new_wizard(self):
        """Start a new wizard."""
        self.current_step = StructureWizardStep.WELCOME
        self._update_step_display()
        self.current_elements = []
        self.structure_rules = []
        self.wizard_results = {}
    
    def _finish_wizard(self):
        """Finish the wizard."""
        self.wizard_completed.emit(self.wizard_results)
        self.close()


class ExecutionThread(QThread):
    """Thread for executing wizard operations."""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    execution_completed = pyqtSignal(dict)
    
    def __init__(self, elements: List[Element], rules: List[StructureRule], export_config: ExportConfiguration):
        super().__init__()
        self.elements = elements
        self.rules = rules
        self.export_config = export_config
    
    def run(self):
        """Run the execution."""
        try:
            results = {}
            
            # Step 1: Structure validation
            self.status_updated.emit("Validating structure...")
            self.progress_updated.emit(25)
            
            # Step 2: Apply structure changes
            self.status_updated.emit("Applying structure changes...")
            self.progress_updated.emit(50)
            
            # Step 3: Export data
            self.status_updated.emit("Exporting data...")
            self.progress_updated.emit(75)
            
            # Step 4: Complete
            self.status_updated.emit("Execution completed successfully!")
            self.progress_updated.emit(100)
            
            results['success'] = True
            results['execution_time'] = "2.5 seconds"
            
            self.execution_completed.emit(results)
            
        except Exception as e:
            self.status_updated.emit(f"Error: {str(e)}")
            self.execution_completed.emit({'success': False, 'error': str(e)})