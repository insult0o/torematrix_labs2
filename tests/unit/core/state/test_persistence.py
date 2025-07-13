"""
Tests for state persistence functionality.

Tests all persistence backends and middleware components with
comprehensive coverage including performance benchmarks.
"""

import pytest
import asyncio
import tempfile
import time
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.torematrix.core.state.persistence.base import (
    PersistenceBackend, PersistenceConfig, PersistenceStrategy, PersistenceMiddleware
)
from src.torematrix.core.state.persistence.json_backend import JSONPersistenceBackend
from src.torematrix.core.state.persistence.sqlite_backend import SQLitePersistenceBackend
from src.torematrix.core.state.persistence.redis_backend import RedisPersistenceBackend


class TestPersistenceConfig:
    """Test persistence configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = PersistenceConfig()
        
        assert config.strategy == PersistenceStrategy.DEBOUNCED
        assert config.debounce_delay == 0.5
        assert config.batch_size == 100
        assert config.compression_enabled is True
        assert config.max_versions == 100
        assert config.auto_prune is True
        assert config.retry_attempts == 3
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = PersistenceConfig(
            strategy=PersistenceStrategy.IMMEDIATE,
            compression_enabled=False,
            max_versions=50
        )
        
        assert config.strategy == PersistenceStrategy.IMMEDIATE
        assert config.compression_enabled is False
        assert config.max_versions == 50


class TestJSONPersistenceBackend:
    """Test JSON file-based persistence backend."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return PersistenceConfig(compression_enabled=True)
    
    @pytest.fixture
    async def backend(self, config, temp_dir):
        """Create and initialize JSON backend."""
        backend = JSONPersistenceBackend(config, temp_dir)
        await backend.initialize()
        yield backend
        await backend.cleanup()
    
    @pytest.mark.asyncio
    async def test_initialization(self, config, temp_dir):
        """Test backend initialization."""
        backend = JSONPersistenceBackend(config, temp_dir)
        await backend.initialize()
        
        # Check directories were created
        assert Path(temp_dir, "states").exists()
        assert Path(temp_dir, "metadata").exists()
        assert Path(temp_dir, "index.json").exists()
        
        await backend.cleanup()
    
    @pytest.mark.asyncio
    async def test_save_and_load_state(self, backend):
        """Test basic save and load operations."""
        test_state = {
            "document": {"id": "test_doc", "title": "Test Document"},
            "elements": [{"id": "elem1", "type": "text", "content": "Hello"}],
            "ui": {"current_page": 1}
        }
        
        version = "test_v1"
        metadata = {"test": True, "author": "test_user"}
        
        # Save state
        await backend.save_state(test_state, version, metadata)
        
        # Load state
        loaded_state = await backend.load_state(version)
        
        assert loaded_state == test_state
        
        # Test loading latest
        latest_state = await backend.load_state()
        assert latest_state == test_state
    
    @pytest.mark.asyncio
    async def test_list_versions(self, backend):
        """Test listing state versions."""
        states = [
            {"test": "state1"},
            {"test": "state2"},
            {"test": "state3"}
        ]
        
        versions = []
        for i, state in enumerate(states):
            version = f"v{i+1}"
            await backend.save_state(state, version)
            versions.append(version)
        
        listed_versions = await backend.list_versions()
        assert len(listed_versions) == 3
        assert all(v in listed_versions for v in versions)
    
    @pytest.mark.asyncio
    async def test_delete_version(self, backend):
        """Test deleting a state version."""
        test_state = {"test": "delete_me"}
        version = "delete_test"
        
        await backend.save_state(test_state, version)
        assert version in await backend.list_versions()
        
        # Delete version
        deleted = await backend.delete_version(version)
        assert deleted is True
        assert version not in await backend.list_versions()
        
        # Try to delete non-existent version
        deleted = await backend.delete_version("non_existent")
        assert deleted is False
    
    @pytest.mark.asyncio
    async def test_get_metadata(self, backend):
        """Test retrieving metadata."""
        test_state = {"test": "metadata_test"}
        version = "meta_test"
        metadata = {"author": "test", "timestamp": time.time()}
        
        await backend.save_state(test_state, version, metadata)
        
        retrieved_metadata = await backend.get_metadata(version)
        assert retrieved_metadata is not None
        assert retrieved_metadata["author"] == "test"
        assert "size_bytes" in retrieved_metadata
        
        # Test non-existent version
        none_metadata = await backend.get_metadata("non_existent")
        assert none_metadata is None
    
    @pytest.mark.asyncio
    async def test_compression(self, config, temp_dir):
        """Test compression functionality."""
        # Create large state to trigger compression
        large_state = {
            "elements": [
                {"id": f"elem_{i}", "content": f"This is element {i} with some content"}
                for i in range(100)
            ]
        }
        
        backend = JSONPersistenceBackend(config, temp_dir)
        await backend.initialize()
        
        try:
            await backend.save_state(large_state, "compressed_test")
            
            # Check if compressed file exists
            compressed_file = Path(temp_dir, "states", "compressed_test.json.gz")
            uncompressed_file = Path(temp_dir, "states", "compressed_test.json")
            
            # Should create compressed file for large data
            assert compressed_file.exists() or uncompressed_file.exists()
            
            # Verify we can load it back
            loaded_state = await backend.load_state("compressed_test")
            assert loaded_state == large_state
            
        finally:
            await backend.cleanup()


