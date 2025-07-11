#!/usr/bin/env python3
"""
Clean up old document-based persistence files.
"""

import sys
from pathlib import Path
import shutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def cleanup_old_persistence():
    """Clean up old document-based persistence files."""
    print("🚀 TORE Matrix Labs - Cleanup Old Persistence")
    print("=" * 80)
    
    # Find old .tore_selections directories
    old_dirs = list(Path.cwd().glob("**/.tore_selections"))
    
    if not old_dirs:
        print("✅ No old .tore_selections directories found")
        return True
    
    print(f"🔍 Found {len(old_dirs)} old persistence directories:")
    
    for old_dir in old_dirs:
        print(f"\n📂 Directory: {old_dir}")
        
        # List files in the directory
        files = list(old_dir.glob("*_selections.json"))
        print(f"   📄 Files: {len(files)}")
        
        for file in files:
            print(f"      • {file.name}")
        
        # Ask for confirmation
        print(f"\n🗑️  Clean up this directory? (y/n)", end=" ")
        response = input().strip().lower()
        
        if response == 'y':
            try:
                # Remove the directory and all contents
                shutil.rmtree(old_dir)
                print(f"✅ Removed: {old_dir}")
            except Exception as e:
                print(f"❌ Error removing {old_dir}: {e}")
        else:
            print(f"⏭️  Skipped: {old_dir}")
    
    print(f"\n✅ Cleanup process completed!")
    print(f"🎯 All persistence is now project-specific only.")
    
    return True

if __name__ == "__main__":
    cleanup_old_persistence()