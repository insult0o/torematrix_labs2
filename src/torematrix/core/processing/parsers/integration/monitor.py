"""Performance monitoring and metrics collection for parsers."""

import asyncio
import time
import logging
import statistics
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque


@dataclass
class ParseMetric:
    """Individual parsing operation metric."""
    timestamp: datetime
    parser_type: str
    element_type: str
    success: bool
    processing_time: float
    confidence: float
    memory_used: int = 0
    cache_hit: bool = False


@dataclass
class PerformanceStats:
    """Performance statistics for a parser."""
    parser_type: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    median_time: float = 0.0
    p95_time: float = 0.0
    avg_confidence: float = 0.0
    total_memory: int = 0
    avg_memory: float = 0.0
    
    def update(self, metric: ParseMetric):
        """Update stats with new metric."""
        self.total_requests += 1
        
        if metric.success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        self.total_time += metric.processing_time
        self.min_time = min(self.min_time, metric.processing_time)
        self.max_time = max(self.max_time, metric.processing_time)
        
        if self.total_requests > 0:
            self.avg_time = self.total_time / self.total_requests
        
        if metric.memory_used > 0:
            self.total_memory += metric.memory_used
            self.avg_memory = self.total_memory / self.total_requests
        
        # Update confidence (only for successful requests)
        if metric.success and self.successful_requests > 0:
            # Running average
            prev_avg = self.avg_confidence
            self.avg_confidence = (prev_avg * (self.successful_requests - 1) + metric.confidence) / self.successful_requests


