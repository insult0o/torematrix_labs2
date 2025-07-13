"""
TORE Matrix Labs Parser Framework

A unified document parsing framework that provides multi-strategy parsing,
element classification, and quality validation for various document formats.
"""

from .base_parser import (
    BaseDocumentParser,
    BaseElementParser,
    ParseResult,
    ParserConfiguration,
    ParsingStrategy
)
from .document_parser_factory import DocumentParserFactory

__all__ = [
    'BaseDocumentParser',
    'BaseElementParser',
    'ParseResult',
    'ParserConfiguration',
    'ParsingStrategy',
    'DocumentParserFactory'
]

__version__ = '1.0.0'