"""
Configuration for migration from old site to new site container.
"""

# Source directory containing XML files and HTML partials
SOURCE_DIR = "/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/migration-clean"

# Target site and folder IDs in Cascade
TARGET_BASE_FOLDER_ID = "b2ced1e27f0001015b805e73d0886cfd"

# Base assets to copy (Asset Factory pattern)
BASE_PAGE_ASSET_ID = "e179c5267f000101269ba29b4762cdbd"
BASE_FOLDER_ASSET_ID = "fb6b2b757f000101773f7cb12b4b2845"

# Directory filtering rules
# Skip any directory that starts with underscore
SKIP_DIR_PATTERN = "_*"

# File patterns
PAGE_FILE_EXTENSION = ".xml"

# Test mode filters (set to None for full migration)
# Example: TEST_FOLDER_FILTER = "about" to only process about folder and subfolders
TEST_FOLDER_FILTER = None  # Set to folder name for testing, None for full migration
