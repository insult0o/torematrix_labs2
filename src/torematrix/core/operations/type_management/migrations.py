"""Type Migration Manager

Version-aware type migrations with schema evolution and data transformation.
Supports forward and backward migrations with comprehensive validation.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Callable, Union
import json
import hashlib
from pathlib import Path

from torematrix.core.models.types import TypeRegistry, TypeDefinition


logger = logging.getLogger(__name__)


class MigrationDirection(Enum):
    """Direction of migration"""
    FORWARD = "forward"
    BACKWARD = "backward"


class MigrationStatus(Enum):
    """Status of migration operations"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class MigrationStep:
    """Single step in a migration"""
    step_id: str
    description: str
    operation: str  # add_field, remove_field, rename_field, transform_data, etc.
    parameters: Dict[str, Any]
    reversible: bool = True
    forward_sql: Optional[str] = None
    backward_sql: Optional[str] = None
    validation_rules: List[str] = field(default_factory=list)


@dataclass
class MigrationPlan:
    """Plan for type migration"""
    migration_id: str
    name: str
    description: str
    from_version: str
    to_version: str
    direction: MigrationDirection
    steps: List[MigrationStep]
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: float = 0.0
    affects_data: bool = True
    requires_downtime: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def is_reversible(self) -> bool:
        """Check if all steps in migration are reversible"""
        return all(step.reversible for step in self.steps)


@dataclass
class MigrationResult:
    """Result of migration execution"""
    migration_id: str
    plan: MigrationPlan
    status: MigrationStatus
    executed_steps: List[str]
    failed_step: Optional[str] = None
    affected_elements: Set[str] = field(default_factory=set)
    data_changes: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    @property
    def duration_seconds(self) -> float:
        """Calculate migration duration"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate of executed steps"""
        if not self.plan.steps:
            return 1.0
        return len(self.executed_steps) / len(self.plan.steps)


@dataclass
class TypeVersion:
    """Version information for a type"""
    type_id: str
    version: str
    schema: Dict[str, Any]
    migration_hash: str
    created_at: datetime = field(default_factory=datetime.now)
    deprecated: bool = False
    supported_until: Optional[datetime] = None