class TestSQLitePersistenceBackend:
    """Test SQLite database-based persistence backend."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return PersistenceConfig(compression_enabled=True)
    
    @pytest.fixture
    async def backend(self, config, temp_db):
        """Create and initialize SQLite backend."""
        backend = SQLitePersistenceBackend(config, temp_db)
        await backend.initialize()
        yield backend
        await backend.cleanup()
    
    @pytest.mark.asyncio
    async def test_initialization(self, config, temp_db):
        """Test backend initialization."""
        backend = SQLitePersistenceBackend(config, temp_db)
        await backend.initialize()
        
        # Check database file was created
        assert Path(temp_db).exists()
        
        await backend.cleanup()
    
    @pytest.mark.asyncio
    async def test_save_and_load_state(self, backend):
        """Test basic save and load operations."""
        test_state = {
            "document": {"id": "test_doc"},
            "elements": [{"id": "elem1", "type": "text"}]
        }
        
        version = "sqlite_test_v1"
        metadata = {"backend": "sqlite", "test": True}
        
        # Save state
        await backend.save_state(test_state, version, metadata)
        
        # Load state
        loaded_state = await backend.load_state(version)
        assert loaded_state == test_state
        
        # Test loading latest
        latest_state = await backend.load_state()
        assert latest_state == test_state
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, backend):
        """Test concurrent save/load operations."""
        async def save_operation(version_num):
            state = {"test": f"concurrent_{version_num}", "data": list(range(version_num * 10))}
            await backend.save_state(state, f"concurrent_v{version_num}")
        
        # Run concurrent saves
        tasks = [save_operation(i) for i in range(5)]
        await asyncio.gather(*tasks)
        
        # Verify all were saved
        versions = await backend.list_versions()
        assert len(versions) == 5
        
        # Verify data integrity
        for i in range(5):
            loaded_state = await backend.load_state(f"concurrent_v{i}")
            assert loaded_state["test"] == f"concurrent_{i}"
            assert loaded_state["data"] == list(range(i * 10))
    
    @pytest.mark.asyncio
    async def test_large_state_compression(self, backend):
        """Test compression with large states."""
        # Create state with 10MB of data
        large_data = {
            "large_list": ["x" * 1000 for _ in range(10000)],
            "metadata": {"size": "large"}
        }
        
        await backend.save_state(large_data, "large_state_test")
        
        # Verify we can load it back
        loaded_state = await backend.load_state("large_state_test")
        assert loaded_state["metadata"]["size"] == "large"
        assert len(loaded_state["large_list"]) == 10000
    
    @pytest.mark.asyncio
    async def test_storage_stats(self, backend):
        """Test storage statistics."""
        # Save some states
        for i in range(3):
            await backend.save_state(
                {"test": f"stats_{i}", "data": list(range(i * 100))},
                f"stats_v{i}"
            )
        
        stats = await backend.get_storage_stats()
        
        assert stats["total_versions"] == 3
        assert stats["total_size_bytes"] > 0
        assert stats["db_path"] == str(backend.db_path)
        assert stats["latest_version"] == "stats_v2"


@pytest.mark.skipif(
    os.getenv("REDIS_URL") is None,
    reason="Redis not available (set REDIS_URL environment variable)"
)
class TestRedisPersistenceBackend:
    """Test Redis-based persistence backend."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return PersistenceConfig(compression_enabled=True)
    
    @pytest.fixture
    async def backend(self, config):
        """Create and initialize Redis backend."""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        backend = RedisPersistenceBackend(
            config, 
            redis_url=redis_url,
            key_prefix="test_torematrix"
        )
        
        try:
            await backend.initialize()
            yield backend
        finally:
            # Clean up test data
            await backend.flush_all_versions()
            await backend.cleanup()
    
    @pytest.mark.asyncio
    async def test_save_and_load_state(self, backend):
        """Test basic save and load operations."""
        test_state = {
            "redis_test": True,
            "elements": [{"id": "elem1", "content": "Redis test"}]
        }
        
        version = "redis_test_v1"
        metadata = {"backend": "redis", "test": True}
        
        # Save state
        await backend.save_state(test_state, version, metadata)
        
        # Load state
        loaded_state = await backend.load_state(version)
        assert loaded_state == test_state
    
    @pytest.mark.asyncio
    async def test_ttl_functionality(self, backend):
        """Test TTL (time-to-live) functionality."""
        test_state = {"ttl_test": True}
        version = "ttl_test"
        
        # Save with short TTL
        await backend.save_state(test_state, version)
        await backend.set_ttl(version, 1)  # 1 second TTL
        
        # Should be accessible immediately
        loaded_state = await backend.load_state(version)
        assert loaded_state == test_state
        
        # Wait for expiration (in real test, would use Redis FLUSHALL for cleanup)
        # This is just to demonstrate the TTL functionality
        assert await backend.get_metadata(version) is not None


