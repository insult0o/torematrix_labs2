"""
Template System for Merge/Split Operations - Agent 4 Implementation.

This module provides a comprehensive template system for creating, managing,
and applying reusable operation patterns. Templates allow users to save
common workflows and apply them consistently across documents.

Features:
- Template creation and management
- Pattern matching for automatic template suggestions
- Template sharing and import/export
- Version control for templates
- Template categorization and tagging
"""

from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
import json
import uuid
import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLabel, QListWidget, QTextEdit, QComboBox, QSpinBox, QCheckBox,
    QGroupBox, QTabWidget, QSplitter, QTreeWidget, QTreeWidgetItem,
    QDialog, QDialogButtonBox, QProgressBar, QMessageBox, QToolButton,
    QLineEdit, QScrollArea, QFrame, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QPalette, QFont

from .....core.models.element import Element, ElementType
from .....core.state import StateManager
from .....core.events import EventBus
from .....ui.components.base import BaseWidget

logger = logging.getLogger(__name__)


class TemplateType(Enum):
    """Types of operation templates."""
    MERGE = auto()
    SPLIT = auto()
    VALIDATION = auto()
    TRANSFORMATION = auto()
    WORKFLOW = auto()
    CUSTOM = auto()


class TemplateCategory(Enum):
    """Template categories for organization."""
    DOCUMENT_PROCESSING = auto()
    TEXT_MANIPULATION = auto()
    STRUCTURE_ANALYSIS = auto()
    QUALITY_ASSURANCE = auto()
    AUTOMATION = auto()
    USER_DEFINED = auto()


@dataclass
class TemplateMetadata:
    """Metadata for operation templates."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    created_date: datetime = field(default_factory=datetime.now)
    modified_date: datetime = field(default_factory=datetime.now)
    category: TemplateCategory = TemplateCategory.USER_DEFINED
    tags: List[str] = field(default_factory=list)
    usage_count: int = 0
    success_rate: float = 1.0


@dataclass
class TemplateStep:
    """Individual step in a template."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    operation_type: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None
    order: int = 0
    optional: bool = False


