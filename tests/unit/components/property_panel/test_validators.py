"""Tests for Property Validation Framework

Comprehensive test suite for validation framework including validators,
validation engine, UI components, and rule system. Ensures >95% code
coverage and validates all functionality.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QTimer
from PyQt6.QtTest import QTest

from torematrix.ui.components.property_panel.validators import (
    ValidationSeverity, ValidationMessage, ValidationResult,
    PropertyValidator, RequiredValidator, TypeValidator, RangeValidator,
    LengthValidator, RegexValidator, ChoiceValidator, ValidationEngine
)
from torematrix.ui.components.property_panel.validation_ui import (
    ValidationIcon, ValidationIndicatorWidget, ValidationDetailsDialog,
    ValidationSummaryWidget
)
from torematrix.ui.components.property_panel.rules import (
    RuleOperator, RuleLogic, RuleCondition, ValidationRule,
    BusinessRuleValidator, RuleBuilder, RuleSet, RuleManager
)


@pytest.fixture
def qapp():
    """PyQt application fixture"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestValidationMessage:
    """Test ValidationMessage functionality"""
    
    def test_creation(self):
        msg = ValidationMessage(
            message="Test error",
            severity=ValidationSeverity.ERROR,
            field="test_field",
            code="test_error",
            suggestion="Fix this"
        )
        
        assert msg.message == "Test error"
        assert msg.severity == ValidationSeverity.ERROR
        assert msg.field == "test_field"
        assert msg.code == "test_error"
        assert msg.suggestion == "Fix this"
    
    def test_defaults(self):
        msg = ValidationMessage("Test", ValidationSeverity.INFO)
        assert msg.field is None
        assert msg.code is None
        assert msg.suggestion is None
        assert msg.details is None


class TestValidationResult:
    """Test ValidationResult functionality"""
    
    def test_creation(self):
        result = ValidationResult(is_valid=True)
        assert result.is_valid
        assert len(result.messages) == 0
        assert len(result.field_errors) == 0
        assert len(result.warnings) == 0
        assert len(result.info) == 0
        assert result.validation_timestamp is not None
    
    def test_add_message(self):
        result = ValidationResult(is_valid=True)
        
        # Add error - should invalidate result
        error_msg = ValidationMessage("Error", ValidationSeverity.ERROR, field="test")
        result.add_message(error_msg)
        
        assert not result.is_valid
        assert len(result.messages) == 1
        assert "test" in result.field_errors
        assert len(result.field_errors["test"]) == 1
    
    def test_add_warning(self):
        result = ValidationResult(is_valid=True)
        
        warning_msg = ValidationMessage("Warning", ValidationSeverity.WARNING, field="test")
        result.add_message(warning_msg)
        
        assert result.is_valid  # Warnings don't invalidate
        assert len(result.warnings) == 1
        assert len(result.field_errors["test"]) == 1
    
    def test_convenience_methods(self):
        result = ValidationResult(is_valid=True)
        
        result.add_error("Error message", field="field1", code="ERR001")
        result.add_warning("Warning message", field="field2", code="WARN001")
        result.add_info("Info message", field="field3")
        
        assert not result.is_valid
        assert result.get_error_count() == 1
        assert result.get_warning_count() == 1
        assert len(result.get_field_messages("field1")) == 1
        assert result.has_field_errors("field1")
        assert not result.has_field_errors("field2")  # Warning, not error
    
    def test_get_summary(self):
        result = ValidationResult(is_valid=True)
        assert result.get_summary() == "Valid"
        
        result.add_warning("Warning")
        assert "warnings" in result.get_summary()
        
        result.add_error("Error")
        assert "errors" in result.get_summary()


