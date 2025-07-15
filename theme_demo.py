#!/usr/bin/env python3
"""Advanced Theme System Demo - Real-time Theme Switching"""

import sys
import json
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QPushButton, QComboBox, QSlider,
                           QTextEdit, QFrame, QGridLayout, QColorDialog, QCheckBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette


class ThemeDemo(QMainWindow):
    """Advanced theme system demonstration."""
    
    theme_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.current_theme = "Professional Light"
        self.themes = self.load_themes()
        self.init_ui()
        self.apply_theme(self.current_theme)
        
    def init_ui(self):
        """Initialize the theme demo interface."""
        self.setWindowTitle("🎨 TORE Matrix Labs V3 - Advanced Theme System")
        self.setGeometry(100, 100, 1400, 900)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Header
        header = QLabel("🎨 Advanced Theme System - Real-time Theme Switching")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        header.setObjectName("header")
        layout.addWidget(header)
        
        # Theme controls
        controls_frame = QFrame()
        controls_frame.setObjectName("controls_frame")
        controls_layout = QHBoxLayout(controls_frame)
        
        # Theme selector
        theme_label = QLabel("Theme:")
        theme_label.setObjectName("control_label")
        controls_layout.addWidget(theme_label)
        
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(list(self.themes.keys()))
        self.theme_selector.setCurrentText(self.current_theme)
        self.theme_selector.currentTextChanged.connect(self.change_theme)
        controls_layout.addWidget(self.theme_selector)
        
        # Font size control
        font_label = QLabel("Font Size:")
        font_label.setObjectName("control_label")
        controls_layout.addWidget(font_label)
        
        self.font_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_slider.setRange(8, 20)
        self.font_slider.setValue(12)
        self.font_slider.valueChanged.connect(self.change_font_size)
        controls_layout.addWidget(self.font_slider)
        
        self.font_value = QLabel("12px")
        self.font_value.setObjectName("control_label")
        controls_layout.addWidget(self.font_value)
        
        # Accessibility options
        self.high_contrast = QCheckBox("High Contrast")
        self.high_contrast.toggled.connect(self.toggle_high_contrast)
        controls_layout.addWidget(self.high_contrast)
        
        # Custom color button
        color_btn = QPushButton("🎨 Custom Colors")
        color_btn.clicked.connect(self.open_color_dialog)
        controls_layout.addWidget(color_btn)
        
        layout.addWidget(controls_frame)
        
        # Demo content grid
        content_grid = QGridLayout()
        
        # Sample UI components
        self.create_sample_components(content_grid)
        
        content_widget = QWidget()
        content_widget.setLayout(content_grid)
        layout.addWidget(content_widget)
        
        # Live theme info
        self.theme_info = QTextEdit()
        self.theme_info.setReadOnly(True)
        self.theme_info.setMaximumHeight(200)
        self.theme_info.setObjectName("theme_info")
        self.update_theme_info()
        layout.addWidget(self.theme_info)
        
    def create_sample_components(self, layout):
        """Create sample UI components to demonstrate theming."""
        row = 0
        
        # Buttons row
        layout.addWidget(QLabel("Buttons:"), row, 0)
        button_layout = QHBoxLayout()
        
        primary_btn = QPushButton("Primary Action")
        primary_btn.setObjectName("primary_button")
        button_layout.addWidget(primary_btn)
        
        secondary_btn = QPushButton("Secondary")
        secondary_btn.setObjectName("secondary_button")
        button_layout.addWidget(secondary_btn)
        
        danger_btn = QPushButton("Danger")
        danger_btn.setObjectName("danger_button")
        button_layout.addWidget(danger_btn)
        
        button_widget = QWidget()
        button_widget.setLayout(button_layout)
        layout.addWidget(button_widget, row, 1)
        row += 1
        
        # Text components
        layout.addWidget(QLabel("Text:"), row, 0)
        text_layout = QVBoxLayout()
        
        title_text = QLabel("Sample Title Text")
        title_text.setObjectName("title_text")
        text_layout.addWidget(title_text)
        
        body_text = QLabel("This is sample body text to demonstrate typography.")
        body_text.setObjectName("body_text")
        text_layout.addWidget(body_text)
        
        text_widget = QWidget()
        text_widget.setLayout(text_layout)
        layout.addWidget(text_widget, row, 1)
        row += 1
        
        # Input components
        layout.addWidget(QLabel("Inputs:"), row, 0)
        from PyQt6.QtWidgets import QLineEdit, QSpinBox
        
        input_layout = QHBoxLayout()
        
        text_input = QLineEdit("Sample text input")
        text_input.setObjectName("text_input")
        input_layout.addWidget(text_input)
        
        spin_input = QSpinBox()
        spin_input.setValue(42)
        spin_input.setObjectName("spin_input")
        input_layout.addWidget(spin_input)
        
        input_widget = QWidget()
        input_widget.setLayout(input_layout)
        layout.addWidget(input_widget, row, 1)
        row += 1
        
        # Status indicators
        layout.addWidget(QLabel("Status:"), row, 0)
        status_layout = QHBoxLayout()
        
        success_label = QLabel("✅ Success")
        success_label.setObjectName("success_status")
        status_layout.addWidget(success_label)
        
        warning_label = QLabel("⚠️ Warning")
        warning_label.setObjectName("warning_status")
        status_layout.addWidget(warning_label)
        
        error_label = QLabel("❌ Error")
        error_label.setObjectName("error_status")
        status_layout.addWidget(error_label)
        
        status_widget = QWidget()
        status_widget.setLayout(status_layout)
        layout.addWidget(status_widget, row, 1)
    
    def load_themes(self):
        """Load available themes."""
        return {
            "Professional Light": {
                "background": "#ffffff",
                "surface": "#f8f9fa",
                "primary": "#3498db",
                "secondary": "#6c757d",
                "success": "#28a745",
                "warning": "#ffc107",
                "danger": "#dc3545",
                "text": "#212529",
                "text_secondary": "#6c757d"
            },
            "Professional Dark": {
                "background": "#1e1e1e",
                "surface": "#2d2d30",
                "primary": "#569cd6",
                "secondary": "#9cdcfe",
                "success": "#4ec9b0",
                "warning": "#dcdcaa",
                "danger": "#f48771",
                "text": "#d4d4d4",
                "text_secondary": "#9cdcfe"
            },
            "High Contrast Light": {
                "background": "#ffffff",
                "surface": "#f0f0f0",
                "primary": "#0000ff",
                "secondary": "#000000",
                "success": "#008000",
                "warning": "#ff8000",
                "danger": "#ff0000",
                "text": "#000000",
                "text_secondary": "#333333"
            },
            "High Contrast Dark": {
                "background": "#000000",
                "surface": "#1a1a1a",
                "primary": "#00ffff",
                "secondary": "#ffffff",
                "success": "#00ff00",
                "warning": "#ffff00",
                "danger": "#ff0000",
                "text": "#ffffff",
                "text_secondary": "#cccccc"
            },
            "Ocean Blue": {
                "background": "#f0f8ff",
                "surface": "#e6f3ff",
                "primary": "#1e88e5",
                "secondary": "#42a5f5",
                "success": "#00acc1",
                "warning": "#ffb74d",
                "danger": "#e57373",
                "text": "#0d47a1",
                "text_secondary": "#1565c0"
            }
        }
    
    def change_theme(self, theme_name):
        """Change the current theme."""
        self.current_theme = theme_name
        self.apply_theme(theme_name)
        self.update_theme_info()
        
    def apply_theme(self, theme_name):
        """Apply the selected theme to the interface."""
        if theme_name not in self.themes:
            return
        
        theme = self.themes[theme_name]
        
        # Build stylesheet
        stylesheet = f"""
        QMainWindow {{
            background-color: {theme['background']};
            color: {theme['text']};
        }}
        
        QWidget {{
            background-color: {theme['background']};
            color: {theme['text']};
        }}
        
        #header {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {theme['primary']}, stop:1 {theme['secondary']});
            color: white;
            padding: 15px;
            border-radius: 10px;
            margin: 10px;
        }}
        
        #controls_frame {{
            background-color: {theme['surface']};
            border: 1px solid {theme['secondary']};
            border-radius: 8px;
            padding: 10px;
            margin: 5px;
        }}
        
        #control_label {{
            color: {theme['text']};
            font-weight: bold;
        }}
        
        QComboBox {{
            background-color: {theme['surface']};
            border: 2px solid {theme['secondary']};
            border-radius: 4px;
            padding: 5px;
            color: {theme['text']};
        }}
        
        QComboBox:hover {{
            border-color: {theme['primary']};
        }}
        
        QSlider::groove:horizontal {{
            background: {theme['surface']};
            height: 8px;
            border-radius: 4px;
        }}
        
        QSlider::handle:horizontal {{
            background: {theme['primary']};
            border: 2px solid {theme['primary']};
            width: 18px;
            margin: -5px 0;
            border-radius: 9px;
        }}
        
        #primary_button {{
            background-color: {theme['primary']};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }}
        
        #primary_button:hover {{
            background-color: {theme['primary']}dd;
        }}
        
        #secondary_button {{
            background-color: {theme['secondary']};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
        }}
        
        #danger_button {{
            background-color: {theme['danger']};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
        }}
        
        #title_text {{
            font-size: 16px;
            font-weight: bold;
            color: {theme['text']};
        }}
        
        #body_text {{
            color: {theme['text_secondary']};
        }}
        
        #text_input {{
            background-color: {theme['surface']};
            border: 2px solid {theme['secondary']};
            border-radius: 4px;
            padding: 5px;
            color: {theme['text']};
        }}
        
        #text_input:focus {{
            border-color: {theme['primary']};
        }}
        
        #spin_input {{
            background-color: {theme['surface']};
            border: 2px solid {theme['secondary']};
            border-radius: 4px;
            color: {theme['text']};
        }}
        
        #success_status {{
            color: {theme['success']};
            font-weight: bold;
        }}
        
        #warning_status {{
            color: {theme['warning']};
            font-weight: bold;
        }}
        
        #error_status {{
            color: {theme['danger']};
            font-weight: bold;
        }}
        
        #theme_info {{
            background-color: {theme['surface']};
            border: 2px solid {theme['secondary']};
            border-radius: 8px;
            color: {theme['text']};
            font-family: monospace;
        }}
        
        QCheckBox {{
            color: {theme['text']};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {theme['primary']};
            border: 2px solid {theme['primary']};
        }}
        """
        
        self.setStyleSheet(stylesheet)
        self.theme_changed.emit(theme_name)
    
    def change_font_size(self, size):
        """Change the font size."""
        self.font_value.setText(f"{size}px")
        font = self.font()
        font.setPointSize(size)
        self.setFont(font)
    
    def toggle_high_contrast(self, enabled):
        """Toggle high contrast mode."""
        if enabled:
            if "dark" in self.current_theme.lower():
                self.theme_selector.setCurrentText("High Contrast Dark")
            else:
                self.theme_selector.setCurrentText("High Contrast Light")
    
    def open_color_dialog(self):
        """Open color customization dialog."""
        color = QColorDialog.getColor(Qt.GlobalColor.blue, self, "Choose Primary Color")
        if color.isValid():
            # Create custom theme with selected color
            custom_theme = self.themes["Professional Light"].copy()
            custom_theme["primary"] = color.name()
            self.themes["Custom"] = custom_theme
            
            if "Custom" not in [self.theme_selector.itemText(i) for i in range(self.theme_selector.count())]:
                self.theme_selector.addItem("Custom")
            
            self.theme_selector.setCurrentText("Custom")
    
    def update_theme_info(self):
        """Update the theme information display."""
        if self.current_theme not in self.themes:
            return
        
        theme = self.themes[self.current_theme]
        
        info_text = f"""
🎨 Current Theme: {self.current_theme}

📋 Color Palette:
  • Background: {theme['background']}
  • Surface: {theme['surface']}
  • Primary: {theme['primary']}
  • Secondary: {theme['secondary']}
  • Success: {theme['success']}
  • Warning: {theme['warning']}
  • Danger: {theme['danger']}
  • Text: {theme['text']}
  • Text Secondary: {theme['text_secondary']}

🔧 Features Demonstrated:
  • Real-time theme switching
  • Component style inheritance
  • Color palette management
  • Accessibility support (high contrast)
  • Custom color selection
  • Typography scaling
  • Consistent styling across components

💡 TORE Matrix Labs V3 Theme System:
  • Hot-reload theme switching
  • Accessibility compliance (WCAG 2.1)
  • Custom theme creation
  • Component-specific styling
  • User preference persistence
  • Dark/light mode support
        """
        
        self.theme_info.setPlainText(info_text.strip())


def main():
    """Run the theme system demo."""
    app = QApplication(sys.argv)
    
    demo = ThemeDemo()
    demo.show()
    
    print("🎨 TORE Matrix Labs V3 - Advanced Theme System Demo")
    print("✨ Real-time theme switching with 5+ built-in themes")
    print("🎯 Accessibility features and custom color support")
    print("📱 Responsive design with typography scaling")
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())