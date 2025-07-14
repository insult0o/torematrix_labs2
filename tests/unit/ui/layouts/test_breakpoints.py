"""Tests for the breakpoint management system."""

import pytest
from unittest.mock import Mock, patch
import time
from datetime import datetime, timedelta

from src.torematrix.ui.layouts.breakpoints import (
    BreakpointType, DeviceClass, BreakpointDefinition, BreakpointEvent,
    DeviceProfile, BreakpointCalculator, BreakpointManager
)
from src.torematrix.core.config import ConfigurationManager


@pytest.fixture
def mock_config_manager():
    """Mock config manager for testing."""
    manager = Mock(spec=ConfigManager)
    manager.get.return_value = {}
    return manager


@pytest.fixture
def sample_breakpoint():
    """Sample breakpoint definition for testing."""
    return BreakpointDefinition(
        name="md",
        type=BreakpointType.CONTAINER_WIDTH,
        min_value=768,
        max_value=991,
        device_classes={DeviceClass.TABLET_PORTRAIT, DeviceClass.TABLET_LANDSCAPE},
        priority=80
    )


@pytest.fixture
def sample_device_profile():
    """Sample device profile for testing."""
    return DeviceProfile(
        name="Tablet",
        device_class=DeviceClass.TABLET_LANDSCAPE,
        typical_widths=[1024, 1280],
        typical_heights=[768, 800],
        typical_dpi_range=(120, 160),
        touch_enabled=True,
        preferred_breakpoints=["md", "lg"]
    )


class TestBreakpointDefinition:
    """Test BreakpointDefinition functionality."""
    
    def test_breakpoint_creation(self):
        """Test creating a breakpoint definition."""
        bp = BreakpointDefinition(
            name="test",
            type=BreakpointType.CONTAINER_WIDTH,
            min_value=100,
            max_value=200,
            priority=50
        )
        
        assert bp.name == "test"
        assert bp.type == BreakpointType.CONTAINER_WIDTH
        assert bp.min_value == 100
        assert bp.max_value == 200
        assert bp.priority == 50
    
    def test_breakpoint_validation(self):
        """Test breakpoint validation."""
        # Valid breakpoint
        bp = BreakpointDefinition(
            name="valid",
            type=BreakpointType.CONTAINER_WIDTH,
            min_value=100,
            max_value=200
        )
        assert bp.min_value < bp.max_value
        
        # Invalid breakpoint should raise error
        with pytest.raises(ValueError):
            BreakpointDefinition(
                name="invalid",
                type=BreakpointType.CONTAINER_WIDTH,
                min_value=200,
                max_value=100
            )
    
    def test_breakpoint_matching_basic(self):
        """Test basic breakpoint matching."""
        bp = BreakpointDefinition(
            name="test",
            type=BreakpointType.CONTAINER_WIDTH,
            min_value=100,
            max_value=200
        )
        
        assert bp.matches(150) is True
        assert bp.matches(50) is False
        assert bp.matches(250) is False
        assert bp.matches(100) is True  # Boundary case
        assert bp.matches(200) is True  # Boundary case
    
    def test_breakpoint_matching_with_context(self):
        """Test breakpoint matching with custom conditions."""
        def custom_condition(context):
            return context.get('device_type') == 'mobile'
        
        bp = BreakpointDefinition(
            name="mobile_custom",
            type=BreakpointType.CONTAINER_WIDTH,
            min_value=100,
            max_value=500,
            custom_condition=custom_condition
        )
        
        # Should match width and context
        assert bp.matches(300, {'device_type': 'mobile'}) is True
        
        # Should not match wrong context
        assert bp.matches(300, {'device_type': 'desktop'}) is False
        
        # Should not match without context
        assert bp.matches(300, {}) is False
    
    def test_breakpoint_open_ended(self):
        """Test open-ended breakpoints."""
        # No maximum
        bp_no_max = BreakpointDefinition(
            name="large",
            type=BreakpointType.CONTAINER_WIDTH,
            min_value=1000
        )
        
        assert bp_no_max.matches(1500) is True
        assert bp_no_max.matches(5000) is True
        assert bp_no_max.matches(500) is False
        
        # No minimum
        bp_no_min = BreakpointDefinition(
            name="small",
            type=BreakpointType.CONTAINER_WIDTH,
            max_value=500
        )
        
        assert bp_no_min.matches(300) is True
        assert bp_no_min.matches(100) is True
        assert bp_no_min.matches(600) is False


