"""Tests for the adaptive layout system."""

import pytest
from unittest.mock import Mock, patch
import time
from PyQt6.QtWidgets import QWidget, QApplication, QVBoxLayout
from PyQt6.QtCore import QSize, QRect, QObject

from src.torematrix.ui.layouts.adaptive import (
    AdaptationStrategy, LayoutDirection, ContentPriority, LayoutConstraints,
    ContentItem, LayoutSolution, LayoutAlgorithm, StackedLayoutAlgorithm,
    SplitLayoutAlgorithm, GridLayoutAlgorithm, AdaptiveLayoutEngine,
    AdaptiveLayout
)
from src.torematrix.ui.layouts.responsive import ScreenProperties
from src.torematrix.ui.layouts.breakpoints import BreakpointManager


@pytest.fixture
def app():
    """Fixture to provide QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_breakpoint_manager():
    """Mock breakpoint manager for testing."""
    return Mock(spec=BreakpointManager)


@pytest.fixture
def sample_screen_properties():
    """Sample screen properties for testing."""
    return ScreenProperties(
        width=1024,
        height=768,
        dpi=96.0,
        scale_factor=1.0,
        is_touch_enabled=False
    )


@pytest.fixture
def sample_constraints():
    """Sample layout constraints for testing."""
    return LayoutConstraints(
        min_content_width=200,
        max_content_width=1000,
        min_sidebar_width=150,
        max_sidebar_width=300,
        min_touch_target_size=44,
        max_columns=6
    )


@pytest.fixture
def sample_content_items(app):
    """Sample content items for testing."""
    items = []
    for i in range(3):
        widget = QWidget()
        widget.setObjectName(f"test_widget_{i}")
        
        item = ContentItem(
            widget=widget,
            priority=ContentPriority.MEDIUM,
            min_size=QSize(100, 50),
            preferred_size=QSize(200, 100),
            max_size=QSize(400, 200)
        )
        items.append(item)
    
    return items


class TestLayoutConstraints:
    """Test LayoutConstraints functionality."""
    
    def test_constraints_creation(self):
        """Test creating layout constraints."""
        constraints = LayoutConstraints(
            min_content_width=300,
            max_content_width=1200,
            min_touch_target_size=48
        )
        
        assert constraints.min_content_width == 300
        assert constraints.max_content_width == 1200
        assert constraints.min_touch_target_size == 48
        assert constraints.performance_budget_ms == 16.0  # Default


class TestContentItem:
    """Test ContentItem functionality."""
    
    @pytest.mark.usefixtures("app")
    def test_content_item_creation(self):
        """Test creating content items."""
        widget = QWidget()
        
        item = ContentItem(
            widget=widget,
            priority=ContentPriority.HIGH,
            min_size=QSize(100, 50),
            preferred_size=QSize(200, 100),
            can_collapse=False,
            can_hide=True
        )
        
        assert item.widget == widget
        assert item.priority == ContentPriority.HIGH
        assert item.min_size == QSize(100, 50)
        assert item.preferred_size == QSize(200, 100)
        assert item.can_collapse is False
        assert item.can_hide is True
        assert item.stretch_factor == 1  # Default
    
    @pytest.mark.usefixtures("app")
    def test_content_item_with_custom_adaptation(self):
        """Test content item with custom adaptation function."""
        widget = QWidget()
        
        def custom_adapter(layout):
            # Custom adaptation logic
            pass
        
        item = ContentItem(
            widget=widget,
            priority=ContentPriority.LOW,
            min_size=QSize(50, 25),
            preferred_size=QSize(100, 50),
            custom_adaptation=custom_adapter
        )
        
        assert item.custom_adaptation == custom_adapter


class TestLayoutSolution:
    """Test LayoutSolution functionality."""
    
    @pytest.mark.usefixtures("app")
    def test_solution_creation(self):
        """Test creating layout solutions."""
        widget = QWidget()
        
        solution = LayoutSolution(
            layout_type="test",
            widget_placements={widget: QRect(0, 0, 100, 50)},
            visibility_states={widget: True},
            scroll_requirements={widget: False},
            performance_score=85.0,
            usability_score=90.0,
            accessibility_score=80.0,
            total_score=85.0,
            adaptation_time_ms=15.5
        )
        
        assert solution.layout_type == "test"
        assert widget in solution.widget_placements
        assert solution.widget_placements[widget] == QRect(0, 0, 100, 50)
        assert solution.visibility_states[widget] is True
        assert solution.performance_score == 85.0
        assert solution.total_score == 85.0


class TestStackedLayoutAlgorithm:
    """Test StackedLayoutAlgorithm functionality."""
    
    def test_algorithm_properties(self):
        """Test algorithm basic properties."""
        algorithm = StackedLayoutAlgorithm()
        
        assert algorithm.get_algorithm_name() == "StackedLayout"
        assert algorithm.supports_constraints(LayoutConstraints()) is True
    
    def test_layout_calculation(self, sample_content_items, sample_constraints, sample_screen_properties):
        """Test stacked layout calculation."""
        algorithm = StackedLayoutAlgorithm()
        container_size = QSize(800, 600)
        
        solution = algorithm.calculate_layout(
            sample_content_items,
            container_size,
            sample_constraints,
            sample_screen_properties
        )
        
        assert isinstance(solution, LayoutSolution)
        assert solution.layout_type == "stacked"
        assert len(solution.widget_placements) <= len(sample_content_items)
        
        # Check that placements are valid
        for widget, rect in solution.widget_placements.items():
            assert isinstance(rect, QRect)
            assert rect.width() > 0
            assert rect.height() > 0
    
    def test_performance_scoring(self):
        """Test performance scoring logic."""
        algorithm = StackedLayoutAlgorithm()
        
        # Fewer widgets should score higher
        score_few = algorithm._calculate_performance_score(5)
        score_many = algorithm._calculate_performance_score(20)
        
        assert score_few > score_many
        assert score_few <= 100
        assert score_many >= 0
    
    def test_usability_scoring(self, sample_content_items):
        """Test usability scoring logic."""
        algorithm = StackedLayoutAlgorithm()
        
        # All visible should score higher than some hidden
        all_visible = {item.widget: True for item in sample_content_items}
        some_hidden = {item.widget: i < 2 for i, item in enumerate(sample_content_items)}
        
        score_all = algorithm._calculate_usability_score(sample_content_items, all_visible)
        score_some = algorithm._calculate_usability_score(sample_content_items, some_hidden)
        
        assert score_all > score_some
    
    def test_accessibility_scoring(self, sample_constraints, sample_screen_properties):
        """Test accessibility scoring logic."""
        algorithm = StackedLayoutAlgorithm()
        
        # Touch device with appropriate touch targets should score higher
        touch_props = ScreenProperties(480, 800, 150.0, 2.0, is_touch_enabled=True)
        touch_constraints = LayoutConstraints(min_touch_target_size=44)
        
        score_touch = algorithm._calculate_accessibility_score(touch_props, touch_constraints)
        score_desktop = algorithm._calculate_accessibility_score(sample_screen_properties, sample_constraints)
        
        assert score_touch > score_desktop


class TestSplitLayoutAlgorithm:
    """Test SplitLayoutAlgorithm functionality."""
    
    def test_algorithm_properties(self):
        """Test algorithm basic properties."""
        algorithm = SplitLayoutAlgorithm()
        
        assert algorithm.get_algorithm_name() == "SplitLayout"
        
        # Should support reasonable constraints
        reasonable_constraints = LayoutConstraints(min_content_width=300)
        assert algorithm.supports_constraints(reasonable_constraints) is True
        
        # Should not support very restrictive constraints
        restrictive_constraints = LayoutConstraints(min_content_width=800)
        assert algorithm.supports_constraints(restrictive_constraints) is False
    
    def test_split_configuration_calculation(self, sample_content_items, sample_constraints):
        """Test split configuration calculation."""
        algorithm = SplitLayoutAlgorithm()
        
        # Large container should use 3-column
        large_size = QSize(1400, 800)
        large_config = algorithm._calculate_optimal_split(sample_content_items, large_size, sample_constraints)
        assert large_config['type'] == '3-column'
        
        # Medium container should use 2-column
        medium_size = QSize(900, 600)
        medium_config = algorithm._calculate_optimal_split(sample_content_items, medium_size, sample_constraints)
        assert medium_config['type'] == '2-column'
        
        # Small container should use 1-column
        small_size = QSize(600, 400)
        small_config = algorithm._calculate_optimal_split(sample_content_items, small_size, sample_constraints)
        assert small_config['type'] == '1-column'
    
    def test_layout_calculation(self, sample_content_items, sample_constraints, sample_screen_properties):
        """Test split layout calculation."""
        algorithm = SplitLayoutAlgorithm()
        container_size = QSize(1200, 800)
        
        solution = algorithm.calculate_layout(
            sample_content_items,
            container_size,
            sample_constraints,
            sample_screen_properties
        )
        
        assert isinstance(solution, LayoutSolution)
        assert solution.layout_type == "split"
        
        # Should place all items (split layout rarely hides items)
        assert len(solution.widget_placements) == len(sample_content_items)
    
    def test_region_calculation(self, sample_constraints):
        """Test split region calculation."""
        algorithm = SplitLayoutAlgorithm()
        container_size = QSize(1200, 800)
        
        # Test 2-column configuration
        config = {'type': '2-column', 'left_ratio': 0.3, 'right_ratio': 0.7}
        regions = algorithm._calculate_split_regions(container_size, config, sample_constraints)
        
        assert 'left' in regions
        assert 'right' in regions
        
        left_rect = regions['left']
        right_rect = regions['right']
        
        # Regions should be within container
        assert left_rect.width() > 0
        assert right_rect.width() > 0
        assert left_rect.height() == right_rect.height()
        
        # Should roughly match ratios
        total_content_width = left_rect.width() + right_rect.width()
        left_ratio = left_rect.width() / total_content_width
        assert abs(left_ratio - 0.3) < 0.1  # Allow some tolerance for margins


class TestGridLayoutAlgorithm:
    """Test GridLayoutAlgorithm functionality."""
    
    def test_algorithm_properties(self):
        """Test algorithm basic properties."""
        algorithm = GridLayoutAlgorithm()
        
        assert algorithm.get_algorithm_name() == "GridLayout"
        
        # Should support constraints with multiple columns
        good_constraints = LayoutConstraints(max_columns=6)
        assert algorithm.supports_constraints(good_constraints) is True
        
        # Should not support single-column constraints
        bad_constraints = LayoutConstraints(max_columns=1)
        assert algorithm.supports_constraints(bad_constraints) is False
    
    def test_grid_calculation(self, sample_content_items, sample_constraints):
        """Test optimal grid calculation."""
        algorithm = GridLayoutAlgorithm()
        container_size = QSize(800, 600)
        
        grid_config = algorithm._calculate_optimal_grid(
            sample_content_items,
            container_size,
            sample_constraints
        )
        
        assert 'columns' in grid_config
        assert 'rows' in grid_config
        assert grid_config['columns'] >= 1
        assert grid_config['rows'] >= 1
        
        # Total cells should accommodate items
        total_cells = grid_config['columns'] * grid_config['rows']
        assert total_cells >= len(sample_content_items)
    
    def test_layout_calculation(self, sample_content_items, sample_constraints, sample_screen_properties):
        """Test grid layout calculation."""
        algorithm = GridLayoutAlgorithm()
        container_size = QSize(800, 600)
        
        solution = algorithm.calculate_layout(
            sample_content_items,
            container_size,
            sample_constraints,
            sample_screen_properties
        )
        
        assert isinstance(solution, LayoutSolution)
        assert solution.layout_type == "grid"
        
        # Check grid placement
        placed_widgets = list(solution.widget_placements.keys())
        assert len(placed_widgets) <= len(sample_content_items)


class TestAdaptiveLayoutEngine:
    """Test AdaptiveLayoutEngine functionality."""
    
    def test_engine_initialization(self, mock_breakpoint_manager):
        """Test engine initialization."""
        engine = AdaptiveLayoutEngine(mock_breakpoint_manager)
        
        assert engine._breakpoint_manager == mock_breakpoint_manager
        assert len(engine._algorithms) > 0
        assert engine._adaptation_strategy == AdaptationStrategy.BALANCED
        
        # Should have default algorithms
        algorithm_names = engine.get_available_algorithms()
        assert "StackedLayout" in algorithm_names
        assert "SplitLayout" in algorithm_names
        assert "GridLayout" in algorithm_names
    
    def test_algorithm_management(self, mock_breakpoint_manager):
        """Test adding and removing algorithms."""
        engine = AdaptiveLayoutEngine(mock_breakpoint_manager)
        initial_count = len(engine._algorithms)
        
        # Add custom algorithm
        class CustomAlgorithm(LayoutAlgorithm):
            def calculate_layout(self, content_items, container_size, constraints, screen_properties):
                return LayoutSolution("custom", {}, {}, {}, 50.0, 50.0, 50.0, 50.0, 10.0)
            
            def get_algorithm_name(self):
                return "CustomAlgorithm"
            
            def supports_constraints(self, constraints):
                return True
        
        custom_algo = CustomAlgorithm()
        engine.add_algorithm(custom_algo)
        
        assert len(engine._algorithms) == initial_count + 1
        assert "CustomAlgorithm" in engine._algorithms
        
        # Remove algorithm
        success = engine.remove_algorithm("CustomAlgorithm")
        assert success is True
        assert "CustomAlgorithm" not in engine._algorithms
    
    def test_content_management(self, mock_breakpoint_manager, sample_content_items):
        """Test content item management."""
        engine = AdaptiveLayoutEngine(mock_breakpoint_manager)
        
        # Set content items
        engine.set_content_items(sample_content_items)
        assert len(engine._content_items) == len(sample_content_items)
        
        # Add individual item
        new_widget = QWidget()
        new_item = ContentItem(
            widget=new_widget,
            priority=ContentPriority.HIGH,
            min_size=QSize(50, 25),
            preferred_size=QSize(100, 50)
        )
        
        engine.add_content_item(new_item)
        assert len(engine._content_items) == len(sample_content_items) + 1
        
        # Remove item
        success = engine.remove_content_item(new_widget)
        assert success is True
        assert len(engine._content_items) == len(sample_content_items)
    
    def test_adaptation_strategy(self, mock_breakpoint_manager):
        """Test adaptation strategy setting."""
        engine = AdaptiveLayoutEngine(mock_breakpoint_manager)
        
        engine.set_adaptation_strategy(AdaptationStrategy.PERFORMANCE_FIRST)
        assert engine._adaptation_strategy == AdaptationStrategy.PERFORMANCE_FIRST
    
    def test_layout_calculation(self, mock_breakpoint_manager, sample_content_items, sample_screen_properties):
        """Test adaptive layout calculation."""
        engine = AdaptiveLayoutEngine(mock_breakpoint_manager)
        engine.set_content_items(sample_content_items)
        
        container_size = QSize(1024, 768)
        
        solution = engine.calculate_adaptive_layout(container_size, sample_screen_properties)
        
        assert solution is not None
        assert isinstance(solution, LayoutSolution)
        assert solution.total_score > 0
    
    def test_algorithm_selection(self, mock_breakpoint_manager, sample_screen_properties):
        """Test algorithm selection logic."""
        engine = AdaptiveLayoutEngine(mock_breakpoint_manager)
        
        # Test mobile properties should prefer stacked layout
        mobile_props = ScreenProperties(480, 800, 150.0, 2.0, is_touch_enabled=True)
        mobile_algorithm = engine._select_best_algorithm(QSize(480, 800), mobile_props)
        assert isinstance(mobile_algorithm, StackedLayoutAlgorithm)
        
        # Test desktop properties should prefer split layout
        desktop_props = ScreenProperties(1920, 1080, 96.0, 1.0, is_touch_enabled=False)
        desktop_algorithm = engine._select_best_algorithm(QSize(1920, 1080), desktop_props)
        assert isinstance(desktop_algorithm, SplitLayoutAlgorithm)
    
    def test_caching(self, mock_breakpoint_manager, sample_content_items, sample_screen_properties):
        """Test solution caching."""
        engine = AdaptiveLayoutEngine(mock_breakpoint_manager)
        engine.set_content_items(sample_content_items)
        
        container_size = QSize(1024, 768)
        
        # First calculation
        solution1 = engine.calculate_adaptive_layout(container_size, sample_screen_properties)
        cache_size_after_first = len(engine._solution_cache)
        
        # Second calculation with same parameters should use cache
        solution2 = engine.calculate_adaptive_layout(container_size, sample_screen_properties)
        cache_size_after_second = len(engine._solution_cache)
        
        assert solution1 is not None
        assert solution2 is not None
        assert cache_size_after_first > 0
        assert cache_size_after_second >= cache_size_after_first
    
    def test_performance_metrics(self, mock_breakpoint_manager, sample_content_items, sample_screen_properties):
        """Test performance metrics collection."""
        engine = AdaptiveLayoutEngine(mock_breakpoint_manager)
        engine.set_content_items(sample_content_items)
        
        # Perform some calculations
        for i in range(3):
            container_size = QSize(1000 + i * 100, 700 + i * 50)
            engine.calculate_adaptive_layout(container_size, sample_screen_properties)
        
        metrics = engine.get_performance_metrics()
        assert len(metrics) > 0
        
        # Should have timing data for at least one algorithm
        assert any(time > 0 for time in metrics.values())


@pytest.mark.usefixtures("app")
class TestAdaptiveLayout:
    """Test AdaptiveLayout high-level interface."""
    
    def test_layout_initialization(self, mock_breakpoint_manager):
        """Test adaptive layout initialization."""
        container = QWidget()
        layout = AdaptiveLayout(container, mock_breakpoint_manager)
        
        assert layout._container == container
        assert layout._breakpoint_manager == mock_breakpoint_manager
        assert layout._engine is not None
        assert layout._adaptation_enabled is True
    
    def test_widget_management(self, mock_breakpoint_manager):
        """Test widget addition and removal."""
        container = QWidget()
        layout = AdaptiveLayout(container, mock_breakpoint_manager)
        
        # Add widget
        test_widget = QWidget()
        layout.add_widget(
            test_widget,
            priority=ContentPriority.HIGH,
            can_collapse=False,
            can_hide=True
        )
        
        # Should have added content item
        content_items = layout._engine._content_items
        assert len(content_items) == 1
        assert content_items[0].widget == test_widget
        assert content_items[0].priority == ContentPriority.HIGH
        
        # Remove widget
        success = layout.remove_widget(test_widget)
        assert success is True
        assert len(layout._engine._content_items) == 0
    
    def test_adaptation_control(self, mock_breakpoint_manager):
        """Test adaptation enable/disable."""
        container = QWidget()
        layout = AdaptiveLayout(container, mock_breakpoint_manager)
        
        # Disable adaptation
        layout.enable_adaptation(False)
        assert layout._adaptation_enabled is False
        
        # Enable adaptation
        layout.enable_adaptation(True)
        assert layout._adaptation_enabled is True
    
    def test_strategy_setting(self, mock_breakpoint_manager):
        """Test setting adaptation strategy."""
        container = QWidget()
        layout = AdaptiveLayout(container, mock_breakpoint_manager)
        
        layout.set_adaptation_strategy(AdaptationStrategy.ACCESSIBILITY_FIRST)
        assert layout._engine._adaptation_strategy == AdaptationStrategy.ACCESSIBILITY_FIRST


class TestStrategyAdjustments:
    """Test strategy-specific layout adjustments."""
    
    def test_performance_first_adjustments(self, mock_breakpoint_manager, sample_content_items, sample_screen_properties):
        """Test performance-first strategy adjustments."""
        engine = AdaptiveLayoutEngine(mock_breakpoint_manager)
        engine.set_content_items(sample_content_items)
        engine.set_adaptation_strategy(AdaptationStrategy.PERFORMANCE_FIRST)
        
        # Create initial solution
        container_size = QSize(800, 600)
        solution = engine.calculate_adaptive_layout(container_size, sample_screen_properties)
        
        assert solution is not None
        # Performance-first should potentially hide some items for better performance
    
    def test_accessibility_first_adjustments(self, mock_breakpoint_manager, sample_content_items):
        """Test accessibility-first strategy adjustments."""
        engine = AdaptiveLayoutEngine(mock_breakpoint_manager)
        engine.set_content_items(sample_content_items)
        engine.set_adaptation_strategy(AdaptationStrategy.ACCESSIBILITY_FIRST)
        
        # Touch device properties
        touch_props = ScreenProperties(768, 1024, 150.0, 2.0, is_touch_enabled=True)
        container_size = QSize(768, 1024)
        
        solution = engine.calculate_adaptive_layout(container_size, touch_props)
        
        assert solution is not None
        # Accessibility-first should ensure proper touch targets
    
    def test_content_first_adjustments(self, mock_breakpoint_manager, sample_screen_properties):
        """Test content-first strategy adjustments."""
        engine = AdaptiveLayoutEngine(mock_breakpoint_manager)
        engine.set_adaptation_strategy(AdaptationStrategy.CONTENT_FIRST)
        
        # Create items with different priorities
        high_priority_widget = QWidget()
        high_priority_item = ContentItem(
            widget=high_priority_widget,
            priority=ContentPriority.CRITICAL,
            min_size=QSize(100, 50),
            preferred_size=QSize(200, 100)
        )
        
        low_priority_widget = QWidget()
        low_priority_item = ContentItem(
            widget=low_priority_widget,
            priority=ContentPriority.LOW,
            min_size=QSize(50, 25),
            preferred_size=QSize(100, 50)
        )
        
        engine.set_content_items([high_priority_item, low_priority_item])
        
        container_size = QSize(300, 200)  # Small container
        solution = engine.calculate_adaptive_layout(container_size, sample_screen_properties)
        
        assert solution is not None
        # Content-first should prioritize high-priority content visibility


class TestIntegration:
    """Integration tests for adaptive layout system."""
    
    @pytest.mark.usefixtures("app")
    def test_full_system_integration(self, mock_breakpoint_manager):
        """Test integration of all adaptive layout components."""
        container = QWidget()
        container.resize(1024, 768)
        
        layout = AdaptiveLayout(container, mock_breakpoint_manager)
        
        # Add multiple widgets with different priorities
        for i in range(5):
            widget = QWidget()
            priority = [ContentPriority.LOW, ContentPriority.MEDIUM, ContentPriority.HIGH][i % 3]
            layout.add_widget(widget, priority=priority)
        
        # Force layout update
        layout.force_layout_update()
        
        # Should have a current solution
        solution = layout.get_current_solution()
        # Note: Might be None if layout update is async
    
    def test_performance_under_load(self, mock_breakpoint_manager, sample_content_items):
        """Test performance under high load."""
        engine = AdaptiveLayoutEngine(mock_breakpoint_manager)
        engine.set_content_items(sample_content_items)
        
        start_time = time.time()
        
        # Perform many layout calculations
        for i in range(100):
            screen_props = ScreenProperties(
                width=800 + i,
                height=600 + i // 2,
                dpi=96.0,
                scale_factor=1.0
            )
            container_size = QSize(800 + i, 600 + i // 2)
            
            engine.calculate_adaptive_layout(container_size, screen_props)
        
        elapsed = time.time() - start_time
        
        # Should complete in reasonable time
        assert elapsed < 2.0  # 2 seconds for 100 calculations
        
        # Performance metrics should show reasonable values
        metrics = engine.get_performance_metrics()
        assert len(metrics) > 0


if __name__ == "__main__":
    pytest.main([__file__])