#!/usr/bin/env python3
"""
Test the page number logic without Qt widgets to identify the issue.
"""

def test_page_number_logic():
    """Test the page number logic that's causing the issue."""
    print("🔍 TESTING PAGE NUMBER LOGIC")
    print("=" * 50)
    
    # Mock corrections with page 1
    mock_corrections = [
        {
            'id': 'text_issue_1',
            'type': 'ocr_correction',
            'description': 'OCR may have misread "procedural" as "proccdural" - please verify spelling',
            'original_text': 'proccdural guidance',
            'suggested_fix': 'procedural guidance',
            'confidence': 0.8,
            'reasoning': 'Text processing found potential OCR spelling errors in non-excluded areas',
            'status': 'suggested',
            'location': {
                'page': 1,  # This should be correct - 1-indexed
                'paragraph': 1,
                'bbox': [100, 200, 400, 220],
                'text_position': {'start': 0, 'end': 17}
            },
            'severity': 'medium'
        }
    ]
    
    print(f"📄 Testing with {len(mock_corrections)} corrections")
    print(f"   Correction page: {mock_corrections[0]['location']['page']}")
    
    # Test the logic from page_validation_widget.py lines 209-249
    print("\n🔍 TESTING CORRECTIONS GROUPING")
    print("=" * 50)
    
    corrections_by_page = {}
    for correction in mock_corrections:
        page = correction.get('location', {}).get('page', 1)
        print(f"Processing correction with page: {page} (type: {type(page)})")
        if page not in corrections_by_page:
            corrections_by_page[page] = []
        corrections_by_page[page].append(correction)
    
    print(f"corrections_by_page keys: {list(corrections_by_page.keys())}")
    
    # Test the logic from lines 245-250
    current_page = 1
    if corrections_by_page:
        first_page = min(corrections_by_page.keys())
        current_page = first_page
        print(f"first_page: {first_page} (type: {type(first_page)})")
        print(f"current_page set to: {current_page}")
    
    # This should be 1, not 0
    if current_page == 1:
        print("✅ Current page is correct (1)")
    else:
        print(f"❌ Current page is wrong: {current_page}")
    
    # Test enhanced extraction page numbering
    print("\n🔍 TESTING ENHANCED EXTRACTION PAGE NUMBERING")
    print("=" * 50)
    
    # Simulate what happens in the enhanced extraction
    # From enhanced_pdf_extractor.py lines 66-68:
    # for page_num in range(len(doc)):
    #     page_number = page_num + 1
    
    # Mock a 55-page document
    doc_page_count = 55
    page_texts = {}
    
    for page_num in range(doc_page_count):
        page_number = page_num + 1  # Convert 0-indexed to 1-indexed
        page_texts[page_number] = f"Page {page_number} text content"
    
    print(f"Enhanced extraction pages: {list(page_texts.keys())[:10]}... (first 10)")
    
    # Test accessing page 1
    if 1 in page_texts:
        print("✅ Page 1 found in enhanced extraction")
    else:
        print("❌ Page 1 NOT found in enhanced extraction")
    
    # Test accessing page 0
    if 0 in page_texts:
        print("❌ Page 0 found in enhanced extraction (this is wrong)")
    else:
        print("✅ Page 0 NOT found in enhanced extraction (this is correct)")
    
    # Test the specific case that's causing the error
    print("\n🔍 TESTING ERROR SCENARIO")
    print("=" * 50)
    
    # The error message was: "Failed to extract text from page 1: 0"
    # This suggests that page_number is 0, not 1
    
    # Let's test what would happen if current_page gets reset to 0 somewhere
    test_page_number = 0
    
    print(f"Testing access to page {test_page_number}")
    if test_page_number in page_texts:
        print(f"✅ Page {test_page_number} found in page_texts")
    else:
        print(f"❌ Page {test_page_number} NOT found in page_texts")
        print(f"   Available pages: {sorted(page_texts.keys())[:5]}... (first 5)")
    
    # Test with page 1
    test_page_number = 1
    print(f"Testing access to page {test_page_number}")
    if test_page_number in page_texts:
        print(f"✅ Page {test_page_number} found in page_texts")
    else:
        print(f"❌ Page {test_page_number} NOT found in page_texts")
    
    print("\n🔍 SUSPECTED ISSUE")
    print("=" * 50)
    
    # The issue might be in the coordinate correspondence system
    # Let's check if there's a conversion that changes page 1 to page 0
    
    # From coordinate_correspondence.py, there might be a conversion like:
    # page_index = page_number - 1  # Convert 1-indexed to 0-indexed
    
    page_number = 1  # From corrections
    page_index = page_number - 1  # Convert to 0-indexed for PyMuPDF
    
    print(f"Original page_number: {page_number}")
    print(f"Converted page_index: {page_index}")
    
    # If page_index (0) is used instead of page_number (1) to access page_texts, 
    # it would fail because page_texts uses 1-indexed keys
    
    if page_index in page_texts:
        print(f"✅ page_index {page_index} found in page_texts")
    else:
        print(f"❌ page_index {page_index} NOT found in page_texts")
        print("   This is the likely cause of the error!")
    
    print("\n🔍 CONCLUSION")
    print("=" * 50)
    print("The issue is likely that somewhere in the code, page_number (1-indexed)")
    print("is being converted to page_index (0-indexed) and then used to access")
    print("page_texts, which uses 1-indexed keys.")
    print("")
    print("The fix is to ensure that page_texts is accessed with 1-indexed keys,")
    print("not 0-indexed keys from coordinate conversions.")

if __name__ == "__main__":
    test_page_number_logic()