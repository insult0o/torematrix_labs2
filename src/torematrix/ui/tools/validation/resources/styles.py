"""
Stylesheet definitions for merge/split operation dialogs.

This module provides comprehensive styling for all merge/split UI components
with support for light/dark themes and accessibility features.
"""

from typing import Dict, Any

# Base color palette
COLORS = {
    "primary": "#2196f3",
    "primary_dark": "#1976d2", 
    "primary_light": "#e3f2fd",
    "secondary": "#ff9800",
    "secondary_dark": "#f57c00",
    "secondary_light": "#fff3e0",
    "success": "#4caf50",
    "success_light": "#e8f5e9",
    "warning": "#ff9800",
    "warning_light": "#fff3e0", 
    "error": "#f44336",
    "error_light": "#ffebee",
    "info": "#2196f3",
    "info_light": "#e3f2fd",
    "background": "#ffffff",
    "surface": "#f5f5f5",
    "border": "#e0e0e0",
    "text_primary": "#212121",
    "text_secondary": "#666666",
    "text_disabled": "#9e9e9e"
}

# Dialog base styles
DIALOG_BASE_STYLE = f"""
QDialog {{
    background-color: {COLORS['background']};
    color: {COLORS['text_primary']};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 11px;
}}

QDialog QLabel {{
    color: {COLORS['text_primary']};
}}

QDialog QLabel[accessibleName="title"] {{
    font-size: 16px;
    font-weight: bold;
    color: {COLORS['text_primary']};
    margin-bottom: 8px;
}}

QDialog QLabel[accessibleName="description"] {{
    color: {COLORS['text_secondary']};
    margin-bottom: 10px;
}}
"""

# Button styles
BUTTON_STYLES = f"""
QPushButton {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 8px 16px;
    color: {COLORS['text_primary']};
    font-weight: 500;
    min-width: 80px;
}}

QPushButton:hover {{
    background-color: {COLORS['border']};
    border-color: {COLORS['primary']};
}}

QPushButton:pressed {{
    background-color: {COLORS['primary_light']};
}}

QPushButton:disabled {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_disabled']};
    border-color: {COLORS['border']};
}}

QPushButton[class="primary"] {{
    background-color: {COLORS['primary']};
    color: white;
    border-color: {COLORS['primary']};
}}

QPushButton[class="primary"]:hover {{
    background-color: {COLORS['primary_dark']};
}}

QPushButton[class="primary"]:disabled {{
    background-color: {COLORS['text_disabled']};
    border-color: {COLORS['text_disabled']};
}}

QPushButton[class="secondary"] {{
    background-color: {COLORS['secondary']};
    color: white;
    border-color: {COLORS['secondary']};
}}

QPushButton[class="secondary"]:hover {{
    background-color: {COLORS['secondary_dark']};
}}

QPushButton[class="danger"] {{
    background-color: {COLORS['error']};
    color: white;
    border-color: {COLORS['error']};
}}

QPushButton[class="danger"]:hover {{
    background-color: #d32f2f;
}}
"""

# List widget styles
LIST_STYLES = f"""
QListWidget {{
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    background-color: {COLORS['background']};
    selection-background-color: {COLORS['primary_light']};
    selection-color: {COLORS['text_primary']};
    outline: none;
}}

QListWidget::item {{
    padding: 8px;
    border-bottom: 1px solid {COLORS['surface']};
    min-height: 20px;
}}

QListWidget::item:selected {{
    background-color: {COLORS['primary_light']};
    border-color: {COLORS['primary']};
}}

QListWidget::item:hover {{
    background-color: {COLORS['surface']};
}}

QListWidget[class="droppable"] {{
    border: 2px dashed {COLORS['border']};
    background-color: {COLORS['surface']};
}}

QListWidget[class="droppable"][dragActive="true"] {{
    border-color: {COLORS['primary']};
    background-color: {COLORS['primary_light']};
}}
"""

# Text edit styles
TEXT_EDIT_STYLES = f"""
QTextEdit {{
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    background-color: {COLORS['background']};
    color: {COLORS['text_primary']};
    padding: 8px;
    selection-background-color: {COLORS['primary_light']};
}}

QTextEdit:focus {{
    border-color: {COLORS['primary']};
    outline: none;
}}

QTextEdit:read-only {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_secondary']};
}}

QTextEdit[class="preview"] {{
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 10px;
    line-height: 1.4;
}}
"""

