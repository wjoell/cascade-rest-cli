"""
Clone destination XML template for all origin XML files.

Creates *-destination.xml files next to each origin .xml file in the migration-clean
directory, using the default-content-page.xml template as the base.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import List, Tuple

# Paths relative to slc-edu-migration repo
MIGRATION_CLEAN_DIR = "/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/migration-clean"
DESTINATION_TEMPLATE = "/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/source-destination-mapping/xml-document-specimens/destination/default-content-page.xml"


def find_all_origin_xml_files(base_dir: str) -> List[str]:
    """
    Find all .xml files in migration-clean directory.
    
    Args:
        base_dir: Path to migration-clean directory
        
    Returns:
        List of absolute paths to .xml files (excluding *-migration.html and *-destination.xml)
    """
    xml_files = []
    
    for root, dirs, files in os.walk(base_dir):
        # Skip underscore-prefixed directories (sandbox, reports, etc.)
        dirs[:] = [d for d in dirs if not d.startswith('_')]
        
        for file in files:
            if file.endswith('.xml') and not file.endswith('-destination.xml'):
                xml_files.append(os.path.join(root, file))
    
    return sorted(xml_files)


def create_destination_xml(origin_xml_path: str, template_path: str, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Create a destination XML file by copying the template.
    
    Args:
        origin_xml_path: Path to origin .xml file
        template_path: Path to destination template
        dry_run: If True, don't actually create files
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    # Generate destination filename
    base_path = origin_xml_path.rsplit('.xml', 1)[0]
    destination_path = f"{base_path}-destination.xml"
    
    # Check if destination already exists
    if os.path.exists(destination_path):
        return (False, f"Already exists: {destination_path}")
    
    if dry_run:
        return (True, f"Would create: {destination_path}")
    
    # Copy template to destination
    try:
        shutil.copy2(template_path, destination_path)
        return (True, f"Created: {destination_path}")
    except Exception as e:
        return (False, f"Error creating {destination_path}: {e}")


def clone_all_destinations(base_dir: str, template_path: str, dry_run: bool = False) -> dict:
    """
    Clone destination templates for all origin XML files.
    
    Args:
        base_dir: Path to migration-clean directory
        template_path: Path to destination template
        dry_run: If True, don't actually create files
        
    Returns:
        Dict with statistics
    """
    # Verify template exists
    if not os.path.exists(template_path):
        print(f"❌ Template not found: {template_path}")
        return {'error': 'Template not found', 'total': 0, 'created': 0, 'skipped': 0, 'failed': 0}
    
    # Find all origin XML files
    print(f"🔍 Scanning for XML files in: {base_dir}")
    xml_files = find_all_origin_xml_files(base_dir)
    print(f"📄 Found {len(xml_files)} XML files")
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No files will be created\n")
    
    # Clone template for each file
    results = {
        'total': len(xml_files),
        'created': 0,
        'skipped': 0,
        'failed': 0
    }
    
    for i, xml_path in enumerate(xml_files, 1):
        rel_path = os.path.relpath(xml_path, base_dir)
        
        # Progress indicator every 100 files
        if i % 100 == 0 or i == 1 or i == len(xml_files):
            print(f"\nProcessing {i}/{len(xml_files)}: {rel_path}")
        
        success, message = create_destination_xml(xml_path, template_path, dry_run)
        
        if success:
            if "Already exists" in message:
                results['skipped'] += 1
            else:
                results['created'] += 1
                if i <= 5 or i % 100 == 0:  # Show first few and every 100th
                    print(f"  ✅ {message}")
        else:
            results['failed'] += 1
            print(f"  ❌ {message}")
    
    return results


def generate_manifest(base_dir: str, output_file: str = None):
    """
    Generate a manifest of all cloned destination files.
    
    Args:
        base_dir: Path to migration-clean directory
        output_file: Optional path to write manifest to
    """
    destination_files = []
    
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if not d.startswith('_')]
        
        for file in files:
            if file.endswith('-destination.xml'):
                rel_path = os.path.relpath(os.path.join(root, file), base_dir)
                destination_files.append(rel_path)
    
    manifest = sorted(destination_files)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write('\n'.join(manifest))
        print(f"\n📋 Manifest written to: {output_file}")
    
    return manifest


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Clone destination XML templates for migration')
    parser.add_argument('--dry-run', action='store_true', default=False,
                       help='Preview what would be created without actually creating files')
    parser.add_argument('--manifest', type=str,
                       help='Generate manifest file of all destination XMLs')
    parser.add_argument('--base-dir', type=str, default=MIGRATION_CLEAN_DIR,
                       help='Base directory containing XML files')
    parser.add_argument('--template', type=str, default=DESTINATION_TEMPLATE,
                       help='Path to destination template XML')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("DESTINATION XML TEMPLATE CLONING")
    print("=" * 80)
    print(f"Base directory: {args.base_dir}")
    print(f"Template: {args.template}")
    print("=" * 80)
    
    # Verify base directory exists
    if not os.path.exists(args.base_dir):
        print(f"\n❌ Base directory not found: {args.base_dir}")
        sys.exit(1)
    
    # Clone templates
    results = clone_all_destinations(args.base_dir, args.template, args.dry_run)
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    if 'error' in results:
        print(f"❌ Error: {results['error']}")
    else:
        print(f"Total XML files: {results['total']}")
        print(f"Created: {results['created']}")
        print(f"Skipped (already exist): {results['skipped']}")
        print(f"Failed: {results['failed']}")
    print("=" * 80)
    
    # Generate manifest if requested
    if args.manifest and not args.dry_run:
        manifest = generate_manifest(args.base_dir, args.manifest)
        print(f"Total destination files: {len(manifest)}")
    
    sys.exit(0 if results['failed'] == 0 else 1)