class TestBreakpointCalculator:
    """Test BreakpointCalculator functionality."""
    
    def test_content_breakpoints_calculation(self):
        """Test calculation of content-based breakpoints."""
        calculator = BreakpointCalculator()
        
        # Sample content widths
        content_widths = [200, 250, 300]
        
        breakpoints = calculator.calculate_content_breakpoints(
            content_widths,
            min_items_per_row=1,
            max_items_per_row=3,
            margin=16
        )
        
        assert len(breakpoints) > 0
        assert all(isinstance(bp, int) for bp in breakpoints)
        assert breakpoints == sorted(breakpoints)  # Should be sorted
    
    def test_content_breakpoints_caching(self):
        """Test caching of content breakpoint calculations."""
        calculator = BreakpointCalculator()
        
        content_widths = [200, 250, 300]
        
        # First calculation
        breakpoints1 = calculator.calculate_content_breakpoints(content_widths)
        
        # Second calculation with same parameters should use cache
        breakpoints2 = calculator.calculate_content_breakpoints(content_widths)
        
        assert breakpoints1 == breakpoints2
        
        # Cache should have an entry
        assert len(calculator._content_analysis_cache) > 0
    
    def test_natural_breakpoints_calculation(self):
        """Test calculation of natural breakpoints."""
        from PyQt6.QtCore import QSize
        
        calculator = BreakpointCalculator()
        
        widget_sizes = [
            QSize(200, 150),
            QSize(250, 200),
            QSize(300, 250),
            QSize(210, 160),  # Similar to first
            QSize(800, 600)   # Very different
        ]
        
        breakpoints = calculator.calculate_natural_breakpoints(widget_sizes)
        
        assert len(breakpoints) > 0
        assert all(isinstance(bp, BreakpointDefinition) for bp in breakpoints)
        
        # Check that breakpoints have natural naming
        for bp in breakpoints:
            assert bp.name.startswith('natural_')
            assert bp.metadata.get('auto_generated') is True
    
    def test_clustering_algorithm(self):
        """Test the clustering algorithm."""
        calculator = BreakpointCalculator()
        
        # Values with clear clusters
        values = [100, 105, 110, 200, 205, 210, 500]
        
        clusters = calculator._find_clusters(values, tolerance=0.1)
        
        # Should find 3 clusters around 100, 200, and 500
        assert len(clusters) == 3
        assert 100 in clusters
        assert 200 in clusters or 205 in clusters  # Could be either
        assert 500 in clusters