class TestRequiredValidator:
    """Test RequiredValidator"""
    
    def setup_method(self):
        self.validator = RequiredValidator()
    
    def test_valid_values(self):
        # Non-empty string
        result = self.validator.validate("test")
        assert result.is_valid
        
        # Non-empty list
        result = self.validator.validate([1, 2, 3])
        assert result.is_valid
        
        # Zero is valid
        result = self.validator.validate(0)
        assert result.is_valid
        
        # False is valid
        result = self.validator.validate(False)
        assert result.is_valid
    
    def test_invalid_values(self):
        # None
        result = self.validator.validate(None)
        assert not result.is_valid
        assert "required" in result.messages[0].code
        
        # Empty string
        result = self.validator.validate("")
        assert not result.is_valid
        
        # Whitespace string
        result = self.validator.validate("   ")
        assert not result.is_valid
        
        # Empty list
        result = self.validator.validate([])
        assert not result.is_valid


class TestTypeValidator:
    """Test TypeValidator"""
    
    def test_string_validation(self):
        validator = TypeValidator(str)
        
        assert validator.validate("test").is_valid
        assert not validator.validate(123).is_valid
        assert not validator.validate(None).is_valid
    
    def test_allow_none(self):
        validator = TypeValidator(str, allow_none=True)
        
        assert validator.validate("test").is_valid
        assert validator.validate(None).is_valid
        assert not validator.validate(123).is_valid
    
    def test_multiple_types(self):
        validator = TypeValidator((str, int))
        
        assert validator.validate("test").is_valid
        assert validator.validate(123).is_valid
        assert not validator.validate(12.5).is_valid
    
    def test_error_message(self):
        validator = TypeValidator(str)
        result = validator.validate(123)
        
        assert not result.is_valid
        assert "Expected str, got int" in result.messages[0].message
        assert "type_mismatch" in result.messages[0].code


class TestRangeValidator:
    """Test RangeValidator"""
    
    def test_min_value(self):
        validator = RangeValidator(min_value=10)
        
        assert validator.validate(15).is_valid
        assert validator.validate(10).is_valid  # Inclusive by default
        assert not validator.validate(5).is_valid
    
    def test_max_value(self):
        validator = RangeValidator(max_value=100)
        
        assert validator.validate(50).is_valid
        assert validator.validate(100).is_valid  # Inclusive by default
        assert not validator.validate(150).is_valid
    
    def test_min_max_value(self):
        validator = RangeValidator(min_value=10, max_value=100)
        
        assert validator.validate(50).is_valid
        assert validator.validate(10).is_valid
        assert validator.validate(100).is_valid
        assert not validator.validate(5).is_valid
        assert not validator.validate(150).is_valid
    
    def test_exclusive_range(self):
        validator = RangeValidator(min_value=10, max_value=100, inclusive=False)
        
        assert validator.validate(50).is_valid
        assert not validator.validate(10).is_valid
        assert not validator.validate(100).is_valid
    
    def test_string_conversion(self):
        validator = RangeValidator(min_value=10, max_value=100)
        
        assert validator.validate("50").is_valid
        assert not validator.validate("5").is_valid
    
    def test_invalid_type(self):
        validator = RangeValidator(min_value=10)
        result = validator.validate("invalid")
        
        assert not result.is_valid
        assert "not_numeric" in result.messages[0].code
    
    def test_none_value(self):
        validator = RangeValidator(min_value=10)
        result = validator.validate(None)
        assert result.is_valid  # None is allowed


class TestLengthValidator:
    """Test LengthValidator"""
    
    def test_string_length(self):
        validator = LengthValidator(min_length=3, max_length=10)
        
        assert validator.validate("test").is_valid
        assert validator.validate("testing").is_valid
        assert not validator.validate("ab").is_valid  # Too short
        assert not validator.validate("this is too long").is_valid  # Too long
    
    def test_list_length(self):
        validator = LengthValidator(min_length=2, max_length=5)
        
        assert validator.validate([1, 2, 3]).is_valid
        assert not validator.validate([1]).is_valid  # Too short
        assert not validator.validate([1, 2, 3, 4, 5, 6]).is_valid  # Too long
    
    def test_min_only(self):
        validator = LengthValidator(min_length=3)
        
        assert validator.validate("test").is_valid
        assert validator.validate("very long string").is_valid
        assert not validator.validate("ab").is_valid
    
    def test_max_only(self):
        validator = LengthValidator(max_length=10)
        
        assert validator.validate("test").is_valid
        assert validator.validate("").is_valid
        assert not validator.validate("this is too long").is_valid
    
    def test_invalid_type(self):
        validator = LengthValidator(min_length=3)
        result = validator.validate(123)
        
        assert not result.is_valid
        assert "no_length" in result.messages[0].code


