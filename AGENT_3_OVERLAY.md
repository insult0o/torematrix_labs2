# AGENT 3: Spatial Indexing & Performance Optimization - Document Viewer System

## 🎯 Mission
Implement spatial indexing with quadtree, viewport culling, and performance optimization for handling hundreds of elements efficiently in the document viewer overlay system.

## 📋 Sub-Issue Assignment
**GitHub Issue**: #147 - [Document Viewer] Sub-Issue #17.3: Spatial Indexing & Performance Optimization
**Agent Role**: Performance/Optimization
**Timeline**: Day 1-3 of 6-day cycle

## 🎯 Objectives
1. Implement quadtree spatial indexing for efficient element lookup
2. Build viewport culling system for performance optimization
3. Create element clustering algorithms for different zoom levels
4. Develop efficient redraw strategies and algorithms
5. Implement performance profiling and monitoring system

## 🏗️ Architecture Responsibilities

### Core Components
- **Spatial Indexing**: Quadtree implementation for fast element lookup
- **Viewport Culling**: Efficient rendering of only visible elements
- **Element Clustering**: Group elements at different zoom levels
- **Performance Optimization**: Efficient redraw and update strategies
- **Profiling System**: Real-time performance monitoring and analysis

### Key Files to Create
```
src/torematrix/ui/viewer/
├── spatial.py           # Quadtree spatial indexing
├── culling.py          # Viewport culling system
├── clustering.py       # Element clustering algorithms
├── optimization.py     # Performance optimization utilities
└── profiling.py        # Performance profiling system

tests/unit/viewer/
├── test_spatial.py      # Spatial indexing tests
├── test_culling.py     # Viewport culling tests
├── test_clustering.py  # Element clustering tests
├── test_optimization.py # Performance optimization tests
└── test_profiling.py   # Profiling system tests
```

## 🔗 Dependencies
- **Agent 1 (Core)**: Overlay rendering engine for performance integration
- **Agent 2 (Selection)**: Selection system for optimized hit testing
- **Monitoring System**: For performance metric collection
- **NumPy**: For efficient spatial calculations

## 🚀 Implementation Plan

### Day 1: Spatial Indexing Foundation
1. **Quadtree Implementation**
   - Core quadtree data structure
   - Element insertion and removal
   - Spatial query algorithms
   - Tree balancing and optimization

2. **Spatial Query System**
   - Point-in-region queries
   - Range queries for selection
   - Nearest neighbor searches
   - Intersection testing

### Day 2: Culling & Clustering
1. **Viewport Culling System**
   - Frustum culling for visible elements
   - Dynamic culling based on zoom level
   - Culling cache management
   - Performance optimization

2. **Element Clustering**
   - Zoom-based clustering algorithms
   - Cluster centroid calculation
   - Dynamic cluster updates
   - Level-of-detail management

### Day 3: Performance & Profiling
1. **Optimization Strategies**
   - Efficient redraw algorithms
   - Memory pooling for objects
   - Batch processing optimization
   - Update scheduling

2. **Performance Profiling**
   - Real-time performance monitoring
   - Memory usage tracking
   - Frame rate analysis
   - Bottleneck identification

## 📋 Deliverables Checklist
- [ ] Quadtree spatial indexing with optimized queries
- [ ] Viewport culling system for performance
- [ ] Element clustering for different zoom levels
- [ ] Performance optimization utilities
- [ ] Profiling system with real-time monitoring
- [ ] Comprehensive unit tests with >95% coverage

## 🔧 Technical Requirements
- **Query Performance**: <1ms for spatial queries with 1000+ elements
- **Memory Efficiency**: <100MB for spatial index with 10k elements
- **Scalability**: Handle 10,000+ elements efficiently
- **Real-time**: Maintain 60fps with dynamic updates
- **Accuracy**: Precise spatial calculations with floating-point precision

## 🏗️ Integration Points

### With Agent 1 (Core Rendering)
- Integrate with rendering pipeline for culling
- Provide spatial queries for render optimization
- Hook into coordinate transformation system

### With Agent 2 (Selection)
- Optimize selection hit testing with spatial index
- Provide fast element lookup for selection
- Support multi-element selection algorithms

### With Agent 4 (Interactive Features)
- Enable fast hit testing for interactions
- Support hover and tooltip queries
- Optimize touch interaction performance

## 📊 Success Metrics
- [ ] Spatial query performance <1ms for 1000+ elements
- [ ] Memory usage <100MB for 10k element spatial index
- [ ] Viewport culling improves rendering performance by 5x
- [ ] Element clustering reduces complexity by 10x at low zoom
- [ ] Real-time profiling with <1% performance overhead

## 🔍 Quadtree Spatial Indexing

### Core Quadtree Implementation
```python
class QuadTree:
    def __init__(self, bounds, max_objects=10, max_levels=5):
        self.bounds = bounds
        self.max_objects = max_objects
        self.max_levels = max_levels
        self.level = 0
        self.objects = []
        self.nodes = [None, None, None, None]
    
    def insert(self, element):
        # Insert element into quadtree
        if self.nodes[0] is not None:
            index = self._get_index(element.bounds)
            if index != -1:
                self.nodes[index].insert(element)
                return
        
        self.objects.append(element)
        
        # Split if needed
        if len(self.objects) > self.max_objects and self.level < self.max_levels:
            if self.nodes[0] is None:
                self._split()
            
            # Redistribute objects
            objects_to_redistribute = self.objects[:]
            self.objects = []
            
            for obj in objects_to_redistribute:
                index = self._get_index(obj.bounds)
                if index != -1:
                    self.nodes[index].insert(obj)
                else:
                    self.objects.append(obj)
    
    def query(self, bounds):
        # Query elements within bounds
        results = []
        
        # Check objects in current node
        for obj in self.objects:
            if self._intersects(obj.bounds, bounds):
                results.append(obj)
        
        # Check child nodes
        if self.nodes[0] is not None:
            for i in range(4):
                if self._intersects(self.nodes[i].bounds, bounds):
                    results.extend(self.nodes[i].query(bounds))
        
        return results
    
    def _split(self):
        # Split quadtree into 4 children
        sub_width = self.bounds.width / 2
        sub_height = self.bounds.height / 2
        x = self.bounds.x
        y = self.bounds.y
        
        self.nodes[0] = QuadTree(
            Rectangle(x + sub_width, y, sub_width, sub_height),
            self.max_objects, self.max_levels
        )
        self.nodes[1] = QuadTree(
            Rectangle(x, y, sub_width, sub_height),
            self.max_objects, self.max_levels
        )
        self.nodes[2] = QuadTree(
            Rectangle(x, y + sub_height, sub_width, sub_height),
            self.max_objects, self.max_levels
        )
        self.nodes[3] = QuadTree(
            Rectangle(x + sub_width, y + sub_height, sub_width, sub_height),
            self.max_objects, self.max_levels
        )
        
        # Update level for all children
        for node in self.nodes:
            node.level = self.level + 1
```

### Viewport Culling System
```python
class ViewportCuller:
    def __init__(self, spatial_index):
        self.spatial_index = spatial_index
        self.culling_cache = {}
        self.cache_validity = {}
    
    def cull_elements(self, viewport_bounds, zoom_level):
        # Efficiently cull elements outside viewport
        cache_key = (viewport_bounds, zoom_level)
        
        # Check cache validity
        if cache_key in self.culling_cache:
            if self._is_cache_valid(cache_key):
                return self.culling_cache[cache_key]
        
        # Perform culling
        visible_elements = []
        
        # Use spatial index for efficient querying
        candidate_elements = self.spatial_index.query(viewport_bounds)
        
        for element in candidate_elements:
            if self._is_element_visible(element, viewport_bounds, zoom_level):
                visible_elements.append(element)
        
        # Cache results
        self.culling_cache[cache_key] = visible_elements
        self.cache_validity[cache_key] = time.time()
        
        return visible_elements
    
    def _is_element_visible(self, element, viewport_bounds, zoom_level):
        # Check if element is visible in current viewport
        if not self._intersects(element.bounds, viewport_bounds):
            return False
        
        # Check minimum size threshold
        min_size = self._get_min_size_for_zoom(zoom_level)
        if element.bounds.width < min_size or element.bounds.height < min_size:
            return False
        
        return True
```

### Element Clustering System
```python
class ElementClusterer:
    def __init__(self, clustering_threshold=50):
        self.clustering_threshold = clustering_threshold
        self.clusters = {}
        self.cluster_cache = {}
    
    def cluster_elements(self, elements, zoom_level):
        # Cluster elements based on zoom level
        if zoom_level > 1.0:
            # High zoom - show individual elements
            return [(elem, None) for elem in elements]
        
        # Low zoom - create clusters
        clusters = self._create_clusters(elements, zoom_level)
        
        result = []
        for cluster in clusters:
            if len(cluster.elements) == 1:
                result.append((cluster.elements[0], None))
            else:
                # Create cluster representation
                cluster_repr = self._create_cluster_representation(cluster)
                result.append((cluster_repr, cluster))
        
        return result
    
    def _create_clusters(self, elements, zoom_level):
        # Use spatial clustering algorithm
        clusters = []
        unclustered = elements[:]
        
        while unclustered:
            # Start new cluster with first element
            seed_element = unclustered.pop(0)
            cluster = ElementCluster(seed_element)
            
            # Find nearby elements to add to cluster
            cluster_bounds = self._get_cluster_bounds(seed_element, zoom_level)
            
            i = 0
            while i < len(unclustered):
                element = unclustered[i]
                if self._should_cluster(element, cluster_bounds):
                    cluster.add_element(element)
                    unclustered.pop(i)
                    # Expand cluster bounds
                    cluster_bounds = self._expand_bounds(cluster_bounds, element.bounds)
                else:
                    i += 1
            
            clusters.append(cluster)
        
        return clusters
    
    def _create_cluster_representation(self, cluster):
        # Create visual representation of cluster
        centroid = cluster.get_centroid()
        element_count = len(cluster.elements)
        
        return ClusterElement(
            bounds=self._get_cluster_bounds(centroid),
            count=element_count,
            elements=cluster.elements
        )
```

## ⚡ Performance Optimization Strategies

### Efficient Redraw Algorithms
```python
class RedrawOptimizer:
    def __init__(self):
        self.dirty_regions = []
        self.redraw_queue = []
        self.last_redraw_time = 0
    
    def mark_dirty(self, bounds):
        # Mark region as needing redraw
        self.dirty_regions.append(bounds)
        
        # Merge overlapping regions
        self._merge_dirty_regions()
    
    def schedule_redraw(self, element, priority=0):
        # Schedule element for redraw
        self.redraw_queue.append((element, priority))
        
        # Sort by priority
        self.redraw_queue.sort(key=lambda x: x[1], reverse=True)
    
    def process_redraws(self, max_time_ms=16):
        # Process redraws within time budget
        start_time = time.time()
        processed = 0
        
        while (self.redraw_queue and 
               (time.time() - start_time) * 1000 < max_time_ms):
            element, _ = self.redraw_queue.pop(0)
            self._redraw_element(element)
            processed += 1
        
        return processed
```

### Performance Profiling System
```python
class PerformanceProfiler:
    def __init__(self):
        self.metrics = {}
        self.timers = {}
        self.memory_tracker = MemoryTracker()
    
    def start_timer(self, name):
        # Start timing operation
        self.timers[name] = time.time()
    
    def end_timer(self, name):
        # End timing operation
        if name in self.timers:
            duration = time.time() - self.timers[name]
            self._record_metric(name, duration)
            del self.timers[name]
    
    def profile_function(self, func):
        # Decorator for function profiling
        def wrapper(*args, **kwargs):
            self.start_timer(func.__name__)
            result = func(*args, **kwargs)
            self.end_timer(func.__name__)
            return result
        return wrapper
    
    def get_performance_report(self):
        # Generate comprehensive performance report
        return {
            'timing_metrics': self.metrics,
            'memory_usage': self.memory_tracker.get_usage(),
            'frame_rate': self._calculate_frame_rate(),
            'bottlenecks': self._identify_bottlenecks()
        }
```

## 🧪 Testing Strategy

### Performance Benchmarks
- Spatial query performance with varying element counts
- Viewport culling effectiveness
- Element clustering efficiency
- Memory usage optimization

### Stress Testing
- Large dataset handling (10,000+ elements)
- Rapid zoom/pan operations
- Concurrent spatial operations
- Memory leak detection

### Integration Testing
- Integration with rendering pipeline
- Selection system optimization
- Real-time performance monitoring

## 🎯 Day 3 Completion Criteria
By end of Day 3, deliver:
- Complete quadtree spatial indexing system
- Efficient viewport culling implementation
- Element clustering for zoom optimization
- Performance optimization utilities
- Real-time profiling system
- Integration APIs for other agents

---
**Agent 3 Focus**: Build high-performance spatial systems that enable smooth interaction with hundreds of elements.