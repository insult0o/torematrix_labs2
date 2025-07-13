from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .coordinates import Coordinates

@dataclass(frozen=True)
class ElementMetadata:
    coordinates: Optional[Coordinates] = None
    confidence: float = 1.0
    detection_method: str = "default"
    page_number: Optional[int] = None
    languages: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize metadata to dictionary"""
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
        """Deserialize metadata from dictionary"""
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