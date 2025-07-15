"""
Zoom Preset System for Document Viewer

Provides predefined zoom levels and quick access controls for common
viewing modes like fit to width, fit to height, actual size, and custom levels.
"""

from typing import Dict, List, Optional, Tuple, Any, Callable
from enum import Enum
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal, QSizeF, QRectF, QPointF
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QComboBox, QLabel, QFrame, QSlider, QSpinBox, QToolButton,
                            QButtonGroup, QMenu, QAction)
from PyQt6.QtGui import QIcon, QFont
import math


class ZoomPresetType(Enum):
    """Types of zoom presets"""
    FIT_TO_WIDTH = "fit_to_width"
    FIT_TO_HEIGHT = "fit_to_height"
    FIT_TO_PAGE = "fit_to_page"
    ACTUAL_SIZE = "actual_size"
    CUSTOM = "custom"


@dataclass
class ZoomPreset:
    """Zoom preset configuration"""
    name: str
    preset_type: ZoomPresetType
    zoom_factor: float = 1.0
    description: str = ""
    keyboard_shortcut: str = ""
    icon: Optional[str] = None
    
    def __post_init__(self):
        if not self.description:
            self.description = self.name


class ZoomPresetManager(QObject):
    """Manages zoom presets and calculations"""
    
    # Preset signals
    preset_applied = pyqtSignal(ZoomPreset, float)  # preset, calculated_zoom
    preset_changed = pyqtSignal(str)  # preset_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Preset storage
        self._presets: Dict[str, ZoomPreset] = {}
        self._custom_presets: List[float] = []
        self._current_preset: Optional[str] = None
        
        # Document and viewport info
        self._document_size = QSizeF(0, 0)
        self._viewport_size = QSizeF(0, 0)
        self._current_zoom = 1.0
        
        # Configuration
        self._zoom_limits = (0.1, 10.0)  # 10% to 1000%
        
        self._setup_default_presets()
    
    def _setup_default_presets(self) -> None:
        """Setup default zoom presets"""
        default_presets = [
            ZoomPreset(
                name="Fit to Width",
                preset_type=ZoomPresetType.FIT_TO_WIDTH,
                description="Fit document width to viewport",
                keyboard_shortcut="Ctrl+1",
                icon="arrows-expand-horizontal"
            ),
            ZoomPreset(
                name="Fit to Height", 
                preset_type=ZoomPresetType.FIT_TO_HEIGHT,
                description="Fit document height to viewport",
                keyboard_shortcut="Ctrl+2",
                icon="arrows-expand-vertical"
            ),
            ZoomPreset(
                name="Fit to Page",
                preset_type=ZoomPresetType.FIT_TO_PAGE,
                description="Fit entire page to viewport",
                keyboard_shortcut="Ctrl+0",
                icon="arrows-expand"
            ),
            ZoomPreset(
                name="Actual Size",
                preset_type=ZoomPresetType.ACTUAL_SIZE,
                zoom_factor=1.0,
                description="100% actual document size",
                keyboard_shortcut="Ctrl+Alt+0",
                icon="magnifying-glass"
            ),
            # Common zoom levels
            ZoomPreset(
                name="25%",
                preset_type=ZoomPresetType.CUSTOM,
                zoom_factor=0.25,
                description="25% zoom level"
            ),
            ZoomPreset(
                name="50%",
                preset_type=ZoomPresetType.CUSTOM,
                zoom_factor=0.5,
                description="50% zoom level"
            ),
            ZoomPreset(
                name="75%",
                preset_type=ZoomPresetType.CUSTOM,
                zoom_factor=0.75,
                description="75% zoom level"
            ),
            ZoomPreset(
                name="100%",
                preset_type=ZoomPresetType.CUSTOM,
                zoom_factor=1.0,
                description="100% zoom level"
            ),
            ZoomPreset(
                name="125%",
                preset_type=ZoomPresetType.CUSTOM,
                zoom_factor=1.25,
                description="125% zoom level"
            ),
            ZoomPreset(
                name="150%",
                preset_type=ZoomPresetType.CUSTOM,
                zoom_factor=1.5,
                description="150% zoom level"
            ),
            ZoomPreset(
                name="200%",
                preset_type=ZoomPresetType.CUSTOM,
                zoom_factor=2.0,
                description="200% zoom level"
            ),
            ZoomPreset(
                name="400%",
                preset_type=ZoomPresetType.CUSTOM,
                zoom_factor=4.0,
                description="400% zoom level"
            )
        ]
        
        for preset in default_presets:
            self.add_preset(preset)
    
    def add_preset(self, preset: ZoomPreset) -> None:
        """Add a zoom preset"""
        self._presets[preset.name] = preset
    
    def remove_preset(self, name: str) -> bool:
        """Remove a zoom preset"""
        if name in self._presets:
            del self._presets[name]
            return True
        return False
    
    def get_preset(self, name: str) -> Optional[ZoomPreset]:
        """Get a zoom preset by name"""
        return self._presets.get(name)
    
    def get_all_presets(self) -> List[ZoomPreset]:
        """Get all available presets"""
        return list(self._presets.values())
    
    def get_presets_by_type(self, preset_type: ZoomPresetType) -> List[ZoomPreset]:
        """Get presets of specific type"""
        return [p for p in self._presets.values() if p.preset_type == preset_type]
    
    def set_document_size(self, size: QSizeF) -> None:
        """Set document size for fit calculations"""
        self._document_size = size
    
    def set_viewport_size(self, size: QSizeF) -> None:
        """Set viewport size for fit calculations"""
        self._viewport_size = size
    
    def set_current_zoom(self, zoom: float) -> None:
        """Set current zoom level"""
        self._current_zoom = zoom
    
    def apply_preset(self, preset_name: str) -> bool:
        """Apply a zoom preset"""
        preset = self._presets.get(preset_name)
        if not preset:
            return False
        
        # Calculate actual zoom factor based on preset type
        zoom_factor = self._calculate_zoom_factor(preset)
        
        if zoom_factor is None:
            return False
        
        # Apply zoom limits
        zoom_factor = max(self._zoom_limits[0], min(self._zoom_limits[1], zoom_factor))
        
        self._current_preset = preset_name
        self.preset_applied.emit(preset, zoom_factor)
        self.preset_changed.emit(preset_name)
        
        return True
    
    def _calculate_zoom_factor(self, preset: ZoomPreset) -> Optional[float]:
        """Calculate zoom factor for preset"""
        if preset.preset_type == ZoomPresetType.ACTUAL_SIZE:
            return 1.0
        
        elif preset.preset_type == ZoomPresetType.CUSTOM:
            return preset.zoom_factor
        
        elif preset.preset_type == ZoomPresetType.FIT_TO_WIDTH:
            if self._document_size.width() > 0 and self._viewport_size.width() > 0:
                return self._viewport_size.width() / self._document_size.width()
        
        elif preset.preset_type == ZoomPresetType.FIT_TO_HEIGHT:
            if self._document_size.height() > 0 and self._viewport_size.height() > 0:
                return self._viewport_size.height() / self._document_size.height()
        
        elif preset.preset_type == ZoomPresetType.FIT_TO_PAGE:
            if (self._document_size.width() > 0 and self._document_size.height() > 0 and
                self._viewport_size.width() > 0 and self._viewport_size.height() > 0):
                
                width_scale = self._viewport_size.width() / self._document_size.width()
                height_scale = self._viewport_size.height() / self._document_size.height()
                return min(width_scale, height_scale)
        
        return None
    
    def get_current_preset(self) -> Optional[str]:
        """Get current active preset name"""
        return self._current_preset
    
    def find_closest_preset(self, zoom_factor: float) -> Optional[str]:
        """Find the preset closest to given zoom factor"""
        closest_preset = None
        closest_distance = float('inf')
        
        for name, preset in self._presets.items():
            if preset.preset_type == ZoomPresetType.CUSTOM:
                distance = abs(preset.zoom_factor - zoom_factor)
                if distance < closest_distance:
                    closest_distance = distance
                    closest_preset = name
        
        # Consider close enough if within 5%
        if closest_distance < 0.05:
            return closest_preset
        
        return None
    
    def create_custom_preset(self, name: str, zoom_factor: float) -> bool:
        """Create a custom zoom preset"""
        if name in self._presets:
            return False
        
        preset = ZoomPreset(
            name=name,
            preset_type=ZoomPresetType.CUSTOM,
            zoom_factor=zoom_factor,
            description=f"Custom zoom level: {zoom_factor:.0%}"
        )
        
        self.add_preset(preset)
        return True
    
    def set_zoom_limits(self, min_zoom: float, max_zoom: float) -> None:
        """Set zoom limits"""
        self._zoom_limits = (min_zoom, max_zoom)


