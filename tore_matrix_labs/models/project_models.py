"""
Project management models for TORE Matrix Labs.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import uuid

from config.constants import ProcessingStatus, ExportFormat


class ProjectStatus(Enum):
    """Project status enumeration."""
    DRAFT = "draft"
    ACTIVE = "active"
    PROCESSING = "processing"
    REVIEW = "review"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass
class ProjectSettings:
    """Project-specific settings."""
    auto_process: bool = True
    require_validation: bool = True
    quality_threshold: float = 0.8
    chunk_size: int = 512
    chunk_overlap: int = 50
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    export_format: ExportFormat = ExportFormat.JSONL
    custom_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectStatistics:
    """Project statistics and metrics."""
    total_documents: int = 0
    processed_documents: int = 0
    validated_documents: int = 0
    approved_documents: int = 0
    total_pages: int = 0
    total_chunks: int = 0
    total_tables: int = 0
    total_images: int = 0
    avg_quality_score: float = 0.0
    processing_time: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if isinstance(self.last_updated, str):
            self.last_updated = datetime.fromisoformat(self.last_updated)
    
    def update_stats(self, documents: List[Any]):
        """Update statistics based on document list."""
        self.total_documents = len(documents)
        self.processed_documents = sum(1 for doc in documents if doc.processing_status in [
            ProcessingStatus.EXTRACTED, ProcessingStatus.VALIDATING, 
            ProcessingStatus.CORRECTING, ProcessingStatus.APPROVED, ProcessingStatus.EXPORTED
        ])
        self.validated_documents = sum(1 for doc in documents if doc.get_latest_validation())
        self.approved_documents = sum(1 for doc in documents if doc.is_approved())
        self.total_pages = sum(doc.metadata.page_count for doc in documents)
        
        if documents:
            self.avg_quality_score = sum(doc.quality_score for doc in documents) / len(documents)
            self.processing_time = sum(doc.get_processing_time() for doc in documents)
        
        self.last_updated = datetime.now()


@dataclass
class ExportConfiguration:
    """Export configuration settings."""
    id: str
    name: str
    format: ExportFormat
    include_metadata: bool = True
    include_images: bool = True
    include_tables: bool = True
    chunk_by_page: bool = False
    max_chunk_size: int = 512
    output_directory: str = "exports"
    filename_template: str = "{project_name}_{timestamp}"
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class ValidationRule:
    """Validation rule for project."""
    id: str
    name: str
    rule_type: str  # 'quality_threshold', 'required_fields', 'pattern_match'
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    severity: str = "warning"  # 'error', 'warning', 'info'
    description: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class ProjectBackup:
    """Project backup information."""
    id: str
    project_id: str
    backup_date: datetime
    backup_path: str
    backup_size: int
    backup_type: str  # 'manual', 'automatic', 'milestone'
    description: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if isinstance(self.backup_date, str):
            self.backup_date = datetime.fromisoformat(self.backup_date)


@dataclass
class ProjectMember:
    """Project team member."""
    id: str
    name: str
    email: str
    role: str  # 'admin', 'editor', 'validator', 'viewer'
    joined_at: datetime = field(default_factory=datetime.now)
    permissions: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if isinstance(self.joined_at, str):
            self.joined_at = datetime.fromisoformat(self.joined_at)
    
    def has_permission(self, permission: str) -> bool:
        """Check if member has specific permission."""
        return permission in self.permissions or self.role == 'admin'


@dataclass
class ProjectActivity:
    """Project activity log entry."""
    id: str
    project_id: str
    user_id: str
    activity_type: str  # 'document_added', 'document_processed', 'validation_completed', etc.
    description: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)


@dataclass
class Project:
    """Main project model."""
    id: str
    name: str
    description: str
    status: ProjectStatus
    settings: ProjectSettings
    statistics: ProjectStatistics
    document_ids: List[str] = field(default_factory=list)
    export_configurations: List[ExportConfiguration] = field(default_factory=list)
    validation_rules: List[ValidationRule] = field(default_factory=list)
    members: List[ProjectMember] = field(default_factory=list)
    activities: List[ProjectActivity] = field(default_factory=list)
    backups: List[ProjectBackup] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    tags: List[str] = field(default_factory=list)
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
    
    def add_document(self, document_id: str):
        """Add document to project."""
        if document_id not in self.document_ids:
            self.document_ids.append(document_id)
            self.updated_at = datetime.now()
    
    def remove_document(self, document_id: str):
        """Remove document from project."""
        if document_id in self.document_ids:
            self.document_ids.remove(document_id)
            self.updated_at = datetime.now()
    
    def add_member(self, member: ProjectMember):
        """Add team member to project."""
        self.members.append(member)
        self.updated_at = datetime.now()
    
    def remove_member(self, member_id: str):
        """Remove team member from project."""
        self.members = [m for m in self.members if m.id != member_id]
        self.updated_at = datetime.now()
    
    def get_member(self, member_id: str) -> Optional[ProjectMember]:
        """Get team member by ID."""
        for member in self.members:
            if member.id == member_id:
                return member
        return None
    
    def add_activity(self, activity: ProjectActivity):
        """Add activity to project log."""
        self.activities.append(activity)
        self.updated_at = datetime.now()
    
    def add_export_configuration(self, config: ExportConfiguration):
        """Add export configuration."""
        self.export_configurations.append(config)
        self.updated_at = datetime.now()
    
    def remove_export_configuration(self, config_id: str):
        """Remove export configuration."""
        self.export_configurations = [c for c in self.export_configurations if c.id != config_id]
        self.updated_at = datetime.now()
    
    def get_export_configuration(self, config_id: str) -> Optional[ExportConfiguration]:
        """Get export configuration by ID."""
        for config in self.export_configurations:
            if config.id == config_id:
                return config
        return None
    
    def add_validation_rule(self, rule: ValidationRule):
        """Add validation rule."""
        self.validation_rules.append(rule)
        self.updated_at = datetime.now()
    
    def remove_validation_rule(self, rule_id: str):
        """Remove validation rule."""
        self.validation_rules = [r for r in self.validation_rules if r.id != rule_id]
        self.updated_at = datetime.now()
    
    def get_enabled_validation_rules(self) -> List[ValidationRule]:
        """Get enabled validation rules."""
        return [rule for rule in self.validation_rules if rule.enabled]
    
    def update_status(self, new_status: ProjectStatus):
        """Update project status."""
        self.status = new_status
        self.updated_at = datetime.now()
    
    def get_completion_percentage(self) -> float:
        """Get project completion percentage."""
        if self.statistics.total_documents == 0:
            return 0.0
        return (self.statistics.approved_documents / self.statistics.total_documents) * 100
    
    def is_ready_for_export(self) -> bool:
        """Check if project is ready for export."""
        return (self.status == ProjectStatus.COMPLETED or 
                self.statistics.approved_documents > 0)
    
    def create_backup(self, backup_path: str, backup_type: str = "manual", description: str = "") -> ProjectBackup:
        """Create project backup."""
        backup = ProjectBackup(
            id=str(uuid.uuid4()),
            project_id=self.id,
            backup_date=datetime.now(),
            backup_path=backup_path,
            backup_size=0,  # Will be calculated by backup system
            backup_type=backup_type,
            description=description
        )
        self.backups.append(backup)
        self.updated_at = datetime.now()
        return backup
    
    def get_recent_activities(self, limit: int = 10) -> List[ProjectActivity]:
        """Get recent project activities."""
        sorted_activities = sorted(self.activities, key=lambda x: x.timestamp, reverse=True)
        return sorted_activities[:limit]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert project to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'created_by': self.created_by,
            'tags': self.tags,
            'custom_metadata': self.custom_metadata,
            'document_count': len(self.document_ids),
            'completion_percentage': self.get_completion_percentage(),
            'statistics': {
                'total_documents': self.statistics.total_documents,
                'processed_documents': self.statistics.processed_documents,
                'validated_documents': self.statistics.validated_documents,
                'approved_documents': self.statistics.approved_documents,
                'total_pages': self.statistics.total_pages,
                'avg_quality_score': self.statistics.avg_quality_score
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Create project from dictionary."""
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            status=ProjectStatus(data['status']),
            settings=ProjectSettings(),
            statistics=ProjectStatistics(),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            created_by=data.get('created_by', ''),
            tags=data.get('tags', []),
            custom_metadata=data.get('custom_metadata', {})
        )


