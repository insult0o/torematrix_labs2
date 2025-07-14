"""
Tests for state snapshot functionality.

Comprehensive tests for snapshot creation, compression, restoration, and management.
"""

import pytest
import time
import asyncio
from unittest.mock import MagicMock, patch
import json
import gzip

from src.torematrix.core.state.snapshots import (
    Snapshot, SnapshotManager, SnapshotStrategy, SnapshotType, 
    CompressionAlgorithm
)


class TestSnapshot:
    """Test Snapshot functionality."""
    
    def test_snapshot_creation(self):
        """Test creating a snapshot."""
        state_data = {"test": "data", "counter": 42}
        snapshot = Snapshot(
            id="test_snapshot",
            timestamp=time.time(),
            state=state_data,
            snapshot_type=SnapshotType.FULL
        )
        
        assert snapshot.id == "test_snapshot"
        assert snapshot.state == state_data
        assert snapshot.snapshot_type == SnapshotType.FULL
        assert snapshot.size_bytes > 0
        assert snapshot.checksum != ""
        assert "created_at" in snapshot.metadata
    
    def test_snapshot_with_metadata(self):
        """Test snapshot with custom metadata."""
        metadata = {"author": "test_user", "purpose": "testing"}
        snapshot = Snapshot(
            id="meta_test",
            timestamp=time.time(),
            state={"data": "test"},
            metadata=metadata
        )
        
        assert snapshot.metadata["author"] == "test_user"
        assert snapshot.metadata["purpose"] == "testing"
        assert "created_at" in snapshot.metadata
        assert "size_bytes" in snapshot.metadata
    
    def test_snapshot_tags(self):
        """Test snapshot tagging functionality."""
        snapshot = Snapshot(
            id="tag_test",
            timestamp=time.time(),
            state={"test": True}
        )
        
        # Add tags
        snapshot.add_tag("important")
        snapshot.add_tag("backup")
        
        assert snapshot.has_tag("important")
        assert snapshot.has_tag("backup")
        assert not snapshot.has_tag("nonexistent")
        
        # Remove tag
        snapshot.remove_tag("backup")
        assert not snapshot.has_tag("backup")
        assert snapshot.has_tag("important")
    
    def test_snapshot_integrity_verification(self):
        """Test snapshot integrity verification."""
        snapshot = Snapshot(
            id="integrity_test",
            timestamp=time.time(),
            state={"data": "original"}
        )
        
        # Should verify correctly
        assert snapshot.verify_integrity() is True
        
        # Modify state and verify it fails
        snapshot.state["data"] = "modified"
        assert snapshot.verify_integrity() is False
    
    def test_snapshot_serialization(self):
        """Test snapshot to/from dict conversion."""
        original_snapshot = Snapshot(
            id="serial_test",
            timestamp=time.time(),
            state={"test": "serialization"},
            snapshot_type=SnapshotType.INCREMENTAL,
            tags={"tag1", "tag2"}
        )
        
        # Convert to dict
        snapshot_dict = original_snapshot.to_dict()
        assert snapshot_dict["id"] == "serial_test"
        assert snapshot_dict["state"]["test"] == "serialization"
        assert snapshot_dict["snapshot_type"] == "incremental"
        assert set(snapshot_dict["tags"]) == {"tag1", "tag2"}
        
        # Convert back from dict
        restored_snapshot = Snapshot.from_dict(snapshot_dict)
        assert restored_snapshot.id == original_snapshot.id
        assert restored_snapshot.state == original_snapshot.state
        assert restored_snapshot.snapshot_type == original_snapshot.snapshot_type
        assert restored_snapshot.tags == original_snapshot.tags


class TestSnapshotStrategy:
    """Test SnapshotStrategy configuration."""
    
    def test_default_strategy(self):
        """Test default strategy configuration."""
        strategy = SnapshotStrategy()
        
        assert strategy.auto_snapshot is True
        assert strategy.snapshot_interval == 300.0
        assert strategy.max_snapshots == 100
        assert strategy.compression_enabled is True
        assert strategy.compression_algorithm == CompressionAlgorithm.JSON_GZIP
        assert strategy.incremental_threshold == 10
    
    def test_custom_strategy(self):
        """Test custom strategy configuration."""
        strategy = SnapshotStrategy(
            auto_snapshot=False,
            snapshot_interval=600.0,
            max_snapshots=50,
            compression_enabled=False
        )
        
        assert strategy.auto_snapshot is False
        assert strategy.snapshot_interval == 600.0
        assert strategy.max_snapshots == 50
        assert strategy.compression_enabled is False


