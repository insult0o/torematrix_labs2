#!/usr/bin/env python3
"""
Test to debug signal flow in image preview.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Test signal debugging setup."""
    print("🚀 TORE Matrix Labs - Signal Flow Debug Test")
    print("=" * 80)
    
    print("✅ Added extensive signal debugging!")
    print("")
    print("🔧 DEBUG SIGNALS ADDED:")
    print("   🟠 DRAG LABEL: 'Emitting area_preview_update signal'")
    print("   🔴 DRAG LABEL: 'Emitting area_selected signal'") 
    print("   🟡 PDF VIEWER: 'Area preview update signal emitted'")
    print("   🔴 PDF VIEWER: 'Area selected signal emitted'")
    print("   🟢 MANUAL VALIDATION: 'Received preview update signal'")
    print("   🟢 MANUAL VALIDATION: 'Received area selected signal'")
    print("")
    print("🧪 TESTING WORKFLOW:")
    print("   1. Run the application")
    print("   2. Load a document (any PDF)")
    print("   3. Switch to Manual Validation tab")
    print("   4. Try dragging on the PDF")
    print("")
    print("📋 EXPECTED SIGNAL FLOW:")
    print("   🟠 DRAG LABEL: Emitting area_preview_update signal")
    print("   🟡 PDF VIEWER: Area preview update signal emitted")
    print("   🟢 MANUAL VALIDATION: Received preview update signal")
    print("   🖼️  Image preview should appear immediately")
    print("")
    print("   After dragging (classification dialog):")
    print("   🔴 DRAG LABEL: Emitting area_selected signal") 
    print("   🔴 PDF VIEWER: Area selected signal emitted")
    print("   🟢 MANUAL VALIDATION: Received area selected signal")
    print("   🖼️  Image preview should persist")
    print("")
    print("🔍 IF NO SIGNALS APPEAR:")
    print("   • PDF not loaded → Check for PDF loading errors")
    print("   • Mouse events not captured → Try larger drag area (>20px)")
    print("   • Widget not initialized → Check tab is active")
    print("")
    print("🔍 IF SIGNALS STOP AT SPECIFIC POINT:")
    print("   • Missing 🟠 DRAG LABEL → Mouse events not working")
    print("   • Missing 🟡 PDF VIEWER → Internal signal connection broken")
    print("   • Missing 🟢 MANUAL VALIDATION → Main window connection broken")
    print("")
    print("📊 COORDINATE DEBUG INFO:")
    print("   • 'Converting coordinates:' shows widget→PDF conversion")
    print("   • 'Preview bbox: [x1, y1, x2, y2]' shows final coordinates")
    print("   • 'PDF page size: ..., area rect: ...' shows PDF extraction")
    print("   • 'Extracted pixmap size: NxN' shows image creation")
    print("   • 'Preview image set successfully!' confirms display")
    print("")
    print("🎯 This debugging will pinpoint exactly where the signal flow breaks!")
    print("Run the app and check console output during drag operations.")
    
    return True

if __name__ == "__main__":
    main()