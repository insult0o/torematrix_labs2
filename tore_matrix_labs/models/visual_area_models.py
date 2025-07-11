"""
Visual Area Models for TORE Matrix Labs

Data structures for persistent visual area selection and management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Tuple, Dict, Any, Optional
from enum import Enum


class AreaType(Enum):
    """Types of visual areas that can be selected."""
    IMAGE = "IMAGE"
    TABLE = "TABLE"
    DIAGRAM = "DIAGRAM"
    TEXT = "TEXT"
    CUSTOM = "CUSTOM"


class AreaStatus(Enum):
    """Status of a visual area."""
    SELECTED = "selected"      # Just selected by user
    CONFIRMED = "confirmed"    # Confirmed by user
    SAVED = "saved"           # Saved to project
    MODIFIED = "modified"     # Modified after initial creation
    DELETED = "deleted"       # Marked for deletion


@dataclass
class VisualArea:
    """Enhanced area selection with visual representation and persistence."""
    
    # Core identification
    id: str
    document_id: str
    area_type: AreaType
    
    # Spatial information  
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2 in PDF coordinates
    page: int
    
    # Visual properties
    color: str = "#FF4444"  # RGB hex color based on type
    status: AreaStatus = AreaStatus.SELECTED
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    user_notes: str = ""
    
    # Visual rendering properties
    border_width: int = 2
    fill_opacity: float = 0.3
    border_glow: bool = True
    
    # Widget coordinates for UI interaction
    widget_rect: Optional[Tuple[int, int, int, int]] = None  # x, y, width, height
    
    @classmethod
    def from_area_data(cls, area_data: Dict[str, Any]) -> 'VisualArea':
        """Create VisualArea from area selection data."""
        area_type = AreaType(area_data.get('type', 'CUSTOM'))
        
        # Set color based on type
        color_map = {
            AreaType.IMAGE: "#FF4444",    # Red
            AreaType.TABLE: "#44FF44",    # Green  
            AreaType.DIAGRAM: "#4444FF",  # Blue
            AreaType.TEXT: "#FFFF44",     # Yellow
            AreaType.CUSTOM: "#FF44FF"    # Magenta
        }
        
        return cls(
            id=area_data.get('id', f"area_{datetime.now().timestamp()}"),
            document_id=area_data.get('document_id', 'unknown'),
            area_type=area_type,
            bbox=tuple(area_data.get('bbox', [0, 0, 100, 100])),
            page=area_data.get('page', 1),
            color=color_map.get(area_type, "#FF4444"),
            status=AreaStatus(area_data.get('status', 'selected')),
            created_at=datetime.fromisoformat(area_data.get('created_at', datetime.now().isoformat())),
            modified_at=datetime.fromisoformat(area_data.get('modified_at', datetime.now().isoformat())),
            user_notes=area_data.get('user_notes', ''),
            widget_rect=tuple(area_data['selection_rect']) if 'selection_rect' in area_data else None
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'id': self.id,
            'document_id': self.document_id,
            'type': self.area_type.value,
            'bbox': list(self.bbox),
            'page': self.page,
            'color': self.color,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'modified_at': self.modified_at.isoformat(),
            'user_notes': self.user_notes,
            'border_width': self.border_width,
            'fill_opacity': self.fill_opacity,
            'border_glow': self.border_glow,
            'widget_rect': list(self.widget_rect) if self.widget_rect else None
        }
    
    def update_bbox(self, new_bbox: Tuple[float, float, float, float]):
        """Update bbox and mark as modified."""
        self.bbox = new_bbox
        self.modified_at = datetime.now()
        self.status = AreaStatus.MODIFIED
    
    def update_widget_rect(self, new_rect: Tuple[int, int, int, int]):
        """Update widget coordinates."""
        self.widget_rect = new_rect
        self.modified_at = datetime.now()
    
    def confirm(self):
        """Mark area as confirmed by user."""
        self.status = AreaStatus.CONFIRMED
        self.modified_at = datetime.now()
    
    def save(self):
        """Mark area as saved."""
        self.status = AreaStatus.SAVED
        self.modified_at = datetime.now()
    
    def mark_for_deletion(self):
        """Mark area for deletion."""
        self.status = AreaStatus.DELETED
        self.modified_at = datetime.now()
    
    def is_point_inside(self, x: float, y: float) -> bool:
        """Check if point is inside the area bbox."""
        x1, y1, x2, y2 = self.bbox
        return x1 <= x <= x2 and y1 <= y <= y2
    
    def get_resize_handle_at(self, x: float, y: float, handle_size: float = 10) -> Optional[str]:
        """Get resize handle at given coordinates."""
        x1, y1, x2, y2 = self.bbox
        
        # Check corners first
        if abs(x - x1) <= handle_size and abs(y - y1) <= handle_size:
            return "top_left"
        elif abs(x - x2) <= handle_size and abs(y - y1) <= handle_size:
            return "top_right"
        elif abs(x - x1) <= handle_size and abs(y - y2) <= handle_size:
            return "bottom_left"
        elif abs(x - x2) <= handle_size and abs(y - y2) <= handle_size:
            return "bottom_right"
        
        # Check edges
        elif abs(x - x1) <= handle_size and y1 <= y <= y2:
            return "left"
        elif abs(x - x2) <= handle_size and y1 <= y <= y2:
            return "right"
        elif abs(y - y1) <= handle_size and x1 <= x <= x2:
            return "top"
        elif abs(y - y2) <= handle_size and x1 <= x <= x2:
            return "bottom"
        
        return None


@dataclass 
class AreaSelectionSession:
    """Manages a session of area selections for a document."""
    
    document_id: str
    areas: Dict[str, VisualArea] = field(default_factory=dict)
    active_area_id: Optional[str] = None
    session_id: str = field(default_factory=lambda: f"session_{datetime.now().timestamp()}")
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_area(self, area: VisualArea):
        """Add area to session."""
        self.areas[area.id] = area
        self.active_area_id = area.id
    
    def remove_area(self, area_id: str):
        """Remove area from session."""
        if area_id in self.areas:
            del self.areas[area_id]
            if self.active_area_id == area_id:
                self.active_area_id = None
    
    def get_active_area(self) -> Optional[VisualArea]:
        """Get currently active area."""
        if self.active_area_id and self.active_area_id in self.areas:
            return self.areas[self.active_area_id]
        return None
    
    def get_areas_for_page(self, page: int) -> Dict[str, VisualArea]:
        """Get all areas for a specific page."""
        return {aid: area for aid, area in self.areas.items() if area.page == page}
    
    def set_active_area(self, area_id: str):
        """Set active area by ID."""
        if area_id in self.areas:
            self.active_area_id = area_id
    
    def get_area_count(self) -> int:
        """Get total number of areas."""
        return len(self.areas)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            'document_id': self.document_id,
            'session_id': self.session_id,
            'created_at': self.created_at.isoformat(),
            'active_area_id': self.active_area_id,
            'areas': {aid: area.to_dict() for aid, area in self.areas.items()}
        }