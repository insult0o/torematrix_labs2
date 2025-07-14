"""Theme performance profiling utility.

Provides tools for analyzing theme performance and generating optimization reports.
"""

import argparse
import json
import time
from pathlib import Path
from typing import Dict, Any, List

# Import theme system components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from torematrix.ui.themes.performance import (
    ThemePerformanceManager, PerformanceProfiler, MemoryProfiler,
    PerformanceOptimizer, PerformanceMetric
)


class ThemePerformanceProfiler:
    """Command-line theme performance profiler."""
    
    def __init__(self):
        """Initialize performance profiler."""
        self.performance_manager = ThemePerformanceManager()
        self.profiler = self.performance_manager.profiler
        self.memory_profiler = self.performance_manager.memory_profiler
        self.optimizer = self.performance_manager.optimizer
    
    def profile_theme_operations(
        self, 
        theme_name: str, 
        operations: List[str],
        iterations: int = 10
    ) -> Dict[str, Any]:
        """Profile theme operations.
        
        Args:
            theme_name: Name of theme to profile
            operations: List of operations to profile
            iterations: Number of iterations per operation
            
        Returns:
            Profiling results
        """
        results = {
            'theme_name': theme_name,
            'iterations': iterations,
            'operations': {},
            'summary': {}
        }
        
        print(f"🔍 Profiling theme '{theme_name}' with {iterations} iterations...")
        
        for operation in operations:
            print(f"  📊 Profiling operation: {operation}")
            
            operation_times = []
            
            for i in range(iterations):
                start_time = time.time()
                
                # Simulate different operations
                if operation == 'stylesheet_generation':
                    self._simulate_stylesheet_generation(theme_name)
                elif operation == 'theme_switching':
                    self._simulate_theme_switching(theme_name)
                elif operation == 'cache_operations':
                    self._simulate_cache_operations(theme_name)
                elif operation == 'compilation':
                    self._simulate_compilation(theme_name)
                else:
                    print(f"    ⚠️  Unknown operation: {operation}")
                    continue
                
                operation_time = (time.time() - start_time) * 1000  # Convert to ms
                operation_times.append(operation_time)
                
                # Record metric
                metric_type = self._get_metric_type_for_operation(operation)
                if metric_type:
                    self.profiler.record_metric(theme_name, metric_type, operation_time)
            
            if operation_times:
                results['operations'][operation] = {
                    'times_ms': operation_times,
                    'avg_ms': sum(operation_times) / len(operation_times),
                    'min_ms': min(operation_times),
                    'max_ms': max(operation_times),
                    'total_ms': sum(operation_times),
                }
                
                print(f"    ✅ {operation}: {results['operations'][operation]['avg_ms']:.2f}ms avg")
        
        # Generate summary
        all_times = []
        for op_data in results['operations'].values():
            all_times.extend(op_data['times_ms'])
        
        if all_times:
            results['summary'] = {
                'total_operations': len(all_times),
                'overall_avg_ms': sum(all_times) / len(all_times),
                'overall_min_ms': min(all_times),
                'overall_max_ms': max(all_times),
                'total_time_ms': sum(all_times),
            }
        
        return results
    
    def _simulate_stylesheet_generation(self, theme_name: str) -> None:
        """Simulate stylesheet generation."""
        # Simple simulation - would use actual theme engine in real scenario
        time.sleep(0.05)  # 50ms simulation
    
    def _simulate_theme_switching(self, theme_name: str) -> None:
        """Simulate theme switching."""
        time.sleep(0.1)  # 100ms simulation
    
    def _simulate_cache_operations(self, theme_name: str) -> None:
        """Simulate cache operations."""
        time.sleep(0.02)  # 20ms simulation
    
    def _simulate_compilation(self, theme_name: str) -> None:
        """Simulate theme compilation."""
        time.sleep(0.08)  # 80ms simulation
    
    def _get_metric_type_for_operation(self, operation: str) -> PerformanceMetric:
        """Get metric type for operation."""
        mapping = {
            'stylesheet_generation': PerformanceMetric.STYLESHEET_GENERATION_TIME,
            'theme_switching': PerformanceMetric.THEME_SWITCH_TIME,
            'cache_operations': PerformanceMetric.CACHE_HIT_RATIO,
            'compilation': PerformanceMetric.CSS_COMPILATION_TIME,
        }
        return mapping.get(operation)
    
    def analyze_performance(self, theme_name: str = None) -> Dict[str, Any]:
        """Analyze performance and generate recommendations.
        
        Args:
            theme_name: Specific theme to analyze
            
        Returns:
            Performance analysis results
        """
        print("🔍 Analyzing performance...")
        
        # Get performance statistics
        stats = {}
        for metric in PerformanceMetric:
            metric_stats = self.profiler.get_statistics(metric, theme_name)
            if metric_stats:
                stats[metric.value] = metric_stats
        
        # Get optimization suggestions
        suggestions = self.optimizer.analyze_performance(theme_name)
        
        # Get memory information
        memory_info = {
            'current_mb': self.memory_profiler._get_memory_usage(),
            'total_theme_mb': self.memory_profiler.get_total_theme_memory(),
        }
        
        results = {
            'analysis_timestamp': time.time(),
            'theme_filter': theme_name,
            'statistics': stats,
            'suggestions': [
                {
                    'category': s.category,
                    'priority': s.priority,
                    'description': s.description,
                    'improvement': s.potential_improvement,
                    'complexity': s.implementation_complexity,
                }
                for s in suggestions
            ],
            'memory_info': memory_info,
            'performance_targets': {
                target.metric.value: {
                    'target': target.target_value,
                    'warning': target.warning_threshold,
                    'critical': target.critical_threshold,
                    'unit': target.unit,
                }
                for target in self.profiler.targets.values()
            }
        }
        
        # Print summary
        print("\n📊 Performance Analysis Results:")
        print(f"  📈 Metrics analyzed: {len(stats)}")
        print(f"  💡 Optimization suggestions: {len(suggestions)}")
        print(f"  🧠 Current memory usage: {memory_info['current_mb']:.1f}MB")
        
        if suggestions:
            print("\n🚨 Top Recommendations:")
            for i, suggestion in enumerate(suggestions[:3], 1):
                print(f"  {i}. [{suggestion['priority'].upper()}] {suggestion['category']}")
                print(f"     {suggestion['description']}")
                print(f"     💡 {suggestion['improvement']}")
        
        return results
    
    def export_report(self, results: Dict[str, Any], output_file: Path) -> None:
        """Export performance report to file.
        
        Args:
            results: Performance analysis results
            output_file: Output file path
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)
            
            print(f"📄 Performance report exported to: {output_file}")
            
        except Exception as e:
            print(f"❌ Failed to export report: {e}")
    
    def benchmark_themes(self, theme_names: List[str]) -> Dict[str, Any]:
        """Benchmark multiple themes.
        
        Args:
            theme_names: List of theme names to benchmark
            
        Returns:
            Benchmark results
        """
        print(f"🏁 Benchmarking {len(theme_names)} themes...")
        
        benchmark_results = {
            'benchmark_timestamp': time.time(),
            'themes': {},
            'comparison': {}
        }
        
        operations = ['stylesheet_generation', 'theme_switching', 'cache_operations']
        
        for theme_name in theme_names:
            print(f"\n🎨 Benchmarking theme: {theme_name}")
            theme_results = self.profile_theme_operations(theme_name, operations, iterations=5)
            benchmark_results['themes'][theme_name] = theme_results
        
        # Generate comparison
        if len(theme_names) > 1:
            print("\n📊 Generating comparison...")
            
            for operation in operations:
                operation_times = {}
                for theme_name in theme_names:
                    if theme_name in benchmark_results['themes']:
                        theme_data = benchmark_results['themes'][theme_name]
                        if operation in theme_data['operations']:
                            operation_times[theme_name] = theme_data['operations'][operation]['avg_ms']
                
                if operation_times:
                    fastest_theme = min(operation_times, key=operation_times.get)
                    slowest_theme = max(operation_times, key=operation_times.get)
                    
                    benchmark_results['comparison'][operation] = {
                        'fastest': {
                            'theme': fastest_theme,
                            'time_ms': operation_times[fastest_theme]
                        },
                        'slowest': {
                            'theme': slowest_theme,
                            'time_ms': operation_times[slowest_theme]
                        },
                        'all_times': operation_times
                    }
                    
                    print(f"  ⚡ {operation}: {fastest_theme} fastest ({operation_times[fastest_theme]:.1f}ms)")
        
        return benchmark_results


def main():
    """Main entry point for performance profiler CLI."""
    parser = argparse.ArgumentParser(
        description="Profile theme performance and generate optimization reports"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Profile command
    profile_parser = subparsers.add_parser('profile', help='Profile theme operations')
    profile_parser.add_argument('theme_name', help='Theme name to profile')
    profile_parser.add_argument(
        '--operations', 
        nargs='+',
        default=['stylesheet_generation', 'theme_switching'],
        help='Operations to profile'
    )
    profile_parser.add_argument(
        '--iterations', 
        type=int, 
        default=10,
        help='Number of iterations per operation'
    )
    profile_parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Output file for results'
    )
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze performance and get recommendations')
    analyze_parser.add_argument('--theme', help='Specific theme to analyze')
    analyze_parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Output file for analysis'
    )
    
    # Benchmark command
    benchmark_parser = subparsers.add_parser('benchmark', help='Benchmark multiple themes')
    benchmark_parser.add_argument('themes', nargs='+', help='Theme names to benchmark')
    benchmark_parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Output file for benchmark results'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    profiler = ThemePerformanceProfiler()
    
    try:
        if args.command == 'profile':
            results = profiler.profile_theme_operations(
                args.theme_name,
                args.operations,
                args.iterations
            )
            
            if args.output:
                profiler.export_report(results, args.output)
            else:
                print(f"\n📊 Results: {json.dumps(results, indent=2)}")
        
        elif args.command == 'analyze':
            results = profiler.analyze_performance(args.theme)
            
            if args.output:
                profiler.export_report(results, args.output)
            else:
                print(f"\n📊 Analysis: {json.dumps(results, indent=2)}")
        
        elif args.command == 'benchmark':
            results = profiler.benchmark_themes(args.themes)
            
            if args.output:
                profiler.export_report(results, args.output)
            else:
                print(f"\n🏁 Benchmark: {json.dumps(results, indent=2)}")
        
    except Exception as e:
        print(f"❌ Profiler failed: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())