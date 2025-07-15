"""Property Panel Theming and UI Polish System

Provides comprehensive theming, styling, and visual polish for the property panel
with support for multiple themes, animations, and visual enhancements.
"""

from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass
from PyQt6.QtWidgets import (
    QWidget, QApplication, QLabel, QFrame, QVBoxLayout, QHBoxLayout,
    QStyleOption, QStyle, QGraphicsDropShadowEffect, QGraphicsBlurEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QPropertyAnimation, QEasingCurve, QTimer, QRect
from PyQt6.QtGui import (
    QColor, QPalette, QFont, QFontMetrics, QPainter, QPen, QBrush,
    QLinearGradient, QRadialGradient, QPixmap, QIcon
)


class ThemeType(Enum):
    """Available theme types"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"
    HIGH_CONTRAST = "high_contrast"
    CUSTOM = "custom"


class AnimationType(Enum):
    """Animation types for UI elements"""
    FADE = "fade"
    SLIDE = "slide"
    SCALE = "scale"
    BOUNCE = "bounce"
    GLOW = "glow"


@dataclass
class ThemeConfiguration:
    """Theme configuration settings"""
    name: str
    theme_type: ThemeType
    primary_color: QColor
    secondary_color: QColor
    background_color: QColor
    surface_color: QColor
    text_color: QColor
    accent_color: QColor
    border_color: QColor
    hover_color: QColor
    selection_color: QColor
    error_color: QColor
    warning_color: QColor
    success_color: QColor
    
    # Typography
    font_family: str = "Segoe UI"
    font_size: int = 10
    font_weight: int = 400
    line_height: float = 1.4
    
    # Spacing and sizing
    border_radius: int = 4
    border_width: int = 1
    padding: int = 8
    margin: int = 4
    
    # Effects
    shadow_enabled: bool = True
    shadow_color: QColor = None
    shadow_blur: int = 10
    shadow_offset: int = 2
    
    # Animation settings
    animation_duration: int = 200
    animation_easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic
    
    def __post_init__(self):
        if self.shadow_color is None:
            self.shadow_color = QColor(0, 0, 0, 50)


class PropertyPanelThemeManager(QObject):
    """Manages theming and visual styling for the property panel"""
    
    # Signals
    theme_changed = pyqtSignal(str)  # theme_name
    animation_finished = pyqtSignal(str)  # animation_id
    style_applied = pyqtSignal(QWidget)  # widget
    
    def __init__(self, property_panel: QWidget):
        super().__init__()
        self.property_panel = property_panel
        self.current_theme = "light"
        self.themes: Dict[str, ThemeConfiguration] = {}
        self.animations: Dict[str, QPropertyAnimation] = {}
        self.styled_widgets: List[QWidget] = []
        
        # Animation settings
        self.animation_enabled = True
        self.global_animation_duration = 200
        
        # Setup default themes
        self._setup_default_themes()
        self._apply_theme(self.current_theme)
        
        # Monitor system theme changes
        self._setup_system_monitoring()
    
    def _setup_default_themes(self) -> None:
        """Setup default theme configurations"""
        # Light theme
        light_theme = ThemeConfiguration(
            name="Light",
            theme_type=ThemeType.LIGHT,
            primary_color=QColor("#0078d4"),
            secondary_color=QColor("#005a9e"),
            background_color=QColor("#ffffff"),
            surface_color=QColor("#f3f2f1"),
            text_color=QColor("#323130"),
            accent_color=QColor("#0078d4"),
            border_color=QColor("#d2d0ce"),
            hover_color=QColor("#f3f2f1"),
            selection_color=QColor("#deecf9"),
            error_color=QColor("#d13438"),
            warning_color=QColor("#ff8c00"),
            success_color=QColor("#107c10"),
            font_family="Segoe UI",
            font_size=10,
            border_radius=4,
            shadow_enabled=True,
            shadow_color=QColor(0, 0, 0, 20)
        )
        self.themes["light"] = light_theme
        
        # Dark theme
        dark_theme = ThemeConfiguration(
            name="Dark",
            theme_type=ThemeType.DARK,
            primary_color=QColor("#0078d4"),
            secondary_color=QColor("#106ebe"),
            background_color=QColor("#1e1e1e"),
            surface_color=QColor("#2d2d30"),
            text_color=QColor("#cccccc"),
            accent_color=QColor("#0078d4"),
            border_color=QColor("#3e3e42"),
            hover_color=QColor("#2d2d30"),
            selection_color=QColor("#264f78"),
            error_color=QColor("#f48771"),
            warning_color=QColor("#ffaa44"),
            success_color=QColor("#89d185"),
            font_family="Segoe UI",
            font_size=10,
            border_radius=4,
            shadow_enabled=True,
            shadow_color=QColor(0, 0, 0, 100)
        )
        self.themes["dark"] = dark_theme
        
        # High contrast theme
        high_contrast_theme = ThemeConfiguration(
            name="High Contrast",
            theme_type=ThemeType.HIGH_CONTRAST,
            primary_color=QColor("#ffffff"),
            secondary_color=QColor("#c0c0c0"),
            background_color=QColor("#000000"),
            surface_color=QColor("#000000"),
            text_color=QColor("#ffffff"),
            accent_color=QColor("#ffff00"),
            border_color=QColor("#ffffff"),
            hover_color=QColor("#808080"),
            selection_color=QColor("#0000ff"),
            error_color=QColor("#ff0000"),
            warning_color=QColor("#ffff00"),
            success_color=QColor("#00ff00"),
            font_family="Segoe UI",
            font_size=12,
            font_weight=700,
            border_radius=0,
            border_width=2,
            shadow_enabled=False
        )
        self.themes["high_contrast"] = high_contrast_theme
    
    def _setup_system_monitoring(self) -> None:
        """Setup monitoring for system theme changes"""
        app = QApplication.instance()
        if app:
            # Monitor palette changes for automatic theme switching
            app.paletteChanged.connect(self._on_system_palette_changed)
    
    def apply_theme(self, theme_name: str) -> bool:
        """Apply a theme to the property panel"""
        if theme_name not in self.themes:
            return False
        
        if theme_name == self.current_theme:
            return True
        
        # Animate theme transition if enabled
        if self.animation_enabled:
            self._animate_theme_transition(theme_name)
        else:
            self._apply_theme(theme_name)
        
        return True
    
    def _apply_theme(self, theme_name: str) -> None:
        """Apply theme styling to property panel"""
        if theme_name not in self.themes:
            return
        
        theme = self.themes[theme_name]
        self.current_theme = theme_name
        
        # Generate and apply stylesheet
        stylesheet = self._generate_stylesheet(theme)
        self.property_panel.setStyleSheet(stylesheet)
        
        # Apply theme to child widgets
        self._apply_theme_to_widgets(theme)
        
        # Apply visual effects if enabled
        if theme.shadow_enabled:
            self._apply_shadow_effects(theme)
        
        # Update fonts
        self._apply_font_styling(theme)
        
        self.theme_changed.emit(theme_name)
        self.style_applied.emit(self.property_panel)
    
    def _generate_stylesheet(self, theme: ThemeConfiguration) -> str:
        """Generate CSS stylesheet from theme configuration"""
        return f"""
        /* Property Panel Base Styling */
        QWidget {{
            background-color: {theme.background_color.name()};
            color: {theme.text_color.name()};
            font-family: {theme.font_family};
            font-size: {theme.font_size}pt;
            font-weight: {theme.font_weight};
            border: none;
        }}
        
        /* Property Panel Container */
        #PropertyPanel {{
            background-color: {theme.background_color.name()};
            border: {theme.border_width}px solid {theme.border_color.name()};
            border-radius: {theme.border_radius}px;
        }}
        
        /* Property Groups */
        QGroupBox {{
            background-color: {theme.surface_color.name()};
            border: {theme.border_width}px solid {theme.border_color.name()};
            border-radius: {theme.border_radius}px;
            font-weight: bold;
            padding-top: 10px;
            margin-top: {theme.margin}px;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 {theme.padding}px;
            color: {theme.primary_color.name()};
        }}
        
        /* Property Editors */
        QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
            background-color: {theme.surface_color.name()};
            border: {theme.border_width}px solid {theme.border_color.name()};
            border-radius: {theme.border_radius}px;
            padding: {theme.padding}px;
            selection-background-color: {theme.selection_color.name()};
        }}
        
        QLineEdit:hover, QTextEdit:hover, QComboBox:hover {{
            border-color: {theme.primary_color.name()};
            background-color: {theme.hover_color.name()};
        }}
        
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
            border-color: {theme.accent_color.name()};
            border-width: 2px;
        }}
        
        /* Buttons */
        QPushButton {{
            background-color: {theme.primary_color.name()};
            color: white;
            border: none;
            border-radius: {theme.border_radius}px;
            padding: {theme.padding}px {theme.padding * 2}px;
            font-weight: bold;
        }}
        
        QPushButton:hover {{
            background-color: {theme.secondary_color.name()};
        }}
        
        QPushButton:pressed {{
            background-color: {theme.secondary_color.name()};
            transform: translateY(1px);
        }}
        
        QPushButton:disabled {{
            background-color: {theme.border_color.name()};
            color: {theme.text_color.name()};
        }}
        
        /* Labels */
        QLabel {{
            color: {theme.text_color.name()};
            background: transparent;
        }}
        
        QLabel.property-name {{
            font-weight: bold;
            color: {theme.primary_color.name()};
        }}
        
        QLabel.property-description {{
            font-style: italic;
            color: {theme.text_color.name()};
            opacity: 0.8;
        }}
        
        /* Checkboxes and Radio Buttons */
        QCheckBox, QRadioButton {{
            spacing: {theme.padding}px;
        }}
        
        QCheckBox::indicator, QRadioButton::indicator {{
            width: 16px;
            height: 16px;
        }}
        
        QCheckBox::indicator:unchecked {{
            border: {theme.border_width}px solid {theme.border_color.name()};
            background-color: {theme.surface_color.name()};
            border-radius: 2px;
        }}
        
        QCheckBox::indicator:checked {{
            border: {theme.border_width}px solid {theme.accent_color.name()};
            background-color: {theme.accent_color.name()};
            border-radius: 2px;
        }}
        
        /* Sliders */
        QSlider::groove:horizontal {{
            border: 1px solid {theme.border_color.name()};
            height: 4px;
            background: {theme.surface_color.name()};
            border-radius: 2px;
        }}
        
        QSlider::handle:horizontal {{
            background: {theme.primary_color.name()};
            border: 1px solid {theme.border_color.name()};
            width: 16px;
            margin: -6px 0;
            border-radius: 8px;
        }}
        
        QSlider::handle:horizontal:hover {{
            background: {theme.secondary_color.name()};
        }}
        
        /* Progress Bars */
        QProgressBar {{
            border: {theme.border_width}px solid {theme.border_color.name()};
            border-radius: {theme.border_radius}px;
            text-align: center;
            background-color: {theme.surface_color.name()};
        }}
        
        QProgressBar::chunk {{
            background-color: {theme.primary_color.name()};
            border-radius: {theme.border_radius}px;
        }}
        
        /* Tabs */
        QTabWidget::pane {{
            border: {theme.border_width}px solid {theme.border_color.name()};
            border-radius: {theme.border_radius}px;
            background-color: {theme.surface_color.name()};
        }}
        
        QTabBar::tab {{
            background-color: {theme.surface_color.name()};
            border: {theme.border_width}px solid {theme.border_color.name()};
            padding: {theme.padding}px {theme.padding * 2}px;
            margin-right: 2px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {theme.primary_color.name()};
            color: white;
        }}
        
        QTabBar::tab:hover {{
            background-color: {theme.hover_color.name()};
        }}
        
        /* Scrollbars */
        QScrollBar:vertical {{
            border: none;
            background: {theme.surface_color.name()};
            width: 12px;
            margin: 0;
        }}
        
        QScrollBar::handle:vertical {{
            background: {theme.border_color.name()};
            border-radius: 6px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background: {theme.primary_color.name()};
        }}
        
        /* Status and Error States */
        .error {{
            color: {theme.error_color.name()};
            border-color: {theme.error_color.name()};
        }}
        
        .warning {{
            color: {theme.warning_color.name()};
            border-color: {theme.warning_color.name()};
        }}
        
        .success {{
            color: {theme.success_color.name()};
            border-color: {theme.success_color.name()};
        }}
        
        /* Animations */
        * {{
            transition: all {theme.animation_duration}ms ease-out;
        }}
        """
    
    def _apply_theme_to_widgets(self, theme: ThemeConfiguration) -> None:
        """Apply theme styling to individual widgets"""
        for widget in self.styled_widgets:
            if widget and not widget.isNull():
                self._style_widget(widget, theme)
    
    def _style_widget(self, widget: QWidget, theme: ThemeConfiguration) -> None:
        """Apply theme styling to a specific widget"""
        # Apply palette
        palette = widget.palette()
        palette.setColor(QPalette.ColorRole.Window, theme.background_color)
        palette.setColor(QPalette.ColorRole.WindowText, theme.text_color)
        palette.setColor(QPalette.ColorRole.Base, theme.surface_color)
        palette.setColor(QPalette.ColorRole.AlternateBase, theme.hover_color)
        palette.setColor(QPalette.ColorRole.Text, theme.text_color)
        palette.setColor(QPalette.ColorRole.Button, theme.surface_color)
        palette.setColor(QPalette.ColorRole.ButtonText, theme.text_color)
        palette.setColor(QPalette.ColorRole.Highlight, theme.selection_color)
        palette.setColor(QPalette.ColorRole.HighlightedText, theme.text_color)
        widget.setPalette(palette)
        
        # Apply font
        font = QFont(theme.font_family, theme.font_size, theme.font_weight)
        widget.setFont(font)
    
    def _apply_shadow_effects(self, theme: ThemeConfiguration) -> None:
        """Apply shadow effects to property panel"""
        if not theme.shadow_enabled:
            return
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(theme.shadow_blur)
        shadow.setColor(theme.shadow_color)
        shadow.setOffset(theme.shadow_offset, theme.shadow_offset)
        
        self.property_panel.setGraphicsEffect(shadow)
    
    def _apply_font_styling(self, theme: ThemeConfiguration) -> None:
        """Apply font styling to property panel"""
        font = QFont(theme.font_family, theme.font_size, theme.font_weight)
        self.property_panel.setFont(font)
        
        # Update all child widgets
        for child in self.property_panel.findChildren(QWidget):
            child.setFont(font)
    
    def _animate_theme_transition(self, new_theme_name: str) -> None:
        """Animate transition between themes"""
        if not self.animation_enabled:
            self._apply_theme(new_theme_name)
            return
        
        # Create fade out animation
        fade_out = QPropertyAnimation(self.property_panel, b"windowOpacity")
        fade_out.setDuration(self.global_animation_duration // 2)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Apply theme when fade out completes
        def on_fade_out_finished():
            self._apply_theme(new_theme_name)
            fade_in.start()
        
        fade_out.finished.connect(on_fade_out_finished)
        
        # Create fade in animation
        fade_in = QPropertyAnimation(self.property_panel, b"windowOpacity")
        fade_in.setDuration(self.global_animation_duration // 2)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.InCubic)
        
        fade_in.finished.connect(lambda: self.animation_finished.emit("theme_transition"))
        
        # Store animations
        self.animations["fade_out"] = fade_out
        self.animations["fade_in"] = fade_in
        
        # Start transition
        fade_out.start()
    
    def register_widget(self, widget: QWidget) -> None:
        """Register a widget for theme application"""
        if widget not in self.styled_widgets:
            self.styled_widgets.append(widget)
            if self.current_theme in self.themes:
                self._style_widget(widget, self.themes[self.current_theme])
    
    def unregister_widget(self, widget: QWidget) -> None:
        """Unregister a widget from theme application"""
        if widget in self.styled_widgets:
            self.styled_widgets.remove(widget)
    
    def add_custom_theme(self, theme: ThemeConfiguration) -> None:
        """Add a custom theme configuration"""
        self.themes[theme.name.lower()] = theme
    
    def get_available_themes(self) -> List[str]:
        """Get list of available theme names"""
        return list(self.themes.keys())
    
    def get_current_theme(self) -> str:
        """Get current theme name"""
        return self.current_theme
    
    def get_theme_configuration(self, theme_name: str) -> Optional[ThemeConfiguration]:
        """Get theme configuration by name"""
        return self.themes.get(theme_name)
    
    def set_animation_enabled(self, enabled: bool) -> None:
        """Enable or disable animations"""
        self.animation_enabled = enabled
    
    def set_animation_duration(self, duration: int) -> None:
        """Set global animation duration"""
        self.global_animation_duration = duration
    
    def animate_widget(self, widget: QWidget, animation_type: AnimationType, 
                      duration: Optional[int] = None) -> str:
        """Animate a widget with specified animation type"""
        if not self.animation_enabled:
            return ""
        
        duration = duration or self.global_animation_duration
        animation_id = f"{id(widget)}_{animation_type.value}_{id(self)}"
        
        if animation_type == AnimationType.FADE:
            animation = self._create_fade_animation(widget, duration)
        elif animation_type == AnimationType.SLIDE:
            animation = self._create_slide_animation(widget, duration)
        elif animation_type == AnimationType.SCALE:
            animation = self._create_scale_animation(widget, duration)
        elif animation_type == AnimationType.BOUNCE:
            animation = self._create_bounce_animation(widget, duration)
        elif animation_type == AnimationType.GLOW:
            animation = self._create_glow_animation(widget, duration)
        else:
            return ""
        
        animation.finished.connect(lambda: self.animation_finished.emit(animation_id))
        self.animations[animation_id] = animation
        animation.start()
        
        return animation_id
    
    def _create_fade_animation(self, widget: QWidget, duration: int) -> QPropertyAnimation:
        """Create fade animation"""
        animation = QPropertyAnimation(widget, b"windowOpacity")
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        return animation
    
    def _create_slide_animation(self, widget: QWidget, duration: int) -> QPropertyAnimation:
        """Create slide animation"""
        animation = QPropertyAnimation(widget, b"pos")
        animation.setDuration(duration)
        start_pos = widget.pos()
        animation.setStartValue(start_pos)
        animation.setEndValue(start_pos)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        return animation
    
    def _create_scale_animation(self, widget: QWidget, duration: int) -> QPropertyAnimation:
        """Create scale animation"""
        animation = QPropertyAnimation(widget, b"size")
        animation.setDuration(duration)
        animation.setStartValue(widget.size())
        animation.setEndValue(widget.size())
        animation.setEasingCurve(QEasingCurve.Type.OutElastic)
        return animation
    
    def _create_bounce_animation(self, widget: QWidget, duration: int) -> QPropertyAnimation:
        """Create bounce animation"""
        animation = QPropertyAnimation(widget, b"pos")
        animation.setDuration(duration)
        animation.setEasingCurve(QEasingCurve.Type.OutBounce)
        return animation
    
    def _create_glow_animation(self, widget: QWidget, duration: int) -> QPropertyAnimation:
        """Create glow animation using opacity changes"""
        animation = QPropertyAnimation(widget, b"windowOpacity")
        animation.setDuration(duration)
        animation.setStartValue(0.7)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        animation.setLoopCount(-1)  # Infinite loop
        return animation
    
    def stop_animation(self, animation_id: str) -> None:
        """Stop a specific animation"""
        if animation_id in self.animations:
            self.animations[animation_id].stop()
            del self.animations[animation_id]
    
    def stop_all_animations(self) -> None:
        """Stop all running animations"""
        for animation in self.animations.values():
            animation.stop()
        self.animations.clear()
    
    def _on_system_palette_changed(self, palette: QPalette) -> None:
        """Handle system palette changes for auto theme switching"""
        if self.current_theme == "auto":
            # Detect if system is using dark mode
            window_color = palette.color(QPalette.ColorRole.Window)
            text_color = palette.color(QPalette.ColorRole.WindowText)
            
            # Simple dark mode detection
            window_luminance = self._calculate_luminance(window_color)
            text_luminance = self._calculate_luminance(text_color)
            
            if window_luminance < 0.5:
                self.apply_theme("dark")
            else:
                self.apply_theme("light")
    
    def _calculate_luminance(self, color: QColor) -> float:
        """Calculate relative luminance of a color"""
        def srgb_to_linear(c):
            c = c / 255.0
            return c / 12.92 if c <= 0.03928 else pow((c + 0.055) / 1.055, 2.4)
        
        r = srgb_to_linear(color.red())
        g = srgb_to_linear(color.green())
        b = srgb_to_linear(color.blue())
        
        return 0.2126 * r + 0.7152 * g + 0.0722 * b


class UIPolishManager(QObject):
    """Manages UI polish and visual enhancements"""
    
    def __init__(self, property_panel: QWidget):
        super().__init__()
        self.property_panel = property_panel
        self.polish_enabled = True
        self.effects: Dict[str, Any] = {}
    
    def apply_polish(self) -> None:
        """Apply UI polish and visual enhancements"""
        if not self.polish_enabled:
            return
        
        self._apply_rounded_corners()
        self._apply_subtle_shadows()
        self._apply_smooth_scrolling()
        self._apply_hover_effects()
        self._apply_focus_enhancements()
    
    def _apply_rounded_corners(self) -> None:
        """Apply rounded corners to appropriate widgets"""
        style = """
        QFrame, QGroupBox, QLineEdit, QTextEdit, QComboBox, QPushButton {
            border-radius: 6px;
        }
        """
        self.property_panel.setStyleSheet(
            self.property_panel.styleSheet() + style
        )
    
    def _apply_subtle_shadows(self) -> None:
        """Apply subtle shadow effects"""
        for widget in self.property_panel.findChildren(QFrame):
            if widget.frameStyle() != QFrame.Shape.NoFrame:
                shadow = QGraphicsDropShadowEffect()
                shadow.setBlurRadius(5)
                shadow.setColor(QColor(0, 0, 0, 30))
                shadow.setOffset(0, 2)
                widget.setGraphicsEffect(shadow)
    
    def _apply_smooth_scrolling(self) -> None:
        """Enable smooth scrolling for scroll areas"""
        # This would be implemented with custom scroll area handling
        pass
    
    def _apply_hover_effects(self) -> None:
        """Apply hover effects to interactive elements"""
        hover_style = """
        QPushButton:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
        
        QLineEdit:hover, QComboBox:hover {
            border-width: 2px;
        }
        """
        self.property_panel.setStyleSheet(
            self.property_panel.styleSheet() + hover_style
        )
    
    def _apply_focus_enhancements(self) -> None:
        """Apply enhanced focus indicators"""
        focus_style = """
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
            border: 2px solid #0078d4;
            box-shadow: 0 0 0 3px rgba(0, 120, 212, 0.3);
        }
        """
        self.property_panel.setStyleSheet(
            self.property_panel.styleSheet() + focus_style
        )
    
    def set_polish_enabled(self, enabled: bool) -> None:
        """Enable or disable UI polish"""
        self.polish_enabled = enabled
        if enabled:
            self.apply_polish()


# Export theming components
__all__ = [
    'ThemeType',
    'AnimationType', 
    'ThemeConfiguration',
    'PropertyPanelThemeManager',
    'UIPolishManager'
]