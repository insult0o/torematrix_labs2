"""
Performance optimization engine for state management.
"""

import time
import asyncio
from typing import Any, Dict, List, Optional, Callable, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
import weakref
import threading


class OptimizationLevel(Enum):
    """Optimization levels for different performance requirements."""
    MINIMAL = "minimal"      # Basic optimizations, lowest overhead
    BALANCED = "balanced"    # Good balance of performance and features
    AGGRESSIVE = "aggressive" # Maximum performance, may sacrifice features
    CUSTOM = "custom"        # User-defined optimization rules


@dataclass
class OptimizationRule:
    """Rule for automatic performance optimization."""
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    action: Callable[[Dict[str, Any]], None]
    priority: int = 0
    enabled: bool = True
    description: str = ""


@dataclass
class PerformanceThresholds:
    """Performance thresholds for optimization triggers."""
    max_selector_time_ms: float = 10.0
    max_update_time_ms: float = 16.0  # 60fps target
    max_memory_growth_mb_per_min: float = 10.0
    min_cache_hit_rate: float = 0.90
    max_subscription_notification_time_ms: float = 5.0


class OptimizationStrategy(ABC):
    """Abstract base class for optimization strategies."""
    
    @abstractmethod
    def can_optimize(self, metrics: Dict[str, Any]) -> bool:
        """Check if this strategy can optimize given metrics."""
        pass
    
    @abstractmethod
    async def optimize(self, context: 'OptimizationContext') -> Dict[str, Any]:
        """Execute optimization strategy."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get human-readable description of optimization."""
        pass


class SelectorCacheOptimization(OptimizationStrategy):
    """Optimize selector caching based on usage patterns."""
    
    def can_optimize(self, metrics: Dict[str, Any]) -> bool:
        """Check if selector cache needs optimization."""
        selector_metrics = metrics.get('selector', {})
        cache_hit_rate = selector_metrics.get('cache_hit_rate', 100)
        avg_time = selector_metrics.get('avg_execution_time_ms', 0)
        
        return cache_hit_rate < 90 or avg_time > 5.0
    
    async def optimize(self, context: 'OptimizationContext') -> Dict[str, Any]:
        """Optimize selector caching."""
        optimizations = []
        
        # Increase cache sizes for frequently used selectors
        for selector in context.selectors:
            if hasattr(selector, '_cache') and hasattr(selector, 'get_stats'):
                stats = selector.get_stats()
                if stats['cache_hit_rate'] < 90 and stats['call_count'] > 100:
                    # Increase cache size
                    old_size = getattr(selector, '_max_cache_size', 100)
                    new_size = min(old_size * 2, 1000)
                    selector._max_cache_size = new_size
                    optimizations.append(f"Increased cache size for {selector.name}: {old_size} -> {new_size}")
        
        # Enable smart caching for high-frequency selectors
        for selector in context.high_frequency_selectors:
            if not hasattr(selector, '_smart_cache_enabled'):
                selector._smart_cache_enabled = True
                optimizations.append(f"Enabled smart caching for {selector.name}")
        
        return {
            'strategy': 'selector_cache_optimization',
            'optimizations': optimizations,
            'estimated_improvement': '10-30% cache hit rate increase'
        }
    
    def get_description(self) -> str:
        return "Optimize selector caching to improve hit rates and reduce computation"


class SubscriptionOptimization(OptimizationStrategy):
    """Optimize subscription management and notifications."""
    
    def can_optimize(self, metrics: Dict[str, Any]) -> bool:
        """Check if subscription optimization is needed."""
        subscription_metrics = metrics.get('subscriptions', {})
        notification_time = subscription_metrics.get('avg_notification_time_ms', 0)
        active_count = subscription_metrics.get('active_count', 0)
        
        return notification_time > 5.0 or active_count > 1000
    
    async def optimize(self, context: 'OptimizationContext') -> Dict[str, Any]:
        """Optimize subscription system."""
        optimizations = []
        
        # Enable batch notifications
        if hasattr(context.subscription_manager, 'enable_batching'):
            context.subscription_manager.enable_batching(True)
            optimizations.append("Enabled batch notifications")
        
        # Clean up dead subscriptions
        if hasattr(context.subscription_manager, 'cleanup_dead_subscriptions'):
            cleaned = context.subscription_manager.cleanup_dead_subscriptions()
            if cleaned > 0:
                optimizations.append(f"Cleaned up {cleaned} dead subscriptions")
        
        # Optimize subscription paths
        if hasattr(context.subscription_manager, 'optimize_paths'):
            context.subscription_manager.optimize_paths()
            optimizations.append("Optimized subscription paths")
        
        return {
            'strategy': 'subscription_optimization',
            'optimizations': optimizations,
            'estimated_improvement': '20-50% notification time reduction'
        }
    
    def get_description(self) -> str:
        return "Optimize subscription management and notification performance"


