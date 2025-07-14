from dataclasses import dataclass
from typing import List, Optional, Tuple

@dataclass(frozen=True)
class Coordinates:
    layout_bbox: Optional[Tuple[float, float, float, float]] = None
    text_bbox: Optional[Tuple[float, float, float, float]] = None
    points: Optional[List[Tuple[float, float]]] = None
    system: str = "pixel"  # pixel, point, normalized