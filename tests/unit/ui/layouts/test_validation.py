"""Unit tests for layout validation system."""

import pytest
from unittest.mock import Mock, MagicMock

from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import QSize, QMargins

from torematrix.ui.layouts.validation import (
    ValidationSeverity, ValidationMessage, ValidationResult, ValidationRule,
    LayoutValidator, LayoutNameRule, LayoutGeometryRule, LayoutItemsRule,
    LayoutTypeSpecificRule, LayoutPerformanceRule,
    validate_layout, validate_layout_quick, get_validator, add_validation_rule
)
from torematrix.ui.layouts.base import (
    LayoutType, LayoutGeometry, LayoutItem, LayoutConfiguration
)


class TestValidationMessage:
    """Test ValidationMessage data class."""
    
    def test_basic_message(self):
        """Test basic validation message."""
        message = ValidationMessage(
            severity=ValidationSeverity.ERROR,
            code="TEST_ERROR",
            message="Test error message"
        )
        
        assert message.severity == ValidationSeverity.ERROR
        assert message.code == "TEST_ERROR"
        assert message.message == "Test error message"
        assert message.item_id is None
        assert message.suggestion is None
        assert message.auto_fix is None
    
    def test_complete_message(self):
        """Test validation message with all fields."""
        def auto_fix():
            return True
        
        message = ValidationMessage(
            severity=ValidationSeverity.WARNING,
            code="TEST_WARNING",
            message="Test warning message",
            item_id="item1",
            suggestion="Fix suggestion",
            auto_fix=auto_fix
        )
        
        assert message.severity == ValidationSeverity.WARNING
        assert message.code == "TEST_WARNING"
        assert message.message == "Test warning message"
        assert message.item_id == "item1"
        assert message.suggestion == "Fix suggestion"
        assert message.auto_fix == auto_fix


class TestValidationResult:
    """Test ValidationResult data class."""
    
    def test_valid_result(self):
        """Test valid validation result."""
        messages = [
            ValidationMessage(ValidationSeverity.INFO, "INFO_1", "Info message"),
            ValidationMessage(ValidationSeverity.WARNING, "WARN_1", "Warning message")
        ]
        
        result = ValidationResult(is_valid=True, messages=messages)
        
        assert result.is_valid is True
        assert len(result.messages) == 2
        assert result.warnings_count == 1
        assert result.errors_count == 0
    
    def test_invalid_result_with_errors(self):
        """Test invalid result with errors."""
        messages = [
            ValidationMessage(ValidationSeverity.WARNING, "WARN_1", "Warning"),
            ValidationMessage(ValidationSeverity.ERROR, "ERR_1", "Error"),
            ValidationMessage(ValidationSeverity.CRITICAL, "CRIT_1", "Critical")
        ]
        
        result = ValidationResult(is_valid=True, messages=messages)  # Will be overridden
        
        assert result.is_valid is False  # Should be overridden due to errors
        assert result.warnings_count == 1
        assert result.errors_count == 2


