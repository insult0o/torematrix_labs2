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

# Optimization Components (Agent 3)
try:
    from .zoom import (
        ZoomManager,
        ZoomState,
        ZoomPerformanceMetrics
    )
    from .pan import (
        PanManager,
        PanState,
        PanConstraints,
        PanPerformanceMetrics
    )
    from .rotation import (
        RotationManager,
        RotationState,
        RotationConstraints,
        RotationPerformanceMetrics
    )
    from .cache import (
        TransformationCache,
        CoordinateCache,
        CacheEntry,
        CacheStatistics
    )
    
    OPTIMIZATION_AVAILABLE = True
except ImportError:
    OPTIMIZATION_AVAILABLE = False

# Build __all__ list conditionally
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

# Add optimization components if available
if OPTIMIZATION_AVAILABLE:
    __all__.extend([
        # Zoom Optimization
        'ZoomManager',
        'ZoomState', 
        'ZoomPerformanceMetrics',
        
        # Pan Optimization
        'PanManager',
        'PanState',
        'PanConstraints',
        'PanPerformanceMetrics',
        
        # Rotation Optimization
        'RotationManager',
        'RotationState',
        'RotationConstraints', 
        'RotationPerformanceMetrics',
        
        # Caching System
        'TransformationCache',
        'CoordinateCache',
        'CacheEntry',
        'CacheStatistics',
        
        # Availability Flag
        'OPTIMIZATION_AVAILABLE'
    ])
else:
    __all__.append('OPTIMIZATION_AVAILABLE')