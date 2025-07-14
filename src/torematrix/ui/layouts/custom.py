"""Custom layout creation and management for ToreMatrix V3.

Provides tools for creating, editing, and managing custom layout templates
with user-friendly interfaces and template derivation capabilities.
"""

from typing import Dict, List, Optional, Any, Callable, Union, Set
from dataclasses import dataclass, field
from pathlib import Path
import json
import logging
from datetime import datetime, timezone
from enum import Enum
import copy

from PyQt6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QComboBox,
    QListWidget, QListWidgetItem, QSplitter, QTabWidget,
    QCheckBox, QSpinBox, QGroupBox, QFormLayout, QMessageBox,
    QScrollArea, QFrame
)
from PyQt6.QtCore import QObject, pyqtSignal, QSize, Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter

from ..base import BaseUIComponent
from ...core.events import EventBus
from ...core.config import ConfigManager  
from ...core.state import StateManager
from .serialization import LayoutMetadata, LayoutType, LayoutNode
from .persistence import LayoutPersistence, LayoutStorageType

logger = logging.getLogger(__name__)


class LayoutError(Exception):
    """Raised when layout operations fail."""
    pass


class TemplateCategory(Enum):
    """Template categories for organization."""
    DOCUMENT = "document"
    ANALYSIS = "analysis"
    COMPARISON = "comparison"
    DEBUG = "debug"
    CUSTOM = "custom"
    WORKFLOW = "workflow"


@dataclass
class LayoutConstraint:
    """Layout constraint definition."""
    min_width: Optional[int] = None
    max_width: Optional[int] = None
    min_height: Optional[int] = None
    max_height: Optional[int] = None
    aspect_ratio: Optional[float] = None
    fixed_size: bool = False
    resizable: bool = True


@dataclass
class ComponentSlot:
    """Represents a slot where components can be placed."""
    slot_id: str
    slot_type: str
    display_name: str
    description: str = ""
    required: bool = False
    multiple: bool = False
    constraints: LayoutConstraint = field(default_factory=LayoutConstraint)
    default_component: Optional[str] = None
    allowed_components: List[str] = field(default_factory=list)


@dataclass
class LayoutTemplate:
    """Layout template definition."""
    template_id: str
    name: str
    description: str
    category: TemplateCategory
    author: str = ""
    version: str = "1.0.0"
    created: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    modified: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Template structure
    root_layout_type: LayoutType = LayoutType.SPLITTER
    component_slots: List[ComponentSlot] = field(default_factory=list)
    layout_properties: Dict[str, Any] = field(default_factory=dict)
    global_constraints: LayoutConstraint = field(default_factory=LayoutConstraint)
    
    # Template metadata
    tags: List[str] = field(default_factory=list)
    preview_image: Optional[str] = None
    usage_count: int = 0
    rating: float = 0.0
    
    # Template inheritance
    derived_from: Optional[str] = None
    derivation_notes: str = ""