class MemoryOptimization(OptimizationStrategy):
    """Optimize memory usage and prevent leaks."""
    
    def can_optimize(self, metrics: Dict[str, Any]) -> bool:
        """Check if memory optimization is needed."""
        memory_metrics = metrics.get('memory', {})
        growth_rate = memory_metrics.get('growth_rate_mb_per_min', 0)
        usage_mb = memory_metrics.get('usage_mb', 0)
        
        return growth_rate > 10.0 or usage_mb > 1000
    
    async def optimize(self, context: 'OptimizationContext') -> Dict[str, Any]:
        """Optimize memory usage."""
        optimizations = []
        
        # Clear old cache entries
        for selector in context.selectors:
            if hasattr(selector, 'invalidate'):
                # Only clear cache for selectors with low hit rates
                stats = getattr(selector, 'get_stats', lambda: {})()
                if stats and stats.get('cache_hit_rate', 100) < 50:
                    selector.invalidate()
                    optimizations.append(f"Cleared cache for low-efficiency selector: {selector.name}")
        
        # Force garbage collection
        import gc
        collected = gc.collect()
        if collected > 0:
            optimizations.append(f"Garbage collection freed {collected} objects")
        
        # Compress state if possible
        if hasattr(context.state_manager, 'compress_state'):
            compressed = context.state_manager.compress_state()
            if compressed:
                optimizations.append("Compressed state data structures")
        
        return {
            'strategy': 'memory_optimization',
            'optimizations': optimizations,
            'estimated_improvement': '10-30% memory usage reduction'
        }
    
    def get_description(self) -> str:
        return "Optimize memory usage and prevent memory leaks"


class RenderOptimization(OptimizationStrategy):
    """Optimize rendering performance for 60fps target."""
    
    def can_optimize(self, metrics: Dict[str, Any]) -> bool:
        """Check if render optimization is needed."""
        performance_metrics = metrics.get('performance', {})
        frame_rate = performance_metrics.get('frame_rate', 60)
        render_time = performance_metrics.get('render_time_ms', 0)
        
        return frame_rate < 55 or render_time > 16
    
    async def optimize(self, context: 'OptimizationContext') -> Dict[str, Any]:
        """Optimize rendering performance."""
        optimizations = []
        
        # Enable update batching
        if hasattr(context.update_batcher, 'set_batch_timeout'):
            # Reduce batch timeout for more responsive updates
            context.update_batcher.set_batch_timeout(8)  # 8ms for 120fps potential
            optimizations.append("Reduced update batch timeout to 8ms")
        
        # Enable virtual rendering for large element lists
        if hasattr(context.element_renderer, 'enable_virtualization'):
            context.element_renderer.enable_virtualization(True)
            optimizations.append("Enabled virtual rendering for large element lists")
        
        # Optimize selector execution order
        if hasattr(context, 'optimize_selector_order'):
            context.optimize_selector_order()
            optimizations.append("Optimized selector execution order")
        
        return {
            'strategy': 'render_optimization',
            'optimizations': optimizations,
            'estimated_improvement': '60fps target achievement'
        }
    
    def get_description(self) -> str:
        return "Optimize rendering performance to maintain 60fps"


@dataclass
class OptimizationContext:
    """Context for optimization strategies."""
    metrics: Dict[str, Any]
    selectors: List[Any]
    high_frequency_selectors: List[Any] 
    subscription_manager: Any
    state_manager: Any
    update_batcher: Any
    element_renderer: Any
    thresholds: PerformanceThresholds
    
    def optimize_selector_order(self):
        """Optimize selector execution order based on dependencies."""
        # Sort selectors by dependency depth and frequency
        self.selectors.sort(key=lambda s: (
            len(getattr(s, 'dependencies', [])),
            -getattr(s, '_total_calls', 0)
        ))


