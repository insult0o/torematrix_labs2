"""Type Icon Manager

Manages icons for type definitions with upload, preview,
and organization capabilities.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QFileDialog, QMessageBox,
    QLineEdit, QComboBox, QGroupBox, QListWidget, QListWidgetItem,
    QSizePolicy, QDialog, QDialogButtonBox, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QMimeData, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QDragEnterEvent, QDropEvent

from torematrix.core.models.types import TypeRegistry, get_type_registry
from torematrix.core.models.types.metadata import (
    TypeIcon, IconType, MetadataManager, get_metadata_manager
)


class IconPreviewWidget(QFrame):
    """Widget for previewing a single icon"""
    
    icon_selected = pyqtSignal(str)  # icon_path
    icon_deleted = pyqtSignal(str)   # icon_path
    
    def __init__(self, icon_path: str, icon_type: IconType = None, parent=None):
        super().__init__(parent)
        
        self.icon_path = icon_path
        self.icon_type = icon_type or IconType.FILE
        self.is_selected = False
        
        self.setup_ui()
        self.apply_styles()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # Icon display
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setMinimumSize(48, 48)
        self.icon_label.setMaximumSize(48, 48)
        layout.addWidget(self.icon_label)
        
        # Icon name
        icon_name = Path(self.icon_path).stem
        self.name_label = QLabel(icon_name)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setFont(QFont("", 8))
        self.name_label.setWordWrap(True)
        layout.addWidget(self.name_label)
        
        # Load icon
        self.load_icon()
    
    def load_icon(self):
        """Load and display icon"""
        try:
            if self.icon_type == IconType.EMOJI:
                # Create pixmap from emoji text
                pixmap = QPixmap(48, 48)
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                painter.setFont(QFont("", 24))
                painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, self.icon_path)
                painter.end()
                self.icon_label.setPixmap(pixmap)
            elif self.icon_type == IconType.FONT_AWESOME:
                # Create text representation
                pixmap = QPixmap(48, 48)
                pixmap.fill(Qt.GlobalColor.white)
                painter = QPainter(pixmap)
                painter.setFont(QFont("Arial", 8))
                painter.setPen(QColor("#333"))
                painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, f"FA\n{self.icon_path}")
                painter.end()
                self.icon_label.setPixmap(pixmap)
            else:
                # Load as image file
                pixmap = QPixmap(self.icon_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.icon_label.setPixmap(scaled_pixmap)
                else:
                    self.create_placeholder_icon()
        except Exception:
            self.create_placeholder_icon()
    
    def create_placeholder_icon(self):
        """Create placeholder icon"""
        pixmap = QPixmap(48, 48)
        pixmap.fill(QColor("#f0f0f0"))
        painter = QPainter(pixmap)
        painter.setPen(QColor("#999"))
        painter.drawRect(0, 0, 47, 47)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "?")
        painter.end()
        self.icon_label.setPixmap(pixmap)
    
    def apply_styles(self):
        """Apply styles"""
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(1)
        self.update_selection_style()
        
        # Enable click detection
        self.setMinimumSize(60, 70)
        self.setMaximumSize(60, 70)
    
    def update_selection_style(self):
        """Update style based on selection"""
        if self.is_selected:
            self.setStyleSheet("""
                QFrame {
                    border: 2px solid #0078d4;
                    background: #e3f2fd;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    border: 1px solid #ccc;
                    background: white;
                }
                QFrame:hover {
                    border-color: #0078d4;
                    background: #f8f8f8;
                }
            """)
    
    def set_selected(self, selected: bool):
        """Set selection state"""
        self.is_selected = selected
        self.update_selection_style()
    
    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.icon_selected.emit(self.icon_path)
        super().mousePressEvent(event)
    
    def contextMenuEvent(self, event):
        """Handle context menu"""
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        
        delete_action = menu.addAction("Delete Icon")
        delete_action.triggered.connect(lambda: self.icon_deleted.emit(self.icon_path))
        
        menu.exec(event.globalPos())


class IconUploadDialog(QDialog):
    """Dialog for uploading new icons"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.uploaded_icons: List[Dict[str, Any]] = []
        
        self.setWindowTitle("Upload Icons")
        self.setModal(True)
        self.resize(500, 400)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "Upload icon files (PNG, JPG, SVG) or enter emoji/Font Awesome icons."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Upload methods
        upload_group = QGroupBox("Upload Methods")
        upload_layout = QVBoxLayout(upload_group)
        
        # File upload
        file_layout = QHBoxLayout()
        self.file_btn = QPushButton("Select Files...")
        self.file_btn.clicked.connect(self.select_files)
        file_layout.addWidget(self.file_btn)
        
        self.file_label = QLabel("No files selected")
        file_layout.addWidget(self.file_label)
        file_layout.addStretch()
        upload_layout.addLayout(file_layout)
        
        # Emoji input
        emoji_layout = QHBoxLayout()
        emoji_layout.addWidget(QLabel("Emoji:"))
        self.emoji_input = QLineEdit()
        self.emoji_input.setPlaceholderText("Enter emoji (e.g., 📝, 🔧, 📊)")
        emoji_layout.addWidget(self.emoji_input)
        
        self.add_emoji_btn = QPushButton("Add")
        self.add_emoji_btn.clicked.connect(self.add_emoji)
        emoji_layout.addWidget(self.add_emoji_btn)
        upload_layout.addLayout(emoji_layout)
        
        # Font Awesome input
        fa_layout = QHBoxLayout()
        fa_layout.addWidget(QLabel("Font Awesome:"))
        self.fa_input = QLineEdit()
        self.fa_input.setPlaceholderText("Enter icon name (e.g., file-text, cog, chart-bar)")
        fa_layout.addWidget(self.fa_input)
        
        self.add_fa_btn = QPushButton("Add")
        self.add_fa_btn.clicked.connect(self.add_font_awesome)
        fa_layout.addWidget(self.add_fa_btn)
        upload_layout.addLayout(fa_layout)
        
        layout.addWidget(upload_group)
        
        # Preview area
        preview_group = QGroupBox("Icons to Upload")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_scroll = QScrollArea()
        self.preview_widget = QWidget()
        self.preview_layout = QGridLayout(self.preview_widget)
        self.preview_scroll.setWidget(self.preview_widget)
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setMinimumHeight(150)
        preview_layout.addWidget(self.preview_scroll)
        
        layout.addWidget(preview_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def select_files(self):
        """Select icon files"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Icon Files",
            "",
            "Image Files (*.png *.jpg *.jpeg *.svg *.gif *.bmp)"
        )
        
        if files:
            for file_path in files:
                self.add_file_icon(file_path)
            
            self.file_label.setText(f"{len(files)} files selected")
    
    def add_file_icon(self, file_path: str):
        """Add file icon to upload list"""
        icon_data = {
            'path': file_path,
            'type': IconType.FILE,
            'name': Path(file_path).stem
        }
        
        self.uploaded_icons.append(icon_data)
        self.update_preview()
    
    def add_emoji(self):
        """Add emoji icon"""
        emoji = self.emoji_input.text().strip()
        if emoji:
            icon_data = {
                'path': emoji,
                'type': IconType.EMOJI,
                'name': f"emoji_{len(self.uploaded_icons)}"
            }
            
            self.uploaded_icons.append(icon_data)
            self.emoji_input.clear()
            self.update_preview()
    
    def add_font_awesome(self):
        """Add Font Awesome icon"""
        fa_name = self.fa_input.text().strip()
        if fa_name:
            icon_data = {
                'path': fa_name,
                'type': IconType.FONT_AWESOME,
                'name': fa_name
            }
            
            self.uploaded_icons.append(icon_data)
            self.fa_input.clear()
            self.update_preview()
    
    def update_preview(self):
        """Update preview area"""
        # Clear existing previews
        for i in reversed(range(self.preview_layout.count())):
            self.preview_layout.itemAt(i).widget().setParent(None)
        
        # Add new previews
        for i, icon_data in enumerate(self.uploaded_icons):
            preview = IconPreviewWidget(icon_data['path'], icon_data['type'])
            preview.icon_deleted.connect(lambda path: self.remove_icon(path))
            
            row = i // 6
            col = i % 6
            self.preview_layout.addWidget(preview, row, col)
    
    def remove_icon(self, icon_path: str):
        """Remove icon from upload list"""
        self.uploaded_icons = [icon for icon in self.uploaded_icons if icon['path'] != icon_path]
        self.update_preview()


class TypeIconManager(QWidget):
    """Manager for type icons with upload and organization"""
    
    # Signals
    icon_selected = pyqtSignal(str, str)  # icon_path, icon_type
    icons_changed = pyqtSignal()
    
    def __init__(self, registry: TypeRegistry = None, parent=None):
        super().__init__(parent)
        
        self.registry = registry or get_type_registry()
        self.metadata_manager = get_metadata_manager()
        
        # State
        self.available_icons: Dict[str, TypeIcon] = {}
        self.selected_icon_path: Optional[str] = None
        self.filter_text: str = ""
        self.filter_type: Optional[IconType] = None
        
        self.setup_ui()
        self.load_icons()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("Icon Manager")
        title.setFont(QFont("", 12, QFont.Weight.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Upload button
        self.upload_btn = QPushButton("📤 Upload Icons")
        self.upload_btn.clicked.connect(self.upload_icons)
        header_layout.addWidget(self.upload_btn)
        
        layout.addLayout(header_layout)
        
        # Filters
        filter_layout = QHBoxLayout()
        
        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search icons...")
        self.search_input.textChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.search_input)
        
        # Type filter
        self.type_filter = QComboBox()
        self.type_filter.addItem("All Types", None)
        self.type_filter.addItem("📁 Files", IconType.FILE)
        self.type_filter.addItem("😀 Emoji", IconType.EMOJI)
        self.type_filter.addItem("🔤 Font Awesome", IconType.FONT_AWESOME)
        self.type_filter.currentDataChanged.connect(self.on_type_filter_changed)
        filter_layout.addWidget(self.type_filter)
        
        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_filters)
        filter_layout.addWidget(clear_btn)
        
        layout.addLayout(filter_layout)
        
        # Icon grid
        self.icon_scroll = QScrollArea()
        self.icon_widget = QWidget()
        self.icon_layout = QGridLayout(self.icon_widget)
        self.icon_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.icon_scroll.setWidget(self.icon_widget)
        self.icon_scroll.setWidgetResizable(True)
        layout.addWidget(self.icon_scroll)
        
        # Selection info
        self.selection_info = QLabel("No icon selected")
        self.selection_info.setStyleSheet("color: #666; font-style: italic; padding: 4px;")
        layout.addWidget(self.selection_info)
    
    def connect_signals(self):
        """Connect signals"""
        pass
    
    def load_icons(self):
        """Load available icons"""
        # Load from metadata manager
        self.available_icons = self.metadata_manager.get_all_icons()
        
        # Add some default icons if none exist
        if not self.available_icons:
            self.create_default_icons()
        
        self.update_icon_display()
    
    def create_default_icons(self):
        """Create default icon set"""
        default_icons = [
            ('📝', IconType.EMOJI, 'document'),
            ('📊', IconType.EMOJI, 'chart'),
            ('🖼️', IconType.EMOJI, 'image'),
            ('📋', IconType.EMOJI, 'list'),
            ('🔧', IconType.EMOJI, 'tool'),
            ('⚙️', IconType.EMOJI, 'settings'),
            ('📄', IconType.EMOJI, 'page'),
            ('🏗️', IconType.EMOJI, 'structure'),
        ]
        
        for icon_path, icon_type, name in default_icons:
            icon = TypeIcon(
                icon_id=f"default_{name}",
                icon_type=icon_type,
                icon_path=icon_path,
                name=name,
                tags=["default"]
            )
            self.metadata_manager.register_icon(icon)
            self.available_icons[icon.icon_id] = icon
    
    def update_icon_display(self):
        """Update icon display grid"""
        # Clear existing icons
        for i in reversed(range(self.icon_layout.count())):
            widget = self.icon_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Filter icons
        filtered_icons = self.get_filtered_icons()
        
        # Add icons to grid
        icons_per_row = 8
        for i, (icon_id, icon) in enumerate(filtered_icons.items()):
            preview = IconPreviewWidget(icon.icon_path, icon.icon_type)
            preview.icon_selected.connect(lambda path, icon=icon: self.select_icon(icon))
            preview.icon_deleted.connect(lambda path, icon_id=icon_id: self.delete_icon(icon_id))
            
            row = i // icons_per_row
            col = i % icons_per_row
            self.icon_layout.addWidget(preview, row, col)
    
    def get_filtered_icons(self) -> Dict[str, TypeIcon]:
        """Get icons matching current filters"""
        filtered = {}
        
        for icon_id, icon in self.available_icons.items():
            # Text filter
            if self.filter_text:
                query = self.filter_text.lower()
                if not any([
                    query in icon.name.lower(),
                    query in icon_id.lower(),
                    any(query in tag.lower() for tag in icon.tags)
                ]):
                    continue
            
            # Type filter
            if self.filter_type and icon.icon_type != self.filter_type:
                continue
            
            filtered[icon_id] = icon
        
        return filtered
    
    def select_icon(self, icon: TypeIcon):
        """Select an icon"""
        self.selected_icon_path = icon.icon_path
        
        # Update selection info
        self.selection_info.setText(f"Selected: {icon.name} ({icon.icon_type.value})")
        
        # Update visual selection
        for i in range(self.icon_layout.count()):
            widget = self.icon_layout.itemAt(i).widget()
            if isinstance(widget, IconPreviewWidget):
                widget.set_selected(widget.icon_path == icon.icon_path)
        
        # Emit signal
        self.icon_selected.emit(icon.icon_path, icon.icon_type.value)
    
    def upload_icons(self):
        """Open upload dialog"""
        dialog = IconUploadDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Process uploaded icons
            for icon_data in dialog.uploaded_icons:
                icon = TypeIcon(
                    icon_id=f"user_{icon_data['name']}_{len(self.available_icons)}",
                    icon_type=icon_data['type'],
                    icon_path=icon_data['path'],
                    name=icon_data['name'],
                    tags=["user", "uploaded"]
                )
                
                self.metadata_manager.register_icon(icon)
                self.available_icons[icon.icon_id] = icon
            
            self.update_icon_display()
            self.icons_changed.emit()
    
    def delete_icon(self, icon_id: str):
        """Delete an icon"""
        if icon_id in self.available_icons:
            icon = self.available_icons[icon_id]
            
            # Confirm deletion
            reply = QMessageBox.question(
                self,
                "Delete Icon",
                f"Are you sure you want to delete icon '{icon.name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.metadata_manager.unregister_icon(icon_id)
                del self.available_icons[icon_id]
                
                # Clear selection if deleted icon was selected
                if self.selected_icon_path == icon.icon_path:
                    self.selected_icon_path = None
                    self.selection_info.setText("No icon selected")
                
                self.update_icon_display()
                self.icons_changed.emit()
    
    def apply_filters(self):
        """Apply current filters"""
        self.filter_text = self.search_input.text().strip()
        self.update_icon_display()
    
    def on_type_filter_changed(self, icon_type):
        """Handle type filter change"""
        self.filter_type = icon_type
        self.update_icon_display()
    
    def clear_filters(self):
        """Clear all filters"""
        self.search_input.clear()
        self.type_filter.setCurrentIndex(0)
        self.filter_text = ""
        self.filter_type = None
        self.update_icon_display()
    
    def get_selected_icon(self) -> Optional[str]:
        """Get currently selected icon path"""
        return self.selected_icon_path
    
    def refresh(self):
        """Refresh icon list"""
        self.load_icons()
