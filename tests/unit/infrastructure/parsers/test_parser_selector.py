import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from torematrix.infrastructure.parsers.parser_selector import ParserSelector, DocumentProfile

@pytest.fixture
def parser_selector():
    return ParserSelector()

def test_select_parsers_for_table_document(parser_selector):
    with patch('fitz.open') as mock_open:
        mock_doc = Mock()
        mock_doc.__len__ = lambda x: 1
        mock_page = Mock()
        mock_page.get_drawings.return_value = True  # Has tables
        mock_page.annots.return_value = False  # No forms
        mock_page.get_images.return_value = False  # No images
        mock_page.get_text.return_value = "Sample text"
        mock_page.get_text_blocks.return_value = ["block1"]
        mock_doc.__getitem__.return_value = mock_page
        mock_open.return_value = mock_doc
        
        parsers = parser_selector.select_parsers(Path("test.pdf"))
        
        assert 'pdfplumber' in parsers  # Should include pdfplumber for tables
        assert 'pymupdf' in parsers  # Should include fast parser
        assert 'pypdf2' in parsers  # Should include fallback

def test_select_parsers_for_image_heavy_document(parser_selector):
    with patch('fitz.open') as mock_open:
        mock_doc = Mock()
        mock_doc.__len__ = lambda x: 1
        mock_page = Mock()
        mock_page.get_drawings.return_value = False
        mock_page.annots.return_value = False
        mock_page.get_images.return_value = True  # Has images
        mock_page.get_text.return_value = "Sample text"
        mock_page.get_text_blocks.return_value = ["block1"]
        mock_doc.__getitem__.return_value = mock_page
        mock_open.return_value = mock_doc
        
        parsers = parser_selector.select_parsers(Path("test.pdf"))
        
        assert 'pymupdf' in parsers  # Should prioritize PyMuPDF for images
        assert 'pypdf2' in parsers  # Should include fallback

def test_select_parsers_for_complex_layout(parser_selector):
    with patch('fitz.open') as mock_open:
        mock_doc = Mock()
        mock_doc.__len__ = lambda x: 1
        mock_page = Mock()
        mock_page.get_drawings.return_value = False
        mock_page.annots.return_value = False
        mock_page.get_images.return_value = False
        mock_page.get_text.return_value = "Sample text"
        mock_page.get_text_blocks.return_value = ["block1", "block2", "block3", "block4", "block5", "block6"]  # Complex layout
        mock_doc.__getitem__.return_value = mock_page
        mock_open.return_value = mock_doc
        
        parsers = parser_selector.select_parsers(Path("test.pdf"))
        
        assert 'pdfminer' in parsers  # Should include pdfminer for complex layouts
        assert 'pypdf2' in parsers  # Should include fallback

def test_analyze_document(parser_selector):
    with patch('fitz.open') as mock_open:
        mock_doc = Mock()
        mock_doc.__len__ = lambda x: 1
        mock_page = Mock()
        mock_page.get_drawings.return_value = True
        mock_page.annots.return_value = True
        mock_page.get_images.return_value = True
        mock_page.get_text.return_value = "Sample text"
        mock_page.get_text_blocks.return_value = ["block1", "block2", "block3"]
        mock_doc.__getitem__.return_value = mock_page
        mock_open.return_value = mock_doc
        
        profile = parser_selector._analyze_document(Path("test.pdf"))
        
        assert isinstance(profile, DocumentProfile)
        assert profile.has_tables is True
        assert profile.has_forms is True
        assert profile.has_images is True
        assert profile.is_complex_layout is False  # Less than 5 blocks