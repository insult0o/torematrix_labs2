"""Search Results Export System

Comprehensive export functionality for search results with support
for multiple formats, progress tracking, and export configuration.
"""

import json
import csv
import logging
import asyncio
from typing import Dict, List, Optional, Any, Union, IO
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton,
    QPushButton, QProgressBar, QLabel, QCheckBox, QSpinBox,
    QComboBox, QLineEdit, QTextEdit, QFileDialog, QMessageBox,
    QDialogButtonBox, QTabWidget, QWidget, QFormLayout, QSlider
)

from torematrix.core.models.element import Element
from .highlighting import HighlightedElement

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """Supported export formats"""
    JSON = "json"
    CSV = "csv"
    XML = "xml"
    HTML = "html"
    PDF = "pdf"
    XLSX = "xlsx"
    TXT = "txt"
    MARKDOWN = "markdown"


class ExportStatus(Enum):
    """Export operation status"""
    PENDING = "pending"
    PREPARING = "preparing"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExportConfiguration:
    """Configuration for export operations"""
    format: ExportFormat = ExportFormat.JSON
    include_metadata: bool = True
    include_highlights: bool = True
    include_search_terms: bool = True
    include_statistics: bool = False
    
    # Format-specific options
    json_pretty: bool = True
    json_indent: int = 2
    csv_delimiter: str = ","
    csv_quote_char: str = '"'
    html_include_css: bool = True
    html_inline_styles: bool = False
    pdf_page_size: str = "A4"
    pdf_orientation: str = "portrait"
    xlsx_include_charts: bool = False
    
    # Content filtering
    max_elements: Optional[int] = None
    element_types_filter: List[str] = field(default_factory=list)
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    
    # Advanced options
    compress_output: bool = False
    split_large_files: bool = False
    split_size_mb: int = 100
    custom_template: Optional[str] = None


@dataclass
class ExportProgress:
    """Progress information for export operations"""
    total_elements: int = 0
    processed_elements: int = 0
    current_stage: str = ""
    status: ExportStatus = ExportStatus.PENDING
    start_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None
    output_files: List[str] = field(default_factory=list)
    
    @property
    def progress_percentage(self) -> float:
        """Get progress as percentage"""
        if self.total_elements == 0:
            return 0.0
        return (self.processed_elements / self.total_elements) * 100.0
    
    @property
    def is_complete(self) -> bool:
        """Check if export is complete"""
        return self.status in [ExportStatus.COMPLETED, ExportStatus.FAILED, ExportStatus.CANCELLED]
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        if not self.start_time:
            return 0.0
        return (datetime.now() - self.start_time).total_seconds()


