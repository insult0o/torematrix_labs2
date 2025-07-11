#!/usr/bin/env python3
"""
Test Enhanced V1 Integration

This script tests the enhanced systems integration without launching the full GUI,
allowing us to verify that all components work correctly.
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_enhanced_event_system():
    """Test the enhanced event system."""
    logger.info("Testing Enhanced Event System...")
    
    try:
        from enhanced_event_system import UnifiedEventBus, EventTypeV1, SignalBridge, GlobalSignalProcessor
        
        # Test event bus
        event_bus = UnifiedEventBus()
        logger.info("  ✅ UnifiedEventBus created")
        
        # Test signal processor
        signal_processor = GlobalSignalProcessor(event_bus)
        logger.info("  ✅ GlobalSignalProcessor created")
        
        # Test signal bridge
        signal_bridge = SignalBridge(event_bus)
        logger.info("  ✅ SignalBridge created")
        
        # Test basic event publishing
        event_id = event_bus.publish(EventTypeV1.APPLICATION_STARTED, "test_script", {"test": True})
        logger.info(f"  ✅ Published test event: {event_id}")
        
        # Test statistics
        stats = signal_processor.get_processing_stats()
        logger.info(f"  ✅ Signal processor stats: {stats}")
        
        # Cleanup
        signal_processor.shutdown()
        logger.info("  ✅ Enhanced Event System test passed")
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Enhanced Event System test failed: {e}")
        return False


def test_enhanced_persistence():
    """Test the enhanced persistence system."""
    logger.info("Testing Enhanced Persistence System...")
    
    try:
        from enhanced_persistence import (
            PersistenceService, PersistenceConfig, PersistenceMode,
            StateCategory, PersistenceLevel, EnhancedStateManager
        )
        
        # Test persistence config
        config = PersistenceConfig(
            mode=PersistenceMode.TESTING,
            base_storage_dir=Path("/tmp/tore_test"),
            enable_backups=False  # Disable for testing
        )
        logger.info("  ✅ PersistenceConfig created")
        
        # Test persistence service
        persistence_service = PersistenceService(config)
        logger.info("  ✅ PersistenceService created")
        
        # Test component registration
        success = persistence_service.register_component(
            "test_component",
            StateCategory.UI,
            PersistenceLevel.SESSION,
            {"test_value": 42}
        )
        if success:
            logger.info("  ✅ Component registered successfully")
        else:
            logger.error("  ❌ Component registration failed")
            return False
        
        # Test state updates
        success = persistence_service.update_component_state(
            "test_component",
            {"test_value": 100, "new_value": "hello"}
        )
        if success:
            logger.info("  ✅ State update successful")
        else:
            logger.error("  ❌ State update failed")
            return False
        
        # Test state retrieval
        value = persistence_service.get_component_state("test_component", "test_value")
        if value == 100:
            logger.info("  ✅ State retrieval successful")
        else:
            logger.error(f"  ❌ State retrieval failed: expected 100, got {value}")
            return False
        
        # Test state snapshot
        snapshot = persistence_service.create_state_snapshot()
        if snapshot and "test_component" in snapshot.get("components", {}):
            logger.info("  ✅ State snapshot created successfully")
        else:
            logger.error("  ❌ State snapshot failed")
            return False
        
        # Test statistics
        status = persistence_service.get_comprehensive_status()
        logger.info(f"  ✅ Persistence service status: {status['service']['registered_components']} components")
        
        # Cleanup
        persistence_service.cleanup()
        logger.info("  ✅ Enhanced Persistence System test passed")
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Enhanced Persistence System test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_v1_imports():
    """Test that V1 components can be imported."""
    logger.info("Testing V1 Component Imports...")
    
    try:
        # Test core V1 imports
        from tore_matrix_labs.config.settings import Settings
        logger.info("  ✅ Settings imported")
        
        from tore_matrix_labs.ui.main_window import MainWindow
        logger.info("  ✅ MainWindow imported")
        
        from tore_matrix_labs.core.document_processor import DocumentProcessor
        logger.info("  ✅ DocumentProcessor imported")
        
        logger.info("  ✅ V1 Component Imports test passed")
        return True
        
    except Exception as e:
        logger.error(f"  ❌ V1 Component Imports test failed: {e}")
        return False


def test_integration_compatibility():
    """Test that enhanced systems and V1 can work together."""
    logger.info("Testing Integration Compatibility...")
    
    try:
        # Import both systems
        from enhanced_event_system import UnifiedEventBus, EventTypeV1
        from enhanced_persistence import PersistenceService, PersistenceConfig, PersistenceMode, StateCategory
        from tore_matrix_labs.config.settings import Settings
        
        # Create enhanced systems
        event_bus = UnifiedEventBus()
        persistence_service = PersistenceService(
            PersistenceConfig(mode=PersistenceMode.TESTING, enable_backups=False)
        )
        
        # Create V1 settings
        v1_settings = Settings()
        
        # Test cross-system communication
        event_id = event_bus.publish(EventTypeV1.APPLICATION_STARTED, "integration_test")
        logger.info(f"  ✅ Event published: {event_id}")
        
        # Test state management integration
        persistence_service.register_component("v1_settings", StateCategory.SYSTEM)
        persistence_service.update_component_state("v1_settings", {"integrated": True})
        
        # Verify state
        integrated = persistence_service.get_component_state("v1_settings", "integrated")
        if integrated:
            logger.info("  ✅ Cross-system state management works")
        else:
            logger.error("  ❌ Cross-system state management failed")
            return False
        
        # Cleanup
        persistence_service.cleanup()
        
        logger.info("  ✅ Integration Compatibility test passed")
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Integration Compatibility test failed: {e}")
        return False


def main():
    """Run all integration tests."""
    logger.info("🧪 Running Enhanced V1 Integration Tests")
    logger.info("=" * 50)
    
    tests = [
        ("Enhanced Event System", test_enhanced_event_system),
        ("Enhanced Persistence", test_enhanced_persistence),
        ("V1 Component Imports", test_v1_imports),
        ("Integration Compatibility", test_integration_compatibility),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n📋 {test_name}")
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 Test Results Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"  {status}: {test_name}")
        if result:
            passed += 1
    
    logger.info(f"\n🎯 Overall: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        logger.info("🎉 All tests passed! Enhanced V1 is ready to launch.")
        return 0
    else:
        logger.info("⚠️  Some tests failed. Check the logs above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())