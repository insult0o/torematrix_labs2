"""Text property editors for string and multiline text input"""

from typing import Any, Optional, List
from PyQt6.QtWidgets import (
    QLineEdit, QTextEdit, QCompleter, QVBoxLayout, 
    QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QValidator, QTextDocument, QFont

from .base import (
    BasePropertyEditor, EditorConfiguration, PropertyEditorMixin, 
    EditorValidationMixin, PropertyEditorState
)
from ..events import PropertyNotificationCenter


class TextPropertyEditor(BasePropertyEditor, PropertyEditorMixin, EditorValidationMixin):
    """Single-line text property editor"""
    
    def __init__(self, config: EditorConfiguration, 
                 notification_center: Optional[PropertyNotificationCenter] = None,
                 parent=None):
        super().__init__(config, notification_center, parent)
        self._completion_enabled = False
        self._completion_source: Optional[List[str]] = None
        self._completer: Optional[QCompleter] = None
        
    def _setup_ui(self) -> None:
        """Setup the text editor UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Create text input
        self._text_edit = QLineEdit()
        self._text_edit.setPlaceholderText(f"Enter {self._config.property_name}...")
        
        # Apply common styling
        self.setup_common_styling(self._text_edit)
        
        # Configure based on metadata
        if self._config.metadata:
            if self._config.metadata.description:
                self._text_edit.setToolTip(self._config.metadata.description)
        
        # Configure validation rules
        self._setup_validation()
        
        layout.addWidget(self._text_edit)
        
        # Connect signals
        self._text_edit.textChanged.connect(self._on_text_changed)
        self._text_edit.editingFinished.connect(self._on_editing_finished)
        self._text_edit.returnPressed.connect(self._on_return_pressed)
    
    def _setup_validation(self) -> None:
        """Setup validation for text input"""
        if not self._config.metadata or not self._config.metadata.validation_rules:
            return
        
        for rule in self._config.metadata.validation_rules:
            if rule.startswith('length:'):
                # Extract length constraints
                try:
                    length_spec = rule[7:]  # Remove 'length:' prefix
                    if '-' in length_spec:
                        min_len, max_len = map(int, length_spec.split('-'))
                        self._text_edit.setMaxLength(max_len)
                    else:
                        max_len = int(length_spec)
                        self._text_edit.setMaxLength(max_len)
                except ValueError:
                    pass
            
            elif rule.startswith('pattern:'):
                # Setup regex validator
                try:
                    import re
                    pattern = rule[8:]  # Remove 'pattern:' prefix
                    # Could implement QRegularExpressionValidator here
                except ImportError:
                    pass
    
    def _get_editor_value(self) -> str:
        """Get current text value"""
        return self._text_edit.text()
    
    def _set_editor_value(self, value: Any) -> None:
        """Set text value"""
        text_value = str(value) if value is not None else ""
        self._text_edit.setText(text_value)
    
    def _validate_value(self, value: Any) -> tuple[bool, Optional[str]]:
        """Validate text value"""
        if not isinstance(value, str):
            return False, "Value must be a string"
        
        # Check metadata validation rules
        if self._config.metadata and self._config.metadata.validation_rules:
            for rule in self._config.metadata.validation_rules:
                if rule == 'required':
                    is_valid, error = self.validate_required(value)
                    if not is_valid:
                        return is_valid, error
                
                elif rule.startswith('length:'):
                    try:
                        length_spec = rule[7:]
                        if '-' in length_spec:
                            min_len, max_len = map(int, length_spec.split('-'))
                            is_valid, error = self.validate_length(value, min_len, max_len)
                        else:
                            max_len = int(length_spec)
                            is_valid, error = self.validate_length(value, None, max_len)
                        
                        if not is_valid:
                            return is_valid, error
                    except ValueError:
                        pass
                
                elif rule.startswith('pattern:'):
                    pattern = rule[8:]
                    is_valid, error = self.validate_pattern(value, pattern)
                    if not is_valid:
                        return is_valid, error
        
        return True, None
    
    def _on_text_changed(self) -> None:
        """Handle text change"""
        self._on_value_changed()
        
        # Update validation styling
        current_value = self._get_editor_value()
        is_valid, _ = self._validate_value(current_value)
        self.setup_validation_styling(self._text_edit, not is_valid)
    
    def _on_editing_finished(self) -> None:
        """Handle editing finished"""
        if self.get_state() == PropertyEditorState.EDITING:
            self.commit_changes()
    
    def _on_return_pressed(self) -> None:
        """Handle return key press"""
        self.commit_changes()
    
    def _on_state_changed(self, old_state: PropertyEditorState, new_state: PropertyEditorState) -> None:
        """Handle state changes"""
        if new_state == PropertyEditorState.ERROR:
            self.setup_validation_styling(self._text_edit, True)
            if self._validation_error:
                self._text_edit.setToolTip(self.create_error_tooltip(self._validation_error))
        else:
            self.setup_validation_styling(self._text_edit, False)
            self._text_edit.setToolTip(self._config.metadata.description if self._config.metadata else "")
    
    def set_completion_source(self, completions: List[str]) -> None:
        """Set completion source for auto-completion"""
        self._completion_source = completions
        self._completion_enabled = True
        
        if self._completer:
            self._completer.deleteLater()
        
        self._completer = QCompleter(completions)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._text_edit.setCompleter(self._completer)
    
    def clear_completion(self) -> None:
        """Clear auto-completion"""
        self._completion_enabled = False
        self._completion_source = None
        if self._completer:
            self._completer.deleteLater()
            self._completer = None
        self._text_edit.setCompleter(None)
    
    def select_all(self) -> None:
        """Select all text"""
        self._text_edit.selectAll()
    
    def get_line_edit(self) -> QLineEdit:
        """Get the underlying QLineEdit widget"""
        return self._text_edit


class MultilineTextEditor(BasePropertyEditor, PropertyEditorMixin, EditorValidationMixin):
    """Multiline text property editor"""
    
    def __init__(self, config: EditorConfiguration,
                 notification_center: Optional[PropertyNotificationCenter] = None,
                 parent=None):
        super().__init__(config, notification_center, parent)
        self._word_wrap = True
        self._max_lines = 10
        self._auto_resize = True
        self._change_timer = QTimer()
        self._change_timer.setSingleShot(True)
        self._change_timer.timeout.connect(self._on_delayed_change)
    
    def _setup_ui(self) -> None:
        """Setup the multiline text editor UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Create text edit
        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText(f"Enter {self._config.property_name}...")
        
        # Configure text edit
        self._text_edit.setWordWrapMode(QTextDocument.WrapMode.WordWrap if self._word_wrap else QTextDocument.WrapMode.NoWrap)
        self._text_edit.setMaximumHeight(self._max_lines * 20)  # Approximate line height
        
        # Apply common styling
        self.setup_common_styling(self._text_edit)
        
        # Configure based on metadata
        if self._config.metadata:
            if self._config.metadata.description:
                self._text_edit.setToolTip(self._config.metadata.description)
        
        layout.addWidget(self._text_edit)
        
        # Add control buttons for multiline editor
        if not self._config.compact_mode:
            self._create_control_buttons(layout)
        
        # Connect signals
        self._text_edit.textChanged.connect(self._on_text_changed)
        self._text_edit.focusOutEvent = self._on_focus_out
    
    def _create_control_buttons(self, layout: QVBoxLayout) -> None:
        """Create control buttons for multiline editor"""
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 2, 0, 0)
        button_layout.setSpacing(4)
        
        # Word wrap toggle
        self._wrap_button = QPushButton("Wrap")
        self._wrap_button.setCheckable(True)
        self._wrap_button.setChecked(self._word_wrap)
        self._wrap_button.setMaximumWidth(60)
        self._wrap_button.clicked.connect(self._toggle_word_wrap)
        
        # Clear button
        self._clear_button = QPushButton("Clear")
        self._clear_button.setMaximumWidth(60)
        self._clear_button.clicked.connect(self._clear_text)
        
        button_layout.addWidget(self._wrap_button)
        button_layout.addWidget(self._clear_button)
        button_layout.addStretch()
        
        # Character count label
        self._char_count_label = QLabel("0 chars")
        self._char_count_label.setStyleSheet("color: #666; font-size: 9px;")
        button_layout.addWidget(self._char_count_label)
        
        layout.addWidget(button_frame)
    
    def _get_editor_value(self) -> str:
        """Get current text value"""
        return self._text_edit.toPlainText()
    
    def _set_editor_value(self, value: Any) -> None:
        """Set text value"""
        text_value = str(value) if value is not None else ""
        self._text_edit.setPlainText(text_value)
        self._update_char_count()
    
    def _validate_value(self, value: Any) -> tuple[bool, Optional[str]]:
        """Validate text value"""
        if not isinstance(value, str):
            return False, "Value must be a string"
        
        # Check metadata validation rules
        if self._config.metadata and self._config.metadata.validation_rules:
            for rule in self._config.metadata.validation_rules:
                if rule == 'required':
                    is_valid, error = self.validate_required(value.strip())
                    if not is_valid:
                        return is_valid, error
                
                elif rule.startswith('length:'):
                    try:
                        length_spec = rule[7:]
                        if '-' in length_spec:
                            min_len, max_len = map(int, length_spec.split('-'))
                            is_valid, error = self.validate_length(value, min_len, max_len)
                        else:
                            max_len = int(length_spec)
                            is_valid, error = self.validate_length(value, None, max_len)
                        
                        if not is_valid:
                            return is_valid, error
                    except ValueError:
                        pass
        
        return True, None
    
    def _on_text_changed(self) -> None:
        """Handle text change with delay"""
        # Use timer to avoid too frequent updates
        self._change_timer.stop()
        self._change_timer.start(300)  # 300ms delay
        
        self._update_char_count()
        
        # Auto-resize if enabled
        if self._auto_resize:
            self._auto_resize_height()
    
    def _on_delayed_change(self) -> None:
        """Handle delayed text change"""
        self._on_value_changed()
        
        # Update validation styling
        current_value = self._get_editor_value()
        is_valid, _ = self._validate_value(current_value)
        self.setup_validation_styling(self._text_edit, not is_valid)
    
    def _on_focus_out(self, event) -> None:
        """Handle focus out event"""
        # Call original focus out handler
        QTextEdit.focusOutEvent(self._text_edit, event)
        
        # Commit changes on focus out
        if self.get_state() == PropertyEditorState.EDITING:
            self.commit_changes()
    
    def _toggle_word_wrap(self) -> None:
        """Toggle word wrap mode"""
        self._word_wrap = not self._word_wrap
        wrap_mode = QTextDocument.WrapMode.WordWrap if self._word_wrap else QTextDocument.WrapMode.NoWrap
        self._text_edit.setWordWrapMode(wrap_mode)
        self._wrap_button.setChecked(self._word_wrap)
    
    def _clear_text(self) -> None:
        """Clear all text"""
        self._text_edit.clear()
    
    def _update_char_count(self) -> None:
        """Update character count display"""
        if hasattr(self, '_char_count_label'):
            char_count = len(self._text_edit.toPlainText())
            self._char_count_label.setText(f"{char_count} chars")
    
    def _auto_resize_height(self) -> None:
        """Auto-resize height based on content"""
        if not self._auto_resize:
            return
        
        document = self._text_edit.document()
        height = document.size().height()
        
        # Constrain to max lines
        max_height = self._max_lines * 20
        new_height = min(int(height) + 10, max_height)  # +10 for padding
        new_height = max(new_height, 60)  # Minimum height
        
        self._text_edit.setMaximumHeight(new_height)
        self._text_edit.setMinimumHeight(min(new_height, 60))
    
    def set_word_wrap(self, enabled: bool) -> None:
        """Set word wrap mode"""
        self._word_wrap = enabled
        wrap_mode = QTextDocument.WrapMode.WordWrap if enabled else QTextDocument.WrapMode.NoWrap
        self._text_edit.setWordWrapMode(wrap_mode)
        if hasattr(self, '_wrap_button'):
            self._wrap_button.setChecked(enabled)
    
    def set_max_lines(self, max_lines: int) -> None:
        """Set maximum number of visible lines"""
        self._max_lines = max_lines
        max_height = max_lines * 20
        self._text_edit.setMaximumHeight(max_height)
    
    def set_auto_resize(self, enabled: bool) -> None:
        """Set auto-resize mode"""
        self._auto_resize = enabled
        if enabled:
            self._auto_resize_height()
    
    def get_text_edit(self) -> QTextEdit:
        """Get the underlying QTextEdit widget"""
        return self._text_edit
    
    def insert_text(self, text: str) -> None:
        """Insert text at current cursor position"""
        cursor = self._text_edit.textCursor()
        cursor.insertText(text)
    
    def select_all(self) -> None:
        """Select all text"""
        self._text_edit.selectAll()
    
    def get_selected_text(self) -> str:
        """Get currently selected text"""
        return self._text_edit.textCursor().selectedText()


