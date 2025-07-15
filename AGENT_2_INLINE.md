# AGENT 2: Enhanced Text Processing (Issue #23.2/#186)

## 🎯 Your Assignment
You are **Agent 2** implementing **Enhanced Text Processing** for the Inline Editing System. Your focus is adding spell check, validation, formatting preservation, and rich text capabilities to the core editor framework built by Agent 1.

## 📋 Specific Tasks

### 1. Enhanced Text Editor
```python
# src/torematrix/ui/components/editors/text.py
from PyQt6.QtWidgets import QTextEdit, QCompleter, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel, QTimer
from PyQt6.QtGui import QTextCharFormat, QColor, QTextCursor, QSyntaxHighlighter
from typing import Dict, List, Optional, Tuple
import re

class EnhancedTextEdit(QTextEdit):
    """Enhanced text editor with spell check and formatting"""
    
    # Signals
    spell_check_completed = pyqtSignal(dict)
    formatting_applied = pyqtSignal(str)
    validation_changed = pyqtSignal(bool, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.spell_checker = None
        self.validator = None
        self.format_preservor = None
        self._setup_features()
    
    def _setup_features(self):
        """Setup enhanced features"""
        # Enable spell check highlighting
        self.spell_check_timer = QTimer()
        self.spell_check_timer.setSingleShot(True)
        self.spell_check_timer.timeout.connect(self._check_spelling)
        
        # Connect text changes to validation
        self.textChanged.connect(self._on_text_changed)
        
        # Setup autocomplete
        self.completer = QCompleter()
        self.setCompleter(self.completer)
    
    def set_spell_checker(self, spell_checker):
        """Set spell check engine"""
        self.spell_checker = spell_checker
    
    def set_validator(self, validator):
        """Set text validator"""
        self.validator = validator
    
    def set_format_preservor(self, preservor):
        """Set format preservation handler"""
        self.format_preservor = preservor
```

### 2. Spell Check Integration
```python
# src/torematrix/ui/components/editors/spellcheck.py
import re
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QTextCharFormat, QColor, QTextCursor

@dataclass
class SpellSuggestion:
    word: str
    suggestions: List[str]
    position: int
    length: int

class SpellChecker(QObject):
    """Spell check engine with highlighting"""
    
    suggestions_ready = pyqtSignal(list)  # List[SpellSuggestion]
    
    def __init__(self):
        super().__init__()
        self.dictionary = set()
        self.custom_words = set()
        self.ignored_words = set()
        self._load_dictionary()
    
    def _load_dictionary(self):
        """Load spell check dictionary"""
        # Load from system dictionary or package
        try:
            import enchant
            self.dict_checker = enchant.Dict("en_US")
        except ImportError:
            # Fallback to basic word list
            self._load_basic_dictionary()
    
    def check_text(self, text: str) -> List[SpellSuggestion]:
        """Check text for spelling errors"""
        suggestions = []
        words = re.finditer(r'\b\w+\b', text)
        
        for match in words:
            word = match.group()
            if not self._is_word_correct(word):
                suggestions.append(SpellSuggestion(
                    word=word,
                    suggestions=self._get_suggestions(word),
                    position=match.start(),
                    length=len(word)
                ))
        
        return suggestions
    
    def _is_word_correct(self, word: str) -> bool:
        """Check if word is spelled correctly"""
        if word.lower() in self.ignored_words:
            return True
        if word in self.custom_words:
            return True
            
        try:
            return self.dict_checker.check(word)
        except:
            return word.lower() in self.dictionary
    
    def _get_suggestions(self, word: str) -> List[str]:
        """Get spelling suggestions for word"""
        try:
            return self.dict_checker.suggest(word)[:5]
        except:
            return []

class SpellCheckHighlighter(QObject):
    """Handles spell check highlighting in text editor"""
    
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit
        self.error_format = QTextCharFormat()
        self.error_format.setUnderlineColor(QColor(Qt.GlobalColor.red))
        self.error_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
    
    def highlight_errors(self, suggestions: List[SpellSuggestion]):
        """Highlight spelling errors in text"""
        cursor = self.text_edit.textCursor()
        cursor.beginEditBlock()
        
        # Clear previous highlights
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setCharFormat(QTextCharFormat())
        
        # Apply error highlights
        for suggestion in suggestions:
            cursor.setPosition(suggestion.position)
            cursor.setPosition(suggestion.position + suggestion.length,
                             QTextCursor.MoveMode.KeepAnchor)
            cursor.setCharFormat(self.error_format)
        
        cursor.endEditBlock()
```

