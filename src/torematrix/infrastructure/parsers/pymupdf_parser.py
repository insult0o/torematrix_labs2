from pathlib import Path
import fitz  # PyMuPDF

from .pdf_parser_base import PDFParserBase, ParseResult

class PyMuPDFParser(PDFParserBase):
    def parse(self, file_path: Path) -> ParseResult:
        doc = fitz.open(file_path)
        pages = []
        has_tables = False
        has_forms = False
        has_images = False
        
        try:
            for page in doc:
                text = page.get_text()
                pages.append(text)
                
                if not has_tables and page.get_drawings():
                    # PyMuPDF doesn't have direct table detection
                    # Use drawings as potential table indicators
                    has_tables = True
                    
                if not has_forms and page.annots():
                    has_forms = True
                    
                if not has_images:
                    images = page.get_images()
                    if images:
                        has_images = True

            return ParseResult(
                text="\n\n".join(pages),
                confidence=0.9,  # PyMuPDF is very reliable
                page_count=len(doc),
                has_tables=has_tables,
                has_forms=has_forms,
                has_images=has_images,
                pages=pages
            )
        finally:
            doc.close()

    def get_supported_features(self) -> List[str]:
        return [
            "text_extraction",
            "image_extraction",
            "form_annotation_detection",
            "vector_graphics", 
            "fast_processing"
        ]