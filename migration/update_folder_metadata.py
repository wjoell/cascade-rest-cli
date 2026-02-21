"""
Update folder metadata via Cascade REST API.

Reads folder metadata from CSV and updates destination folders with:
- display_name (wired metadata)
- include-sitemaps (dynamic metadata)
- left-nav-include (dynamic metadata)
"""

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cascade_rest.core import read_single_asset, edit_single_asset
from secrets_manager import secrets_manager


# Paths
CSV_PATH = "/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/folder_metadata.csv"
LOG_DIR = "/Users/winston/Repositories/wjoell/slc-edu-migration/logs"


class FolderUpdateLogger:
    """Logger for folder update operations."""
    
    def __init__(self, log_path: str):
        self.log_path = log_path
        self.entries = []
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        # Write header
        with open(log_path, 'w', encoding='utf-8') as f:
            header = {
                'type': 'folder_update_log_header',
                'started': datetime.now(timezone.utc).isoformat(),
                'version': '1.0'
            }
            f.write(json.dumps(header) + '\n')
    
    def log(self, folder_path: str, folder_id: str, status: str, 
            message: str = None, changes: Dict = None):
        """Log a folder update operation."""
        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'folder_path': folder_path,
            'folder_id': folder_id,
            'status': status,  # SUCCESS, ERROR, SKIPPED, NO_CHANGES
            'message': message,
            'changes': changes
        }
        self.entries.append(entry)
        
        # Append to log file
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
        
        # Print status
        icon = {'SUCCESS': '✅', 'ERROR': '❌', 'SKIPPED': '⏭️', 'NO_CHANGES': '➖'}.get(status, '❓')
        print(f"  {icon} {folder_path}: {status}" + (f" - {message}" if message else ""))
    
    def get_summary(self) -> Dict:
        """Get summary statistics."""
        stats = {'SUCCESS': 0, 'ERROR': 0, 'SKIPPED': 0, 'NO_CHANGES': 0}
        for entry in self.entries:
            stats[entry['status']] = stats.get(entry['status'], 0) + 1
        return stats


def get_auth():
    """Get authentication credentials from 1Password."""
    print("🔑 Fetching credentials from 1Password...")
    creds = secrets_manager.get_from_1password(
        'Cascade REST Development Production', 'Cascade Rest API Production'
    )
    
    if not creds:
        raise RuntimeError("Failed to fetch credentials from 1Password")
    
    auth = {'apiKey': creds.get('api_key')} if creds.get('api_key') else {
        'u': creds.get('username'), 'p': creds.get('password')
    }
    
    return creds['cms_path'], auth


def load_folder_metadata(csv_path: str) -> Dict[str, Dict]:
    """Load folder metadata from CSV, keyed by folder ID."""
    folders = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['id']:  # Only include rows with IDs
                folders[row['id']] = {
                    'path': row['path'],
                    'name': row['name'],
                    'display_name': row['display_name'],
                    'include_sitemaps': row['include_sitemaps'],
                    'left_nav_include': row['left_nav_include']
                }
    
    return folders


def find_dynamic_field(dynamic_fields: List[Dict], field_name: str) -> Optional[Dict]:
    """Find a dynamic field by name in the dynamicFields array."""
    for field in dynamic_fields:
        if field.get('name') == field_name:
            return field
    return None


def update_dynamic_field(dynamic_fields: List[Dict], field_name: str, value: str):
    """Update or create a dynamic field value."""
    field = find_dynamic_field(dynamic_fields, field_name)
    
    if field:
        # Update existing field
        field['fieldValues'] = [{'value': value}] if value else []
    else:
        # Add new field (shouldn't happen if metadata set is correct)
        dynamic_fields.append({
            'name': field_name,
            'fieldValues': [{'value': value}] if value else []
        })


def get_dynamic_field_value(dynamic_fields: List[Dict], field_name: str) -> str:
    """Get the current value of a dynamic field."""
    field = find_dynamic_field(dynamic_fields, field_name)
    if field and field.get('fieldValues'):
        return field['fieldValues'][0].get('value', '')
    return ''


