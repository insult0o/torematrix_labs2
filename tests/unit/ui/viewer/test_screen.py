"""
Comprehensive test suite for screen management system.
Tests all classes and methods in src.torematrix.ui.viewer.screen.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from src.torematrix.ui.viewer.screen import (
    ScreenType,
    DPIMode,
    ScreenMetrics,
    ScreenConfiguration,
    ScreenManager,
    ScreenCoordinateMapper,
    screen_manager
)
from src.torematrix.ui.viewer.coordinates import Point, Rectangle


class TestScreenMetrics:
    """Test ScreenMetrics class functionality."""
    
    def test_screen_metrics_creation(self):
        """Test screen metrics creation."""
        metrics = ScreenMetrics(
            logical_dpi=96.0,
            physical_dpi=108.0,
            scale_factor=1.5,
            pixel_density=4.25,
            color_depth=24,
            refresh_rate=60.0,
            orientation=90
        )
        
        assert metrics.logical_dpi == 96.0
        assert metrics.physical_dpi == 108.0
        assert metrics.scale_factor == 1.5
        assert metrics.pixel_density == 4.25
        assert metrics.color_depth == 24
        assert metrics.refresh_rate == 60.0
        assert metrics.orientation == 90
    
    def test_screen_metrics_copy(self):
        """Test screen metrics copying."""
        original = ScreenMetrics(
            logical_dpi=96.0,
            physical_dpi=108.0,
            scale_factor=1.5,
            pixel_density=4.25,
            color_depth=24,
            refresh_rate=60.0
        )
        
        copy = original.copy()
        
        assert copy.logical_dpi == original.logical_dpi
        assert copy.physical_dpi == original.physical_dpi
        assert copy.scale_factor == original.scale_factor
        assert copy.pixel_density == original.pixel_density
        assert copy.color_depth == original.color_depth
        assert copy.refresh_rate == original.refresh_rate
        
        # Should be different objects
        assert copy is not original


class TestScreenConfiguration:
    """Test ScreenConfiguration class functionality."""
    
    def test_screen_configuration_creation(self):
        """Test screen configuration creation."""
        metrics = ScreenMetrics(
            logical_dpi=96.0,
            physical_dpi=108.0,
            scale_factor=1.5,
            pixel_density=4.25,
            color_depth=24,
            refresh_rate=60.0
        )
        
        geometry = Rectangle(0, 0, 1920, 1080)
        available_geometry = Rectangle(0, 40, 1920, 1040)
        position = Point(0, 0)
        
        config = ScreenConfiguration(
            screen_id="screen_1",
            name="Primary Monitor",
            screen_type=ScreenType.PRIMARY,
            geometry=geometry,
            available_geometry=available_geometry,
            metrics=metrics,
            is_enabled=True,
            position_in_layout=position
        )
        
        assert config.screen_id == "screen_1"
        assert config.name == "Primary Monitor"
        assert config.screen_type == ScreenType.PRIMARY
        assert config.geometry == geometry
        assert config.available_geometry == available_geometry
        assert config.metrics == metrics
        assert config.is_enabled is True
        assert config.position_in_layout == position
    
    def test_screen_configuration_copy(self):
        """Test screen configuration copying."""
        metrics = ScreenMetrics(96.0, 108.0, 1.5, 4.25, 24, 60.0)
        geometry = Rectangle(0, 0, 1920, 1080)
        available_geometry = Rectangle(0, 40, 1920, 1040)
        position = Point(100, 200)
        
        original = ScreenConfiguration(
            screen_id="screen_1",
            name="Test Monitor",
            screen_type=ScreenType.SECONDARY,
            geometry=geometry,
            available_geometry=available_geometry,
            metrics=metrics,
            position_in_layout=position
        )
        
        copy = original.copy()
        
        assert copy.screen_id == original.screen_id
        assert copy.name == original.name
        assert copy.screen_type == original.screen_type
        assert copy.is_enabled == original.is_enabled
        
        # Geometry should be copied
        assert copy.geometry.x == original.geometry.x
        assert copy.geometry.y == original.geometry.y
        assert copy.geometry.width == original.geometry.width
        assert copy.geometry.height == original.geometry.height
        
        # Position should be copied
        assert copy.position_in_layout.x == original.position_in_layout.x
        assert copy.position_in_layout.y == original.position_in_layout.y
        
        # Should be different objects
        assert copy is not original
        assert copy.geometry is not original.geometry
        assert copy.metrics is not original.metrics


class TestScreenManager:
    """Test ScreenManager class functionality."""
    
    @pytest.fixture
    def mock_qt_screens(self):
        """Create mock Qt screens for testing."""
        mock_screen1 = Mock()
        mock_screen1.name.return_value = "Primary"
        mock_screen1.geometry.return_value = Mock()
        mock_screen1.geometry().x.return_value = 0
        mock_screen1.geometry().y.return_value = 0
        mock_screen1.geometry().width.return_value = 1920
        mock_screen1.geometry().height.return_value = 1080
        mock_screen1.availableGeometry.return_value = Mock()
        mock_screen1.availableGeometry().x.return_value = 0
        mock_screen1.availableGeometry().y.return_value = 40
        mock_screen1.availableGeometry().width.return_value = 1920
        mock_screen1.availableGeometry().height.return_value = 1040
        mock_screen1.logicalDotsPerInch.return_value = 96.0
        mock_screen1.physicalDotsPerInch.return_value = 108.0
        mock_screen1.devicePixelRatio.return_value = 1.0
        mock_screen1.depth.return_value = 24
        mock_screen1.refreshRate.return_value = 60.0
        
        mock_screen2 = Mock()
        mock_screen2.name.return_value = "Secondary"
        mock_screen2.geometry.return_value = Mock()
        mock_screen2.geometry().x.return_value = 1920
        mock_screen2.geometry().y.return_value = 0
        mock_screen2.geometry().width.return_value = 1280
        mock_screen2.geometry().height.return_value = 1024
        mock_screen2.availableGeometry.return_value = Mock()
        mock_screen2.availableGeometry().x.return_value = 1920
        mock_screen2.availableGeometry().y.return_value = 40
        mock_screen2.availableGeometry().width.return_value = 1280
        mock_screen2.availableGeometry().height.return_value = 984
        mock_screen2.logicalDotsPerInch.return_value = 96.0
        mock_screen2.physicalDotsPerInch.return_value = 96.0
        mock_screen2.devicePixelRatio.return_value = 1.0
        mock_screen2.depth.return_value = 24
        mock_screen2.refreshRate.return_value = 75.0
        
        return mock_screen1, mock_screen2
    
    @pytest.fixture
    def screen_manager_instance(self, mock_qt_screens):
        """Create a screen manager instance for testing."""
        mock_screen1, mock_screen2 = mock_qt_screens
        
        with patch('src.torematrix.ui.viewer.screen.QApplication') as mock_app:
            mock_app.instance.return_value = mock_app
            mock_app.screens.return_value = [mock_screen1, mock_screen2]
            mock_app.primaryScreen.return_value = mock_screen1
            
            manager = ScreenManager()
            yield manager
    
    def test_screen_manager_initialization(self, screen_manager_instance):
        """Test screen manager initialization."""
        manager = screen_manager_instance
        
        assert manager.get_screen_count() >= 0
        assert manager._dpi_mode == DPIMode.SYSTEM
        assert manager._custom_dpi_scale == 1.0
    
    def test_screen_detection(self, screen_manager_instance):
        """Test screen detection."""
        manager = screen_manager_instance
        
        # Should have detected screens
        screen_count = manager.get_screen_count()
        assert screen_count > 0
        
        # Should have primary screen
        primary_id = manager.get_primary_screen_id()
        assert primary_id is not None
        
        # Should have configurations
        configs = manager.get_screen_configurations()
        assert len(configs) == screen_count
        
        for config in configs:
            assert isinstance(config, ScreenConfiguration)
            assert config.screen_id
            assert config.name
            assert config.geometry.width > 0
            assert config.geometry.height > 0
    
    def test_primary_screen_operations(self, screen_manager_instance):
        """Test primary screen operations."""
        manager = screen_manager_instance
        
        primary_id = manager.get_primary_screen_id()
        assert primary_id is not None
        
        primary_config = manager.get_primary_screen_configuration()
        assert primary_config is not None
        assert primary_config.screen_id == primary_id
        assert primary_config.screen_type == ScreenType.PRIMARY
    
    def test_current_screen_operations(self, screen_manager_instance):
        """Test current screen operations."""
        manager = screen_manager_instance
        
        # Should have current screen set
        current_id = manager.get_current_screen_id()
        
        if current_id:
            current_config = manager.get_current_screen_configuration()
            assert current_config is not None
            assert current_config.screen_id == current_id
        
        # Test setting current screen
        configs = manager.get_screen_configurations()
        if configs:
            first_screen_id = configs[0].screen_id
            success = manager.set_current_screen(first_screen_id)
            assert success
            
            assert manager.get_current_screen_id() == first_screen_id
        
        # Test setting invalid screen
        success = manager.set_current_screen("invalid_screen_id")
        assert not success
    
    def test_screen_at_point(self, screen_manager_instance):
        """Test finding screen at point."""
        manager = screen_manager_instance
        
        configs = manager.get_screen_configurations()
        if configs:
            config = configs[0]
            
            # Point inside screen
            point_inside = Point(
                config.geometry.x + config.geometry.width // 2,
                config.geometry.y + config.geometry.height // 2
            )
            
            screen_id = manager.get_screen_at_point(point_inside)
            assert screen_id == config.screen_id
            
            # Point outside all screens
            point_outside = Point(-1000, -1000)
            screen_id = manager.get_screen_at_point(point_outside)
            assert screen_id is None
    
    def test_widget_screen_detection(self, screen_manager_instance):
        """Test widget screen detection."""
        manager = screen_manager_instance
        
        # Create mock widget
        mock_widget = Mock()
        mock_window = Mock()
        mock_screen = Mock()
        
        mock_widget.window.return_value = mock_window
        mock_window.screen.return_value = mock_screen
        mock_screen.name.return_value = "TestScreen"
        
        # Mock the screen ID conversion
        with patch.object(manager, '_qt_screen_to_id', return_value='test_screen_id'):
            screen_id = manager.get_screen_for_widget(mock_widget)
            # Might be None if screen not in our detected screens
    
    def test_point_mapping_between_screens(self, screen_manager_instance):
        """Test point mapping between screens."""
        manager = screen_manager_instance
        
        configs = manager.get_screen_configurations()
        if len(configs) >= 2:
            screen1_id = configs[0].screen_id
            screen2_id = configs[1].screen_id
            
            # Test mapping point between screens
            point = Point(100, 200)
            mapped_point = manager.map_point_to_screen(point, screen1_id, screen2_id)
            
            assert isinstance(mapped_point, Point)
            
            # Mapping to same screen should return same point
            same_point = manager.map_point_to_screen(point, screen1_id, screen1_id)
            assert same_point.x == point.x
            assert same_point.y == point.y
    
    def test_rectangle_mapping_between_screens(self, screen_manager_instance):
        """Test rectangle mapping between screens."""
        manager = screen_manager_instance
        
        configs = manager.get_screen_configurations()
        if len(configs) >= 2:
            screen1_id = configs[0].screen_id
            screen2_id = configs[1].screen_id
            
            # Test mapping rectangle between screens
            rect = Rectangle(50, 100, 300, 200)
            mapped_rect = manager.map_rectangle_to_screen(rect, screen1_id, screen2_id)
            
            assert isinstance(mapped_rect, Rectangle)
            assert mapped_rect.width > 0
            assert mapped_rect.height > 0
            
            # Mapping to same screen should return same rectangle
            same_rect = manager.map_rectangle_to_screen(rect, screen1_id, screen1_id)
            assert same_rect.x == rect.x
            assert same_rect.y == rect.y
            assert same_rect.width == rect.width
            assert same_rect.height == rect.height
    
    def test_dpi_operations(self, screen_manager_instance):
        """Test DPI-related operations."""
        manager = screen_manager_instance
        
        configs = manager.get_screen_configurations()
        if configs:
            screen_id = configs[0].screen_id
            
            # Test getting effective DPI
            dpi = manager.get_effective_dpi(screen_id)
            assert dpi > 0
            
            # Test getting effective scale factor
            scale = manager.get_effective_scale_factor(screen_id)
            assert scale > 0
            
            # Test setting DPI mode
            manager.set_dpi_mode(DPIMode.AWARE)
            assert manager._dpi_mode == DPIMode.AWARE
            
            # Test custom DPI scale
            manager.set_custom_dpi_scale(1.5)
            assert manager._custom_dpi_scale == 1.5
            
            # Test screen DPI override
            manager.set_screen_dpi_override(screen_id, 120.0)
            assert screen_id in manager._dpi_override
            assert manager._dpi_override[screen_id] == 120.0
            
            # Test removing override
            manager.remove_screen_dpi_override(screen_id)
            assert screen_id not in manager._dpi_override
    
    def test_virtual_desktop_bounds(self, screen_manager_instance):
        """Test virtual desktop bounds calculation."""
        manager = screen_manager_instance
        
        bounds = manager.get_virtual_desktop_bounds()
        
        assert isinstance(bounds, Rectangle)
        assert bounds.width > 0
        assert bounds.height > 0
    
    def test_performance_metrics(self, screen_manager_instance):
        """Test performance metrics."""
        manager = screen_manager_instance
        
        # Perform some operations to generate metrics
        configs = manager.get_screen_configurations()
        if configs:
            screen_id = configs[0].screen_id
            manager.get_effective_dpi(screen_id)
            manager.get_effective_scale_factor(screen_id)
        
        metrics = manager.get_screen_performance_metrics()
        
        assert 'screen_count' in metrics
        assert 'screen_queries' in metrics
        assert 'cache_hits' in metrics
        assert 'cache_hit_rate' in metrics
        assert 'last_detection_time' in metrics
        assert 'monitor_interval' in metrics
        assert 'dpi_mode' in metrics
        assert 'custom_dpi_scale' in metrics
        assert 'dpi_overrides' in metrics
        
        assert metrics['screen_count'] >= 0
        assert metrics['cache_hit_rate'] >= 0.0
    
    def test_widget_tracking(self, screen_manager_instance):
        """Test widget tracking functionality."""
        manager = screen_manager_instance
        
        # Create mock widget
        mock_widget = Mock()
        mock_window = Mock()
        mock_screen = Mock()
        
        mock_widget.window.return_value = mock_window
        mock_widget.isVisible.return_value = True
        mock_window.screen.return_value = mock_screen
        mock_screen.name.return_value = "TestScreen"
        
        # Test tracking widget
        manager.track_widget(mock_widget)
        
        # Test untracking widget
        manager.untrack_widget(mock_widget)
    
    def test_signal_emissions(self, mock_qt_screens):
        """Test signal emissions."""
        mock_screen1, mock_screen2 = mock_qt_screens
        
        with patch('src.torematrix.ui.viewer.screen.QApplication') as mock_app:
            mock_app.instance.return_value = mock_app
            mock_app.screens.return_value = [mock_screen1]
            mock_app.primaryScreen.return_value = mock_screen1
            
            manager = ScreenManager()
            
            # Track signal emissions
            screen_added_signals = []
            screen_removed_signals = []
            screen_changed_signals = []
            primary_changed_signals = []
            dpi_changed_signals = []
            
            manager.screen_added.connect(lambda config: screen_added_signals.append(config))
            manager.screen_removed.connect(lambda screen_id: screen_removed_signals.append(screen_id))
            manager.screen_changed.connect(lambda config: screen_changed_signals.append(config))
            manager.primary_screen_changed.connect(lambda screen_id: primary_changed_signals.append(screen_id))
            manager.dpi_changed.connect(lambda screen_id, dpi: dpi_changed_signals.append((screen_id, dpi)))
            
            # Simulate screen changes
            mock_app.screens.return_value = [mock_screen1, mock_screen2]
            manager._detect_all_screens()
            
            # Should have detected new screen
            assert len(screen_added_signals) > 0
            
            # Test DPI change signal
            configs = manager.get_screen_configurations()
            if configs:
                manager.set_dpi_mode(DPIMode.AWARE)
                # Should emit DPI change signals
    
    def test_initialization_and_shutdown(self, screen_manager_instance):
        """Test initialization and shutdown."""
        manager = screen_manager_instance
        
        # Test initialization
        manager.initialize()
        
        # Should not crash and should maintain state
        assert manager.get_screen_count() >= 0
        
        # Test shutdown
        manager.shutdown()
        
        # Should have cleared state
        assert len(manager._screens) == 0
        assert len(manager._tracked_windows) == 0
        assert len(manager._window_screen_cache) == 0


class TestScreenCoordinateMapper:
    """Test ScreenCoordinateMapper class functionality."""
    
    @pytest.fixture
    def coordinate_mapper(self, screen_manager_instance):
        """Create a coordinate mapper for testing."""
        return ScreenCoordinateMapper(screen_manager_instance)
    
    def test_coordinate_mapper_initialization(self, coordinate_mapper):
        """Test coordinate mapper initialization."""
        mapper = coordinate_mapper
        
        assert mapper._screen_manager is not None
        assert mapper._cache_max_size == 1000
        assert len(mapper._coordinate_cache) == 0
    
    def test_document_to_screen_mapping(self, coordinate_mapper, screen_manager_instance):
        """Test document to screen coordinate mapping."""
        mapper = coordinate_mapper
        manager = screen_manager_instance
        
        configs = manager.get_screen_configurations()
        if configs:
            screen_id = configs[0].screen_id
            
            document_bounds = Rectangle(0, 0, 1000, 800)
            doc_point = Point(500, 400)  # Center of document
            
            screen_point = mapper.map_document_to_screen(doc_point, document_bounds, screen_id)
            
            assert isinstance(screen_point, Point)
            # Should map to somewhere in screen space
    
    def test_screen_to_document_mapping(self, coordinate_mapper, screen_manager_instance):
        """Test screen to document coordinate mapping."""
        mapper = coordinate_mapper
        manager = screen_manager_instance
        
        configs = manager.get_screen_configurations()
        if configs:
            screen_id = configs[0].screen_id
            
            document_bounds = Rectangle(0, 0, 1000, 800)
            screen_point = Point(960, 540)  # Screen center
            
            doc_point = mapper.map_screen_to_document(screen_point, document_bounds, screen_id)
            
            assert isinstance(doc_point, Point)
            # Should map to somewhere in document space
    
    def test_round_trip_coordinate_mapping(self, coordinate_mapper, screen_manager_instance):
        """Test round-trip coordinate mapping."""
        mapper = coordinate_mapper
        manager = screen_manager_instance
        
        configs = manager.get_screen_configurations()
        if configs:
            screen_id = configs[0].screen_id
            
            document_bounds = Rectangle(0, 0, 1000, 800)
            original_doc_point = Point(250, 600)
            
            # Document -> Screen -> Document
            screen_point = mapper.map_document_to_screen(original_doc_point, document_bounds, screen_id)
            back_to_doc = mapper.map_screen_to_document(screen_point, document_bounds, screen_id)
            
            # Should be close to original (allowing for floating point errors and scaling)
            assert abs(back_to_doc.x - original_doc_point.x) < 10
            assert abs(back_to_doc.y - original_doc_point.y) < 10
    
    def test_optimal_screen_selection(self, coordinate_mapper, screen_manager_instance):
        """Test optimal screen selection for document."""
        mapper = coordinate_mapper
        
        document_bounds = Rectangle(0, 0, 1920, 1080)
        optimal_screen = mapper.get_optimal_screen_for_document(document_bounds)
        
        # Should return a screen ID or None if no screens
        if optimal_screen:
            assert isinstance(optimal_screen, str)
    
    def test_cache_operations(self, coordinate_mapper):
        """Test coordinate mapper cache operations."""
        mapper = coordinate_mapper
        
        # Add some entries to cache
        mapper._coordinate_cache["test_key"] = (Point(10, 20), Point(30, 40))
        
        assert len(mapper._coordinate_cache) == 1
        
        # Clear cache
        mapper.clear_cache()
        
        assert len(mapper._coordinate_cache) == 0


class TestScreenManagerIntegration:
    """Test screen manager integration with other components."""
    
    def test_global_screen_manager_instance(self):
        """Test global screen manager instance."""
        # Test that global instance exists
        assert screen_manager is not None
        assert isinstance(screen_manager, ScreenManager)
    
    def test_screen_manager_with_qt_application(self):
        """Test screen manager with Qt application."""
        # This test verifies behavior when Qt application is available
        with patch('src.torematrix.ui.viewer.screen.QApplication') as mock_app:
            mock_screen = Mock()
            mock_screen.name.return_value = "Test"
            mock_screen.geometry.return_value = Mock()
            mock_screen.geometry().x.return_value = 0
            mock_screen.geometry().y.return_value = 0
            mock_screen.geometry().width.return_value = 1920
            mock_screen.geometry().height.return_value = 1080
            mock_screen.availableGeometry.return_value = Mock()
            mock_screen.availableGeometry().x.return_value = 0
            mock_screen.availableGeometry().y.return_value = 40
            mock_screen.availableGeometry().width.return_value = 1920
            mock_screen.availableGeometry().height.return_value = 1040
            mock_screen.logicalDotsPerInch.return_value = 96.0
            mock_screen.physicalDotsPerInch.return_value = 108.0
            mock_screen.devicePixelRatio.return_value = 1.0
            mock_screen.depth.return_value = 24
            mock_screen.refreshRate.return_value = 60.0
            
            mock_app.instance.return_value = mock_app
            mock_app.screens.return_value = [mock_screen]
            mock_app.primaryScreen.return_value = mock_screen
            mock_app.screenAdded = Mock()
            mock_app.screenRemoved = Mock()
            mock_app.primaryScreenChanged = Mock()
            
            manager = ScreenManager()
            
            # Should have detected the screen
            assert manager.get_screen_count() > 0
    
    def test_screen_manager_without_qt_application(self):
        """Test screen manager behavior without Qt application."""
        with patch('src.torematrix.ui.viewer.screen.QApplication') as mock_app:
            mock_app.instance.return_value = None
            
            manager = ScreenManager()
            
            # Should handle gracefully
            manager._detect_all_screens()
            
            # Should have default behavior
            assert manager.get_screen_count() >= 0


class TestScreenManagerErrorHandling:
    """Test screen manager error handling and edge cases."""
    
    def test_invalid_screen_operations(self):
        """Test operations with invalid screen IDs."""
        with patch('src.torematrix.ui.viewer.screen.QApplication') as mock_app:
            mock_app.instance.return_value = None
            
            manager = ScreenManager()
            
            # Test getting invalid screen configuration
            config = manager.get_screen_configuration("invalid_id")
            assert config is None
            
            # Test mapping with invalid screen IDs
            point = Point(100, 200)
            mapped = manager.map_point_to_screen(point, "invalid1", "invalid2")
            assert mapped == point  # Should return original point
            
            # Test DPI operations with invalid screen
            dpi = manager.get_effective_dpi("invalid_id")
            assert dpi == 96.0  # Default DPI
            
            scale = manager.get_effective_scale_factor("invalid_id")
            assert scale == 1.0  # Default scale
    
    def test_widget_operations_with_invalid_widget(self):
        """Test widget operations with invalid widgets."""
        with patch('src.torematrix.ui.viewer.screen.QApplication') as mock_app:
            mock_app.instance.return_value = None
            
            manager = ScreenManager()
            
            # Test with widget that has no window
            mock_widget = Mock()
            mock_widget.window.return_value = None
            
            screen_id = manager.get_screen_for_widget(mock_widget)
            assert screen_id is None
            
            # Test tracking invalid widget
            manager.track_widget(mock_widget)  # Should not crash
            manager.untrack_widget(mock_widget)  # Should not crash
    
    def test_coordinate_mapper_with_invalid_screen(self):
        """Test coordinate mapper with invalid screen."""
        with patch('src.torematrix.ui.viewer.screen.QApplication') as mock_app:
            mock_app.instance.return_value = None
            
            manager = ScreenManager()
            mapper = ScreenCoordinateMapper(manager)
            
            document_bounds = Rectangle(0, 0, 1000, 800)
            point = Point(500, 400)
            
            # Should return original point for invalid screen
            result = mapper.map_document_to_screen(point, document_bounds, "invalid_id")
            assert result == point
            
            result = mapper.map_screen_to_document(point, document_bounds, "invalid_id")
            assert result == point
    
    def test_dpi_mode_edge_cases(self):
        """Test DPI mode edge cases."""
        with patch('src.torematrix.ui.viewer.screen.QApplication') as mock_app:
            mock_screen = Mock()
            mock_screen.name.return_value = "Test"
            mock_screen.geometry.return_value = Mock()
            mock_screen.geometry().x.return_value = 0
            mock_screen.geometry().y.return_value = 0
            mock_screen.geometry().width.return_value = 1920
            mock_screen.geometry().height.return_value = 1080
            mock_screen.availableGeometry.return_value = Mock()
            mock_screen.availableGeometry().x.return_value = 0
            mock_screen.availableGeometry().y.return_value = 40
            mock_screen.availableGeometry().width.return_value = 1920
            mock_screen.availableGeometry().height.return_value = 1040
            mock_screen.logicalDotsPerInch.return_value = 96.0
            mock_screen.physicalDotsPerInch.return_value = 108.0
            mock_screen.devicePixelRatio.return_value = 2.0
            mock_screen.depth.return_value = 24
            mock_screen.refreshRate.return_value = 60.0
            
            mock_app.instance.return_value = mock_app
            mock_app.screens.return_value = [mock_screen]
            mock_app.primaryScreen.return_value = mock_screen
            
            manager = ScreenManager()
            
            configs = manager.get_screen_configurations()
            if configs:
                screen_id = configs[0].screen_id
                
                # Test different DPI modes
                for mode in DPIMode:
                    manager.set_dpi_mode(mode)
                    dpi = manager.get_effective_dpi(screen_id)
                    scale = manager.get_effective_scale_factor(screen_id)
                    
                    assert dpi > 0
                    assert scale > 0
                
                # Test extreme custom scale values
                manager.set_custom_dpi_scale(0.1)
                scale = manager.get_effective_scale_factor(screen_id)
                assert scale > 0
                
                manager.set_custom_dpi_scale(10.0)
                scale = manager.get_effective_scale_factor(screen_id)
                assert scale > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])