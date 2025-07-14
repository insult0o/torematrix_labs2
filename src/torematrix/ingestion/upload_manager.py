"""
Core upload manager for document ingestion system.

Handles multi-file uploads with validation, storage, and metadata extraction.
Integrates with Unstructured.io for content validation and processing.
"""

from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import asyncio
import aiofiles
from datetime import datetime
import hashlib
import uuid
import logging
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field
from fastapi import UploadFile

from .models import UploadResult, UploadSession, FileMetadata, FileStatus, FileType
from .storage import StorageManager, StorageBackend
from .validators import CompositeValidator, create_default_validator, HashValidator
from ..integrations.unstructured.client import UnstructuredClient
from ..integrations.unstructured.config import UnstructuredConfig

logger = logging.getLogger(__name__)


class UploadManagerConfig(BaseModel):
    """Configuration for upload manager."""
    
    max_file_size: int = Field(default=100 * 1024 * 1024, description="Maximum file size in bytes")
    chunk_size: int = Field(default=1024 * 1024, description="Chunk size for streaming uploads")
    allowed_extensions: List[str] = Field(
        default_factory=lambda: [
            ".pdf", ".docx", ".doc", ".odt", ".rtf", ".txt",
            ".html", ".xml", ".json", ".csv", ".xlsx", ".xls",
            ".pptx", ".ppt", ".epub", ".md", ".rst"
        ],
        description="Allowed file extensions"
    )
    session_ttl: int = Field(default=3600, description="Session TTL in seconds")
    validate_content: bool = Field(default=True, description="Enable content validation")
    extract_metadata: bool = Field(default=True, description="Enable metadata extraction")


