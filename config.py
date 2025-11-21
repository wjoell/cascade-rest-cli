"""
Configuration settings for Cascade REST CLI
"""

import os
from pathlib import Path

# Default Cascade Server URL
DEFAULT_CMS_PATH = "https://cms.example.edu:8443"

# Default site name for searches
DEFAULT_SITE = None

# Output format options
OUTPUT_FORMATS = ["json", "table", "summary"]

# Default output format
DEFAULT_OUTPUT_FORMAT = "json"

# Batch operation settings
BATCH_SIZE = 50
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
PARALLEL_WORKERS = 4  # for concurrent operations

# Logging settings
LOG_LEVEL = "INFO"
LOG_FILE = "cascade_cli.log"
LOG_DIR = Path("logs")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_ROTATION_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# Cache settings
CACHE_ENABLED = True
CACHE_TTL = 300  # seconds (5 minutes)

# CSV Import/Export settings
CSV_ENCODING = "utf-8"
CSV_DELIMITER = ","
CSV_QUOTECHAR = '"'
CSV_BACKUP_DIR = Path("csv_backups")

# Rollback settings
ROLLBACK_ENABLED = True
ROLLBACK_DIR = Path("rollbacks")
ROLLBACK_RETENTION_DAYS = 30

# Advanced filtering settings
FILTER_OPERATORS = [
    "equals",
    "contains",
    "starts_with",
    "ends_with",
    "regex",
    "in",
    "not_in",
    "greater_than",
    "less_than",
    "date_after",
    "date_before",
    "date_between",
    "is_empty",
    "is_not_empty",
]
DATE_FORMATS = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y", "%d/%m/%Y"]

# Performance settings
REQUEST_TIMEOUT = 30  # seconds
CONNECTION_POOL_SIZE = 10
