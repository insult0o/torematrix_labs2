from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

@dataclass
class ParseResult:
    text: str  
    confidence: float
    page_count: int
    has_tables: bool
    has_forms: bool
    has_images: bool
    pages: List[str]  # Text content per page

class PDFParserBase(ABC):
    @abstractmethod
    def parse(self, file_path: Path) -> ParseResult:
        """Parse a PDF file and return structured content.
        
        Args:
            file_path: Path to the PDF file

        Returns:
            ParseResult containing extracted content and metadata
            
        Raises:
            FileNotFoundError: If file does not exist
            PermissionError: If file cannot be accessed
            RuntimeError: For parser-specific errors
        """
        pass

    @abstractmethod
    def get_supported_features(self) -> List[str]:
        """Return list of supported parsing features."""
        pass