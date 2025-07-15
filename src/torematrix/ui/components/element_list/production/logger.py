"""
Logger for Hierarchical Element List

Provides specialized logging for element list operations
with performance tracking and debugging support.
"""

import logging
from typing import Optional, Dict, Any
from PyQt6.QtCore import QObject

logger = logging.getLogger(__name__)


class ElementListLogger(QObject):
    """
    Specialized logger for element list operations
    
    Provides performance tracking, operation logging,
    and debugging support for production environments.
    """
    
    def __init__(self, element_list_widget, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self.element_list = element_list_widget
        self.enable_performance_logging = True
        self.enable_operation_logging = True
        
        # Setup logger
        self.logger = logging.getLogger(f"{__name__}.{id(element_list_widget)}")
        
        logger.info("ElementListLogger initialized")
    
    def log_operation(self, operation: str, context: Dict[str, Any]):
        """Log an element list operation"""
        if self.enable_operation_logging:
            self.logger.info(f"Operation: {operation}", extra={"context": context})
    
    def log_performance(self, operation: str, duration: float, details: Dict[str, Any]):
        """Log performance metrics"""
        if self.enable_performance_logging:
            self.logger.info(f"Performance: {operation} took {duration:.3f}s", 
                           extra={"duration": duration, "details": details})