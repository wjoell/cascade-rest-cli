"""
Create link asset folders and symlinks in Cascade CMS.

Uses the link_asset_structure.csv to create:
1. Folders for each domain (with provided asset IDs)
2. Symlink assets within each folder pointing to external URLs

Requires:
- link_asset_structure.csv
- Asset IDs for parent folders (provided via command line or config)
"""

import csv
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cascade_rest import core, folders
from cascade_rest.folders import get_folder_child_id_by_name
from typing import Dict, List, Optional
from migration.database import get_db


# Parent folder ID for link assets (to be provided)
LINK_ASSETS_PARENT_ID = None  # Will be set via command line

# Site name
SITE_NAME = "SarahLawrence.edu"


def load_link_structure(csv_file: str) -> Dict[str, List[Dict]]:
    """
    Load link structure from CSV grouped by folder.
    
    Returns:
        Dict mapping folder_name to list of link dicts
    """
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        links = list(reader)
    
    # Group by folder
    by_folder = {}
    for link in links:
        folder = link['folder_name']
        if folder not in by_folder:
            by_folder[folder] = []
        by_folder[folder].append(link)
    
    return by_folder


def create_folder(folder_name: str, parent_id: str, base_folder_id: str,
                  auth: Dict, cms_path: str, *, log_to_db: bool = True) -> Optional[str]:
    """
    Create a folder by copying a base folder template.
    
    Returns:
        Folder ID if successful, None otherwise
    """
    print(f"  Creating folder: {folder_name}")

    # If folder already exists under parent, return its ID
    try:
        existing_id = get_folder_child_id_by_name(cms_path, auth, parent_id, folder_name)
    except Exception:
        existing_id = ""
    if existing_id:
        print(f"   ⏭️  Exists (ID: {existing_id})")
        if log_to_db:
            db = get_db()
            db.add_folder(
                source_path=f"link-assets/{folder_name}",
                cascade_id=existing_id,
                parent_path="link-assets",
                folder_name=folder_name,
            )
        return existing_id

    # Copy the base folder to create new folder
    result = core.copy_asset_by_id(
        cms_path=cms_path,
        auth=auth,
        asset_type="folder",
        asset_id=base_folder_id,
        destination_folder_id=parent_id,
        new_name=folder_name,
    )

    if result and result.get("success"):
        # Copy API doesn't return the new ID; look it up under the parent by name
        try:
            folder_id = get_folder_child_id_by_name(cms_path, auth, parent_id, folder_name)
        except Exception:
            folder_id = ""
        if folder_id:
            print(f"    ✅ Created folder with ID: {folder_id}")
            if log_to_db:
                db = get_db()
                db.add_folder(
                    source_path=f"link-assets/{folder_name}",
                    cascade_id=folder_id,
                    parent_path="link-assets",
                    folder_name=folder_name,
                )
            return folder_id

    print(f"    ❌ Failed to create folder")
    return None


