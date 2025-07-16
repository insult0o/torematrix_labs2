"""
Template System for Merge/Split Operations - Agent 4 Implementation.

This module provides a comprehensive template system for common merge/split operation
patterns. It allows users to save, reuse, and share operation configurations to
streamline repetitive tasks and ensure consistency across documents.

Features:
- Template creation from existing operations
- Pre-defined operation patterns
- Template validation and verification
- Template sharing and import/export
- Pattern matching for auto-suggestions
"""

from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
import json
import uuid
from datetime import datetime
from pathlib import Path
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLabel, QListWidget, QTextEdit, QComboBox, QSpinBox, QCheckBox,
    QGroupBox, QTabWidget, QSplitter, QTreeWidget, QTreeWidgetItem,
    QDialog, QDialogButtonBox, QProgressBar, QMessageBox, QToolButton,
    QLineEdit, QScrollArea, QFrame, QSlider, QButtonGroup, QRadioButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QMutex, QWaitCondition
from PyQt6.QtGui import QIcon, QPalette, QFont, QValidator

from .....core.models.element import Element, ElementType
from .....core.state import StateManager
from .....core.events import EventBus
from .....ui.components.base import BaseWidget

logger = logging.getLogger(__name__)


class TemplateType(Enum):
    """Types of operation templates."""
    MERGE = auto()
    SPLIT = auto()
    TRANSFORM = auto()
    BATCH = auto()
    CUSTOM = auto()


class TemplateCategory(Enum):
    """Template categories for organization."""
    DOCUMENT_PROCESSING = auto()
    DATA_EXTRACTION = auto()
    CONTENT_ORGANIZATION = auto()
    QUALITY_IMPROVEMENT = auto()
    AUTOMATION = auto()
    USER_DEFINED = auto()


class ValidationLevel(Enum):
    """Template validation levels."""
    NONE = auto()
    BASIC = auto()
    STRICT = auto()
    CUSTOM = auto()


@dataclass
class TemplateMetadata:
    """Metadata for operation templates."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    category: TemplateCategory = TemplateCategory.USER_DEFINED
    template_type: TemplateType = TemplateType.CUSTOM
    author: str = ""
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    success_rate: float = 1.0
    tags: List[str] = field(default_factory=list)
    compatibility: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TemplateStep:
    """Individual step in a template."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    operation: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    conditions: Dict[str, Any] = field(default_factory=dict)
    validation: Dict[str, Any] = field(default_factory=dict)
    retry_config: Dict[str, Any] = field(default_factory=dict)
    parallel: bool = False
    optional: bool = False


@dataclass
class OperationTemplate:
    """Complete operation template definition."""
    metadata: TemplateMetadata = field(default_factory=TemplateMetadata)
    steps: List[TemplateStep] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    pre_conditions: List[str] = field(default_factory=list)
    post_conditions: List[str] = field(default_factory=list)
    error_handling: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            "metadata": {
                "id": self.metadata.id,
                "name": self.metadata.name,
                "description": self.metadata.description,
                "category": self.metadata.category.name,
                "template_type": self.metadata.template_type.name,
                "author": self.metadata.author,
                "version": self.metadata.version,
                "created_at": self.metadata.created_at.isoformat(),
                "modified_at": self.metadata.modified_at.isoformat(),
                "usage_count": self.metadata.usage_count,
                "success_rate": self.metadata.success_rate,
                "tags": self.metadata.tags,
                "compatibility": self.metadata.compatibility
            },
            "steps": [
                {
                    "id": step.id,
                    "name": step.name,
                    "operation": step.operation,
                    "parameters": step.parameters,
                    "conditions": step.conditions,
                    "validation": step.validation,
                    "retry_config": step.retry_config,
                    "parallel": step.parallel,
                    "optional": step.optional
                }
                for step in self.steps
            ],
            "variables": self.variables,
            "constraints": self.constraints,
            "pre_conditions": self.pre_conditions,
            "post_conditions": self.post_conditions,
            "error_handling": self.error_handling
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OperationTemplate':
        """Create template from dictionary."""
        metadata_data = data.get("metadata", {})
        metadata = TemplateMetadata(
            id=metadata_data.get("id", str(uuid.uuid4())),
            name=metadata_data.get("name", ""),
            description=metadata_data.get("description", ""),
            category=TemplateCategory[metadata_data.get("category", "USER_DEFINED")],
            template_type=TemplateType[metadata_data.get("template_type", "CUSTOM")],
            author=metadata_data.get("author", ""),
            version=metadata_data.get("version", "1.0.0"),
            created_at=datetime.fromisoformat(metadata_data.get("created_at", datetime.now().isoformat())),
            modified_at=datetime.fromisoformat(metadata_data.get("modified_at", datetime.now().isoformat())),
            usage_count=metadata_data.get("usage_count", 0),
            success_rate=metadata_data.get("success_rate", 1.0),
            tags=metadata_data.get("tags", []),
            compatibility=metadata_data.get("compatibility", {})
        )
        
        steps = [
            TemplateStep(
                id=step_data.get("id", str(uuid.uuid4())),
                name=step_data.get("name", ""),
                operation=step_data.get("operation", ""),
                parameters=step_data.get("parameters", {}),
                conditions=step_data.get("conditions", {}),
                validation=step_data.get("validation", {}),
                retry_config=step_data.get("retry_config", {}),
                parallel=step_data.get("parallel", False),
                optional=step_data.get("optional", False)
            )
            for step_data in data.get("steps", [])
        ]
        
        return cls(
            metadata=metadata,
            steps=steps,
            variables=data.get("variables", {}),
            constraints=data.get("constraints", {}),
            pre_conditions=data.get("pre_conditions", []),
            post_conditions=data.get("post_conditions", []),
            error_handling=data.get("error_handling", {})
        )


