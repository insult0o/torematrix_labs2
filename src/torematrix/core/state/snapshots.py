"""
State snapshot management system.

This module provides comprehensive snapshot functionality for state management,
including compression, incremental snapshots, and efficient storage.
"""

import asyncio
import time
import gzip
import pickle
import json
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Set
from enum import Enum
import logging
from datetime import datetime
import copy

logger = logging.getLogger(__name__)


class SnapshotType(Enum):
    """Types of snapshots."""
    FULL = "full"           # Complete state snapshot
    INCREMENTAL = "incremental"  # Changes since last snapshot
    COMPRESSED = "compressed"    # Compressed full snapshot
    DELTA = "delta"         # Delta-based incremental


class CompressionAlgorithm(Enum):
    """Compression algorithms for snapshots."""
    NONE = "none"
    GZIP = "gzip"
    PICKLE = "pickle"
    JSON_GZIP = "json_gzip"


@dataclass
class Snapshot:
    """
    Represents a state snapshot with metadata.
    
    Snapshots can be full state captures or incremental changes,
    with optional compression and encryption.
    """
    id: str
    timestamp: float
    state: Union[Dict[str, Any], bytes]  # Can be compressed bytes
    metadata: Dict[str, Any] = field(default_factory=dict)
    snapshot_type: SnapshotType = SnapshotType.FULL
    compression: CompressionAlgorithm = CompressionAlgorithm.NONE
    compressed: bool = False
    size_bytes: int = 0
    checksum: str = ""
    parent_snapshot_id: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        """Post-initialization to calculate derived fields."""
        if not self.metadata:
            self.metadata = {}
        
        # Calculate size if not provided
        if self.size_bytes == 0:
            self.size_bytes = self._calculate_size()
        
        # Calculate checksum if not provided
        if not self.checksum:
            self.checksum = self._calculate_checksum()
        
        # Add timestamp metadata
        self.metadata.update({
            "created_at": datetime.fromtimestamp(self.timestamp).isoformat(),
            "size_bytes": self.size_bytes,
            "compressed": self.compressed,
            "compression_algorithm": self.compression.value,
            "snapshot_type": self.snapshot_type.value,
        })
    
    def _calculate_size(self) -> int:
        """Calculate the size of the snapshot data."""
        if isinstance(self.state, bytes):
            return len(self.state)
        else:
            # Estimate size for dict
            try:
                return len(json.dumps(self.state).encode('utf-8'))
            except Exception:
                return 0
    
    def _calculate_checksum(self) -> str:
        """Calculate checksum for data integrity."""
        if isinstance(self.state, bytes):
            return hashlib.sha256(self.state).hexdigest()
        else:
            # Create deterministic JSON string
            try:
                json_str = json.dumps(self.state, sort_keys=True, ensure_ascii=False)
                return hashlib.sha256(json_str.encode('utf-8')).hexdigest()
            except Exception:
                return ""
    
    def verify_integrity(self) -> bool:
        """Verify snapshot data integrity using checksum."""
        return self._calculate_checksum() == self.checksum
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the snapshot."""
        self.tags.add(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the snapshot."""
        self.tags.discard(tag)
    
    def has_tag(self, tag: str) -> bool:
        """Check if snapshot has a specific tag."""
        return tag in self.tags
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary for serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "state": self.state if isinstance(self.state, dict) else None,
            "state_bytes": self.state.hex() if isinstance(self.state, bytes) else None,
            "metadata": self.metadata,
            "snapshot_type": self.snapshot_type.value,
            "compression": self.compression.value,
            "compressed": self.compressed,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "parent_snapshot_id": self.parent_snapshot_id,
            "tags": list(self.tags),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Snapshot":
        """Create snapshot from dictionary."""
        # Handle state data
        if data.get("state_bytes"):
            state = bytes.fromhex(data["state_bytes"])
        else:
            state = data.get("state", {})
        
        return cls(
            id=data["id"],
            timestamp=data["timestamp"],
            state=state,
            metadata=data.get("metadata", {}),
            snapshot_type=SnapshotType(data.get("snapshot_type", "full")),
            compression=CompressionAlgorithm(data.get("compression", "none")),
            compressed=data.get("compressed", False),
            size_bytes=data.get("size_bytes", 0),
            checksum=data.get("checksum", ""),
            parent_snapshot_id=data.get("parent_snapshot_id"),
            tags=set(data.get("tags", [])),
        )


