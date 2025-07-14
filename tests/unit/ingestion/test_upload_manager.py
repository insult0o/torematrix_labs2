"""
Unit tests for the upload manager module.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile
from datetime import datetime
import asyncio

from fastapi import UploadFile
from io import BytesIO

from torematrix.ingestion.upload_manager import UploadManager, UploadManagerConfig
from torematrix.ingestion.models import UploadResult, UploadSession, FileMetadata, FileStatus, FileType
from torematrix.ingestion.storage import LocalFileStorage, StorageManager
from torematrix.integrations.unstructured.client import UnstructuredClient


class MockUploadFile:
    """Mock UploadFile for testing."""
    
    def __init__(self, filename: str, content: bytes = b"test content"):
        self.filename = filename
        self.file = BytesIO(content)
        self._content = content
    
    async def read(self, size: int = -1) -> bytes:
        return self.file.read(size)
    
    async def seek(self, offset: int) -> None:
        self.file.seek(offset)
    
    async def close(self) -> None:
        self.file.close()


@pytest.fixture
async def temp_storage_dir():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
async def upload_manager(temp_storage_dir):
    """Create upload manager instance."""
    storage = LocalFileStorage(temp_storage_dir)
    config = UploadManagerConfig(max_file_size=10 * 1024 * 1024)  # 10MB
    
    manager = UploadManager(
        storage=storage,
        config=config
    )
    
    yield manager


@pytest.fixture
def mock_unstructured_client():
    """Create mock Unstructured client."""
    client = Mock(spec=UnstructuredClient)
    client.process_file = AsyncMock()
    return client


class TestUploadManager:
    """Test cases for UploadManager."""
    
    async def test_create_session(self, upload_manager):
        """Test session creation."""
        session = await upload_manager.create_session("user123", {"name": "Test Session"})
        
        assert session.session_id.startswith("session-")
        assert session.user_id == "user123"
        assert session.status == "active"
        assert session.files == []
        assert session.metadata["name"] == "Test Session"
        
        # Verify session is stored
        retrieved = await upload_manager.get_session(session.session_id)
        assert retrieved == session
    
    async def test_upload_valid_file(self, upload_manager):
        """Test uploading a valid file."""
        session = await upload_manager.create_session("user123")
        
        # Create mock file
        file = MockUploadFile("test.pdf", b"PDF content here")
        
        # Mock magic mime detection
        with patch("magic.Magic.from_file", return_value="application/pdf"):
            result = await upload_manager.upload_file(session.session_id, file)
        
        assert result.filename == "test.pdf"
        assert result.validation_status == "valid"
        assert result.errors == []
        assert result.size == len(b"PDF content here")
        assert result.hash != ""
        assert result.mime_type == "application/pdf"
        
        # Check session was updated
        session = await upload_manager.get_session(session.session_id)
        assert len(session.files) == 1
        assert session.files[0] == result
    
    async def test_upload_invalid_extension(self, upload_manager):
        """Test uploading file with invalid extension."""
        session = await upload_manager.create_session("user123")
        
        file = MockUploadFile("malware.exe", b"EXE content")
        
        result = await upload_manager.upload_file(session.session_id, file)
        
        assert result.validation_status == "failed"
        assert any("not allowed" in error for error in result.errors)
    
    async def test_upload_empty_file(self, upload_manager):
        """Test uploading empty file."""
        session = await upload_manager.create_session("user123")
        
        file = MockUploadFile("empty.pdf", b"")
        
        result = await upload_manager.upload_file(session.session_id, file)
        
        assert result.validation_status == "failed"
        assert any("Empty file" in error for error in result.errors)
    
    async def test_upload_with_content_validation(self, upload_manager, mock_unstructured_client):
        """Test upload with Unstructured content validation."""
        upload_manager.unstructured_client = mock_unstructured_client
        
        # Mock successful validation
        mock_result = Mock()
        mock_result.elements = [{"type": "text", "content": "test"}]
        mock_result.metadata = {"page_count": 1}
        mock_unstructured_client.process_file.return_value = mock_result
        
        session = await upload_manager.create_session("user123")
        file = MockUploadFile("document.pdf", b"PDF content")
        
        with patch("magic.Magic.from_file", return_value="application/pdf"):
            result = await upload_manager.upload_file(
                session.session_id, 
                file, 
                validate_content=True
            )
        
        assert result.validation_status == "valid"
        assert mock_unstructured_client.process_file.called
    
    async def test_upload_encrypted_document(self, upload_manager, mock_unstructured_client):
        """Test upload of encrypted document."""
        upload_manager.unstructured_client = mock_unstructured_client
        
        # Mock encrypted document
        mock_result = Mock()
        mock_result.elements = []
        mock_result.metadata = {"is_encrypted": True}
        mock_unstructured_client.process_file.return_value = mock_result
        
        session = await upload_manager.create_session("user123")
        file = MockUploadFile("encrypted.pdf", b"Encrypted PDF")
        
        with patch("magic.Magic.from_file", return_value="application/pdf"):
            result = await upload_manager.upload_file(
                session.session_id,
                file,
                validate_content=True
            )
        
        assert result.validation_status == "warning"
        assert any("encrypted" in error.lower() for error in result.errors)
    
    async def test_batch_upload(self, upload_manager):
        """Test batch file upload."""
        session = await upload_manager.create_session("user123")
        
        files = [
            MockUploadFile(f"file{i}.pdf", f"Content {i}".encode())
            for i in range(5)
        ]
        
        with patch("magic.Magic.from_file", return_value="application/pdf"):
            results = await upload_manager.upload_batch(
                session.session_id,
                files,
                max_concurrent=3
            )
        
        assert len(results) == 5
        assert all(r.validation_status == "valid" for r in results)
        
        # Check session has all files
        session = await upload_manager.get_session(session.session_id)
        assert len(session.files) == 5
    
    async def test_batch_upload_with_failures(self, upload_manager):
        """Test batch upload with some failures."""
        session = await upload_manager.create_session("user123")
        
        files = [
            MockUploadFile("good.pdf", b"Good content"),
            MockUploadFile("bad.exe", b"Bad content"),
            MockUploadFile("empty.pdf", b""),
        ]
        
        with patch("magic.Magic.from_file", return_value="application/pdf"):
            results = await upload_manager.upload_batch(session.session_id, files)
        
        assert len(results) == 3
        assert results[0].validation_status == "valid"
        assert results[1].validation_status == "failed"  # Bad extension
        assert results[2].validation_status == "failed"  # Empty file
    
    async def test_create_file_metadata(self, upload_manager):
        """Test creating FileMetadata from upload result."""
        session = await upload_manager.create_session("user123")
        
        upload_result = UploadResult(
            file_id="file-123",
            filename="document.pdf",
            size=1024,
            mime_type="application/pdf",
            hash="abc123",
            validation_status="valid",
            errors=[],
            metadata={"pages": 10},
            storage_key="uploads/session-123/file-123/document.pdf"
        )
        
        metadata = upload_manager.create_file_metadata(upload_result, session)
        
        assert metadata.file_id == "file-123"
        assert metadata.filename == "document.pdf"
        assert metadata.file_type == FileType.PDF
        assert metadata.mime_type == "application/pdf"
        assert metadata.size == 1024
        assert metadata.hash == "abc123"
        assert metadata.upload_session_id == session.session_id
        assert metadata.uploaded_by == "user123"
        assert metadata.status == FileStatus.UPLOADED
        assert metadata.document_metadata["pages"] == 10
    
    async def test_detect_file_type(self, upload_manager):
        """Test file type detection."""
        test_cases = [
            ("application/pdf", "document.pdf", FileType.PDF),
            ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "doc.docx", FileType.WORD),
            ("text/plain", "file.txt", FileType.TEXT),
            ("text/html", "page.html", FileType.HTML),
            ("application/vnd.ms-excel", "data.xls", FileType.SPREADSHEET),
            ("image/png", "image.png", FileType.IMAGE),
            ("application/zip", "archive.zip", FileType.ARCHIVE),
            ("application/unknown", "file.xyz", FileType.OTHER),
        ]
        
        for mime_type, filename, expected_type in test_cases:
            detected = upload_manager._detect_file_type(mime_type, filename)
            assert detected == expected_type
    
    async def test_cleanup_expired_sessions(self, upload_manager):
        """Test cleaning up expired sessions."""
        # Create sessions
        session1 = await upload_manager.create_session("user1")
        session2 = await upload_manager.create_session("user2")
        
        # Manually expire session1
        session1.created_at = datetime.utcnow().replace(year=2020)
        
        # Run cleanup
        cleaned = await upload_manager.cleanup_expired_sessions(ttl_seconds=3600)
        
        assert cleaned == 1
        assert await upload_manager.get_session(session1.session_id) is None
        assert await upload_manager.get_session(session2.session_id) is not None
    
    async def test_upload_file_exception_handling(self, upload_manager):
        """Test exception handling during upload."""
        session = await upload_manager.create_session("user123")
        
        # Create file that will cause an exception
        file = MockUploadFile("test.pdf", b"content")
        
        # Mock storage to raise exception
        with patch.object(upload_manager.storage, 'save', side_effect=Exception("Storage error")):
            with patch("magic.Magic.from_file", return_value="application/pdf"):
                result = await upload_manager.upload_file(session.session_id, file)
        
        assert result.validation_status == "failed"
        assert any("Storage error" in error for error in result.errors)
    
    async def test_concurrent_uploads(self, upload_manager):
        """Test concurrent upload handling."""
        session = await upload_manager.create_session("user123")
        
        # Create many files
        files = [
            MockUploadFile(f"file{i}.pdf", f"Content {i}".encode())
            for i in range(20)
        ]
        
        with patch("magic.Magic.from_file", return_value="application/pdf"):
            # Upload all files concurrently
            tasks = [
                upload_manager.upload_file(session.session_id, file)
                for file in files
            ]
            
            results = await asyncio.gather(*tasks)
        
        assert len(results) == 20
        assert all(r.validation_status == "valid" for r in results)
        
        # Verify session has all files
        session = await upload_manager.get_session(session.session_id)
        assert len(session.files) == 20
    
    async def test_metadata_extraction(self, upload_manager, mock_unstructured_client):
        """Test metadata extraction."""
        upload_manager.unstructured_client = mock_unstructured_client
        
        # Mock metadata extraction
        mock_result = Mock()
        mock_result.elements = []
        mock_result.metadata = {
            "page_count": 10,
            "author": "John Doe",
            "title": "Test Document",
            "language": "en"
        }
        mock_unstructured_client.process_file.return_value = mock_result
        
        session = await upload_manager.create_session("user123")
        file = MockUploadFile("document.pdf", b"PDF content")
        
        with patch("magic.Magic.from_file", return_value="application/pdf"):
            result = await upload_manager.upload_file(
                session.session_id,
                file,
                extract_metadata=True
            )
        
        assert result.metadata["page_count"] == 10
        assert result.metadata["author"] == "John Doe"
        assert result.metadata["title"] == "Test Document"
        assert result.metadata["language"] == "en"