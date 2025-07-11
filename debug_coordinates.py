#!/usr/bin/env python3
"""
Debug coordinate mapping issues.
"""

import fitz
import json

# Load project data
with open('4.tore', 'r') as f:
    data = json.load(f)

pdf_path = data['documents'][0]['path']
doc = fitz.open(pdf_path)
page = doc[0]

print(f"📄 PDF Page rect: {page.rect}")
print(f"📊 Page dimensions: {page.rect.width} x {page.rect.height}")

# Get text and structured data
page_text = page.get_text()
text_dict = page.get_text("dict")

print(f"\n📖 Extracted text (first 100 chars):")
print(repr(page_text[:100]))

print(f"\n📍 First few text spans with coordinates:")
span_count = 0
for block in text_dict.get("blocks", []):
    if "lines" in block and span_count < 5:
        for line in block["lines"]:
            print(f"Line bbox: {line.get('bbox', [])}")
            for span in line["spans"]:
                span_text = span["text"]
                span_bbox = span["bbox"]
                print(f"  Span: '{span_text}' at bbox {span_bbox}")
                span_count += 1
                if span_count >= 5:
                    break
            if span_count >= 5:
                break

# Test search for specific text
print(f"\n🔍 Testing text search:")
search_terms = ["PANS-ATM", "Chapter", "5-1"]
for term in search_terms:
    results = page.search_for(term)
    if results:
        print(f"  Found '{term}' at: {[r for r in results]}")
    else:
        print(f"  '{term}' not found")

# Check if text positions match corrections
print(f"\n🔍 Testing corrections data:")
corrections = data['documents'][0]['processing_data']['corrections']
for i in range(min(3, len(corrections))):
    correction = corrections[i]
    location = correction["location"]
    bbox = location["bbox"]
    text_pos = location.get("text_position", [])
    
    print(f"\nCorrection {i+1}: {correction['description']}")
    print(f"  bbox: {bbox}")
    print(f"  text_position: {text_pos}")
    
    if text_pos and len(text_pos) >= 2:
        actual_text = page_text[text_pos[0]:text_pos[1]]
        print(f"  actual text at position: {repr(actual_text)}")
    
    # Check Y-coordinate relative to page height
    if bbox and len(bbox) >= 4:
        y_from_bottom = bbox[1]  # Y coordinate from bottom
        y_from_top = page.rect.height - bbox[3]  # Y coordinate from top
        print(f"  Y from bottom: {y_from_bottom:.1f}, Y from top: {y_from_top:.1f}")

doc.close()