def update_single_folder(cms_path: str, auth: Dict, folder_id: str, 
                         csv_data: Dict, logger: FolderUpdateLogger,
                         dry_run: bool = False) -> bool:
    """
    Update a single folder's metadata.
    
    Returns True if successful or no changes needed.
    """
    folder_path = csv_data['path']
    
    # Read current folder state
    result = read_single_asset(cms_path, auth, 'folder', folder_id)
    
    if not result or not result.get('success'):
        logger.log(folder_path, folder_id, 'ERROR', 'Failed to read folder')
        return False
    
    folder = result['asset']['folder']
    metadata = folder.get('metadata', {})
    dynamic_fields = metadata.get('dynamicFields', [])
    
    # Track changes
    changes = {}
    
    # Check display_name
    current_display = metadata.get('displayName', '')
    new_display = csv_data['display_name']
    if current_display != new_display:
        changes['displayName'] = {'from': current_display, 'to': new_display}
        metadata['displayName'] = new_display
    
    # Check include-sitemaps
    current_sitemaps = get_dynamic_field_value(dynamic_fields, 'include-sitemaps')
    new_sitemaps = csv_data['include_sitemaps']
    if current_sitemaps != new_sitemaps:
        changes['include-sitemaps'] = {'from': current_sitemaps, 'to': new_sitemaps}
        update_dynamic_field(dynamic_fields, 'include-sitemaps', new_sitemaps)
    
    # Check left-nav-include
    current_nav = get_dynamic_field_value(dynamic_fields, 'left-nav-include')
    new_nav = csv_data['left_nav_include']
    if current_nav != new_nav:
        changes['left-nav-include'] = {'from': current_nav, 'to': new_nav}
        update_dynamic_field(dynamic_fields, 'left-nav-include', new_nav)
    
    # No changes needed
    if not changes:
        logger.log(folder_path, folder_id, 'NO_CHANGES')
        return True
    
    # Dry run - don't actually update
    if dry_run:
        logger.log(folder_path, folder_id, 'SKIPPED', 'Dry run', changes)
        return True
    
    # Build update payload - send entire folder object
    payload = {'asset': {'folder': folder}}
    
    # Send update
    update_result = edit_single_asset(cms_path, auth, 'folder', folder_id, payload)
    
    if update_result.get('success'):
        logger.log(folder_path, folder_id, 'SUCCESS', None, changes)
        return True
    else:
        error_msg = update_result.get('message', 'Unknown error')
        logger.log(folder_path, folder_id, 'ERROR', error_msg, changes)
        return False


def update_all_folders(dry_run: bool = False):
    """Update all folders from CSV."""
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    log_path = f"{LOG_DIR}/folder-update-{timestamp}.jsonl"
    
    print("=" * 60)
    print("FOLDER METADATA UPDATE")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print()
    
    # Get auth
    cms_path, auth = get_auth()
    print(f"✅ Connected to {cms_path}")
    
    # Load CSV data
    folders = load_folder_metadata(CSV_PATH)
    print(f"📄 Loaded {len(folders)} folders with IDs from CSV")
    print(f"📋 Log file: {log_path}")
    print()
    
    # Initialize logger
    logger = FolderUpdateLogger(log_path)
    
    # Process each folder
    print("Processing folders...")
    for folder_id, csv_data in folders.items():
        update_single_folder(cms_path, auth, folder_id, csv_data, logger, dry_run)
    
    # Summary
    summary = logger.get_summary()
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Success:    {summary.get('SUCCESS', 0)}")
    print(f"  No changes: {summary.get('NO_CHANGES', 0)}")
    print(f"  Skipped:    {summary.get('SKIPPED', 0)}")
    print(f"  Errors:     {summary.get('ERROR', 0)}")
    print(f"\n📋 Log: {log_path}")


def update_single_by_id(folder_id: str, dry_run: bool = False):
    """Update a single folder by ID (for testing)."""
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    log_path = f"{LOG_DIR}/folder-update-single-{timestamp}.jsonl"
    
    print("=" * 60)
    print("SINGLE FOLDER UPDATE")
    print("=" * 60)
    print(f"Folder ID: {folder_id}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print()
    
    # Get auth
    cms_path, auth = get_auth()
    print(f"✅ Connected to {cms_path}")
    
    # Load CSV data
    folders = load_folder_metadata(CSV_PATH)
    
    if folder_id not in folders:
        print(f"❌ Folder ID {folder_id} not found in CSV")
        return False
    
    csv_data = folders[folder_id]
    print(f"📄 CSV data for {csv_data['path']}:")
    print(f"   display_name: {csv_data['display_name']}")
    print(f"   include_sitemaps: {csv_data['include_sitemaps']}")
    print(f"   left_nav_include: {csv_data['left_nav_include']}")
    print()
    
    # Initialize logger
    logger = FolderUpdateLogger(log_path)
    
    # Update
    result = update_single_folder(cms_path, auth, folder_id, csv_data, logger, dry_run)
    
    print(f"\n📋 Log: {log_path}")
    return result


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Update folder metadata from CSV')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without updating')
    parser.add_argument('--folder-id', type=str, help='Update single folder by ID')
    
    args = parser.parse_args()
    
    if args.folder_id:
        update_single_by_id(args.folder_id, dry_run=args.dry_run)
    else:
        update_all_folders(dry_run=args.dry_run)
