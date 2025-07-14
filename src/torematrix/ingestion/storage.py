"""
Storage abstraction layer for document ingestion.

Provides a unified interface for storing files across different backends
including local filesystem and S3-compatible object storage.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Union
from pathlib import Path
import aiofiles
import os
import uuid
import asyncio
import logging
from datetime import datetime

try:
    import aioboto3
    HAS_AIOBOTO3 = True
except ImportError:
    HAS_AIOBOTO3 = False

try:
    from azure.storage.blob.aio import BlobServiceClient
    HAS_AZURE = True
except ImportError:
    HAS_AZURE = False

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    async def save(self, content: bytes, key: str) -> str:
        """
        Save content and return storage key.
        
        Args:
            content: File content as bytes
            key: Storage key/path
            
        Returns:
            Storage key for retrieval
        """
        pass
    
    @abstractmethod
    async def load(self, key: str) -> bytes:
        """
        Load content by key.
        
        Args:
            key: Storage key/path
            
        Returns:
            File content as bytes
            
        Raises:
            FileNotFoundError: If key doesn't exist
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete content by key.
        
        Args:
            key: Storage key/path
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if key exists.
        
        Args:
            key: Storage key/path
            
        Returns:
            True if exists, False otherwise
        """
        pass
    
    async def save_stream(self, stream: AsyncIterator[bytes], key: str) -> str:
        """
        Save content from an async stream.
        
        Default implementation collects chunks and saves.
        Backends can override for streaming support.
        """
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
        content = b"".join(chunks)
        return await self.save(content, key)
    
    async def get_metadata(self, key: str) -> dict:
        """Get metadata about stored object."""
        return {
            "exists": await self.exists(key),
            "key": key
        }


class LocalFileStorage(StorageBackend):
    """Local filesystem storage implementation."""
    
    def __init__(self, base_path: Union[str, Path]):
        """
        Initialize local storage.
        
        Args:
            base_path: Base directory for file storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized local storage at {self.base_path}")
    
    def _get_path(self, key: str) -> Path:
        """
        Get full path for a storage key.
        
        Creates subdirectories based on key prefix for better organization.
        """
        # Use first 2 chars as directory prefix to avoid too many files in one dir
        if len(key) >= 2:
            prefix = key[:2]
            return self.base_path / prefix / key
        return self.base_path / key
    
    async def save(self, content: bytes, key: str) -> str:
        """Save content to local filesystem."""
        path = self._get_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            async with aiofiles.open(path, "wb") as f:
                await f.write(content)
            
            logger.debug(f"Saved {len(content)} bytes to {path}")
            return key
            
        except Exception as e:
            logger.error(f"Failed to save file {key}: {e}")
            raise
    
    async def load(self, key: str) -> bytes:
        """Load content from local filesystem."""
        path = self._get_path(key)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        
        try:
            async with aiofiles.open(path, "rb") as f:
                content = await f.read()
            
            logger.debug(f"Loaded {len(content)} bytes from {path}")
            return content
            
        except Exception as e:
            logger.error(f"Failed to load file {key}: {e}")
            raise
    
    async def delete(self, key: str) -> bool:
        """Delete file from local filesystem."""
        path = self._get_path(key)
        
        try:
            if path.exists():
                path.unlink()
                
                # Try to remove empty parent directory
                try:
                    path.parent.rmdir()
                except OSError:
                    pass  # Directory not empty
                
                logger.debug(f"Deleted file {key}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete file {key}: {e}")
            raise
    
    async def exists(self, key: str) -> bool:
        """Check if file exists in local filesystem."""
        return self._get_path(key).exists()
    
    async def get_metadata(self, key: str) -> dict:
        """Get file metadata."""
        path = self._get_path(key)
        
        if not path.exists():
            return {"exists": False, "key": key}
        
        stat = path.stat()
        return {
            "exists": True,
            "key": key,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "path": str(path)
        }


