"""Layout migration system for ToreMatrix V3.

Provides version compatibility, schema migration, and upgrade paths for
layout formats across different versions of the application.
"""

from typing import Dict, List, Optional, Any, Callable, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import logging
import re
from datetime import datetime, timezone
try:
    from semantic_version import Version, Spec
except ImportError:
    # Fallback for version comparison
    class Version:
        def __init__(self, version_str):
            self.version_str = version_str
            parts = version_str.split('.')
            self.major = int(parts[0]) if len(parts) > 0 else 0
            self.minor = int(parts[1]) if len(parts) > 1 else 0
            self.patch = int(parts[2]) if len(parts) > 2 else 0
        
        def __lt__(self, other):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
        
        def __le__(self, other):
            return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)
        
        def __gt__(self, other):
            return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)
        
        def __ge__(self, other):
            return (self.major, self.minor, self.patch) >= (other.major, other.minor, other.patch)
        
        def __eq__(self, other):
            return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)
    
    Spec = None  # Not used in fallback
import hashlib

from PyQt6.QtCore import QObject, pyqtSignal

from ..base import BaseUIComponent
from ...core.events import EventBus
from ...core.config import ConfigurationManager  
from ...core.state import Store
from .serialization import SerializedLayout, LayoutMetadata
from .persistence import LayoutPersistence

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Raised when layout migration fails."""
    pass


class MigrationResult(Enum):
    """Migration operation results."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    PARTIAL = "partial"
    ROLLBACK = "rollback"


class MigrationType(Enum):
    """Types of migrations."""
    SCHEMA_UPGRADE = "schema_upgrade"
    COMPONENT_RENAME = "component_rename"
    PROPERTY_MAPPING = "property_mapping"
    LAYOUT_RESTRUCTURE = "layout_restructure"
    FORMAT_CONVERSION = "format_conversion"
    COMPATIBILITY_FIX = "compatibility_fix"


@dataclass
class MigrationStep:
    """Individual migration step definition."""
    step_id: str
    name: str
    description: str
    migration_type: MigrationType
    from_version: str
    to_version: str
    required: bool = True
    backup_required: bool = True
    reversible: bool = False
    
    # Migration function
    migration_function: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    rollback_function: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    
    # Validation
    pre_validation: Optional[Callable[[Dict[str, Any]], bool]] = None
    post_validation: Optional[Callable[[Dict[str, Any]], bool]] = None
    
    # Metadata
    created: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    author: str = ""
    notes: str = ""


@dataclass
class MigrationPlan:
    """Complete migration plan for a layout."""
    plan_id: str
    source_version: str
    target_version: str
    layout_name: str
    steps: List[MigrationStep] = field(default_factory=list)
    created: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    estimated_duration: float = 0.0  # seconds
    risk_level: str = "low"  # low, medium, high


