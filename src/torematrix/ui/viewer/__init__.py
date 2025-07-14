"""
Document Viewer UI Components.

This module provides the core viewer components for document display,
coordinate transformation, viewport management, and screen handling.
"""

from .coordinates import (
    Point,
    Rectangle,
    CoordinateTransform,
    CoordinateValidator,
    CoordinateConverter
)

from .viewport import (
    ViewportState,
    ViewportInfo,
    ScreenInfo,
    ViewportManager
)

from .screen import (
    ScreenType,
    DPIMode,
    ScreenMetrics,
    ScreenConfiguration,
    ScreenManager,
    ScreenCoordinateMapper,
    screen_manager
)

__all__ = [
    # Coordinates
    'Point',
    'Rectangle',
    'CoordinateTransform',
    'CoordinateValidator',
    'CoordinateConverter',
    
    # Viewport
    'ViewportState',
    'ViewportInfo',
    'ScreenInfo',
    'ViewportManager',
    
    # Screen Management
    'ScreenType',
    'DPIMode',
    'ScreenMetrics',
    'ScreenConfiguration',
    'ScreenManager',
    'ScreenCoordinateMapper',
    'screen_manager',
]