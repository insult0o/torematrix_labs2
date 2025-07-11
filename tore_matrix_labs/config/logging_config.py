"""
Logging configuration for TORE Matrix Labs.
"""

import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime


def setup_logging(
    level: int = logging.INFO,
    log_file: str = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
):
    """
    Set up application logging.
    
    Args:
        level: Logging level
        log_file: Path to log file (auto-generated if None)
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
    """
    
    # Create logs directory
    if log_file is None:
        if os.name == 'nt':  # Windows
            log_dir = Path.home() / "AppData" / "Roaming" / "TORE Matrix Labs" / "logs"
        else:  # Unix-like
            log_dir = Path.home() / ".config" / "tore-matrix-labs" / "logs"
        
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"tore_matrix_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # Create file handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    logging.getLogger('PyQt5').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info("TORE Matrix Labs logging initialized")
    logger.info(f"Log file: {log_file}")


class ProgressLogger:
    """Logger for tracking long-running operations."""
    
    def __init__(self, name: str, total: int = 100):
        self.logger = logging.getLogger(name)
        self.total = total
        self.current = 0
        self.last_percent = 0
    
    def update(self, increment: int = 1, message: str = ""):
        """Update progress and log if significant change."""
        self.current += increment
        percent = int((self.current / self.total) * 100)
        
        if percent >= self.last_percent + 10:  # Log every 10%
            self.logger.info(f"Progress: {percent}% ({self.current}/{self.total}) {message}")
            self.last_percent = percent
    
    def complete(self, message: str = ""):
        """Mark operation as complete."""
        self.current = self.total
        self.logger.info(f"Progress: 100% complete {message}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)