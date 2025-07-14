"""
Basic tests for configuration system integration.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime
from pathlib import Path

from src.torematrix.core.config.integration import (
    ConfigAuditAction,
    ConfigAuditEntry,
    ConfigurationAuditLogger,
    EventBusIntegration
)
from src.torematrix.core.config.events import ConfigurationChangeEvent, ConfigEventType
from src.torematrix.core.config.types import ConfigSource


class TestBasicIntegration:
    """Basic integration tests."""
    
    def test_audit_entry_creation(self):
        """Test creating audit entry."""
        entry = ConfigAuditEntry(
            action=ConfigAuditAction.CONFIG_WRITE,
            config_path="test.key",
            old_value="old",
            new_value="new"
        )
        
        assert entry.action == ConfigAuditAction.CONFIG_WRITE
        assert entry.config_path == "test.key"
    
    def test_audit_logger_basic(self):
        """Test basic audit logger functionality."""
        logger = ConfigurationAuditLogger()
        assert logger is not None
    
    def test_event_bus_integration_basic(self):
        """Test basic event bus integration."""
        mock_bus = Mock()
        integration = EventBusIntegration(mock_bus)
        assert integration.event_bus == mock_bus


if __name__ == '__main__':
    pytest.main([__file__])