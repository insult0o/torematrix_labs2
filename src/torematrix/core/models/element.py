"""Core element and document models."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Element:
    """Individual document element."""
    id: str
    type: str
    text: str
    bbox: Optional[List[float]] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.bbox is None:
            self.bbox = []


@dataclass
class ProcessedDocument:
    """Processed document with elements and metadata."""
    id: str
    elements: List[Element]
    metadata: Dict[str, Any] = None
    processing_stats: Dict[str, Any] = None
    relationships: Optional[List[Dict[str, Any]]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.processing_stats is None:
            self.processing_stats = {}
        if self.relationships is None:
            self.relationships = []