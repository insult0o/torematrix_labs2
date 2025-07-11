#!/usr/bin/env python3
"""
Test script for the new manual validation workflow.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from tore_matrix_labs.config.settings import Settings
from tore_matrix_labs.config.constants import DocumentType
from tore_matrix_labs.core.workflow_integration import WorkflowIntegrationManager, create_project_with_manual_validation
from tore_matrix_labs.models.manual_validation_models import (
    ManualValidationSession, DocumentSnippet, SnippetType, 
    SnippetLocation, SnippetMetadata
)


def test_workflow_initialization():
    """Test workflow initialization."""
    print("🧪 Testing Manual Validation Workflow Initialization")
    print("=" * 60)
    
    # Initialize settings
    settings = Settings()
    
    # Create workflow manager
    workflow_manager = WorkflowIntegrationManager(settings)
    
    # Test document path
    test_document = "5555.pdf"
    if not Path(test_document).exists():
        print(f"❌ Test document not found: {test_document}")
        return False
    
    # Start document processing
    print(f"📄 Starting document processing: {test_document}")
    result = workflow_manager.start_document_processing(test_document, DocumentType.ICAO)
    
    if result['success']:
        print("✅ Document processing initialized successfully")
        print(f"   📋 Document ID: {result['document'].id}")
        print(f"   📊 Page count: {result['document'].metadata.page_count}")
        print(f"   🎯 Next step: {result['next_step']}")
        
        # Test workflow state
        workflow_state = result['workflow_state']
        status = workflow_manager.get_workflow_status(workflow_state)
        
        print(f"   📈 Workflow status: {status['status']}")
        print(f"   📝 Workflow version: {status['workflow_version']}")
        
        return True
    else:
        print(f"❌ Document processing failed: {result.get('error', 'Unknown error')}")
        return False


def test_manual_validation_simulation():
    """Test manual validation simulation."""
    print("\n🧪 Testing Manual Validation Simulation")
    print("=" * 60)
    
    # Initialize settings
    settings = Settings()
    workflow_manager = WorkflowIntegrationManager(settings)
    
    # Test document path
    test_document = "5555.pdf"
    if not Path(test_document).exists():
        print(f"❌ Test document not found: {test_document}")
        return False
    
    # Start document processing
    result = workflow_manager.start_document_processing(test_document, DocumentType.ICAO)
    
    if not result['success']:
        print(f"❌ Failed to initialize workflow: {result.get('error')}")
        return False
    
    # Get validation session
    validation_session = result['validation_session']
    workflow_state = result['workflow_state']
    
    # Simulate manual validation by adding some snippets
    print("📝 Simulating manual validation...")
    
    # Add some test snippets
    test_snippets = [
        {
            'id': 'test_image_1',
            'type': SnippetType.IMAGE,
            'page': 1,
            'bbox': [100, 100, 200, 200],
            'user_name': 'Test Image 1'
        },
        {
            'id': 'test_table_1',
            'type': SnippetType.TABLE,
            'page': 1,
            'bbox': [100, 300, 400, 500],
            'user_name': 'Test Table 1'
        },
        {
            'id': 'test_diagram_1',
            'type': SnippetType.DIAGRAM,
            'page': 2,
            'bbox': [150, 150, 350, 350],
            'user_name': 'Test Diagram 1'
        }
    ]
    
    for snippet_data in test_snippets:
        # Create snippet
        snippet = DocumentSnippet(
            id=snippet_data['id'],
            snippet_type=snippet_data['type'],
            location=SnippetLocation(
                page=snippet_data['page'],
                bbox=snippet_data['bbox']
            ),
            metadata=SnippetMetadata(
                snippet_id=snippet_data['id'],
                snippet_type=snippet_data['type'],
                user_name=snippet_data['user_name']
            )
        )
        
        # Add to validation session
        if snippet_data['page'] not in validation_session.page_results:
            from tore_matrix_labs.models.manual_validation_models import PageValidationResult
            validation_session.page_results[snippet_data['page']] = PageValidationResult(
                page_number=snippet_data['page']
            )
        
        validation_session.page_results[snippet_data['page']].snippets.append(snippet)
    
    # Update validated pages
    validation_session.validated_pages = [1, 2]
    
    print(f"   ✅ Added {len(test_snippets)} test snippets")
    print(f"   📊 Statistics: {validation_session.get_statistics()}")
    
    # Complete manual validation
    print("🎯 Completing manual validation...")
    completion_result = workflow_manager.complete_manual_validation(workflow_state, validation_session)
    
    if completion_result['success']:
        print("✅ Manual validation completed successfully")
        print(f"   📋 Final document status: {completion_result['document'].processing_status.value}")
        print(f"   🎯 Quality score: {completion_result['document'].quality_score}")
        
        # Test LLM export
        print("📤 Testing LLM export...")
        llm_export = workflow_manager.create_llm_ready_export(completion_result['workflow_state'])
        
        if llm_export['success']:
            print("✅ LLM export created successfully")
            print(f"   📝 Total snippets: {llm_export['llm_export']['manual_validation_results']['total_snippets']}")
            print(f"   🎯 Export ready: {llm_export['llm_export']['quality_assessment']['export_ready']}")
        else:
            print(f"❌ LLM export failed: {llm_export.get('error')}")
        
        return True
    else:
        print(f"❌ Manual validation completion failed: {completion_result.get('error')}")
        return False


def test_project_integration():
    """Test project integration with manual validation."""
    print("\n🧪 Testing Project Integration")
    print("=" * 60)
    
    # Create test project
    test_documents = ["5555.pdf"]
    
    # Check if test document exists
    if not Path(test_documents[0]).exists():
        print(f"❌ Test document not found: {test_documents[0]}")
        return False
    
    # Initialize settings
    settings = Settings()
    
    # Create project with manual validation
    project_data = create_project_with_manual_validation(
        "Test Manual Validation Project",
        test_documents,
        settings
    )
    
    print("✅ Created test project with manual validation")
    print(f"   📋 Project name: {project_data['name']}")
    print(f"   📝 Version: {project_data['version']}")
    print(f"   🎯 Manual validation enabled: {project_data['workflow_metadata']['manual_validation_enabled']}")
    print(f"   📊 Documents: {len(project_data['documents'])}")
    
    # Save project to file
    project_file = Path("test_manual_validation_project.tore")
    with open(project_file, 'w') as f:
        json.dump(project_data, f, indent=2)
    
    print(f"💾 Saved project to: {project_file}")
    
    # Test loading project
    with open(project_file, 'r') as f:
        loaded_project = json.load(f)
    
    print("✅ Project loaded successfully")
    
    # Test workflow integration
    workflow_manager = WorkflowIntegrationManager(settings)
    workflow_state = workflow_manager.load_workflow_from_project(loaded_project)
    
    if workflow_state:
        print("✅ Workflow state loaded from project")
        print(f"   📋 Document ID: {workflow_state['document_id']}")
        print(f"   📝 Status: {workflow_state['status']}")
    else:
        print("ℹ️  No existing workflow state in project (expected for new project)")
    
    return True


def test_exclusion_zones():
    """Test exclusion zones functionality."""
    print("\n🧪 Testing Exclusion Zones")
    print("=" * 60)
    
    from tore_matrix_labs.core.exclusion_zones import ExclusionZoneManager, ExclusionZone
    
    # Create exclusion zone manager
    exclusion_manager = ExclusionZoneManager()
    
    # Create test exclusion zones
    test_zones = [
        ExclusionZone(
            page=1,
            bbox=[100, 100, 200, 200],
            zone_type='IMAGE',
            snippet_id='test_image_1',
            priority=3
        ),
        ExclusionZone(
            page=1,
            bbox=[100, 300, 400, 500],
            zone_type='TABLE',
            snippet_id='test_table_1',
            priority=1
        )
    ]
    
    # Add zones
    for zone in test_zones:
        exclusion_manager.add_zone(zone)
    
    print(f"✅ Added {len(test_zones)} exclusion zones")
    
    # Test exclusion logic
    test_elements = [
        {'bbox': [150, 150, 180, 180], 'text': 'Text in image area'},  # Should be excluded
        {'bbox': [250, 250, 280, 280], 'text': 'Text outside areas'},  # Should be included
        {'bbox': [200, 350, 300, 400], 'text': 'Text in table area'},  # Should be excluded
    ]
    
    for element in test_elements:
        should_exclude, zone = exclusion_manager.should_exclude_text_element(1, element['bbox'])
        status = "❌ EXCLUDED" if should_exclude else "✅ INCLUDED"
        zone_info = f" (in {zone.zone_type} zone)" if zone else ""
        print(f"   {status} '{element['text']}'{zone_info}")
    
    # Test statistics
    stats = exclusion_manager.get_exclusion_statistics()
    print(f"📊 Exclusion statistics: {stats}")
    
    return True


def main():
    """Run all tests."""
    print("🚀 TORE Matrix Labs - Manual Validation Workflow Test Suite")
    print("=" * 80)
    
    tests = [
        ("Workflow Initialization", test_workflow_initialization),
        ("Manual Validation Simulation", test_manual_validation_simulation),
        ("Project Integration", test_project_integration),
        ("Exclusion Zones", test_exclusion_zones)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
                failed += 1
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Manual validation workflow is ready.")
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)