class TemplateEngine:
    """Core engine for template management and execution."""
    
    def __init__(self, state_manager: StateManager, event_bus: EventBus):
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.templates: Dict[str, OperationTemplate] = {}
        self.template_storage_path = Path("templates")
        self.pattern_matcher = TemplatePatternMatcher()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._mutex = QMutex()
        
        self._load_built_in_templates()
    
    def _load_built_in_templates(self):
        """Load built-in operation templates."""
        # Document merge template
        merge_template = OperationTemplate(
            metadata=TemplateMetadata(
                name="Document Section Merge",
                description="Merge related document sections with metadata preservation",
                category=TemplateCategory.DOCUMENT_PROCESSING,
                template_type=TemplateType.MERGE,
                author="System",
                tags=["merge", "document", "sections"]
            ),
            steps=[
                TemplateStep(
                    name="Validate Elements",
                    operation="validate_elements",
                    parameters={"check_compatibility": True},
                    validation={"required_fields": ["text", "bounds"]}
                ),
                TemplateStep(
                    name="Merge Content",
                    operation="merge_content",
                    parameters={"preserve_formatting": True, "separator": "\n"},
                    validation={"max_length": 10000}
                ),
                TemplateStep(
                    name="Update Metadata",
                    operation="update_metadata",
                    parameters={"merge_strategy": "combine"},
                    validation={"preserve_original": True}
                )
            ],
            pre_conditions=["elements_selected", "compatible_types"],
            post_conditions=["merged_element_created", "original_elements_removed"]
        )
        
        # Content split template
        split_template = OperationTemplate(
            metadata=TemplateMetadata(
                name="Content Split by Pattern",
                description="Split content based on patterns or delimiters",
                category=TemplateCategory.DATA_EXTRACTION,
                template_type=TemplateType.SPLIT,
                author="System",
                tags=["split", "pattern", "content"]
            ),
            steps=[
                TemplateStep(
                    name="Analyze Content",
                    operation="analyze_content",
                    parameters={"detect_patterns": True},
                    validation={"min_content_length": 10}
                ),
                TemplateStep(
                    name="Apply Split Pattern",
                    operation="split_content",
                    parameters={"pattern": "{{split_pattern}}", "preserve_whitespace": False},
                    validation={"min_parts": 2}
                ),
                TemplateStep(
                    name="Create Elements",
                    operation="create_elements",
                    parameters={"inherit_properties": True},
                    validation={"unique_ids": True}
                )
            ],
            variables={"split_pattern": "\\n\\n"},
            pre_conditions=["element_selected", "has_content"],
            post_conditions=["multiple_elements_created", "original_element_removed"]
        )
        
        # Quality improvement template
        quality_template = OperationTemplate(
            metadata=TemplateMetadata(
                name="Text Quality Enhancement",
                description="Improve text quality through cleaning and formatting",
                category=TemplateCategory.QUALITY_IMPROVEMENT,
                template_type=TemplateType.TRANSFORM,
                author="System",
                tags=["quality", "text", "cleanup"]
            ),
            steps=[
                TemplateStep(
                    name="Clean Text",
                    operation="clean_text",
                    parameters={"remove_extra_whitespace": True, "fix_encoding": True},
                    validation={"preserve_meaning": True}
                ),
                TemplateStep(
                    name="Format Text",
                    operation="format_text",
                    parameters={"normalize_quotes": True, "fix_punctuation": True},
                    validation={"readability_score": 0.7}
                ),
                TemplateStep(
                    name="Validate Result",
                    operation="validate_result",
                    parameters={"check_completeness": True},
                    validation={"quality_threshold": 0.8}
                )
            ],
            pre_conditions=["text_element_selected"],
            post_conditions=["text_improved", "quality_score_increased"]
        )
        
        self.templates[merge_template.metadata.id] = merge_template
        self.templates[split_template.metadata.id] = split_template
        self.templates[quality_template.metadata.id] = quality_template
    
    async def create_template_from_operation(self, operation_data: Dict[str, Any], 
                                           metadata: TemplateMetadata) -> OperationTemplate:
        """Create a template from an executed operation."""
        template = OperationTemplate(metadata=metadata)
        
        # Extract steps from operation data
        if "steps" in operation_data:
            for step_data in operation_data["steps"]:
                step = TemplateStep(
                    name=step_data.get("name", ""),
                    operation=step_data.get("operation", ""),
                    parameters=step_data.get("parameters", {}),
                    conditions=step_data.get("conditions", {}),
                    validation=step_data.get("validation", {})
                )
                template.steps.append(step)
        
        # Store template
        self.templates[template.metadata.id] = template
        await self._save_template(template)
        
        return template
    
    async def execute_template(self, template_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a template with given context."""
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")
        
        template = self.templates[template_id]
        
        # Validate pre-conditions
        for condition in template.pre_conditions:
            if not await self._check_condition(condition, context):
                raise ValueError(f"Pre-condition failed: {condition}")
        
        results = []
        
        # Execute steps
        for step in template.steps:
            if not step.optional or await self._check_conditions(step.conditions, context):
                result = await self._execute_step(step, context)
                results.append(result)
                
                # Update context with step results
                context.update(result.get("context_updates", {}))
        
        # Validate post-conditions
        for condition in template.post_conditions:
            if not await self._check_condition(condition, context):
                logger.warning(f"Post-condition failed: {condition}")
        
        # Update usage statistics
        template.metadata.usage_count += 1
        template.metadata.modified_at = datetime.now()
        
        return {"results": results, "template_id": template_id}
    
    async def _execute_step(self, step: TemplateStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single template step."""
        # Substitute variables in parameters
        parameters = self._substitute_variables(step.parameters, context)
        
        # Execute operation based on step.operation
        if step.operation == "validate_elements":
            return await self._validate_elements(parameters, context)
        elif step.operation == "merge_content":
            return await self._merge_content(parameters, context)
        elif step.operation == "split_content":
            return await self._split_content(parameters, context)
        else:
            # Plugin-based operation execution
            return await self._execute_plugin_operation(step.operation, parameters, context)
    
    async def _validate_elements(self, parameters: Dict[str, Any], 
                                context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate elements for template execution."""
        elements = context.get("selected_elements", [])
        
        if not elements:
            return {"success": False, "error": "No elements selected"}
        
        if parameters.get("check_compatibility", False):
            # Check if elements are compatible for merge/split
            types = {elem.element_type for elem in elements}
            if len(types) > 1 and not parameters.get("allow_mixed_types", False):
                return {"success": False, "error": "Incompatible element types"}
        
        return {"success": True, "validated_elements": len(elements)}
    
    async def _merge_content(self, parameters: Dict[str, Any], 
                           context: Dict[str, Any]) -> Dict[str, Any]:
        """Merge content from selected elements."""
        elements = context.get("selected_elements", [])
        separator = parameters.get("separator", " ")
        preserve_formatting = parameters.get("preserve_formatting", True)
        
        if not elements:
            return {"success": False, "error": "No elements to merge"}
        
        # Combine text content
        texts = []
        for element in elements:
            if hasattr(element, 'text') and element.text:
                texts.append(element.text)
        
        merged_text = separator.join(texts)
        
        # Validate length
        max_length = parameters.get("max_length")
        if max_length and len(merged_text) > max_length:
            return {"success": False, "error": f"Merged content exceeds max length: {max_length}"}
        
        return {
            "success": True,
            "merged_text": merged_text,
            "source_count": len(elements),
            "context_updates": {"merged_content": merged_text}
        }
    
    async def _split_content(self, parameters: Dict[str, Any], 
                           context: Dict[str, Any]) -> Dict[str, Any]:
        """Split content based on pattern."""
        element = context.get("selected_element")
        if not element or not hasattr(element, 'text'):
            return {"success": False, "error": "No text element selected"}
        
        pattern = parameters.get("pattern", "\n\n")
        preserve_whitespace = parameters.get("preserve_whitespace", False)
        
        # Split content
        parts = element.text.split(pattern)
        
        if not preserve_whitespace:
            parts = [part.strip() for part in parts if part.strip()]
        
        min_parts = parameters.get("min_parts", 1)
        if len(parts) < min_parts:
            return {"success": False, "error": f"Split resulted in fewer than {min_parts} parts"}
        
        return {
            "success": True,
            "split_parts": parts,
            "part_count": len(parts),
            "context_updates": {"split_parts": parts}
        }
    
    async def _execute_plugin_operation(self, operation: str, parameters: Dict[str, Any],
                                      context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute plugin-based operation."""
        # Placeholder for plugin system integration
        logger.warning(f"Plugin operation not implemented: {operation}")
        return {"success": False, "error": f"Operation not implemented: {operation}"}
    
    def _substitute_variables(self, parameters: Dict[str, Any], 
                            context: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute template variables in parameters."""
        result = {}
        
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                var_name = value[2:-2].strip()
                result[key] = context.get(var_name, value)
            else:
                result[key] = value
        
        return result
    
    async def _check_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Check if a condition is met."""
        # Simple condition checking - can be expanded
        if condition == "elements_selected":
            return bool(context.get("selected_elements"))
        elif condition == "element_selected":
            return bool(context.get("selected_element"))
        elif condition == "has_content":
            element = context.get("selected_element")
            return element and hasattr(element, 'text') and element.text
        elif condition == "compatible_types":
            elements = context.get("selected_elements", [])
            if len(elements) <= 1:
                return True
            types = {elem.element_type for elem in elements}
            return len(types) == 1
        
        return True
    
    async def _check_conditions(self, conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check multiple conditions."""
        for condition, expected in conditions.items():
            actual = context.get(condition)
            if actual != expected:
                return False
        return True
    
    async def _save_template(self, template: OperationTemplate):
        """Save template to storage."""
        if not self.template_storage_path.exists():
            self.template_storage_path.mkdir(parents=True)
        
        template_file = self.template_storage_path / f"{template.metadata.id}.json"
        with open(template_file, 'w') as f:
            json.dump(template.to_dict(), f, indent=2)
    
    def get_template_suggestions(self, context: Dict[str, Any]) -> List[OperationTemplate]:
        """Get template suggestions based on context."""
        return self.pattern_matcher.find_matching_templates(self.templates.values(), context)


class TemplatePatternMatcher:
    """Pattern matching for template suggestions."""
    
    def find_matching_templates(self, templates: List[OperationTemplate], 
                              context: Dict[str, Any]) -> List[OperationTemplate]:
        """Find templates that match the current context."""
        matching = []
        
        for template in templates:
            score = self._calculate_match_score(template, context)
            if score > 0.5:  # Threshold for suggestion
                matching.append((template, score))
        
        # Sort by score (descending)
        matching.sort(key=lambda x: x[1], reverse=True)
        return [template for template, score in matching]
    
    def _calculate_match_score(self, template: OperationTemplate, 
                             context: Dict[str, Any]) -> float:
        """Calculate how well a template matches the context."""
        score = 0.0
        
        # Check element types
        selected_elements = context.get("selected_elements", [])
        if selected_elements:
            element_types = {elem.element_type for elem in selected_elements}
            
            # Score based on template type
            if template.metadata.template_type == TemplateType.MERGE and len(selected_elements) > 1:
                score += 0.4
            elif template.metadata.template_type == TemplateType.SPLIT and len(selected_elements) == 1:
                score += 0.4
            
            # Score based on element compatibility
            if "text" in [elem.element_type.value.lower() for elem in selected_elements]:
                score += 0.3
        
        # Score based on usage statistics
        if template.metadata.usage_count > 0:
            score += min(0.2, template.metadata.success_rate * 0.2)
        
        return min(1.0, score)


class TemplateManagerWidget(BaseWidget):
    """Widget for managing operation templates."""
    
    template_selected = pyqtSignal(str)  # template_id
    template_executed = pyqtSignal(str, dict)  # template_id, context
    
    def __init__(self, state_manager: StateManager, event_bus: EventBus, parent=None):
        super().__init__(state_manager, event_bus, parent)
        
        self.template_engine = TemplateEngine(state_manager, event_bus)
        self.current_template: Optional[OperationTemplate] = None
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Templates tab
        self.templates_tab = self._create_templates_tab()
        self.tab_widget.addTab(self.templates_tab, "Templates")
        
        # Editor tab
        self.editor_tab = self._create_editor_tab()
        self.tab_widget.addTab(self.editor_tab, "Editor")
        
        # Execution tab
        self.execution_tab = self._create_execution_tab()
        self.tab_widget.addTab(self.execution_tab, "Execute")
        
        layout.addWidget(self.tab_widget)
    
    def _create_templates_tab(self) -> QWidget:
        """Create templates browser tab."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Left panel - template list
        left_panel = QVBoxLayout()
        
        # Category filter
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems([cat.name for cat in TemplateCategory])
        category_layout.addWidget(self.category_combo)
        left_panel.addLayout(category_layout)
        
        # Template list
        self.template_list = QListWidget()
        left_panel.addWidget(self.template_list)
        
        # Template actions
        actions_layout = QHBoxLayout()
        self.new_template_btn = QPushButton("New")
        self.duplicate_template_btn = QPushButton("Duplicate")
        self.delete_template_btn = QPushButton("Delete")
        actions_layout.addWidget(self.new_template_btn)
        actions_layout.addWidget(self.duplicate_template_btn)
        actions_layout.addWidget(self.delete_template_btn)
        left_panel.addLayout(actions_layout)
        
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        
        # Right panel - template details
        right_panel = QVBoxLayout()
        
        # Template info
        info_group = QGroupBox("Template Information")
        info_layout = QGridLayout(info_group)
        
        info_layout.addWidget(QLabel("Name:"), 0, 0)
        self.template_name_label = QLabel()
        info_layout.addWidget(self.template_name_label, 0, 1)
        
        info_layout.addWidget(QLabel("Description:"), 1, 0)
        self.template_desc_label = QLabel()
        self.template_desc_label.setWordWrap(True)
        info_layout.addWidget(self.template_desc_label, 1, 1)
        
        info_layout.addWidget(QLabel("Usage:"), 2, 0)
        self.template_usage_label = QLabel()
        info_layout.addWidget(self.template_usage_label, 2, 1)
        
        right_panel.addWidget(info_group)
        
        # Template steps
        steps_group = QGroupBox("Steps")
        steps_layout = QVBoxLayout(steps_group)
        
        self.steps_tree = QTreeWidget()
        self.steps_tree.setHeaderLabels(["Step", "Operation", "Parameters"])
        steps_layout.addWidget(self.steps_tree)
        
        right_panel.addWidget(steps_group)
        
        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        
        # Create splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 500])
        
        layout.addWidget(splitter)
        
        return widget
    
    def _create_editor_tab(self) -> QWidget:
        """Create template editor tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Editor toolbar
        toolbar_layout = QHBoxLayout()
        self.save_template_btn = QPushButton("Save")
        self.load_template_btn = QPushButton("Load")
        self.validate_template_btn = QPushButton("Validate")
        toolbar_layout.addWidget(self.save_template_btn)
        toolbar_layout.addWidget(self.load_template_btn)
        toolbar_layout.addWidget(self.validate_template_btn)
        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)
        
        # Template editor (simplified - would need full editor implementation)
        self.template_editor = QTextEdit()
        self.template_editor.setPlaceholderText("Template JSON will appear here...")
        layout.addWidget(self.template_editor)
        
        return widget
    
    def _create_execution_tab(self) -> QWidget:
        """Create template execution tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Context setup
        context_group = QGroupBox("Execution Context")
        context_layout = QVBoxLayout(context_group)
        
        # Selected elements info
        elements_layout = QHBoxLayout()
        elements_layout.addWidget(QLabel("Selected Elements:"))
        self.selected_elements_label = QLabel("None")
        elements_layout.addWidget(self.selected_elements_label)
        context_layout.addLayout(elements_layout)
        
        # Variables
        variables_layout = QVBoxLayout()
        variables_layout.addWidget(QLabel("Template Variables:"))
        self.variables_widget = QWidget()
        variables_layout.addWidget(self.variables_widget)
        context_layout.addLayout(variables_layout)
        
        layout.addWidget(context_group)
        
        # Execution controls
        exec_layout = QHBoxLayout()
        self.execute_btn = QPushButton("Execute Template")
        self.execute_btn.setEnabled(False)
        self.preview_btn = QPushButton("Preview")
        exec_layout.addWidget(self.execute_btn)
        exec_layout.addWidget(self.preview_btn)
        exec_layout.addStretch()
        layout.addLayout(exec_layout)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Results
        results_group = QGroupBox("Execution Results")
        results_layout = QVBoxLayout(results_group)
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        layout.addWidget(results_group)
        
        return widget
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.template_list.currentItemChanged.connect(self._on_template_selected)
        self.execute_btn.clicked.connect(self._execute_current_template)
        self.new_template_btn.clicked.connect(self._create_new_template)
        self.category_combo.currentTextChanged.connect(self._filter_templates)
        
    def _load_templates(self):
        """Load templates into the list."""
        self.template_list.clear()
        
        category = self.category_combo.currentText()
        templates = self.template_engine.templates.values()
        
        if category != "ALL":
            templates = [t for t in templates if t.metadata.category.name == category]
        
        for template in templates:
            item_text = f"{template.metadata.name} ({template.metadata.template_type.name})"
            item = self.template_list.addItem(item_text)
            # Store template ID in item data
            self.template_list.item(self.template_list.count() - 1).setData(Qt.ItemDataRole.UserRole, template.metadata.id)
    
    def _on_template_selected(self, current, previous):
        """Handle template selection."""
        if not current:
            return
        
        template_id = current.data(Qt.ItemDataRole.UserRole)
        if template_id in self.template_engine.templates:
            self.current_template = self.template_engine.templates[template_id]
            self._update_template_details()
            self.execute_btn.setEnabled(True)
            self.template_selected.emit(template_id)
    
    def _update_template_details(self):
        """Update template details display."""
        if not self.current_template:
            return
        
        template = self.current_template
        
        # Update info labels
        self.template_name_label.setText(template.metadata.name)
        self.template_desc_label.setText(template.metadata.description)
        self.template_usage_label.setText(
            f"Used {template.metadata.usage_count} times, {template.metadata.success_rate:.1%} success rate"
        )
        
        # Update steps tree
        self.steps_tree.clear()
        for step in template.steps:
            item = QTreeWidgetItem([
                step.name,
                step.operation,
                str(len(step.parameters)) + " params"
            ])
            self.steps_tree.addTopLevelItem(item)
        
        # Update template editor
        self.template_editor.setText(json.dumps(template.to_dict(), indent=2))
    
    async def _execute_current_template(self):
        """Execute the currently selected template."""
        if not self.current_template:
            return
        
        # Prepare context
        context = {
            "selected_elements": self.state_manager.get_selected_elements(),
            "selected_element": self.state_manager.get_primary_selection()
        }
        
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate
            
            result = await self.template_engine.execute_template(
                self.current_template.metadata.id, 
                context
            )
            
            self.results_text.setText(json.dumps(result, indent=2))
            self.template_executed.emit(self.current_template.metadata.id, context)
            
        except Exception as e:
            QMessageBox.warning(self, "Template Execution Error", str(e))
            self.results_text.setText(f"Error: {str(e)}")
        finally:
            self.progress_bar.setVisible(False)
    
    def _create_new_template(self):
        """Create a new template."""
        # Placeholder for template creation dialog
        QMessageBox.information(self, "Create Template", "Template creation dialog would open here")
    
    def _filter_templates(self):
        """Filter templates by category."""
        self._load_templates()
    
    def showEvent(self, event):
        """Handle widget show event."""
        super().showEvent(event)
        self._load_templates()