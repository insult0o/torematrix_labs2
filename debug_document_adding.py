#!/usr/bin/env python3
"""
Debug why documents are not being added to projects.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Debug document adding issue."""
    print("🚀 TORE Matrix Labs - Document Adding Debug")
    print("=" * 80)
    
    print("🔍 ISSUE ANALYSIS:")
    print("   • Project file shows 'documents': []")
    print("   • Documents not appearing in project tree")
    print("   • My fix code exists but not being executed")
    print("")
    
    print("🔧 LIKELY CAUSES:")
    print("")
    
    print("1️⃣ WORKFLOW PATH NOT TAKEN")
    print("   • You might not be clicking 'Process' button")
    print("   • Different processing path being used")
    print("   • Code not being executed at all")
    print("")
    
    print("2️⃣ ERROR IN DOCUMENT CREATION")
    print("   • Exception during document creation")
    print("   • add_processed_document method failing")
    print("   • Silent failure somewhere")
    print("")
    
    print("3️⃣ PROJECT NOT ACTIVE")
    print("   • No current project when processing")
    print("   • Project widget not accessible")
    print("   • project_widget.add_processed_document() fails")
    print("")
    
    print("🧪 DEBUGGING STEPS:")
    print("")
    
    print("🔍 Step 1: Check if _start_manual_validation is called")
    print("   Expected console output when clicking 'Process':")
    print("   🟢 PROCESSING: Adding document to project immediately...")
    print("   🟢 PROCESSING: Document added to project (status: IN_VALIDATION)")
    print("   🟢 PROJECT: Document added, auto-saving project...")
    print("")
    
    print("🔍 Step 2: Check if project is active")
    print("   Expected console output:")
    print("   🔵 SAVE PROJECT: current_project exists: True")
    print("   🔵 SAVE PROJECT: documents count: 1")
    print("")
    
    print("🔍 Step 3: Check actual workflow path")
    print("   • Are you clicking 'Process' in Ingestion tab?")
    print("   • Does it switch to Manual Validation tab?")
    print("   • Do you see the debug messages in console?")
    print("")
    
    print("💡 QUICK DIAGNOSTIC:")
    print("")
    
    print("When you process a document, you should see this sequence:")
    print("1. Click 'Process' button")
    print("2. Console shows: '🟢 PROCESSING: Adding document to project immediately...'")
    print("3. Manual Validation tab opens")
    print("4. Console shows: '🟢 PROJECT: Document added, auto-saving project...'")
    print("5. Console shows: '🟢 SAVE PROJECT: File written successfully!'")
    print("")
    
    print("❌ IF YOU DON'T SEE THESE MESSAGES:")
    print("   • The workflow path is not being taken")
    print("   • Different processing method being used")
    print("   • Error preventing code execution")
    print("")
    
    print("🔧 FALLBACK SOLUTION:")
    print("If the automatic adding doesn't work, I can create a manual 'Add to Project' button")
    print("that explicitly adds the current document to the project.")
    print("")
    
    print("🚀 NEXT STEPS:")
    print("1. Try processing a document again")
    print("2. Watch console output carefully")
    print("3. Report what console messages you see (or don't see)")
    print("4. I'll fix the specific issue based on what's missing")
    
    return True

if __name__ == "__main__":
    main()