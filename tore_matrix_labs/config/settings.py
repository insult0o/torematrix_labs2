"""
Application settings and configuration management.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
from .constants import QualityLevel

# Load environment variables
load_dotenv()


@dataclass
class ProcessingSettings:
    """Document processing configuration."""
    max_file_size_mb: int = 500
    max_pages_per_document: int = 1000
    concurrent_workers: int = 4
    chunk_size: int = 512
    chunk_overlap: int = 50
    quality_threshold: float = 0.8
    auto_correct_enabled: bool = True
    preserve_formatting: bool = True
    extract_images: bool = True
    extract_tables: bool = True
    default_quality_level: QualityLevel = QualityLevel.GOOD  # Default quality level for new documents


@dataclass
class UISettings:
    """User interface configuration."""
    theme: str = "professional"
    window_width: int = 1400
    window_height: int = 900
    font_size: int = 11
    font_family: str = "Segoe UI"
    auto_save_interval: int = 300  # seconds
    show_preview: bool = True
    enable_animations: bool = True


@dataclass
class DatabaseSettings:
    """Database configuration."""
    type: str = "sqlite"
    path: str = "data/tore_matrix.db"
    backup_enabled: bool = True
    backup_interval: int = 3600  # seconds
    max_backup_files: int = 10


@dataclass
class AISettings:
    """AI/ML integration settings."""
    openai_api_key: str = ""
    huggingface_token: str = ""
    default_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size: int = 32
    max_tokens_per_chunk: int = 8192
    temperature: float = 0.1
    enable_gpu: bool = True


@dataclass
class ExportSettings:
    """Export configuration."""
    default_format: str = "jsonl"
    include_metadata: bool = True
    compress_output: bool = True
    validate_exports: bool = True
    output_directory: str = "exports"


class Settings:
    """Main settings manager."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._get_default_config_path()
        self.config_dir = Path(self.config_file).parent
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize settings with defaults
        self.processing = ProcessingSettings()
        self.ui = UISettings()
        self.database = DatabaseSettings()
        self.ai = AISettings()
        self.export = ExportSettings()
        
        # Load from file if exists
        self.load()
        
        # Update with environment variables
        self._load_from_env()
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        if os.name == 'nt':  # Windows
            config_dir = Path.home() / "AppData" / "Roaming" / "TORE Matrix Labs"
        else:  # Unix-like
            config_dir = Path.home() / ".config" / "tore-matrix-labs"
        
        return str(config_dir / "config.json")
    
    def _load_from_env(self):
        """Load settings from environment variables."""
        # AI settings from environment
        if os.getenv("OPENAI_API_KEY"):
            self.ai.openai_api_key = os.getenv("OPENAI_API_KEY")
        if os.getenv("HUGGINGFACE_TOKEN"):
            self.ai.huggingface_token = os.getenv("HUGGINGFACE_TOKEN")
        
        # Database settings
        if os.getenv("DATABASE_PATH"):
            self.database.path = os.getenv("DATABASE_PATH")
        
        # Processing settings
        if os.getenv("MAX_WORKERS"):
            self.processing.concurrent_workers = int(os.getenv("MAX_WORKERS"))
    
    def load(self):
        """Load settings from configuration file."""
        if not os.path.exists(self.config_file):
            return
        
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            # Update settings from config
            if 'processing' in config_data:
                self.processing = ProcessingSettings(**config_data['processing'])
            if 'ui' in config_data:
                self.ui = UISettings(**config_data['ui'])
            if 'database' in config_data:
                self.database = DatabaseSettings(**config_data['database'])
            if 'ai' in config_data:
                self.ai = AISettings(**config_data['ai'])
            if 'export' in config_data:
                self.export = ExportSettings(**config_data['export'])
                
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
    
    def save(self):
        """Save settings to configuration file."""
        config_data = {
            'processing': asdict(self.processing),
            'ui': asdict(self.ui),
            'database': asdict(self.database),
            'ai': asdict(self.ai),
            'export': asdict(self.export)
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config file: {e}")
    
    def get_data_directory(self) -> Path:
        """Get application data directory."""
        data_dir = Path(self.config_dir) / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    
    def get_temp_directory(self) -> Path:
        """Get temporary files directory."""
        temp_dir = Path(self.config_dir) / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir
    
    def get_export_directory(self) -> Path:
        """Get export directory."""
        export_dir = Path(self.export.output_directory)
        if not export_dir.is_absolute():
            export_dir = self.get_data_directory() / export_dir
        export_dir.mkdir(parents=True, exist_ok=True)
        return export_dir
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value by key with optional default."""
        # Map common setting keys to actual attributes
        key_mapping = {
            'snippet_storage_path': lambda: str(self.get_data_directory() / 'snippets'),
            'parallel_processing_workers': lambda: self.processing.concurrent_workers,
            'default_quality_level': lambda: self.processing.default_quality_level,
            'max_file_size_mb': lambda: self.processing.max_file_size_mb,
            'chunk_size': lambda: self.processing.chunk_size,
            'chunk_overlap': lambda: self.processing.chunk_overlap,
            'quality_threshold': lambda: self.processing.quality_threshold,
            'auto_correct_enabled': lambda: self.processing.auto_correct_enabled,
            'extract_images': lambda: self.processing.extract_images,
            'extract_tables': lambda: self.processing.extract_tables,
            'window_width': lambda: self.ui.window_width,
            'window_height': lambda: self.ui.window_height,
            'theme': lambda: self.ui.theme,
            'font_size': lambda: self.ui.font_size,
            'font_family': lambda: self.ui.font_family,
            'openai_api_key': lambda: self.ai.openai_api_key,
            'huggingface_token': lambda: self.ai.huggingface_token,
            'database_path': lambda: self.database.path,
            'output_directory': lambda: self.export.output_directory
        }
        
        if key in key_mapping:
            try:
                return key_mapping[key]()
            except Exception:
                return default
        
        # Try to get from nested attributes
        try:
            # Check processing settings
            if hasattr(self.processing, key):
                return getattr(self.processing, key)
            
            # Check UI settings
            if hasattr(self.ui, key):
                return getattr(self.ui, key)
            
            # Check AI settings
            if hasattr(self.ai, key):
                return getattr(self.ai, key)
            
            # Check database settings
            if hasattr(self.database, key):
                return getattr(self.database, key)
            
            # Check export settings
            if hasattr(self.export, key):
                return getattr(self.export, key)
            
        except AttributeError:
            pass
        
        return default