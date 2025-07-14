"""
Format handlers for Agent 4 - File Format Support & Testing.

This module provides comprehensive format-specific handlers for all supported document types.
"""

# Format handlers
from .pdf_handler import PDFHandler, PDFFeatures
from .office_handler import OfficeHandler, OfficeFeatures  
from .web_handler import WebHandler, WebFeatures
from .email_handler import EmailHandler, EmailFeatures
from .text_handler import TextHandler, TextFeatures

__all__ = [
    'PDFHandler', 'PDFFeatures',
    'OfficeHandler', 'OfficeFeatures', 
    'WebHandler', 'WebFeatures',
    'EmailHandler', 'EmailFeatures',
    'TextHandler', 'TextFeatures'
]