"""Layout validation rules and constraints for ToreMatrix Layout Management System.

This module provides comprehensive validation for layout configurations,
ensuring consistency, performance, and reliability of the layout system.
"""

from typing import Dict, List, Optional, Any, Set, Tuple, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import logging

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QSize

from .base import (
    LayoutConfiguration, LayoutItem, LayoutType, LayoutGeometry,
    LayoutProvider
)

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Validation message severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationMessage:
    """A validation message with details."""
    severity: ValidationSeverity
    code: str
    message: str
    item_id: Optional[str] = None
    suggestion: Optional[str] = None
    auto_fix: Optional[Callable[[], bool]] = None


@dataclass
class ValidationResult:
    """Result of layout validation."""
    is_valid: bool
    messages: List[ValidationMessage]
    warnings_count: int = 0
    errors_count: int = 0
    
    def __post_init__(self):
        """Calculate message counts."""
        self.warnings_count = sum(1 for msg in self.messages if msg.severity == ValidationSeverity.WARNING)
        self.errors_count = sum(1 for msg in self.messages if msg.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL])
        
        # Update validity based on errors
        if self.errors_count > 0:
            self.is_valid = False


class ValidationRule(ABC):
    """Base class for layout validation rules."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.enabled = True
    
    @abstractmethod
    def validate(self, config: LayoutConfiguration) -> List[ValidationMessage]:
        """Validate a layout configuration."""
        pass
    
    def is_applicable(self, config: LayoutConfiguration) -> bool:
        """Check if this rule applies to the given configuration."""
        return True


class LayoutNameRule(ValidationRule):
    """Validates layout name requirements."""
    
    def __init__(self):
        super().__init__(
            "Layout Name",
            "Validates that layout has a proper name"
        )
    
    def validate(self, config: LayoutConfiguration) -> List[ValidationMessage]:
        """Validate layout name."""
        messages = []
        
        if not config.name:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="LAYOUT_NO_NAME",
                message="Layout must have a name",
                suggestion="Provide a descriptive name for the layout"
            ))
        elif len(config.name.strip()) < 2:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                code="LAYOUT_SHORT_NAME",
                message="Layout name is very short",
                suggestion="Use a more descriptive name (at least 2 characters)"
            ))
        elif len(config.name) > 100:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                code="LAYOUT_LONG_NAME",
                message="Layout name is very long",
                suggestion="Use a shorter, more concise name (under 100 characters)"
            ))
        
        # Check for invalid characters
        invalid_chars = set('<>:"/\\|?*')
        if any(char in config.name for char in invalid_chars):
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="LAYOUT_INVALID_NAME_CHARS",
                message="Layout name contains invalid characters",
                suggestion=f"Remove these characters: {invalid_chars & set(config.name)}"
            ))
        
        return messages


class LayoutGeometryRule(ValidationRule):
    """Validates layout geometry constraints."""
    
    def __init__(self, min_width: int = 320, min_height: int = 240, max_width: int = 7680, max_height: int = 4320):
        super().__init__(
            "Layout Geometry",
            "Validates layout size and position constraints"
        )
        self.min_width = min_width
        self.min_height = min_height
        self.max_width = max_width
        self.max_height = max_height
    
    def validate(self, config: LayoutConfiguration) -> List[ValidationMessage]:
        """Validate layout geometry."""
        messages = []
        geometry = config.geometry
        
        # Validate dimensions
        if geometry.width < self.min_width:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="LAYOUT_WIDTH_TOO_SMALL",
                message=f"Layout width ({geometry.width}) is below minimum ({self.min_width})",
                suggestion=f"Increase width to at least {self.min_width} pixels"
            ))
        
        if geometry.height < self.min_height:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="LAYOUT_HEIGHT_TOO_SMALL",
                message=f"Layout height ({geometry.height}) is below minimum ({self.min_height})",
                suggestion=f"Increase height to at least {self.min_height} pixels"
            ))
        
        if geometry.width > self.max_width:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                code="LAYOUT_WIDTH_TOO_LARGE",
                message=f"Layout width ({geometry.width}) exceeds recommended maximum ({self.max_width})",
                suggestion=f"Consider reducing width to under {self.max_width} pixels for better performance"
            ))
        
        if geometry.height > self.max_height:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                code="LAYOUT_HEIGHT_TOO_LARGE",
                message=f"Layout height ({geometry.height}) exceeds recommended maximum ({self.max_height})",
                suggestion=f"Consider reducing height to under {self.max_height} pixels for better performance"
            ))
        
        # Validate position
        if geometry.x < -1000 or geometry.y < -1000:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                code="LAYOUT_POSITION_NEGATIVE",
                message="Layout position is very negative",
                suggestion="Ensure layout is positioned within visible screen area"
            ))
        
        return messages


class LayoutItemsRule(ValidationRule):
    """Validates layout items and their constraints."""
    
    def __init__(self, max_items: int = 50):
        super().__init__(
            "Layout Items",
            "Validates layout items and their configuration"
        )
        self.max_items = max_items
    
    def validate(self, config: LayoutConfiguration) -> List[ValidationMessage]:
        """Validate layout items."""
        messages = []
        
        # Check item count
        if len(config.items) > self.max_items:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                code="LAYOUT_TOO_MANY_ITEMS",
                message=f"Layout has {len(config.items)} items (recommended maximum: {self.max_items})",
                suggestion="Consider grouping items or using multiple layouts for better performance"
            ))
        
        # Validate individual items
        item_ids = set()
        item_names = set()
        
        for item in config.items:
            # Check for duplicate IDs
            if item.id in item_ids:
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    code="LAYOUT_DUPLICATE_ITEM_ID",
                    message=f"Duplicate item ID: {item.id}",
                    item_id=item.id,
                    suggestion="Ensure all item IDs are unique"
                ))
            item_ids.add(item.id)
            
            # Check for duplicate names (warning only)
            if item.name in item_names:
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    code="LAYOUT_DUPLICATE_ITEM_NAME",
                    message=f"Duplicate item name: {item.name}",
                    item_id=item.id,
                    suggestion="Consider using unique names for better identification"
                ))
            item_names.add(item.name)
            
            # Validate item properties
            messages.extend(self._validate_item(item))
        
        return messages
    
    def _validate_item(self, item: LayoutItem) -> List[ValidationMessage]:
        """Validate a single layout item."""
        messages = []
        
        # Check widget existence
        if not item.widget:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="LAYOUT_ITEM_NO_WIDGET",
                message=f"Item {item.id} has no widget",
                item_id=item.id,
                suggestion="Ensure all layout items have valid widgets"
            ))
        
        # Check name
        if not item.name:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                code="LAYOUT_ITEM_NO_NAME",
                message=f"Item {item.id} has no name",
                item_id=item.id,
                suggestion="Provide descriptive names for layout items"
            ))
        
        # Check stretch factor
        if item.stretch_factor < 0:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="LAYOUT_ITEM_INVALID_STRETCH",
                message=f"Item {item.id} has negative stretch factor ({item.stretch_factor})",
                item_id=item.id,
                suggestion="Use non-negative stretch factors"
            ))
        elif item.stretch_factor > 1000:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                code="LAYOUT_ITEM_HIGH_STRETCH",
                message=f"Item {item.id} has very high stretch factor ({item.stretch_factor})",
                item_id=item.id,
                suggestion="Consider using more reasonable stretch factors (0-10)"
            ))
        
        # Check size constraints
        if item.minimum_size and item.maximum_size:
            if item.minimum_size.width() > item.maximum_size.width():
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    code="LAYOUT_ITEM_SIZE_CONFLICT",
                    message=f"Item {item.id} minimum width exceeds maximum width",
                    item_id=item.id,
                    suggestion="Ensure minimum size is not larger than maximum size"
                ))
            
            if item.minimum_size.height() > item.maximum_size.height():
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    code="LAYOUT_ITEM_SIZE_CONFLICT",
                    message=f"Item {item.id} minimum height exceeds maximum height",
                    item_id=item.id,
                    suggestion="Ensure minimum size is not larger than maximum size"
                ))
        
        return messages


class LayoutTypeSpecificRule(ValidationRule):
    """Validates layout-type-specific constraints."""
    
    def __init__(self):
        super().__init__(
            "Layout Type Specific",
            "Validates constraints specific to layout types"
        )
    
    def validate(self, config: LayoutConfiguration) -> List[ValidationMessage]:
        """Validate layout-type-specific constraints."""
        messages = []
        
        layout_type = config.layout_type
        
        if layout_type == LayoutType.DOCUMENT:
            messages.extend(self._validate_document_layout(config))
        elif layout_type in [LayoutType.SPLIT_HORIZONTAL, LayoutType.SPLIT_VERTICAL]:
            messages.extend(self._validate_split_layout(config))
        elif layout_type == LayoutType.TABBED:
            messages.extend(self._validate_tabbed_layout(config))
        elif layout_type == LayoutType.MULTI_PANEL:
            messages.extend(self._validate_multi_panel_layout(config))
        
        return messages
    
    def _validate_document_layout(self, config: LayoutConfiguration) -> List[ValidationMessage]:
        """Validate document layout specific constraints."""
        messages = []
        
        # Check for required areas
        area_types = set()
        for item in config.items:
            area_type = item.properties.get("area_type", "document")
            area_types.add(area_type)
        
        # Document layout should have at least a document area
        if "document" not in area_types and config.items:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                code="DOCUMENT_LAYOUT_NO_DOCUMENT_AREA",
                message="Document layout has no document area",
                suggestion="Add at least one item with area_type='document'"
            ))
        
        return messages
    
    def _validate_split_layout(self, config: LayoutConfiguration) -> List[ValidationMessage]:
        """Validate split layout specific constraints."""
        messages = []
        
        # Check area distribution
        primary_items = 0
        secondary_items = 0
        
        for item in config.items:
            area_type = item.properties.get("area_type", "primary")
            if area_type == "primary":
                primary_items += 1
            elif area_type == "secondary":
                secondary_items += 1
        
        if primary_items == 0 and config.items:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                code="SPLIT_LAYOUT_NO_PRIMARY",
                message="Split layout has no primary area items",
                suggestion="Add items with area_type='primary'"
            ))
        
        return messages
    
    def _validate_tabbed_layout(self, config: LayoutConfiguration) -> List[ValidationMessage]:
        """Validate tabbed layout specific constraints."""
        messages = []
        
        # Check tab distribution
        tabs = set()
        for item in config.items:
            tab_name = item.properties.get("tab_name", "Main")
            tabs.add(tab_name)
        
        if len(tabs) > 20:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                code="TABBED_LAYOUT_TOO_MANY_TABS",
                message=f"Tabbed layout has {len(tabs)} tabs (recommended maximum: 20)",
                suggestion="Consider grouping tabs or using multiple layouts"
            ))
        
        return messages
    
    def _validate_multi_panel_layout(self, config: LayoutConfiguration) -> List[ValidationMessage]:
        """Validate multi-panel layout specific constraints."""
        messages = []
        
        # Check panel structure
        panel_structure = config.properties.get("panel_structure")
        if panel_structure:
            messages.extend(self._validate_panel_structure(panel_structure))
        
        return messages
    
    def _validate_panel_structure(self, structure: Dict[str, Any], depth: int = 0) -> List[ValidationMessage]:
        """Validate panel structure recursively."""
        messages = []
        
        if depth > 5:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                code="MULTI_PANEL_TOO_DEEP",
                message=f"Panel structure is very deep (depth: {depth})",
                suggestion="Consider flattening the panel structure for better performance"
            ))
        
        structure_type = structure.get("type")
        if structure_type in ["horizontal_split", "vertical_split"]:
            panels = structure.get("panels", [])
            if len(panels) > 10:
                messages.append(ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    code="MULTI_PANEL_TOO_MANY_CHILDREN",
                    message=f"Splitter has {len(panels)} children (recommended maximum: 10)",
                    suggestion="Consider grouping panels for better organization"
                ))
            
            # Validate child panels
            for panel in panels:
                messages.extend(self._validate_panel_structure(panel, depth + 1))
        
        return messages


class LayoutPerformanceRule(ValidationRule):
    """Validates layout performance considerations."""
    
    def __init__(self):
        super().__init__(
            "Layout Performance",
            "Validates performance-related layout constraints"
        )
    
    def validate(self, config: LayoutConfiguration) -> List[ValidationMessage]:
        """Validate layout performance considerations."""
        messages = []
        
        # Check total widget count
        total_widgets = len(config.items)
        if total_widgets > 100:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                code="LAYOUT_PERFORMANCE_MANY_WIDGETS",
                message=f"Layout has {total_widgets} widgets (may impact performance)",
                suggestion="Consider lazy loading or virtualization for large numbers of widgets"
            ))
        
        # Check nested complexity
        nested_depth = self._calculate_nesting_depth(config)
        if nested_depth > 8:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                code="LAYOUT_PERFORMANCE_DEEP_NESTING",
                message=f"Layout has deep nesting (depth: {nested_depth})",
                suggestion="Consider flattening the layout structure for better performance"
            ))
        
        # Check memory usage potential
        heavy_widgets = 0
        for item in config.items:
            widget_type = type(item.widget).__name__ if item.widget else "Unknown"
            if any(heavy_type in widget_type for heavy_type in ["WebView", "OpenGL", "Canvas", "Chart"]):
                heavy_widgets += 1
        
        if heavy_widgets > 5:
            messages.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                code="LAYOUT_PERFORMANCE_HEAVY_WIDGETS",
                message=f"Layout has {heavy_widgets} potentially heavy widgets",
                suggestion="Consider lazy loading or reducing the number of heavy widgets"
            ))
        
        return messages
    
    def _calculate_nesting_depth(self, config: LayoutConfiguration) -> int:
        """Calculate maximum nesting depth of layout structure."""
        if config.layout_type == LayoutType.MULTI_PANEL:
            panel_structure = config.properties.get("panel_structure")
            if panel_structure:
                return self._calculate_structure_depth(panel_structure)
        
        # For other layouts, depth is relatively simple
        return 2 if config.items else 1
    
    def _calculate_structure_depth(self, structure: Dict[str, Any], current_depth: int = 1) -> int:
        """Calculate structure depth recursively."""
        structure_type = structure.get("type")
        if structure_type in ["horizontal_split", "vertical_split"]:
            panels = structure.get("panels", [])
            max_child_depth = current_depth
            for panel in panels:
                child_depth = self._calculate_structure_depth(panel, current_depth + 1)
                max_child_depth = max(max_child_depth, child_depth)
            return max_child_depth
        else:
            return current_depth


class LayoutValidator:
    """Main layout validator that coordinates all validation rules."""
    
    def __init__(self):
        self._rules: List[ValidationRule] = []
        self._setup_default_rules()
    
    def _setup_default_rules(self) -> None:
        """Setup default validation rules."""
        self._rules = [
            LayoutNameRule(),
            LayoutGeometryRule(),
            LayoutItemsRule(),
            LayoutTypeSpecificRule(),
            LayoutPerformanceRule(),
        ]
    
    def add_rule(self, rule: ValidationRule) -> None:
        """Add a custom validation rule."""
        self._rules.append(rule)
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove a validation rule by name."""
        for i, rule in enumerate(self._rules):
            if rule.name == rule_name:
                del self._rules[i]
                return True
        return False
    
    def get_rules(self) -> List[ValidationRule]:
        """Get all validation rules."""
        return self._rules.copy()
    
    def validate(self, config: LayoutConfiguration) -> ValidationResult:
        """Validate a layout configuration."""
        all_messages = []
        
        try:
            # Run all applicable rules
            for rule in self._rules:
                if rule.enabled and rule.is_applicable(config):
                    try:
                        messages = rule.validate(config)
                        all_messages.extend(messages)
                    except Exception as e:
                        logger.error(f"Error in validation rule {rule.name}: {e}")
                        all_messages.append(ValidationMessage(
                            severity=ValidationSeverity.ERROR,
                            code="VALIDATION_RULE_ERROR",
                            message=f"Validation rule '{rule.name}' failed: {e}",
                            suggestion="Check validation rule implementation"
                        ))
            
            # Create result
            result = ValidationResult(
                is_valid=True,  # Will be updated in __post_init__
                messages=all_messages
            )
            
            logger.debug(f"Layout validation completed: {len(all_messages)} messages, valid: {result.is_valid}")
            return result
            
        except Exception as e:
            logger.error(f"Layout validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                messages=[ValidationMessage(
                    severity=ValidationSeverity.CRITICAL,
                    code="VALIDATION_FAILED",
                    message=f"Layout validation failed: {e}",
                    suggestion="Check layout configuration and validation system"
                )]
            )
    
    def validate_quick(self, config: LayoutConfiguration) -> bool:
        """Quick validation that returns only boolean result."""
        result = self.validate(config)
        return result.is_valid
    
    def auto_fix(self, config: LayoutConfiguration) -> Tuple[LayoutConfiguration, List[ValidationMessage]]:
        """Attempt to automatically fix validation issues."""
        fixed_config = config
        fix_messages = []
        
        # Run validation first
        result = self.validate(config)
        
        # Apply auto-fixes where available
        for message in result.messages:
            if message.auto_fix:
                try:
                    if message.auto_fix():
                        fix_messages.append(ValidationMessage(
                            severity=ValidationSeverity.INFO,
                            code="AUTO_FIX_APPLIED",
                            message=f"Auto-fixed: {message.message}",
                            item_id=message.item_id
                        ))
                except Exception as e:
                    logger.warning(f"Auto-fix failed for {message.code}: {e}")
        
        return fixed_config, fix_messages


# Global validator instance
_validator = LayoutValidator()


def validate_layout(config: LayoutConfiguration) -> ValidationResult:
    """Validate a layout configuration using the global validator."""
    return _validator.validate(config)


def validate_layout_quick(config: LayoutConfiguration) -> bool:
    """Quick layout validation using the global validator."""
    return _validator.validate_quick(config)


def get_validator() -> LayoutValidator:
    """Get the global layout validator."""
    return _validator


def add_validation_rule(rule: ValidationRule) -> None:
    """Add a custom validation rule to the global validator."""
    _validator.add_rule(rule)