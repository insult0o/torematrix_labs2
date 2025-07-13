#!/usr/bin/env python3
"""
Basic Agent 4 Integration Test.

Simple validation test that doesn't require external dependencies
like Redis or PostgreSQL.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_imports():
    """Test that all core modules can be imported."""
    print("🧪 Testing Core Module Imports")
    print("-" * 40)
    
    tests = [
        ("File Models", "src.torematrix.ingestion.models", "FileMetadata"),
        ("Queue Config", "src.torematrix.ingestion.queue_config", "QueueConfig"),
        ("Unstructured Integration", "src.torematrix.integrations.unstructured.integration", "UnstructuredIntegration"),
    ]
    
    success_count = 0
    
    for name, module_path, class_name in tests:
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"✅ {name}: {cls.__name__}")
            success_count += 1
        except Exception as e:
            print(f"❌ {name}: {e}")
    
    print(f"\nImport Results: {success_count}/{len(tests)} successful")
    return success_count == len(tests)


def test_models():
    """Test that models can be instantiated."""
    print("\n📋 Testing Model Creation")
    print("-" * 40)
    
    try:
        from src.torematrix.ingestion.models import FileMetadata, FileStatus, FileType, UploadSession
        from src.torematrix.ingestion.queue_config import QueueConfig, RetryPolicy
        from datetime import datetime
        
        # Test FileMetadata
        file_metadata = FileMetadata(
            file_id="file-123",
            filename="test.pdf",
            file_type=FileType.PDF,
            mime_type="application/pdf",
            size=1024,
            hash="abc123",
            upload_session_id="session-123",
            uploaded_by="user-123",
            uploaded_at=datetime.utcnow(),
            storage_key="/path/to/file"
        )
        print(f"✅ FileMetadata: {file_metadata.filename}")
        
        # Test UploadSession
        session = UploadSession(
            session_id="session-123",
            user_id="user-123",
            created_at=datetime.utcnow()
        )
        print(f"✅ UploadSession: {session.session_id}")
        
        # Test QueueConfig
        config = QueueConfig()
        print(f"✅ QueueConfig: {config.default_queue_name}")
        
        # Test RetryPolicy
        retry_policy = RetryPolicy()
        print(f"✅ RetryPolicy: {retry_policy.max_attempts} attempts")
        
        return True
        
    except Exception as e:
        print(f"❌ Model creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_unstructured_formats():
    """Test Unstructured.io format support."""
    print("\n🔌 Testing Unstructured.io Integration")
    print("-" * 40)
    
    try:
        from src.torematrix.integrations.unstructured.integration import UnstructuredIntegration
        
        integration = UnstructuredIntegration()
        formats = integration.get_supported_formats()
        
        total_formats = sum(len(exts) for exts in formats.values())
        print(f"✅ Format support: {total_formats} file extensions")
        
        for category, extensions in formats.items():
            print(f"   {category}: {len(extensions)} formats")
        
        # Test that we have required formats
        required_categories = ['pdf', 'office', 'text', 'web']
        missing_categories = [cat for cat in required_categories if cat not in formats]
        
        if missing_categories:
            print(f"⚠️  Missing categories: {missing_categories}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Unstructured integration test failed: {e}")
        return False


def test_file_fixtures():
    """Test file creation fixtures."""
    print("\n📄 Testing Test Fixtures")
    print("-" * 40)
    
    try:
        from tests.fixtures.ingestion_fixtures import (
            create_test_files, 
            generate_random_content,
            TestDataGenerator
        )
        import tempfile
        
        # Test content generation
        content = generate_random_content(50)
        print(f"✅ Content generation: {len(content)} characters")
        
        # Test file creation
        with tempfile.TemporaryDirectory() as tmpdir:
            test_files = create_test_files([
                ("test.txt", "Test content"),
                ("test.html", "<h1>Test</h1>")
            ], Path(tmpdir))
            
            print(f"✅ File creation: {len(test_files)} files created")
            
            # Test data generator
            generator = TestDataGenerator(Path(tmpdir))
            batch_files = generator.create_document_batch(3)
            print(f"✅ Data generator: {len(batch_files)} batch files")
            generator.cleanup()
        
        return True
        
    except Exception as e:
        print(f"❌ Fixture test failed: {e}")
        return False


def test_basic_integration():
    """Test basic integration without external dependencies."""
    print("\n🔧 Testing Basic Integration")
    print("-" * 40)
    
    try:
        from src.torematrix.ingestion.integration import IngestionSettings
        
        # Test settings creation
        settings = IngestionSettings(
            upload_dir="/tmp/test",
            database_url="sqlite:///test.db"
        )
        print(f"✅ Settings: {len(settings.allowed_extensions)} allowed extensions")
        
        # Test that integration system can be imported
        from src.torematrix.ingestion.integration import IngestionSystem
        print(f"✅ IngestionSystem class available")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic integration test failed: {e}")
        return False


def print_summary(results):
    """Print test summary."""
    print("\n" + "=" * 60)
    print("🎯 AGENT 4 BASIC TEST SUMMARY")
    print("=" * 60)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"\nResults: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 All basic tests passed!")
        print("   Agent 4 components are properly structured")
        print("   Ready for full integration testing with dependencies")
    else:
        print("\n⚠️  Some tests failed - review errors above")
    
    print("\n📚 Next Steps:")
    print("   1. Install Redis: docker run -d -p 6379:6379 redis:7-alpine")
    print("   2. Run full integration test: python test_agent4_integration.py")
    print("   3. Run test suite: pytest tests/")
    print("   4. Deploy with Docker: docker-compose -f docker-compose.test.yml up")
    
    return passed_tests == total_tests


def main():
    """Main test function."""
    print("🚀 Agent 4 Basic Integration Validation")
    print(f"🐍 Python version: {sys.version}")
    print(f"📍 Working directory: {Path.cwd()}")
    
    # Run tests
    results = {
        "Module Imports": test_imports(),
        "Model Creation": test_models(),
        "Unstructured Formats": test_unstructured_formats(),
        "Test Fixtures": test_file_fixtures(),
        "Basic Integration": test_basic_integration()
    }
    
    # Print summary
    success = print_summary(results)
    
    return 0 if success else 1


if __name__ == "__main__":
    try:
        result = main()
        sys.exit(result)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)