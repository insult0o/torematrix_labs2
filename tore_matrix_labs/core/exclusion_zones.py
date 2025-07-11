#!/usr/bin/env python3
"""
Exclusion zones system for skipping manually validated areas during text extraction.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import fitz  # PyMuPDF
from dataclasses import dataclass

from ..models.manual_validation_models import ManualValidationSession, DocumentSnippet, SnippetType


@dataclass
class ExclusionZone:
    """Represents an area to exclude from text extraction."""
    page: int
    bbox: List[float]  # [x1, y1, x2, y2]
    zone_type: str  # IMAGE, TABLE, DIAGRAM
    snippet_id: str
    priority: int = 1  # Higher priority zones override lower ones
    
    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is within this exclusion zone."""
        return (self.bbox[0] <= x <= self.bbox[2] and 
                self.bbox[1] <= y <= self.bbox[3])
    
    def overlaps_with(self, other_bbox: List[float]) -> bool:
        """Check if this zone overlaps with another bounding box."""
        return not (self.bbox[2] < other_bbox[0] or  # Zone is to the left
                   self.bbox[0] > other_bbox[2] or  # Zone is to the right
                   self.bbox[3] < other_bbox[1] or  # Zone is above
                   self.bbox[1] > other_bbox[3])    # Zone is below
    
    def get_overlap_area(self, other_bbox: List[float]) -> float:
        """Calculate the area of overlap with another bounding box."""
        if not self.overlaps_with(other_bbox):
            return 0.0
        
        # Calculate intersection rectangle
        x1 = max(self.bbox[0], other_bbox[0])
        y1 = max(self.bbox[1], other_bbox[1])
        x2 = min(self.bbox[2], other_bbox[2])
        y2 = min(self.bbox[3], other_bbox[3])
        
        return (x2 - x1) * (y2 - y1)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'page': self.page,
            'bbox': self.bbox,
            'zone_type': self.zone_type,
            'snippet_id': self.snippet_id,
            'priority': self.priority
        }


