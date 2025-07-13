# TORE Matrix Labs Parser Framework

## Overview

The TORE Matrix Labs Parser Framework provides a unified, extensible architecture for parsing various document formats. It supports multiple parsing strategies, element classification, and quality validation while integrating seamlessly with the existing document processing pipeline.

## Architecture

### Core Components

1. **Base Classes**
   - `BaseDocumentParser`: Abstract base class for document parsers
   - `BaseElementParser`: Abstract base class for element-specific parsers
   - `ParsedElement`: Base class for all parsed document elements

2. **Element Types**
   - Text elements (paragraphs, headings, lists)
   - Table elements with HTML rendering
   - Image elements with base64 encoding
   - Complex elements (diagrams, formulas, code blocks)

3. **Parser Factory**
   - `DocumentParserFactory`: Creates appropriate parsers based on file type
   - Strategy pattern for parser selection
   - Extensible registration system

4. **Quality & Validation**
   - Element-level confidence scoring
   - Document-level quality assessment
   - Validation framework for parsed content

## Quick Start

### Basic Usage

```python
from tore_matrix_labs.core.parsers import (
    DocumentParserFactory,
    ParserConfiguration,
    ParsingStrategy
)

# Create parser configuration
config = ParserConfiguration(
    strategy=ParsingStrategy.AUTO,
    enable_ocr=True,
    extract_tables=True,
    extract_images=True
)

# Create parser for document
parser = DocumentParserFactory.create_parser(
    file_path=Path("document.pdf"),
    config=config
)

# Parse document
result = parser.parse(Path("document.pdf"))

if result.success:
    print(f"Parsed {len(result.elements)} elements")
    print(f"Quality score: {result.quality.overall_score}")
    
    # Access elements by type
    tables = result.get_elements_by_type("table")
    for table in tables:
        print(table.to_html())
```

### Integration with Existing Pipeline

```python
from tore_matrix_labs.core.parsers.parser_integration import EnhancedDocumentProcessor

# Enhance existing processor
enhanced_processor = EnhancedDocumentProcessor(
    base_processor=existing_processor,
    parser_config=config
)

# Process document with parser framework
results = enhanced_processor.process_document("document.pdf")
```

## Creating Custom Parsers

### Implementing a Document Parser

```python
from tore_matrix_labs.core.parsers import BaseDocumentParser, ParseResult, ParsingStrategy

class CustomPDFParser(BaseDocumentParser):
    def parse(self, file_path: Path) -> ParseResult:
        # Validate file
        is_valid, error = self.validate_file(file_path)
        if not is_valid:
            result = ParseResult(success=False)
            result.add_error(error)
            return result
        
        # Extract metadata
        metadata = self.extract_metadata(file_path)
        
        # Parse document content
        elements = []
        try:
            # Your parsing logic here
            elements = self._parse_pdf_content(file_path)
            
            # Calculate quality
            quality = self._assess_quality(elements)
            
            return ParseResult(
                success=True,
                elements=elements,
                metadata=metadata,
                quality=quality,
                strategy_used=self.get_strategy()
            )
        except Exception as e:
            result = ParseResult(success=False)
            result.add_error(str(e))
            return result
    
    def supports_format(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.pdf'
    
    def get_strategy(self) -> ParsingStrategy:
        return ParsingStrategy.PYMUPDF

# Register parser
DocumentParserFactory.register_parser(ParsingStrategy.PYMUPDF, CustomPDFParser)
```

### Implementing an Element Parser

```python
from tore_matrix_labs.core.parsers import BaseElementParser
from tore_matrix_labs.core.parsers.elements import DiagramElement

class MermaidDiagramParser(BaseElementParser):
    def parse_element(self, raw_data: str) -> Optional[DiagramElement]:
        # Parse Mermaid diagram syntax
        if not self._is_mermaid_diagram(raw_data):
            return None
        
        diagram_data = self._parse_mermaid_syntax(raw_data)
        
        return DiagramElement(
            diagram_type="mermaid",
            data=diagram_data,
            title=diagram_data.get('title'),
            description="Mermaid diagram"
        )
    
    def supports_element_type(self, element_type: str) -> bool:
        return element_type == "mermaid_diagram"
```

## Element Types Reference

### Text Elements

- **TextElement**: Generic text content
- **HeadingElement**: Headings with level (H1-H6)
- **ParagraphElement**: Paragraph text with sentence splitting
- **ListElement**: Ordered/unordered lists

### Table Elements

- **TableElement**: Complete table with rows and cells
- **TableRow**: Table row container
- **TableCell**: Individual table cell with spans

### Image Elements

- **ImageElement**: Image with binary data or file reference
- **FigureElement**: Image with caption and numbering

### Complex Elements

- **DiagramElement**: Structured diagram data
- **FormulaElement**: Mathematical formulas (LaTeX, MathML)
- **CodeElement**: Code blocks with syntax highlighting info

## Configuration Options

```python
@dataclass
class ParserConfiguration:
    strategy: ParsingStrategy = ParsingStrategy.AUTO
    enable_ocr: bool = True
    ocr_languages: List[str] = ["eng"]
    extract_tables: bool = True
    extract_images: bool = True
    extract_metadata: bool = True
    preserve_formatting: bool = True
    chunk_size: int = 1000
    overlap_size: int = 200
    quality_threshold: float = 0.8
    timeout_seconds: Optional[int] = None
    custom_options: Dict[str, Any] = {}
```

## Quality Assessment

The framework provides comprehensive quality metrics:

```python
@dataclass
class ParseQuality:
    overall_score: float
    text_extraction_score: float
    structure_preservation_score: float
    element_detection_score: float
    metadata_completeness: float
    confidence_distribution: Dict[ElementConfidence, int]
    issues_found: List[Dict[str, Any]]
    processing_time: float
```

## Serialization

All elements support JSON serialization:

```python
# Serialize element
element_dict = element.to_dict()
json_str = element.to_json()

# Deserialize element
restored_element = TextElement.from_dict(element_dict)
```

## Error Handling

The framework provides detailed error information:

```python
result = parser.parse(file_path)

if not result.success:
    for error in result.errors:
        print(f"Error: {error}")
    
    for warning in result.warnings:
        print(f"Warning: {warning}")
```

## Performance Considerations

1. **Caching**: Parser results can be cached using element IDs
2. **Streaming**: Large documents can be parsed incrementally
3. **Parallel Processing**: Elements can be parsed in parallel
4. **Memory Management**: Images and large content are handled efficiently

## Testing

Run the comprehensive test suite:

```bash
python -m pytest tests/test_parser_framework.py -v
```

## Future Enhancements

- ML-based element classification
- Advanced table structure detection
- Multi-modal diagram understanding
- Real-time collaborative parsing
- Cloud-based parser services