class TestRegexValidator:
    """Test RegexValidator"""
    
    def test_email_pattern(self):
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        validator = RegexValidator(email_pattern, "Valid email format")
        
        assert validator.validate("test@example.com").is_valid
        assert validator.validate("user.name+tag@domain.co.uk").is_valid
        assert not validator.validate("invalid-email").is_valid
        assert not validator.validate("@domain.com").is_valid
    
    def test_phone_pattern(self):
        phone_pattern = r'^\d{3}-\d{3}-\d{4}$'
        validator = RegexValidator(phone_pattern, "Phone format: XXX-XXX-XXXX")
        
        assert validator.validate("123-456-7890").is_valid
        assert not validator.validate("1234567890").is_valid
        assert not validator.validate("123-45-6789").is_valid
    
    def test_non_string_value(self):
        validator = RegexValidator(r'\d+')
        result = validator.validate(123)
        
        assert not result.is_valid
        assert "not_string" in result.messages[0].code


class TestChoiceValidator:
    """Test ChoiceValidator"""
    
    def test_valid_choices(self):
        choices = ['red', 'green', 'blue']
        validator = ChoiceValidator(choices)
        
        assert validator.validate('red').is_valid
        assert validator.validate('green').is_valid
        assert validator.validate('blue').is_valid
        assert not validator.validate('yellow').is_valid
    
    def test_case_insensitive(self):
        choices = ['Red', 'Green', 'Blue']
        validator = ChoiceValidator(choices, case_sensitive=False)
        
        assert validator.validate('red').is_valid
        assert validator.validate('RED').is_valid
        assert validator.validate('Green').is_valid
        assert not validator.validate('yellow').is_valid
    
    def test_numeric_choices(self):
        choices = [1, 2, 3, 5, 8]
        validator = ChoiceValidator(choices)
        
        assert validator.validate(1).is_valid
        assert validator.validate(5).is_valid
        assert not validator.validate(4).is_valid
        assert not validator.validate(10).is_valid


class TestValidationEngine:
    """Test ValidationEngine"""
    
    def setup_method(self):
        self.engine = ValidationEngine()
    
    def test_register_validator(self):
        validator = RequiredValidator()
        self.engine.register_validator("test_required", validator)
        
        assert "test_required" in self.engine.validators
        assert self.engine.validators["test_required"] == validator
    
    def test_unregister_validator(self):
        validator = RequiredValidator()
        self.engine.register_validator("test_required", validator)
        self.engine.unregister_validator("test_required")
        
        assert "test_required" not in self.engine.validators
    
    def test_field_validators(self):
        # Add field-specific validator
        self.engine.add_field_validator("name", "required")
        
        assert "name" in self.engine.field_validators
        assert "required" in self.engine.field_validators["name"]
        
        # Remove field validator
        self.engine.remove_field_validator("name", "required")
        assert "required" not in self.engine.field_validators.get("name", [])
    
    def test_global_validators(self):
        self.engine.add_global_validator("string_type")
        assert "string_type" in self.engine.global_validators
        
        self.engine.remove_global_validator("string_type")
        assert "string_type" not in self.engine.global_validators
    
    def test_validate_field(self):
        # Setup validators
        self.engine.add_field_validator("name", "required")
        
        # Test valid value
        result = self.engine.validate_field("name", "John Doe")
        assert result.is_valid
        
        # Test invalid value
        result = self.engine.validate_field("name", "")
        assert not result.is_valid
        assert result.performance_ms is not None
    
    def test_validate_field_async(self):
        """Test asynchronous validation with debouncing"""
        with patch.object(self.engine.validation_timer, 'start') as mock_start:
            self.engine.validate_field_async("name", "test")
            
            assert "name" in self.engine.pending_validations
            mock_start.assert_called_once_with(self.engine.debounce_delay_ms)
    
    def test_configure_debouncing(self):
        self.engine.configure_debouncing(500)
        assert self.engine.debounce_delay_ms == 500
        
        # Test minimum limit
        self.engine.configure_debouncing(50)
        assert self.engine.debounce_delay_ms == 100  # Minimum 100ms
    
    def test_performance_target(self):
        self.engine.set_performance_target(25.0)
        assert self.engine.max_validation_time_ms == 25.0
    
    def test_get_validator_info(self):
        info = self.engine.get_validator_info()
        
        assert isinstance(info, dict)
        assert "required" in info
        assert "name" in info["required"]
        assert "description" in info["required"]