@dataclass
class MigrationRecord:
    """Record of a completed migration."""
    record_id: str
    layout_name: str
    plan_id: str
    from_version: str
    to_version: str
    result: MigrationResult
    started: datetime
    completed: datetime
    duration: float
    steps_completed: int
    total_steps: int
    error_message: Optional[str] = None
    backup_path: Optional[str] = None
    rollback_available: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class LayoutVersionManager:
    """Manages layout version information and compatibility."""
    
    CURRENT_VERSION = "3.0.0"
    MIN_SUPPORTED_VERSION = "1.0.0"
    
    def __init__(self):
        self._version_schema: Dict[str, Dict[str, Any]] = {}
        self._compatibility_matrix: Dict[str, List[str]] = {}
        
        self._initialize_version_schemas()
        self._initialize_compatibility_matrix()
    
    def is_version_supported(self, version: str) -> bool:
        """Check if a version is supported for migration."""
        try:
            target_version = Version(version)
            min_version = Version(self.MIN_SUPPORTED_VERSION)
            return target_version >= min_version
        except Exception:
            return False
    
    def get_current_version(self) -> str:
        """Get current layout format version."""
        return self.CURRENT_VERSION
    
    def needs_migration(self, layout_version: str) -> bool:
        """Check if a layout needs migration."""
        try:
            layout_ver = Version(layout_version)
            current_ver = Version(self.CURRENT_VERSION)
            return layout_ver < current_ver
        except Exception:
            return True  # Assume migration needed if version parsing fails
    
    def get_migration_path(self, from_version: str, to_version: str) -> List[str]:
        """Get migration path between versions."""
        try:
            from_ver = Version(from_version)
            to_ver = Version(to_version)
            
            if from_ver == to_ver:
                return []
            
            # For now, direct migration path
            # In complex scenarios, this would find intermediate versions
            return [from_version, to_version]
            
        except Exception:
            raise MigrationError(f"Invalid version format: {from_version} -> {to_version}")
    
    def get_version_schema(self, version: str) -> Dict[str, Any]:
        """Get schema definition for a version."""
        return self._version_schema.get(version, {})
    
    def validate_layout_format(self, layout_data: Dict[str, Any], version: str) -> bool:
        """Validate layout data against version schema."""
        schema = self.get_version_schema(version)
        if not schema:
            logger.warning(f"No schema available for version {version}")
            return True  # Assume valid if no schema
        
        # Basic validation - in practice would use jsonschema or similar
        required_fields = schema.get("required_fields", [])
        for field in required_fields:
            if field not in layout_data:
                return False
        
        return True
    
    def detect_layout_version(self, layout_data: Dict[str, Any]) -> str:
        """Detect layout version from data."""
        # Check metadata version first
        if "metadata" in layout_data:
            metadata = layout_data["metadata"]
            if "version" in metadata:
                return metadata["version"]
        
        # Check root version field
        if "version" in layout_data:
            return layout_data["version"]
        
        # Fallback: detect by structure
        return self._detect_version_by_structure(layout_data)
    
    def _initialize_version_schemas(self) -> None:
        """Initialize version schema definitions."""
        # Version 1.0.0 schema
        self._version_schema["1.0.0"] = {
            "required_fields": ["layout", "metadata"],
            "optional_fields": ["displays"],
            "layout_types": ["splitter", "tab_widget", "widget"],
            "metadata_fields": ["name", "created"]
        }
        
        # Version 2.0.0 schema
        self._version_schema["2.0.0"] = {
            "required_fields": ["layout", "metadata", "displays"],
            "optional_fields": ["global_properties"],
            "layout_types": ["splitter", "tab_widget", "stacked_widget", "vbox_layout", "hbox_layout", "widget"],
            "metadata_fields": ["name", "version", "created", "modified", "author"]
        }
        
        # Version 3.0.0 schema (current)
        self._version_schema["3.0.0"] = {
            "required_fields": ["layout", "metadata", "displays", "global_properties"],
            "optional_fields": [],
            "layout_types": ["splitter", "tab_widget", "stacked_widget", "vbox_layout", "hbox_layout", "grid_layout", "widget", "custom"],
            "metadata_fields": ["name", "version", "created", "modified", "author", "description", "tags"]
        }
    
    def _initialize_compatibility_matrix(self) -> None:
        """Initialize version compatibility matrix."""
        self._compatibility_matrix = {
            "1.0.0": ["2.0.0", "3.0.0"],
            "2.0.0": ["3.0.0"],
            "3.0.0": []  # Current version
        }
    
    def _detect_version_by_structure(self, layout_data: Dict[str, Any]) -> str:
        """Detect version by analyzing data structure."""
        # Check for version 3.0.0 features
        if ("global_properties" in layout_data and 
            "displays" in layout_data and
            isinstance(layout_data.get("metadata"), dict)):
            metadata = layout_data["metadata"]
            if "tags" in metadata or "description" in metadata:
                return "3.0.0"
        
        # Check for version 2.0.0 features
        if ("displays" in layout_data and 
            isinstance(layout_data.get("metadata"), dict)):
            metadata = layout_data["metadata"]
            if "author" in metadata or "modified" in metadata:
                return "2.0.0"
        
        # Default to 1.0.0
        return "1.0.0"


