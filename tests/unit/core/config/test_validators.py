"""
Unit tests for configuration validators.
"""

import pytest
from pathlib import Path
import tempfile

from torematrix.core.config.validators import (
    ValidationRule, RequiredRule, TypeRule, RangeRule, LengthRule,
    PatternRule, ChoiceRule, PathRule, URLRule, EmailRule, CustomRule,
    ConfigValidator, validate_field, validate_config, create_default_validator
)
from torematrix.core.config.types import ValidationSeverity
from torematrix.core.config.exceptions import ValidationError


class TestValidationRules:
    """Test individual validation rules."""
    
    def test_required_rule(self):
        """Test RequiredRule."""
        rule = RequiredRule()
        
        assert rule.validate("value") is True
        assert rule.validate(123) is True
        assert rule.validate([1, 2, 3]) is True
        assert rule.validate({"key": "value"}) is True
        
        assert rule.validate(None) is False
        assert rule.validate("") is False
        assert rule.validate([]) is False
        assert rule.validate({}) is False
    
    def test_type_rule(self):
        """Test TypeRule."""
        # String type
        rule = TypeRule(str)
        assert rule.validate("string") is True
        assert rule.validate(123) is False
        
        # Integer type
        rule = TypeRule(int)
        assert rule.validate(123) is True
        assert rule.validate("123") is False
        
        # List type
        rule = TypeRule(list)
        assert rule.validate([1, 2, 3]) is True
        assert rule.validate((1, 2, 3)) is False
    
    def test_range_rule(self):
        """Test RangeRule."""
        # Min and max
        rule = RangeRule(min_value=0, max_value=100)
        assert rule.validate(50) is True
        assert rule.validate(0) is True
        assert rule.validate(100) is True
        assert rule.validate(-1) is False
        assert rule.validate(101) is False
        assert rule.validate("50") is False  # Not numeric
        
        # Min only
        rule = RangeRule(min_value=10)
        assert rule.validate(20) is True
        assert rule.validate(10) is True
        assert rule.validate(9) is False
        
        # Max only
        rule = RangeRule(max_value=100)
        assert rule.validate(50) is True
        assert rule.validate(100) is True
        assert rule.validate(101) is False
    
    def test_length_rule(self):
        """Test LengthRule."""
        # Min and max length
        rule = LengthRule(min_length=3, max_length=10)
        assert rule.validate("hello") is True
        assert rule.validate("abc") is True
        assert rule.validate("1234567890") is True
        assert rule.validate("ab") is False
        assert rule.validate("12345678901") is False
        assert rule.validate(123) is False  # No length
        
        # Min length only
        rule = LengthRule(min_length=5)
        assert rule.validate("hello world") is True
        assert rule.validate("test") is False
        
        # Works with lists
        rule = LengthRule(max_length=3)
        assert rule.validate([1, 2, 3]) is True
        assert rule.validate([1, 2, 3, 4]) is False
    
    def test_pattern_rule(self):
        """Test PatternRule."""
        # Simple pattern
        rule = PatternRule(r'^\d{3}-\d{3}-\d{4}$', "Must be phone number")
        assert rule.validate("123-456-7890") is True
        assert rule.validate("1234567890") is False
        assert rule.validate(123) is False  # Not string
        
        # Version pattern
        rule = PatternRule(r'^\d+\.\d+\.\d+$')
        assert rule.validate("1.2.3") is True
        assert rule.validate("1.2.3-beta") is False
    
    def test_choice_rule(self):
        """Test ChoiceRule."""
        rule = ChoiceRule(["small", "medium", "large"])
        assert rule.validate("small") is True
        assert rule.validate("medium") is True
        assert rule.validate("extra-large") is False
        
        # Numeric choices
        rule = ChoiceRule([1, 2, 3])
        assert rule.validate(2) is True
        assert rule.validate(4) is False
    
    def test_path_rule(self):
        """Test PathRule."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Existing path
            rule = PathRule(must_exist=True)
            assert rule.validate(temp_path) is True
            assert rule.validate(temp_path / "non-existent") is False
            
            # Create if missing
            rule = PathRule(must_exist=True, create_if_missing=True)
            new_path = temp_path / "new_dir"
            assert rule.validate(str(new_path)) is True
            assert new_path.exists()
            
            # Any path (no existence check)
            rule = PathRule()
            assert rule.validate("/any/path") is True
            assert rule.validate(123) is False  # Not a path
    
    def test_url_rule(self):
        """Test URLRule."""
        rule = URLRule()
        
        # Valid URLs
        assert rule.validate("http://example.com") is True
        assert rule.validate("https://example.com") is True
        assert rule.validate("http://localhost:8080") is True
        assert rule.validate("https://api.example.com/v1/users") is True
        assert rule.validate("http://192.168.1.1") is True
        
        # Invalid URLs
        assert rule.validate("example.com") is False  # No protocol
        assert rule.validate("ftp://example.com") is False  # Wrong protocol
        assert rule.validate("not a url") is False
        assert rule.validate(123) is False  # Not string
    
    def test_email_rule(self):
        """Test EmailRule."""
        rule = EmailRule()
        
        # Valid emails
        assert rule.validate("user@example.com") is True
        assert rule.validate("john.doe@company.org") is True
        assert rule.validate("test+tag@domain.co.uk") is True
        
        # Invalid emails
        assert rule.validate("not-an-email") is False
        assert rule.validate("@example.com") is False
        assert rule.validate("user@") is False
        assert rule.validate(123) is False  # Not string
    
    def test_custom_rule(self):
        """Test CustomRule."""
        # Even number validator
        def is_even(value):
            return isinstance(value, int) and value % 2 == 0
        
        rule = CustomRule(is_even, "Must be even number")
        assert rule.validate(2) is True
        assert rule.validate(4) is True
        assert rule.validate(3) is False
        assert rule.validate("4") is False  # Not int
        
        # Rule with exception handling
        def failing_validator(value):
            raise ValueError("Always fails")
        
        rule = CustomRule(failing_validator, "Will fail")
        assert rule.validate("anything") is False  # Exception caught
    
    def test_error_messages(self):
        """Test error message formatting."""
        rule = RequiredRule()
        message = rule.get_error_message("username", None)
        assert "username" in message
        assert "required" in message.lower()
        
        rule = RangeRule(min_value=0, max_value=10)
        message = rule.get_error_message("age", -5)
        assert "age" in message
        assert "between 0 and 10" in message
        assert "got: -5" in message


class TestConfigValidator:
    """Test ConfigValidator class."""
    
    def test_add_rules(self):
        """Test adding validation rules."""
        validator = ConfigValidator()
        
        validator.add_rule("username", RequiredRule())
        validator.add_rule("username", LengthRule(min_length=3))
        
        assert "username" in validator.rules
        assert len(validator.rules["username"]) == 2
        
        # Add multiple rules at once
        validator.add_rules("email", [
            RequiredRule(),
            EmailRule()
        ])
        assert len(validator.rules["email"]) == 2
    
    def test_validate_field(self):
        """Test single field validation."""
        validator = ConfigValidator()
        validator.add_rule("age", RangeRule(min_value=0, max_value=120))
        
        # Valid value
        errors = validator.validate_field("age", 25)
        assert len(errors) == 0
        
        # Invalid value
        errors = validator.validate_field("age", 150)
        assert len(errors) == 1
        assert "between 0 and 120" in errors[0]
        
        # Non-existent field
        errors = validator.validate_field("unknown", "value")
        assert len(errors) == 0  # No rules, no errors
    
    def test_validate_config(self):
        """Test full configuration validation."""
        validator = ConfigValidator()
        
        # Add field rules
        validator.add_rule("username", RequiredRule())
        validator.add_rule("username", LengthRule(min_length=3))
        validator.add_rule("email", EmailRule())
        validator.add_rule("age", RangeRule(min_value=18))
        
        # Valid config
        config = {
            "username": "johndoe",
            "email": "john@example.com",
            "age": 25
        }
        errors = validator.validate(config)
        assert len(errors) == 0
        
        # Invalid config
        config = {
            "username": "jd",  # Too short
            "email": "invalid-email",
            "age": 16  # Too young
        }
        errors = validator.validate(config)
        assert len(errors) == 3
    
    def test_cross_field_validation(self):
        """Test cross-field validation rules."""
        validator = ConfigValidator()
        
        # Add cross-field rule
        def password_match(config):
            errors = []
            if config.get("password") != config.get("password_confirm"):
                errors.append("Passwords do not match")
            return errors
        
        validator.add_cross_field_rule(password_match)
        
        # Matching passwords
        config = {
            "password": "secret123",
            "password_confirm": "secret123"
        }
        errors = validator.validate(config)
        assert len(errors) == 0
        
        # Non-matching passwords
        config = {
            "password": "secret123",
            "password_confirm": "secret456"
        }
        errors = validator.validate(config)
        assert len(errors) == 1
        assert "Passwords do not match" in errors[0]
    
    def test_cross_field_exception_handling(self):
        """Test exception handling in cross-field rules."""
        validator = ConfigValidator()
        
        def failing_rule(config):
            raise RuntimeError("Rule failed")
        
        validator.add_cross_field_rule(failing_rule)
        
        errors = validator.validate({})
        assert len(errors) == 1
        assert "Cross-field validation error" in errors[0]


class TestValidationDecorators:
    """Test validation decorators."""
    
    def test_validate_field_decorator(self):
        """Test field validation decorator."""
        @validate_field(RequiredRule(), LengthRule(min_length=3))
        def username_field():
            pass
        
        assert hasattr(username_field, '_validation_rules')
        assert len(username_field._validation_rules) == 2
    
    def test_validate_config_decorator(self):
        """Test configuration validation decorator."""
        validator = ConfigValidator()
        validator.add_rule("name", RequiredRule())
        
        class TestConfig:
            def __init__(self):
                self.name = None
            
            def to_dict(self):
                return {"name": self.name}
            
            @validate_config(validator)
            def save(self):
                return True
        
        config = TestConfig()
        
        # Should raise validation error
        with pytest.raises(ValidationError) as exc:
            config.save()
        
        assert "validation failed" in str(exc.value)
        
        # Valid config should work
        config.name = "Test"
        assert config.save() is True


class TestDefaultValidator:
    """Test default validator creation."""
    
    def test_create_default_validator(self):
        """Test creating default validator for ApplicationConfig."""
        validator = create_default_validator()
        
        # Check some expected rules
        assert "app_name" in validator.rules
        assert "version" in validator.rules
        assert "environment" in validator.rules
        
        # Test version validation
        config = {"version": "1.2.3"}
        errors = validator.validate_field("version", config["version"])
        assert len(errors) == 0
        
        config = {"version": "invalid"}
        errors = validator.validate_field("version", config["version"])
        assert len(errors) > 0
        
        # Test cross-field validation
        config = {
            "database": {
                "type": "postgresql",
                "user": None,
                "password": None
            }
        }
        errors = validator.validate(config)
        assert any("user required" in err for err in errors)
        assert any("password required" in err for err in errors)