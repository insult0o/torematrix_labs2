#!/usr/bin/env python3
"""
Test Suite for TORE Matrix Labs V2

This comprehensive testing framework ensures bug-free operation of all
components in the refactored codebase.

Test Categories:
- Unit Tests: Individual component testing
- Integration Tests: Component interaction testing
- UI Tests: User interface testing with PyQt5
- Performance Tests: Load and stress testing

Test Framework Features:
- pytest-based testing with fixtures
- Mocking for external dependencies
- Performance benchmarking
- Coverage reporting
- Continuous integration support
- Bug regression testing
"""

import logging
import sys
from pathlib import Path

# Add the parent directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure test logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Test configuration
TEST_CONFIG = {
    "use_real_files": False,  # Use mock files by default
    "performance_tests": True,
    "ui_tests": True,
    "integration_tests": True,
    "coverage_threshold": 90,  # Minimum coverage percentage
    "test_timeout": 300,  # 5 minutes max per test
}

__version__ = "2.0.0"
__author__ = "TORE Matrix Labs Team"