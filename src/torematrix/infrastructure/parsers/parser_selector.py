from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Type

from .pdf_parser_base import PDFParserBase
from .pdfplumber_parser import PDFPlumberParser
from .pymupdf_parser import PyMuPDFParser
from .pdfminer_parser import PDFMinerParser
from .pypdf2_parser import PyPDF2Parser

@dataclass
class DocumentProfile:
    is_scanned: bool
    has_tables: bool
    has_forms: bool
    has_images: bool
    is_complex_layout: bool
    file_size_mb: float

class ParserSelector:
    def __init__(self):
        self.parsers: Dict[str, Type[PDFParserBase]] = {
            'pdfplumber': PDFPlumberParser,
            'pymupdf': PyMuPDFParser,
            'pdfminer': PDFMinerParser,
            'pypdf2': PyPDF2Parser
        }
        
    def select_parsers(self, file_path: Path) -> List[str]:
        """Select optimal parsers based on document characteristics.
        
        Returns ordered list of parser names to try.
        """
        profile = self._analyze_document(file_path)
        selected_parsers = []
        
        if profile.has_tables:
            selected_parsers.append('pdfplumber')  # Best for tables
            
        if profile.has_images or profile.file_size_mb > 10:
            selected_parsers.append('pymupdf')  # Fast and good with images
            
        if profile.is_complex_layout:
            selected_parsers.append('pdfminer')  # Good layout analysis
            
        # Always include PyPDF2 as fallback
        if 'pypdf2' not in selected_parsers:
            selected_parsers.append('pypdf2')
            
        # Ensure we haven't duplicated any parsers
        return list(dict.fromkeys(selected_parsers))
    
    def _analyze_document(self, file_path: Path) -> DocumentProfile:
        """Analyze document to determine characteristics."""
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        
        # Use PyMuPDF for quick analysis since it's fastest
        doc = None
        try:
            import fitz
            doc = fitz.open(file_path)
            first_page = doc[0]
            
            # Check for tables (look for grid-like lines)
            has_tables = bool(first_page.get_drawings())
            
            # Check for forms
            has_forms = bool(first_page.annots())
            
            # Check for images
            has_images = bool(first_page.get_images())
            
            # Check if scanned (high image area, low text)
            text = first_page.get_text()
            is_scanned = len(text.strip()) < 100 and has_images
            
            # Complex layout if multiple blocks or columns
            blocks = first_page.get_text("blocks")
            is_complex_layout = len(blocks) > 5
            
            return DocumentProfile(
                is_scanned=is_scanned,
                has_tables=has_tables,
                has_forms=has_forms,
                has_images=has_images,
                is_complex_layout=is_complex_layout,
                file_size_mb=file_size_mb
            )
        finally:
            if doc:
                doc.close()