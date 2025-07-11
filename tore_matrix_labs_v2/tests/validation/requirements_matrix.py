#!/usr/bin/env python3
"""
Requirements Matrix for TORE Matrix Labs V2 Validation

This module defines all original requirements, planned features, and desired
functionality that must be verified in the refactored V2 system.

It creates a comprehensive test matrix that automatically validates:
- Every endpoint and API function
- All core business logic
- UI workflows and interactions
- Performance requirements
- Data integrity and migration
- Security and error handling
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
import json
from pathlib import Path


class RequirementType(Enum):
    """Types of requirements to validate."""
    CORE_FUNCTIONALITY = "core_functionality"
    API_ENDPOINT = "api_endpoint"
    UI_WORKFLOW = "ui_workflow"
    PERFORMANCE = "performance"
    DATA_INTEGRITY = "data_integrity"
    SECURITY = "security"
    MIGRATION = "migration"
    INTEGRATION = "integration"


class RequirementStatus(Enum):
    """Status of requirement validation."""
    NOT_TESTED = "not_tested"
    PASSED = "passed"
    FAILED = "failed"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    NOT_IMPLEMENTED = "not_implemented"


@dataclass
class TestCase:
    """Individual test case for a requirement."""
    id: str
    name: str
    description: str
    test_function: str  # Function name to execute
    expected_result: Any
    test_data: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    timeout: int = 30  # seconds


@dataclass
class Requirement:
    """A single requirement with associated test cases."""
    id: str
    name: str
    description: str
    requirement_type: RequirementType
    priority: str  # high, medium, low
    
    # Original specification references
    original_feature: str = ""
    claude_md_reference: str = ""
    planned_enhancement: str = ""
    
    # Testing
    test_cases: List[TestCase] = field(default_factory=list)
    status: RequirementStatus = RequirementStatus.NOT_TESTED
    
    # Results
    test_results: Dict[str, Any] = field(default_factory=dict)
    implementation_notes: str = ""
    
    def add_test_case(self, test_case: TestCase):
        """Add a test case to this requirement."""
        self.test_cases.append(test_case)
    
    def is_fully_tested(self) -> bool:
        """Check if all test cases have been executed."""
        return all(tc.id in self.test_results for tc in self.test_cases)


class RequirementsMatrix:
    """Complete requirements matrix for V2 validation."""
    
    def __init__(self):
        self.requirements: Dict[str, Requirement] = {}
        self._load_requirements()
    
    def _load_requirements(self):
        """Load all requirements from specifications."""
        
        # Core Document Processing Requirements
        self._add_document_processing_requirements()
        
        # API and Service Requirements  
        self._add_api_requirements()
        
        # UI and Workflow Requirements
        self._add_ui_requirements()
        
        # Performance Requirements
        self._add_performance_requirements()
        
        # Data and Migration Requirements
        self._add_data_requirements()
        
        # Security Requirements
        self._add_security_requirements()
        
        # Integration Requirements
        self._add_integration_requirements()
    
    def _add_document_processing_requirements(self):
        """Add core document processing requirements."""
        
        # PDF Processing
        req = Requirement(
            id="DOC_001",
            name="PDF Document Processing",
            description="Process PDF documents with complete text extraction",
            requirement_type=RequirementType.CORE_FUNCTIONALITY,
            priority="high",
            original_feature="Original PDF processing using PyMuPDF",
            claude_md_reference="PDF processing with quality validation"
        )
        
        req.add_test_case(TestCase(
            id="DOC_001_001",
            name="Basic PDF Text Extraction",
            description="Extract text from simple PDF document",
            test_function="test_pdf_text_extraction",
            expected_result={"success": True, "text_length": ">100"}
        ))
        
        req.add_test_case(TestCase(
            id="DOC_001_002", 
            name="PDF Coordinate Mapping",
            description="Extract character-level coordinates from PDF",
            test_function="test_pdf_coordinate_extraction",
            expected_result={"success": True, "coordinates_count": ">50"}
        ))
        
        req.add_test_case(TestCase(
            id="DOC_001_003",
            name="PDF Image Detection",
            description="Detect and extract image areas from PDF",
            test_function="test_pdf_image_detection",
            expected_result={"success": True, "images_detected": ">=0"}
        ))
        
        self.requirements["DOC_001"] = req
        
        # DOCX Processing
        req = Requirement(
            id="DOC_002",
            name="DOCX Document Processing",
            description="Process Microsoft Word documents",
            requirement_type=RequirementType.CORE_FUNCTIONALITY,
            priority="high",
            original_feature="DOCX support planned in original roadmap"
        )
        
        req.add_test_case(TestCase(
            id="DOC_002_001",
            name="DOCX Text Extraction",
            description="Extract text from DOCX document",
            test_function="test_docx_text_extraction",
            expected_result={"success": True, "text_extracted": True}
        ))
        
        self.requirements["DOC_002"] = req
        
        # OCR Processing
        req = Requirement(
            id="DOC_003",
            name="OCR Text Recognition",
            description="OCR processing for scanned documents",
            requirement_type=RequirementType.CORE_FUNCTIONALITY,
            priority="medium",
            original_feature="OCR integration in original system"
        )
        
        req.add_test_case(TestCase(
            id="DOC_003_001",
            name="OCR Engine Integration",
            description="Process document using OCR when needed",
            test_function="test_ocr_processing",
            expected_result={"success": True, "ocr_executed": True}
        ))
        
        self.requirements["DOC_003"] = req
    
    def _add_api_requirements(self):
        """Add API and service endpoint requirements."""
        
        # UnifiedDocumentProcessor API
        req = Requirement(
            id="API_001",
            name="UnifiedDocumentProcessor API",
            description="Complete document processing API",
            requirement_type=RequirementType.API_ENDPOINT,
            priority="high",
            original_feature="Consolidates document_processor.py and enhanced_document_processor.py"
        )
        
        req.add_test_case(TestCase(
            id="API_001_001",
            name="Process Document Endpoint",
            description="Test process_document() method",
            test_function="test_process_document_api",
            expected_result={"success": True, "processing_result": "not_null"}
        ))
        
        req.add_test_case(TestCase(
            id="API_001_002",
            name="Batch Processing Endpoint",
            description="Test process_batch() method",
            test_function="test_batch_processing_api",
            expected_result={"success": True, "batch_results": ">=1"}
        ))
        
        self.requirements["API_001"] = req
        
        # CoordinateMappingService API
        req = Requirement(
            id="API_002",
            name="CoordinateMappingService API",
            description="Coordinate transformation service",
            requirement_type=RequirementType.API_ENDPOINT,
            priority="high",
            original_feature="Replaces duplicated coordinate logic across 5+ widgets"
        )
        
        req.add_test_case(TestCase(
            id="API_002_001",
            name="PDF to Widget Coordinate Mapping",
            description="Test pdf_to_widget() transformation",
            test_function="test_pdf_to_widget_mapping",
            expected_result={"success": True, "coordinates_transformed": True}
        ))
        
        req.add_test_case(TestCase(
            id="API_002_002",
            name="Character Level Mapping",
            description="Test character-level coordinate mapping",
            test_function="test_character_level_mapping",
            expected_result={"success": True, "character_positions": ">0"}
        ))
        
        self.requirements["API_002"] = req
        
        # EventBus API
        req = Requirement(
            id="API_003",
            name="EventBus Communication System",
            description="Decoupled event-based communication",
            requirement_type=RequirementType.API_ENDPOINT,
            priority="medium",
            original_feature="Replaces complex Qt signal chains"
        )
        
        req.add_test_case(TestCase(
            id="API_003_001",
            name="Event Publishing",
            description="Test event publishing mechanism",
            test_function="test_event_publishing",
            expected_result={"success": True, "event_published": True}
        ))
        
        req.add_test_case(TestCase(
            id="API_003_002",
            name="Event Subscription",
            description="Test event subscription and handling",
            test_function="test_event_subscription",
            expected_result={"success": True, "event_received": True}
        ))
        
        self.requirements["API_003"] = req
    
    def _add_ui_requirements(self):
        """Add UI workflow requirements."""
        
        # Page-by-Page Validation
        req = Requirement(
            id="UI_001",
            name="Page-by-Page Validation Workflow",
            description="Side-by-side PDF and text validation",
            requirement_type=RequirementType.UI_WORKFLOW,
            priority="high",
            original_feature="PageValidationWidget replacing problematic coordinate highlighting",
            claude_md_reference="New page-by-page interface implementation"
        )
        
        req.add_test_case(TestCase(
            id="UI_001_001",
            name="Page Navigation",
            description="Navigate between document pages",
            test_function="test_page_navigation",
            expected_result={"success": True, "page_changed": True}
        ))
        
        req.add_test_case(TestCase(
            id="UI_001_002",
            name="Issue Highlighting",
            description="Highlight corrections in PDF and text",
            test_function="test_issue_highlighting",
            expected_result={"success": True, "highlighting_active": True}
        ))
        
        req.add_test_case(TestCase(
            id="UI_001_003",
            name="Correction Workflow",
            description="Approve/reject corrections workflow",
            test_function="test_correction_workflow",
            expected_result={"success": True, "corrections_processed": True}
        ))
        
        self.requirements["UI_001"] = req
        
        # Document Loading and Display
        req = Requirement(
            id="UI_002",
            name="Document Loading and Display",
            description="Load and display documents in UI",
            requirement_type=RequirementType.UI_WORKFLOW,
            priority="high",
            original_feature="Document loading from original main.py"
        )
        
        req.add_test_case(TestCase(
            id="UI_002_001",
            name="Document Loading",
            description="Load document into UI",
            test_function="test_document_loading",
            expected_result={"success": True, "document_loaded": True}
        ))
        
        self.requirements["UI_002"] = req
    
    def _add_performance_requirements(self):
        """Add performance requirements."""
        
        req = Requirement(
            id="PERF_001",
            name="Document Processing Performance",
            description="Processing speed requirements",
            requirement_type=RequirementType.PERFORMANCE,
            priority="medium",
            original_feature="Performance optimization goals"
        )
        
        req.add_test_case(TestCase(
            id="PERF_001_001",
            name="Single Document Processing Speed",
            description="Process single document within time limit",
            test_function="test_single_document_performance",
            expected_result={"processing_time": "<5.0"},
            timeout=10
        ))
        
        req.add_test_case(TestCase(
            id="PERF_001_002",
            name="Memory Usage",
            description="Memory usage within acceptable limits",
            test_function="test_memory_usage",
            expected_result={"memory_increase": "<100MB"}
        ))
        
        self.requirements["PERF_001"] = req
    
    def _add_data_requirements(self):
        """Add data integrity and migration requirements."""
        
        # .tore File Migration
        req = Requirement(
            id="DATA_001",
            name="TORE File Migration",
            description="Migrate existing .tore files to V2 format",
            requirement_type=RequirementType.MIGRATION,
            priority="high",
            original_feature="Backward compatibility with all existing .tore files"
        )
        
        req.add_test_case(TestCase(
            id="DATA_001_001",
            name="V1.0 to V2.0 Migration",
            description="Migrate V1.0 .tore file to V2.0",
            test_function="test_v1_0_migration",
            expected_result={"success": True, "data_preserved": True}
        ))
        
        req.add_test_case(TestCase(
            id="DATA_001_002",
            name="V1.1 to V2.0 Migration",
            description="Migrate V1.1 .tore file to V2.0",
            test_function="test_v1_1_migration",
            expected_result={"success": True, "data_preserved": True}
        ))
        
        req.add_test_case(TestCase(
            id="DATA_001_003",
            name="Batch Migration",
            description="Migrate multiple files in batch",
            test_function="test_batch_migration",
            expected_result={"success": True, "all_files_migrated": True}
        ))
        
        self.requirements["DATA_001"] = req
        
        # Data Validation
        req = Requirement(
            id="DATA_002",
            name="Data Integrity Validation",
            description="Ensure data integrity throughout processing",
            requirement_type=RequirementType.DATA_INTEGRITY,
            priority="high",
            original_feature="Quality assurance engine"
        )
        
        req.add_test_case(TestCase(
            id="DATA_002_001",
            name="Coordinate Data Validation",
            description="Validate coordinate data integrity",
            test_function="test_coordinate_validation",
            expected_result={"success": True, "coordinates_valid": True}
        ))
        
        self.requirements["DATA_002"] = req
    
    def _add_security_requirements(self):
        """Add security requirements."""
        
        req = Requirement(
            id="SEC_001",
            name="Input Validation and Security",
            description="Secure handling of document inputs",
            requirement_type=RequirementType.SECURITY,
            priority="medium",
            original_feature="Secure document processing"
        )
        
        req.add_test_case(TestCase(
            id="SEC_001_001",
            name="Malicious File Handling",
            description="Safely handle potentially malicious files",
            test_function="test_malicious_file_handling",
            expected_result={"success": True, "security_maintained": True}
        ))
        
        self.requirements["SEC_001"] = req
    
    def _add_integration_requirements(self):
        """Add integration requirements."""
        
        req = Requirement(
            id="INT_001",
            name="End-to-End Integration",
            description="Complete workflow integration",
            requirement_type=RequirementType.INTEGRATION,
            priority="high",
            original_feature="Complete document processing pipeline"
        )
        
        req.add_test_case(TestCase(
            id="INT_001_001",
            name="Complete Processing Pipeline",
            description="Test entire processing pipeline end-to-end",
            test_function="test_complete_pipeline",
            expected_result={"success": True, "pipeline_completed": True}
        ))
        
        self.requirements["INT_001"] = req
    
    def get_requirements_by_type(self, req_type: RequirementType) -> List[Requirement]:
        """Get requirements by type."""
        return [req for req in self.requirements.values() 
                if req.requirement_type == req_type]
    
    def get_requirements_by_priority(self, priority: str) -> List[Requirement]:
        """Get requirements by priority."""
        return [req for req in self.requirements.values() 
                if req.priority == priority]
    
    def get_all_test_cases(self) -> List[TestCase]:
        """Get all test cases from all requirements."""
        test_cases = []
        for req in self.requirements.values():
            test_cases.extend(req.test_cases)
        return test_cases
    
    def get_coverage_statistics(self) -> Dict[str, Any]:
        """Get testing coverage statistics."""
        total_requirements = len(self.requirements)
        total_test_cases = len(self.get_all_test_cases())
        
        tested_requirements = sum(1 for req in self.requirements.values() 
                                if req.status != RequirementStatus.NOT_TESTED)
        
        passed_requirements = sum(1 for req in self.requirements.values() 
                                if req.status == RequirementStatus.PASSED)
        
        return {
            "total_requirements": total_requirements,
            "total_test_cases": total_test_cases,
            "tested_requirements": tested_requirements,
            "passed_requirements": passed_requirements,
            "coverage_percentage": (tested_requirements / total_requirements * 100) if total_requirements > 0 else 0,
            "pass_rate": (passed_requirements / tested_requirements * 100) if tested_requirements > 0 else 0
        }
    
    def export_requirements_matrix(self, output_path: Path):
        """Export requirements matrix to JSON."""
        data = {
            "requirements": {
                req_id: {
                    "id": req.id,
                    "name": req.name,
                    "description": req.description,
                    "requirement_type": req.requirement_type.value,
                    "priority": req.priority,
                    "original_feature": req.original_feature,
                    "claude_md_reference": req.claude_md_reference,
                    "planned_enhancement": req.planned_enhancement,
                    "status": req.status.value,
                    "test_cases": [
                        {
                            "id": tc.id,
                            "name": tc.name,
                            "description": tc.description,
                            "test_function": tc.test_function,
                            "expected_result": tc.expected_result
                        }
                        for tc in req.test_cases
                    ],
                    "test_results": req.test_results,
                    "implementation_notes": req.implementation_notes
                }
                for req_id, req in self.requirements.items()
            },
            "statistics": self.get_coverage_statistics()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# Global requirements matrix instance
REQUIREMENTS_MATRIX = RequirementsMatrix()


def get_requirements_matrix() -> RequirementsMatrix:
    """Get the global requirements matrix."""
    return REQUIREMENTS_MATRIX


def export_requirements_summary():
    """Export a human-readable requirements summary."""
    matrix = get_requirements_matrix()
    
    summary = []
    summary.append("# TORE Matrix Labs V2 - Requirements Matrix Summary\n")
    
    # Statistics
    stats = matrix.get_coverage_statistics()
    summary.append(f"**Total Requirements:** {stats['total_requirements']}")
    summary.append(f"**Total Test Cases:** {stats['total_test_cases']}")
    summary.append(f"**Coverage:** {stats['coverage_percentage']:.1f}%")
    summary.append(f"**Pass Rate:** {stats['pass_rate']:.1f}%\n")
    
    # Requirements by type
    for req_type in RequirementType:
        reqs = matrix.get_requirements_by_type(req_type)
        if reqs:
            summary.append(f"## {req_type.value.replace('_', ' ').title()}")
            for req in reqs:
                summary.append(f"- **{req.id}**: {req.name} ({len(req.test_cases)} test cases)")
            summary.append("")
    
    return "\n".join(summary)


if __name__ == "__main__":
    # Export requirements matrix for review
    matrix = get_requirements_matrix()
    matrix.export_requirements_matrix(Path("requirements_matrix.json"))
    
    with open("requirements_summary.md", "w") as f:
        f.write(export_requirements_summary())
    
    print("✅ Requirements matrix exported to requirements_matrix.json")
    print("📋 Requirements summary exported to requirements_summary.md")
    print(f"📊 Total: {len(matrix.requirements)} requirements, {len(matrix.get_all_test_cases())} test cases")