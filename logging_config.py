"""
Logging configuration for Cascade REST CLI
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional
import json
from datetime import datetime

from config import (
    LOG_LEVEL,
    LOG_FILE,
    LOG_DIR,
    LOG_FORMAT,
    LOG_ROTATION_SIZE,
    LOG_BACKUP_COUNT,
)


class OperationLogger:
    """Enhanced logger for tracking operations with structured logging"""

    def __init__(self, name: str = "cascade_cli"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, LOG_LEVEL.upper()))

        # Create logs directory if it doesn't exist
        LOG_DIR.mkdir(exist_ok=True)

        # Setup handlers if not already configured
        if not self.logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self):
        """Setup file and console handlers"""

        # File handler with rotation
        log_file_path = LOG_DIR / LOG_FILE
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path, maxBytes=LOG_ROTATION_SIZE, backupCount=LOG_BACKUP_COUNT
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(LOG_FORMAT)
        file_handler.setFormatter(file_formatter)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter("%(levelname)s - %(message)s")
        console_handler.setFormatter(console_formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def log_operation_start(self, operation: str, **kwargs):
        """Log the start of an operation with context"""
        context = {
            "operation": operation,
            "timestamp": datetime.now().isoformat(),
            "context": kwargs,
        }
        self.logger.info(f"Starting {operation}", extra={"structured": context})

    def log_operation_end(self, operation: str, success: bool, **kwargs):
        """Log the end of an operation with results"""
        context = {
            "operation": operation,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "results": kwargs,
        }
        level = logging.INFO if success else logging.ERROR
        self.logger.log(
            level,
            f"Completed {operation} - {'SUCCESS' if success else 'FAILED'}",
            extra={"structured": context},
        )

    def log_batch_progress(self, operation: str, current: int, total: int, **kwargs):
        """Log progress of batch operations"""
        progress = (current / total) * 100 if total > 0 else 0
        context = {
            "operation": operation,
            "progress": f"{current}/{total} ({progress:.1f}%)",
            "timestamp": datetime.now().isoformat(),
            **kwargs,
        }
        self.logger.info(
            f"Batch progress: {current}/{total} ({progress:.1f}%)",
            extra={"structured": context},
        )

    def log_api_call(
        self,
        method: str,
        url: str,
        status_code: Optional[int] = None,
        response_time: Optional[float] = None,
        **kwargs,
    ):
        """Log API calls with timing and status"""
        context = {
            "api_call": {
                "method": method,
                "url": url,
                "status_code": status_code,
                "response_time_ms": response_time * 1000 if response_time else None,
                "timestamp": datetime.now().isoformat(),
            },
            **kwargs,
        }

        if status_code:
            level = logging.ERROR if status_code >= 400 else logging.DEBUG
            self.logger.log(
                level,
                f"API {method} {url} - {status_code}",
                extra={"structured": context},
            )
        else:
            self.logger.debug(f"API {method} {url}", extra={"structured": context})

    def log_error(self, error: Exception, context: Optional[dict] = None):
        """Log errors with full context"""
        error_context = {
            "error": {
                "type": type(error).__name__,
                "message": str(error),
                "timestamp": datetime.now().isoformat(),
            },
            "context": context or {},
        }
        self.logger.error(
            f"Error: {type(error).__name__}: {error}",
            extra={"structured": error_context},
            exc_info=True,
        )

    def log_rollback_operation(self, operation_id: str, action: str, **kwargs):
        """Log rollback operations"""
        context = {
            "rollback": {
                "operation_id": operation_id,
                "action": action,
                "timestamp": datetime.now().isoformat(),
            },
            **kwargs,
        }
        self.logger.info(
            f"Rollback {action}: {operation_id}", extra={"structured": context}
        )


def get_logger(name: str = "cascade_cli") -> OperationLogger:
    """Get a configured logger instance"""
    return OperationLogger(name)


# Global logger instance
logger = get_logger()
