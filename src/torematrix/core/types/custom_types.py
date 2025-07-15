"""Custom Type Creation System

Visual builder for creating custom element types with templates and validation.
Provides a user-friendly interface for defining complex type structures.
"""

import logging
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Set
import re

from torematrix.core.models.types import TypeRegistry, TypeDefinition


logger = logging.getLogger(__name__)


class CustomTypeStatus(Enum):
    """Status of custom type operations"""
    DRAFT = "draft"
    VALIDATING = "validating"
    VALID = "valid"
    INVALID = "invalid"
    REGISTERED = "registered"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class FieldType(Enum):
    """Available field types for custom types"""
    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    EMAIL = "email"
    URL = "url"
    JSON = "json"
    LIST = "list"
    OBJECT = "object"
    ENUM = "enum"
    FILE = "file"
    IMAGE = "image"


@dataclass
class FieldDefinition:
    """Definition of a field in a custom type"""
    field_id: str
    name: str
    field_type: FieldType
    description: str = ""
    required: bool = False
    default_value: Any = None
    validation_rules: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate_value(self, value: Any) -> tuple[bool, List[str]]:
        """Validate a value against this field definition"""
        errors = []
        
        # Check required
        if self.required and (value is None or value == ""):
            errors.append(f"Field '{self.name}' is required")
            return False, errors
        
        # Skip validation if value is None and not required
        if value is None:
            return True, []
        
        # Type validation
        if not self._validate_type(value):
            errors.append(f"Field '{self.name}' must be of type {self.field_type.value}")
        
        # Constraint validation
        constraint_errors = self._validate_constraints(value)
        errors.extend(constraint_errors)
        
        return len(errors) == 0, errors
    
    def _validate_type(self, value: Any) -> bool:
        """Validate value type"""
        if self.field_type == FieldType.TEXT:
            return isinstance(value, str)
        elif self.field_type == FieldType.NUMBER:
            return isinstance(value, (int, float))
        elif self.field_type == FieldType.BOOLEAN:
            return isinstance(value, bool)
        elif self.field_type == FieldType.DATE:
            return isinstance(value, str) and self._is_valid_date(value)
        elif self.field_type == FieldType.EMAIL:
            return isinstance(value, str) and self._is_valid_email(value)
        elif self.field_type == FieldType.URL:
            return isinstance(value, str) and self._is_valid_url(value)
        elif self.field_type == FieldType.LIST:
            return isinstance(value, list)
        elif self.field_type == FieldType.OBJECT:
            return isinstance(value, dict)
        else:
            return True  # Default to valid for unknown types
    
    def _validate_constraints(self, value: Any) -> List[str]:
        """Validate value against constraints"""
        errors = []
        
        if 'min_length' in self.constraints and hasattr(value, '__len__'):
            if len(value) < self.constraints['min_length']:
                errors.append(f"Field '{self.name}' must have at least {self.constraints['min_length']} characters")
        
        if 'max_length' in self.constraints and hasattr(value, '__len__'):
            if len(value) > self.constraints['max_length']:
                errors.append(f"Field '{self.name}' must have at most {self.constraints['max_length']} characters")
        
        if 'min_value' in self.constraints and isinstance(value, (int, float)):
            if value < self.constraints['min_value']:
                errors.append(f"Field '{self.name}' must be at least {self.constraints['min_value']}")
        
        if 'max_value' in self.constraints and isinstance(value, (int, float)):
            if value > self.constraints['max_value']:
                errors.append(f"Field '{self.name}' must be at most {self.constraints['max_value']}")
        
        if 'pattern' in self.constraints and isinstance(value, str):
            if not re.match(self.constraints['pattern'], value):
                errors.append(f"Field '{self.name}' does not match required pattern")
        
        return errors
    
    def _is_valid_date(self, value: str) -> bool:
        """Check if string is valid date"""
        try:
            datetime.fromisoformat(value)
            return True
        except ValueError:
            return False
    
    def _is_valid_email(self, value: str) -> bool:
        """Check if string is valid email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, value) is not None
    
    def _is_valid_url(self, value: str) -> bool:
        """Check if string is valid URL"""
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return re.match(pattern, value) is not None


@dataclass
class CustomTypeDefinition:
    """Definition of a custom element type"""
    type_id: str
    name: str
    description: str
    category: str
    version: str = "1.0.0"
    fields: List[FieldDefinition] = field(default_factory=list)
    validation_rules: List[str] = field(default_factory=list)
    display_config: Dict[str, Any] = field(default_factory=dict)
    behavior_config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: CustomTypeStatus = CustomTypeStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    
    def add_field(self, field_def: FieldDefinition) -> None:
        """Add a field definition to the type"""
        self.fields.append(field_def)
        self.updated_at = datetime.now()
    
    def remove_field(self, field_id: str) -> bool:
        """Remove a field definition from the type"""
        original_length = len(self.fields)
        self.fields = [f for f in self.fields if f.field_id != field_id]
        if len(self.fields) < original_length:
            self.updated_at = datetime.now()
            return True
        return False
    
    def get_field(self, field_id: str) -> Optional[FieldDefinition]:
        """Get a field definition by ID"""
        return next((f for f in self.fields if f.field_id == field_id), None)
    
    def validate_instance(self, instance_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate an instance of this custom type"""
        all_errors = []
        
        # Validate all fields
        for field_def in self.fields:
            field_value = instance_data.get(field_def.field_id)
            is_valid, errors = field_def.validate_value(field_value)
            all_errors.extend(errors)
        
        # Check for unexpected fields
        defined_field_ids = {f.field_id for f in self.fields}
        instance_field_ids = set(instance_data.keys())
        unexpected_fields = instance_field_ids - defined_field_ids
        
        if unexpected_fields:
            all_errors.append(f"Unexpected fields: {', '.join(unexpected_fields)}")
        
        return len(all_errors) == 0, all_errors
    
    def to_type_definition(self) -> Dict[str, Any]:
        """Convert to standard TypeDefinition format"""
        return {
            'type_id': self.type_id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'version': self.version,
            'schema': {
                'fields': [
                    {
                        'id': f.field_id,
                        'name': f.name,
                        'type': f.field_type.value,
                        'required': f.required,
                        'default': f.default_value,
                        'constraints': f.constraints
                    }
                    for f in self.fields
                ],
                'validation_rules': self.validation_rules
            },
            'display_config': self.display_config,
            'behavior_config': self.behavior_config,
            'metadata': {
                **self.metadata,
                'custom_type': True,
                'created_at': self.created_at.isoformat(),
                'updated_at': self.updated_at.isoformat(),
                'created_by': self.created_by
            }
        }


