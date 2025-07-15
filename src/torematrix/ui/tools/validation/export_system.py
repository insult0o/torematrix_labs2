"""
Export System for Hierarchy Management

Agent 4 implementation for Issue #245 - Export System for structured document elements.
Provides comprehensive export functionality with multiple format support.
"""

import json
import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
import io
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path
import asyncio

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTextEdit, QProgressBar, QCheckBox, QGroupBox, QFormLayout, QLineEdit,
    QSpinBox, QTabWidget, QTreeWidget, QTreeWidgetItem, QFileDialog,
    QMessageBox, QSplitter, QFrame, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette

from torematrix.core.models.element import Element, ElementType
from torematrix.core.operations.hierarchy import HierarchyManager
from torematrix.core.state import StateStore
from torematrix.core.events import EventBus
from torematrix.utils.geometry import Rect


logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """Supported export formats."""
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    HTML = "html"
    MARKDOWN = "markdown"
    DOCX = "docx"
    PDF = "pdf"
    XLSX = "xlsx"
    TXT = "txt"
    YAML = "yaml"


class ExportScope(Enum):
    """Export scope options."""
    ALL_ELEMENTS = "all_elements"
    SELECTED_ELEMENTS = "selected_elements"
    CURRENT_PAGE = "current_page"
    HIERARCHY_BRANCH = "hierarchy_branch"
    FILTERED_ELEMENTS = "filtered_elements"