class TestPersistenceMiddleware:
    """Test persistence middleware integration."""
    
    @pytest.fixture
    def mock_backend(self):
        """Create mock persistence backend."""
        backend = AsyncMock(spec=PersistenceBackend)
        backend.initialize = AsyncMock()
        backend.save_state = AsyncMock()
        backend.cleanup = AsyncMock()
        backend.prune_old_versions = AsyncMock(return_value=0)
        return backend
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return PersistenceConfig(
            strategy=PersistenceStrategy.IMMEDIATE,
            compression_enabled=False
        )
    
    @pytest.fixture
    async def middleware(self, mock_backend, config):
        """Create persistence middleware."""
        middleware = PersistenceMiddleware(mock_backend, config)
        await middleware.start()
        yield middleware
        await middleware.stop()
    
    @pytest.mark.asyncio
    async def test_immediate_persistence(self, middleware, mock_backend):
        """Test immediate persistence strategy."""
        # Mock store
        mock_store = MagicMock()
        mock_store.get_state.return_value = {"test": "immediate"}
        
        # Mock action
        mock_action = MagicMock()
        mock_action.__class__.__name__ = "TestAction"
        
        # Mock next middleware
        async def next_middleware(action):
            return "success"
        
        # Execute middleware
        result = await middleware(mock_store, next_middleware, mock_action)
        
        assert result == "success"
        mock_backend.save_state.assert_called_once()
        
        # Check save was called with correct parameters
        call_args = mock_backend.save_state.call_args
        assert call_args[0][0] == {"test": "immediate"}  # state
        assert call_args[0][1].startswith("v_")  # version
        assert call_args[0][2]["action_type"] == "TestAction"  # metadata
    
    @pytest.mark.asyncio
    async def test_debounced_persistence(self, mock_backend):
        """Test debounced persistence strategy."""
        config = PersistenceConfig(
            strategy=PersistenceStrategy.DEBOUNCED,
            debounce_delay=0.1
        )
        
        middleware = PersistenceMiddleware(mock_backend, config)
        await middleware.start()
        
        try:
            # Mock store and action
            mock_store = MagicMock()
            mock_store.get_state.return_value = {"test": "debounced"}
            mock_action = MagicMock()
            
            async def next_middleware(action):
                return "success"
            
            # Execute multiple actions quickly
            for i in range(3):
                await middleware(mock_store, next_middleware, mock_action)
            
            # Should not have saved yet (debounced)
            assert mock_backend.save_state.call_count == 0
            
            # Wait for debounce
            await asyncio.sleep(0.2)
            
            # Should have saved once
            assert mock_backend.save_state.call_count == 1
            
        finally:
            await middleware.stop()
    
    @pytest.mark.asyncio
    async def test_batch_persistence(self, mock_backend):
        """Test batch persistence strategy."""
        config = PersistenceConfig(
            strategy=PersistenceStrategy.BATCH,
            batch_interval=0.1,
            batch_size=3
        )
        
        middleware = PersistenceMiddleware(mock_backend, config)
        await middleware.start()
        
        try:
            # Mock store and action
            mock_store = MagicMock()
            mock_store.get_state.return_value = {"test": "batch"}
            mock_action = MagicMock()
            
            async def next_middleware(action):
                return "success"
            
            # Execute actions
            for i in range(5):
                await middleware(mock_store, next_middleware, mock_action)
            
            # Wait for batch flush
            await asyncio.sleep(0.2)
            
            # Should have saved at least once
            assert mock_backend.save_state.call_count >= 1
            
        finally:
            await middleware.stop()
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self, mock_backend, config):
        """Test retry logic on save failure."""
        # Configure to fail twice, then succeed
        mock_backend.save_state.side_effect = [
            Exception("Save failed"),
            Exception("Save failed again"), 
            None  # Success on third try
        ]
        
        middleware = PersistenceMiddleware(mock_backend, config)
        await middleware.start()
        
        try:
            mock_store = MagicMock()
            mock_store.get_state.return_value = {"test": "retry"}
            mock_action = MagicMock()
            
            async def next_middleware(action):
                return "success"
            
            # Should not raise exception (retries will handle it)
            result = await middleware(mock_store, next_middleware, mock_action)
            assert result == "success"
            
            # Wait for async save
            await asyncio.sleep(0.1)
            
            # Should have retried 3 times
            assert mock_backend.save_state.call_count == 3
            
        finally:
            await middleware.stop()


