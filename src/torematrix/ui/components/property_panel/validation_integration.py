"""Validation Integration Example

Example showing how to integrate the validation framework with property editors
and the property panel. Demonstrates real-time validation, visual feedback,
and rule-based validation in practice.
"""

from typing import Dict, Any, Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QLabel
from PyQt6.QtCore import pyqtSignal

from .validators import ValidationEngine, ValidationResult, RequiredValidator, LengthValidator
from .validation_ui import ValidationIndicatorWidget, ValidationSummaryWidget
from .rules import RuleBuilder, RuleOperator, ValidationSeverity, BusinessRuleValidator


class ValidatedPropertyEditor(QWidget):
    """Example property editor with integrated validation"""
    
    value_changed = pyqtSignal(str, object)  # field_name, value
    validation_changed = pyqtSignal(str, ValidationResult)  # field_name, result
    
    def __init__(self, field_name: str, field_type: str = "string", parent=None):
        super().__init__(parent)
        
        self.field_name = field_name
        self.field_type = field_type
        
        # Validation engine
        self.validation_engine = ValidationEngine()
        self.setup_validation()
        
        # UI setup
        self.setup_ui()
        self.setup_connections()
    
    def setup_validation(self):
        """Setup field-specific validation"""
        # Add basic validators based on field type
        if self.field_type == "string":
            self.validation_engine.add_field_validator(self.field_name, "string_type")
        elif self.field_type == "required_string":
            self.validation_engine.add_field_validator(self.field_name, "required")
            self.validation_engine.add_field_validator(self.field_name, "string_type")
        
        # Example: Add length validation for name fields
        if "name" in self.field_name.lower():
            length_validator = LengthValidator(min_length=2, max_length=50)
            self.validation_engine.register_validator("name_length", length_validator)
            self.validation_engine.add_field_validator(self.field_name, "name_length")
        
        # Example: Add business rule for email fields
        if "email" in self.field_name.lower():
            email_rule = (RuleBuilder()
                         .name("Email Format")
                         .when("value", RuleOperator.MATCHES_REGEX, r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
                         .message("Please enter a valid email address")
                         .suggestion("Use format: user@domain.com")
                         .severity(ValidationSeverity.ERROR)
                         .build())
            
            email_validator = BusinessRuleValidator([email_rule])
            self.validation_engine.register_validator("email_format", email_validator)
            self.validation_engine.add_field_validator(self.field_name, "email_format")
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        
        # Field label
        self.label = QLabel(self.field_name.replace("_", " ").title())
        layout.addWidget(self.label)
        
        # Input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(f"Enter {self.field_name}")
        layout.addWidget(self.input_field)
        
        # Validation indicator
        self.validation_indicator = ValidationIndicatorWidget()
        layout.addWidget(self.validation_indicator)
    
    def setup_connections(self):
        """Setup signal connections"""
        # Connect input changes to validation
        self.input_field.textChanged.connect(self._on_value_changed)
        
        # Connect validation results
        self.validation_engine.validation_completed.connect(self._on_validation_completed)
        self.validation_engine.validation_started.connect(self._on_validation_started)
        
        # Connect validation indicator
        self.validation_indicator.details_requested.connect(self._show_validation_details)
    
    def _on_value_changed(self, text: str):
        """Handle input value change"""
        # Emit value change
        self.value_changed.emit(self.field_name, text)
        
        # Trigger async validation with debouncing
        context = {
            'field_name': self.field_name,
            'field_type': self.field_type,
            'element_type': 'example'
        }
        
        self.validation_engine.validate_field_async(self.field_name, text, context)
    
    def _on_validation_started(self, field_name: str):
        """Handle validation start"""
        if field_name == self.field_name:
            self.validation_indicator.set_validating(True)
    
    def _on_validation_completed(self, field_name: str, result: ValidationResult):
        """Handle validation completion"""
        if field_name == self.field_name:
            self.validation_indicator.set_validation_result(result)
            self.validation_changed.emit(field_name, result)
    
    def _show_validation_details(self, result: ValidationResult):
        """Show detailed validation results"""
        from .validation_ui import ValidationDetailsDialog
        dialog = ValidationDetailsDialog(result, self)
        dialog.exec()
    
    def set_value(self, value: Any):
        """Set editor value"""
        self.input_field.setText(str(value) if value is not None else "")
    
    def get_value(self) -> str:
        """Get editor value"""
        return self.input_field.text()


class PropertyValidationManager:
    """Manager for property validation across the property panel"""
    
    def __init__(self):
        self.validation_engine = ValidationEngine()
        self.field_results: Dict[str, ValidationResult] = {}
        self.summary_widget: Optional[ValidationSummaryWidget] = None
        
        # Setup common validation rules
        self.setup_common_rules()
    
    def setup_common_rules(self):
        """Setup common validation rules"""
        # Example: Coordinate validation rule
        coordinate_rule = (RuleBuilder()
                          .name("Valid Coordinate")
                          .when("value", RuleOperator.GREATER_EQUAL, 0.0)
                          .message("Coordinates must be non-negative")
                          .for_fields("x", "y", "width", "height")
                          .severity(ValidationSeverity.ERROR)
                          .build())
        
        # Example: Text length rule
        text_length_rule = (RuleBuilder()
                           .name("Reasonable Text Length")
                           .when("value", RuleOperator.LESS_THAN, 1000)
                           .message("Text is very long - consider breaking it up")
                           .for_fields("text", "content", "description")
                           .severity(ValidationSeverity.WARNING)
                           .build())
        
        # Register business rule validator
        business_rules = BusinessRuleValidator([coordinate_rule, text_length_rule])
        self.validation_engine.register_validator("business_rules", business_rules)
        self.validation_engine.add_global_validator("business_rules")
    
    def set_summary_widget(self, widget: ValidationSummaryWidget):
        """Set the summary widget for overall validation status"""
        self.summary_widget = widget
    
    def validate_field(self, field_name: str, value: Any, context: Dict[str, Any] = None) -> ValidationResult:
        """Validate a field and update summary"""
        result = self.validation_engine.validate_field(field_name, value, context)
        
        # Store result
        self.field_results[field_name] = result
        
        # Update summary widget
        if self.summary_widget:
            self.summary_widget.set_field_result(field_name, result)
        
        return result
    
    def validate_all_fields(self, field_values: Dict[str, Any], context: Dict[str, Any] = None) -> ValidationResult:
        """Validate all fields and return combined result"""
        combined_result = ValidationResult(is_valid=True)
        
        for field_name, value in field_values.items():
            field_context = context.copy() if context else {}
            field_context['field_name'] = field_name
            
            result = self.validate_field(field_name, value, field_context)
            
            # Merge results
            combined_result.is_valid = combined_result.is_valid and result.is_valid
            for message in result.messages:
                combined_result.add_message(message)
        
        return combined_result
    
    def add_custom_validator(self, name: str, validator, fields: Optional[list] = None):
        """Add a custom validator"""
        self.validation_engine.register_validator(name, validator)
        
        if fields:
            for field in fields:
                self.validation_engine.add_field_validator(field, name)
        else:
            self.validation_engine.add_global_validator(name)
    
    def get_field_validation_status(self, field_name: str) -> Optional[ValidationResult]:
        """Get validation status for a specific field"""
        return self.field_results.get(field_name)
    
    def get_overall_validation_status(self) -> Dict[str, Any]:
        """Get overall validation status summary"""
        total_fields = len(self.field_results)
        valid_fields = sum(1 for result in self.field_results.values() if result.is_valid)
        total_errors = sum(result.get_error_count() for result in self.field_results.values())
        total_warnings = sum(result.get_warning_count() for result in self.field_results.values())
        
        return {
            'total_fields': total_fields,
            'valid_fields': valid_fields,
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'overall_valid': total_errors == 0
        }


# Example usage functions

def create_example_property_form() -> QWidget:
    """Create an example property form with validation"""
    from PyQt6.QtWidgets import QWidget, QVBoxLayout
    
    widget = QWidget()
    layout = QVBoxLayout(widget)
    
    # Create validation manager
    validation_manager = PropertyValidationManager()
    
    # Create summary widget
    summary_widget = ValidationSummaryWidget()
    validation_manager.set_summary_widget(summary_widget)
    layout.addWidget(summary_widget)
    
    # Create property editors
    name_editor = ValidatedPropertyEditor("name", "required_string")
    email_editor = ValidatedPropertyEditor("email", "string")
    x_editor = ValidatedPropertyEditor("x", "number")
    
    layout.addWidget(name_editor)
    layout.addWidget(email_editor)
    layout.addWidget(x_editor)
    
    # Connect to validation manager
    def on_field_validation(field_name: str, result: ValidationResult):
        validation_manager.field_results[field_name] = result
        summary_widget.set_field_result(field_name, result)
    
    name_editor.validation_changed.connect(on_field_validation)
    email_editor.validation_changed.connect(on_field_validation)
    x_editor.validation_changed.connect(on_field_validation)
    
    return widget


def create_validation_rules_example():
    """Example of creating custom validation rules"""
    # Create a rule builder
    builder = RuleBuilder()
    
    # Build a complex validation rule
    password_rule = (builder
                    .name("Strong Password")
                    .description("Password must meet security requirements")
                    .when("value", RuleOperator.GREATER_EQUAL, 8)  # Length check
                    .message("Password must be at least 8 characters long")
                    .severity(ValidationSeverity.ERROR)
                    .for_fields("password", "new_password")
                    .build())
    
    # Create another rule using different conditions  
    email_domain_rule = (RuleBuilder()
                        .name("Company Email")
                        .when("value", RuleOperator.ENDS_WITH, "@company.com")
                        .message("Must use company email address")
                        .severity(ValidationSeverity.WARNING)
                        .for_fields("email", "contact_email")
                        .build())
    
    return [password_rule, email_domain_rule]


if __name__ == "__main__":
    """Example usage demonstration"""
    print("Validation Framework Integration Example")
    print("=====================================")
    
    # Test validation engine
    engine = ValidationEngine()
    
    # Test basic validation
    result = engine.validate_field("test_field", "test_value")
    print(f"Basic validation result: {result.is_valid}")
    
    # Test rule creation
    rules = create_validation_rules_example()
    print(f"Created {len(rules)} validation rules")
    
    # Test business rule validator
    validator = BusinessRuleValidator(rules)
    context = {"field_name": "password", "element_type": "user"}
    result = validator.validate("short", context)
    print(f"Password validation result: {result.is_valid}")
    if not result.is_valid:
        print(f"Error: {result.messages[0].message}")
    
    print("\n✅ Validation framework integration example completed successfully!")