"""Property Import/Export Manager

Handles importing and exporting property data in multiple formats for
backup, sharing, and bulk operations.
"""

from typing import Dict, List, Any, Optional, Union, IO
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import json
import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
import pickle
from datetime import datetime
from io import StringIO
import time

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QComboBox, QCheckBox, QProgressBar, QTextEdit, QFileDialog, QMessageBox,
    QDialog, QDialogButtonBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QTreeWidget, QTreeWidgetItem, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QObject, QTimer
from PyQt6.QtGui import QFont, QIcon


class ImportExportFormat(Enum):
    """Supported import/export formats"""
    JSON = "json"
    CSV = "csv"
    XML = "xml"
    PICKLE = "pickle"
    
    @property
    def extension(self) -> str:
        """Get file extension for format"""
        extensions = {
            ImportExportFormat.JSON: ".json",
            ImportExportFormat.CSV: ".csv",
            ImportExportFormat.XML: ".xml",
            ImportExportFormat.PICKLE: ".pkl"
        }
        return extensions[self]
    
    @property
    def description(self) -> str:
        """Get human readable description"""
        descriptions = {
            ImportExportFormat.JSON: "JSON - JavaScript Object Notation",
            ImportExportFormat.CSV: "CSV - Comma Separated Values",
            ImportExportFormat.XML: "XML - Extensible Markup Language",
            ImportExportFormat.PICKLE: "Pickle - Python Binary Format"
        }
        return descriptions[self]


@dataclass
class ExportConfiguration:
    """Configuration for export operations"""
    format: ImportExportFormat
    include_metadata: bool = True
    include_empty_values: bool = False
    flatten_nested: bool = False
    element_filter: Optional[str] = None  # Filter expression
    property_filter: Optional[List[str]] = None  # Specific properties to export
    custom_fields: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_fields is None:
            self.custom_fields = {}
        if self.property_filter is None:
            self.property_filter = []


@dataclass
class ImportConfiguration:
    """Configuration for import operations"""
    format: ImportExportFormat
    merge_strategy: str = "replace"  # replace, merge, skip
    validate_on_import: bool = True
    create_backup: bool = True
    ignore_errors: bool = False
    custom_mapping: Dict[str, str] = None
    
    def __post_init__(self):
        if self.custom_mapping is None:
            self.custom_mapping = {}