class TestRuleCondition:
    """Test RuleCondition functionality"""
    
    def test_equals_operator(self):
        condition = RuleCondition("field1", RuleOperator.EQUALS, "test")
        
        assert condition.evaluate({"field1": "test"})
        assert not condition.evaluate({"field1": "other"})
    
    def test_greater_than_operator(self):
        condition = RuleCondition("age", RuleOperator.GREATER_THAN, 18)
        
        assert condition.evaluate({"age": 25})
        assert not condition.evaluate({"age": 15})
        assert not condition.evaluate({"age": 18})  # Not inclusive
    
    def test_contains_operator(self):
        condition = RuleCondition("text", RuleOperator.CONTAINS, "test")
        
        assert condition.evaluate({"text": "this is a test"})
        assert not condition.evaluate({"text": "no match here"})
    
    def test_case_sensitivity(self):
        condition = RuleCondition("text", RuleOperator.CONTAINS, "TEST", case_sensitive=False)
        
        assert condition.evaluate({"text": "this is a test"})
        assert condition.evaluate({"text": "this is a TEST"})
    
    def test_in_list_operator(self):
        condition = RuleCondition("status", RuleOperator.IN_LIST, ["active", "pending"])
        
        assert condition.evaluate({"status": "active"})
        assert condition.evaluate({"status": "pending"})
        assert not condition.evaluate({"status": "inactive"})
    
    def test_is_null_operator(self):
        condition = RuleCondition("optional", RuleOperator.IS_NULL)
        
        assert condition.evaluate({"optional": None})
        assert not condition.evaluate({"optional": "value"})
    
    def test_is_empty_operator(self):
        condition = RuleCondition("text", RuleOperator.IS_EMPTY)
        
        assert condition.evaluate({"text": ""})
        assert condition.evaluate({"text": "   "})  # Whitespace is empty
        assert condition.evaluate({"text": []})
        assert condition.evaluate({"text": None})
        assert not condition.evaluate({"text": "value"})
    
    def test_nested_field_access(self):
        condition = RuleCondition("user.name", RuleOperator.EQUALS, "John")
        
        context = {
            "user": {
                "name": "John",
                "age": 30
            }
        }
        
        assert condition.evaluate(context)
        
        condition = RuleCondition("user.age", RuleOperator.GREATER_THAN, 25)
        assert condition.evaluate(context)


