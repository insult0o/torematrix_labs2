"""
Temporary stub for ElementMetadata until Agent 2 implements it.

This allows Agent 1 to test the Element base class.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass(frozen=True)
class Coordinates:
    """Stub for coordinates."""
    layout_bbox: Optional[tuple] = None
    text_bbox: Optional[tuple] = None
    points: Optional[List[tuple]] = None
    system: str = "pixel"


@dataclass(frozen=True) 
class ElementMetadata:
    """Stub for element metadata."""
    coordinates: Optional[Coordinates] = None
    confidence: float = 1.0
    detection_method: str = "default"
    page_number: Optional[int] = None
    languages: List[str] = None
    custom_fields: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.languages is None:
            object.__setattr__(self, 'languages', [])
        if self.custom_fields is None:
            object.__setattr__(self, 'custom_fields', {})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'coordinates': self.coordinates.__dict__ if self.coordinates else None,
            'confidence': self.confidence,
            'detection_method': self.detection_method,
            'page_number': self.page_number,
            'languages': self.languages,
            'custom_fields': self.custom_fields
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ElementMetadata':
        """Create from dictionary."""
        coordinates = None
        if data.get('coordinates'):
            coord_data = data['coordinates']
            coordinates = Coordinates(
                layout_bbox=coord_data.get('layout_bbox'),
                text_bbox=coord_data.get('text_bbox'),
                points=coord_data.get('points'),
                system=coord_data.get('system', 'pixel')
            )
        
        return cls(
            coordinates=coordinates,
            confidence=data.get('confidence', 1.0),
            detection_method=data.get('detection_method', 'default'),
            page_number=data.get('page_number'),
            languages=data.get('languages', []),
            custom_fields=data.get('custom_fields', {})
        )