class RichTextEditor(MultilineTextEditor):
    """Rich text editor with formatting capabilities"""
    
    def __init__(self, config: EditorConfiguration,
                 notification_center: Optional[PropertyNotificationCenter] = None,
                 parent=None):
        super().__init__(config, notification_center, parent)
        self._formatting_enabled = True
    
    def _setup_ui(self) -> None:
        """Setup rich text editor UI"""
        super()._setup_ui()
        
        # Enable rich text
        self._text_edit.setAcceptRichText(True)
        
        # Add formatting toolbar if not in compact mode
        if not self._config.compact_mode and self._formatting_enabled:
            self._create_formatting_toolbar()
    
    def _create_formatting_toolbar(self) -> None:
        """Create formatting toolbar"""
        toolbar_frame = QFrame()
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(0, 2, 0, 2)
        toolbar_layout.setSpacing(2)
        
        # Bold button
        self._bold_button = QPushButton("B")
        self._bold_button.setCheckable(True)
        self._bold_button.setMaximumSize(30, 25)
        self._bold_button.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self._bold_button.clicked.connect(self._toggle_bold)
        
        # Italic button
        self._italic_button = QPushButton("I")
        self._italic_button.setCheckable(True)
        self._italic_button.setMaximumSize(30, 25)
        font = QFont("Arial", 10)
        font.setItalic(True)
        self._italic_button.setFont(font)
        self._italic_button.clicked.connect(self._toggle_italic)
        
        # Underline button
        self._underline_button = QPushButton("U")
        self._underline_button.setCheckable(True)
        self._underline_button.setMaximumSize(30, 25)
        font = QFont("Arial", 10)
        font.setUnderline(True)
        self._underline_button.setFont(font)
        self._underline_button.clicked.connect(self._toggle_underline)
        
        toolbar_layout.addWidget(self._bold_button)
        toolbar_layout.addWidget(self._italic_button)
        toolbar_layout.addWidget(self._underline_button)
        toolbar_layout.addStretch()
        
        # Insert toolbar at the beginning
        self.layout().insertWidget(0, toolbar_frame)
        
        # Connect text edit signals for format updates
        self._text_edit.cursorPositionChanged.connect(self._update_format_buttons)
    
    def _toggle_bold(self) -> None:
        """Toggle bold formatting"""
        fmt = self._text_edit.currentCharFormat()
        weight = QFont.Weight.Bold if not fmt.font().bold() else QFont.Weight.Normal
        fmt.setFontWeight(weight)
        self._text_edit.setCurrentCharFormat(fmt)
    
    def _toggle_italic(self) -> None:
        """Toggle italic formatting"""
        fmt = self._text_edit.currentCharFormat()
        fmt.setFontItalic(not fmt.font().italic())
        self._text_edit.setCurrentCharFormat(fmt)
    
    def _toggle_underline(self) -> None:
        """Toggle underline formatting"""
        fmt = self._text_edit.currentCharFormat()
        fmt.setFontUnderline(not fmt.font().underline())
        self._text_edit.setCurrentCharFormat(fmt)
    
    def _update_format_buttons(self) -> None:
        """Update format button states based on current cursor position"""
        if not hasattr(self, '_bold_button'):
            return
        
        fmt = self._text_edit.currentCharFormat()
        font = fmt.font()
        
        self._bold_button.setChecked(font.bold())
        self._italic_button.setChecked(font.italic())
        self._underline_button.setChecked(font.underline())
    
    def _get_editor_value(self) -> str:
        """Get HTML content for rich text"""
        return self._text_edit.toHtml()
    
    def _set_editor_value(self, value: Any) -> None:
        """Set HTML content"""
        if isinstance(value, str):
            if value.startswith('<') and value.endswith('>'):
                # Looks like HTML
                self._text_edit.setHtml(value)
            else:
                # Plain text
                self._text_edit.setPlainText(value)
        else:
            self._text_edit.setPlainText(str(value) if value is not None else "")
        
        self._update_char_count()
    
    def get_plain_text(self) -> str:
        """Get plain text content"""
        return self._text_edit.toPlainText()
    
    def set_formatting_enabled(self, enabled: bool) -> None:
        """Enable/disable rich text formatting"""
        self._formatting_enabled = enabled
        self._text_edit.setAcceptRichText(enabled)