class LayoutMigrator:
    """Performs layout migrations between versions."""
    
    def __init__(
        self,
        version_manager: LayoutVersionManager,
        persistence: LayoutPersistence
    ):
        self._version_manager = version_manager
        self._persistence = persistence
        self._migration_steps: Dict[str, MigrationStep] = {}
        self._migration_records: List[MigrationRecord] = []
        
        self._register_builtin_migrations()
    
    def register_migration_step(self, step: MigrationStep) -> None:
        """Register a migration step."""
        self._migration_steps[step.step_id] = step
        logger.debug(f"Registered migration step: {step.step_id}")
    
    def create_migration_plan(
        self,
        layout_name: str,
        from_version: str,
        to_version: Optional[str] = None
    ) -> MigrationPlan:
        """Create a migration plan for a layout."""
        target_version = to_version or self._version_manager.get_current_version()
        
        # Get migration path
        version_path = self._version_manager.get_migration_path(from_version, target_version)
        
        # Create plan
        plan_id = self._generate_plan_id(layout_name, from_version, target_version)
        plan = MigrationPlan(
            plan_id=plan_id,
            source_version=from_version,
            target_version=target_version,
            layout_name=layout_name
        )
        
        # Add migration steps
        for i in range(len(version_path) - 1):
            from_ver = version_path[i]
            to_ver = version_path[i + 1]
            
            steps = self._get_migration_steps_for_versions(from_ver, to_ver)
            plan.steps.extend(steps)
        
        # Calculate estimates
        plan.estimated_duration = sum(0.5 for _ in plan.steps)  # 0.5s per step estimate
        plan.risk_level = self._assess_risk_level(plan.steps)
        
        return plan
    
    def execute_migration_plan(
        self,
        plan: MigrationPlan,
        create_backup: bool = True
    ) -> MigrationRecord:
        """Execute a migration plan."""
        record_id = self._generate_record_id(plan.plan_id)
        started = datetime.now(timezone.utc)
        
        record = MigrationRecord(
            record_id=record_id,
            layout_name=plan.layout_name,
            plan_id=plan.plan_id,
            from_version=plan.source_version,
            to_version=plan.target_version,
            result=MigrationResult.FAILED,  # Will be updated
            started=started,
            completed=started,  # Will be updated
            duration=0.0,
            steps_completed=0,
            total_steps=len(plan.steps)
        )
        
        try:
            # Load layout data
            layout_data = self._load_layout_data(plan.layout_name)
            if not layout_data:
                raise MigrationError(f"Failed to load layout '{plan.layout_name}'")
            
            # Create backup if requested
            if create_backup:
                backup_path = self._create_migration_backup(plan.layout_name, layout_data)
                record.backup_path = backup_path
                record.rollback_available = True
            
            # Execute migration steps
            current_data = layout_data.copy()
            
            for i, step in enumerate(plan.steps):
                try:
                    logger.info(f"Executing migration step: {step.name}")
                    
                    # Pre-validation
                    if step.pre_validation and not step.pre_validation(current_data):
                        raise MigrationError(f"Pre-validation failed for step {step.step_id}")
                    
                    # Execute migration
                    if step.migration_function:
                        current_data = step.migration_function(current_data)
                    
                    # Post-validation
                    if step.post_validation and not step.post_validation(current_data):
                        raise MigrationError(f"Post-validation failed for step {step.step_id}")
                    
                    record.steps_completed += 1
                    
                except Exception as e:
                    logger.error(f"Migration step {step.step_id} failed: {e}")
                    if step.required:
                        raise MigrationError(f"Required migration step failed: {e}") from e
                    else:
                        logger.warning(f"Optional migration step skipped: {step.step_id}")
            
            # Save migrated layout
            self._save_migrated_layout(plan.layout_name, current_data)
            
            # Update record
            record.result = MigrationResult.SUCCESS
            record.completed = datetime.now(timezone.utc)
            record.duration = (record.completed - record.started).total_seconds()
            
            logger.info(f"Migration completed successfully: {plan.layout_name} {plan.source_version} -> {plan.target_version}")
            
        except Exception as e:
            record.result = MigrationResult.FAILED
            record.error_message = str(e)
            record.completed = datetime.now(timezone.utc)
            record.duration = (record.completed - record.started).total_seconds()
            
            logger.error(f"Migration failed: {e}")
            
            # Attempt rollback if backup available
            if record.rollback_available and record.backup_path:
                try:
                    self._perform_rollback(plan.layout_name, record.backup_path)
                    record.result = MigrationResult.ROLLBACK
                    logger.info(f"Rollback completed for {plan.layout_name}")
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")
        
        # Store migration record
        self._migration_records.append(record)
        
        return record
    
    def migrate_layout(
        self,
        layout_name: str,
        target_version: Optional[str] = None,
        create_backup: bool = True
    ) -> MigrationRecord:
        """Migrate a single layout to target version."""
        # Load layout to detect current version
        layout_data = self._load_layout_data(layout_name)
        if not layout_data:
            raise MigrationError(f"Layout '{layout_name}' not found")
        
        current_version = self._version_manager.detect_layout_version(layout_data)
        target_ver = target_version or self._version_manager.get_current_version()
        
        # Check if migration is needed
        if not self._version_manager.needs_migration(current_version):
            logger.info(f"Layout '{layout_name}' is already current version")
            # Create a success record
            return MigrationRecord(
                record_id=self._generate_record_id("no_migration"),
                layout_name=layout_name,
                plan_id="no_migration",
                from_version=current_version,
                to_version=target_ver,
                result=MigrationResult.SKIPPED,
                started=datetime.now(timezone.utc),
                completed=datetime.now(timezone.utc),
                duration=0.0,
                steps_completed=0,
                total_steps=0
            )
        
        # Create and execute migration plan
        plan = self.create_migration_plan(layout_name, current_version, target_ver)
        return self.execute_migration_plan(plan, create_backup)
    
    def rollback_migration(self, record_id: str) -> bool:
        """Rollback a migration using its record."""
        record = next((r for r in self._migration_records if r.record_id == record_id), None)
        
        if not record:
            logger.error(f"Migration record {record_id} not found")
            return False
        
        if not record.rollback_available or not record.backup_path:
            logger.error(f"Rollback not available for migration {record_id}")
            return False
        
        try:
            self._perform_rollback(record.layout_name, record.backup_path)
            logger.info(f"Rollback completed for migration {record_id}")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed for migration {record_id}: {e}")
            return False
    
    def get_migration_history(self, layout_name: Optional[str] = None) -> List[MigrationRecord]:
        """Get migration history, optionally filtered by layout name."""
        records = self._migration_records
        
        if layout_name:
            records = [r for r in records if r.layout_name == layout_name]
        
        return sorted(records, key=lambda r: r.started, reverse=True)
    
    def validate_migration_integrity(self, layout_name: str) -> bool:
        """Validate the integrity of a migrated layout."""
        try:
            layout_data = self._load_layout_data(layout_name)
            if not layout_data:
                return False
            
            version = self._version_manager.detect_layout_version(layout_data)
            return self._version_manager.validate_layout_format(layout_data, version)
            
        except Exception as e:
            logger.error(f"Migration integrity validation failed: {e}")
            return False
    
    # Private methods
    
    def _register_builtin_migrations(self) -> None:
        """Register built-in migration steps."""
        # Migration from 1.0.0 to 2.0.0
        self.register_migration_step(MigrationStep(
            step_id="v1_to_v2_add_displays",
            name="Add Displays Information",
            description="Add display geometry information to layout",
            migration_type=MigrationType.SCHEMA_UPGRADE,
            from_version="1.0.0",
            to_version="2.0.0",
            migration_function=self._migrate_v1_to_v2_add_displays,
            pre_validation=self._validate_v1_format,
            post_validation=self._validate_v2_format
        ))
        
        self.register_migration_step(MigrationStep(
            step_id="v1_to_v2_enhance_metadata",
            name="Enhance Metadata",
            description="Add author, version, and modified fields to metadata",
            migration_type=MigrationType.SCHEMA_UPGRADE,
            from_version="1.0.0",
            to_version="2.0.0",
            migration_function=self._migrate_v1_to_v2_enhance_metadata
        ))
        
        # Migration from 2.0.0 to 3.0.0
        self.register_migration_step(MigrationStep(
            step_id="v2_to_v3_add_global_properties",
            name="Add Global Properties",
            description="Add global properties section",
            migration_type=MigrationType.SCHEMA_UPGRADE,
            from_version="2.0.0",
            to_version="3.0.0",
            migration_function=self._migrate_v2_to_v3_add_global_properties
        ))
        
        self.register_migration_step(MigrationStep(
            step_id="v2_to_v3_enhance_metadata_tags",
            name="Add Metadata Tags and Description",
            description="Add tags and description to metadata",
            migration_type=MigrationType.SCHEMA_UPGRADE,
            from_version="2.0.0",
            to_version="3.0.0",
            migration_function=self._migrate_v2_to_v3_enhance_metadata
        ))
        
        logger.info("Registered built-in migration steps")
    
    def _migrate_v1_to_v2_add_displays(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate v1 to v2: Add displays information."""
        if "displays" not in data:
            # Add default display information
            data["displays"] = [{
                "x": 0,
                "y": 0,
                "width": 1920,
                "height": 1080,
                "dpi": 96.0,
                "name": "Default Display",
                "primary": True
            }]
        
        return data
    
    def _migrate_v1_to_v2_enhance_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate v1 to v2: Enhance metadata."""
        if "metadata" in data:
            metadata = data["metadata"]
            
            # Add version if not present
            if "version" not in metadata:
                metadata["version"] = "2.0.0"
            
            # Add author if not present
            if "author" not in metadata:
                metadata["author"] = "Migrated"
            
            # Add modified timestamp
            if "modified" not in metadata:
                metadata["modified"] = datetime.now(timezone.utc).isoformat()
        
        return data
    
    def _migrate_v2_to_v3_add_global_properties(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate v2 to v3: Add global properties."""
        if "global_properties" not in data:
            data["global_properties"] = {
                "serialization_timestamp": datetime.now(timezone.utc).isoformat(),
                "migration_source": "v2.0.0"
            }
        
        return data
    
    def _migrate_v2_to_v3_enhance_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate v2 to v3: Add tags and description to metadata."""
        if "metadata" in data:
            metadata = data["metadata"]
            
            # Update version
            metadata["version"] = "3.0.0"
            
            # Add description if not present
            if "description" not in metadata:
                metadata["description"] = "Migrated layout"
            
            # Add tags if not present
            if "tags" not in metadata:
                metadata["tags"] = ["migrated"]
        
        return data
    
    def _validate_v1_format(self, data: Dict[str, Any]) -> bool:
        """Validate v1.0.0 format."""
        required_fields = ["layout", "metadata"]
        return all(field in data for field in required_fields)
    
    def _validate_v2_format(self, data: Dict[str, Any]) -> bool:
        """Validate v2.0.0 format."""
        required_fields = ["layout", "metadata", "displays"]
        return all(field in data for field in required_fields)
    
    def _get_migration_steps_for_versions(self, from_version: str, to_version: str) -> List[MigrationStep]:
        """Get migration steps for version transition."""
        steps = []
        
        for step in self._migration_steps.values():
            if step.from_version == from_version and step.to_version == to_version:
                steps.append(step)
        
        # Sort by migration type and step ID for consistent order
        steps.sort(key=lambda s: (s.migration_type.value, s.step_id))
        
        return steps
    
    def _assess_risk_level(self, steps: List[MigrationStep]) -> str:
        """Assess risk level of migration steps."""
        if not steps:
            return "low"
        
        # Count different risk factors
        schema_changes = sum(1 for s in steps if s.migration_type == MigrationType.SCHEMA_UPGRADE)
        restructures = sum(1 for s in steps if s.migration_type == MigrationType.LAYOUT_RESTRUCTURE)
        irreversible = sum(1 for s in steps if not s.reversible)
        
        if restructures > 0 or irreversible > 2:
            return "high"
        elif schema_changes > 3 or irreversible > 0:
            return "medium"
        else:
            return "low"
    
    def _load_layout_data(self, layout_name: str) -> Optional[Dict[str, Any]]:
        """Load layout data for migration."""
        try:
            # Find layout file
            layout_file = self._persistence._find_layout_file(layout_name)
            if not layout_file.exists():
                return None
            
            with open(layout_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Failed to load layout data for {layout_name}: {e}")
            return None
    
    def _save_migrated_layout(self, layout_name: str, data: Dict[str, Any]) -> None:
        """Save migrated layout data."""
        try:
            # Find layout file
            layout_file = self._persistence._find_layout_file(layout_name)
            
            with open(layout_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
                
        except Exception as e:
            raise MigrationError(f"Failed to save migrated layout: {e}") from e
    
    def _create_migration_backup(self, layout_name: str, data: Dict[str, Any]) -> str:
        """Create backup before migration."""
        try:
            backup_dir = self._persistence._backup_path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{layout_name}_migration_backup_{timestamp}.json"
            backup_path = backup_dir / backup_filename
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            return str(backup_path)
            
        except Exception as e:
            raise MigrationError(f"Failed to create migration backup: {e}") from e
    
    def _perform_rollback(self, layout_name: str, backup_path: str) -> None:
        """Perform rollback from backup."""
        try:
            # Load backup data
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Restore layout
            self._save_migrated_layout(layout_name, backup_data)
            
        except Exception as e:
            raise MigrationError(f"Rollback failed: {e}") from e
    
    def _generate_plan_id(self, layout_name: str, from_version: str, to_version: str) -> str:
        """Generate unique plan ID."""
        data = f"{layout_name}_{from_version}_{to_version}_{datetime.now().isoformat()}"
        return hashlib.md5(data.encode()).hexdigest()[:16]
    
    def _generate_record_id(self, plan_id: str) -> str:
        """Generate unique record ID."""
        data = f"{plan_id}_{datetime.now().isoformat()}"
        return hashlib.md5(data.encode()).hexdigest()[:16]


class LayoutMigrationManager(BaseUIComponent):
    """Main manager for layout migration operations."""
    
    # Signals
    migration_started = pyqtSignal(str, str, str)  # layout_name, from_version, to_version
    migration_completed = pyqtSignal(str, str)     # layout_name, result
    migration_progress = pyqtSignal(str, int, int) # layout_name, completed, total
    
    def __init__(
        self,
        event_bus: EventBus,
        config_manager: ConfigurationManager,
        state_manager: Store,
        persistence: LayoutPersistence,
        parent: Optional[QObject] = None
    ):
        super().__init__(event_bus, config_manager, state_manager, parent)
        
        self._persistence = persistence
        self._version_manager = LayoutVersionManager()
        self._migrator = LayoutMigrator(self._version_manager, persistence)
        
        # Migration settings
        self._auto_migration_enabled = True
        self._backup_before_migration = True
    
    def _setup_component(self) -> None:
        """Setup the migration manager."""
        # Subscribe to events
        self.subscribe_event("layout.loaded", self._on_layout_loaded)
        self.subscribe_event("application.startup", self._on_application_startup)
        
        logger.info("Layout migration manager initialized")
    
    def migrate_layout(
        self,
        layout_name: str,
        target_version: Optional[str] = None
    ) -> MigrationRecord:
        """Migrate a layout to target version."""
        target_ver = target_version or self._version_manager.get_current_version()
        
        # Detect current version
        layout_data = self._migrator._load_layout_data(layout_name)
        if not layout_data:
            raise MigrationError(f"Layout '{layout_name}' not found")
        
        current_version = self._version_manager.detect_layout_version(layout_data)
        
        # Emit migration started signal
        self.migration_started.emit(layout_name, current_version, target_ver)
        
        # Publish event
        self.publish_event("layout.migration_started", {
            "layout_name": layout_name,
            "from_version": current_version,
            "to_version": target_ver
        })
        
        try:
            # Perform migration
            record = self._migrator.migrate_layout(
                layout_name,
                target_ver,
                self._backup_before_migration
            )
            
            # Emit completion signal
            self.migration_completed.emit(layout_name, record.result.value)
            
            # Publish event
            self.publish_event("layout.migration_completed", {
                "layout_name": layout_name,
                "result": record.result.value,
                "duration": record.duration,
                "steps_completed": record.steps_completed
            })
            
            return record
            
        except Exception as e:
            # Emit failure signal
            self.migration_completed.emit(layout_name, MigrationResult.FAILED.value)
            
            # Publish event
            self.publish_event("layout.migration_failed", {
                "layout_name": layout_name,
                "error": str(e)
            })
            
            raise
    
    def migrate_all_layouts(self, target_version: Optional[str] = None) -> Dict[str, MigrationRecord]:
        """Migrate all layouts to target version."""
        results = {}
        layouts = self._persistence.list_layouts()
        
        for layout_name in layouts:
            try:
                record = self.migrate_layout(layout_name, target_version)
                results[layout_name] = record
            except Exception as e:
                logger.error(f"Failed to migrate layout {layout_name}: {e}")
                # Create failed record
                results[layout_name] = MigrationRecord(
                    record_id="failed",
                    layout_name=layout_name,
                    plan_id="failed",
                    from_version="unknown",
                    to_version=target_version or self._version_manager.get_current_version(),
                    result=MigrationResult.FAILED,
                    started=datetime.now(timezone.utc),
                    completed=datetime.now(timezone.utc),
                    duration=0.0,
                    steps_completed=0,
                    total_steps=0,
                    error_message=str(e)
                )
        
        return results
    
    def check_layout_compatibility(self, layout_name: str) -> Dict[str, Any]:
        """Check compatibility of a layout with current version."""
        try:
            layout_data = self._migrator._load_layout_data(layout_name)
            if not layout_data:
                return {"compatible": False, "error": "Layout not found"}
            
            current_version = self._version_manager.detect_layout_version(layout_data)
            needs_migration = self._version_manager.needs_migration(current_version)
            is_supported = self._version_manager.is_version_supported(current_version)
            
            result = {
                "compatible": not needs_migration,
                "current_version": current_version,
                "needs_migration": needs_migration,
                "is_supported": is_supported,
                "target_version": self._version_manager.get_current_version()
            }
            
            if needs_migration and is_supported:
                plan = self._migrator.create_migration_plan(layout_name, current_version)
                result.update({
                    "migration_plan": {
                        "steps": len(plan.steps),
                        "estimated_duration": plan.estimated_duration,
                        "risk_level": plan.risk_level
                    }
                })
            
            return result
            
        except Exception as e:
            return {"compatible": False, "error": str(e)}
    
    def get_migration_history(self, layout_name: Optional[str] = None) -> List[MigrationRecord]:
        """Get migration history."""
        return self._migrator.get_migration_history(layout_name)
    
    def rollback_migration(self, record_id: str) -> bool:
        """Rollback a migration."""
        success = self._migrator.rollback_migration(record_id)
        
        if success:
            self.publish_event("layout.migration_rollback", {
                "record_id": record_id
            })
        
        return success
    
    def enable_auto_migration(self, enabled: bool) -> None:
        """Enable or disable automatic migration."""
        self._auto_migration_enabled = enabled
        self._config_manager.set("layouts.auto_migration_enabled", enabled)
    
    def is_auto_migration_enabled(self) -> bool:
        """Check if auto migration is enabled."""
        return self._auto_migration_enabled
    
    def set_backup_before_migration(self, enabled: bool) -> None:
        """Enable or disable backup before migration."""
        self._backup_before_migration = enabled
        self._config_manager.set("layouts.backup_before_migration", enabled)
    
    def _on_layout_loaded(self, event_data: Dict[str, Any]) -> None:
        """Handle layout loaded event - check for auto migration."""
        if not self._auto_migration_enabled:
            return
        
        layout_name = event_data.get("layout_name")
        if not layout_name:
            return
        
        compatibility = self.check_layout_compatibility(layout_name)
        
        if compatibility.get("needs_migration") and compatibility.get("is_supported"):
            logger.info(f"Auto-migrating layout '{layout_name}'")
            try:
                self.migrate_layout(layout_name)
            except Exception as e:
                logger.error(f"Auto-migration failed for '{layout_name}': {e}")
    
    def _on_application_startup(self, event_data: Dict[str, Any]) -> None:
        """Handle application startup - check for outdated layouts."""
        if not self._auto_migration_enabled:
            return
        
        # Check all layouts for migration needs
        layouts = self._persistence.list_layouts()
        outdated_layouts = []
        
        for layout_name in layouts:
            compatibility = self.check_layout_compatibility(layout_name)
            if compatibility.get("needs_migration"):
                outdated_layouts.append(layout_name)
        
        if outdated_layouts:
            logger.info(f"Found {len(outdated_layouts)} layouts that need migration")
            
            # Publish event for UI to handle
            self.publish_event("layout.migration_needed", {
                "outdated_layouts": outdated_layouts,
                "auto_migration_enabled": self._auto_migration_enabled
            })