class TestLayoutNameRule:
    """Test LayoutNameRule validation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.rule = LayoutNameRule()
    
    def test_valid_name(self):
        """Test validation with valid name."""
        config = LayoutConfiguration(
            id="test", name="Valid Layout Name", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry()
        )
        
        messages = self.rule.validate(config)
        assert len(messages) == 0
    
    def test_empty_name(self):
        """Test validation with empty name."""
        config = LayoutConfiguration(
            id="test", name="", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry()
        )
        
        messages = self.rule.validate(config)
        assert len(messages) == 1
        assert messages[0].severity == ValidationSeverity.ERROR
        assert messages[0].code == "LAYOUT_NO_NAME"
    
    def test_short_name(self):
        """Test validation with very short name."""
        config = LayoutConfiguration(
            id="test", name="A", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry()
        )
        
        messages = self.rule.validate(config)
        assert len(messages) == 1
        assert messages[0].severity == ValidationSeverity.WARNING
        assert messages[0].code == "LAYOUT_SHORT_NAME"
    
    def test_long_name(self):
        """Test validation with very long name."""
        config = LayoutConfiguration(
            id="test", name="A" * 150, 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry()
        )
        
        messages = self.rule.validate(config)
        assert len(messages) == 1
        assert messages[0].severity == ValidationSeverity.WARNING
        assert messages[0].code == "LAYOUT_LONG_NAME"
    
    def test_invalid_characters(self):
        """Test validation with invalid characters."""
        config = LayoutConfiguration(
            id="test", name="Layout<>Name", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry()
        )
        
        messages = self.rule.validate(config)
        assert len(messages) == 1
        assert messages[0].severity == ValidationSeverity.ERROR
        assert messages[0].code == "LAYOUT_INVALID_NAME_CHARS"


class TestLayoutGeometryRule:
    """Test LayoutGeometryRule validation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.rule = LayoutGeometryRule()
    
    def test_valid_geometry(self):
        """Test validation with valid geometry."""
        geometry = LayoutGeometry(x=100, y=100, width=800, height=600)
        config = LayoutConfiguration(
            id="test", name="Test Layout", 
            layout_type=LayoutType.DOCUMENT, geometry=geometry
        )
        
        messages = self.rule.validate(config)
        assert len(messages) == 0
    
    def test_width_too_small(self):
        """Test validation with width too small."""
        geometry = LayoutGeometry(width=100, height=600)  # Below minimum 320
        config = LayoutConfiguration(
            id="test", name="Test Layout", 
            layout_type=LayoutType.DOCUMENT, geometry=geometry
        )
        
        messages = self.rule.validate(config)
        assert len(messages) == 1
        assert messages[0].severity == ValidationSeverity.ERROR
        assert messages[0].code == "LAYOUT_WIDTH_TOO_SMALL"
    
    def test_height_too_small(self):
        """Test validation with height too small."""
        geometry = LayoutGeometry(width=800, height=100)  # Below minimum 240
        config = LayoutConfiguration(
            id="test", name="Test Layout", 
            layout_type=LayoutType.DOCUMENT, geometry=geometry
        )
        
        messages = self.rule.validate(config)
        assert len(messages) == 1
        assert messages[0].severity == ValidationSeverity.ERROR
        assert messages[0].code == "LAYOUT_HEIGHT_TOO_SMALL"
    
    def test_width_too_large(self):
        """Test validation with width too large."""
        geometry = LayoutGeometry(width=10000, height=600)  # Above maximum 7680
        config = LayoutConfiguration(
            id="test", name="Test Layout", 
            layout_type=LayoutType.DOCUMENT, geometry=geometry
        )
        
        messages = self.rule.validate(config)
        assert len(messages) == 1
        assert messages[0].severity == ValidationSeverity.WARNING
        assert messages[0].code == "LAYOUT_WIDTH_TOO_LARGE"
    
    def test_negative_position(self):
        """Test validation with very negative position."""
        geometry = LayoutGeometry(x=-2000, y=-2000, width=800, height=600)
        config = LayoutConfiguration(
            id="test", name="Test Layout", 
            layout_type=LayoutType.DOCUMENT, geometry=geometry
        )
        
        messages = self.rule.validate(config)
        assert len(messages) == 1
        assert messages[0].severity == ValidationSeverity.WARNING
        assert messages[0].code == "LAYOUT_POSITION_NEGATIVE"