@dataclass
class SnapshotStrategy:
    """Configuration for snapshot creation strategy."""
    auto_snapshot: bool = True
    snapshot_interval: float = 300.0  # 5 minutes
    max_snapshots: int = 100
    compression_enabled: bool = True
    compression_algorithm: CompressionAlgorithm = CompressionAlgorithm.JSON_GZIP
    incremental_threshold: int = 10  # Actions before creating incremental
    auto_tag_enabled: bool = True
    retention_days: Optional[int] = 30


class SnapshotManager:
    """
    Comprehensive snapshot management system.
    
    Provides functionality for:
    - Creating full and incremental snapshots
    - Compression and decompression
    - Snapshot restoration
    - Automatic cleanup and retention
    - Performance optimization
    """
    
    def __init__(
        self,
        strategy: Optional[SnapshotStrategy] = None,
        compression_enabled: bool = True
    ):
        self.strategy = strategy or SnapshotStrategy()
        self.compression_enabled = compression_enabled
        
        # Storage
        self._snapshots: Dict[str, Snapshot] = {}
        self._snapshot_index: List[str] = []  # Ordered by timestamp
        self._tags_index: Dict[str, Set[str]] = {}  # tag -> snapshot_ids
        
        # State tracking
        self._last_snapshot_time = 0.0
        self._actions_since_snapshot = 0
        self._current_state_hash = ""
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._auto_snapshot_task: Optional[asyncio.Task] = None
        
        # Statistics
        self._stats = {
            "total_snapshots": 0,
            "full_snapshots": 0,
            "incremental_snapshots": 0,
            "total_size_bytes": 0,
            "compression_ratio": 1.0,
            "average_snapshot_time": 0.0,
        }
    
    async def start(self) -> None:
        """Start the snapshot manager and background tasks."""
        if self.strategy.auto_snapshot:
            self._auto_snapshot_task = asyncio.create_task(self._auto_snapshot_worker())
        
        self._cleanup_task = asyncio.create_task(self._cleanup_worker())
        logger.info("Snapshot manager started")
    
    async def stop(self) -> None:
        """Stop the snapshot manager and cleanup tasks."""
        if self._auto_snapshot_task:
            self._auto_snapshot_task.cancel()
            try:
                await self._auto_snapshot_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Snapshot manager stopped")
    
    def create_snapshot(
        self,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[Set[str]] = None,
        snapshot_type: Optional[SnapshotType] = None
    ) -> str:
        """
        Create a new snapshot.
        
        Args:
            state: Current state to snapshot
            metadata: Additional metadata
            tags: Tags for the snapshot
            snapshot_type: Type of snapshot to create
            
        Returns:
            The ID of the created snapshot
        """
        start_time = time.time()
        
        # Generate snapshot ID
        snapshot_id = f"snapshot_{int(time.time() * 1000000)}"
        
        # Determine snapshot type
        if snapshot_type is None:
            snapshot_type = self._determine_snapshot_type(state)
        
        # Create snapshot based on type
        if snapshot_type == SnapshotType.INCREMENTAL:
            snapshot_data = self._create_incremental_snapshot(state)
            parent_id = self._get_latest_snapshot_id()
        else:
            snapshot_data = copy.deepcopy(state)
            parent_id = None
        
        # Apply compression if enabled
        compressed_data, compression_algo = self._compress_data(snapshot_data)
        
        # Create snapshot object
        snapshot = Snapshot(
            id=snapshot_id,
            timestamp=time.time(),
            state=compressed_data,
            metadata=metadata or {},
            snapshot_type=snapshot_type,
            compression=compression_algo,
            compressed=compression_algo != CompressionAlgorithm.NONE,
            parent_snapshot_id=parent_id,
            tags=tags or set()
        )
        
        # Add automatic tags
        if self.strategy.auto_tag_enabled:
            self._add_auto_tags(snapshot, state)
        
        # Store snapshot
        self._snapshots[snapshot_id] = snapshot
        self._snapshot_index.append(snapshot_id)
        self._snapshot_index.sort(key=lambda sid: self._snapshots[sid].timestamp)
        
        # Update tags index
        for tag in snapshot.tags:
            if tag not in self._tags_index:
                self._tags_index[tag] = set()
            self._tags_index[tag].add(snapshot_id)
        
        # Update tracking
        self._last_snapshot_time = time.time()
        self._actions_since_snapshot = 0
        self._current_state_hash = snapshot.checksum
        
        # Update statistics
        creation_time = time.time() - start_time
        self._update_stats(snapshot, creation_time)
        
        # Auto-cleanup if needed
        if len(self._snapshots) > self.strategy.max_snapshots:
            self._prune_old_snapshots()
        
        logger.debug(f"Created {snapshot_type.value} snapshot: {snapshot_id}")
        return snapshot_id
    
    def restore_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """
        Restore state from a snapshot.
        
        Args:
            snapshot_id: ID of the snapshot to restore
            
        Returns:
            The restored state, or None if snapshot not found
        """
        if snapshot_id not in self._snapshots:
            logger.warning(f"Snapshot not found: {snapshot_id}")
            return None
        
        snapshot = self._snapshots[snapshot_id]
        
        # Verify integrity
        if not snapshot.verify_integrity():
            logger.error(f"Snapshot integrity check failed: {snapshot_id}")
            return None
        
        try:
            # Decompress data
            state_data = self._decompress_data(snapshot.state, snapshot.compression)
            
            # Handle different snapshot types
            if snapshot.snapshot_type == SnapshotType.INCREMENTAL:
                # Need to restore from base snapshot and apply incremental changes
                return self._restore_incremental_snapshot(snapshot, state_data)
            else:
                # Full snapshot - return as is
                return state_data
                
        except Exception as e:
            logger.error(f"Failed to restore snapshot {snapshot_id}: {e}")
            return None
    
    def create_incremental(
        self,
        base_snapshot_id: str,
        current_state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create an incremental snapshot based on a base snapshot.
        
        Args:
            base_snapshot_id: ID of the base snapshot
            current_state: Current state to create incremental from
            metadata: Additional metadata
            
        Returns:
            ID of the created incremental snapshot, or None if base not found
        """
        if base_snapshot_id not in self._snapshots:
            logger.warning(f"Base snapshot not found: {base_snapshot_id}")
            return None
        
        base_snapshot = self._snapshots[base_snapshot_id]
        base_state = self.restore_snapshot(base_snapshot_id)
        
        if base_state is None:
            logger.error(f"Failed to restore base snapshot: {base_snapshot_id}")
            return None
        
        # Calculate delta
        delta = self._calculate_delta(base_state, current_state)
        
        # Create incremental snapshot
        return self.create_snapshot(
            state=delta,
            metadata=metadata,
            snapshot_type=SnapshotType.INCREMENTAL
        )
    
    def list_snapshots(
        self,
        tags: Optional[Set[str]] = None,
        snapshot_type: Optional[SnapshotType] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """
        List snapshots with optional filtering.
        
        Args:
            tags: Filter by tags (AND operation)
            snapshot_type: Filter by snapshot type
            limit: Maximum number of snapshots to return
            
        Returns:
            List of snapshot IDs matching the criteria
        """
        snapshot_ids = self._snapshot_index.copy()
        
        # Filter by tags
        if tags:
            filtered_ids = set(snapshot_ids)
            for tag in tags:
                if tag in self._tags_index:
                    filtered_ids &= self._tags_index[tag]
                else:
                    filtered_ids = set()  # Tag not found
                    break
            snapshot_ids = list(filtered_ids)
        
        # Filter by type
        if snapshot_type:
            snapshot_ids = [
                sid for sid in snapshot_ids
                if self._snapshots[sid].snapshot_type == snapshot_type
            ]
        
        # Sort by timestamp (newest first)
        snapshot_ids.sort(
            key=lambda sid: self._snapshots[sid].timestamp,
            reverse=True
        )
        
        # Apply limit
        if limit:
            snapshot_ids = snapshot_ids[:limit]
        
        return snapshot_ids
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """
        Delete a snapshot.
        
        Args:
            snapshot_id: ID of the snapshot to delete
            
        Returns:
            True if snapshot was deleted, False if not found
        """
        if snapshot_id not in self._snapshots:
            return False
        
        snapshot = self._snapshots[snapshot_id]
        
        # Check for dependent snapshots
        dependents = self._find_dependent_snapshots(snapshot_id)
        if dependents:
            logger.warning(
                f"Cannot delete snapshot {snapshot_id}: "
                f"has {len(dependents)} dependent snapshots"
            )
            return False
        
        # Remove from indexes
        del self._snapshots[snapshot_id]
        if snapshot_id in self._snapshot_index:
            self._snapshot_index.remove(snapshot_id)
        
        # Update tags index
        for tag in snapshot.tags:
            if tag in self._tags_index:
                self._tags_index[tag].discard(snapshot_id)
                if not self._tags_index[tag]:
                    del self._tags_index[tag]
        
        # Update stats
        self._stats["total_snapshots"] -= 1
        if snapshot.snapshot_type == SnapshotType.FULL:
            self._stats["full_snapshots"] -= 1
        else:
            self._stats["incremental_snapshots"] -= 1
        
        logger.debug(f"Deleted snapshot: {snapshot_id}")
        return True
    
    def get_snapshot_info(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a snapshot."""
        if snapshot_id not in self._snapshots:
            return None
        
        snapshot = self._snapshots[snapshot_id]
        return {
            "id": snapshot.id,
            "timestamp": snapshot.timestamp,
            "created_at": snapshot.metadata.get("created_at"),
            "snapshot_type": snapshot.snapshot_type.value,
            "size_bytes": snapshot.size_bytes,
            "compressed": snapshot.compressed,
            "compression_algorithm": snapshot.compression.value,
            "checksum": snapshot.checksum,
            "parent_snapshot_id": snapshot.parent_snapshot_id,
            "tags": list(snapshot.tags),
            "metadata": snapshot.metadata,
        }
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Get snapshot manager statistics."""
        total_size = sum(s.size_bytes for s in self._snapshots.values())
        
        return {
            **self._stats,
            "total_size_bytes": total_size,
            "snapshots_count": len(self._snapshots),
            "tags_count": len(self._tags_index),
            "last_snapshot_time": self._last_snapshot_time,
            "actions_since_snapshot": self._actions_since_snapshot,
        }
    
    def action_occurred(self) -> None:
        """Notify manager that an action occurred (for auto-snapshot logic)."""
        self._actions_since_snapshot += 1
    
    # Private methods
    
    def _determine_snapshot_type(self, state: Dict[str, Any]) -> SnapshotType:
        """Determine the appropriate snapshot type."""
        # Check if we should create an incremental snapshot
        if (self._actions_since_snapshot >= self.strategy.incremental_threshold and
            self._snapshot_index):
            return SnapshotType.INCREMENTAL
        else:
            return SnapshotType.FULL
    
    def _create_incremental_snapshot(self, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """Create incremental snapshot data."""
        if not self._snapshot_index:
            # No previous snapshot - create full snapshot
            return current_state
        
        # Get the latest snapshot
        latest_id = self._snapshot_index[-1]
        base_state = self.restore_snapshot(latest_id)
        
        if base_state is None:
            # Failed to restore base - create full snapshot
            return current_state
        
        # Calculate delta
        return self._calculate_delta(base_state, current_state)
    
    def _calculate_delta(
        self,
        old_state: Dict[str, Any],
        new_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate delta between two states."""
        delta = {
            "type": "delta",
            "changes": {},
            "additions": {},
            "deletions": set(),
        }
        
        # Find changes and additions
        for key, value in new_state.items():
            if key not in old_state:
                delta["additions"][key] = value
            elif old_state[key] != value:
                delta["changes"][key] = {
                    "old": old_state[key],
                    "new": value
                }
        
        # Find deletions
        for key in old_state:
            if key not in new_state:
                delta["deletions"].add(key)
        
        # Convert set to list for serialization
        delta["deletions"] = list(delta["deletions"])
        
        return delta
    
    def _restore_incremental_snapshot(
        self,
        snapshot: Snapshot,
        delta_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Restore state from an incremental snapshot."""
        if not snapshot.parent_snapshot_id:
            logger.error("Incremental snapshot has no parent")
            return None
        
        # Restore base state
        base_state = self.restore_snapshot(snapshot.parent_snapshot_id)
        if base_state is None:
            return None
        
        # Apply delta
        result_state = copy.deepcopy(base_state)
        
        # Apply changes
        for key, change in delta_data.get("changes", {}).items():
            result_state[key] = change["new"]
        
        # Apply additions
        for key, value in delta_data.get("additions", {}).items():
            result_state[key] = value
        
        # Apply deletions
        for key in delta_data.get("deletions", []):
            result_state.pop(key, None)
        
        return result_state
    
    def _compress_data(
        self,
        data: Dict[str, Any]
    ) -> tuple[Union[Dict[str, Any], bytes], CompressionAlgorithm]:
        """Compress snapshot data."""
        if not self.compression_enabled:
            return data, CompressionAlgorithm.NONE
        
        algorithm = self.strategy.compression_algorithm
        
        try:
            if algorithm == CompressionAlgorithm.GZIP:
                # Use pickle + gzip
                pickled = pickle.dumps(data)
                compressed = gzip.compress(pickled)
                return compressed, algorithm
            
            elif algorithm == CompressionAlgorithm.JSON_GZIP:
                # Use JSON + gzip
                json_str = json.dumps(data, ensure_ascii=False)
                compressed = gzip.compress(json_str.encode('utf-8'))
                return compressed, algorithm
            
            elif algorithm == CompressionAlgorithm.PICKLE:
                # Just pickle
                pickled = pickle.dumps(data)
                return pickled, algorithm
            
            else:
                return data, CompressionAlgorithm.NONE
                
        except Exception as e:
            logger.warning(f"Compression failed: {e}")
            return data, CompressionAlgorithm.NONE
    
    def _decompress_data(
        self,
        data: Union[Dict[str, Any], bytes],
        algorithm: CompressionAlgorithm
    ) -> Dict[str, Any]:
        """Decompress snapshot data."""
        if algorithm == CompressionAlgorithm.NONE:
            return data
        
        if not isinstance(data, bytes):
            logger.warning("Expected bytes for compressed data")
            return data
        
        try:
            if algorithm == CompressionAlgorithm.GZIP:
                decompressed = gzip.decompress(data)
                return pickle.loads(decompressed)
            
            elif algorithm == CompressionAlgorithm.JSON_GZIP:
                decompressed = gzip.decompress(data)
                json_str = decompressed.decode('utf-8')
                return json.loads(json_str)
            
            elif algorithm == CompressionAlgorithm.PICKLE:
                return pickle.loads(data)
            
            else:
                logger.warning(f"Unknown compression algorithm: {algorithm}")
                return {}
                
        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            raise
    
    def _add_auto_tags(self, snapshot: Snapshot, state: Dict[str, Any]) -> None:
        """Add automatic tags to a snapshot."""
        # Add timestamp-based tags
        dt = datetime.fromtimestamp(snapshot.timestamp)
        snapshot.add_tag(f"year_{dt.year}")
        snapshot.add_tag(f"month_{dt.year}_{dt.month:02d}")
        snapshot.add_tag(f"day_{dt.year}_{dt.month:02d}_{dt.day:02d}")
        
        # Add type tag
        snapshot.add_tag(f"type_{snapshot.snapshot_type.value}")
        
        # Add size-based tags
        if snapshot.size_bytes < 1024:
            snapshot.add_tag("size_small")
        elif snapshot.size_bytes < 1024 * 1024:
            snapshot.add_tag("size_medium")
        else:
            snapshot.add_tag("size_large")
        
        # Add state-based tags (example)
        if isinstance(state, dict):
            if "document" in state:
                snapshot.add_tag("has_document")
            if "elements" in state and state["elements"]:
                snapshot.add_tag("has_elements")
                element_count = len(state["elements"])
                if element_count > 100:
                    snapshot.add_tag("many_elements")
    
    def _get_latest_snapshot_id(self) -> Optional[str]:
        """Get the ID of the latest snapshot."""
        return self._snapshot_index[-1] if self._snapshot_index else None
    
    def _find_dependent_snapshots(self, snapshot_id: str) -> List[str]:
        """Find snapshots that depend on the given snapshot."""
        dependents = []
        for sid, snapshot in self._snapshots.items():
            if snapshot.parent_snapshot_id == snapshot_id:
                dependents.append(sid)
        return dependents
    
    def _update_stats(self, snapshot: Snapshot, creation_time: float) -> None:
        """Update manager statistics."""
        self._stats["total_snapshots"] += 1
        
        if snapshot.snapshot_type == SnapshotType.FULL:
            self._stats["full_snapshots"] += 1
        else:
            self._stats["incremental_snapshots"] += 1
        
        # Update average creation time
        total_time = (self._stats["average_snapshot_time"] * 
                     (self._stats["total_snapshots"] - 1) + creation_time)
        self._stats["average_snapshot_time"] = total_time / self._stats["total_snapshots"]
    
    def _prune_old_snapshots(self) -> None:
        """Remove old snapshots to stay within limits."""
        while len(self._snapshots) > self.strategy.max_snapshots:
            # Remove oldest snapshot that has no dependents
            for snapshot_id in self._snapshot_index:
                if not self._find_dependent_snapshots(snapshot_id):
                    self.delete_snapshot(snapshot_id)
                    break
            else:
                # All snapshots have dependents - remove oldest anyway
                oldest_id = self._snapshot_index[0]
                logger.warning(f"Force removing snapshot with dependents: {oldest_id}")
                self.delete_snapshot(oldest_id)
    
    async def _auto_snapshot_worker(self) -> None:
        """Background worker for automatic snapshots."""
        try:
            while True:
                await asyncio.sleep(self.strategy.snapshot_interval)
                
                # Check if we need to create a snapshot
                time_since_last = time.time() - self._last_snapshot_time
                if (time_since_last >= self.strategy.snapshot_interval or
                    self._actions_since_snapshot >= self.strategy.incremental_threshold):
                    
                    # Would need current state from store to create auto snapshot
                    # This would be provided by the store integration
                    logger.debug("Auto snapshot interval reached")
                    
        except asyncio.CancelledError:
            pass
    
    async def _cleanup_worker(self) -> None:
        """Background worker for cleanup tasks."""
        try:
            while True:
                await asyncio.sleep(3600)  # Run every hour
                
                # Clean up expired snapshots
                if self.strategy.retention_days:
                    cutoff_time = time.time() - (self.strategy.retention_days * 24 * 3600)
                    
                    expired = [
                        sid for sid in self._snapshot_index
                        if self._snapshots[sid].timestamp < cutoff_time
                    ]
                    
                    for snapshot_id in expired:
                        if not self._find_dependent_snapshots(snapshot_id):
                            self.delete_snapshot(snapshot_id)
                            logger.debug(f"Cleaned up expired snapshot: {snapshot_id}")
                    
        except asyncio.CancelledError:
            pass