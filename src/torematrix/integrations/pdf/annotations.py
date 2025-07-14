"""
PDF.js Annotation System.

This module provides comprehensive annotation support for PDF documents
including rendering, interaction, overlay positioning, and metadata access.

Agent 4 Implementation:
- PDF annotation rendering (text, image, shapes)
- Annotation interaction (click, hover, show/hide)
- Overlay system with proper positioning
- Annotation data extraction and metadata
- Visibility toggles and filtering
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal, QPointF, QRectF
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QCheckBox, QPushButton
from PyQt6.QtGui import QColor, QPen, QBrush, QPainter
from PyQt6.QtWebEngineWidgets import QWebEngineView

logger = logging.getLogger(__name__)


class AnnotationType(Enum):
    """PDF annotation types."""
    TEXT = "text"
    HIGHLIGHT = "highlight"
    UNDERLINE = "underline"
    STRIKEOUT = "strikeout"
    SQUIGGLY = "squiggly"
    NOTE = "note"
    FREETEXT = "freetext"
    LINE = "line"
    SQUARE = "square"
    CIRCLE = "circle"
    POLYGON = "polygon"
    POLYLINE = "polyline"
    STAMP = "stamp"
    INK = "ink"
    POPUP = "popup"
    FILEATTACHMENT = "fileattachment"
    SOUND = "sound"
    MOVIE = "movie"
    WIDGET = "widget"
    LINK = "link"


class AnnotationState(Enum):
    """Annotation interaction states."""
    NORMAL = "normal"
    HOVER = "hover"
    SELECTED = "selected"
    HIDDEN = "hidden"


@dataclass
class AnnotationCoordinates:
    """Annotation positioning coordinates."""
    page: int
    x: float
    y: float
    width: float
    height: float
    rotation: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "page": self.page,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation
        }
    
    def to_qrectf(self) -> QRectF:
        """Convert to Qt rectangle."""
        return QRectF(self.x, self.y, self.width, self.height)


@dataclass
class AnnotationStyle:
    """Annotation visual styling."""
    color: str = "#ffff00"  # Yellow
    opacity: float = 0.5
    border_color: str = "#ff0000"  # Red
    border_width: float = 1.0
    font_size: float = 12.0
    font_family: str = "Arial"
    text_color: str = "#000000"  # Black
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "color": self.color,
            "opacity": self.opacity,
            "border_color": self.border_color,
            "border_width": self.border_width,
            "font_size": self.font_size,
            "font_family": self.font_family,
            "text_color": self.text_color
        }


@dataclass
class PDFAnnotation:
    """Represents a PDF annotation with full metadata."""
    id: str
    type: AnnotationType
    coordinates: AnnotationCoordinates
    content: str = ""
    title: str = ""
    author: str = ""
    subject: str = ""
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    style: Optional[AnnotationStyle] = None
    state: AnnotationState = AnnotationState.NORMAL
    visible: bool = True
    interactive: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize default style if not provided."""
        if self.style is None:
            self.style = AnnotationStyle()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "coordinates": self.coordinates.to_dict(),
            "content": self.content,
            "title": self.title,
            "author": self.author,
            "subject": self.subject,
            "creation_date": self.creation_date,
            "modification_date": self.modification_date,
            "style": self.style.to_dict() if self.style else None,
            "state": self.state.value,
            "visible": self.visible,
            "interactive": self.interactive,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PDFAnnotation':
        """Create annotation from dictionary."""
        coords_data = data["coordinates"]
        coordinates = AnnotationCoordinates(**coords_data)
        
        style_data = data.get("style")
        style = AnnotationStyle(**style_data) if style_data else None
        
        return cls(
            id=data["id"],
            type=AnnotationType(data["type"]),
            coordinates=coordinates,
            content=data.get("content", ""),
            title=data.get("title", ""),
            author=data.get("author", ""),
            subject=data.get("subject", ""),
            creation_date=data.get("creation_date"),
            modification_date=data.get("modification_date"),
            style=style,
            state=AnnotationState(data.get("state", "normal")),
            visible=data.get("visible", True),
            interactive=data.get("interactive", True),
            metadata=data.get("metadata", {})
        )


