"""
Content migration script for migrating HTML from migration-clean files to Cascade pages.

Handles database lookups, API read/write operations, and path mapping.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import glob

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from migration.database import get_db
from migration.content_cleaner import clean_migration_file
from cascade_rest.core import read_single_asset, edit_single_asset


def map_migration_file_to_page_id(migration_file_path: str, source_base_dir: str, db) -> Optional[Tuple[str, str]]:
    """
    Map a migration HTML file to its corresponding Cascade page ID.
    
    Args:
        migration_file_path: Full path to *-migration.html file
        source_base_dir: Base directory for migration source files
        db: Database instance
        
    Returns:
        Tuple of (cascade_id, source_path) if found, None otherwise
    """
    # Get relative path from base directory
    rel_path = os.path.relpath(migration_file_path, source_base_dir)
    
    # Convert path/to/file-migration.html -> path/to/file.xml
    if rel_path.endswith('-migration.html'):
        # Strip -migration.html and add .xml
        base_path = rel_path[:-len('-migration.html')]
        xml_source_path = base_path + '.xml'
        
        # Look up in database
        cascade_id = db.get_page_id(xml_source_path)
        
        if cascade_id:
            return (cascade_id, xml_source_path)
    
    return None


def find_source_content_node(structured_data_nodes: List[Dict]) -> Optional[int]:
    """
    Find the index of the source-content node in structured data nodes list.
    
    Args:
        structured_data_nodes: List of structured data node dictionaries
        
    Returns:
        Index of source-content node, or None if not found
    """
    for idx, node in enumerate(structured_data_nodes):
        if node.get('identifier') == 'source-content':
            return idx
    return None


def update_page_content(
    cascade_id: str,
    cleaned_html: str,
    cms_path: str,
    auth: dict,
    dry_run: bool = False
) -> bool:
    """
    Update the source-content field of a Cascade page with cleaned HTML.
    
    Args:
        cascade_id: Cascade page ID
        cleaned_html: Cleaned HTML content to insert
        cms_path: CMS API path
        auth: Authentication dict
        dry_run: If True, don't actually update (just validate)
        
    Returns:
        True if successful, False otherwise
    """
    # Read current page asset
    result = read_single_asset(cms_path, auth, 'page', cascade_id)
    
    if not result or 'asset' not in result:
        print(f"  ❌ Failed to read page {cascade_id}")
        return False
    
    # Navigate to structured data nodes
    try:
        asset = result['asset']
        page = asset['page']
        structured_data = page.get('structuredData', {})
        sd_nodes = structured_data.get('structuredDataNodes', [])
        
        if not isinstance(sd_nodes, list):
            print(f"  ❌ structuredDataNodes is not a list")
            return False
        
        # Find source-content node
        source_content_idx = find_source_content_node(sd_nodes)
        
        if source_content_idx is None:
            print(f"  ❌ source-content node not found in structured data")
            return False
        
        # Update the text field
        if dry_run:
            current_length = len(sd_nodes[source_content_idx].get('text', ''))
            new_length = len(cleaned_html)
            print(f"  📝 Would update source-content (current: {current_length} bytes → new: {new_length} bytes)")
            return True
        
        sd_nodes[source_content_idx]['text'] = cleaned_html
        
        # Write back the complete asset
        payload = {'asset': asset}
        update_result = edit_single_asset(cms_path, auth, 'page', cascade_id, payload)
        
        if update_result.get('success'):
            print(f"  ✅ Updated source-content")
            return True
        else:
            error_msg = update_result.get('message', 'Unknown error')
            print(f"  ❌ Update failed: {error_msg}")
            return False
            
    except (KeyError, TypeError, IndexError) as e:
        print(f"  ❌ Error navigating asset structure: {e}")
        return False


def migrate_single_file(
    migration_file_path: str,
    source_base_dir: str,
    cms_path: str,
    auth: dict,
    dry_run: bool = False,
    show_cleaned: bool = False
) -> Tuple[bool, str]:
    """
    Migrate a single HTML file to its corresponding Cascade page.
    
    Args:
        migration_file_path: Path to the migration HTML file
        source_base_dir: Base directory for source files
        cms_path: CMS API path
        auth: Authentication dict
        dry_run: If True, don't actually update
        show_cleaned: If True, print cleaned content
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    rel_path = os.path.relpath(migration_file_path, source_base_dir)
    print(f"\n📄 Processing: {rel_path}")
    
    # Get database instance
    db = get_db()
    
    # Map file to page ID
    mapping = map_migration_file_to_page_id(migration_file_path, source_base_dir, db)
    
    if not mapping:
        msg = f"  ⏭️  Skipped: No database entry found"
        print(msg)
        return (False, msg)
    
    cascade_id, source_path = mapping
    print(f"  🔗 Mapped to: {source_path} (ID: {cascade_id})")
    
    # Clean the HTML content
    try:
        cleaned_html = clean_migration_file(migration_file_path)
        print(f"  🧹 Cleaned content: {len(cleaned_html)} bytes")
        
        if show_cleaned:
            print("\n" + "=" * 80)
            print("CLEANED CONTENT:")
            print("=" * 80)
            print(cleaned_html)
            print("=" * 80)
            
    except Exception as e:
        msg = f"  ❌ Error cleaning file: {e}"
        print(msg)
        return (False, msg)
    
    # Update the page content
    success = update_page_content(
        cascade_id=cascade_id,
        cleaned_html=cleaned_html,
        cms_path=cms_path,
        auth=auth,
        dry_run=dry_run
    )
    
    if success:
        action = "Would update" if dry_run else "Updated"
        msg = f"  ✅ {action} successfully"
        return (True, msg)
    else:
        msg = f"  ❌ Update failed"
        return (False, msg)


