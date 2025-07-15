"""Markdown preview system with live rendering and syntax highlighting"""

import re
import html
from typing import Dict, List, Tuple, Optional, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QTextBrowser,
    QSplitter, QToolBar, QPushButton, QComboBox, QCheckBox, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont, 
    QTextDocument, QPixmap, QPainter
)


class MarkdownSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Markdown text"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_formats()
        self._setup_rules()
        
    def _setup_formats(self):
        """Setup text formats for different Markdown elements"""
        # Headers
        self.header_format = QTextCharFormat()
        self.header_format.setForeground(QColor(0, 0, 139))
        self.header_format.setFontWeight(QFont.Weight.Bold)
        
        # Bold text
        self.bold_format = QTextCharFormat()
        self.bold_format.setFontWeight(QFont.Weight.Bold)
        
        # Italic text
        self.italic_format = QTextCharFormat()
        self.italic_format.setFontItalic(True)
        
        # Code
        self.code_format = QTextCharFormat()
        self.code_format.setForeground(QColor(139, 0, 0))
        self.code_format.setBackground(QColor(240, 240, 240))
        self.code_format.setFontFamily("Consolas")
        
        # Links
        self.link_format = QTextCharFormat()
        self.link_format.setForeground(QColor(0, 0, 238))
        self.link_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)
        
        # Lists
        self.list_format = QTextCharFormat()
        self.list_format.setForeground(QColor(0, 100, 0))
        
        # Blockquotes
        self.quote_format = QTextCharFormat()
        self.quote_format.setForeground(QColor(105, 105, 105))
        self.quote_format.setFontItalic(True)
        
        # HTML tags
        self.html_format = QTextCharFormat()
        self.html_format.setForeground(QColor(128, 0, 128))
        
    def _setup_rules(self):
        """Setup highlighting rules"""
        self.rules = [
            # Headers
            (r'^#{1,6}.*$', self.header_format),
            
            # Bold text **text** or __text__
            (r'\*\*[^*]+\*\*', self.bold_format),
            (r'__[^_]+__', self.bold_format),
            
            # Italic text *text* or _text_
            (r'\*[^*]+\*', self.italic_format),
            (r'_[^_]+_', self.italic_format),
            
            # Inline code `code`
            (r'`[^`]+`', self.code_format),
            
            # Links [text](url)
            (r'\[([^\]]+)\]\([^)]+\)', self.link_format),
            
            # Lists
            (r'^\s*[\*\-\+]\s+.*$', self.list_format),
            (r'^\s*\d+\.\s+.*$', self.list_format),
            
            # Blockquotes
            (r'^>.*$', self.quote_format),
            
            # HTML tags
            (r'<[^>]+>', self.html_format),
        ]
        
    def highlightBlock(self, text: str):
        """Highlight a block of text"""
        # Apply rules
        for pattern, format in self.rules:
            regex = re.compile(pattern, re.MULTILINE)
            for match in regex.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, format)
                
        # Handle code blocks
        self._highlight_code_blocks(text)
        
    def _highlight_code_blocks(self, text: str):
        """Highlight code blocks separately"""
        # Triple backtick code blocks
        code_block_pattern = r'```.*?```'
        for match in re.finditer(code_block_pattern, text, re.DOTALL):
            start = match.start()
            length = match.end() - start
            self.setFormat(start, length, self.code_format)


