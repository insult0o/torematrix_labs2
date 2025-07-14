"""Theme Selector Dialog for browsing and selecting themes.

Provides a comprehensive interface for users to browse available themes,
preview them in real-time, and select the theme they want to apply.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QGroupBox, QComboBox, QLineEdit, QCheckBox,
    QFrame, QSplitter, QTextEdit, QTabWidget, QListWidget, QListWidgetItem,
    QSizePolicy, QApplication, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QThread, pyqtSlot
from PyQt6.QtGui import QPixmap, QPainter, QFont, QIcon, QColor, QPalette

from ..themes.base import Theme, ThemeMetadata
from ..themes.engine import ThemeEngine
from ..themes.types import ThemeType, ThemeCategory
from ..themes.cache import ThemeCache
from ..themes.accessibility import AccessibilityManager, AccessibilityLevel
from ..themes.icons import IconThemeManager
from .base import BaseDialog

logger = logging.getLogger(__name__)


class ThemePreviewWidget(QWidget):
    """Widget for previewing a theme with sample components."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_theme: Optional[Theme] = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the preview UI with sample components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Preview header
        header = QLabel("Theme Preview")
        header.setObjectName("preview_header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Sample components
        components_group = QGroupBox("Sample Components")
        components_layout = QVBoxLayout(components_group)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        primary_btn = QPushButton("Primary Button")
        primary_btn.setObjectName("primary_button")
        buttons_layout.addWidget(primary_btn)
        
        secondary_btn = QPushButton("Secondary Button")
        secondary_btn.setObjectName("secondary_button")
        buttons_layout.addWidget(secondary_btn)
        
        disabled_btn = QPushButton("Disabled Button")
        disabled_btn.setEnabled(False)
        buttons_layout.addWidget(disabled_btn)
        
        components_layout.addLayout(buttons_layout)
        
        # Text elements
        text_group = QGroupBox("Text Elements")
        text_layout = QVBoxLayout(text_group)
        
        heading = QLabel("Heading Text")
        heading.setObjectName("preview_heading")
        heading.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        text_layout.addWidget(heading)
        
        body_text = QLabel("This is body text showing how regular content appears in this theme.")
        body_text.setObjectName("preview_body")
        body_text.setWordWrap(True)
        text_layout.addWidget(body_text)
        
        link_text = QLabel('<a href="#">This is a link</a>')
        link_text.setObjectName("preview_link")
        text_layout.addWidget(link_text)
        
        components_layout.addWidget(text_group)
        
        # Input elements
        input_group = QGroupBox("Input Elements")
        input_layout = QVBoxLayout(input_group)
        
        text_input = QLineEdit("Sample text input")
        text_input.setObjectName("preview_input")
        input_layout.addWidget(text_input)
        
        checkbox = QCheckBox("Sample checkbox")
        checkbox.setChecked(True)
        input_layout.addWidget(checkbox)
        
        combo = QComboBox()
        combo.addItems(["Option 1", "Option 2", "Option 3"])
        input_layout.addWidget(combo)
        
        components_layout.addWidget(input_group)
        
        layout.addWidget(components_group)
        
        # Status indicators
        status_group = QGroupBox("Status Indicators")
        status_layout = QHBoxLayout(status_group)
        
        success_label = QLabel("Success")
        success_label.setObjectName("status_success")
        status_layout.addWidget(success_label)
        
        warning_label = QLabel("Warning")
        warning_label.setObjectName("status_warning")
        status_layout.addWidget(warning_label)
        
        error_label = QLabel("Error")
        error_label.setObjectName("status_error")
        status_layout.addWidget(error_label)
        
        info_label = QLabel("Info")
        info_label.setObjectName("status_info")
        status_layout.addWidget(info_label)
        
        layout.addWidget(status_group)
        
        layout.addStretch()
    
    def set_theme(self, theme: Optional[Theme]):
        """Apply a theme to the preview widget."""
        self.current_theme = theme
        if theme:
            # Apply theme stylesheet to preview
            stylesheet = theme.generate_stylesheet()
            self.setStyleSheet(stylesheet)
        else:
            self.setStyleSheet("")
        
        self.update()


class ThemeInfoWidget(QWidget):
    """Widget displaying detailed theme information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the theme info UI."""
        layout = QVBoxLayout(self)
        
        # Theme details
        self.title_label = QLabel()
        self.title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(self.title_label)
        
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label)
        
        # Metadata
        metadata_group = QGroupBox("Theme Information")
        metadata_layout = QGridLayout(metadata_group)
        
        self.author_label = QLabel()
        self.version_label = QLabel()
        self.category_label = QLabel()
        self.accessibility_label = QLabel()
        
        metadata_layout.addWidget(QLabel("Author:"), 0, 0)
        metadata_layout.addWidget(self.author_label, 0, 1)
        metadata_layout.addWidget(QLabel("Version:"), 1, 0)
        metadata_layout.addWidget(self.version_label, 1, 1)
        metadata_layout.addWidget(QLabel("Category:"), 2, 0)
        metadata_layout.addWidget(self.category_label, 2, 1)
        metadata_layout.addWidget(QLabel("Accessibility:"), 3, 0)
        metadata_layout.addWidget(self.accessibility_label, 3, 1)
        
        layout.addWidget(metadata_group)
        
        # Features
        features_group = QGroupBox("Features")
        features_layout = QVBoxLayout(features_group)
        
        self.high_contrast_check = QCheckBox("High Contrast Available")
        self.high_contrast_check.setEnabled(False)
        features_layout.addWidget(self.high_contrast_check)
        
        self.color_blind_check = QCheckBox("Color Blind Friendly")
        self.color_blind_check.setEnabled(False)
        features_layout.addWidget(self.color_blind_check)
        
        self.dark_mode_check = QCheckBox("Dark Mode Support")
        self.dark_mode_check.setEnabled(False)
        features_layout.addWidget(self.dark_mode_check)
        
        layout.addWidget(features_group)
        
        layout.addStretch()
    
    def set_theme(self, theme: Optional[Theme]):
        """Update display with theme information."""
        if not theme:
            self.clear_info()
            return
        
        # Basic info
        self.title_label.setText(theme.name)
        self.description_label.setText(theme.metadata.description or "No description available")
        
        # Metadata
        self.author_label.setText(theme.metadata.author or "Unknown")
        self.version_label.setText(theme.metadata.version or "1.0.0")
        self.category_label.setText(theme.metadata.category.value.title() if theme.metadata.category else "Unknown")
        
        # Accessibility level
        accessibility_level = getattr(theme.metadata, 'accessibility_level', None)
        if accessibility_level:
            self.accessibility_label.setText(accessibility_level.value)
        else:
            self.accessibility_label.setText("Not specified")
        
        # Features
        theme_data = theme._data
        accessibility_data = theme_data.get('accessibility', {})
        
        self.high_contrast_check.setChecked(accessibility_data.get('high_contrast_available', False))
        self.color_blind_check.setChecked(accessibility_data.get('color_blind_friendly', False))
        self.dark_mode_check.setChecked(theme.metadata.category == ThemeType.DARK)
    
    def clear_info(self):
        """Clear all displayed information."""
        self.title_label.setText("No theme selected")
        self.description_label.setText("")
        self.author_label.setText("")
        self.version_label.setText("")
        self.category_label.setText("")
        self.accessibility_label.setText("")
        self.high_contrast_check.setChecked(False)
        self.color_blind_check.setChecked(False)
        self.dark_mode_check.setChecked(False)


