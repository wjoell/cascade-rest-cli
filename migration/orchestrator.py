"""
Main orchestrator for the migration process.
Coordinates folder creation and page creation.
"""

from typing import Dict
from .scanner import get_migration_summary
from .folder_creator import create_folders
from .page_creator import create_pages


def run_migration(auth: Dict[str, str], cms_path: str = None, dry_run: bool = True, 
                  create_folders_only: bool = False, create_pages_only: bool = False,
                  use_db: bool = True) -> Dict[str, any]:
    """
    Run the full migration process: create folders, then create pages.
    Uses Asset Factory pattern to copy base assets.
    
    Args:
        auth: Authentication dictionary for Cascade API
        cms_path: Cascade CMS path (required for non-dry-run)
        dry_run: If True, preview actions without executing
        create_folders_only: If True, only create folders (skip pages)
        create_pages_only: If True, only create pages (assumes folders exist)
        use_db: If True, use database for tracking and skip checking
        
    Returns:
        Dictionary with results from both phases
    """
    print("=" * 80)
    print("MIGRATION ORCHESTRATOR")
    print("=" * 80)
    
    # Get summary
    folder_count, page_count = get_migration_summary()
    print(f"\nMigration scope:")
    print(f"  - Folders to create: {folder_count}")
    print(f"  - Pages to create: {page_count}")
    print(f"  - Mode: {'DRY RUN' if dry_run else 'LIVE EXECUTION'}")
    print()
    
    result = {
        'folders': None,
        'pages': None,
        'dry_run': dry_run
    }
    
    # Phase 1: Create folders
    if not create_pages_only:
        print("\n" + "=" * 80)
        print("PHASE 1: FOLDER CREATION")
        print("=" * 80)
        folder_result = create_folders(auth, cms_path=cms_path, dry_run=dry_run, use_db=use_db)
        result['folders'] = folder_result
        
        if not dry_run and not folder_result['success']:
            print("\n⚠️  Folder creation encountered errors. Stopping before page creation.")
            return result
        
        if create_folders_only:
            print("\n✓ Folder creation complete (folders-only mode)")
            return result
    
    # Phase 2: Create pages
    if not create_folders_only:
        print("\n" + "=" * 80)
        print("PHASE 2: PAGE CREATION")
        print("=" * 80)
        
        # Get folder ID map from folder creation result
        folder_id_map = None
        if result['folders'] and not dry_run:
            # Database will provide folder ID map automatically in page_creator
            pass
        
        page_result = create_pages(auth, cms_path=cms_path, folder_id_map=folder_id_map, dry_run=dry_run, use_db=use_db)
        result['pages'] = page_result
    
    # Summary
    print("\n" + "=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)
    
    if result['folders']:
        print(f"\nFolders:")
        print(f"  Total: {result['folders']['total']}")
        if not dry_run:
            print(f"  Created: {len(result['folders']['created'])}")
            print(f"  Skipped: {len(result['folders'].get('skipped', []))}")
            print(f"  Failed: {len(result['folders']['failed'])}")
            print(f"  Collisions: {len(result['folders'].get('collisions', []))}")
    
    if result['pages']:
        print(f"\nPages:")
        print(f"  Total: {result['pages']['total']}")
        if not dry_run:
            print(f"  Created: {len(result['pages']['created'])}")
            print(f"  Skipped: {len(result['pages'].get('skipped', []))}")
            print(f"  Failed: {len(result['pages']['failed'])}")
            print(f"  Collisions: {len(result['pages'].get('collisions', []))}")
    
    print()
    return result


if __name__ == "__main__":
    # Test orchestrator with dry run
    print("Testing migration orchestrator...")
    result = run_migration({}, dry_run=True)