# Group box styles
GROUP_BOX_STYLES = f"""
QGroupBox {{
    font-weight: bold;
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 8px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    background-color: {COLORS['background']};
    color: {COLORS['text_primary']};
}}
"""

# Combo box styles
COMBO_BOX_STYLES = f"""
QComboBox {{
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 6px 12px;
    background-color: {COLORS['background']};
    color: {COLORS['text_primary']};
    min-width: 120px;
}}

QComboBox:hover {{
    border-color: {COLORS['primary']};
}}

QComboBox:focus {{
    border-color: {COLORS['primary']};
    outline: none;
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid {COLORS['text_secondary']};
    margin-right: 5px;
}}

QComboBox QAbstractItemView {{
    border: 1px solid {COLORS['border']};
    background-color: {COLORS['background']};
    selection-background-color: {COLORS['primary_light']};
    outline: none;
}}
"""

# Checkbox and radio button styles
CHECKBOX_STYLES = f"""
QCheckBox {{
    spacing: 8px;
    color: {COLORS['text_primary']};
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    background-color: {COLORS['background']};
}}

QCheckBox::indicator:hover {{
    border-color: {COLORS['primary']};
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS['primary']};
    border-color: {COLORS['primary']};
    image: none;
}}

QRadioButton {{
    spacing: 8px;
    color: {COLORS['text_primary']};
}}

QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    background-color: {COLORS['background']};
}}

QRadioButton::indicator:hover {{
    border-color: {COLORS['primary']};
}}

QRadioButton::indicator:checked {{
    background-color: {COLORS['primary']};
    border-color: {COLORS['primary']};
}}
"""

# Table widget styles
TABLE_STYLES = f"""
QTableWidget {{
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    background-color: {COLORS['background']};
    gridline-color: {COLORS['border']};
    selection-background-color: {COLORS['primary_light']};
}}

QTableWidget::item {{
    padding: 8px;
    border: none;
}}

QTableWidget::item:selected {{
    background-color: {COLORS['primary_light']};
    color: {COLORS['text_primary']};
}}

QHeaderView::section {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    padding: 8px;
    font-weight: bold;
    color: {COLORS['text_primary']};
}}
"""

# Progress bar styles
PROGRESS_BAR_STYLES = f"""
QProgressBar {{
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    background-color: {COLORS['surface']};
    text-align: center;
    color: {COLORS['text_primary']};
    height: 20px;
}}

QProgressBar::chunk {{
    background-color: {COLORS['primary']};
    border-radius: 3px;
}}

QProgressBar[class="success"]::chunk {{
    background-color: {COLORS['success']};
}}

QProgressBar[class="warning"]::chunk {{
    background-color: {COLORS['warning']};
}}

QProgressBar[class="error"]::chunk {{
    background-color: {COLORS['error']};
}}
"""

# Splitter styles
SPLITTER_STYLES = f"""
QSplitter::handle {{
    background-color: {COLORS['border']};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

QSplitter::handle:hover {{
    background-color: {COLORS['primary']};
}}
"""

# Tab widget styles
TAB_WIDGET_STYLES = f"""
QTabWidget::pane {{
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    background-color: {COLORS['background']};
}}

QTabBar::tab {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-bottom: none;
    padding: 8px 16px;
    margin-right: 2px;
    color: {COLORS['text_secondary']};
}}

QTabBar::tab:selected {{
    background-color: {COLORS['background']};
    color: {COLORS['text_primary']};
    font-weight: bold;
}}

QTabBar::tab:hover {{
    background-color: {COLORS['primary_light']};
    color: {COLORS['text_primary']};
}}

QTabBar::tab:first {{
    border-top-left-radius: 4px;
}}

QTabBar::tab:last {{
    border-top-right-radius: 4px;
    margin-right: 0;
}}
"""

# Scroll area styles
SCROLL_AREA_STYLES = f"""
QScrollArea {{
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    background-color: {COLORS['background']};
}}

QScrollBar:vertical {{
    border: none;
    background-color: {COLORS['surface']};
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['border']};
    border-radius: 6px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['text_secondary']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    border: none;
    background: none;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}
"""

