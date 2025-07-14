"""
PDF.js Integration Package

This package provides PDF.js integration for high-performance PDF viewing
and processing in TORE Matrix Labs V3.

Agent 1 Foundation:
- Core PDF viewer with Qt integration
- Basic navigation and zoom controls
- PDF loading and error handling

Future Agent Integrations:
- Agent 2: Qt-JavaScript bridge communication
- Agent 3: Performance optimization and caching
- Agent 4: Advanced features and UI integration
"""

from .exceptions import PDFIntegrationError, PDFRenderError

# Import viewer components only when needed (requires PyQt6)
try:
    from .viewer import PDFViewer, PDFDocument, PDFLoadError
    _VIEWER_AVAILABLE = True
except ImportError:
    _VIEWER_AVAILABLE = False
    PDFViewer = None
    PDFDocument = None
    PDFLoadError = None

__all__ = [
    'PDFViewer',
    'PDFDocument', 
    'PDFLoadError',
    'PDFIntegrationError',
    'PDFRenderError'
]

__version__ = "1.0.0"
__author__ = "TORE Matrix Labs - Agent 1"