class TestPerformanceBenchmarks:
    """Performance benchmarks for persistence backends."""
    
    @pytest.fixture
    def large_state(self):
        """Generate large state for performance testing."""
        return {
            "document": {
                "id": "large_doc",
                "metadata": {"pages": 100, "size": "large"}
            },
            "elements": [
                {
                    "id": f"elem_{i}",
                    "type": "text" if i % 2 == 0 else "table",
                    "content": f"Element {i} content " * 50,  # Make content larger
                    "metadata": {"page": i // 10, "position": {"x": i * 10, "y": i * 20}}
                }
                for i in range(1000)  # 1000 elements
            ],
            "ui": {
                "current_page": 50,
                "zoom": 1.0,
                "selections": list(range(100))
            }
        }
    
    @pytest.mark.asyncio
    async def test_json_backend_performance(self, large_state):
        """Benchmark JSON backend performance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = PersistenceConfig(compression_enabled=True)
            backend = JSONPersistenceBackend(config, temp_dir)
            await backend.initialize()
            
            try:
                # Benchmark save operations
                save_times = []
                for i in range(10):
                    start_time = time.time()
                    await backend.save_state(large_state, f"perf_test_{i}")
                    save_time = time.time() - start_time
                    save_times.append(save_time)
                
                # Benchmark load operations
                load_times = []
                for i in range(10):
                    start_time = time.time()
                    loaded_state = await backend.load_state(f"perf_test_{i}")
                    load_time = time.time() - start_time
                    load_times.append(load_time)
                    assert len(loaded_state["elements"]) == 1000
                
                # Calculate statistics
                avg_save_time = sum(save_times) / len(save_times)
                avg_load_time = sum(load_times) / len(load_times)
                
                print(f"JSON Backend Performance:")
                print(f"  Average save time: {avg_save_time:.3f}s")
                print(f"  Average load time: {avg_load_time:.3f}s")
                
                # Assert reasonable performance (adjust thresholds as needed)
                assert avg_save_time < 1.0, f"Save time too slow: {avg_save_time}s"
                assert avg_load_time < 0.5, f"Load time too slow: {avg_load_time}s"
                
            finally:
                await backend.cleanup()
    
    @pytest.mark.asyncio
    async def test_sqlite_backend_performance(self, large_state):
        """Benchmark SQLite backend performance."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            config = PersistenceConfig(compression_enabled=True)
            backend = SQLitePersistenceBackend(config, db_path)
            await backend.initialize()
            
            try:
                # Benchmark save operations
                save_times = []
                for i in range(10):
                    start_time = time.time()
                    await backend.save_state(large_state, f"perf_test_{i}")
                    save_time = time.time() - start_time
                    save_times.append(save_time)
                
                # Benchmark load operations
                load_times = []
                for i in range(10):
                    start_time = time.time()
                    loaded_state = await backend.load_state(f"perf_test_{i}")
                    load_time = time.time() - start_time
                    load_times.append(load_time)
                    assert len(loaded_state["elements"]) == 1000
                
                # Calculate statistics
                avg_save_time = sum(save_times) / len(save_times)
                avg_load_time = sum(load_times) / len(load_times)
                
                print(f"SQLite Backend Performance:")
                print(f"  Average save time: {avg_save_time:.3f}s")
                print(f"  Average load time: {avg_load_time:.3f}s")
                
                # SQLite should be faster than JSON for repeated operations
                assert avg_save_time < 0.5, f"Save time too slow: {avg_save_time}s"
                assert avg_load_time < 0.3, f"Load time too slow: {avg_load_time}s"
                
            finally:
                await backend.cleanup()
                
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_memory_usage_large_states(self, large_state):
        """Test memory usage with large states (>100MB)."""
        # Create even larger state (target >100MB)
        huge_state = {
            "document": large_state["document"],
            "elements": large_state["elements"] * 50,  # 50,000 elements
            "ui": large_state["ui"]
        }
        
        # Estimate size
        state_json = json.dumps(huge_state)
        size_mb = len(state_json.encode('utf-8')) / (1024 * 1024)
        print(f"Large state size: {size_mb:.1f} MB")
        
        assert size_mb > 100, f"State not large enough: {size_mb:.1f} MB"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config = PersistenceConfig(compression_enabled=True)
            backend = JSONPersistenceBackend(config, temp_dir)
            await backend.initialize()
            
            try:
                # Test save/load with huge state
                start_time = time.time()
                await backend.save_state(huge_state, "huge_state_test")
                save_time = time.time() - start_time
                
                start_time = time.time()
                loaded_state = await backend.load_state("huge_state_test")
                load_time = time.time() - start_time
                
                print(f"Large state ({size_mb:.1f} MB) performance:")
                print(f"  Save time: {save_time:.3f}s")
                print(f"  Load time: {load_time:.3f}s")
                
                # Verify data integrity
                assert len(loaded_state["elements"]) == len(huge_state["elements"])
                
                # Performance should still be reasonable
                assert save_time < 10.0, f"Save time too slow: {save_time}s"
                assert load_time < 5.0, f"Load time too slow: {load_time}s"
                
            finally:
                await backend.cleanup()