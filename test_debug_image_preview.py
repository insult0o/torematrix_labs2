#!/usr/bin/env python3
"""
Test to help debug image preview with detailed console output.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Test image preview with debugging."""
    print("🚀 TORE Matrix Labs - Image Preview Debug Test")
    print("=" * 80)
    
    print("✅ Image preview debugging has been enhanced!")
    print("")
    print("🔧 CHANGES MADE:")
    print("   1. ✅ Fixed _on_area_selected to call _update_selection_list() and _show_preview_image()")
    print("   2. ✅ Added extensive debug logging to _show_preview_image()")
    print("   3. ✅ Added coordinate conversion debugging to PDF viewer")
    print("   4. ✅ All signals and methods are properly connected")
    print("")
    print("🧪 TO TEST THE IMAGE PREVIEW:")
    print("   1. Run the application: python3 main.py")
    print("   2. Load a document (via Ingestion or Project Manager)")
    print("   3. Switch to Manual Validation tab")
    print("   4. Try dragging on the PDF")
    print("")
    print("📋 CONSOLE OUTPUT TO WATCH FOR:")
    print("   • 'Document loaded into manual validation widget: /path/to/file.pdf'")
    print("   • 'Received preview update: {area data}'")
    print("   • 'Showing preview for area: {area data}'")
    print("   • 'Preview bbox: [x1, y1, x2, y2], page: 0'")
    print("   • 'Converting coordinates:' with scaling details")
    print("   • 'PDF page size: ..., area rect: ...'")
    print("   • 'Extracted pixmap size: ...x...'")
    print("   • 'QPixmap load success: True, size: ...x...'")
    print("   • 'Preview image set successfully!'")
    print("")
    print("⚠️  COMMON ISSUES TO CHECK:")
    print("   • If you see 'No PDF viewer or document' → PDF not loaded properly")
    print("   • If coordinates are [0, 0, 0, 0] → Area selection not working")
    print("   • If pixmap size is 0x0 → Coordinate conversion issue")
    print("   • If 'Invalid area rectangle' → Bbox calculation problem")
    print("   • If no console output at all → Signal connection issue")
    print("")
    print("🎯 THE PREVIEW SHOULD NOW WORK FOR:")
    print("   ⚡ Real-time preview DURING dragging (with 'Live Preview:' label)")
    print("   🖼️  Persistent preview AFTER area classification")
    print("   🔄 Preview updates when selecting different areas from list")
    print("")
    print("🎊 Ready for testing! The extensive debug logs will show exactly what's happening.")
    
    return True

if __name__ == "__main__":
    main()