class ZoomPresetWidget(QWidget):
    """Widget for zoom preset selection and control"""
    
    # Preset signals
    preset_selected = pyqtSignal(str)  # preset_name
    zoom_changed = pyqtSignal(float)   # zoom_factor
    
    def __init__(self, preset_manager: ZoomPresetManager, parent=None):
        super().__init__(parent)
        
        self._preset_manager = preset_manager
        self._updating_ui = False
        
        # Connect to preset manager
        preset_manager.preset_applied.connect(self._on_preset_applied)
        preset_manager.preset_changed.connect(self._on_preset_changed)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup preset widget UI"""
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(4, 4, 4, 4)
        self.layout().setSpacing(4)
        
        # Title
        title_label = QLabel("Zoom Presets")
        title_label.setFont(QFont("", 9, QFont.Weight.Bold))
        self.layout().addWidget(title_label)
        
        # Quick access buttons
        self._create_quick_buttons()
        
        # Preset selector
        self._create_preset_selector()
        
        # Custom zoom control
        self._create_custom_zoom_control()
    
    def _create_quick_buttons(self) -> None:
        """Create quick access buttons for common presets"""
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(2)
        
        # Fit buttons
        self._fit_width_btn = QPushButton("Fit W")
        self._fit_width_btn.setFixedSize(50, 24)
        self._fit_width_btn.setToolTip("Fit to Width (Ctrl+1)")
        self._fit_width_btn.clicked.connect(lambda: self._apply_preset("Fit to Width"))
        button_layout.addWidget(self._fit_width_btn)
        
        self._fit_height_btn = QPushButton("Fit H") 
        self._fit_height_btn.setFixedSize(50, 24)
        self._fit_height_btn.setToolTip("Fit to Height (Ctrl+2)")
        self._fit_height_btn.clicked.connect(lambda: self._apply_preset("Fit to Height"))
        button_layout.addWidget(self._fit_height_btn)
        
        self._fit_page_btn = QPushButton("Fit P")
        self._fit_page_btn.setFixedSize(50, 24)
        self._fit_page_btn.setToolTip("Fit to Page (Ctrl+0)")
        self._fit_page_btn.clicked.connect(lambda: self._apply_preset("Fit to Page"))
        button_layout.addWidget(self._fit_page_btn)
        
        self._actual_size_btn = QPushButton("100%")
        self._actual_size_btn.setFixedSize(50, 24)
        self._actual_size_btn.setToolTip("Actual Size (Ctrl+Alt+0)")
        self._actual_size_btn.clicked.connect(lambda: self._apply_preset("Actual Size"))
        button_layout.addWidget(self._actual_size_btn)
        
        self.layout().addWidget(button_frame)
    
    def _create_preset_selector(self) -> None:
        """Create preset selector dropdown"""
        selector_frame = QFrame()
        selector_layout = QHBoxLayout(selector_frame)
        selector_layout.setContentsMargins(0, 0, 0, 0)
        
        selector_layout.addWidget(QLabel("Preset:"))
        
        self._preset_combo = QComboBox()
        self._preset_combo.setMinimumWidth(100)
        self._update_preset_list()
        self._preset_combo.currentTextChanged.connect(self._on_preset_combo_changed)
        selector_layout.addWidget(self._preset_combo)
        
        self.layout().addWidget(selector_frame)
    
    def _create_custom_zoom_control(self) -> None:
        """Create custom zoom level control"""
        zoom_frame = QFrame()
        zoom_layout = QVBoxLayout(zoom_frame)
        zoom_layout.setContentsMargins(0, 0, 0, 0)
        zoom_layout.setSpacing(2)
        
        # Zoom slider
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Zoom:"))
        
        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setMinimum(10)  # 10%
        self._zoom_slider.setMaximum(1000)  # 1000%
        self._zoom_slider.setValue(100)  # 100%
        self._zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        slider_layout.addWidget(self._zoom_slider)
        
        self._zoom_label = QLabel("100%")
        self._zoom_label.setFixedWidth(40)
        slider_layout.addWidget(self._zoom_label)
        
        zoom_layout.addLayout(slider_layout)
        
        # Zoom input
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Custom:"))
        
        self._zoom_spinbox = QSpinBox()
        self._zoom_spinbox.setMinimum(10)
        self._zoom_spinbox.setMaximum(1000)
        self._zoom_spinbox.setValue(100)
        self._zoom_spinbox.setSuffix("%")
        self._zoom_spinbox.valueChanged.connect(self._on_zoom_spinbox_changed)
        input_layout.addWidget(self._zoom_spinbox)
        
        # Apply button
        apply_btn = QPushButton("Apply")
        apply_btn.setFixedSize(50, 24)
        apply_btn.clicked.connect(self._apply_custom_zoom)
        input_layout.addWidget(apply_btn)
        
        input_layout.addStretch()
        zoom_layout.addLayout(input_layout)
        
        self.layout().addWidget(zoom_frame)
    
    def _update_preset_list(self) -> None:
        """Update the preset selector list"""
        self._updating_ui = True
        
        current_text = self._preset_combo.currentText()
        self._preset_combo.clear()
        
        # Add presets grouped by type
        fit_presets = self._preset_manager.get_presets_by_type(ZoomPresetType.FIT_TO_WIDTH)
        fit_presets.extend(self._preset_manager.get_presets_by_type(ZoomPresetType.FIT_TO_HEIGHT))
        fit_presets.extend(self._preset_manager.get_presets_by_type(ZoomPresetType.FIT_TO_PAGE))
        fit_presets.extend(self._preset_manager.get_presets_by_type(ZoomPresetType.ACTUAL_SIZE))
        
        if fit_presets:
            self._preset_combo.addItem("--- Fit Presets ---")
            for preset in fit_presets:
                self._preset_combo.addItem(preset.name)
        
        custom_presets = self._preset_manager.get_presets_by_type(ZoomPresetType.CUSTOM)
        if custom_presets:
            self._preset_combo.addItem("--- Zoom Levels ---")
            # Sort custom presets by zoom factor
            custom_presets.sort(key=lambda p: p.zoom_factor)
            for preset in custom_presets:
                self._preset_combo.addItem(preset.name)
        
        # Restore selection
        if current_text:
            index = self._preset_combo.findText(current_text)
            if index >= 0:
                self._preset_combo.setCurrentIndex(index)
        
        self._updating_ui = False
    
    def _apply_preset(self, preset_name: str) -> None:
        """Apply a preset by name"""
        if self._preset_manager.apply_preset(preset_name):
            self.preset_selected.emit(preset_name)
    
    def _apply_custom_zoom(self) -> None:
        """Apply custom zoom level"""
        zoom_percent = self._zoom_spinbox.value()
        zoom_factor = zoom_percent / 100.0
        self.zoom_changed.emit(zoom_factor)
    
    def _on_preset_combo_changed(self, preset_name: str) -> None:
        """Handle preset selector change"""
        if self._updating_ui or not preset_name or preset_name.startswith("---"):
            return
        
        self._apply_preset(preset_name)
    
    def _on_zoom_slider_changed(self, value: int) -> None:
        """Handle zoom slider change"""
        if self._updating_ui:
            return
        
        zoom_factor = value / 100.0
        self._zoom_label.setText(f"{value}%")
        
        # Update spinbox
        self._updating_ui = True
        self._zoom_spinbox.setValue(value)
        self._updating_ui = False
    
    def _on_zoom_spinbox_changed(self, value: int) -> None:
        """Handle zoom spinbox change"""
        if self._updating_ui:
            return
        
        # Update slider
        self._updating_ui = True
        self._zoom_slider.setValue(value)
        self._zoom_label.setText(f"{value}%")
        self._updating_ui = False
    
    def _on_preset_applied(self, preset: ZoomPreset, zoom_factor: float) -> None:
        """Handle preset application"""
        self._updating_ui = True
        
        # Update UI to reflect applied preset
        zoom_percent = int(zoom_factor * 100)
        self._zoom_slider.setValue(zoom_percent)
        self._zoom_spinbox.setValue(zoom_percent)
        self._zoom_label.setText(f"{zoom_percent}%")
        
        # Update preset selector
        index = self._preset_combo.findText(preset.name)
        if index >= 0:
            self._preset_combo.setCurrentIndex(index)
        
        self._updating_ui = False
    
    def _on_preset_changed(self, preset_name: str) -> None:
        """Handle preset change notification"""
        pass  # UI already updated in _on_preset_applied
    
    def update_zoom_level(self, zoom_factor: float) -> None:
        """Update UI to reflect external zoom change"""
        if self._updating_ui:
            return
        
        self._updating_ui = True
        
        zoom_percent = int(zoom_factor * 100)
        self._zoom_slider.setValue(zoom_percent)
        self._zoom_spinbox.setValue(zoom_percent)
        self._zoom_label.setText(f"{zoom_percent}%")
        
        # Check if zoom matches a preset
        closest_preset = self._preset_manager.find_closest_preset(zoom_factor)
        if closest_preset:
            index = self._preset_combo.findText(closest_preset)
            if index >= 0:
                self._preset_combo.setCurrentIndex(index)
        
        self._updating_ui = False


class ZoomToolbar(QWidget):
    """Compact zoom toolbar with essential controls"""
    
    # Toolbar signals
    zoom_in_requested = pyqtSignal()
    zoom_out_requested = pyqtSignal()
    preset_selected = pyqtSignal(str)
    zoom_changed = pyqtSignal(float)
    
    def __init__(self, preset_manager: ZoomPresetManager, parent=None):
        super().__init__(parent)
        
        self._preset_manager = preset_manager
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup zoom toolbar UI"""
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(2, 2, 2, 2)
        self.layout().setSpacing(2)
        
        # Zoom out button
        self._zoom_out_btn = QToolButton()
        self._zoom_out_btn.setText("−")
        self._zoom_out_btn.setFixedSize(24, 24)
        self._zoom_out_btn.setToolTip("Zoom Out")
        self._zoom_out_btn.clicked.connect(self.zoom_out_requested)
        self.layout().addWidget(self._zoom_out_btn)
        
        # Zoom level display/selector
        self._zoom_combo = QComboBox()
        self._zoom_combo.setEditable(True)
        self._zoom_combo.setFixedWidth(80)
        self._populate_zoom_combo()
        self._zoom_combo.currentTextChanged.connect(self._on_zoom_combo_changed)
        self.layout().addWidget(self._zoom_combo)
        
        # Zoom in button  
        self._zoom_in_btn = QToolButton()
        self._zoom_in_btn.setText("+")
        self._zoom_in_btn.setFixedSize(24, 24)
        self._zoom_in_btn.setToolTip("Zoom In")
        self._zoom_in_btn.clicked.connect(self.zoom_in_requested)
        self.layout().addWidget(self._zoom_in_btn)
        
        # Preset buttons dropdown
        self._preset_btn = QToolButton()
        self._preset_btn.setText("⋯")
        self._preset_btn.setFixedSize(24, 24)
        self._preset_btn.setToolTip("Zoom Presets")
        self._preset_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._create_preset_menu()
        self.layout().addWidget(self._preset_btn)
        
        self.layout().addStretch()
    
    def _populate_zoom_combo(self) -> None:
        """Populate zoom combo with common levels"""
        zoom_levels = ["25%", "50%", "75%", "100%", "125%", "150%", "200%", "400%"]
        self._zoom_combo.addItems(zoom_levels)
        self._zoom_combo.setCurrentText("100%")
    
    def _create_preset_menu(self) -> None:
        """Create preset menu for toolbar button"""
        menu = QMenu(self)
        
        # Fit presets
        fit_group = menu.addMenu("Fit Presets")
        fit_group.addAction("Fit to Width", lambda: self.preset_selected.emit("Fit to Width"))
        fit_group.addAction("Fit to Height", lambda: self.preset_selected.emit("Fit to Height"))
        fit_group.addAction("Fit to Page", lambda: self.preset_selected.emit("Fit to Page"))
        fit_group.addAction("Actual Size", lambda: self.preset_selected.emit("Actual Size"))
        
        menu.addSeparator()
        
        # Common zoom levels
        zoom_group = menu.addMenu("Zoom Levels")
        for preset in self._preset_manager.get_presets_by_type(ZoomPresetType.CUSTOM):
            zoom_group.addAction(preset.name, lambda p=preset.name: self.preset_selected.emit(p))
        
        self._preset_btn.setMenu(menu)
    
    def _on_zoom_combo_changed(self, text: str) -> None:
        """Handle zoom combo change"""
        try:
            # Extract percentage value
            if text.endswith('%'):
                zoom_percent = float(text[:-1])
            else:
                zoom_percent = float(text)
            
            zoom_factor = zoom_percent / 100.0
            self.zoom_changed.emit(zoom_factor)
        
        except ValueError:
            pass  # Invalid input, ignore
    
    def update_zoom_level(self, zoom_factor: float) -> None:
        """Update toolbar to reflect zoom level"""
        zoom_percent = int(zoom_factor * 100)
        self._zoom_combo.setCurrentText(f"{zoom_percent}%")