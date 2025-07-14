"""Unit tests for cache metrics."""

import pytest
from torematrix.core.cache.cache_metrics import CacheMetrics


@pytest.fixture
def metrics() -> CacheMetrics:
    """Create a test metrics instance."""
    return CacheMetrics()


def test_hit_recording(metrics: CacheMetrics):
    """Test recording cache hits."""
    metrics.record_hit('memory')
    metrics.record_hit('memory')
    metrics.record_hit('disk')
    
    assert metrics.hits['memory'] == 2
    assert metrics.hits['disk'] == 1


def test_miss_recording(metrics: CacheMetrics):
    """Test recording cache misses."""
    metrics.record_miss('memory')
    metrics.record_miss('disk')
    metrics.record_miss('disk')
    
    assert metrics.misses['memory'] == 1
    assert metrics.misses['disk'] == 2


def test_hit_rate_calculation(metrics: CacheMetrics):
    """Test hit rate calculation."""
    # Record 3 hits and 1 miss
    metrics.record_hit('memory')
    metrics.record_hit('memory')
    metrics.record_hit('memory')
    metrics.record_miss('memory')
    
    assert metrics.get_hit_rate('memory') == 0.75


def test_hit_rate_no_requests(metrics: CacheMetrics):
    """Test hit rate calculation with no requests."""
    assert metrics.get_hit_rate('memory') == 0


def test_metrics_summary(metrics: CacheMetrics):
    """Test metrics summary generation."""
    metrics.record_hit('memory')
    metrics.record_hit('disk')
    metrics.record_miss('memory')
    metrics.record_miss('redis')
    
    summary = metrics.get_metrics_summary()
    
    assert summary['hit_rates']['memory'] == 0.5
    assert summary['hit_rates']['disk'] == 1.0
    assert summary['hit_rates']['redis'] == 0.0
    assert summary['total_hits']['memory'] == 1
    assert summary['total_misses']['memory'] == 1
    assert 'timestamp' in summary