### 3. Text Validation Engine
```python
# src/torematrix/ui/components/editors/validation.py
from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import re

class ValidationLevel(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass
class ValidationResult:
    is_valid: bool
    level: ValidationLevel
    message: str
    position: int = -1
    length: int = 0

class TextValidator(ABC):
    """Base text validator interface"""
    
    @abstractmethod
    def validate(self, text: str, context: Dict[str, Any] = None) -> List[ValidationResult]:
        """Validate text and return results"""
        pass

class ElementTextValidator(TextValidator):
    """Validator for element text content"""
    
    def __init__(self):
        self.min_length = 1
        self.max_length = 10000
        self.forbidden_chars = set(['<', '>', '&'])
    
    def validate(self, text: str, context: Dict[str, Any] = None) -> List[ValidationResult]:
        """Validate element text"""
        results = []
        
        # Length validation
        if len(text.strip()) < self.min_length:
            results.append(ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Text cannot be empty"
            ))
        
        if len(text) > self.max_length:
            results.append(ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message=f"Text exceeds maximum length ({self.max_length})"
            ))
        
        # Character validation
        for i, char in enumerate(text):
            if char in self.forbidden_chars:
                results.append(ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.WARNING,
                    message=f"Character '{char}' may cause issues",
                    position=i,
                    length=1
                ))
        
        # If no errors, return success
        if not any(r.level == ValidationLevel.ERROR for r in results):
            results.append(ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Text is valid"
            ))
        
        return results

class CodeValidator(TextValidator):
    """Validator for code content"""
    
    def validate(self, text: str, context: Dict[str, Any] = None) -> List[ValidationResult]:
        """Validate code syntax"""
        results = []
        language = context.get('language', 'python') if context else 'python'
        
        if language == 'python':
            try:
                compile(text, '<string>', 'exec')
                results.append(ValidationResult(
                    is_valid=True,
                    level=ValidationLevel.INFO,
                    message="Python syntax is valid"
                ))
            except SyntaxError as e:
                results.append(ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message=f"Syntax error: {e.msg}",
                    position=e.offset or 0
                ))
        
        return results
```

### 4. Formatting Preservation
```python
# src/torematrix/ui/components/editors/formatting.py
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from PyQt6.QtGui import QTextCharFormat, QFont, QColor
from PyQt6.QtCore import Qt
import json

@dataclass
class FormatSpan:
    start: int
    length: int
    format: Dict[str, Any]

class FormatPreservator:
    """Preserves and restores text formatting"""
    
    def __init__(self):
        self.format_spans: List[FormatSpan] = []
    
    def capture_formatting(self, text_edit) -> str:
        """Capture current text formatting"""
        cursor = text_edit.textCursor()
        document = text_edit.document()
        self.format_spans.clear()
        
        # Iterate through document and capture formats
        cursor.setPosition(0)
        while not cursor.atEnd():
            char_format = cursor.charFormat()
            if self._has_formatting(char_format):
                start_pos = cursor.position()
                
                # Find end of this format
                original_format = char_format
                while (not cursor.atEnd() and 
                       self._formats_equal(cursor.charFormat(), original_format)):
                    cursor.movePosition(QTextCursor.MoveOperation.NextCharacter)
                
                length = cursor.position() - start_pos
                if length > 0:
                    self.format_spans.append(FormatSpan(
                        start=start_pos,
                        length=length,
                        format=self._format_to_dict(original_format)
                    ))
            else:
                cursor.movePosition(QTextCursor.MoveOperation.NextCharacter)
        
        return self._serialize_formats()
    
    def restore_formatting(self, text_edit, formats_data: str):
        """Restore text formatting from data"""
        if not formats_data:
            return
            
        self._deserialize_formats(formats_data)
        cursor = text_edit.textCursor()
        cursor.beginEditBlock()
        
        for span in self.format_spans:
            cursor.setPosition(span.start)
            cursor.setPosition(span.start + span.length,
                             QTextCursor.MoveMode.KeepAnchor)
            
            char_format = self._dict_to_format(span.format)
            cursor.setCharFormat(char_format)
        
        cursor.endEditBlock()
    
    def _has_formatting(self, char_format: QTextCharFormat) -> bool:
        """Check if character format has special formatting"""
        return (char_format.font().bold() or 
                char_format.font().italic() or
                char_format.font().underline() or
                char_format.foreground().color() != QColor())
    
    def _format_to_dict(self, char_format: QTextCharFormat) -> Dict[str, Any]:
        """Convert QTextCharFormat to dictionary"""
        font = char_format.font()
        return {
            'bold': font.bold(),
            'italic': font.italic(),
            'underline': font.underline(),
            'font_family': font.family(),
            'font_size': font.pointSize(),
            'color': char_format.foreground().color().name()
        }
```

