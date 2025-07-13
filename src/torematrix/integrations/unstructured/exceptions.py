"""
Exception classes for unstructured integration.

This module defines custom exceptions for the unstructured integration.
"""


class UnstructuredError(Exception):
    """Base exception for unstructured integration errors."""
    pass


class UnstructuredParsingError(UnstructuredError):
    """Exception raised when document parsing fails."""
    pass


class UnstructuredConfigError(UnstructuredError):
    """Exception raised for configuration issues."""
    pass


class UnstructuredMappingError(UnstructuredError):
    """Exception raised when element mapping fails."""
    pass


class UnstructuredValidationError(UnstructuredError):
    """Exception raised when validation fails."""
    pass


# Additional exceptions for other agents
class UnstructuredTimeoutError(UnstructuredError):
    """Exception raised when operations timeout."""
    pass


class UnstructuredConnectionError(UnstructuredError):
    """Exception raised for connection issues."""
    pass


class UnstructuredResourceError(UnstructuredError):
    """Exception raised for resource-related issues."""
    pass