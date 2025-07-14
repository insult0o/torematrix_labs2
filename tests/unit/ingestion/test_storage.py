"""
Unit tests for storage backends.
"""

import pytest
from pathlib import Path
import tempfile
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import uuid

from torematrix.ingestion.storage import (
    StorageBackend,
    LocalFileStorage,
    S3Storage,
    StorageManager
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
async def local_storage(temp_dir):
    """Create local storage instance."""
    return LocalFileStorage(temp_dir)


@pytest.fixture
def mock_s3_client():
    """Create mock S3 client."""
    client = AsyncMock()
    return client


class TestLocalFileStorage:
    """Test cases for local file storage."""
    
    async def test_save_and_load(self, local_storage):
        """Test saving and loading content."""
        content = b"Hello, World!"
        key = "test-file.txt"
        
        # Save content
        saved_key = await local_storage.save(content, key)
        assert saved_key == key
        
        # Load content
        loaded = await local_storage.load(key)
        assert loaded == content
    
    async def test_save_creates_directories(self, local_storage):
        """Test that save creates necessary directories."""
        content = b"test content"
        key = "ab/cd/ef/deep-file.txt"
        
        saved_key = await local_storage.save(content, key)
        assert saved_key == key
        
        # Verify file exists
        assert await local_storage.exists(key)
    
    async def test_load_nonexistent_file(self, local_storage):
        """Test loading non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            await local_storage.load("nonexistent.txt")
    
    async def test_delete_existing_file(self, local_storage):
        """Test deleting existing file."""
        content = b"delete me"
        key = "deletable.txt"
        
        await local_storage.save(content, key)
        assert await local_storage.exists(key)
        
        # Delete file
        result = await local_storage.delete(key)
        assert result is True
        assert not await local_storage.exists(key)
    
    async def test_delete_nonexistent_file(self, local_storage):
        """Test deleting non-existent file returns False."""
        result = await local_storage.delete("nonexistent.txt")
        assert result is False
    
    async def test_exists(self, local_storage):
        """Test checking file existence."""
        key = "check-exists.txt"
        
        assert not await local_storage.exists(key)
        
        await local_storage.save(b"content", key)
        
        assert await local_storage.exists(key)
    
    async def test_get_metadata(self, local_storage):
        """Test getting file metadata."""
        content = b"metadata test"
        key = "metadata-file.txt"
        
        # Non-existent file
        metadata = await local_storage.get_metadata(key)
        assert metadata["exists"] is False
        assert metadata["key"] == key
        
        # Save file
        await local_storage.save(content, key)
        
        # Get metadata
        metadata = await local_storage.get_metadata(key)
        assert metadata["exists"] is True
        assert metadata["key"] == key
        assert metadata["size"] == len(content)
        assert "created" in metadata
        assert "modified" in metadata
        assert "path" in metadata
    
    async def test_save_stream(self, local_storage):
        """Test saving from async stream."""
        async def content_stream():
            for chunk in [b"Hello", b", ", b"World", b"!"]:
                yield chunk
        
        key = "stream-file.txt"
        saved_key = await local_storage.save_stream(content_stream(), key)
        
        assert saved_key == key
        
        loaded = await local_storage.load(key)
        assert loaded == b"Hello, World!"
    
    async def test_concurrent_operations(self, local_storage):
        """Test concurrent save/load operations."""
        # Create multiple files concurrently
        tasks = []
        for i in range(10):
            content = f"Content {i}".encode()
            key = f"concurrent-{i}.txt"
            tasks.append(local_storage.save(content, key))
        
        await asyncio.gather(*tasks)
        
        # Load all files concurrently
        load_tasks = []
        for i in range(10):
            key = f"concurrent-{i}.txt"
            load_tasks.append(local_storage.load(key))
        
        results = await asyncio.gather(*load_tasks)
        
        for i, content in enumerate(results):
            assert content == f"Content {i}".encode()


class TestS3Storage:
    """Test cases for S3 storage."""
    
    @pytest.fixture
    def s3_storage(self):
        """Create S3 storage instance."""
        with patch("torematrix.ingestion.storage.HAS_AIOBOTO3", True):
            storage = S3Storage(
                bucket="test-bucket",
                prefix="test-prefix",
                region="us-east-1"
            )
            return storage
    
    async def test_save_to_s3(self, s3_storage, mock_s3_client):
        """Test saving content to S3."""
        content = b"S3 content"
        key = "s3-file.txt"
        
        with patch.object(s3_storage._session, 'client') as mock_client_context:
            mock_client_context.return_value.__aenter__.return_value = mock_s3_client
            
            saved_key = await s3_storage.save(content, key)
            
            assert saved_key == key
            mock_s3_client.put_object.assert_called_once_with(
                Bucket="test-bucket",
                Key="test-prefix/s3-file.txt",
                Body=content,
                ContentType="application/octet-stream"
            )
    
    async def test_load_from_s3(self, s3_storage, mock_s3_client):
        """Test loading content from S3."""
        content = b"S3 content"
        key = "s3-file.txt"
        
        # Mock response
        mock_response = {
            "Body": AsyncMock()
        }
        mock_response["Body"].read = AsyncMock(return_value=content)
        mock_s3_client.get_object.return_value = mock_response
        
        with patch.object(s3_storage._session, 'client') as mock_client_context:
            mock_client_context.return_value.__aenter__.return_value = mock_s3_client
            
            loaded = await s3_storage.load(key)
            
            assert loaded == content
            mock_s3_client.get_object.assert_called_once_with(
                Bucket="test-bucket",
                Key="test-prefix/s3-file.txt"
            )
    
    async def test_delete_from_s3(self, s3_storage, mock_s3_client):
        """Test deleting from S3."""
        key = "s3-file.txt"
        
        with patch.object(s3_storage._session, 'client') as mock_client_context:
            mock_client_context.return_value.__aenter__.return_value = mock_s3_client
            
            result = await s3_storage.delete(key)
            
            assert result is True
            mock_s3_client.delete_object.assert_called_once_with(
                Bucket="test-bucket",
                Key="test-prefix/s3-file.txt"
            )
    
    async def test_exists_in_s3(self, s3_storage, mock_s3_client):
        """Test checking existence in S3."""
        key = "s3-file.txt"
        
        with patch.object(s3_storage._session, 'client') as mock_client_context:
            mock_client_context.return_value.__aenter__.return_value = mock_s3_client
            
            # File exists
            result = await s3_storage.exists(key)
            assert result is True
            
            # File doesn't exist
            mock_s3_client.head_object.side_effect = Exception("Not found")
            result = await s3_storage.exists(key)
            assert result is False
    
    async def test_s3_key_prefix(self, s3_storage):
        """Test S3 key prefix handling."""
        # With prefix
        assert s3_storage._get_key("file.txt") == "test-prefix/file.txt"
        
        # Without prefix
        s3_storage.prefix = ""
        assert s3_storage._get_key("file.txt") == "file.txt"
    
    async def test_s3_metadata(self, s3_storage, mock_s3_client):
        """Test getting S3 object metadata."""
        key = "s3-file.txt"
        
        mock_s3_client.head_object.return_value = {
            "ContentLength": 1024,
            "LastModified": "2024-01-01T00:00:00Z",
            "ETag": "abc123",
            "ContentType": "text/plain"
        }
        
        with patch.object(s3_storage._session, 'client') as mock_client_context:
            mock_client_context.return_value.__aenter__.return_value = mock_s3_client
            
            metadata = await s3_storage.get_metadata(key)
            
            assert metadata["exists"] is True
            assert metadata["size"] == 1024
            assert metadata["etag"] == "abc123"
            assert metadata["content_type"] == "text/plain"


class TestStorageManager:
    """Test cases for storage manager."""
    
    @pytest.fixture
    async def storage_manager(self, local_storage):
        """Create storage manager with local primary storage."""
        return StorageManager(primary=local_storage)
    
    @pytest.fixture
    async def storage_with_fallback(self, temp_dir):
        """Create storage manager with primary and fallback."""
        primary = LocalFileStorage(temp_dir / "primary")
        fallback = LocalFileStorage(temp_dir / "fallback")
        return StorageManager(primary=primary, fallback=fallback)
    
    async def test_save_to_primary(self, storage_manager):
        """Test saving to primary storage."""
        content = b"primary content"
        key = await storage_manager.save(content)
        
        assert key is not None
        assert await storage_manager.exists(key)
        
        loaded = await storage_manager.load(key)
        assert loaded == content
    
    async def test_save_with_key(self, storage_manager):
        """Test saving with specific key."""
        content = b"keyed content"
        key = "specific-key.txt"
        
        saved_key = await storage_manager.save(content, key)
        assert saved_key == key
        
        loaded = await storage_manager.load(key)
        assert loaded == content
    
    async def test_save_generates_uuid(self, storage_manager):
        """Test that save generates UUID if no key provided."""
        content = b"auto key content"
        
        key = await storage_manager.save(content)
        
        # Verify it's a valid UUID
        uuid.UUID(key)  # Will raise if invalid
        
        loaded = await storage_manager.load(key)
        assert loaded == content
    
    async def test_fallback_on_primary_failure(self, storage_with_fallback):
        """Test fallback storage on primary failure."""
        content = b"fallback content"
        key = "fallback-test.txt"
        
        # Make primary fail
        storage_with_fallback.primary.save = AsyncMock(side_effect=Exception("Primary failed"))
        
        # Should save to fallback
        saved_key = await storage_with_fallback.save(content, key)
        assert saved_key == key
        
        # Should load from fallback
        loaded = await storage_with_fallback.load(key)
        assert loaded == content
    
    async def test_load_from_fallback_when_missing_in_primary(self, storage_with_fallback):
        """Test loading from fallback when file missing in primary."""
        content = b"only in fallback"
        key = "fallback-only.txt"
        
        # Save directly to fallback
        await storage_with_fallback.fallback.save(content, key)
        
        # Should find in fallback
        loaded = await storage_with_fallback.load(key)
        assert loaded == content
    
    async def test_delete_from_both_storages(self, storage_with_fallback):
        """Test deletion from both primary and fallback."""
        content = b"delete from both"
        key = "delete-both.txt"
        
        # Save to both
        await storage_with_fallback.primary.save(content, key)
        await storage_with_fallback.fallback.save(content, key)
        
        # Delete should remove from both
        result = await storage_with_fallback.delete(key)
        assert result is True
        
        assert not await storage_with_fallback.primary.exists(key)
        assert not await storage_with_fallback.fallback.exists(key)
    
    async def test_exists_checks_both_storages(self, storage_with_fallback):
        """Test exists checks both storages."""
        key = "check-both.txt"
        
        # Not in either
        assert not await storage_with_fallback.exists(key)
        
        # Only in primary
        await storage_with_fallback.primary.save(b"content", key)
        assert await storage_with_fallback.exists(key)
        
        # Delete from primary, add to fallback
        await storage_with_fallback.primary.delete(key)
        await storage_with_fallback.fallback.save(b"content", key)
        assert await storage_with_fallback.exists(key)
    
    async def test_backup_to_fallback(self, storage_with_fallback):
        """Test automatic backup to fallback."""
        content = b"backup content"
        key = "backup-test.txt"
        
        # Save should trigger backup
        await storage_with_fallback.save(content, key)
        
        # Give async backup time to complete
        await asyncio.sleep(0.1)
        
        # Should exist in both
        assert await storage_with_fallback.primary.exists(key)
        assert await storage_with_fallback.fallback.exists(key)
    
    async def test_restore_to_primary(self, storage_with_fallback):
        """Test automatic restore to primary."""
        content = b"restore content"
        key = "restore-test.txt"
        
        # Save only to fallback
        await storage_with_fallback.fallback.save(content, key)
        
        # Load should trigger restore
        loaded = await storage_with_fallback.load(key)
        assert loaded == content
        
        # Give async restore time to complete
        await asyncio.sleep(0.1)
        
        # Should now exist in primary
        assert await storage_with_fallback.primary.exists(key)
    
    async def test_metadata_from_primary(self, storage_with_fallback):
        """Test getting metadata from primary first."""
        content = b"metadata content"
        key = "metadata-test.txt"
        
        await storage_with_fallback.primary.save(content, key)
        
        metadata = await storage_with_fallback.get_metadata(key)
        
        assert metadata["exists"] is True
        assert metadata["backend"] == "primary"
        assert metadata["size"] == len(content)