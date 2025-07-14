"""
Configuration models using Pydantic for validation and type safety.
"""

from typing import Optional, Dict, Any, List, Set
from pathlib import Path
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict as PydanticConfigDict
from datetime import timedelta

from .types import ConfigDict


class BaseConfig(BaseModel):
    """Base configuration model with common functionality."""
    
    model_config = PydanticConfigDict(
        validate_assignment=True,
        use_enum_values=True,
        extra="forbid"  # Strict mode - no extra fields allowed
    )
    
    def to_dict(self) -> ConfigDict:
        """Convert configuration to dictionary."""
        return self.model_dump(exclude_unset=False)
    
    def merge(self, other: Dict[str, Any]) -> None:
        """Merge other configuration into this one."""
        for key, value in other.items():
            if hasattr(self, key):
                current = getattr(self, key)
                if isinstance(current, BaseConfig) and isinstance(value, dict):
                    current.merge(value)
                else:
                    setattr(self, key, value)


class LoggingConfig(BaseConfig):
    """Logging configuration."""
    
    level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file: Optional[Path] = None
    console: bool = True
    rotation_size: Optional[int] = Field(None, gt=0, description="Max log file size in MB")
    retention_days: Optional[int] = Field(None, gt=0)
    
    @field_validator("file", mode="before")
    @classmethod
    def validate_file(cls, v):
        """Convert string to Path."""
        if v is not None and not isinstance(v, Path):
            return Path(v)
        return v


class DatabaseConfig(BaseConfig):
    """Database configuration."""
    
    type: str = Field(default="sqlite", pattern="^(sqlite|postgresql|mongodb)$")
    host: str = Field(default="localhost")
    port: int = Field(default=5432, ge=1, le=65535)
    name: str = Field(default="torematrix")
    user: Optional[str] = None
    password: Optional[str] = None
    
    # Connection pool settings
    pool_size: int = Field(default=10, ge=1, le=100)
    max_overflow: int = Field(default=20, ge=0)
    pool_timeout: int = Field(default=30, ge=1)
    
    # SQLite specific
    sqlite_path: Path = Field(default=Path("data/torematrix.db"))
    
    @model_validator(mode="after")
    def validate_database_config(self):
        """Validate database configuration based on type."""
        # For SQLite, we just validate that settings are appropriate
        # We don't modify them here to avoid recursion with validate_assignment
        if self.type in ["postgresql", "mongodb"]:
            # These require proper connection settings
            if not self.user:
                raise ValueError(f"{self.type} requires a username")
        
        return self
    
    @field_validator("sqlite_path", mode="before")
    @classmethod
    def validate_sqlite_path(cls, v):
        """Convert string to Path."""
        if not isinstance(v, Path):
            return Path(v)
        return v


class CacheConfig(BaseConfig):
    """Cache configuration."""
    
    enabled: bool = True
    type: str = Field(default="memory", pattern="^(memory|disk|redis)$")
    
    # Memory cache settings
    max_memory_mb: int = Field(default=512, ge=1)
    ttl_seconds: int = Field(default=3600, ge=0)
    
    # Disk cache settings
    disk_path: Path = Field(default=Path("cache/"))
    max_disk_gb: float = Field(default=10.0, gt=0)
    
    # Redis settings
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_db: int = Field(default=0, ge=0)
    redis_password: Optional[str] = None
    
    @field_validator("disk_path", mode="before")
    @classmethod
    def validate_disk_path(cls, v):
        """Convert string to Path."""
        if not isinstance(v, Path):
            return Path(v)
        return v


class ProcessingConfig(BaseConfig):
    """Document processing configuration."""
    
    max_file_size_mb: int = Field(default=100, gt=0)
    supported_formats: Set[str] = Field(
        default={"pdf", "docx", "odt", "rtf", "txt"}
    )
    
    # OCR settings
    enable_ocr: bool = True
    ocr_language: str = Field(default="eng")
    ocr_dpi: int = Field(default=300, ge=72, le=600)
    
    # Processing limits
    max_pages: Optional[int] = Field(None, gt=0)
    timeout_seconds: int = Field(default=300, gt=0)
    max_concurrent_jobs: int = Field(default=4, ge=1, le=32)
    
    # Quality settings
    min_confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    enable_validation: bool = True
    
    @field_validator("supported_formats", mode="before")
    @classmethod
    def validate_formats(cls, v):
        """Ensure formats are lowercase."""
        if isinstance(v, list):
            v = set(v)
        return {fmt.lower() for fmt in v}


class UIConfig(BaseConfig):
    """User interface configuration."""
    
    theme: str = Field(default="light", pattern="^(light|dark|auto)$")
    language: str = Field(default="en", pattern="^[a-z]{2}(-[A-Z]{2})?$")
    font_size: int = Field(default=12, ge=8, le=24)
    
    # Layout settings
    sidebar_width: int = Field(default=300, ge=200, le=600)
    show_toolbar: bool = True
    show_statusbar: bool = True
    
    # Behavior settings
    auto_save: bool = True
    auto_save_interval: int = Field(default=60, ge=10)
    confirm_exit: bool = True
    remember_layout: bool = True
    
    # Advanced settings
    enable_animations: bool = True
    hardware_acceleration: bool = True
    debug_mode: bool = False