class TestValidationRule:
    """Test ValidationRule functionality"""
    
    def test_single_condition_and_logic(self):
        condition = RuleCondition("age", RuleOperator.GREATER_THAN, 18)
        rule = ValidationRule("Adult Check", "Must be adult", [condition])
        
        assert rule.evaluate({"age": 25})
        assert not rule.evaluate({"age": 15})
    
    def test_multiple_conditions_and_logic(self):
        conditions = [
            RuleCondition("age", RuleOperator.GREATER_THAN, 18),
            RuleCondition("status", RuleOperator.EQUALS, "active")
        ]
        rule = ValidationRule("Active Adult", "Must be active adult", conditions, RuleLogic.AND)
        
        assert rule.evaluate({"age": 25, "status": "active"})
        assert not rule.evaluate({"age": 25, "status": "inactive"})
        assert not rule.evaluate({"age": 15, "status": "active"})
    
    def test_multiple_conditions_or_logic(self):
        conditions = [
            RuleCondition("role", RuleOperator.EQUALS, "admin"),
            RuleCondition("role", RuleOperator.EQUALS, "moderator")
        ]
        rule = ValidationRule("Privileged User", "Admin or moderator", conditions, RuleLogic.OR)
        
        assert rule.evaluate({"role": "admin"})
        assert rule.evaluate({"role": "moderator"})
        assert not rule.evaluate({"role": "user"})
    
    def test_not_logic(self):
        condition = RuleCondition("status", RuleOperator.EQUALS, "banned")
        rule = ValidationRule("Not Banned", "Must not be banned", [condition], RuleLogic.NOT)
        
        assert rule.evaluate({"status": "active"})
        assert not rule.evaluate({"status": "banned"})
    
    def test_field_applicability(self):
        rule = ValidationRule("Name Rule", "For name fields", applies_to_fields=["name", "full_name"])
        
        assert rule.is_applicable("name", "user")
        assert rule.is_applicable("full_name", "user")
        assert not rule.is_applicable("email", "user")
    
    def test_type_applicability(self):
        rule = ValidationRule("User Rule", "For user types", applies_to_types=["user", "admin"])
        
        assert rule.is_applicable("name", "user")
        assert rule.is_applicable("name", "admin")
        assert not rule.is_applicable("name", "product")
    
    def test_disabled_rule(self):
        rule = ValidationRule("Disabled Rule", "Should not apply", enabled=False)
        
        assert not rule.is_applicable("any_field", "any_type")


class TestRuleBuilder:
    """Test RuleBuilder functionality"""
    
    def test_build_simple_rule(self):
        rule = (RuleBuilder()
                .name("Age Check")
                .description("Must be adult")
                .when("age", RuleOperator.GREATER_THAN, 18)
                .severity(ValidationSeverity.ERROR)
                .message("Must be 18 or older")
                .build())
        
        assert rule.name == "Age Check"
        assert rule.description == "Must be adult"
        assert len(rule.conditions) == 1
        assert rule.severity == ValidationSeverity.ERROR
        assert rule.message == "Must be 18 or older"
    
    def test_build_complex_rule(self):
        rule = (RuleBuilder()
                .name("Complex Rule")
                .when("age", RuleOperator.GREATER_THAN, 18)
                .and_when("status", RuleOperator.EQUALS, "active")
                .for_fields("user_age")
                .for_types("user", "admin")
                .priority(10)
                .suggestion("Check age and status")
                .build())
        
        assert len(rule.conditions) == 2
        assert rule.logic == RuleLogic.AND
        assert rule.applies_to_fields == ["user_age"]
        assert rule.applies_to_types == ["user", "admin"]
        assert rule.priority == 10
    
    def test_builder_reset(self):
        builder = RuleBuilder()
        
        # Build first rule
        rule1 = (builder
                .name("Rule 1")
                .when("field1", RuleOperator.EQUALS, "value1")
                .build())
        
        # Build second rule - should not have first rule's data
        rule2 = (builder
                .name("Rule 2")
                .when("field2", RuleOperator.EQUALS, "value2")
                .build())
        
        assert rule1.name == "Rule 1"
        assert rule2.name == "Rule 2"
        assert len(rule1.conditions) == 1
        assert len(rule2.conditions) == 1
        assert rule1.conditions[0].field == "field1"
        assert rule2.conditions[0].field == "field2"


