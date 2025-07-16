"""
ValidationToolbar - Contextual toolbar for manual validation operations.

Agent 3 implementation for Issue #242 - UI Components & User Experience.
This module provides a responsive toolbar with drawing tools, validation controls,
and performance-optimized state management.
"""

import logging
from enum import Enum, auto
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from datetime import datetime

from PyQt6.QtWidgets import (
    QToolBar, QAction, QActionGroup, QComboBox, QSpinBox, QLabel,
    QSeparator, QPushButton, QButtonGroup, QMenu, QWidgetAction,
    QSlider, QCheckBox, QFrame, QHBoxLayout, QVBoxLayout, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSettings, QSize
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QPen, QBrush, QColor, QFont,
    QKeySequence, QAction as QActionBase
)

from .drawing_state import DrawingStateManager, DrawingState, DrawingMode
from ....core.models import ElementType


class ToolbarMode(Enum):
    """Toolbar display modes for different contexts."""
    MINIMAL = auto()
    STANDARD = auto()
    ADVANCED = auto()
    EXPERT = auto()


@dataclass
class ToolbarConfig:
    """Configuration for toolbar appearance and behavior."""
    mode: ToolbarMode = ToolbarMode.STANDARD
    show_icons: bool = True
    show_text: bool = True
    icon_size: int = 24
    auto_hide: bool = False
    floating: bool = False
    orientation: Qt.Orientation = Qt.Orientation.Horizontal