@dataclass
class OperationResult:
    """Result of import/export operation"""
    success: bool
    file_path: Optional[str] = None
    processed_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: List[str] = None
    operation_time: float = 0.0
    file_size: int = 0
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class PropertyImportExportManager(QObject):
    """Manages property import/export operations"""
    
    # Signals
    operation_started = pyqtSignal(str, str)  # operation_type, format
    operation_progress = pyqtSignal(int, str)  # percentage, status
    operation_completed = pyqtSignal(object)  # OperationResult
    operation_error = pyqtSignal(str)  # error message
    
    def __init__(self, property_panel):
        super().__init__()
        self.property_panel = property_panel
        self.property_manager = None
        self.cancel_requested = False
        
        # Operation history
        self.operation_history: List[OperationResult] = []
        
    def set_property_manager(self, manager) -> None:
        """Set property manager for data access"""
        self.property_manager = manager
    
    def export_properties(self, 
                         element_ids: List[str],
                         config: ExportConfiguration,
                         file_path: str) -> OperationResult:
        """Export properties to file"""
        self.cancel_requested = False
        start_time = time.time()
        
        try:
            self.operation_started.emit("export", config.format.value)
            
            # Collect property data
            self.operation_progress.emit(10, "Collecting property data...")
            property_data = self._collect_property_data(element_ids, config)
            
            # Export to format
            self.operation_progress.emit(50, f"Exporting to {config.format.value.upper()}...")
            
            if config.format == ImportExportFormat.JSON:
                self._export_json(property_data, file_path, config)
            elif config.format == ImportExportFormat.CSV:
                self._export_csv(property_data, file_path, config)
            elif config.format == ImportExportFormat.XML:
                self._export_xml(property_data, file_path, config)
            elif config.format == ImportExportFormat.PICKLE:
                self._export_pickle(property_data, file_path, config)
            
            self.operation_progress.emit(90, "Finalizing export...")
            
            # Create result
            end_time = time.time()
            file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
            
            result = OperationResult(
                success=True,
                file_path=file_path,
                processed_count=len(element_ids),
                operation_time=end_time - start_time,
                file_size=file_size
            )
            
            self.operation_progress.emit(100, "Export completed")
            self.operation_completed.emit(result)
            self.operation_history.append(result)
            
            return result
            
        except Exception as e:
            error_msg = f"Export failed: {str(e)}"
            self.operation_error.emit(error_msg)
            
            result = OperationResult(
                success=False,
                errors=[error_msg],
                operation_time=time.time() - start_time
            )
            self.operation_history.append(result)
            
            return result
    
    def import_properties(self, 
                         file_path: str,
                         config: ImportConfiguration) -> OperationResult:
        """Import properties from file"""
        self.cancel_requested = False
        start_time = time.time()
        
        try:
            self.operation_started.emit("import", config.format.value)
            
            # Create backup if requested
            backup_path = None
            if config.create_backup:
                self.operation_progress.emit(5, "Creating backup...")
                backup_path = self._create_backup()
            
            # Load data from file
            self.operation_progress.emit(20, f"Loading {config.format.value.upper()} file...")
            data = self._load_data(file_path, config.format)
            
            # Process import
            self.operation_progress.emit(40, "Processing import data...")
            result = self._process_import(data, config)
            
            # Finalize
            end_time = time.time()
            result.operation_time = end_time - start_time
            
            self.operation_progress.emit(100, "Import completed")
            self.operation_completed.emit(result)
            self.operation_history.append(result)
            
            return result
            
        except Exception as e:
            error_msg = f"Import failed: {str(e)}"
            self.operation_error.emit(error_msg)
            
            result = OperationResult(
                success=False,
                errors=[error_msg],
                operation_time=time.time() - start_time
            )
            self.operation_history.append(result)
            
            return result
    
    def _collect_property_data(self, element_ids: List[str], config: ExportConfiguration) -> Dict[str, Any]:
        """Collect property data from elements"""
        export_data = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'format': config.format.value,
                'element_count': len(element_ids),
                'configuration': asdict(config)
            },
            'elements': {}
        }
        
        for i, element_id in enumerate(element_ids):
            if self.cancel_requested:
                break
            
            # Update progress
            progress = int(10 + (i / len(element_ids)) * 40)
            self.operation_progress.emit(progress, f"Processing element {i+1}/{len(element_ids)}")
            
            element_data = self._collect_element_data(element_id, config)
            if element_data:  # Only add if not empty
                export_data['elements'][element_id] = element_data
        
        return export_data
    
    def _collect_element_data(self, element_id: str, config: ExportConfiguration) -> Dict[str, Any]:
        """Collect data for single element"""
        if not self.property_manager:
            return {}
        
        try:
            # Get all properties for element
            properties = self.property_manager.get_element_properties(element_id)
            if not properties:
                return {}
            
            element_data = {'properties': {}}
            
            # Filter properties if specified
            if config.property_filter:
                properties = {k: v for k, v in properties.items() if k in config.property_filter}
            
            # Process each property
            for prop_name, prop_value in properties.items():
                # Skip empty values if configured
                if not config.include_empty_values and not prop_value:
                    continue
                
                element_data['properties'][prop_name] = prop_value
                
                # Include metadata if requested
                if config.include_metadata:
                    if 'metadata' not in element_data:
                        element_data['metadata'] = {}
                    
                    metadata = self.property_manager.get_property_metadata(element_id, prop_name)
                    if metadata:
                        element_data['metadata'][prop_name] = asdict(metadata)
            
            return element_data
            
        except Exception as e:
            return {'error': str(e)}
    
    def _export_json(self, data: Dict[str, Any], file_path: str, config: ExportConfiguration) -> None:
        """Export to JSON format"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    def _export_csv(self, data: Dict[str, Any], file_path: str, config: ExportConfiguration) -> None:
        """Export to CSV format"""
        elements = data.get('elements', {})
        
        if not elements:
            return
        
        # Flatten data for CSV
        rows = []
        headers = set(['element_id'])
        
        for element_id, element_data in elements.items():
            row = {'element_id': element_id}
            properties = element_data.get('properties', {})
            
            if config.flatten_nested:
                flattened = self._flatten_dict(properties)
                row.update(flattened)
                headers.update(flattened.keys())
            else:
                row.update(properties)
                headers.update(properties.keys())
            
            rows.append(row)
        
        # Write CSV
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=sorted(headers))
                writer.writeheader()
                writer.writerows(rows)
    
    def _export_xml(self, data: Dict[str, Any], file_path: str, config: ExportConfiguration) -> None:
        """Export to XML format"""
        root = ET.Element('property_export')
        
        # Add export info
        info_elem = ET.SubElement(root, 'export_info')
        for key, value in data.get('export_info', {}).items():
            child = ET.SubElement(info_elem, key)
            child.text = str(value)
        
        # Add elements
        elements_elem = ET.SubElement(root, 'elements')
        for element_id, element_data in data.get('elements', {}).items():
            element_elem = ET.SubElement(elements_elem, 'element')
            element_elem.set('id', element_id)
            
            # Add properties
            props_elem = ET.SubElement(element_elem, 'properties')
            for prop_name, prop_value in element_data.get('properties', {}).items():
                prop_elem = ET.SubElement(props_elem, 'property')
                prop_elem.set('name', prop_name)
                prop_elem.text = str(prop_value)
        
        # Pretty print XML
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(xml_str)
    
    def _export_pickle(self, data: Dict[str, Any], file_path: str, config: ExportConfiguration) -> None:
        """Export to Pickle format"""
        with open(file_path, 'wb') as f:
            pickle.dump(data, f)
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _load_data(self, file_path: str, format: ImportExportFormat) -> Dict[str, Any]:
        """Load data from file based on format"""
        if format == ImportExportFormat.JSON:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        elif format == ImportExportFormat.PICKLE:
            with open(file_path, 'rb') as f:
                return pickle.load(f)
        
        elif format == ImportExportFormat.CSV:
            return self._load_csv(file_path)
        
        elif format == ImportExportFormat.XML:
            return self._load_xml(file_path)
        
        else:
            raise ValueError(f"Unsupported import format: {format}")
    
    def _load_csv(self, file_path: str) -> Dict[str, Any]:
        """Load data from CSV file"""
        elements = {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                element_id = row.pop('element_id', None)
                if element_id:
                    elements[element_id] = {
                        'properties': {k: v for k, v in row.items() if v}
                    }
        
        return {
            'export_info': {'format': 'csv'},
            'elements': elements
        }
    
    def _load_xml(self, file_path: str) -> Dict[str, Any]:
        """Load data from XML file"""
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        elements = {}
        elements_elem = root.find('elements')
        
        if elements_elem is not None:
            for element_elem in elements_elem.findall('element'):
                element_id = element_elem.get('id')
                if element_id:
                    properties = {}
                    props_elem = element_elem.find('properties')
                    
                    if props_elem is not None:
                        for prop_elem in props_elem.findall('property'):
                            prop_name = prop_elem.get('name')
                            prop_value = prop_elem.text
                            if prop_name:
                                properties[prop_name] = prop_value
                    
                    elements[element_id] = {'properties': properties}
        
        return {
            'export_info': {'format': 'xml'},
            'elements': elements
        }
    
    def _process_import(self, data: Dict[str, Any], config: ImportConfiguration) -> OperationResult:
        """Process imported data"""
        result = OperationResult(success=True)
        elements = data.get('elements', {})
        total_elements = len(elements)
        
        for i, (element_id, element_data) in enumerate(elements.items()):
            if self.cancel_requested:
                break
            
            # Update progress
            progress = int(40 + (i / total_elements) * 50)
            self.operation_progress.emit(progress, f"Importing element {i+1}/{total_elements}")
            
            try:
                success = self._import_element(element_id, element_data, config)
                if success:
                    result.processed_count += 1
                else:
                    result.skipped_count += 1
            
            except Exception as e:
                result.error_count += 1
                result.errors.append(f"Error importing {element_id}: {str(e)}")
                
                if not config.ignore_errors:
                    result.success = False
                    break
        
        return result
    
    def _import_element(self, element_id: str, element_data: Dict[str, Any], 
                       config: ImportConfiguration) -> bool:
        """Import single element"""
        if not self.property_manager:
            return False
        
        properties = element_data.get('properties', {})
        
        for prop_name, prop_value in properties.items():
            # Apply custom mapping if provided
            mapped_name = config.custom_mapping.get(prop_name, prop_name)
            
            # Handle merge strategy
            if config.merge_strategy == 'skip':
                current_value = self.property_manager.get_property_value(element_id, mapped_name)
                if current_value is not None:
                    continue
            
            # Validate if requested
            if config.validate_on_import:
                # Would validate property value here
                pass
            
            # Set property value
            self.property_manager.set_property_value(element_id, mapped_name, prop_value)
        
        return True
    
    def _create_backup(self) -> str:
        """Create backup of current data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"property_backup_{timestamp}.json"
        
        # Would create backup file here
        # For now, just return the path
        return backup_path
    
    def cancel_operation(self) -> None:
        """Cancel current operation"""
        self.cancel_requested = True
    
    def get_operation_history(self) -> List[OperationResult]:
        """Get operation history"""
        return self.operation_history.copy()
    
    def clear_operation_history(self) -> None:
        """Clear operation history"""
        self.operation_history.clear()