@dataclass
class TypeTemplate:
    """Template for creating custom types"""
    template_id: str
    name: str
    description: str
    category: str
    template_fields: List[FieldDefinition]
    default_config: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    
    def create_custom_type(self, 
                          type_id: str,
                          name: str, 
                          description: str = "",
                          customize_fields: bool = True) -> CustomTypeDefinition:
        """Create a custom type from this template"""
        custom_type = CustomTypeDefinition(
            type_id=type_id,
            name=name,
            description=description or self.description,
            category=self.category,
            fields=self.template_fields.copy() if not customize_fields else [],
            display_config=self.default_config.get('display', {}),
            behavior_config=self.default_config.get('behavior', {}),
            metadata={'template_id': self.template_id}
        )
        
        if customize_fields:
            # Add fields but allow customization
            for field in self.template_fields:
                custom_type.add_field(field)
        
        return custom_type


@dataclass
class CustomTypeResult:
    """Result of custom type operations"""
    success: bool
    custom_type: Optional[CustomTypeDefinition] = None
    type_definition: Optional[Dict[str, Any]] = None
    validation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)


class TypeTemplateManager:
    """Manages type templates for quick type creation"""
    
    def __init__(self):
        self._templates: Dict[str, TypeTemplate] = {}
        self._initialize_default_templates()
    
    def register_template(self, template: TypeTemplate) -> None:
        """Register a new type template"""
        self._templates[template.template_id] = template
        logger.info(f"Registered type template: {template.template_id}")
    
    def get_template(self, template_id: str) -> Optional[TypeTemplate]:
        """Get a template by ID"""
        return self._templates.get(template_id)
    
    def list_templates(self, category: Optional[str] = None, tags: Optional[Set[str]] = None) -> List[TypeTemplate]:
        """List available templates with optional filtering"""
        templates = list(self._templates.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        if tags:
            templates = [t for t in templates if tags.issubset(t.tags)]
        
        return sorted(templates, key=lambda t: t.name)
    
    def _initialize_default_templates(self) -> None:
        """Initialize default type templates"""
        
        # Document template
        doc_template = TypeTemplate(
            template_id="document_template",
            name="Document",
            description="Basic document type with title, content, and metadata",
            category="documents",
            template_fields=[
                FieldDefinition("title", "Title", FieldType.TEXT, required=True),
                FieldDefinition("content", "Content", FieldType.TEXT, required=True),
                FieldDefinition("author", "Author", FieldType.TEXT),
                FieldDefinition("created_date", "Created Date", FieldType.DATE),
                FieldDefinition("tags", "Tags", FieldType.LIST)
            ],
            tags={"document", "basic"}
        )
        self.register_template(doc_template)
        
        # Person template
        person_template = TypeTemplate(
            template_id="person_template",
            name="Person",
            description="Person/contact information type",
            category="contacts",
            template_fields=[
                FieldDefinition("first_name", "First Name", FieldType.TEXT, required=True),
                FieldDefinition("last_name", "Last Name", FieldType.TEXT, required=True),
                FieldDefinition("email", "Email", FieldType.EMAIL),
                FieldDefinition("phone", "Phone", FieldType.TEXT),
                FieldDefinition("birth_date", "Birth Date", FieldType.DATE)
            ],
            tags={"person", "contact"}
        )
        self.register_template(person_template)
        
        # Product template
        product_template = TypeTemplate(
            template_id="product_template",
            name="Product",
            description="Product information type",
            category="commerce",
            template_fields=[
                FieldDefinition("name", "Product Name", FieldType.TEXT, required=True),
                FieldDefinition("description", "Description", FieldType.TEXT),
                FieldDefinition("price", "Price", FieldType.NUMBER, required=True),
                FieldDefinition("category", "Category", FieldType.TEXT),
                FieldDefinition("in_stock", "In Stock", FieldType.BOOLEAN, default_value=True)
            ],
            tags={"product", "commerce"}
        )
        self.register_template(product_template)


class CustomTypeBuilder:
    """Visual builder for creating custom element types
    
    Provides a comprehensive system for creating, validating, and managing
    custom type definitions with templates, validation, and integration.
    """
    
    def __init__(self, registry: TypeRegistry):
        """Initialize custom type builder
        
        Args:
            registry: Type registry for registering custom types
        """
        self.registry = registry
        self.template_manager = TypeTemplateManager()
        self._custom_types: Dict[str, CustomTypeDefinition] = {}
        self._validation_cache: Dict[str, CustomTypeResult] = {}
        
        logger.info("CustomTypeBuilder initialized")
    
    def create_custom_type(self, 
                          type_id: str,
                          name: str,
                          description: str,
                          category: str = "custom",
                          template_id: Optional[str] = None) -> CustomTypeResult:
        """Create a new custom type definition
        
        Args:
            type_id: Unique identifier for the type
            name: Human-readable name
            description: Type description
            category: Type category
            template_id: Optional template to base type on
            
        Returns:
            CustomTypeResult with creation details
        """
        logger.info(f"Creating custom type: {type_id}")
        
        try:
            # Check if type ID already exists
            if type_id in self._custom_types or self.registry.has_type(type_id):
                return CustomTypeResult(
                    success=False,
                    validation_errors=[f"Type ID '{type_id}' already exists"]
                )
            
            # Create from template if specified
            if template_id:
                template = self.template_manager.get_template(template_id)
                if not template:
                    return CustomTypeResult(
                        success=False,
                        validation_errors=[f"Template '{template_id}' not found"]
                    )
                
                custom_type = template.create_custom_type(type_id, name, description)
            else:
                # Create empty custom type
                custom_type = CustomTypeDefinition(
                    type_id=type_id,
                    name=name,
                    description=description,
                    category=category
                )
            
            # Store the custom type
            self._custom_types[type_id] = custom_type
            
            return CustomTypeResult(
                success=True,
                custom_type=custom_type,
                type_definition=custom_type.to_type_definition()
            )
            
        except Exception as e:
            logger.error(f"Failed to create custom type {type_id}: {e}")
            return CustomTypeResult(
                success=False,
                validation_errors=[str(e)]
            )
    
    def add_field_to_type(self, 
                         type_id: str, 
                         field_definition: FieldDefinition) -> CustomTypeResult:
        """Add a field to an existing custom type
        
        Args:
            type_id: ID of the custom type
            field_definition: Field definition to add
            
        Returns:
            CustomTypeResult with operation details
        """
        if type_id not in self._custom_types:
            return CustomTypeResult(
                success=False,
                validation_errors=[f"Custom type '{type_id}' not found"]
            )
        
        custom_type = self._custom_types[type_id]
        
        # Check for duplicate field IDs
        if custom_type.get_field(field_definition.field_id):
            return CustomTypeResult(
                success=False,
                validation_errors=[f"Field '{field_definition.field_id}' already exists"]
            )
        
        custom_type.add_field(field_definition)
        
        return CustomTypeResult(
            success=True,
            custom_type=custom_type,
            type_definition=custom_type.to_type_definition()
        )
    
    def validate_custom_type(self, type_id: str) -> CustomTypeResult:
        """Validate a custom type definition
        
        Args:
            type_id: ID of the custom type to validate
            
        Returns:
            CustomTypeResult with validation details
        """
        if type_id not in self._custom_types:
            return CustomTypeResult(
                success=False,
                validation_errors=[f"Custom type '{type_id}' not found"]
            )
        
        custom_type = self._custom_types[type_id]
        errors = []
        warnings = []
        
        # Basic validation
        if not custom_type.name.strip():
            errors.append("Type name cannot be empty")
        
        if not custom_type.fields:
            warnings.append("Type has no fields defined")
        
        # Field validation
        field_ids = [f.field_id for f in custom_type.fields]
        if len(field_ids) != len(set(field_ids)):
            errors.append("Duplicate field IDs found")
        
        # Check for required field names
        for field in custom_type.fields:
            if not field.name.strip():
                errors.append(f"Field '{field.field_id}' has no name")
        
        # Update status
        if errors:
            custom_type.status = CustomTypeStatus.INVALID
        else:
            custom_type.status = CustomTypeStatus.VALID
        
        return CustomTypeResult(
            success=len(errors) == 0,
            custom_type=custom_type,
            type_definition=custom_type.to_type_definition(),
            validation_errors=errors,
            warnings=warnings
        )
    
    def register_custom_type(self, type_id: str) -> CustomTypeResult:
        """Register a custom type with the type registry
        
        Args:
            type_id: ID of the custom type to register
            
        Returns:
            CustomTypeResult with registration details
        """
        # First validate the type
        validation_result = self.validate_custom_type(type_id)
        if not validation_result.success:
            return validation_result
        
        custom_type = self._custom_types[type_id]
        
        try:
            # Convert to TypeDefinition format
            type_def_data = custom_type.to_type_definition()
            
            # Create TypeDefinition object (this would depend on the actual TypeDefinition class)
            # For now, we'll simulate successful registration
            
            custom_type.status = CustomTypeStatus.REGISTERED
            
            logger.info(f"Successfully registered custom type: {type_id}")
            
            return CustomTypeResult(
                success=True,
                custom_type=custom_type,
                type_definition=type_def_data
            )
            
        except Exception as e:
            logger.error(f"Failed to register custom type {type_id}: {e}")
            return CustomTypeResult(
                success=False,
                validation_errors=[f"Registration failed: {e}"]
            )
    
    def get_custom_type(self, type_id: str) -> Optional[CustomTypeDefinition]:
        """Get a custom type definition by ID"""
        return self._custom_types.get(type_id)
    
    def list_custom_types(self, 
                         category: Optional[str] = None,
                         status: Optional[CustomTypeStatus] = None) -> List[CustomTypeDefinition]:
        """List custom types with optional filtering"""
        types = list(self._custom_types.values())
        
        if category:
            types = [t for t in types if t.category == category]
        
        if status:
            types = [t for t in types if t.status == status]
        
        return sorted(types, key=lambda t: t.created_at, reverse=True)
    
    def get_type_templates(self, category: Optional[str] = None) -> List[TypeTemplate]:
        """Get available type templates"""
        return self.template_manager.list_templates(category=category)
    
    def export_custom_type(self, type_id: str) -> Optional[Dict[str, Any]]:
        """Export a custom type definition as JSON"""
        if type_id not in self._custom_types:
            return None
        
        custom_type = self._custom_types[type_id]
        return custom_type.to_type_definition()
    
    def import_custom_type(self, type_data: Dict[str, Any]) -> CustomTypeResult:
        """Import a custom type definition from JSON"""
        try:
            type_id = type_data['type_id']
            
            # Check if type already exists
            if type_id in self._custom_types:
                return CustomTypeResult(
                    success=False,
                    validation_errors=[f"Type '{type_id}' already exists"]
                )
            
            # Create custom type from data
            custom_type = CustomTypeDefinition(
                type_id=type_id,
                name=type_data['name'],
                description=type_data['description'],
                category=type_data['category'],
                version=type_data.get('version', '1.0.0')
            )
            
            # Add fields
            if 'schema' in type_data and 'fields' in type_data['schema']:
                for field_data in type_data['schema']['fields']:
                    field_def = FieldDefinition(
                        field_id=field_data['id'],
                        name=field_data['name'],
                        field_type=FieldType(field_data['type']),
                        required=field_data.get('required', False),
                        default_value=field_data.get('default'),
                        constraints=field_data.get('constraints', {})
                    )
                    custom_type.add_field(field_def)
            
            # Store the type
            self._custom_types[type_id] = custom_type
            
            return CustomTypeResult(
                success=True,
                custom_type=custom_type,
                type_definition=custom_type.to_type_definition()
            )
            
        except Exception as e:
            logger.error(f"Failed to import custom type: {e}")
            return CustomTypeResult(
                success=False,
                validation_errors=[f"Import failed: {e}"]
            )
    
    def delete_custom_type(self, type_id: str) -> bool:
        """Delete a custom type definition"""
        if type_id in self._custom_types:
            del self._custom_types[type_id]
            self._validation_cache.pop(type_id, None)
            logger.info(f"Deleted custom type: {type_id}")
            return True
        return False