class TypeMigrationManager:
    """Version-aware type migration system
    
    Provides comprehensive type migration capabilities:
    - Schema evolution tracking
    - Forward and backward migrations
    - Data transformation during migration
    - Migration validation and rollback
    - Version compatibility checking
    """
    
    def __init__(self, registry: TypeRegistry, migration_dir: Optional[Path] = None):
        """Initialize migration manager
        
        Args:
            registry: Type registry for type definitions
            migration_dir: Directory for storing migration files
        """
        self.registry = registry
        self.migration_dir = migration_dir or Path("migrations")
        self.migration_dir.mkdir(exist_ok=True)
        
        self._migrations: Dict[str, MigrationPlan] = {}
        self._type_versions: Dict[str, List[TypeVersion]] = {}
        self._executed_migrations: Set[str] = set()
        
        self._load_migrations()
        self._load_type_versions()
        
        logger.info(f"TypeMigrationManager initialized with {len(self._migrations)} migrations")
    
    def create_migration(self, 
                        name: str,
                        description: str,
                        from_version: str,
                        to_version: str,
                        steps: List[MigrationStep]) -> MigrationPlan:
        """Create a new migration plan
        
        Args:
            name: Migration name
            description: Migration description
            from_version: Source version
            to_version: Target version
            steps: List of migration steps
            
        Returns:
            Created MigrationPlan
            
        Raises:
            ValueError: If migration parameters are invalid
        """
        if not name or not from_version or not to_version:
            raise ValueError("Migration name, from_version, and to_version are required")
        
        if from_version == to_version:
            raise ValueError("Source and target versions cannot be the same")
        
        # Generate migration ID
        migration_id = self._generate_migration_id(name, from_version, to_version)
        
        # Estimate duration
        estimated_duration = sum(self._estimate_step_duration(step) for step in steps)
        
        migration = MigrationPlan(
            migration_id=migration_id,
            name=name,
            description=description,
            from_version=from_version,
            to_version=to_version,
            direction=MigrationDirection.FORWARD,
            steps=steps,
            estimated_duration=estimated_duration
        )
        
        # Validate migration
        validation_result = self._validate_migration(migration)
        if validation_result['errors']:
            raise ValueError(f"Migration validation failed: {validation_result['errors']}")
        
        # Store migration
        self._migrations[migration_id] = migration
        self._save_migration(migration)
        
        logger.info(f"Created migration {migration_id}: {from_version} -> {to_version}")
        return migration
    
    def execute_migration(self, 
                         migration_id: str,
                         dry_run: bool = False,
                         progress_callback: Optional[Callable] = None) -> MigrationResult:
        """Execute a migration plan
        
        Args:
            migration_id: ID of migration to execute
            dry_run: If True, validate without executing
            progress_callback: Optional progress callback function
            
        Returns:
            MigrationResult with execution details
            
        Raises:
            ValueError: If migration not found
            RuntimeError: If migration execution fails
        """
        if migration_id not in self._migrations:
            raise ValueError(f"Migration {migration_id} not found")
        
        plan = self._migrations[migration_id]
        logger.info(f"Executing migration {migration_id} (dry_run={dry_run})")
        
        result = MigrationResult(
            migration_id=migration_id,
            plan=plan,
            status=MigrationStatus.PENDING,
            executed_steps=[]
        )
        
        try:
            # Pre-execution validation
            validation = self._validate_migration_execution(plan)
            if validation['errors']:
                result.status = MigrationStatus.FAILED
                result.errors.extend(validation['errors'])
                return result
            
            result.warnings.extend(validation['warnings'])
            
            if dry_run:
                result.status = MigrationStatus.COMPLETED
                logger.info(f"Dry run completed for migration {migration_id}")
                return result
            
            # Execute migration steps
            result.status = MigrationStatus.RUNNING
            
            for i, step in enumerate(plan.steps):
                logger.debug(f"Executing step {i+1}/{len(plan.steps)}: {step.description}")
                
                try:
                    # Execute step
                    step_result = self._execute_migration_step(step, plan.direction)
                    
                    # Track results
                    result.executed_steps.append(step.step_id)
                    result.affected_elements.update(step_result.get('affected_elements', set()))
                    result.data_changes.update(step_result.get('data_changes', {}))
                    result.warnings.extend(step_result.get('warnings', []))
                    
                    # Update progress
                    if progress_callback:
                        progress = (i + 1) / len(plan.steps)
                        progress_callback(progress, f"Executed step: {step.description}")
                
                except Exception as e:
                    logger.error(f"Migration step failed: {step.step_id}: {e}")
                    result.status = MigrationStatus.FAILED
                    result.failed_step = step.step_id
                    result.errors.append(f"Step {step.step_id} failed: {e}")
                    
                    # Attempt rollback if possible
                    if plan.is_reversible:
                        try:
                            self._rollback_executed_steps(result.executed_steps, plan)
                            result.status = MigrationStatus.ROLLED_BACK
                        except Exception as rollback_error:
                            result.errors.append(f"Rollback failed: {rollback_error}")
                    
                    break
            
            # Mark as completed if all steps succeeded
            if result.status == MigrationStatus.RUNNING:
                result.status = MigrationStatus.COMPLETED
                self._executed_migrations.add(migration_id)
                self._update_type_version(plan)
            
        except Exception as e:
            logger.error(f"Migration execution failed: {e}")
            result.status = MigrationStatus.FAILED
            result.errors.append(str(e))
        
        finally:
            result.end_time = datetime.now()
        
        logger.info(f"Migration {migration_id} completed with status: {result.status}")
        return result
    
    def rollback_migration(self, migration_id: str) -> MigrationResult:
        """Rollback a previously executed migration
        
        Args:
            migration_id: ID of migration to rollback
            
        Returns:
            MigrationResult with rollback details
            
        Raises:
            ValueError: If migration not found or not executed
        """
        if migration_id not in self._migrations:
            raise ValueError(f"Migration {migration_id} not found")
        
        if migration_id not in self._executed_migrations:
            raise ValueError(f"Migration {migration_id} has not been executed")
        
        plan = self._migrations[migration_id]
        if not plan.is_reversible:
            raise ValueError(f"Migration {migration_id} is not reversible")
        
        logger.info(f"Rolling back migration {migration_id}")
        
        # Create reverse migration plan
        reverse_plan = self._create_reverse_plan(plan)
        
        # Execute reverse migration
        result = self.execute_migration(reverse_plan.migration_id)
        
        if result.status == MigrationStatus.COMPLETED:
            self._executed_migrations.discard(migration_id)
        
        return result
    
    def get_migration_path(self, 
                          from_version: str, 
                          to_version: str) -> List[MigrationPlan]:
        """Get migration path between versions
        
        Args:
            from_version: Source version
            to_version: Target version
            
        Returns:
            List of migrations to execute in order
        """
        if from_version == to_version:
            return []
        
        # Simple implementation - in practice would use graph algorithms
        path = []
        current_version = from_version
        
        while current_version != to_version:
            # Find migration from current version
            found_migration = None
            for migration in self._migrations.values():
                if migration.from_version == current_version:
                    # Prefer direct path to target
                    if migration.to_version == to_version:
                        found_migration = migration
                        break
                    # Or take any valid step forward
                    elif not found_migration:
                        found_migration = migration
            
            if not found_migration:
                logger.warning(f"No migration path found from {current_version} to {to_version}")
                break
            
            path.append(found_migration)
            current_version = found_migration.to_version
        
        return path
    
    def get_type_version_history(self, type_id: str) -> List[TypeVersion]:
        """Get version history for a type
        
        Args:
            type_id: Type to get history for
            
        Returns:
            List of type versions in chronological order
        """
        return self._type_versions.get(type_id, [])
    
    def get_current_version(self, type_id: str) -> Optional[str]:
        """Get current version of a type
        
        Args:
            type_id: Type to get version for
            
        Returns:
            Current version string, or None if not found
        """
        versions = self._type_versions.get(type_id, [])
        if versions:
            return max(versions, key=lambda v: v.created_at).version
        return None
    
    def validate_migration_compatibility(self, 
                                       migration_id: str,
                                       target_elements: List[str]) -> Dict[str, Any]:
        """Validate migration compatibility with target elements
        
        Args:
            migration_id: Migration to validate
            target_elements: Elements that would be affected
            
        Returns:
            Validation result dictionary
        """
        if migration_id not in self._migrations:
            return {'valid': False, 'errors': [f"Migration {migration_id} not found"]}
        
        plan = self._migrations[migration_id]
        errors = []
        warnings = []
        
        # Check element compatibility
        for element_id in target_elements:
            # Mock validation - would check actual element data
            element_type = self._get_element_type(element_id)
            if not self._is_type_compatible(element_type, plan):
                errors.append(f"Element {element_id} type {element_type} incompatible with migration")
        
        # Check dependencies
        for dep_id in plan.dependencies:
            if dep_id not in self._executed_migrations:
                errors.append(f"Dependency migration {dep_id} not executed")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'affected_elements': len(target_elements),
            'estimated_duration': plan.estimated_duration
        }
    
    def _generate_migration_id(self, name: str, from_version: str, to_version: str) -> str:
        """Generate unique migration ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        content = f"{name}_{from_version}_{to_version}_{timestamp}"
        hash_suffix = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"migration_{timestamp}_{hash_suffix}"
    
    def _validate_migration(self, migration: MigrationPlan) -> Dict[str, List[str]]:
        """Validate migration plan"""
        errors = []
        warnings = []
        
        # Check for empty steps
        if not migration.steps:
            errors.append("Migration must have at least one step")
        
        # Validate each step
        for step in migration.steps:
            if not step.step_id or not step.description:
                errors.append(f"Step missing required fields: {step}")
            
            if step.operation not in ['add_field', 'remove_field', 'rename_field', 'transform_data']:
                warnings.append(f"Unknown operation: {step.operation}")
        
        # Check for circular dependencies
        if migration.migration_id in migration.dependencies:
            errors.append("Migration cannot depend on itself")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_migration_execution(self, plan: MigrationPlan) -> Dict[str, List[str]]:
        """Validate migration before execution"""
        errors = []
        warnings = []
        
        # Check dependencies
        for dep_id in plan.dependencies:
            if dep_id not in self._executed_migrations:
                errors.append(f"Dependency {dep_id} not executed")
        
        # Check if already executed
        if plan.migration_id in self._executed_migrations:
            warnings.append("Migration already executed")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _execute_migration_step(self, 
                               step: MigrationStep, 
                               direction: MigrationDirection) -> Dict[str, Any]:
        """Execute a single migration step"""
        logger.debug(f"Executing migration step: {step.step_id}")
        
        result = {
            'affected_elements': set(),
            'data_changes': {},
            'warnings': [],
            'errors': []
        }
        
        try:
            # Execute based on operation type
            if step.operation == "add_field":
                self._execute_add_field(step, result)
            elif step.operation == "remove_field":
                self._execute_remove_field(step, result)
            elif step.operation == "rename_field":
                self._execute_rename_field(step, result)
            elif step.operation == "transform_data":
                self._execute_transform_data(step, result)
            else:
                result['warnings'].append(f"Unknown operation: {step.operation}")
            
        except Exception as e:
            result['errors'].append(str(e))
            raise
        
        return result
    
    def _execute_add_field(self, step: MigrationStep, result: Dict[str, Any]) -> None:
        """Execute add field operation"""
        field_name = step.parameters.get('field_name')
        field_type = step.parameters.get('field_type')
        default_value = step.parameters.get('default_value')
        
        if not field_name or not field_type:
            raise ValueError("add_field requires field_name and field_type parameters")
        
        # Mock implementation - would update schema and data
        result['data_changes'][f'add_field_{field_name}'] = {
            'field_type': field_type,
            'default_value': default_value
        }
        
        logger.debug(f"Added field {field_name} of type {field_type}")
    
    def _execute_remove_field(self, step: MigrationStep, result: Dict[str, Any]) -> None:
        """Execute remove field operation"""
        field_name = step.parameters.get('field_name')
        
        if not field_name:
            raise ValueError("remove_field requires field_name parameter")
        
        # Mock implementation - would remove from schema and data
        result['data_changes'][f'remove_field_{field_name}'] = {'removed': True}
        
        logger.debug(f"Removed field {field_name}")
    
    def _execute_rename_field(self, step: MigrationStep, result: Dict[str, Any]) -> None:
        """Execute rename field operation"""
        old_name = step.parameters.get('old_name')
        new_name = step.parameters.get('new_name')
        
        if not old_name or not new_name:
            raise ValueError("rename_field requires old_name and new_name parameters")
        
        # Mock implementation - would rename in schema and data
        result['data_changes'][f'rename_field_{old_name}'] = {'new_name': new_name}
        
        logger.debug(f"Renamed field {old_name} to {new_name}")
    
    def _execute_transform_data(self, step: MigrationStep, result: Dict[str, Any]) -> None:
        """Execute data transformation operation"""
        transformation = step.parameters.get('transformation')
        target_field = step.parameters.get('target_field')
        
        if not transformation or not target_field:
            raise ValueError("transform_data requires transformation and target_field parameters")
        
        # Mock implementation - would apply transformation
        result['data_changes'][f'transform_{target_field}'] = {'transformation': transformation}
        
        logger.debug(f"Applied transformation to field {target_field}")
    
    def _estimate_step_duration(self, step: MigrationStep) -> float:
        """Estimate duration for a migration step"""
        # Simple estimation based on operation type
        operation_times = {
            'add_field': 1.0,
            'remove_field': 0.5,
            'rename_field': 2.0,
            'transform_data': 5.0
        }
        return operation_times.get(step.operation, 1.0)
    
    def _create_reverse_plan(self, plan: MigrationPlan) -> MigrationPlan:
        """Create reverse migration plan"""
        reverse_steps = []
        
        # Reverse the steps and operations
        for step in reversed(plan.steps):
            if not step.reversible:
                continue
            
            reverse_step = MigrationStep(
                step_id=f"reverse_{step.step_id}",
                description=f"Reverse: {step.description}",
                operation=self._get_reverse_operation(step.operation),
                parameters=self._get_reverse_parameters(step.operation, step.parameters)
            )
            reverse_steps.append(reverse_step)
        
        return MigrationPlan(
            migration_id=f"reverse_{plan.migration_id}",
            name=f"Reverse: {plan.name}",
            description=f"Reverse migration for {plan.description}",
            from_version=plan.to_version,
            to_version=plan.from_version,
            direction=MigrationDirection.BACKWARD,
            steps=reverse_steps
        )
    
    def _get_reverse_operation(self, operation: str) -> str:
        """Get reverse operation for a given operation"""
        reverse_ops = {
            'add_field': 'remove_field',
            'remove_field': 'add_field',
            'rename_field': 'rename_field',  # Same operation, reverse parameters
            'transform_data': 'transform_data'  # Would need reverse transformation
        }
        return reverse_ops.get(operation, operation)
    
    def _get_reverse_parameters(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get reverse parameters for an operation"""
        if operation == 'rename_field':
            return {
                'old_name': params.get('new_name'),
                'new_name': params.get('old_name')
            }
        return params
    
    def _rollback_executed_steps(self, executed_steps: List[str], plan: MigrationPlan) -> None:
        """Rollback executed migration steps"""
        logger.info(f"Rolling back {len(executed_steps)} executed steps")
        
        # Find executed steps and reverse them
        steps_to_reverse = []
        for step_id in reversed(executed_steps):
            step = next((s for s in plan.steps if s.step_id == step_id), None)
            if step and step.reversible:
                steps_to_reverse.append(step)
        
        # Execute reverse operations
        for step in steps_to_reverse:
            try:
                reverse_result = self._execute_migration_step(step, MigrationDirection.BACKWARD)
                logger.debug(f"Rolled back step: {step.step_id}")
            except Exception as e:
                logger.error(f"Failed to rollback step {step.step_id}: {e}")
                raise
    
    def _update_type_version(self, plan: MigrationPlan) -> None:
        """Update type version after successful migration"""
        # Mock implementation - would update version tracking
        logger.debug(f"Updated type version: {plan.from_version} -> {plan.to_version}")
    
    def _load_migrations(self) -> None:
        """Load migrations from storage"""
        # Mock implementation - would load from files
        logger.debug("Loading migrations from storage")
    
    def _load_type_versions(self) -> None:
        """Load type versions from storage"""
        # Mock implementation - would load version history
        logger.debug("Loading type versions from storage")
    
    def _save_migration(self, migration: MigrationPlan) -> None:
        """Save migration to storage"""
        # Mock implementation - would save to file
        migration_file = self.migration_dir / f"{migration.migration_id}.json"
        logger.debug(f"Saving migration to {migration_file}")
    
    def _get_element_type(self, element_id: str) -> str:
        """Get type of element (mock)"""
        return "text"  # Mock implementation
    
    def _is_type_compatible(self, element_type: str, plan: MigrationPlan) -> bool:
        """Check if element type is compatible with migration (mock)"""
        return True  # Mock implementation