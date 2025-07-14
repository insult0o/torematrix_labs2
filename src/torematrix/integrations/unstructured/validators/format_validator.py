"""
Format Validator for Agent 4 - Input file validation.
"""

import asyncio
import logging
import mimetypes
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation strictness levels."""
    STRICT = "strict"      # Strict validation, fail on any issues
    MODERATE = "moderate"  # Moderate validation, warn on issues
    PERMISSIVE = "permissive"  # Permissive, allow most files


@dataclass
class ValidationResult:
    """Result of file format validation."""
    is_valid: bool
    file_path: Path
    detected_format: Optional[str] = None
    file_size_mb: float = 0.0
    mime_type: Optional[str] = None
    encoding: Optional[str] = None
    warnings: List[str] = None
    errors: List[str] = None
    recommended_strategy: Optional[str] = None
    file_info: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []
        if self.file_info is None:
            self.file_info = {}


class FormatValidator:
    """Comprehensive file format validator."""
    
    # Supported formats organized by category
    SUPPORTED_FORMATS = {
        'pdf': {'.pdf'},
        'office': {'.docx', '.xlsx', '.pptx', '.doc', '.xls', '.ppt'},
        'text': {'.txt', '.md', '.rst', '.csv', '.json', '.log'},
        'web': {'.html', '.htm', '.xml', '.xhtml'},
        'email': {'.eml', '.msg'},
        'image': {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'},
        'archive': {'.zip', '.tar', '.gz', '.rar', '.7z'}
    }
    
    # File size limits (MB) per format
    SIZE_LIMITS = {
        'pdf': 500,      # 500MB max for PDFs
        'office': 200,   # 200MB max for Office docs
        'text': 50,      # 50MB max for text files
        'web': 100,      # 100MB max for web files
        'email': 100,    # 100MB max for emails
        'image': 50,     # 50MB max for images
        'archive': 1000  # 1GB max for archives
    }
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.MODERATE):
        self.validation_level = validation_level
        
        # Create reverse lookup for extensions to categories
        self._extension_to_category = {}
        for category, extensions in self.SUPPORTED_FORMATS.items():
            for ext in extensions:
                self._extension_to_category[ext] = category
    
    async def validate_file(self, file_path: Path, **kwargs) -> ValidationResult:
        """Comprehensive file validation."""
        result = ValidationResult(is_valid=False, file_path=file_path)
        
        try:
            # Basic file existence and access
            if not await self._check_file_exists(file_path, result):
                return result
            
            # File properties analysis
            await self._analyze_file_properties(file_path, result)
            
            # Format detection and validation
            await self._validate_format_support(file_path, result)
            
            # Size validation
            await self._validate_file_size(file_path, result)
            
            # Content integrity checks
            await self._validate_file_integrity(file_path, result)
            
            # Security checks
            await self._validate_file_security(file_path, result)
            
            # Determine processing strategy
            self._recommend_processing_strategy(result)
            
            # Final validation decision
            result.is_valid = self._make_validation_decision(result)
            
            logger.info(f"File validation complete: {file_path.name} - Valid: {result.is_valid}")
            return result
            
        except Exception as e:
            logger.error(f"Validation failed for {file_path}: {e}")
            result.errors.append(f"Validation exception: {str(e)}")
            return result
    
    async def _check_file_exists(self, file_path: Path, result: ValidationResult) -> bool:
        """Check if file exists and is accessible."""
        try:
            if not file_path.exists():
                result.errors.append(f"File does not exist: {file_path}")
                return False
            
            if not file_path.is_file():
                result.errors.append(f"Path is not a file: {file_path}")
                return False
            
            if not file_path.stat().st_size > 0:
                result.warnings.append("File is empty")
                if self.validation_level == ValidationLevel.STRICT:
                    result.errors.append("Empty files not allowed in strict mode")
                    return False
            
            return True
            
        except PermissionError:
            result.errors.append(f"Permission denied accessing file: {file_path}")
            return False
        except Exception as e:
            result.errors.append(f"File access error: {str(e)}")
            return False
    
    async def _analyze_file_properties(self, file_path: Path, result: ValidationResult) -> None:
        """Analyze basic file properties."""
        try:
            stat = file_path.stat()
            
            # File size
            size_bytes = stat.st_size
            result.file_size_mb = size_bytes / (1024 * 1024)
            
            # MIME type detection
            result.mime_type, _ = mimetypes.guess_type(str(file_path))
            
            # File info
            result.file_info = {
                'size_bytes': size_bytes,
                'size_mb': result.file_size_mb,
                'extension': file_path.suffix.lower(),
                'name': file_path.name,
                'stem': file_path.stem,
                'modified_time': stat.st_mtime,
                'mime_type': result.mime_type
            }
            
            # Try to detect encoding for text-like files
            if self._is_text_like_file(file_path):
                result.encoding = await self._detect_file_encoding(file_path)
                result.file_info['encoding'] = result.encoding
            
        except Exception as e:
            result.warnings.append(f"Property analysis failed: {str(e)}")
    
    async def _validate_format_support(self, file_path: Path, result: ValidationResult) -> None:
        """Validate that the file format is supported."""
        extension = file_path.suffix.lower()
        
        # Check if extension is supported
        if extension in self._extension_to_category:
            result.detected_format = self._extension_to_category[extension]
        else:
            # Try MIME type based detection
            if result.mime_type:
                result.detected_format = self._detect_format_from_mime(result.mime_type)
            
            if not result.detected_format:
                error_msg = f"Unsupported file format: {extension}"
                if self.validation_level == ValidationLevel.STRICT:
                    result.errors.append(error_msg)
                else:
                    result.warnings.append(error_msg)
                    result.detected_format = "unknown"
    
    async def _validate_file_size(self, file_path: Path, result: ValidationResult) -> None:
        """Validate file size against limits."""
        if not result.detected_format or result.detected_format == "unknown":
            return
        
        max_size = self.SIZE_LIMITS.get(result.detected_format, 100)  # Default 100MB
        
        if result.file_size_mb > max_size:
            error_msg = f"File too large: {result.file_size_mb:.1f}MB > {max_size}MB limit for {result.detected_format}"
            
            if self.validation_level == ValidationLevel.STRICT:
                result.errors.append(error_msg)
            elif self.validation_level == ValidationLevel.MODERATE:
                result.warnings.append(error_msg)
            # Permissive mode allows large files
        
        # Warn about very small files
        if result.file_size_mb < 0.001:  # Less than 1KB
            result.warnings.append("File is very small, may not contain meaningful content")
    
    async def _validate_file_integrity(self, file_path: Path, result: ValidationResult) -> None:
        """Basic file integrity checks."""
        try:
            if result.detected_format == "pdf":
                await self._check_pdf_integrity(file_path, result)
            elif result.detected_format == "office":
                await self._check_office_integrity(file_path, result)
            elif result.detected_format == "text":
                await self._check_text_integrity(file_path, result)
            elif result.detected_format == "web":
                await self._check_web_integrity(file_path, result)
            elif result.detected_format == "email":
                await self._check_email_integrity(file_path, result)
                
        except Exception as e:
            result.warnings.append(f"Integrity check failed: {str(e)}")
    
    async def _check_pdf_integrity(self, file_path: Path, result: ValidationResult) -> None:
        """Check PDF file integrity."""
        try:
            # Read first few bytes to check PDF header
            with open(file_path, 'rb') as f:
                header = f.read(8)
                
            if not header.startswith(b'%PDF-'):
                result.errors.append("Invalid PDF header")
            else:
                # Extract PDF version
                version_match = header[5:8]
                result.file_info['pdf_version'] = version_match.decode('ascii', errors='ignore')
                
        except Exception as e:
            result.warnings.append(f"PDF integrity check failed: {str(e)}")
    
    async def _check_office_integrity(self, file_path: Path, result: ValidationResult) -> None:
        """Check Office document integrity."""
        try:
            extension = file_path.suffix.lower()
            
            if extension in ['.docx', '.xlsx', '.pptx']:
                # Modern Office formats are ZIP files
                with open(file_path, 'rb') as f:
                    header = f.read(4)
                    
                if not header.startswith(b'PK'):
                    result.errors.append(f"Invalid {extension} file format (not a ZIP archive)")
            else:
                # Legacy Office formats have specific signatures
                with open(file_path, 'rb') as f:
                    header = f.read(8)
                    
                if not (header.startswith(b'\xd0\xcf\x11\xe0') or header.startswith(b'\x09\x08')):
                    result.warnings.append(f"Potentially corrupted {extension} file")
                    
        except Exception as e:
            result.warnings.append(f"Office integrity check failed: {str(e)}")
    
    async def _check_text_integrity(self, file_path: Path, result: ValidationResult) -> None:
        """Check text file integrity."""
        try:
            # Try to read a sample to check encoding
            with open(file_path, 'rb') as f:
                sample = f.read(1024)
                
            # Check for binary content in text files
            if b'\x00' in sample:
                result.warnings.append("Text file contains null bytes (possibly binary)")
            
            # Try to decode with detected encoding
            if result.encoding:
                try:
                    sample.decode(result.encoding)
                except UnicodeDecodeError:
                    result.warnings.append(f"Text file has encoding issues with {result.encoding}")
                    
        except Exception as e:
            result.warnings.append(f"Text integrity check failed: {str(e)}")
    
    async def _check_web_integrity(self, file_path: Path, result: ValidationResult) -> None:
        """Check web document integrity."""
        try:
            # Read start of file to check for proper format
            with open(file_path, 'r', encoding=result.encoding or 'utf-8', errors='replace') as f:
                content = f.read(1024).lower()
                
            extension = file_path.suffix.lower()
            
            if extension in ['.html', '.htm']:
                if not ('<html' in content or '<!doctype' in content):
                    result.warnings.append("HTML file missing proper DOCTYPE or html tag")
            elif extension == '.xml':
                if not content.strip().startswith('<?xml'):
                    result.warnings.append("XML file missing XML declaration")
                    
        except Exception as e:
            result.warnings.append(f"Web integrity check failed: {str(e)}")
    
    async def _check_email_integrity(self, file_path: Path, result: ValidationResult) -> None:
        """Check email file integrity."""
        try:
            extension = file_path.suffix.lower()
            
            if extension == '.eml':
                # Check for email headers
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read(512)
                    
                if not any(header in content for header in ['From:', 'To:', 'Subject:', 'Date:']):
                    result.warnings.append("EML file missing standard email headers")
            elif extension == '.msg':
                # Check MSG file signature
                with open(file_path, 'rb') as f:
                    header = f.read(8)
                    
                if not header.startswith(b'\xd0\xcf\x11\xe0'):
                    result.warnings.append("MSG file has unexpected format")
                    
        except Exception as e:
            result.warnings.append(f"Email integrity check failed: {str(e)}")
    
    async def _validate_file_security(self, file_path: Path, result: ValidationResult) -> None:
        """Basic security validation."""
        try:
            # Check for suspicious file names
            name_lower = file_path.name.lower()
            
            suspicious_patterns = [
                'script', 'executable', 'malware', 'virus',
                '.exe', '.bat', '.cmd', '.scr', '.vbs'
            ]
            
            for pattern in suspicious_patterns:
                if pattern in name_lower:
                    result.warnings.append(f"File name contains suspicious pattern: {pattern}")
            
            # Check file size for potential zip bombs (very small files that expand hugely)
            if result.detected_format == "archive" and result.file_size_mb < 0.1:
                result.warnings.append("Very small archive file - potential zip bomb")
            
            # Check for hidden or system files on certain platforms
            if file_path.name.startswith('.') and len(file_path.name) > 1:
                result.warnings.append("Hidden file detected")
                
        except Exception as e:
            result.warnings.append(f"Security check failed: {str(e)}")
    
    def _recommend_processing_strategy(self, result: ValidationResult) -> None:
        """Recommend processing strategy based on file characteristics."""
        if not result.detected_format:
            result.recommended_strategy = "generic"
            return
        
        # Strategy recommendations based on file format and size
        strategies = {
            'pdf': self._recommend_pdf_strategy,
            'office': self._recommend_office_strategy,
            'text': self._recommend_text_strategy,
            'web': self._recommend_web_strategy,
            'email': self._recommend_email_strategy
        }
        
        strategy_func = strategies.get(result.detected_format)
        if strategy_func:
            result.recommended_strategy = strategy_func(result)
        else:
            result.recommended_strategy = "auto"
    
    def _recommend_pdf_strategy(self, result: ValidationResult) -> str:
        """Recommend PDF processing strategy."""
        if result.file_size_mb > 50:
            return "fast"  # Use fast strategy for large PDFs
        elif result.file_size_mb < 1:
            return "hi_res"  # Use high resolution for small PDFs
        else:
            return "auto"  # Let system decide
    
    def _recommend_office_strategy(self, result: ValidationResult) -> str:
        """Recommend Office processing strategy."""
        extension = result.file_path.suffix.lower()
        
        if extension in ['.xlsx', '.csv']:
            return "table_focused"
        elif extension in ['.pptx']:
            return "image_focused"
        else:
            return "balanced"
    
    def _recommend_text_strategy(self, result: ValidationResult) -> str:
        """Recommend text processing strategy."""
        extension = result.file_path.suffix.lower()
        
        if extension == '.csv':
            return "structured"
        elif extension in ['.md', '.rst']:
            return "markup_aware"
        else:
            return "plain_text"
    
    def _recommend_web_strategy(self, result: ValidationResult) -> str:
        """Recommend web processing strategy."""
        return "dom_aware"  # Always use DOM-aware processing for web files
    
    def _recommend_email_strategy(self, result: ValidationResult) -> str:
        """Recommend email processing strategy."""
        return "header_aware"  # Always extract headers and structure
    
    def _make_validation_decision(self, result: ValidationResult) -> bool:
        """Make final validation decision based on level and findings."""
        if result.errors:
            return False  # Any errors = invalid
        
        if self.validation_level == ValidationLevel.STRICT:
            return len(result.warnings) == 0  # No warnings allowed
        elif self.validation_level == ValidationLevel.MODERATE:
            return len(result.warnings) <= 3  # Allow few warnings
        else:  # PERMISSIVE
            return True  # Allow if no errors
    
    def _is_text_like_file(self, file_path: Path) -> bool:
        """Check if file is text-like and needs encoding detection."""
        extension = file_path.suffix.lower()
        text_extensions = {'.txt', '.md', '.rst', '.csv', '.json', '.log', '.html', '.htm', '.xml', '.eml'}
        return extension in text_extensions
    
    async def _detect_file_encoding(self, file_path: Path) -> str:
        """Detect file encoding."""
        try:
            # Try common encodings
            encodings = ['utf-8', 'utf-16', 'latin1', 'cp1252']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        f.read(1024)  # Try to read sample
                    return encoding
                except UnicodeDecodeError:
                    continue
            
            return 'utf-8'  # Fallback
            
        except Exception:
            return 'utf-8'
    
    def _detect_format_from_mime(self, mime_type: str) -> Optional[str]:
        """Detect format category from MIME type."""
        mime_mappings = {
            'application/pdf': 'pdf',
            'application/msword': 'office',
            'application/vnd.openxmlformats-officedocument': 'office',
            'text/plain': 'text',
            'text/html': 'web',
            'text/xml': 'web',
            'application/xml': 'web',
            'message/rfc822': 'email'
        }
        
        for mime_prefix, category in mime_mappings.items():
            if mime_type.startswith(mime_prefix):
                return category
        
        return None
    
    def get_supported_extensions(self) -> Set[str]:
        """Get all supported file extensions."""
        extensions = set()
        for category_extensions in self.SUPPORTED_FORMATS.values():
            extensions.update(category_extensions)
        return extensions
    
    def get_format_info(self, extension: str) -> Dict[str, Any]:
        """Get information about a specific format."""
        category = self._extension_to_category.get(extension.lower())
        if not category:
            return {}
        
        return {
            'category': category,
            'extensions': self.SUPPORTED_FORMATS[category],
            'size_limit_mb': self.SIZE_LIMITS.get(category, 100),
            'supported': True
        }