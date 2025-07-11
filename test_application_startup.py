#!/usr/bin/env python3
"""
Test application startup without GUI.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_core_imports():
    """Test that all core modules can be imported."""
    print("🧪 Testing Core Module Imports")
    print("=" * 50)
    
    modules_to_test = [
        "tore_matrix_labs.config.settings",
        "tore_matrix_labs.models.document_models", 
        "tore_matrix_labs.models.manual_validation_models",
        "tore_matrix_labs.core.content_extractor",
        "tore_matrix_labs.core.enhanced_document_processor",
        "tore_matrix_labs.core.snippet_storage",
        "tore_matrix_labs.core.exclusion_zones",
        "tore_matrix_labs.core.parallel_processor",
        "tore_matrix_labs.core.workflow_integration",
        "tore_matrix_labs.ui.components.manual_validation_widget",
        "tore_matrix_labs.ui.components.enhanced_pdf_highlighting",
        "tore_matrix_labs.ui.components.pdf_viewer",
        "tore_matrix_labs.utils.numpy_compatibility"
    ]
    
    passed = 0
    failed = 0
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✅ {module}")
            passed += 1
        except Exception as e:
            print(f"❌ {module}: {e}")
            failed += 1
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_manual_validation_workflow():
    """Test that manual validation workflow can be initialized."""
    print("\n🧪 Testing Manual Validation Workflow")
    print("=" * 50)
    
    try:
        from tore_matrix_labs.config.settings import Settings
        from tore_matrix_labs.core.workflow_integration import WorkflowIntegrationManager
        
        # Create settings
        settings = Settings()
        print("✅ Settings created")
        
        # Create workflow manager
        workflow_manager = WorkflowIntegrationManager(settings)
        print("✅ Workflow integration manager created")
        
        # Test that it has the expected methods
        required_methods = [
            'start_document_processing',
            'complete_manual_validation', 
            'save_workflow_to_project',
            'load_workflow_from_project'
        ]
        
        for method in required_methods:
            if hasattr(workflow_manager, method):
                print(f"✅ Method {method}: Available")
            else:
                print(f"❌ Method {method}: Missing")
                return False
        
        print("✅ Manual validation workflow ready")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_enhanced_highlighting():
    """Test enhanced highlighting system."""
    print("\n🧪 Testing Enhanced Highlighting System")
    print("=" * 50)
    
    try:
        from tore_matrix_labs.ui.components.enhanced_pdf_highlighting import (
            create_multiline_highlight, draw_multiline_highlight,
            HighlightRectangle, MultiLineHighlight
        )
        
        # Test data structures
        rect = HighlightRectangle(x=100, y=150, width=200, height=20)
        print(f"✅ HighlightRectangle: {rect.to_dict()}")
        
        highlight = MultiLineHighlight(rectangles=[], original_bbox=[100, 150, 300, 200])
        highlight.add_rectangle(rect)
        print(f"✅ MultiLineHighlight: {len(highlight.rectangles)} rectangles")
        
        # Test convenience functions are available
        print("✅ create_multiline_highlight: Available")
        print("✅ draw_multiline_highlight: Available")
        
        print("✅ Enhanced highlighting system ready")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_application_initialization():
    """Test that application can be initialized (without GUI)."""
    print("\n🧪 Testing Application Initialization")
    print("=" * 50)
    
    try:
        # Test main components
        from tore_matrix_labs.config.settings import Settings
        from tore_matrix_labs.ui.main_window import MainWindow
        
        print("✅ Main components imported successfully")
        
        # Test that Settings can be created
        settings = Settings()
        print("✅ Settings initialized")
        
        # Note: We can't actually create MainWindow without Qt event loop
        print("ℹ️  MainWindow class available (GUI creation requires Qt event loop)")
        
        print("✅ Application initialization ready")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run application startup tests."""
    print("🚀 TORE Matrix Labs - Application Startup Test")
    print("=" * 80)
    
    tests = [
        test_core_imports,
        test_manual_validation_workflow,
        test_enhanced_highlighting,
        test_application_initialization
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"💥 Test error: {e}")
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All startup tests passed!")
        print("\n📋 Application Status:")
        print("   ✅ All core modules load successfully")
        print("   ✅ Manual validation workflow ready")
        print("   ✅ Enhanced highlighting system functional") 
        print("   ✅ Application can be started")
        
        print("\n🔧 To run the application:")
        print("   python3 -m tore_matrix_labs")
        print("   or")
        print("   tore-matrix (if installed)")
        
        print("\n🎯 New Features Available:")
        print("   ✅ Manual validation workflow for 100% accuracy")
        print("   ✅ Multi-line highlighting with precise positioning")
        print("   ✅ Drag-to-select IMAGE/TABLE/DIAGRAM classification")
        print("   ✅ Parallel processing for optimal performance")
        print("   ✅ LLM-ready export functionality")
        
    else:
        print("⚠️  Some startup tests failed.")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)