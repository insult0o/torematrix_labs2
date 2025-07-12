from pathlib import Path
from typing import Dict, Optional
import logging

from .pdf_parser_base import PDFParserBase, ParseResult
from .parser_selector import ParserSelector
from .pdfplumber_parser import PDFPlumberParser
from .pymupdf_parser import PyMuPDFParser
from .pdfminer_parser import PDFMinerParser
from .pypdf2_parser import PyPDF2Parser
from .parser_cache import PDFParserCache, CacheConfig

logger = logging.getLogger(__name__)

class PDFParserManager:
    def __init__(self, cache_config: CacheConfig = None):
        self.selector = ParserSelector()
        self.parsers: Dict[str, PDFParserBase] = {
            'pdfplumber': PDFPlumberParser(),
            'pymupdf': PyMuPDFParser(),
            'pdfminer': PDFMinerParser(),
            'pypdf2': PyPDF2Parser()
        }
        self.cache = PDFParserCache(cache_config)
        
    def parse(self, file_path: Path) -> Optional[ParseResult]:
        """Parse PDF with fallback using multiple parsers.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            ParseResult from best parser, or None if all parsers fail
        """
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
            
        # Get ordered list of parsers to try
        parser_names = self.selector.select_parsers(file_path)
        
        results: Dict[str, ParseResult] = {}
        errors: Dict[str, Exception] = {}
        
        # Try each parser in order
        for parser_name in parser_names:
            parser = self.parsers[parser_name]
            try:
                # Use cache wrapper around parser
                result = self.cache.get_or_parse(
                    file_path,
                    parser_name,
                    parser.parse
                )
                results[parser_name] = result
                
                # If high confidence result, return early
                if result.confidence > 0.9:
                    logger.info(f"Got high confidence result from {parser_name}")
                    return result
                    
            except Exception as e:
                logger.warning(f"Parser {parser_name} failed: {str(e)}")
                errors[parser_name] = e
                continue
                
        if not results:
            logger.error("All parsers failed!")
            for parser_name, error in errors.items():
                logger.error(f"{parser_name} error: {str(error)}")
            return None
            
        # If we get here, use result with highest confidence
        best_result = max(results.items(), key=lambda x: x[1].confidence)
        logger.info(f"Using result from {best_result[0]}")
        return best_result[1]
        
    def merge_results(self, results: Dict[str, ParseResult]) -> ParseResult:
        """Merge results from multiple parsers intelligently."""
        if not results:
            raise ValueError("No results to merge")
            
        # Use text from highest confidence parser
        best_result = max(results.items(), key=lambda x: x[1].confidence)
        merged = best_result[1]
        
        # Merge feature detection results using OR
        merged.has_tables = any(r.has_tables for r in results.values())
        merged.has_forms = any(r.has_forms for r in results.values())
        merged.has_images = any(r.has_images for r in results.values())
        
        # Use max page count to handle partial extractions
        merged.page_count = max(r.page_count for r in results.values())
        
        # Average the confidences
        merged.confidence = sum(r.confidence for r in results.values()) / len(results)
        
        return merged