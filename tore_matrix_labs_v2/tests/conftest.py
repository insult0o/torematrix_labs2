#!/usr/bin/env python3
"""
Pytest configuration and fixtures for TORE Matrix Labs V2 tests.

This module provides shared fixtures and configuration for all tests,
ensuring consistent test environments and reducing code duplication.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock
import json

# Import the modules we're testing
from core.services.coordinate_mapping_service import CoordinateMappingService
from core.services.text_extraction_service import TextExtractionService
from core.services.validation_service import ValidationService
from core.processors.unified_document_processor import UnifiedDocumentProcessor
from core.processors.quality_assessment_engine import QualityAssessmentEngine
from core.storage.repository_base import StorageConfig, StorageBackend
from core.models.unified_document_model import UnifiedDocument, DocumentStatus
from ui.services.event_bus import EventBus
from ui.services.ui_state_manager import UIStateManager


@pytest.fixture(scope="session")
def test_data_dir():
    """Create a temporary directory for test data."""
    temp_dir = tempfile.mkdtemp(prefix="tore_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_pdf_path(test_data_dir):
    """Create a sample PDF file for testing."""
    pdf_path = test_data_dir / "sample.pdf"
    
    # Create a minimal PDF using PyMuPDF
    try:
        import fitz
        doc = fitz.open()  # New empty document
        page = doc.new_page()
        
        # Add some text
        text = "This is a test document.\nIt has multiple lines.\n\nAnd some tables:\nColumn1\tColumn2\nValue1\tValue2"
        page.insert_text((72, 72), text)
        
        doc.save(str(pdf_path))
        doc.close()
        
    except ImportError:
        # Fallback: create a dummy file
        with open(pdf_path, 'wb') as f:
            f.write(b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n%%EOF')
    
    return pdf_path


@pytest.fixture
def sample_document(sample_pdf_path):
    """Create a sample UnifiedDocument for testing."""
    return UnifiedDocument(
        id="test_doc_001",
        file_path=str(sample_pdf_path),
        file_name="sample.pdf",
        status=DocumentStatus.LOADED
    )


@pytest.fixture
def storage_config(test_data_dir):
    """Create a test storage configuration."""
    return StorageConfig(
        backend=StorageBackend.JSON_FILE,
        database_path=test_data_dir / "test_db.json",
        enable_caching=True,
        cache_size=100
    )


@pytest.fixture
def mock_storage_config():
    """Create a mock storage configuration for unit tests."""
    config = Mock(spec=StorageConfig)
    config.backend = StorageBackend.JSON_FILE
    config.enable_caching = True
    config.cache_size = 100
    config.auto_commit = True
    return config


@pytest.fixture
def coordinate_service():
    """Create a CoordinateMappingService instance for testing."""
    return CoordinateMappingService()


@pytest.fixture
def text_extraction_service(coordinate_service):
    """Create a TextExtractionService instance for testing."""
    return TextExtractionService(coordinate_service)


@pytest.fixture
def validation_service(coordinate_service, text_extraction_service):
    """Create a ValidationService instance for testing."""
    return ValidationService(coordinate_service, text_extraction_service)


@pytest.fixture
def quality_engine():
    """Create a QualityAssessmentEngine instance for testing."""
    return QualityAssessmentEngine()


@pytest.fixture
def document_processor(coordinate_service, text_extraction_service, validation_service, quality_engine):
    """Create a UnifiedDocumentProcessor instance for testing."""
    return UnifiedDocumentProcessor(
        coordinate_service=coordinate_service,
        extraction_service=text_extraction_service,
        validation_service=validation_service,
        quality_engine=quality_engine
    )


@pytest.fixture
def event_bus():
    """Create an EventBus instance for testing."""
    return EventBus()


@pytest.fixture
def ui_state_manager(event_bus):
    """Create a UIStateManager instance for testing."""
    return UIStateManager(event_bus)


@pytest.fixture
def mock_pymupdf_document():
    """Create a mock PyMuPDF document for testing."""
    # Create mock document
    mock_doc = Mock()
    mock_doc.__len__ = Mock(return_value=2)  # 2 pages
    
    # Create mock pages
    mock_page1 = Mock()
    mock_page1.get_text.return_value = "This is page 1 content."
    mock_page1.get_text.return_value = {
        "blocks": [
            {
                "lines": [
                    {
                        "spans": [
                            {
                                "chars": [
                                    {"bbox": [10, 10, 20, 20], "c": "T"},
                                    {"bbox": [20, 10, 30, 20], "c": "h"},
                                    {"bbox": [30, 10, 40, 20], "c": "i"},
                                    {"bbox": [40, 10, 50, 20], "c": "s"},
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }
    mock_page1.rect.width = 612
    mock_page1.rect.height = 792
    
    mock_page2 = Mock()
    mock_page2.get_text.return_value = "This is page 2 content."
    mock_page2.rect.width = 612
    mock_page2.rect.height = 792
    
    # Set up page access
    mock_doc.__getitem__ = Mock(side_effect=[mock_page1, mock_page2])
    
    return mock_doc


@pytest.fixture
def sample_extraction_result():
    """Create a sample extraction result for testing."""
    from core.services.text_extraction_service import ExtractionResult
    
    result = ExtractionResult(
        text="This is extracted text.\nWith multiple lines.",
        character_count=42,
        word_count=7,
        extraction_method="pymupdf",
        extraction_confidence=0.85
    )
    
    # Add sample page data
    result.pages = [
        {
            "page": 1,
            "text": "This is extracted text.",
            "coordinates": {
                "0": {"bbox": [10, 10, 20, 20], "char": "T"},
                "1": {"bbox": [20, 10, 30, 20], "char": "h"},
                "2": {"bbox": [30, 10, 40, 20], "char": "i"},
                "3": {"bbox": [40, 10, 50, 20], "char": "s"},
            }
        },
        {
            "page": 2,
            "text": "With multiple lines.",
            "coordinates": {}
        }
    ]
    
    return result


@pytest.fixture
def sample_tore_data():
    """Create sample .tore file data for testing."""
    return {
        "name": "Test Project",
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "documents": [
            {
                "id": "doc_001",
                "name": "test_document.pdf",
                "path": "/path/to/test_document.pdf",
                "status": "processed",
                "visual_areas": {
                    "area_001": {
                        "id": "area_001",
                        "document_id": "doc_001",
                        "type": "IMAGE",
                        "page": 1,
                        "bbox": [100, 100, 200, 200],
                        "status": "validated",
                        "created_at": datetime.now().isoformat(),
                        "modified_at": datetime.now().isoformat()
                    },
                    "area_002": {
                        "id": "area_002",
                        "document_id": "doc_001",
                        "type": "TABLE",
                        "page": 1,
                        "bbox": [100, 300, 400, 500],
                        "status": "validated",
                        "created_at": datetime.now().isoformat(),
                        "modified_at": datetime.now().isoformat()
                    }
                }
            }
        ]
    }


@pytest.fixture
def sample_tore_file(test_data_dir, sample_tore_data):
    """Create a sample .tore file for testing."""
    tore_path = test_data_dir / "test_project.tore"
    
    with open(tore_path, 'w') as f:
        json.dump(sample_tore_data, f, indent=2)
    
    return tore_path


@pytest.fixture(autouse=True)
def clean_test_environment():
    """Clean up test environment before and after each test."""
    # Setup
    yield
    # Cleanup - any global cleanup needed


@pytest.fixture
def mock_qt_app():
    """Create a mock Qt application for UI testing."""
    try:
        from PyQt5.QtWidgets import QApplication
        import sys
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        yield app
        
        # Cleanup
        app.processEvents()
        
    except ImportError:
        # Mock Qt if not available
        mock_app = Mock()
        yield mock_app


@pytest.fixture
def performance_timer():
    """Timer fixture for performance testing."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