def create_symlink(link_name: str, url: str, folder_id: str, base_symlink_id: str,
                   auth: Dict, cms_path: str, title: str = '', *, folder_name: Optional[str] = None,
                   log_to_db: bool = True) -> Optional[str]:
    """
    Create a symlink asset by copying a base symlink and updating it.
    
    Returns:
        New symlink ID if successful, None otherwise
    """
    # Step 0: If it already exists in the folder, update in place (idempotent)
    try:
        existing_id = get_folder_child_id_by_name(cms_path, auth, folder_id, link_name)
    except Exception:
        existing_id = ""

    if existing_id:
        # Read and update existing symlink
        read_result = core.read_single_asset(cms_path, auth, 'symlink', existing_id)
        if not read_result or not read_result.get('success'):
            return None
        symlink_data = read_result['asset']['symlink']
        symlink_data['linkURL'] = url
        symlink_data['name'] = link_name
        if title:
            symlink_data['metadata']['title'] = title
            symlink_data['metadata']['displayName'] = title
        edit_payload = {"asset": {"symlink": symlink_data}}
        edit_result = core.edit_single_asset(
            cms_path=cms_path,
            auth=auth,
            asset_type="symlink",
            asset_id=existing_id,
            payload=edit_payload,
        )
        if edit_result.get('success'):
            # Log to DB if requested
            if log_to_db and folder_name:
                db = get_db()
                db.add_link(
                    source_key=f"link-assets/{folder_name}/{link_name}",
                    cascade_id=existing_id,
                    folder_name=folder_name,
                    link_name=link_name,
                    url=url,
                    title=title or None,
                )
            return existing_id
        return None

    # Step 1: Copy the base symlink to the target folder
    copy_result = core.copy_asset_by_id(
        cms_path=cms_path,
        auth=auth,
        asset_type="symlink",
        asset_id=base_symlink_id,
        destination_folder_id=folder_id,
        new_name=link_name,
    )

    if not copy_result or not copy_result.get('success'):
        # If name collision reported despite pre-check (race), fall back to updating existing
        msg = (copy_result or {}).get('message', '')
        if isinstance(msg, str) and ('already exists' in msg.lower() or 'duplicate' in msg.lower()):
            try:
                new_id = get_folder_child_id_by_name(cms_path, auth, folder_id, link_name)
            except Exception:
                new_id = ""
            if not new_id:
                return None
            # Update existing
            read_result = core.read_single_asset(cms_path, auth, 'symlink', new_id)
            if not read_result or not read_result.get('success'):
                return None
            symlink_data = read_result['asset']['symlink']
            symlink_data['linkURL'] = url
            symlink_data['name'] = link_name
            if title:
                symlink_data['metadata']['title'] = title
                symlink_data['metadata']['displayName'] = title
            edit_payload = {"asset": {"symlink": symlink_data}}
            edit_result = core.edit_single_asset(
                cms_path=cms_path,
                auth=auth,
                asset_type="symlink",
                asset_id=new_id,
                payload=edit_payload,
            )
            if edit_result.get('success'):
                if log_to_db and folder_name:
                    db = get_db()
                    db.add_link(
                        source_key=f"link-assets/{folder_name}/{link_name}",
                        cascade_id=new_id,
                        folder_name=folder_name,
                        link_name=link_name,
                        url=url,
                        title=title or None,
                    )
                return new_id
            return None
        return None

    # Copy API doesn't return created ID; look it up in the parent folder by name
    try:
        new_id = get_folder_child_id_by_name(cms_path, auth, folder_id, link_name)
    except Exception:
        new_id = ""
    if not new_id:
        return None

    # Step 2: Read the newly created symlink
    read_result = core.read_single_asset(cms_path, auth, 'symlink', new_id)
    
    if not read_result or not read_result.get('success'):
        return None
    
    symlink_data = read_result['asset']['symlink']
    
    # Step 3: Update the symlink with the correct URL and metadata
    symlink_data['linkURL'] = url
    symlink_data['name'] = link_name
    
    # Update metadata
    if title:
        symlink_data['metadata']['title'] = title
        symlink_data['metadata']['displayName'] = title
    
    # Step 4: Write back the updated symlink
    edit_payload = {"asset": {"symlink": symlink_data}}
    edit_result = core.edit_single_asset(
        cms_path=cms_path,
        auth=auth,
        asset_type="symlink",
        asset_id=new_id,
        payload=edit_payload
    )
    
    if edit_result.get('success'):
        # Log to DB if requested
        if log_to_db and folder_name:
            db = get_db()
            db.add_link(
                source_key=f"link-assets/{folder_name}/{link_name}",
                cascade_id=new_id,
                folder_name=folder_name,
                link_name=link_name,
                url=url,
                title=title or None,
            )
        return new_id
    else:
        return None