### 5. Formatting Toolbar
```python
# src/torematrix/ui/components/editors/toolbar.py
from PyQt6.QtWidgets import (QToolBar, QAction, QPushButton, QComboBox, 
                            QSpinBox, QColorDialog)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIcon, QFont, QColor, QTextCharFormat

class FormattingToolbar(QToolBar):
    """Formatting toolbar for rich text editing"""
    
    format_requested = pyqtSignal(str, object)  # format_type, value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(False)
        self.setFloatable(False)
        self._setup_actions()
    
    def _setup_actions(self):
        """Setup formatting actions"""
        # Font family
        self.font_combo = QComboBox()
        self.font_combo.setEditable(False)
        self.font_combo.currentTextChanged.connect(
            lambda font: self.format_requested.emit('font_family', font))
        self.addWidget(self.font_combo)
        
        # Font size
        self.size_spinbox = QSpinBox()
        self.size_spinbox.setRange(8, 72)
        self.size_spinbox.setValue(12)
        self.size_spinbox.valueChanged.connect(
            lambda size: self.format_requested.emit('font_size', size))
        self.addWidget(self.size_spinbox)
        
        self.addSeparator()
        
        # Bold, Italic, Underline
        self.bold_action = QAction("B", self)
        self.bold_action.setCheckable(True)
        self.bold_action.triggered.connect(
            lambda checked: self.format_requested.emit('bold', checked))
        self.addAction(self.bold_action)
        
        self.italic_action = QAction("I", self)
        self.italic_action.setCheckable(True)
        self.italic_action.triggered.connect(
            lambda checked: self.format_requested.emit('italic', checked))
        self.addAction(self.italic_action)
        
        self.underline_action = QAction("U", self)
        self.underline_action.setCheckable(True)
        self.underline_action.triggered.connect(
            lambda checked: self.format_requested.emit('underline', checked))
        self.addAction(self.underline_action)
        
        self.addSeparator()
        
        # Text color
        self.color_btn = QPushButton("🎨")
        self.color_btn.clicked.connect(self._choose_color)
        self.addWidget(self.color_btn)
    
    def _choose_color(self):
        """Open color picker"""
        color = QColorDialog.getColor(Qt.GlobalColor.black, self)
        if color.isValid():
            self.format_requested.emit('color', color)
```

## 📁 Files to Create

### Enhanced Text Processing Files
1. **`src/torematrix/ui/components/editors/text.py`** - Enhanced text editor
2. **`src/torematrix/ui/components/editors/spellcheck.py`** - Spell check integration
3. **`src/torematrix/ui/components/editors/validation.py`** - Text validation engine
4. **`src/torematrix/ui/components/editors/formatting.py`** - Format preservation
5. **`src/torematrix/ui/components/editors/toolbar.py`** - Formatting toolbar

### Text Processing Utilities
6. **`src/torematrix/core/processing/text_processors.py`** - Text processing utilities
7. **`src/torematrix/core/processing/syntax.py`** - Syntax highlighting

### Test Files
8. **`tests/unit/components/editors/test_text.py`** - Enhanced text editor tests
9. **`tests/unit/components/editors/test_spellcheck.py`** - Spell check tests
10. **`tests/unit/components/editors/test_validation.py`** - Validation tests
11. **`tests/unit/components/editors/test_formatting.py`** - Formatting tests

## 🧪 Testing Requirements

