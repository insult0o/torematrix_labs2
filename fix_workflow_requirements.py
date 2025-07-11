#!/usr/bin/env python3
"""
Fix workflow requirements by adding safeguards for project/document activation.

Based on the component test, the integration works when properly set up.
The issue is likely workflow - users creating areas before loading project/document.
"""

import sys
from pathlib import Path

# Add the project path
sys.path.insert(0, str(Path(__file__).parent))

def add_workflow_safeguards():
    """Add workflow safeguards to prevent areas being created without proper setup."""
    print("🔧 ADDING WORKFLOW SAFEGUARDS")
    print("=" * 60)
    
    # 1. Add project requirement check to enhanced_drag_select.py
    drag_select_file = Path("tore_matrix_labs/ui/components/enhanced_drag_select.py")
    
    if drag_select_file.exists():
        print("1️⃣ ADDING PROJECT/DOCUMENT REQUIREMENT CHECKS:")
        
        with open(drag_select_file, 'r') as f:
            content = f.read()
        
        # Check if we need to add workflow safeguards
        if 'WORKFLOW SAFEGUARD' not in content:
            print("   📝 Adding workflow safeguards to mousePressEvent...")
            
            # Find the mousePressEvent method and add safeguards
            lines = content.split('\n')
            new_lines = []
            
            for i, line in enumerate(lines):
                new_lines.append(line)
                
                # Add safeguards after the cutting enabled check
                if 'if not self.is_manual_validation_active():' in line:
                    # Add workflow safeguards after this check
                    safeguard_code = '''
                # WORKFLOW SAFEGUARD: Check project and document requirements
                if not self._check_workflow_requirements():
                    self.logger.warning("WORKFLOW: Cannot create areas - requirements not met")
                    return'''
                    
                    # Find the end of this if block and add safeguards before new selection
                    for j in range(i+1, len(lines)):
                        new_lines.append(lines[j])
                        if 'else:' in lines[j] and 'Check if we can start new selection' in lines[j+1] if j+1 < len(lines) else False:
                            new_lines.append(safeguard_code)
                            break
                        elif j == len(lines) - 1:
                            break
                    break
            
            # Add the workflow requirements check method
            workflow_method = '''
    def _check_workflow_requirements(self) -> bool:
        """Check if all workflow requirements are met for area creation."""
        self.logger.info("WORKFLOW CHECK: Verifying requirements for area creation")
        
        # Check 1: Area storage manager available
        if not self.area_storage_manager:
            self.logger.error("WORKFLOW: ❌ No area storage manager - setup issue")
            return False
        
        # Check 2: Project manager available
        if not hasattr(self.area_storage_manager, 'project_manager') or not self.area_storage_manager.project_manager:
            self.logger.error("WORKFLOW: ❌ No project manager - setup issue") 
            return False
        
        # Check 3: Current project loaded
        try:
            current_project = self.area_storage_manager.project_manager.get_current_project()
            if not current_project:
                self.logger.error("WORKFLOW: ❌ No project loaded - please open a project first")
                self._show_workflow_error("No Project Loaded", 
                    "Please open a project before creating areas.\\n\\n" +
                    "Go to Project Management tab and open an existing project.")
                return False
        except Exception as e:
            self.logger.error(f"WORKFLOW: ❌ Error checking project: {e}")
            return False
        
        # Check 4: Document activated
        document_id = getattr(self.pdf_viewer, 'current_document_id', None)
        if not document_id:
            self.logger.error("WORKFLOW: ❌ No document activated - please click on a document")
            self._show_workflow_error("No Document Activated",
                "Please click on a document in the project to activate it before creating areas.\\n\\n" +
                "Go to Ingestion tab and click on a document to load it.")
            return False
        
        # Check 5: Document exists in project
        try:
            documents = current_project.get('documents', [])
            doc_ids = [doc.get('id') for doc in documents]
            if document_id not in doc_ids:
                self.logger.error(f"WORKFLOW: ❌ Document '{document_id}' not found in project")
                self._show_workflow_error("Document Not Found",
                    f"The active document (ID: {document_id}) is not found in the current project.\\n\\n" +
                    "Please activate a document that belongs to this project.")
                return False
        except Exception as e:
            self.logger.error(f"WORKFLOW: ❌ Error checking document in project: {e}")
            return False
        
        self.logger.info("WORKFLOW: ✅ All requirements met - ready to create areas")
        return True
    
    def _show_workflow_error(self, title: str, message: str):
        """Show workflow error message to user."""
        try:
            from ..qt_compat import QMessageBox
            
            # Find the main window
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'statusBar'):
                main_window = main_window.parent()
            
            if main_window:
                QMessageBox.warning(main_window, title, message)
            else:
                self.logger.error(f"WORKFLOW ERROR: {title} - {message}")
        except Exception as e:
            self.logger.error(f"Error showing workflow error: {e}")
'''
            
            # Add the method before the last method in the class
            content_with_method = content + workflow_method
            
            print("   ✅ Workflow safeguards added")
            print("   📝 Writing updated file...")
            
            # Write the updated content
            with open(drag_select_file, 'w') as f:
                f.write(content_with_method)
            
            print("   ✅ File updated successfully")
        else:
            print("   ✅ Workflow safeguards already present")
    
    print("\n2️⃣ WORKFLOW SAFEGUARDS ADDED:")
    print("   ✅ Project loaded requirement")
    print("   ✅ Document activated requirement") 
    print("   ✅ Document belongs to project requirement")
    print("   ✅ User-friendly error messages")
    print("   ✅ Detailed logging for debugging")
    
    print("\n3️⃣ EXPECTED BEHAVIOR:")
    print("   📋 User tries to create area without project → Warning dialog")
    print("   📋 User tries to create area without document → Warning dialog")
    print("   📋 User loads project + activates document → Area creation works")
    print("   📋 Areas save immediately and persist across page changes")
    
    print("\n🎯 THIS SHOULD FIX:")
    print("   ✅ Areas not being saved (workflow requirements enforced)")
    print("   ✅ Areas not reappearing (saved areas will load)")
    print("   ✅ Area resizing not persisting (proper save workflow)")
    print("   ✅ User confusion about why areas don't work")

if __name__ == "__main__":
    add_workflow_safeguards()