class ExportStatus(Enum):
    """Export operation status."""
    PENDING = "pending"
    PREPARING = "preparing"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExportOptions:
    """Export configuration options."""
    format: ExportFormat = ExportFormat.JSON
    scope: ExportScope = ExportScope.ALL_ELEMENTS
    include_metadata: bool = True
    include_coordinates: bool = True
    include_hierarchy: bool = True
    include_relationships: bool = True
    include_text: bool = True
    include_images: bool = False
    flatten_hierarchy: bool = False
    custom_fields: List[str] = field(default_factory=list)
    filter_types: List[ElementType] = field(default_factory=list)
    max_text_length: int = -1  # -1 means no limit
    encoding: str = "utf-8"
    pretty_print: bool = True
    compression: bool = False
    output_path: str = ""
    template_path: str = ""
    additional_options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExportResult:
    """Result of export operation."""
    success: bool
    export_path: str
    format: ExportFormat
    element_count: int
    file_size: int
    execution_time: float
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExportEngine:
    """Core export engine for multiple formats."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".ExportEngine")
        self.supported_formats = {
            ExportFormat.JSON: self._export_json,
            ExportFormat.XML: self._export_xml,
            ExportFormat.CSV: self._export_csv,
            ExportFormat.HTML: self._export_html,
            ExportFormat.MARKDOWN: self._export_markdown,
            ExportFormat.TXT: self._export_txt,
            ExportFormat.YAML: self._export_yaml,
        }
    
    def export(self, elements: List[Element], options: ExportOptions) -> ExportResult:
        """Export elements using specified options."""
        start_time = datetime.now()
        
        try:
            # Validate options
            if not self._validate_options(options):
                return ExportResult(
                    success=False,
                    export_path="",
                    format=options.format,
                    element_count=0,
                    file_size=0,
                    execution_time=0.0,
                    error_message="Invalid export options"
                )
            
            # Filter elements based on scope
            filtered_elements = self._filter_elements(elements, options)
            
            # Export using appropriate handler
            if options.format in self.supported_formats:
                export_data = self.supported_formats[options.format](filtered_elements, options)
                
                # Write to file
                file_size = self._write_to_file(export_data, options)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return ExportResult(
                    success=True,
                    export_path=options.output_path,
                    format=options.format,
                    element_count=len(filtered_elements),
                    file_size=file_size,
                    execution_time=execution_time
                )
            else:
                return ExportResult(
                    success=False,
                    export_path="",
                    format=options.format,
                    element_count=0,
                    file_size=0,
                    execution_time=0.0,
                    error_message=f"Unsupported format: {options.format}"
                )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ExportResult(
                success=False,
                export_path="",
                format=options.format,
                element_count=0,
                file_size=0,
                execution_time=execution_time,
                error_message=str(e)
            )
    
    def _validate_options(self, options: ExportOptions) -> bool:
        """Validate export options."""
        if not options.output_path:
            return False
        
        if options.format not in self.supported_formats:
            return False
        
        return True
    
    def _filter_elements(self, elements: List[Element], options: ExportOptions) -> List[Element]:
        """Filter elements based on export options."""
        filtered = elements
        
        # Filter by element types if specified
        if options.filter_types:
            filtered = [elem for elem in filtered if elem.element_type in options.filter_types]
        
        # Apply scope filtering
        if options.scope == ExportScope.SELECTED_ELEMENTS:
            # Would need selection info from UI
            pass
        elif options.scope == ExportScope.CURRENT_PAGE:
            # Would need page info
            pass
        elif options.scope == ExportScope.HIERARCHY_BRANCH:
            # Would need hierarchy info
            pass
        
        return filtered
    
    def _export_json(self, elements: List[Element], options: ExportOptions) -> str:
        """Export elements to JSON format."""
        data = {
            "export_info": {
                "format": "json",
                "timestamp": datetime.now().isoformat(),
                "element_count": len(elements),
                "options": {
                    "include_metadata": options.include_metadata,
                    "include_coordinates": options.include_coordinates,
                    "include_hierarchy": options.include_hierarchy,
                    "include_relationships": options.include_relationships,
                }
            },
            "elements": []
        }
        
        for element in elements:
            element_data = {
                "id": element.id,
                "type": element.element_type.value if element.element_type else "unknown",
                "text": element.text[:options.max_text_length] if options.max_text_length > 0 else element.text
            }
            
            if options.include_coordinates and element.bounds:
                element_data["coordinates"] = {
                    "x": element.bounds.x,
                    "y": element.bounds.y,
                    "width": element.bounds.width,
                    "height": element.bounds.height
                }
            
            if options.include_hierarchy:
                element_data["parent_id"] = element.parent_id
                element_data["children"] = element.children
            
            if options.include_metadata and element.metadata:
                element_data["metadata"] = element.metadata
            
            data["elements"].append(element_data)
        
        return json.dumps(data, indent=2 if options.pretty_print else None, ensure_ascii=False)
    
    def _export_xml(self, elements: List[Element], options: ExportOptions) -> str:
        """Export elements to XML format."""
        root = ET.Element("document")
        
        # Add export info
        export_info = ET.SubElement(root, "export_info")
        ET.SubElement(export_info, "format").text = "xml"
        ET.SubElement(export_info, "timestamp").text = datetime.now().isoformat()
        ET.SubElement(export_info, "element_count").text = str(len(elements))
        
        # Add elements
        elements_elem = ET.SubElement(root, "elements")
        
        for element in elements:
            elem_node = ET.SubElement(elements_elem, "element")
            elem_node.set("id", element.id)
            elem_node.set("type", element.element_type.value if element.element_type else "unknown")
            
            if options.include_text:
                text_elem = ET.SubElement(elem_node, "text")
                text_elem.text = element.text[:options.max_text_length] if options.max_text_length > 0 else element.text
            
            if options.include_coordinates and element.bounds:
                coords_elem = ET.SubElement(elem_node, "coordinates")
                coords_elem.set("x", str(element.bounds.x))
                coords_elem.set("y", str(element.bounds.y))
                coords_elem.set("width", str(element.bounds.width))
                coords_elem.set("height", str(element.bounds.height))
            
            if options.include_hierarchy:
                if element.parent_id:
                    hierarchy_elem = ET.SubElement(elem_node, "hierarchy")
                    hierarchy_elem.set("parent_id", element.parent_id)
                
                if element.children:
                    children_elem = ET.SubElement(elem_node, "children")
                    for child_id in element.children:
                        child_elem = ET.SubElement(children_elem, "child")
                        child_elem.set("id", child_id)
        
        # Pretty print if requested
        if options.pretty_print:
            rough_string = ET.tostring(root, encoding='unicode')
            reparsed = minidom.parseString(rough_string)
            return reparsed.toprettyxml(indent="  ")
        else:
            return ET.tostring(root, encoding='unicode')
    
    def _export_csv(self, elements: List[Element], options: ExportOptions) -> str:
        """Export elements to CSV format."""
        output = io.StringIO()
        
        # Prepare headers
        headers = ["id", "type", "text"]
        if options.include_coordinates:
            headers.extend(["x", "y", "width", "height"])
        if options.include_hierarchy:
            headers.extend(["parent_id", "children"])
        if options.include_metadata:
            headers.append("metadata")
        
        writer = csv.writer(output)
        writer.writerow(headers)
        
        # Write elements
        for element in elements:
            row = [
                element.id,
                element.element_type.value if element.element_type else "unknown",
                element.text[:options.max_text_length] if options.max_text_length > 0 else element.text
            ]
            
            if options.include_coordinates:
                if element.bounds:
                    row.extend([element.bounds.x, element.bounds.y, element.bounds.width, element.bounds.height])
                else:
                    row.extend(["", "", "", ""])
            
            if options.include_hierarchy:
                row.append(element.parent_id or "")
                row.append("|".join(element.children) if element.children else "")
            
            if options.include_metadata:
                row.append(json.dumps(element.metadata) if element.metadata else "")
            
            writer.writerow(row)
        
        return output.getvalue()
    
    def _export_html(self, elements: List[Element], options: ExportOptions) -> str:
        """Export elements to HTML format."""
        html_parts = [
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            '<meta charset="utf-8">',
            '<title>Document Export</title>',
            '<style>',
            'body { font-family: Arial, sans-serif; margin: 20px; }',
            '.element { margin: 10px 0; padding: 10px; border: 1px solid #ccc; }',
            '.element-header { font-weight: bold; margin-bottom: 5px; }',
            '.element-text { margin: 5px 0; }',
            '.element-metadata { font-size: 0.9em; color: #666; }',
            '</style>',
            '</head>',
            '<body>',
            f'<h1>Document Export</h1>',
            f'<p>Exported on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>',
            f'<p>Total elements: {len(elements)}</p>',
            '<hr>'
        ]
        
        for element in elements:
            html_parts.append('<div class="element">')
            html_parts.append(f'<div class="element-header">Element: {element.id} ({element.element_type.value if element.element_type else "unknown"})</div>')
            
            if options.include_text:
                text = element.text[:options.max_text_length] if options.max_text_length > 0 else element.text
                html_parts.append(f'<div class="element-text">{text}</div>')
            
            if options.include_coordinates and element.bounds:
                html_parts.append(f'<div class="element-metadata">Coordinates: ({element.bounds.x}, {element.bounds.y}, {element.bounds.width}, {element.bounds.height})</div>')
            
            if options.include_hierarchy:
                if element.parent_id:
                    html_parts.append(f'<div class="element-metadata">Parent: {element.parent_id}</div>')
                if element.children:
                    html_parts.append(f'<div class="element-metadata">Children: {", ".join(element.children)}</div>')
            
            html_parts.append('</div>')
        
        html_parts.extend(['</body>', '</html>'])
        
        return '\n'.join(html_parts)
    
    def _export_markdown(self, elements: List[Element], options: ExportOptions) -> str:
        """Export elements to Markdown format."""
        md_parts = [
            '# Document Export',
            f'Exported on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            f'Total elements: {len(elements)}',
            '---',
            ''
        ]
        
        for element in elements:
            # Element header
            md_parts.append(f'## Element: {element.id}')
            md_parts.append(f'**Type:** {element.element_type.value if element.element_type else "unknown"}')
            md_parts.append('')
            
            # Element text
            if options.include_text:
                text = element.text[:options.max_text_length] if options.max_text_length > 0 else element.text
                md_parts.append(f'**Text:** {text}')
                md_parts.append('')
            
            # Coordinates
            if options.include_coordinates and element.bounds:
                md_parts.append(f'**Coordinates:** ({element.bounds.x}, {element.bounds.y}, {element.bounds.width}, {element.bounds.height})')
                md_parts.append('')
            
            # Hierarchy
            if options.include_hierarchy:
                if element.parent_id:
                    md_parts.append(f'**Parent:** {element.parent_id}')
                if element.children:
                    md_parts.append(f'**Children:** {", ".join(element.children)}')
                md_parts.append('')
            
            md_parts.append('---')
            md_parts.append('')
        
        return '\n'.join(md_parts)
    
    def _export_txt(self, elements: List[Element], options: ExportOptions) -> str:
        """Export elements to plain text format."""
        text_parts = [
            'Document Export',
            f'Exported on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            f'Total elements: {len(elements)}',
            '=' * 50,
            ''
        ]
        
        for i, element in enumerate(elements, 1):
            text_parts.append(f'Element {i}: {element.id}')
            text_parts.append(f'Type: {element.element_type.value if element.element_type else "unknown"}')
            
            if options.include_text:
                text = element.text[:options.max_text_length] if options.max_text_length > 0 else element.text
                text_parts.append(f'Text: {text}')
            
            if options.include_coordinates and element.bounds:
                text_parts.append(f'Coordinates: ({element.bounds.x}, {element.bounds.y}, {element.bounds.width}, {element.bounds.height})')
            
            if options.include_hierarchy:
                if element.parent_id:
                    text_parts.append(f'Parent: {element.parent_id}')
                if element.children:
                    text_parts.append(f'Children: {", ".join(element.children)}')
            
            text_parts.append('-' * 30)
            text_parts.append('')
        
        return '\n'.join(text_parts)
    
    def _export_yaml(self, elements: List[Element], options: ExportOptions) -> str:
        """Export elements to YAML format."""
        try:
            import yaml
            
            data = {
                "export_info": {
                    "format": "yaml",
                    "timestamp": datetime.now().isoformat(),
                    "element_count": len(elements),
                    "options": {
                        "include_metadata": options.include_metadata,
                        "include_coordinates": options.include_coordinates,
                        "include_hierarchy": options.include_hierarchy,
                        "include_relationships": options.include_relationships,
                    }
                },
                "elements": []
            }
            
            for element in elements:
                element_data = {
                    "id": element.id,
                    "type": element.element_type.value if element.element_type else "unknown",
                    "text": element.text[:options.max_text_length] if options.max_text_length > 0 else element.text
                }
                
                if options.include_coordinates and element.bounds:
                    element_data["coordinates"] = {
                        "x": element.bounds.x,
                        "y": element.bounds.y,
                        "width": element.bounds.width,
                        "height": element.bounds.height
                    }
                
                if options.include_hierarchy:
                    if element.parent_id:
                        element_data["parent_id"] = element.parent_id
                    if element.children:
                        element_data["children"] = element.children
                
                if options.include_metadata and element.metadata:
                    element_data["metadata"] = element.metadata
                
                data["elements"].append(element_data)
            
            return yaml.dump(data, default_flow_style=False, allow_unicode=True)
            
        except ImportError:
            # Fallback to JSON if yaml not available
            return self._export_json(elements, options)
    
    def _write_to_file(self, data: str, options: ExportOptions) -> int:
        """Write data to file and return file size."""
        with open(options.output_path, 'w', encoding=options.encoding) as f:
            f.write(data)
        
        return len(data.encode(options.encoding))


class ExportWidget(QWidget):
    """Main export widget for hierarchy management."""
    
    # Signals
    export_started = pyqtSignal(ExportOptions)
    export_completed = pyqtSignal(ExportResult)
    export_progress = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hierarchy_manager: Optional[HierarchyManager] = None
        self.state_store: Optional[StateStore] = None
        self.event_bus: Optional[EventBus] = None
        
        self.export_engine = ExportEngine()
        self.current_elements: List[Element] = []
        self.export_options = ExportOptions()
        
        self._setup_ui()
        self._setup_connections()
        
        logger.info("Export widget initialized")
    
    def _setup_ui(self):
        """Setup the export UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Export System")
        header_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(header_label)
        
        # Main content
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Options
        options_widget = self._create_options_widget()
        content_splitter.addWidget(options_widget)
        
        # Right panel - Preview
        preview_widget = self._create_preview_widget()
        content_splitter.addWidget(preview_widget)
        
        content_splitter.setSizes([400, 600])
        layout.addWidget(content_splitter)
        
        # Progress and controls
        controls_frame = QFrame()
        controls_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        controls_layout = QVBoxLayout(controls_frame)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        controls_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready to export")
        controls_layout.addWidget(self.status_label)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.preview_button = QPushButton("Preview")
        self.preview_button.clicked.connect(self._preview_export)
        button_layout.addWidget(self.preview_button)
        
        self.export_button = QPushButton("Export")
        self.export_button.clicked.connect(self._start_export)
        button_layout.addWidget(self.export_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._cancel_export)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)
        
        controls_layout.addLayout(button_layout)
        
        layout.addWidget(controls_frame)
    
    def _create_options_widget(self) -> QWidget:
        """Create export options widget."""
        options_widget = QWidget()
        layout = QVBoxLayout(options_widget)
        
        # Format selection
        format_group = QGroupBox("Export Format")
        format_layout = QFormLayout(format_group)
        
        self.format_combo = QComboBox()
        for format_type in ExportFormat:
            self.format_combo.addItem(format_type.value.upper(), format_type)
        format_layout.addRow("Format:", self.format_combo)
        
        layout.addWidget(format_group)
        
        # Scope selection
        scope_group = QGroupBox("Export Scope")
        scope_layout = QFormLayout(scope_group)
        
        self.scope_combo = QComboBox()
        for scope in ExportScope:
            self.scope_combo.addItem(scope.value.replace("_", " ").title(), scope)
        scope_layout.addRow("Scope:", self.scope_combo)
        
        layout.addWidget(scope_group)
        
        # Include options
        include_group = QGroupBox("Include Options")
        include_layout = QFormLayout(include_group)
        
        self.include_metadata_cb = QCheckBox("Include Metadata")
        self.include_metadata_cb.setChecked(True)
        include_layout.addRow("Metadata:", self.include_metadata_cb)
        
        self.include_coordinates_cb = QCheckBox("Include Coordinates")
        self.include_coordinates_cb.setChecked(True)
        include_layout.addRow("Coordinates:", self.include_coordinates_cb)
        
        self.include_hierarchy_cb = QCheckBox("Include Hierarchy")
        self.include_hierarchy_cb.setChecked(True)
        include_layout.addRow("Hierarchy:", self.include_hierarchy_cb)
        
        self.include_relationships_cb = QCheckBox("Include Relationships")
        self.include_relationships_cb.setChecked(True)
        include_layout.addRow("Relationships:", self.include_relationships_cb)
        
        layout.addWidget(include_group)
        
        # Text options
        text_group = QGroupBox("Text Options")
        text_layout = QFormLayout(text_group)
        
        self.max_text_length_spin = QSpinBox()
        self.max_text_length_spin.setRange(-1, 10000)
        self.max_text_length_spin.setValue(-1)
        self.max_text_length_spin.setSpecialValueText("No limit")
        text_layout.addRow("Max text length:", self.max_text_length_spin)
        
        self.pretty_print_cb = QCheckBox("Pretty Print")
        self.pretty_print_cb.setChecked(True)
        text_layout.addRow("Formatting:", self.pretty_print_cb)
        
        layout.addWidget(text_group)
        
        # Output options
        output_group = QGroupBox("Output Options")
        output_layout = QVBoxLayout(output_group)
        
        path_layout = QHBoxLayout()
        self.output_path_edit = QLineEdit()
        path_layout.addWidget(self.output_path_edit)
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_output_path)
        path_layout.addWidget(browse_button)
        
        output_layout.addLayout(path_layout)
        
        layout.addWidget(output_group)
        
        layout.addStretch()
        
        return options_widget
    
    def _create_preview_widget(self) -> QWidget:
        """Create export preview widget."""
        preview_widget = QWidget()
        layout = QVBoxLayout(preview_widget)
        
        # Preview header
        preview_label = QLabel("Export Preview")
        preview_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(preview_label)
        
        # Preview tabs
        self.preview_tabs = QTabWidget()
        
        # Elements tab
        elements_tab = QWidget()
        elements_layout = QVBoxLayout(elements_tab)
        
        self.elements_tree = QTreeWidget()
        self.elements_tree.setHeaderLabels(["Element", "Type", "Text Preview"])
        elements_layout.addWidget(self.elements_tree)
        
        self.preview_tabs.addTab(elements_tab, "Elements")
        
        # Output tab
        output_tab = QWidget()
        output_layout = QVBoxLayout(output_tab)
        
        self.output_preview = QTextEdit()
        self.output_preview.setReadOnly(True)
        self.output_preview.setFont(QFont("Courier", 10))
        output_layout.addWidget(self.output_preview)
        
        self.preview_tabs.addTab(output_tab, "Output Preview")
        
        layout.addWidget(self.preview_tabs)
        
        return preview_widget
    
    def _setup_connections(self):
        """Setup signal connections."""
        self.format_combo.currentTextChanged.connect(self._update_options)
        self.scope_combo.currentTextChanged.connect(self._update_options)
        self.include_metadata_cb.toggled.connect(self._update_options)
        self.include_coordinates_cb.toggled.connect(self._update_options)
        self.include_hierarchy_cb.toggled.connect(self._update_options)
        self.include_relationships_cb.toggled.connect(self._update_options)
        self.max_text_length_spin.valueChanged.connect(self._update_options)
        self.pretty_print_cb.toggled.connect(self._update_options)
        self.output_path_edit.textChanged.connect(self._update_options)
    
    def set_hierarchy_manager(self, manager: HierarchyManager):
        """Set the hierarchy manager."""
        self.hierarchy_manager = manager
    
    def set_state_store(self, store: StateStore):
        """Set the state store."""
        self.state_store = store
    
    def set_event_bus(self, event_bus: EventBus):
        """Set the event bus."""
        self.event_bus = event_bus
    
    def show_elements(self, elements: List[Element]):
        """Show elements for export."""
        self.current_elements = elements
        self._update_elements_display()
        self._update_preview()
        
        logger.info(f"Showing {len(elements)} elements for export")
    
    def _update_options(self):
        """Update export options based on UI."""
        # Format
        format_data = self.format_combo.currentData()
        if format_data:
            self.export_options.format = format_data
        
        # Scope
        scope_data = self.scope_combo.currentData()
        if scope_data:
            self.export_options.scope = scope_data
        
        # Include options
        self.export_options.include_metadata = self.include_metadata_cb.isChecked()
        self.export_options.include_coordinates = self.include_coordinates_cb.isChecked()
        self.export_options.include_hierarchy = self.include_hierarchy_cb.isChecked()
        self.export_options.include_relationships = self.include_relationships_cb.isChecked()
        
        # Text options
        self.export_options.max_text_length = self.max_text_length_spin.value()
        self.export_options.pretty_print = self.pretty_print_cb.isChecked()
        
        # Output path
        self.export_options.output_path = self.output_path_edit.text()
        
        # Update preview
        self._update_preview()
    
    def _update_elements_display(self):
        """Update elements display."""
        self.elements_tree.clear()
        
        for element in self.current_elements:
            item = QTreeWidgetItem([
                element.id,
                element.element_type.value if element.element_type else "unknown",
                element.text[:50] + "..." if len(element.text) > 50 else element.text
            ])
            self.elements_tree.addTopLevelItem(item)
    
    def _update_preview(self):
        """Update export preview."""
        if not self.current_elements:
            self.output_preview.setText("No elements to preview")
            return
        
        try:
            preview_data = self.export_engine.supported_formats[self.export_options.format](
                self.current_elements[:5],  # Preview first 5 elements
                self.export_options
            )
            
            # Truncate preview if too long
            if len(preview_data) > 10000:
                preview_data = preview_data[:10000] + "\n... (truncated)"
            
            self.output_preview.setText(preview_data)
            
        except Exception as e:
            self.output_preview.setText(f"Preview error: {str(e)}")
    
    def _browse_output_path(self):
        """Browse for output path."""
        format_ext = self.export_options.format.value
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Output Path",
            f"export.{format_ext}",
            f"{format_ext.upper()} Files (*.{format_ext});;All Files (*)"
        )
        if file_path:
            self.output_path_edit.setText(file_path)
    
    def _preview_export(self):
        """Preview export without saving."""
        self._update_preview()
        self.preview_tabs.setCurrentIndex(1)  # Switch to output preview tab
    
    def _start_export(self):
        """Start export process."""
        if not self.current_elements:
            QMessageBox.warning(self, "Export Error", "No elements to export")
            return
        
        if not self.export_options.output_path:
            QMessageBox.warning(self, "Export Error", "Please specify output path")
            return
        
        self.export_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting export...")
        
        # Create export thread
        self.export_thread = ExportThread(
            self.current_elements,
            self.export_options,
            self.export_engine
        )
        self.export_thread.progress_updated.connect(self.progress_bar.setValue)
        self.export_thread.status_updated.connect(self.status_label.setText)
        self.export_thread.export_completed.connect(self._on_export_completed)
        self.export_thread.start()
        
        self.export_started.emit(self.export_options)
    
    def _cancel_export(self):
        """Cancel export process."""
        if hasattr(self, 'export_thread'):
            self.export_thread.terminate()
        
        self.export_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Export cancelled")
    
    def _on_export_completed(self, result: ExportResult):
        """Handle export completion."""
        self.export_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        if result.success:
            self.progress_bar.setValue(100)
            self.status_label.setText(f"Export completed: {result.export_path}")
            
            # Show success message
            QMessageBox.information(
                self,
                "Export Complete",
                f"Export completed successfully!\n\nFile: {result.export_path}\nElements: {result.element_count}\nSize: {result.file_size} bytes\nTime: {result.execution_time:.2f} seconds"
            )
        else:
            self.progress_bar.setValue(0)
            self.status_label.setText(f"Export failed: {result.error_message}")
            
            # Show error message
            QMessageBox.critical(
                self,
                "Export Error",
                f"Export failed!\n\nError: {result.error_message}"
            )
        
        self.export_completed.emit(result)


class ExportThread(QThread):
    """Thread for export operations."""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    export_completed = pyqtSignal(ExportResult)
    
    def __init__(self, elements: List[Element], options: ExportOptions, engine: ExportEngine):
        super().__init__()
        self.elements = elements
        self.options = options
        self.engine = engine
    
    def run(self):
        """Run the export."""
        try:
            self.status_updated.emit("Preparing export...")
            self.progress_updated.emit(25)
            
            self.status_updated.emit("Exporting elements...")
            self.progress_updated.emit(50)
            
            result = self.engine.export(self.elements, self.options)
            
            self.status_updated.emit("Export completed!")
            self.progress_updated.emit(100)
            
            self.export_completed.emit(result)
            
        except Exception as e:
            error_result = ExportResult(
                success=False,
                export_path="",
                format=self.options.format,
                element_count=0,
                file_size=0,
                execution_time=0.0,
                error_message=str(e)
            )
            self.export_completed.emit(error_result)