### Enhanced Text Tests (20+ tests minimum)
```python
# tests/unit/components/editors/test_spellcheck.py
import pytest
from torematrix.ui.components.editors.spellcheck import SpellChecker, SpellSuggestion

class TestSpellChecker:
    def test_correct_words(self):
        """Test correct words are not flagged"""
        checker = SpellChecker()
        suggestions = checker.check_text("This is correct text.")
        assert len(suggestions) == 0
    
    def test_misspelled_words(self):
        """Test misspelled words are detected"""
        checker = SpellChecker()
        suggestions = checker.check_text("This is incorect text.")
        assert len(suggestions) == 1
        assert suggestions[0].word == "incorect"
        assert "incorrect" in suggestions[0].suggestions
    
    def test_custom_words(self):
        """Test custom word dictionary"""
        checker = SpellChecker()
        checker.custom_words.add("torematrix")
        suggestions = checker.check_text("torematrix is awesome")
        assert len(suggestions) == 0
```

### Integration with Agent 1
```python
# Enhanced inline editor integration
from .text import EnhancedTextEdit
from .spellcheck import SpellChecker, SpellCheckHighlighter
from .validation import ElementTextValidator

class EnhancedInlineEditor(InlineEditor):
    """Inline editor with enhanced text processing"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_enhanced_features()
    
    def _setup_enhanced_features(self):
        """Setup enhanced text processing"""
        # Replace basic text edit with enhanced version
        enhanced_edit = EnhancedTextEdit()
        
        # Setup spell checker
        spell_checker = SpellChecker()
        enhanced_edit.set_spell_checker(spell_checker)
        
        # Setup validator
        validator = ElementTextValidator()
        enhanced_edit.set_validator(validator)
        
        # Replace in layout
        layout = self.layout()
        layout.replaceWidget(self.text_edit, enhanced_edit)
        self.text_edit.deleteLater()
        self.text_edit = enhanced_edit
```

## 🔗 Integration Points for Other Agents

### For Agent 3 (Advanced Features)
```python
# Text processing state for auto-save and diff
class EnhancedTextEdit(QTextEdit):
    def get_processing_state(self) -> Dict[str, Any]:
        """Get text processing state for advanced features"""
        return {
            'spell_check_results': self.last_spell_results,
            'validation_results': self.last_validation_results,
            'formatting_data': self.format_preservor.capture_formatting(self),
            'cursor_position': self.textCursor().position()
        }
    
    def restore_processing_state(self, state: Dict[str, Any]):
        """Restore text processing state"""
        if 'formatting_data' in state:
            self.format_preservor.restore_formatting(self, state['formatting_data'])
```

### For Agent 4 (Integration)
```python
# Element-specific text processing
class EnhancedTextEdit(QTextEdit):
    def configure_for_element(self, element_type: str, element_data: Dict[str, Any]):
        """Configure text processing for specific element type"""
        if element_type == 'code':
            validator = CodeValidator()
            self.set_validator(validator)
        elif element_type == 'formula':
            # Setup formula-specific processing
            pass
        # Add more element-specific configurations
```

## ✅ Acceptance Criteria Checklist

### Spell Check Integration
- [ ] Spell check highlights misspelled words
- [ ] Suggestions provided for corrections
- [ ] Custom word dictionary support
- [ ] Performance optimized for real-time checking

### Text Validation
- [ ] Multi-line text editing supported
- [ ] Validation provides real-time feedback
- [ ] Element-specific validation rules
- [ ] Error highlighting and messages

### Format Preservation
- [ ] Bold, italic, underline preserved
- [ ] Font family and size maintained
- [ ] Text color preserved
- [ ] Complex formatting handled correctly

### Enhanced Features
- [ ] Rich text support working
- [ ] Syntax highlighting for code elements
- [ ] IME support for international input
- [ ] Formatting toolbar functions correctly

### Testing
- [ ] All unit tests pass
- [ ] >95% code coverage achieved
- [ ] Integration with Agent 1 complete

## 🚀 Success Metrics
- **Spell Check**: >95% accuracy in error detection
- **Validation**: Real-time feedback <200ms
- **Format Preservation**: 100% formatting retention
- **Testing**: 20+ comprehensive tests all passing
- **Performance**: Text processing optimized

## 🔄 Development Workflow
1. Create branch: `feature/inline-editing-agent2-issue186`
2. Implement enhanced text editor
3. Add spell check integration
4. Create validation engine
5. Implement format preservation
6. Add formatting toolbar
7. Write comprehensive tests
8. Integrate with Agent 1 core editor
9. Ensure >95% test coverage
10. Create PR when complete

Build robust text processing that enhances the core editor with professional features!