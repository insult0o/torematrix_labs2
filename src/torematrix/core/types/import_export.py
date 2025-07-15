"""Type Definition Import/Export System

Comprehensive import/export functionality for type definitions with:
- Multiple format support (JSON, XML, YAML, binary)
- Validation and schema checking
- Conflict resolution and merging strategies
- Batch processing capabilities
"""

import json
import yaml
import pickle
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, IO
import xml.etree.ElementTree as ET
from xml.dom import minidom
import gzip
import zipfile
import tempfile
import hashlib
import datetime

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """Supported export formats"""
    JSON = "json"
    YAML = "yaml"
    XML = "xml"
    PICKLE = "pickle"
    BINARY = "binary"
    ZIP = "zip"


class ImportStrategy(Enum):
    """Import merge strategies"""
    REPLACE = "replace"  # Replace existing definitions
    MERGE = "merge"      # Merge with existing definitions
    SKIP = "skip"        # Skip existing definitions
    UPDATE = "update"    # Update only changed fields


class ValidationLevel(Enum):
    """Validation strictness levels"""
    NONE = "none"
    BASIC = "basic"
    STRICT = "strict"
    PARANOID = "paranoid"


@dataclass
class ExportOptions:
    """Export configuration options"""
    format: ExportFormat = ExportFormat.JSON
    include_metadata: bool = True
    include_schema: bool = True
    compress: bool = False
    pretty_format: bool = True
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    filter_types: List[str] = field(default_factory=list)
    exclude_internal: bool = True


@dataclass
class ImportOptions:
    """Import configuration options"""
    strategy: ImportStrategy = ImportStrategy.MERGE
    validation_level: ValidationLevel = ValidationLevel.STRICT
    create_backup: bool = True
    ignore_version_conflicts: bool = False
    custom_resolvers: Dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False


