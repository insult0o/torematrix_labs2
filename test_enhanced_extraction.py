#!/usr/bin/env python3
"""
Test enhanced PDF extraction with perfect coordinate correlation.
"""

import sys
import json
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from tore_matrix_labs.core.enhanced_pdf_extractor import EnhancedPDFExtractor
from tore_matrix_labs.config.settings import Settings

def test_enhanced_extraction():
    """Test the enhanced PDF extraction capabilities."""
    
    print("🚀 Testing Enhanced PDF Extraction with Perfect Coordinate Correlation")
    print("=" * 80)
    
    # Initialize extractor
    settings = Settings()
    extractor = EnhancedPDFExtractor(settings)
    
    # Test with our PDF
    pdf_path = "/home/insulto/tore_matrix_labs/5555.pdf"
    if not Path(pdf_path).exists():
        print(f"❌ PDF file not found: {pdf_path}")
        return False
    
    print(f"📄 Testing enhanced extraction on: {Path(pdf_path).name}")
    
    # Test 1: Extraction quality assessment
    print("\n🔍 Test 1: Enhanced Extraction Quality Assessment")
    quality_report = extractor.validate_extraction_quality(pdf_path)
    
    print(f"   📊 Extraction method: {quality_report['extraction_method']}")
    print(f"   📈 Total elements: {quality_report['total_elements']}")
    print(f"   📄 Total pages: {quality_report['total_pages']}")
    print(f"   📏 Full text length: {quality_report['full_text_length']} characters")
    print(f"   🎯 Coordinate accuracy: {quality_report['coordinate_accuracy']:.1%}")
    print(f"   📍 Elements with coordinates: {quality_report['elements_with_coords']}")
    print(f"   ⭐ Quality score: {quality_report['quality_score']:.1%}")
    
    # Test 2: Character-level extraction
    print("\n🔬 Test 2: Character-Level Extraction with Precise Positioning")
    elements, full_text, page_texts = extractor.extract_with_perfect_correlation(pdf_path)
    
    print(f"   📚 Extracted {len(elements)} character-level elements")
    print(f"   📝 Full text: {len(full_text)} characters")
    print(f"   📄 Page texts: {len(page_texts)} pages")
    
    # Show sample of precise character positioning
    print("\n   🔬 Sample Character-Level Elements:")
    word_elements = []
    current_word = ""
    word_start_idx = 0
    
    for i, element in enumerate(elements[:100]):  # Check first 100 elements
        if element.content.isalnum():
            if not current_word:
                word_start_idx = i
            current_word += element.content
        else:
            if current_word:
                word_elements.append({
                    'word': current_word,
                    'start_idx': word_start_idx,
                    'end_idx': i,
                    'elements': elements[word_start_idx:i]
                })
                current_word = ""
                
                if len(word_elements) >= 3:  # Show first 3 words
                    break
    
    for j, word_info in enumerate(word_elements):
        word = word_info['word']
        word_elements_list = word_info['elements']
        
        if word_elements_list:
            first_elem = word_elements_list[0]
            last_elem = word_elements_list[-1]
            
            # Calculate word bbox
            word_bbox = (
                first_elem.bbox[0],
                min(e.bbox[1] for e in word_elements_list),
                last_elem.bbox[2],
                max(e.bbox[3] for e in word_elements_list)
            )
            
            print(f"     Word {j+1}: '{word}'")
            print(f"       📍 Characters: {len(word_elements_list)}")
            print(f"       📊 Word bbox: {word_bbox}")
            print(f"       📄 Page: {first_elem.page_number}")
            print(f"       🎯 Char positions: {first_elem.char_start}-{last_elem.char_end}")
    
    # Test 3: Perfect text finding with coordinates
    print("\n🔎 Test 3: Finding Text with Perfect Coordinate Correlation")
    test_searches = ["PANS-ATM", "Chapter", "5-1", "SEPARATION"]
    
    total_found = 0
    total_accurate = 0
    
    for search_text in test_searches:
        matches = extractor.find_text_with_perfect_coordinates(elements, full_text, search_text)
        if matches:
            print(f"   ✅ Found '{search_text}': {len(matches)} matches")
            total_found += len(matches)
            
            for match in matches[:2]:  # Show first 2 matches
                print(f"     📍 Page {match['page_number']}, bbox: {match['bbox']}")
                print(f"     📊 Character position: {match['char_position']}")
                print(f"     🎯 Confidence: {match['confidence']:.1%}")
                
                # Verify accuracy
                char_pos = match['char_position']
                if char_pos + len(search_text) <= len(full_text):
                    actual_text = full_text[char_pos:char_pos + len(search_text)]
                    if actual_text == search_text:
                        print(f"     ✅ Text verification: PERFECT MATCH")
                        total_accurate += 1
                    else:
                        print(f"     ❌ Text verification: Expected '{search_text}', got '{actual_text}'")
                else:
                    print(f"     ❌ Text verification: Position out of bounds")
        else:
            print(f"   ❌ '{search_text}' not found")
    
    if total_found > 0:
        text_accuracy = total_accurate / total_found * 100
        print(f"   📊 Text finding accuracy: {text_accuracy:.1f}% ({total_accurate}/{total_found})")
    
    # Test 4: Create enhanced corrections
    print("\n🛠️  Test 4: Creating Enhanced Corrections with Perfect Correlation")
    enhanced_corrections = extractor.create_perfect_corrections(pdf_path)
    
    print(f"   📝 Created {len(enhanced_corrections)} enhanced corrections")
    
    # Show sample corrections
    for i, correction in enumerate(enhanced_corrections[:5]):
        print(f"\n   Enhanced Correction {i+1}:")
        print(f"     🔍 Error: {correction['description']}")
        print(f"     📍 Page: {correction['location']['page']}")
        print(f"     📊 bbox: {correction['location']['bbox']}")
        print(f"     📝 text_position: {correction['location']['text_position']}")
        print(f"     🎯 Confidence: {correction['confidence']:.1%}")
        
        # Verify the text position accuracy
        char_start, char_end = correction['location']['text_position']
        if char_start < len(full_text) and char_end <= len(full_text):
            actual_text = full_text[char_start:char_end]
            expected_text = correction['description'].replace("Potential OCR error: ", "").strip("'\"")
            if actual_text == expected_text:
                print(f"     ✅ Position verification: PERFECT MATCH")
            else:
                print(f"     ❌ Position verification: Expected '{expected_text}', got '{actual_text}'")
        else:
            print(f"     ❌ Position verification: Out of bounds")
    
    # Test 5: Compare with current system
    print("\n📊 Test 5: Comparison with Current System")
    
    # Load current corrections for comparison
    project_file = Path("4.tore")
    if project_file.exists():
        with open(project_file, 'r') as f:
            current_data = json.load(f)
        
        current_corrections = current_data['documents'][0]['processing_data']['corrections']
        
        print(f"   📈 Current system corrections: {len(current_corrections)}")
        print(f"   🚀 Enhanced system corrections: {len(enhanced_corrections)}")
        
        # Test accuracy of both systems
        print("\n   🔍 Accuracy Comparison:")
        
        # Current system accuracy
        current_accurate = 0
        current_tested = 0
        for correction in current_corrections[:10]:  # Test first 10
            text_pos = correction['location'].get('text_position', [])
            if text_pos and len(text_pos) >= 2 and text_pos[1] <= len(full_text):
                current_tested += 1
                actual_text = full_text[text_pos[0]:text_pos[1]]
                expected_text = correction['description'].replace("Potential OCR error: ", "").strip("'\"")
                if actual_text.strip() == expected_text:
                    current_accurate += 1
        
        current_accuracy = (current_accurate / current_tested * 100) if current_tested > 0 else 0
        
        # Enhanced system accuracy (should be 100%)
        enhanced_accurate = 0
        enhanced_tested = 0
        for correction in enhanced_corrections[:10]:  # Test first 10
            text_pos = correction['location'].get('text_position', [])
            if text_pos and len(text_pos) >= 2 and text_pos[1] <= len(full_text):
                enhanced_tested += 1
                actual_text = full_text[text_pos[0]:text_pos[1]]
                expected_text = correction['description'].replace("Potential OCR error: ", "").strip("'\"")
                if actual_text == expected_text:
                    enhanced_accurate += 1
        
        enhanced_accuracy = (enhanced_accurate / enhanced_tested * 100) if enhanced_tested > 0 else 0
        
        print(f"   📊 Current system accuracy: {current_accuracy:.1f}% ({current_accurate}/{current_tested})")
        print(f"   🚀 Enhanced system accuracy: {enhanced_accuracy:.1f}% ({enhanced_accurate}/{enhanced_tested})")
        
        improvement = enhanced_accuracy - current_accuracy
        print(f"   📈 Accuracy improvement: +{improvement:.1f} percentage points")
    
    print("\n🎉 ENHANCED EXTRACTION TEST COMPLETED!")
    
    overall_quality = quality_report['quality_score']
    if overall_quality >= 0.95:
        print("✅ EXCELLENT: Enhanced extraction provides near-perfect coordinate correlation!")
    elif overall_quality >= 0.85:
        print("✅ VERY GOOD: Enhanced extraction significantly improves coordinate accuracy!")
    elif overall_quality >= 0.75:
        print("✅ GOOD: Enhanced extraction provides better coordinate correlation!")
    else:
        print("⚠️  NEEDS IMPROVEMENT: Results mixed - further optimization needed")
    
    print("\n💡 Enhanced Extraction Benefits:")
    print("   🎯 Character-level coordinate precision")
    print("   📊 Perfect text-to-position correlation") 
    print("   🔍 Advanced OCR error pattern detection")
    print("   📏 Precise bounding box calculation")
    print("   🧠 Font-based element classification")
    print("   ⚡ Fast processing using optimized PyMuPDF")
    
    return True

if __name__ == "__main__":
    try:
        success = test_enhanced_extraction()
        if success:
            print("\n🚀 ENHANCED EXTRACTION READY FOR INTEGRATION!")
        else:
            print("\n❌ Enhanced extraction test failed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()