class ImportExportDialog(QDialog):
    """Dialog for property import/export operations"""
    
    def __init__(self, property_manager, selected_elements: List[str] = None, parent=None):
        super().__init__(parent)
        self.property_manager = property_manager
        self.selected_elements = selected_elements or []
        
        self.setWindowTitle("Property Import/Export")
        self.setModal(True)
        self.resize(600, 500)
        
        # Create manager
        self.import_export_manager = PropertyImportExportManager(parent)
        self.import_export_manager.set_property_manager(property_manager)
        
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self) -> None:
        """Setup dialog UI"""
        layout = QVBoxLayout(self)
        
        # Tab widget for import/export
        self.tab_widget = QTabWidget()
        
        # Export tab
        export_tab = self._create_export_tab()
        self.tab_widget.addTab(export_tab, "Export")
        
        # Import tab
        import_tab = self._create_import_tab()
        self.tab_widget.addTab(import_tab, "Import")
        
        layout.addWidget(self.tab_widget)
        
        # Button box
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
    
    def _create_export_tab(self) -> QWidget:
        """Create export tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Selection info
        if self.selected_elements:
            info_label = QLabel(f"Exporting {len(self.selected_elements)} selected elements")
        else:
            info_label = QLabel("Exporting all elements")
        info_label.setFont(QFont("", 10, QFont.Weight.Bold))
        layout.addWidget(info_label)
        
        # Format selection
        format_group = QGroupBox("Export Format")
        format_layout = QVBoxLayout(format_group)
        
        self.export_format_combo = QComboBox()
        for fmt in ImportExportFormat:
            self.export_format_combo.addItem(fmt.description, fmt)
        format_layout.addWidget(self.export_format_combo)
        
        layout.addWidget(format_group)
        
        # Options
        options_group = QGroupBox("Export Options")
        options_layout = QVBoxLayout(options_group)
        
        self.include_metadata_cb = QCheckBox("Include metadata")
        self.include_metadata_cb.setChecked(True)
        options_layout.addWidget(self.include_metadata_cb)
        
        self.include_empty_cb = QCheckBox("Include empty values")
        options_layout.addWidget(self.include_empty_cb)
        
        self.flatten_nested_cb = QCheckBox("Flatten nested properties")
        options_layout.addWidget(self.flatten_nested_cb)
        
        layout.addWidget(options_group)
        
        # Progress
        self.export_progress = QProgressBar()
        self.export_progress.setVisible(False)
        layout.addWidget(self.export_progress)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.export_btn = QPushButton("Export Properties")
        self.export_btn.clicked.connect(self._start_export)
        
        self.export_cancel_btn = QPushButton("Cancel")
        self.export_cancel_btn.clicked.connect(self._cancel_export)
        self.export_cancel_btn.setVisible(False)
        
        controls_layout.addWidget(self.export_btn)
        controls_layout.addWidget(self.export_cancel_btn)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        return tab
    
    def _create_import_tab(self) -> QWidget:
        """Create import tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # File selection
        file_group = QGroupBox("Import File")
        file_layout = QHBoxLayout(file_group)
        
        self.import_file_label = QLabel("No file selected")
        file_layout.addWidget(self.import_file_label)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_import_file)
        file_layout.addWidget(self.browse_btn)
        
        layout.addWidget(file_group)
        
        # Options
        options_group = QGroupBox("Import Options")
        options_layout = QVBoxLayout(options_group)
        
        self.merge_strategy_combo = QComboBox()
        self.merge_strategy_combo.addItems(["Replace existing", "Merge with existing", "Skip existing"])
        options_layout.addWidget(QLabel("Merge Strategy:"))
        options_layout.addWidget(self.merge_strategy_combo)
        
        self.validate_import_cb = QCheckBox("Validate on import")
        self.validate_import_cb.setChecked(True)
        options_layout.addWidget(self.validate_import_cb)
        
        self.create_backup_cb = QCheckBox("Create backup before import")
        self.create_backup_cb.setChecked(True)
        options_layout.addWidget(self.create_backup_cb)
        
        layout.addWidget(options_group)
        
        # Progress
        self.import_progress = QProgressBar()
        self.import_progress.setVisible(False)
        layout.addWidget(self.import_progress)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.import_btn = QPushButton("Import Properties")
        self.import_btn.clicked.connect(self._start_import)
        self.import_btn.setEnabled(False)
        
        self.import_cancel_btn = QPushButton("Cancel")
        self.import_cancel_btn.clicked.connect(self._cancel_import)
        self.import_cancel_btn.setVisible(False)
        
        controls_layout.addWidget(self.import_btn)
        controls_layout.addWidget(self.import_cancel_btn)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        return tab
    
    def _setup_connections(self) -> None:
        """Setup signal connections"""
        # Manager connections
        self.import_export_manager.operation_progress.connect(self._on_operation_progress)
        self.import_export_manager.operation_completed.connect(self._on_operation_completed)
        self.import_export_manager.operation_error.connect(self._on_operation_error)
    
    def _start_export(self) -> None:
        """Start export operation"""
        # Get export configuration
        format = self.export_format_combo.currentData()
        config = ExportConfiguration(
            format=format,
            include_metadata=self.include_metadata_cb.isChecked(),
            include_empty_values=self.include_empty_cb.isChecked(),
            flatten_nested=self.flatten_nested_cb.isChecked()
        )
        
        # Get file path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Properties",
            f"properties{format.extension}",
            f"{format.description} (*{format.extension})"
        )
        
        if file_path:
            # Get element IDs to export
            element_ids = self.selected_elements or self._get_all_element_ids()
            
            # Start export
            self.export_progress.setVisible(True)
            self.export_btn.setEnabled(False)
            self.export_cancel_btn.setVisible(True)
            
            self.import_export_manager.export_properties(element_ids, config, file_path)
    
    def _start_import(self) -> None:
        """Start import operation"""
        file_path = self.import_file_label.property('file_path')
        if not file_path:
            return
        
        # Detect format from file extension
        suffix = Path(file_path).suffix.lower()
        format_map = {
            '.json': ImportExportFormat.JSON,
            '.csv': ImportExportFormat.CSV,
            '.xml': ImportExportFormat.XML,
            '.pkl': ImportExportFormat.PICKLE
        }
        
        format = format_map.get(suffix)
        if not format:
            QMessageBox.warning(self, "Unsupported Format", f"Unsupported file format: {suffix}")
            return
        
        # Get import configuration
        merge_strategies = ['replace', 'merge', 'skip']
        merge_strategy = merge_strategies[self.merge_strategy_combo.currentIndex()]
        
        config = ImportConfiguration(
            format=format,
            merge_strategy=merge_strategy,
            validate_on_import=self.validate_import_cb.isChecked(),
            create_backup=self.create_backup_cb.isChecked()
        )
        
        # Start import
        self.import_progress.setVisible(True)
        self.import_btn.setEnabled(False)
        self.import_cancel_btn.setVisible(True)
        
        self.import_export_manager.import_properties(file_path, config)
    
    def _cancel_export(self) -> None:
        """Cancel export operation"""
        self.import_export_manager.cancel_operation()
    
    def _cancel_import(self) -> None:
        """Cancel import operation"""
        self.import_export_manager.cancel_operation()
    
    def _browse_import_file(self) -> None:
        """Browse for import file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Properties",
            "",
            "All supported (*.json *.csv *.xml *.pkl);;JSON files (*.json);;CSV files (*.csv);;XML files (*.xml);;Pickle files (*.pkl)"
        )
        
        if file_path:
            self.import_file_label.setText(Path(file_path).name)
            self.import_file_label.setProperty('file_path', file_path)
            self.import_btn.setEnabled(True)
    
    def _get_all_element_ids(self) -> List[str]:
        """Get all element IDs from property manager"""
        if self.property_manager and hasattr(self.property_manager, 'get_all_element_ids'):
            return self.property_manager.get_all_element_ids()
        return []
    
    def _on_operation_progress(self, percentage: int, status: str) -> None:
        """Handle operation progress"""
        if self.tab_widget.currentIndex() == 0:  # Export tab
            self.export_progress.setValue(percentage)
        else:  # Import tab
            self.import_progress.setValue(percentage)
    
    def _on_operation_completed(self, result: OperationResult) -> None:
        """Handle operation completion"""
        # Hide progress and reset buttons
        self.export_progress.setVisible(False)
        self.import_progress.setVisible(False)
        self.export_btn.setEnabled(True)
        self.import_btn.setEnabled(True)
        self.export_cancel_btn.setVisible(False)
        self.import_cancel_btn.setVisible(False)
        
        if result.success:
            QMessageBox.information(
                self,
                "Operation Complete",
                f"Successfully processed {result.processed_count} elements"
            )
        else:
            QMessageBox.warning(
                self,
                "Operation Failed",
                f"Operation failed: {'; '.join(result.errors)}"
            )
    
    def _on_operation_error(self, error_msg: str) -> None:
        """Handle operation error"""
        # Hide progress and reset buttons
        self.export_progress.setVisible(False)
        self.import_progress.setVisible(False)
        self.export_btn.setEnabled(True)
        self.import_btn.setEnabled(True)
        self.export_cancel_btn.setVisible(False)
        self.import_cancel_btn.setVisible(False)
        
        QMessageBox.critical(self, "Operation Error", error_msg)


# Export import/export components
__all__ = [
    'ImportExportFormat',
    'ExportConfiguration',
    'ImportConfiguration',
    'OperationResult',
    'PropertyImportExportManager',
    'ImportExportDialog'
]