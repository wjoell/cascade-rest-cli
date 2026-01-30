"""
Validation module for migration pre-flight checks.
"""

from pathlib import Path
from typing import List, Dict, Tuple
from .scanner import scan_folder_structure, scan_xml_files


def check_name_collisions() -> Dict[str, List[str]]:
    """
    Check for potential name collisions within the same parent folder.
    
    In Cascade, no two assets can have the same name in the same folder,
    regardless of type (folder, page, file, etc.).
    
    Returns:
        Dictionary with:
        - 'collisions': List of collision descriptions
        - 'has_collisions': bool indicating if any collisions exist
    """
    folders = scan_folder_structure()
    pages = scan_xml_files()
    
    collisions = []
    
    # Build a map of parent folder -> list of asset names
    # Key: parent folder path, Value: dict with 'folders' and 'pages' lists
    folder_contents = {}
    
    # Add all folders to the map
    for folder_path in folders:
        parent_path = str(Path(folder_path).parent)
        if parent_path == '.':
            parent_path = ''  # Root level
        
        folder_name = Path(folder_path).name
        
        if parent_path not in folder_contents:
            folder_contents[parent_path] = {'folders': [], 'pages': []}
        
        folder_contents[parent_path]['folders'].append({
            'name': folder_name,
            'path': folder_path
        })
    
    # Add all pages to the map
    for page_info in pages:
        parent_path = page_info['folder_path']
        page_name = page_info['page_name']
        
        if parent_path not in folder_contents:
            folder_contents[parent_path] = {'folders': [], 'pages': []}
        
        folder_contents[parent_path]['pages'].append({
            'name': page_name,
            'path': page_info['relative_path']
        })
    
    # Check each parent folder for collisions
    for parent_path, contents in folder_contents.items():
        folder_names = [f['name'] for f in contents['folders']]
        page_names = [p['name'] for p in contents['pages']]
        
        # Check for duplicate folder names
        seen_folders = set()
        for folder in contents['folders']:
            if folder['name'] in seen_folders:
                location = f"in '{parent_path}'" if parent_path else "at root"
                collisions.append(
                    f"Duplicate folder name: '{folder['name']}' {location}"
                )
            seen_folders.add(folder['name'])
        
        # Check for duplicate page names
        seen_pages = set()
        for page in contents['pages']:
            if page['name'] in seen_pages:
                location = f"in '{parent_path}'" if parent_path else "at root"
                collisions.append(
                    f"Duplicate page name: '{page['name']}' {location}"
                )
            seen_pages.add(page['name'])
        
        # Check for folder/page name collisions
        for folder_name in folder_names:
            if folder_name in page_names:
                location = f"in '{parent_path}'" if parent_path else "at root"
                collisions.append(
                    f"Name collision: '{folder_name}' exists as both folder and page {location}"
                )
    
    return {
        'collisions': collisions,
        'has_collisions': len(collisions) > 0
    }


def validate_migration() -> Dict[str, any]:
    """
    Run all validation checks before migration.
    
    Returns:
        Dictionary with validation results:
        - 'valid': bool indicating if migration can proceed
        - 'errors': List of error messages
        - 'warnings': List of warning messages
    """
    errors = []
    warnings = []
    
    # Check for name collisions
    collision_check = check_name_collisions()
    if collision_check['has_collisions']:
        errors.extend(collision_check['collisions'])
    
    # Add more validation checks here as needed
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }


if __name__ == "__main__":
    # Test validation
    print("Running migration validation...")
    result = validate_migration()
    
    if result['valid']:
        print("✅ Validation passed - no issues found")
    else:
        print(f"❌ Validation failed - {len(result['errors'])} error(s) found:")
        for error in result['errors']:
            print(f"  • {error}")
    
    if result['warnings']:
        print(f"\n⚠️  {len(result['warnings'])} warning(s):")
        for warning in result['warnings']:
            print(f"  • {warning}")
