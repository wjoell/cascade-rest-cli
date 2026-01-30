"""
Scanner module for discovering folders and XML files in the source directory.
"""

import os
from pathlib import Path
from typing import List, Dict, Tuple
from fnmatch import fnmatch
from .config import SOURCE_DIR, SKIP_DIR_PATTERN, PAGE_FILE_EXTENSION, TEST_FOLDER_FILTER


def should_skip_directory(dir_name: str) -> bool:
    """
    Check if a directory should be skipped based on its name.
    
    Args:
        dir_name: Name of the directory (not full path)
        
    Returns:
        True if directory should be skipped (starts with underscore)
    """
    return fnmatch(dir_name, SKIP_DIR_PATTERN)


def scan_folder_structure() -> List[str]:
    """
    Scan the source directory and return a list of folder paths that should be created.
    Skips directories starting with underscore.
    Respects TEST_FOLDER_FILTER if set.
    
    Returns:
        List of relative folder paths (relative to SOURCE_DIR) that should be created
    """
    source_path = Path(SOURCE_DIR)
    folders = []
    
    for root, dirs, files in os.walk(source_path):
        # Filter out directories to skip (modifying dirs in-place affects os.walk traversal)
        dirs[:] = [d for d in dirs if not should_skip_directory(d)]
        
        # Calculate relative path from SOURCE_DIR
        rel_path = Path(root).relative_to(source_path)
        
        # Skip the root directory itself
        if str(rel_path) != ".":
            folder_str = str(rel_path)
            
            # Apply test folder filter if set
            if TEST_FOLDER_FILTER:
                # Only include folders that are the test folder or its subfolders
                if folder_str == TEST_FOLDER_FILTER or folder_str.startswith(TEST_FOLDER_FILTER + "/"):
                    folders.append(folder_str)
            else:
                folders.append(folder_str)
    
    return sorted(folders)


def scan_xml_files() -> List[Dict[str, str]]:
    """
    Scan the source directory and return information about all XML files.
    Respects TEST_FOLDER_FILTER if set.
    
    Returns:
        List of dictionaries with keys:
        - 'xml_path': Full path to XML file
        - 'folder_path': Relative path to containing folder (from SOURCE_DIR)
        - 'page_name': Page asset name (without .xml extension)
        - 'relative_path': Full relative path to XML file (from SOURCE_DIR)
    """
    source_path = Path(SOURCE_DIR)
    xml_files = []
    
    for root, dirs, files in os.walk(source_path):
        # Filter out directories to skip
        dirs[:] = [d for d in dirs if not should_skip_directory(d)]
        
        # Calculate relative path from SOURCE_DIR
        rel_folder = Path(root).relative_to(source_path)
        folder_str = str(rel_folder) if str(rel_folder) != "." else ""
        
        # Apply test folder filter if set
        if TEST_FOLDER_FILTER and folder_str:
            if not (folder_str == TEST_FOLDER_FILTER or folder_str.startswith(TEST_FOLDER_FILTER + "/")):
                continue
        
        # Find XML files
        for file in files:
            if file.endswith(PAGE_FILE_EXTENSION):
                # Remove .xml extension for page name
                page_name = file[:-len(PAGE_FILE_EXTENSION)]
                
                xml_files.append({
                    'xml_path': os.path.join(root, file),
                    'folder_path': folder_str,
                    'page_name': page_name,
                    'relative_path': str(Path(rel_folder) / file) if str(rel_folder) != "." else file
                })
    
    return sorted(xml_files, key=lambda x: x['relative_path'])


def get_migration_summary() -> Tuple[int, int]:
    """
    Get a summary of what will be migrated.
    
    Returns:
        Tuple of (folder_count, page_count)
    """
    folders = scan_folder_structure()
    pages = scan_xml_files()
    return len(folders), len(pages)


if __name__ == "__main__":
    # Test the scanner
    print("Scanning source directory...")
    folder_count, page_count = get_migration_summary()
    print(f"Found {folder_count} folders and {page_count} XML files to migrate")
    
    # Show first few folders
    folders = scan_folder_structure()
    print("\nFirst 10 folders:")
    for folder in folders[:10]:
        print(f"  {folder}")
    
    # Show first few pages
    pages = scan_xml_files()
    print(f"\nFirst 10 pages:")
    for page in pages[:10]:
        print(f"  {page['relative_path']} -> {page['page_name']}")
