"""
Module for creating page assets in Cascade based on source XML files.
"""

from pathlib import Path
from typing import Dict, List
from cascade_rest import core
from cascade_rest.folders import get_folder_child_id_by_name
from .config import TARGET_BASE_FOLDER_ID, BASE_PAGE_ASSET_ID
from .scanner import scan_xml_files, scan_folder_structure
from .database import get_db


def create_pages(auth: Dict[str, str], cms_path: str = None, folder_id_map: Dict[str, str] = None, dry_run: bool = True, use_db: bool = True) -> Dict[str, any]:
    """
    Create page assets in Cascade based on XML files.
    Uses Asset Factory pattern: copies base page asset with new names.
    This creates empty page shells - no content/data population yet.
    
    Args:
        auth: Authentication dictionary for Cascade API
        cms_path: Cascade CMS path (required for non-dry-run)
        folder_id_map: Dictionary mapping folder paths to their Cascade IDs
                      If None, will be loaded from database or built via API
        dry_run: If True, only preview pages to be created without actually creating them
        use_db: If True, check database for existing pages and store created IDs
        
    Returns:
        Dictionary with:
        - 'success': bool
        - 'created': List of created page info
        - 'failed': List of failed pages with error info
        - 'dry_run': bool indicating if this was a dry run
        - 'total': Total number of pages
    """
    xml_files = scan_xml_files()
    
    # Initialize database if enabled
    db = get_db() if use_db and not dry_run else None
    
    result = {
        'success': True,
        'created': [],
        'failed': [],
        'skipped': [],  # Track skipped pages (already in DB)
        'collisions': [],  # Track name collisions
        'dry_run': dry_run,
        'total': len(xml_files)
    }
    
    # Build folder map if not provided
    if folder_id_map is None:
        if not dry_run:
            # Try to load from database first
            if db:
                print("\n📊 Loading folder ID map from database...")
                folder_id_map = db.build_folder_id_map()
                folder_id_map[''] = TARGET_BASE_FOLDER_ID
                print(f"   ✓ Loaded {len(folder_id_map)-1} folders from database")
            else:
                # Fall back to API lookups
                print("\n🔍 Building folder ID map via API...")
                folder_id_map = {'': TARGET_BASE_FOLDER_ID}
                
                # Traverse folder structure to build map
                folders = scan_folder_structure()
                for folder_path in folders:
                    parent_path = str(Path(folder_path).parent)
                    if parent_path == '.':
                        parent_path = ''
                    
                    parent_id = folder_id_map.get(parent_path)
                    if parent_id:
                        folder_name = Path(folder_path).name
                        try:
                            folder_id = get_folder_child_id_by_name(
                                cms_path, auth, parent_id, folder_name
                            )
                            if folder_id:
                                folder_id_map[folder_path] = folder_id
                        except Exception as e:
                            print(f"   ⚠️  Could not get ID for folder '{folder_path}': {e}")
                
                print(f"   ✓ Mapped {len(folder_id_map)} folders")
        else:
            folder_id_map = {'': TARGET_BASE_FOLDER_ID}
    
    if dry_run:
        print(f"[DRY RUN] Would create {len(xml_files)} pages")
        print("\nPage creation preview (first 20):")
        for i, page_info in enumerate(xml_files[:20]):
            folder = page_info['folder_path'] if page_info['folder_path'] else '(root)'
            print(f"  {i+1}. {folder}/{page_info['page_name']}")
        if len(xml_files) > 20:
            print(f"  ... and {len(xml_files) - 20} more pages")
        return result
    
    print(f"Creating {len(xml_files)} pages in Cascade...")
    
    for i, page_info in enumerate(xml_files, 1):
        folder_path = page_info['folder_path']
        page_name = page_info['page_name']
        source_path = f"{folder_path}/{page_name}.xml" if folder_path else f"{page_name}.xml"
        
        # Check if page already exists in database
        if db and db.page_exists(source_path):
            existing_id = db.get_page_id(source_path)
            result['skipped'].append({
                'page': page_name,
                'folder': folder_path,
                'id': existing_id
            })
            display_path = f"{folder_path}/{page_name}" if folder_path else page_name
            print(f"  [{i}/{len(xml_files)}] ⏭️  Skipping (already migrated): {display_path}")
            continue
        
        # Get parent folder ID
        parent_folder_id = folder_id_map.get(folder_path)
        if not parent_folder_id:
            result['failed'].append({
                'page': page_name,
                'folder': folder_path,
                'error': f'Parent folder ID not found: {folder_path}'
            })
            result['success'] = False
            continue
        
        # Display progress
        display_path = f"{folder_path}/{page_name}" if folder_path else page_name
        print(f"  [{i}/{len(xml_files)}] Creating page: {display_path}")
        
        # Copy base page asset with new name (Asset Factory pattern)
        api_result = core.copy_asset_by_id(
            cms_path=cms_path,
            auth=auth,
            asset_type="page",
            asset_id=BASE_PAGE_ASSET_ID,
            destination_folder_id=parent_folder_id,
            new_name=page_name,
        )
        
        # Extract page ID from successful response
        page_result = None
        if api_result and api_result.get("success"):
            # Cascade copy API doesn't return the created asset ID
            # Look it up by reading the parent folder's children
            try:
                created_id = get_folder_child_id_by_name(
                    cms_path, auth, parent_folder_id, page_name
                )
                
                if created_id:
                    page_result = {
                        'id': created_id,
                        'name': page_name
                    }
                else:
                    print(f"   ⚠️  Could not find page '{page_name}' in parent folder")
                    
            except Exception as e:
                print(f"   ✗ Error looking up page ID: {e}")
        
        if page_result:
            page_id = page_result.get('id', 'unknown')
            result['created'].append({
                'page': page_name,
                'folder': folder_path,
                'id': page_id,
                'xml_source': page_info['xml_path']
            })
            
            # Store in database
            if db and page_id != 'unknown':
                db.add_page(
                    source_path=source_path,
                    cascade_id=page_id,
                    folder_path=folder_path if folder_path else None,
                    page_name=page_name,
                    xml_source=page_info['xml_path']
                )
                print(f"   💾 Stored in database")
        else:
            # Check if it's a collision/duplicate
            error_msg = api_result.get('message', 'API call failed') if api_result else 'API call failed'
            is_collision = 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower()
            
            if is_collision:
                result['collisions'].append({
                    'page': page_name,
                    'folder': folder_path,
                    'error': error_msg
                })
                # Don't mark as overall failure for collisions - just skip
                print(f"   ➡️  Skipping (collision): {display_path}")
            else:
                result['failed'].append({
                    'page': page_name,
                    'folder': folder_path,
                    'error': error_msg
                })
                result['success'] = False
    
    print(f"\nPage creation complete!")
    print(f"  Created: {len(result['created'])}")
    print(f"  Failed: {len(result['failed'])}")
    print(f"  Skipped: {len(result['skipped'])}")
    print(f"  Collisions: {len(result['collisions'])}")
    
    return result


if __name__ == "__main__":
    # Test with dry run
    print("Testing page creator (dry run)...")
    result = create_pages({}, dry_run=True)
    print(f"\nDry run complete. Would create {result['total']} pages.")