def migrate_all_files(
    source_base_dir: str,
    cms_path: str,
    auth: dict,
    dry_run: bool = False,
    filter_path: Optional[str] = None
) -> Dict[str, int]:
    """
    Migrate all *-migration.html files in the source directory.
    
    Args:
        source_base_dir: Base directory containing migration files
        cms_path: CMS API path
        auth: Authentication dict
        dry_run: If True, don't actually update
        filter_path: Optional path filter (e.g., "about" to only process about folder)
        
    Returns:
        Dict with counts of total, successful, skipped, and failed migrations
    """
    # Find all migration HTML files
    if filter_path:
        search_pattern = os.path.join(source_base_dir, filter_path, '**', '*-migration.html')
    else:
        search_pattern = os.path.join(source_base_dir, '**', '*-migration.html')
    
    migration_files = glob.glob(search_pattern, recursive=True)
    
    print(f"\n{'=' * 80}")
    print(f"CONTENT MIGRATION {'(DRY RUN)' if dry_run else ''}")
    print(f"{'=' * 80}")
    print(f"Source directory: {source_base_dir}")
    if filter_path:
        print(f"Path filter: {filter_path}")
    print(f"Files found: {len(migration_files)}")
    print(f"{'=' * 80}")
    
    results = {
        'total': len(migration_files),
        'successful': 0,
        'skipped': 0,
        'failed': 0
    }
    
    for migration_file in migration_files:
        success, message = migrate_single_file(
            migration_file_path=migration_file,
            source_base_dir=source_base_dir,
            cms_path=cms_path,
            auth=auth,
            dry_run=dry_run,
            show_cleaned=False
        )
        
        if success:
            results['successful'] += 1
        elif 'Skipped' in message:
            results['skipped'] += 1
        else:
            results['failed'] += 1
    
    # Print summary
    print(f"\n{'=' * 80}")
    print("MIGRATION SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total files: {results['total']}")
    print(f"Successful: {results['successful']}")
    print(f"Skipped: {results['skipped']}")
    print(f"Failed: {results['failed']}")
    print(f"{'=' * 80}\n")
    
    return results


if __name__ == '__main__':
    import argparse
    from session_manager import session_manager
    from migration.config import SOURCE_DIR
    
    parser = argparse.ArgumentParser(description='Migrate content from migration HTML files to Cascade pages')
    parser.add_argument('--file', help='Single file to migrate (relative to source dir)')
    parser.add_argument('--filter', help='Path filter for batch migration (e.g., "about")')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Preview changes without updating (default: True)')
    parser.add_argument('--no-dry-run', dest='dry_run', action='store_false',
                       help='Actually perform the migration')
    parser.add_argument('--show-cleaned', action='store_true',
                       help='Display cleaned content (only with --file)')
    
    args = parser.parse_args()
    
    # Get CMS connection from session
    session = session_manager.get_session()
    
    if not session:
        print("❌ Error: Not connected to Cascade CMS")
        print("Run: python cli.py connect-1password [vault] [item]")
        print("Or: python cli.py setup")
        sys.exit(1)
    
    cms_path = session.get('cms_path')
    api_key = session.get('api_key')
    
    if not cms_path or not api_key:
        print("❌ Error: Invalid session - missing credentials")
        sys.exit(1)
    
    auth = {'apiKey': api_key}
    print(f"✅ Connected to: {cms_path}")
    print()
    
    # Run migration
    if args.file:
        # Single file migration
        file_path = os.path.join(SOURCE_DIR, args.file)
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            sys.exit(1)
        
        success, message = migrate_single_file(
            migration_file_path=file_path,
            source_base_dir=SOURCE_DIR,
            cms_path=cms_path,
            auth=auth,
            dry_run=args.dry_run,
            show_cleaned=args.show_cleaned
        )
        
        sys.exit(0 if success else 1)
    else:
        # Batch migration
        results = migrate_all_files(
            source_base_dir=SOURCE_DIR,
            cms_path=cms_path,
            auth=auth,
            dry_run=args.dry_run,
            filter_path=args.filter
        )
        
        # Exit with error code if any failed
        sys.exit(0 if results['failed'] == 0 else 1)
