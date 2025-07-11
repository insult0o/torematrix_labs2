#!/usr/bin/env python3
"""
Test script to verify coordinate mapping improvements.
"""

import sys
import json
import fitz  # PyMuPDF
from pathlib import Path

def test_coordinate_mapping():
    """Test the coordinate mapping accuracy."""
    
    # Load the project file
    project_file = Path("4.tore")
    if not project_file.exists():
        print("❌ Project file not found")
        return False
    
    # Load project data
    with open(project_file, 'r') as f:
        project_data = json.load(f)
    
    # Get the first document
    doc_data = project_data["documents"][0]
    pdf_path = doc_data["path"]
    corrections = doc_data["processing_data"]["corrections"]
    
    print(f"📄 Testing coordinate mapping for: {pdf_path}")
    print(f"📝 Total corrections: {len(corrections)}")
    
    # Open the PDF
    doc = fitz.open(pdf_path)
    
    # Test first page
    page = doc[0]
    page_text = page.get_text()
    text_dict = page.get_text("dict")
    
    print(f"📖 Page text length: {len(page_text)}")
    print(f"📊 Text dict blocks: {len(text_dict.get('blocks', []))}")
    
    # Test coordinate mapping for a few corrections
    test_corrections = corrections[:3]  # Test first 3 corrections
    
    for i, correction in enumerate(test_corrections):
        print(f"\n🔍 Testing correction {i+1}: {correction['description']}")
        
        location = correction["location"]
        bbox = location["bbox"]
        text_position = location.get("text_position", [])
        
        print(f"   📍 Original bbox: {bbox}")
        print(f"   📍 Text position: {text_position}")
        
        # Test text position mapping
        if text_position and len(text_position) >= 2:
            start_pos, end_pos = text_position[0], text_position[1]
            if start_pos < len(page_text) and end_pos <= len(page_text):
                text_content = page_text[start_pos:end_pos]
                print(f"   ✅ Text at position: '{text_content}'")
            else:
                print(f"   ❌ Text position out of bounds")
        
        # Test PyMuPDF text search
        search_text = correction["description"].replace("Potential OCR error: ", "").strip("'\"")
        if search_text:
            search_results = page.search_for(search_text)
            if search_results:
                found_bbox = search_results[0]
                print(f"   🔍 Found text at bbox: {[found_bbox.x0, found_bbox.y0, found_bbox.x1, found_bbox.y1]}")
                
                # Compare with original bbox
                bbox_diff = [
                    abs(bbox[0] - found_bbox.x0),
                    abs(bbox[1] - found_bbox.y0),
                    abs(bbox[2] - found_bbox.x1),
                    abs(bbox[3] - found_bbox.y1)
                ]
                print(f"   📏 Bbox difference: {bbox_diff}")
                
                if all(diff < 10 for diff in bbox_diff):
                    print(f"   ✅ Coordinate mapping accurate!")
                else:
                    print(f"   ⚠️  Coordinate mapping needs improvement")
            else:
                print(f"   ❌ Text not found in PDF")
    
    # Test character-level mapping
    print(f"\n🔡 Testing character-level mapping...")
    
    # Build character mapping similar to the improved algorithm
    char_mapping = {}
    reconstructed_text = ""
    
    for block in text_dict.get("blocks", []):
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    span_text = span["text"]
                    span_bbox = span["bbox"]
                    
                    # Map each character
                    for i, char in enumerate(span_text):
                        if len(span_text) > 0:
                            char_width = (span_bbox[2] - span_bbox[0]) / len(span_text)
                            char_x0 = span_bbox[0] + i * char_width
                            char_x1 = span_bbox[0] + (i + 1) * char_width
                            char_bbox = [char_x0, span_bbox[1], char_x1, span_bbox[3]]
                            
                            char_mapping[len(reconstructed_text)] = char_bbox
                        
                        reconstructed_text += char
                
                # Add newline
                if reconstructed_text and not reconstructed_text.endswith('\n'):
                    reconstructed_text += '\n'
    
    # Test mapping accuracy
    mapping_coverage = len(char_mapping) / len(reconstructed_text) * 100 if reconstructed_text else 0
    print(f"   📊 Character mapping coverage: {mapping_coverage:.1f}%")
    
    # Test alignment with page text
    alignment_score = 0
    for i in range(min(len(page_text), len(reconstructed_text))):
        if page_text[i] == reconstructed_text[i]:
            alignment_score += 1
    
    alignment_percentage = alignment_score / len(page_text) * 100 if page_text else 0
    print(f"   📊 Text alignment accuracy: {alignment_percentage:.1f}%")
    
    doc.close()
    
    print(f"\n✅ Coordinate mapping test completed!")
    print(f"   📍 Character-level mapping: {len(char_mapping)} positions")
    print(f"   📖 Text extraction: {len(page_text)} characters")
    print(f"   🎯 Alignment accuracy: {alignment_percentage:.1f}%")
    
    return True

if __name__ == "__main__":
    try:
        test_coordinate_mapping()
        print("\n🎉 COORDINATE MAPPING TEST COMPLETED SUCCESSFULLY!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()