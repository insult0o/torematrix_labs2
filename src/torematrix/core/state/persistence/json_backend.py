"""
JSON file-based persistence backend.

This backend stores state as JSON files on disk, providing a simple
and human-readable persistence solution.
"""

import json
import os
import aiofiles
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
from datetime import datetime
import gzip
import tempfile
import shutil

from .base import PersistenceBackend, PersistenceConfig

logger = logging.getLogger(__name__)


class JSONPersistenceBackend(PersistenceBackend):
    """
    JSON file-based persistence backend.
    
    Stores each state version as a separate JSON file in a directory structure.
    Supports compression and atomic writes for data integrity.
    """
    
    def __init__(self, config: PersistenceConfig, storage_path: str = "state_storage"):
        super().__init__(config)
        self.storage_path = Path(storage_path)
        self.states_dir = self.storage_path / "states"
        self.metadata_dir = self.storage_path / "metadata"
        self._file_locks: Dict[str, asyncio.Lock] = {}
        
    async def _do_initialize(self) -> None:
        """Initialize the JSON storage directories."""
        try:
            # Create directories if they don't exist
            self.states_dir.mkdir(parents=True, exist_ok=True)
            self.metadata_dir.mkdir(parents=True, exist_ok=True)
            
            # Create index file if it doesn't exist
            index_file = self.storage_path / "index.json"
            if not index_file.exists():
                await self._write_index({
                    "versions": [],
                    "latest_version": None,
                    "created_at": datetime.now().isoformat(),
                    "format_version": "1.0"
                })
                
            logger.info(f"JSON persistence backend initialized at {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize JSON backend: {e}")
            raise
    
    async def save_state(
        self, 
        state: Dict[str, Any], 
        version: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save state to a JSON file.
        
        Args:
            state: The state data to save
            version: Version identifier for this state
            metadata: Optional metadata associated with this state
        """
        try:
            # Prepare state data
            state_data = {
                "version": version,
                "timestamp": datetime.now().isoformat(),
                "state": state,
                "compressed": self.config.compression_enabled
            }
            
            # Prepare metadata
            metadata_data = {
                "version": version,
                "timestamp": datetime.now().isoformat(),
                "size_bytes": 0,  # Will be updated after saving
                "compression_ratio": 1.0,  # Will be updated if compressed
                **(metadata or {})
            }
            
            # Get file lock for this version
            if version not in self._file_locks:
                self._file_locks[version] = asyncio.Lock()
            
            async with self._file_locks[version]:
                # Save state file
                state_file = self.states_dir / f"{version}.json"
                await self._save_state_file(state_file, state_data)
                
                # Update metadata with actual file size
                metadata_data["size_bytes"] = state_file.stat().st_size
                
                # Save metadata file
                metadata_file = self.metadata_dir / f"{version}.json"
                await self._save_metadata_file(metadata_file, metadata_data)
                
                # Update index
                await self._update_index(version)
                
            logger.debug(f"State version {version} saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save state version {version}: {e}")
            raise
    
    async def load_state(self, version: Optional[str] = None) -> Dict[str, Any]:
        """
        Load state from a JSON file.
        
        Args:
            version: Specific version to load, or None for latest
            
        Returns:
            The loaded state data
        """
        try:
            if version is None:
                version = await self._get_latest_version()
                if version is None:
                    return {}
            
            state_file = self.states_dir / f"{version}.json"
            if not state_file.exists():
                raise FileNotFoundError(f"State version {version} not found")
            
            # Get file lock for this version
            if version not in self._file_locks:
                self._file_locks[version] = asyncio.Lock()
            
            async with self._file_locks[version]:
                state_data = await self._load_state_file(state_file)
                
            logger.debug(f"State version {version} loaded successfully")
            return state_data["state"]
            
        except Exception as e:
            logger.error(f"Failed to load state version {version}: {e}")
            raise
    
    async def list_versions(self) -> List[str]:
        """
        List all saved state versions.
        
        Returns:
            List of version identifiers, sorted by creation time
        """
        try:
            index = await self._read_index()
            return index.get("versions", [])
        except Exception as e:
            logger.error(f"Failed to list versions: {e}")
            return []
    
    async def delete_version(self, version: str) -> bool:
        """
        Delete a specific state version.
        
        Args:
            version: Version identifier to delete
            
        Returns:
            True if version was deleted, False if it didn't exist
        """
        try:
            state_file = self.states_dir / f"{version}.json"
            metadata_file = self.metadata_dir / f"{version}.json"
            
            deleted = False
            
            # Get file lock for this version
            if version not in self._file_locks:
                self._file_locks[version] = asyncio.Lock()
            
            async with self._file_locks[version]:
                # Delete state file
                if state_file.exists():
                    state_file.unlink()
                    deleted = True
                
                # Delete metadata file
                if metadata_file.exists():
                    metadata_file.unlink()
                    deleted = True
                
                # Update index
                if deleted:
                    await self._remove_from_index(version)
            
            # Clean up lock
            if version in self._file_locks:
                del self._file_locks[version]
            
            logger.debug(f"State version {version} deleted: {deleted}")
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete state version {version}: {e}")
            return False
    
    async def get_metadata(self, version: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific version.
        
        Args:
            version: Version identifier
            
        Returns:
            Metadata dict or None if version doesn't exist
        """
        try:
            metadata_file = self.metadata_dir / f"{version}.json"
            if not metadata_file.exists():
                return None
            
            # Get file lock for this version
            if version not in self._file_locks:
                self._file_locks[version] = asyncio.Lock()
            
            async with self._file_locks[version]:
                metadata = await self._load_metadata_file(metadata_file)
                
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to get metadata for version {version}: {e}")
            return None
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        self._file_locks.clear()
        logger.debug("JSON persistence backend cleaned up")
    
    async def _save_state_file(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Save state data to a JSON file with atomic write."""
        # Use a temporary file for atomic write
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.json.tmp',
                dir=file_path.parent,
                delete=False
            ) as tf:
                temp_file = Path(tf.name)
                
                if self.config.compression_enabled:
                    # Write compressed JSON
                    json_str = json.dumps(data, indent=2, ensure_ascii=False)
                    with gzip.open(temp_file.with_suffix('.json.gz.tmp'), 'wt', encoding='utf-8') as gz_file:
                        gz_file.write(json_str)
                    
                    # Update compression ratio in data
                    original_size = len(json_str.encode('utf-8'))
                    compressed_size = temp_file.with_suffix('.json.gz.tmp').stat().st_size
                    data["compression_ratio"] = compressed_size / original_size if original_size > 0 else 1.0
                    
                    # Move compressed file to final location
                    shutil.move(str(temp_file.with_suffix('.json.gz.tmp')), str(file_path.with_suffix('.json.gz')))
                else:
                    # Write uncompressed JSON
                    json.dump(data, tf, indent=2, ensure_ascii=False)
                    tf.flush()
                    os.fsync(tf.fileno())
                    
                    # Move to final location
                    shutil.move(str(temp_file), str(file_path))
                    
        except Exception as e:
            # Clean up temp file if it exists
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass
            raise e
    
    async def _load_state_file(self, file_path: Path) -> Dict[str, Any]:
        """Load state data from a JSON file."""
        # Check for compressed version first
        compressed_file = file_path.with_suffix('.json.gz')
        
        if compressed_file.exists():
            # Load compressed file
            async with aiofiles.open(compressed_file, 'rb') as f:
                compressed_data = await f.read()
                json_str = gzip.decompress(compressed_data).decode('utf-8')
                return json.loads(json_str)
        else:
            # Load uncompressed file
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
    
    async def _save_metadata_file(self, file_path: Path, metadata: Dict[str, Any]) -> None:
        """Save metadata to a JSON file."""
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(metadata, indent=2, ensure_ascii=False))
    
    async def _load_metadata_file(self, file_path: Path) -> Dict[str, Any]:
        """Load metadata from a JSON file."""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            return json.loads(content)
    
    async def _read_index(self) -> Dict[str, Any]:
        """Read the index file."""
        index_file = self.storage_path / "index.json"
        async with aiofiles.open(index_file, 'r', encoding='utf-8') as f:
            content = await f.read()
            return json.loads(content)
    
    async def _write_index(self, index_data: Dict[str, Any]) -> None:
        """Write the index file atomically."""
        index_file = self.storage_path / "index.json"
        temp_file = index_file.with_suffix('.json.tmp')
        
        try:
            async with aiofiles.open(temp_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(index_data, indent=2, ensure_ascii=False))
            
            # Atomic move
            shutil.move(str(temp_file), str(index_file))
            
        except Exception as e:
            # Clean up temp file
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass
            raise e
    
    async def _update_index(self, version: str) -> None:
        """Update the index with a new version."""
        index = await self._read_index()
        
        versions = index.get("versions", [])
        if version not in versions:
            versions.append(version)
            # Sort versions by timestamp (assuming version format includes timestamp)
            versions.sort()
        
        index["versions"] = versions
        index["latest_version"] = version
        index["last_updated"] = datetime.now().isoformat()
        
        await self._write_index(index)
    
    async def _remove_from_index(self, version: str) -> None:
        """Remove a version from the index."""
        index = await self._read_index()
        
        versions = index.get("versions", [])
        if version in versions:
            versions.remove(version)
        
        # Update latest version if needed
        if index.get("latest_version") == version:
            index["latest_version"] = versions[-1] if versions else None
        
        index["versions"] = versions
        index["last_updated"] = datetime.now().isoformat()
        
        await self._write_index(index)
    
    async def _get_latest_version(self) -> Optional[str]:
        """Get the latest version from the index."""
        index = await self._read_index()
        return index.get("latest_version")
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        try:
            index = await self._read_index()
            versions = index.get("versions", [])
            
            total_size = 0
            compressed_size = 0
            
            for version in versions:
                state_file = self.states_dir / f"{version}.json"
                compressed_file = state_file.with_suffix('.json.gz')
                
                if compressed_file.exists():
                    size = compressed_file.stat().st_size
                    compressed_size += size
                    total_size += size
                elif state_file.exists():
                    size = state_file.stat().st_size
                    total_size += size
            
            return {
                "total_versions": len(versions),
                "total_size_bytes": total_size,
                "compressed_size_bytes": compressed_size,
                "compression_ratio": compressed_size / total_size if total_size > 0 else 1.0,
                "storage_path": str(self.storage_path),
                "latest_version": index.get("latest_version")
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {}