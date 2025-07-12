"""Cache metrics collection and reporting."""

from collections import defaultdict
from typing import Dict, Any
from datetime import datetime


class CacheMetrics:
    """Collects and reports cache performance metrics."""
    
    def __init__(self):
        self.hits = defaultdict(int)
        self.misses = defaultdict(int)
        self.sizes = defaultdict(int)
        self.latencies = defaultdict(list)
    
    def record_hit(self, cache_level: str):
        """Record a cache hit."""
        self.hits[cache_level] += 1
    
    def record_miss(self, cache_level: str):
        """Record a cache miss."""
        self.misses[cache_level] += 1
    
    def get_hit_rate(self, cache_level: str) -> float:
        """Calculate hit rate for a cache level."""
        total = self.hits[cache_level] + self.misses[cache_level]
        return self.hits[cache_level] / total if total > 0 else 0
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all cache metrics."""
        return {
            'hit_rates': {
                level: self.get_hit_rate(level) 
                for level in ['memory', 'disk', 'redis', 'object']
            },
            'total_hits': dict(self.hits),
            'total_misses': dict(self.misses),
            'cache_sizes': dict(self.sizes),
            'timestamp': datetime.now().isoformat()
        }