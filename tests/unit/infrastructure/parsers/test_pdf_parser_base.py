import pytest
from pathlib import Path
from torematrix.infrastructure.parsers.pdf_parser_base import PDFParserBase, ParseResult

class TestParserBase(PDFParserBase):
    def parse(self, file_path: Path) -> ParseResult:
        return ParseResult(
            text="test content",
            confidence=1.0,
            page_count=1,
            has_tables=False,
            has_forms=False,
            has_images=False,
            pages=["test content"]
        )
        
    def get_supported_features(self) -> List[str]:
        return ["text_extraction"]

def test_parse_result_creation():
    result = ParseResult(
        text="test",
        confidence=0.8,
        page_count=1,
        has_tables=True,
        has_forms=False,
        has_images=True,
        pages=["test"]
    )
    
    assert result.text == "test"
    assert result.confidence == 0.8
    assert result.page_count == 1
    assert result.has_tables is True
    assert result.has_forms is False
    assert result.has_images is True
    assert result.pages == ["test"]
    
def test_base_parser_interface():
    parser = TestParserBase()
    result = parser.parse(Path("test.pdf"))
    
    assert isinstance(result, ParseResult)
    assert result.text == "test content"
    assert result.confidence == 1.0
    
    features = parser.get_supported_features()
    assert isinstance(features, list)
    assert "text_extraction" in features