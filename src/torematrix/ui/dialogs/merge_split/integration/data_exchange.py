"""
Data Exchange System for Merge/Split Operations Engine.

Agent 4 - Integration & Advanced Features (Issue #237)
Provides import/export capabilities for merge/split configurations,
operation history, and data exchange with external systems.
"""

from typing import Dict, List, Optional, Any, Union, Type, TextIO, BinaryIO
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod
import asyncio
import json
import csv
import xml.etree.ElementTree as ET
import yaml
import logging
import uuid
from datetime import datetime
from pathlib import Path
import zipfile
import tempfile
import base64

from .....core.models import Element
from .....core.state import Store

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """Supported export formats."""
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    YAML = "yaml"
    EXCEL = "xlsx"
    ZIP = "zip"
    BINARY = "binary"


class ImportFormat(Enum):
    """Supported import formats."""
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    YAML = "yaml"
    EXCEL = "xlsx"
    ZIP = "zip"
    BINARY = "binary"


class DataExchangeError(Exception):
    """Exception raised for data exchange errors."""
    def __init__(self, message: str, format_type: str = None, error_code: str = None):
        super().__init__(message)
        self.format_type = format_type
        self.error_code = error_code


@dataclass
class ExportConfig:
    """Configuration for export operations."""
    format: ExportFormat
    include_metadata: bool = True
    include_history: bool = True
    include_validation: bool = True
    compress: bool = False
    encrypt: bool = False
    encryption_key: Optional[str] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    date_format: str = "%Y-%m-%d %H:%M:%S"
    encoding: str = "utf-8"


@dataclass
class ImportConfig:
    """Configuration for import operations."""
    format: ImportFormat
    validate_schema: bool = True
    merge_conflicts_strategy: str = "keep_existing"  # keep_existing, overwrite, merge
    restore_history: bool = False
    decrypt: bool = False
    decryption_key: Optional[str] = None
    custom_mappings: Dict[str, str] = field(default_factory=dict)
    encoding: str = "utf-8"


@dataclass
class ExportResult:
    """Result of an export operation."""
    success: bool
    export_id: str
    file_path: Optional[Path] = None
    data: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    exported_at: datetime = field(default_factory=datetime.now)
    file_size: Optional[int] = None
    record_count: Optional[int] = None


@dataclass
class ImportResult:
    """Result of an import operation."""
    success: bool
    import_id: str
    records_imported: int = 0
    records_skipped: int = 0
    records_failed: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    imported_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataFormatter(ABC):
    """Abstract base class for data formatters."""
    
    @abstractmethod
    def export_data(self, data: Any, config: ExportConfig) -> Union[str, bytes]:
        """Export data to format-specific representation."""
        pass
    
    @abstractmethod
    def import_data(self, data: Union[str, bytes], config: ImportConfig) -> Any:
        """Import data from format-specific representation."""
        pass
    
    @abstractmethod
    def validate_data(self, data: Union[str, bytes]) -> bool:
        """Validate data format."""
        pass


class JSONFormatter(DataFormatter):
    """JSON data formatter."""
    
    def export_data(self, data: Any, config: ExportConfig) -> str:
        """Export data to JSON format."""
        try:
            return json.dumps(data, indent=2, default=self._json_serializer, ensure_ascii=False)
        except Exception as e:
            raise DataExchangeError(f"Failed to export JSON: {e}", "json")
    
    def import_data(self, data: str, config: ImportConfig) -> Any:
        """Import data from JSON format."""
        try:
            return json.loads(data)
        except Exception as e:
            raise DataExchangeError(f"Failed to import JSON: {e}", "json")
    
    def validate_data(self, data: str) -> bool:
        """Validate JSON data."""
        try:
            json.loads(data)
            return True
        except Exception:
            return False
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for complex objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Path):
            return str(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)