class ResultExporter(QThread):
    """Threaded export worker for search results"""
    
    # Signals
    progress_updated = pyqtSignal(object)  # ExportProgress
    stage_changed = pyqtSignal(str)  # stage name
    export_completed = pyqtSignal(str)  # output file path
    export_failed = pyqtSignal(str)  # error message
    
    def __init__(self, elements: List[Union[Element, HighlightedElement]], 
                 config: ExportConfiguration, output_path: str, parent=None):
        super().__init__(parent)
        
        self.elements = elements
        self.config = config
        self.output_path = output_path
        self.should_cancel = False
        
        self.progress = ExportProgress(
            total_elements=len(elements),
            status=ExportStatus.PENDING
        )
        
        # Format handlers
        self._format_handlers = {
            ExportFormat.JSON: self._export_to_json,
            ExportFormat.CSV: self._export_to_csv,
            ExportFormat.XML: self._export_to_xml,
            ExportFormat.HTML: self._export_to_html,
            ExportFormat.TXT: self._export_to_txt,
            ExportFormat.MARKDOWN: self._export_to_markdown,
        }
        
        logger.debug(f"Export worker initialized: {len(elements)} elements to {config.format.value}")
    
    def cancel(self):
        """Cancel the export operation"""
        self.should_cancel = True
        self.progress.status = ExportStatus.CANCELLED
        logger.info("Export cancelled by user")
    
    def run(self):
        """Run the export operation"""
        try:
            self.progress.start_time = datetime.now()
            self.progress.status = ExportStatus.PREPARING
            self._emit_progress("Preparing export...")
            
            # Filter elements if needed
            filtered_elements = self._filter_elements()
            self.progress.total_elements = len(filtered_elements)
            
            if self.should_cancel:
                return
            
            # Start export
            self.progress.status = ExportStatus.EXPORTING
            self._emit_progress("Starting export...")
            
            # Get format handler
            handler = self._format_handlers.get(self.config.format)
            if not handler:
                raise ValueError(f"Unsupported export format: {self.config.format}")
            
            # Execute export
            output_file = handler(filtered_elements)
            
            if self.should_cancel:
                return
            
            # Complete export
            self.progress.status = ExportStatus.COMPLETED
            self.progress.output_files.append(output_file)
            self._emit_progress("Export completed")
            
            self.export_completed.emit(output_file)
            logger.info(f"Export completed successfully: {output_file}")
            
        except Exception as e:
            self.progress.status = ExportStatus.FAILED
            self.progress.error_message = str(e)
            self._emit_progress(f"Export failed: {e}")
            self.export_failed.emit(str(e))
            logger.error(f"Export failed: {e}")
    
    def _emit_progress(self, stage: str):
        """Emit progress update"""
        self.progress.current_stage = stage
        self.progress_updated.emit(self.progress)
        self.stage_changed.emit(stage)
    
    def _filter_elements(self) -> List[Union[Element, HighlightedElement]]:
        """Filter elements based on configuration"""
        filtered = self.elements.copy()
        
        # Apply element type filter
        if self.config.element_types_filter:
            filtered = [elem for elem in filtered if self._get_element_type(elem) in self.config.element_types_filter]
        
        # Apply max elements limit
        if self.config.max_elements and len(filtered) > self.config.max_elements:
            filtered = filtered[:self.config.max_elements]
        
        # Apply date range filter
        if self.config.date_range_start or self.config.date_range_end:
            filtered = [elem for elem in filtered if self._element_in_date_range(elem)]
        
        logger.debug(f"Filtered {len(self.elements)} elements to {len(filtered)}")
        return filtered
    
    def _get_element_type(self, element: Union[Element, HighlightedElement]) -> str:
        """Get element type"""
        if isinstance(element, HighlightedElement):
            return getattr(element.element, 'element_type', 'unknown')
        return getattr(element, 'element_type', 'unknown')
    
    def _element_in_date_range(self, element: Union[Element, HighlightedElement]) -> bool:
        """Check if element is in configured date range"""
        elem = element.element if isinstance(element, HighlightedElement) else element
        elem_date = getattr(elem, 'created_at', None) or getattr(elem, 'timestamp', None)
        
        if not elem_date:
            return True  # Include elements without dates
        
        if self.config.date_range_start and elem_date < self.config.date_range_start:
            return False
        
        if self.config.date_range_end and elem_date > self.config.date_range_end:
            return False
        
        return True
    
    def _update_progress(self, processed: int):
        """Update processing progress"""
        self.progress.processed_elements = processed
        
        if processed % 10 == 0 or processed == self.progress.total_elements:  # Update every 10 items
            self.progress_updated.emit(self.progress)
        
        if self.should_cancel:
            raise InterruptedError("Export cancelled")
    
    # Format-specific export methods
    
    def _export_to_json(self, elements: List[Union[Element, HighlightedElement]]) -> str:
        """Export to JSON format"""
        self._emit_progress("Converting to JSON...")
        
        output_data = {
            'export_info': {
                'format': 'json',
                'timestamp': datetime.now().isoformat(),
                'total_elements': len(elements),
                'configuration': self._serialize_config()
            },
            'elements': []
        }
        
        for i, element in enumerate(elements):
            self._update_progress(i)
            
            element_data = self._serialize_element(element)
            output_data['elements'].append(element_data)
        
        # Write to file
        output_file = self.output_path
        if not output_file.endswith('.json'):
            output_file += '.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            if self.config.json_pretty:
                json.dump(output_data, f, indent=self.config.json_indent, ensure_ascii=False)
            else:
                json.dump(output_data, f, ensure_ascii=False)
        
        return output_file
    
    def _export_to_csv(self, elements: List[Union[Element, HighlightedElement]]) -> str:
        """Export to CSV format"""
        self._emit_progress("Converting to CSV...")
        
        output_file = self.output_path
        if not output_file.endswith('.csv'):
            output_file += '.csv'
        
        # Determine CSV columns
        columns = ['id', 'type', 'text', 'content']
        
        if self.config.include_metadata:
            columns.extend(['created_at', 'updated_at', 'metadata'])
        
        if self.config.include_highlights:
            columns.extend(['highlighted_text', 'match_count', 'search_terms'])
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(
                f, 
                delimiter=self.config.csv_delimiter,
                quotechar=self.config.csv_quote_char,
                quoting=csv.QUOTE_MINIMAL
            )
            
            # Write header
            writer.writerow(columns)
            
            # Write data rows
            for i, element in enumerate(elements):
                self._update_progress(i)
                
                row_data = self._serialize_element_for_csv(element, columns)
                writer.writerow(row_data)
        
        return output_file
    
    def _export_to_xml(self, elements: List[Union[Element, HighlightedElement]]) -> str:
        """Export to XML format"""
        self._emit_progress("Converting to XML...")
        
        # Create root element
        root = ET.Element('search_results')
        
        # Add metadata
        info_elem = ET.SubElement(root, 'export_info')
        ET.SubElement(info_elem, 'format').text = 'xml'
        ET.SubElement(info_elem, 'timestamp').text = datetime.now().isoformat()
        ET.SubElement(info_elem, 'total_elements').text = str(len(elements))
        
        # Add elements
        elements_elem = ET.SubElement(root, 'elements')
        
        for i, element in enumerate(elements):
            self._update_progress(i)
            
            elem_xml = self._serialize_element_for_xml(element)
            elements_elem.append(elem_xml)
        
        # Write to file
        output_file = self.output_path
        if not output_file.endswith('.xml'):
            output_file += '.xml'
        
        tree = ET.ElementTree(root)
        tree.write(output_file, encoding='utf-8', xml_declaration=True)
        
        return output_file
    
    def _export_to_html(self, elements: List[Union[Element, HighlightedElement]]) -> str:
        """Export to HTML format"""
        self._emit_progress("Converting to HTML...")
        
        html_content = self._generate_html_template()
        
        # Add elements
        elements_html = []
        for i, element in enumerate(elements):
            self._update_progress(i)
            
            element_html = self._serialize_element_for_html(element)
            elements_html.append(element_html)
        
        # Combine everything
        final_html = html_content.replace('{{ELEMENTS}}', '\n'.join(elements_html))
        final_html = final_html.replace('{{TIMESTAMP}}', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        final_html = final_html.replace('{{TOTAL_ELEMENTS}}', str(len(elements)))
        
        # Write to file
        output_file = self.output_path
        if not output_file.endswith('.html'):
            output_file += '.html'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_html)
        
        return output_file
    
    def _export_to_txt(self, elements: List[Union[Element, HighlightedElement]]) -> str:
        """Export to plain text format"""
        self._emit_progress("Converting to text...")
        
        output_file = self.output_path
        if not output_file.endswith('.txt'):
            output_file += '.txt'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"Search Results Export\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Elements: {len(elements)}\n")
            f.write("=" * 50 + "\n\n")
            
            # Write elements
            for i, element in enumerate(elements):
                self._update_progress(i)
                
                f.write(f"Element {i + 1}:\n")
                f.write("-" * 20 + "\n")
                
                # Get element data
                elem = element.element if isinstance(element, HighlightedElement) else element
                
                f.write(f"ID: {getattr(elem, 'element_id', 'N/A')}\n")
                f.write(f"Type: {getattr(elem, 'element_type', 'N/A')}\n")
                
                # Content
                content = getattr(elem, 'text', '') or getattr(elem, 'content', '')
                if isinstance(element, HighlightedElement) and self.config.include_highlights:
                    content = element.highlighted_text
                
                f.write(f"Content: {content}\n")
                
                if self.config.include_metadata:
                    f.write(f"Created: {getattr(elem, 'created_at', 'N/A')}\n")
                
                f.write("\n")
        
        return output_file
    
    def _export_to_markdown(self, elements: List[Union[Element, HighlightedElement]]) -> str:
        """Export to Markdown format"""
        self._emit_progress("Converting to Markdown...")
        
        output_file = self.output_path
        if not output_file.endswith('.md'):
            output_file += '.md'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write("# Search Results Export\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
            f.write(f"**Total Elements:** {len(elements)}  \n\n")
            
            # Table of contents
            f.write("## Table of Contents\n\n")
            for i, element in enumerate(elements[:10]):  # Only first 10 for TOC
                elem = element.element if isinstance(element, HighlightedElement) else element
                title = getattr(elem, 'title', f"Element {i + 1}")
                f.write(f"- [{title}](#element-{i + 1})\n")
            
            if len(elements) > 10:
                f.write(f"- ... and {len(elements) - 10} more elements\n")
            
            f.write("\n---\n\n")
            
            # Write elements
            for i, element in enumerate(elements):
                self._update_progress(i)
                
                elem = element.element if isinstance(element, HighlightedElement) else element
                
                f.write(f"## Element {i + 1}\n\n")
                
                # Metadata table
                f.write("| Property | Value |\n")
                f.write("|----------|-------|\n")
                f.write(f"| ID | `{getattr(elem, 'element_id', 'N/A')}` |\n")
                f.write(f"| Type | `{getattr(elem, 'element_type', 'N/A')}` |\n")
                
                if self.config.include_metadata:
                    f.write(f"| Created | {getattr(elem, 'created_at', 'N/A')} |\n")
                
                f.write("\n")
                
                # Content
                content = getattr(elem, 'text', '') or getattr(elem, 'content', '')
                if isinstance(element, HighlightedElement) and self.config.include_highlights:
                    # Convert HTML highlights to Markdown
                    content = element.highlighted_html.replace('<mark', '**').replace('</mark>', '**')
                    content = content.replace('**style="[^"]*">', '**')  # Remove style attributes
                
                f.write("### Content\n\n")
                f.write(f"{content}\n\n")
                
                if isinstance(element, HighlightedElement) and self.config.include_search_terms:
                    f.write("### Search Information\n\n")
                    f.write(f"**Search Terms:** {', '.join(element.search_terms)}  \n")
                    f.write(f"**Matches Found:** {element.total_matches}  \n\n")
                
                f.write("---\n\n")
        
        return output_file
    
    # Serialization helper methods
    
    def _serialize_config(self) -> Dict[str, Any]:
        """Serialize export configuration"""
        return {
            'format': self.config.format.value,
            'include_metadata': self.config.include_metadata,
            'include_highlights': self.config.include_highlights,
            'include_search_terms': self.config.include_search_terms,
            'max_elements': self.config.max_elements
        }
    
    def _serialize_element(self, element: Union[Element, HighlightedElement]) -> Dict[str, Any]:
        """Serialize element to dictionary"""
        elem = element.element if isinstance(element, HighlightedElement) else element
        
        data = {
            'id': getattr(elem, 'element_id', None),
            'type': getattr(elem, 'element_type', None),
            'text': getattr(elem, 'text', None),
            'content': getattr(elem, 'content', None)
        }
        
        if self.config.include_metadata:
            data.update({
                'created_at': getattr(elem, 'created_at', None),
                'updated_at': getattr(elem, 'updated_at', None),
                'metadata': getattr(elem, 'metadata', {})
            })
        
        if isinstance(element, HighlightedElement) and self.config.include_highlights:
            data.update({
                'highlighted_html': element.highlighted_html,
                'highlighted_text': element.highlighted_text,
                'match_count': element.total_matches,
                'matches': [match.to_dict() for match in element.matches]
            })
        
        if isinstance(element, HighlightedElement) and self.config.include_search_terms:
            data['search_terms'] = element.search_terms
        
        return data
    
    def _serialize_element_for_csv(self, element: Union[Element, HighlightedElement], columns: List[str]) -> List[str]:
        """Serialize element for CSV output"""
        elem = element.element if isinstance(element, HighlightedElement) else element
        
        row = []
        for col in columns:
            if col == 'id':
                row.append(str(getattr(elem, 'element_id', '')))
            elif col == 'type':
                row.append(str(getattr(elem, 'element_type', '')))
            elif col == 'text':
                row.append(str(getattr(elem, 'text', '')))
            elif col == 'content':
                row.append(str(getattr(elem, 'content', '')))
            elif col == 'created_at':
                row.append(str(getattr(elem, 'created_at', '')))
            elif col == 'updated_at':
                row.append(str(getattr(elem, 'updated_at', '')))
            elif col == 'metadata':
                row.append(str(getattr(elem, 'metadata', {})))
            elif col == 'highlighted_text' and isinstance(element, HighlightedElement):
                row.append(element.highlighted_text)
            elif col == 'match_count' and isinstance(element, HighlightedElement):
                row.append(str(element.total_matches))
            elif col == 'search_terms' and isinstance(element, HighlightedElement):
                row.append(', '.join(element.search_terms))
            else:
                row.append('')
        
        return row
    
    def _serialize_element_for_xml(self, element: Union[Element, HighlightedElement]) -> ET.Element:
        """Serialize element for XML output"""
        elem = element.element if isinstance(element, HighlightedElement) else element
        
        elem_xml = ET.Element('element')
        
        # Basic properties
        if hasattr(elem, 'element_id'):
            elem_xml.set('id', str(elem.element_id))
        if hasattr(elem, 'element_type'):
            elem_xml.set('type', str(elem.element_type))
        
        # Content
        if hasattr(elem, 'text') and elem.text:
            text_elem = ET.SubElement(elem_xml, 'text')
            text_elem.text = str(elem.text)
        
        if hasattr(elem, 'content') and elem.content:
            content_elem = ET.SubElement(elem_xml, 'content')
            content_elem.text = str(elem.content)
        
        # Metadata
        if self.config.include_metadata:
            if hasattr(elem, 'created_at') and elem.created_at:
                created_elem = ET.SubElement(elem_xml, 'created_at')
                created_elem.text = str(elem.created_at)
        
        # Highlighting
        if isinstance(element, HighlightedElement) and self.config.include_highlights:
            highlights_elem = ET.SubElement(elem_xml, 'highlights')
            highlights_elem.set('match_count', str(element.total_matches))
            
            highlighted_elem = ET.SubElement(highlights_elem, 'highlighted_text')
            highlighted_elem.text = element.highlighted_text
        
        return elem_xml
    
    def _serialize_element_for_html(self, element: Union[Element, HighlightedElement]) -> str:
        """Serialize element for HTML output"""
        elem = element.element if isinstance(element, HighlightedElement) else element
        
        html_parts = ['<div class="search-result">']
        
        # Header
        html_parts.append('<div class="result-header">')
        html_parts.append(f'<span class="result-id">{getattr(elem, "element_id", "N/A")}</span>')
        html_parts.append(f'<span class="result-type">{getattr(elem, "element_type", "N/A")}</span>')
        html_parts.append('</div>')
        
        # Content
        content = getattr(elem, 'text', '') or getattr(elem, 'content', '')
        if isinstance(element, HighlightedElement) and self.config.include_highlights:
            content = element.highlighted_html
        
        html_parts.append('<div class="result-content">')
        html_parts.append(content)
        html_parts.append('</div>')
        
        # Metadata
        if self.config.include_metadata:
            html_parts.append('<div class="result-metadata">')
            if hasattr(elem, 'created_at') and elem.created_at:
                html_parts.append(f'<span class="created-at">Created: {elem.created_at}</span>')
            html_parts.append('</div>')
        
        html_parts.append('</div>')
        
        return '\n'.join(html_parts)
    
    def _generate_html_template(self) -> str:
        """Generate HTML template"""
        css = ""
        if self.config.html_include_css:
            css = """
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .header { border-bottom: 2px solid #ddd; padding-bottom: 20px; margin-bottom: 30px; }
                .search-result { border: 1px solid #eee; padding: 15px; margin-bottom: 20px; border-radius: 5px; }
                .result-header { font-weight: bold; margin-bottom: 10px; color: #666; }
                .result-type { float: right; background: #f0f0f0; padding: 2px 8px; border-radius: 3px; font-size: 0.9em; }
                .result-content { line-height: 1.5; margin-bottom: 10px; }
                .result-metadata { font-size: 0.9em; color: #999; }
                mark { background-color: #ffff99; padding: 1px 2px; }
            </style>
            """
        
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Search Results Export</title>
            {css}
        </head>
        <body>
            <div class="header">
                <h1>Search Results Export</h1>
                <p>Generated: {{{{TIMESTAMP}}}}</p>
                <p>Total Elements: {{{{TOTAL_ELEMENTS}}}}</p>
            </div>
            <div class="results">
                {{{{ELEMENTS}}}}
            </div>
        </body>
        </html>
        """


class ExportDialog(QDialog):
    """Dialog for configuring and starting exports"""
    
    export_started = pyqtSignal(object)  # ExportConfiguration
    
    def __init__(self, elements: List[Union[Element, HighlightedElement]], parent=None):
        super().__init__(parent)
        
        self.elements = elements
        self.config = ExportConfiguration()
        self.exporter: Optional[ResultExporter] = None
        
        self.setWindowTitle("Export Search Results")
        self.setMinimumSize(500, 600)
        
        self._setup_ui()
        self._connect_signals()
        
        logger.debug(f"Export dialog opened for {len(elements)} elements")
    
    def _setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel(f"Export {len(self.elements)} search results")
        header.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Tabs for configuration
        tabs = QTabWidget()
        
        # Basic options tab
        basic_tab = self._create_basic_tab()
        tabs.addTab(basic_tab, "Basic")
        
        # Format options tab
        format_tab = self._create_format_tab()
        tabs.addTab(format_tab, "Format Options")
        
        # Filters tab
        filters_tab = self._create_filters_tab()
        tabs.addTab(filters_tab, "Filters")
        
        layout.addWidget(tabs)
        
        # Progress area
        self.progress_widget = QWidget()
        progress_layout = QVBoxLayout(self.progress_widget)
        
        self.progress_label = QLabel("Ready to export")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(self.progress_widget)
        
        # Buttons
        buttons = QDialogButtonBox()
        
        self.export_button = QPushButton("Export")
        self.export_button.setDefault(True)
        buttons.addButton(self.export_button, QDialogButtonBox.ButtonRole.AcceptRole)
        
        self.cancel_button = QPushButton("Cancel")
        buttons.addButton(self.cancel_button, QDialogButtonBox.ButtonRole.RejectRole)
        
        layout.addWidget(buttons)
    
    def _create_basic_tab(self) -> QWidget:
        """Create basic options tab"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Format selection
        format_group = QGroupBox("Export Format")
        format_layout = QVBoxLayout(format_group)
        
        self.format_buttons = {}
        for fmt in ExportFormat:
            radio = QRadioButton(fmt.value.upper())
            if fmt == ExportFormat.JSON:  # Default selection
                radio.setChecked(True)
            self.format_buttons[fmt] = radio
            format_layout.addWidget(radio)
        
        layout.addRow(format_group)
        
        # Content options
        content_group = QGroupBox("Content Options")
        content_layout = QVBoxLayout(content_group)
        
        self.include_metadata_cb = QCheckBox("Include metadata")
        self.include_metadata_cb.setChecked(True)
        content_layout.addWidget(self.include_metadata_cb)
        
        self.include_highlights_cb = QCheckBox("Include search highlights")
        self.include_highlights_cb.setChecked(True)
        content_layout.addWidget(self.include_highlights_cb)
        
        self.include_search_terms_cb = QCheckBox("Include search terms")
        self.include_search_terms_cb.setChecked(True)
        content_layout.addWidget(self.include_search_terms_cb)
        
        self.include_statistics_cb = QCheckBox("Include export statistics")
        content_layout.addWidget(self.include_statistics_cb)
        
        layout.addRow(content_group)
        
        return widget
    
    def _create_format_tab(self) -> QWidget:
        """Create format-specific options tab"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # JSON options
        json_group = QGroupBox("JSON Options")
        json_layout = QFormLayout(json_group)
        
        self.json_pretty_cb = QCheckBox("Pretty formatting")
        self.json_pretty_cb.setChecked(True)
        json_layout.addRow(self.json_pretty_cb)
        
        self.json_indent_spin = QSpinBox()
        self.json_indent_spin.setRange(0, 8)
        self.json_indent_spin.setValue(2)
        json_layout.addRow("Indent size:", self.json_indent_spin)
        
        layout.addRow(json_group)
        
        # CSV options
        csv_group = QGroupBox("CSV Options")
        csv_layout = QFormLayout(csv_group)
        
        self.csv_delimiter_edit = QLineEdit(",")
        csv_layout.addRow("Delimiter:", self.csv_delimiter_edit)
        
        self.csv_quote_edit = QLineEdit('"')
        csv_layout.addRow("Quote character:", self.csv_quote_edit)
        
        layout.addRow(csv_group)
        
        # HTML options
        html_group = QGroupBox("HTML Options")
        html_layout = QVBoxLayout(html_group)
        
        self.html_include_css_cb = QCheckBox("Include CSS styling")
        self.html_include_css_cb.setChecked(True)
        html_layout.addWidget(self.html_include_css_cb)
        
        self.html_inline_styles_cb = QCheckBox("Use inline styles")
        html_layout.addWidget(self.html_inline_styles_cb)
        
        layout.addRow(html_group)
        
        return widget
    
    def _create_filters_tab(self) -> QWidget:
        """Create filters tab"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Element limit
        self.max_elements_cb = QCheckBox("Limit number of elements")
        layout.addRow(self.max_elements_cb)
        
        self.max_elements_spin = QSpinBox()
        self.max_elements_spin.setRange(1, 100000)
        self.max_elements_spin.setValue(1000)
        self.max_elements_spin.setEnabled(False)
        layout.addRow("Max elements:", self.max_elements_spin)
        
        # Element types filter
        types_group = QGroupBox("Element Types (leave empty for all)")
        types_layout = QVBoxLayout(types_group)
        
        self.element_types_edit = QLineEdit()
        self.element_types_edit.setPlaceholderText("e.g., text, image, table (comma-separated)")
        types_layout.addWidget(self.element_types_edit)
        
        layout.addRow(types_group)
        
        # Advanced options
        advanced_group = QGroupBox("Advanced Options")
        advanced_layout = QVBoxLayout(advanced_group)
        
        self.compress_output_cb = QCheckBox("Compress output file")
        advanced_layout.addWidget(self.compress_output_cb)
        
        self.split_large_files_cb = QCheckBox("Split large files")
        advanced_layout.addWidget(self.split_large_files_cb)
        
        layout.addRow(advanced_group)
        
        return widget
    
    def _connect_signals(self):
        """Connect UI signals"""
        self.export_button.clicked.connect(self.start_export)
        self.cancel_button.clicked.connect(self.reject)
        
        # Enable/disable options based on selection
        self.max_elements_cb.toggled.connect(self.max_elements_spin.setEnabled)
    
    def start_export(self):
        """Start the export process"""
        # Collect configuration
        self._collect_configuration()
        
        # Get output file
        output_path = self._get_output_path()
        if not output_path:
            return
        
        # Start export
        self.exporter = ResultExporter(self.elements, self.config, output_path)
        self.exporter.progress_updated.connect(self._on_progress_updated)
        self.exporter.stage_changed.connect(self._on_stage_changed)
        self.exporter.export_completed.connect(self._on_export_completed)
        self.exporter.export_failed.connect(self._on_export_failed)
        
        # Update UI
        self.export_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        
        # Start export
        self.exporter.start()
        self.export_started.emit(self.config)
        
        logger.info(f"Export started: {self.config.format.value} to {output_path}")
    
    def _collect_configuration(self):
        """Collect configuration from UI"""
        # Format
        for fmt, button in self.format_buttons.items():
            if button.isChecked():
                self.config.format = fmt
                break
        
        # Content options
        self.config.include_metadata = self.include_metadata_cb.isChecked()
        self.config.include_highlights = self.include_highlights_cb.isChecked()
        self.config.include_search_terms = self.include_search_terms_cb.isChecked()
        self.config.include_statistics = self.include_statistics_cb.isChecked()
        
        # Format-specific options
        self.config.json_pretty = self.json_pretty_cb.isChecked()
        self.config.json_indent = self.json_indent_spin.value()
        self.config.csv_delimiter = self.csv_delimiter_edit.text()
        self.config.csv_quote_char = self.csv_quote_edit.text()
        self.config.html_include_css = self.html_include_css_cb.isChecked()
        self.config.html_inline_styles = self.html_inline_styles_cb.isChecked()
        
        # Filters
        if self.max_elements_cb.isChecked():
            self.config.max_elements = self.max_elements_spin.value()
        
        element_types_text = self.element_types_edit.text().strip()
        if element_types_text:
            self.config.element_types_filter = [t.strip() for t in element_types_text.split(',')]
        
        self.config.compress_output = self.compress_output_cb.isChecked()
        self.config.split_large_files = self.split_large_files_cb.isChecked()
    
    def _get_output_path(self) -> Optional[str]:
        """Get output file path from user"""
        format_ext = self.config.format.value
        file_filter = f"{format_ext.upper()} files (*.{format_ext});;All files (*.*)"
        
        output_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Export File",
            f"search_results.{format_ext}",
            file_filter
        )
        
        return output_path if output_path else None
    
    def _on_progress_updated(self, progress: ExportProgress):
        """Handle progress updates"""
        self.progress_bar.setValue(int(progress.progress_percentage))
    
    def _on_stage_changed(self, stage: str):
        """Handle stage changes"""
        self.progress_label.setText(stage)
    
    def _on_export_completed(self, output_file: str):
        """Handle export completion"""
        self.progress_bar.setVisible(False)
        self.progress_label.setText(f"Export completed: {output_file}")
        
        QMessageBox.information(
            self,
            "Export Complete",
            f"Search results exported successfully to:\n{output_file}"
        )
        
        self.accept()
    
    def _on_export_failed(self, error: str):
        """Handle export failure"""
        self.progress_bar.setVisible(False)
        self.progress_label.setText(f"Export failed: {error}")
        self.export_button.setEnabled(True)
        
        QMessageBox.critical(
            self,
            "Export Failed",
            f"Export failed with error:\n{error}"
        )


# Factory functions for easy use
def export_elements(elements: List[Union[Element, HighlightedElement]], 
                   format: ExportFormat = ExportFormat.JSON,
                   output_path: str = "search_results",
                   **config_kwargs) -> str:
    """Quick export function for elements"""
    config = ExportConfiguration(format=format, **config_kwargs)
    
    if not output_path.endswith(f'.{format.value}'):
        output_path += f'.{format.value}'
    
    exporter = ResultExporter(elements, config, output_path)
    exporter.run()  # Synchronous execution
    
    return output_path


def show_export_dialog(elements: List[Union[Element, HighlightedElement]], 
                      parent=None) -> Optional[ExportDialog]:
    """Show export configuration dialog"""
    if not elements:
        QMessageBox.warning(parent, "No Results", "No search results to export.")
        return None
    
    dialog = ExportDialog(elements, parent)
    return dialog