class ThemeListWidget(QListWidget):
    """Custom list widget for displaying themes with filtering."""
    
    theme_selected = pyqtSignal(object)  # Theme object
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.themes: Dict[str, Theme] = {}
        self.current_filter: Dict[str, Any] = {}
        
        self.setup_ui()
        self.itemClicked.connect(self._on_item_clicked)
    
    def setup_ui(self):
        """Setup the list widget."""
        self.setMinimumWidth(300)
        self.setAlternatingRowColors(True)
    
    def add_theme(self, theme: Theme):
        """Add a theme to the list."""
        self.themes[theme.name] = theme
        self._add_theme_item(theme)
    
    def _add_theme_item(self, theme: Theme):
        """Add a theme item to the list widget."""
        item = QListWidgetItem()
        item.setText(theme.name)
        item.setData(Qt.ItemDataRole.UserRole, theme.name)
        
        # Set tooltip with theme description
        if theme.metadata.description:
            item.setToolTip(theme.metadata.description)
        
        # Add icon based on theme type
        if theme.metadata.category == ThemeType.DARK:
            item.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        elif theme.metadata.category == ThemeType.LIGHT:
            item.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_FileIcon))
        
        self.addItem(item)
    
    def clear_themes(self):
        """Clear all themes from the list."""
        self.clear()
        self.themes.clear()
    
    def set_filter(self, filter_criteria: Dict[str, Any]):
        """Apply filter to theme list."""
        self.current_filter = filter_criteria
        self._apply_filter()
    
    def _apply_filter(self):
        """Apply current filter to visible items."""
        for i in range(self.count()):
            item = self.item(i)
            theme_name = item.data(Qt.ItemDataRole.UserRole)
            theme = self.themes.get(theme_name)
            
            if theme and self._matches_filter(theme):
                item.setHidden(False)
            else:
                item.setHidden(True)
    
    def _matches_filter(self, theme: Theme) -> bool:
        """Check if theme matches current filter criteria."""
        if not self.current_filter:
            return True
        
        # Category filter
        if 'category' in self.current_filter:
            if theme.metadata.category != self.current_filter['category']:
                return False
        
        # Search text filter
        if 'search' in self.current_filter:
            search_text = self.current_filter['search'].lower()
            if search_text and search_text not in theme.name.lower():
                if not theme.metadata.description or search_text not in theme.metadata.description.lower():
                    return False
        
        # Accessibility filter
        if 'accessibility_only' in self.current_filter:
            if self.current_filter['accessibility_only']:
                accessibility_data = theme._data.get('accessibility', {})
                if not accessibility_data.get('high_contrast_available', False):
                    return False
        
        return True
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle item click."""
        theme_name = item.data(Qt.ItemDataRole.UserRole)
        theme = self.themes.get(theme_name)
        if theme:
            self.theme_selected.emit(theme)


class ThemeSelectorDialog(BaseDialog):
    """Dialog for selecting themes with preview and filtering capabilities."""
    
    theme_selected = pyqtSignal(object)  # Selected theme
    
    def __init__(self, 
                 theme_engine: ThemeEngine,
                 current_theme: Optional[Theme] = None,
                 parent=None):
        """Initialize theme selector dialog.
        
        Args:
            theme_engine: Theme engine instance
            current_theme: Currently active theme
            parent: Parent widget
        """
        self.theme_engine = theme_engine
        self.current_theme = current_theme
        self.selected_theme: Optional[Theme] = None
        
        super().__init__(parent)
        
        self.setWindowTitle("Select Theme")
        self.setModal(True)
        self.resize(900, 600)
        
        self.load_themes()
    
    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Choose a Theme")
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Filter controls
        filter_group = QGroupBox("Filter Themes")
        filter_layout = QHBoxLayout(filter_group)
        
        # Search
        filter_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search themes...")
        self.search_input.textChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.search_input)
        
        # Category filter
        filter_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories", None)
        self.category_combo.addItem("Light Themes", ThemeType.LIGHT)
        self.category_combo.addItem("Dark Themes", ThemeType.DARK)
        self.category_combo.addItem("High Contrast", ThemeType.HIGH_CONTRAST)
        self.category_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.category_combo)
        
        # Accessibility filter
        self.accessibility_only_check = QCheckBox("Accessible themes only")
        self.accessibility_only_check.toggled.connect(self._on_filter_changed)
        filter_layout.addWidget(self.accessibility_only_check)
        
        filter_layout.addStretch()
        layout.addWidget(filter_group)
        
        # Main content area
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - theme list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        themes_label = QLabel("Available Themes")
        themes_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        left_layout.addWidget(themes_label)
        
        self.theme_list = ThemeListWidget()
        self.theme_list.theme_selected.connect(self._on_theme_selected)
        left_layout.addWidget(self.theme_list)
        
        content_splitter.addWidget(left_widget)
        
        # Right side - preview and info
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Preview tabs
        self.preview_tabs = QTabWidget()
        
        # Preview tab
        self.preview_widget = ThemePreviewWidget()
        self.preview_tabs.addTab(self.preview_widget, "Preview")
        
        # Info tab
        self.info_widget = ThemeInfoWidget()
        self.preview_tabs.addTab(self.info_widget, "Information")
        
        right_layout.addWidget(self.preview_tabs)
        
        content_splitter.addWidget(right_widget)
        content_splitter.setSizes([300, 600])
        
        layout.addWidget(content_splitter)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh Themes")
        self.refresh_btn.clicked.connect(self.load_themes)
        button_layout.addWidget(self.refresh_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.apply_btn = QPushButton("Apply Theme")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._on_apply_theme)
        button_layout.addWidget(self.apply_btn)
        
        layout.addWidget(QWidget())  # Spacer
        layout.addLayout(button_layout)
    
    def load_themes(self):
        """Load available themes from the theme engine."""
        try:
            self.theme_list.clear_themes()
            
            # Get themes from engine
            available_themes = self.theme_engine.get_available_themes()
            
            for theme in available_themes:
                self.theme_list.add_theme(theme)
            
            # Select current theme if available
            if self.current_theme and self.current_theme.name in self.theme_list.themes:
                for i in range(self.theme_list.count()):
                    item = self.theme_list.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == self.current_theme.name:
                        self.theme_list.setCurrentItem(item)
                        self._on_theme_selected(self.current_theme)
                        break
        
        except Exception as e:
            logger.error(f"Failed to load themes: {e}")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to load themes: {str(e)}"
            )
    
    def _on_filter_changed(self):
        """Handle filter changes."""
        filter_criteria = {}
        
        # Search filter
        search_text = self.search_input.text().strip()
        if search_text:
            filter_criteria['search'] = search_text
        
        # Category filter
        category_data = self.category_combo.currentData()
        if category_data:
            filter_criteria['category'] = category_data
        
        # Accessibility filter
        if self.accessibility_only_check.isChecked():
            filter_criteria['accessibility_only'] = True
        
        self.theme_list.set_filter(filter_criteria)
    
    def _on_theme_selected(self, theme: Theme):
        """Handle theme selection."""
        self.selected_theme = theme
        
        # Update preview and info
        self.preview_widget.set_theme(theme)
        self.info_widget.set_theme(theme)
        
        # Enable apply button
        self.apply_btn.setEnabled(True)
        
        logger.debug(f"Selected theme: {theme.name}")
    
    def _on_apply_theme(self):
        """Handle apply theme button click."""
        if self.selected_theme:
            self.theme_selected.emit(self.selected_theme)
            self.accept()
    
    def get_selected_theme(self) -> Optional[Theme]:
        """Get the selected theme."""
        return self.selected_theme


# Convenience function for showing theme selector
def show_theme_selector(theme_engine: ThemeEngine, 
                       current_theme: Optional[Theme] = None,
                       parent=None) -> Optional[Theme]:
    """Show theme selector dialog and return selected theme.
    
    Args:
        theme_engine: Theme engine instance
        current_theme: Currently active theme
        parent: Parent widget
        
    Returns:
        Selected theme or None if cancelled
    """
    dialog = ThemeSelectorDialog(theme_engine, current_theme, parent)
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_selected_theme()
    
    return None