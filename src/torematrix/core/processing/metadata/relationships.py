"""Core relationship detection engine for document elements.

This module provides the main RelationshipDetectionEngine that orchestrates
the detection of various types of relationships between document elements.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import networkx as nx

from ...models.element import UnifiedElement
from ...models.metadata import ElementMetadata
from .models.relationship import Relationship, RelationshipType
from .graph import ElementRelationshipGraph
from .algorithms.spatial import SpatialAnalyzer
from .algorithms.content import ContentAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class RelationshipConfig:
    """Configuration for relationship detection."""
    spatial_threshold: float = 10.0
    content_similarity_threshold: float = 0.7
    reading_order_confidence_threshold: float = 0.8
    max_relationship_distance: int = 5
    enable_ml_classification: bool = True
    enable_rule_based_classification: bool = True


@dataclass
class DocumentContext:
    """Document context for relationship detection."""
    document_id: str
    language: str = "en"
    reading_direction: str = "ltr"
    page_layout: Optional[Dict] = None
    metadata: Optional[Dict] = None


class RelationshipDetectionEngine:
    """Core engine for detecting element relationships.
    
    This engine coordinates various analyzers to detect spatial, content-based,
    and semantic relationships between document elements, building a comprehensive
    relationship graph.
    """
    
    def __init__(self, config: RelationshipConfig):
        """Initialize the relationship detection engine.
        
        Args:
            config: Configuration for relationship detection
        """
        self.config = config
        self.graph = ElementRelationshipGraph()
        self.spatial_analyzer = SpatialAnalyzer(config)
        self.content_analyzer = ContentAnalyzer(config)
        self.stats = {
            "relationships_detected": 0,
            "elements_processed": 0,
            "detection_time": 0.0
        }
        
    async def detect_relationships(
        self, 
        elements: List[UnifiedElement],
        context: DocumentContext
    ) -> ElementRelationshipGraph:
        """Detect all relationships between elements.
        
        Args:
            elements: List of document elements
            context: Document context for detection
            
        Returns:
            Complete relationship graph
        """
        logger.info(f"Starting relationship detection for {len(elements)} elements")
        
        # Clear previous graph data
        self.graph.clear()
        
        # Add all elements to graph first
        for element in elements:
            self.graph.add_element(element)
        
        # Detect different types of relationships in parallel
        tasks = [
            self.detect_spatial_relationships(elements),
            self.detect_content_relationships(elements),
            self.detect_hierarchical_relationships(elements),
            self.detect_reading_order_relationships(elements, context)
        ]
        
        relationship_sets = await asyncio.gather(*tasks)
        
        # Add all detected relationships to graph
        for relationships in relationship_sets:
            for relationship in relationships:
                self.graph.add_relationship(
                    relationship.source_id,
                    relationship.target_id,
                    relationship
                )
        
        # Update statistics
        total_relationships = sum(len(rs) for rs in relationship_sets)
        self.stats["relationships_detected"] = total_relationships
        self.stats["elements_processed"] = len(elements)
        
        logger.info(f"Detected {total_relationships} relationships")
        return self.graph
        
    async def detect_spatial_relationships(
        self, 
        elements: List[UnifiedElement]
    ) -> List[Relationship]:
        """Detect spatial relationships (containment, adjacency).
        
        Args:
            elements: List of elements to analyze
            
        Returns:
            List of spatial relationships
        """
        logger.debug("Detecting spatial relationships")
        
        relationships = []
        
        # Check each pair of elements for spatial relationships
        for i, element1 in enumerate(elements):
            for element2 in elements[i+1:]:
                spatial_rels = await self.spatial_analyzer.analyze_relationship(
                    element1, element2
                )
                relationships.extend(spatial_rels)
        
        logger.debug(f"Found {len(relationships)} spatial relationships")
        return relationships
        
    async def detect_content_relationships(
        self, 
        elements: List[UnifiedElement]
    ) -> List[Relationship]:
        """Detect content-based relationships.
        
        Args:
            elements: List of elements to analyze
            
        Returns:
            List of content relationships
        """
        logger.debug("Detecting content relationships")
        
        relationships = []
        
        # Analyze content similarity and semantic connections
        for i, element1 in enumerate(elements):
            for element2 in elements[i+1:]:
                content_rels = await self.content_analyzer.analyze_relationship(
                    element1, element2
                )
                relationships.extend(content_rels)
        
        logger.debug(f"Found {len(relationships)} content relationships")
        return relationships
        
    async def detect_hierarchical_relationships(
        self, 
        elements: List[UnifiedElement]
    ) -> List[Relationship]:
        """Detect parent-child hierarchical relationships.
        
        Args:
            elements: List of elements to analyze
            
        Returns:
            List of hierarchical relationships
        """
        logger.debug("Detecting hierarchical relationships")
        
        relationships = []
        
        # Detect containment hierarchies
        for element in elements:
            parent_candidates = [
                e for e in elements 
                if e.id != element.id and self._is_potential_parent(e, element)
            ]
            
            # Find most likely parent (smallest containing element)
            if parent_candidates:
                parent = min(
                    parent_candidates,
                    key=lambda p: self._calculate_area(p)
                )
                
                relationship = Relationship(
                    source_id=parent.id,
                    target_id=element.id,
                    relationship_type=RelationshipType.PARENT_CHILD,
                    confidence=0.9,
                    metadata={"detection_method": "containment"}
                )
                relationships.append(relationship)
        
        logger.debug(f"Found {len(relationships)} hierarchical relationships")
        return relationships
        
    async def detect_reading_order_relationships(
        self, 
        elements: List[UnifiedElement],
        context: DocumentContext
    ) -> List[Relationship]:
        """Detect reading order relationships.
        
        Args:
            elements: List of elements to analyze
            context: Document context
            
        Returns:
            List of reading order relationships
        """
        logger.debug("Detecting reading order relationships")
        
        relationships = []
        
        # Sort elements by reading order
        sorted_elements = self._sort_by_reading_order(elements, context)
        
        # Create reading order relationships
        for i in range(len(sorted_elements) - 1):
            current = sorted_elements[i]
            next_elem = sorted_elements[i + 1]
            
            relationship = Relationship(
                source_id=current.id,
                target_id=next_elem.id,
                relationship_type=RelationshipType.READING_ORDER,
                confidence=0.8,
                metadata={
                    "order_index": i,
                    "direction": context.reading_direction
                }
            )
            relationships.append(relationship)
        
        logger.debug(f"Found {len(relationships)} reading order relationships")
        return relationships
        
    def get_statistics(self) -> Dict[str, float]:
        """Get detection statistics.
        
        Returns:
            Dictionary of statistics
        """
        return self.stats.copy()
        
    def _is_potential_parent(
        self, 
        parent: UnifiedElement, 
        child: UnifiedElement
    ) -> bool:
        """Check if one element could be parent of another.
        
        Args:
            parent: Potential parent element
            child: Potential child element
            
        Returns:
            True if parent could contain child
        """
        if not (parent.metadata and child.metadata):
            return False
            
        if not (parent.metadata.coordinates and child.metadata.coordinates):
            return False
            
        parent_bbox = parent.metadata.coordinates.layout_bbox
        child_bbox = child.metadata.coordinates.layout_bbox
        
        if not (parent_bbox and child_bbox):
            return False
            
        # Check if child is contained within parent
        return (
            parent_bbox[0] <= child_bbox[0] and
            parent_bbox[1] <= child_bbox[1] and
            parent_bbox[2] >= child_bbox[2] and
            parent_bbox[3] >= child_bbox[3]
        )
        
    def _calculate_area(self, element: UnifiedElement) -> float:
        """Calculate area of element bounding box.
        
        Args:
            element: Element to calculate area for
            
        Returns:
            Area in square units
        """
        if not (element.metadata and element.metadata.coordinates):
            return float('inf')
            
        bbox = element.metadata.coordinates.layout_bbox
        if not bbox:
            return float('inf')
            
        return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        
    def _sort_by_reading_order(
        self, 
        elements: List[UnifiedElement],
        context: DocumentContext
    ) -> List[UnifiedElement]:
        """Sort elements by reading order.
        
        Args:
            elements: Elements to sort
            context: Document context
            
        Returns:
            Elements sorted by reading order
        """
        def reading_order_key(element: UnifiedElement) -> Tuple[float, float]:
            if not (element.metadata and element.metadata.coordinates):
                return (float('inf'), float('inf'))
                
            bbox = element.metadata.coordinates.layout_bbox
            if not bbox:
                return (float('inf'), float('inf'))
                
            # For left-to-right, top-to-bottom reading
            if context.reading_direction == "ltr":
                return (bbox[1], bbox[0])  # (top, left)
            else:  # rtl
                return (bbox[1], -bbox[2])  # (top, -right)
        
        return sorted(elements, key=reading_order_key)