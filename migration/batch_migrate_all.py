"""
Batch migration script for all XML files.

Runs xml_migrate_poc.migrate_single_file on all origin XML files
in the migration-clean directory.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from xml_migrate_poc import migrate_single_file

# Source directory
SOURCE_DIR = "/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/migration-clean"

# Global log file
LOG_DIR = "/Users/winston/Repositories/wjoell/slc-edu-migration/logs"


def find_all_origin_files(source_dir: str) -> list:
    """Find all origin XML files (excluding destination and other special files)."""
    origin_files = []
    
    for root, dirs, files in os.walk(source_dir):
        # Skip underscore-prefixed directories
        dirs[:] = [d for d in dirs if not d.startswith('_')]
        
        for fname in files:
            # Include only .xml files that aren't destination or migration files
            if (fname.endswith('.xml') and 
                not fname.endswith('-destination.xml') and
                not fname.endswith('-migration.html')):
                origin_files.append(os.path.join(root, fname))
    
    return sorted(origin_files)


def run_batch_migration(source_dir: str = SOURCE_DIR, dry_run: bool = False):
    """Run migration on all origin XML files."""
    
    # Create log directory
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Generate log file path
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    global_log_path = f"{LOG_DIR}/batch-migration-{timestamp}.log"
    
    # Find all origin files
    origin_files = find_all_origin_files(source_dir)
    
    print("=" * 80)
    print("BATCH XML MIGRATION")
    print("=" * 80)
    print(f"Source directory: {source_dir}")
    print(f"Found {len(origin_files)} origin files")
    print(f"Global log: {global_log_path}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("=" * 80)
    print()
    
    # Statistics
    successful = 0
    failed = 0
    skipped = 0
    total_sections = 0
    total_content_items = 0
    errors = []
    
    for i, origin_path in enumerate(origin_files, 1):
        rel_path = os.path.relpath(origin_path, source_dir)
        dest_path = origin_path.replace('.xml', '-destination.xml')
        
        # Progress update every 100 files
        if i % 100 == 0 or i == 1:
            print(f"\n[{i}/{len(origin_files)}] Processing: {rel_path}")
        
        # Check destination exists
        if not os.path.exists(dest_path):
            skipped += 1
            errors.append(f"SKIP: {rel_path} - destination template not found")
            continue
        
        try:
            stats = migrate_single_file(origin_path, dest_path, global_log_path=global_log_path)
            
            if stats['success']:
                successful += 1
                total_sections += stats['sections_created']
                total_content_items += stats['content_items_created']
            else:
                failed += 1
                errors.append(f"FAIL: {rel_path}")
                
        except Exception as e:
            failed += 1
            errors.append(f"ERROR: {rel_path} - {str(e)[:50]}")
    
    # Summary
    print("\n" + "=" * 80)
    print("BATCH MIGRATION COMPLETE")
    print("=" * 80)
    print(f"\nFiles processed: {len(origin_files)}")
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed}")
    print(f"  ⏭️  Skipped: {skipped}")
    print(f"\nContent migrated:")
    print(f"  Sections: {total_sections}")
    print(f"  Content items: {total_content_items}")
    print(f"\n📋 Global log: {global_log_path}")
    
    if errors:
        print(f"\n❌ Errors ({len(errors)}):")
        for err in errors[:20]:
            print(f"  {err}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")
    
    return {
        'total': len(origin_files),
        'successful': successful,
        'failed': failed,
        'skipped': skipped,
        'sections': total_sections,
        'content_items': total_content_items,
        'errors': errors
    }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch migrate all XML files')
    parser.add_argument('--dry-run', action='store_true', help='Preview without migrating')
    parser.add_argument('--source-dir', type=str, default=SOURCE_DIR, help='Source directory')
    
    args = parser.parse_args()
    
    results = run_batch_migration(source_dir=args.source_dir, dry_run=args.dry_run)
    
    sys.exit(0 if results['failed'] == 0 else 1)