class XMLFormatter(DataFormatter):
    """XML data formatter."""
    
    def export_data(self, data: Any, config: ExportConfig) -> str:
        """Export data to XML format."""
        try:
            root = ET.Element("merge_split_data")
            self._dict_to_xml(data, root)
            return ET.tostring(root, encoding='unicode', xml_declaration=True)
        except Exception as e:
            raise DataExchangeError(f"Failed to export XML: {e}", "xml")
    
    def import_data(self, data: str, config: ImportConfig) -> Any:
        """Import data from XML format."""
        try:
            root = ET.fromstring(data)
            return self._xml_to_dict(root)
        except Exception as e:
            raise DataExchangeError(f"Failed to import XML: {e}", "xml")
    
    def validate_data(self, data: str) -> bool:
        """Validate XML data."""
        try:
            ET.fromstring(data)
            return True
        except Exception:
            return False
    
    def _dict_to_xml(self, data, parent):
        """Convert dictionary to XML elements."""
        if isinstance(data, dict):
            for key, value in data.items():
                element = ET.SubElement(parent, str(key))
                self._dict_to_xml(value, element)
        elif isinstance(data, list):
            for item in data:
                item_element = ET.SubElement(parent, "item")
                self._dict_to_xml(item, item_element)
        else:
            parent.text = str(data)
    
    def _xml_to_dict(self, element):
        """Convert XML element to dictionary."""
        result = {}
        
        # Handle attributes
        if element.attrib:
            result.update(element.attrib)
        
        # Handle text content
        if element.text and element.text.strip():
            if len(element) == 0:  # Leaf node
                return element.text.strip()
            else:
                result['text'] = element.text.strip()
        
        # Handle child elements
        for child in element:
            child_data = self._xml_to_dict(child)
            if child.tag in result:
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        
        return result


