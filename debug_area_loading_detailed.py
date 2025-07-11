#!/usr/bin/env python3
"""
Detailed analysis of the area loading bug in session reload.
"""

import json
from pathlib import Path

def analyze_area_loading_flow():
    """Analyze the exact flow of area loading during project reload."""
    
    print("🔍 DETAILED AREA LOADING FLOW ANALYSIS")
    print("=" * 60)
    
    # Load the project file with areas
    project_file = "/home/insulto/tore_matrix_labs/123.tore"
    
    with open(project_file, 'r') as f:
        project_data = json.load(f)
    
    print(f"📁 PROJECT: {project_data['name']}")
    print(f"📊 DOCUMENTS: {len(project_data['documents'])}")
    
    # Get the first document with areas
    doc_with_areas = None
    for doc in project_data['documents']:
        if doc.get('visual_areas'):
            doc_with_areas = doc
            break
    
    if not doc_with_areas:
        print("❌ No document with areas found")
        return
    
    print(f"\n📄 DOCUMENT WITH AREAS:")
    print(f"   ID: {doc_with_areas['id']}")
    print(f"   Name: {doc_with_areas['name']}")
    print(f"   Areas: {len(doc_with_areas.get('visual_areas', {}))}")
    
    # Now let's trace the exact loading sequence
    print(f"\n🔄 TRACING LOADING SEQUENCE:")
    
    # Step 1: Project Manager loads project
    print(f"\n1️⃣ PROJECT MANAGER LOADS PROJECT")
    print(f"   - ProjectManager.load_project() called")
    print(f"   - Sets self.current_project = project_data")
    print(f"   - Sets self.documents = project_data['documents']")
    print(f"   - Emits project_loaded signal")
    
    # Step 2: Main window receives project_loaded signal
    print(f"\n2️⃣ MAIN WINDOW RECEIVES SIGNAL")
    print(f"   - MainWindow._on_project_loaded() called")
    print(f"   - Calls get_project_documents() which converts format")
    print(f"   - Calls DocumentStateManager.load_project_documents()")
    print(f"   - Calls _populate_manual_validation_from_project()")
    
    # Step 3: Document format conversion
    print(f"\n3️⃣ DOCUMENT FORMAT CONVERSION")
    print(f"   - ProjectManager.get_project_documents() called")
    print(f"   - For each document, calls _convert_document_format()")
    
    # Simulate the conversion for our document
    converted_doc = simulate_document_conversion(doc_with_areas)
    print(f"   - Converted document has {len(converted_doc.get('visual_areas', {}))} areas")
    
    # Step 4: Document State Manager
    print(f"\n4️⃣ DOCUMENT STATE MANAGER")
    print(f"   - DocumentStateManager.load_project_documents() called")
    print(f"   - Creates document_cache entries")
    
    # Simulate the cache entry
    cache_entry = simulate_cache_entry(converted_doc)
    print(f"   - Cache entry has {len(cache_entry.get('visual_areas', {}))} areas")
    
    # Step 5: Manual validation population
    print(f"\n5️⃣ MANUAL VALIDATION POPULATION")
    print(f"   - _populate_manual_validation_from_project() called")
    print(f"   - Looks for documents with visual_areas")
    
    # Check if areas are found during population
    areas_found = check_areas_in_converted_doc(converted_doc)
    print(f"   - Areas found in converted doc: {areas_found}")
    
    if areas_found:
        print(f"   - Creates Document object and calls load_document()")
        print(f"   - load_document() calls load_existing_areas_from_project()")
        
        # Step 6: Area Storage Manager
        print(f"\n6️⃣ AREA STORAGE MANAGER")
        print(f"   - load_existing_areas_from_project() called")
        print(f"   - Gets document_id from current_document")
        print(f"   - Calls area_storage_manager.load_areas(document_id)")
        
        # Simulate area storage manager lookup
        storage_result = simulate_area_storage_lookup(doc_with_areas['id'], project_data)
        print(f"   - Area storage manager result: {storage_result}")
    
    print(f"\n🎯 POTENTIAL ISSUE IDENTIFICATION:")
    
    # Issue 1: Check if the document ID matches between steps
    original_id = doc_with_areas['id']
    converted_id = converted_doc['id']
    cache_id = cache_entry['id']
    
    print(f"   📋 Document ID Consistency:")
    print(f"      - Original: {original_id}")
    print(f"      - Converted: {converted_id}")
    print(f"      - Cached: {cache_id}")
    print(f"      - Match: {original_id == converted_id == cache_id}")
    
    # Issue 2: Check if areas are preserved through conversion
    original_areas = len(doc_with_areas.get('visual_areas', {}))
    converted_areas = len(converted_doc.get('visual_areas', {}))
    cached_areas = len(cache_entry.get('visual_areas', {}))
    
    print(f"   📊 Areas Count Consistency:")
    print(f"      - Original: {original_areas}")
    print(f"      - Converted: {converted_areas}")
    print(f"      - Cached: {cached_areas}")
    print(f"      - Match: {original_areas == converted_areas == cached_areas}")
    
    # Issue 3: Check the exact area storage manager lookup
    print(f"   🔍 Area Storage Manager Lookup:")
    print(f"      - Looking for document ID: {original_id}")
    print(f"      - Project has {len(project_data['documents'])} documents")
    
    for i, doc in enumerate(project_data['documents']):
        doc_id = doc.get('id', 'NO_ID')
        areas_count = len(doc.get('visual_areas', {}))
        match = doc_id == original_id
        print(f"      - Doc {i+1}: {doc_id} ({areas_count} areas) - Match: {match}")
    
    # Issue 4: Check timing issues
    print(f"   ⏱️ Timing Issues:")
    print(f"      - Area storage manager depends on project_manager.current_project")
    print(f"      - Manual validation loads immediately after project signal")
    print(f"      - Potential race condition if project not fully loaded")