@dataclass
class OperationTemplate:
    """Complete operation template definition."""
    metadata: TemplateMetadata = field(default_factory=TemplateMetadata)
    template_type: TemplateType = TemplateType.CUSTOM
    steps: List[TemplateStep] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    expected_inputs: Dict[str, str] = field(default_factory=dict)
    expected_outputs: Dict[str, str] = field(default_factory=dict)
    validation_rules: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary for serialization."""
        return {
            "metadata": {
                "id": self.metadata.id,
                "name": self.metadata.name,
                "description": self.metadata.description,
                "version": self.metadata.version,
                "author": self.metadata.author,
                "created_date": self.metadata.created_date.isoformat(),
                "modified_date": self.metadata.modified_date.isoformat(),
                "category": self.metadata.category.name,
                "tags": self.metadata.tags,
                "usage_count": self.metadata.usage_count,
                "success_rate": self.metadata.success_rate
            },
            "template_type": self.template_type.name,
            "steps": [
                {
                    "id": step.id,
                    "name": step.name,
                    "operation_type": step.operation_type,
                    "parameters": step.parameters,
                    "condition": step.condition,
                    "order": step.order,
                    "optional": step.optional
                }
                for step in self.steps
            ],
            "prerequisites": self.prerequisites,
            "expected_inputs": self.expected_inputs,
            "expected_outputs": self.expected_outputs,
            "validation_rules": self.validation_rules
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OperationTemplate':
        """Create template from dictionary."""
        metadata_data = data.get("metadata", {})
        metadata = TemplateMetadata(
            id=metadata_data.get("id", str(uuid.uuid4())),
            name=metadata_data.get("name", ""),
            description=metadata_data.get("description", ""),
            version=metadata_data.get("version", "1.0.0"),
            author=metadata_data.get("author", ""),
            created_date=datetime.fromisoformat(metadata_data.get("created_date", datetime.now().isoformat())),
            modified_date=datetime.fromisoformat(metadata_data.get("modified_date", datetime.now().isoformat())),
            category=TemplateCategory[metadata_data.get("category", "USER_DEFINED")],
            tags=metadata_data.get("tags", []),
            usage_count=metadata_data.get("usage_count", 0),
            success_rate=metadata_data.get("success_rate", 1.0)
        )
        
        steps = [
            TemplateStep(
                id=step_data.get("id", str(uuid.uuid4())),
                name=step_data.get("name", ""),
                operation_type=step_data.get("operation_type", ""),
                parameters=step_data.get("parameters", {}),
                condition=step_data.get("condition"),
                order=step_data.get("order", 0),
                optional=step_data.get("optional", False)
            )
            for step_data in data.get("steps", [])
        ]
        
        return cls(
            metadata=metadata,
            template_type=TemplateType[data.get("template_type", "CUSTOM")],
            steps=steps,
            prerequisites=data.get("prerequisites", []),
            expected_inputs=data.get("expected_inputs", {}),
            expected_outputs=data.get("expected_outputs", {}),
            validation_rules=data.get("validation_rules", [])
        )


class TemplatePatternMatcher:
    """Matches current context against template patterns."""
    
    def __init__(self):
        self.pattern_cache: Dict[str, float] = {}
    
    def match_template(self, template: OperationTemplate, context: Dict[str, Any]) -> float:
        """Calculate how well a template matches the current context."""
        cache_key = f"{template.metadata.id}_{hash(str(context))}"
        
        if cache_key in self.pattern_cache:
            return self.pattern_cache[cache_key]
        
        score = 0.0
        
        # Check template type match
        context_type = context.get("operation_intent")
        if context_type and context_type.upper() == template.template_type.name:
            score += 0.4
        
        # Check input requirements
        available_inputs = set(context.keys())
        required_inputs = set(template.expected_inputs.keys())
        
        if required_inputs:
            input_match = len(available_inputs & required_inputs) / len(required_inputs)
            score += input_match * 0.3
        
        # Check element count compatibility
        selected_elements = context.get("selected_elements", [])
        element_count = len(selected_elements)
        
        # Heuristic scoring based on element count and template type
        if template.template_type == TemplateType.MERGE and element_count > 1:
            score += 0.2
        elif template.template_type == TemplateType.SPLIT and element_count == 1:
            score += 0.2
        
        # Success rate factor
        score *= template.metadata.success_rate
        
        self.pattern_cache[cache_key] = score
        return score
    
    def get_matching_templates(self, templates: List[OperationTemplate], 
                             context: Dict[str, Any], threshold: float = 0.3) -> List[tuple]:
        """Get templates that match context above threshold."""
        matches = []
        
        for template in templates:
            score = self.match_template(template, context)
            if score >= threshold:
                matches.append((template, score))
        
        # Sort by score descending
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches


class TemplateEngine:
    """Core template management engine."""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path) if storage_path else Path.home() / ".torematrix" / "templates"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.templates: Dict[str, OperationTemplate] = {}
        self.pattern_matcher = TemplatePatternMatcher()
        
        self._load_templates()
        self._load_default_templates()
    
    def _load_templates(self):
        """Load templates from storage."""
        try:
            for template_file in self.storage_path.glob("*.json"):
                with open(template_file, 'r') as f:
                    template_data = json.load(f)
                    template = OperationTemplate.from_dict(template_data)
                    self.templates[template.metadata.id] = template
        except Exception as e:
            logger.error(f"Error loading templates: {e}")
    
    def _load_default_templates(self):
        """Load default built-in templates."""
        # Text merge template
        merge_template = OperationTemplate(
            metadata=TemplateMetadata(
                name="Text Element Merge",
                description="Merge multiple text elements with customizable separator",
                category=TemplateCategory.TEXT_MANIPULATION,
                tags=["merge", "text", "combine"],
                author="System"
            ),
            template_type=TemplateType.MERGE,
            steps=[
                TemplateStep(
                    name="Validate Selection",
                    operation_type="validate_selection",
                    parameters={"min_elements": 2, "element_type": "text"},
                    order=1
                ),
                TemplateStep(
                    name="Merge Text",
                    operation_type="merge_text",
                    parameters={"separator": " ", "preserve_formatting": True},
                    order=2
                )
            ],
            expected_inputs={"selected_elements": "List of text elements"},
            expected_outputs={"merged_element": "Single merged text element"}
        )
        
        # Document split template
        split_template = OperationTemplate(
            metadata=TemplateMetadata(
                name="Document Section Split",
                description="Split large document sections into smaller parts",
                category=TemplateCategory.DOCUMENT_PROCESSING,
                tags=["split", "section", "structure"],
                author="System"
            ),
            template_type=TemplateType.SPLIT,
            steps=[
                TemplateStep(
                    name="Analyze Structure",
                    operation_type="analyze_structure",
                    parameters={"detect_headings": True, "min_section_length": 100},
                    order=1
                ),
                TemplateStep(
                    name="Split Content",
                    operation_type="split_content",
                    parameters={"split_method": "semantic", "max_parts": 10},
                    order=2
                )
            ],
            expected_inputs={"target_element": "Large document element"},
            expected_outputs={"split_elements": "List of smaller elements"}
        )
        
        self.templates[merge_template.metadata.id] = merge_template
        self.templates[split_template.metadata.id] = split_template
    
    def create_template(self, template: OperationTemplate) -> bool:
        """Create a new template."""
        try:
            self.templates[template.metadata.id] = template
            self._save_template(template)
            return True
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            return False
    
    def update_template(self, template: OperationTemplate) -> bool:
        """Update an existing template."""
        try:
            template.metadata.modified_date = datetime.now()
            self.templates[template.metadata.id] = template
            self._save_template(template)
            return True
        except Exception as e:
            logger.error(f"Error updating template: {e}")
            return False
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        try:
            if template_id in self.templates:
                del self.templates[template_id]
                
                # Remove file
                template_file = self.storage_path / f"{template_id}.json"
                if template_file.exists():
                    template_file.unlink()
                
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting template: {e}")
            return False
    
    def get_template(self, template_id: str) -> Optional[OperationTemplate]:
        """Get template by ID."""
        return self.templates.get(template_id)
    
    def get_all_templates(self) -> List[OperationTemplate]:
        """Get all templates."""
        return list(self.templates.values())
    
    def get_templates_by_category(self, category: TemplateCategory) -> List[OperationTemplate]:
        """Get templates by category."""
        return [t for t in self.templates.values() if t.metadata.category == category]
    
    def search_templates(self, query: str) -> List[OperationTemplate]:
        """Search templates by name, description, or tags."""
        query_lower = query.lower()
        matches = []
        
        for template in self.templates.values():
            if (query_lower in template.metadata.name.lower() or
                query_lower in template.metadata.description.lower() or
                any(query_lower in tag.lower() for tag in template.metadata.tags)):
                matches.append(template)
        
        return matches
    
    def get_matching_templates(self, context: Dict[str, Any]) -> List[tuple]:
        """Get templates that match the current context."""
        return self.pattern_matcher.get_matching_templates(
            list(self.templates.values()), context
        )
    
    def _save_template(self, template: OperationTemplate):
        """Save template to storage."""
        template_file = self.storage_path / f"{template.metadata.id}.json"
        with open(template_file, 'w') as f:
            json.dump(template.to_dict(), f, indent=2)
    
    def export_template(self, template_id: str, export_path: str) -> bool:
        """Export template to file."""
        try:
            template = self.get_template(template_id)
            if template:
                with open(export_path, 'w') as f:
                    json.dump(template.to_dict(), f, indent=2)
                return True
            return False
        except Exception as e:
            logger.error(f"Error exporting template: {e}")
            return False
    
    def import_template(self, import_path: str) -> Optional[OperationTemplate]:
        """Import template from file."""
        try:
            with open(import_path, 'r') as f:
                template_data = json.load(f)
                template = OperationTemplate.from_dict(template_data)
                
                # Generate new ID to avoid conflicts
                template.metadata.id = str(uuid.uuid4())
                
                self.create_template(template)
                return template
        except Exception as e:
            logger.error(f"Error importing template: {e}")
            return None


class TemplateManagerWidget(BaseWidget):
    """Widget for managing operation templates."""
    
    template_selected = pyqtSignal(str)  # template_id
    template_applied = pyqtSignal(str, dict)  # template_id, parameters
    
    def __init__(self, state_manager: StateManager, event_bus: EventBus, parent=None):
        super().__init__(state_manager, event_bus, parent)
        
        self.template_engine = TemplateEngine()
        
        self._setup_ui()
        self._connect_signals()
        self._refresh_templates()
    
    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Templates tab
        self.templates_tab = self._create_templates_tab()
        self.tab_widget.addTab(self.templates_tab, "Templates")
        
        # Create tab
        self.create_tab = self._create_template_creation_tab()
        self.tab_widget.addTab(self.create_tab, "Create")
        
        # Suggestions tab
        self.suggestions_tab = self._create_suggestions_tab()
        self.tab_widget.addTab(self.suggestions_tab, "Suggestions")
        
        layout.addWidget(self.tab_widget)
    
    def _create_templates_tab(self) -> QWidget:
        """Create templates management tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Template list
        self.templates_list = QListWidget()
        layout.addWidget(self.templates_list)
        
        # Control buttons
        buttons_layout = QHBoxLayout()
        self.apply_template_btn = QPushButton("Apply Template")
        self.edit_template_btn = QPushButton("Edit Template")
        self.delete_template_btn = QPushButton("Delete Template")
        self.export_template_btn = QPushButton("Export Template")
        self.import_template_btn = QPushButton("Import Template")
        
        buttons_layout.addWidget(self.apply_template_btn)
        buttons_layout.addWidget(self.edit_template_btn)
        buttons_layout.addWidget(self.delete_template_btn)
        buttons_layout.addWidget(self.export_template_btn)
        buttons_layout.addWidget(self.import_template_btn)
        
        layout.addLayout(buttons_layout)
        
        return widget
    
    def _create_template_creation_tab(self) -> QWidget:
        """Create template creation tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Template creation form
        form_group = QGroupBox("New Template")
        form_layout = QGridLayout(form_group)
        
        self.name_edit = QLineEdit()
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        self.category_combo = QComboBox()
        for category in TemplateCategory:
            self.category_combo.addItem(category.name.title().replace('_', ' '))
        
        form_layout.addWidget(QLabel("Name:"), 0, 0)
        form_layout.addWidget(self.name_edit, 0, 1)
        form_layout.addWidget(QLabel("Description:"), 1, 0)
        form_layout.addWidget(self.description_edit, 1, 1)
        form_layout.addWidget(QLabel("Category:"), 2, 0)
        form_layout.addWidget(self.category_combo, 2, 1)
        
        layout.addWidget(form_group)
        
        # Create button
        self.create_template_btn = QPushButton("Create Template")
        layout.addWidget(self.create_template_btn)
        
        return widget
    
    def _create_suggestions_tab(self) -> QWidget:
        """Create template suggestions tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Context info
        context_group = QGroupBox("Current Context")
        context_layout = QVBoxLayout(context_group)
        
        self.context_label = QLabel("No active context")
        context_layout.addWidget(self.context_label)
        
        layout.addWidget(context_group)
        
        # Suggestions list
        suggestions_group = QGroupBox("Suggested Templates")
        suggestions_layout = QVBoxLayout(suggestions_group)
        
        self.suggestions_list = QListWidget()
        suggestions_layout.addWidget(self.suggestions_list)
        
        # Apply suggestion button
        self.apply_suggestion_btn = QPushButton("Apply Selected Template")
        self.apply_suggestion_btn.setEnabled(False)
        suggestions_layout.addWidget(self.apply_suggestion_btn)
        
        layout.addWidget(suggestions_group)
        
        return widget
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.apply_template_btn.clicked.connect(self._apply_selected_template)
        self.create_template_btn.clicked.connect(self._create_new_template)
        self.import_template_btn.clicked.connect(self._import_template)
        self.export_template_btn.clicked.connect(self._export_template)
        self.delete_template_btn.clicked.connect(self._delete_template)
        
        self.templates_list.itemSelectionChanged.connect(self._on_template_selection_changed)
        self.suggestions_list.itemSelectionChanged.connect(self._on_suggestion_selection_changed)
    
    def _refresh_templates(self):
        """Refresh the templates list."""
        self.templates_list.clear()
        
        for template in self.template_engine.get_all_templates():
            item_text = f"{template.metadata.name} ({template.template_type.name})"
            self.templates_list.addItem(item_text)
    
    def _apply_selected_template(self):
        """Apply the selected template."""
        current_row = self.templates_list.currentRow()
        if current_row >= 0:
            templates = self.template_engine.get_all_templates()
            if current_row < len(templates):
                template = templates[current_row]
                self.template_applied.emit(template.metadata.id, {})
    
    def _create_new_template(self):
        """Create a new template."""
        name = self.name_edit.text().strip()
        description = self.description_edit.toPlainText().strip()
        
        if not name:
            QMessageBox.warning(self, "Error", "Template name is required")
            return
        
        category_index = self.category_combo.currentIndex()
        category = list(TemplateCategory)[category_index]
        
        template = OperationTemplate(
            metadata=TemplateMetadata(
                name=name,
                description=description,
                category=category
            )
        )
        
        if self.template_engine.create_template(template):
            QMessageBox.information(self, "Success", "Template created successfully")
            self._refresh_templates()
            self.name_edit.clear()
            self.description_edit.clear()
        else:
            QMessageBox.warning(self, "Error", "Failed to create template")
    
    def _import_template(self):
        """Import a template from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Template", "", "JSON Files (*.json)"
        )
        
        if file_path:
            template = self.template_engine.import_template(file_path)
            if template:
                QMessageBox.information(self, "Success", f"Template '{template.metadata.name}' imported successfully")
                self._refresh_templates()
            else:
                QMessageBox.warning(self, "Error", "Failed to import template")
    
    def _export_template(self):
        """Export the selected template."""
        current_row = self.templates_list.currentRow()
        if current_row >= 0:
            templates = self.template_engine.get_all_templates()
            if current_row < len(templates):
                template = templates[current_row]
                
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "Export Template", f"{template.metadata.name}.json", "JSON Files (*.json)"
                )
                
                if file_path:
                    if self.template_engine.export_template(template.metadata.id, file_path):
                        QMessageBox.information(self, "Success", "Template exported successfully")
                    else:
                        QMessageBox.warning(self, "Error", "Failed to export template")
    
    def _delete_template(self):
        """Delete the selected template."""
        current_row = self.templates_list.currentRow()
        if current_row >= 0:
            templates = self.template_engine.get_all_templates()
            if current_row < len(templates):
                template = templates[current_row]
                
                reply = QMessageBox.question(
                    self, "Confirm Delete",
                    f"Delete template '{template.metadata.name}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    if self.template_engine.delete_template(template.metadata.id):
                        QMessageBox.information(self, "Success", "Template deleted successfully")
                        self._refresh_templates()
                    else:
                        QMessageBox.warning(self, "Error", "Failed to delete template")
    
    def _on_template_selection_changed(self):
        """Handle template selection change."""
        has_selection = len(self.templates_list.selectedItems()) > 0
        self.apply_template_btn.setEnabled(has_selection)
        self.edit_template_btn.setEnabled(has_selection)
        self.delete_template_btn.setEnabled(has_selection)
        self.export_template_btn.setEnabled(has_selection)
    
    def _on_suggestion_selection_changed(self):
        """Handle suggestion selection change."""
        has_selection = len(self.suggestions_list.selectedItems()) > 0
        self.apply_suggestion_btn.setEnabled(has_selection)