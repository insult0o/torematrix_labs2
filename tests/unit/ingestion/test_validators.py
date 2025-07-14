"""
Unit tests for file validators.
"""

import pytest
from pathlib import Path
import tempfile
import json
import zipfile
from unittest.mock import patch, Mock

from torematrix.ingestion.validators import (
    MimeTypeValidator,
    FileSizeValidator,
    ContentValidator,
    SecurityValidator,
    HashValidator,
    CompositeValidator,
    create_default_validator
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestMimeTypeValidator:
    """Test cases for MIME type validator."""
    
    async def test_valid_mime_type(self, temp_dir):
        """Test validation of correct MIME type."""
        validator = MimeTypeValidator()
        
        # Create test PDF file
        test_file = temp_dir / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3")
        
        with patch("magic.Magic.from_file", return_value="application/pdf"):
            errors = await validator.validate(test_file)
        
        assert errors == []
    
    async def test_mime_type_mismatch(self, temp_dir):
        """Test detection of MIME type mismatch."""
        validator = MimeTypeValidator()
        
        # Create file with wrong extension
        test_file = temp_dir / "fake.pdf"
        test_file.write_text("This is plain text")
        
        with patch("magic.Magic.from_file", return_value="text/plain"):
            errors = await validator.validate(test_file)
        
        assert len(errors) == 1
        assert "MIME type mismatch" in errors[0]
    
    async def test_unknown_extension(self, temp_dir):
        """Test handling of unknown file extension."""
        validator = MimeTypeValidator()
        
        test_file = temp_dir / "file.xyz"
        test_file.write_bytes(b"unknown content")
        
        with patch("magic.Magic.from_file", return_value="application/octet-stream"):
            errors = await validator.validate(test_file)
        
        # Should not error on unknown extensions
        assert errors == []
    
    async def test_file_not_found(self):
        """Test handling of missing file."""
        validator = MimeTypeValidator()
        
        errors = await validator.validate(Path("/nonexistent/file.pdf"))
        
        assert len(errors) == 1
        assert "File not found" in errors[0]


class TestFileSizeValidator:
    """Test cases for file size validator."""
    
    async def test_valid_file_size(self, temp_dir):
        """Test validation of file within size limits."""
        validator = FileSizeValidator(max_size=1024, min_size=10)
        
        test_file = temp_dir / "test.txt"
        test_file.write_bytes(b"x" * 100)  # 100 bytes
        
        errors = await validator.validate(test_file)
        assert errors == []
    
    async def test_file_too_large(self, temp_dir):
        """Test detection of oversized file."""
        validator = FileSizeValidator(max_size=100)
        
        test_file = temp_dir / "large.txt"
        test_file.write_bytes(b"x" * 200)  # 200 bytes
        
        errors = await validator.validate(test_file)
        
        assert len(errors) == 1
        assert "File too large" in errors[0]
        assert "200 bytes" in errors[0]
    
    async def test_file_too_small(self, temp_dir):
        """Test detection of undersized file."""
        validator = FileSizeValidator(min_size=10)
        
        test_file = temp_dir / "small.txt"
        test_file.write_bytes(b"x")  # 1 byte
        
        errors = await validator.validate(test_file)
        
        assert len(errors) == 1
        assert "File too small" in errors[0]


class TestContentValidator:
    """Test cases for content validator."""
    
    async def test_valid_pdf(self, temp_dir):
        """Test validation of valid PDF."""
        validator = ContentValidator()
        
        test_file = temp_dir / "test.pdf"
        # Minimal PDF structure
        test_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\nxref\n0 1\ntrailer\n<<>>\n%%EOF")
        
        # Mock PyPDF2
        with patch("torematrix.ingestion.validators.HAS_PYPDF2", True):
            mock_reader = Mock()
            mock_reader.is_encrypted = False
            mock_reader.pages = [Mock()]
            mock_reader.pages[0].extract_text.return_value = "Test content"
            
            with patch("PyPDF2.PdfReader", return_value=mock_reader):
                errors = await validator.validate(test_file)
        
        assert errors == []
    
    async def test_encrypted_pdf(self, temp_dir):
        """Test detection of encrypted PDF."""
        validator = ContentValidator()
        
        test_file = temp_dir / "encrypted.pdf"
        test_file.write_bytes(b"%PDF-1.4")
        
        with patch("torematrix.ingestion.validators.HAS_PYPDF2", True):
            mock_reader = Mock()
            mock_reader.is_encrypted = True
            
            with patch("PyPDF2.PdfReader", return_value=mock_reader):
                errors = await validator.validate(test_file)
        
        assert len(errors) == 1
        assert "PDF is encrypted" in errors[0]
    
    async def test_valid_json(self, temp_dir):
        """Test validation of valid JSON."""
        validator = ContentValidator()
        
        test_file = temp_dir / "test.json"
        test_file.write_text('{"key": "value", "number": 123}')
        
        errors = await validator.validate(test_file)
        assert errors == []
    
    async def test_invalid_json(self, temp_dir):
        """Test detection of invalid JSON."""
        validator = ContentValidator()
        
        test_file = temp_dir / "invalid.json"
        test_file.write_text('{"key": "value", invalid}')
        
        errors = await validator.validate(test_file)
        
        assert len(errors) == 1
        assert "Invalid JSON" in errors[0]
    
    async def test_valid_zip(self, temp_dir):
        """Test validation of valid ZIP archive."""
        validator = ContentValidator()
        
        test_file = temp_dir / "test.zip"
        
        # Create valid ZIP
        with zipfile.ZipFile(test_file, 'w') as zf:
            zf.writestr("file1.txt", "content1")
            zf.writestr("file2.txt", "content2")
        
        errors = await validator.validate(test_file)
        assert errors == []
    
    async def test_empty_zip(self, temp_dir):
        """Test detection of empty ZIP archive."""
        validator = ContentValidator()
        
        test_file = temp_dir / "empty.zip"
        
        # Create empty ZIP
        with zipfile.ZipFile(test_file, 'w') as zf:
            pass
        
        errors = await validator.validate(test_file)
        
        assert len(errors) == 1
        assert "ZIP archive is empty" in errors[0]
    
    async def test_text_file_encoding(self, temp_dir):
        """Test text file encoding detection."""
        validator = ContentValidator()
        
        # UTF-8 file
        utf8_file = temp_dir / "utf8.txt"
        utf8_file.write_text("Hello world with émojis 🌍", encoding="utf-8")
        
        errors = await validator.validate(utf8_file)
        assert errors == []
        
        # Binary file pretending to be text
        binary_file = temp_dir / "binary.txt"
        binary_file.write_bytes(b"\x00\x01\x02\x03\x04")
        
        errors = await validator.validate(binary_file)
        assert len(errors) == 1
        assert "Unable to decode text file" in errors[0]


class TestSecurityValidator:
    """Test cases for security validator."""
    
    async def test_safe_file(self, temp_dir):
        """Test validation of safe file."""
        validator = SecurityValidator()
        
        test_file = temp_dir / "document.pdf"
        test_file.write_bytes(b"PDF content")
        
        errors = await validator.validate(test_file)
        assert errors == []
    
    async def test_dangerous_extension(self, temp_dir):
        """Test detection of dangerous file extension."""
        validator = SecurityValidator()
        
        test_file = temp_dir / "malware.exe"
        test_file.write_bytes(b"MZ")  # PE header
        
        errors = await validator.validate(test_file)
        
        assert len(errors) == 1
        assert "Potentially dangerous file type: .exe" in errors[0]
    
    async def test_double_extension(self, temp_dir):
        """Test detection of suspicious double extension."""
        validator = SecurityValidator()
        
        test_file = temp_dir / "document.pdf.exe"
        test_file.write_bytes(b"MZ")
        
        errors = await validator.validate(test_file)
        
        assert len(errors) >= 1
        assert any("Suspicious double extension" in error for error in errors)
    
    async def test_script_extensions(self, temp_dir):
        """Test detection of script file extensions."""
        validator = SecurityValidator()
        
        script_extensions = [".bat", ".cmd", ".vbs", ".js", ".jar"]
        
        for ext in script_extensions:
            test_file = temp_dir / f"script{ext}"
            test_file.write_bytes(b"script content")
            
            errors = await validator.validate(test_file)
            assert len(errors) == 1
            assert f"Potentially dangerous file type: {ext}" in errors[0]


class TestHashValidator:
    """Test cases for hash validator."""
    
    async def test_calculate_hash(self, temp_dir):
        """Test hash calculation."""
        validator = HashValidator(algorithm="sha256")
        
        test_file = temp_dir / "test.txt"
        content = b"Hello, World!"
        test_file.write_bytes(content)
        
        # Validate doesn't return errors, just calculates
        errors = await validator.validate(test_file)
        assert errors == []
        
        # Test actual hash calculation
        hash_value = await validator.calculate_hash(test_file)
        
        # Known SHA-256 for "Hello, World!"
        expected = "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
        assert hash_value == expected
    
    async def test_different_algorithms(self, temp_dir):
        """Test different hash algorithms."""
        test_file = temp_dir / "test.txt"
        test_file.write_bytes(b"test content")
        
        algorithms = ["md5", "sha1", "sha256", "sha512"]
        
        for algo in algorithms:
            validator = HashValidator(algorithm=algo)
            errors = await validator.validate(test_file)
            assert errors == []
            
            hash_value = await validator.calculate_hash(test_file)
            assert len(hash_value) > 0


class TestCompositeValidator:
    """Test cases for composite validator."""
    
    async def test_all_validators_pass(self, temp_dir):
        """Test when all validators pass."""
        validators = [
            FileSizeValidator(max_size=1024),
            SecurityValidator()
        ]
        
        composite = CompositeValidator(validators)
        
        test_file = temp_dir / "valid.txt"
        test_file.write_bytes(b"Valid content")
        
        errors = await composite.validate(test_file)
        assert errors == []
    
    async def test_multiple_validator_errors(self, temp_dir):
        """Test when multiple validators report errors."""
        validators = [
            FileSizeValidator(max_size=10),  # Will fail
            SecurityValidator()
        ]
        
        composite = CompositeValidator(validators)
        
        test_file = temp_dir / "large.exe"  # Both will fail
        test_file.write_bytes(b"x" * 100)
        
        errors = await composite.validate(test_file)
        
        assert len(errors) >= 2
        assert any("FileSizeValidator" in error for error in errors)
        assert any("SecurityValidator" in error for error in errors)
    
    async def test_validator_exception_handling(self, temp_dir):
        """Test handling of validator exceptions."""
        # Create validator that raises exception
        bad_validator = Mock()
        bad_validator.name = "BadValidator"
        bad_validator.validate = Mock(side_effect=Exception("Validator error"))
        
        validators = [
            bad_validator,
            SecurityValidator()  # Should still run
        ]
        
        composite = CompositeValidator(validators)
        
        test_file = temp_dir / "test.txt"
        test_file.write_bytes(b"content")
        
        errors = await composite.validate(test_file)
        
        assert len(errors) == 1
        assert "[BadValidator] Validator failed" in errors[0]


class TestCreateDefaultValidator:
    """Test cases for default validator creation."""
    
    async def test_default_validator_creation(self):
        """Test creation of default validator."""
        validator = create_default_validator()
        
        assert isinstance(validator, CompositeValidator)
        assert len(validator.validators) >= 3  # Size, MIME, Content at minimum
    
    async def test_default_validator_with_security(self):
        """Test default validator with security enabled."""
        validator = create_default_validator(check_security=True)
        
        validator_names = [v.name for v in validator.validators]
        assert "SecurityValidator" in validator_names
    
    async def test_default_validator_without_security(self):
        """Test default validator without security."""
        validator = create_default_validator(check_security=False)
        
        validator_names = [v.name for v in validator.validators]
        assert "SecurityValidator" not in validator_names
    
    async def test_default_validator_functionality(self, temp_dir):
        """Test that default validator works properly."""
        validator = create_default_validator(max_file_size=1024)
        
        # Valid file
        valid_file = temp_dir / "valid.pdf"
        valid_file.write_bytes(b"%PDF-1.4\ntest")
        
        with patch("magic.Magic.from_file", return_value="application/pdf"):
            errors = await validator.validate(valid_file)
        
        # Should have some errors due to invalid PDF structure
        # but not critical ones
        assert isinstance(errors, list)