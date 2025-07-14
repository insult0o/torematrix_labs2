"""
Momentum physics engine for smooth pan inertia.
Provides natural deceleration after pan gestures.
"""

from typing import List, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QPointF
import time
import math
from collections import deque


class MomentumEngine(QObject):
    """
    Physics engine for smooth momentum and inertia during pan operations.
    Provides natural deceleration curves after user gestures.
    """
    
    # Momentum signals
    momentum_update = pyqtSignal(QPointF)  # momentum_delta
    momentum_finished = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Momentum configuration
        self.friction_coefficient = 0.85  # Deceleration factor per frame
        self.min_velocity_threshold = 0.5  # Minimum velocity to continue
        self.velocity_scale_factor = 0.3  # Scale down velocity for smooth feel
        self.max_momentum_duration = 2000  # Maximum momentum time (ms)
        
        # Velocity tracking
        self.velocity_samples = deque(maxlen=10)  # Last 10 velocity samples
        self.sample_window = 100  # ms window for velocity calculation
        
        # Momentum state
        self.current_velocity = QPointF(0, 0)
        self.momentum_active = False
        self.momentum_start_time = 0.0
        
        # Timer for momentum updates
        self.momentum_timer = QTimer()
        self.momentum_timer.timeout.connect(self._update_momentum)
        self.momentum_timer.setInterval(16)  # ~60fps
    
    def add_velocity_sample(self, delta: QPointF):
        """
        Add a velocity sample during panning.
        
        Args:
            delta: Movement delta since last sample
        """
        current_time = time.time() * 1000  # Convert to ms
        
        # Add sample with timestamp
        self.velocity_samples.append({
            'delta': delta,
            'timestamp': current_time
        })
    
    def calculate_release_velocity(self) -> QPointF:
        """
        Calculate release velocity based on recent samples.
        
        Returns:
            QPointF: Calculated velocity vector
        """
        if len(self.velocity_samples) < 2:
            return QPointF(0, 0)
        
        current_time = time.time() * 1000
        
        # Filter samples within time window
        recent_samples = []
        for sample in self.velocity_samples:
            if current_time - sample['timestamp'] <= self.sample_window:
                recent_samples.append(sample)
        
        if len(recent_samples) < 2:
            return QPointF(0, 0)
        
        # Calculate average velocity
        total_delta = QPointF(0, 0)
        total_time = 0.0
        
        for i in range(1, len(recent_samples)):
            delta = recent_samples[i]['delta']
            time_diff = recent_samples[i]['timestamp'] - recent_samples[i-1]['timestamp']
            
            if time_diff > 0:
                total_delta += delta
                total_time += time_diff
        
        if total_time > 0:
            # Calculate velocity in pixels per millisecond
            velocity = QPointF(
                total_delta.x() / total_time * 16,  # Scale to frame rate
                total_delta.y() / total_time * 16
            )
            
            # Apply scale factor for natural feel
            velocity *= self.velocity_scale_factor
            
            return velocity
        
        return QPointF(0, 0)
    
    def should_apply_momentum(self, velocity: QPointF) -> bool:
        """
        Check if momentum should be applied based on velocity.
        
        Args:
            velocity: Calculated release velocity
            
        Returns:
            bool: True if momentum should be applied
        """
        velocity_magnitude = math.sqrt(velocity.x()**2 + velocity.y()**2)
        return velocity_magnitude > self.min_velocity_threshold
    
    def start_momentum(self, initial_velocity: QPointF) -> bool:
        """
        Start momentum animation with initial velocity.
        
        Args:
            initial_velocity: Starting velocity vector
            
        Returns:
            bool: True if momentum started successfully
        """
        if self.momentum_active:
            self.stop_momentum()
        
        self.current_velocity = initial_velocity
        self.momentum_active = True
        self.momentum_start_time = time.time() * 1000
        
        # Start momentum timer
        self.momentum_timer.start()
        return True
    
    def stop_momentum(self):
        """Stop momentum animation immediately."""
        if self.momentum_active:
            self.momentum_timer.stop()
            self.momentum_active = False
            self.current_velocity = QPointF(0, 0)
            self.momentum_finished.emit()
    
    def is_active(self) -> bool:
        """Check if momentum is currently active."""
        return self.momentum_active
    
    def _update_momentum(self):
        """Update momentum physics frame."""
        if not self.momentum_active:
            return
        
        current_time = time.time() * 1000
        
        # Check for timeout
        if current_time - self.momentum_start_time > self.max_momentum_duration:
            self.stop_momentum()
            return
        
        # Apply friction to velocity
        self.current_velocity *= self.friction_coefficient
        
        # Check if velocity is too small to continue
        velocity_magnitude = math.sqrt(
            self.current_velocity.x()**2 + self.current_velocity.y()**2
        )
        
        if velocity_magnitude < self.min_velocity_threshold:
            self.stop_momentum()
            return
        
        # Emit momentum update
        self.momentum_update.emit(self.current_velocity)
    
    def set_friction(self, friction: float):
        """
        Set friction coefficient for momentum deceleration.
        
        Args:
            friction: Friction coefficient (0.1 to 0.95)
        """
        if 0.1 <= friction <= 0.95:
            self.friction_coefficient = friction
    
    def set_velocity_threshold(self, threshold: float):
        """
        Set minimum velocity threshold for momentum continuation.
        
        Args:
            threshold: Minimum velocity threshold
        """
        if threshold > 0:
            self.min_velocity_threshold = threshold
    
    def get_momentum_state(self) -> dict:
        """Get current momentum state for debugging."""
        return {
            'active': self.momentum_active,
            'velocity': (self.current_velocity.x(), self.current_velocity.y()),
            'friction': self.friction_coefficient,
            'threshold': self.min_velocity_threshold,
            'samples_count': len(self.velocity_samples)
        }