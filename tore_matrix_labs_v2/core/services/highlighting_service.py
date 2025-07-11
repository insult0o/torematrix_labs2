#!/usr/bin/env python3
"""
Highlighting Service for TORE Matrix Labs V2

Provides visual highlighting capabilities for PDF and text content.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class HighlightType(Enum):
    """Types of highlighting."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"


@dataclass
class Highlight:
    """A visual highlight."""
    coordinates: List[float]
    highlight_type: HighlightType
    text: str = ""
    description: str = ""


class HighlightingService:
    """Service for managing visual highlights."""
    
    def __init__(self):
        self.highlights: List[Highlight] = []
    
    def add_highlight(self, coordinates: List[float], highlight_type: HighlightType, 
                     text: str = "", description: str = "") -> str:
        """Add a highlight."""
        highlight = Highlight(coordinates, highlight_type, text, description)
        self.highlights.append(highlight)
        return f"highlight_{len(self.highlights)}"
    
    def clear_highlights(self):
        """Clear all highlights."""
        self.highlights.clear()
    
    def get_highlights(self) -> List[Highlight]:
        """Get all highlights."""
        return self.highlights.copy()