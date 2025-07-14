"""
Tests for Memory Management Utilities.
"""

import pytest
import gc
import time
import weakref
from unittest.mock import Mock, patch, MagicMock
import threading

from tore_matrix_labs.ui.components.memory import (
    MemorySnapshot,
    WeakRefManager,
    CircularReferenceDetector,
    MemoryLeakDetector,
    get_weak_ref_manager,
    get_circular_ref_detector,
    get_memory_leak_detector,
    MemoryManagedMixin
)


class TestMemorySnapshot:
    """Test the MemorySnapshot dataclass."""
    
    def test_memory_snapshot_creation(self):
        """Test creating a memory snapshot."""
        from datetime import datetime
        
        snapshot = MemorySnapshot(
            timestamp=datetime.now(),
            total_memory=1024 * 1024 * 100,  # 100 MB
            component_count=50,
            reference_count=1000,
            gc_stats={'collections': (10, 5, 2)},
            top_allocations=[('module.py:100', 1024)]
        )
        
        assert snapshot.memory_mb() == 100.0
        assert snapshot.component_count == 50
        assert snapshot.reference_count == 1000


class TestWeakRefManager:
    """Test the WeakRefManager class."""
    
    def test_create_ref(self):
        """Test creating a weak reference."""
        manager = WeakRefManager()
        obj = Mock()
        
        ref = manager.create_ref(obj)
        
        assert ref() is obj
        assert id(obj) in manager._refs
    
    def test_create_ref_with_callback(self):
        """Test creating a weak reference with callback."""
        manager = WeakRefManager()
        callback = Mock()
        
        # Create object in scope
        def create_and_release():
            obj = Mock()
            ref = manager.create_ref(obj, callback)
            obj_id = id(obj)
            return obj_id
        
        obj_id = create_and_release()
        
        # Force garbage collection
        gc.collect()
        time.sleep(0.1)  # Give callback time to execute
        
        # Verify callback called
        callback.assert_called_once()
        assert obj_id not in manager._refs
    
    def test_add_cleanup_callback(self):
        """Test adding cleanup callbacks."""
        manager = WeakRefManager()
        callback1 = Mock()
        callback2 = Mock()
        
        # Create object in scope
        def create_and_release():
            obj = Mock()
            ref = manager.create_ref(obj)
            manager.add_cleanup_callback(obj, callback1)
            manager.add_cleanup_callback(obj, callback2)
            return id(obj)
        
        obj_id = create_and_release()
        
        # Force garbage collection
        gc.collect()
        time.sleep(0.1)
        
        # Verify both callbacks called
        callback1.assert_called_once()
        callback2.assert_called_once()
    
    def test_get_ref(self):
        """Test getting object from weak reference."""
        manager = WeakRefManager()
        obj = Mock()
        obj_id = id(obj)
        
        ref = manager.create_ref(obj)
        
        # Should get object while it exists
        assert manager.get_ref(obj_id) is obj
        
        # Should return None for non-existent ID
        assert manager.get_ref(999999) is None
        
        # Should return None after object is deleted
        del obj
        gc.collect()
        assert manager.get_ref(obj_id) is None
    
    def test_get_active_count(self):
        """Test getting count of active references."""
        manager = WeakRefManager()
        
        obj1 = Mock()
        obj2 = Mock()
        
        ref1 = manager.create_ref(obj1)
        ref2 = manager.create_ref(obj2)
        
        assert manager.get_active_count() == 2
        
        del obj1
        gc.collect()
        
        assert manager.get_active_count() == 1


class TestCircularReferenceDetector:
    """Test the CircularReferenceDetector class."""
    
    def test_add_relationship_safe(self):
        """Test adding a safe parent-child relationship."""
        detector = CircularReferenceDetector()
        parent = Mock()
        child = Mock()
        
        result = detector.add_relationship(parent, child)
        
        assert result is True
        assert id(child) in detector._relationships[id(parent)]
    
    def test_detect_direct_cycle(self):
        """Test detecting a direct circular reference."""
        detector = CircularReferenceDetector()
        obj1 = Mock()
        obj2 = Mock()
        
        # Create relationship: obj1 -> obj2
        assert detector.add_relationship(obj1, obj2) is True
        
        # Try to create cycle: obj2 -> obj1
        assert detector.add_relationship(obj2, obj1) is False
    
    def test_detect_indirect_cycle(self):
        """Test detecting an indirect circular reference."""
        detector = CircularReferenceDetector()
        obj1 = Mock()
        obj2 = Mock()
        obj3 = Mock()
        
        # Create chain: obj1 -> obj2 -> obj3
        assert detector.add_relationship(obj1, obj2) is True
        assert detector.add_relationship(obj2, obj3) is True
        
        # Try to create cycle: obj3 -> obj1
        assert detector.add_relationship(obj3, obj1) is False
    
    def test_remove_relationship(self):
        """Test removing a relationship."""
        detector = CircularReferenceDetector()
        parent = Mock()
        child = Mock()
        
        detector.add_relationship(parent, child)
        detector.remove_relationship(parent, child)
        
        assert id(child) not in detector._relationships.get(id(parent), set())
    
    def test_clear_relationships(self):
        """Test clearing all relationships for an object."""
        detector = CircularReferenceDetector()
        obj1 = Mock()
        obj2 = Mock()
        obj3 = Mock()
        
        # Create relationships
        detector.add_relationship(obj1, obj2)
        detector.add_relationship(obj2, obj3)
        detector.add_relationship(obj3, obj1)  # This would fail, but for testing
        
        # Clear relationships for obj2
        detector.clear_relationships(obj2)
        
        # Verify obj2 removed as parent and child
        assert id(obj2) not in detector._relationships
        assert id(obj2) not in detector._relationships.get(id(obj1), set())


