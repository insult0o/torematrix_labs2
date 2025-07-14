"""
Test configuration for PDF integration tests.
"""

import pytest
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, MagicMock

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineCore import QWebEnginePage


@pytest.fixture(scope="session")
def app() -> Generator[QApplication, None, None]:
    """Create QApplication for testing."""
    application = QApplication.instance()
    if not application:
        application = QApplication([])
    yield application


@pytest.fixture
def temp_pdf_path() -> Generator[Path, None, None]:
    """Create temporary PDF file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        # Create minimal PDF content
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
299
%%EOF"""
        f.write(pdf_content)
        f.flush()
        
        temp_path = Path(f.name)
        yield temp_path
        
        # Cleanup
        temp_path.unlink(missing_ok=True)


@pytest.fixture
def mock_web_page() -> Mock:
    """Create mock QWebEnginePage for testing."""
    page = Mock(spec=QWebEnginePage)
    page.runJavaScript = Mock()
    page.loadFinished = Mock()
    page.loadProgress = Mock()
    page.url = Mock(return_value=QUrl("file:///test/viewer.html"))
    return page


@pytest.fixture
def mock_js_result() -> dict:
    """Create mock JavaScript result for testing."""
    return {
        'success': True,
        'pages': 5,
        'metadata': {
            'title': 'Test PDF',
            'author': 'Test Author',
            'subject': 'Test Subject',
            'creator': 'Test Creator',
            'producer': 'Test Producer',
            'creationDate': '2023-01-01',
            'modificationDate': '2023-01-02',
            'pages': 5
        }
    }


@pytest.fixture
def sample_pdf_metadata() -> dict:
    """Create sample PDF metadata for testing."""
    return {
        'title': 'Sample PDF Document',
        'author': 'Test Author',
        'subject': 'Test Subject',
        'creator': 'Test Creator',
        'producer': 'Test Producer',
        'creationDate': '2023-01-01T00:00:00Z',
        'modificationDate': '2023-01-02T00:00:00Z',
        'pages': 10
    }