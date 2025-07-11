#!/usr/bin/env python3
"""
TORE Matrix Labs - Demo Script
Demonstrates the application working without requiring actual PDF files.
"""

def demo_tore_matrix():
    """Demonstrate TORE Matrix Labs functionality."""
    
    print("🚀 TORE Matrix Labs - Demo")
    print("=" * 50)
    print()
    
    # Test imports
    print("✅ Testing Core Imports...")
    try:
        from tore_matrix_labs.config.settings import Settings
        from tore_matrix_labs.config.constants import DocumentType, QualityLevel
        from tore_matrix_labs.models.document_models import Document, DocumentMetadata
        print("   ✓ Configuration and models imported successfully")
    except ImportError as e:
        print(f"   ✗ Import failed: {e}")
        return
    
    # Test settings
    print("\n✅ Testing Configuration System...")
    try:
        settings = Settings()
        print(f"   ✓ Settings loaded - Quality threshold: {settings.processing.quality_threshold}")
        print(f"   ✓ Chunk size: {settings.processing.chunk_size}")
        print(f"   ✓ Data directory: {settings.get_data_directory()}")
    except Exception as e:
        print(f"   ✗ Settings failed: {e}")
        return
    
    # Test document model
    print("\n✅ Testing Document Models...")
    try:
        from datetime import datetime
        
        metadata = DocumentMetadata(
            file_name="test.pdf",
            file_path="/test/test.pdf",
            file_size=1024000,
            file_type="pdf",
            creation_date=datetime.now(),
            modification_date=datetime.now(),
            page_count=10,
            title="Test ICAO Document"
        )
        
        doc = Document(
            id="test-doc-1",
            metadata=metadata,
            document_type=DocumentType.ICAO,
            processing_status=ProcessingStatus.PENDING,
            processing_config=ProcessingConfiguration(),
            quality_level=QualityLevel.EXCELLENT,
            quality_score=0.95
        )
        
        print(f"   ✓ Document created: {doc.metadata.file_name}")
        print(f"   ✓ Document type: {doc.document_type.value}")
        print(f"   ✓ Quality level: {doc.quality_level.value}")
        
    except Exception as e:
        print(f"   ✗ Document model failed: {e}")
        return
    
    # Test GUI components (if available)
    print("\n✅ Testing GUI Components...")
    try:
        from tore_matrix_labs.ui.qt_compat import QT_FRAMEWORK
        print(f"   ✓ Qt framework available: {QT_FRAMEWORK}")
        
        from tore_matrix_labs.ui.main_window import MainWindow
        print("   ✓ Main window class imported successfully")
        
    except ImportError:
        print("   ⚠ GUI components not available (expected in headless environment)")
    
    # Test CLI components
    print("\n✅ Testing CLI Components...")
    try:
        from tore_matrix_labs.cli import cli
        print("   ✓ CLI interface imported successfully")
    except Exception as e:
        print(f"   ✗ CLI failed: {e}")
        return
    
    # Test core processing (stub)
    print("\n✅ Testing Core Processing Components...")
    try:
        from tore_matrix_labs.core.document_analyzer import DocumentAnalyzer
        from tore_matrix_labs.core.content_extractor import ContentExtractor
        from tore_matrix_labs.core.quality_assessor import QualityAssessor
        
        analyzer = DocumentAnalyzer(settings)
        extractor = ContentExtractor(settings)
        assessor = QualityAssessor(settings)
        
        print("   ✓ Document analyzer initialized")
        print("   ✓ Content extractor initialized") 
        print("   ✓ Quality assessor initialized")
        
    except Exception as e:
        print(f"   ✗ Core processing failed: {e}")
        return
    
    print("\n🎉 All Components Working Successfully!")
    print("=" * 50)
    print()
    print("📋 Available Commands:")
    print("   tore-matrix --help              # Show CLI help")
    print("   tore-matrix process file.pdf    # Process PDF document")
    print("   tore-matrix analyze file.pdf    # Analyze document quality")
    print("   tore-matrix batch --input-dir docs/  # Batch process")
    print()
    print("🖥️  GUI Mode:")
    print("   python -m tore_matrix_labs      # Start application")
    print("   python -m tore_matrix_labs --gui # Force GUI mode")
    print()
    print("📚 Documentation:")
    print("   See README.md for complete usage instructions")
    print()


if __name__ == "__main__":
    # Import the missing constants
    from tore_matrix_labs.config.constants import ProcessingStatus
    from tore_matrix_labs.models.document_models import ProcessingConfiguration
    
    demo_tore_matrix()