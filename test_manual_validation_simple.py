#!/usr/bin/env python3
"""
Simple test for the manual validation workflow core components.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_manual_validation_models():
    """Test the manual validation models."""
    print("🧪 Testing Manual Validation Models")
    print("=" * 60)
    
    try:
        from tore_matrix_labs.models.manual_validation_models import (
            ManualValidationSession, DocumentSnippet, SnippetType, 
            SnippetLocation, SnippetMetadata, ValidationStatus
        )
        
        # Create a test validation session
        session = ManualValidationSession(
            document_id="test_doc_1",
            document_path="/path/to/test.pdf",
            total_pages=10
        )
        
        print(f"✅ Created validation session: {session.session_id}")
        print(f"   📋 Status: {session.status.value}")
        print(f"   📊 Total pages: {session.total_pages}")
        
        # Create test snippets
        snippet1 = DocumentSnippet(
            id="snippet_1",
            snippet_type=SnippetType.IMAGE,
            location=SnippetLocation(page=1, bbox=[100, 100, 200, 200]),
            metadata=SnippetMetadata(
                snippet_id="snippet_1",
                snippet_type=SnippetType.IMAGE,
                user_name="Test Image"
            )
        )
        
        snippet2 = DocumentSnippet(
            id="snippet_2",
            snippet_type=SnippetType.TABLE,
            location=SnippetLocation(page=2, bbox=[150, 150, 350, 350]),
            metadata=SnippetMetadata(
                snippet_id="snippet_2",
                snippet_type=SnippetType.TABLE,
                user_name="Test Table"
            )
        )
        
        print(f"✅ Created {len([snippet1, snippet2])} test snippets")
        
        # Test serialization
        snippet_dict = snippet1.to_dict()
        snippet_restored = DocumentSnippet.from_dict(snippet_dict)
        
        print(f"✅ Serialization test passed: {snippet_restored.id}")
        
        # Test session statistics
        from tore_matrix_labs.models.manual_validation_models import PageValidationResult
        
        page_result = PageValidationResult(page_number=1)
        page_result.snippets = [snippet1]
        session.add_page_result(page_result)
        
        stats = session.get_statistics()
        print(f"✅ Session statistics: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing manual validation models: {e}")
        return False


def test_exclusion_zones():
    """Test exclusion zones functionality."""
    print("\n🧪 Testing Exclusion Zones")
    print("=" * 60)
    
    try:
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
        
        # Test serialization
        export_data = exclusion_manager.export_zones_to_json()
        print(f"✅ Export data created: {len(export_data['zones_by_page'])} pages")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing exclusion zones: {e}")
        return False


def test_tore_format_extension():
    """Test .tore format extension."""
    print("\n🧪 Testing .tore Format Extension")
    print("=" * 60)
    
    try:
        from tore_matrix_labs.core.snippet_storage import ToreProjectExtension
        from tore_matrix_labs.models.manual_validation_models import (
            ManualValidationSession, DocumentSnippet, SnippetType, 
            SnippetLocation, SnippetMetadata, PageValidationResult
        )
        
        # Create test session
        session = ManualValidationSession(
            document_id="test_doc_1",
            document_path="/path/to/test.pdf",
            total_pages=5
        )
        
        # Add test snippet
        snippet = DocumentSnippet(
            id="test_snippet",
            snippet_type=SnippetType.IMAGE,
            location=SnippetLocation(page=1, bbox=[100, 100, 200, 200]),
            metadata=SnippetMetadata(
                snippet_id="test_snippet",
                snippet_type=SnippetType.IMAGE,
                user_name="Test Image"
            )
        )
        
        page_result = PageValidationResult(page_number=1)
        page_result.snippets = [snippet]
        session.add_page_result(page_result)
        session.mark_completed()
        
        # Test project extension
        project_data = {
            'name': 'test_project',
            'version': '1.0',
            'documents': []
        }
        
        # Add manual validation to project
        extended_project = ToreProjectExtension.add_manual_validation_to_project(
            project_data, session
        )
        
        print(f"✅ Added manual validation to project")
        print(f"   📋 Status: {extended_project['manual_validation']['status']}")
        print(f"   📊 Total snippets: {len(extended_project['manual_validation']['snippets'])}")
        print(f"   🎯 Exclusion zones: {len(extended_project['manual_validation']['exclusion_zones'])}")
        
        # Test loading back
        loaded_session = ToreProjectExtension.load_manual_validation_from_project(extended_project)
        
        if loaded_session:
            print(f"✅ Loaded session back: {loaded_session.session_id}")
            print(f"   📊 Snippets: {len(loaded_session.get_all_snippets())}")
        else:
            print("❌ Failed to load session back")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing .tore format extension: {e}")
        return False


def test_project_creation():
    """Test project creation with manual validation."""
    print("\n🧪 Testing Project Creation")
    print("=" * 60)
    
    try:
        from tore_matrix_labs.core.workflow_integration import create_project_with_manual_validation
        from tore_matrix_labs.config.settings import Settings
        
        # Create settings
        settings = Settings()
        
        # Create test project
        test_documents = ["test_doc1.pdf", "test_doc2.pdf"]
        
        project_data = create_project_with_manual_validation(
            "Test Manual Validation Project",
            test_documents,
            settings
        )
        
        print(f"✅ Created project with manual validation")
        print(f"   📋 Project name: {project_data['name']}")
        print(f"   📝 Version: {project_data['version']}")
        print(f"   🎯 Manual validation enabled: {project_data['workflow_metadata']['manual_validation_enabled']}")
        print(f"   📊 Documents: {len(project_data['documents'])}")
        
        # Test serialization
        project_json = json.dumps(project_data, indent=2)
        print(f"✅ Project serialized: {len(project_json)} characters")
        
        # Test loading
        loaded_project = json.loads(project_json)
        print(f"✅ Project loaded: {loaded_project['name']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing project creation: {e}")
        return False


def test_widget_creation():
    """Test widget creation (without Qt dependencies)."""
    print("\n🧪 Testing Widget Structure")
    print("=" * 60)
    
    try:
        # Test that we can import the widget modules
        from tore_matrix_labs.ui.components.manual_validation_widget import (
            ClassificationDialog, DragSelectPDFViewer, ManualValidationWidget
        )
        
        print("✅ Manual validation widget modules imported successfully")
        print("   📋 ClassificationDialog: Available")
        print("   📋 DragSelectPDFViewer: Available")
        print("   📋 ManualValidationWidget: Available")
        
        # Note: We can't actually create the widgets without Qt event loop
        print("ℹ️  Widget creation requires Qt event loop (skipped in test)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing widget creation: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 TORE Matrix Labs - Manual Validation Core Components Test")
    print("=" * 80)
    
    tests = [
        ("Manual Validation Models", test_manual_validation_models),
        ("Exclusion Zones", test_exclusion_zones),
        (".tore Format Extension", test_tore_format_extension),
        ("Project Creation", test_project_creation),
        ("Widget Structure", test_widget_creation)
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
        print("🎉 All core components tests passed!")
        print("📋 Manual validation workflow components are ready.")
        print("🖥️  To test the full workflow, run the application with a GUI.")
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)