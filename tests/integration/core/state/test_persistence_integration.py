"""
Integration tests for state persistence system.

Tests the complete persistence system including backends, history, snapshots,
and middleware working together.
"""

import pytest
import asyncio
import tempfile
import time
from unittest.mock import MagicMock

from src.torematrix.core.state.persistence.base import PersistenceConfig, PersistenceStrategy
from src.torematrix.core.state.persistence.json_backend import JSONPersistenceBackend
from src.torematrix.core.state.persistence.sqlite_backend import SQLitePersistenceBackend
from src.torematrix.core.state.history import TimeTravel, TimeTravelMiddleware
from src.torematrix.core.state.snapshots import SnapshotManager, SnapshotStrategy
from src.torematrix.core.state.migrations import StateMigrator, InitialStateMigration


class MockStore:
    """Mock store for testing middleware integration."""
    
    def __init__(self, initial_state=None):
        self._state = initial_state or {}
        self._middleware_chain = []
    
    def get_state(self):
        return self._state.copy()
    
    def set_state(self, state):
        self._state = state.copy()
    
    def add_middleware(self, middleware):
        self._middleware_chain.append(middleware)
    
    async def dispatch(self, action):
        """Dispatch an action through the middleware chain."""
        async def execute_chain(middleware_index, action):
            if middleware_index >= len(self._middleware_chain):
                # Final handler - apply action to state
                return self._apply_action(action)
            
            middleware = self._middleware_chain[middleware_index]
            
            async def next_middleware(action):
                return await execute_chain(middleware_index + 1, action)
            
            return await middleware(self, next_middleware, action)
        
        return await execute_chain(0, action)
    
    def _apply_action(self, action):
        """Apply action to state (mock implementation)."""
        if action.get("type") == "increment":
            self._state["counter"] = self._state.get("counter", 0) + 1
        elif action.get("type") == "set_value":
            self._state[action["key"]] = action["value"]
        elif action.get("type") == "add_element":
            if "elements" not in self._state:
                self._state["elements"] = []
            self._state["elements"].append(action["element"])
        
        return "success"