class MarkdownRenderer:
    """Converts Markdown to HTML with custom extensions"""
    
    def __init__(self):
        self.extensions = {
            'tables': True,
            'strikethrough': True,
            'task_lists': True,
            'footnotes': True,
            'math': True
        }
        
    def render(self, markdown_text: str) -> str:
        """Render Markdown text to HTML
        
        Args:
            markdown_text: Markdown source text
            
        Returns:
            Rendered HTML
        """
        html_content = self._basic_markdown_to_html(markdown_text)
        
        # Apply extensions
        if self.extensions.get('tables'):
            html_content = self._render_tables(html_content)
            
        if self.extensions.get('strikethrough'):
            html_content = self._render_strikethrough(html_content)
            
        if self.extensions.get('task_lists'):
            html_content = self._render_task_lists(html_content)
            
        if self.extensions.get('math'):
            html_content = self._render_math(html_content)
            
        return self._wrap_html(html_content)
        
    def _basic_markdown_to_html(self, text: str) -> str:
        """Convert basic Markdown elements to HTML"""
        # Escape HTML first
        text = html.escape(text)
        
        # Headers
        text = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^#### (.*?)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
        text = re.sub(r'^##### (.*?)$', r'<h5>\1</h5>', text, flags=re.MULTILINE)
        text = re.sub(r'^###### (.*?)$', r'<h6>\1</h6>', text, flags=re.MULTILINE)
        
        # Bold and italic
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__(.*?)__', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
        text = re.sub(r'_(.*?)_', r'<em>\1</em>', text)
        
        # Inline code
        text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
        
        # Links
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        
        # Images
        text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', text)
        
        # Code blocks
        text = self._render_code_blocks(text)
        
        # Lists
        text = self._render_lists(text)
        
        # Blockquotes
        text = self._render_blockquotes(text)
        
        # Line breaks
        text = re.sub(r'\n\n', '</p><p>', text)
        text = re.sub(r'\n', '<br>', text)
        
        return text
        
    def _render_code_blocks(self, text: str) -> str:
        """Render code blocks"""
        # Triple backtick code blocks
        def replace_code_block(match):
            code = match.group(1)
            language = match.group(2) if match.group(2) else ''
            code_html = html.escape(code.strip())
            
            if language:
                return f'<pre><code class="language-{language}">{code_html}</code></pre>'
            else:
                return f'<pre><code>{code_html}</code></pre>'
                
        text = re.sub(r'```(\w+)?\n(.*?)\n```', replace_code_block, text, flags=re.DOTALL)
        
        # Indented code blocks
        lines = text.split('\n')
        in_code_block = False
        result_lines = []
        code_lines = []
        
        for line in lines:
            if line.startswith('    ') or line.startswith('\t'):
                if not in_code_block:
                    in_code_block = True
                    code_lines = []
                code_lines.append(line[4:] if line.startswith('    ') else line[1:])
            else:
                if in_code_block:
                    code_html = html.escape('\n'.join(code_lines))
                    result_lines.append(f'<pre><code>{code_html}</code></pre>')
                    in_code_block = False
                result_lines.append(line)
                
        # Handle final code block
        if in_code_block:
            code_html = html.escape('\n'.join(code_lines))
            result_lines.append(f'<pre><code>{code_html}</code></pre>')
            
        return '\n'.join(result_lines)
        
    def _render_lists(self, text: str) -> str:
        """Render lists"""
        lines = text.split('\n')
        result_lines = []
        in_ul = False
        in_ol = False
        
        for line in lines:
            ul_match = re.match(r'^(\s*)[\*\-\+]\s+(.*)', line)
            ol_match = re.match(r'^(\s*)\d+\.\s+(.*)', line)
            
            if ul_match:
                if not in_ul:
                    result_lines.append('<ul>')
                    in_ul = True
                if in_ol:
                    result_lines.append('</ol>')
                    in_ol = False
                result_lines.append(f'<li>{ul_match.group(2)}</li>')
            elif ol_match:
                if not in_ol:
                    result_lines.append('<ol>')
                    in_ol = True
                if in_ul:
                    result_lines.append('</ul>')
                    in_ul = False
                result_lines.append(f'<li>{ol_match.group(2)}</li>')
            else:
                if in_ul:
                    result_lines.append('</ul>')
                    in_ul = False
                if in_ol:
                    result_lines.append('</ol>')
                    in_ol = False
                result_lines.append(line)
                
        # Close any open lists
        if in_ul:
            result_lines.append('</ul>')
        if in_ol:
            result_lines.append('</ol>')
            
        return '\n'.join(result_lines)
        
    def _render_blockquotes(self, text: str) -> str:
        """Render blockquotes"""
        lines = text.split('\n')
        result_lines = []
        in_blockquote = False
        quote_lines = []
        
        for line in lines:
            if line.startswith('>'):
                if not in_blockquote:
                    in_blockquote = True
                    quote_lines = []
                quote_lines.append(line[1:].strip())
            else:
                if in_blockquote:
                    quote_html = '<br>'.join(quote_lines)
                    result_lines.append(f'<blockquote>{quote_html}</blockquote>')
                    in_blockquote = False
                result_lines.append(line)
                
        # Handle final blockquote
        if in_blockquote:
            quote_html = '<br>'.join(quote_lines)
            result_lines.append(f'<blockquote>{quote_html}</blockquote>')
            
        return '\n'.join(result_lines)
        
    def _render_tables(self, text: str) -> str:
        """Render GitHub-style tables"""
        # Table pattern: | col1 | col2 | col3 |
        table_pattern = r'(\|[^|\n]+)+\|'
        
        lines = text.split('\n')
        result_lines = []
        in_table = False
        table_lines = []
        
        for i, line in enumerate(lines):
            if re.match(table_pattern, line.strip()):
                if not in_table:
                    in_table = True
                    table_lines = []
                table_lines.append(line.strip())
            else:
                if in_table:
                    # Process table
                    table_html = self._process_table(table_lines)
                    result_lines.append(table_html)
                    in_table = False
                result_lines.append(line)
                
        # Handle final table
        if in_table:
            table_html = self._process_table(table_lines)
            result_lines.append(table_html)
            
        return '\n'.join(result_lines)
        
    def _process_table(self, table_lines: List[str]) -> str:
        """Process table lines into HTML"""
        if len(table_lines) < 2:
            return '\n'.join(table_lines)
            
        # First line is header
        header_line = table_lines[0]
        header_cells = [cell.strip() for cell in header_line.split('|')[1:-1]]
        
        # Second line should be separator
        if len(table_lines) > 1 and re.match(r'\|[\s\-:]+\|', table_lines[1]):
            data_lines = table_lines[2:]
        else:
            data_lines = table_lines[1:]
            
        html = '<table border="1" cellpadding="5" cellspacing="0">'
        
        # Header
        html += '<thead><tr>'
        for cell in header_cells:
            html += f'<th>{cell}</th>'
        html += '</tr></thead>'
        
        # Data rows
        html += '<tbody>'
        for line in data_lines:
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            html += '<tr>'
            for cell in cells:
                html += f'<td>{cell}</td>'
            html += '</tr>'
        html += '</tbody></table>'
        
        return html
        
    def _render_strikethrough(self, text: str) -> str:
        """Render strikethrough text"""
        return re.sub(r'~~(.*?)~~', r'<del>\1</del>', text)
        
    def _render_task_lists(self, text: str) -> str:
        """Render task lists"""
        # [ ] unchecked task
        text = re.sub(r'^\s*- \[ \] (.*)', r'<li style="list-style: none;"><input type="checkbox" disabled> \1</li>', text, flags=re.MULTILINE)
        
        # [x] checked task
        text = re.sub(r'^\s*- \[x\] (.*)', r'<li style="list-style: none;"><input type="checkbox" checked disabled> \1</li>', text, flags=re.MULTILINE)
        
        return text
        
    def _render_math(self, text: str) -> str:
        """Render math expressions (basic)"""
        # Inline math $expression$
        text = re.sub(r'\$(.*?)\$', r'<span class="math">\1</span>', text)
        
        # Block math $$expression$$
        text = re.sub(r'\$\$(.*?)\$\$', r'<div class="math-block">\1</div>', text, flags=re.DOTALL)
        
        return text
        
    def _wrap_html(self, content: str) -> str:
        """Wrap content in HTML document"""
        css = """
        <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 20px auto;
            padding: 20px;
            color: #333;
        }
        h1, h2, h3, h4, h5, h6 { 
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
            line-height: 1.25;
        }
        h1 { font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: 10px; }
        h2 { font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: 8px; }
        h3 { font-size: 1.25em; }
        p { margin-bottom: 16px; }
        code { 
            padding: 2px 4px;
            font-size: 85%;
            background-color: rgba(27,31,35,0.05);
            border-radius: 3px;
            font-family: 'SFMono-Regular', Consolas, monospace;
        }
        pre {
            padding: 16px;
            overflow: auto;
            font-size: 85%;
            line-height: 1.45;
            background-color: #f6f8fa;
            border-radius: 6px;
        }
        pre code {
            background: transparent;
            padding: 0;
        }
        blockquote {
            padding: 0 1em;
            color: #6a737d;
            border-left: 0.25em solid #dfe2e5;
            margin: 0;
        }
        table {
            border-collapse: collapse;
            margin: 20px 0;
            width: 100%;
        }
        th, td {
            border: 1px solid #dfe2e5;
            padding: 6px 13px;
        }
        th {
            background-color: #f6f8fa;
            font-weight: 600;
        }
        .math { 
            color: #d73a49;
            font-style: italic;
        }
        .math-block {
            text-align: center;
            margin: 20px 0;
            padding: 10px;
            background-color: #f6f8fa;
            border-radius: 6px;
        }
        </style>
        """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Markdown Preview</title>
            {css}
        </head>
        <body>
            <p>{content}</p>
        </body>
        </html>
        """


class MarkdownPreview(QWidget):
    """Markdown preview widget with live rendering
    
    Features:
    - Live preview with syntax highlighting
    - Multiple rendering modes
    - Export to HTML/PDF
    - Scroll synchronization
    - Custom CSS themes
    """
    
    # Signals
    preview_updated = pyqtSignal(str)  # html_content
    export_requested = pyqtSignal(str, str)  # format, content
    theme_changed = pyqtSignal(str)  # theme_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.markdown_text = ""
        self.renderer = MarkdownRenderer()
        self.auto_update = True
        self.sync_scroll = True
        
        self._setup_ui()
        self._setup_connections()
        
        # Update timer for live preview
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._update_preview)
        
    def _setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)
        
        # Main content area
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Editor side
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Enter Markdown text here...")
        
        # Apply syntax highlighting
        self.highlighter = MarkdownSyntaxHighlighter(self.editor.document())
        
        # Preview side
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(True)
        
        splitter.addWidget(self.editor)
        splitter.addWidget(self.preview)
        splitter.setSizes([50, 50])
        
        layout.addWidget(splitter)
        
    def _create_toolbar(self) -> QToolBar:
        """Create toolbar with preview controls
        
        Returns:
            Configured toolbar
        """
        toolbar = QToolBar()
        
        # Auto-update toggle
        self.auto_update_checkbox = QCheckBox("Live Preview")
        self.auto_update_checkbox.setChecked(self.auto_update)
        self.auto_update_checkbox.toggled.connect(self._toggle_auto_update)
        toolbar.addWidget(self.auto_update_checkbox)
        
        toolbar.addSeparator()
        
        # Scroll sync toggle
        self.sync_scroll_checkbox = QCheckBox("Sync Scroll")
        self.sync_scroll_checkbox.setChecked(self.sync_scroll)
        self.sync_scroll_checkbox.toggled.connect(self._toggle_sync_scroll)
        toolbar.addWidget(self.sync_scroll_checkbox)
        
        toolbar.addSeparator()
        
        # Theme selector
        toolbar.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Default", "GitHub", "Dark", "Academic"])
        self.theme_combo.currentTextChanged.connect(self._change_theme)
        toolbar.addWidget(self.theme_combo)
        
        toolbar.addSeparator()
        
        # Manual update button
        update_btn = QPushButton("Update Preview")
        update_btn.clicked.connect(self._update_preview)
        toolbar.addWidget(update_btn)
        
        # Export button
        export_btn = QPushButton("Export HTML")
        export_btn.clicked.connect(self._export_html)
        toolbar.addWidget(export_btn)
        
        return toolbar
        
    def _setup_connections(self):
        """Setup signal connections"""
        self.editor.textChanged.connect(self._on_text_changed)
        
        # Scroll synchronization
        if self.sync_scroll:
            self.editor.verticalScrollBar().valueChanged.connect(self._sync_scroll_to_preview)
            
    def set_markdown_text(self, text: str):
        """Set Markdown text to display
        
        Args:
            text: Markdown source text
        """
        self.markdown_text = text
        self.editor.setPlainText(text)
        
        if self.auto_update:
            self._update_preview()
            
    def get_markdown_text(self) -> str:
        """Get current Markdown text
        
        Returns:
            Current Markdown text
        """
        return self.editor.toPlainText()
        
    def get_html(self) -> str:
        """Get rendered HTML
        
        Returns:
            Rendered HTML content
        """
        return self.preview.toHtml()
        
    def _on_text_changed(self):
        """Handle text changes in editor"""
        self.markdown_text = self.editor.toPlainText()
        
        if self.auto_update:
            # Delay update to avoid too frequent updates
            self.update_timer.start(500)
            
    def _update_preview(self):
        """Update the preview pane"""
        if not self.markdown_text:
            self.preview.clear()
            return
            
        # Render Markdown to HTML
        html_content = self.renderer.render(self.markdown_text)
        
        # Set HTML content
        self.preview.setHtml(html_content)
        
        self.preview_updated.emit(html_content)
        
    def _toggle_auto_update(self, enabled: bool):
        """Toggle auto-update mode
        
        Args:
            enabled: Whether to enable auto-update
        """
        self.auto_update = enabled
        
        if enabled:
            self._update_preview()
            
    def _toggle_sync_scroll(self, enabled: bool):
        """Toggle scroll synchronization
        
        Args:
            enabled: Whether to enable scroll sync
        """
        self.sync_scroll = enabled
        
        if enabled:
            self.editor.verticalScrollBar().valueChanged.connect(self._sync_scroll_to_preview)
        else:
            self.editor.verticalScrollBar().valueChanged.disconnect(self._sync_scroll_to_preview)
            
    def _sync_scroll_to_preview(self, value: int):
        """Synchronize scroll position to preview
        
        Args:
            value: Scroll bar value
        """
        if not self.sync_scroll:
            return
            
        # Calculate relative position
        editor_scrollbar = self.editor.verticalScrollBar()
        preview_scrollbar = self.preview.verticalScrollBar()
        
        if editor_scrollbar.maximum() > 0:
            ratio = value / editor_scrollbar.maximum()
            preview_pos = int(ratio * preview_scrollbar.maximum())
            preview_scrollbar.setValue(preview_pos)
            
    def _change_theme(self, theme_name: str):
        """Change preview theme
        
        Args:
            theme_name: Name of theme to apply
        """
        # This would apply different CSS themes
        self.theme_changed.emit(theme_name)
        self._update_preview()
        
    def _export_html(self):
        """Export preview as HTML"""
        html_content = self.get_html()
        self.export_requested.emit("html", html_content)
        
    def set_extensions(self, extensions: Dict[str, bool]):
        """Set Markdown extensions
        
        Args:
            extensions: Dictionary of extension settings
        """
        self.renderer.extensions.update(extensions)
        
        if self.auto_update:
            self._update_preview()
            
    def insert_markdown_element(self, element_type: str, text: str = ""):
        """Insert a Markdown element at cursor position
        
        Args:
            element_type: Type of element (header, bold, italic, etc.)
            text: Text to wrap or insert
        """
        cursor = self.editor.textCursor()
        
        if element_type == "bold":
            cursor.insertText(f"**{text}**")
        elif element_type == "italic":
            cursor.insertText(f"*{text}*")
        elif element_type == "code":
            cursor.insertText(f"`{text}`")
        elif element_type == "header1":
            cursor.insertText(f"# {text}")
        elif element_type == "header2":
            cursor.insertText(f"## {text}")
        elif element_type == "header3":
            cursor.insertText(f"### {text}")
        elif element_type == "link":
            cursor.insertText(f"[{text}](url)")
        elif element_type == "image":
            cursor.insertText(f"![{text}](image_url)")
        elif element_type == "list":
            cursor.insertText(f"- {text}")
        elif element_type == "quote":
            cursor.insertText(f"> {text}")
        elif element_type == "code_block":
            cursor.insertText(f"```\n{text}\n```")
            
    def get_preview_statistics(self) -> Dict[str, Any]:
        """Get preview statistics
        
        Returns:
            Dictionary with preview statistics
        """
        text = self.markdown_text
        
        return {
            'character_count': len(text),
            'word_count': len(text.split()),
            'line_count': len(text.splitlines()),
            'paragraph_count': len([p for p in text.split('\n\n') if p.strip()]),
            'header_count': len(re.findall(r'^#+', text, re.MULTILINE)),
            'link_count': len(re.findall(r'\[([^\]]+)\]\([^)]+\)', text)),
            'image_count': len(re.findall(r'!\[([^\]]*)\]\([^)]+\)', text)),
            'code_block_count': len(re.findall(r'```.*?```', text, re.DOTALL))
        }