class ValidationToolbar(QToolBar):
    """
    Contextual toolbar for manual validation operations.
    
    Provides drawing tools, validation controls, and state management
    with performance optimization and responsive design.
    """
    
    # Signals for UI integration
    tool_selected = pyqtSignal(str)  # tool_name
    mode_changed = pyqtSignal(ToolbarMode)
    element_type_selected = pyqtSignal(ElementType)
    zoom_requested = pyqtSignal(float)  # zoom_factor
    action_triggered = pyqtSignal(str, dict)  # action_name, parameters
    
    def __init__(self, state_manager: DrawingStateManager, parent=None):
        """Initialize the validation toolbar."""
        super().__init__("Validation Tools", parent)
        
        self.logger = logging.getLogger("torematrix.ui.toolbar")
        self.state_manager = state_manager
        self.config = ToolbarConfig()
        
        # Performance optimization
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._delayed_update)
        
        # State tracking
        self._current_tool = None
        self._tool_actions = {}
        self._action_groups = {}
        self._custom_widgets = {}
        
        # Settings persistence
        self.settings = QSettings("ToreMatrix", "ValidationToolbar")
        
        # Setup toolbar
        self._setup_toolbar()
        self._create_actions()
        self._create_widgets()
        self._setup_layout()
        self._connect_signals()
        self._load_settings()
        
        self.logger.info("ValidationToolbar initialized")
    
    def _setup_toolbar(self):
        """Configure toolbar properties."""
        self.setMovable(True)
        self.setFloatable(True)
        self.setAllowedAreas(
            Qt.ToolBarArea.TopToolBarArea | 
            Qt.ToolBarArea.BottomToolBarArea |
            Qt.ToolBarArea.LeftToolBarArea |
            Qt.ToolBarArea.RightToolBarArea
        )
        
        # Performance: Set icon size to avoid constant rescaling
        self.setIconSize(QSize(self.config.icon_size, self.config.icon_size))
        
        # Professional styling
        self.setStyleSheet("""
            QToolBar {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #f8f9fa, stop: 1 #e9ecef);
                border: 1px solid #dee2e6;
                border-radius: 4px;
                spacing: 2px;
                padding: 4px;
            }
            QToolBar::handle {
                background: #6c757d;
                width: 8px;
                margin: 2px;
                border-radius: 2px;
            }
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 3px;
                padding: 4px;
                margin: 1px;
            }
            QToolButton:hover {
                background: #e9ecef;
                border-color: #adb5bd;
            }
            QToolButton:pressed {
                background: #dee2e6;
                border-color: #6c757d;
            }
            QToolButton:checked {
                background: #007bff;
                color: white;
                border-color: #0056b3;
            }
        """)
    
    def _create_actions(self):
        """Create toolbar actions."""
        # Drawing tool actions
        self._create_drawing_tools()
        
        # Mode control actions
        self._create_mode_controls()
        
        # Validation actions
        self._create_validation_actions()
        
        # View control actions
        self._create_view_controls()
        
        # Quick action buttons
        self._create_quick_actions()
    
    def _create_drawing_tools(self):
        """Create drawing tool actions."""
        tool_group = QActionGroup(self)
        tool_group.setExclusive(True)
        
        # Rectangle selection tool
        rect_action = QAction("Rectangle", self)
        rect_action.setCheckable(True)
        rect_action.setChecked(True)
        rect_action.setIcon(self._create_tool_icon("rectangle"))
        rect_action.setShortcut(QKeySequence("R"))
        rect_action.setToolTip("Rectangle Selection Tool (R)")
        rect_action.triggered.connect(lambda: self._select_tool("rectangle"))
        
        # Polygon selection tool
        polygon_action = QAction("Polygon", self)
        polygon_action.setCheckable(True)
        polygon_action.setIcon(self._create_tool_icon("polygon"))
        polygon_action.setShortcut(QKeySequence("P"))
        polygon_action.setToolTip("Polygon Selection Tool (P)")
        polygon_action.triggered.connect(lambda: self._select_tool("polygon"))
        
        # Freehand selection tool
        freehand_action = QAction("Freehand", self)
        freehand_action.setCheckable(True)
        freehand_action.setIcon(self._create_tool_icon("freehand"))
        freehand_action.setShortcut(QKeySequence("F"))
        freehand_action.setToolTip("Freehand Selection Tool (F)")
        freehand_action.triggered.connect(lambda: self._select_tool("freehand"))
        
        # Add to group and store
        for action in [rect_action, polygon_action, freehand_action]:
            tool_group.addAction(action)
        
        self._action_groups["drawing_tools"] = tool_group
        self._tool_actions.update({
            "rectangle": rect_action,
            "polygon": polygon_action,
            "freehand": freehand_action
        })
    
    def _create_mode_controls(self):
        """Create mode control actions."""
        mode_group = QActionGroup(self)
        mode_group.setExclusive(True)
        
        # Selection mode
        select_mode = QAction("Select", self)
        select_mode.setCheckable(True)
        select_mode.setChecked(True)
        select_mode.setIcon(self._create_mode_icon("select"))
        select_mode.setShortcut(QKeySequence("S"))
        select_mode.setToolTip("Selection Mode (S)")
        select_mode.triggered.connect(lambda: self._set_drawing_mode(DrawingMode.SELECTION))
        
        # Drawing mode
        draw_mode = QAction("Draw", self)
        draw_mode.setCheckable(True)
        draw_mode.setIcon(self._create_mode_icon("draw"))
        draw_mode.setShortcut(QKeySequence("D"))
        draw_mode.setToolTip("Drawing Mode (D)")
        draw_mode.triggered.connect(lambda: self._set_drawing_mode(DrawingMode.DRAWING))
        
        # Preview mode
        preview_mode = QAction("Preview", self)
        preview_mode.setCheckable(True)
        preview_mode.setIcon(self._create_mode_icon("preview"))
        preview_mode.setShortcut(QKeySequence("V"))
        preview_mode.setToolTip("Preview Mode (V)")
        preview_mode.triggered.connect(lambda: self._set_drawing_mode(DrawingMode.PREVIEW))
        
        for action in [select_mode, draw_mode, preview_mode]:
            mode_group.addAction(action)
        
        self._action_groups["mode_controls"] = mode_group
        self._tool_actions.update({
            "select_mode": select_mode,
            "draw_mode": draw_mode,
            "preview_mode": preview_mode
        })
    
    def _create_validation_actions(self):
        """Create validation control actions."""
        # Start validation
        start_action = QAction("Start", self)
        start_action.setIcon(self._create_validation_icon("start"))
        start_action.setShortcut(QKeySequence("Ctrl+S"))
        start_action.setToolTip("Start Validation (Ctrl+S)")
        start_action.triggered.connect(self._start_validation)
        
        # Stop validation
        stop_action = QAction("Stop", self)
        stop_action.setIcon(self._create_validation_icon("stop"))
        stop_action.setShortcut(QKeySequence("Ctrl+T"))
        stop_action.setToolTip("Stop Validation (Ctrl+T)")
        stop_action.triggered.connect(self._stop_validation)
        stop_action.setEnabled(False)
        
        # Reset validation
        reset_action = QAction("Reset", self)
        reset_action.setIcon(self._create_validation_icon("reset"))
        reset_action.setShortcut(QKeySequence("Ctrl+R"))
        reset_action.setToolTip("Reset Validation (Ctrl+R)")
        reset_action.triggered.connect(self._reset_validation)
        
        # Accept area
        accept_action = QAction("Accept", self)
        accept_action.setIcon(self._create_validation_icon("accept"))
        accept_action.setShortcut(QKeySequence("Return"))
        accept_action.setToolTip("Accept Current Area (Enter)")
        accept_action.triggered.connect(self._accept_area)
        accept_action.setEnabled(False)
        
        # Reject area
        reject_action = QAction("Reject", self)
        reject_action.setIcon(self._create_validation_icon("reject"))
        reject_action.setShortcut(QKeySequence("Escape"))
        reject_action.setToolTip("Reject Current Area (Escape)")
        reject_action.triggered.connect(self._reject_area)
        reject_action.setEnabled(False)
        
        self._tool_actions.update({
            "start_validation": start_action,
            "stop_validation": stop_action,
            "reset_validation": reset_action,
            "accept_area": accept_action,
            "reject_area": reject_action
        })
    
    def _create_view_controls(self):
        """Create view control actions."""
        # Zoom controls
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setIcon(self._create_view_icon("zoom_in"))
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.setToolTip("Zoom In (Ctrl++)")
        zoom_in_action.triggered.connect(lambda: self.zoom_requested.emit(1.2))
        
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setIcon(self._create_view_icon("zoom_out"))
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.setToolTip("Zoom Out (Ctrl+-)")
        zoom_out_action.triggered.connect(lambda: self.zoom_requested.emit(0.8))
        
        zoom_fit_action = QAction("Fit", self)
        zoom_fit_action.setIcon(self._create_view_icon("zoom_fit"))
        zoom_fit_action.setShortcut(QKeySequence("Ctrl+0"))
        zoom_fit_action.setToolTip("Zoom to Fit (Ctrl+0)")
        zoom_fit_action.triggered.connect(lambda: self.zoom_requested.emit(0.0))  # 0.0 = fit
        
        self._tool_actions.update({
            "zoom_in": zoom_in_action,
            "zoom_out": zoom_out_action,
            "zoom_fit": zoom_fit_action
        })
    
    def _create_quick_actions(self):
        """Create quick action buttons."""
        # OCR trigger
        ocr_action = QAction("OCR", self)
        ocr_action.setIcon(self._create_action_icon("ocr"))
        ocr_action.setShortcut(QKeySequence("Ctrl+O"))
        ocr_action.setToolTip("Run OCR on Selection (Ctrl+O)")
        ocr_action.triggered.connect(self._trigger_ocr)
        ocr_action.setEnabled(False)
        
        # Undo action
        undo_action = QAction("Undo", self)
        undo_action.setIcon(self._create_action_icon("undo"))
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.setToolTip("Undo Last Action (Ctrl+Z)")
        undo_action.triggered.connect(self._undo_action)
        undo_action.setEnabled(False)
        
        # Redo action
        redo_action = QAction("Redo", self)
        redo_action.setIcon(self._create_action_icon("redo"))
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.setToolTip("Redo Last Action (Ctrl+Y)")
        redo_action.triggered.connect(self._redo_action)
        redo_action.setEnabled(False)
        
        self._tool_actions.update({
            "trigger_ocr": ocr_action,
            "undo": undo_action,
            "redo": redo_action
        })
    
    def _create_widgets(self):
        """Create custom toolbar widgets."""
        # Element type selector
        self._create_element_type_selector()
        
        # Zoom level display
        self._create_zoom_display()
        
        # Status indicator
        self._create_status_indicator()
        
        # Performance meter
        if self.config.mode in [ToolbarMode.ADVANCED, ToolbarMode.EXPERT]:
            self._create_performance_meter()
    
    def _create_element_type_selector(self):
        """Create element type selection widget."""
        element_combo = QComboBox()
        element_combo.setToolTip("Select Element Type")
        element_combo.setMinimumWidth(120)
        
        # Add element types
        for element_type in ElementType:
            element_combo.addItem(element_type.value.title(), element_type)
        
        element_combo.currentIndexChanged.connect(self._on_element_type_changed)
        
        # Create widget action
        element_widget = QWidget()
        element_layout = QHBoxLayout(element_widget)
        element_layout.setContentsMargins(4, 2, 4, 2)
        element_layout.addWidget(QLabel("Type:"))
        element_layout.addWidget(element_combo)
        
        element_action = QWidgetAction(self)
        element_action.setDefaultWidget(element_widget)
        
        self._custom_widgets["element_selector"] = {
            "action": element_action,
            "combo": element_combo,
            "widget": element_widget
        }
    
    def _create_zoom_display(self):
        """Create zoom level display widget."""
        zoom_widget = QWidget()
        zoom_layout = QHBoxLayout(zoom_widget)
        zoom_layout.setContentsMargins(4, 2, 4, 2)
        
        zoom_label = QLabel("Zoom:")
        zoom_level = QLabel("100%")
        zoom_level.setMinimumWidth(50)
        zoom_level.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zoom_level.setStyleSheet("""
            QLabel {
                background: #e9ecef;
                border: 1px solid #adb5bd;
                border-radius: 3px;
                padding: 2px 4px;
                font-family: monospace;
            }
        """)
        
        zoom_layout.addWidget(zoom_label)
        zoom_layout.addWidget(zoom_level)
        
        zoom_action = QWidgetAction(self)
        zoom_action.setDefaultWidget(zoom_widget)
        
        self._custom_widgets["zoom_display"] = {
            "action": zoom_action,
            "label": zoom_level,
            "widget": zoom_widget
        }
    
    def _create_status_indicator(self):
        """Create validation status indicator."""
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(4, 2, 4, 2)
        
        status_label = QLabel("Ready")
        status_label.setMinimumWidth(80)
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setStyleSheet("""
            QLabel {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
                border-radius: 3px;
                padding: 2px 8px;
                font-weight: 600;
            }
        """)
        
        status_layout.addWidget(status_label)
        
        status_action = QWidgetAction(self)
        status_action.setDefaultWidget(status_widget)
        
        self._custom_widgets["status_indicator"] = {
            "action": status_action,
            "label": status_label,
            "widget": status_widget
        }
    
    def _create_performance_meter(self):
        """Create performance monitoring widget."""
        from PyQt6.QtWidgets import QProgressBar
        
        perf_widget = QWidget()
        perf_layout = QHBoxLayout(perf_widget)
        perf_layout.setContentsMargins(4, 2, 4, 2)
        
        perf_label = QLabel("CPU:")
        perf_bar = QProgressBar()
        perf_bar.setRange(0, 100)
        perf_bar.setValue(25)
        perf_bar.setMaximumWidth(60)
        perf_bar.setMaximumHeight(16)
        perf_bar.setTextVisible(False)
        
        perf_layout.addWidget(perf_label)
        perf_layout.addWidget(perf_bar)
        
        perf_action = QWidgetAction(self)
        perf_action.setDefaultWidget(perf_widget)
        
        self._custom_widgets["performance_meter"] = {
            "action": perf_action,
            "bar": perf_bar,
            "widget": perf_widget
        }
    
    def _setup_layout(self):
        """Setup toolbar layout with sections."""
        # Drawing tools section
        for tool_name in ["rectangle", "polygon", "freehand"]:
            self.addAction(self._tool_actions[tool_name])
        
        self.addSeparator()
        
        # Mode controls section
        for mode_name in ["select_mode", "draw_mode", "preview_mode"]:
            self.addAction(self._tool_actions[mode_name])
        
        self.addSeparator()
        
        # Validation controls section
        validation_actions = ["start_validation", "stop_validation", "reset_validation"]
        for action_name in validation_actions:
            self.addAction(self._tool_actions[action_name])
        
        self.addSeparator()
        
        # Area controls section
        for action_name in ["accept_area", "reject_area"]:
            self.addAction(self._tool_actions[action_name])
        
        self.addSeparator()
        
        # Element type selector
        self.addAction(self._custom_widgets["element_selector"]["action"])
        
        self.addSeparator()
        
        # View controls section
        for action_name in ["zoom_in", "zoom_out", "zoom_fit"]:
            self.addAction(self._tool_actions[action_name])
        
        # Zoom display
        self.addAction(self._custom_widgets["zoom_display"]["action"])
        
        self.addSeparator()
        
        # Quick actions section
        for action_name in ["trigger_ocr", "undo", "redo"]:
            self.addAction(self._tool_actions[action_name])
        
        # Add flexible space
        from PyQt6.QtWidgets import QSizePolicy
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.addWidget(spacer)
        
        # Status and performance
        self.addAction(self._custom_widgets["status_indicator"]["action"])
        
        if "performance_meter" in self._custom_widgets:
            self.addAction(self._custom_widgets["performance_meter"]["action"])
    
    def _connect_signals(self):
        """Connect signals from state manager."""
        self.state_manager.mode_changed.connect(self._on_mode_changed)
        self.state_manager.state_changed.connect(self._on_state_changed)
        self.state_manager.area_selected.connect(self._on_area_selected)
        self.state_manager.error_occurred.connect(self._on_error_occurred)
    
    def _load_settings(self):
        """Load toolbar settings from preferences."""
        self.config.show_icons = self.settings.value("show_icons", True, bool)
        self.config.show_text = self.settings.value("show_text", True, bool)
        self.config.icon_size = self.settings.value("icon_size", 24, int)
        self.config.auto_hide = self.settings.value("auto_hide", False, bool)
        
        # Apply settings
        self.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon if self.config.show_text
            else Qt.ToolButtonStyle.ToolButtonIconOnly
        )
        
        self.setIconSize(QSize(self.config.icon_size, self.config.icon_size))
    
    def _save_settings(self):
        """Save toolbar settings to preferences."""
        self.settings.setValue("show_icons", self.config.show_icons)
        self.settings.setValue("show_text", self.config.show_text)
        self.settings.setValue("icon_size", self.config.icon_size)
        self.settings.setValue("auto_hide", self.config.auto_hide)
    
    # Signal handlers
    def _on_mode_changed(self, mode: DrawingMode):
        """Handle drawing mode changes."""
        # Update mode buttons
        mode_mapping = {
            DrawingMode.SELECTION: "select_mode",
            DrawingMode.DRAWING: "draw_mode",
            DrawingMode.PREVIEW: "preview_mode"
        }
        
        if mode in mode_mapping:
            action_name = mode_mapping[mode]
            if action_name in self._tool_actions:
                self._tool_actions[action_name].setChecked(True)
        
        # Update status
        self._update_status_for_mode(mode)
        
        self.logger.debug(f"Toolbar mode changed: {mode}")
    
    def _on_state_changed(self, state: DrawingState):
        """Handle drawing state changes."""
        # Update button states based on current state
        state_config = {
            DrawingState.IDLE: {
                "start_validation": True,
                "stop_validation": False,
                "accept_area": False,
                "reject_area": False,
                "trigger_ocr": False
            },
            DrawingState.AREA_SELECTING: {
                "start_validation": False,
                "stop_validation": True,
                "accept_area": False,
                "reject_area": True,
                "trigger_ocr": False
            },
            DrawingState.AREA_SELECTED: {
                "start_validation": False,
                "stop_validation": True,
                "accept_area": True,
                "reject_area": True,
                "trigger_ocr": True
            },
            DrawingState.OCR_PROCESSING: {
                "start_validation": False,
                "stop_validation": False,
                "accept_area": False,
                "reject_area": False,
                "trigger_ocr": False
            }
        }
        
        if state in state_config:
            for action_name, enabled in state_config[state].items():
                if action_name in self._tool_actions:
                    self._tool_actions[action_name].setEnabled(enabled)
        
        # Update status display
        self._update_status_for_state(state)
        
        self.logger.debug(f"Toolbar state changed: {state}")
    
    def _on_area_selected(self, area):
        """Handle area selection."""
        self._update_status("Area Selected", "success")
        self.logger.info(f"Area selected in toolbar: {area.area_id}")
    
    def _on_error_occurred(self, error_message: str):
        """Handle error states."""
        self._update_status("Error", "error")
        self.logger.error(f"Validation error: {error_message}")
    
    def _on_element_type_changed(self, index: int):
        """Handle element type selection change."""
        combo = self._custom_widgets["element_selector"]["combo"]
        element_type = combo.itemData(index)
        if element_type:
            self.element_type_selected.emit(element_type)
            self.logger.debug(f"Element type selected: {element_type}")
    
    # Action handlers
    def _select_tool(self, tool_name: str):
        """Handle tool selection."""
        self._current_tool = tool_name
        self.tool_selected.emit(tool_name)
        self.logger.debug(f"Tool selected: {tool_name}")
    
    def _set_drawing_mode(self, mode: DrawingMode):
        """Handle drawing mode change requests."""
        if mode == DrawingMode.SELECTION:
            self.state_manager.reset_to_selection()
        elif mode == DrawingMode.DRAWING:
            self.state_manager.start_drawing_mode()
        # Note: Preview mode would be handled by UI components
        
        self.mode_changed.emit(self.config.mode)
    
    def _start_validation(self):
        """Start validation process."""
        if self.state_manager.start_drawing_mode():
            self._update_status("Validation Started", "active")
            self.action_triggered.emit("start_validation", {})
    
    def _stop_validation(self):
        """Stop validation process."""
        if self.state_manager.stop_drawing_mode():
            self._update_status("Validation Stopped", "idle")
            self.action_triggered.emit("stop_validation", {})
    
    def _reset_validation(self):
        """Reset validation state."""
        if self.state_manager.reset_to_selection():
            self._update_status("Reset Complete", "idle")
            self.action_triggered.emit("reset_validation", {})
    
    def _accept_area(self):
        """Accept current area selection."""
        self._update_status("Area Accepted", "success")
        self.action_triggered.emit("accept_area", {})
    
    def _reject_area(self):
        """Reject current area selection."""
        if self.state_manager.reset_to_selection():
            self._update_status("Area Rejected", "idle")
            self.action_triggered.emit("reject_area", {})
    
    def _trigger_ocr(self):
        """Trigger OCR processing."""
        self._update_status("OCR Processing", "processing")
        self.action_triggered.emit("trigger_ocr", {})
    
    def _undo_action(self):
        """Handle undo action."""
        self.action_triggered.emit("undo", {})
    
    def _redo_action(self):
        """Handle redo action."""
        self.action_triggered.emit("redo", {})
    
    # Utility methods
    def _update_status(self, text: str, status_type: str = "idle"):
        """Update status indicator."""
        if "status_indicator" in self._custom_widgets:
            label = self._custom_widgets["status_indicator"]["label"]
            label.setText(text)
            
            # Update styling based on status type
            style_map = {
                "idle": "background: #d4edda; color: #155724; border-color: #c3e6cb;",
                "active": "background: #cce5ff; color: #004085; border-color: #80bdff;",
                "processing": "background: #fff3cd; color: #856404; border-color: #ffeaa7;",
                "success": "background: #d4edda; color: #155724; border-color: #c3e6cb;",
                "error": "background: #f8d7da; color: #721c24; border-color: #f5c6cb;"
            }
            
            base_style = """
                QLabel {
                    %s
                    border: 1px solid;
                    border-radius: 3px;
                    padding: 2px 8px;
                    font-weight: 600;
                }
            """ % style_map.get(status_type, style_map["idle"])
            
            label.setStyleSheet(base_style)
        
        # Schedule delayed update for performance
        self._update_timer.start(100)
    
    def _update_status_for_mode(self, mode: DrawingMode):
        """Update status display for drawing mode."""
        mode_status = {
            DrawingMode.DISABLED: ("Disabled", "idle"),
            DrawingMode.SELECTION: ("Selection Mode", "active"),
            DrawingMode.DRAWING: ("Drawing Mode", "active"),
            DrawingMode.PREVIEW: ("Preview Mode", "idle"),
            DrawingMode.CONFIRMING: ("Confirming", "processing")
        }
        
        if mode in mode_status:
            text, status_type = mode_status[mode]
            self._update_status(text, status_type)
    
    def _update_status_for_state(self, state: DrawingState):
        """Update status display for drawing state."""
        state_status = {
            DrawingState.IDLE: ("Ready", "idle"),
            DrawingState.AREA_SELECTING: ("Selecting Area", "active"),
            DrawingState.AREA_SELECTED: ("Area Selected", "success"),
            DrawingState.ELEMENT_CREATING: ("Creating Element", "processing"),
            DrawingState.ELEMENT_CREATED: ("Element Created", "success"),
            DrawingState.OCR_PROCESSING: ("OCR Processing", "processing"),
            DrawingState.OCR_COMPLETED: ("OCR Complete", "success"),
            DrawingState.ERROR: ("Error", "error")
        }
        
        if state in state_status:
            text, status_type = state_status[state]
            self._update_status(text, status_type)
    
    def _delayed_update(self):
        """Perform delayed UI updates for performance."""
        # Update performance meter if available
        if "performance_meter" in self._custom_widgets:
            try:
                import psutil
                cpu_usage = psutil.cpu_percent(interval=None)
                self._custom_widgets["performance_meter"]["bar"].setValue(int(cpu_usage))
            except ImportError:
                # psutil not available, use placeholder
                self._custom_widgets["performance_meter"]["bar"].setValue(25)
    
    def update_zoom_display(self, zoom_factor: float):
        """Update zoom level display."""
        if "zoom_display" in self._custom_widgets:
            zoom_text = f"{zoom_factor:.0%}" if zoom_factor > 0 else "Fit"
            self._custom_widgets["zoom_display"]["label"].setText(zoom_text)
    
    def set_toolbar_mode(self, mode: ToolbarMode):
        """Change toolbar display mode."""
        self.config.mode = mode
        
        # Show/hide advanced features based on mode
        advanced_widgets = ["performance_meter"]
        
        for widget_name in advanced_widgets:
            if widget_name in self._custom_widgets:
                visible = mode in [ToolbarMode.ADVANCED, ToolbarMode.EXPERT]
                self._custom_widgets[widget_name]["action"].setVisible(visible)
        
        self.mode_changed.emit(mode)
        self._save_settings()
    
    # Icon creation methods (simplified - would use actual icons in production)
    def _create_tool_icon(self, tool_name: str) -> QIcon:
        """Create icon for drawing tools."""
        # Simplified icon creation - would use actual SVG/PNG icons
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if tool_name == "rectangle":
            painter.setPen(QPen(QColor("#007bff"), 2))
            painter.drawRect(4, 4, 16, 16)
        elif tool_name == "polygon":
            painter.setPen(QPen(QColor("#28a745"), 2))
            from PyQt6.QtCore import QPoint
            points = [QPoint(12, 4), QPoint(20, 8), QPoint(16, 16), QPoint(8, 16), QPoint(4, 8)]
            painter.drawPolygon(points)
        elif tool_name == "freehand":
            painter.setPen(QPen(QColor("#dc3545"), 2))
            painter.drawEllipse(4, 4, 16, 16)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_mode_icon(self, mode_name: str) -> QIcon:
        """Create icon for mode controls."""
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#6c757d"), 2))
        
        if mode_name == "select":
            painter.drawRect(6, 6, 12, 12)
            painter.fillRect(8, 8, 8, 8, QBrush(QColor("#6c757d")))
        elif mode_name == "draw":
            painter.drawLine(4, 20, 20, 4)
            painter.drawEllipse(2, 18, 4, 4)
        elif mode_name == "preview":
            painter.drawEllipse(6, 6, 12, 12)
            painter.fillRect(11, 11, 2, 2, QBrush(QColor("#6c757d")))
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_validation_icon(self, action_name: str) -> QIcon:
        """Create icon for validation actions."""
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        from PyQt6.QtCore import QPoint
        
        if action_name == "start":
            painter.setBrush(QBrush(QColor("#28a745")))
            painter.drawPolygon([QPoint(8, 4), QPoint(20, 12), QPoint(8, 20)])
        elif action_name == "stop":
            painter.setBrush(QBrush(QColor("#dc3545")))
            painter.drawRect(6, 6, 12, 12)
        elif action_name == "reset":
            painter.setPen(QPen(QColor("#ffc107"), 2))
            painter.drawEllipse(4, 4, 16, 16)
            painter.drawLine(12, 8, 12, 16)
        elif action_name == "accept":
            painter.setPen(QPen(QColor("#28a745"), 3))
            painter.drawLine(6, 12, 10, 16)
            painter.drawLine(10, 16, 18, 8)
        elif action_name == "reject":
            painter.setPen(QPen(QColor("#dc3545"), 3))
            painter.drawLine(6, 6, 18, 18)
            painter.drawLine(18, 6, 6, 18)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_view_icon(self, view_name: str) -> QIcon:
        """Create icon for view controls."""
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#007bff"), 2))
        
        if view_name == "zoom_in":
            painter.drawEllipse(4, 4, 12, 12)
            painter.drawLine(10, 7, 10, 13)
            painter.drawLine(7, 10, 13, 10)
            painter.drawLine(14, 14, 20, 20)
        elif view_name == "zoom_out":
            painter.drawEllipse(4, 4, 12, 12)
            painter.drawLine(7, 10, 13, 10)
            painter.drawLine(14, 14, 20, 20)
        elif view_name == "zoom_fit":
            painter.drawRect(6, 6, 12, 12)
            painter.drawLine(4, 4, 8, 8)
            painter.drawLine(20, 20, 16, 16)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_action_icon(self, action_name: str) -> QIcon:
        """Create icon for quick actions."""
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#6c757d"), 2))
        
        if action_name == "ocr":
            painter.drawRect(6, 4, 12, 16)
            painter.drawLine(8, 8, 16, 8)
            painter.drawLine(8, 12, 14, 12)
            painter.drawLine(8, 16, 16, 16)
        elif action_name == "undo":
            painter.drawArc(4, 4, 16, 16, 90 * 16, 180 * 16)
            painter.drawLine(6, 8, 10, 4)
            painter.drawLine(6, 8, 10, 12)
        elif action_name == "redo":
            painter.drawArc(4, 4, 16, 16, 90 * 16, -180 * 16)
            painter.drawLine(18, 8, 14, 4)
            painter.drawLine(18, 8, 14, 12)
        
        painter.end()
        return QIcon(pixmap)
    
    def closeEvent(self, event):
        """Handle toolbar close event."""
        self._save_settings()
        super().closeEvent(event)