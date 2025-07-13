#!/usr/bin/env python3
"""Simple test script to verify the parser system works."""

import asyncio
import sys
from unittest.mock import Mock

def create_mock_element(element_type, text):
    """Create a mock element for testing."""
    element = Mock()
    element.type = element_type
    element.text = text
    element.metadata = {}
    return element

async def test_code_parser():
    """Test the code parser."""
    from src.torematrix.core.processing.parsers.code import CodeParser
    
    parser = CodeParser()
    
    # Test Python code
    python_code = """
def hello_world():
    print("Hello, World!")
    return True

class TestClass:
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value
"""
    
    element = create_mock_element("CodeBlock", python_code)
    
    try:
        result = await parser.parse(element)
        
        if result.success:
            print("✅ Code parser test PASSED")
            print(f"   Language detected: {result.data.get('language')}")
            print(f"   Functions found: {result.data.get('elements', {}).get('functions', [])}")
            print(f"   Classes found: {result.data.get('elements', {}).get('classes', [])}")
            print(f"   Confidence: {result.metadata.confidence:.2f}")
            return True
        else:
            print("❌ Code parser test FAILED")
            print(f"   Error: {result.validation_errors}")
            return False
    except Exception as e:
        print(f"❌ Code parser test FAILED with exception: {e}")
        return False

async def test_table_parser():
    """Test the table parser."""
    from src.torematrix.core.processing.parsers.table import TableParser
    
    parser = TableParser()
    
    # Test simple table
    table_text = """
| Name | Age | City |
|------|-----|------|
| John | 25  | NYC  |
| Jane | 30  | LA   |
| Bob  | 35  | CHI  |
"""
    
    element = create_mock_element("Table", table_text)
    
    try:
        result = await parser.parse(element)
        
        if result.success:
            print("✅ Table parser test PASSED")
            print(f"   Rows: {result.data.get('rows')}")
            print(f"   Columns: {result.data.get('columns')}")
            print(f"   Headers: {result.data.get('headers')}")
            print(f"   Confidence: {result.metadata.confidence:.2f}")
            return True
        else:
            print("❌ Table parser test FAILED")
            print(f"   Error: {result.validation_errors}")
            return False
    except Exception as e:
        print(f"❌ Table parser test FAILED with exception: {e}")
        return False

async def test_parser_factory():
    """Test the parser factory."""
    from src.torematrix.core.processing.parsers.factory import ParserFactory
    from src.torematrix.core.processing.parsers.code import CodeParser
    from src.torematrix.core.processing.parsers.table import TableParser
    
    try:
        # Clear and register parsers
        ParserFactory.clear_all_parsers()
        ParserFactory.register_parser('code', CodeParser)
        ParserFactory.register_parser('table', TableParser)
        
        # Test parser selection
        code_element = create_mock_element("CodeBlock", "def test(): pass")
        table_element = create_mock_element("Table", "| A | B |\n| 1 | 2 |")
        
        code_parser = ParserFactory.get_parser(code_element)
        table_parser = ParserFactory.get_parser(table_element)
        
        if code_parser and table_parser:
            print("✅ Parser factory test PASSED")
            print(f"   Code parser: {code_parser.__class__.__name__}")
            print(f"   Table parser: {table_parser.__class__.__name__}")
            
            # Test parsing through factory
            code_result = await code_parser.parse(code_element)
            table_result = await table_parser.parse(table_element)
            
            if code_result.success and table_result.success:
                print(f"   Both parsers executed successfully")
                return True
            else:
                print(f"   Parser execution failed")
                return False
        else:
            print("❌ Parser factory test FAILED")
            print(f"   Could not get parsers from factory")
            return False
    except Exception as e:
        print(f"❌ Parser factory test FAILED with exception: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 Testing TORE Matrix Labs V3 Parser System")
    print("=" * 50)
    
    tests = [
        ("Code Parser", test_code_parser),
        ("Table Parser", test_table_parser),
        ("Parser Factory", test_parser_factory),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        try:
            result = await test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ {test_name} test FAILED with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_name, _) in enumerate(tests):
        status = "✅ PASSED" if results[i] else "❌ FAILED"
        print(f"   {test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! Parser system is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))