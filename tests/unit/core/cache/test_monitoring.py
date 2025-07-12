"""Unit tests for cache monitoring."""

import json
import time
from datetime import datetime, timedelta
import pytest
from pathlib import Path

from torematrix.core.cache.monitoring import CacheMonitor


@pytest.fixture
def metrics_dir(tmp_path):
    """Create a temporary metrics directory."""
    return tmp_path / "metrics"


@pytest.fixture
def monitor(metrics_dir):
    """Create a test monitor instance."""
    return CacheMonitor(metrics_dir)


def test_hit_recording(monitor):
    """Test recording cache hits."""
    monitor.record_hit('memory')
    monitor.record_hit('memory')
    monitor.record_hit('disk')
    
    # Check hit rates
    assert monitor.get_hit_rate('memory') == 1.0  # 2 hits, 0 misses
    assert monitor.get_hit_rate('disk') == 1.0   # 1 hit, 0 misses


def test_miss_recording(monitor):
    """Test recording cache misses."""
    monitor.record_miss('memory')
    monitor.record_miss('disk')
    monitor.record_miss('disk')
    
    # Check hit rates
    assert monitor.get_hit_rate('memory') == 0.0  # 0 hits, 1 miss
    assert monitor.get_hit_rate('disk') == 0.0   # 0 hits, 2 misses


def test_mixed_hit_miss(monitor):
    """Test recording both hits and misses."""
    # Record 3 hits and 1 miss
    monitor.record_hit('memory')
    monitor.record_hit('memory')
    monitor.record_hit('memory')
    monitor.record_miss('memory')
    
    assert monitor.get_hit_rate('memory') == 0.75


def test_size_recording(monitor):
    """Test recording cache sizes."""
    monitor.record_size('memory', 1024)
    monitor.record_size('disk', 1048576)
    
    summary = monitor.get_metrics_summary()
    assert summary['sizes']['memory'] == 1024
    assert summary['sizes']['disk'] == 1048576


def test_latency_recording(monitor):
    """Test recording operation latencies."""
    monitor.record_latency('memory', 'get', 0.001)
    monitor.record_latency('memory', 'set', 0.002)
    monitor.record_latency('disk', 'get', 0.1)
    
    summary = monitor.get_metrics_summary()
    assert 'latencies' in summary
    assert 'memory' in summary['latencies']
    assert 'disk' in summary['latencies']


def test_eviction_recording(monitor):
    """Test recording cache evictions."""
    monitor.record_eviction('memory')
    monitor.record_eviction('memory')
    monitor.record_eviction('disk')
    
    summary = monitor.get_metrics_summary()
    assert summary['evictions']['memory'] == 2
    assert summary['evictions']['disk'] == 1


def test_error_recording(monitor):
    """Test recording cache errors."""
    monitor.record_error('redis', 'connection')
    monitor.record_error('redis', 'timeout')
    monitor.record_error('disk', 'serialization')
    
    summary = monitor.get_metrics_summary()
    assert 'redis' in summary['errors']
    assert summary['errors']['redis']['connection'] == 1
    assert summary['errors']['redis']['timeout'] == 1
    assert summary['errors']['disk']['serialization'] == 1


def test_metrics_persistence(monitor, metrics_dir):
    """Test saving and loading metrics."""
    # Record some metrics
    monitor.record_hit('memory')
    monitor.record_miss('disk')
    monitor.record_size('memory', 1024)
    
    # Save metrics
    monitor.save_metrics('test_metrics.json')
    
    # Load metrics
    loaded_metrics = monitor.load_metrics('test_metrics.json')
    
    assert 'hit_rates' in loaded_metrics
    assert 'sizes' in loaded_metrics
    assert loaded_metrics['sizes']['memory'] == 1024


def test_cleanup_old_metrics(monitor, metrics_dir):
    """Test cleaning up old metrics files."""
    # Create some test metrics files
    old_date = datetime.now() - timedelta(days=40)
    recent_date = datetime.now() - timedelta(days=5)
    
    old_file = metrics_dir / f"cache_metrics_{old_date:%Y%m%d_%H%M%S}.json"
    recent_file = metrics_dir / f"cache_metrics_{recent_date:%Y%m%d_%H%M%S}.json"
    
    metrics_dir.mkdir(parents=True)
    old_file.touch()
    recent_file.touch()
    
    # Clean up files older than 30 days
    monitor.cleanup_old_metrics(max_age_days=30)
    
    # Check that only recent file remains
    assert not old_file.exists()
    assert recent_file.exists()


def test_metrics_summary_format(monitor):
    """Test metrics summary structure."""
    monitor.record_hit('memory')
    monitor.record_miss('disk')
    monitor.record_size('redis', 2048)
    monitor.record_latency('object', 'get', 0.5)
    monitor.record_error('redis', 'timeout')
    
    summary = monitor.get_metrics_summary()
    
    # Check all required sections
    assert 'hit_rates' in summary
    assert 'sizes' in summary
    assert 'latencies' in summary
    assert 'evictions' in summary
    assert 'errors' in summary
    assert 'timestamp' in summary
    
    # Check timestamp format
    datetime.fromisoformat(summary['timestamp'])  # Should not raise
    
    # Check metrics for all cache levels
    for level in ['memory', 'disk', 'redis', 'object']:
        assert level in summary['hit_rates']
        assert level in summary['sizes']
        assert level in summary['latencies']
        assert level in summary['evictions']