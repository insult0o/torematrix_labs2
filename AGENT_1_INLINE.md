# AGENT 1: Core Inline Editor Framework (Issue #23.1/#185)

## 🎯 Your Assignment
You are **Agent 1** implementing the **Core Inline Editor Framework** for the Element Management Inline Editing System. Your focus is building the foundational inline editing infrastructure with activation mechanisms and basic editing capabilities.

## 📋 Specific Tasks

### 1. Core Editor Infrastructure
```python
# src/torematrix/ui/components/editors/base.py
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal

class BaseEditor(QWidget, ABC):
    """Base interface for all inline editors"""
    
    # Signals
    editing_started = pyqtSignal()
    editing_finished = pyqtSignal(bool)  # success
    content_changed = pyqtSignal(str)
    validation_failed = pyqtSignal(str)
    
    @abstractmethod
    def start_editing(self, content: str) -> None:
        """Start editing with initial content"""
        pass
    
    @abstractmethod
    def finish_editing(self, save: bool = True) -> Optional[str]:
        """Finish editing, return content if saving"""
        pass
    
    @abstractmethod
    def validate_content(self) -> tuple[bool, str]:
        """Validate current content, return (valid, error_msg)"""
        pass
```

### 2. Main Inline Editor Widget
```python
# src/torematrix/ui/components/editors/inline.py
from PyQt6.QtWidgets import (QTextEdit, QHBoxLayout, QVBoxLayout, 
                            QPushButton, QWidget, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QKeySequence, QTextCursor

class InlineEditor(BaseEditor):
    """Main inline editor with double-click activation"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_editing = False
        self.original_content = ""
        self._setup_ui()
        self._setup_shortcuts()
        
    def _setup_ui(self):
        """Setup editor UI with text area and controls"""
        layout = QVBoxLayout(self)
        
        # Text editor
        self.text_edit = QTextEdit()
        self.text_edit.setMaximumHeight(200)
        self.text_edit.hide()
        
        # Display label (for non-editing mode)
        self.display_label = QLabel()
        self.display_label.setWordWrap(True)
        self.display_label.mouseDoubleClickEvent = self._on_double_click
        
        # Control buttons
        controls = QHBoxLayout()
        self.save_btn = QPushButton("💾 Save")
        self.cancel_btn = QPushButton("❌ Cancel")
        self.save_btn.clicked.connect(self._save_content)
        self.cancel_btn.clicked.connect(self._cancel_editing)
        
        controls.addWidget(self.save_btn)
        controls.addWidget(self.cancel_btn)
        controls.addStretch()
        
        # Hide controls initially
        self.controls_widget = QWidget()
        self.controls_widget.setLayout(controls)
        self.controls_widget.hide()
        
        layout.addWidget(self.display_label)
        layout.addWidget(self.text_edit)
        layout.addWidget(self.controls_widget)
```

### 3. Editor Factory System
```python
# src/torematrix/ui/components/editors/factory.py
from typing import Type, Dict, Any
from enum import Enum
from .base import BaseEditor
from .inline import InlineEditor

class EditorType(Enum):
    INLINE = "inline"
    RICH_TEXT = "rich_text"
    CODE = "code"
    FORMULA = "formula"

class EditorFactory:
    """Factory for creating appropriate editors based on content type"""
    
    _editors: Dict[EditorType, Type[BaseEditor]] = {
        EditorType.INLINE: InlineEditor,
    }
    
    @classmethod
    def create_editor(cls, editor_type: EditorType, 
                     config: Dict[str, Any] = None) -> BaseEditor:
        """Create editor instance"""
        if editor_type not in cls._editors:
            raise ValueError(f"Unknown editor type: {editor_type}")
            
        editor_class = cls._editors[editor_type]
        return editor_class(**(config or {}))
    
    @classmethod
    def register_editor(cls, editor_type: EditorType, 
                       editor_class: Type[BaseEditor]) -> None:
        """Register new editor type"""
        cls._editors[editor_type] = editor_class
```

### 4. Activation and State Management
```python
# Complete the InlineEditor implementation
class InlineEditor(BaseEditor):
    # ... previous code ...
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        self.shortcut_f2 = QShortcut(QKeySequence("F2"), self)
        self.shortcut_f2.activated.connect(self._start_editing_shortcut)
        
        self.shortcut_escape = QShortcut(QKeySequence("Escape"), self)
        self.shortcut_escape.activated.connect(self._cancel_editing)
        
        self.shortcut_save = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.shortcut_save.activated.connect(self._save_content)
    
    def _on_double_click(self, event):
        """Handle double-click to start editing"""
        if not self.is_editing:
            self.start_editing(self.display_label.text())
    
    def start_editing(self, content: str) -> None:
        """Start inline editing mode"""
        if self.is_editing:
            return
            
        self.original_content = content
        self.is_editing = True
        
        # Switch to edit mode
        self.display_label.hide()
        self.text_edit.setPlainText(content)
        self.text_edit.show()
        self.controls_widget.show()
        
        # Focus and select all
        self.text_edit.setFocus()
        self.text_edit.selectAll()
        
        # Visual indicators
        self.setStyleSheet("border: 2px solid #007ACC; border-radius: 4px;")
        
        self.editing_started.emit()
    
    def finish_editing(self, save: bool = True) -> Optional[str]:
        """Finish editing and return to display mode"""
        if not self.is_editing:
            return None
            
        content = None
        if save:
            valid, error = self.validate_content()
            if valid:
                content = self.text_edit.toPlainText()
                self.display_label.setText(content)
            else:
                self.validation_failed.emit(error)
                return None
        else:
            # Restore original content
            self.display_label.setText(self.original_content)
        
        # Switch back to display mode
        self.is_editing = False
        self.text_edit.hide()
        self.controls_widget.hide()
        self.display_label.show()
        
        # Remove visual indicators
        self.setStyleSheet("")
        
        self.editing_finished.emit(save and content is not None)
        return content
    
    def validate_content(self) -> tuple[bool, str]:
        """Basic content validation"""
        content = self.text_edit.toPlainText().strip()
        if not content:
            return False, "Content cannot be empty"
        return True, ""
```

