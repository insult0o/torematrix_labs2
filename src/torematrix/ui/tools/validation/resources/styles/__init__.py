"""
Styling resources for merge/split UI components.

This module provides comprehensive CSS styling with theme support,
accessibility features, and component-specific styles.
"""

from enum import Enum
from typing import Dict, Any

# Color palette for UI components
COLORS = {
    # Primary colors
    "primary": "#2196f3",
    "secondary": "#ff9800", 
    "success": "#4caf50",
    "warning": "#ff9800",
    "error": "#f44336",
    "info": "#2196f3",
    
    # Background colors
    "background": "#ffffff",
    "surface": "#f5f5f5",
    "border": "#e0e0e0",
    
    # Text colors
    "text_primary": "#212121",
    "text_secondary": "#757575",
    "text_disabled": "#9e9e9e",
    
    # Dark theme colors
    "dark_background": "#121212",
    "dark_surface": "#1e1e1e",
    "dark_border": "#333333",
    "dark_text_primary": "#ffffff",
    "dark_text_secondary": "#b0b0b0"
}


def get_color(color_name: str) -> str:
    """Get color value by name."""
    return COLORS.get(color_name, "#000000")


def apply_theme(widget, theme: str = "light"):
    """Apply theme to a widget."""
    widget.setProperty("theme", theme)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def get_style_for_component(component: str) -> str:
    """Get specific styles for a component."""
    styles = {
        "button": """
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #0d47a1;
            }
            QPushButton:disabled {
                background-color: #e0e0e0;
                color: #9e9e9e;
            }
        """,
        
        "dialog": """
            QDialog {
                background-color: #ffffff;
                color: #212121;
            }
        """,
        
        "list": """
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
                selection-background-color: #e3f2fd;
            }
        """,
        
        "text": """
            QTextEdit {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 8px;
                background-color: white;
            }
        """
    }
    
    return styles.get(component, "")


