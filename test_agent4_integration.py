#!/usr/bin/env python3
"""
Agent 4 Integration Test Script.

Quick validation test for the Document Ingestion System integration.
Tests the main integration system with mock components.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.torematrix.ingestion.integration import IngestionSystem, IngestionSettings


async def test_integration_system():
    """Test the integration system with basic functionality."""
    print("🧪 Testing TORE Matrix V3 Document Ingestion Integration")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Configure system for testing
        settings = IngestionSettings(
            upload_dir=str(Path(tmpdir) / "uploads"),
            database_url="sqlite:///test_integration.db",
            redis_url="redis://localhost:6379/3"  # Test DB
        )
        
        print(f"📁 Upload directory: {settings.upload_dir}")
        
        # Initialize system
        system = IngestionSystem(settings)
        
        try:
            print("🔧 Initializing system...")
            await system.initialize()
            print("✅ System initialized successfully")
            
            # Test integration status
            print("\n📊 Checking integration status...")
            status = await system.get_integration_status()
            
            print(f"   Initialized: {status['initialized']}")
            print(f"   Using mocks: {status.get('using_mocks', 'Unknown')}")
            
            # Check components
            components = status.get("components", {})
            for component, info in components.items():
                available = "✅" if info.get("available") else "❌"
                comp_type = info.get("type", "real")
                print(f"   {component}: {available} ({comp_type})")
            
            # Test document processing with a simple file
            print("\n📄 Testing document processing...")
            
            # Create test file
            test_file = Path(tmpdir) / "test_document.txt"
            test_content = """
This is a test document for the TORE Matrix V3 Document Ingestion System.

It contains multiple paragraphs to test the processing pipeline:
- File upload and validation
- Queue processing 
- Document extraction
- Progress tracking

The system should handle this document efficiently and provide
real-time progress updates throughout the processing pipeline.
            """.strip()
            
            test_file.write_text(test_content)
            print(f"   Created test file: {test_file.name} ({len(test_content)} chars)")
            
            # Process the document
            start_time = time.time()
            result = await system.process_document(test_file)
            processing_time = time.time() - start_time
            
            # Display results
            print(f"\n📈 Processing Results:")
            print(f"   Success: {'✅' if result.get('success') else '❌'}")
            print(f"   Processing time: {processing_time:.2f} seconds")
            
            if result.get("success"):
                print(f"   File ID: {result.get('file_id')}")
                print(f"   Job ID: {result.get('job_id')}")
                if 'processing_time' in result:
                    print(f"   System processing time: {result['processing_time']:.2f}s")
            else:
                print(f"   Error: {result.get('error', 'Unknown error')}")
                if 'errors' in result:
                    for error in result['errors']:
                        print(f"   - {error}")
            
            # Test status again after processing
            print("\n🔍 Final system status...")
            final_status = await system.get_integration_status()
            print(f"   System still initialized: {final_status['initialized']}")
            
            return result.get("success", False)
            
        except Exception as e:
            print(f"❌ Error during testing: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            print("\n🔄 Shutting down system...")
            await system.shutdown()
            print("✅ System shutdown complete")


async def test_unstructured_integration():
    """Test Unstructured.io integration specifically."""
    print("\n🔌 Testing Unstructured.io Integration")
    print("-" * 40)
    
    try:
        from src.torematrix.integrations.unstructured.integration import UnstructuredIntegration
        
        integration = UnstructuredIntegration()
        
        # Test format support
        formats = integration.get_supported_formats()
        total_formats = sum(len(exts) for exts in formats.values())
        
        print(f"📋 Supported formats: {total_formats} file extensions")
        for category, extensions in formats.items():
            print(f"   {category}: {len(extensions)} formats")
        
        # Test integration status
        status = integration.get_integration_status()
        print(f"🔧 Integration status: {type(status).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Unstructured integration test failed: {e}")
        return False


def print_summary(integration_success: bool, unstructured_success: bool):
    """Print test summary."""
    print("\n" + "=" * 60)
    print("🎯 AGENT 4 INTEGRATION TEST SUMMARY")
    print("=" * 60)
    
    print(f"Integration System: {'✅ PASS' if integration_success else '❌ FAIL'}")
    print(f"Unstructured.io: {'✅ PASS' if unstructured_success else '❌ FAIL'}")
    
    overall_success = integration_success and unstructured_success
    print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if overall_success:
        print("\n🎉 Agent 4 integration is ready!")
        print("   - System integration layer working")
        print("   - Mock components functioning")
        print("   - Document processing pipeline operational")
        print("   - Ready for Agent 1-3 component integration")
    else:
        print("\n⚠️  Issues detected:")
        if not integration_success:
            print("   - Integration system needs attention")
        if not unstructured_success:
            print("   - Unstructured.io integration issues")
    
    print("\n📚 Next Steps:")
    print("   1. Run comprehensive tests: pytest tests/")
    print("   2. Test with Docker: docker-compose -f docker-compose.test.yml up")
    print("   3. Review deployment guide: docs/deployment.md")
    print("   4. Integration with Agent 1-3 components when ready")
    
    return overall_success


async def main():
    """Main test function."""
    print("🚀 Starting Agent 4 Integration Validation")
    print(f"🐍 Python version: {sys.version}")
    print(f"📍 Working directory: {Path.cwd()}")
    
    # Run tests
    integration_success = await test_integration_system()
    unstructured_success = await test_unstructured_integration()
    
    # Print summary
    overall_success = print_summary(integration_success, unstructured_success)
    
    return 0 if overall_success else 1


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(result)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)