class TestMemoryLeakDetector:
    """Test the MemoryLeakDetector class."""
    
    def test_start_stop_tracking(self):
        """Test starting and stopping memory tracking."""
        detector = MemoryLeakDetector()
        
        detector.start_tracking()
        assert detector._tracking_enabled is True
        
        detector.stop_tracking()
        assert detector._tracking_enabled is False
    
    def test_register_component(self):
        """Test registering a component."""
        detector = MemoryLeakDetector()
        component = Mock()
        
        detector.register_component(component)
        
        # Component should be in weak set
        assert component in detector._component_registry
    
    def test_take_snapshot(self):
        """Test taking a memory snapshot."""
        detector = MemoryLeakDetector()
        
        # Register some components
        for _ in range(5):
            detector.register_component(Mock())
        
        snapshot = detector.take_snapshot()
        
        assert snapshot is not None
        assert snapshot.component_count == 5
        assert snapshot.total_memory > 0
        assert len(detector._snapshots) == 1
    
    def test_check_for_leaks_no_leak(self):
        """Test leak checking with no leaks."""
        detector = MemoryLeakDetector()
        
        # Take snapshots with stable memory
        for i in range(5):
            for _ in range(i):
                detector.register_component(Mock())
            detector.take_snapshot()
            time.sleep(0.01)
        
        warnings = detector.check_for_leaks(threshold_mb=1000.0)  # High threshold
        
        # Should have no warnings with high threshold
        assert len(warnings) == 0
    
    def test_check_for_leaks_with_growth(self):
        """Test leak checking with component growth."""
        detector = MemoryLeakDetector()
        
        # Take initial snapshot
        detector.take_snapshot()
        
        # Add many components
        for _ in range(200):
            detector.register_component(Mock())
        
        # Take final snapshot
        detector.take_snapshot()
        
        warnings = detector.check_for_leaks(threshold_mb=0.1)
        
        # Should detect component growth
        component_warnings = [w for w in warnings if 'Component count' in w]
        assert len(component_warnings) > 0
    
    def test_get_memory_report(self):
        """Test getting memory report."""
        detector = MemoryLeakDetector()
        
        # Register components and take snapshots
        for i in range(3):
            for _ in range(10):
                detector.register_component(Mock())
            detector.take_snapshot()
            time.sleep(0.01)
        
        report = detector.get_memory_report()
        
        assert 'timestamp' in report
        assert 'memory_mb' in report
        assert 'component_count' in report
        assert 'snapshot_count' in report
        assert report['snapshot_count'] == 3
        
        # Should have growth metrics
        assert 'growth' in report
        assert 'components' in report['growth']


class TestMemoryManagedMixin:
    """Test the MemoryManagedMixin class."""
    
    def test_mixin_initialization(self):
        """Test that mixin initializes properly."""
        class TestComponent(MemoryManagedMixin):
            pass
        
        component = TestComponent()
        
        assert hasattr(component, '_child_refs')
        assert hasattr(component, '_parent_ref')
        assert component._parent_ref is None
    
    def test_add_child_safe(self):
        """Test adding a child safely."""
        class TestComponent(MemoryManagedMixin):
            pass
        
        parent = TestComponent()
        child = TestComponent()
        
        result = parent.add_child(child)
        
        assert result is True
        assert len(parent.get_children()) == 1
        assert parent.get_children()[0] is child
        assert child.get_parent() is parent
    
    def test_add_child_circular_prevention(self):
        """Test that circular references are prevented."""
        class TestComponent(MemoryManagedMixin):
            pass
        
        parent = TestComponent()
        child = TestComponent()
        
        # Add child to parent
        assert parent.add_child(child) is True
        
        # Try to add parent to child (would create cycle)
        assert child.add_child(parent) is False
    
    def test_remove_child(self):
        """Test removing a child."""
        class TestComponent(MemoryManagedMixin):
            pass
        
        parent = TestComponent()
        child1 = TestComponent()
        child2 = TestComponent()
        
        parent.add_child(child1)
        parent.add_child(child2)
        parent.remove_child(child1)
        
        children = parent.get_children()
        assert len(children) == 1
        assert child2 in children
        assert child1 not in children
    
    def test_weak_references_cleanup(self):
        """Test that weak references allow garbage collection."""
        class TestComponent(MemoryManagedMixin):
            pass
        
        parent = TestComponent()
        
        # Add child in scope
        def add_child():
            child = TestComponent()
            parent.add_child(child)
            return weakref.ref(child)
        
        child_ref = add_child()
        
        # Child should be collected
        gc.collect()
        assert child_ref() is None
        assert len(parent.get_children()) == 0
    
    def test_cleanup_memory(self):
        """Test memory cleanup."""
        class TestComponent(MemoryManagedMixin):
            pass
        
        parent = TestComponent()
        child = TestComponent()
        
        parent.add_child(child)
        parent.cleanup_memory()
        
        assert len(parent._child_refs) == 0
        assert parent._parent_ref is None


class TestGlobalInstances:
    """Test global instance getters."""
    
    def test_get_weak_ref_manager(self):
        """Test getting global weak ref manager."""
        manager1 = get_weak_ref_manager()
        manager2 = get_weak_ref_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, WeakRefManager)
    
    def test_get_circular_ref_detector(self):
        """Test getting global circular ref detector."""
        detector1 = get_circular_ref_detector()
        detector2 = get_circular_ref_detector()
        
        assert detector1 is detector2
        assert isinstance(detector1, CircularReferenceDetector)
    
    def test_get_memory_leak_detector(self):
        """Test getting global memory leak detector."""
        detector1 = get_memory_leak_detector()
        detector2 = get_memory_leak_detector()
        
        assert detector1 is detector2
        assert isinstance(detector1, MemoryLeakDetector)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])