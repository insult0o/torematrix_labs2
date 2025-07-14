#!/usr/bin/env python3
"""
Quick test to verify acceptance test structure and basic imports.

This script performs a basic validation that all test components can be imported
and the test structure is correct.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all required components can be imported."""
    print("🔍 Testing imports...")
    
    try:
        # Test event bus imports (Dependency #1)
        from src.torematrix.core.events.event_bus import EventBus
        from src.torematrix.core.events.event_types import Event, EventPriority
        print("✅ Event Bus imports successful")
    except ImportError as e:
        print(f"❌ Event Bus import failed: {e}")
        return False
    
    try:
        # Test element model imports (Dependency #2)
        from src.torematrix.core.models.element import Element, ElementType
        from src.torematrix.core.models.factory import ElementFactory
        print("✅ Element Model imports successful")
    except ImportError as e:
        print(f"❌ Element Model import failed: {e}")
        return False
    
    # Note: State management system is not yet implemented
    # These imports would be tested once Issue #3 is completed
    print("⏳ State Management system - not yet implemented")
    print("⏳ Persistence System - not yet implemented")
    
    return True

def test_basic_functionality():
    """Test basic functionality of core components."""
    print("\n🧪 Testing basic functionality...")
    
    try:
        # Test element creation
        from src.torematrix.core.models.factory import ElementFactory
        from src.torematrix.core.models.element import ElementType
        element = ElementFactory.create_from_text("Test content", ElementType.NARRATIVE_TEXT)
        assert element.element_id is not None
        assert element.text == "Test content"
        print("✅ Element creation works")
        
        # Test element validation
        assert element.element_type == ElementType.NARRATIVE_TEXT
        assert element.metadata is not None
        print("✅ Element validation works")
        
        # Test factory methods
        batch_elements = ElementFactory.create_batch([
            {"element_type": ElementType.TITLE, "text": "Test Title"},
            {"element_type": ElementType.NARRATIVE_TEXT, "text": "Test Content"}
        ])
        assert len(batch_elements) == 2
        print("✅ Batch creation works")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def test_file_structure():
    """Test that all required test files exist."""
    print("\n📁 Testing file structure...")
    
    required_files = [
        "tests/acceptance/core/state/__init__.py",
        "tests/acceptance/core/state/test_issue_3_acceptance_criteria.py",
        "tests/acceptance/core/state/test_dependencies_integration.py",
        "tests/acceptance/run_acceptance_tests.py",
        "tests/acceptance/README.md"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = project_root / file_path
        if not full_path.exists():
            missing_files.append(file_path)
        else:
            print(f"✅ {file_path}")
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files present")
    return True

def main():
    """Run all quick tests."""
    print("🚀 Quick Acceptance Test Validation")
    print("=" * 50)
    
    # Run all tests
    tests = [
        ("File Structure", test_file_structure),
        ("Component Imports", test_imports),
        ("Basic Functionality", test_basic_functionality)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 QUICK TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All quick tests passed!")
        print("Acceptance test structure is ready.")
        print("\nNext steps:")
        print("1. Install missing dependencies if any")
        print("2. Run full acceptance tests:")
        print("   python tests/acceptance/run_acceptance_tests.py")
        return True
    else:
        print(f"\n⚠️ {total - passed} tests failed")
        print("Fix issues before running full acceptance tests.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)