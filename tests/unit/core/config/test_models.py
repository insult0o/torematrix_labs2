"""
Unit tests for configuration models.
"""

import pytest
from pathlib import Path
from pydantic import ValidationError as PydanticValidationError

from torematrix.core.config.models import (
    BaseConfig, LoggingConfig, DatabaseConfig, CacheConfig,
    ProcessingConfig, UIConfig, SecurityConfig, PerformanceConfig,
    FeatureFlags, ApplicationConfig
)


class TestBaseConfig:
    """Test BaseConfig base class."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = BaseConfig()
        assert isinstance(config.to_dict(), dict)
    
    def test_merge(self):
        """Test merging configurations."""
        class TestConfig(BaseConfig):
            value1: str = "default1"
            value2: int = 42
        
        config = TestConfig()
        config.merge({"value1": "updated", "value2": 100})
        
        assert config.value1 == "updated"
        assert config.value2 == 100
    
    def test_no_extra_fields(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(PydanticValidationError):
            BaseConfig(extra_field="not_allowed")


class TestLoggingConfig:
    """Test LoggingConfig model."""
    
    def test_default_values(self):
        """Test default logging configuration."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.console is True
        assert config.file is None
    
    def test_level_validation(self):
        """Test log level validation."""
        config = LoggingConfig(level="DEBUG")
        assert config.level == "DEBUG"
        
        with pytest.raises(PydanticValidationError):
            LoggingConfig(level="INVALID")
    
    def test_file_path_conversion(self):
        """Test string to Path conversion."""
        config = LoggingConfig(file="logs/app.log")
        assert isinstance(config.file, Path)
        assert str(config.file) == "logs/app.log"
    
    def test_rotation_validation(self):
        """Test rotation settings validation."""
        config = LoggingConfig(rotation_size=10, retention_days=7)
        assert config.rotation_size == 10
        assert config.retention_days == 7
        
        with pytest.raises(PydanticValidationError):
            LoggingConfig(rotation_size=-1)


class TestDatabaseConfig:
    """Test DatabaseConfig model."""
    
    def test_default_sqlite_config(self):
        """Test default SQLite configuration."""
        config = DatabaseConfig()
        assert config.type == "sqlite"
        assert config.sqlite_path == Path("data/torematrix.db")
        assert config.user is None
        assert config.password is None
    
    def test_postgresql_config(self):
        """Test PostgreSQL configuration."""
        config = DatabaseConfig(
            type="postgresql",
            host="db.example.com",
            port=5432,
            name="mydb",
            user="dbuser",
            password="secret"
        )
        assert config.type == "postgresql"
        assert config.host == "db.example.com"
        assert config.user == "dbuser"
    
    def test_port_validation(self):
        """Test port number validation."""
        config = DatabaseConfig(port=3306)
        assert config.port == 3306
        
        with pytest.raises(PydanticValidationError):
            DatabaseConfig(port=70000)  # Too high
        
        with pytest.raises(PydanticValidationError):
            DatabaseConfig(port=0)  # Too low
    
    def test_pool_settings(self):
        """Test connection pool settings."""
        config = DatabaseConfig(pool_size=20, max_overflow=10)
        assert config.pool_size == 20
        assert config.max_overflow == 10
        
        with pytest.raises(PydanticValidationError):
            DatabaseConfig(pool_size=200)  # Too high


class TestCacheConfig:
    """Test CacheConfig model."""
    
    def test_default_values(self):
        """Test default cache configuration."""
        config = CacheConfig()
        assert config.enabled is True
        assert config.type == "memory"
        assert config.max_memory_mb == 512
    
    def test_disk_cache_config(self):
        """Test disk cache configuration."""
        config = CacheConfig(
            type="disk",
            disk_path="cache/data",
            max_disk_gb=5.0
        )
        assert config.type == "disk"
        assert config.disk_path == Path("cache/data")
        assert config.max_disk_gb == 5.0
    
    def test_redis_config(self):
        """Test Redis cache configuration."""
        config = CacheConfig(
            type="redis",
            redis_host="redis.example.com",
            redis_port=6380,
            redis_password="secret"
        )
        assert config.type == "redis"
        assert config.redis_host == "redis.example.com"
        assert config.redis_port == 6380


class TestProcessingConfig:
    """Test ProcessingConfig model."""
    
    def test_default_values(self):
        """Test default processing configuration."""
        config = ProcessingConfig()
        assert config.max_file_size_mb == 100
        assert "pdf" in config.supported_formats
        assert config.enable_ocr is True
        assert config.ocr_language == "eng"
    
    def test_format_normalization(self):
        """Test format normalization to lowercase."""
        config = ProcessingConfig(supported_formats=["PDF", "DOCX", "TXT"])
        assert config.supported_formats == {"pdf", "docx", "txt"}
    
    def test_ocr_settings(self):
        """Test OCR settings validation."""
        config = ProcessingConfig(ocr_dpi=150)
        assert config.ocr_dpi == 150
        
        with pytest.raises(PydanticValidationError):
            ProcessingConfig(ocr_dpi=50)  # Too low
    
    def test_confidence_validation(self):
        """Test confidence threshold validation."""
        config = ProcessingConfig(min_confidence=0.95)
        assert config.min_confidence == 0.95
        
        with pytest.raises(PydanticValidationError):
            ProcessingConfig(min_confidence=1.5)  # Too high