def simulate_document_conversion(original_doc):
    """Simulate the _convert_document_format method."""
    
    # Extract visual areas from multiple possible locations
    visual_areas = {}
    
    # Check processing_data for visual areas
    processing_data = original_doc.get('processing_data', {})
    if 'visual_areas' in processing_data:
        visual_areas.update(processing_data['visual_areas'])
    
    # Check direct visual_areas field
    if 'visual_areas' in original_doc:
        visual_areas.update(original_doc['visual_areas'])
    
    converted = {
        'id': original_doc.get('id', 'unknown'),
        'name': original_doc.get('name', 'Unknown'),
        'path': original_doc.get('path', ''),
        'status': original_doc.get('status', 'unknown'),
        'processing_data': {
            'visual_areas': visual_areas
        },
        'visual_areas': visual_areas
    }
    
    return converted

def simulate_cache_entry(converted_doc):
    """Simulate the DocumentStateManager cache entry creation."""
    
    cache_entry = {
        'id': converted_doc.get('id'),
        'path': converted_doc.get('path', ''),
        'name': converted_doc.get('name', ''),
        'visual_areas': converted_doc.get('visual_areas', {}),
        'data': {}
    }
    
    return cache_entry

def check_areas_in_converted_doc(converted_doc):
    """Check if areas are found in the converted document during population."""
    
    # This simulates the logic in _populate_manual_validation_from_project
    visual_areas = {}
    
    # Check processing_data for visual areas
    processing_data = converted_doc.get('processing_data', {})
    if 'visual_areas' in processing_data:
        visual_areas.update(processing_data['visual_areas'])
    
    # Check direct visual_areas field
    if 'visual_areas' in converted_doc:
        visual_areas.update(converted_doc['visual_areas'])
    
    return len(visual_areas) > 0

def simulate_area_storage_lookup(document_id, project_data):
    """Simulate the AreaStorageManager.load_areas method."""
    
    documents = project_data.get('documents', [])
    
    for doc in documents:
        if doc.get('id') == document_id:
            visual_areas_data = doc.get('visual_areas', {})
            return {
                'found': True,
                'areas_count': len(visual_areas_data),
                'areas': visual_areas_data
            }
    
    return {
        'found': False,
        'areas_count': 0,
        'areas': {}
    }

if __name__ == "__main__":
    analyze_area_loading_flow()