class ExclusionZoneManager:
    """Manages exclusion zones for text extraction."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.zones_by_page: Dict[int, List[ExclusionZone]] = {}
        self.overlap_threshold = 0.5  # 50% overlap threshold
    
    def add_zone(self, zone: ExclusionZone):
        """Add an exclusion zone."""
        if zone.page not in self.zones_by_page:
            self.zones_by_page[zone.page] = []
        
        self.zones_by_page[zone.page].append(zone)
        self.logger.debug(f"Added exclusion zone for page {zone.page}: {zone.zone_type}")
    
    def add_zones_from_validation_session(self, validation_session: ManualValidationSession):
        """Add exclusion zones from a manual validation session."""
        for page_num, page_result in validation_session.page_results.items():
            for snippet in page_result.snippets:
                zone = ExclusionZone(
                    page=page_num,
                    bbox=snippet.location.bbox,
                    zone_type=snippet.snippet_type.value,
                    snippet_id=snippet.id,
                    priority=self._get_priority_for_type(snippet.snippet_type)
                )
                self.add_zone(zone)
        
        self.logger.info(f"Added {len(validation_session.get_all_snippets())} exclusion zones from validation session")
    
    def _get_priority_for_type(self, snippet_type: SnippetType) -> int:
        """Get priority level for different snippet types."""
        priority_map = {
            SnippetType.IMAGE: 3,    # Highest priority
            SnippetType.DIAGRAM: 2,  # Medium priority
            SnippetType.TABLE: 1     # Lower priority (might have extractable text)
        }
        return priority_map.get(snippet_type, 1)
    
    def get_zones_for_page(self, page_number: int) -> List[ExclusionZone]:
        """Get all exclusion zones for a specific page."""
        return self.zones_by_page.get(page_number, [])
    
    def should_exclude_text_element(self, page_number: int, element_bbox: List[float]) -> Tuple[bool, Optional[ExclusionZone]]:
        """
        Check if a text element should be excluded based on exclusion zones.
        
        Returns:
            (should_exclude, overlapping_zone)
        """
        zones = self.get_zones_for_page(page_number)
        
        for zone in zones:
            overlap_area = zone.get_overlap_area(element_bbox)
            
            if overlap_area > 0:
                # Calculate overlap percentage
                element_area = (element_bbox[2] - element_bbox[0]) * (element_bbox[3] - element_bbox[1])
                overlap_percentage = overlap_area / element_area if element_area > 0 else 0
                
                # Exclude if overlap exceeds threshold
                if overlap_percentage >= self.overlap_threshold:
                    return True, zone
        
        return False, None
    
    def should_exclude_point(self, page_number: int, x: float, y: float) -> Tuple[bool, Optional[ExclusionZone]]:
        """Check if a point should be excluded."""
        zones = self.get_zones_for_page(page_number)
        
        for zone in zones:
            if zone.contains_point(x, y):
                return True, zone
        
        return False, None
    
    def filter_text_elements(self, page_number: int, text_elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter text elements, removing those in exclusion zones."""
        filtered_elements = []
        excluded_count = 0
        
        for element in text_elements:
            # Extract bounding box from element
            element_bbox = self._extract_bbox_from_element(element)
            
            if element_bbox:
                should_exclude, overlapping_zone = self.should_exclude_text_element(page_number, element_bbox)
                
                if should_exclude:
                    excluded_count += 1
                    self.logger.debug(f"Excluded text element in {overlapping_zone.zone_type} zone: {element.get('text', '')[:50]}...")
                else:
                    filtered_elements.append(element)
            else:
                # If we can't extract bbox, keep the element
                filtered_elements.append(element)
        
        if excluded_count > 0:
            self.logger.info(f"Filtered {excluded_count} text elements from page {page_number}")
        
        return filtered_elements
    
    def _extract_bbox_from_element(self, element: Dict[str, Any]) -> Optional[List[float]]:
        """Extract bounding box from text element."""
        # Try different possible bbox keys
        bbox_keys = ['bbox', 'bounding_box', 'rect', 'bounds']
        
        for key in bbox_keys:
            if key in element:
                bbox = element[key]
                if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                    return list(bbox)
        
        # Try to construct from individual coordinates
        if all(key in element for key in ['x0', 'y0', 'x1', 'y1']):
            return [element['x0'], element['y0'], element['x1'], element['y1']]
        
        return None
    
    def get_exclusion_statistics(self) -> Dict[str, Any]:
        """Get statistics about exclusion zones."""
        stats = {
            'total_zones': 0,
            'zones_by_page': {},
            'zones_by_type': {'IMAGE': 0, 'TABLE': 0, 'DIAGRAM': 0},
            'pages_with_zones': len(self.zones_by_page)
        }
        
        for page_num, zones in self.zones_by_page.items():
            stats['zones_by_page'][page_num] = len(zones)
            stats['total_zones'] += len(zones)
            
            for zone in zones:
                stats['zones_by_type'][zone.zone_type] += 1
        
        return stats
    
    def optimize_zones(self):
        """Optimize exclusion zones by merging overlapping ones."""
        for page_num in self.zones_by_page:
            zones = self.zones_by_page[page_num]
            
            # Sort zones by priority (highest first)
            zones.sort(key=lambda z: z.priority, reverse=True)
            
            # Merge overlapping zones of the same type
            merged_zones = []
            for zone in zones:
                merged = False
                for existing in merged_zones:
                    if (zone.zone_type == existing.zone_type and 
                        zone.overlaps_with(existing.bbox)):
                        # Merge zones by expanding the existing one
                        existing.bbox = [
                            min(existing.bbox[0], zone.bbox[0]),
                            min(existing.bbox[1], zone.bbox[1]),
                            max(existing.bbox[2], zone.bbox[2]),
                            max(existing.bbox[3], zone.bbox[3])
                        ]
                        merged = True
                        break
                
                if not merged:
                    merged_zones.append(zone)
            
            original_count = len(zones)
            self.zones_by_page[page_num] = merged_zones
            
            if len(merged_zones) < original_count:
                self.logger.debug(f"Optimized page {page_num}: {original_count} → {len(merged_zones)} zones")
    
    def create_visual_debug_info(self, page_number: int, page_width: float, page_height: float) -> Dict[str, Any]:
        """Create visual debug information for exclusion zones."""
        zones = self.get_zones_for_page(page_number)
        
        debug_info = {
            'page_number': page_number,
            'page_size': [page_width, page_height],
            'zones': []
        }
        
        for zone in zones:
            zone_info = {
                'type': zone.zone_type,
                'bbox': zone.bbox,
                'snippet_id': zone.snippet_id,
                'priority': zone.priority,
                'coverage_percentage': (
                    (zone.bbox[2] - zone.bbox[0]) * (zone.bbox[3] - zone.bbox[1])
                ) / (page_width * page_height) * 100
            }
            debug_info['zones'].append(zone_info)
        
        return debug_info
    
    def export_zones_to_json(self) -> Dict[str, Any]:
        """Export all exclusion zones to JSON format."""
        export_data = {
            'zones_by_page': {},
            'statistics': self.get_exclusion_statistics()
        }
        
        for page_num, zones in self.zones_by_page.items():
            export_data['zones_by_page'][str(page_num)] = [
                zone.to_dict() for zone in zones
            ]
        
        return export_data
    
    def import_zones_from_json(self, data: Dict[str, Any]):
        """Import exclusion zones from JSON format."""
        self.zones_by_page = {}
        
        for page_num_str, zones_data in data.get('zones_by_page', {}).items():
            page_num = int(page_num_str)
            
            for zone_data in zones_data:
                zone = ExclusionZone(
                    page=zone_data['page'],
                    bbox=zone_data['bbox'],
                    zone_type=zone_data['zone_type'],
                    snippet_id=zone_data['snippet_id'],
                    priority=zone_data.get('priority', 1)
                )
                self.add_zone(zone)
        
        self.logger.info(f"Imported {len(self.zones_by_page)} pages of exclusion zones")


class ContentFilterWithExclusions:
    """Content filter that applies exclusion zones during text extraction."""
    
    def __init__(self, exclusion_manager: ExclusionZoneManager):
        self.exclusion_manager = exclusion_manager
        self.logger = logging.getLogger(__name__)
    
    def filter_extracted_content(self, extracted_content: Dict[str, Any]) -> Dict[str, Any]:
        """Filter extracted content based on exclusion zones."""
        filtered_content = extracted_content.copy()
        
        # Filter text elements
        if 'text_elements' in filtered_content:
            filtered_elements = []
            for element in filtered_content['text_elements']:
                page_num = element.get('page', 1)
                filtered_page_elements = self.exclusion_manager.filter_text_elements(
                    page_num, [element]
                )
                filtered_elements.extend(filtered_page_elements)
            
            filtered_content['text_elements'] = filtered_elements
        
        # Filter other content types if needed
        # Tables and images from manual validation are handled separately
        
        return filtered_content
    
    def should_process_text_block(self, page_number: int, text_block: Dict[str, Any]) -> bool:
        """Check if a text block should be processed."""
        bbox = self.exclusion_manager._extract_bbox_from_element(text_block)
        
        if bbox:
            should_exclude, _ = self.exclusion_manager.should_exclude_text_element(page_number, bbox)
            return not should_exclude
        
        return True  # Process if we can't determine bbox