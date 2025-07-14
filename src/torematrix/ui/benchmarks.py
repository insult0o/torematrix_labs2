"""Performance benchmarks and verification system for ToreMatrix V3 UI.

This module provides automated benchmarking and verification tools
to ensure UI performance meets specified targets across different
hardware configurations and usage scenarios.
"""

from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time
import logging
import statistics
import json
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt6.QtWidgets import QApplication, QWidget, QMainWindow
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QElapsedTimer
from PyQt6.QtGui import QResizeEvent

from .themes import ThemeManager
from .layouts import ResponsiveLayout, ScreenSize
from .performance import PerformanceOptimizer
from .utils.dpi_utils import DPIManager

logger = logging.getLogger(__name__)


class BenchmarkCategory(Enum):
    """Categories of UI benchmarks."""
    STARTUP = "startup"
    THEME_SWITCHING = "theme_switching"
    LAYOUT_ADAPTATION = "layout_adaptation"
    MEMORY_USAGE = "memory_usage"
    ICON_LOADING = "icon_loading"
    STYLESHEET_LOADING = "stylesheet_loading"
    WIDGET_CREATION = "widget_creation"
    RESPONSIVENESS = "responsiveness"
    DPI_SCALING = "dpi_scaling"


class BenchmarkSeverity(Enum):
    """Severity levels for benchmark failures."""
    CRITICAL = "critical"    # Major performance regression
    WARNING = "warning"      # Performance concern
    INFO = "info"           # Informational only