class TestLayoutItemsRule:
    """Test LayoutItemsRule validation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.rule = LayoutItemsRule()
    
    def test_valid_items(self):
        """Test validation with valid items."""
        widget1 = QLabel("Widget 1")
        widget2 = QLabel("Widget 2")
        
        item1 = LayoutItem("item1", widget1, "Item 1", LayoutType.DOCUMENT, LayoutGeometry())
        item2 = LayoutItem("item2", widget2, "Item 2", LayoutType.DOCUMENT, LayoutGeometry())
        
        config = LayoutConfiguration(
            id="test", name="Test Layout", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry(),
            items=[item1, item2]
        )
        
        messages = self.rule.validate(config)
        assert len(messages) == 0
    
    def test_too_many_items(self):
        """Test validation with too many items."""
        items = []
        for i in range(60):  # Above maximum 50
            widget = QLabel(f"Widget {i}")
            item = LayoutItem(f"item{i}", widget, f"Item {i}", LayoutType.DOCUMENT, LayoutGeometry())
            items.append(item)
        
        config = LayoutConfiguration(
            id="test", name="Test Layout", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry(),
            items=items
        )
        
        messages = self.rule.validate(config)
        assert len(messages) == 1
        assert messages[0].severity == ValidationSeverity.WARNING
        assert messages[0].code == "LAYOUT_TOO_MANY_ITEMS"
    
    def test_duplicate_item_ids(self):
        """Test validation with duplicate item IDs."""
        widget1 = QLabel("Widget 1")
        widget2 = QLabel("Widget 2")
        
        item1 = LayoutItem("duplicate_id", widget1, "Item 1", LayoutType.DOCUMENT, LayoutGeometry())
        item2 = LayoutItem("duplicate_id", widget2, "Item 2", LayoutType.DOCUMENT, LayoutGeometry())
        
        config = LayoutConfiguration(
            id="test", name="Test Layout", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry(),
            items=[item1, item2]
        )
        
        messages = self.rule.validate(config)
        errors = [msg for msg in messages if msg.code == "LAYOUT_DUPLICATE_ITEM_ID"]
        assert len(errors) == 1
        assert errors[0].severity == ValidationSeverity.ERROR
    
    def test_duplicate_item_names(self):
        """Test validation with duplicate item names."""
        widget1 = QLabel("Widget 1")
        widget2 = QLabel("Widget 2")
        
        item1 = LayoutItem("item1", widget1, "Duplicate Name", LayoutType.DOCUMENT, LayoutGeometry())
        item2 = LayoutItem("item2", widget2, "Duplicate Name", LayoutType.DOCUMENT, LayoutGeometry())
        
        config = LayoutConfiguration(
            id="test", name="Test Layout", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry(),
            items=[item1, item2]
        )
        
        messages = self.rule.validate(config)
        warnings = [msg for msg in messages if msg.code == "LAYOUT_DUPLICATE_ITEM_NAME"]
        assert len(warnings) == 1
        assert warnings[0].severity == ValidationSeverity.WARNING
    
    def test_item_no_widget(self):
        """Test validation with item having no widget."""
        item = LayoutItem("item1", None, "Item 1", LayoutType.DOCUMENT, LayoutGeometry())
        
        config = LayoutConfiguration(
            id="test", name="Test Layout", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry(),
            items=[item]
        )
        
        messages = self.rule.validate(config)
        errors = [msg for msg in messages if msg.code == "LAYOUT_ITEM_NO_WIDGET"]
        assert len(errors) == 1
        assert errors[0].severity == ValidationSeverity.ERROR
    
    def test_item_negative_stretch(self):
        """Test validation with negative stretch factor."""
        widget = QLabel("Widget")
        item = LayoutItem("item1", widget, "Item 1", LayoutType.DOCUMENT, LayoutGeometry(), stretch_factor=-1)
        
        config = LayoutConfiguration(
            id="test", name="Test Layout", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry(),
            items=[item]
        )
        
        messages = self.rule.validate(config)
        errors = [msg for msg in messages if msg.code == "LAYOUT_ITEM_INVALID_STRETCH"]
        assert len(errors) == 1
        assert errors[0].severity == ValidationSeverity.ERROR
    
    def test_item_size_conflict(self):
        """Test validation with conflicting size constraints."""
        widget = QLabel("Widget")
        item = LayoutItem(
            "item1", widget, "Item 1", LayoutType.DOCUMENT, LayoutGeometry(),
            minimum_size=QSize(500, 400),
            maximum_size=QSize(300, 200)  # Smaller than minimum
        )
        
        config = LayoutConfiguration(
            id="test", name="Test Layout", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry(),
            items=[item]
        )
        
        messages = self.rule.validate(config)
        errors = [msg for msg in messages if msg.code == "LAYOUT_ITEM_SIZE_CONFLICT"]
        assert len(errors) == 2  # One for width, one for height


class TestLayoutTypeSpecificRule:
    """Test LayoutTypeSpecificRule validation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.rule = LayoutTypeSpecificRule()
    
    def test_document_layout_validation(self):
        """Test document layout specific validation."""
        widget = QLabel("Widget")
        item = LayoutItem("item1", widget, "Item 1", LayoutType.DOCUMENT, LayoutGeometry())
        item.properties["area_type"] = "properties"  # No document area
        
        config = LayoutConfiguration(
            id="test", name="Test Layout", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry(),
            items=[item]
        )
        
        messages = self.rule.validate(config)
        warnings = [msg for msg in messages if msg.code == "DOCUMENT_LAYOUT_NO_DOCUMENT_AREA"]
        assert len(warnings) == 1
        assert warnings[0].severity == ValidationSeverity.WARNING
    
    def test_split_layout_validation(self):
        """Test split layout specific validation."""
        widget = QLabel("Widget")
        item = LayoutItem("item1", widget, "Item 1", LayoutType.SPLIT_HORIZONTAL, LayoutGeometry())
        item.properties["area_type"] = "secondary"  # No primary area
        
        config = LayoutConfiguration(
            id="test", name="Test Layout", 
            layout_type=LayoutType.SPLIT_HORIZONTAL, geometry=LayoutGeometry(),
            items=[item]
        )
        
        messages = self.rule.validate(config)
        warnings = [msg for msg in messages if msg.code == "SPLIT_LAYOUT_NO_PRIMARY"]
        assert len(warnings) == 1
        assert warnings[0].severity == ValidationSeverity.WARNING
    
    def test_tabbed_layout_too_many_tabs(self):
        """Test tabbed layout with too many tabs."""
        items = []
        for i in range(25):  # More than recommended 20
            widget = QLabel(f"Widget {i}")
            item = LayoutItem(f"item{i}", widget, f"Item {i}", LayoutType.TABBED, LayoutGeometry())
            item.properties["tab_name"] = f"Tab {i}"
            items.append(item)
        
        config = LayoutConfiguration(
            id="test", name="Test Layout", 
            layout_type=LayoutType.TABBED, geometry=LayoutGeometry(),
            items=items
        )
        
        messages = self.rule.validate(config)
        warnings = [msg for msg in messages if msg.code == "TABBED_LAYOUT_TOO_MANY_TABS"]
        assert len(warnings) == 1
        assert warnings[0].severity == ValidationSeverity.WARNING