def create_all_link_assets(structure_file: str, parent_folder_id: str, 
                           base_folder_id: str, base_symlink_id: str, 
                           auth: Dict, cms_path: str, 
                           priority_filter: str = 'ALL', dry_run: bool = False,
                           folders_only: bool = False, links_only: bool = False,
                           use_db: bool = True, report_duplicates: bool = False,
                           dedupe: bool = False):
    """
    Create all link asset folders and symlinks.
    
    Args:
        structure_file: Path to link_asset_structure.csv
        parent_folder_id: Parent folder ID for link assets section
        base_folder_id: ID of base folder to copy for creating domain folders
        base_symlink_id: ID of base symlink to copy for creating new links
        auth: Cascade authentication
        cms_path: Cascade CMS path
        priority_filter: Create only 'HIGH', 'MEDIUM', or 'ALL' priority links
        dry_run: If True, only print what would be created
    """
    print(f"\n{'=' * 80}")
    print("CREATING LINK ASSETS IN CASCADE CMS")
    print(f"{'=' * 80}\n")
    
    if dry_run:
        print("🔍 DRY RUN MODE - No assets will be created\n")
    
    # Load structure
    print(f"Loading link structure from: {structure_file}")
    by_folder = load_link_structure(structure_file)
    
    # Filter by priority
    if priority_filter != 'ALL':
        filtered = {}
        for folder, links in by_folder.items():
            folder_links = [l for l in links if l['priority'] == priority_filter]
            if folder_links:
                filtered[folder] = folder_links
        by_folder = filtered
    
    total_folders = len(by_folder)
    total_links = sum(len(links) for links in by_folder.values())
    
    print(f"Found {total_folders} folders with {total_links} total links")
    if priority_filter != 'ALL':
        print(f"Filter: {priority_filter} priority only")
    if folders_only:
        print("Mode: FOLDERS ONLY")
    if links_only:
        print("Mode: LINKS ONLY")
    print()
    
    # Optional DB
    db = get_db() if use_db and not dry_run else None

    # In report-only mode, just scan for duplicates and exit
    if report_duplicates and not dry_run:
        print("Running duplicate name audit (no changes)...")
        import re
        dup_total = 0
        for folder_name in sorted(by_folder.keys()):
            # Resolve folder ID
            folder_id = None
            if db:
                recs = [r for r in db.get_folders_in_path('link-assets') if r['folder_name'] == folder_name]
                if recs:
                    folder_id = recs[0]['cascade_id']
            if not folder_id:
                try:
                    folder_id = get_folder_child_id_by_name(cms_path, auth, parent_folder_id, folder_name)
                except Exception:
                    folder_id = None
            if not folder_id:
                continue
            # Load children
            try:
                children = folders.get_folder_children(cms_path, auth, folder_id)
            except Exception:
                continue
            names = [c['path']['path'].split('/')[-1] for c in children if c.get('type') == 'symlink']
            name_set = set(names)
            dups = []
            for n in names:
                m = re.match(r"^(.*?)(\d+)$", n)
                if m:
                    base = m.group(1)
                    if base in name_set:
                        dups.append((n, base))
            if dups:
                dup_total += len(dups)
                print(f"- {folder_name}: {len(dups)} duplicates (e.g., {', '.join(x for x,_ in dups[:5])})")
        if dup_total == 0:
            print("No duplicate name patterns detected.")
        else:
            print(f"\nTotal duplicate-named assets detected: {dup_total}")
        return

    if dedupe:
        print("\nRunning duplicate cleanup (removing numbered duplicates)...")
        import re
        removed = 0
        planned = 0
        for folder_name in sorted(by_folder.keys()):
            # Resolve folder ID
            folder_id = None
            if db:
                recs = [r for r in db.get_folders_in_path('link-assets') if r['folder_name'] == folder_name]
                if recs:
                    folder_id = recs[0]['cascade_id']
            if not folder_id:
                try:
                    folder_id = get_folder_child_id_by_name(cms_path, auth, parent_folder_id, folder_name)
                except Exception:
                    folder_id = None
            if not folder_id:
                continue
            # Load children
            try:
                children = folders.get_folder_children(cms_path, auth, folder_id)
            except Exception:
                continue
            # Build mapping
            by_name = {c['path']['path'].split('/')[-1]: c for c in children if c.get('type') == 'symlink'}
            name_set = set(by_name.keys())
            to_delete = []
            for name in list(name_set):
                m = re.match(r"^(.*?)(\d+)$", name)
                if not m:
                    continue
                base = m.group(1)
                if base in name_set:
                    to_delete.append(by_name[name]['id'])
            if to_delete:
                action = "Would delete" if dry_run else "Deleting"
                print(f"- {folder_name}: {action} {len(to_delete)} duplicates")
                for asset_id in to_delete:
                    if dry_run:
                        planned += 1
                    else:
                        core.delete_asset(cms_path, auth, 'symlink', asset_id, unpublish=True)
                        removed += 1
        if dry_run:
            print(f"Done. Would remove {planned} duplicate assets.")
        else:
            print(f"Done. Removed {removed} duplicate assets.")
        return

    # Track created folders
    folder_ids = {}
    created_folders = 0
    created_links = 0
    failed_links = 0
    
    # Create folders and symlinks
    for folder_name in sorted(by_folder.keys()):
        links = by_folder[folder_name]
        domain = links[0]['domain']
        priority = links[0]['priority']
        
        print(f"\n📁 [{priority}] {folder_name}/ ({domain})")
        print(f"   {len(links)} links to create")
        
        if dry_run:
            print(f"   Would create folder under parent ID: {parent_folder_id}")
        else:
            # Create or look up folder
            if not links_only:
                folder_id = create_folder(
                    folder_name, parent_folder_id, base_folder_id, auth, cms_path,
                    log_to_db=bool(db)
                )
            else:
                # Links-only mode: resolve folder from DB or API without creating
                folder_id = None
                # Try DB first
                if db:
                    recs = [r for r in db.get_folders_in_path('link-assets') if r['folder_name'] == folder_name]
                    if recs:
                        folder_id = recs[0]['cascade_id']
                # Fallback to API lookup under parent
                if not folder_id:
                    try:
                        folder_id = get_folder_child_id_by_name(cms_path, auth, parent_folder_id, folder_name)
                    except Exception:
                        folder_id = None

            if not folder_id:
                print(f"   ⚠️  Skipping links for this folder (no folder ID)")
                continue
            
            folder_ids[folder_name] = folder_id
            created_folders += 1
        
        if folders_only:
            # Skip link creation in folders-only mode
            continue

        # Create symlinks in folder
        for idx, link in enumerate(links, 1):
            link_name = link['link_name']
            url = link['url']
            title = link['title']
            count = link['count']

            # Decide if we print this item (first 5, last, or if <=10)
            should_print = len(links) <= 10 or idx <= 5 or idx == len(links)
            if should_print:
                count_str = f"({count} uses)" if int(count) > 1 else ""
                print(f"   {idx:3}. {link_name[:50]:<50} {count_str}")

            if dry_run:
                if should_print:
                    print(f"        Would create symlink to: {url[:70]}")
                continue

            # Create symlink (always attempt, regardless of printing)
            new_id = create_symlink(
                link_name=link_name,
                url=url,
                folder_id=folder_ids[folder_name],
                base_symlink_id=base_symlink_id,
                auth=auth,
                cms_path=cms_path,
                title=title,
                folder_name=folder_name,
                log_to_db=bool(db),
            )

            if new_id:
                created_links += 1
                if should_print:
                    print(f"        ✅ Created (ID: {new_id})")
            else:
                failed_links += 1
                if should_print:
                    print(f"        ❌ Failed")

            # After printing first 5, show abbreviated message once
            if idx == 6 and len(links) > 10:
                print(f"        ... {len(links) - 6} more links ...")
    
    # Summary
    print(f"\n\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    
    if dry_run:
        print(f"Would create:")
        print(f"  Folders: {total_folders}")
        print(f"  Links: {total_links}")
    else:
        print(f"Created:")
        print(f"  Folders: {created_folders} / {total_folders}")
        print(f"  Links: {created_links} / {total_links}")
        if failed_links > 0:
            print(f"  Failed: {failed_links}")


def main():
    """Main execution."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='Create link assets in Cascade CMS')
    parser.add_argument('--parent-id', required=True, help='Parent folder ID for link assets')
    parser.add_argument('--base-folder-id', required=True, help='Base folder ID to copy for creating domain folders')
    parser.add_argument('--base-symlink-id', required=True, help='Base symlink ID to copy')
    parser.add_argument('--priority', choices=['HIGH', 'MEDIUM', 'ALL'], default='HIGH',
                       help='Priority level to create (default: HIGH)')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Preview what would be created without making changes')
    parser.add_argument('--folders-only', action='store_true', help='Create/lookup folders only (no links)')
    parser.add_argument('--links-only', action='store_true', help='Create links only (folders must exist)')
    parser.add_argument('--no-db', action='store_true', help='Do not use the migration database for logging/lookups')
    parser.add_argument('--report-duplicates', action='store_true', help='Audit for duplicate-named symlinks (no changes)')
    parser.add_argument('--dedupe', action='store_true', help='Remove numbered duplicate symlinks (respects --dry-run)')
    parser.add_argument('--structure-file', 
                       default=os.path.expanduser('~/Repositories/wjoell/slc-edu-migration/source-assets/link_asset_structure.csv'),
                       help='Path to link_asset_structure.csv')
    
    args = parser.parse_args()
    
    # Get CMS connection from CLI session using session_manager
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from session_manager import session_manager
    
    session = session_manager.get_session()
    
    if not session:
        print("❌ Error: Not connected to Cascade CMS")
        print("Run: python cli.py connect-1password [vault] [item]")
        print("Or: python cli.py setup")
        return
    
    cms_path = session.get('cms_path')
    api_key = session.get('api_key')
    
    if not cms_path or not api_key:
        print("❌ Error: Invalid session - missing credentials")
        return
    
    auth = {'apiKey': api_key}
    print(f"✅ Connected to: {cms_path}")
    print()
    
    # Verify file exists
    if not os.path.exists(args.structure_file):
        print(f"❌ Error: Structure file not found: {args.structure_file}")
        return
    
    # Create assets
    create_all_link_assets(
        structure_file=args.structure_file,
        parent_folder_id=args.parent_id,
        base_folder_id=args.base_folder_id,
        base_symlink_id=args.base_symlink_id,
        auth=auth,
        cms_path=cms_path,
        priority_filter=args.priority,
        dry_run=args.dry_run,
        folders_only=args.folders_only,
        links_only=args.links_only,
        use_db=not args.no_db,
        report_duplicates=args.report_duplicates,
        dedupe=args.dedupe,
    )


if __name__ == '__main__':
    main()