class OptimizationEngine:
    """
    Intelligent performance optimization engine.
    
    Automatically detects performance issues and applies optimizations
    to maintain target performance levels.
    """
    
    def __init__(
        self,
        optimization_level: OptimizationLevel = OptimizationLevel.BALANCED,
        thresholds: Optional[PerformanceThresholds] = None
    ):
        self.optimization_level = optimization_level
        self.thresholds = thresholds or PerformanceThresholds()
        
        # Optimization strategies
        self._strategies: List[OptimizationStrategy] = [
            SelectorCacheOptimization(),
            SubscriptionOptimization(),
            MemoryOptimization(),
            RenderOptimization()
        ]
        
        # Custom optimization rules
        self._custom_rules: List[OptimizationRule] = []
        
        # Optimization history
        self._optimization_history: List[Dict[str, Any]] = []
        
        # Running state
        self._running = False
        self._optimization_task: Optional[asyncio.Task] = None
        self._optimization_interval = 30.0  # seconds
        
        # Threading
        self._lock = threading.RLock()
        
        # Callbacks
        self._optimization_callbacks: List[Callable] = []
    
    def add_strategy(self, strategy: OptimizationStrategy):
        """Add custom optimization strategy."""
        self._strategies.append(strategy)
    
    def add_rule(self, rule: OptimizationRule):
        """Add custom optimization rule."""
        self._custom_rules.append(rule)
    
    def add_optimization_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for optimization events."""
        self._optimization_callbacks.append(callback)
    
    async def analyze_performance(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze performance metrics and identify optimization opportunities.
        
        Args:
            metrics: Current performance metrics
            
        Returns:
            Analysis results with optimization recommendations
        """
        analysis = {
            'timestamp': time.time(),
            'issues': [],
            'recommendations': [],
            'critical_issues': [],
            'optimization_score': 100
        }
        
        # Check selector performance
        selector_metrics = metrics.get('selector', {})
        if selector_metrics:
            avg_time = selector_metrics.get('avg_execution_time_ms', 0)
            cache_hit_rate = selector_metrics.get('cache_hit_rate', 100)
            
            if avg_time > self.thresholds.max_selector_time_ms:
                analysis['issues'].append({
                    'type': 'selector_performance',
                    'severity': 'high' if avg_time > 20 else 'medium',
                    'message': f"Selector execution time too high: {avg_time:.2f}ms",
                    'threshold': self.thresholds.max_selector_time_ms
                })
                analysis['recommendations'].append("Optimize selector caching and dependencies")
                analysis['optimization_score'] -= 20
            
            if cache_hit_rate < self.thresholds.min_cache_hit_rate * 100:
                analysis['issues'].append({
                    'type': 'cache_efficiency',
                    'severity': 'medium',
                    'message': f"Cache hit rate too low: {cache_hit_rate:.1f}%",
                    'threshold': self.thresholds.min_cache_hit_rate * 100
                })
                analysis['recommendations'].append("Increase cache sizes or improve cache keys")
                analysis['optimization_score'] -= 15
        
        # Check memory performance
        memory_metrics = metrics.get('memory', {})
        if memory_metrics:
            growth_rate = memory_metrics.get('growth_rate_mb_per_min', 0)
            
            if growth_rate > self.thresholds.max_memory_growth_mb_per_min:
                analysis['critical_issues'].append({
                    'type': 'memory_leak',
                    'severity': 'critical',
                    'message': f"Memory growth rate too high: {growth_rate:.2f} MB/min",
                    'threshold': self.thresholds.max_memory_growth_mb_per_min
                })
                analysis['recommendations'].append("Check for memory leaks and optimize garbage collection")
                analysis['optimization_score'] -= 30
        
        # Check render performance
        performance_metrics = metrics.get('performance', {})
        if performance_metrics:
            frame_rate = performance_metrics.get('frame_rate', 60)
            render_time = performance_metrics.get('render_time_ms', 0)
            
            if frame_rate < 55:
                analysis['issues'].append({
                    'type': 'frame_rate',
                    'severity': 'high',
                    'message': f"Frame rate below target: {frame_rate:.1f} fps",
                    'threshold': 60
                })
                analysis['recommendations'].append("Optimize rendering pipeline and update batching")
                analysis['optimization_score'] -= 25
            
            if render_time > self.thresholds.max_update_time_ms:
                analysis['issues'].append({
                    'type': 'render_time',
                    'severity': 'medium',
                    'message': f"Render time too high: {render_time:.2f}ms",
                    'threshold': self.thresholds.max_update_time_ms
                })
                analysis['recommendations'].append("Enable virtual rendering and optimize selectors")
                analysis['optimization_score'] -= 15
        
        return analysis
    
    async def optimize(self, context: OptimizationContext) -> Dict[str, Any]:
        """
        Execute optimizations based on current metrics.
        
        Args:
            context: Optimization context with metrics and components
            
        Returns:
            Optimization results
        """
        optimization_results = {
            'timestamp': time.time(),
            'strategies_applied': [],
            'rules_applied': [],
            'total_optimizations': 0,
            'estimated_improvement': {}
        }
        
        # Apply applicable strategies
        for strategy in self._strategies:
            if strategy.can_optimize(context.metrics):
                try:
                    result = await strategy.optimize(context)
                    optimization_results['strategies_applied'].append(result)
                    optimization_results['total_optimizations'] += len(result.get('optimizations', []))
                    
                    # Merge estimated improvements
                    if 'estimated_improvement' in result:
                        strategy_name = result.get('strategy', strategy.__class__.__name__)
                        optimization_results['estimated_improvement'][strategy_name] = result['estimated_improvement']
                
                except Exception as e:
                    print(f"Optimization strategy {strategy.__class__.__name__} failed: {e}")
        
        # Apply custom rules
        for rule in self._custom_rules:
            if rule.enabled and rule.condition(context.metrics):
                try:
                    rule.action(context.metrics)
                    optimization_results['rules_applied'].append({
                        'rule': rule.name,
                        'description': rule.description
                    })
                    optimization_results['total_optimizations'] += 1
                
                except Exception as e:
                    print(f"Optimization rule {rule.name} failed: {e}")
        
        # Store in history
        with self._lock:
            self._optimization_history.append(optimization_results)
            
            # Keep only recent history
            if len(self._optimization_history) > 100:
                self._optimization_history = self._optimization_history[-50:]
        
        # Notify callbacks
        for callback in self._optimization_callbacks:
            try:
                callback(optimization_results)
            except Exception:
                pass
        
        return optimization_results
    
    async def start_auto_optimization(
        self,
        metrics_provider: Callable[[], Dict[str, Any]],
        context_provider: Callable[[], OptimizationContext],
        interval: float = None
    ):
        """
        Start automatic optimization based on metrics.
        
        Args:
            metrics_provider: Function that returns current metrics
            context_provider: Function that returns optimization context
            interval: Optimization check interval in seconds
        """
        if self._running:
            return
        
        self._running = True
        self._optimization_interval = interval or self._optimization_interval
        
        self._optimization_task = asyncio.create_task(
            self._auto_optimization_loop(metrics_provider, context_provider)
        )
    
    async def stop_auto_optimization(self):
        """Stop automatic optimization."""
        self._running = False
        
        if self._optimization_task:
            self._optimization_task.cancel()
            try:
                await self._optimization_task
            except asyncio.CancelledError:
                pass
            finally:
                self._optimization_task = None
    
    async def _auto_optimization_loop(
        self,
        metrics_provider: Callable[[], Dict[str, Any]],
        context_provider: Callable[[], OptimizationContext]
    ):
        """Auto-optimization loop."""
        while self._running:
            try:
                # Get current metrics
                metrics = metrics_provider()
                
                # Analyze performance
                analysis = await self.analyze_performance(metrics)
                
                # Only optimize if issues are detected
                if analysis['issues'] or analysis['critical_issues']:
                    context = context_provider()
                    context.metrics = metrics
                    
                    await self.optimize(context)
                
                await asyncio.sleep(self._optimization_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Auto-optimization error: {e}")
                await asyncio.sleep(self._optimization_interval)
    
    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """Get optimization history."""
        with self._lock:
            return self._optimization_history.copy()
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics."""
        with self._lock:
            if not self._optimization_history:
                return {'total_optimizations': 0, 'strategies_used': [], 'avg_optimizations_per_run': 0}
            
            total_optimizations = sum(
                result.get('total_optimizations', 0) 
                for result in self._optimization_history
            )
            
            strategies_used = set()
            for result in self._optimization_history:
                for strategy_result in result.get('strategies_applied', []):
                    strategies_used.add(strategy_result.get('strategy', 'unknown'))
            
            return {
                'total_optimizations': total_optimizations,
                'optimization_runs': len(self._optimization_history),
                'avg_optimizations_per_run': total_optimizations / len(self._optimization_history),
                'strategies_used': list(strategies_used),
                'is_running': self._running,
                'optimization_interval': self._optimization_interval
            }
    
    def clear_history(self):
        """Clear optimization history."""
        with self._lock:
            self._optimization_history.clear()