#!/usr/bin/env python3
"""
Debug script to analyze the session reload bug where areas don't show in manual validation after reloading a project.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def analyze_project_file(project_file: str):
    """Analyze a project file to understand the area loading issue."""
    print(f"\n🔍 ANALYZING PROJECT FILE: {project_file}")
    
    try:
        with open(project_file, 'r') as f:
            project_data = json.load(f)
            
        print(f"📊 PROJECT INFO:")
        print(f"   Name: {project_data.get('name', 'Unknown')}")
        print(f"   Documents: {len(project_data.get('documents', []))}")
        
        documents = project_data.get('documents', [])
        total_areas = 0
        
        for i, doc in enumerate(documents):
            print(f"\n📄 DOCUMENT {i+1}:")
            print(f"   ID: {doc.get('id', 'Unknown')}")
            print(f"   Name: {doc.get('name', 'Unknown')}")
            print(f"   Path: {doc.get('path', 'Unknown')}")
            print(f"   Status: {doc.get('status', 'Unknown')}")
            
            # Check for visual_areas in multiple locations
            visual_areas = {}
            
            # 1. Direct visual_areas field
            if 'visual_areas' in doc:
                visual_areas.update(doc['visual_areas'])
                print(f"   ✅ Direct visual_areas: {len(doc['visual_areas'])}")
            
            # 2. visual_areas in processing_data
            processing_data = doc.get('processing_data', {})
            if 'visual_areas' in processing_data:
                visual_areas.update(processing_data['visual_areas'])
                print(f"   ✅ Processing data visual_areas: {len(processing_data['visual_areas'])}")
            
            total_areas += len(visual_areas)
            
            if visual_areas:
                print(f"   🎯 TOTAL AREAS: {len(visual_areas)}")
                for area_id, area in visual_areas.items():
                    print(f"      - {area_id}: {area.get('type', 'Unknown')} on page {area.get('page', 'Unknown')}")
            else:
                print(f"   ❌ NO AREAS FOUND")
                
        print(f"\n📊 SUMMARY:")
        print(f"   Total documents: {len(documents)}")
        print(f"   Total visual areas: {total_areas}")
        
        return {
            'documents': documents,
            'total_areas': total_areas,
            'project_data': project_data
        }
        
    except Exception as e:
        print(f"❌ ERROR analyzing project file: {e}")
        return None

def simulate_area_loading_process(project_data: Dict[str, Any]):
    """Simulate the area loading process to identify the bug."""
    print(f"\n🔄 SIMULATING AREA LOADING PROCESS...")
    
    documents = project_data.get('documents', [])
    
    # Step 1: Project loading and document conversion
    print(f"\n📋 STEP 1: PROJECT LOADING")
    converted_documents = []
    
    for doc in documents:
        print(f"   Converting document: {doc.get('name', 'Unknown')}")
        
        # This simulates the _convert_document_format method
        converted_doc = {
            'id': doc.get('id', 'unknown'),
            'name': doc.get('name', 'Unknown'),
            'path': doc.get('path', ''),
            'status': doc.get('status', 'unknown'),
            'processing_data': {
                'visual_areas': (
                    doc.get('visual_areas', {}) or
                    doc.get('processing_data', {}).get('visual_areas', {})
                )
            },
            'visual_areas': (
                doc.get('visual_areas', {}) or
                doc.get('processing_data', {}).get('visual_areas', {})
            )
        }
        
        converted_documents.append(converted_doc)
        
        visual_areas = converted_doc['visual_areas']
        print(f"      ✅ Areas in converted doc: {len(visual_areas)}")
    
    # Step 2: Document State Manager loading
    print(f"\n📋 STEP 2: DOCUMENT STATE MANAGER")
    document_cache = {}
    
    for doc in converted_documents:
        doc_id = doc.get('id')
        if doc_id:
            cached_doc = {
                'id': doc_id,
                'path': doc.get('path', ''),
                'name': doc.get('name', ''),
                'visual_areas': doc.get('visual_areas', {}),
                'data': {}
            }
            
            document_cache[doc_id] = cached_doc
            visual_areas = cached_doc['visual_areas']
            print(f"   📄 Cached doc {doc_id}: {len(visual_areas)} areas")
    
    # Step 3: Manual validation widget loading
    print(f"\n📋 STEP 3: MANUAL VALIDATION WIDGET")
    
    # Find first document with areas
    first_doc_with_areas = None
    for doc in converted_documents:
        visual_areas = doc.get('visual_areas', {})
        if visual_areas:
            first_doc_with_areas = doc
            break
    
    if first_doc_with_areas:
        print(f"   ✅ Found document with areas: {first_doc_with_areas['name']}")
        print(f"   ✅ Areas count: {len(first_doc_with_areas.get('visual_areas', {}))}")
        
        # Simulate manual validation widget loading
        print(f"   🔄 Simulating load_document() call...")
        
        # This would call load_existing_areas_from_project()
        print(f"   🔄 Simulating load_existing_areas_from_project()...")
        
        # Check if area storage manager can find the areas
        document_id = first_doc_with_areas['id']
        areas_found = simulate_area_storage_loading(document_id, project_data)
        
        if areas_found:
            print(f"   ✅ Area storage manager found areas: {len(areas_found)}")
        else:
            print(f"   ❌ Area storage manager found NO areas")
            
    else:
        print(f"   ❌ No document with areas found")
    
    return {
        'converted_documents': converted_documents,
        'document_cache': document_cache,
        'first_doc_with_areas': first_doc_with_areas
    }

def simulate_area_storage_loading(document_id: str, project_data: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate the area storage manager loading process."""
    print(f"      🔍 Area storage manager looking for document '{document_id}'...")
    
    documents = project_data.get('documents', [])
    
    for doc in documents:
        if doc.get('id') == document_id:
            print(f"      ✅ Found target document in project")
            
            visual_areas_data = doc.get('visual_areas', {})
            print(f"      📊 Document has {len(visual_areas_data)} visual areas")
            
            if visual_areas_data:
                print(f"      🎯 Areas found:")
                for area_id, area_data in visual_areas_data.items():
                    print(f"         - {area_id}: {area_data.get('type', 'Unknown')} on page {area_data.get('page', 'Unknown')}")
                
                return visual_areas_data
            else:
                print(f"      ❌ No visual_areas data in document")
                return {}
    
    print(f"      ❌ Document '{document_id}' not found in project")
    return {}