class TestSnapshotManager:
    """Test SnapshotManager functionality."""
    
    @pytest.fixture
    def strategy(self):
        """Create test strategy."""
        return SnapshotStrategy(
            auto_snapshot=False,  # Disable for testing
            max_snapshots=10,
            compression_enabled=True
        )
    
    @pytest.fixture
    def manager(self, strategy):
        """Create snapshot manager."""
        return SnapshotManager(strategy=strategy)
    
    def test_manager_initialization(self, manager):
        """Test manager initialization."""
        assert len(manager._snapshots) == 0
        assert len(manager._snapshot_index) == 0
        assert len(manager._tags_index) == 0
        assert manager._actions_since_snapshot == 0
    
    def test_create_full_snapshot(self, manager):
        """Test creating a full snapshot."""
        test_state = {
            "document": {"id": "doc1", "title": "Test Document"},
            "elements": [{"id": "elem1", "content": "Test content"}],
            "ui": {"page": 1}
        }
        
        snapshot_id = manager.create_snapshot(
            state=test_state,
            metadata={"test": True},
            tags={"important", "backup"}
        )
        
        assert snapshot_id in manager._snapshots
        snapshot = manager._snapshots[snapshot_id]
        
        assert snapshot.snapshot_type == SnapshotType.FULL
        assert snapshot.has_tag("important")
        assert snapshot.has_tag("backup")
        assert snapshot.metadata["test"] is True
        
        # Check indexes updated
        assert snapshot_id in manager._snapshot_index
        assert "important" in manager._tags_index
        assert snapshot_id in manager._tags_index["important"]
    
    def test_restore_snapshot(self, manager):
        """Test restoring a snapshot."""
        test_state = {
            "data": "test_restore",
            "numbers": [1, 2, 3, 4, 5]
        }
        
        # Create snapshot
        snapshot_id = manager.create_snapshot(test_state)
        
        # Restore snapshot
        restored_state = manager.restore_snapshot(snapshot_id)
        
        assert restored_state == test_state
        assert restored_state is not test_state  # Should be a copy
    
    def test_restore_nonexistent_snapshot(self, manager):
        """Test restoring non-existent snapshot."""
        restored_state = manager.restore_snapshot("nonexistent")
        assert restored_state is None
    
    def test_create_incremental_snapshot(self, manager):
        """Test creating incremental snapshots."""
        # Create base snapshot
        base_state = {"counter": 0, "items": ["a", "b"]}
        base_id = manager.create_snapshot(base_state)
        
        # Simulate some actions
        for _ in range(15):  # Exceed incremental threshold
            manager.action_occurred()
        
        # Create incremental snapshot
        new_state = {"counter": 5, "items": ["a", "b", "c", "d"]}
        incremental_id = manager.create_snapshot(new_state)
        
        incremental_snapshot = manager._snapshots[incremental_id]
        assert incremental_snapshot.snapshot_type == SnapshotType.INCREMENTAL
        assert incremental_snapshot.parent_snapshot_id == base_id
    
    def test_create_incremental_from_base(self, manager):
        """Test creating incremental snapshot from specific base."""
        # Create base snapshot
        base_state = {"version": 1, "data": {"a": 1, "b": 2}}
        base_id = manager.create_snapshot(base_state)
        
        # Create incremental from base
        current_state = {"version": 1, "data": {"a": 1, "b": 3, "c": 4}}
        incremental_id = manager.create_incremental(
            base_id, 
            current_state,
            metadata={"type": "incremental_test"}
        )
        
        assert incremental_id is not None
        incremental_snapshot = manager._snapshots[incremental_id]
        assert incremental_snapshot.snapshot_type == SnapshotType.INCREMENTAL
        assert incremental_snapshot.parent_snapshot_id == base_id
    
    def test_list_snapshots(self, manager):
        """Test listing snapshots with filtering."""
        # Create snapshots with different tags
        snapshot1 = manager.create_snapshot(
            {"data": "snapshot1"}, 
            tags={"important", "backup"}
        )
        snapshot2 = manager.create_snapshot(
            {"data": "snapshot2"}, 
            tags={"test", "backup"}
        )
        snapshot3 = manager.create_snapshot(
            {"data": "snapshot3"}, 
            tags={"important", "daily"}
        )
        
        # List all snapshots
        all_snapshots = manager.list_snapshots()
        assert len(all_snapshots) == 3
        assert all(sid in [snapshot1, snapshot2, snapshot3] for sid in all_snapshots)
        
        # Filter by tags
        important_snapshots = manager.list_snapshots(tags={"important"})
        assert len(important_snapshots) == 2
        assert snapshot1 in important_snapshots
        assert snapshot3 in important_snapshots
        
        # Filter by multiple tags (AND operation)
        backup_important = manager.list_snapshots(tags={"important", "backup"})
        assert len(backup_important) == 1
        assert snapshot1 in backup_important
        
        # Filter by snapshot type
        full_snapshots = manager.list_snapshots(snapshot_type=SnapshotType.FULL)
        assert len(full_snapshots) == 3  # All are full snapshots
        
        # Test limit
        limited_snapshots = manager.list_snapshots(limit=2)
        assert len(limited_snapshots) == 2
    
    def test_delete_snapshot(self, manager):
        """Test deleting snapshots."""
        # Create snapshot
        snapshot_id = manager.create_snapshot({"test": "delete_me"})
        assert snapshot_id in manager._snapshots
        
        # Delete snapshot
        deleted = manager.delete_snapshot(snapshot_id)
        assert deleted is True
        assert snapshot_id not in manager._snapshots
        assert snapshot_id not in manager._snapshot_index
        
        # Try to delete non-existent snapshot
        deleted = manager.delete_snapshot("nonexistent")
        assert deleted is False
    
    def test_delete_snapshot_with_dependents(self, manager):
        """Test deleting snapshot that has dependents."""
        # Create base snapshot
        base_state = {"base": True}
        base_id = manager.create_snapshot(base_state)
        
        # Create incremental snapshot depending on base
        incremental_state = {"base": True, "incremental": True}
        incremental_id = manager.create_incremental(base_id, incremental_state)
        
        # Try to delete base snapshot - should fail
        deleted = manager.delete_snapshot(base_id)
        assert deleted is False
        assert base_id in manager._snapshots
        
        # Delete incremental first
        deleted = manager.delete_snapshot(incremental_id)
        assert deleted is True
        
        # Now can delete base
        deleted = manager.delete_snapshot(base_id)
        assert deleted is True
    
    def test_snapshot_pruning(self, manager):
        """Test automatic snapshot pruning."""
        # Create more snapshots than the limit
        for i in range(15):  # Limit is 10
            manager.create_snapshot({"iteration": i})
        
        # Should have pruned to the limit
        assert len(manager._snapshots) <= manager.strategy.max_snapshots
        
        # Should keep the most recent snapshots
        snapshots = manager.list_snapshots()
        for snapshot_id in snapshots:
            snapshot = manager._snapshots[snapshot_id]
            restored_state = manager.restore_snapshot(snapshot_id)
            # Should have kept later iterations
            assert restored_state["iteration"] >= 5
    
    def test_auto_tagging(self, manager):
        """Test automatic tagging functionality."""
        # Create snapshot with elements
        state_with_elements = {
            "document": {"id": "doc1"},
            "elements": [{"id": "elem1"}, {"id": "elem2"}]
        }
        
        snapshot_id = manager.create_snapshot(state_with_elements)
        snapshot = manager._snapshots[snapshot_id]
        
        # Check automatic tags were added
        assert any(tag.startswith("year_") for tag in snapshot.tags)
        assert any(tag.startswith("type_") for tag in snapshot.tags)
        assert snapshot.has_tag("has_document")
        assert snapshot.has_tag("has_elements")
    
    def test_compression_functionality(self, manager):
        """Test snapshot compression."""
        # Create large state to trigger compression
        large_state = {
            "large_data": ["item " * 100 for _ in range(100)],
            "metadata": {"compressed": True}
        }
        
        snapshot_id = manager.create_snapshot(large_state)
        snapshot = manager._snapshots[snapshot_id]
        
        # Verify snapshot was compressed (if enabled)
        if manager.strategy.compression_enabled:
            assert snapshot.compressed is True
            assert isinstance(snapshot.state, bytes)
        
        # Verify we can restore it correctly
        restored_state = manager.restore_snapshot(snapshot_id)
        assert restored_state == large_state
    
    def test_get_snapshot_info(self, manager):
        """Test getting snapshot information."""
        snapshot_id = manager.create_snapshot(
            {"info_test": True},
            metadata={"test_info": "value"},
            tags={"info", "test"}
        )
        
        info = manager.get_snapshot_info(snapshot_id)
        
        assert info is not None
        assert info["id"] == snapshot_id
        assert info["snapshot_type"] == "full"
        assert info["compressed"] in [True, False]
        assert "info" in info["tags"]
        assert "test" in info["tags"]
        assert info["metadata"]["test_info"] == "value"
        
        # Test non-existent snapshot
        info = manager.get_snapshot_info("nonexistent")
        assert info is None
    
    def test_manager_stats(self, manager):
        """Test getting manager statistics."""
        # Create some snapshots
        for i in range(3):
            manager.create_snapshot({"stats_test": i})
            manager.action_occurred()
        
        stats = manager.get_manager_stats()
        
        assert stats["snapshots_count"] == 3
        assert stats["total_size_bytes"] > 0
        assert stats["actions_since_snapshot"] > 0
        assert "total_snapshots" in stats
    
    @pytest.mark.asyncio
    async def test_start_stop_manager(self, manager):
        """Test starting and stopping the manager."""
        # Start manager
        await manager.start()
        
        # Should have background tasks running
        assert manager._cleanup_task is not None
        # auto_snapshot_task is None because auto_snapshot is disabled
        
        # Stop manager
        await manager.stop()
        
        # Tasks should be cancelled
        assert manager._cleanup_task.cancelled()


