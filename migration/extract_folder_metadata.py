"""
Extract folder metadata from origin page XML files.

Scans all origin XML files and extracts the nearest ancestor folder's metadata.
Deduplicates by folder path and outputs a CSV for the REST API migration step.
"""

import csv
import os
from pathlib import Path
from xml.etree import ElementTree as ET
from typing import Dict, List, Optional


# Source directory containing origin XML files
SOURCE_DIR = "/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/migration-clean"

# Output CSV path
OUTPUT_CSV = "/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/folder_metadata.csv"


def get_dynamic_metadata_value(folder_elem: ET.Element, field_name: str) -> str:
    """Extract a dynamic metadata field value from a folder element."""
    for dm in folder_elem.findall('dynamic-metadata'):
        name_elem = dm.find('name')
        if name_elem is not None and name_elem.text == field_name:
            value_elem = dm.find('value')
            return value_elem.text if value_elem is not None and value_elem.text else ''
    return ''


def extract_folder_metadata(xml_path: str) -> List[Dict]:
    """
    Extract ALL ancestor folders' metadata from an origin XML file.
    
    Returns list of dicts with folder metadata (excluding root).
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"  ⚠️  XML parse error in {xml_path}: {e}")
        return []
    
    # Find all system-folder elements
    folders = root.findall('.//system-folder')
    if not folders:
        return []
    
    results = []
    
    for folder in folders:
        # Extract path
        path_elem = folder.find('path')
        folder_path = path_elem.text if path_elem is not None else ''
        
        # Skip root folder (path is "//" or "/")
        if folder_path in ['//', '/', '']:
            continue
        
        # Extract metadata
        name_elem = folder.find('name')
        display_name_elem = folder.find('display-name')
        
        results.append({
            'path': folder_path,
            'name': name_elem.text if name_elem is not None else '',
            'display_name': display_name_elem.text if display_name_elem is not None else '',
            'include_sitemaps': get_dynamic_metadata_value(folder, 'include-sitemaps'),
            'left_nav_include': get_dynamic_metadata_value(folder, 'left-nav-include'),
            'id': ''  # Empty for database lookup later
        })
    
    return results


def scan_all_folders(source_dir: str) -> Dict[str, Dict]:
    """
    Scan all XML files and collect unique folder metadata.
    
    Returns dict keyed by folder path for deduplication.
    """
    folders = {}
    
    source_path = Path(source_dir)
    xml_files = list(source_path.rglob('*.xml'))
    
    print(f"Scanning {len(xml_files)} XML files...")
    
    for xml_file in xml_files:
        # Skip destination files
        if '-destination' in xml_file.name:
            continue
        
        folder_list = extract_folder_metadata(str(xml_file))
        for folder_meta in folder_list:
            path = folder_meta['path']
            if path not in folders:
                folders[path] = folder_meta
    
    return folders


def write_csv(folders: Dict[str, Dict], output_path: str):
    """Write folder metadata to CSV."""
    # Sort by path for readability
    sorted_folders = sorted(folders.values(), key=lambda f: f['path'])
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Header
        writer.writerow(['path', 'name', 'display_name', 'include_sitemaps', 'left_nav_include', 'id'])
        
        # Data rows
        for folder in sorted_folders:
            writer.writerow([
                folder['path'],
                folder['name'],
                folder['display_name'],
                folder['include_sitemaps'],
                folder['left_nav_include'],
                folder['id']
            ])
    
    return len(sorted_folders)


def main():
    print("=" * 60)
    print("FOLDER METADATA EXTRACTION")
    print("=" * 60)
    print()
    
    # Scan all XML files
    folders = scan_all_folders(SOURCE_DIR)
    
    print(f"\nFound {len(folders)} unique folders")
    
    # Write CSV
    count = write_csv(folders, OUTPUT_CSV)
    
    print(f"\n✅ Wrote {count} folders to: {OUTPUT_CSV}")
    
    # Preview first few rows
    print("\nPreview (first 10 rows):")
    print("-" * 80)
    sorted_folders = sorted(folders.values(), key=lambda f: f['path'])[:10]
    for f in sorted_folders:
        print(f"  {f['path']}")
        print(f"    display_name: {f['display_name']}")
        print(f"    include_sitemaps: {f['include_sitemaps']}, left_nav_include: {f['left_nav_include']}")


if __name__ == '__main__':
    main()
