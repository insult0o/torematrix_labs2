#!/usr/bin/env python3
"""
Test Issue #62 Criteria - TableElement Implementation

This test verifies all the tasks mentioned in issue #62:
- TableElement class extending Element
- cells and headers properties
- table-specific metadata
- serialization/deserialization
- table tests pass
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_table_element_implementation():
    """Test that TableElement class is properly implemented."""
    print("🧪 Testing TableElement Implementation")
    print("=" * 50)
    
    results = {}
    
    # Test 1: TableElement class extends Element
    print("1. Testing TableElement class extending Element...")
    try:
        from src.torematrix.core.models.complex_types import TableElement
        from src.torematrix.core.models.element import Element
        
        # Check inheritance
        if issubclass(TableElement, Element):
            print("   ✅ TableElement extends Element")
            results["extends_element"] = True
        else:
            print("   ❌ TableElement does not extend Element")
            results["extends_element"] = False
    except Exception as e:
        print(f"   ❌ TableElement class not found: {e}")
        results["extends_element"] = False
    
    # Test 2: cells and headers properties
    print("2. Testing cells and headers properties...")
    try:
        from src.torematrix.core.models.complex_types import TableElement
        
        # Create a table element
        table = TableElement(
            text="Test Table",
            cells=[["A1", "B1"], ["A2", "B2"]],
            headers=["Column A", "Column B"]
        )
        
        # Check properties exist and work
        if hasattr(table, 'cells') and hasattr(table, 'headers'):
            if table.cells == [["A1", "B1"], ["A2", "B2"]] and table.headers == ["Column A", "Column B"]:
                print("   ✅ cells and headers properties working")
                results["properties"] = True
            else:
                print("   ❌ cells/headers properties not working correctly")
                results["properties"] = False
        else:
            print("   ❌ cells/headers properties not found")
            results["properties"] = False
    except Exception as e:
        print(f"   ❌ Properties test failed: {e}")
        results["properties"] = False
    
    # Test 3: table-specific metadata
    print("3. Testing table-specific metadata...")
    try:
        from src.torematrix.core.models.complex_types import TableElement, TableMetadata
        
        # Create table with metadata
        table = TableElement(
            text="Test Table",
            cells=[["A1", "B1"], ["A2", "B2"]],
            headers=["Column A", "Column B"]
        )
        
        # Check table metadata exists
        if hasattr(table, 'table_metadata') and isinstance(table.table_metadata, TableMetadata):
            print("   ✅ table-specific metadata implemented")
            results["metadata"] = True
        else:
            print("   ❌ table-specific metadata missing")
            results["metadata"] = False
    except Exception as e:
        print(f"   ❌ Metadata test failed: {e}")
        results["metadata"] = False
    
    # Test 4: serialization/deserialization
    print("4. Testing serialization/deserialization...")
    try:
        from src.torematrix.core.models.complex_types import TableElement
        
        # Create original table
        original = TableElement(
            text="Test Table",
            cells=[["A1", "B1"], ["A2", "B2"]],
            headers=["Column A", "Column B"]
        )
        
        # Test serialization
        data = original.to_dict()
        
        # Test deserialization
        restored = TableElement.from_dict(data)
        
        # Verify round-trip
        if (restored.cells == original.cells and 
            restored.headers == original.headers and
            restored.text == original.text):
            print("   ✅ serialization/deserialization working")
            results["serialization"] = True
        else:
            print("   ❌ serialization round-trip failed")
            results["serialization"] = False
    except Exception as e:
        print(f"   ❌ Serialization test failed: {e}")
        results["serialization"] = False
    
    # Test 5: Integration with factory
    print("5. Testing integration with element factory...")
    try:
        from src.torematrix.core.models.factory import ElementFactory
        from src.torematrix.core.models.complex_types import create_table
        from src.torematrix.core.models.element import ElementType
        
        # Test factory creation
        table1 = ElementFactory.create_element(
            ElementType.TABLE,
            "Factory Table",
            cells=[["X", "Y"], ["1", "2"]],
            headers=["Col X", "Col Y"]
        )
        
        # Test helper function
        table2 = create_table(
            cells=[["A", "B"], ["C", "D"]],
            headers=["Header A", "Header B"]
        )
        
        if (isinstance(table1, TableElement) and isinstance(table2, TableElement)):
            print("   ✅ factory integration working")
            results["factory"] = True
        else:
            print("   ❌ factory integration failed")
            results["factory"] = False
    except Exception as e:
        print(f"   ❌ Factory test failed: {e}")
        import traceback
        traceback.print_exc()
        results["factory"] = False
    
    return results

def test_table_creation():
    """Test the specific test_table_creation mentioned in issue."""
    print("\n🧪 Testing table_creation (Issue #62 specific)")
    print("-" * 30)
    
    try:
        from src.torematrix.core.models.complex_types import TableElement
        from src.torematrix.core.models.element import ElementType
        
        # Create table element
        table = TableElement(
            element_type=ElementType.TABLE,
            text="Sample Table",
            cells=[
                ["Name", "Age", "City"],
                ["Alice", "30", "New York"],
                ["Bob", "25", "Boston"]
            ],
            headers=["Name", "Age", "City"]
        )
        
        # Validate creation
        assert table.element_type == ElementType.TABLE
        assert table.text == "Sample Table"
        assert len(table.cells) == 3
        assert len(table.headers) == 3
        assert table.cells[0] == ["Name", "Age", "City"]
        
        print("   ✅ test_table_creation equivalent: PASS")
        return True
        
    except Exception as e:
        print(f"   ❌ test_table_creation failed: {e}")
        return False

def test_table_serialization():
    """Test the specific test_table_serialization mentioned in issue."""
    print("\n🧪 Testing table_serialization (Issue #62 specific)")
    print("-" * 30)
    
    try:
        from src.torematrix.core.models.complex_types import TableElement
        from src.torematrix.core.models.element import ElementType
        
        # Create complex table
        original = TableElement(
            element_type=ElementType.TABLE,
            text="Complex Table",
            cells=[
                ["Product", "Price", "Stock"],
                ["Laptop", "$999", "5"],
                ["Mouse", "$25", "50"]
            ],
            headers=["Product", "Price", "Stock"]
        )
        
        # Test serialization
        serialized = original.to_dict()
        
        # Verify serialized data structure
        assert "cells" in serialized
        assert "headers" in serialized
        assert "table_metadata" in serialized
        assert "element_type" in serialized
        assert "text" in serialized
        
        # Test deserialization
        restored = TableElement.from_dict(serialized)
        
        # Verify complete round-trip
        assert restored.element_type == original.element_type
        assert restored.text == original.text
        assert restored.cells == original.cells
        assert restored.headers == original.headers
        
        print("   ✅ test_table_serialization equivalent: PASS")
        return True
        
    except Exception as e:
        print(f"   ❌ test_table_serialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def print_final_summary(impl_results, creation_test, serialization_test):
    """Print comprehensive test summary."""
    print("\n" + "=" * 80)
    print("🎯 ISSUE #62 COMPREHENSIVE TEST RESULTS")
    print("=" * 80)
    
    print("\n📋 IMPLEMENTATION TASKS")
    print("-" * 30)
    for task, passed in impl_results.items():
        status = "✅ IMPLEMENTED" if passed else "❌ MISSING"
        task_name = task.replace('_', ' ').title()
        print(f"   {task_name}: {status}")
    
    print("\n📋 SPECIFIC TESTS MENTIONED IN ISSUE")
    print("-" * 30)
    print(f"   test_table_creation: {'✅ PASS' if creation_test else '❌ FAIL'}")
    print(f"   test_table_serialization: {'✅ PASS' if serialization_test else '❌ FAIL'}")
    
    # Calculate overall success
    impl_success = all(impl_results.values())
    tests_success = creation_test and serialization_test
    overall_success = impl_success and tests_success
    
    impl_percent = (sum(impl_results.values()) / len(impl_results)) * 100
    
    print(f"\n🎯 FINAL RESULT")
    print("-" * 20)
    print(f"Implementation Tasks: {'✅ ALL COMPLETE' if impl_success else '❌ SOME INCOMPLETE'} ({impl_percent:.0f}%)")
    print(f"Specific Tests: {'✅ ALL PASS' if tests_success else '❌ SOME FAIL'}")
    print(f"Overall Status: {'🎉 ISSUE #62 RESOLVED' if overall_success else '⚠️ ISSUE #62 NEEDS WORK'}")
    
    if overall_success:
        print("\n🏆 READY TO CLOSE ISSUE #62")
        print("   ✅ TableElement class properly implemented")
        print("   ✅ All required properties and methods working")
        print("   ✅ Serialization/deserialization functional")
        print("   ✅ All mentioned tests would pass")
        print("   ✅ Integration with factory complete")
    
    return overall_success

def main():
    """Main test function."""
    print("🚀 ISSUE #62 VERIFICATION TEST")
    print(f"📍 Testing TableElement implementation")
    print(f"⏰ Test time: {Path(__file__).stat().st_mtime}")
    
    # Run all tests
    impl_results = test_table_element_implementation()
    creation_test = test_table_creation()
    serialization_test = test_table_serialization()
    
    # Print comprehensive summary
    overall_success = print_final_summary(impl_results, creation_test, serialization_test)
    
    return 0 if overall_success else 1

if __name__ == "__main__":
    try:
        result = main()
        sys.exit(result)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)