class TestSnapshotPerformance:
    """Performance tests for snapshot functionality."""
    
    @pytest.fixture
    def large_state(self):
        """Generate large state for performance testing."""
        return {
            "document": {
                "id": "perf_test_doc",
                "metadata": {"pages": 1000, "size": "huge"}
            },
            "elements": [
                {
                    "id": f"elem_{i}",
                    "type": "text" if i % 3 == 0 else "table" if i % 3 == 1 else "image",
                    "content": f"Performance test element {i} " * 20,
                    "metadata": {
                        "page": i // 100,
                        "position": {"x": i * 5, "y": i * 10},
                        "properties": {"font_size": 12, "color": "black"}
                    }
                }
                for i in range(5000)  # 5000 elements
            ],
            "ui": {
                "current_page": 500,
                "zoom": 1.5,
                "selections": list(range(500)),
                "history": [{"action": f"action_{j}"} for j in range(1000)]
            }
        }
    
    def test_large_snapshot_creation_performance(self, large_state):
        """Test performance of creating large snapshots."""
        strategy = SnapshotStrategy(
            compression_enabled=True,
            compression_algorithm=CompressionAlgorithm.JSON_GZIP
        )
        manager = SnapshotManager(strategy=strategy)
        
        # Measure creation time
        start_time = time.time()
        snapshot_id = manager.create_snapshot(large_state)
        creation_time = time.time() - start_time
        
        print(f"Large snapshot creation time: {creation_time:.3f}s")
        
        # Should complete in reasonable time
        assert creation_time < 2.0, f"Snapshot creation too slow: {creation_time}s"
        
        # Verify snapshot was created
        assert snapshot_id in manager._snapshots
        snapshot = manager._snapshots[snapshot_id]
        assert len(snapshot.state) > 0  # Compressed or uncompressed
    
    def test_large_snapshot_restoration_performance(self, large_state):
        """Test performance of restoring large snapshots."""
        strategy = SnapshotStrategy(compression_enabled=True)
        manager = SnapshotManager(strategy=strategy)
        
        # Create snapshot
        snapshot_id = manager.create_snapshot(large_state)
        
        # Measure restoration time
        start_time = time.time()
        restored_state = manager.restore_snapshot(snapshot_id)
        restoration_time = time.time() - start_time
        
        print(f"Large snapshot restoration time: {restoration_time:.3f}s")
        
        # Should complete in reasonable time
        assert restoration_time < 1.0, f"Snapshot restoration too slow: {restoration_time}s"
        
        # Verify data integrity
        assert len(restored_state["elements"]) == len(large_state["elements"])
        assert restored_state["document"]["id"] == large_state["document"]["id"]
    
    def test_compression_ratio_performance(self, large_state):
        """Test compression ratio and performance."""
        # Test with compression
        strategy_compressed = SnapshotStrategy(
            compression_enabled=True,
            compression_algorithm=CompressionAlgorithm.JSON_GZIP
        )
        manager_compressed = SnapshotManager(strategy=strategy_compressed)
        
        # Test without compression
        strategy_uncompressed = SnapshotStrategy(compression_enabled=False)
        manager_uncompressed = SnapshotManager(strategy=strategy_uncompressed)
        
        # Create snapshots
        compressed_id = manager_compressed.create_snapshot(large_state)
        uncompressed_id = manager_uncompressed.create_snapshot(large_state)
        
        compressed_snapshot = manager_compressed._snapshots[compressed_id]
        uncompressed_snapshot = manager_uncompressed._snapshots[uncompressed_id]
        
        print(f"Compressed size: {compressed_snapshot.size_bytes} bytes")
        print(f"Uncompressed size: {uncompressed_snapshot.size_bytes} bytes")
        
        # Compression should reduce size significantly for large data
        if compressed_snapshot.compressed:
            compression_ratio = compressed_snapshot.size_bytes / uncompressed_snapshot.size_bytes
            print(f"Compression ratio: {compression_ratio:.3f}")
            assert compression_ratio < 0.5, "Compression not effective enough"
    
    def test_multiple_snapshots_memory_usage(self):
        """Test memory usage with multiple snapshots."""
        strategy = SnapshotStrategy(
            max_snapshots=50,
            compression_enabled=True
        )
        manager = SnapshotManager(strategy=strategy)
        
        # Create multiple snapshots with varying sizes
        for i in range(20):
            state = {
                "iteration": i,
                "data": [f"item_{j}" for j in range(i * 100)],  # Increasing size
                "metadata": {"size": i * 100}
            }
            manager.create_snapshot(state)
        
        # Check manager stats
        stats = manager.get_manager_stats()
        print(f"Total snapshots: {stats['snapshots_count']}")
        print(f"Total size: {stats['total_size_bytes']} bytes")
        
        # Should stay within reasonable limits
        assert stats["snapshots_count"] <= strategy.max_snapshots
        assert stats["total_size_bytes"] < 100 * 1024 * 1024  # Less than 100MB
    
    def test_incremental_snapshot_efficiency(self):
        """Test efficiency of incremental snapshots."""
        manager = SnapshotManager()
        
        # Create base snapshot
        base_state = {
            "large_array": list(range(10000)),
            "metadata": {"version": 1}
        }
        base_id = manager.create_snapshot(base_state)
        base_snapshot = manager._snapshots[base_id]
        
        # Create incremental snapshot with small change
        incremental_state = base_state.copy()
        incremental_state["metadata"]["version"] = 2
        incremental_state["small_change"] = "added"
        
        incremental_id = manager.create_incremental(base_id, incremental_state)
        incremental_snapshot = manager._snapshots[incremental_id]
        
        print(f"Base snapshot size: {base_snapshot.size_bytes} bytes")
        print(f"Incremental snapshot size: {incremental_snapshot.size_bytes} bytes")
        
        # Incremental should be much smaller than base
        ratio = incremental_snapshot.size_bytes / base_snapshot.size_bytes
        print(f"Incremental/Base ratio: {ratio:.3f}")
        assert ratio < 0.1, "Incremental snapshot not efficient enough"
        
        # Verify restoration works correctly
        restored_state = manager.restore_snapshot(incremental_id)
        assert restored_state == incremental_state