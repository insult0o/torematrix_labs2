"""
PDF.js Advanced Features Integration.

This module coordinates all advanced PDF features including search, annotations,
text selection, print functionality, and UI framework integration.

Agent 4 Implementation:
- Feature management and coordination
- Integration with all previous agents
- User interface for advanced features
- Production-ready feature delivery
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QAction
from PyQt6.QtGui import QIcon, QKeySequence
from PyQt6.QtWebEngineWidgets import QWebEngineView

from .viewer import PDFViewer
from .bridge import PDFBridge
from .search import SearchManager
from .annotations import AnnotationManager
from .ui import PDFUIManager
from .accessibility import AccessibilityManager

logger = logging.getLogger(__name__)


class FeatureSet(Enum):
    """Available PDF features."""
    SEARCH = "search"
    TEXT_SELECTION = "text_selection"
    ANNOTATIONS = "annotations"
    PRINT = "print"
    ACCESSIBILITY = "accessibility"
    UI_INTEGRATION = "ui_integration"


@dataclass
class FeatureConfig:
    """Configuration for PDF features."""
    # Search Configuration
    search_enabled: bool = True
    search_case_sensitive: bool = False
    search_whole_words: bool = False
    search_regex_enabled: bool = True
    search_history_size: int = 50
    
    # Text Selection Configuration
    text_selection_enabled: bool = True
    clipboard_integration: bool = True
    context_menu_enabled: bool = True
    
    # Annotation Configuration
    annotations_enabled: bool = True
    annotation_overlay: bool = True
    annotation_interaction: bool = True
    
    # Print Configuration
    print_enabled: bool = True
    print_preview: bool = True
    export_to_image: bool = True
    
    # UI Configuration
    toolbar_enabled: bool = True
    thumbnail_panel: bool = True
    progress_indicators: bool = True
    
    # Accessibility Configuration
    accessibility_enabled: bool = True
    screen_reader_support: bool = True
    keyboard_navigation: bool = True
    high_contrast_support: bool = True


@dataclass
class FeatureMetrics:
    """Performance metrics for features."""
    search_time_ms: float = 0.0
    ui_response_time_ms: float = 0.0
    thumbnail_load_time_ms: float = 0.0
    print_preparation_time_ms: float = 0.0
    accessibility_score: float = 0.0
    
    # Target metrics from Agent 4 requirements
    search_target_ms: float = 2000.0
    ui_target_ms: float = 100.0
    thumbnail_target_ms: float = 500.0
    print_target_ms: float = 5000.0
    accessibility_target: float = 0.9  # WCAG 2.1 AA compliance
    
    last_updated: float = field(default_factory=time.time)


class FeatureManager(QObject):
    """
    Advanced PDF.js feature manager and coordinator.
    
    This is the main Agent 4 class that coordinates all advanced features
    and integrates with previous agents to deliver a complete PDF viewing experience.
    
    Features managed:
    - Full-text search with highlighting
    - Text selection and clipboard integration
    - Annotation rendering and interaction
    - Print functionality with options
    - UI framework integration
    - Accessibility compliance
    
    Signals:
        feature_enabled: Emitted when a feature is enabled
        feature_disabled: Emitted when a feature is disabled
        search_completed: Emitted when search operation completes
        text_selected: Emitted when text is selected
        annotation_clicked: Emitted when annotation is clicked
        print_requested: Emitted when print is requested
        metrics_updated: Emitted when feature metrics are updated
    """
    
    # Signals
    feature_enabled = pyqtSignal(str)  # feature_name
    feature_disabled = pyqtSignal(str)  # feature_name
    search_completed = pyqtSignal(str, list)  # query, results
    text_selected = pyqtSignal(str, dict)  # selected_text, coordinates
    annotation_clicked = pyqtSignal(dict)  # annotation_data
    print_requested = pyqtSignal(dict)  # print_options
    metrics_updated = pyqtSignal(FeatureMetrics)
    
    def __init__(self, pdf_viewer: PDFViewer, config: Optional[FeatureConfig] = None):
        """Initialize feature manager.
        
        Args:
            pdf_viewer: PDFViewer instance from Agent 1
            config: Feature configuration
        """
        super().__init__()
        
        self.pdf_viewer = pdf_viewer
        self.config = config or FeatureConfig()
        
        # Feature managers
        self.search_manager: Optional[SearchManager] = None
        self.annotation_manager: Optional[AnnotationManager] = None
        self.ui_manager: Optional[PDFUIManager] = None
        self.accessibility_manager: Optional[AccessibilityManager] = None
        
        # Integration with previous agents
        self.bridge: Optional[PDFBridge] = None  # Agent 2 bridge
        self.performance_config: Optional[Dict] = None  # Agent 3 config
        
        # Feature state
        self.enabled_features: Dict[str, bool] = {}
        self.feature_metrics = FeatureMetrics()
        self.feature_callbacks: Dict[str, List[Callable]] = {}
        
        # Performance monitoring
        self.metrics_timer = QTimer()
        self.metrics_timer.timeout.connect(self._update_metrics)
        self.metrics_timer.start(1000)  # Update every second
        
        # Initialize features
        self._initialize_features()
        
        logger.info("FeatureManager initialized with Agent 4 advanced features")
    
    def _initialize_features(self) -> None:
        """Initialize all feature managers."""
        try:
            # Initialize search manager
            if self.config.search_enabled:
                from .search import SearchManager
                self.search_manager = SearchManager(self.pdf_viewer, self.config)
                self.search_manager.search_completed.connect(self.search_completed.emit)
                self.enabled_features[FeatureSet.SEARCH.value] = True
                logger.debug("Search manager initialized")
            
            # Initialize annotation manager
            if self.config.annotations_enabled:
                from .annotations import AnnotationManager
                self.annotation_manager = AnnotationManager(self.pdf_viewer, self.config)
                self.annotation_manager.annotation_clicked.connect(self.annotation_clicked.emit)
                self.enabled_features[FeatureSet.ANNOTATIONS.value] = True
                logger.debug("Annotation manager initialized")
            
            # Initialize UI manager
            if self.config.toolbar_enabled or self.config.thumbnail_panel:
                from .ui import PDFUIManager
                self.ui_manager = PDFUIManager(self.pdf_viewer, self.config)
                self.enabled_features[FeatureSet.UI_INTEGRATION.value] = True
                logger.debug("UI manager initialized")
            
            # Initialize accessibility manager
            if self.config.accessibility_enabled:
                from .accessibility import AccessibilityManager
                self.accessibility_manager = AccessibilityManager(self.pdf_viewer, self.config)
                self.enabled_features[FeatureSet.ACCESSIBILITY.value] = True
                logger.debug("Accessibility manager initialized")
            
            # Enable text selection by default
            if self.config.text_selection_enabled:
                self.enabled_features[FeatureSet.TEXT_SELECTION.value] = True
            
            # Enable print by default
            if self.config.print_enabled:
                self.enabled_features[FeatureSet.PRINT.value] = True
            
            logger.info(f"Features initialized: {list(self.enabled_features.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to initialize features: {e}")
            raise
    
    def connect_bridge(self, bridge: PDFBridge) -> None:
        """Connect to Agent 2 bridge for JavaScript communication.
        
        Args:
            bridge: PDFBridge instance from Agent 2
        """
        self.bridge = bridge
        
        # Connect bridge signals to feature handlers
        bridge.feature_event.connect(self._handle_feature_event)
        bridge.element_selected.connect(self._handle_element_selected)
        
        # Forward bridge to feature managers
        if self.search_manager:
            self.search_manager.connect_bridge(bridge)
        if self.annotation_manager:
            self.annotation_manager.connect_bridge(bridge)
        if self.ui_manager:
            self.ui_manager.connect_bridge(bridge)
        
        logger.info("Bridge connected to feature manager")
    
    def set_performance_config(self, config: Dict[str, Any]) -> None:
        """Receive performance configuration from Agent 3.
        
        Args:
            config: Performance configuration from Agent 3
        """
        self.performance_config = config
        
        # Forward performance config to feature managers
        if self.search_manager:
            self.search_manager.set_performance_config(config)
        if self.annotation_manager:
            self.annotation_manager.set_performance_config(config)
        if self.ui_manager:
            self.ui_manager.set_performance_config(config)
        
        logger.info("Performance configuration applied to features")
    
    def enable_feature(self, feature: Union[str, FeatureSet]) -> bool:
        """Enable a specific feature.
        
        Args:
            feature: Feature to enable
            
        Returns:
            True if feature was enabled successfully
        """
        feature_name = feature.value if isinstance(feature, FeatureSet) else feature
        
        try:
            if feature_name == FeatureSet.SEARCH.value and self.search_manager:
                self.search_manager.enable()
                self.enabled_features[feature_name] = True
                
            elif feature_name == FeatureSet.ANNOTATIONS.value and self.annotation_manager:
                self.annotation_manager.enable()
                self.enabled_features[feature_name] = True
                
            elif feature_name == FeatureSet.UI_INTEGRATION.value and self.ui_manager:
                self.ui_manager.enable()
                self.enabled_features[feature_name] = True
                
            elif feature_name == FeatureSet.ACCESSIBILITY.value and self.accessibility_manager:
                self.accessibility_manager.enable()
                self.enabled_features[feature_name] = True
                
            elif feature_name in [FeatureSet.TEXT_SELECTION.value, FeatureSet.PRINT.value]:
                # These features are handled directly by the feature manager
                self.enabled_features[feature_name] = True
            
            self.feature_enabled.emit(feature_name)
            logger.info(f"Feature enabled: {feature_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enable feature {feature_name}: {e}")
            return False
    
    def disable_feature(self, feature: Union[str, FeatureSet]) -> bool:
        """Disable a specific feature.
        
        Args:
            feature: Feature to disable
            
        Returns:
            True if feature was disabled successfully
        """
        feature_name = feature.value if isinstance(feature, FeatureSet) else feature
        
        try:
            if feature_name == FeatureSet.SEARCH.value and self.search_manager:
                self.search_manager.disable()
                
            elif feature_name == FeatureSet.ANNOTATIONS.value and self.annotation_manager:
                self.annotation_manager.disable()
                
            elif feature_name == FeatureSet.UI_INTEGRATION.value and self.ui_manager:
                self.ui_manager.disable()
                
            elif feature_name == FeatureSet.ACCESSIBILITY.value and self.accessibility_manager:
                self.accessibility_manager.disable()
            
            self.enabled_features[feature_name] = False
            self.feature_disabled.emit(feature_name)
            logger.info(f"Feature disabled: {feature_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disable feature {feature_name}: {e}")
            return False
    
    def is_feature_enabled(self, feature: Union[str, FeatureSet]) -> bool:
        """Check if a feature is enabled.
        
        Args:
            feature: Feature to check
            
        Returns:
            True if feature is enabled
        """
        feature_name = feature.value if isinstance(feature, FeatureSet) else feature
        return self.enabled_features.get(feature_name, False)
    
    def get_enabled_features(self) -> List[str]:
        """Get list of enabled features.
        
        Returns:
            List of enabled feature names
        """
        return [name for name, enabled in self.enabled_features.items() if enabled]
    
    def search_text(self, query: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """Perform text search in PDF.
        
        Args:
            query: Search query
            options: Search options (case_sensitive, whole_words, regex)
            
        Returns:
            True if search was initiated successfully
        """
        if not self.search_manager or not self.is_feature_enabled(FeatureSet.SEARCH):
            logger.warning("Search feature not available")
            return False
        
        start_time = time.time()
        result = self.search_manager.search(query, options or {})
        
        # Update metrics
        self.feature_metrics.search_time_ms = (time.time() - start_time) * 1000
        
        return result
    
    def select_text(self, start_coords: Dict[str, Any], end_coords: Dict[str, Any]) -> str:
        """Select text in PDF.
        
        Args:
            start_coords: Start coordinates for selection
            end_coords: End coordinates for selection
            
        Returns:
            Selected text content
        """
        if not self.is_feature_enabled(FeatureSet.TEXT_SELECTION):
            logger.warning("Text selection feature not enabled")
            return ""
        
        start_time = time.time()
        
        # Send text selection command to JavaScript
        if self.bridge:
            self.bridge.send_feature_command("text_selection", "select_text", {
                "start": start_coords,
                "end": end_coords
            })
        
        # Update metrics
        self.feature_metrics.ui_response_time_ms = (time.time() - start_time) * 1000
        
        return ""  # Text will be returned via bridge callback
    
    def show_annotation(self, annotation_id: str) -> bool:
        """Show annotation in PDF.
        
        Args:
            annotation_id: ID of annotation to show
            
        Returns:
            True if annotation was shown successfully
        """
        if not self.annotation_manager or not self.is_feature_enabled(FeatureSet.ANNOTATIONS):
            logger.warning("Annotation feature not available")
            return False
        
        return self.annotation_manager.show_annotation(annotation_id)
    
    def print_document(self, options: Optional[Dict[str, Any]] = None) -> bool:
        """Print PDF document.
        
        Args:
            options: Print options (page_range, quality, etc.)
            
        Returns:
            True if print was initiated successfully
        """
        if not self.is_feature_enabled(FeatureSet.PRINT):
            logger.warning("Print feature not enabled")
            return False
        
        start_time = time.time()
        
        # Send print command to JavaScript
        if self.bridge:
            self.bridge.send_feature_command("print", "print_document", options or {})
            self.print_requested.emit(options or {})
        
        # Update metrics
        self.feature_metrics.print_preparation_time_ms = (time.time() - start_time) * 1000
        
        return True
    
    def _handle_feature_event(self, feature_name: str, data: Dict[str, Any]) -> None:
        """Handle feature events from JavaScript bridge.
        
        Args:
            feature_name: Name of the feature
            data: Event data
        """
        try:
            if feature_name == "search":
                if self.search_manager:
                    self.search_manager.handle_js_event(data)
                    
            elif feature_name == "text_selection":
                if data.get("type") == "text_selected":
                    self.text_selected.emit(data.get("text", ""), data.get("coordinates", {}))
                    
            elif feature_name == "annotations":
                if self.annotation_manager:
                    self.annotation_manager.handle_js_event(data)
                    
            elif feature_name == "print":
                if data.get("type") == "print_ready":
                    logger.info("Print preparation completed")
                    
            # Trigger feature callbacks
            if feature_name in self.feature_callbacks:
                for callback in self.feature_callbacks[feature_name]:
                    try:
                        callback(data)
                    except Exception as e:
                        logger.error(f"Feature callback error: {e}")
                        
        except Exception as e:
            logger.error(f"Error handling feature event {feature_name}: {e}")
    
    def _handle_element_selected(self, selection_event) -> None:
        """Handle element selection from bridge.
        
        Args:
            selection_event: Selection event from bridge
        """
        if self.is_feature_enabled(FeatureSet.TEXT_SELECTION):
            # Forward to text selection handling
            self.text_selected.emit(
                selection_event.text_content or "",
                {
                    "page": selection_event.coordinates.page,
                    "x": selection_event.coordinates.x,
                    "y": selection_event.coordinates.y,
                    "width": selection_event.coordinates.width,
                    "height": selection_event.coordinates.height
                }
            )
    
    def _update_metrics(self) -> None:
        """Update feature performance metrics."""
        try:
            # Update metrics from feature managers
            if self.search_manager:
                search_metrics = self.search_manager.get_metrics()
                self.feature_metrics.search_time_ms = search_metrics.get("avg_search_time_ms", 0)
            
            if self.ui_manager:
                ui_metrics = self.ui_manager.get_metrics()
                self.feature_metrics.ui_response_time_ms = ui_metrics.get("avg_response_time_ms", 0)
                self.feature_metrics.thumbnail_load_time_ms = ui_metrics.get("thumbnail_load_time_ms", 0)
            
            if self.accessibility_manager:
                accessibility_metrics = self.accessibility_manager.get_metrics()
                self.feature_metrics.accessibility_score = accessibility_metrics.get("compliance_score", 0)
            
            self.feature_metrics.last_updated = time.time()
            self.metrics_updated.emit(self.feature_metrics)
            
        except Exception as e:
            logger.error(f"Error updating feature metrics: {e}")
    
    def get_feature_metrics(self) -> FeatureMetrics:
        """Get current feature performance metrics.
        
        Returns:
            Current feature metrics
        """
        return self.feature_metrics
    
    def add_feature_callback(self, feature_name: str, callback: Callable) -> None:
        """Add callback for feature events.
        
        Args:
            feature_name: Name of the feature
            callback: Callback function
        """
        if feature_name not in self.feature_callbacks:
            self.feature_callbacks[feature_name] = []
        self.feature_callbacks[feature_name].append(callback)
    
    def remove_feature_callback(self, feature_name: str, callback: Callable) -> None:
        """Remove callback for feature events.
        
        Args:
            feature_name: Name of the feature
            callback: Callback function to remove
        """
        if feature_name in self.feature_callbacks:
            try:
                self.feature_callbacks[feature_name].remove(callback)
            except ValueError:
                pass
    
    def get_feature_status(self) -> Dict[str, Any]:
        """Get comprehensive feature status.
        
        Returns:
            Dictionary containing feature status and metrics
        """
        return {
            "enabled_features": self.get_enabled_features(),
            "feature_metrics": {
                "search_time_ms": self.feature_metrics.search_time_ms,
                "ui_response_time_ms": self.feature_metrics.ui_response_time_ms,
                "thumbnail_load_time_ms": self.feature_metrics.thumbnail_load_time_ms,
                "print_preparation_time_ms": self.feature_metrics.print_preparation_time_ms,
                "accessibility_score": self.feature_metrics.accessibility_score
            },
            "target_metrics": {
                "search_target_ms": self.feature_metrics.search_target_ms,
                "ui_target_ms": self.feature_metrics.ui_target_ms,
                "thumbnail_target_ms": self.feature_metrics.thumbnail_target_ms,
                "print_target_ms": self.feature_metrics.print_target_ms,
                "accessibility_target": self.feature_metrics.accessibility_target
            },
            "targets_met": {
                "search": self.feature_metrics.search_time_ms <= self.feature_metrics.search_target_ms,
                "ui": self.feature_metrics.ui_response_time_ms <= self.feature_metrics.ui_target_ms,
                "thumbnail": self.feature_metrics.thumbnail_load_time_ms <= self.feature_metrics.thumbnail_target_ms,
                "print": self.feature_metrics.print_preparation_time_ms <= self.feature_metrics.print_target_ms,
                "accessibility": self.feature_metrics.accessibility_score >= self.feature_metrics.accessibility_target
            },
            "agent_integration": {
                "agent_1_viewer": self.pdf_viewer is not None,
                "agent_2_bridge": self.bridge is not None,
                "agent_3_performance": self.performance_config is not None
            }
        }
    
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Stop metrics timer
            if self.metrics_timer:
                self.metrics_timer.stop()
            
            # Cleanup feature managers
            if self.search_manager:
                self.search_manager.cleanup()
            if self.annotation_manager:
                self.annotation_manager.cleanup()
            if self.ui_manager:
                self.ui_manager.cleanup()
            if self.accessibility_manager:
                self.accessibility_manager.cleanup()
            
            # Clear callbacks
            self.feature_callbacks.clear()
            
            logger.info("FeatureManager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")