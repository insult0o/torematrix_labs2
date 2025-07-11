#!/usr/bin/env python3
"""
Test script to verify the bug fixes for project loading and area management.
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, '.')

def test_project_file_structure():
    """Test if project files have the expected structure."""
    print("🔍 Testing project file structure...")
    
    test_files = ['4.tore', '7.tore']
    
    for file_name in test_files:
        file_path = Path(file_name)
        if not file_path.exists():
            print(f"❌ {file_name} not found")
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            print(f"✅ {file_name} is valid JSON")
            
            # Check basic structure
            if 'documents' in project_data:
                docs = project_data['documents']
                print(f"   📄 Contains {len(docs)} documents")
                
                # Check for visual areas in documents
                total_areas = 0
                for doc in docs:
                    if 'visual_areas' in doc:
                        areas = doc['visual_areas']
                        total_areas += len(areas)
                        
                if total_areas > 0:
                    print(f"   🎯 Contains {total_areas} visual areas")
                else:
                    print(f"   ⚠️ No visual areas found")
            else:
                print(f"   ❌ No documents section found")
                
        except json.JSONDecodeError as e:
            print(f"❌ {file_name} invalid JSON: {e}")
        except Exception as e:
            print(f"❌ Error reading {file_name}: {e}")

def test_area_storage_manager():
    """Test area storage manager functionality."""
    print("\n🔍 Testing AreaStorageManager...")
    
    try:
        from tore_matrix_labs.core.area_storage_manager import AreaStorageManager
        from tore_matrix_labs.ui.components.project_manager_widget import ProjectManagerWidget
        from tore_matrix_labs.config.settings import Settings
        
        # Create components
        settings = Settings()
        project_manager = ProjectManagerWidget(settings)
        area_storage = AreaStorageManager(project_manager)
        
        print("✅ AreaStorageManager created successfully")
        
        # Test loading a project file
        project_file = Path('4.tore')
        if project_file.exists():
            print(f"📂 Loading project file: {project_file}")
            project_manager.load_project(str(project_file))
            
            # Test area loading for first document
            documents = project_manager.get_project_documents()
            if documents:
                first_doc = documents[0]
                doc_id = first_doc.get('id')
                
                if doc_id:
                    print(f"🔍 Testing area loading for document: {doc_id}")
                    areas = area_storage.load_areas(doc_id)
                    print(f"✅ Loaded {len(areas)} areas from storage")
                    
                    if areas:
                        for area_id, area in areas.items():
                            print(f"   🎯 Area {area_id}: {area.area_type.value} on page {area.page}")
                else:
                    print("⚠️ No document ID found")
            else:
                print("⚠️ No documents found in project")
        else:
            print(f"⚠️ Project file {project_file} not found")
            
    except Exception as e:
        print(f"❌ Error testing AreaStorageManager: {e}")
        import traceback
        traceback.print_exc()

def test_manual_validation_widget():
    """Test manual validation widget area loading."""
    print("\n🔍 Testing ManualValidationWidget area loading...")
    
    try:
        from tore_matrix_labs.ui.components.manual_validation_widget import ManualValidationWidget
        from tore_matrix_labs.config.settings import Settings
        from tore_matrix_labs.models.document_models import Document, DocumentMetadata
        from datetime import datetime
        
        settings = Settings()
        widget = ManualValidationWidget(settings)
        print("✅ ManualValidationWidget created successfully")
        
        # Test the new helper methods
        if hasattr(widget, 'load_existing_areas_from_project'):
            print("✅ load_existing_areas_from_project method exists")
        else:
            print("❌ load_existing_areas_from_project method missing")
            
        if hasattr(widget, '_refresh_pdf_viewer_areas'):
            print("✅ _refresh_pdf_viewer_areas method exists")
        else:
            print("❌ _refresh_pdf_viewer_areas method missing")
            
        if hasattr(widget, '_get_main_window'):
            print("✅ _get_main_window method exists")
        else:
            print("❌ _get_main_window method missing")
            
    except Exception as e:
        print(f"❌ Error testing ManualValidationWidget: {e}")
        import traceback
        traceback.print_exc()

def test_enhanced_drag_select():
    """Test enhanced drag select styling fixes."""
    print("\n🔍 Testing EnhancedDragSelect styling fixes...")
    
    try:
        from tore_matrix_labs.ui.components.enhanced_drag_select import EnhancedDragSelectLabel
        from tore_matrix_labs.ui.components.pdf_viewer import PDFViewer
        from tore_matrix_labs.config.settings import Settings
        
        settings = Settings()
        pdf_viewer = PDFViewer(settings)
        drag_select = EnhancedDragSelectLabel(pdf_viewer)
        
        print("✅ EnhancedDragSelectLabel created successfully")
        
        # Check if the area deactivation mechanism is in place
        # by examining the mousePressEvent code
        import inspect
        source = inspect.getsource(drag_select.mousePressEvent)
        
        if "DEACTIVATE" in source and "active_area_id = None" in source:
            print("✅ Area deactivation mechanism implemented")
        else:
            print("❌ Area deactivation mechanism missing")
            
        if "fill_opacity = min(0.6" in inspect.getsource(drag_select.__class__):
            print("✅ Improved opacity handling implemented")
        else:
            print("❌ Improved opacity handling missing")
            
    except Exception as e:
        print(f"❌ Error testing EnhancedDragSelect: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Testing Bug Fixes for TORE Matrix Labs")
    print("=" * 50)
    
    test_project_file_structure()
    test_area_storage_manager()
    test_manual_validation_widget()
    test_enhanced_drag_select()
    
    print("\n" + "=" * 50)
    print("🏁 Testing completed!")