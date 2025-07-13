from pathlib import Path
from io import StringIO
from typing import List

from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage

from .pdf_parser_base import PDFParserBase, ParseResult

class PDFMinerParser(PDFParserBase):
    def parse(self, file_path: Path) -> ParseResult:
        pages = []
        rsrcmgr = PDFResourceManager()
        
        with open(file_path, 'rb') as file:
            for page in PDFPage.get_pages(file):
                output = StringIO()
                device = TextConverter(rsrcmgr, output, laparams=LAParams())
                interpreter = PDFPageInterpreter(rsrcmgr, device)
                interpreter.process_page(page)
                text = output.getvalue()
                pages.append(text)
                device.close()
                output.close()

        # PDFMiner doesn't provide direct table/form/image detection
        # Use heuristics based on layout analysis
        full_text = "\n\n".join(pages)
        has_tables = "│" in full_text or "+" in full_text  # Common table markers
        has_forms = "□" in full_text or "⬚" in full_text  # Common form markers
        has_images = False  # PDFMiner not optimized for image detection

        return ParseResult(
            text=full_text,
            confidence=0.85,  # PDFMiner has good text positioning
            page_count=len(pages),
            has_tables=has_tables,
            has_forms=has_forms,
            has_images=has_images,
            pages=pages
        )

    def get_supported_features(self) -> List[str]:
        return [
            "text_extraction",
            "character_positioning",
            "font_information",
            "layout_analysis",
            "text_direction_detection"
        ]