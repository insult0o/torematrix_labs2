"""
Pan controls and user interaction for document viewer.
Provides mouse drag, touch gestures, and keyboard navigation with momentum physics.
"""

from typing import Optional, Tuple, Callable, Dict, Any, List
from PyQt6.QtCore import QObject, pyqtSignal, QPointF, QTimer
from PyQt6.QtGui import QMouseEvent, QWheelEvent
import math
import time
import threading
from dataclasses import dataclass
from collections import deque

from .zoom import ZoomEngine
from .momentum import MomentumEngine


@dataclass
class PanState:
    """Represents the current pan state."""
    offset: QPointF
    is_panning: bool
    momentum_active: bool
    timestamp: float


class PanEngine(QObject):
    """
    Core pan engine providing smooth drag navigation with momentum physics.
    Integrates with zoom engine for coordinated pan/zoom operations.
    """
    
    # Signals for pan state changes
    pan_changed = pyqtSignal(QPointF)  # pan_offset
    pan_started = pyqtSignal(QPointF)  # start_position
    pan_finished = pyqtSignal(QPointF)  # final_position
    boundary_hit = pyqtSignal(str)  # direction: 'left', 'right', 'top', 'bottom'
    pan_velocity_changed = pyqtSignal(QPointF)  # current_velocity
    
    def __init__(self, zoom_engine: ZoomEngine, parent=None):
        super().__init__(parent)
        
        # Core dependencies
        self.zoom_engine = zoom_engine
        self.momentum_engine = MomentumEngine(self)
        
        # Pan state
        self.current_offset = QPointF(0, 0)
        self.is_panning = False
        self.last_pan_position = QPointF(0, 0)
        self.pan_start_position = QPointF(0, 0)
        
        # Pan configuration
        self.pan_sensitivity = 1.0
        self.boundary_margin = 50  # pixels
        self.momentum_enabled = True
        self.inertia_enabled = True
        
        # Document and view boundaries
        self.document_size = QPointF(1000, 1000)  # Default size
        self.view_size = QPointF(800, 600)  # Default view
        
        # Performance tracking
        self.operation_times = deque(maxlen=100)
        
        # Thread safety
        self._pan_lock = threading.RLock()
        
        # Connect momentum engine
        self.momentum_engine.momentum_update.connect(self._apply_momentum_offset)
        self.momentum_engine.momentum_finished.connect(self._finish_momentum_pan)
        
        # Connect to zoom engine changes
        self.zoom_engine.zoom_changed.connect(self._on_zoom_changed)
    
    def set_document_size(self, width: float, height: float):
        """Set the document size for boundary calculations."""
        with self._pan_lock:
            self.document_size = QPointF(width, height)
            self._update_pan_boundaries()
    
    def set_view_size(self, width: float, height: float):
        """Set the view size for boundary calculations."""
        with self._pan_lock:
            self.view_size = QPointF(width, height)
            self._update_pan_boundaries()
    
    def start_pan(self, start_position: QPointF) -> bool:
        """
        Start panning operation from specified position.
        
        Args:
            start_position: Mouse/touch position where pan started
            
        Returns:
            bool: True if pan operation started successfully
        """
        start_time = time.perf_counter()
        
        try:
            with self._pan_lock:
                if self.is_panning:
                    return False
                
                self.is_panning = True
                self.pan_start_position = start_position
                self.last_pan_position = start_position
                
                # Stop any existing momentum
                self.momentum_engine.stop_momentum()
                
                self.pan_started.emit(start_position)
                return True
        
        finally:
            # Record operation timing
            end_time = time.perf_counter()
            operation_time = (end_time - start_time) * 1000
            self.operation_times.append(operation_time)
    
    def update_pan(self, current_position: QPointF) -> bool:
        """
        Update pan based on current mouse/touch position.
        
        Args:
            current_position: Current mouse/touch position
            
        Returns:
            bool: True if pan was applied successfully
        """
        start_time = time.perf_counter()
        
        try:
            with self._pan_lock:
                if not self.is_panning:
                    return False
                
                # Calculate pan delta
                delta = current_position - self.last_pan_position
                delta *= self.pan_sensitivity
                
                # Apply zoom scaling to pan sensitivity
                zoom_factor = self.zoom_engine.current_zoom
                adjusted_delta = delta / zoom_factor
                
                # Apply pan with boundary checking
                new_offset = self.current_offset + adjusted_delta
                constrained_offset = self._constrain_to_boundaries(new_offset)
                
                # Check for boundary hits
                if constrained_offset != new_offset:
                    self._emit_boundary_signals(new_offset, constrained_offset)
                
                # Update state
                self.current_offset = constrained_offset
                self.last_pan_position = current_position
                
                # Track velocity for momentum
                self.momentum_engine.add_velocity_sample(adjusted_delta)
                
                self.pan_changed.emit(self.current_offset)
                return True
        
        finally:
            # Record operation timing
            end_time = time.perf_counter()
            operation_time = (end_time - start_time) * 1000
            self.operation_times.append(operation_time)
    
    def finish_pan(self, end_position: QPointF) -> bool:
        """
        Finish panning operation and optionally apply momentum.
        
        Args:
            end_position: Final mouse/touch position
            
        Returns:
            bool: True if pan finished successfully
        """
        with self._pan_lock:
            if not self.is_panning:
                return False
            
            self.is_panning = False
            
            # Calculate final velocity and apply momentum if enabled
            if self.momentum_enabled and self.inertia_enabled:
                final_velocity = self.momentum_engine.calculate_release_velocity()
                if self.momentum_engine.should_apply_momentum(final_velocity):
                    self.momentum_engine.start_momentum(final_velocity)
                    return True
            
            self.pan_finished.emit(self.current_offset)
            return True
    
    def pan_to_position(self, position: QPointF, animated: bool = True) -> bool:
        """
        Pan to specific document position.
        
        Args:
            position: Target position in document coordinates
            animated: Whether to animate the transition
            
        Returns:
            bool: True if pan operation started
        """
        target_offset = self._calculate_offset_for_position(position)
        
        if animated:
            return self._animate_pan_to_offset(target_offset)
        else:
            with self._pan_lock:
                self.current_offset = self._constrain_to_boundaries(target_offset)
                self.pan_changed.emit(self.current_offset)
                return True
    
    def pan_by_delta(self, delta: QPointF, animated: bool = False) -> bool:
        """
        Pan by relative delta amount.
        
        Args:
            delta: Relative movement in view coordinates
            animated: Whether to animate the movement
            
        Returns:
            bool: True if pan was applied
        """
        with self._pan_lock:
            target_offset = self.current_offset + delta
            
            if animated:
                return self._animate_pan_to_offset(target_offset)
            else:
                self.current_offset = self._constrain_to_boundaries(target_offset)
                self.pan_changed.emit(self.current_offset)
                return True
    
    def center_on_point(self, document_point: QPointF, animated: bool = True) -> bool:
        """
        Center view on specific document point.
        
        Args:
            document_point: Point in document coordinates to center on
            animated: Whether to animate the centering
            
        Returns:
            bool: True if centering started
        """
        # Calculate offset to center the point
        view_center = self.view_size / 2
        zoom_factor = self.zoom_engine.current_zoom
        
        # Convert document point to view coordinates
        scaled_point = QPointF(document_point.x() * zoom_factor, 
                              document_point.y() * zoom_factor)
        target_offset = view_center - scaled_point
        
        if animated:
            return self._animate_pan_to_offset(target_offset)
        else:
            with self._pan_lock:
                self.current_offset = self._constrain_to_boundaries(target_offset)
                self.pan_changed.emit(self.current_offset)
                return True
    
    def get_pan_state(self) -> PanState:
        """Get current pan state for debugging/serialization."""
        return PanState(
            offset=self.current_offset,
            is_panning=self.is_panning,
            momentum_active=self.momentum_engine.is_active(),
            timestamp=time.time()
        )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring."""
        if not self.operation_times:
            return {
                'avg_operation_time': 0.0,
                'max_operation_time': 0.0,
                'operation_count': 0,
                'meets_target': True,
                'current_offset': (self.current_offset.x(), self.current_offset.y())
            }
        
        avg_time = sum(self.operation_times) / len(self.operation_times)
        max_time = max(self.operation_times)
        meets_target = avg_time < 8.0  # 8ms target for smooth panning
        
        return {
            'avg_operation_time': avg_time,
            'max_operation_time': max_time,
            'operation_count': len(self.operation_times),
            'meets_target': meets_target,
            'current_offset': (self.current_offset.x(), self.current_offset.y()),
            'is_panning': self.is_panning,
            'momentum_active': self.momentum_engine.is_active()
        }
    
    # Private methods
    
    def _constrain_to_boundaries(self, offset: QPointF) -> QPointF:
        """Apply boundary constraints to pan offset."""
        zoom_factor = self.zoom_engine.current_zoom
        
        # Calculate document bounds in view coordinates
        doc_width = self.document_size.x() * zoom_factor
        doc_height = self.document_size.y() * zoom_factor
        
        # Calculate valid offset range
        min_x = self.view_size.x() - doc_width - self.boundary_margin
        max_x = self.boundary_margin
        min_y = self.view_size.y() - doc_height - self.boundary_margin
        max_y = self.boundary_margin
        
        # Constrain offset
        constrained_x = max(min_x, min(max_x, offset.x()))
        constrained_y = max(min_y, min(max_y, offset.y()))
        
        return QPointF(constrained_x, constrained_y)
    
    def _emit_boundary_signals(self, intended: QPointF, constrained: QPointF):
        """Emit appropriate boundary hit signals."""
        if intended.x() < constrained.x():
            self.boundary_hit.emit('left')
        elif intended.x() > constrained.x():
            self.boundary_hit.emit('right')
        
        if intended.y() < constrained.y():
            self.boundary_hit.emit('top')
        elif intended.y() > constrained.y():
            self.boundary_hit.emit('bottom')
    
    def _calculate_offset_for_position(self, position: QPointF) -> QPointF:
        """Calculate pan offset needed to show specific document position."""
        zoom_factor = self.zoom_engine.current_zoom
        view_center = self.view_size / 2
        
        # Convert position to view coordinates and center it
        scaled_pos = QPointF(position.x() * zoom_factor, position.y() * zoom_factor)
        return view_center - scaled_pos
    
    def _animate_pan_to_offset(self, target_offset: QPointF) -> bool:
        """Animate pan to target offset (placeholder for future animation)."""
        # For now, just apply immediately
        # In a full implementation, this would use the animation engine
        with self._pan_lock:
            self.current_offset = self._constrain_to_boundaries(target_offset)
            self.pan_changed.emit(self.current_offset)
            return True
    
    def _apply_momentum_offset(self, momentum_delta: QPointF):
        """Apply momentum offset during momentum animation."""
        with self._pan_lock:
            new_offset = self.current_offset + momentum_delta
            constrained_offset = self._constrain_to_boundaries(new_offset)
            
            # Stop momentum if we hit a boundary
            if constrained_offset != new_offset:
                self.momentum_engine.stop_momentum()
                self._emit_boundary_signals(new_offset, constrained_offset)
            
            self.current_offset = constrained_offset
            self.pan_changed.emit(self.current_offset)
    
    def _finish_momentum_pan(self):
        """Handle momentum pan completion."""
        self.pan_finished.emit(self.current_offset)
    
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes for pan coordinate adjustment."""
        # Pan coordinates may need adjustment when zoom changes
        # This ensures the view stays consistent
        self._update_pan_boundaries()
    
    def _update_pan_boundaries(self):
        """Update pan boundaries based on current document and view sizes."""
        # Recalculate and apply boundary constraints
        with self._pan_lock:
            constrained_offset = self._constrain_to_boundaries(self.current_offset)
            if constrained_offset != self.current_offset:
                self.current_offset = constrained_offset
                self.pan_changed.emit(self.current_offset)
    
    def get_transform_matrix(self):
        """Get current pan transformation matrix."""
        from PyQt6.QtGui import QTransform
        
        transform = QTransform()
        transform.translate(self.current_offset.x(), self.current_offset.y())
        
        # Combine with zoom transform
        zoom_transform = self.zoom_engine.get_transform_matrix()
        return zoom_transform * transform
    
    # Public utility methods for other agents
    
    def get_current_pan_offset(self) -> QPointF:
        """Get current pan offset for integration."""
        return self.current_offset
    
    def get_document_bounds(self) -> Tuple[QPointF, QPointF]:
        """Get document bounds for integration."""
        return (QPointF(0, 0), self.document_size)
    
    def register_pan_callback(self, callback: Callable[[QPointF], None]):
        """Register callback for pan offset changes."""
        self.pan_changed.connect(callback)
    
    def unregister_pan_callback(self, callback: Callable[[QPointF], None]):
        """Unregister pan offset change callback."""
        self.pan_changed.disconnect(callback)
    
    def set_pan_sensitivity(self, sensitivity: float):
        """Set pan sensitivity multiplier."""
        if 0.1 <= sensitivity <= 5.0:  # Reasonable range
            self.pan_sensitivity = sensitivity
    
    def enable_momentum(self, enabled: bool = True):
        """Enable or disable pan momentum."""
        self.momentum_enabled = enabled
    
    def enable_inertia(self, enabled: bool = True):
        """Enable or disable pan inertia."""
        self.inertia_enabled = enabled