class ParserMonitor:
    """Performance monitoring system for parser operations."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("torematrix.parsers.monitor")
        
        # Configuration
        self.retention_hours = config.get('retention_hours', 24)
        self.max_metrics = config.get('max_metrics', 10000)
        self.aggregation_interval = config.get('aggregation_interval', 60)  # seconds
        self.enable_detailed_logging = config.get('enable_detailed_logging', False)
        
        # Metrics storage
        self._metrics: deque[ParseMetric] = deque(maxlen=self.max_metrics)
        self._parser_stats: Dict[str, PerformanceStats] = {}
        self._element_stats: Dict[str, PerformanceStats] = {}
        self._recent_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Real-time monitoring
        self._current_hour_metrics = deque(maxlen=3600)  # 1 metric per second max
        self._alerts = []
        self._alert_thresholds = {
            'max_processing_time': config.get('max_processing_time', 30.0),
            'min_success_rate': config.get('min_success_rate', 0.95),
            'max_error_rate': config.get('max_error_rate', 0.05),
            'min_confidence': config.get('min_confidence', 0.7)
        }
        
        # Background tasks
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        self._aggregation_task = asyncio.create_task(self._periodic_aggregation())
    
    async def record_parse_metrics(self, parser_type: str, element_type: str, 
                                  success: bool, processing_time: float, 
                                  confidence: float, memory_used: int = 0,
                                  cache_hit: bool = False) -> None:
        """Record metrics for a parsing operation."""
        metric = ParseMetric(
            timestamp=datetime.utcnow(),
            parser_type=parser_type,
            element_type=element_type,
            success=success,
            processing_time=processing_time,
            confidence=confidence,
            memory_used=memory_used,
            cache_hit=cache_hit
        )
        
        # Store metric
        self._metrics.append(metric)
        self._current_hour_metrics.append(metric)
        
        # Update parser stats
        if parser_type not in self._parser_stats:
            self._parser_stats[parser_type] = PerformanceStats(parser_type=parser_type)
        self._parser_stats[parser_type].update(metric)
        
        # Update element stats
        if element_type not in self._element_stats:
            self._element_stats[element_type] = PerformanceStats(parser_type=element_type)
        self._element_stats[element_type].update(metric)
        
        # Track recent processing times for percentile calculations
        self._recent_times[parser_type].append(processing_time)
        
        # Check for alerts
        await self._check_alerts(metric)
        
        # Detailed logging if enabled
        if self.enable_detailed_logging:
            self.logger.debug(
                f"Recorded metric: {parser_type} -> {element_type} "
                f"(success: {success}, time: {processing_time:.3f}s, "
                f"confidence: {confidence:.2f})"
            )
    
    async def get_parser_performance(self, parser_type: str) -> Optional[Dict[str, Any]]:
        """Get performance metrics for a specific parser."""
        if parser_type not in self._parser_stats:
            return None
        
        stats = self._parser_stats[parser_type]
        
        # Calculate percentiles from recent times
        recent_times = list(self._recent_times[parser_type])
        percentiles = {}
        if recent_times:
            percentiles = {
                'p50': statistics.median(recent_times),
                'p95': statistics.quantiles(recent_times, n=20)[18] if len(recent_times) >= 20 else max(recent_times),
                'p99': statistics.quantiles(recent_times, n=100)[98] if len(recent_times) >= 100 else max(recent_times)
            }
        
        return {
            'parser_type': parser_type,
            'total_requests': stats.total_requests,
            'success_rate': stats.successful_requests / max(stats.total_requests, 1),
            'error_rate': stats.failed_requests / max(stats.total_requests, 1),
            'timing': {
                'avg_time': stats.avg_time,
                'min_time': stats.min_time if stats.min_time != float('inf') else 0,
                'max_time': stats.max_time,
                **percentiles
            },
            'confidence': {
                'avg_confidence': stats.avg_confidence
            },
            'memory': {
                'avg_memory_mb': stats.avg_memory / (1024 * 1024) if stats.avg_memory > 0 else 0
            },
            'last_updated': datetime.utcnow().isoformat()
        }
    
    async def get_system_overview(self) -> Dict[str, Any]:
        """Get system-wide performance overview."""
        total_requests = sum(stats.total_requests for stats in self._parser_stats.values())
        total_successful = sum(stats.successful_requests for stats in self._parser_stats.values())
        total_failed = sum(stats.failed_requests for stats in self._parser_stats.values())
        
        # Recent performance (last hour)
        recent_metrics = [m for m in self._current_hour_metrics 
                         if m.timestamp > datetime.utcnow() - timedelta(hours=1)]
        
        recent_success_rate = 0.0
        recent_avg_time = 0.0
        recent_avg_confidence = 0.0
        
        if recent_metrics:
            recent_successful = sum(1 for m in recent_metrics if m.success)
            recent_success_rate = recent_successful / len(recent_metrics)
            recent_avg_time = sum(m.processing_time for m in recent_metrics) / len(recent_metrics)
            recent_avg_confidence = sum(m.confidence for m in recent_metrics if m.success) / max(recent_successful, 1)
        
        # Parser breakdown
        parser_breakdown = {}
        for parser_type, stats in self._parser_stats.items():
            parser_breakdown[parser_type] = {
                'requests': stats.total_requests,
                'success_rate': stats.successful_requests / max(stats.total_requests, 1),
                'avg_time': stats.avg_time
            }
        
        # Element type breakdown
        element_breakdown = {}
        for element_type, stats in self._element_stats.items():
            element_breakdown[element_type] = {
                'requests': stats.total_requests,
                'success_rate': stats.successful_requests / max(stats.total_requests, 1)
            }
        
        return {
            'total_requests': total_requests,
            'overall_success_rate': total_successful / max(total_requests, 1),
            'overall_error_rate': total_failed / max(total_requests, 1),
            'recent_performance': {
                'success_rate': recent_success_rate,
                'avg_time': recent_avg_time,
                'avg_confidence': recent_avg_confidence,
                'request_count': len(recent_metrics)
            },
            'parser_breakdown': parser_breakdown,
            'element_breakdown': element_breakdown,
            'active_alerts': len(self._alerts),
            'metrics_retained': len(self._metrics),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def get_alerts(self) -> List[Dict[str, Any]]:
        """Get current performance alerts."""
        return [alert.copy() for alert in self._alerts]
    
    async def clear_alerts(self) -> int:
        """Clear all alerts and return count cleared."""
        count = len(self._alerts)
        self._alerts.clear()
        return count
    
    async def export_metrics(self, start_time: Optional[datetime] = None, 
                           end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Export metrics for external analysis."""
        if start_time is None:
            start_time = datetime.utcnow() - timedelta(hours=1)
        if end_time is None:
            end_time = datetime.utcnow()
        
        filtered_metrics = [
            m for m in self._metrics 
            if start_time <= m.timestamp <= end_time
        ]
        
        return [
            {
                'timestamp': metric.timestamp.isoformat(),
                'parser_type': metric.parser_type,
                'element_type': metric.element_type,
                'success': metric.success,
                'processing_time': metric.processing_time,
                'confidence': metric.confidence,
                'memory_used': metric.memory_used,
                'cache_hit': metric.cache_hit
            }
            for metric in filtered_metrics
        ]
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform monitoring system health check."""
        health = {
            'status': 'healthy',
            'metrics_count': len(self._metrics),
            'parsers_monitored': len(self._parser_stats),
            'elements_monitored': len(self._element_stats),
            'alerts_active': len(self._alerts)
        }
        
        # Check for issues
        if len(self._alerts) > 0:
            health['status'] = 'warning'
            health['issue'] = f"{len(self._alerts)} active alerts"
        
        # Check if monitoring is working
        recent_metrics = [m for m in self._current_hour_metrics 
                         if m.timestamp > datetime.utcnow() - timedelta(minutes=5)]
        
        if not recent_metrics and len(self._metrics) > 0:
            health['status'] = 'warning'
            health['issue'] = 'No recent metrics (last 5 minutes)'
        
        return health
    
    async def close(self) -> None:
        """Close monitoring system and cleanup."""
        # Cancel background tasks
        for task in [self._cleanup_task, self._aggregation_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.logger.info("Parser monitoring closed")
    
    async def _check_alerts(self, metric: ParseMetric) -> None:
        """Check metric against alert thresholds."""
        alerts = []
        
        # Processing time alert
        if metric.processing_time > self._alert_thresholds['max_processing_time']:
            alerts.append({
                'type': 'high_processing_time',
                'message': f"High processing time: {metric.processing_time:.2f}s for {metric.parser_type}",
                'severity': 'warning',
                'timestamp': datetime.utcnow().isoformat(),
                'parser_type': metric.parser_type,
                'value': metric.processing_time,
                'threshold': self._alert_thresholds['max_processing_time']
            })
        
        # Confidence alert
        if metric.success and metric.confidence < self._alert_thresholds['min_confidence']:
            alerts.append({
                'type': 'low_confidence',
                'message': f"Low confidence: {metric.confidence:.2f} for {metric.parser_type}",
                'severity': 'warning',
                'timestamp': datetime.utcnow().isoformat(),
                'parser_type': metric.parser_type,
                'value': metric.confidence,
                'threshold': self._alert_thresholds['min_confidence']
            })
        
        # Error rate alert (check recent error rate)
        if not metric.success:
            recent_metrics = [m for m in self._current_hour_metrics 
                            if (m.parser_type == metric.parser_type and 
                                m.timestamp > datetime.utcnow() - timedelta(minutes=10))]
            
            if len(recent_metrics) >= 10:  # Need minimum sample size
                error_rate = sum(1 for m in recent_metrics if not m.success) / len(recent_metrics)
                if error_rate > self._alert_thresholds['max_error_rate']:
                    alerts.append({
                        'type': 'high_error_rate',
                        'message': f"High error rate: {error_rate:.1%} for {metric.parser_type}",
                        'severity': 'error',
                        'timestamp': datetime.utcnow().isoformat(),
                        'parser_type': metric.parser_type,
                        'value': error_rate,
                        'threshold': self._alert_thresholds['max_error_rate']
                    })
        
        # Add alerts to list (avoid duplicates)
        for alert in alerts:
            # Check if similar alert already exists
            existing = any(
                a['type'] == alert['type'] and 
                a['parser_type'] == alert['parser_type'] and
                datetime.fromisoformat(a['timestamp']) > datetime.utcnow() - timedelta(minutes=5)
                for a in self._alerts
            )
            
            if not existing:
                self._alerts.append(alert)
                self.logger.warning(f"Alert triggered: {alert['message']}")
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup of old metrics."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self._cleanup_old_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic cleanup: {e}")
    
    async def _cleanup_old_metrics(self) -> None:
        """Remove old metrics beyond retention period."""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.retention_hours)
        
        # Clean main metrics
        initial_count = len(self._metrics)
        self._metrics = deque(
            (m for m in self._metrics if m.timestamp > cutoff_time),
            maxlen=self.max_metrics
        )
        
        # Clean current hour metrics
        hour_cutoff = datetime.utcnow() - timedelta(hours=1)
        self._current_hour_metrics = deque(
            (m for m in self._current_hour_metrics if m.timestamp > hour_cutoff),
            maxlen=3600
        )
        
        # Clean old alerts
        alert_cutoff = datetime.utcnow() - timedelta(hours=1)
        self._alerts = [
            alert for alert in self._alerts
            if datetime.fromisoformat(alert['timestamp']) > alert_cutoff
        ]
        
        cleaned_count = initial_count - len(self._metrics)
        if cleaned_count > 0:
            self.logger.debug(f"Cleaned up {cleaned_count} old metrics")
    
    async def _periodic_aggregation(self) -> None:
        """Periodic aggregation of statistics."""
        while True:
            try:
                await asyncio.sleep(self.aggregation_interval)
                await self._update_aggregated_stats()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic aggregation: {e}")
    
    async def _update_aggregated_stats(self) -> None:
        """Update aggregated statistics."""
        # Update percentiles for each parser
        for parser_type, times in self._recent_times.items():
            if parser_type in self._parser_stats and times:
                stats = self._parser_stats[parser_type]
                times_list = list(times)
                
                if len(times_list) >= 2:
                    stats.median_time = statistics.median(times_list)
                if len(times_list) >= 20:
                    stats.p95_time = statistics.quantiles(times_list, n=20)[18]