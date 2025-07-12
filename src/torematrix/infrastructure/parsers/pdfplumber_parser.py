from pathlib import Path
import pdfplumber

from .pdf_parser_base import PDFParserBase, ParseResult

class PDFPlumberParser(PDFParserBase):
    def parse(self, file_path: Path) -> ParseResult:
        with pdfplumber.open(file_path) as pdf:
            pages = []
            has_tables = False
            has_forms = False
            has_images = False
            
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages.append(text)
                
                if not has_tables and page.find_tables():
                    has_tables = True
                    
                if not has_forms and page.form_fields:
                    has_forms = True
                    
                if not has_images and page.images:
                    has_images = True

            return ParseResult(
                text="\n\n".join(pages),
                confidence=0.8,  # PDFPlumber generally reliable
                page_count=len(pdf.pages),
                has_tables=has_tables,
                has_forms=has_forms,
                has_images=has_images,
                pages=pages
            )

    def get_supported_features(self) -> List[str]:
        return [
            "text_extraction",
            "table_detection",
            "form_detection",
            "image_detection",
            "layout_preservation"
        ]