def identify_potential_issues(analysis_results: Dict[str, Any]):
    """Identify potential issues with the area loading process."""
    print(f"\n🔍 IDENTIFYING POTENTIAL ISSUES...")
    
    issues = []
    
    # Issue 1: Document ID mismatches
    converted_docs = analysis_results.get('converted_documents', [])
    for doc in converted_docs:
        if not doc.get('id'):
            issues.append(f"Document '{doc.get('name', 'Unknown')}' has no ID")
    
    # Issue 2: Area storage manager path issues
    if not analysis_results.get('first_doc_with_areas'):
        issues.append("No document with areas found during conversion")
    
    # Issue 3: Missing area storage manager connection
    issues.append("Check if area_storage_manager is properly initialized")
    
    # Issue 4: Timing issues
    issues.append("Check if manual validation widget loads before area storage manager is ready")
    
    print(f"\n🚨 POTENTIAL ISSUES IDENTIFIED:")
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue}")
    
    return issues

def analyze_initialization_sequence():
    """Analyze the initialization sequence for potential timing issues."""
    print(f"\n🔄 ANALYZING INITIALIZATION SEQUENCE...")
    
    print(f"1. MainWindow.__init__()")
    print(f"   - Creates DocumentStateManager")
    print(f"   - Sets area_storage_manager = None")
    print(f"   - Calls _init_ui()")
    
    print(f"\n2. MainWindow._init_ui()")
    print(f"   - Creates ManualValidationWidget")
    print(f"   - Creates ProjectManagerWidget")
    print(f"   - Creates AreaStorageManager(project_widget)")
    print(f"   - Sets manual_validation_widget.area_storage_manager")
    
    print(f"\n3. Project Loading:")
    print(f"   - ProjectManager.load_project()")
    print(f"   - ProjectManager._emit_project_loaded_signal()")
    print(f"   - MainWindow._on_project_loaded()")
    print(f"   - DocumentStateManager.load_project_documents()")
    print(f"   - ManualValidationWidget.on_documents_available()")
    
    print(f"\n4. Area Loading:")
    print(f"   - ManualValidationWidget.load_document()")
    print(f"   - ManualValidationWidget.load_existing_areas_from_project()")
    print(f"   - AreaStorageManager.load_areas()")
    
    print(f"\n🎯 CRITICAL OBSERVATION:")
    print(f"   The manual validation widget calls load_existing_areas_from_project()")
    print(f"   which uses AreaStorageManager.load_areas()")
    print(f"   But this depends on the project_manager having the current project loaded")
    print(f"   There may be a timing issue where the project isn't fully loaded yet")

if __name__ == "__main__":
    print("🔍 SESSION RELOAD BUG ANALYSIS")
    print("=" * 50)
    
    # Analyze a project file with visual areas
    project_file = "/home/insulto/tore_matrix_labs/123.tore"
    
    analysis = analyze_project_file(project_file)
    
    if analysis:
        simulation_results = simulate_area_loading_process(analysis['project_data'])
        issues = identify_potential_issues(simulation_results)
        
        analyze_initialization_sequence()
        
        print(f"\n" + "=" * 50)
        print(f"🎯 CONCLUSION:")
        print(f"   The areas exist in the .tore file but may not be loading properly")
        print(f"   due to timing issues or incorrect document ID matching")
        print(f"   in the area storage manager loading process.")
        print(f"=" * 50)