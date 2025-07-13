"""
Version tracking and migration support module.

This module provides version tracking for element models, migration
utilities, and compatibility management across different versions.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
from enum import Enum
import json

from .element import Element


class ModelVersion(Enum):
    """Supported model versions"""
    V1_0 = "1.0"
    V2_0 = "2.0"
    V3_0 = "3.0"
    CURRENT = "3.0"


class MigrationType(Enum):
    """Types of migration operations"""
    FORWARD = "forward"      # Upgrade to newer version
    BACKWARD = "backward"    # Downgrade to older version
    LATERAL = "lateral"      # Same version, different format


@dataclass(frozen=True)
class VersionInfo:
    """
    Version information for tracking element model versions.
    
    Provides metadata about model version, creation time,
    and migration history.
    """
    version: ModelVersion
    created_at: datetime
    schema_hash: Optional[str] = None
    migration_history: List[str] = field(default_factory=list)
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize version info to dictionary"""
        return {
            'version': self.version.value,
            'created_at': self.created_at.isoformat(),
            'schema_hash': self.schema_hash,
            'migration_history': self.migration_history,
            'custom_metadata': self.custom_metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VersionInfo':
        """Deserialize version info from dictionary"""
        return cls(
            version=ModelVersion(data['version']),
            created_at=datetime.fromisoformat(data['created_at']),
            schema_hash=data.get('schema_hash'),
            migration_history=data.get('migration_history', []),
            custom_metadata=data.get('custom_metadata', {})
        )
    
    def add_migration_record(self, migration_info: str) -> 'VersionInfo':
        """Add migration record to history"""
        new_history = self.migration_history + [migration_info]
        return VersionInfo(
            version=self.version,
            created_at=self.created_at,
            schema_hash=self.schema_hash,
            migration_history=new_history,
            custom_metadata=self.custom_metadata
        )


@dataclass(frozen=True)
class MigrationStep:
    """
    Represents a single migration step.
    
    Defines how to transform data from one version to another
    with validation and rollback support.
    """
    from_version: ModelVersion
    to_version: ModelVersion
    migration_type: MigrationType
    description: str
    transform_function: str  # Name of transformation function
    validation_rules: List[str] = field(default_factory=list)
    rollback_function: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize migration step to dictionary"""
        return {
            'from_version': self.from_version.value,
            'to_version': self.to_version.value,
            'migration_type': self.migration_type.value,
            'description': self.description,
            'transform_function': self.transform_function,
            'validation_rules': self.validation_rules,
            'rollback_function': self.rollback_function
        }


class VersionManager:
    """
    Manages version tracking and migration operations.
    
    Provides centralized version management for element models
    with migration support and compatibility checking.
    """
    
    # Version compatibility matrix
    COMPATIBILITY_MATRIX = {
        ModelVersion.V1_0: [ModelVersion.V2_0, ModelVersion.V3_0],
        ModelVersion.V2_0: [ModelVersion.V1_0, ModelVersion.V3_0],
        ModelVersion.V3_0: [ModelVersion.V1_0, ModelVersion.V2_0]
    }
    
    def __init__(self):
        self.migration_steps: List[MigrationStep] = []
        self._register_default_migrations()
    
    def _register_default_migrations(self) -> None:
        """Register default migration steps"""
        # V1 to V3 migration
        self.migration_steps.append(MigrationStep(
            from_version=ModelVersion.V1_0,
            to_version=ModelVersion.V3_0,
            migration_type=MigrationType.FORWARD,
            description="Migrate V1 .tore format to V3 unified model",
            transform_function="migrate_v1_to_v3",
            validation_rules=["validate_element_types", "validate_metadata"],
            rollback_function="migrate_v3_to_v1"
        ))
        
        # V3 to V1 migration
        self.migration_steps.append(MigrationStep(
            from_version=ModelVersion.V3_0,
            to_version=ModelVersion.V1_0,
            migration_type=MigrationType.BACKWARD,
            description="Convert V3 unified model to V1 .tore format",
            transform_function="migrate_v3_to_v1",
            validation_rules=["validate_v1_compatibility"],
            rollback_function="migrate_v1_to_v3"
        ))
    
    def get_current_version(self) -> ModelVersion:
        """Get current model version"""
        return ModelVersion.CURRENT
    
    def is_compatible(self, version1: ModelVersion, version2: ModelVersion) -> bool:
        """Check if two versions are compatible"""
        if version1 == version2:
            return True
        
        return version2 in self.COMPATIBILITY_MATRIX.get(version1, [])
    
    def get_migration_path(
        self, 
        from_version: ModelVersion, 
        to_version: ModelVersion
    ) -> List[MigrationStep]:
        """
        Get migration path between two versions.
        
        Args:
            from_version: Source version
            to_version: Target version
            
        Returns:
            List of migration steps to perform
            
        Raises:
            ValueError: If no migration path exists
        """
        if from_version == to_version:
            return []
        
        # Direct migration
        for step in self.migration_steps:
            if step.from_version == from_version and step.to_version == to_version:
                return [step]
        
        # Multi-step migration (simplified for now)
        # In a real implementation, you'd use a graph algorithm
        raise ValueError(f"No migration path from {from_version.value} to {to_version.value}")
    
    def create_version_info(
        self, 
        version: Optional[ModelVersion] = None,
        custom_metadata: Optional[Dict[str, Any]] = None
    ) -> VersionInfo:
        """Create version info for current data"""
        return VersionInfo(
            version=version or self.get_current_version(),
            created_at=datetime.now(),
            schema_hash=self._generate_schema_hash(),
            custom_metadata=custom_metadata or {}
        )
    
    def _generate_schema_hash(self) -> str:
        """Generate hash of current schema for validation"""
        # Simplified schema hash - in practice, this would be more sophisticated
        import hashlib
        schema_info = {
            'version': ModelVersion.CURRENT.value,
            'element_fields': ['element_id', 'element_type', 'text', 'metadata', 'parent_id'],
            'metadata_fields': ['coordinates', 'confidence', 'detection_method', 'page_number', 'languages']
        }
        return hashlib.md5(json.dumps(schema_info, sort_keys=True).encode()).hexdigest()
    
    def validate_version(self, version_info: VersionInfo) -> List[str]:
        """
        Validate version compatibility and integrity.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check version compatibility
        current_version = self.get_current_version()
        if not self.is_compatible(version_info.version, current_version):
            errors.append(f"Version {version_info.version.value} is not compatible with current version {current_version.value}")
        
        # Check schema hash if available
        if version_info.schema_hash and version_info.version == current_version:
            current_hash = self._generate_schema_hash()
            if version_info.schema_hash != current_hash:
                errors.append("Schema hash mismatch - possible version corruption")
        
        return errors


class MigrationEngine:
    """
    Engine for executing data migrations.
    
    Handles the actual transformation of data between versions
    with validation and error handling.
    """
    
    def __init__(self, version_manager: VersionManager):
        self.version_manager = version_manager
        self.migration_functions = {}
        self._register_migration_functions()
    
    def _register_migration_functions(self) -> None:
        """Register migration transformation functions"""
        self.migration_functions = {
            'migrate_v1_to_v3': self._migrate_v1_to_v3,
            'migrate_v3_to_v1': self._migrate_v3_to_v1,
            'validate_element_types': self._validate_element_types,
            'validate_metadata': self._validate_metadata,
            'validate_v1_compatibility': self._validate_v1_compatibility
        }
    
    def migrate_data(
        self, 
        data: Dict[str, Any], 
        from_version: ModelVersion, 
        to_version: ModelVersion
    ) -> Tuple[Dict[str, Any], VersionInfo]:
        """
        Migrate data from one version to another.
        
        Args:
            data: Data to migrate
            from_version: Source version
            to_version: Target version
            
        Returns:
            Tuple of (migrated_data, new_version_info)
            
        Raises:
            ValueError: If migration fails
        """
        try:
            # Get migration path
            migration_path = self.version_manager.get_migration_path(from_version, to_version)
            
            # Execute migration steps
            current_data = data.copy()
            migration_records = []
            
            for step in migration_path:
                # Execute transformation
                transform_func = self.migration_functions.get(step.transform_function)
                if not transform_func:
                    raise ValueError(f"Migration function not found: {step.transform_function}")
                
                current_data = transform_func(current_data)
                
                # Validate result
                for validation_rule in step.validation_rules:
                    validation_func = self.migration_functions.get(validation_rule)
                    if validation_func:
                        validation_errors = validation_func(current_data)
                        if validation_errors:
                            raise ValueError(f"Validation failed: {validation_errors}")
                
                # Record migration
                migration_record = f"{step.from_version.value} -> {step.to_version.value}: {step.description}"
                migration_records.append(migration_record)
            
            # Create new version info
            version_info = self.version_manager.create_version_info(
                version=to_version,
                custom_metadata={'migration_records': migration_records}
            )
            
            return current_data, version_info
            
        except Exception as e:
            raise ValueError(f"Migration failed: {e}")
    
    def _migrate_v1_to_v3(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate V1 format to V3 format"""
        from .compatibility import ToreV1Converter
        
        # Convert elements
        elements = ToreV1Converter.from_v1_format(data)
        
        # Build V3 format
        v3_data = {
            'version': ModelVersion.V3_0.value,
            'format': 'unified_element_model',
            'created_at': datetime.now().isoformat(),
            'migrated_from': 'v1',
            'elements': [elem.to_dict() for elem in elements]
        }
        
        return v3_data
    
    def _migrate_v3_to_v1(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate V3 format to V1 format"""
        from .compatibility import ToreV1Converter
        
        # Convert elements
        elements = []
        if 'elements' in data:
            for elem_data in data['elements']:
                element = Element.from_dict(elem_data)
                elements.append(element)
        
        # Convert to V1 format
        v1_data = ToreV1Converter.to_v1_format(elements)
        
        return v1_data
    
    def _validate_element_types(self, data: Dict[str, Any]) -> List[str]:
        """Validate element types in data"""
        errors = []
        
        if 'elements' not in data:
            errors.append("No elements found in data")
            return errors
        
        for i, elem_data in enumerate(data['elements']):
            if 'element_type' not in elem_data:
                errors.append(f"Element {i} missing element_type")
            else:
                try:
                    from .element import ElementType
                    ElementType(elem_data['element_type'])
                except ValueError:
                    errors.append(f"Element {i} has invalid element_type: {elem_data['element_type']}")
        
        return errors
    
    def _validate_metadata(self, data: Dict[str, Any]) -> List[str]:
        """Validate metadata in data"""
        errors = []
        
        # Basic metadata validation
        for i, elem_data in enumerate(data.get('elements', [])):
            if 'metadata' in elem_data and elem_data['metadata']:
                metadata = elem_data['metadata']
                
                # Check confidence range
                confidence = metadata.get('confidence', 1.0)
                if not 0.0 <= confidence <= 1.0:
                    errors.append(f"Element {i} has invalid confidence: {confidence}")
        
        return errors
    
    def _validate_v1_compatibility(self, data: Dict[str, Any]) -> List[str]:
        """Validate V1 compatibility"""
        errors = []
        
        # Check required V1 fields
        if 'elements' not in data:
            errors.append("V1 format requires 'elements' field")
        
        # Check element structure
        for i, elem_data in enumerate(data.get('elements', [])):
            required_fields = ['id', 'type', 'text']
            for field in required_fields:
                if field not in elem_data:
                    errors.append(f"V1 element {i} missing required field: {field}")
        
        return errors


class VersionedElementCollection:
    """
    Collection that maintains version information for elements.
    
    Provides automatic version tracking and migration support
    for element collections.
    """
    
    def __init__(
        self, 
        elements: List[Element], 
        version_info: Optional[VersionInfo] = None
    ):
        self.elements = elements
        self.version_info = version_info or VersionManager().create_version_info()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize collection with version info"""
        return {
            'version_info': self.version_info.to_dict(),
            'elements': [elem.to_dict() for elem in self.elements]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VersionedElementCollection':
        """Deserialize collection with version info"""
        version_info = VersionInfo.from_dict(data['version_info'])
        elements = [Element.from_dict(elem_data) for elem_data in data['elements']]
        return cls(elements, version_info)
    
    def migrate_to_version(self, target_version: ModelVersion) -> 'VersionedElementCollection':
        """Migrate collection to target version"""
        if self.version_info.version == target_version:
            return self
        
        version_manager = VersionManager()
        migration_engine = MigrationEngine(version_manager)
        
        # Convert to dict for migration
        data = self.to_dict()
        
        # Migrate
        migrated_data, new_version_info = migration_engine.migrate_data(
            data, self.version_info.version, target_version
        )
        
        # Reconstruct collection
        return VersionedElementCollection.from_dict(migrated_data)
    
    def validate(self) -> List[str]:
        """Validate collection and version consistency"""
        version_manager = VersionManager()
        return version_manager.validate_version(self.version_info)