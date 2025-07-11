"""
Application constants and enumerations.
"""

from enum import Enum
from typing import Dict, List


class DocumentType(Enum):
    """Document type classification."""
    ICAO = "icao"
    ATC = "atc"
    REGULATORY = "regulatory"
    TECHNICAL = "technical"
    MANUAL = "manual"
    UNKNOWN = "unknown"


class ProcessingStatus(Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    EXTRACTED = "extracted"
    VALIDATING = "validating"
    CORRECTING = "correcting"
    APPROVED = "approved"
    EXPORTED = "exported"
    FAILED = "failed"


class QualityLevel(Enum):
    """Quality assessment levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNACCEPTABLE = "unacceptable"


class ExportFormat(Enum):
    """Export format options."""
    JSONL = "jsonl"
    JSON = "json"
    CSV = "csv"
    PARQUET = "parquet"
    HDF5 = "hdf5"
    ALPACA = "alpaca"
    OPENAI = "openai"


class ChunkingStrategy(Enum):
    """Text chunking strategies."""
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    HIERARCHICAL = "hierarchical"
    SLIDING_WINDOW = "sliding_window"


class ValidationState(Enum):
    """Validation states for content."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"
    DEFERRED = "deferred"


# File type mappings
SUPPORTED_FILE_TYPES = {
    '.pdf': 'Portable Document Format',
    '.docx': 'Microsoft Word Document',
    '.odt': 'OpenDocument Text',
    '.rtf': 'Rich Text Format'
}

# Quality thresholds
QUALITY_THRESHOLDS = {
    QualityLevel.EXCELLENT: 0.95,
    QualityLevel.GOOD: 0.85,
    QualityLevel.ACCEPTABLE: 0.75,
    QualityLevel.POOR: 0.60,
    QualityLevel.UNACCEPTABLE: 0.0
}

# Processing limits
MAX_FILE_SIZE_MB = 500
MAX_PAGES_PER_DOCUMENT = 1000
MAX_CONCURRENT_WORKERS = 8
DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 50

# UI Constants
DEFAULT_WINDOW_WIDTH = 1400
DEFAULT_WINDOW_HEIGHT = 900
MIN_WINDOW_WIDTH = 800
MIN_WINDOW_HEIGHT = 600

# Database constants
DATABASE_VERSION = 1
BACKUP_RETENTION_DAYS = 30

# Export constants
DEFAULT_EXPORT_BATCH_SIZE = 1000
MAX_EXPORT_ITEMS = 100000

# AI Model constants
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_EMBEDDING_DIMENSIONS = 384
MAX_EMBEDDING_BATCH_SIZE = 64

# OCR constants
OCR_CONFIDENCE_THRESHOLD = 0.7
OCR_LANGUAGES = ['eng', 'fra', 'deu', 'spa', 'ita']

# Validation constants
MIN_TEXT_LENGTH = 10
MAX_TEXT_LENGTH = 100000
MIN_TABLE_ROWS = 2
MIN_TABLE_COLUMNS = 2

# Error messages
ERROR_MESSAGES = {
    'file_too_large': 'File size exceeds maximum limit of {max_size}MB',
    'file_not_found': 'File not found: {filename}',
    'invalid_format': 'Unsupported file format: {format}',
    'processing_failed': 'Failed to process document: {error}',
    'validation_failed': 'Validation failed: {error}',
    'export_failed': 'Export failed: {error}',
    'database_error': 'Database error: {error}',
    'api_error': 'API error: {error}'
}

# Success messages
SUCCESS_MESSAGES = {
    'document_processed': 'Document processed successfully',
    'validation_complete': 'Validation completed',
    'export_complete': 'Export completed successfully',
    'project_saved': 'Project saved successfully',
    'settings_updated': 'Settings updated successfully'
}

# Default project structure
DEFAULT_PROJECT_STRUCTURE = {
    'documents': [],
    'settings': {},
    'metadata': {},
    'validation_rules': {},
    'export_configs': []
}

# Keyboard shortcuts
KEYBOARD_SHORTCUTS = {
    'new_project': 'Ctrl+N',
    'open_project': 'Ctrl+O',
    'save_project': 'Ctrl+S',
    'import_document': 'Ctrl+I',
    'export_data': 'Ctrl+E',
    'validate_document': 'Ctrl+V',
    'correct_document': 'Ctrl+C',
    'toggle_preview': 'F3',
    'settings': 'Ctrl+,',
    'help': 'F1',
    'quit': 'Ctrl+Q'
}

# Theme colors
THEME_COLORS = {
    'professional': {
        'primary': '#2C3E50',
        'secondary': '#34495E',
        'accent': '#3498DB',
        'background': '#ECF0F1',
        'text': '#2C3E50',
        'success': '#27AE60',
        'warning': '#F39C12',
        'error': '#E74C3C'
    },
    'dark': {
        'primary': '#1E1E1E',
        'secondary': '#2D2D2D',
        'accent': '#007ACC',
        'background': '#0D1117',
        'text': '#F0F6FC',
        'success': '#238636',
        'warning': '#D29922',
        'error': '#F85149'
    },
    'light': {
        'primary': '#FFFFFF',
        'secondary': '#F8F9FA',
        'accent': '#0366D6',
        'background': '#FFFFFF',
        'text': '#24292F',
        'success': '#28A745',
        'warning': '#FFC107',
        'error': '#DC3545'
    }
}