@dataclass
class ProjectTemplate:
    """Project template for quick project creation."""
    id: str
    name: str
    description: str
    settings: ProjectSettings
    validation_rules: List[ValidationRule] = field(default_factory=list)
    export_configurations: List[ExportConfiguration] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
    
    def create_project(self, name: str, description: str, created_by: str) -> Project:
        """Create new project from template."""
        project = Project(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            status=ProjectStatus.DRAFT,
            settings=self.settings,
            statistics=ProjectStatistics(),
            created_by=created_by
        )
        
        # Copy validation rules
        for rule in self.validation_rules:
            new_rule = ValidationRule(
                id=str(uuid.uuid4()),
                name=rule.name,
                rule_type=rule.rule_type,
                parameters=rule.parameters.copy(),
                enabled=rule.enabled,
                severity=rule.severity,
                description=rule.description
            )
            project.validation_rules.append(new_rule)
        
        # Copy export configurations
        for config in self.export_configurations:
            new_config = ExportConfiguration(
                id=str(uuid.uuid4()),
                name=config.name,
                format=config.format,
                include_metadata=config.include_metadata,
                include_images=config.include_images,
                include_tables=config.include_tables,
                chunk_by_page=config.chunk_by_page,
                max_chunk_size=config.max_chunk_size,
                output_directory=config.output_directory,
                filename_template=config.filename_template,
                custom_fields=config.custom_fields.copy()
            )
            project.export_configurations.append(new_config)
        
        return project


# Type aliases for convenience
ProjectID = str
MemberID = str
ActivityID = str
BackupID = str
TemplateID = str