class TestLayoutPerformanceRule:
    """Test LayoutPerformanceRule validation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.rule = LayoutPerformanceRule()
    
    def test_too_many_widgets(self):
        """Test validation with too many widgets."""
        items = []
        for i in range(120):  # More than recommended 100
            widget = QLabel(f"Widget {i}")
            item = LayoutItem(f"item{i}", widget, f"Item {i}", LayoutType.DOCUMENT, LayoutGeometry())
            items.append(item)
        
        config = LayoutConfiguration(
            id="test", name="Test Layout", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry(),
            items=items
        )
        
        messages = self.rule.validate(config)
        warnings = [msg for msg in messages if msg.code == "LAYOUT_PERFORMANCE_MANY_WIDGETS"]
        assert len(warnings) == 1
        assert warnings[0].severity == ValidationSeverity.WARNING
    
    def test_multi_panel_deep_nesting(self):
        """Test multi-panel layout with deep nesting."""
        # Create deeply nested structure
        panel_structure = {
            "type": "horizontal_split",
            "panels": [
                {
                    "type": "vertical_split",
                    "panels": [
                        {
                            "type": "horizontal_split",
                            "panels": [
                                {
                                    "type": "vertical_split",
                                    "panels": [
                                        {
                                            "type": "horizontal_split",
                                            "panels": [
                                                {
                                                    "type": "vertical_split",
                                                    "panels": [
                                                        {"type": "panel", "name": "deep_panel"}
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        config = LayoutConfiguration(
            id="test", name="Test Layout", 
            layout_type=LayoutType.MULTI_PANEL, geometry=LayoutGeometry(),
            properties={"panel_structure": panel_structure}
        )
        
        messages = self.rule.validate(config)
        warnings = [msg for msg in messages if msg.code == "LAYOUT_PERFORMANCE_DEEP_NESTING"]
        assert len(warnings) == 1
        assert warnings[0].severity == ValidationSeverity.WARNING


class TestLayoutValidator:
    """Test LayoutValidator main class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.validator = LayoutValidator()
    
    def test_default_rules_loaded(self):
        """Test that default rules are loaded."""
        rules = self.validator.get_rules()
        rule_names = [rule.name for rule in rules]
        
        assert "Layout Name" in rule_names
        assert "Layout Geometry" in rule_names
        assert "Layout Items" in rule_names
        assert "Layout Type Specific" in rule_names
        assert "Layout Performance" in rule_names
    
    def test_add_remove_custom_rule(self):
        """Test adding and removing custom rules."""
        class CustomRule(ValidationRule):
            def __init__(self):
                super().__init__("Custom Rule", "Custom test rule")
            
            def validate(self, config):
                return []
        
        custom_rule = CustomRule()
        
        # Add rule
        self.validator.add_rule(custom_rule)
        rules = self.validator.get_rules()
        rule_names = [rule.name for rule in rules]
        assert "Custom Rule" in rule_names
        
        # Remove rule
        result = self.validator.remove_rule("Custom Rule")
        assert result is True
        
        rules = self.validator.get_rules()
        rule_names = [rule.name for rule in rules]
        assert "Custom Rule" not in rule_names
    
    def test_validate_valid_config(self):
        """Test validation of valid configuration."""
        config = LayoutConfiguration(
            id="test", name="Valid Layout", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry()
        )
        
        result = self.validator.validate(config)
        
        assert result.is_valid is True
        assert result.errors_count == 0
    
    def test_validate_invalid_config(self):
        """Test validation of invalid configuration."""
        config = LayoutConfiguration(
            id="test", name="", # Invalid: empty name
            layout_type=LayoutType.DOCUMENT, 
            geometry=LayoutGeometry(width=100, height=100)  # Invalid: too small
        )
        
        result = self.validator.validate(config)
        
        assert result.is_valid is False
        assert result.errors_count > 0
    
    def test_validate_quick(self):
        """Test quick validation."""
        valid_config = LayoutConfiguration(
            id="test", name="Valid Layout", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry()
        )
        
        invalid_config = LayoutConfiguration(
            id="test", name="", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry()
        )
        
        assert self.validator.validate_quick(valid_config) is True
        assert self.validator.validate_quick(invalid_config) is False
    
    def test_auto_fix(self):
        """Test auto-fix functionality."""
        config = LayoutConfiguration(
            id="test", name="Test Layout", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry()
        )
        
        fixed_config, fix_messages = self.validator.auto_fix(config)
        
        # For this test, no auto-fixes are implemented, so config should be unchanged
        assert fixed_config == config
        assert len(fix_messages) == 0


class TestValidationFunctions:
    """Test module-level validation functions."""
    
    def test_validate_layout_function(self):
        """Test validate_layout function."""
        config = LayoutConfiguration(
            id="test", name="Test Layout", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry()
        )
        
        result = validate_layout(config)
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
    
    def test_validate_layout_quick_function(self):
        """Test validate_layout_quick function."""
        config = LayoutConfiguration(
            id="test", name="Test Layout", 
            layout_type=LayoutType.DOCUMENT, geometry=LayoutGeometry()
        )
        
        result = validate_layout_quick(config)
        assert isinstance(result, bool)
        assert result is True
    
    def test_get_validator_function(self):
        """Test get_validator function."""
        validator = get_validator()
        assert isinstance(validator, LayoutValidator)
    
    def test_add_validation_rule_function(self):
        """Test add_validation_rule function."""
        class TestRule(ValidationRule):
            def __init__(self):
                super().__init__("Test Function Rule", "Test rule")
            
            def validate(self, config):
                return []
        
        rule = TestRule()
        add_validation_rule(rule)
        
        validator = get_validator()
        rule_names = [r.name for r in validator.get_rules()]
        assert "Test Function Rule" in rule_names


if __name__ == "__main__":
    pytest.main([__file__])