@dataclass
class AnnotationMetrics:
    """Annotation system performance metrics."""
    total_annotations: int = 0
    visible_annotations: int = 0
    annotations_by_type: Dict[str, int] = field(default_factory=dict)
    avg_render_time_ms: float = 0.0
    interaction_response_time_ms: float = 0.0
    overlay_update_time_ms: float = 0.0
    last_updated: float = field(default_factory=time.time)


class AnnotationManager(QObject):
    """
    Advanced PDF annotation management system.
    
    Provides comprehensive annotation support including:
    - Annotation rendering with proper positioning
    - Interactive annotation system (click, hover, selection)
    - Annotation overlay management
    - Metadata access and extraction
    - Visibility controls and filtering
    - Performance monitoring
    
    Signals:
        annotation_loaded: Emitted when annotations are loaded
        annotation_clicked: Emitted when annotation is clicked
        annotation_hovered: Emitted when annotation is hovered
        annotation_selected: Emitted when annotation is selected
        annotation_visibility_changed: Emitted when visibility changes
        metrics_updated: Emitted when metrics are updated
    """
    
    # Signals
    annotation_loaded = pyqtSignal(list)  # annotations
    annotation_clicked = pyqtSignal(PDFAnnotation)
    annotation_hovered = pyqtSignal(PDFAnnotation)
    annotation_selected = pyqtSignal(PDFAnnotation)
    annotation_visibility_changed = pyqtSignal(str, bool)  # annotation_id, visible
    metrics_updated = pyqtSignal(AnnotationMetrics)
    
    def __init__(self, pdf_viewer: QWebEngineView, config: Any):
        """Initialize annotation manager.
        
        Args:
            pdf_viewer: PDF viewer instance
            config: Feature configuration
        """
        super().__init__()
        
        self.pdf_viewer = pdf_viewer
        self.config = config
        
        # Annotation storage
        self.annotations: Dict[str, PDFAnnotation] = {}
        self.annotations_by_page: Dict[int, List[str]] = {}
        self.selected_annotation: Optional[PDFAnnotation] = None
        
        # Visibility filtering
        self.visible_types: Dict[AnnotationType, bool] = {
            ann_type: True for ann_type in AnnotationType
        }
        self.annotation_filters: Dict[str, Callable] = {}
        
        # Performance monitoring
        self.metrics = AnnotationMetrics()
        self.render_times: List[float] = []
        
        # JavaScript communication
        self.bridge = None
        self.performance_config = None
        
        # UI components
        self.annotation_panel: Optional[QWidget] = None
        self.enabled = True
        
        logger.info("AnnotationManager initialized")
    
    def connect_bridge(self, bridge) -> None:
        """Connect to PDF bridge for JavaScript communication.
        
        Args:
            bridge: PDFBridge instance
        """
        self.bridge = bridge
        logger.info("Annotation manager connected to bridge")
    
    def set_performance_config(self, config: Dict[str, Any]) -> None:
        """Set performance configuration from Agent 3.
        
        Args:
            config: Performance configuration
        """
        self.performance_config = config
        logger.debug("Annotation performance configuration updated")
    
    def enable(self) -> None:
        """Enable annotation functionality."""
        self.enabled = True
        self._refresh_annotations()
        logger.info("Annotation functionality enabled")
    
    def disable(self) -> None:
        """Disable annotation functionality."""
        self.enabled = False
        self._hide_all_annotations()
        logger.info("Annotation functionality disabled")
    
    def load_annotations(self) -> bool:
        """Load annotations from PDF document.
        
        Returns:
            True if annotations were loaded successfully
        """
        if not self.enabled:
            return False
        
        try:
            # Request annotations from JavaScript
            if self.bridge:
                self.bridge.send_feature_command("annotations", "load_annotations", {})
                return True
            else:
                # Fallback: direct JavaScript execution
                js_code = """
                    if (typeof window.loadAnnotations === 'function') {
                        window.loadAnnotations();
                    }
                """
                self.pdf_viewer.page().runJavaScript(js_code)
                return True
                
        except Exception as e:
            logger.error(f"Failed to load annotations: {e}")
            return False
    
    def handle_js_event(self, data: Dict[str, Any]) -> None:
        """Handle annotation events from JavaScript.
        
        Args:
            data: Event data from JavaScript
        """
        try:
            event_type = data.get("type")
            
            if event_type == "annotations_loaded":
                self._handle_annotations_loaded(data)
            elif event_type == "annotation_clicked":
                self._handle_annotation_clicked(data)
            elif event_type == "annotation_hovered":
                self._handle_annotation_hovered(data)
            elif event_type == "annotation_render_complete":
                self._handle_render_complete(data)
            
        except Exception as e:
            logger.error(f"Error handling annotation event: {e}")
    
    def _handle_annotations_loaded(self, data: Dict[str, Any]) -> None:
        """Handle annotations loaded from JavaScript.
        
        Args:
            data: Annotations data
        """
        try:
            annotations_data = data.get("annotations", [])
            
            # Clear existing annotations
            self.annotations.clear()
            self.annotations_by_page.clear()
            
            # Load new annotations
            for ann_data in annotations_data:
                annotation = PDFAnnotation.from_dict(ann_data)
                self.annotations[annotation.id] = annotation
                
                # Index by page
                page = annotation.coordinates.page
                if page not in self.annotations_by_page:
                    self.annotations_by_page[page] = []
                self.annotations_by_page[page].append(annotation.id)
            
            # Update metrics
            self._update_metrics()
            
            # Emit loaded signal
            annotation_list = list(self.annotations.values())
            self.annotation_loaded.emit([ann.to_dict() for ann in annotation_list])
            
            logger.info(f"Loaded {len(self.annotations)} annotations")
            
        except Exception as e:
            logger.error(f"Error handling loaded annotations: {e}")
    
    def _handle_annotation_clicked(self, data: Dict[str, Any]) -> None:
        """Handle annotation click from JavaScript.
        
        Args:
            data: Click event data
        """
        try:
            annotation_id = data.get("annotation_id")
            if annotation_id and annotation_id in self.annotations:
                annotation = self.annotations[annotation_id]
                annotation.state = AnnotationState.SELECTED
                self.selected_annotation = annotation
                
                # Emit clicked signal
                self.annotation_clicked.emit(annotation)
                
                logger.debug(f"Annotation clicked: {annotation_id}")
            
        except Exception as e:
            logger.error(f"Error handling annotation click: {e}")
    
    def _handle_annotation_hovered(self, data: Dict[str, Any]) -> None:
        """Handle annotation hover from JavaScript.
        
        Args:
            data: Hover event data
        """
        try:
            annotation_id = data.get("annotation_id")
            is_hovering = data.get("hovering", False)
            
            if annotation_id and annotation_id in self.annotations:
                annotation = self.annotations[annotation_id]
                
                if is_hovering:
                    annotation.state = AnnotationState.HOVER
                    self.annotation_hovered.emit(annotation)
                else:
                    annotation.state = AnnotationState.NORMAL
                
                logger.debug(f"Annotation hover: {annotation_id} (hovering: {is_hovering})")
            
        except Exception as e:
            logger.error(f"Error handling annotation hover: {e}")
    
    def _handle_render_complete(self, data: Dict[str, Any]) -> None:
        """Handle annotation render completion.
        
        Args:
            data: Render completion data
        """
        try:
            render_time_ms = data.get("render_time_ms", 0)
            self.render_times.append(render_time_ms)
            
            # Keep only last 50 render times
            if len(self.render_times) > 50:
                self.render_times.pop(0)
            
            # Update average render time
            self.metrics.avg_render_time_ms = sum(self.render_times) / len(self.render_times)
            self.metrics.last_updated = time.time()
            
        except Exception as e:
            logger.error(f"Error handling render completion: {e}")
    
    def show_annotation(self, annotation_id: str) -> bool:
        """Show specific annotation.
        
        Args:
            annotation_id: ID of annotation to show
            
        Returns:
            True if annotation was shown successfully
        """
        if annotation_id not in self.annotations:
            return False
        
        try:
            annotation = self.annotations[annotation_id]
            annotation.visible = True
            
            # Send show command to JavaScript
            if self.bridge:
                self.bridge.send_feature_command("annotations", "show_annotation", {
                    "annotation_id": annotation_id
                })
            
            # Emit visibility changed signal
            self.annotation_visibility_changed.emit(annotation_id, True)
            
            logger.debug(f"Annotation shown: {annotation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error showing annotation {annotation_id}: {e}")
            return False
    
    def hide_annotation(self, annotation_id: str) -> bool:
        """Hide specific annotation.
        
        Args:
            annotation_id: ID of annotation to hide
            
        Returns:
            True if annotation was hidden successfully
        """
        if annotation_id not in self.annotations:
            return False
        
        try:
            annotation = self.annotations[annotation_id]
            annotation.visible = False
            
            # Send hide command to JavaScript
            if self.bridge:
                self.bridge.send_feature_command("annotations", "hide_annotation", {
                    "annotation_id": annotation_id
                })
            
            # Emit visibility changed signal
            self.annotation_visibility_changed.emit(annotation_id, False)
            
            logger.debug(f"Annotation hidden: {annotation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error hiding annotation {annotation_id}: {e}")
            return False
    
    def toggle_annotation_type(self, annotation_type: AnnotationType, visible: bool) -> None:
        """Toggle visibility of all annotations of a specific type.
        
        Args:
            annotation_type: Type of annotation to toggle
            visible: Whether to show or hide
        """
        try:
            self.visible_types[annotation_type] = visible
            
            # Update all annotations of this type
            for annotation in self.annotations.values():
                if annotation.type == annotation_type:
                    if visible:
                        self.show_annotation(annotation.id)
                    else:
                        self.hide_annotation(annotation.id)
            
            logger.info(f"Toggled {annotation_type.value} annotations: {visible}")
            
        except Exception as e:
            logger.error(f"Error toggling annotation type {annotation_type}: {e}")
    
    def get_annotations_on_page(self, page_number: int) -> List[PDFAnnotation]:
        """Get all annotations on a specific page.
        
        Args:
            page_number: Page number
            
        Returns:
            List of annotations on the page
        """
        annotation_ids = self.annotations_by_page.get(page_number, [])
        return [self.annotations[ann_id] for ann_id in annotation_ids if ann_id in self.annotations]
    
    def get_annotations_by_type(self, annotation_type: AnnotationType) -> List[PDFAnnotation]:
        """Get all annotations of a specific type.
        
        Args:
            annotation_type: Type of annotation
            
        Returns:
            List of annotations of the specified type
        """
        return [ann for ann in self.annotations.values() if ann.type == annotation_type]
    
    def get_visible_annotations(self) -> List[PDFAnnotation]:
        """Get all visible annotations.
        
        Returns:
            List of visible annotations
        """
        return [ann for ann in self.annotations.values() if ann.visible]
    
    def search_annotations(self, query: str, field: str = "content") -> List[PDFAnnotation]:
        """Search annotations by content or metadata.
        
        Args:
            query: Search query
            field: Field to search in (content, title, author, subject)
            
        Returns:
            List of matching annotations
        """
        results = []
        query_lower = query.lower()
        
        for annotation in self.annotations.values():
            search_text = ""
            
            if field == "content":
                search_text = annotation.content.lower()
            elif field == "title":
                search_text = annotation.title.lower()
            elif field == "author":
                search_text = annotation.author.lower()
            elif field == "subject":
                search_text = annotation.subject.lower()
            
            if query_lower in search_text:
                results.append(annotation)
        
        return results
    
    def _refresh_annotations(self) -> None:
        """Refresh annotation display."""
        if self.enabled:
            for annotation in self.annotations.values():
                if annotation.visible and self.visible_types.get(annotation.type, True):
                    self.show_annotation(annotation.id)
    
    def _hide_all_annotations(self) -> None:
        """Hide all annotations."""
        for annotation_id in self.annotations.keys():
            self.hide_annotation(annotation_id)
    
    def _update_metrics(self) -> None:
        """Update annotation metrics."""
        self.metrics.total_annotations = len(self.annotations)
        self.metrics.visible_annotations = len(self.get_visible_annotations())
        
        # Count by type
        self.metrics.annotations_by_type.clear()
        for annotation in self.annotations.values():
            type_name = annotation.type.value
            self.metrics.annotations_by_type[type_name] = \
                self.metrics.annotations_by_type.get(type_name, 0) + 1
        
        self.metrics.last_updated = time.time()
        self.metrics_updated.emit(self.metrics)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get annotation system metrics.
        
        Returns:
            Dictionary containing annotation metrics
        """
        return {
            "total_annotations": self.metrics.total_annotations,
            "visible_annotations": self.metrics.visible_annotations,
            "annotations_by_type": self.metrics.annotations_by_type.copy(),
            "avg_render_time_ms": self.metrics.avg_render_time_ms,
            "interaction_response_time_ms": self.metrics.interaction_response_time_ms,
            "overlay_update_time_ms": self.metrics.overlay_update_time_ms,
            "visible_types": {t.value: v for t, v in self.visible_types.items()}
        }
    
    def create_annotation_panel(self, parent: Optional[QWidget] = None) -> QWidget:
        """Create annotation management panel.
        
        Args:
            parent: Parent widget
            
        Returns:
            Annotation panel widget
        """
        if self.annotation_panel:
            return self.annotation_panel
        
        # Create main widget
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        
        # Type filters
        filters_layout = QVBoxLayout()
        filters_layout.addWidget(QLabel("Annotation Types:"))
        
        self.type_checkboxes = {}
        for ann_type in AnnotationType:
            checkbox = QCheckBox(ann_type.value.replace("_", " ").title())
            checkbox.setChecked(self.visible_types[ann_type])
            checkbox.toggled.connect(
                lambda checked, t=ann_type: self.toggle_annotation_type(t, checked)
            )
            self.type_checkboxes[ann_type] = checkbox
            filters_layout.addWidget(checkbox)
        
        layout.addLayout(filters_layout)
        
        # Annotation list
        layout.addWidget(QLabel("Annotations:"))
        self.annotation_list = QListWidget()
        self.annotation_list.itemClicked.connect(self._on_annotation_list_clicked)
        layout.addWidget(self.annotation_list)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_annotations)
        button_layout.addWidget(refresh_btn)
        
        hide_all_btn = QPushButton("Hide All")
        hide_all_btn.clicked.connect(self._hide_all_annotations)
        button_layout.addWidget(hide_all_btn)
        
        show_all_btn = QPushButton("Show All")
        show_all_btn.clicked.connect(self._refresh_annotations)
        button_layout.addWidget(show_all_btn)
        
        layout.addLayout(button_layout)
        
        # Connect signals
        self.annotation_loaded.connect(self._update_annotation_list)
        
        self.annotation_panel = widget
        return widget
    
    def _on_annotation_list_clicked(self, item: QListWidgetItem) -> None:
        """Handle annotation list item click.
        
        Args:
            item: Clicked list item
        """
        annotation_id = item.data(Qt.UserRole)
        if annotation_id and annotation_id in self.annotations:
            annotation = self.annotations[annotation_id]
            self.annotation_selected.emit(annotation)
    
    def _update_annotation_list(self, annotations: List[Dict]) -> None:
        """Update annotation list widget.
        
        Args:
            annotations: List of annotation data
        """
        self.annotation_list.clear()
        
        for ann_data in annotations:
            annotation = self.annotations.get(ann_data["id"])
            if annotation:
                item_text = f"{annotation.type.value}: {annotation.title or annotation.content[:50]}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, annotation.id)
                self.annotation_list.addItem(item)
    
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            self.annotations.clear()
            self.annotations_by_page.clear()
            self.render_times.clear()
            
            if self.annotation_panel:
                self.annotation_panel.deleteLater()
                self.annotation_panel = None
            
            logger.info("AnnotationManager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during annotation cleanup: {e}")