# Main stylesheet for merge/split operations
merge_split_styles = """
/* Base Dialog Styling */
QDialog {
    background-color: #ffffff;
    color: #212121;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

QDialog[theme="dark"] {
    background-color: #121212;
    color: #ffffff;
}

/* Button Styling */
QPushButton {
    background-color: #2196f3;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
    min-height: 20px;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #1976d2;
}

QPushButton:pressed {
    background-color: #0d47a1;
}

QPushButton:disabled {
    background-color: #e0e0e0;
    color: #9e9e9e;
}

QPushButton:focus {
    outline: 2px solid #005fcc;
    outline-offset: 2px;
}

QPushButton[theme="dark"] {
    background-color: #1976d2;
}

QPushButton[theme="dark"]:hover {
    background-color: #2196f3;
}

QPushButton[theme="dark"]:disabled {
    background-color: #333333;
    color: #666666;
}

/* Secondary Button Styling */
QPushButton.secondary {
    background-color: #ff9800;
}

QPushButton.secondary:hover {
    background-color: #f57c00;
}

/* Success Button Styling */
QPushButton.success {
    background-color: #4caf50;
}

QPushButton.success:hover {
    background-color: #388e3c;
}

/* Warning Button Styling */
QPushButton.warning {
    background-color: #ff9800;
}

QPushButton.warning:hover {
    background-color: #f57c00;
}

/* Error/Danger Button Styling */
QPushButton.danger {
    background-color: #f44336;
}

QPushButton.danger:hover {
    background-color: #d32f2f;
}

/* List Widget Styling */
QListWidget {
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    background-color: white;
    alternate-background-color: #f8f9fa;
    selection-background-color: #e3f2fd;
    selection-color: #1976d2;
    outline: none;
    padding: 4px;
}

QListWidget:focus {
    border-color: #2196f3;
    outline: 2px solid #005fcc;
    outline-offset: 1px;
}

QListWidget::item {
    padding: 8px;
    border-radius: 2px;
    margin: 1px;
}

QListWidget::item:hover {
    background-color: #f5f5f5;
}

QListWidget::item:selected {
    background-color: #e3f2fd;
    color: #1976d2;
}

QListWidget[theme="dark"] {
    background-color: #1e1e1e;
    border-color: #333333;
    color: #ffffff;
    alternate-background-color: #252525;
    selection-background-color: #0d47a1;
}

QListWidget[theme="dark"]::item:hover {
    background-color: #333333;
}

/* Text Edit Styling */
QTextEdit {
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 8px;
    background-color: white;
    color: #212121;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    line-height: 1.4;
}

QTextEdit:focus {
    border-color: #2196f3;
    outline: 2px solid #005fcc;
    outline-offset: 1px;
}

QTextEdit[theme="dark"] {
    background-color: #1e1e1e;
    border-color: #333333;
    color: #ffffff;
}

/* Group Box Styling */
QGroupBox {
    font-weight: bold;
    border: 2px solid #e0e0e0;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 8px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
    color: #1976d2;
}

QGroupBox[theme="dark"] {
    border-color: #333333;
    color: #ffffff;
}

QGroupBox[theme="dark"]::title {
    color: #2196f3;
}

/* Combo Box Styling */
QComboBox {
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 6px 8px;
    background-color: white;
    min-width: 100px;
    min-height: 20px;
}

QComboBox:focus {
    border-color: #2196f3;
    outline: 2px solid #005fcc;
    outline-offset: 1px;
}

QComboBox::drop-down {
    border: none;
    padding-right: 20px;
}

QComboBox::down-arrow {
    width: 12px;
    height: 12px;
}

QComboBox[theme="dark"] {
    background-color: #1e1e1e;
    border-color: #333333;
    color: #ffffff;
}

/* Check Box Styling */
QCheckBox {
    spacing: 8px;
    color: #212121;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #e0e0e0;
    border-radius: 3px;
    background-color: white;
}

QCheckBox::indicator:checked {
    background-color: #2196f3;
    border-color: #2196f3;
}

QCheckBox::indicator:hover {
    border-color: #2196f3;
}

QCheckBox:focus {
    outline: 2px solid #005fcc;
    outline-offset: 2px;
}

QCheckBox[theme="dark"] {
    color: #ffffff;
}

QCheckBox[theme="dark"]::indicator {
    background-color: #1e1e1e;
    border-color: #333333;
}

/* Radio Button Styling */
QRadioButton {
    spacing: 8px;
    color: #212121;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #e0e0e0;
    border-radius: 9px;
    background-color: white;
}

QRadioButton::indicator:checked {
    background-color: #2196f3;
    border-color: #2196f3;
}

QRadioButton:focus {
    outline: 2px solid #005fcc;
    outline-offset: 2px;
}

QRadioButton[theme="dark"] {
    color: #ffffff;
}

QRadioButton[theme="dark"]::indicator {
    background-color: #1e1e1e;
    border-color: #333333;
}

/* Table Widget Styling */
QTableWidget {
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    background-color: white;
    alternate-background-color: #f8f9fa;
    gridline-color: #e0e0e0;
    selection-background-color: #e3f2fd;
}

QTableWidget::item {
    padding: 8px;
    border: none;
}

QTableWidget::item:selected {
    background-color: #e3f2fd;
    color: #1976d2;
}

QHeaderView::section {
    background-color: #f5f5f5;
    padding: 8px;
    border: 1px solid #e0e0e0;
    font-weight: bold;
    color: #212121;
}

QTableWidget[theme="dark"] {
    background-color: #1e1e1e;
    border-color: #333333;
    color: #ffffff;
    alternate-background-color: #252525;
    gridline-color: #333333;
}

QTableWidget[theme="dark"] QHeaderView::section {
    background-color: #333333;
    color: #ffffff;
}

/* Progress Bar Styling */
QProgressBar {
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    text-align: center;
    background-color: #f5f5f5;
    height: 20px;
}

QProgressBar::chunk {
    background-color: #2196f3;
    border-radius: 3px;
}

QProgressBar[theme="dark"] {
    background-color: #333333;
    border-color: #555555;
    color: #ffffff;
}

/* Splitter Styling */
QSplitter::handle {
    background-color: #e0e0e0;
    width: 2px;
    height: 2px;
}

QSplitter::handle:hover {
    background-color: #2196f3;
}

QSplitter[theme="dark"]::handle {
    background-color: #333333;
}

/* Tab Widget Styling */
QTabWidget::pane {
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 8px;
    background-color: white;
}

QTabWidget::tab-bar {
    alignment: left;
}

QTabBar::tab {
    background-color: #f5f5f5;
    border: 1px solid #e0e0e0;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: white;
    border-bottom-color: white;
    color: #2196f3;
    font-weight: bold;
}

QTabBar::tab:hover {
    background-color: #e3f2fd;
}

QTabBar::tab:focus {
    outline: 2px solid #005fcc;
    outline-offset: 2px;
}

QTabWidget[theme="dark"]::pane {
    background-color: #1e1e1e;
    border-color: #333333;
}

QTabWidget[theme="dark"] QTabBar::tab {
    background-color: #333333;
    border-color: #555555;
    color: #ffffff;
}

QTabWidget[theme="dark"] QTabBar::tab:selected {
    background-color: #1e1e1e;
    color: #2196f3;
}

/* Scroll Area Styling */
QScrollArea {
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    background-color: white;
}

QScrollArea[theme="dark"] {
    background-color: #1e1e1e;
    border-color: #333333;
}

/* Scroll Bar Styling */
QScrollBar:vertical {
    background-color: #f5f5f5;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #c0c0c0;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #a0a0a0;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar[theme="dark"]:vertical {
    background-color: #333333;
}

QScrollBar[theme="dark"]::handle:vertical {
    background-color: #666666;
}

/* Tool Button Styling */
QToolButton {
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 6px;
    background-color: white;
    min-width: 24px;
    min-height: 24px;
}

QToolButton:hover {
    background-color: #f5f5f5;
    border-color: #2196f3;
}

QToolButton:pressed {
    background-color: #e3f2fd;
}

QToolButton:focus {
    outline: 2px solid #005fcc;
    outline-offset: 1px;
}

QToolButton[theme="dark"] {
    background-color: #1e1e1e;
    border-color: #333333;
    color: #ffffff;
}

QToolButton[theme="dark"]:hover {
    background-color: #333333;
}

/* Label Styling */
QLabel {
    color: #212121;
}

QLabel[theme="dark"] {
    color: #ffffff;
}

/* Frame Styling */
QFrame {
    border: none;
}

QFrame[frameShape="5"] { /* HLine */
    border-top: 1px solid #e0e0e0;
    max-height: 1px;
}

QFrame[theme="dark"][frameShape="5"] {
    border-top-color: #333333;
}

/* Accessibility Support */
*:focus {
    outline: 2px solid #005fcc;
    outline-offset: 2px;
}

/* High contrast mode support */
@media (prefers-contrast: high) {
    * {
        border-width: 2px !important;
        outline-width: 3px !important;
    }
    
    QPushButton {
        border: 2px solid #000000 !important;
    }
    
    QListWidget,
    QTextEdit,
    QComboBox {
        border: 2px solid #000000 !important;
    }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}
"""