class TestUIConfig:
    """Test UIConfig model."""
    
    def test_default_values(self):
        """Test default UI configuration."""
        config = UIConfig()
        assert config.theme == "light"
        assert config.language == "en"
        assert config.font_size == 12
    
    def test_theme_validation(self):
        """Test theme validation."""
        config = UIConfig(theme="dark")
        assert config.theme == "dark"
        
        with pytest.raises(PydanticValidationError):
            UIConfig(theme="invalid")
    
    def test_language_validation(self):
        """Test language code validation."""
        config = UIConfig(language="es")
        assert config.language == "es"
        
        config = UIConfig(language="en-US")
        assert config.language == "en-US"
        
        with pytest.raises(PydanticValidationError):
            UIConfig(language="invalid-code")
    
    def test_layout_settings(self):
        """Test layout settings validation."""
        config = UIConfig(sidebar_width=400)
        assert config.sidebar_width == 400
        
        with pytest.raises(PydanticValidationError):
            UIConfig(sidebar_width=100)  # Too small


class TestSecurityConfig:
    """Test SecurityConfig model."""
    
    def test_default_values(self):
        """Test default security configuration."""
        config = SecurityConfig()
        assert config.enable_authentication is False
        assert config.encrypt_sensitive_data is True
        assert config.api_rate_limit == 100
    
    def test_session_settings(self):
        """Test session settings."""
        config = SecurityConfig(
            enable_authentication=True,
            session_timeout_minutes=60,
            max_login_attempts=3
        )
        assert config.enable_authentication is True
        assert config.session_timeout_minutes == 60
        assert config.max_login_attempts == 3
    
    def test_allowed_extensions_normalization(self):
        """Test file extension normalization."""
        config = SecurityConfig(
            allowed_upload_extensions=[".PDF", "DOCX", ".txt"]
        )
        assert config.allowed_upload_extensions == {"pdf", "docx", "txt"}
    
    def test_cors_settings(self):
        """Test CORS settings."""
        config = SecurityConfig(
            enable_cors=True,
            allowed_origins=["http://localhost:3000", "https://app.example.com"]
        )
        assert config.enable_cors is True
        assert len(config.allowed_origins) == 2


class TestPerformanceConfig:
    """Test PerformanceConfig model."""
    
    def test_default_values(self):
        """Test default performance configuration."""
        config = PerformanceConfig()
        assert config.worker_threads == 4
        assert config.max_memory_usage_percent == 80
        assert config.enable_profiling is False
    
    def test_thread_validation(self):
        """Test thread count validation."""
        config = PerformanceConfig(worker_threads=8, io_threads=4)
        assert config.worker_threads == 8
        assert config.io_threads == 4
        
        with pytest.raises(PydanticValidationError):
            PerformanceConfig(worker_threads=64)  # Too many
    
    def test_memory_validation(self):
        """Test memory usage validation."""
        config = PerformanceConfig(max_memory_usage_percent=90)
        assert config.max_memory_usage_percent == 90
        
        with pytest.raises(PydanticValidationError):
            PerformanceConfig(max_memory_usage_percent=40)  # Too low


class TestFeatureFlags:
    """Test FeatureFlags model."""
    
    def test_default_values(self):
        """Test default feature flags."""
        config = FeatureFlags()
        assert config.enable_hot_reload is True
        assert config.enable_auto_migration is False
        assert config.enable_experimental_parsers is False
    
    def test_flag_updates(self):
        """Test updating feature flags."""
        config = FeatureFlags()
        config.enable_api_v2 = True
        config.enable_webhook_notifications = True
        
        assert config.enable_api_v2 is True
        assert config.enable_webhook_notifications is True


class TestApplicationConfig:
    """Test ApplicationConfig model."""
    
    def test_default_values(self):
        """Test default application configuration."""
        config = ApplicationConfig()
        assert config.app_name == "TORE Matrix Labs V3"
        assert config.version == "3.0.0"
        assert config.environment == "development"
        assert config.debug is False
    
    def test_sub_configurations(self):
        """Test sub-configuration initialization."""
        config = ApplicationConfig()
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.cache, CacheConfig)
        assert isinstance(config.ui, UIConfig)
    
    def test_environment_validation(self):
        """Test environment validation."""
        config = ApplicationConfig(environment="production")
        assert config.environment == "production"
        
        with pytest.raises(PydanticValidationError):
            ApplicationConfig(environment="invalid")
    
    def test_production_settings(self):
        """Test production environment forces certain settings."""
        config = ApplicationConfig(
            environment="production",
            debug=True  # Should be forced to False
        )
        assert config.debug is False
        assert config.logging.level == "WARNING"
        assert config.security.enable_authentication is True
        assert config.security.encrypt_sensitive_data is True
    
    def test_development_settings(self):
        """Test development environment defaults."""
        config = ApplicationConfig(environment="development")
        assert config.debug is True  # Default to True in development
    
    def test_validation_method(self):
        """Test configuration validation."""
        config = ApplicationConfig()
        errors = config.validate()
        assert isinstance(errors, list)
        
        # Test with invalid database config
        config.database.type = "postgresql"
        config.database.password = None
        errors = config.validate()
        assert len(errors) > 0
        assert any("password required" in err for err in errors)
    
    def test_path_creation(self):
        """Test path validation and creation."""
        import tempfile
        import shutil
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config = ApplicationConfig(
                data_dir=temp_path / "data",
                temp_dir=temp_path / "temp",
                log_dir=temp_path / "logs"
            )
            
            # Paths should be created during validation
            errors = config.validate()
            assert len(errors) == 0
            assert config.data_dir.exists()
            assert config.temp_dir.exists()
            assert config.log_dir.exists()
    
    def test_feature_compatibility(self):
        """Test feature flag compatibility validation."""
        config = ApplicationConfig()
        config.features.enable_hot_reload = True
        config.features.enable_smart_caching = False
        
        errors = config.validate()
        assert any("Hot reload requires smart caching" in err for err in errors)