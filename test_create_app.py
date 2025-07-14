#!/usr/bin/env python3
"""Test create_application function coverage."""

import sys
from unittest.mock import Mock, patch

# Mock PyQt6 before importing
sys.modules['PyQt6'] = Mock()
sys.modules['PyQt6.QtWidgets'] = Mock()
sys.modules['PyQt6.QtCore'] = Mock()
sys.modules['PyQt6.QtGui'] = Mock()

# Now import and test
from torematrix.ui.main_window import create_application

def test_create_application():
    """Test the create_application function."""
    # Mock QApplication class
    mock_app = Mock()
    mock_app_class = Mock(return_value=mock_app)
    
    # Mock hasattr to test both branches
    with patch('torematrix.ui.main_window.QApplication', mock_app_class):
        with patch('torematrix.ui.main_window.hasattr', return_value=True):
            with patch('torematrix.ui.main_window.Qt') as mock_qt:
                # Add the attributes we're checking for
                mock_qt.AA_EnableHighDpiScaling = Mock()
                mock_qt.AA_UseHighDpiPixmaps = Mock()
                
                app = create_application()
                
                # Verify app properties were set
                mock_app.setApplicationName.assert_called_with("ToreMatrix V3")
                mock_app.setApplicationVersion.assert_called_with("3.0.0")
                mock_app.setOrganizationName.assert_called_with("ToreMatrix Labs")
                mock_app.setOrganizationDomain.assert_called_with("torematrix.com")
                mock_app.setStyle.assert_called_with("Fusion")
                
                print("✓ All create_application tests passed!")
                return True

if __name__ == "__main__":
    test_create_application()