class SecurityConfig(BaseConfig):
    """Security configuration."""
    
    enable_authentication: bool = False
    session_timeout_minutes: int = Field(default=30, gt=0)
    max_login_attempts: int = Field(default=5, gt=0)
    
    # Encryption settings
    encrypt_sensitive_data: bool = True
    encryption_algorithm: str = Field(default="AES-256-GCM")
    
    # API security
    api_rate_limit: int = Field(default=100, gt=0, description="Requests per minute")
    enable_cors: bool = False
    allowed_origins: List[str] = Field(default_factory=list)
    
    # File security
    allowed_upload_extensions: Set[str] = Field(
        default={"pdf", "docx", "odt", "rtf", "txt", "png", "jpg", "jpeg"}
    )
    max_upload_size_mb: int = Field(default=50, gt=0)
    scan_uploads: bool = True
    
    @field_validator("allowed_upload_extensions", mode="before")
    @classmethod
    def validate_extensions(cls, v):
        """Ensure extensions are lowercase without dots."""
        if isinstance(v, list):
            v = set(v)
        return {ext.lower().lstrip('.') for ext in v}


class PerformanceConfig(BaseConfig):
    """Performance tuning configuration."""
    
    # Threading settings
    worker_threads: int = Field(default=4, ge=1, le=32)
    io_threads: int = Field(default=2, ge=1, le=8)
    
    # Queue settings
    max_queue_size: int = Field(default=1000, gt=0)
    queue_timeout_seconds: int = Field(default=30, gt=0)
    
    # Memory settings
    max_memory_usage_percent: int = Field(default=80, ge=50, le=95)
    garbage_collection_interval: int = Field(default=300, gt=0)
    
    # Profiling
    enable_profiling: bool = False
    profile_output_dir: Path = Field(default=Path("profiles/"))
    
    @field_validator("profile_output_dir", mode="before")
    @classmethod
    def validate_profile_dir(cls, v):
        """Convert string to Path."""
        if not isinstance(v, Path):
            return Path(v)
        return v


class FeatureFlags(BaseConfig):
    """Feature flags for gradual rollout."""
    
    # Core features
    enable_hot_reload: bool = True
    enable_auto_migration: bool = False
    enable_experimental_parsers: bool = False
    
    # Processing features
    enable_parallel_processing: bool = True
    enable_smart_caching: bool = True
    enable_incremental_updates: bool = False
    
    # UI features
    enable_dark_mode: bool = True
    enable_advanced_search: bool = True
    enable_batch_operations: bool = True
    
    # Integration features
    enable_api_v2: bool = False
    enable_webhook_notifications: bool = False
    enable_external_storage: bool = False


class ApplicationConfig(BaseConfig):
    """Main application configuration."""
    
    # Basic settings
    app_name: str = Field(default="TORE Matrix Labs V3")
    version: str = Field(default="3.0.0")
    environment: str = Field(
        default="development",
        pattern="^(development|testing|staging|production)$"
    )
    debug: bool = Field(default=True)  # Default to True for development
    
    # Sub-configurations
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    
    # Paths
    data_dir: Path = Field(default=Path("data/"))
    temp_dir: Path = Field(default=Path("temp/"))
    log_dir: Path = Field(default=Path("logs/"))
    
    @field_validator("data_dir", "temp_dir", "log_dir", mode="before")
    @classmethod
    def validate_paths(cls, v):
        """Convert strings to Path objects."""
        if not isinstance(v, Path):
            return Path(v)
        return v
    
    def __init__(self, **data):
        """Initialize with environment-specific defaults."""
        # Apply environment-specific defaults before initialization
        if data.get("environment") == "production":
            # Force certain settings in production
            data.setdefault("debug", False)
            
            # Update nested configs if not explicitly set
            if "logging" not in data:
                data["logging"] = {"level": "WARNING"}
            elif isinstance(data["logging"], dict) and "level" not in data["logging"]:
                data["logging"]["level"] = "WARNING"
                
            if "security" not in data:
                data["security"] = {
                    "enable_authentication": True,
                    "encrypt_sensitive_data": True
                }
            elif isinstance(data["security"], dict):
                data["security"].setdefault("enable_authentication", True)
                data["security"].setdefault("encrypt_sensitive_data", True)
                
            if "performance" not in data:
                data["performance"] = {"enable_profiling": False}
            elif isinstance(data["performance"], dict):
                data["performance"].setdefault("enable_profiling", False)
                
        elif data.get("environment") == "development":
            # Default to debug mode in development
            data.setdefault("debug", True)
        
        # Call parent initialization
        super().__init__(**data)
    
    def validate(self) -> List[str]:
        """Validate entire configuration."""
        errors = []
        
        # Check paths exist or can be created
        for path_field in ["data_dir", "temp_dir", "log_dir"]:
            path = getattr(self, path_field)
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create {path_field} at {path}: {e}")
        
        # Validate database connection if not sqlite
        if self.database.type != "sqlite":
            if not self.database.password:
                errors.append(f"Database password required for {self.database.type}")
        
        # Validate cache settings
        if self.cache.type == "redis" and self.cache.enabled:
            if not self.cache.redis_host:
                errors.append("Redis host required when Redis cache is enabled")
        
        # Check feature compatibility
        if self.features.enable_hot_reload and not self.features.enable_smart_caching:
            errors.append("Hot reload requires smart caching to be enabled")
        
        return errors