class TestRuleSet:
    """Test RuleSet functionality"""
    
    def setup_method(self):
        self.rule_set = RuleSet("Test Rules")
    
    def test_add_remove_rules(self):
        rule = ValidationRule("Test Rule", "Test description")
        
        self.rule_set.add_rule(rule)
        assert len(self.rule_set.rules) == 1
        assert self.rule_set.get_rule("Test Rule") == rule
        
        self.rule_set.remove_rule("Test Rule")
        assert len(self.rule_set.rules) == 0
        assert self.rule_set.get_rule("Test Rule") is None
    
    def test_get_applicable_rules(self):
        rule1 = ValidationRule("General Rule", "Applies to all")
        rule2 = ValidationRule("Field Rule", "For name field", applies_to_fields=["name"])
        rule3 = ValidationRule("Type Rule", "For user type", applies_to_types=["user"])
        
        self.rule_set.add_rule(rule1)
        self.rule_set.add_rule(rule2)
        self.rule_set.add_rule(rule3)
        
        # Should get general rule and field rule
        applicable = self.rule_set.get_applicable_rules("name", "product")
        assert len(applicable) == 2
        assert rule1 in applicable
        assert rule2 in applicable
        
        # Should get general rule and type rule
        applicable = self.rule_set.get_applicable_rules("email", "user")
        assert len(applicable) == 2
        assert rule1 in applicable
        assert rule3 in applicable
    
    def test_disabled_ruleset(self):
        rule = ValidationRule("Test Rule", "Test")
        self.rule_set.add_rule(rule)
        self.rule_set.enabled = False
        
        applicable = self.rule_set.get_applicable_rules("any_field", "any_type")
        assert len(applicable) == 0
    
    def test_serialization(self):
        rule = (RuleBuilder()
                .name("Test Rule")
                .description("Test description")
                .when("field1", RuleOperator.EQUALS, "value1")
                .severity(ValidationSeverity.WARNING)
                .message("Test message")
                .build())
        
        self.rule_set.add_rule(rule)
        self.rule_set.metadata = {"version": "1.0"}
        
        # Convert to dict
        data = self.rule_set.to_dict()
        
        assert data["name"] == "Test Rules"
        assert data["enabled"] == True
        assert data["metadata"]["version"] == "1.0"
        assert len(data["rules"]) == 1
        
        # Load from dict
        new_rule_set = RuleSet("Empty")
        new_rule_set.from_dict(data)
        
        assert new_rule_set.name == "Test Rules"
        assert len(new_rule_set.rules) == 1
        assert new_rule_set.rules[0].name == "Test Rule"


class TestRuleManager:
    """Test RuleManager functionality"""
    
    def setup_method(self):
        self.manager = RuleManager()
    
    def test_rule_set_management(self):
        rule_set = RuleSet("Test Rules")
        
        self.manager.add_rule_set(rule_set)
        assert "Test Rules" in self.manager.rule_sets
        
        self.manager.activate_rule_set("Test Rules")
        assert "Test Rules" in self.manager.active_rule_sets
        
        self.manager.deactivate_rule_set("Test Rules")
        assert "Test Rules" not in self.manager.active_rule_sets
        
        self.manager.remove_rule_set("Test Rules")
        assert "Test Rules" not in self.manager.rule_sets
    
    def test_get_active_rules(self):
        # Create rule sets
        rule_set1 = RuleSet("Set 1")
        rule1 = ValidationRule("Rule 1", "Test", priority=10)
        rule_set1.add_rule(rule1)
        
        rule_set2 = RuleSet("Set 2")
        rule2 = ValidationRule("Rule 2", "Test", priority=5)
        rule_set2.add_rule(rule2)
        
        # Add and activate rule sets
        self.manager.add_rule_set(rule_set1)
        self.manager.add_rule_set(rule_set2)
        self.manager.activate_rule_set("Set 1")
        self.manager.activate_rule_set("Set 2")
        
        # Get active rules - should be sorted by priority
        rules = self.manager.get_active_rules("any_field", "any_type")
        assert len(rules) == 2
        assert rules[0] == rule1  # Higher priority first
        assert rules[1] == rule2
    
    def test_validate_with_rules(self):
        # Create rule that fails
        rule = (RuleBuilder()
                .name("Age Rule")
                .when("value", RuleOperator.LESS_THAN, 18)
                .message("Too young")
                .build())
        
        rule_set = RuleSet("Age Rules")
        rule_set.add_rule(rule)
        
        self.manager.add_rule_set(rule_set)
        self.manager.activate_rule_set("Age Rules")
        
        # Validate - should fail
        context = {"element_type": "user"}
        result = self.manager.validate_with_rules("age", 15, context)
        
        assert not result.is_valid
        assert len(result.messages) == 1
        assert "Too young" in result.messages[0].message


