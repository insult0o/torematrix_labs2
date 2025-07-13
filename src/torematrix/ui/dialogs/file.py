"""File selection dialog implementation.

Provides file and directory selection dialogs with filtering,
preview capabilities, and recent files support.
"""

from typing import Optional, List, Dict, Tuple, Callable
from pathlib import Path
from dataclasses import dataclass
import mimetypes
import logging

from PySide6.QtWidgets import (
    QFileDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QSplitter,
    QTextEdit, QComboBox, QCheckBox, QWidget, QGroupBox
)
from PySide6.QtCore import Qt, Signal, QFileInfo, QDir
from PySide6.QtGui import QIcon, QPixmap

from .base import BaseDialog, DialogResult, DialogButton
from ...core.events import Event, EventType

logger = logging.getLogger(__name__)


@dataclass
class FileFilter:
    """File filter configuration."""
    name: str
    extensions: List[str]
    mime_types: Optional[List[str]] = None
    
    def to_qt_filter(self) -> str:
        """Convert to Qt filter string.
        
        Returns:
            Qt-compatible filter string
        """
        ext_patterns = [f"*.{ext}" for ext in self.extensions]
        return f"{self.name} ({' '.join(ext_patterns)})"


class FileDialog(BaseDialog):
    """Enhanced file selection dialog.
    
    Features:
    - Multiple file filters
    - File preview
    - Recent files list
    - Quick access locations
    - Validation callbacks
    """
    
    # Signals
    file_selected = Signal(str)  # file path
    files_selected = Signal(list)  # file paths
    filter_changed = Signal(FileFilter)
    
    # Common filters
    FILTER_ALL = FileFilter("All Files", ["*"])
    FILTER_DOCUMENTS = FileFilter(
        "Documents", 
        ["pdf", "doc", "docx", "odt", "txt", "rtf"],
        ["application/pdf", "application/msword", "text/plain"]
    )
    FILTER_IMAGES = FileFilter(
        "Images",
        ["png", "jpg", "jpeg", "gif", "bmp", "svg"],
        ["image/*"]
    )
    FILTER_DATA = FileFilter(
        "Data Files",
        ["json", "xml", "csv", "xlsx", "xls"],
        ["application/json", "application/xml", "text/csv"]
    )
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "Select File",
        mode: str = "open",  # open, save, directory
        filters: Optional[List[FileFilter]] = None,
        default_filter: Optional[FileFilter] = None,
        multiple: bool = False,
        show_preview: bool = True,
        show_recent: bool = True,
        initial_dir: Optional[str] = None,
        validation_callback: Optional[Callable[[str], bool]] = None,
        **kwargs
    ):
        """Initialize file dialog.
        
        Args:
            parent: Parent widget
            title: Dialog title
            mode: Selection mode (open, save, directory)
            filters: List of file filters
            default_filter: Default filter to use
            multiple: Allow multiple selection
            show_preview: Show file preview panel
            show_recent: Show recent files panel
            initial_dir: Initial directory
            validation_callback: File validation function
            **kwargs: Additional BaseDialog arguments
        """
        super().__init__(parent, title, **kwargs)
        
        self.mode = mode
        self.filters = filters or [self.FILTER_ALL]
        self.default_filter = default_filter or self.filters[0]
        self.multiple = multiple
        self.show_preview = show_preview
        self.show_recent = show_recent
        self.initial_dir = initial_dir or str(Path.home())
        self.validation_callback = validation_callback
        
        self._selected_files: List[str] = []
        self._recent_files: List[str] = []
        
        self._setup_file_ui()
        self._load_recent_files()
    
    def _setup_file_ui(self) -> None:
        """Setup the file dialog UI."""
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.content_layout.addWidget(splitter)
        
        # Left panel - file browser and options
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # File browser section
        browser_group = QGroupBox("Browse")
        browser_layout = QVBoxLayout(browser_group)
        
        # Current directory label
        self.dir_label = QLabel(self.initial_dir)
        self.dir_label.setWordWrap(True)
        browser_layout.addWidget(self.dir_label)
        
        # Browse button
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._show_native_dialog)
        browser_layout.addWidget(self.browse_button)
        
        # Filter combo
        if len(self.filters) > 1:
            filter_layout = QHBoxLayout()
            filter_layout.addWidget(QLabel("Filter:"))
            self.filter_combo = QComboBox()
            for filter_obj in self.filters:
                self.filter_combo.addItem(filter_obj.name, filter_obj)
            self.filter_combo.setCurrentText(self.default_filter.name)
            self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
            filter_layout.addWidget(self.filter_combo, 1)
            browser_layout.addLayout(filter_layout)
        
        # Options
        if self.mode == "open" and self.multiple:
            self.multiple_check = QCheckBox("Select multiple files")
            self.multiple_check.setChecked(True)
            browser_layout.addWidget(self.multiple_check)
        
        left_layout.addWidget(browser_group)
        
        # Recent files section
        if self.show_recent and self.mode != "directory":
            recent_group = QGroupBox("Recent Files")
            recent_layout = QVBoxLayout(recent_group)
            
            self.recent_list = QListWidget()
            self.recent_list.itemDoubleClicked.connect(self._on_recent_selected)
            recent_layout.addWidget(self.recent_list)
            
            left_layout.addWidget(recent_group, 1)
        
        splitter.addWidget(left_panel)
        
        # Right panel - preview
        if self.show_preview and self.mode != "directory":
            preview_group = QGroupBox("Preview")
            preview_layout = QVBoxLayout(preview_group)
            
            self.preview_widget = QTextEdit()
            self.preview_widget.setReadOnly(True)
            preview_layout.addWidget(self.preview_widget)
            
            splitter.addWidget(preview_group)
            splitter.setSizes([400, 300])
        
        # Selected files display
        if self.multiple:
            selected_group = QGroupBox("Selected Files")
            selected_layout = QVBoxLayout(selected_group)
            
            self.selected_list = QListWidget()
            selected_layout.addWidget(self.selected_list)
            
            # Remove button
            self.remove_button = QPushButton("Remove Selected")
            self.remove_button.clicked.connect(self._remove_selected)
            selected_layout.addWidget(self.remove_button)
            
            self.content_layout.addWidget(selected_group)
        
        # Add buttons
        self._add_dialog_buttons()
    
    def _add_dialog_buttons(self) -> None:
        """Add appropriate dialog buttons based on mode."""
        if self.mode == "save":
            self.add_button(DialogButton("Save", DialogResult.OK, is_default=True))
            self.add_button(DialogButton("Cancel", DialogResult.CANCEL))
        else:
            self.add_button(DialogButton("Select", DialogResult.OK, is_default=True))
            self.add_button(DialogButton("Cancel", DialogResult.CANCEL))
    
    def _show_native_dialog(self) -> None:
        """Show native file dialog."""
        dialog = QFileDialog(self)
        dialog.setDirectory(self.initial_dir)
        
        # Set mode
        if self.mode == "open":
            if self.multiple:
                dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
            else:
                dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        elif self.mode == "save":
            dialog.setFileMode(QFileDialog.FileMode.AnyFile)
            dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        elif self.mode == "directory":
            dialog.setFileMode(QFileDialog.FileMode.Directory)
        
        # Set filters
        if self.mode != "directory" and self.filters:
            filter_strings = [f.to_qt_filter() for f in self.filters]
            filter_strings.append("All Files (*)")
            dialog.setNameFilters(filter_strings)
            dialog.selectNameFilter(self.default_filter.to_qt_filter())
        
        # Show dialog
        if dialog.exec():
            selected = dialog.selectedFiles()
            if selected:
                if self.multiple:
                    self._add_files(selected)
                else:
                    self._select_file(selected[0])
    
    def _select_file(self, file_path: str) -> None:
        """Select a single file.
        
        Args:
            file_path: Path to file
        """
        # Validate if callback provided
        if self.validation_callback and not self.validation_callback(file_path):
            logger.warning(f"File validation failed: {file_path}")
            return
        
        self._selected_files = [file_path]
        self.dir_label.setText(file_path)
        
        # Update preview
        if self.show_preview:
            self._update_preview(file_path)
        
        # Add to recent
        self._add_to_recent(file_path)
        
        self.file_selected.emit(file_path)
    
    def _add_files(self, file_paths: List[str]) -> None:
        """Add multiple files to selection.
        
        Args:
            file_paths: List of file paths
        """
        for path in file_paths:
            if self.validation_callback and not self.validation_callback(path):
                logger.warning(f"File validation failed: {path}")
                continue
                
            if path not in self._selected_files:
                self._selected_files.append(path)
                if hasattr(self, 'selected_list'):
                    item = QListWidgetItem(Path(path).name)
                    item.setData(Qt.ItemDataRole.UserRole, path)
                    self.selected_list.addItem(item)
        
        self.files_selected.emit(self._selected_files)
    
    def _remove_selected(self) -> None:
        """Remove selected files from list."""
        if hasattr(self, 'selected_list'):
            for item in self.selected_list.selectedItems():
                path = item.data(Qt.ItemDataRole.UserRole)
                if path in self._selected_files:
                    self._selected_files.remove(path)
                self.selected_list.takeItem(self.selected_list.row(item))
    
    def _update_preview(self, file_path: str) -> None:
        """Update file preview.
        
        Args:
            file_path: Path to preview
        """
        try:
            path = Path(file_path)
            if not path.exists():
                self.preview_widget.setText("File not found")
                return
            
            # Get file info
            size = path.stat().st_size
            mime_type, _ = mimetypes.guess_type(str(path))
            
            # Show preview based on type
            if mime_type and mime_type.startswith('text/'):
                # Text file - show content
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read(1024)  # First 1KB
                        if len(content) < path.stat().st_size:
                            content += "\n\n... (truncated)"
                        self.preview_widget.setPlainText(content)
                except Exception as e:
                    self.preview_widget.setText(f"Error reading file: {e}")
            
            elif mime_type and mime_type.startswith('image/'):
                # Image file - show thumbnail
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        300, 300, 
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.preview_widget.setHtml(
                        f'<img src="{path}" width="{scaled.width()}" height="{scaled.height()}">'
                    )
                else:
                    self.preview_widget.setText("Cannot load image")
            
            else:
                # Other files - show info
                info_text = f"""File: {path.name}
Type: {mime_type or 'Unknown'}
Size: {self._format_size(size)}
Modified: {path.stat().st_mtime}
                """
                self.preview_widget.setPlainText(info_text)
                
        except Exception as e:
            logger.error(f"Error updating preview: {e}")
            self.preview_widget.setText(f"Preview error: {e}")
    
    def _format_size(self, size: int) -> str:
        """Format file size for display.
        
        Args:
            size: Size in bytes
            
        Returns:
            Formatted size string
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def _on_filter_changed(self, index: int) -> None:
        """Handle filter change.
        
        Args:
            index: Selected filter index
        """
        if hasattr(self, 'filter_combo'):
            filter_obj = self.filter_combo.itemData(index)
            if filter_obj:
                self.default_filter = filter_obj
                self.filter_changed.emit(filter_obj)
    
    def _on_recent_selected(self, item: QListWidgetItem) -> None:
        """Handle recent file selection.
        
        Args:
            item: Selected list item
        """
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path and Path(file_path).exists():
            self._select_file(file_path)
    
    def _load_recent_files(self) -> None:
        """Load recent files from settings."""
        # TODO: Load from state manager or settings
        if hasattr(self, 'recent_list'):
            # Add some example recent files
            for i, path in enumerate(self._recent_files[:10]):
                if Path(path).exists():
                    item = QListWidgetItem(Path(path).name)
                    item.setData(Qt.ItemDataRole.UserRole, path)
                    item.setToolTip(path)
                    self.recent_list.addItem(item)
    
    def _add_to_recent(self, file_path: str) -> None:
        """Add file to recent list.
        
        Args:
            file_path: File to add
        """
        if file_path not in self._recent_files:
            self._recent_files.insert(0, file_path)
            self._recent_files = self._recent_files[:20]  # Keep last 20
            
            # TODO: Save to settings
            if self.event_bus:
                self.event_bus.emit(Event(
                    type=EventType.UI_STATE_CHANGED,
                    data={
                        'action': 'recent_file_added',
                        'file': file_path
                    }
                ))
    
    def get_selected_file(self) -> Optional[str]:
        """Get selected file path.
        
        Returns:
            Selected file path or None
        """
        return self._selected_files[0] if self._selected_files else None
    
    def get_selected_files(self) -> List[str]:
        """Get all selected file paths.
        
        Returns:
            List of selected file paths
        """
        return self._selected_files.copy()
    
    def set_initial_directory(self, directory: str) -> None:
        """Set initial directory.
        
        Args:
            directory: Directory path
        """
        if Path(directory).is_dir():
            self.initial_dir = directory
            self.dir_label.setText(directory)


def show_open_file_dialog(
    parent: Optional[QWidget] = None,
    title: str = "Open File",
    filters: Optional[List[FileFilter]] = None,
    **kwargs
) -> Optional[str]:
    """Show file open dialog and return selected file.
    
    Args:
        parent: Parent widget
        title: Dialog title
        filters: File filters
        **kwargs: Additional FileDialog arguments
        
    Returns:
        Selected file path or None
    """
    dialog = FileDialog(parent, title, mode="open", filters=filters, **kwargs)
    if dialog.exec() == QFileDialog.DialogCode.Accepted:
        return dialog.get_selected_file()
    return None


def show_save_file_dialog(
    parent: Optional[QWidget] = None,
    title: str = "Save File",
    filters: Optional[List[FileFilter]] = None,
    **kwargs
) -> Optional[str]:
    """Show file save dialog and return selected file.
    
    Args:
        parent: Parent widget
        title: Dialog title
        filters: File filters
        **kwargs: Additional FileDialog arguments
        
    Returns:
        Selected file path or None
    """
    dialog = FileDialog(parent, title, mode="save", filters=filters, **kwargs)
    if dialog.exec() == QFileDialog.DialogCode.Accepted:
        return dialog.get_selected_file()
    return None