class CSVFormatter(DataFormatter):
    """CSV data formatter."""
    
    def export_data(self, data: Any, config: ExportConfig) -> str:
        """Export data to CSV format."""
        try:
            if not isinstance(data, list):
                raise DataExchangeError("CSV export requires list data", "csv")
            
            if not data:
                return ""
            
            # Flatten data if needed
            flattened_data = [self._flatten_dict(item) if isinstance(item, dict) else item for item in data]
            
            # Get all possible fieldnames
            fieldnames = set()
            for item in flattened_data:
                if isinstance(item, dict):
                    fieldnames.update(item.keys())
            
            fieldnames = sorted(fieldnames)
            
            # Generate CSV
            import io
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in flattened_data:
                if isinstance(item, dict):
                    writer.writerow(item)
                else:
                    writer.writerow({fieldnames[0]: item})
            
            return output.getvalue()
            
        except Exception as e:
            raise DataExchangeError(f"Failed to export CSV: {e}", "csv")
    
    def import_data(self, data: str, config: ImportConfig) -> List[Dict[str, Any]]:
        """Import data from CSV format."""
        try:
            import io
            input_stream = io.StringIO(data)
            reader = csv.DictReader(input_stream)
            return list(reader)
        except Exception as e:
            raise DataExchangeError(f"Failed to import CSV: {e}", "csv")
    
    def validate_data(self, data: str) -> bool:
        """Validate CSV data."""
        try:
            import io
            csv.Sniffer().sniff(data)
            return True
        except Exception:
            return False
    
    def _flatten_dict(self, d, parent_key='', sep='_'):
        """Flatten nested dictionary."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                items.append((new_key, json.dumps(v)))
            else:
                items.append((new_key, v))
        return dict(items)


class YAMLFormatter(DataFormatter):
    """YAML data formatter."""
    
    def export_data(self, data: Any, config: ExportConfig) -> str:
        """Export data to YAML format."""
        try:
            return yaml.dump(data, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            raise DataExchangeError(f"Failed to export YAML: {e}", "yaml")
    
    def import_data(self, data: str, config: ImportConfig) -> Any:
        """Import data from YAML format."""
        try:
            return yaml.safe_load(data)
        except Exception as e:
            raise DataExchangeError(f"Failed to import YAML: {e}", "yaml")
    
    def validate_data(self, data: str) -> bool:
        """Validate YAML data."""
        try:
            yaml.safe_load(data)
            return True
        except Exception:
            return False


class DataExporter:
    """Data exporter for merge/split operations."""
    
    def __init__(self, store: Store):
        self.store = store
        self._formatters: Dict[ExportFormat, DataFormatter] = {
            ExportFormat.JSON: JSONFormatter(),
            ExportFormat.XML: XMLFormatter(),
            ExportFormat.CSV: CSVFormatter(),
            ExportFormat.YAML: YAMLFormatter(),
        }
    
    async def export_operation_history(
        self, 
        operation_ids: Optional[List[str]] = None,
        config: Optional[ExportConfig] = None
    ) -> ExportResult:
        """Export operation history."""
        if config is None:
            config = ExportConfig(format=ExportFormat.JSON)
        
        export_id = str(uuid.uuid4())
        
        try:
            # Get operation history from store
            state = self.store.get_state()
            operations = state.get('operations', {}).get('history', [])
            
            # Filter by operation IDs if specified
            if operation_ids:
                operations = [op for op in operations if op.get('id') in operation_ids]
            
            # Prepare export data
            export_data = {
                'export_info': {
                    'export_id': export_id,
                    'exported_at': datetime.now().isoformat(),
                    'format': config.format.value,
                    'record_count': len(operations)
                },
                'operations': operations
            }
            
            if config.include_metadata:
                export_data['metadata'] = {
                    'version': '1.0.0',
                    'system': 'TORE Matrix Labs V3',
                    'component': 'Merge/Split Operations Engine'
                }
            
            # Format data
            formatter = self._formatters.get(config.format)
            if not formatter:
                raise DataExchangeError(f"Unsupported export format: {config.format}")
            
            formatted_data = formatter.export_data(export_data, config)
            
            return ExportResult(
                success=True,
                export_id=export_id,
                data=formatted_data,
                record_count=len(operations),
                metadata={'format': config.format.value}
            )
            
        except Exception as e:
            logger.error(f"Export operation history failed: {e}")
            return ExportResult(
                success=False,
                export_id=export_id,
                error=str(e)
            )
    
    async def export_merge_configurations(
        self, 
        config_names: Optional[List[str]] = None,
        config: Optional[ExportConfig] = None
    ) -> ExportResult:
        """Export merge configurations."""
        if config is None:
            config = ExportConfig(format=ExportFormat.JSON)
        
        export_id = str(uuid.uuid4())
        
        try:
            # Get configurations from store
            state = self.store.get_state()
            configurations = state.get('merge_split', {}).get('configurations', {})
            
            # Filter by config names if specified
            if config_names:
                configurations = {k: v for k, v in configurations.items() if k in config_names}
            
            # Prepare export data
            export_data = {
                'export_info': {
                    'export_id': export_id,
                    'exported_at': datetime.now().isoformat(),
                    'format': config.format.value,
                    'record_count': len(configurations)
                },
                'configurations': configurations
            }
            
            # Format data
            formatter = self._formatters.get(config.format)
            if not formatter:
                raise DataExchangeError(f"Unsupported export format: {config.format}")
            
            formatted_data = formatter.export_data(export_data, config)
            
            return ExportResult(
                success=True,
                export_id=export_id,
                data=formatted_data,
                record_count=len(configurations),
                metadata={'format': config.format.value}
            )
            
        except Exception as e:
            logger.error(f"Export configurations failed: {e}")
            return ExportResult(
                success=False,
                export_id=export_id,
                error=str(e)
            )
    
    async def export_to_file(
        self, 
        export_result: ExportResult, 
        file_path: Union[str, Path]
    ) -> bool:
        """Export data to a file."""
        try:
            file_path = Path(file_path)
            
            if export_result.data is None:
                raise DataExchangeError("No data to export")
            
            # Write data to file
            if isinstance(export_result.data, str):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(export_result.data)
            else:
                with open(file_path, 'wb') as f:
                    f.write(export_result.data)
            
            # Update export result with file info
            export_result.file_path = file_path
            export_result.file_size = file_path.stat().st_size
            
            logger.info(f"Exported data to file: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export to file {file_path}: {e}")
            return False


class DataImporter:
    """Data importer for merge/split operations."""
    
    def __init__(self, store: Store):
        self.store = store
        self._formatters: Dict[ImportFormat, DataFormatter] = {
            ImportFormat.JSON: JSONFormatter(),
            ImportFormat.XML: XMLFormatter(),
            ImportFormat.CSV: CSVFormatter(),
            ImportFormat.YAML: YAMLFormatter(),
        }
    
    async def import_operation_history(
        self, 
        data: Union[str, bytes],
        config: Optional[ImportConfig] = None
    ) -> ImportResult:
        """Import operation history."""
        if config is None:
            config = ImportConfig(format=ImportFormat.JSON)
        
        import_id = str(uuid.uuid4())
        
        try:
            # Format data
            formatter = self._formatters.get(config.format)
            if not formatter:
                raise DataExchangeError(f"Unsupported import format: {config.format}")
            
            if config.validate_schema:
                if not formatter.validate_data(data):
                    raise DataExchangeError("Invalid data format")
            
            imported_data = formatter.import_data(data, config)
            
            # Validate structure
            if not isinstance(imported_data, dict) or 'operations' not in imported_data:
                raise DataExchangeError("Invalid operation history structure")
            
            operations = imported_data['operations']
            records_imported = 0
            records_skipped = 0
            records_failed = 0
            errors = []
            
            # Import operations
            for operation in operations:
                try:
                    # Validate operation structure
                    if not isinstance(operation, dict) or 'id' not in operation:
                        records_failed += 1
                        errors.append(f"Invalid operation structure: missing id")
                        continue
                    
                    # Check for conflicts
                    if config.merge_conflicts_strategy == "keep_existing":
                        existing = await self._check_operation_exists(operation['id'])
                        if existing:
                            records_skipped += 1
                            continue
                    
                    # Import operation
                    await self._import_operation(operation)
                    records_imported += 1
                    
                except Exception as e:
                    records_failed += 1
                    errors.append(f"Failed to import operation {operation.get('id', 'unknown')}: {e}")
            
            return ImportResult(
                success=True,
                import_id=import_id,
                records_imported=records_imported,
                records_skipped=records_skipped,
                records_failed=records_failed,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Import operation history failed: {e}")
            return ImportResult(
                success=False,
                import_id=import_id,
                errors=[str(e)]
            )
    
    async def import_configurations(
        self, 
        data: Union[str, bytes],
        config: Optional[ImportConfig] = None
    ) -> ImportResult:
        """Import merge/split configurations."""
        if config is None:
            config = ImportConfig(format=ImportFormat.JSON)
        
        import_id = str(uuid.uuid4())
        
        try:
            # Format data
            formatter = self._formatters.get(config.format)
            if not formatter:
                raise DataExchangeError(f"Unsupported import format: {config.format}")
            
            imported_data = formatter.import_data(data, config)
            
            # Validate structure
            if not isinstance(imported_data, dict) or 'configurations' not in imported_data:
                raise DataExchangeError("Invalid configurations structure")
            
            configurations = imported_data['configurations']
            records_imported = 0
            records_skipped = 0
            errors = []
            
            # Import configurations
            for config_name, config_data in configurations.items():
                try:
                    await self._import_configuration(config_name, config_data, config)
                    records_imported += 1
                except Exception as e:
                    errors.append(f"Failed to import configuration {config_name}: {e}")
            
            return ImportResult(
                success=True,
                import_id=import_id,
                records_imported=records_imported,
                records_skipped=records_skipped,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Import configurations failed: {e}")
            return ImportResult(
                success=False,
                import_id=import_id,
                errors=[str(e)]
            )
    
    async def import_from_file(
        self, 
        file_path: Union[str, Path],
        config: Optional[ImportConfig] = None
    ) -> ImportResult:
        """Import data from a file."""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise DataExchangeError(f"File not found: {file_path}")
            
            # Read file data
            if config and config.format in [ImportFormat.BINARY]:
                with open(file_path, 'rb') as f:
                    data = f.read()
            else:
                with open(file_path, 'r', encoding=config.encoding if config else 'utf-8') as f:
                    data = f.read()
            
            # Determine import type based on file content structure
            # For now, assume operation history
            return await self.import_operation_history(data, config)
            
        except Exception as e:
            logger.error(f"Failed to import from file {file_path}: {e}")
            return ImportResult(
                success=False,
                import_id=str(uuid.uuid4()),
                errors=[str(e)]
            )
    
    async def _check_operation_exists(self, operation_id: str) -> bool:
        """Check if operation already exists."""
        state = self.store.get_state()
        operations = state.get('operations', {}).get('history', [])
        return any(op.get('id') == operation_id for op in operations)
    
    async def _import_operation(self, operation: Dict[str, Any]) -> None:
        """Import a single operation."""
        # Implementation would update store with operation
        # This is a placeholder for the actual implementation
        logger.debug(f"Importing operation: {operation.get('id')}")
    
    async def _import_configuration(
        self, 
        config_name: str, 
        config_data: Dict[str, Any], 
        import_config: ImportConfig
    ) -> None:
        """Import a single configuration."""
        # Implementation would update store with configuration
        # This is a placeholder for the actual implementation
        logger.debug(f"Importing configuration: {config_name}")


class ConfigurationExporter(DataExporter):
    """Specialized exporter for merge/split configurations."""
    
    async def export_merge_templates(self) -> ExportResult:
        """Export merge operation templates."""
        return await self.export_merge_configurations(
            config=ExportConfig(
                format=ExportFormat.JSON,
                include_metadata=True
            )
        )
    
    async def export_split_templates(self) -> ExportResult:
        """Export split operation templates."""
        # Similar to merge templates but for split operations
        export_id = str(uuid.uuid4())
        
        try:
            state = self.store.get_state()
            split_templates = state.get('merge_split', {}).get('split_templates', {})
            
            export_data = {
                'export_info': {
                    'export_id': export_id,
                    'exported_at': datetime.now().isoformat(),
                    'type': 'split_templates'
                },
                'templates': split_templates
            }
            
            formatter = self._formatters[ExportFormat.JSON]
            formatted_data = formatter.export_data(export_data, ExportConfig(format=ExportFormat.JSON))
            
            return ExportResult(
                success=True,
                export_id=export_id,
                data=formatted_data,
                record_count=len(split_templates)
            )
            
        except Exception as e:
            return ExportResult(
                success=False,
                export_id=export_id,
                error=str(e)
            )


class HistoryExporter(DataExporter):
    """Specialized exporter for operation history."""
    
    async def export_recent_operations(self, days: int = 7) -> ExportResult:
        """Export recent operations within specified days."""
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        # Get recent operations
        state = self.store.get_state()
        all_operations = state.get('operations', {}).get('history', [])
        recent_operations = [
            op for op in all_operations 
            if op.get('timestamp', 0) > cutoff_date
        ]
        
        export_id = str(uuid.uuid4())
        export_data = {
            'export_info': {
                'export_id': export_id,
                'exported_at': datetime.now().isoformat(),
                'filter': f'recent_{days}_days'
            },
            'operations': recent_operations
        }
        
        formatter = self._formatters[ExportFormat.JSON]
        formatted_data = formatter.export_data(export_data, ExportConfig(format=ExportFormat.JSON))
        
        return ExportResult(
            success=True,
            export_id=export_id,
            data=formatted_data,
            record_count=len(recent_operations)
        )


# Convenience factory functions
def create_data_exporter(store: Store) -> DataExporter:
    """Create a data exporter."""
    return DataExporter(store)


def create_data_importer(store: Store) -> DataImporter:
    """Create a data importer."""
    return DataImporter(store)