#!/usr/bin/env python3
"""
Debug persistence functionality step by step.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Debug persistence functionality."""
    print("🚀 TORE Matrix Labs - Persistence Debug Test")
    print("=" * 80)
    
    print("✅ Extensive persistence debugging added!")
    print("")
    print("🔧 DEBUG POINTS ADDED:")
    print("   🔵 Document loading → 'DOCUMENT LOADED: About to load persistent selections'")
    print("   🔵 Area selection → 'AREA SELECTED: About to save persistent selections'")
    print("   🔵 Path generation → 'GET PERSISTENCE PATH: current_file_path = ...'")
    print("   🔵 Save operation → 'PERSISTENCE: _save_persistent_selections called'")
    print("   🔵 Load operation → 'PERSISTENCE: _load_persistent_selections called'")
    print("   🟢 Success messages → 'PERSISTENCE: Successfully saved/loaded N selections'")
    print("   🔴 Error messages → 'PERSISTENCE: Error saving/loading: ...'")
    print("")
    print("🧪 TO DEBUG PERSISTENCE:")
    print("   1. Run the application")
    print("   2. Load a PDF document")
    print("   3. Switch to Manual Validation tab")
    print("   4. Watch console for: 'DOCUMENT LOADED: About to load persistent selections'")
    print("   5. Try dragging to select an area")
    print("   6. Watch console for: 'AREA SELECTED: About to save persistent selections'")
    print("   7. Complete area classification")
    print("   8. Check console for: 'PERSISTENCE: Successfully saved N selections'")
    print("")
    print("🔍 COMMON ISSUES TO CHECK:")
    print("   🔴 'No current_file_path' → Document not properly loaded")
    print("   🔴 'Error creating directory' → Permission issues")
    print("   🔴 'No persistence file path' → Path generation failed")
    print("   🔴 'File does not exist' → First time use (normal)")
    print("   🔴 'Error saving/loading' → JSON serialization or file I/O issues")
    print("")
    print("📁 EXPECTED FILE LOCATIONS:")
    print("   • If document is at: /home/user/documents/contract.pdf")
    print("   • Persistence dir: /home/user/documents/.tore_selections/")
    print("   • Persistence file: /home/user/documents/.tore_selections/contract_selections.json")
    print("")
    print("🎯 DEBUGGING STEPS:")
    print("   1. Load document → Should see path generation debug")
    print("   2. Try loading → Should see 'File does not exist' (first time)")
    print("   3. Select area → Should see save attempt")
    print("   4. Check if file was created in the expected location")
    print("   5. Reload document → Should see successful load")
    print("")
    print("📋 SUCCESS INDICATORS:")
    print("   ✅ 'PERSISTENCE: Successfully saved N selections to {path}'")
    print("   ✅ 'PERSISTENCE: Successfully loaded N selections from {path}'")
    print("   ✅ Status message: 'Restored N previously selected areas'")
    print("   ✅ UI shows restored areas in the list")
    print("   ✅ Preview works for restored areas")
    print("")
    print("🔍 If you see any 🔴 red error messages, that's the issue!")
    print("The extensive debugging will pinpoint exactly where persistence fails.")
    
    return True

if __name__ == "__main__":
    main()