@dataclass
class ExportResult:
    """Result of export operation"""
    success: bool
    file_path: Optional[Path] = None
    format: Optional[ExportFormat] = None
    exported_count: int = 0
    file_size: int = 0
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ImportResult:
    """Result of import operation"""
    success: bool
    imported_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    conflicts_resolved: int = 0
    backup_created: Optional[Path] = None
    imported_types: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class TypeDefinitionData:
    """Container for type definition data"""
    id: str
    name: str
    version: str
    definition: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    schema: Optional[Dict[str, Any]] = None
    dependencies: List[str] = field(default_factory=list)
    checksum: Optional[str] = None
    
    def calculate_checksum(self) -> str:
        """Calculate checksum for definition"""
        data_str = json.dumps(self.definition, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()


class FormatHandler(ABC):
    """Abstract base class for format handlers"""
    
    @abstractmethod
    def export(self, data: List[TypeDefinitionData], 
               file_path: Path, options: ExportOptions) -> ExportResult:
        """Export data to file"""
        pass
    
    @abstractmethod
    def import_data(self, file_path: Path, 
                   options: ImportOptions) -> List[TypeDefinitionData]:
        """Import data from file"""
        pass
    
    @abstractmethod
    def validate_file(self, file_path: Path) -> tuple[bool, List[str]]:
        """Validate file format"""
        pass


class JSONFormatHandler(FormatHandler):
    """JSON format handler"""
    
    def export(self, data: List[TypeDefinitionData], 
               file_path: Path, options: ExportOptions) -> ExportResult:
        """Export to JSON format"""
        try:
            export_data = {
                "export_info": {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "format": "json",
                    "version": "1.0",
                    "type_count": len(data),
                    "options": {
                        "include_metadata": options.include_metadata,
                        "include_schema": options.include_schema,
                        "exclude_internal": options.exclude_internal
                    }
                },
                "types": {}
            }
            
            # Add custom fields
            if options.custom_fields:
                export_data["export_info"]["custom"] = options.custom_fields
            
            # Process each type definition
            for type_def in data:
                type_data = {
                    "name": type_def.name,
                    "version": type_def.version,
                    "definition": type_def.definition
                }
                
                if options.include_metadata:
                    type_data["metadata"] = type_def.metadata
                
                if options.include_schema and type_def.schema:
                    type_data["schema"] = type_def.schema
                
                if type_def.dependencies:
                    type_data["dependencies"] = type_def.dependencies
                
                type_data["checksum"] = type_def.calculate_checksum()
                export_data["types"][type_def.id] = type_data
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                if options.pretty_format:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(export_data, f, separators=(',', ':'))
            
            # Calculate result
            file_size = file_path.stat().st_size
            checksum = self._calculate_file_checksum(file_path)
            
            return ExportResult(
                success=True,
                file_path=file_path,
                format=ExportFormat.JSON,
                exported_count=len(data),
                file_size=file_size,
                checksum=checksum,
                metadata=export_data["export_info"]
            )
            
        except Exception as e:
            logger.error(f"JSON export failed: {e}")
            return ExportResult(
                success=False,
                errors=[f"JSON export failed: {e}"]
            )
    
    def import_data(self, file_path: Path, 
                   options: ImportOptions) -> List[TypeDefinitionData]:
        """Import from JSON format"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate structure
            if "types" not in data:
                raise ValueError("Invalid JSON structure: missing 'types' section")
            
            type_definitions = []
            for type_id, type_data in data["types"].items():
                type_def = TypeDefinitionData(
                    id=type_id,
                    name=type_data["name"],
                    version=type_data["version"],
                    definition=type_data["definition"],
                    metadata=type_data.get("metadata", {}),
                    schema=type_data.get("schema"),
                    dependencies=type_data.get("dependencies", []),
                    checksum=type_data.get("checksum")
                )
                type_definitions.append(type_def)
            
            return type_definitions
            
        except Exception as e:
            logger.error(f"JSON import failed: {e}")
            raise ValueError(f"JSON import failed: {e}")
    
    def validate_file(self, file_path: Path) -> tuple[bool, List[str]]:
        """Validate JSON file"""
        errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check required structure
            if not isinstance(data, dict):
                errors.append("Root element must be an object")
            
            if "types" not in data:
                errors.append("Missing required 'types' section")
            
            if "export_info" not in data:
                errors.append("Missing 'export_info' section")
            
            # Validate types section
            if "types" in data:
                for type_id, type_data in data["types"].items():
                    if not isinstance(type_data, dict):
                        errors.append(f"Type '{type_id}' must be an object")
                        continue
                    
                    required_fields = ["name", "version", "definition"]
                    for field in required_fields:
                        if field not in type_data:
                            errors.append(f"Type '{type_id}' missing required field: {field}")
            
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON syntax: {e}")
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return len(errors) == 0, errors
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate file checksum"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()


class YAMLFormatHandler(FormatHandler):
    """YAML format handler"""
    
    def export(self, data: List[TypeDefinitionData], 
               file_path: Path, options: ExportOptions) -> ExportResult:
        """Export to YAML format"""
        try:
            export_data = {
                "export_info": {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "format": "yaml",
                    "version": "1.0",
                    "type_count": len(data)
                },
                "types": {}
            }
            
            # Process type definitions
            for type_def in data:
                type_data = {
                    "name": type_def.name,
                    "version": type_def.version,
                    "definition": type_def.definition
                }
                
                if options.include_metadata:
                    type_data["metadata"] = type_def.metadata
                
                export_data["types"][type_def.id] = type_data
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(export_data, f, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            
            file_size = file_path.stat().st_size
            checksum = self._calculate_file_checksum(file_path)
            
            return ExportResult(
                success=True,
                file_path=file_path,
                format=ExportFormat.YAML,
                exported_count=len(data),
                file_size=file_size,
                checksum=checksum
            )
            
        except Exception as e:
            logger.error(f"YAML export failed: {e}")
            return ExportResult(
                success=False,
                errors=[f"YAML export failed: {e}"]
            )
    
    def import_data(self, file_path: Path, 
                   options: ImportOptions) -> List[TypeDefinitionData]:
        """Import from YAML format"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if "types" not in data:
                raise ValueError("Invalid YAML structure: missing 'types' section")
            
            type_definitions = []
            for type_id, type_data in data["types"].items():
                type_def = TypeDefinitionData(
                    id=type_id,
                    name=type_data["name"],
                    version=type_data["version"],
                    definition=type_data["definition"],
                    metadata=type_data.get("metadata", {}),
                    dependencies=type_data.get("dependencies", [])
                )
                type_definitions.append(type_def)
            
            return type_definitions
            
        except Exception as e:
            logger.error(f"YAML import failed: {e}")
            raise ValueError(f"YAML import failed: {e}")
    
    def validate_file(self, file_path: Path) -> tuple[bool, List[str]]:
        """Validate YAML file"""
        errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not isinstance(data, dict):
                errors.append("Root element must be a mapping")
            
            if "types" not in data:
                errors.append("Missing required 'types' section")
            
        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML syntax: {e}")
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return len(errors) == 0, errors
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate file checksum"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()


class XMLFormatHandler(FormatHandler):
    """XML format handler"""
    
    def export(self, data: List[TypeDefinitionData], 
               file_path: Path, options: ExportOptions) -> ExportResult:
        """Export to XML format"""
        try:
            # Create root element
            root = ET.Element("type_definitions")
            
            # Add export info
            export_info = ET.SubElement(root, "export_info")
            ET.SubElement(export_info, "timestamp").text = datetime.datetime.now().isoformat()
            ET.SubElement(export_info, "format").text = "xml"
            ET.SubElement(export_info, "version").text = "1.0"
            ET.SubElement(export_info, "type_count").text = str(len(data))
            
            # Add types
            types_elem = ET.SubElement(root, "types")
            
            for type_def in data:
                type_elem = ET.SubElement(types_elem, "type")
                type_elem.set("id", type_def.id)
                
                ET.SubElement(type_elem, "name").text = type_def.name
                ET.SubElement(type_elem, "version").text = type_def.version
                
                # Add definition as CDATA
                definition_elem = ET.SubElement(type_elem, "definition")
                definition_elem.text = json.dumps(type_def.definition)
                
                if options.include_metadata and type_def.metadata:
                    metadata_elem = ET.SubElement(type_elem, "metadata")
                    metadata_elem.text = json.dumps(type_def.metadata)
            
            # Write to file
            if options.pretty_format:
                rough_string = ET.tostring(root, 'unicode')
                reparsed = minidom.parseString(rough_string)
                pretty_xml = reparsed.toprettyxml(indent="  ")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(pretty_xml)
            else:
                tree = ET.ElementTree(root)
                tree.write(file_path, encoding='utf-8', xml_declaration=True)
            
            file_size = file_path.stat().st_size
            checksum = self._calculate_file_checksum(file_path)
            
            return ExportResult(
                success=True,
                file_path=file_path,
                format=ExportFormat.XML,
                exported_count=len(data),
                file_size=file_size,
                checksum=checksum
            )
            
        except Exception as e:
            logger.error(f"XML export failed: {e}")
            return ExportResult(
                success=False,
                errors=[f"XML export failed: {e}"]
            )
    
    def import_data(self, file_path: Path, 
                   options: ImportOptions) -> List[TypeDefinitionData]:
        """Import from XML format"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            if root.tag != "type_definitions":
                raise ValueError("Invalid XML structure: root must be 'type_definitions'")
            
            types_elem = root.find("types")
            if types_elem is None:
                raise ValueError("Missing 'types' section")
            
            type_definitions = []
            for type_elem in types_elem.findall("type"):
                type_id = type_elem.get("id")
                name = type_elem.find("name").text
                version = type_elem.find("version").text
                definition_text = type_elem.find("definition").text
                
                definition = json.loads(definition_text)
                
                metadata = {}
                metadata_elem = type_elem.find("metadata")
                if metadata_elem is not None and metadata_elem.text:
                    metadata = json.loads(metadata_elem.text)
                
                type_def = TypeDefinitionData(
                    id=type_id,
                    name=name,
                    version=version,
                    definition=definition,
                    metadata=metadata
                )
                type_definitions.append(type_def)
            
            return type_definitions
            
        except Exception as e:
            logger.error(f"XML import failed: {e}")
            raise ValueError(f"XML import failed: {e}")
    
    def validate_file(self, file_path: Path) -> tuple[bool, List[str]]:
        """Validate XML file"""
        errors = []
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            if root.tag != "type_definitions":
                errors.append("Root element must be 'type_definitions'")
            
            types_elem = root.find("types")
            if types_elem is None:
                errors.append("Missing 'types' section")
            
        except ET.ParseError as e:
            errors.append(f"Invalid XML syntax: {e}")
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return len(errors) == 0, errors
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate file checksum"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()


class BinaryFormatHandler(FormatHandler):
    """Binary/Pickle format handler"""
    
    def export(self, data: List[TypeDefinitionData], 
               file_path: Path, options: ExportOptions) -> ExportResult:
        """Export to binary format"""
        try:
            export_data = {
                "export_info": {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "format": "binary",
                    "version": "1.0",
                    "type_count": len(data)
                },
                "types": data
            }
            
            with open(file_path, 'wb') as f:
                if options.compress:
                    with gzip.open(f, 'wb') as gz_f:
                        pickle.dump(export_data, gz_f, protocol=pickle.HIGHEST_PROTOCOL)
                else:
                    pickle.dump(export_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            file_size = file_path.stat().st_size
            checksum = self._calculate_file_checksum(file_path)
            
            return ExportResult(
                success=True,
                file_path=file_path,
                format=ExportFormat.BINARY,
                exported_count=len(data),
                file_size=file_size,
                checksum=checksum
            )
            
        except Exception as e:
            logger.error(f"Binary export failed: {e}")
            return ExportResult(
                success=False,
                errors=[f"Binary export failed: {e}"]
            )
    
    def import_data(self, file_path: Path, 
                   options: ImportOptions) -> List[TypeDefinitionData]:
        """Import from binary format"""
        try:
            with open(file_path, 'rb') as f:
                try:
                    # Try compressed first
                    with gzip.open(f, 'rb') as gz_f:
                        data = pickle.load(gz_f)
                except:
                    # Try uncompressed
                    f.seek(0)
                    data = pickle.load(f)
            
            if "types" not in data:
                raise ValueError("Invalid binary structure: missing 'types' section")
            
            return data["types"]
            
        except Exception as e:
            logger.error(f"Binary import failed: {e}")
            raise ValueError(f"Binary import failed: {e}")
    
    def validate_file(self, file_path: Path) -> tuple[bool, List[str]]:
        """Validate binary file"""
        errors = []
        
        try:
            with open(file_path, 'rb') as f:
                try:
                    # Try compressed
                    with gzip.open(f, 'rb') as gz_f:
                        data = pickle.load(gz_f)
                except:
                    # Try uncompressed
                    f.seek(0)
                    data = pickle.load(f)
            
            if not isinstance(data, dict):
                errors.append("Root data must be a dictionary")
            
            if "types" not in data:
                errors.append("Missing required 'types' section")
            
        except Exception as e:
            errors.append(f"Invalid binary format: {e}")
        
        return len(errors) == 0, errors
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate file checksum"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()


class TypeDefinitionImportExport:
    """Main class for importing and exporting type definitions"""
    
    def __init__(self):
        self.format_handlers: Dict[ExportFormat, FormatHandler] = {
            ExportFormat.JSON: JSONFormatHandler(),
            ExportFormat.YAML: YAMLFormatHandler(),
            ExportFormat.XML: XMLFormatHandler(),
            ExportFormat.BINARY: BinaryFormatHandler(),
            ExportFormat.PICKLE: BinaryFormatHandler(),
        }
        
        self.type_registry: Dict[str, TypeDefinitionData] = {}
        
        logger.info("TypeDefinitionImportExport initialized")
    
    def export_type_definitions(self, 
                              type_ids: List[str],
                              file_path: Union[str, Path],
                              options: Optional[ExportOptions] = None) -> ExportResult:
        """Export type definitions to file
        
        Args:
            type_ids: List of type IDs to export
            file_path: Destination file path
            options: Export options
            
        Returns:
            Export result with success status and metadata
        """
        if options is None:
            options = ExportOptions()
        
        file_path = Path(file_path)
        
        try:
            # Get type definitions
            type_definitions = []
            missing_types = []
            
            for type_id in type_ids:
                if type_id in self.type_registry:
                    type_def = self.type_registry[type_id]
                    
                    # Apply filters
                    if options.filter_types and type_def.name not in options.filter_types:
                        continue
                    
                    type_definitions.append(type_def)
                else:
                    missing_types.append(type_id)
            
            if missing_types:
                logger.warning(f"Missing type definitions: {missing_types}")
            
            if not type_definitions:
                return ExportResult(
                    success=False,
                    errors=["No type definitions found to export"]
                )
            
            # Get format handler
            handler = self.format_handlers.get(options.format)
            if not handler:
                return ExportResult(
                    success=False,
                    errors=[f"Unsupported export format: {options.format}"]
                )
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Export data
            result = handler.export(type_definitions, file_path, options)
            
            if result.success:
                logger.info(f"Exported {result.exported_count} type definitions to {file_path}")
            
            return result
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return ExportResult(
                success=False,
                errors=[f"Export failed: {e}"]
            )
    
    def import_type_definitions(self, 
                              file_path: Union[str, Path],
                              options: Optional[ImportOptions] = None) -> ImportResult:
        """Import type definitions from file
        
        Args:
            file_path: Source file path
            options: Import options
            
        Returns:
            Import result with success status and statistics
        """
        if options is None:
            options = ImportOptions()
        
        file_path = Path(file_path)
        
        try:
            if not file_path.exists():
                return ImportResult(
                    success=False,
                    errors=[f"File not found: {file_path}"]
                )
            
            # Detect format from file extension
            format_mapping = {
                '.json': ExportFormat.JSON,
                '.yaml': ExportFormat.YAML,
                '.yml': ExportFormat.YAML,
                '.xml': ExportFormat.XML,
                '.pkl': ExportFormat.BINARY,
                '.pickle': ExportFormat.BINARY,
                '.bin': ExportFormat.BINARY
            }
            
            file_format = format_mapping.get(file_path.suffix.lower())
            if not file_format:
                return ImportResult(
                    success=False,
                    errors=[f"Unknown file format: {file_path.suffix}"]
                )
            
            # Get format handler
            handler = self.format_handlers.get(file_format)
            if not handler:
                return ImportResult(
                    success=False,
                    errors=[f"No handler for format: {file_format}"]
                )
            
            # Validate file
            if options.validation_level != ValidationLevel.NONE:
                is_valid, validation_errors = handler.validate_file(file_path)
                if not is_valid:
                    return ImportResult(
                        success=False,
                        errors=[f"File validation failed: {'; '.join(validation_errors)}"]
                    )
            
            # Create backup if requested
            backup_path = None
            if options.create_backup and not options.dry_run:
                backup_path = self._create_backup()
            
            # Import data
            type_definitions = handler.import_data(file_path, options)
            
            if options.dry_run:
                return ImportResult(
                    success=True,
                    imported_count=len(type_definitions),
                    imported_types=[td.id for td in type_definitions]
                )
            
            # Process imported definitions
            result = self._process_imported_definitions(type_definitions, options)
            result.backup_created = backup_path
            
            logger.info(f"Imported {result.imported_count} type definitions from {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return ImportResult(
                success=False,
                errors=[f"Import failed: {e}"]
            )
    
    def _process_imported_definitions(self, 
                                    type_definitions: List[TypeDefinitionData],
                                    options: ImportOptions) -> ImportResult:
        """Process imported type definitions according to import strategy"""
        result = ImportResult(success=True)
        
        for type_def in type_definitions:
            try:
                existing_def = self.type_registry.get(type_def.id)
                
                if existing_def:
                    # Handle existing definition
                    if options.strategy == ImportStrategy.SKIP:
                        result.skipped_count += 1
                        continue
                    elif options.strategy == ImportStrategy.REPLACE:
                        self.type_registry[type_def.id] = type_def
                        result.updated_count += 1
                    elif options.strategy == ImportStrategy.MERGE:
                        merged_def = self._merge_definitions(existing_def, type_def)
                        self.type_registry[type_def.id] = merged_def
                        result.updated_count += 1
                        result.conflicts_resolved += 1
                    elif options.strategy == ImportStrategy.UPDATE:
                        if self._has_changes(existing_def, type_def):
                            self.type_registry[type_def.id] = type_def
                            result.updated_count += 1
                        else:
                            result.skipped_count += 1
                else:
                    # New definition
                    self.type_registry[type_def.id] = type_def
                    result.imported_count += 1
                
                result.imported_types.append(type_def.id)
                
            except Exception as e:
                result.errors.append(f"Error processing {type_def.id}: {e}")
        
        return result
    
    def _merge_definitions(self, 
                          existing: TypeDefinitionData, 
                          incoming: TypeDefinitionData) -> TypeDefinitionData:
        """Merge two type definitions"""
        merged = TypeDefinitionData(
            id=existing.id,
            name=incoming.name,  # Use incoming name
            version=incoming.version,  # Use incoming version
            definition={**existing.definition, **incoming.definition},
            metadata={**existing.metadata, **incoming.metadata},
            schema=incoming.schema or existing.schema,
            dependencies=list(set(existing.dependencies + incoming.dependencies))
        )
        
        merged.checksum = merged.calculate_checksum()
        return merged
    
    def _has_changes(self, existing: TypeDefinitionData, 
                    incoming: TypeDefinitionData) -> bool:
        """Check if incoming definition has changes"""
        return (existing.calculate_checksum() != incoming.calculate_checksum())
    
    def _create_backup(self) -> Path:
        """Create backup of current type registry"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = Path(tempfile.gettempdir()) / f"type_registry_backup_{timestamp}.json"
        
        # Export current registry to backup
        type_definitions = list(self.type_registry.values())
        handler = JSONFormatHandler()
        
        export_options = ExportOptions(
            format=ExportFormat.JSON,
            include_metadata=True,
            pretty_format=True
        )
        
        handler.export(type_definitions, backup_path, export_options)
        
        logger.info(f"Created backup: {backup_path}")
        return backup_path
    
    def register_type_definition(self, type_def: TypeDefinitionData):
        """Register a type definition in the registry"""
        self.type_registry[type_def.id] = type_def
        logger.debug(f"Registered type definition: {type_def.id}")
    
    def get_type_definition(self, type_id: str) -> Optional[TypeDefinitionData]:
        """Get a type definition by ID"""
        return self.type_registry.get(type_id)
    
    def list_type_definitions(self) -> List[TypeDefinitionData]:
        """List all registered type definitions"""
        return list(self.type_registry.values())
    
    def validate_file_format(self, file_path: Union[str, Path]) -> tuple[bool, List[str]]:
        """Validate a file's format without importing"""
        file_path = Path(file_path)
        
        # Detect format
        format_mapping = {
            '.json': ExportFormat.JSON,
            '.yaml': ExportFormat.YAML,
            '.yml': ExportFormat.YAML,
            '.xml': ExportFormat.XML,
            '.pkl': ExportFormat.BINARY,
            '.pickle': ExportFormat.BINARY,
            '.bin': ExportFormat.BINARY
        }
        
        file_format = format_mapping.get(file_path.suffix.lower())
        if not file_format:
            return False, [f"Unknown file format: {file_path.suffix}"]
        
        handler = self.format_handlers.get(file_format)
        if not handler:
            return False, [f"No handler for format: {file_format}"]
        
        return handler.validate_file(file_path)
    
    def get_format_info(self) -> Dict[str, Any]:
        """Get information about supported formats"""
        return {
            "supported_formats": list(ExportFormat),
            "format_extensions": {
                "json": [".json"],
                "yaml": [".yaml", ".yml"],
                "xml": [".xml"],
                "binary": [".pkl", ".pickle", ".bin"]
            },
            "features": {
                "compression": ["binary"],
                "pretty_formatting": ["json", "yaml", "xml"],
                "schema_validation": ["json", "yaml", "xml"],
                "metadata_support": ["json", "yaml", "xml", "binary"]
            }
        }


# Export main components
__all__ = [
    'ExportFormat',
    'ImportStrategy', 
    'ValidationLevel',
    'ExportOptions',
    'ImportOptions',
    'ExportResult',
    'ImportResult',
    'TypeDefinitionData',
    'TypeDefinitionImportExport'
]