class TestBreakpointManager:
    """Test BreakpointManager functionality."""
    
    def test_manager_initialization(self, mock_config_manager):
        """Test manager initialization."""
        manager = BreakpointManager(mock_config_manager)
        
        # Should have default breakpoints
        assert len(manager._breakpoints) > 0
        
        # Should have device profiles
        assert len(manager._device_profiles) > 0
        
        # Check for standard breakpoints
        assert "xs" in manager._breakpoints
        assert "sm" in manager._breakpoints
        assert "md" in manager._breakpoints
        assert "lg" in manager._breakpoints
        assert "xl" in manager._breakpoints
        assert "xxl" in manager._breakpoints
    
    def test_breakpoint_management(self, mock_config_manager, sample_breakpoint):
        """Test adding and removing breakpoints."""
        manager = BreakpointManager(mock_config_manager)
        initial_count = len(manager._breakpoints)
        
        # Add breakpoint
        manager.add_breakpoint(sample_breakpoint)
        assert len(manager._breakpoints) == initial_count + 1
        assert "md" in manager._breakpoints
        
        # Remove breakpoint
        success = manager.remove_breakpoint("md")
        assert success is True
        assert "md" not in manager._breakpoints
        
        # Try to remove non-existent breakpoint
        success = manager.remove_breakpoint("nonexistent")
        assert success is False
    
    def test_breakpoint_evaluation(self, mock_config_manager):
        """Test breakpoint evaluation."""
        manager = BreakpointManager(mock_config_manager)
        
        # Test width-based evaluation
        breakpoint = manager.evaluate_breakpoint(
            800, BreakpointType.CONTAINER_WIDTH
        )
        
        assert breakpoint is not None
        assert isinstance(breakpoint, str)
        
        # Test caching
        breakpoint2 = manager.evaluate_breakpoint(
            800, BreakpointType.CONTAINER_WIDTH
        )
        assert breakpoint == breakpoint2
        
        # Cache should have entries
        assert len(manager._breakpoint_cache) > 0
    
    def test_breakpoint_state_updates(self, mock_config_manager):
        """Test breakpoint state updates and events."""
        manager = BreakpointManager(mock_config_manager)
        
        # Mock signal
        manager.breakpoint_changed = Mock()
        
        # Update state
        changed = manager.update_breakpoint_state(
            BreakpointType.CONTAINER_WIDTH, 800
        )
        
        if changed:
            # Should emit signal if state changed
            manager.breakpoint_changed.emit.assert_called_once()
        
        # Get current state
        current = manager.get_current_breakpoint(BreakpointType.CONTAINER_WIDTH)
        assert current is not None
    
    def test_device_profile_detection(self, mock_config_manager, sample_device_profile):
        """Test device profile detection."""
        manager = BreakpointManager(mock_config_manager)
        
        # Add sample profile
        manager._device_profiles[sample_device_profile.device_class] = sample_device_profile
        
        # Test profile detection
        screen_properties = {
            'width': 1024,
            'height': 768,
            'dpi': 130,
            'is_touch_enabled': True
        }
        
        detected_profile = manager.detect_device_profile(screen_properties)
        
        # Should detect a profile
        assert detected_profile is not None
        assert isinstance(detected_profile, DeviceProfile)
    
    def test_profile_scoring(self, mock_config_manager, sample_device_profile):
        """Test device profile scoring algorithm."""
        manager = BreakpointManager(mock_config_manager)
        
        # Test scoring
        score = manager._calculate_profile_score(
            sample_device_profile,
            width=1024,
            height=768,
            dpi=130,
            is_touch=True
        )
        
        assert score > 0
        
        # Perfect match should score higher than poor match
        perfect_score = manager._calculate_profile_score(
            sample_device_profile,
            width=1024,
            height=768,
            dpi=140,  # Within range
            is_touch=True
        )
        
        poor_score = manager._calculate_profile_score(
            sample_device_profile,
            width=320,   # Mobile width
            height=568,  # Mobile height
            dpi=300,     # Mobile DPI
            is_touch=True
        )
        
        assert perfect_score > poor_score
    
    def test_custom_breakpoints_creation(self, mock_config_manager):
        """Test custom breakpoint creation from content analysis."""
        manager = BreakpointManager(mock_config_manager)
        
        content_analysis = {
            'widget_sizes': [],
            'content_widths': [200, 300, 400],
            'min_items_per_row': 1,
            'max_items_per_row': 3,
            'margin': 16
        }
        
        custom_breakpoints = manager.create_custom_breakpoints_from_content(content_analysis)
        
        assert len(custom_breakpoints) > 0
        assert all(isinstance(bp, BreakpointDefinition) for bp in custom_breakpoints)
        
        # Check that they're marked as auto-generated
        for bp in custom_breakpoints:
            assert bp.metadata.get('auto_generated') is True
    
    def test_performance_optimization(self, mock_config_manager):
        """Test performance optimization features."""
        manager = BreakpointManager(mock_config_manager)
        
        # Add some auto-generated breakpoints
        for i in range(5):
            bp = BreakpointDefinition(
                name=f"auto_{i}",
                type=BreakpointType.CONTAINER_WIDTH,
                min_value=i * 100,
                max_value=(i + 1) * 100,
                metadata={'auto_generated': True}
            )
            manager.add_breakpoint(bp)
        
        # Simulate usage history
        for i in range(10):
            manager.update_breakpoint_state(BreakpointType.CONTAINER_WIDTH, 150)
            manager.update_breakpoint_state(BreakpointType.CONTAINER_WIDTH, 250)
        
        initial_count = len(manager._breakpoints)
        
        # Optimize for performance
        manager.optimize_breakpoints_for_performance()
        
        # Should potentially remove unused breakpoints
        # (depending on usage patterns)
        final_count = len(manager._breakpoints)
        assert final_count <= initial_count
    
    def test_configuration_persistence(self, mock_config_manager):
        """Test configuration save/load."""
        manager = BreakpointManager(mock_config_manager)
        
        # Save configuration
        manager.save_configuration()
        
        # Should call config manager
        mock_config_manager.set.assert_called_once()
        call_args = mock_config_manager.set.call_args
        assert call_args[0][0] == 'ui.responsive.breakpoints'
        
        # Load configuration
        mock_config_manager.get.return_value = {
            'breakpoints': {
                'test': {
                    'name': 'test',
                    'type': 'CONTAINER_WIDTH',
                    'min_value': 100,
                    'max_value': 200,
                    'device_classes': [],
                    'priority': 50,
                    'metadata': {}
                }
            }
        }
        
        manager.load_configuration()
        
        # Should have loaded the test breakpoint
        assert 'test' in manager._breakpoints
    
    def test_statistics_collection(self, mock_config_manager):
        """Test statistics collection."""
        manager = BreakpointManager(mock_config_manager)
        
        # Generate some activity
        for i in range(5):
            manager.update_breakpoint_state(BreakpointType.CONTAINER_WIDTH, 800 + i * 10)
        
        stats = manager.get_breakpoint_statistics()
        
        assert 'total_breakpoints' in stats
        assert 'active_breakpoints' in stats
        assert 'usage_statistics' in stats
        assert 'change_history_size' in stats
        assert 'cache_size' in stats
        
        assert stats['total_breakpoints'] > 0
        assert stats['change_history_size'] > 0
    
    def test_calculation_enable_disable(self, mock_config_manager):
        """Test enabling/disabling calculations."""
        manager = BreakpointManager(mock_config_manager)
        
        # Disable calculations
        manager.enable_calculation(False)
        
        result = manager.evaluate_breakpoint(800, BreakpointType.CONTAINER_WIDTH)
        assert result is None
        
        # Enable calculations
        manager.enable_calculation(True)
        
        result = manager.evaluate_breakpoint(800, BreakpointType.CONTAINER_WIDTH)
        assert result is not None
    
    def test_history_management(self, mock_config_manager):
        """Test breakpoint change history management."""
        manager = BreakpointManager(mock_config_manager)
        
        # Generate history
        for i in range(10):
            manager.update_breakpoint_state(BreakpointType.CONTAINER_WIDTH, 800 + i * 50)
        
        initial_history_size = len(manager._change_history)
        assert initial_history_size > 0
        
        # Clear history
        manager.clear_history()
        assert len(manager._change_history) == 0


