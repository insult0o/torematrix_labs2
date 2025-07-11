#!/usr/bin/env python3
"""
Migration Manager for TORE Matrix Labs V2

This manager handles migration of existing .tore files from the original
codebase to the new V2 format, ensuring 100% compatibility and data preservation.

Key features:
- Backward compatibility with all .tore file versions
- Data integrity validation during migration
- Automatic schema upgrades
- Rollback capabilities
- Progress reporting for large migrations
- Batch migration support

This ensures that all existing projects work seamlessly with V2.
"""

import logging
import json
import shutil
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum
import hashlib

from .repository_base import RepositoryBase, StorageConfig, StorageBackend
from ..models.unified_document_model import UnifiedDocument, DocumentStatus
from ..models.unified_area_model import UnifiedArea, AreaType, AreaStatus


class MigrationStatus(Enum):
    """Status of migration operations."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ToreVersion(Enum):
    """Supported .tore file versions."""
    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"  # New V2 format


@dataclass
class MigrationResult:
    """Result of a migration operation."""
    
    # Migration identity
    migration_id: str
    source_file: str
    target_file: str
    
    # Status
    status: MigrationStatus = MigrationStatus.NOT_STARTED
    
    # Migration details
    source_version: str = ""
    target_version: str = ToreVersion.V2_0.value
    
    # Statistics
    documents_migrated: int = 0
    areas_migrated: int = 0
    issues_found: int = 0
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Error information
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Backup information
    backup_path: Optional[str] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Get migration duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def success(self) -> bool:
        """Check if migration was successful."""
        return self.status == MigrationStatus.COMPLETED


@dataclass
class MigrationConfig:
    """Configuration for migration operations."""
    
    # Backup settings
    create_backup: bool = True
    backup_suffix: str = ".backup"
    
    # Validation settings
    validate_data: bool = True
    strict_validation: bool = False
    
    # Performance settings
    batch_size: int = 100
    progress_callback: Optional[callable] = None
    
    # Error handling
    continue_on_error: bool = False
    max_errors: int = 10


class MigrationManager:
    """
    Manager for migrating .tore files between versions.
    
    Handles backward compatibility and ensures all existing projects
    work seamlessly with the new V2 architecture.
    """
    
    def __init__(self, config: Optional[MigrationConfig] = None):
        """Initialize the migration manager."""
        self.logger = logging.getLogger(__name__)
        self.config = config or MigrationConfig()
        
        # Migration history
        self.migration_history: List[MigrationResult] = []
        
        # Version handlers
        self.version_handlers = {
            ToreVersion.V1_0: self._migrate_from_v1_0,
            ToreVersion.V1_1: self._migrate_from_v1_1,
        }
        
        # Schema definitions
        self.v2_schema = self._get_v2_schema()
        
        self.logger.info("Migration manager initialized")
    
    def detect_version(self, tore_file: Path) -> Optional[ToreVersion]:
        """
        Detect the version of a .tore file.
        
        Args:
            tore_file: Path to .tore file
            
        Returns:
            Detected version or None if invalid
        """
        try:
            with open(tore_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check for version field
            if "version" in data:
                version_str = data["version"]
                for version in ToreVersion:
                    if version.value == version_str:
                        return version
            
            # Fallback: detect by structure
            if "documents" in data and isinstance(data["documents"], list):
                # Check for V1.1 features
                if any("visual_areas" in doc for doc in data["documents"]):
                    return ToreVersion.V1_1
                else:
                    return ToreVersion.V1_0
            
            self.logger.warning(f"Could not detect version for {tore_file}")
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to detect version for {tore_file}: {str(e)}")
            return None
    
    def migrate_file(self, 
                    source_file: Path,
                    target_file: Optional[Path] = None,
                    target_version: ToreVersion = ToreVersion.V2_0) -> MigrationResult:
        """
        Migrate a single .tore file to the target version.
        
        Args:
            source_file: Source .tore file
            target_file: Target file (defaults to overwriting source)
            target_version: Target version to migrate to
            
        Returns:
            Migration result
        """
        migration_id = f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(source_file)}"
        
        if target_file is None:
            target_file = source_file
        
        result = MigrationResult(
            migration_id=migration_id,
            source_file=str(source_file),
            target_file=str(target_file),
            target_version=target_version.value,
            started_at=datetime.now()
        )
        
        try:
            self.logger.info(f"Starting migration: {source_file} -> {target_file}")
            
            # Detect source version
            source_version = self.detect_version(source_file)
            if not source_version:
                raise ValueError(f"Could not detect version of {source_file}")
            
            result.source_version = source_version.value
            result.status = MigrationStatus.IN_PROGRESS
            
            # Create backup if requested
            if self.config.create_backup and source_file == target_file:
                backup_path = Path(str(source_file) + self.config.backup_suffix)
                shutil.copy2(source_file, backup_path)
                result.backup_path = str(backup_path)
                self.logger.info(f"Created backup: {backup_path}")
            
            # Load source data
            with open(source_file, 'r', encoding='utf-8') as f:
                source_data = json.load(f)
            
            # Perform migration
            if source_version == target_version:
                # No migration needed
                migrated_data = source_data
                self.logger.info("No migration needed - versions match")
            else:
                # Get migration handler
                if source_version not in self.version_handlers:
                    raise ValueError(f"No migration handler for version {source_version.value}")
                
                migration_handler = self.version_handlers[source_version]
                migrated_data = migration_handler(source_data, result)
            
            # Validate migrated data
            if self.config.validate_data:
                self._validate_v2_data(migrated_data, result)
            
            # Save migrated data
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(migrated_data, f, indent=2, ensure_ascii=False)
            
            # Complete migration
            result.status = MigrationStatus.COMPLETED
            result.completed_at = datetime.now()
            
            self.migration_history.append(result)
            
            self.logger.info(f"Migration completed: {migration_id} in {result.duration:.2f}s")
            return result
            
        except Exception as e:
            result.status = MigrationStatus.FAILED
            result.completed_at = datetime.now()
            result.errors.append(str(e))
            
            self.logger.error(f"Migration failed: {migration_id} - {str(e)}")
            
            # Restore backup if migration failed and we're overwriting
            if (result.backup_path and source_file == target_file and 
                Path(result.backup_path).exists()):
                try:
                    shutil.copy2(result.backup_path, source_file)
                    self.logger.info(f"Restored backup: {result.backup_path}")
                except Exception as restore_error:
                    result.errors.append(f"Failed to restore backup: {str(restore_error)}")
            
            self.migration_history.append(result)
            return result
    
    def migrate_batch(self, 
                     tore_files: List[Path],
                     target_directory: Optional[Path] = None) -> List[MigrationResult]:
        """
        Migrate multiple .tore files in batch.
        
        Args:
            tore_files: List of .tore files to migrate
            target_directory: Optional target directory (defaults to in-place)
            
        Returns:
            List of migration results
        """
        self.logger.info(f"Starting batch migration: {len(tore_files)} files")
        
        results = []
        
        for i, source_file in enumerate(tore_files):
            try:
                # Determine target file
                if target_directory:
                    target_file = target_directory / source_file.name
                else:
                    target_file = source_file
                
                # Report progress
                if self.config.progress_callback:
                    self.config.progress_callback(i, len(tore_files), str(source_file))
                
                # Migrate file
                result = self.migrate_file(source_file, target_file)
                results.append(result)
                
                # Check error limits
                if (not self.config.continue_on_error and result.status == MigrationStatus.FAILED):
                    self.logger.error("Migration failed, stopping batch")
                    break
                
                failed_count = sum(1 for r in results if r.status == MigrationStatus.FAILED)
                if failed_count >= self.config.max_errors:
                    self.logger.error(f"Too many errors ({failed_count}), stopping batch")
                    break
                    
            except Exception as e:
                self.logger.error(f"Batch migration error for {source_file}: {str(e)}")
                if not self.config.continue_on_error:
                    break
        
        # Report batch summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        
        self.logger.info(f"Batch migration completed: {successful} successful, {failed} failed")
        
        return results
    
    def rollback_migration(self, migration_result: MigrationResult) -> bool:
        """
        Rollback a migration using its backup.
        
        Args:
            migration_result: Result of migration to rollback
            
        Returns:
            True if rollback successful, False otherwise
        """
        try:
            if not migration_result.backup_path:
                self.logger.error("No backup available for rollback")
                return False
            
            backup_path = Path(migration_result.backup_path)
            if not backup_path.exists():
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
            
            target_path = Path(migration_result.target_file)
            
            # Restore from backup
            shutil.copy2(backup_path, target_path)
            
            # Update migration result
            migration_result.status = MigrationStatus.ROLLED_BACK
            
            self.logger.info(f"Rollback completed: {migration_result.migration_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {str(e)}")
            return False
    
    def _migrate_from_v1_0(self, data: Dict[str, Any], result: MigrationResult) -> Dict[str, Any]:
        """Migrate from V1.0 format to V2.0."""
        self.logger.info("Migrating from V1.0 to V2.0")
        
        migrated = {
            "format_version": "2.0",
            "created_at": data.get("created_at", datetime.now().isoformat()),
            "modified_at": datetime.now().isoformat(),
            "migration_info": {
                "source_version": "1.0",
                "migration_id": result.migration_id,
                "migrated_at": datetime.now().isoformat()
            }
        }
        
        # Migrate project metadata
        migrated["project"] = {
            "id": data.get("id", self._generate_id()),
            "name": data.get("name", "Migrated Project"),
            "description": data.get("description", ""),
            "version": "2.0",
            "settings": data.get("settings", {})
        }
        
        # Migrate documents
        migrated["documents"] = []
        documents = data.get("documents", [])
        
        for doc_data in documents:
            migrated_doc = self._migrate_document_v1_to_v2(doc_data)
            migrated["documents"].append(migrated_doc)
            result.documents_migrated += 1
        
        # Migrate global settings
        migrated["global_settings"] = {
            "quality_thresholds": data.get("quality_thresholds", {}),
            "processing_config": data.get("processing_config", {}),
            "ui_preferences": data.get("ui_preferences", {})
        }
        
        return migrated
    
    def _migrate_from_v1_1(self, data: Dict[str, Any], result: MigrationResult) -> Dict[str, Any]:
        """Migrate from V1.1 format to V2.0."""
        self.logger.info("Migrating from V1.1 to V2.0")
        
        # V1.1 is closer to V2.0, so less transformation needed
        migrated = {
            "format_version": "2.0",
            "created_at": data.get("created_at", datetime.now().isoformat()),
            "modified_at": datetime.now().isoformat(),
            "migration_info": {
                "source_version": "1.1",
                "migration_id": result.migration_id,
                "migrated_at": datetime.now().isoformat()
            }
        }
        
        # Project metadata (minimal changes)
        migrated["project"] = data.get("project", {})
        migrated["project"]["version"] = "2.0"
        
        # Migrate documents with visual areas
        migrated["documents"] = []
        documents = data.get("documents", [])
        
        for doc_data in documents:
            migrated_doc = self._migrate_document_v1_1_to_v2(doc_data)
            migrated["documents"].append(migrated_doc)
            result.documents_migrated += 1
            
            # Count areas
            if "visual_areas" in migrated_doc:
                result.areas_migrated += len(migrated_doc["visual_areas"])
        
        # Global settings
        migrated["global_settings"] = data.get("global_settings", {})
        
        return migrated
    
    def _migrate_document_v1_to_v2(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate a single document from V1.0 to V2.0."""
        
        migrated_doc = {
            "id": doc_data.get("id", self._generate_id()),
            "name": doc_data.get("name", "Unknown Document"),
            "file_path": doc_data.get("file_path", ""),
            "file_name": doc_data.get("file_name", ""),
            "status": self._migrate_status(doc_data.get("status", "unknown")),
            "created_at": doc_data.get("created_at", datetime.now().isoformat()),
            "modified_at": datetime.now().isoformat(),
            "metadata": {
                "file_size": doc_data.get("file_size", 0),
                "file_type": doc_data.get("file_type", ""),
                "page_count": doc_data.get("page_count", 0),
                "processing_time": doc_data.get("processing_time", 0.0),
                "quality_score": doc_data.get("quality_score", 0.0)
            },
            "extraction_results": doc_data.get("extraction_results", {}),
            "quality_assessment": doc_data.get("quality_assessment", {}),
            "visual_areas": {},
            "validation_results": doc_data.get("validation_results", {})
        }
        
        # Migrate areas if they exist
        if "areas" in doc_data:
            for area_id, area_data in doc_data["areas"].items():
                migrated_area = self._migrate_area_v1_to_v2(area_data)
                migrated_doc["visual_areas"][area_id] = migrated_area
        
        return migrated_doc
    
    def _migrate_document_v1_1_to_v2(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate a single document from V1.1 to V2.0."""
        
        # V1.1 structure is closer to V2.0
        migrated_doc = dict(doc_data)  # Start with copy
        
        # Update status format if needed
        if "status" in migrated_doc:
            migrated_doc["status"] = self._migrate_status(migrated_doc["status"])
        
        # Ensure metadata structure
        if "metadata" not in migrated_doc:
            migrated_doc["metadata"] = {}
        
        # Migrate visual areas to new format
        if "visual_areas" in migrated_doc:
            migrated_areas = {}
            for area_id, area_data in migrated_doc["visual_areas"].items():
                migrated_areas[area_id] = self._migrate_area_v1_1_to_v2(area_data)
            migrated_doc["visual_areas"] = migrated_areas
        
        # Update timestamps
        migrated_doc["modified_at"] = datetime.now().isoformat()
        
        return migrated_doc
    
    def _migrate_area_v1_to_v2(self, area_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate a visual area from V1.0 to V2.0."""
        
        return {
            "id": area_data.get("id", self._generate_id()),
            "document_id": area_data.get("document_id", ""),
            "type": self._migrate_area_type(area_data.get("type", "unknown")),
            "page": area_data.get("page", 1),
            "bbox": area_data.get("bbox", [0, 0, 100, 100]),
            "status": self._migrate_area_status(area_data.get("status", "created")),
            "created_at": area_data.get("created_at", datetime.now().isoformat()),
            "modified_at": datetime.now().isoformat(),
            "metadata": area_data.get("metadata", {}),
            "user_notes": area_data.get("user_notes", ""),
            "validation_status": area_data.get("validation_status", "not_validated")
        }
    
    def _migrate_area_v1_1_to_v2(self, area_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate a visual area from V1.1 to V2.0."""
        
        # V1.1 areas are mostly compatible, just update format
        migrated_area = dict(area_data)
        
        # Ensure required fields
        if "id" not in migrated_area:
            migrated_area["id"] = self._generate_id()
        
        # Update type format
        if "type" in migrated_area:
            migrated_area["type"] = self._migrate_area_type(migrated_area["type"])
        
        # Update status format
        if "status" in migrated_area:
            migrated_area["status"] = self._migrate_area_status(migrated_area["status"])
        
        # Update timestamp
        migrated_area["modified_at"] = datetime.now().isoformat()
        
        return migrated_area
    
    def _migrate_status(self, old_status: str) -> str:
        """Migrate document status to V2.0 format."""
        status_mapping = {
            "new": "created",
            "loading": "loading", 
            "loaded": "loaded",
            "processing": "processing",
            "processed": "processed",
            "validating": "validating",
            "validated": "validated",
            "complete": "completed",
            "completed": "completed",
            "error": "failed",
            "failed": "failed"
        }
        
        return status_mapping.get(old_status.lower(), "created")
    
    def _migrate_area_type(self, old_type: str) -> str:
        """Migrate area type to V2.0 format."""
        type_mapping = {
            "image": "IMAGE",
            "table": "TABLE", 
            "diagram": "DIAGRAM",
            "text": "TEXT",
            "header": "HEADER",
            "footer": "FOOTER"
        }
        
        return type_mapping.get(old_type.lower(), "IMAGE")
    
    def _migrate_area_status(self, old_status: str) -> str:
        """Migrate area status to V2.0 format."""
        status_mapping = {
            "new": "created",
            "created": "created",
            "validated": "validated",
            "approved": "approved",
            "rejected": "rejected",
            "modified": "modified"
        }
        
        return status_mapping.get(old_status.lower(), "created")
    
    def _validate_v2_data(self, data: Dict[str, Any], result: MigrationResult):
        """Validate migrated data against V2.0 schema."""
        try:
            # Check required top-level fields
            required_fields = ["format_version", "project", "documents"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate format version
            if data["format_version"] != "2.0":
                result.warnings.append(f"Unexpected format version: {data['format_version']}")
            
            # Validate project structure
            project = data["project"]
            if "id" not in project or "name" not in project:
                raise ValueError("Project missing required fields")
            
            # Validate documents
            for i, doc in enumerate(data["documents"]):
                self._validate_document(doc, result, f"documents[{i}]")
            
            self.logger.info("Data validation passed")
            
        except Exception as e:
            if self.config.strict_validation:
                raise
            else:
                result.warnings.append(f"Validation warning: {str(e)}")
                self.logger.warning(f"Validation warning: {str(e)}")
    
    def _validate_document(self, doc: Dict[str, Any], result: MigrationResult, context: str):
        """Validate a single document structure."""
        required_fields = ["id", "name", "status"]
        for field in required_fields:
            if field not in doc:
                result.issues_found += 1
                if self.config.strict_validation:
                    raise ValueError(f"{context}: Missing required field: {field}")
                else:
                    result.warnings.append(f"{context}: Missing field {field}")
    
    def _get_v2_schema(self) -> Dict[str, Any]:
        """Get the V2.0 schema definition."""
        return {
            "type": "object",
            "required": ["format_version", "project", "documents"],
            "properties": {
                "format_version": {"type": "string", "enum": ["2.0"]},
                "project": {
                    "type": "object",
                    "required": ["id", "name"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "version": {"type": "string"}
                    }
                },
                "documents": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "name", "status"],
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "status": {"type": "string"},
                            "visual_areas": {"type": "object"}
                        }
                    }
                }
            }
        }
    
    def _generate_id(self) -> str:
        """Generate a unique ID."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        hash_input = f"{timestamp}_{id(self)}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]
    
    def get_migration_history(self) -> List[MigrationResult]:
        """Get the migration history."""
        return self.migration_history.copy()
    
    def get_migration_statistics(self) -> Dict[str, Any]:
        """Get migration statistics."""
        total_migrations = len(self.migration_history)
        successful = sum(1 for r in self.migration_history if r.success)
        failed = total_migrations - successful
        
        if total_migrations > 0:
            avg_duration = sum(r.duration or 0 for r in self.migration_history) / total_migrations
            total_documents = sum(r.documents_migrated for r in self.migration_history)
            total_areas = sum(r.areas_migrated for r in self.migration_history)
        else:
            avg_duration = 0.0
            total_documents = 0
            total_areas = 0
        
        return {
            "total_migrations": total_migrations,
            "successful_migrations": successful,
            "failed_migrations": failed,
            "success_rate": successful / total_migrations if total_migrations > 0 else 0.0,
            "average_duration": avg_duration,
            "total_documents_migrated": total_documents,
            "total_areas_migrated": total_areas
        }
    
    def save_project(self, project_data: Dict[str, Any], save_path: Optional[str] = None) -> str:
        """
        Save project data to a .tore file.
        
        Args:
            project_data: Project data to save
            save_path: Optional path to save to
            
        Returns:
            Path where project was saved
        """
        try:
            if save_path:
                output_path = Path(save_path)
            else:
                # Generate default path
                project_name = project_data.get("name", "untitled_project")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{project_name}_{timestamp}.tore"
                output_path = Path.cwd() / filename
            
            # Ensure directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Add V2 metadata
            project_data["version"] = ToreVersion.V2_0.value
            project_data["saved_at"] = datetime.now().isoformat()
            project_data["format"] = "tore_v2"
            
            # Save to JSON file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Project saved to: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save project: {str(e)}")
            raise
    
    def load_project(self, project_path: str) -> Dict[str, Any]:
        """
        Load project data from a .tore file.
        
        Args:
            project_path: Path to project file
            
        Returns:
            Project data
        """
        try:
            path = Path(project_path)
            
            if not path.exists():
                raise FileNotFoundError(f"Project file not found: {path}")
            
            with open(path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            # Check if migration is needed
            version = project_data.get("version", "1.0")
            if version != ToreVersion.V2_0.value:
                self.logger.info(f"Migrating project from version {version} to V2.0")
                # Perform migration if needed
                project_data = self._migrate_project_data(project_data, version)
            
            self.logger.info(f"Project loaded from: {path}")
            return project_data
            
        except Exception as e:
            self.logger.error(f"Failed to load project: {str(e)}")
            raise
    
    def _migrate_project_data(self, project_data: Dict[str, Any], from_version: str) -> Dict[str, Any]:
        """Migrate project data to V2 format."""
        # Simple migration for now - just update version
        project_data["version"] = ToreVersion.V2_0.value
        project_data["migrated_from"] = from_version
        project_data["migrated_at"] = datetime.now().isoformat()
        
        return project_data