@dataclass
class BenchmarkTarget:
    """Performance target definition."""
    name: str
    category: BenchmarkCategory
    target_value: float
    unit: str
    description: str
    tolerance: float = 0.1  # 10% tolerance by default
    severity: BenchmarkSeverity = BenchmarkSeverity.WARNING


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    name: str
    category: BenchmarkCategory
    measured_value: float
    target_value: float
    unit: str
    passed: bool
    deviation_percent: float
    execution_time: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results."""
    name: str
    results: List[BenchmarkResult] = field(default_factory=list)
    total_time: float = 0.0
    passed_count: int = 0
    failed_count: int = 0
    timestamp: float = field(default_factory=time.time)
    
    def add_result(self, result: BenchmarkResult) -> None:
        """Add benchmark result to suite."""
        self.results.append(result)
        if result.passed:
            self.passed_count += 1
        else:
            self.failed_count += 1
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        total = self.passed_count + self.failed_count
        return (self.passed_count / total * 100) if total > 0 else 0.0


class UIBenchmarkRunner(QObject):
    """Automated UI performance benchmark runner."""
    
    # Signals
    benchmark_started = pyqtSignal(str)  # benchmark_name
    benchmark_completed = pyqtSignal(BenchmarkResult)
    suite_completed = pyqtSignal(BenchmarkSuite)
    progress_updated = pyqtSignal(int, int)  # current, total
    
    # Default performance targets
    DEFAULT_TARGETS = {
        "window_startup_time": BenchmarkTarget(
            "Window Startup Time",
            BenchmarkCategory.STARTUP,
            500.0,  # milliseconds
            "ms",
            "Time to create and show main window",
            tolerance=0.2,
            severity=BenchmarkSeverity.CRITICAL
        ),
        "theme_switch_time": BenchmarkTarget(
            "Theme Switch Time",
            BenchmarkCategory.THEME_SWITCHING,
            200.0,  # milliseconds
            "ms",
            "Time to switch between light and dark themes",
            tolerance=0.15,
            severity=BenchmarkSeverity.WARNING
        ),
        "layout_adapt_time": BenchmarkTarget(
            "Layout Adaptation Time",
            BenchmarkCategory.LAYOUT_ADAPTATION,
            100.0,  # milliseconds
            "ms",
            "Time to adapt layout to window resize",
            tolerance=0.2,
            severity=BenchmarkSeverity.WARNING
        ),
        "memory_base_usage": BenchmarkTarget(
            "Base Memory Usage",
            BenchmarkCategory.MEMORY_USAGE,
            100.0,  # megabytes
            "MB",
            "Memory usage with empty main window",
            tolerance=0.3,
            severity=BenchmarkSeverity.WARNING
        ),
        "icon_load_time": BenchmarkTarget(
            "Icon Load Time",
            BenchmarkCategory.ICON_LOADING,
            50.0,  # milliseconds
            "ms",
            "Time to load and cache themed icon",
            tolerance=0.25,
            severity=BenchmarkSeverity.INFO
        ),
        "stylesheet_load_time": BenchmarkTarget(
            "Stylesheet Load Time",
            BenchmarkCategory.STYLESHEET_LOADING,
            25.0,  # milliseconds
            "ms",
            "Time to load and optimize stylesheet",
            tolerance=0.3,
            severity=BenchmarkSeverity.INFO
        ),
        "widget_creation_time": BenchmarkTarget(
            "Widget Creation Time",
            BenchmarkCategory.WIDGET_CREATION,
            10.0,  # milliseconds
            "ms",
            "Average time to create standard widget",
            tolerance=0.2,
            severity=BenchmarkSeverity.WARNING
        ),
        "responsiveness_score": BenchmarkTarget(
            "UI Responsiveness Score",
            BenchmarkCategory.RESPONSIVENESS,
            95.0,  # percentage
            "%",
            "Percentage of UI operations completed within target time",
            tolerance=0.05,
            severity=BenchmarkSeverity.CRITICAL
        ),
        "dpi_scaling_time": BenchmarkTarget(
            "DPI Scaling Time",
            BenchmarkCategory.DPI_SCALING,
            50.0,  # milliseconds
            "ms",
            "Time to apply DPI scaling to widget hierarchy",
            tolerance=0.2,
            severity=BenchmarkSeverity.INFO
        )
    }
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self._targets: Dict[str, BenchmarkTarget] = self.DEFAULT_TARGETS.copy()
        self._current_suite: Optional[BenchmarkSuite] = None
        self._benchmark_count = 0
        self._completed_count = 0
        
        # Components for testing
        self._theme_manager: Optional[ThemeManager] = None
        self._performance_optimizer: Optional[PerformanceOptimizer] = None
        self._dpi_manager: Optional[DPIManager] = None
        
        # Benchmark execution settings
        self._warmup_iterations = 3
        self._measurement_iterations = 10
        self._parallel_execution = False
    
    def set_components(
        self,
        theme_manager: Optional[ThemeManager] = None,
        performance_optimizer: Optional[PerformanceOptimizer] = None,
        dpi_manager: Optional[DPIManager] = None
    ) -> None:
        """Set UI components for benchmarking."""
        self._theme_manager = theme_manager
        self._performance_optimizer = performance_optimizer
        self._dpi_manager = dpi_manager
    
    def add_custom_target(self, target_id: str, target: BenchmarkTarget) -> None:
        """Add custom benchmark target."""
        self._targets[target_id] = target
    
    def remove_target(self, target_id: str) -> bool:
        """Remove benchmark target."""
        if target_id in self._targets:
            del self._targets[target_id]
            return True
        return False
    
    def set_execution_settings(
        self,
        warmup_iterations: int = 3,
        measurement_iterations: int = 10,
        parallel_execution: bool = False
    ) -> None:
        """Configure benchmark execution settings."""
        self._warmup_iterations = max(1, warmup_iterations)
        self._measurement_iterations = max(1, measurement_iterations)
        self._parallel_execution = parallel_execution
    
    def run_all_benchmarks(self, suite_name: str = "UI Performance Suite") -> BenchmarkSuite:
        """Run all configured benchmarks."""
        self._current_suite = BenchmarkSuite(name=suite_name)
        self._benchmark_count = len(self._targets)
        self._completed_count = 0
        
        start_time = time.time()
        
        logger.info(f"Starting benchmark suite: {suite_name}")
        logger.info(f"Configured targets: {self._benchmark_count}")
        logger.info(f"Warmup iterations: {self._warmup_iterations}")
        logger.info(f"Measurement iterations: {self._measurement_iterations}")
        
        if self._parallel_execution:
            self._run_benchmarks_parallel()
        else:
            self._run_benchmarks_sequential()
        
        self._current_suite.total_time = time.time() - start_time
        
        logger.info(f"Benchmark suite completed in {self._current_suite.total_time:.2f}s")
        logger.info(f"Results: {self._current_suite.passed_count} passed, "
                   f"{self._current_suite.failed_count} failed")
        
        self.suite_completed.emit(self._current_suite)
        return self._current_suite
    
    def _run_benchmarks_sequential(self) -> None:
        """Run benchmarks sequentially."""
        for target_id, target in self._targets.items():
            self.benchmark_started.emit(target.name)
            
            try:
                result = self._execute_benchmark(target_id, target)
                self._current_suite.add_result(result)
                self.benchmark_completed.emit(result)
                
            except Exception as e:
                logger.error(f"Benchmark {target.name} failed: {e}")
                # Create failed result
                result = BenchmarkResult(
                    name=target.name,
                    category=target.category,
                    measured_value=-1,
                    target_value=target.target_value,
                    unit=target.unit,
                    passed=False,
                    deviation_percent=float('inf'),
                    execution_time=0.0,
                    metadata={"error": str(e)}
                )
                self._current_suite.add_result(result)
                self.benchmark_completed.emit(result)
            
            self._completed_count += 1
            self.progress_updated.emit(self._completed_count, self._benchmark_count)
    
    def _run_benchmarks_parallel(self) -> None:
        """Run benchmarks in parallel."""
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all benchmarks
            future_to_target = {
                executor.submit(self._execute_benchmark, target_id, target): (target_id, target)
                for target_id, target in self._targets.items()
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_target):
                target_id, target = future_to_target[future]
                self.benchmark_started.emit(target.name)
                
                try:
                    result = future.result()
                    self._current_suite.add_result(result)
                    self.benchmark_completed.emit(result)
                    
                except Exception as e:
                    logger.error(f"Benchmark {target.name} failed: {e}")
                    result = BenchmarkResult(
                        name=target.name,
                        category=target.category,
                        measured_value=-1,
                        target_value=target.target_value,
                        unit=target.unit,
                        passed=False,
                        deviation_percent=float('inf'),
                        execution_time=0.0,
                        metadata={"error": str(e)}
                    )
                    self._current_suite.add_result(result)
                    self.benchmark_completed.emit(result)
                
                self._completed_count += 1
                self.progress_updated.emit(self._completed_count, self._benchmark_count)
    
    def _execute_benchmark(self, target_id: str, target: BenchmarkTarget) -> BenchmarkResult:
        """Execute a single benchmark."""
        # Get benchmark function
        benchmark_func = getattr(self, f"_benchmark_{target_id}", None)
        if not benchmark_func:
            raise ValueError(f"No benchmark function found for {target_id}")
        
        # Warmup runs
        for _ in range(self._warmup_iterations):
            try:
                benchmark_func()
            except Exception:
                pass  # Ignore warmup errors
        
        # Measurement runs
        measurements = []
        execution_start = time.time()
        
        for _ in range(self._measurement_iterations):
            try:
                measured_value = benchmark_func()
                measurements.append(measured_value)
            except Exception as e:
                logger.warning(f"Measurement failed for {target.name}: {e}")
        
        execution_time = time.time() - execution_start
        
        if not measurements:
            raise RuntimeError(f"No successful measurements for {target.name}")
        
        # Calculate statistics
        avg_value = statistics.mean(measurements)
        deviation_percent = abs(avg_value - target.target_value) / target.target_value * 100
        passed = deviation_percent <= (target.tolerance * 100)
        
        metadata = {
            "measurements": measurements,
            "std_dev": statistics.stdev(measurements) if len(measurements) > 1 else 0,
            "min_value": min(measurements),
            "max_value": max(measurements),
            "median_value": statistics.median(measurements)
        }
        
        return BenchmarkResult(
            name=target.name,
            category=target.category,
            measured_value=avg_value,
            target_value=target.target_value,
            unit=target.unit,
            passed=passed,
            deviation_percent=deviation_percent,
            execution_time=execution_time,
            metadata=metadata
        )
    
    # Benchmark implementations
    
    def _benchmark_window_startup_time(self) -> float:
        """Benchmark main window startup time."""
        start_time = time.time()
        
        # Create main window
        window = QMainWindow()
        window.setWindowTitle("Benchmark Window")
        window.resize(800, 600)
        window.show()
        
        # Process events to complete initialization
        app = QApplication.instance()
        if app:
            app.processEvents()
        
        startup_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Cleanup
        window.close()
        window.deleteLater()
        if app:
            app.processEvents()
        
        return startup_time
    
    def _benchmark_theme_switch_time(self) -> float:
        """Benchmark theme switching time."""
        if not self._theme_manager:
            raise RuntimeError("ThemeManager not available for benchmarking")
        
        # Ensure we start with light theme
        self._theme_manager.load_theme(self._theme_manager.LIGHT_THEME)
        
        start_time = time.time()
        
        # Switch to dark theme
        self._theme_manager.load_theme(self._theme_manager.DARK_THEME)
        
        switch_time = (time.time() - start_time) * 1000  # Convert to ms
        
        return switch_time
    
    def _benchmark_layout_adapt_time(self) -> float:
        """Benchmark layout adaptation time."""
        # Create test widget with responsive layout
        container = QWidget()
        container.resize(1000, 600)
        
        # This would need a real ResponsiveLayout instance
        # For now, simulate layout adaptation
        start_time = time.time()
        
        # Simulate resize event
        resize_event = QResizeEvent(container.size(), QApplication.primaryScreen().size())
        container.resizeEvent(resize_event)
        
        adapt_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Cleanup
        container.deleteLater()
        
        return adapt_time
    
    def _benchmark_memory_base_usage(self) -> float:
        """Benchmark base memory usage."""
        if not self._performance_optimizer:
            raise RuntimeError("PerformanceOptimizer not available for benchmarking")
        
        usage = self._performance_optimizer.monitor_memory_usage()
        return usage.get("rss_mb", 0.0)
    
    def _benchmark_icon_load_time(self) -> float:
        """Benchmark icon loading time."""
        if not self._theme_manager:
            raise RuntimeError("ThemeManager not available for benchmarking")
        
        start_time = time.time()
        
        # Load themed icon
        icon = self._theme_manager.get_theme_icon("test_icon", 24)
        
        load_time = (time.time() - start_time) * 1000  # Convert to ms
        
        return load_time
    
    def _benchmark_stylesheet_load_time(self) -> float:
        """Benchmark stylesheet loading time."""
        if not self._performance_optimizer:
            raise RuntimeError("PerformanceOptimizer not available for benchmarking")
        
        # Create temporary stylesheet for testing
        test_stylesheet = "QWidget { background: red; padding: 4px; }"
        
        start_time = time.time()
        
        # Optimize stylesheet (simulates loading)
        optimized = self._performance_optimizer._stylesheet_cache._optimize_stylesheet(test_stylesheet)
        
        load_time = (time.time() - start_time) * 1000  # Convert to ms
        
        return load_time
    
    def _benchmark_widget_creation_time(self) -> float:
        """Benchmark widget creation time."""
        start_time = time.time()
        
        # Create standard widget
        widget = QWidget()
        widget.setMinimumSize(100, 100)
        widget.show()
        
        creation_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Cleanup
        widget.close()
        widget.deleteLater()
        
        return creation_time
    
    def _benchmark_responsiveness_score(self) -> float:
        """Benchmark UI responsiveness score."""
        # Simulate multiple UI operations and measure response times
        operations = [
            self._simulate_button_click,
            self._simulate_menu_open,
            self._simulate_window_resize,
            self._simulate_theme_toggle
        ]
        
        target_time = 16.67  # 60 FPS = 16.67ms per frame
        responsive_count = 0
        total_operations = len(operations) * 10  # Run each operation 10 times
        
        for operation in operations:
            for _ in range(10):
                start_time = time.time()
                try:
                    operation()
                    operation_time = (time.time() - start_time) * 1000
                    if operation_time <= target_time:
                        responsive_count += 1
                except Exception:
                    pass  # Count as non-responsive
        
        return (responsive_count / total_operations) * 100
    
    def _benchmark_dpi_scaling_time(self) -> float:
        """Benchmark DPI scaling application time."""
        if not self._dpi_manager:
            raise RuntimeError("DPIManager not available for benchmarking")
        
        # Create test widget hierarchy
        container = QWidget()
        child1 = QWidget(container)
        child2 = QWidget(container)
        grandchild = QWidget(child1)
        
        start_time = time.time()
        
        # Apply DPI scaling
        self._dpi_manager.apply_dpi_scaling_to_widget(container)
        
        scaling_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Cleanup
        container.deleteLater()
        
        return scaling_time
    
    # Simulation methods for responsiveness benchmark
    
    def _simulate_button_click(self) -> None:
        """Simulate button click operation."""
        from PyQt6.QtWidgets import QPushButton
        button = QPushButton("Test")
        button.click()
        button.deleteLater()
    
    def _simulate_menu_open(self) -> None:
        """Simulate menu opening."""
        from PyQt6.QtWidgets import QMenu
        menu = QMenu("Test Menu")
        menu.addAction("Action 1")
        menu.addAction("Action 2")
        menu.deleteLater()
    
    def _simulate_window_resize(self) -> None:
        """Simulate window resize."""
        widget = QWidget()
        widget.resize(400, 300)
        widget.resize(600, 450)
        widget.deleteLater()
    
    def _simulate_theme_toggle(self) -> None:
        """Simulate theme toggle."""
        if self._theme_manager:
            current = self._theme_manager.get_current_theme()
            # Just read current theme, don't actually toggle
    
    def export_results(self, suite: BenchmarkSuite, file_path: Path) -> bool:
        """Export benchmark results to JSON file."""
        try:
            results_data = {
                "suite_name": suite.name,
                "timestamp": suite.timestamp,
                "total_time": suite.total_time,
                "passed_count": suite.passed_count,
                "failed_count": suite.failed_count,
                "success_rate": suite.success_rate,
                "results": [
                    {
                        "name": result.name,
                        "category": result.category.value,
                        "measured_value": result.measured_value,
                        "target_value": result.target_value,
                        "unit": result.unit,
                        "passed": result.passed,
                        "deviation_percent": result.deviation_percent,
                        "execution_time": result.execution_time,
                        "timestamp": result.timestamp,
                        "metadata": result.metadata
                    }
                    for result in suite.results
                ]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2)
            
            logger.info(f"Benchmark results exported to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export benchmark results: {e}")
            return False
    
    def generate_report(self, suite: BenchmarkSuite) -> str:
        """Generate human-readable benchmark report."""
        report = []
        report.append(f"UI Performance Benchmark Report")
        report.append(f"=" * 40)
        report.append(f"Suite: {suite.name}")
        report.append(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(suite.timestamp))}")
        report.append(f"Total Time: {suite.total_time:.2f}s")
        report.append(f"Success Rate: {suite.success_rate:.1f}%")
        report.append(f"Results: {suite.passed_count} passed, {suite.failed_count} failed")
        report.append("")
        
        # Group results by category
        by_category = {}
        for result in suite.results:
            category = result.category.value
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(result)
        
        for category, results in by_category.items():
            report.append(f"{category.upper()} BENCHMARKS")
            report.append("-" * 30)
            
            for result in results:
                status = "PASS" if result.passed else "FAIL"
                report.append(f"  {result.name}: {status}")
                report.append(f"    Measured: {result.measured_value:.2f} {result.unit}")
                report.append(f"    Target: {result.target_value:.2f} {result.unit}")
                report.append(f"    Deviation: {result.deviation_percent:.1f}%")
                
                if not result.passed:
                    report.append(f"    *** PERFORMANCE ISSUE DETECTED ***")
                
                report.append("")
        
        return "\n".join(report)