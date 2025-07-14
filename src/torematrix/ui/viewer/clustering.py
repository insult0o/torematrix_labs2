"""
Element Clustering System for Agent 3 Performance Optimization.
This module provides clustering algorithms to group elements at different zoom levels
for improved rendering performance and better visual organization.
"""
from __future__ import annotations

import math
import threading
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .coordinates import Rectangle, Point
from .spatial import SpatialIndexManager, SpatialElement
# Forward reference to avoid circular imports


class ClusteringStrategy(Enum):
    """Clustering strategy options."""
    SPATIAL = "spatial"           # Spatial proximity clustering
    HIERARCHICAL = "hierarchical" # Hierarchical clustering by levels
    DENSITY = "density"           # Density-based clustering
    ADAPTIVE = "adaptive"         # Adaptive clustering based on zoom


@dataclass
class ElementCluster:
    """Represents a cluster of elements."""
    cluster_id: str
    elements: List[Any]
    bounds: Rectangle
    centroid: Point
    zoom_level: float
    creation_time: datetime = field(default_factory=datetime.now)
    
    # Visual properties
    representative_element: Optional[Any] = None
    cluster_color: Tuple[int, int, int, int] = (128, 128, 128, 128)
    cluster_size: float = 10.0
    
    # Metadata
    cluster_type: str = "generic"
    layer_names: Set[str] = field(default_factory=set)
    element_types: Set[str] = field(default_factory=set)
    importance: float = 0.5


class ElementClusterer:
    """Main element clustering system."""
    
    def __init__(self, spatial_index: SpatialIndexManager):
        self.spatial_index = spatial_index
        self.current_strategy = ClusteringStrategy.HIERARCHICAL
        self.cluster_cache: Dict[str, List[ElementCluster]] = {}
        self.cache_max_age = 30  # seconds
        self.total_clusterings = 0
        self.total_clustering_time = 0.0
        self.lock = threading.RLock()
    
    def cluster_elements(self, elements: List[Any], 
                        zoom_level: float, 
                        strategy: Optional[ClusteringStrategy] = None) -> List[ElementCluster]:
        """Cluster elements using specified or current strategy."""
        with self.lock:
            import time
            start_time = time.time()
            
            # Simple spatial clustering for now
            clusters = []
            if zoom_level < 1.0 and len(elements) > 5:
                # Create one cluster for low zoom levels
                if elements:
                    # Calculate bounds
                    min_x = min(e.bounds.x for e in elements)
                    min_y = min(e.bounds.y for e in elements)
                    max_x = max(e.bounds.x + e.bounds.width for e in elements)
                    max_y = max(e.bounds.y + e.bounds.height for e in elements)
                    
                    bounds = Rectangle(min_x, min_y, max_x - min_x, max_y - min_y)
                    centroid = Point(
                        bounds.x + bounds.width / 2,
                        bounds.y + bounds.height / 2
                    )
                    
                    cluster = ElementCluster(
                        cluster_id=f"cluster_0",
                        elements=elements,
                        bounds=bounds,
                        centroid=centroid,
                        zoom_level=zoom_level,
                        cluster_type="spatial"
                    )
                    clusters.append(cluster)
            
            # Update performance metrics
            clustering_time = time.time() - start_time
            self.total_clusterings += 1
            self.total_clustering_time += clustering_time
            
            return clusters
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get clustering statistics."""
        with self.lock:
            avg_time = (self.total_clustering_time / self.total_clusterings 
                       if self.total_clusterings > 0 else 0.0)
            
            return {
                'current_strategy': self.current_strategy.value,
                'total_clusterings': self.total_clusterings,
                'average_clustering_time': avg_time,
                'cache_entries': len(self.cluster_cache),
                'cache_max_age': self.cache_max_age
            }