class LayoutTemplateManager:
    """Manages layout templates and their operations."""
    
    def __init__(
        self,
        persistence: LayoutPersistence,
        template_path: Optional[Path] = None
    ):
        self._persistence = persistence
        self._template_path = template_path or Path.home() / ".torematrix" / "templates"
        self._template_path.mkdir(parents=True, exist_ok=True)
        
        self._templates: Dict[str, LayoutTemplate] = {}
        self._component_registry: Dict[str, type] = {}
        
        self._load_builtin_templates()
        self._load_user_templates()
    
    def register_component_type(self, component_id: str, component_type: type) -> None:
        """Register a component type for template usage."""
        self._component_registry[component_id] = component_type
        logger.debug(f"Registered component type: {component_id}")
    
    def create_template(
        self,
        template_id: str,
        name: str,
        description: str,
        category: TemplateCategory,
        root_layout_type: LayoutType = LayoutType.SPLITTER
    ) -> LayoutTemplate:
        """Create a new layout template."""
        if template_id in self._templates:
            raise LayoutError(f"Template '{template_id}' already exists")
        
        template = LayoutTemplate(
            template_id=template_id,
            name=name,
            description=description,
            category=category,
            root_layout_type=root_layout_type
        )
        
        self._templates[template_id] = template
        self._save_template(template)
        
        logger.info(f"Created template '{template_id}'")
        return template
    
    def derive_template(
        self,
        base_template_id: str,
        new_template_id: str,
        name: str,
        description: str,
        modifications: Dict[str, Any] = None
    ) -> LayoutTemplate:
        """Derive a new template from an existing one."""
        if new_template_id in self._templates:
            raise LayoutError(f"Template '{new_template_id}' already exists")
        
        if base_template_id not in self._templates:
            raise LayoutError(f"Base template '{base_template_id}' not found")
        
        base_template = self._templates[base_template_id]
        
        # Deep copy the base template
        derived_template = copy.deepcopy(base_template)
        derived_template.template_id = new_template_id
        derived_template.name = name
        derived_template.description = description
        derived_template.derived_from = base_template_id
        derived_template.created = datetime.now(timezone.utc)
        derived_template.modified = datetime.now(timezone.utc)
        derived_template.usage_count = 0
        derived_template.rating = 0.0
        
        # Apply modifications if provided
        if modifications:
            self._apply_template_modifications(derived_template, modifications)
        
        self._templates[new_template_id] = derived_template
        self._save_template(derived_template)
        
        logger.info(f"Derived template '{new_template_id}' from '{base_template_id}'")
        return derived_template
    
    def get_template(self, template_id: str) -> Optional[LayoutTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)
    
    def list_templates(
        self,
        category: Optional[TemplateCategory] = None,
        tag_filter: Optional[List[str]] = None
    ) -> List[LayoutTemplate]:
        """List available templates with optional filtering."""
        templates = list(self._templates.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        if tag_filter:
            templates = [
                t for t in templates
                if any(tag in t.tags for tag in tag_filter)
            ]
        
        # Sort by usage count and rating
        templates.sort(key=lambda t: (t.usage_count, t.rating), reverse=True)
        
        return templates
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        if template_id not in self._templates:
            return False
        
        template = self._templates.pop(template_id)
        
        # Remove template file
        template_file = self._template_path / f"{template_id}.json"
        if template_file.exists():
            template_file.unlink()
        
        logger.info(f"Deleted template '{template_id}'")
        return True
    
    def add_component_slot(
        self,
        template_id: str,
        slot_id: str,
        slot_type: str,
        display_name: str,
        description: str = "",
        required: bool = False,
        constraints: Optional[LayoutConstraint] = None
    ) -> bool:
        """Add a component slot to a template."""
        template = self._templates.get(template_id)
        if not template:
            return False
        
        slot = ComponentSlot(
            slot_id=slot_id,
            slot_type=slot_type,
            display_name=display_name,
            description=description,
            required=required,
            constraints=constraints or LayoutConstraint()
        )
        
        template.component_slots.append(slot)
        template.modified = datetime.now(timezone.utc)
        self._save_template(template)
        
        return True
    
    def remove_component_slot(self, template_id: str, slot_id: str) -> bool:
        """Remove a component slot from a template."""
        template = self._templates.get(template_id)
        if not template:
            return False
        
        template.component_slots = [
            slot for slot in template.component_slots
            if slot.slot_id != slot_id
        ]
        
        template.modified = datetime.now(timezone.utc)
        self._save_template(template)
        
        return True
    
    def instantiate_template(
        self,
        template_id: str,
        component_assignments: Dict[str, QWidget],
        layout_name: str
    ) -> QWidget:
        """Instantiate a template with specific component assignments."""
        template = self._templates.get(template_id)
        if not template:
            raise LayoutError(f"Template '{template_id}' not found")
        
        # Validate component assignments
        self._validate_component_assignments(template, component_assignments)
        
        # Create layout structure
        root_widget = self._create_layout_from_template(template, component_assignments)
        
        # Update template usage
        template.usage_count += 1
        template.modified = datetime.now(timezone.utc)
        self._save_template(template)
        
        logger.info(f"Instantiated template '{template_id}' as layout '{layout_name}'")
        return root_widget
    
    def generate_preview(self, template_id: str) -> Optional[QPixmap]:
        """Generate a preview image for a template."""
        template = self._templates.get(template_id)
        if not template:
            return None
        
        # Create a simplified preview widget
        preview_widget = self._create_preview_widget(template)
        
        # Render to pixmap
        preview_size = QSize(300, 200)
        pixmap = QPixmap(preview_size)
        pixmap.fill(Qt.GlobalColor.white)
        
        painter = QPainter(pixmap)
        preview_widget.render(painter)
        painter.end()
        
        return pixmap
    
    def _load_builtin_templates(self) -> None:
        """Load built-in layout templates."""
        # Document Layout Template
        doc_template = LayoutTemplate(
            template_id="document_layout",
            name="Document Layout",
            description="Standard document viewing layout with properties panel",
            category=TemplateCategory.DOCUMENT,
            author="ToreMatrix",
            root_layout_type=LayoutType.SPLITTER
        )
        
        doc_template.component_slots.extend([
            ComponentSlot(
                slot_id="main_document",
                slot_type="document_viewer",
                display_name="Document Viewer",
                description="Main document viewing area",
                required=True,
                constraints=LayoutConstraint(min_width=400, min_height=300)
            ),
            ComponentSlot(
                slot_id="properties_panel",
                slot_type="properties_panel",
                display_name="Properties Panel",
                description="Document properties and metadata",
                constraints=LayoutConstraint(min_width=200, max_width=400)
            ),
            ComponentSlot(
                slot_id="corrections_panel",
                slot_type="corrections_panel",
                display_name="Corrections Panel",
                description="Document corrections and validation",
                constraints=LayoutConstraint(min_width=200, max_width=400)
            )
        ])
        
        doc_template.layout_properties = {
            "orientation": Qt.Orientation.Horizontal.value,
            "sizes": [800, 200, 200],
            "handle_width": 5
        }
        
        self._templates[doc_template.template_id] = doc_template
        
        # Split Layout Template
        split_template = LayoutTemplate(
            template_id="split_layout",
            name="Split Layout",
            description="Simple two-panel split layout",
            category=TemplateCategory.ANALYSIS,
            author="ToreMatrix",
            root_layout_type=LayoutType.SPLITTER
        )
        
        split_template.component_slots.extend([
            ComponentSlot(
                slot_id="primary_panel",
                slot_type="content_panel",
                display_name="Primary Panel",
                description="Primary content area",
                required=True
            ),
            ComponentSlot(
                slot_id="secondary_panel",
                slot_type="content_panel",
                display_name="Secondary Panel",
                description="Secondary content area",
                required=True
            )
        ])
        
        split_template.layout_properties = {
            "orientation": Qt.Orientation.Horizontal.value,
            "sizes": [600, 400],
            "handle_width": 3
        }
        
        self._templates[split_template.template_id] = split_template
        
        # Tabbed Layout Template
        tab_template = LayoutTemplate(
            template_id="tabbed_layout",
            name="Tabbed Layout",
            description="Multi-tab interface layout",
            category=TemplateCategory.WORKFLOW,
            author="ToreMatrix",
            root_layout_type=LayoutType.TAB_WIDGET
        )
        
        tab_template.component_slots.extend([
            ComponentSlot(
                slot_id="tab_content",
                slot_type="tab_content",
                display_name="Tab Content",
                description="Content for tabs",
                required=True,
                multiple=True
            )
        ])
        
        tab_template.layout_properties = {
            "tab_position": 0,  # North
            "tabs_closable": True,
            "tabs_movable": True
        }
        
        self._templates[tab_template.template_id] = tab_template
        
        logger.info("Loaded built-in layout templates")
    
    def _load_user_templates(self) -> None:
        """Load user-created templates from storage."""
        for template_file in self._template_path.glob("*.json"):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                template = self._deserialize_template(data)
                self._templates[template.template_id] = template
                
            except Exception as e:
                logger.warning(f"Failed to load template {template_file}: {e}")
        
        logger.info(f"Loaded {len(self._templates)} user templates")
    
    def _save_template(self, template: LayoutTemplate) -> None:
        """Save template to storage."""
        template_file = self._template_path / f"{template.template_id}.json"
        
        try:
            data = self._serialize_template(template)
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to save template {template.template_id}: {e}")
    
    def _serialize_template(self, template: LayoutTemplate) -> Dict[str, Any]:
        """Serialize template to dictionary."""
        return {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "category": template.category.value,
            "author": template.author,
            "version": template.version,
            "created": template.created.isoformat(),
            "modified": template.modified.isoformat(),
            "root_layout_type": template.root_layout_type.value,
            "component_slots": [
                {
                    "slot_id": slot.slot_id,
                    "slot_type": slot.slot_type,
                    "display_name": slot.display_name,
                    "description": slot.description,
                    "required": slot.required,
                    "multiple": slot.multiple,
                    "default_component": slot.default_component,
                    "allowed_components": slot.allowed_components,
                    "constraints": {
                        "min_width": slot.constraints.min_width,
                        "max_width": slot.constraints.max_width,
                        "min_height": slot.constraints.min_height,
                        "max_height": slot.constraints.max_height,
                        "aspect_ratio": slot.constraints.aspect_ratio,
                        "fixed_size": slot.constraints.fixed_size,
                        "resizable": slot.constraints.resizable
                    }
                }
                for slot in template.component_slots
            ],
            "layout_properties": template.layout_properties,
            "global_constraints": {
                "min_width": template.global_constraints.min_width,
                "max_width": template.global_constraints.max_width,
                "min_height": template.global_constraints.min_height,
                "max_height": template.global_constraints.max_height,
                "aspect_ratio": template.global_constraints.aspect_ratio,
                "fixed_size": template.global_constraints.fixed_size,
                "resizable": template.global_constraints.resizable
            },
            "tags": template.tags,
            "preview_image": template.preview_image,
            "usage_count": template.usage_count,
            "rating": template.rating,
            "derived_from": template.derived_from,
            "derivation_notes": template.derivation_notes
        }
    
    def _deserialize_template(self, data: Dict[str, Any]) -> LayoutTemplate:
        """Deserialize template from dictionary."""
        # Parse datetime fields
        created = datetime.fromisoformat(data.get("created", datetime.now(timezone.utc).isoformat()))
        modified = datetime.fromisoformat(data.get("modified", datetime.now(timezone.utc).isoformat()))
        
        # Parse component slots
        component_slots = []
        for slot_data in data.get("component_slots", []):
            constraints_data = slot_data.get("constraints", {})
            constraints = LayoutConstraint(
                min_width=constraints_data.get("min_width"),
                max_width=constraints_data.get("max_width"),
                min_height=constraints_data.get("min_height"),
                max_height=constraints_data.get("max_height"),
                aspect_ratio=constraints_data.get("aspect_ratio"),
                fixed_size=constraints_data.get("fixed_size", False),
                resizable=constraints_data.get("resizable", True)
            )
            
            slot = ComponentSlot(
                slot_id=slot_data["slot_id"],
                slot_type=slot_data["slot_type"],
                display_name=slot_data["display_name"],
                description=slot_data.get("description", ""),
                required=slot_data.get("required", False),
                multiple=slot_data.get("multiple", False),
                constraints=constraints,
                default_component=slot_data.get("default_component"),
                allowed_components=slot_data.get("allowed_components", [])
            )
            component_slots.append(slot)
        
        # Parse global constraints
        global_constraints_data = data.get("global_constraints", {})
        global_constraints = LayoutConstraint(
            min_width=global_constraints_data.get("min_width"),
            max_width=global_constraints_data.get("max_width"),
            min_height=global_constraints_data.get("min_height"),
            max_height=global_constraints_data.get("max_height"),
            aspect_ratio=global_constraints_data.get("aspect_ratio"),
            fixed_size=global_constraints_data.get("fixed_size", False),
            resizable=global_constraints_data.get("resizable", True)
        )
        
        return LayoutTemplate(
            template_id=data["template_id"],
            name=data["name"],
            description=data["description"],
            category=TemplateCategory(data["category"]),
            author=data.get("author", ""),
            version=data.get("version", "1.0.0"),
            created=created,
            modified=modified,
            root_layout_type=LayoutType(data["root_layout_type"]),
            component_slots=component_slots,
            layout_properties=data.get("layout_properties", {}),
            global_constraints=global_constraints,
            tags=data.get("tags", []),
            preview_image=data.get("preview_image"),
            usage_count=data.get("usage_count", 0),
            rating=data.get("rating", 0.0),
            derived_from=data.get("derived_from"),
            derivation_notes=data.get("derivation_notes", "")
        )
    
    def _apply_template_modifications(
        self,
        template: LayoutTemplate,
        modifications: Dict[str, Any]
    ) -> None:
        """Apply modifications to a derived template."""
        if "name" in modifications:
            template.name = modifications["name"]
        if "description" in modifications:
            template.description = modifications["description"]
        if "category" in modifications:
            template.category = TemplateCategory(modifications["category"])
        if "tags" in modifications:
            template.tags = modifications["tags"]
        if "layout_properties" in modifications:
            template.layout_properties.update(modifications["layout_properties"])
        if "derivation_notes" in modifications:
            template.derivation_notes = modifications["derivation_notes"]
    
    def _validate_component_assignments(
        self,
        template: LayoutTemplate,
        assignments: Dict[str, QWidget]
    ) -> None:
        """Validate component assignments against template requirements."""
        required_slots = {
            slot.slot_id for slot in template.component_slots
            if slot.required
        }
        
        provided_slots = set(assignments.keys())
        
        missing_slots = required_slots - provided_slots
        if missing_slots:
            raise LayoutError(f"Missing required component slots: {missing_slots}")
        
        # Validate individual components
        for slot in template.component_slots:
            if slot.slot_id in assignments:
                widget = assignments[slot.slot_id]
                self._validate_component_constraints(widget, slot.constraints)
    
    def _validate_component_constraints(
        self,
        widget: QWidget,
        constraints: LayoutConstraint
    ) -> None:
        """Validate widget against constraints."""
        size = widget.size()
        
        if constraints.min_width and size.width() < constraints.min_width:
            widget.setMinimumWidth(constraints.min_width)
        
        if constraints.max_width and size.width() > constraints.max_width:
            widget.setMaximumWidth(constraints.max_width)
        
        if constraints.min_height and size.height() < constraints.min_height:
            widget.setMinimumHeight(constraints.min_height)
        
        if constraints.max_height and size.height() > constraints.max_height:
            widget.setMaximumHeight(constraints.max_height)
        
        if constraints.fixed_size:
            widget.setFixedSize(size)
        
        if not constraints.resizable:
            widget.setSizePolicy(widget.sizePolicy().Fixed, widget.sizePolicy().Fixed)
    
    def _create_layout_from_template(
        self,
        template: LayoutTemplate,
        assignments: Dict[str, QWidget]
    ) -> QWidget:
        """Create actual layout from template and component assignments."""
        if template.root_layout_type == LayoutType.SPLITTER:
            return self._create_splitter_layout(template, assignments)
        elif template.root_layout_type == LayoutType.TAB_WIDGET:
            return self._create_tab_layout(template, assignments)
        elif template.root_layout_type == LayoutType.VBOX_LAYOUT:
            return self._create_vbox_layout(template, assignments)
        elif template.root_layout_type == LayoutType.HBOX_LAYOUT:
            return self._create_hbox_layout(template, assignments)
        elif template.root_layout_type == LayoutType.GRID_LAYOUT:
            return self._create_grid_layout(template, assignments)
        else:
            raise LayoutError(f"Unsupported template layout type: {template.root_layout_type}")
    
    def _create_splitter_layout(
        self,
        template: LayoutTemplate,
        assignments: Dict[str, QWidget]
    ) -> QSplitter:
        """Create splitter layout from template."""
        splitter = QSplitter()
        
        # Apply properties
        props = template.layout_properties
        if "orientation" in props:
            splitter.setOrientation(props["orientation"])
        if "handle_width" in props:
            splitter.setHandleWidth(props["handle_width"])
        
        # Add components in order
        for slot in template.component_slots:
            if slot.slot_id in assignments:
                widget = assignments[slot.slot_id]
                splitter.addWidget(widget)
        
        # Set sizes if specified
        if "sizes" in props:
            splitter.setSizes(props["sizes"])
        
        return splitter
    
    def _create_tab_layout(
        self,
        template: LayoutTemplate,
        assignments: Dict[str, QWidget]
    ) -> QTabWidget:
        """Create tab widget layout from template."""
        tab_widget = QTabWidget()
        
        # Apply properties
        props = template.layout_properties
        if "tab_position" in props:
            tab_widget.setTabPosition(props["tab_position"])
        if "tabs_closable" in props:
            tab_widget.setTabsClosable(props["tabs_closable"])
        if "tabs_movable" in props:
            tab_widget.setTabsMovable(props["tabs_movable"])
        
        # Add tabs
        for slot in template.component_slots:
            if slot.slot_id in assignments:
                widget = assignments[slot.slot_id]
                tab_widget.addTab(widget, slot.display_name)
        
        return tab_widget
    
    def _create_vbox_layout(
        self,
        template: LayoutTemplate,
        assignments: Dict[str, QWidget]
    ) -> QWidget:
        """Create vertical box layout from template."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Apply properties
        props = template.layout_properties
        if "spacing" in props:
            layout.setSpacing(props["spacing"])
        if "margins" in props:
            margins = props["margins"]
            layout.setContentsMargins(
                margins.get("left", 0),
                margins.get("top", 0),
                margins.get("right", 0),
                margins.get("bottom", 0)
            )
        
        # Add components
        for slot in template.component_slots:
            if slot.slot_id in assignments:
                widget = assignments[slot.slot_id]
                layout.addWidget(widget)
        
        return container
    
    def _create_hbox_layout(
        self,
        template: LayoutTemplate,
        assignments: Dict[str, QWidget]
    ) -> QWidget:
        """Create horizontal box layout from template."""
        container = QWidget()
        layout = QHBoxLayout(container)
        
        # Apply properties
        props = template.layout_properties
        if "spacing" in props:
            layout.setSpacing(props["spacing"])
        if "margins" in props:
            margins = props["margins"]
            layout.setContentsMargins(
                margins.get("left", 0),
                margins.get("top", 0),
                margins.get("right", 0),
                margins.get("bottom", 0)
            )
        
        # Add components
        for slot in template.component_slots:
            if slot.slot_id in assignments:
                widget = assignments[slot.slot_id]
                layout.addWidget(widget)
        
        return container
    
    def _create_grid_layout(
        self,
        template: LayoutTemplate,
        assignments: Dict[str, QWidget]
    ) -> QWidget:
        """Create grid layout from template."""
        container = QWidget()
        layout = QGridLayout(container)
        
        # Apply properties
        props = template.layout_properties
        if "horizontal_spacing" in props:
            layout.setHorizontalSpacing(props["horizontal_spacing"])
        if "vertical_spacing" in props:
            layout.setVerticalSpacing(props["vertical_spacing"])
        
        # Add components (requires grid positions in slot properties)
        for slot in template.component_slots:
            if slot.slot_id in assignments:
                widget = assignments[slot.slot_id]
                
                # Get grid position from slot (should be in constraints or properties)
                row = 0
                col = 0
                row_span = 1
                col_span = 1
                
                # You would extend this to read grid positions from template
                layout.addWidget(widget, row, col, row_span, col_span)
        
        return container
    
    def _create_preview_widget(self, template: LayoutTemplate) -> QWidget:
        """Create a preview widget for template visualization."""
        # Create a simplified version of the template for preview
        preview = QWidget()
        preview.setFixedSize(300, 200)
        
        # Create mock components for preview
        mock_assignments = {}
        for slot in template.component_slots:
            mock_widget = QLabel(slot.display_name)
            mock_widget.setStyleSheet("border: 1px solid gray; padding: 10px;")
            mock_assignments[slot.slot_id] = mock_widget
        
        # Create layout
        if mock_assignments:
            layout_widget = self._create_layout_from_template(template, mock_assignments)
            
            # Embed in preview widget
            container_layout = QVBoxLayout(preview)
            container_layout.addWidget(layout_widget)
        
        return preview


class CustomLayoutManager(BaseUIComponent):
    """Main manager for custom layout operations."""
    
    # Signals
    template_created = pyqtSignal(str)  # template_id
    template_applied = pyqtSignal(str, str)  # template_id, layout_name
    layout_customized = pyqtSignal(str)  # layout_name
    
    def __init__(
        self,
        event_bus: EventBus,
        config_manager: ConfigManager,
        state_manager: StateManager,
        persistence: LayoutPersistence,
        parent: Optional[QObject] = None
    ):
        super().__init__(event_bus, config_manager, state_manager, parent)
        
        self._persistence = persistence
        self._template_manager = LayoutTemplateManager(persistence)
        
        # Component registry for templates
        self._available_components: Dict[str, Callable[[], QWidget]] = {}
    
    def _setup_component(self) -> None:
        """Setup the custom layout manager."""
        # Subscribe to events
        self.subscribe_event("component.registered", self._on_component_registered)
        
        logger.info("Custom layout manager initialized")
    
    def register_component_factory(
        self,
        component_id: str,
        factory: Callable[[], QWidget],
        display_name: str = None
    ) -> None:
        """Register a component factory for layout creation."""
        self._available_components[component_id] = factory
        self._template_manager.register_component_type(component_id, QWidget)
        
        logger.debug(f"Registered component factory: {component_id}")
    
    def create_custom_layout(
        self,
        template_id: str,
        layout_name: str,
        component_assignments: Dict[str, str],
        save_layout: bool = True
    ) -> QWidget:
        """Create a custom layout from a template."""
        try:
            # Get template
            template = self._template_manager.get_template(template_id)
            if not template:
                raise LayoutError(f"Template '{template_id}' not found")
            
            # Create component instances
            widget_assignments = {}
            for slot_id, component_id in component_assignments.items():
                if component_id in self._available_components:
                    factory = self._available_components[component_id]
                    widget = factory()
                    widget_assignments[slot_id] = widget
                else:
                    logger.warning(f"Component '{component_id}' not available, skipping slot '{slot_id}'")
            
            # Instantiate template
            layout_widget = self._template_manager.instantiate_template(
                template_id,
                widget_assignments,
                layout_name
            )
            
            # Save layout if requested
            if save_layout:
                self._persistence.save_layout(
                    layout_name,
                    layout_widget,
                    description=f"Custom layout from template '{template.name}'",
                    storage_type=LayoutStorageType.CUSTOM
                )
            
            # Emit signals
            self.template_applied.emit(template_id, layout_name)
            
            # Publish event
            self.publish_event("layout.custom_created", {
                "template_id": template_id,
                "layout_name": layout_name,
                "component_count": len(widget_assignments)
            })
            
            logger.info(f"Created custom layout '{layout_name}' from template '{template_id}'")
            return layout_widget
            
        except Exception as e:
            logger.error(f"Failed to create custom layout: {e}")
            raise LayoutError(f"Custom layout creation failed: {e}") from e
    
    def customize_existing_layout(
        self,
        source_layout_name: str,
        new_layout_name: str,
        modifications: Dict[str, Any]
    ) -> bool:
        """Customize an existing layout with modifications."""
        try:
            # Load existing layout
            existing_widget = self._persistence.load_layout(source_layout_name)
            
            # Apply modifications (this would be more complex in practice)
            # For now, just save with new name and description
            modified_description = modifications.get(
                "description",
                f"Customized version of '{source_layout_name}'"
            )
            
            # Save as new layout
            self._persistence.save_layout(
                new_layout_name,
                existing_widget,
                description=modified_description,
                storage_type=LayoutStorageType.CUSTOM
            )
            
            # Emit signal
            self.layout_customized.emit(new_layout_name)
            
            logger.info(f"Customized layout '{source_layout_name}' as '{new_layout_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to customize layout: {e}")
            return False
    
    def get_available_templates(
        self,
        category: Optional[TemplateCategory] = None
    ) -> List[LayoutTemplate]:
        """Get available layout templates."""
        return self._template_manager.list_templates(category)
    
    def get_available_components(self) -> Dict[str, str]:
        """Get available components for layout creation."""
        return {
            comp_id: comp_id.replace("_", " ").title()
            for comp_id in self._available_components.keys()
        }
    
    def create_template_from_layout(
        self,
        layout_name: str,
        template_id: str,
        template_name: str,
        description: str,
        category: TemplateCategory = TemplateCategory.CUSTOM
    ) -> bool:
        """Create a template from an existing layout."""
        try:
            # This would analyze an existing layout and create a template
            # For now, create a basic template
            template = self._template_manager.create_template(
                template_id,
                template_name,
                description,
                category
            )
            
            # Emit signal
            self.template_created.emit(template_id)
            
            logger.info(f"Created template '{template_id}' from layout '{layout_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create template from layout: {e}")
            return False
    
    def _on_component_registered(self, event_data: Dict[str, Any]) -> None:
        """Handle component registration events."""
        component_id = event_data.get("component_id")
        factory = event_data.get("factory")
        
        if component_id and factory:
            self.register_component_factory(component_id, factory)