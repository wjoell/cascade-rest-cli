"""
Module for creating folder structure in Cascade based on source directory.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from cascade_rest import core
from cascade_rest.folders import get_folder_child_id_by_name
from .config import TARGET_BASE_FOLDER_ID, BASE_FOLDER_ASSET_ID
from .scanner import scan_folder_structure
from .database import get_db


def create_folders(auth: Dict[str, str], cms_path: str = None, dry_run: bool = True, use_db: bool = True) -> Dict[str, any]:
    """
    Create all folders from the source directory in the target Cascade location.
    Uses Asset Factory pattern: copies base folder asset with new names.
    
    Args:
        auth: Authentication dictionary for Cascade API
        cms_path: Cascade CMS path (required for non-dry-run)
        dry_run: If True, only preview folders to be created without actually creating them
        use_db: If True, check database for existing folders and store created IDs
        
    Returns:
        Dictionary with:
        - 'success': bool
        - 'created': List of created folder paths
        - 'failed': List of failed folder paths with error info
        - 'skipped': List of folders skipped (already exist)
        - 'dry_run': bool indicating if this was a dry run
    """
    folders = scan_folder_structure()
    
    # Initialize database if enabled
    db = get_db() if use_db and not dry_run else None
    
    result = {
        'success': True,
        'created': [],
        'failed': [],
        'skipped': [],
        'collisions': [],  # Track name collisions
        'dry_run': dry_run,
        'total': len(folders)
    }
    
    if dry_run:
        print(f"[DRY RUN] Would create {len(folders)} folders")
        print("\nFolder structure preview (first 20):")
        for i, folder in enumerate(folders[:20]):
            print(f"  {i+1}. {folder}")
        if len(folders) > 20:
            print(f"  ... and {len(folders) - 20} more folders")
        return result
    
    print(f"Creating {len(folders)} folders in Cascade...")
    
    # Track created folder IDs for parent references
    # Load existing IDs from database if available
    if db:
        print("📊 Loading existing folders from database...")
        folder_id_map = db.build_folder_id_map()
        folder_id_map[''] = TARGET_BASE_FOLDER_ID  # Ensure root is present
        print(f"   ✓ Loaded {len(folder_id_map)-1} existing folders")
    else:
        folder_id_map = {
            '': TARGET_BASE_FOLDER_ID  # Root maps to base folder
        }
    
    for i, folder_path in enumerate(folders, 1):
        # Determine parent folder
        parent_path = str(Path(folder_path).parent)
        if parent_path == '.':
            parent_path = ''
        
        parent_id = folder_id_map.get(parent_path)
        if not parent_id:
            result['failed'].append({
                'path': folder_path,
                'error': f'Parent folder not found: {parent_path}'
            })
            result['success'] = False
            continue
        
        # Get folder name (last component of path)
        folder_name = Path(folder_path).name
        
        # Check if folder already exists in database
        if db and db.folder_exists(folder_path):
            existing_id = db.get_folder_id(folder_path)
            folder_id_map[folder_path] = existing_id
            result['skipped'].append(folder_path)
            print(f"  [{i}/{len(folders)}] ⏭️  Skipping (already migrated): {folder_path}")
            continue
        
        # Copy base folder asset with new name (Asset Factory pattern)
        print(f"  [{i}/{len(folders)}] Creating folder: {folder_path}")
        
        api_result = core.copy_asset_by_id(
            cms_path=cms_path,
            auth=auth,
            asset_type="folder",
            asset_id=BASE_FOLDER_ASSET_ID,
            destination_folder_id=parent_id,
            new_name=folder_name,
        )
        
        # Extract folder ID from successful response
        folder_result = None
        if api_result and api_result.get("success"):
            # Cascade copy API doesn't return the created asset ID
            # We need to look it up by reading the parent folder's children
            print(f"   🔍 Looking up folder ID...")
            
            try:
                created_id = get_folder_child_id_by_name(
                    cms_path, auth, parent_id, folder_name
                )
                
                if created_id:
                    print(f"   ✓ Found folder ID: {created_id}")
                else:
                    print(f"   ✗ Could not find folder '{folder_name}' in parent")
                    
            except Exception as e:
                print(f"   ✗ Error looking up folder ID: {e}")
                created_id = None
            
            folder_result = {
                'id': created_id,
                'name': folder_name
            }
        
        if folder_result:
            folder_id = folder_result.get('id', 'unknown')
            result['created'].append(folder_path)
            folder_id_map[folder_path] = folder_id
            
            # Store in database
            if db and folder_id != 'unknown':
                db.add_folder(
                    source_path=folder_path,
                    cascade_id=folder_id,
                    parent_path=parent_path if parent_path else None,
                    folder_name=folder_name
                )
                print(f"   💾 Stored in database")
        else:
            # Check if it's a collision/duplicate
            error_msg = api_result.get('message', 'API call failed') if api_result else 'API call failed'
            is_collision = 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower()
            
            if is_collision:
                result['collisions'].append({
                    'path': folder_path,
                    'error': error_msg
                })
                # Don't mark as overall failure for collisions - just skip
                print(f"   ➡️  Skipping (collision): {folder_path}")
            else:
                result['failed'].append({
                    'path': folder_path,
                    'error': error_msg
                })
                result['success'] = False
    
    print(f"\nFolder creation complete!")
    print(f"  Created: {len(result['created'])}")
    print(f"  Failed: {len(result['failed'])}")
    print(f"  Collisions: {len(result['collisions'])}")
    print(f"  Skipped: {len(result['skipped'])}")
    
    return result


if __name__ == "__main__":
    # Test with dry run
    print("Testing folder creator (dry run)...")
    result = create_folders({}, dry_run=True)
    print(f"\nDry run complete. Would create {result['total']} folders.")