class TestBreakpointEvent:
    """Test BreakpointEvent structure."""
    
    def test_event_creation(self):
        """Test creating breakpoint events."""
        event = BreakpointEvent(
            old_breakpoint="sm",
            new_breakpoint="md",
            breakpoint_type=BreakpointType.CONTAINER_WIDTH,
            trigger_value=800.0,
            timestamp=time.time(),
            context={'device': 'tablet'}
        )
        
        assert event.old_breakpoint == "sm"
        assert event.new_breakpoint == "md"
        assert event.breakpoint_type == BreakpointType.CONTAINER_WIDTH
        assert event.trigger_value == 800.0
        assert event.context['device'] == 'tablet'


class TestDeviceProfile:
    """Test DeviceProfile functionality."""
    
    def test_profile_creation(self):
        """Test creating device profiles."""
        profile = DeviceProfile(
            name="Test Tablet",
            device_class=DeviceClass.TABLET_LANDSCAPE,
            typical_widths=[1024, 1280],
            typical_heights=[768, 800],
            typical_dpi_range=(120, 160),
            touch_enabled=True,
            preferred_breakpoints=["md", "lg"]
        )
        
        assert profile.name == "Test Tablet"
        assert profile.device_class == DeviceClass.TABLET_LANDSCAPE
        assert profile.touch_enabled is True
        assert "md" in profile.preferred_breakpoints
        assert "lg" in profile.preferred_breakpoints


class TestIntegration:
    """Integration tests for breakpoint system."""
    
    def test_manager_calculator_integration(self, mock_config_manager):
        """Test integration between manager and calculator."""
        manager = BreakpointManager(mock_config_manager)
        
        # Create custom breakpoints
        content_analysis = {
            'content_widths': [200, 300, 400],
            'min_items_per_row': 1,
            'max_items_per_row': 3
        }
        
        custom_breakpoints = manager.create_custom_breakpoints_from_content(content_analysis)
        
        # Add them to manager
        for bp in custom_breakpoints:
            manager.add_breakpoint(bp)
        
        # Should be able to evaluate against custom breakpoints
        result = manager.evaluate_breakpoint(250, BreakpointType.CONTAINER_WIDTH)
        assert result is not None
    
    def test_performance_under_load(self, mock_config_manager):
        """Test performance under high load."""
        manager = BreakpointManager(mock_config_manager)
        
        start_time = time.time()
        
        # Perform many evaluations
        for i in range(1000):
            manager.evaluate_breakpoint(
                500 + (i % 100), 
                BreakpointType.CONTAINER_WIDTH
            )
        
        elapsed = time.time() - start_time
        
        # Should complete in reasonable time (under 1 second)
        assert elapsed < 1.0
        
        # Cache should be working
        cache_stats = manager.get_breakpoint_statistics()
        assert cache_stats['cache_size'] > 0


if __name__ == "__main__":
    pytest.main([__file__])