@pytest.mark.asyncio
class TestPersistenceIntegration:
    """Test complete persistence system integration."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    async def integrated_system(self, temp_dir):
        """Create integrated persistence system."""
        # Configuration
        persistence_config = PersistenceConfig(
            strategy=PersistenceStrategy.IMMEDIATE,
            compression_enabled=True,
            max_versions=50
        )
        
        snapshot_strategy = SnapshotStrategy(
            auto_snapshot=False,  # Manual for testing
            max_snapshots=20,
            compression_enabled=True
        )
        
        # Components
        json_backend = JSONPersistenceBackend(persistence_config, temp_dir)
        time_travel = TimeTravel(max_history=100, enable_branching=True)
        snapshot_manager = SnapshotManager(strategy=snapshot_strategy)
        migrator = StateMigrator()
        
        # Initialize components
        await json_backend.initialize()
        await snapshot_manager.start()
        
        # Register migration
        migrator.register_migration(InitialStateMigration())
        
        # Create store and middleware
        store = MockStore({"counter": 0, "initialized": True})
        
        # Add middleware
        from src.torematrix.core.state.persistence.base import PersistenceMiddleware
        persistence_middleware = PersistenceMiddleware(json_backend, persistence_config)
        await persistence_middleware.start()
        
        time_travel_middleware = TimeTravelMiddleware(time_travel)
        
        store.add_middleware(time_travel_middleware)
        store.add_middleware(persistence_middleware)
        
        yield {
            "store": store,
            "json_backend": json_backend,
            "time_travel": time_travel,
            "snapshot_manager": snapshot_manager,
            "migrator": migrator,
            "persistence_middleware": persistence_middleware
        }
        
        # Cleanup
        await persistence_middleware.stop()
        await snapshot_manager.stop()
        await json_backend.cleanup()
    
    async def test_full_system_workflow(self, integrated_system):
        """Test complete workflow with all components."""
        store = integrated_system["store"]
        time_travel = integrated_system["time_travel"]
        snapshot_manager = integrated_system["snapshot_manager"]
        json_backend = integrated_system["json_backend"]
        
        # 1. Dispatch actions and verify they're recorded in history
        actions = [
            {"type": "increment"},
            {"type": "increment"},
            {"type": "set_value", "key": "name", "value": "test_doc"},
            {"type": "add_element", "element": {"id": "elem1", "type": "text"}},
            {"type": "increment"}
        ]
        
        for action in actions:
            result = await store.dispatch(action)
            assert result == "success"
        
        # Verify state
        final_state = store.get_state()
        assert final_state["counter"] == 3
        assert final_state["name"] == "test_doc"
        assert len(final_state["elements"]) == 1
        
        # Verify history was recorded
        assert len(time_travel._history) == len(actions)
        
        # 2. Create snapshot
        snapshot_id = snapshot_manager.create_snapshot(
            final_state,
            metadata={"test": "integration"},
            tags={"integration_test"}
        )
        
        # 3. Verify persistence
        await asyncio.sleep(0.1)  # Allow async persistence to complete
        
        # Should have persisted states
        versions = await json_backend.list_versions()
        assert len(versions) >= len(actions)
        
        # 4. Time travel
        previous_state = time_travel.travel_backward(2)
        assert previous_state["counter"] == 2
        
        # 5. Restore snapshot
        restored_state = snapshot_manager.restore_snapshot(snapshot_id)
        assert restored_state == final_state
        
        # 6. Load persisted state
        latest_persisted = await json_backend.load_state()
        assert latest_persisted["counter"] == final_state["counter"]
    
    async def test_persistence_with_large_state(self, integrated_system):
        """Test persistence with large state data."""
        store = integrated_system["store"]
        snapshot_manager = integrated_system["snapshot_manager"]
        
        # Create large state
        large_elements = [
            {
                "id": f"elem_{i}",
                "type": "text" if i % 2 == 0 else "table",
                "content": f"Large content for element {i} " * 50,
                "metadata": {"page": i // 100, "position": {"x": i, "y": i * 2}}
            }
            for i in range(2000)
        ]
        
        # Add large number of elements
        for element in large_elements[:100]:  # Add in batches
            await store.dispatch({
                "type": "add_element",
                "element": element
            })
        
        final_state = store.get_state()
        
        # Create snapshot of large state
        start_time = time.time()
        snapshot_id = snapshot_manager.create_snapshot(
            final_state,
            tags={"large_state_test"}
        )
        snapshot_time = time.time() - start_time
        
        print(f"Large state snapshot creation time: {snapshot_time:.3f}s")
        assert snapshot_time < 2.0, "Snapshot creation too slow"
        
        # Verify restoration
        start_time = time.time()
        restored_state = snapshot_manager.restore_snapshot(snapshot_id)
        restore_time = time.time() - start_time
        
        print(f"Large state restoration time: {restore_time:.3f}s")
        assert restore_time < 1.0, "Snapshot restoration too slow"
        
        assert len(restored_state["elements"]) == len(final_state["elements"])
    
    async def test_concurrent_operations(self, integrated_system):
        """Test concurrent operations across all components."""
        store = integrated_system["store"]
        time_travel = integrated_system["time_travel"]
        snapshot_manager = integrated_system["snapshot_manager"]
        
        async def worker_actions(worker_id, num_actions):
            """Worker function for concurrent actions."""
            for i in range(num_actions):
                await store.dispatch({
                    "type": "set_value",
                    "key": f"worker_{worker_id}_action_{i}",
                    "value": f"value_{i}"
                })
                
                # Occasionally create snapshots
                if i % 5 == 0:
                    current_state = store.get_state()
                    snapshot_manager.create_snapshot(
                        current_state,
                        tags={f"worker_{worker_id}"}
                    )
        
        # Run concurrent workers
        workers = [
            worker_actions(worker_id, 10)
            for worker_id in range(5)
        ]
        
        await asyncio.gather(*workers)
        
        # Verify all actions were recorded
        assert len(time_travel._history) == 50  # 5 workers * 10 actions each
        
        # Verify snapshots were created
        snapshots = snapshot_manager.list_snapshots()
        assert len(snapshots) >= 5  # At least one per worker
        
        # Verify final state integrity
        final_state = store.get_state()
        for worker_id in range(5):
            assert f"worker_{worker_id}_action_9" in final_state
    
    async def test_error_handling_and_recovery(self, integrated_system):
        """Test error handling and recovery scenarios."""
        store = integrated_system["store"]
        time_travel = integrated_system["time_travel"]
        json_backend = integrated_system["json_backend"]
        
        # Normal operations
        await store.dispatch({"type": "increment"})
        await store.dispatch({"type": "set_value", "key": "test", "value": "before_error"})
        
        # Simulate error in action processing
        original_apply = store._apply_action
        
        def failing_apply(action):
            if action.get("type") == "failing_action":
                raise ValueError("Simulated action failure")
            return original_apply(action)
        
        store._apply_action = failing_apply
        
        # Dispatch failing action
        with pytest.raises(ValueError, match="Simulated action failure"):
            await store.dispatch({"type": "failing_action"})
        
        # Verify history still recorded the failed action
        assert len(time_travel._history) >= 3
        last_entry = time_travel._history[-1]
        assert last_entry.metadata.get("failed") is True
        
        # Restore normal operation
        store._apply_action = original_apply
        
        # Continue with normal operations
        await store.dispatch({"type": "set_value", "key": "test", "value": "after_error"})
        
        # Verify system recovered
        final_state = store.get_state()
        assert final_state["test"] == "after_error"
        
        # Verify persistence still works
        await asyncio.sleep(0.1)
        persisted_state = await json_backend.load_state()
        assert persisted_state["test"] == "after_error"
    
    async def test_memory_efficiency(self, integrated_system):
        """Test memory efficiency with prolonged usage."""
        store = integrated_system["store"]
        time_travel = integrated_system["time_travel"]
        snapshot_manager = integrated_system["snapshot_manager"]
        
        # Perform many operations
        for i in range(200):
            await store.dispatch({
                "type": "set_value",
                "key": f"iteration_{i}",
                "value": f"data_{i}"
            })
            
            # Create periodic snapshots
            if i % 20 == 0:
                current_state = store.get_state()
                snapshot_manager.create_snapshot(
                    current_state,
                    tags={f"checkpoint_{i}"}
                )
        
        # Verify history pruning worked
        assert len(time_travel._history) <= time_travel.max_history
        
        # Verify snapshot pruning worked
        snapshots = snapshot_manager.list_snapshots()
        assert len(snapshots) <= snapshot_manager.strategy.max_snapshots
        
        # Verify system is still functional
        await store.dispatch({"type": "increment"})
        final_state = store.get_state()
        assert final_state["counter"] >= 1
    
    async def test_state_migration_integration(self, integrated_system):
        """Test state migration with persistence."""
        migrator = integrated_system["migrator"]
        snapshot_manager = integrated_system["snapshot_manager"]
        
        # Create state without metadata (old format)
        old_state = {
            "document": {"id": "migration_test"},
            "elements": {"elem1": {"type": "text"}, "elem2": {"type": "image"}},
            "data": "test_migration"
        }
        
        # Create snapshot of old state
        old_snapshot_id = snapshot_manager.create_snapshot(
            old_state,
            tags={"old_format"}
        )
        
        # Migrate state
        migrated_state = migrator.migrate_state(old_state)
        
        # Verify migration applied
        assert "_meta" in migrated_state
        assert migrated_state["_meta"]["version"] == "1.0.0"
        
        # Create snapshot of migrated state
        new_snapshot_id = snapshot_manager.create_snapshot(
            migrated_state,
            tags={"migrated"}
        )
        
        # Verify both snapshots can be restored
        old_restored = snapshot_manager.restore_snapshot(old_snapshot_id)
        new_restored = snapshot_manager.restore_snapshot(new_snapshot_id)
        
        assert "_meta" not in old_restored
        assert "_meta" in new_restored
        assert new_restored["_meta"]["version"] == "1.0.0"