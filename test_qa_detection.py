#!/usr/bin/env python3
"""
Test QA detection functionality to see if issues are properly detected.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_qa_detection():
    """Test that QA validation detection is working properly."""
    print("🔍 TESTING QA VALIDATION DETECTION")
    print("=" * 60)
    
    try:
        from tore_matrix_labs.config.settings import Settings
        from tore_matrix_labs.ui.components.page_validation_widget import PageValidationWidget
        
        # Create settings and widget
        settings = Settings()
        widget = PageValidationWidget(settings)
        
        print("✅ PageValidationWidget created successfully")
        
        # Test with sample text differences
        original_text = "This is the original PDF text with some content."
        extracted_text = "This is the extracted text with different content."
        
        # Manually test the detection method
        if hasattr(widget, '_detect_pdf_vs_extraction_differences'):
            differences = widget._detect_pdf_vs_extraction_differences(
                original_text, extracted_text, 'formatting'
            )
            print(f"✅ Detection method available")
            print(f"📊 Found {len(differences)} differences between test texts")
            
            if differences:
                print("🔍 Sample differences found:")
                for i, diff in enumerate(differences[:3]):  # Show first 3
                    print(f"  - {diff.get('type', 'Unknown')}: {diff.get('description', 'No description')}")
            else:
                print("⚠️ No differences detected - this might indicate a problem")
        else:
            print("❌ Detection method not found")
        
        # Test with identical text
        identical_text = "This is identical text."
        identical_diffs = widget._detect_pdf_vs_extraction_differences(
            identical_text, identical_text, 'formatting'
        )
        print(f"📊 Identical text comparison: {len(identical_diffs)} differences (should be 0)")
        
        # Test with empty text
        empty_diffs = widget._detect_pdf_vs_extraction_differences(
            "Some text", "", 'formatting'
        )
        print(f"📊 Empty extraction comparison: {len(empty_diffs)} differences")
        
        # Test large difference
        large_original = "This is a large text with many lines.\nLine 1\nLine 2\nLine 3"
        large_extracted = "This is different text.\nDifferent line\nAnother line"
        large_diffs = widget._detect_pdf_vs_extraction_differences(
            large_original, large_extracted, 'formatting'
        )
        print(f"📊 Large text comparison: {len(large_diffs)} differences")
        
        print("\n🎯 DETECTION ANALYSIS")
        print("=" * 60)
        if len(differences) > 0:
            print("✅ Detection is working - differences found between different texts")
        else:
            print("❌ Detection may not be working properly")
            
        if len(identical_diffs) == 0:
            print("✅ Detection correctly ignores identical texts")
        else:
            print("⚠️ Detection incorrectly finds differences in identical texts")
            
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Run the QA detection test."""
    success = test_qa_detection()
    
    if success:
        print("\n🎉 QA DETECTION TEST COMPLETED!")
        print("Check the analysis above to see if detection is working properly.")
    else:
        print("\n❌ QA DETECTION TEST FAILED!")
        print("There are issues with the detection functionality.")
        
    return success

if __name__ == "__main__":
    main()