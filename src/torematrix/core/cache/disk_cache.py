"""Disk cache implementation with TTL support."""

import os
import time
import shutil
import pickle
from pathlib import Path
from typing import Optional, Any, Dict
from datetime import datetime, timedelta

from .cache_metrics import CacheMetrics


class DiskCache:
    """Disk-based cache implementation with TTL support."""
    
    def __init__(self, cache_dir: Path, size_limit: int = None):
        """Initialize disk cache.
        
        Args:
            cache_dir: Directory to store cache files
            size_limit: Maximum cache size in bytes (None for no limit)
        """
        self.cache_dir = cache_dir
        self.size_limit = size_limit
        self.metrics = CacheMetrics()
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize metadata storage
        self.metadata_file = self.cache_dir / "metadata.pickle"
        self.metadata = self._load_metadata()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        file_path = self._get_file_path(key)
        metadata = self.metadata.get(key)
        
        if not file_path.exists() or not metadata:
            self.metrics.record_miss('disk')
            return None
        
        # Check TTL
        if metadata['expires_at'] and metadata['expires_at'] < time.time():
            self._remove_key(key)
            self.metrics.record_miss('disk')
            return None
        
        try:
            with open(file_path, 'rb') as f:
                value = pickle.load(f)
                self.metrics.record_hit('disk')
                return value
        except (IOError, pickle.PickleError):
            self._remove_key(key)
            self.metrics.record_miss('disk')
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None for no expiration)
        """
        file_path = self._get_file_path(key)
        
        # Ensure we have space
        if self.size_limit:
            self._ensure_space_available(pickle.dumps(value))
        
        # Write value
        try:
            with open(file_path, 'wb') as f:
                pickle.dump(value, f)
        except (IOError, pickle.PickleError):
            self._remove_key(key)
            return
        
        # Update metadata
        expires_at = time.time() + ttl if ttl else None
        self.metadata[key] = {
            'created_at': time.time(),
            'expires_at': expires_at,
            'size': os.path.getsize(file_path)
        }
        self._save_metadata()
    
    def delete(self, key: str) -> None:
        """Delete value from cache.
        
        Args:
            key: Cache key
        """
        self._remove_key(key)
        self._save_metadata()
    
    def clear(self) -> None:
        """Clear all cache entries."""
        shutil.rmtree(self.cache_dir)
        self.cache_dir.mkdir(parents=True)
        self.metadata = {}
        self._save_metadata()
    
    def get_size(self) -> int:
        """Get total size of cached files in bytes."""
        return sum(
            metadata['size'] 
            for metadata in self.metadata.values()
        )
    
    def _get_file_path(self, key: str) -> Path:
        """Get file path for cache key."""
        # Use hash of key as filename to avoid filesystem issues
        filename = f"{hash(key)}.cache"
        return self.cache_dir / filename
    
    def _remove_key(self, key: str) -> None:
        """Remove key from cache and delete associated file."""
        file_path = self._get_file_path(key)
        try:
            file_path.unlink(missing_ok=True)
        except OSError:
            pass
        self.metadata.pop(key, None)
    
    def _ensure_space_available(self, new_value_size: int) -> None:
        """Ensure space is available for new value, removing old entries if needed."""
        if not self.size_limit:
            return
            
        current_size = self.get_size()
        needed_space = current_size + new_value_size - self.size_limit
        
        if needed_space <= 0:
            return
            
        # Remove oldest entries until we have space
        entries = sorted(
            self.metadata.items(),
            key=lambda x: x[1]['created_at']
        )
        
        space_freed = 0
        for key, metadata in entries:
            self._remove_key(key)
            space_freed += metadata['size']
            if space_freed >= needed_space:
                break
    
    def _load_metadata(self) -> Dict:
        """Load cache metadata from disk."""
        if not self.metadata_file.exists():
            return {}
            
        try:
            with open(self.metadata_file, 'rb') as f:
                return pickle.load(f)
        except (IOError, pickle.PickleError):
            return {}
    
    def _save_metadata(self) -> None:
        """Save cache metadata to disk."""
        try:
            with open(self.metadata_file, 'wb') as f:
                pickle.dump(self.metadata, f)
        except (IOError, pickle.PickleError):
            pass  # Ignore errors saving metadata