class S3Storage(StorageBackend):
    """AWS S3 storage backend implementation."""
    
    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None
    ):
        """
        Initialize S3 storage.
        
        Args:
            bucket: S3 bucket name
            prefix: Key prefix for all objects
            region: AWS region
            endpoint_url: Custom endpoint (for S3-compatible services)
            access_key_id: AWS access key (uses default if not provided)
            secret_access_key: AWS secret key (uses default if not provided)
        """
        if not HAS_AIOBOTO3:
            raise ImportError("aioboto3 is required for S3 storage. Install with: pip install aioboto3")
        
        self.bucket = bucket
        self.prefix = prefix.rstrip("/")
        self.region = region
        self.endpoint_url = endpoint_url
        
        # Create session with credentials if provided
        session_kwargs = {}
        if access_key_id and secret_access_key:
            session_kwargs.update({
                "aws_access_key_id": access_key_id,
                "aws_secret_access_key": secret_access_key
            })
        
        self._session = aioboto3.Session(**session_kwargs)
        logger.info(f"Initialized S3 storage for bucket: {bucket}")
    
    def _get_key(self, key: str) -> str:
        """Get full S3 key with prefix."""
        if self.prefix:
            return f"{self.prefix}/{key}"
        return key
    
    async def save(self, content: bytes, key: str) -> str:
        """Save content to S3."""
        full_key = self._get_key(key)
        
        try:
            async with self._session.client(
                "s3",
                region_name=self.region,
                endpoint_url=self.endpoint_url
            ) as s3:
                await s3.put_object(
                    Bucket=self.bucket,
                    Key=full_key,
                    Body=content,
                    ContentType="application/octet-stream"
                )
            
            logger.debug(f"Saved {len(content)} bytes to s3://{self.bucket}/{full_key}")
            return key
            
        except Exception as e:
            logger.error(f"Failed to save to S3 {key}: {e}")
            raise
    
    async def load(self, key: str) -> bytes:
        """Load content from S3."""
        full_key = self._get_key(key)
        
        try:
            async with self._session.client(
                "s3",
                region_name=self.region,
                endpoint_url=self.endpoint_url
            ) as s3:
                response = await s3.get_object(Bucket=self.bucket, Key=full_key)
                content = await response["Body"].read()
            
            logger.debug(f"Loaded {len(content)} bytes from s3://{self.bucket}/{full_key}")
            return content
            
        except s3.exceptions.NoSuchKey:
            raise FileNotFoundError(f"S3 object not found: {key}")
        except Exception as e:
            logger.error(f"Failed to load from S3 {key}: {e}")
            raise
    
    async def delete(self, key: str) -> bool:
        """Delete object from S3."""
        full_key = self._get_key(key)
        
        try:
            async with self._session.client(
                "s3",
                region_name=self.region,
                endpoint_url=self.endpoint_url
            ) as s3:
                await s3.delete_object(Bucket=self.bucket, Key=full_key)
            
            logger.debug(f"Deleted s3://{self.bucket}/{full_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete from S3 {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if object exists in S3."""
        full_key = self._get_key(key)
        
        try:
            async with self._session.client(
                "s3",
                region_name=self.region,
                endpoint_url=self.endpoint_url
            ) as s3:
                await s3.head_object(Bucket=self.bucket, Key=full_key)
                return True
                
        except:
            return False
    
    async def get_metadata(self, key: str) -> dict:
        """Get S3 object metadata."""
        full_key = self._get_key(key)
        
        try:
            async with self._session.client(
                "s3",
                region_name=self.region,
                endpoint_url=self.endpoint_url
            ) as s3:
                response = await s3.head_object(Bucket=self.bucket, Key=full_key)
                
                return {
                    "exists": True,
                    "key": key,
                    "size": response.get("ContentLength", 0),
                    "modified": response.get("LastModified", "").isoformat() if response.get("LastModified") else None,
                    "etag": response.get("ETag", "").strip('"'),
                    "content_type": response.get("ContentType", ""),
                    "s3_key": full_key
                }
                
        except:
            return {"exists": False, "key": key}


class StorageManager:
    """
    Manages multiple storage backends with fallback support.
    
    Provides high-level operations with automatic failover between
    primary and fallback storage backends.
    """
    
    def __init__(
        self,
        primary: StorageBackend,
        fallback: Optional[StorageBackend] = None
    ):
        """
        Initialize storage manager.
        
        Args:
            primary: Primary storage backend
            fallback: Optional fallback storage backend
        """
        self.primary = primary
        self.fallback = fallback
        self._lock = asyncio.Lock()
        logger.info("Initialized storage manager")
    
    async def save(self, content: bytes, key: Optional[str] = None) -> str:
        """
        Save content to storage with automatic failover.
        
        Args:
            content: File content
            key: Optional storage key (generated if not provided)
            
        Returns:
            Storage key for retrieval
        """
        if not key:
            key = str(uuid.uuid4())
        
        try:
            # Try primary storage
            result = await self.primary.save(content, key)
            
            # Async backup to fallback if configured
            if self.fallback:
                asyncio.create_task(self._backup_to_fallback(content, key))
            
            return result
            
        except Exception as e:
            logger.warning(f"Primary storage failed: {e}")
            
            # Try fallback storage
            if self.fallback:
                try:
                    return await self.fallback.save(content, key)
                except Exception as fallback_error:
                    logger.error(f"Fallback storage also failed: {fallback_error}")
            
            # Re-raise original error if no fallback or fallback failed
            raise
    
    async def load(self, key: str) -> bytes:
        """
        Load content from storage with automatic failover.
        
        Args:
            key: Storage key
            
        Returns:
            File content as bytes
        """
        try:
            # Try primary storage
            return await self.primary.load(key)
            
        except FileNotFoundError:
            # Try fallback for missing files
            if self.fallback and await self.fallback.exists(key):
                logger.info(f"Loading {key} from fallback storage")
                content = await self.fallback.load(key)
                
                # Restore to primary storage
                asyncio.create_task(self._restore_to_primary(content, key))
                
                return content
            
            # Not found in either storage
            raise
            
        except Exception as e:
            logger.warning(f"Primary storage error: {e}")
            
            # Try fallback for other errors
            if self.fallback:
                try:
                    return await self.fallback.load(key)
                except Exception as fallback_error:
                    logger.error(f"Fallback storage also failed: {fallback_error}")
            
            raise
    
    async def delete(self, key: str) -> bool:
        """
        Delete from both primary and fallback storage.
        
        Args:
            key: Storage key
            
        Returns:
            True if deleted from at least one backend
        """
        results = []
        
        # Delete from primary
        try:
            results.append(await self.primary.delete(key))
        except Exception as e:
            logger.error(f"Failed to delete from primary storage: {e}")
            results.append(False)
        
        # Delete from fallback
        if self.fallback:
            try:
                results.append(await self.fallback.delete(key))
            except Exception as e:
                logger.error(f"Failed to delete from fallback storage: {e}")
                results.append(False)
        
        return any(results)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in any storage backend."""
        try:
            if await self.primary.exists(key):
                return True
        except Exception as e:
            logger.warning(f"Error checking primary storage: {e}")
        
        if self.fallback:
            try:
                return await self.fallback.exists(key)
            except Exception as e:
                logger.warning(f"Error checking fallback storage: {e}")
        
        return False
    
    async def get_metadata(self, key: str) -> dict:
        """Get metadata from primary storage, fallback if needed."""
        try:
            metadata = await self.primary.get_metadata(key)
            if metadata.get("exists"):
                metadata["backend"] = "primary"
                return metadata
        except Exception as e:
            logger.warning(f"Error getting metadata from primary: {e}")
        
        if self.fallback:
            try:
                metadata = await self.fallback.get_metadata(key)
                if metadata.get("exists"):
                    metadata["backend"] = "fallback"
                    return metadata
            except Exception as e:
                logger.warning(f"Error getting metadata from fallback: {e}")
        
        return {"exists": False, "key": key}
    
    async def _backup_to_fallback(self, content: bytes, key: str):
        """Async backup to fallback storage."""
        try:
            await self.fallback.save(content, key)
            logger.debug(f"Backed up {key} to fallback storage")
        except Exception as e:
            logger.warning(f"Failed to backup {key} to fallback: {e}")
    
    async def _restore_to_primary(self, content: bytes, key: str):
        """Async restore to primary storage."""
        try:
            await self.primary.save(content, key)
            logger.debug(f"Restored {key} to primary storage")
        except Exception as e:
            logger.warning(f"Failed to restore {key} to primary: {e}")