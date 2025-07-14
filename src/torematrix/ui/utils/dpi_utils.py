"""High DPI display support and scaling utilities for ToreMatrix V3.

This module provides comprehensive high DPI support with automatic scaling,
font management, and icon optimization for all display types.
"""

from typing import Dict, Optional, Tuple, List
import logging
import platform
from enum import Enum

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QObject, QSize, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QScreen, QPixmap, QPainter

logger = logging.getLogger(__name__)


class DPIScale(Enum):
    """DPI scaling categories."""
    NORMAL = 1.0      # 96 DPI (100%)
    MEDIUM = 1.25     # 120 DPI (125%)
    HIGH = 1.5        # 144 DPI (150%)
    EXTRA_HIGH = 2.0  # 192 DPI (200%)
    ULTRA_HIGH = 3.0  # 288 DPI (300%)


class DPIManager(QObject):
    """High DPI display support with automatic scaling and optimization."""
    
    # Signals
    dpi_changed = pyqtSignal(float)  # new_scale_factor
    screen_changed = pyqtSignal(QScreen)
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        # DPI information
        self._scale_factor: float = 1.0
        self._logical_dpi: float = 96.0
        self._physical_dpi: float = 96.0
        self._current_screen: Optional[QScreen] = None
        
        # Font scaling
        self._base_font_size: int = 9
        self._font_scale_factor: float = 1.0
        
        # Icon cache for different DPI scales
        self._scaled_icon_cache: Dict[str, Dict[float, QIcon]] = {}
        
        # Platform-specific settings
        self._platform = platform.system()
        
        # Initialize DPI detection
        self._detect_dpi_settings()
        self._setup_screen_monitoring()
    
    def _detect_dpi_settings(self) -> None:
        """Detect current DPI settings and scaling."""
        app = QApplication.instance()
        if not app:
            logger.warning("No QApplication instance available for DPI detection")
            return
        
        # Get primary screen
        self._current_screen = app.primaryScreen()
        if not self._current_screen:
            logger.warning("No primary screen available")
            return
        
        # Calculate DPI values
        self._logical_dpi = self._current_screen.logicalDotsPerInch()
        self._physical_dpi = self._current_screen.physicalDotsPerInch()
        
        # Calculate scale factor
        self._scale_factor = self._logical_dpi / 96.0
        
        # Adjust for platform-specific behavior
        if self._platform == "Windows":
            # Windows may report different values
            device_pixel_ratio = self._current_screen.devicePixelRatio()
            if device_pixel_ratio > 1.0:
                self._scale_factor = device_pixel_ratio
        elif self._platform == "Darwin":  # macOS
            # macOS handles scaling differently
            device_pixel_ratio = self._current_screen.devicePixelRatio()
            self._scale_factor = device_pixel_ratio
        
        # Calculate font scale factor (usually same as DPI scale)
        self._font_scale_factor = self._scale_factor
        
        logger.info(f"DPI detection: logical={self._logical_dpi:.1f}, "
                   f"physical={self._physical_dpi:.1f}, scale={self._scale_factor:.2f}")
    
    def _setup_screen_monitoring(self) -> None:
        """Setup monitoring for screen changes."""
        app = QApplication.instance()
        if app:
            app.screenAdded.connect(self._handle_screen_added)
            app.screenRemoved.connect(self._handle_screen_removed)
            app.primaryScreenChanged.connect(self._handle_primary_screen_changed)
    
    def _handle_screen_added(self, screen: QScreen) -> None:
        """Handle screen added event."""
        logger.info(f"Screen added: {screen.name()}")
        self._update_dpi_for_screen(screen)
    
    def _handle_screen_removed(self, screen: QScreen) -> None:
        """Handle screen removed event."""
        logger.info(f"Screen removed: {screen.name()}")
        # Re-detect DPI settings
        self._detect_dpi_settings()
    
    def _handle_primary_screen_changed(self, screen: QScreen) -> None:
        """Handle primary screen change."""
        logger.info(f"Primary screen changed to: {screen.name()}")
        self._update_dpi_for_screen(screen)
    
    def _update_dpi_for_screen(self, screen: QScreen) -> None:
        """Update DPI settings for a specific screen."""
        old_scale = self._scale_factor
        
        self._current_screen = screen
        self._logical_dpi = screen.logicalDotsPerInch()
        self._physical_dpi = screen.physicalDotsPerInch()
        self._scale_factor = self._logical_dpi / 96.0
        
        # Platform-specific adjustments
        if self._platform in ["Windows", "Darwin"]:
            device_pixel_ratio = screen.devicePixelRatio()
            if device_pixel_ratio > 1.0:
                self._scale_factor = device_pixel_ratio
        
        self._font_scale_factor = self._scale_factor
        
        # Clear icon cache if scale changed significantly
        if abs(old_scale - self._scale_factor) > 0.1:
            self._scaled_icon_cache.clear()
            self.dpi_changed.emit(self._scale_factor)
        
        self.screen_changed.emit(screen)
    
    def detect_dpi_scaling(self) -> float:
        """Detect and return current DPI scaling factor."""
        return self._scale_factor
    
    def get_scale_factor(self) -> float:
        """Get current DPI scale factor."""
        return self._scale_factor
    
    def get_dpi_category(self) -> DPIScale:
        """Get DPI scaling category."""
        if self._scale_factor <= 1.1:
            return DPIScale.NORMAL
        elif self._scale_factor <= 1.35:
            return DPIScale.MEDIUM
        elif self._scale_factor <= 1.75:
            return DPIScale.HIGH
        elif self._scale_factor <= 2.5:
            return DPIScale.EXTRA_HIGH
        else:
            return DPIScale.ULTRA_HIGH
    
    def get_scaled_size(self, base_size: int) -> int:
        """Get size scaled for current DPI."""
        return int(base_size * self._scale_factor)
    
    def get_scaled_size_f(self, base_size: float) -> float:
        """Get size scaled for current DPI (float version)."""
        return base_size * self._scale_factor
    
    def get_scaled_qsize(self, base_size: QSize) -> QSize:
        """Get QSize scaled for current DPI."""
        return QSize(
            self.get_scaled_size(base_size.width()),
            self.get_scaled_size(base_size.height())
        )
    
    def get_scaled_icon(self, icon_path: str, base_size: int) -> QIcon:
        """Get icon scaled for current DPI."""
        cache_key = f"{icon_path}:{base_size}"
        
        # Check cache
        if cache_key in self._scaled_icon_cache:
            if self._scale_factor in self._scaled_icon_cache[cache_key]:
                return self._scaled_icon_cache[cache_key][self._scale_factor]
        
        # Load and scale icon
        scaled_icon = self._create_scaled_icon(icon_path, base_size)
        
        # Cache the result
        if cache_key not in self._scaled_icon_cache:
            self._scaled_icon_cache[cache_key] = {}
        self._scaled_icon_cache[cache_key][self._scale_factor] = scaled_icon
        
        return scaled_icon
    
    def _create_scaled_icon(self, icon_path: str, base_size: int) -> QIcon:
        """Create properly scaled icon."""
        scaled_size = self.get_scaled_size(base_size)
        
        try:
            # Load original icon
            original_icon = QIcon(icon_path)
            if original_icon.isNull():
                logger.warning(f"Could not load icon: {icon_path}")
                return QIcon()
            
            # Create scaled pixmap
            pixmap = original_icon.pixmap(scaled_size, scaled_size)
            
            # Ensure smooth scaling for high DPI
            if self._scale_factor > 1.5:
                # Use smooth transformation for high DPI
                pixmap = pixmap.scaled(
                    scaled_size, scaled_size,
                    aspectRatioMode=1,  # KeepAspectRatio
                    transformMode=1     # SmoothTransformation
                )
            
            return QIcon(pixmap)
            
        except Exception as e:
            logger.error(f"Failed to create scaled icon for {icon_path}: {e}")
            return QIcon()
    
    def get_icon_sizes_for_dpi(self, base_size: int) -> List[int]:
        """Get list of icon sizes needed for current DPI."""
        base_sizes = [base_size]
        
        # Add 1.5x and 2x versions for high DPI
        if self._scale_factor > 1.25:
            base_sizes.append(int(base_size * 1.5))
        
        if self._scale_factor > 1.75:
            base_sizes.append(base_size * 2)
        
        if self._scale_factor > 2.5:
            base_sizes.append(base_size * 3)
        
        return sorted(set(base_sizes))
    
    def update_fonts_for_dpi(self, base_font: QFont) -> QFont:
        """Update font for current DPI scaling."""
        scaled_font = QFont(base_font)
        
        # Scale font size
        base_size = base_font.pointSize()
        if base_size > 0:
            scaled_size = max(1, int(base_size * self._font_scale_factor))
            scaled_font.setPointSize(scaled_size)
        else:
            # Handle pixel-based fonts
            pixel_size = base_font.pixelSize()
            if pixel_size > 0:
                scaled_pixel_size = max(1, int(pixel_size * self._font_scale_factor))
                scaled_font.setPixelSize(scaled_pixel_size)
        
        return scaled_font
    
    def get_recommended_font_size(self, base_size: int = 9) -> int:
        """Get recommended font size for current DPI."""
        return max(1, int(base_size * self._font_scale_factor))
    
    def apply_dpi_scaling_to_widget(self, widget: QWidget) -> None:
        """Apply DPI scaling to a widget and its properties."""
        if not widget:
            return
        
        try:
            # Scale widget size constraints
            min_size = widget.minimumSize()
            if not min_size.isEmpty():
                widget.setMinimumSize(self.get_scaled_qsize(min_size))
            
            max_size = widget.maximumSize()
            if max_size.width() < 16777215 or max_size.height() < 16777215:
                widget.setMaximumSize(self.get_scaled_qsize(max_size))
            
            # Scale fixed size if set
            if widget.hasFixedSize():
                current_size = widget.size()
                widget.setFixedSize(self.get_scaled_qsize(current_size))
            
            # Update font if needed
            font = widget.font()
            scaled_font = self.update_fonts_for_dpi(font)
            widget.setFont(scaled_font)
            
            # Recursively apply to child widgets
            for child in widget.findChildren(QWidget):
                self.apply_dpi_scaling_to_widget(child)
                
        except Exception as e:
            logger.error(f"Failed to apply DPI scaling to widget: {e}")
    
    def get_screen_info(self) -> Dict[str, any]:
        """Get comprehensive screen information."""
        if not self._current_screen:
            return {}
        
        geometry = self._current_screen.geometry()
        available_geometry = self._current_screen.availableGeometry()
        
        return {
            "name": self._current_screen.name(),
            "logical_dpi": self._logical_dpi,
            "physical_dpi": self._physical_dpi,
            "scale_factor": self._scale_factor,
            "device_pixel_ratio": self._current_screen.devicePixelRatio(),
            "geometry": {
                "width": geometry.width(),
                "height": geometry.height(),
                "x": geometry.x(),
                "y": geometry.y()
            },
            "available_geometry": {
                "width": available_geometry.width(),
                "height": available_geometry.height(),
                "x": available_geometry.x(),
                "y": available_geometry.y()
            },
            "refresh_rate": self._current_screen.refreshRate(),
            "orientation": self._current_screen.orientation(),
            "dpi_category": self.get_dpi_category().value
        }
    
    def get_all_screens_info(self) -> List[Dict[str, any]]:
        """Get information for all available screens."""
        app = QApplication.instance()
        if not app:
            return []
        
        screens_info = []
        for screen in app.screens():
            # Temporarily switch to this screen for info gathering
            original_screen = self._current_screen
            self._current_screen = screen
            
            # Update DPI values for this screen
            self._logical_dpi = screen.logicalDotsPerInch()
            self._physical_dpi = screen.physicalDotsPerInch()
            
            screen_info = self.get_screen_info()
            screens_info.append(screen_info)
            
            # Restore original screen
            self._current_screen = original_screen
        
        return screens_info
    
    def optimize_for_high_dpi(self) -> None:
        """Apply optimizations for high DPI displays."""
        if self._scale_factor <= 1.5:
            return  # No optimization needed for normal DPI
        
        app = QApplication.instance()
        if not app:
            return
        
        try:
            # Enable high DPI pixmaps
            app.setAttribute(app.ApplicationAttribute.AA_UseHighDpiPixmaps)
            
            # Platform-specific optimizations
            if self._platform == "Windows":
                # Ensure proper Windows DPI awareness
                try:
                    import ctypes
                    from ctypes import wintypes
                    
                    # Set DPI awareness
                    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
                except Exception as e:
                    logger.debug(f"Could not set Windows DPI awareness: {e}")
            
            elif self._platform == "Darwin":  # macOS
                # macOS specific optimizations
                pass
            
            elif self._platform == "Linux":
                # Linux specific optimizations
                import os
                os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
            
            logger.info("High DPI optimizations applied")
            
        except Exception as e:
            logger.error(f"Failed to apply high DPI optimizations: {e}")
    
    def create_high_dpi_pixmap(self, size: QSize, device_pixel_ratio: Optional[float] = None) -> QPixmap:
        """Create a pixmap optimized for high DPI rendering."""
        ratio = device_pixel_ratio or self._scale_factor
        
        # Create pixmap with appropriate device pixel ratio
        pixmap = QPixmap(size * ratio)
        pixmap.setDevicePixelRatio(ratio)
        pixmap.fill(0)  # Transparent
        
        return pixmap
    
    def clear_icon_cache(self) -> None:
        """Clear the scaled icon cache."""
        self._scaled_icon_cache.clear()
        logger.debug("DPI icon cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        total_icons = len(self._scaled_icon_cache)
        total_variants = sum(len(variants) for variants in self._scaled_icon_cache.values())
        
        return {
            "cached_icons": total_icons,
            "total_variants": total_variants,
            "current_scale": round(self._scale_factor, 2)
        }