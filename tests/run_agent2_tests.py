#!/usr/bin/env python3
"""
Test runner for Agent 2 Element Selection & State Management tests.
"""
import sys
import os
import pytest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def run_agent2_tests():
    """Run all Agent 2 tests."""
    test_file = Path(__file__).parent / "unit/ui/viewer/test_agent2_integration.py"
    
    # Run tests with verbose output
    exit_code = pytest.main([
        str(test_file),
        "-v",
        "--tb=short",
        "--no-header",
        "--disable-warnings"
    ])
    
    return exit_code

if __name__ == "__main__":
    exit_code = run_agent2_tests()
    sys.exit(exit_code)