## 📁 Files to Create

### Core Files
1. **`src/torematrix/ui/components/editors/__init__.py`**
```python
"""Inline editing components for element management"""

from .base import BaseEditor
from .inline import InlineEditor
from .factory import EditorFactory, EditorType

__all__ = ['BaseEditor', 'InlineEditor', 'EditorFactory', 'EditorType']
```

2. **`src/torematrix/ui/components/editors/base.py`** - Base editor interface
3. **`src/torematrix/ui/components/editors/inline.py`** - Main inline editor widget
4. **`src/torematrix/ui/components/editors/factory.py`** - Editor factory

### Test Files
1. **`tests/unit/components/editors/__init__.py`**
2. **`tests/unit/components/editors/test_base.py`** - Base editor tests
3. **`tests/unit/components/editors/test_inline.py`** - Inline editor tests
4. **`tests/unit/components/editors/test_factory.py`** - Factory tests

## 🧪 Testing Requirements

### Core Tests (15+ tests minimum)
```python
# tests/unit/components/editors/test_inline.py
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

from torematrix.ui.components.editors import InlineEditor

class TestInlineEditor:
    def test_double_click_activation(self, qtbot):
        """Test double-click starts editing"""
        editor = InlineEditor()
        qtbot.addWidget(editor)
        editor.display_label.setText("Test content")
        
        # Simulate double-click
        qtbot.mouseDClick(editor.display_label, Qt.MouseButton.LeftButton)
        
        assert editor.is_editing
        assert editor.text_edit.isVisible()
        assert editor.controls_widget.isVisible()
        assert not editor.display_label.isVisible()
    
    def test_keyboard_shortcuts(self, qtbot):
        """Test F2, Escape, Ctrl+Enter shortcuts"""
        editor = InlineEditor()
        qtbot.addWidget(editor)
        editor.display_label.setText("Test")
        
        # Test F2 activation
        qtbot.keyClick(editor, Qt.Key.Key_F2)
        assert editor.is_editing
        
        # Test Escape cancellation
        qtbot.keyClick(editor, Qt.Key.Key_Escape)
        assert not editor.is_editing
        
        # Test Ctrl+Enter save
        editor.start_editing("Test content")
        qtbot.keyClick(editor, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
        assert not editor.is_editing
    
    def test_save_cancel_functionality(self, qtbot):
        """Test save and cancel operations"""
        # Implementation for save/cancel tests
        pass
    
    def test_content_validation(self, qtbot):
        """Test content validation"""
        # Implementation for validation tests
        pass
```

## 🔗 Integration Points for Other Agents

### For Agent 2 (Enhanced Text Processing)
```python
# Extend BaseEditor for spell check integration
class BaseEditor(QWidget, ABC):
    # Add spell check signals
    spell_check_requested = pyqtSignal(str)
    formatting_requested = pyqtSignal(str, dict)
    
    @abstractmethod
    def apply_spell_suggestions(self, suggestions: Dict[str, str]) -> None:
        """Apply spell check suggestions"""
        pass
```

### For Agent 3 (Advanced Features)
```python
# Extend InlineEditor for advanced features
class InlineEditor(BaseEditor):
    # Add state for diff and auto-save
    auto_save_enabled = True
    diff_mode = False
    
    def get_editor_state(self) -> Dict[str, Any]:
        """Get current editor state for auto-save"""
        return {
            'content': self.text_edit.toPlainText(),
            'cursor_position': self.text_edit.textCursor().position(),
            'is_editing': self.is_editing
        }
```

### For Agent 4 (Integration)
```python
# Add element integration interface
class InlineEditor(BaseEditor):
    element_updated = pyqtSignal(str, str)  # element_id, new_content
    
    def set_element_context(self, element_id: str, element_type: str) -> None:
        """Set element context for integration"""
        self.element_id = element_id
        self.element_type = element_type
```

## ✅ Acceptance Criteria Checklist

### Core Functionality
- [ ] Double-click activates inline editing mode
- [ ] Basic text editing works smoothly
- [ ] Save button saves content and exits editing
- [ ] Cancel button discards changes and exits editing
- [ ] Visual indicators show editing mode clearly

### Keyboard Shortcuts
- [ ] F2 key starts editing
- [ ] Escape key cancels editing
- [ ] Ctrl+Enter saves and exits editing

### Editor Factory
- [ ] Factory creates appropriate editor types
- [ ] Editor registration system works
- [ ] Configuration passing works correctly

### Testing
- [ ] All unit tests pass
- [ ] >95% code coverage achieved
- [ ] Integration points documented

## 🚀 Success Metrics
- **Functionality**: Core editor working reliably
- **Testing**: 15+ comprehensive tests all passing
- **Performance**: Editor activation <100ms
- **Code Quality**: Clean, typed, documented code
- **Integration**: Ready interfaces for other agents

## 🔄 Development Workflow
1. Create branch: `feature/inline-editing-agent1-issue185`
2. Implement core editor infrastructure
3. Add activation mechanisms and shortcuts
4. Create editor factory system
5. Write comprehensive tests
6. Document integration points
7. Ensure >95% test coverage
8. Create PR when complete

Focus on building a solid foundation that other agents can extend with advanced features!