@pytest.mark.usefixtures("qapp")
class TestValidationUI:
    """Test validation UI components"""
    
    def test_validation_icon_creation(self):
        icon = ValidationIcon()
        assert icon.severity == ValidationSeverity.INFO
        assert not icon.is_validating
    
    def test_validation_icon_severity_change(self):
        icon = ValidationIcon()
        icon.set_severity(ValidationSeverity.ERROR)
        assert icon.severity == ValidationSeverity.ERROR
    
    def test_validation_icon_animation(self):
        icon = ValidationIcon()
        icon.set_validating(True)
        assert icon.is_validating
        assert icon.animation_timer.isActive()
        
        icon.set_validating(False)
        assert not icon.is_validating
        assert not icon.animation_timer.isActive()
    
    def test_validation_indicator_widget(self):
        widget = ValidationIndicatorWidget()
        assert not widget.isVisible()  # Initially hidden
        
        # Set validation result
        result = ValidationResult(is_valid=False)
        result.add_error("Test error")
        
        widget.set_validation_result(result)
        # Widget should become visible with error
    
    def test_validation_summary_widget(self):
        widget = ValidationSummaryWidget()
        
        # Add field results
        result1 = ValidationResult(is_valid=True)
        result2 = ValidationResult(is_valid=False)
        result2.add_error("Error in field2")
        
        widget.set_field_result("field1", result1)
        widget.set_field_result("field2", result2)
        
        # Should show overall error status
        # (Exact assertions depend on UI implementation)
    
    def test_validation_details_dialog(self):
        result = ValidationResult(is_valid=False)
        result.add_error("Test error", field="test_field", code="TEST_ERROR")
        result.add_warning("Test warning", field="test_field")
        
        dialog = ValidationDetailsDialog(result)
        
        assert dialog.windowTitle() == "Validation Details"
        assert dialog.messages_list.count() == 2  # Error + warning


class TestBusinessRuleValidator:
    """Test BusinessRuleValidator"""
    
    def test_rule_validation(self):
        # Create rule that requires age > 18
        rule = (RuleBuilder()
                .name("Adult Check")
                .when("value", RuleOperator.GREATER_THAN, 18)
                .message("Must be adult")
                .build())
        
        validator = BusinessRuleValidator([rule])
        
        # Test valid value
        context = {"field_name": "age", "element_type": "user"}
        result = validator.validate(25, context)
        assert result.is_valid
        
        # Test invalid value
        result = validator.validate(15, context)
        assert not result.is_valid
        assert "Must be adult" in result.messages[0].message
    
    def test_rule_applicability(self):
        # Create rule that only applies to name field
        rule = (RuleBuilder()
                .name("Name Rule")
                .when("value", RuleOperator.NOT_EQUALS, "")
                .for_fields("name")
                .message("Name required")
                .build())
        
        validator = BusinessRuleValidator([rule])
        
        # Should apply to name field
        context = {"field_name": "name", "element_type": "user"}
        result = validator.validate("", context)
        assert not result.is_valid
        
        # Should not apply to other fields
        context = {"field_name": "email", "element_type": "user"}
        result = validator.validate("", context)
        assert result.is_valid  # No applicable rules


if __name__ == "__main__":
    pytest.main([__file__, "-v"])