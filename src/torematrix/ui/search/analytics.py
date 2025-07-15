"""Search Analytics and Performance Tracking

Comprehensive analytics system for search operations that tracks:
- Performance metrics and query analysis
- Usage patterns and optimization opportunities
- User behavior and search effectiveness
- Real-time monitoring and alerting
"""

import asyncio
import logging
import time
import json
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of search queries"""
    TEXT = "text"
    FILTER = "filter"
    ADVANCED = "advanced"
    SUGGESTION = "suggestion"
    AUTOCOMPLETE = "autocomplete"


class PerformanceLevel(Enum):
    """Performance level indicators"""
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class QueryMetrics:
    """Metrics for a single query"""
    query_id: str
    query_text: str
    query_type: QueryType
    timestamp: datetime
    execution_time: float
    result_count: int
    cache_hit: bool = False
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Performance details
    index_time: float = 0.0
    filter_time: float = 0.0
    sort_time: float = 0.0
    render_time: float = 0.0
    
    # User interaction
    clicked_results: List[int] = field(default_factory=list)
    view_time: float = 0.0
    refined_query: bool = False
    abandoned: bool = False


@dataclass
class AggregatedMetrics:
    """Aggregated performance metrics"""
    time_period: str
    total_queries: int = 0
    avg_execution_time: float = 0.0
    cache_hit_ratio: float = 0.0
    avg_result_count: float = 0.0
    
    # Performance breakdown
    avg_index_time: float = 0.0
    avg_filter_time: float = 0.0
    avg_sort_time: float = 0.0
    avg_render_time: float = 0.0
    
    # Query patterns
    query_types: Dict[str, int] = field(default_factory=dict)
    popular_queries: List[Tuple[str, int]] = field(default_factory=list)
    
    # User engagement
    avg_click_rate: float = 0.0
    avg_view_time: float = 0.0
    abandonment_rate: float = 0.0
    refinement_rate: float = 0.0
    
    # Performance levels
    performance_distribution: Dict[str, int] = field(default_factory=dict)


@dataclass
class PerformanceAlert:
    """Performance alert information"""
    alert_id: str
    timestamp: datetime
    level: PerformanceLevel
    metric_name: str
    current_value: float
    threshold_value: float
    description: str
    query_id: Optional[str] = None
    suggestion: Optional[str] = None


class SearchAnalyticsCollector(ABC):
    """Abstract interface for analytics data collection"""
    
    @abstractmethod
    async def record_query(self, metrics: QueryMetrics) -> None:
        """Record a query execution"""
        pass
    
    @abstractmethod
    async def record_user_interaction(self, query_id: str, interaction_type: str, data: Dict[str, Any]) -> None:
        """Record user interaction with search results"""
        pass
    
    @abstractmethod
    async def get_aggregated_metrics(self, time_period: str, start_time: datetime, end_time: datetime) -> AggregatedMetrics:
        """Get aggregated metrics for time period"""
        pass


class InMemoryAnalyticsCollector(SearchAnalyticsCollector):
    """In-memory analytics collector for development and testing"""
    
    def __init__(self, max_queries: int = 10000):
        self.max_queries = max_queries
        self.queries: deque = deque(maxlen=max_queries)
        self.interactions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def record_query(self, metrics: QueryMetrics) -> None:
        """Record query metrics"""
        async with self._lock:
            self.queries.append(metrics)
    
    async def record_user_interaction(self, query_id: str, interaction_type: str, data: Dict[str, Any]) -> None:
        """Record user interaction"""
        async with self._lock:
            self.interactions[query_id].append({
                'type': interaction_type,
                'timestamp': datetime.now(),
                'data': data
            })
    
    async def get_aggregated_metrics(self, time_period: str, start_time: datetime, end_time: datetime) -> AggregatedMetrics:
        """Calculate aggregated metrics"""
        async with self._lock:
            # Filter queries by time range
            period_queries = [
                q for q in self.queries 
                if start_time <= q.timestamp <= end_time
            ]
            
            if not period_queries:
                return AggregatedMetrics(time_period=time_period)
            
            # Calculate metrics
            total_queries = len(period_queries)
            avg_execution_time = sum(q.execution_time for q in period_queries) / total_queries
            cache_hits = sum(1 for q in period_queries if q.cache_hit)
            cache_hit_ratio = (cache_hits / total_queries) * 100
            avg_result_count = sum(q.result_count for q in period_queries) / total_queries
            
            # Performance breakdown
            avg_index_time = sum(q.index_time for q in period_queries) / total_queries
            avg_filter_time = sum(q.filter_time for q in period_queries) / total_queries
            avg_sort_time = sum(q.sort_time for q in period_queries) / total_queries
            avg_render_time = sum(q.render_time for q in period_queries) / total_queries
            
            # Query type distribution
            query_types = defaultdict(int)
            for query in period_queries:
                query_types[query.query_type.value] += 1
            
            # Popular queries
            query_counts = defaultdict(int)
            for query in period_queries:
                query_counts[query.query_text.lower()] += 1
            popular_queries = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # User engagement metrics
            clicked_queries = [q for q in period_queries if q.clicked_results]
            avg_click_rate = (len(clicked_queries) / total_queries) * 100 if total_queries > 0 else 0
            
            view_times = [q.view_time for q in period_queries if q.view_time > 0]
            avg_view_time = sum(view_times) / len(view_times) if view_times else 0
            
            abandoned_queries = sum(1 for q in period_queries if q.abandoned)
            abandonment_rate = (abandoned_queries / total_queries) * 100
            
            refined_queries = sum(1 for q in period_queries if q.refined_query)
            refinement_rate = (refined_queries / total_queries) * 100
            
            # Performance level distribution
            performance_distribution = defaultdict(int)
            for query in period_queries:
                level = self._classify_performance(query)
                performance_distribution[level.value] += 1
            
            return AggregatedMetrics(
                time_period=time_period,
                total_queries=total_queries,
                avg_execution_time=avg_execution_time,
                cache_hit_ratio=cache_hit_ratio,
                avg_result_count=avg_result_count,
                avg_index_time=avg_index_time,
                avg_filter_time=avg_filter_time,
                avg_sort_time=avg_sort_time,
                avg_render_time=avg_render_time,
                query_types=dict(query_types),
                popular_queries=popular_queries,
                avg_click_rate=avg_click_rate,
                avg_view_time=avg_view_time,
                abandonment_rate=abandonment_rate,
                refinement_rate=refinement_rate,
                performance_distribution=dict(performance_distribution)
            )
    
    def _classify_performance(self, query: QueryMetrics) -> PerformanceLevel:
        """Classify query performance level"""
        if query.execution_time < 0.05:  # < 50ms
            return PerformanceLevel.EXCELLENT
        elif query.execution_time < 0.1:  # < 100ms
            return PerformanceLevel.GOOD
        elif query.execution_time < 0.2:  # < 200ms
            return PerformanceLevel.AVERAGE
        elif query.execution_time < 0.5:  # < 500ms
            return PerformanceLevel.POOR
        else:
            return PerformanceLevel.CRITICAL


class SearchAnalyticsEngine:
    """Main search analytics engine"""
    
    def __init__(self, collector: Optional[SearchAnalyticsCollector] = None):
        self.collector = collector or InMemoryAnalyticsCollector()
        
        # Configuration
        self.enable_real_time_monitoring = True
        self.performance_thresholds = {
            'execution_time': 0.2,  # 200ms
            'cache_hit_ratio': 80.0,  # 80%
            'abandonment_rate': 20.0,  # 20%
            'error_rate': 5.0  # 5%
        }
        
        # Real-time monitoring
        self._recent_queries: deque = deque(maxlen=100)
        self._alert_callbacks: List[Callable[[PerformanceAlert], None]] = []
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Statistics
        self._stats = {
            'total_queries': 0,
            'total_errors': 0,
            'peak_execution_time': 0.0,
            'start_time': datetime.now()
        }
        
        logger.info("SearchAnalyticsEngine initialized")
    
    async def start_monitoring(self) -> None:
        """Start real-time monitoring"""
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Search analytics monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop real-time monitoring"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            logger.info("Search analytics monitoring stopped")
    
    async def record_query_start(self, query_id: str, query_text: str, 
                                query_type: QueryType, context: Dict[str, Any] = None) -> None:
        """Record the start of a query"""
        # This would store the start time for timing calculations
        pass
    
    async def record_query_complete(self, metrics: QueryMetrics) -> None:
        """Record a completed query with full metrics"""
        try:
            # Update statistics
            self._stats['total_queries'] += 1
            if metrics.execution_time > self._stats['peak_execution_time']:
                self._stats['peak_execution_time'] = metrics.execution_time
            
            # Store in collector
            await self.collector.record_query(metrics)
            
            # Add to recent queries for real-time monitoring
            if self.enable_real_time_monitoring:
                self._recent_queries.append(metrics)
                await self._check_performance_alerts(metrics)
            
            logger.debug(f"Recorded query {metrics.query_id}: {metrics.execution_time:.3f}s")
            
        except Exception as e:
            logger.error(f"Failed to record query metrics: {e}")
            self._stats['total_errors'] += 1
    
    async def record_user_interaction(self, query_id: str, interaction_type: str, 
                                    data: Dict[str, Any]) -> None:
        """Record user interaction with search results"""
        try:
            await self.collector.record_user_interaction(query_id, interaction_type, data)
            logger.debug(f"Recorded interaction {interaction_type} for query {query_id}")
        except Exception as e:
            logger.error(f"Failed to record user interaction: {e}")
    
    async def get_current_performance(self) -> Dict[str, Any]:
        """Get current real-time performance metrics"""
        if not self._recent_queries:
            return {'status': 'no_data'}
        
        recent_list = list(self._recent_queries)
        current_time = datetime.now()
        
        # Calculate metrics for recent queries
        avg_execution_time = sum(q.execution_time for q in recent_list) / len(recent_list)
        cache_hits = sum(1 for q in recent_list if q.cache_hit)
        cache_hit_ratio = (cache_hits / len(recent_list)) * 100
        
        # Query rate (queries per minute)
        oldest_time = min(q.timestamp for q in recent_list)
        time_span = (current_time - oldest_time).total_seconds() / 60.0
        query_rate = len(recent_list) / max(time_span, 1.0)
        
        return {
            'status': 'active',
            'recent_queries': len(recent_list),
            'avg_execution_time': avg_execution_time,
            'cache_hit_ratio': cache_hit_ratio,
            'query_rate_per_minute': query_rate,
            'peak_execution_time': max(q.execution_time for q in recent_list),
            'timestamp': current_time
        }
    
    async def get_aggregated_report(self, time_period: str = 'last_hour') -> AggregatedMetrics:
        """Get aggregated analytics report"""
        end_time = datetime.now()
        
        if time_period == 'last_hour':
            start_time = end_time - timedelta(hours=1)
        elif time_period == 'last_day':
            start_time = end_time - timedelta(days=1)
        elif time_period == 'last_week':
            start_time = end_time - timedelta(weeks=1)
        elif time_period == 'last_month':
            start_time = end_time - timedelta(days=30)
        else:
            start_time = self._stats['start_time']
        
        return await self.collector.get_aggregated_metrics(time_period, start_time, end_time)
    
    async def get_performance_insights(self) -> Dict[str, Any]:
        """Get performance insights and recommendations"""
        report = await self.get_aggregated_report('last_hour')
        insights = []
        
        # Analyze cache performance
        if report.cache_hit_ratio < 60:
            insights.append({
                'type': 'cache_optimization',
                'severity': 'high',
                'message': f'Cache hit ratio is low ({report.cache_hit_ratio:.1f}%)',
                'recommendation': 'Consider increasing cache size or improving cache strategy'
            })
        
        # Analyze execution time
        if report.avg_execution_time > 0.2:
            insights.append({
                'type': 'performance_optimization',
                'severity': 'medium',
                'message': f'Average execution time is high ({report.avg_execution_time:.3f}s)',
                'recommendation': 'Consider optimizing search indexes or query processing'
            })
        
        # Analyze abandonment rate
        if report.abandonment_rate > 25:
            insights.append({
                'type': 'user_experience',
                'severity': 'medium',
                'message': f'High abandonment rate ({report.abandonment_rate:.1f}%)',
                'recommendation': 'Review search relevance and result presentation'
            })
        
        # Query pattern analysis
        if report.total_queries > 0:
            top_query_type = max(report.query_types.items(), key=lambda x: x[1], default=('none', 0))
            insights.append({
                'type': 'usage_pattern',
                'severity': 'info',
                'message': f'Most common query type: {top_query_type[0]} ({top_query_type[1]} queries)',
                'recommendation': 'Optimize for the most common query patterns'
            })
        
        return {
            'timestamp': datetime.now(),
            'insights': insights,
            'summary': {
                'total_queries': report.total_queries,
                'performance_score': self._calculate_performance_score(report),
                'health_status': self._determine_health_status(report)
            }
        }
    
    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]) -> None:
        """Add callback for performance alerts"""
        self._alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable[[PerformanceAlert], None]) -> None:
        """Remove alert callback"""
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)
    
    async def _monitoring_loop(self) -> None:
        """Real-time monitoring loop"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                await self._check_system_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _check_performance_alerts(self, metrics: QueryMetrics) -> None:
        """Check for performance alerts"""
        alerts = []
        
        # Check execution time
        if metrics.execution_time > self.performance_thresholds['execution_time']:
            alerts.append(PerformanceAlert(
                alert_id=f"slow_query_{metrics.query_id}",
                timestamp=datetime.now(),
                level=PerformanceLevel.POOR,
                metric_name='execution_time',
                current_value=metrics.execution_time,
                threshold_value=self.performance_thresholds['execution_time'],
                description=f"Query executed slowly: {metrics.execution_time:.3f}s",
                query_id=metrics.query_id,
                suggestion="Consider optimizing query or increasing cache size"
            ))
        
        # Trigger alert callbacks
        for alert in alerts:
            for callback in self._alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
    
    async def _check_system_health(self) -> None:
        """Check overall system health"""
        current_performance = await self.get_current_performance()
        
        if current_performance.get('status') != 'active':
            return
        
        # Check cache hit ratio
        cache_ratio = current_performance.get('cache_hit_ratio', 0)
        if cache_ratio < self.performance_thresholds['cache_hit_ratio']:
            alert = PerformanceAlert(
                alert_id=f"low_cache_ratio_{int(time.time())}",
                timestamp=datetime.now(),
                level=PerformanceLevel.AVERAGE,
                metric_name='cache_hit_ratio',
                current_value=cache_ratio,
                threshold_value=self.performance_thresholds['cache_hit_ratio'],
                description=f"Cache hit ratio is below threshold: {cache_ratio:.1f}%",
                suggestion="Consider increasing cache size or optimizing cache strategy"
            )
            
            for callback in self._alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
    
    def _calculate_performance_score(self, report: AggregatedMetrics) -> float:
        """Calculate overall performance score (0-100)"""
        if report.total_queries == 0:
            return 0.0
        
        score = 100.0
        
        # Penalize for slow execution
        if report.avg_execution_time > 0.1:
            score -= min(50, (report.avg_execution_time - 0.1) * 500)
        
        # Reward high cache hit ratio
        if report.cache_hit_ratio > 80:
            score += 10
        elif report.cache_hit_ratio < 50:
            score -= 20
        
        # Penalize high abandonment
        if report.abandonment_rate > 20:
            score -= min(30, (report.abandonment_rate - 20) * 1.5)
        
        return max(0.0, min(100.0, score))
    
    def _determine_health_status(self, report: AggregatedMetrics) -> str:
        """Determine system health status"""
        score = self._calculate_performance_score(report)
        
        if score >= 90:
            return 'excellent'
        elif score >= 80:
            return 'good'
        elif score >= 70:
            return 'average'
        elif score >= 60:
            return 'poor'
        else:
            return 'critical'
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics"""
        uptime = datetime.now() - self._stats['start_time']
        
        return {
            'uptime_seconds': uptime.total_seconds(),
            'total_queries': self._stats['total_queries'],
            'total_errors': self._stats['total_errors'],
            'error_rate': (self._stats['total_errors'] / max(1, self._stats['total_queries'])) * 100,
            'peak_execution_time': self._stats['peak_execution_time'],
            'queries_per_hour': (self._stats['total_queries'] / max(1, uptime.total_seconds() / 3600)),
            'start_time': self._stats['start_time']
        }


# Factory functions for easy setup
def create_analytics_engine(collector: Optional[SearchAnalyticsCollector] = None) -> SearchAnalyticsEngine:
    """Create analytics engine with default configuration"""
    return SearchAnalyticsEngine(collector)


def create_in_memory_collector(max_queries: int = 10000) -> InMemoryAnalyticsCollector:
    """Create in-memory analytics collector"""
    return InMemoryAnalyticsCollector(max_queries)


# Utility functions
def export_metrics_to_json(metrics: AggregatedMetrics) -> str:
    """Export aggregated metrics to JSON"""
    return json.dumps(asdict(metrics), default=str, indent=2)


def calculate_query_effectiveness(clicked_results: List[int], total_results: int) -> float:
    """Calculate query effectiveness based on click patterns"""
    if not clicked_results or total_results == 0:
        return 0.0
    
    # Consider position bias - earlier results are more valuable
    effectiveness = 0.0
    for position in clicked_results:
        if position < total_results:
            # Higher score for clicks on earlier results
            position_weight = 1.0 / (1.0 + position * 0.1)
            effectiveness += position_weight
    
    # Normalize by number of clicks
    return min(1.0, effectiveness / len(clicked_results))