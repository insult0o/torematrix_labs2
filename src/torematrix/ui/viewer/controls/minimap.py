"""
Minimap Navigation Component for Document Viewer

Provides thumbnail view of entire document with viewport indicator
and click-to-navigate functionality for quick document navigation.
"""

from typing import Optional, Tuple, List, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal, QRectF, QPointF, QSizeF, QTimer, Qt
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
import math


class MinimapWidget(QWidget):
    """Minimap widget showing document thumbnail with viewport indicator"""
    
    # Navigation signals
    navigation_requested = pyqtSignal(QPointF)  # target_point
    zoom_to_area_requested = pyqtSignal(QRectF)  # target_area
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuration
        self._minimap_size = (200, 150)  # Default minimap size
        self._viewport_color = QColor(255, 0, 0, 128)  # Semi-transparent red
        self._viewport_border_color = QColor(255, 0, 0, 255)  # Solid red
        self._background_color = QColor(240, 240, 240)
        self._document_color = QColor(255, 255, 255)
        
        # State
        self._document_size = QSizeF(0, 0)
        self._viewport_rect = QRectF()
        self._document_thumbnail: Optional[QPixmap] = None
        self._scale_factor = 1.0
        self._dragging_viewport = False
        self._last_mouse_pos = QPointF()
        
        # Performance optimization
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._delayed_update)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup minimap widget UI"""
        self.setFixedSize(*self._minimap_size)
        self.setMinimumSize(150, 100)
        self.setMaximumSize(300, 250)
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        # Set background
        self.setStyleSheet(f"""
            MinimapWidget {{
                background-color: {self._background_color.name()};
                border: 1px solid #ccc;
                border-radius: 4px;
            }}
        """)
    
    def set_document_size(self, size: QSizeF) -> None:
        """Set the document size for minimap scaling"""
        self._document_size = size
        self._update_scale_factor()
        self._schedule_update()
    
    def set_viewport_rect(self, rect: QRectF) -> None:
        """Set the current viewport rectangle"""
        self._viewport_rect = rect
        self._schedule_update()
    
    def set_document_thumbnail(self, thumbnail: QPixmap) -> None:
        """Set the document thumbnail image"""
        self._document_thumbnail = thumbnail
        self._schedule_update()
    
    def _update_scale_factor(self) -> None:
        """Update scale factor for minimap display"""
        if self._document_size.isEmpty():
            self._scale_factor = 1.0
            return
        
        # Calculate scale to fit document in minimap
        width_scale = (self.width() - 20) / self._document_size.width()
        height_scale = (self.height() - 20) / self._document_size.height()
        self._scale_factor = min(width_scale, height_scale)
    
    def _schedule_update(self) -> None:
        """Schedule delayed update for performance"""
        self._update_timer.start(16)  # ~60fps
    
    def _delayed_update(self) -> None:
        """Perform delayed update"""
        self.update()
    
    def paintEvent(self, event):
        """Custom paint event for minimap rendering"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Clear background
        painter.fillRect(self.rect(), self._background_color)
        
        if self._document_size.isEmpty():
            # No document to display
            painter.setPen(QPen(QColor(128, 128, 128), 1))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Document")
            return
        
        # Calculate minimap rectangle
        minimap_rect = self._calculate_minimap_rect()
        
        # Draw document background
        painter.fillRect(minimap_rect, self._document_color)
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawRect(minimap_rect)
        
        # Draw document thumbnail if available
        if self._document_thumbnail:
            scaled_thumbnail = self._document_thumbnail.scaled(
                minimap_rect.size().toSize(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            painter.drawPixmap(minimap_rect.topLeft().toPoint(), scaled_thumbnail)
        
        # Draw viewport indicator
        self._draw_viewport_indicator(painter, minimap_rect)
        
        # Draw navigation hints
        self._draw_navigation_hints(painter)
    
    def _calculate_minimap_rect(self) -> QRectF:
        """Calculate the minimap rectangle within the widget"""
        if self._document_size.isEmpty():
            return QRectF()
        
        # Center the minimap in the widget with margins
        margin = 10
        available_width = self.width() - 2 * margin
        available_height = self.height() - 2 * margin
        
        # Calculate scaled document size
        scaled_width = self._document_size.width() * self._scale_factor
        scaled_height = self._document_size.height() * self._scale_factor
        
        # Center the scaled document
        x = margin + (available_width - scaled_width) / 2
        y = margin + (available_height - scaled_height) / 2
        
        return QRectF(x, y, scaled_width, scaled_height)
    
    def _draw_viewport_indicator(self, painter: QPainter, minimap_rect: QRectF) -> None:
        """Draw the viewport indicator rectangle"""
        if self._viewport_rect.isEmpty() or minimap_rect.isEmpty():
            return
        
        # Scale viewport rectangle to minimap coordinates
        viewport_minimap = QRectF(
            minimap_rect.x() + (self._viewport_rect.x() / self._document_size.width()) * minimap_rect.width(),
            minimap_rect.y() + (self._viewport_rect.y() / self._document_size.height()) * minimap_rect.height(),
            (self._viewport_rect.width() / self._document_size.width()) * minimap_rect.width(),
            (self._viewport_rect.height() / self._document_size.height()) * minimap_rect.height()
        )
        
        # Ensure viewport is within minimap bounds
        viewport_minimap = viewport_minimap.intersected(minimap_rect)
        
        # Draw viewport indicator
        painter.fillRect(viewport_minimap, self._viewport_color)
        painter.setPen(QPen(self._viewport_border_color, 2))
        painter.drawRect(viewport_minimap)
        
        # Add resize handles if viewport is large enough
        if viewport_minimap.width() > 20 and viewport_minimap.height() > 20:
            self._draw_resize_handles(painter, viewport_minimap)
    
    def _draw_resize_handles(self, painter: QPainter, viewport_rect: QRectF) -> None:
        """Draw resize handles on viewport indicator"""
        handle_size = 6
        handle_color = QColor(255, 255, 255, 200)
        
        # Corner handles
        handles = [
            # Top-left, top-right, bottom-left, bottom-right
            QRectF(viewport_rect.topLeft().x() - handle_size/2, viewport_rect.topLeft().y() - handle_size/2, handle_size, handle_size),
            QRectF(viewport_rect.topRight().x() - handle_size/2, viewport_rect.topRight().y() - handle_size/2, handle_size, handle_size),
            QRectF(viewport_rect.bottomLeft().x() - handle_size/2, viewport_rect.bottomLeft().y() - handle_size/2, handle_size, handle_size),
            QRectF(viewport_rect.bottomRight().x() - handle_size/2, viewport_rect.bottomRight().y() - handle_size/2, handle_size, handle_size)
        ]
        
        painter.fillRect(*handles, handle_color)
        painter.setPen(QPen(self._viewport_border_color, 1))
        for handle in handles:
            painter.drawRect(handle)
    
    def _draw_navigation_hints(self, painter: QPainter) -> None:
        """Draw navigation hints and controls"""
        # Draw zoom level indicator
        if hasattr(self, '_current_zoom'):
            zoom_text = f"Zoom: {self._current_zoom:.0%}"
            painter.setPen(QPen(QColor(64, 64, 64), 1))
            painter.setFont(QFont("", 8))
            painter.drawText(5, 15, zoom_text)
    
    def mousePressEvent(self, event):
        """Handle mouse press for navigation"""
        if event.button() == Qt.MouseButton.LeftButton:
            minimap_rect = self._calculate_minimap_rect()
            
            if minimap_rect.contains(event.position()):
                # Check if clicking on viewport indicator
                viewport_minimap = self._get_viewport_minimap_rect(minimap_rect)
                
                if viewport_minimap.contains(event.position()):
                    # Start dragging viewport
                    self._dragging_viewport = True
                    self._last_mouse_pos = event.position()
                else:
                    # Navigate to clicked point
                    self._navigate_to_point(event.position(), minimap_rect)
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for viewport dragging"""
        if self._dragging_viewport and event.buttons() & Qt.MouseButton.LeftButton:
            minimap_rect = self._calculate_minimap_rect()
            
            # Calculate movement delta
            delta = event.position() - self._last_mouse_pos
            self._last_mouse_pos = event.position()
            
            # Convert minimap delta to document coordinates
            document_delta = QPointF(
                (delta.x() / minimap_rect.width()) * self._document_size.width(),
                (delta.y() / minimap_rect.height()) * self._document_size.height()
            )
            
            # Calculate new viewport center
            new_center = QPointF(
                self._viewport_rect.center().x() + document_delta.x(),
                self._viewport_rect.center().y() + document_delta.y()
            )
            
            # Emit navigation request
            self.navigation_requested.emit(new_center)
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging_viewport = False
        
        super().mouseReleaseEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """Handle double click for zoom to fit"""
        if event.button() == Qt.MouseButton.LeftButton:
            minimap_rect = self._calculate_minimap_rect()
            
            if minimap_rect.contains(event.position()):
                # Convert click point to document coordinates
                relative_x = (event.position().x() - minimap_rect.x()) / minimap_rect.width()
                relative_y = (event.position().y() - minimap_rect.y()) / minimap_rect.height()
                
                document_x = relative_x * self._document_size.width()
                document_y = relative_y * self._document_size.height()
                
                # Create zoom area around click point
                zoom_size = min(self._document_size.width(), self._document_size.height()) * 0.2
                zoom_area = QRectF(
                    document_x - zoom_size/2,
                    document_y - zoom_size/2,
                    zoom_size,
                    zoom_size
                )
                
                self.zoom_to_area_requested.emit(zoom_area)
        
        super().mouseDoubleClickEvent(event)
    
    def _navigate_to_point(self, click_point: QPointF, minimap_rect: QRectF) -> None:
        """Navigate to clicked point on minimap"""
        # Convert minimap coordinates to document coordinates
        relative_x = (click_point.x() - minimap_rect.x()) / minimap_rect.width()
        relative_y = (click_point.y() - minimap_rect.y()) / minimap_rect.height()
        
        document_x = relative_x * self._document_size.width()
        document_y = relative_y * self._document_size.height()
        
        target_point = QPointF(document_x, document_y)
        self.navigation_requested.emit(target_point)
    
    def _get_viewport_minimap_rect(self, minimap_rect: QRectF) -> QRectF:
        """Get viewport rectangle in minimap coordinates"""
        if self._viewport_rect.isEmpty() or minimap_rect.isEmpty():
            return QRectF()
        
        return QRectF(
            minimap_rect.x() + (self._viewport_rect.x() / self._document_size.width()) * minimap_rect.width(),
            minimap_rect.y() + (self._viewport_rect.y() / self._document_size.height()) * minimap_rect.height(),
            (self._viewport_rect.width() / self._document_size.width()) * minimap_rect.width(),
            (self._viewport_rect.height() / self._document_size.height()) * minimap_rect.height()
        )
    
    def set_current_zoom(self, zoom_level: float) -> None:
        """Set current zoom level for display"""
        self._current_zoom = zoom_level
        self._schedule_update()
    
    def resizeEvent(self, event):
        """Handle widget resize"""
        super().resizeEvent(event)
        self._update_scale_factor()
        self._schedule_update()


class MinimapController(QObject):
    """Controller for minimap navigation functionality"""
    
    # Control signals
    navigate_to_point = pyqtSignal(QPointF)
    zoom_to_area = pyqtSignal(QRectF)
    center_on_viewport = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Components
        self._minimap_widget: Optional[MinimapWidget] = None
        self._document_renderer = None
        
        # Configuration
        self._auto_update_enabled = True
        self._thumbnail_quality = 0.3  # 30% of original size for performance
        self._max_thumbnail_size = (400, 300)
        
        # State
        self._current_document = None
        self._cached_thumbnails: Dict[str, QPixmap] = {}
        
        # Performance optimization
        self._thumbnail_timer = QTimer()
        self._thumbnail_timer.setSingleShot(True)
        self._thumbnail_timer.timeout.connect(self._generate_thumbnail)
    
    def set_minimap_widget(self, widget: MinimapWidget) -> None:
        """Set the minimap widget to control"""
        self._minimap_widget = widget
        
        # Connect signals
        widget.navigation_requested.connect(self.navigate_to_point)
        widget.zoom_to_area_requested.connect(self.zoom_to_area)
    
    def set_document_renderer(self, renderer) -> None:
        """Set the document renderer for thumbnail generation"""
        self._document_renderer = renderer
    
    def update_document(self, document_info: Dict[str, Any]) -> None:
        """Update minimap with new document information"""
        self._current_document = document_info
        
        if self._minimap_widget:
            # Update document size
            size = QSizeF(
                document_info.get('width', 0),
                document_info.get('height', 0)
            )
            self._minimap_widget.set_document_size(size)
            
            # Schedule thumbnail generation
            if self._auto_update_enabled:
                self._schedule_thumbnail_generation()
    
    def update_viewport(self, viewport_rect: QRectF, zoom_level: float) -> None:
        """Update minimap viewport indicator"""
        if self._minimap_widget:
            self._minimap_widget.set_viewport_rect(viewport_rect)
            self._minimap_widget.set_current_zoom(zoom_level)
    
    def _schedule_thumbnail_generation(self) -> None:
        """Schedule thumbnail generation with delay"""
        self._thumbnail_timer.start(500)  # 500ms delay
    
    def _generate_thumbnail(self) -> None:
        """Generate document thumbnail for minimap"""
        if not self._current_document or not self._document_renderer:
            return
        
        try:
            document_id = self._current_document.get('id', '')
            
            # Check cache first
            if document_id in self._cached_thumbnails:
                thumbnail = self._cached_thumbnails[document_id]
                if self._minimap_widget:
                    self._minimap_widget.set_document_thumbnail(thumbnail)
                return
            
            # Generate new thumbnail
            thumbnail = self._render_document_thumbnail()
            
            if thumbnail and not thumbnail.isNull():
                # Cache the thumbnail
                self._cached_thumbnails[document_id] = thumbnail
                
                # Update minimap
                if self._minimap_widget:
                    self._minimap_widget.set_document_thumbnail(thumbnail)
        
        except Exception as e:
            print(f"Thumbnail generation error: {e}")
    
    def _render_document_thumbnail(self) -> Optional[QPixmap]:
        """Render document thumbnail using the document renderer"""
        if not self._document_renderer or not self._current_document:
            return None
        
        try:
            # Calculate thumbnail size
            doc_width = self._current_document.get('width', 0)
            doc_height = self._current_document.get('height', 0)
            
            if doc_width <= 0 or doc_height <= 0:
                return None
            
            # Calculate scale to fit in max thumbnail size
            width_scale = self._max_thumbnail_size[0] / doc_width
            height_scale = self._max_thumbnail_size[1] / doc_height
            scale = min(width_scale, height_scale, self._thumbnail_quality)
            
            thumbnail_width = int(doc_width * scale)
            thumbnail_height = int(doc_height * scale)
            
            # Render document at thumbnail scale
            thumbnail = self._document_renderer.render_thumbnail(
                size=(thumbnail_width, thumbnail_height),
                quality=self._thumbnail_quality
            )
            
            return thumbnail
        
        except Exception as e:
            print(f"Document thumbnail rendering error: {e}")
            return None
    
    def set_auto_update(self, enabled: bool) -> None:
        """Enable or disable automatic thumbnail updates"""
        self._auto_update_enabled = enabled
    
    def set_thumbnail_quality(self, quality: float) -> None:
        """Set thumbnail rendering quality (0.1 to 1.0)"""
        self._thumbnail_quality = max(0.1, min(1.0, quality))
    
    def clear_thumbnail_cache(self) -> None:
        """Clear cached thumbnails to free memory"""
        self._cached_thumbnails.clear()
    
    def refresh_thumbnail(self) -> None:
        """Force refresh of current document thumbnail"""
        if self._current_document:
            document_id = self._current_document.get('id', '')
            if document_id in self._cached_thumbnails:
                del self._cached_thumbnails[document_id]
            
            self._schedule_thumbnail_generation()


class MinimapPanel(QWidget):
    """Complete minimap panel with controls and minimap widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Components
        self._minimap_widget = MinimapWidget()
        self._controller = MinimapController()
        
        # Setup controller
        self._controller.set_minimap_widget(self._minimap_widget)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup minimap panel UI"""
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(4, 4, 4, 4)
        self.layout().setSpacing(4)
        
        # Title
        title_label = QLabel("Document Overview")
        title_label.setFont(QFont("", 9, QFont.Weight.Bold))
        self.layout().addWidget(title_label)
        
        # Minimap widget
        self.layout().addWidget(self._minimap_widget)
        
        # Control buttons
        self._create_control_buttons()
        
        # Stretch to push everything to top
        self.layout().addStretch()
    
    def _create_control_buttons(self) -> None:
        """Create minimap control buttons"""
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(4)
        
        # Center viewport button
        center_button = QPushButton("Center")
        center_button.setFixedHeight(24)
        center_button.clicked.connect(self._controller.center_on_viewport)
        button_layout.addWidget(center_button)
        
        # Refresh thumbnail button
        refresh_button = QPushButton("Refresh")
        refresh_button.setFixedHeight(24)
        refresh_button.clicked.connect(self._controller.refresh_thumbnail)
        button_layout.addWidget(refresh_button)
        
        button_layout.addStretch()
        self.layout().addWidget(button_frame)
    
    def get_minimap_widget(self) -> MinimapWidget:
        """Get the minimap widget"""
        return self._minimap_widget
    
    def get_controller(self) -> MinimapController:
        """Get the minimap controller"""
        return self._controller