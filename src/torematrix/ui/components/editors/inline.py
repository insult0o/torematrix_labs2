"""Main inline editor widget with double-click activation and basic editing functionality"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QWidget, QLabel,
    QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QEvent
from PyQt6.QtGui import QKeyEvent, QFocusEvent, QMouseEvent, QFont

from .base import BaseEditor, EditorConfig


class InlineEditor(BaseEditor):
    """Main inline editor widget with double-click activation
    
    Features:
    - Double-click activation for quick editing
    - Keyboard shortcuts (F2, Esc, Ctrl+Enter)
    - Visual editing indicators
    - Automatic save/cancel handling
    - Configurable appearance and behavior
    """
    
    def __init__(self, config: Optional[EditorConfig] = None, parent=None):
        super().__init__(config, parent)
        
        # Internal state
        self._edit_widget = None
        self._display_widget = None
        self._control_buttons = None
        self._auto_save_timer = None
        
        # Editing session tracking
        self._edit_start_time = None
        self._original_size = None
        
        self._setup_ui()
        self._setup_auto_save_timer()
    
    def _setup_ui(self):
        """Setup the user interface for inline editing"""
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(2)
        
        # Display widget for view mode
        self._display_widget = QLabel()
        self._display_widget.setWordWrap(True)
        self._display_widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._display_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._display_widget.setStyleSheet("""
            QLabel {
                padding: 4px;
                border: 1px solid transparent;
                border-radius: 3px;
                background-color: transparent;
            }
            QLabel:hover {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
            }
        """)
        
        # Install event filter for double-click detection
        self._display_widget.installEventFilter(self)
        
        # Edit widget for edit mode
        self._edit_widget = QTextEdit()
        self._edit_widget.setMaximumHeight(200)  # Reasonable max height
        self._edit_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._edit_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._edit_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Apply editor styling
        self._edit_widget.setStyleSheet(f"""
            QTextEdit {{
                border: {self.config.focus_border_style};
                border-radius: 3px;
                padding: 4px;
                font-family: {self.config.font_family};
                font-size: {self.config.font_size}px;
                background-color: {self.config.background_color};
                color: {self.config.text_color};
            }}
        """)
        
        # Connect edit widget signals
        self._edit_widget.textChanged.connect(self._on_text_changed)
        self._edit_widget.installEventFilter(self)
        
        # Control buttons
        self._setup_control_buttons()
        
        # Add widgets to layout
        self.main_layout.addWidget(self._display_widget)
        self.main_layout.addWidget(self._edit_widget)
        self.main_layout.addWidget(self._control_buttons)
        
        # Initially show display mode
        self._set_display_mode()
    
    def _setup_control_buttons(self):
        """Setup save/cancel control buttons"""
        self._control_buttons = QWidget()
        button_layout = QHBoxLayout(self._control_buttons)
        button_layout.setContentsMargins(0, 2, 0, 0)
        button_layout.setSpacing(4)
        
        # Save button
        self.save_btn = QPushButton("Save")
        self.save_btn.setFixedSize(60, 24)
        self.save_btn.clicked.connect(lambda: self.finish_editing(save=True))
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QPushButton:pressed {
                background-color: #004578;
            }
        """)
        
        # Cancel button
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedSize(60, 24)
        self.cancel_btn.clicked.connect(lambda: self.finish_editing(save=False))
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #ccc;
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        
        # Shortcut indicators
        shortcut_label = QLabel("F2: Edit | Esc: Cancel | Ctrl+Enter: Save")
        shortcut_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 10px;
                padding: 2px;
            }
        """)
        
        # Layout buttons
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()
        button_layout.addWidget(shortcut_label)
    
    def _setup_auto_save_timer(self):
        """Setup auto-save timer for editing sessions"""
        if self.config.auto_save_enabled:
            self._auto_save_timer = QTimer()
            self._auto_save_timer.setSingleShot(True)
            self._auto_save_timer.timeout.connect(self._perform_auto_save)
    
    def _set_display_mode(self):
        """Switch to display mode (non-editing)"""
        self._edit_widget.hide()
        self._control_buttons.hide()
        self._display_widget.show()
        
        self._is_editing = False
        
        # Update cursor to indicate clickable
        self._display_widget.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def _set_edit_mode(self):
        """Switch to edit mode"""
        self._display_widget.hide()
        self._edit_widget.show()
        self._control_buttons.show()
        
        self._is_editing = True
        
        # Focus and select content if configured
        self._edit_widget.setFocus()
        
        if self.config.auto_select:
            self._edit_widget.selectAll()
        
        # Emit editing started signal
        self.editing_started.emit()
        
        # Track edit session start time
        import time
        self._edit_start_time = time.time()
        
        # Start auto-save timer if enabled
        if self._auto_save_timer and self.config.auto_save_enabled:
            self._auto_save_timer.start(self.config.auto_save_interval * 1000)
    
    def eventFilter(self, obj, event):
        """Handle events for inline editing activation and control"""
        if obj == self._display_widget:
            if event.type() == QEvent.Type.MouseButtonDblClick:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._activate_editing()
                    return True
        
        elif obj == self._edit_widget:
            if event.type() == QEvent.Type.KeyPress:
                return self._handle_key_press(event)
            elif event.type() == QEvent.Type.FocusOut:
                # Auto-save on focus loss if configured
                if self.config.auto_save_enabled:
                    self._perform_auto_save()
        
        return super().eventFilter(obj, event)
    
    def _handle_key_press(self, event: QKeyEvent) -> bool:
        """Handle keyboard shortcuts in edit mode
        
        Args:
            event: Key press event
            
        Returns:
            True if event was handled
        """
        key = event.key()
        modifiers = event.modifiers()
        
        # F2: Toggle editing (if in display mode)
        if key == Qt.Key.Key_F2:
            if not self._is_editing:
                self._activate_editing()
            return True
        
        # Escape: Cancel editing
        elif key == Qt.Key.Key_Escape and self.config.escape_cancels:
            self.finish_editing(save=False)
            return True
        
        # Ctrl+Enter: Save and finish
        elif (key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter) and \
             modifiers & Qt.KeyboardModifier.ControlModifier:
            self.finish_editing(save=True)
            return True
        
        # Enter: Commit if configured
        elif (key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter) and \
             self.config.enter_commits and \
             not (modifiers & Qt.KeyboardModifier.ShiftModifier):
            self.finish_editing(save=True)
            return True
        
        # Tab handling
        elif key == Qt.Key.Key_Tab:
            if self.config.tab_behavior == "commit":
                self.finish_editing(save=True)
                return True
            elif self.config.tab_behavior == "next_field":
                # Let the tab move to next widget
                return False
            # For "indent", let the text edit handle it
        
        # Emit key pressed signal
        self.key_pressed.emit(key)
        
        return False  # Let the text edit handle other keys
    
    def _activate_editing(self):
        """Activate editing mode"""
        if not self._is_readonly and not self._is_editing:
            self._set_edit_mode()
    
    def _on_text_changed(self):
        """Handle text changes in edit widget"""
        if self._is_editing:
            current_content = self._edit_widget.toPlainText()
            
            # Update dirty state
            is_dirty = current_content != self._original_content
            if is_dirty != self._is_dirty:
                self._is_dirty = is_dirty
                self.dirty_changed.emit(is_dirty)
            
            # Emit content changed signal
            self.content_changed.emit(current_content)
            
            # Restart auto-save timer
            if self._auto_save_timer and self.config.auto_save_enabled:
                self._auto_save_timer.start(self.config.auto_save_interval * 1000)
    
    def _perform_auto_save(self):
        """Perform automatic save"""
        if self._is_editing and self._is_dirty:
            # Save current content
            content = self._edit_widget.toPlainText()
            self._original_content = content
            self._display_widget.setText(content)
            
            # Update state
            self._is_dirty = False
            self.dirty_changed.emit(False)
            
            # Note: Don't finish editing, just save in background
    
    # Implementation of abstract methods from BaseEditor
    
    def start_editing(self, content: str) -> None:
        """Start editing with given content
        
        Args:
            content: Initial content to edit
        """
        self._original_content = content
        self._current_content = content
        
        # Set content in both widgets
        self._display_widget.setText(content)
        self._edit_widget.setPlainText(content)
        
        # Activate editing mode
        self._activate_editing()
    
    def finish_editing(self, save: bool = True) -> Optional[str]:
        """Finish editing and optionally save changes
        
        Args:
            save: Whether to save changes
            
        Returns:
            Final content if saved, None if cancelled
        """
        if not self._is_editing:
            return None
        
        # Stop auto-save timer
        if self._auto_save_timer:
            self._auto_save_timer.stop()
        
        final_content = None
        
        if save:
            # Get current content
            content = self._edit_widget.toPlainText()
            
            # Validate content
            if self.validate_content(content):
                # Save the content
                self._original_content = content
                self._current_content = content
                self._display_widget.setText(content)
                final_content = content
                
                # Update state
                self._is_dirty = False
                self.dirty_changed.emit(False)
                
                # Add to undo stack
                self._push_undo_state(content)
                
            else:
                # Validation failed, emit signal with messages
                error_messages = self.get_validation_messages()
                if error_messages:
                    self.validation_failed.emit("; ".join(error_messages))
                else:
                    self.validation_failed.emit("Content validation failed")
                return None
        else:
            # Cancel - revert to original content
            self._edit_widget.setPlainText(self._original_content)
            self._current_content = self._original_content
            
            # Update state
            self._is_dirty = False
            self.dirty_changed.emit(False)
        
        # Switch to display mode
        self._set_display_mode()
        
        # Emit editing finished signal
        self.editing_finished.emit(save)
        
        return final_content
    
    def get_content(self) -> str:
        """Get current editor content
        
        Returns:
            Current content as string
        """
        if self._is_editing:
            return self._edit_widget.toPlainText()
        else:
            return self._current_content
    
    def set_content(self, content: str) -> None:
        """Set editor content
        
        Args:
            content: Content to set
        """
        self._current_content = content
        self._original_content = content
        
        # Update both widgets
        self._display_widget.setText(content)
        self._edit_widget.setPlainText(content)
        
        # Reset dirty state
        self._is_dirty = False
        self.dirty_changed.emit(False)
    
    def is_modified(self) -> bool:
        """Check if content has been modified
        
        Returns:
            True if content is modified
        """
        if self._is_editing:
            return self._edit_widget.toPlainText() != self._original_content
        else:
            return self._current_content != self._original_content
    
    # Additional methods specific to InlineEditor
    
    def set_placeholder_text(self, text: str):
        """Set placeholder text for edit widget
        
        Args:
            text: Placeholder text to display
        """
        self._edit_widget.setPlaceholderText(text)
        self.config.placeholder_text = text
    
    def set_max_height(self, height: int):
        """Set maximum height for edit widget
        
        Args:
            height: Maximum height in pixels
        """
        self._edit_widget.setMaximumHeight(height)
    
    def get_edit_session_info(self) -> Dict[str, Any]:
        """Get information about current edit session
        
        Returns:
            Dictionary with session information
        """
        info = {
            'is_editing': self._is_editing,
            'is_dirty': self._is_dirty,
            'content_length': len(self.get_content()),
            'original_length': len(self._original_content),
            'edit_start_time': self._edit_start_time
        }
        
        if self._edit_start_time:
            import time
            info['edit_duration'] = time.time() - self._edit_start_time
        
        return info
    
    def force_finish_editing(self, save: bool = True):
        """Force finish editing (useful for cleanup)
        
        Args:
            save: Whether to save changes
        """
        if self._is_editing:
            self.finish_editing(save)
    
    def select_all(self):
        """Select all content in editor"""
        if self._is_editing:
            self._edit_widget.selectAll()
    
    def clear(self):
        """Clear editor content"""
        self.set_content("")
    
    def resize_to_content(self):
        """Resize edit widget to fit content"""
        if self._is_editing:
            document = self._edit_widget.document()
            height = int(document.size().height()) + 10  # Add padding
            max_height = self._edit_widget.maximumHeight()
            
            # Set height within reasonable bounds
            new_height = min(max(height, 50), max_height)
            self._edit_widget.setFixedHeight(new_height)
    
    def set_font(self, font: QFont):
        """Set font for editor
        
        Args:
            font: Font to apply
        """
        self._edit_widget.setFont(font)
        self._display_widget.setFont(font)
    
    def set_read_only(self, readonly: bool):
        """Set read-only mode
        
        Args:
            readonly: Whether to enable read-only mode
        """
        super().set_readonly(readonly)
        self._edit_widget.setReadOnly(readonly)
        
        if readonly and self._is_editing:
            # Cancel editing if switching to readonly
            self.finish_editing(save=False)
    
    def get_cursor_position(self) -> int:
        """Get current cursor position in edit widget
        
        Returns:
            Cursor position (character index)
        """
        if self._is_editing:
            return self._edit_widget.textCursor().position()
        return 0
    
    def set_cursor_position(self, position: int):
        """Set cursor position in edit widget
        
        Args:
            position: Character position to set cursor to
        """
        if self._is_editing:
            cursor = self._edit_widget.textCursor()
            cursor.setPosition(min(position, len(self._edit_widget.toPlainText())))
            self._edit_widget.setTextCursor(cursor)