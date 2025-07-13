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