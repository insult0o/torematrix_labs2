import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from torematrix.infrastructure.parsers.pdf_parser_manager import PDFParserManager
from torematrix.infrastructure.parsers.pdf_parser_base import ParseResult

@pytest.fixture
def parser_manager():
    return PDFParserManager()

def test_parse_success_high_confidence(parser_manager):
    mock_file_path = Path("test.pdf")
    mock_file_path.exists = lambda: True
    
    # Mock high confidence result from first parser
    high_confidence_result = ParseResult(
        text="high confidence text",
        confidence=0.95,
        page_count=1,
        has_tables=True,
        has_forms=False,
        has_images=False,
        pages=["high confidence text"]
    )
    
    with patch.object(parser_manager.selector, 'select_parsers') as mock_select:
        mock_select.return_value = ['pdfplumber', 'pymupdf']
        
        with patch.object(parser_manager.cache, 'get_or_parse') as mock_parse:
            mock_parse.return_value = high_confidence_result
            
            result = parser_manager.parse(mock_file_path)
            
            assert result == high_confidence_result
            assert mock_parse.call_count == 1  # Should return early

def test_parse_success_low_confidence(parser_manager):
    mock_file_path = Path("test.pdf")
    mock_file_path.exists = lambda: True
    
    # Mock results from multiple parsers
    results = [
        ParseResult(
            text="low confidence text 1",
            confidence=0.7,
            page_count=1,
            has_tables=True,
            has_forms=False,
            has_images=False,
            pages=["low confidence text 1"]
        ),
        ParseResult(
            text="low confidence text 2",
            confidence=0.8,
            page_count=1,
            has_tables=False,
            has_forms=True,
            has_images=False,
            pages=["low confidence text 2"]
        )
    ]
    
    with patch.object(parser_manager.selector, 'select_parsers') as mock_select:
        mock_select.return_value = ['pdfplumber', 'pymupdf']
        
        with patch.object(parser_manager.cache, 'get_or_parse') as mock_parse:
            mock_parse.side_effect = results
            
            result = parser_manager.parse(mock_file_path)
            
            assert result == results[1]  # Should use highest confidence result
            assert mock_parse.call_count == 2  # Should try both parsers

def test_parse_all_parsers_fail(parser_manager):
    mock_file_path = Path("test.pdf")
    mock_file_path.exists = lambda: True
    
    with patch.object(parser_manager.selector, 'select_parsers') as mock_select:
        mock_select.return_value = ['pdfplumber', 'pymupdf']
        
        with patch.object(parser_manager.cache, 'get_or_parse') as mock_parse:
            mock_parse.side_effect = Exception("Parser failed")
            
            result = parser_manager.parse(mock_file_path)
            
            assert result is None
            assert mock_parse.call_count == 2  # Should try all parsers

def test_merge_results(parser_manager):
    results = {
        'parser1': ParseResult(
            text="text 1",
            confidence=0.7,
            page_count=1,
            has_tables=True,
            has_forms=False,
            has_images=False,
            pages=["text 1"]
        ),
        'parser2': ParseResult(
            text="text 2",
            confidence=0.8,
            page_count=2,
            has_tables=False,
            has_forms=True,
            has_images=True,
            pages=["text 2", "page 2"]
        )
    }
    
    merged = parser_manager.merge_results(results)
    
    assert merged.text == "text 2"  # Should use text from highest confidence
    assert merged.confidence == 0.75  # Average confidence
    assert merged.page_count == 2  # Max page count
    assert merged.has_tables is True  # OR of feature flags
    assert merged.has_forms is True
    assert merged.has_images is True