# Warning and validation styles
VALIDATION_STYLES = f"""
QWidget[class="warning-item"] {{
    border-left: 4px solid {COLORS['warning']};
    background-color: {COLORS['warning_light']};
    border-radius: 4px;
    margin: 2px 0;
}}

QWidget[class="error-item"] {{
    border-left: 4px solid {COLORS['error']};
    background-color: {COLORS['error_light']};
    border-radius: 4px;
    margin: 2px 0;
}}

QWidget[class="info-item"] {{
    border-left: 4px solid {COLORS['info']};
    background-color: {COLORS['info_light']};
    border-radius: 4px;
    margin: 2px 0;
}}

QWidget[class="success-item"] {{
    border-left: 4px solid {COLORS['success']};
    background-color: {COLORS['success_light']};
    border-radius: 4px;
    margin: 2px 0;
}}
"""

# Complete merge/split styles
merge_split_styles = f"""
/* Base dialog styles */
{DIALOG_BASE_STYLE}

/* Button styles */
{BUTTON_STYLES}

/* List widget styles */
{LIST_STYLES}

/* Text edit styles */
{TEXT_EDIT_STYLES}

/* Group box styles */
{GROUP_BOX_STYLES}

/* Combo box styles */
{COMBO_BOX_STYLES}

/* Checkbox and radio styles */
{CHECKBOX_STYLES}

/* Table widget styles */
{TABLE_STYLES}

/* Progress bar styles */
{PROGRESS_BAR_STYLES}

/* Splitter styles */
{SPLITTER_STYLES}

/* Tab widget styles */
{TAB_WIDGET_STYLES}

/* Scroll area styles */
{SCROLL_AREA_STYLES}

/* Validation styles */
{VALIDATION_STYLES}

/* Accessibility styles */
QWidget:focus {{
    outline: 2px solid {COLORS['primary']};
    outline-offset: 2px;
}}

/* Drag and drop styles */
QWidget[dragActive="true"] {{
    border: 2px dashed {COLORS['primary']};
    background-color: {COLORS['primary_light']};
}}

/* High contrast mode support */
@media (prefers-contrast: high) {{
    QDialog {{
        border: 2px solid {COLORS['text_primary']};
    }}
    
    QPushButton {{
        border-width: 2px;
    }}
    
    QListWidget, QTextEdit, QComboBox {{
        border-width: 2px;
    }}
}}

/* Dark theme support */
QDialog[theme="dark"] {{
    background-color: #121212;
    color: #ffffff;
}}

QDialog[theme="dark"] QGroupBox {{
    color: #ffffff;
    border-color: #404040;
}}

QDialog[theme="dark"] QPushButton {{
    background-color: #2c2c2c;
    border-color: #404040;
    color: #ffffff;
}}

QDialog[theme="dark"] QListWidget,
QDialog[theme="dark"] QTextEdit,
QDialog[theme="dark"] QComboBox {{
    background-color: #1e1e1e;
    border-color: #404040;
    color: #ffffff;
}}
"""

def get_style_for_component(component_type: str) -> str:
    """Get specific styles for a component type."""
    style_map = {
        "dialog": DIALOG_BASE_STYLE,
        "button": BUTTON_STYLES,
        "list": LIST_STYLES,
        "text": TEXT_EDIT_STYLES,
        "group": GROUP_BOX_STYLES,
        "combo": COMBO_BOX_STYLES,
        "checkbox": CHECKBOX_STYLES,
        "table": TABLE_STYLES,
        "progress": PROGRESS_BAR_STYLES,
        "splitter": SPLITTER_STYLES,
        "tab": TAB_WIDGET_STYLES,
        "scroll": SCROLL_AREA_STYLES,
        "validation": VALIDATION_STYLES
    }
    return style_map.get(component_type, "")

def get_color(color_name: str) -> str:
    """Get a color value from the color palette."""
    return COLORS.get(color_name, "#000000")

def apply_theme(widget, theme: str = "light"):
    """Apply theme to a widget."""
    if hasattr(widget, 'setProperty'):
        widget.setProperty("theme", theme)
        widget.style().polish(widget)