# Test markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "ui: mark test as a UI test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# Custom assertions
def assert_coordinates_equal(coord1, coord2, tolerance=0.1):
    """Assert that two coordinate objects are approximately equal."""
    assert abs(coord1.x - coord2.x) <= tolerance
    assert abs(coord1.y - coord2.y) <= tolerance
    assert abs(coord1.width - coord2.width) <= tolerance
    assert abs(coord1.height - coord2.height) <= tolerance


def assert_extraction_result_valid(result):
    """Assert that an extraction result is valid."""
    assert result is not None
    assert hasattr(result, 'text')
    assert hasattr(result, 'character_count')
    assert hasattr(result, 'word_count')
    assert hasattr(result, 'extraction_method')
    assert result.character_count >= 0
    assert result.word_count >= 0
    assert 0.0 <= result.extraction_confidence <= 1.0


# Test utilities
class MockFileSystem:
    """Mock file system for testing without real files."""
    
    def __init__(self):
        self.files = {}
    
    def create_file(self, path, content):
        """Create a mock file."""
        self.files[str(path)] = content
    
    def file_exists(self, path):
        """Check if mock file exists."""
        return str(path) in self.files
    
    def get_file_content(self, path):
        """Get mock file content."""
        return self.files.get(str(path))


@pytest.fixture
def mock_filesystem():
    """Create a mock file system for testing."""
    return MockFileSystem()