from pathlib import Path
from PyPDF2 import PdfReader

from .pdf_parser_base import PDFParserBase, ParseResult

class PyPDF2Parser(PDFParserBase):
    def parse(self, file_path: Path) -> ParseResult:
        reader = PdfReader(file_path)
        pages = []
        
        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)
            
        # PyPDF2 provides basic metadata about images and forms
        has_images = any('/XObject' in page for page in reader.pages)
        has_forms = any('/AcroForm' in page for page in reader.pages)
        
        return ParseResult(
            text="\n\n".join(pages),
            confidence=0.7,  # PyPDF2 is basic but reliable
            page_count=len(reader.pages),
            has_tables=False,  # PyPDF2 doesn't detect tables
            has_forms=has_forms,
            has_images=has_images,
            pages=pages
        )

    def get_supported_features(self) -> List[str]:
        return [
            "text_extraction",
            "basic_metadata",
            "form_detection",
            "image_presence_detection",
            "simple_pdf_operations"  # merge, split, rotate etc.
        ]