class UploadManager:
    """
    Manages file uploads with validation and metadata extraction.
    
    Provides session-based upload management with comprehensive validation,
    storage abstraction, and integration with Unstructured.io.
    """
    
    def __init__(
        self,
        storage: Union[StorageManager, StorageBackend],
        config: Optional[UploadManagerConfig] = None,
        unstructured_client: Optional[UnstructuredClient] = None,
        validator: Optional[CompositeValidator] = None
    ):
        """
        Initialize upload manager.
        
        Args:
            storage: Storage manager or backend
            config: Upload manager configuration
            unstructured_client: Optional Unstructured.io client
            validator: Optional custom validator
        """
        self.config = config or UploadManagerConfig()
        
        # Wrap single backend in manager if needed
        if isinstance(storage, StorageBackend):
            self.storage = StorageManager(storage)
        else:
            self.storage = storage
            
        self.unstructured_client = unstructured_client
        self.validator = validator or create_default_validator(
            max_file_size=self.config.max_file_size
        )
        
        # Session management
        self._sessions: Dict[str, UploadSession] = {}
        self._session_lock = asyncio.Lock()
        
        # File handling
        self._hash_validator = HashValidator()
        
        logger.info("Initialized upload manager")
    
    async def create_session(self, user_id: str, metadata: Optional[Dict[str, Any]] = None) -> UploadSession:
        """
        Create a new upload session.
        
        Args:
            user_id: User ID creating the session
            metadata: Optional session metadata
            
        Returns:
            New upload session
        """
        session = UploadSession(
            session_id=f"session-{uuid.uuid4()}",
            user_id=user_id,
            created_at=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        async with self._session_lock:
            self._sessions[session.session_id] = session
        
        logger.info(f"Created upload session {session.session_id} for user {user_id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[UploadSession]:
        """
        Get an existing session.
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            Upload session or None if not found
        """
        return self._sessions.get(session_id)
    
    async def upload_file(
        self,
        session_id: str,
        file: UploadFile,
        validate_content: Optional[bool] = None,
        extract_metadata: Optional[bool] = None
    ) -> UploadResult:
        """
        Upload and validate a single file.
        
        Args:
            session_id: Upload session ID
            file: FastAPI UploadFile object
            validate_content: Override content validation setting
            extract_metadata: Override metadata extraction setting
            
        Returns:
            Upload result with validation status
        """
        # Get session
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Use config defaults if not specified
        if validate_content is None:
            validate_content = self.config.validate_content
        if extract_metadata is None:
            extract_metadata = self.config.extract_metadata
        
        # Generate file ID
        file_id = str(uuid.uuid4())
        storage_key = f"uploads/{session_id}/{file_id}/{file.filename}"
        
        logger.info(f"Starting upload for {file.filename} in session {session_id}")
        
        # Initialize result
        result = UploadResult(
            file_id=file_id,
            filename=file.filename,
            size=0,
            mime_type="",
            hash="",
            validation_status="pending",
            errors=[],
            metadata={},
            storage_key=storage_key
        )
        
        try:
            # Basic validation
            errors = await self._validate_basic(file)
            if errors:
                result.validation_status = "failed"
                result.errors = errors
                session.add_file(result)
                return result
            
            # Save file to temporary location for validation
            temp_path = await self._save_temp_file(file)
            
            try:
                # Get file size
                result.size = temp_path.stat().st_size
                
                # Calculate hash
                result.hash = await self._hash_validator.calculate_hash(temp_path)
                
                # Run validators
                validation_errors = await self.validator.validate(temp_path)
                if validation_errors:
                    result.errors.extend(validation_errors)
                
                # Detect MIME type
                import magic
                mime = magic.Magic(mime=True)
                result.mime_type = mime.from_file(str(temp_path))
                
                # Content validation with Unstructured
                if validate_content and self.unstructured_client:
                    content_errors = await self._validate_content(temp_path, result.mime_type)
                    if content_errors:
                        result.errors.extend(content_errors)
                
                # Extract metadata
                if extract_metadata:
                    metadata = await self._extract_metadata(temp_path, result.mime_type)
                    result.metadata = metadata
                
                # Determine validation status
                if result.errors:
                    result.validation_status = "warning"
                else:
                    result.validation_status = "valid"
                
                # Save to permanent storage
                with open(temp_path, "rb") as f:
                    content = f.read()
                
                await self.storage.save(content, storage_key)
                
                logger.info(
                    f"Upload complete for {file.filename}: "
                    f"status={result.validation_status}, errors={len(result.errors)}"
                )
                
            finally:
                # Clean up temp file
                if temp_path.exists():
                    temp_path.unlink()
            
        except Exception as e:
            logger.error(f"Upload failed for {file.filename}: {e}")
            result.validation_status = "failed"
            result.errors.append(f"Upload failed: {str(e)}")
        
        # Add to session
        session.add_file(result)
        
        return result
    
    async def upload_batch(
        self,
        session_id: str,
        files: List[UploadFile],
        max_concurrent: int = 5
    ) -> List[UploadResult]:
        """
        Upload multiple files concurrently.
        
        Args:
            session_id: Upload session ID
            files: List of files to upload
            max_concurrent: Maximum concurrent uploads
            
        Returns:
            List of upload results
        """
        logger.info(f"Starting batch upload of {len(files)} files")
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def upload_with_limit(file: UploadFile) -> UploadResult:
            async with semaphore:
                return await self.upload_file(session_id, file)
        
        # Upload all files concurrently
        tasks = [upload_with_limit(file) for file in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Create failed result for exception
                failed_result = UploadResult(
                    file_id=str(uuid.uuid4()),
                    filename=files[i].filename,
                    size=0,
                    mime_type="",
                    hash="",
                    validation_status="failed",
                    errors=[f"Upload exception: {str(result)}"],
                    metadata={},
                    storage_key=""
                )
                final_results.append(failed_result)
            else:
                final_results.append(result)
        
        logger.info(
            f"Batch upload complete: "
            f"{sum(1 for r in final_results if r.validation_status == 'valid')} valid, "
            f"{sum(1 for r in final_results if r.validation_status == 'warning')} warnings, "
            f"{sum(1 for r in final_results if r.validation_status == 'failed')} failed"
        )
        
        return final_results
    
    async def _validate_basic(self, file: UploadFile) -> List[str]:
        """Perform basic file validation."""
        errors = []
        
        # Check filename
        if not file.filename:
            errors.append("Missing filename")
            return errors
        
        # Check extension
        ext = Path(file.filename).suffix.lower()
        if ext not in self.config.allowed_extensions:
            errors.append(f"File type {ext} not allowed")
        
        # Check size (read first chunk)
        chunk = await file.read(1024)
        await file.seek(0)  # Reset position
        
        if not chunk:
            errors.append("Empty file")
        
        return errors
    
    async def _save_temp_file(self, file: UploadFile) -> Path:
        """Save uploaded file to temporary location."""
        # Create temp directory
        temp_dir = Path("/tmp/torematrix_uploads")
        temp_dir.mkdir(exist_ok=True)
        
        # Generate temp filename
        temp_path = temp_dir / f"{uuid.uuid4()}_{file.filename}"
        
        # Stream file to disk
        async with aiofiles.open(temp_path, "wb") as f:
            while chunk := await file.read(self.config.chunk_size):
                await f.write(chunk)
        
        # Reset file position
        await file.seek(0)
        
        return temp_path
    
    async def _validate_content(self, file_path: Path, mime_type: str) -> List[str]:
        """Validate content using Unstructured.io."""
        errors = []
        
        try:
            # Quick validation pass
            result = await self.unstructured_client.process_file(
                file_path=str(file_path),
                strategy="fast",
                max_characters=1000  # Just check beginning
            )
            
            # Check for issues
            if not result.elements:
                errors.append("No extractable content found")
            
            # Check metadata for issues
            metadata = result.metadata or {}
            if metadata.get("is_encrypted"):
                errors.append("Document is encrypted")
            
            if metadata.get("has_errors"):
                doc_errors = metadata.get("errors", [])
                errors.extend([f"Document error: {e}" for e in doc_errors])
                
        except Exception as e:
            errors.append(f"Content validation failed: {str(e)}")
            logger.error(f"Unstructured validation error: {e}")
        
        return errors
    
    async def _extract_metadata(self, file_path: Path, mime_type: str) -> Dict[str, Any]:
        """Extract metadata from file."""
        metadata = {
            "mime_type": mime_type,
            "size": file_path.stat().st_size,
            "created": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
        }
        
        # Try to extract document metadata with Unstructured
        if self.unstructured_client and mime_type.startswith(("application/", "text/")):
            try:
                result = await self.unstructured_client.process_file(
                    file_path=str(file_path),
                    include_metadata=True,
                    strategy="fast",
                    max_characters=0  # Metadata only
                )
                
                if result.metadata:
                    metadata.update(result.metadata)
                    
            except Exception as e:
                logger.warning(f"Metadata extraction failed: {e}")
                # Continue without metadata - not critical
        
        return metadata
    
    def create_file_metadata(
        self,
        upload_result: UploadResult,
        session: UploadSession,
        file_type: Optional[FileType] = None
    ) -> FileMetadata:
        """
        Create FileMetadata from upload result.
        
        Args:
            upload_result: Upload result
            session: Upload session
            file_type: Optional file type override
            
        Returns:
            FileMetadata object for queue processing
        """
        # Detect file type if not provided
        if not file_type:
            file_type = self._detect_file_type(upload_result.mime_type, upload_result.filename)
        
        return FileMetadata(
            file_id=upload_result.file_id,
            filename=upload_result.filename,
            file_type=file_type,
            mime_type=upload_result.mime_type,
            size=upload_result.size,
            hash=upload_result.hash,
            upload_session_id=session.session_id,
            uploaded_by=session.user_id,
            uploaded_at=datetime.utcnow(),
            storage_key=upload_result.storage_key,
            status=FileStatus.UPLOADED if upload_result.validation_status in ["valid", "warning"] else FileStatus.FAILED,
            validation_errors=upload_result.errors,
            document_metadata=upload_result.metadata
        )
    
    def _detect_file_type(self, mime_type: str, filename: str) -> FileType:
        """Detect file type from MIME type and filename."""
        # MIME type mapping
        mime_map = {
            "application/pdf": FileType.PDF,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileType.WORD,
            "application/msword": FileType.WORD,
            "text/plain": FileType.TEXT,
            "text/html": FileType.HTML,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": FileType.SPREADSHEET,
            "application/vnd.ms-excel": FileType.SPREADSHEET,
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": FileType.PRESENTATION,
            "application/vnd.ms-powerpoint": FileType.PRESENTATION,
            "image/png": FileType.IMAGE,
            "image/jpeg": FileType.IMAGE,
            "image/gif": FileType.IMAGE,
            "application/zip": FileType.ARCHIVE,
            "application/x-rar-compressed": FileType.ARCHIVE
        }
        
        # Check MIME type first
        if mime_type in mime_map:
            return mime_map[mime_type]
        
        # Fall back to extension
        ext = Path(filename).suffix.lower()
        ext_map = {
            ".pdf": FileType.PDF,
            ".doc": FileType.WORD,
            ".docx": FileType.WORD,
            ".txt": FileType.TEXT,
            ".md": FileType.TEXT,
            ".rst": FileType.TEXT,
            ".html": FileType.HTML,
            ".xml": FileType.HTML,
            ".xls": FileType.SPREADSHEET,
            ".xlsx": FileType.SPREADSHEET,
            ".csv": FileType.SPREADSHEET,
            ".ppt": FileType.PRESENTATION,
            ".pptx": FileType.PRESENTATION,
            ".png": FileType.IMAGE,
            ".jpg": FileType.IMAGE,
            ".jpeg": FileType.IMAGE,
            ".gif": FileType.IMAGE,
            ".zip": FileType.ARCHIVE,
            ".rar": FileType.ARCHIVE,
            ".7z": FileType.ARCHIVE
        }
        
        return ext_map.get(ext, FileType.OTHER)
    
    async def cleanup_expired_sessions(self, ttl_seconds: Optional[int] = None):
        """Clean up expired sessions."""
        if ttl_seconds is None:
            ttl_seconds = self.config.session_ttl
        
        now = datetime.utcnow()
        expired = []
        
        async with self._session_lock:
            for session_id, session in self._sessions.items():
                age = (now - session.created_at).total_seconds()
                if age > ttl_seconds:
                    expired.append(session_id)
            
            # Remove expired sessions
            for session_id in expired:
                del self._sessions[session_id]
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
        
        return len(expired)