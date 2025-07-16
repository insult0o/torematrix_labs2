"""
Styles for merge/split UI components.
"""

# Comprehensive stylesheet for merge/split UI components
merge_split_styles = """
/* Main Dialog Styles */
QDialog {
    background-color: #f8f9fa;
    color: #212529;
}

/* Group Box Styles */
QGroupBox {
    font-weight: bold;
    border: 2px solid #dee2e6;
    border-radius: 5px;
    margin: 5px 0px;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
    background-color: #f8f9fa;
}

/* Button Styles */
QPushButton {
    background-color: #007bff;
    border: none;
    color: white;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #0056b3;
}

QPushButton:pressed {
    background-color: #004085;
}

QPushButton:disabled {
    background-color: #6c757d;
    color: #adb5bd;
}

/* Default button (primary action) */
QPushButton[default="true"] {
    background-color: #28a745;
}

QPushButton[default="true"]:hover {
    background-color: #1e7e34;
}

/* Cancel/secondary buttons */
QPushButton[text="Cancel"] {
    background-color: #6c757d;
}

QPushButton[text="Cancel"]:hover {
    background-color: #545b62;
}

/* List Widget Styles */
QListWidget {
    border: 1px solid #ced4da;
    border-radius: 4px;
    background-color: white;
    selection-background-color: #007bff;
    alternate-background-color: #f8f9fa;
}

QListWidget::item {
    padding: 8px;
    border-bottom: 1px solid #e9ecef;
}

QListWidget::item:selected {
    background-color: #007bff;
    color: white;
}

QListWidget::item:hover {
    background-color: #e9ecef;
}

/* Text Edit Styles */
QTextEdit {
    border: 1px solid #ced4da;
    border-radius: 4px;
    background-color: white;
    padding: 8px;
    font-family: "Consolas", "Monaco", monospace;
}

QTextEdit:focus {
    border-color: #007bff;
    outline: none;
}

/* Line Edit Styles */
QLineEdit {
    border: 1px solid #ced4da;
    border-radius: 4px;
    padding: 6px 12px;
    background-color: white;
}

QLineEdit:focus {
    border-color: #007bff;
}

/* Combo Box Styles */
QComboBox {
    border: 1px solid #ced4da;
    border-radius: 4px;
    padding: 6px 12px;
    background-color: white;
    min-width: 100px;
}

QComboBox:focus {
    border-color: #007bff;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    image: url(down_arrow.png);
    width: 12px;
    height: 12px;
}

/* Tab Widget Styles */
QTabWidget::pane {
    border: 1px solid #dee2e6;
    border-radius: 4px;
    background-color: white;
}

QTabBar::tab {
    background-color: #e9ecef;
    border: 1px solid #dee2e6;
    padding: 8px 16px;
    margin-right: 2px;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: white;
    border-bottom: 1px solid white;
}

QTabBar::tab:hover {
    background-color: #f8f9fa;
}

/* Table Widget Styles */
QTableWidget {
    border: 1px solid #dee2e6;
    border-radius: 4px;
    background-color: white;
    gridline-color: #e9ecef;
}

QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #e9ecef;
}

QTableWidget::item:selected {
    background-color: #007bff;
    color: white;
}

/* Tree Widget Styles */
QTreeWidget {
    border: 1px solid #dee2e6;
    border-radius: 4px;
    background-color: white;
}

QTreeWidget::item {
    padding: 4px;
    border-bottom: 1px solid #f8f9fa;
}

QTreeWidget::item:selected {
    background-color: #007bff;
    color: white;
}

/* Check Box Styles */
QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #ced4da;
    border-radius: 3px;
    background-color: white;
}

QCheckBox::indicator:checked {
    background-color: #007bff;
    border-color: #007bff;
    image: url(checkmark.png);
}

QCheckBox::indicator:hover {
    border-color: #007bff;
}

/* Progress Bar Styles */
QProgressBar {
    border: 1px solid #dee2e6;
    border-radius: 4px;
    text-align: center;
    background-color: #e9ecef;
}

QProgressBar::chunk {
    background-color: #007bff;
    border-radius: 3px;
}

/* Splitter Styles */
QSplitter::handle {
    background-color: #dee2e6;
    width: 2px;
    height: 2px;
}

QSplitter::handle:hover {
    background-color: #007bff;
}

/* Scroll Area Styles */
QScrollArea {
    border: 1px solid #dee2e6;
    border-radius: 4px;
    background-color: white;
}

/* Frame Styles */
QFrame[frameShape="4"] { /* HLine */
    color: #dee2e6;
    background-color: #dee2e6;
    height: 1px;
}

/* Label Styles */
QLabel[accessibleName="title"] {
    font-size: 14px;
    font-weight: bold;
    color: #212529;
}

QLabel[accessibleName="subtitle"] {
    font-size: 12px;
    color: #6c757d;
}

/* Accessibility Styles */
*:focus {
    outline: 2px solid #007bff;
    outline-offset: 2px;
}

/* Dark Theme Support */
QDialog[darkTheme="true"] {
    background-color: #2b2b2b;
    color: #ffffff;
}

QDialog[darkTheme="true"] QGroupBox {
    border-color: #555555;
    background-color: #2b2b2b;
}

QDialog[darkTheme="true"] QListWidget,
QDialog[darkTheme="true"] QTextEdit,
QDialog[darkTheme="true"] QLineEdit,
QDialog[darkTheme="true"] QComboBox {
    background-color: #3c3c3c;
    border-color: #555555;
    color: #ffffff;
}

/* High Contrast Mode */
QDialog[highContrast="true"] {
    background-color: #000000;
    color: #ffffff;
}

QDialog[highContrast="true"] QPushButton {
    background-color: #ffffff;
    color: #000000;
    border: 2px solid #ffffff;
}

/* Animation Classes */
.fade-in {
    animation: fadeIn 0.3s ease-in;
}

.slide-in {
    animation: slideIn 0.3s ease-out;
}
"""

__all__ = ["merge_split_styles"]