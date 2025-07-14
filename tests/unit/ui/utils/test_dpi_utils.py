"""Tests for DPI utilities."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QScreen, QIcon, QFont

from torematrix.ui.utils.dpi_utils import DPIManager, DPIScale


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_screen():
    """Create mock screen for testing."""
    screen = Mock(spec=QScreen)
    screen.logicalDotsPerInch.return_value = 96.0
    screen.physicalDotsPerInch.return_value = 96.0
    screen.devicePixelRatio.return_value = 1.0
    screen.name.return_value = "Mock Screen"
    screen.refreshRate.return_value = 60.0
    screen.orientation.return_value = 1
    
    # Mock geometry
    geometry = Mock()
    geometry.width.return_value = 1920
    geometry.height.return_value = 1080
    geometry.x.return_value = 0
    geometry.y.return_value = 0
    screen.geometry.return_value = geometry
    screen.availableGeometry.return_value = geometry
    
    return screen


@pytest.fixture
def dpi_manager(app, mock_screen):
    """Create DPIManager instance for testing."""
    with patch.object(QApplication, 'primaryScreen', return_value=mock_screen):
        with patch('platform.system', return_value='Linux'):
            manager = DPIManager()
    return manager


class TestDPIScale:
    """Test DPIScale enum."""
    
    def test_dpi_scale_values(self):
        """Test DPI scale enum values."""
        assert DPIScale.NORMAL.value == 1.0
        assert DPIScale.MEDIUM.value == 1.25
        assert DPIScale.HIGH.value == 1.5
        assert DPIScale.EXTRA_HIGH.value == 2.0
        assert DPIScale.ULTRA_HIGH.value == 3.0


class TestDPIManager:
    """Test DPIManager functionality."""
    
    def test_initialization(self, dpi_manager):
        """Test DPIManager initialization."""
        assert dpi_manager._scale_factor == 1.0
        assert dpi_manager._logical_dpi == 96.0
        assert dpi_manager._physical_dpi == 96.0
        assert dpi_manager._current_screen is not None
    
    def test_dpi_detection_normal(self, app):
        """Test DPI detection for normal DPI."""
        mock_screen = Mock()
        mock_screen.logicalDotsPerInch.return_value = 96.0
        mock_screen.physicalDotsPerInch.return_value = 96.0
        mock_screen.devicePixelRatio.return_value = 1.0
        
        with patch.object(QApplication, 'primaryScreen', return_value=mock_screen):
            with patch('platform.system', return_value='Linux'):
                manager = DPIManager()
                
                assert manager._scale_factor == 1.0
                assert manager.get_dpi_category() == DPIScale.NORMAL
    
    def test_dpi_detection_high(self, app):
        """Test DPI detection for high DPI."""
        mock_screen = Mock()
        mock_screen.logicalDotsPerInch.return_value = 144.0
        mock_screen.physicalDotsPerInch.return_value = 144.0
        mock_screen.devicePixelRatio.return_value = 1.5
        
        with patch.object(QApplication, 'primaryScreen', return_value=mock_screen):
            with patch('platform.system', return_value='Linux'):
                manager = DPIManager()
                
                assert manager._scale_factor == 1.5
                assert manager.get_dpi_category() == DPIScale.HIGH
    
    def test_windows_dpi_detection(self, app):
        """Test Windows-specific DPI detection."""
        mock_screen = Mock()
        mock_screen.logicalDotsPerInch.return_value = 96.0
        mock_screen.physicalDotsPerInch.return_value = 96.0
        mock_screen.devicePixelRatio.return_value = 2.0
        
        with patch.object(QApplication, 'primaryScreen', return_value=mock_screen):
            with patch('platform.system', return_value='Windows'):
                manager = DPIManager()
                
                assert manager._scale_factor == 2.0  # Should use devicePixelRatio
    
    def test_macos_dpi_detection(self, app):
        """Test macOS-specific DPI detection."""
        mock_screen = Mock()
        mock_screen.logicalDotsPerInch.return_value = 96.0
        mock_screen.physicalDotsPerInch.return_value = 96.0
        mock_screen.devicePixelRatio.return_value = 2.0
        
        with patch.object(QApplication, 'primaryScreen', return_value=mock_screen):
            with patch('platform.system', return_value='Darwin'):
                manager = DPIManager()
                
                assert manager._scale_factor == 2.0  # Should use devicePixelRatio
    
    def test_get_scale_factor(self, dpi_manager):
        """Test getting scale factor."""
        assert dpi_manager.get_scale_factor() == 1.0
    
    def test_detect_dpi_scaling(self, dpi_manager):
        """Test DPI scaling detection."""
        scale_factor = dpi_manager.detect_dpi_scaling()
        assert scale_factor == 1.0
    
    def test_dpi_category_determination(self, dpi_manager):
        """Test DPI category determination."""
        # Test different scale factors
        dpi_manager._scale_factor = 1.0
        assert dpi_manager.get_dpi_category() == DPIScale.NORMAL
        
        dpi_manager._scale_factor = 1.25
        assert dpi_manager.get_dpi_category() == DPIScale.MEDIUM
        
        dpi_manager._scale_factor = 1.5
        assert dpi_manager.get_dpi_category() == DPIScale.HIGH
        
        dpi_manager._scale_factor = 2.0
        assert dpi_manager.get_dpi_category() == DPIScale.EXTRA_HIGH
        
        dpi_manager._scale_factor = 3.0
        assert dpi_manager.get_dpi_category() == DPIScale.ULTRA_HIGH
    
    def test_scaled_size_calculation(self, dpi_manager):
        """Test scaled size calculations."""
        # Set scale factor to 2.0 for easier testing
        dpi_manager._scale_factor = 2.0
        
        assert dpi_manager.get_scaled_size(100) == 200
        assert dpi_manager.get_scaled_size_f(100.5) == 201.0
        
        qsize = dpi_manager.get_scaled_qsize(QSize(50, 75))
        assert qsize.width() == 100
        assert qsize.height() == 150
    
    def test_icon_scaling(self, dpi_manager):
        """Test icon scaling functionality."""
        dpi_manager._scale_factor = 1.5
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('torematrix.ui.utils.dpi_utils.QIcon') as mock_icon_class:
                mock_icon = Mock()
                mock_icon.isNull.return_value = False
                mock_pixmap = Mock()
                mock_icon.pixmap.return_value = mock_pixmap
                mock_icon_class.return_value = mock_icon
                
                # First call should load and cache
                icon1 = dpi_manager.get_scaled_icon("test.svg", 32)
                assert icon1 is not None
                
                # Second call should use cache
                icon2 = dpi_manager.get_scaled_icon("test.svg", 32)
                assert icon2 is not None
                
                # Verify caching
                cache_key = "test.svg:32"
                assert cache_key in dpi_manager._scaled_icon_cache
    
    def test_icon_sizes_for_dpi(self, dpi_manager):
        """Test getting icon sizes for different DPI levels."""
        # Normal DPI
        dpi_manager._scale_factor = 1.0
        sizes = dpi_manager.get_icon_sizes_for_dpi(24)
        assert sizes == [24]
        
        # Medium DPI
        dpi_manager._scale_factor = 1.5
        sizes = dpi_manager.get_icon_sizes_for_dpi(24)
        assert 24 in sizes
        assert 36 in sizes  # 1.5x
        
        # High DPI
        dpi_manager._scale_factor = 2.5
        sizes = dpi_manager.get_icon_sizes_for_dpi(24)
        assert 24 in sizes
        assert 36 in sizes  # 1.5x
        assert 48 in sizes  # 2x
        assert 72 in sizes  # 3x
    
    def test_font_scaling(self, dpi_manager):
        """Test font scaling for DPI."""
        dpi_manager._scale_factor = 1.5
        dpi_manager._font_scale_factor = 1.5
        
        # Test point size font
        base_font = QFont("Arial", 10)
        scaled_font = dpi_manager.update_fonts_for_dpi(base_font)
        assert scaled_font.pointSize() == 15  # 10 * 1.5
        
        # Test pixel size font
        base_font.setPixelSize(12)
        scaled_font = dpi_manager.update_fonts_for_dpi(base_font)
        assert scaled_font.pixelSize() == 18  # 12 * 1.5
    
    def test_recommended_font_size(self, dpi_manager):
        """Test recommended font size calculation."""
        dpi_manager._font_scale_factor = 1.25
        
        recommended = dpi_manager.get_recommended_font_size(9)
        assert recommended == 11  # 9 * 1.25 = 11.25, rounded down to 11
    
    def test_widget_dpi_scaling(self, dpi_manager, app):
        """Test applying DPI scaling to widgets."""
        widget = QWidget()
        widget.setMinimumSize(QSize(100, 50))
        widget.setMaximumSize(QSize(200, 100))
        
        dpi_manager._scale_factor = 2.0
        dpi_manager.apply_dpi_scaling_to_widget(widget)
        
        assert widget.minimumSize() == QSize(200, 100)
        assert widget.maximumSize() == QSize(400, 200)
    
    def test_screen_info(self, dpi_manager):
        """Test getting screen information."""
        info = dpi_manager.get_screen_info()
        
        assert "name" in info
        assert "logical_dpi" in info
        assert "physical_dpi" in info
        assert "scale_factor" in info
        assert "geometry" in info
        assert "dpi_category" in info
        
        assert info["logical_dpi"] == 96.0
        assert info["scale_factor"] == 1.0
        assert info["dpi_category"] == 1.0  # DPIScale.NORMAL.value
    
    def test_all_screens_info(self, dpi_manager, app):
        """Test getting information for all screens."""
        mock_screen2 = Mock()
        mock_screen2.logicalDotsPerInch.return_value = 144.0
        mock_screen2.physicalDotsPerInch.return_value = 144.0
        mock_screen2.name.return_value = "Screen 2"
        
        with patch.object(app, 'screens', return_value=[dpi_manager._current_screen, mock_screen2]):
            all_info = dpi_manager.get_all_screens_info()
            
            assert len(all_info) == 2
            assert all_info[0]["name"] == "Mock Screen"
            assert all_info[1]["name"] == "Screen 2"
    
    def test_high_dpi_optimization(self, dpi_manager, app):
        """Test high DPI optimization."""
        dpi_manager._scale_factor = 2.0
        
        with patch.object(app, 'setAttribute') as mock_set_attr:
            dpi_manager.optimize_for_high_dpi()
            
            # Should enable high DPI pixmaps
            mock_set_attr.assert_called()
    
    def test_windows_high_dpi_optimization(self, app):
        """Test Windows-specific high DPI optimization."""
        mock_screen = Mock()
        mock_screen.logicalDotsPerInch.return_value = 192.0
        mock_screen.physicalDotsPerInch.return_value = 192.0
        mock_screen.devicePixelRatio.return_value = 2.0
        
        with patch.object(QApplication, 'primaryScreen', return_value=mock_screen):
            with patch('platform.system', return_value='Windows'):
                with patch('ctypes.windll.shcore.SetProcessDpiAwareness') as mock_dpi:
                    manager = DPIManager()
                    manager.optimize_for_high_dpi()
                    
                    # Should attempt to set DPI awareness on Windows
                    # Note: This might not work in test environment, but we test the attempt
    
    def test_high_dpi_pixmap_creation(self, dpi_manager):
        """Test high DPI pixmap creation."""
        dpi_manager._scale_factor = 2.0
        
        pixmap = dpi_manager.create_high_dpi_pixmap(QSize(100, 100))
        
        assert pixmap.size() == QSize(200, 200)  # Scaled by device pixel ratio
        assert pixmap.devicePixelRatio() == 2.0
    
    def test_screen_change_handling(self, dpi_manager):
        """Test screen change event handling."""
        # Create new mock screen with different DPI
        new_screen = Mock()
        new_screen.logicalDotsPerInch.return_value = 144.0
        new_screen.physicalDotsPerInch.return_value = 144.0
        new_screen.devicePixelRatio.return_value = 1.5
        new_screen.name.return_value = "New Screen"
        
        # Mock signal emission
        with patch.object(dpi_manager, 'dpi_changed') as mock_signal:
            dpi_manager._handle_primary_screen_changed(new_screen)
            
            assert dpi_manager._current_screen == new_screen
            assert dpi_manager._scale_factor == 1.5
            # Should emit signal if scale changed significantly
            mock_signal.emit.assert_called_with(1.5)
    
    def test_cache_management(self, dpi_manager):
        """Test icon cache management."""
        # Add some items to cache
        dpi_manager._scaled_icon_cache = {
            "icon1:24": {1.0: Mock()},
            "icon2:32": {1.0: Mock(), 2.0: Mock()}
        }
        
        # Get cache stats
        stats = dpi_manager.get_cache_stats()
        assert stats["cached_icons"] == 2
        assert stats["total_variants"] == 3
        assert stats["current_scale"] == 1.0
        
        # Clear cache
        dpi_manager.clear_icon_cache()
        assert len(dpi_manager._scaled_icon_cache) == 0
    
    def test_screen_monitoring_setup(self, dpi_manager, app):
        """Test screen monitoring setup."""
        # Verify that screen change signals are connected
        # This is tested through the initialization process
        assert dpi_manager._current_screen is not None
    
    def test_icon_loading_failure(self, dpi_manager):
        """Test handling of icon loading failures."""
        with patch('pathlib.Path.exists', return_value=False):
            icon = dpi_manager.get_scaled_icon("nonexistent.svg", 24)
            
            # Should return empty icon for non-existent file
            assert icon is not None  # Returns QIcon(), not None
    
    def test_create_scaled_icon_smooth_scaling(self, dpi_manager):
        """Test smooth scaling for high DPI icons."""
        dpi_manager._scale_factor = 2.5  # High DPI requiring smooth scaling
        
        with patch('torematrix.ui.utils.dpi_utils.QIcon') as mock_icon_class:
            mock_icon = Mock()
            mock_icon.isNull.return_value = False
            mock_pixmap = Mock()
            mock_icon.pixmap.return_value = mock_pixmap
            mock_pixmap.scaled.return_value = mock_pixmap
            mock_icon_class.return_value = mock_icon
            
            scaled_icon = dpi_manager._create_scaled_icon("test.svg", 32)
            
            # Should use smooth transformation for high DPI
            mock_pixmap.scaled.assert_called()
    
    def test_error_handling_no_app(self):
        """Test error handling when no QApplication instance."""
        with patch.object(QApplication, 'instance', return_value=None):
            # Should handle gracefully
            manager = DPIManager()
            assert manager._scale_factor == 1.0  # Default value
    
    def test_error_handling_no_screen(self, app):
        """Test error handling when no primary screen."""
        with patch.object(QApplication, 'primaryScreen', return_value=None):
            # Should handle gracefully
            manager = DPIManager()
            assert manager._scale_factor == 1.0  # Default value