"""
Fix card-options for destination XML files.

Scans all destination XML files and sets <card-options> to 'no-image'
on any <group-cards> block where ALL populated card items lack images.

Usage:
    python fix_card_options.py [--dry-run] [--section SECTION] [--page PAGE]
"""

import os
import sys
import glob
import argparse
from xml.etree import ElementTree as ET


MIGRATION_CLEAN = '/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/migration-clean'


def card_has_content(card: ET.Element) -> bool:
    """Check if a card item has any actual content (heading or wysiwyg)."""
    heading = card.find('.//heading-text')
    if heading is not None and heading.text and heading.text.strip():
        return True
    wysiwyg = card.find('wysiwyg')
    if wysiwyg is not None and (wysiwyg.text or len(wysiwyg)):
        return True
    return False


def card_has_image(card: ET.Element) -> bool:
    """Check if a card item has an image reference."""
    media = card.find('group-single-media')
    if media is None:
        return False
    pub_id = media.find('pub-api-asset-id')
    if pub_id is not None and pub_id.text and pub_id.text.strip():
        return True
    img = media.find('img')
    if img is not None:
        img_path = img.find('path')
        if img_path is not None and img_path.text and img_path.text.strip() and img_path.text.strip() != '/':
            return True
    return False


def fix_card_options_in_file(filepath: str, dry_run: bool = False) -> dict:
    """
    Fix card-options in a single destination XML file.

    Returns dict with counts of changes made.
    """
    try:
        tree = ET.parse(filepath)
    except ET.ParseError as e:
        return {'error': str(e), 'changed': 0}

    root = tree.getroot()
    changed = 0

    for group_cards in root.iter('group-cards'):
        card_items = group_cards.findall('group-card-item')
        if not card_items:
            continue

        # Only consider cards that have actual content
        populated = [c for c in card_items if card_has_content(c)]
        if not populated:
            continue

        # Check if ALL populated cards lack images
        all_missing_images = all(not card_has_image(c) for c in populated)
        if not all_missing_images:
            continue

        # Set card-options to no-image
        options = group_cards.find('card-options')
        if options is None:
            continue
        if options.text == 'no-image':
            continue  # Already set

        old_val = options.text or 'empty'
        options.text = 'no-image'
        changed += 1

    if changed > 0 and not dry_run:
        ET.indent(tree, space='    ')
        tree.write(filepath, encoding='unicode', xml_declaration=False)

    return {'changed': changed}


def main():
    parser = argparse.ArgumentParser(description='Fix card-options for imageless cards')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without writing')
    parser.add_argument('--section', type=str, help='Limit to a specific section (e.g. "student-life")')
    parser.add_argument('--page', type=str, help='Limit to a specific page path (e.g. "student-life/index")')
    parser.add_argument('--output', type=str, help='Write list of changed source paths to file (for --pages-from)')
    args = parser.parse_args()

    if args.page:
        pattern = os.path.join(MIGRATION_CLEAN, args.page + '-destination.xml')
        files = glob.glob(pattern)
    elif args.section:
        pattern = os.path.join(MIGRATION_CLEAN, args.section, '**/*-destination.xml')
        files = sorted(glob.glob(pattern, recursive=True))
    else:
        pattern = os.path.join(MIGRATION_CLEAN, '**/*-destination.xml')
        files = sorted(glob.glob(pattern, recursive=True))

    if not files:
        print(f'No files matched: {pattern}')
        sys.exit(1)

    mode = 'DRY RUN' if args.dry_run else 'LIVE'
    print(f'{"=" * 60}')
    print(f'FIX CARD OPTIONS: {mode}')
    print(f'{"=" * 60}')
    print(f'Files to scan: {len(files)}')
    print()

    total_files_changed = 0
    total_cards_changed = 0
    changed_paths = []

    for filepath in files:
        result = fix_card_options_in_file(filepath, dry_run=args.dry_run)

        if 'error' in result:
            rel = os.path.relpath(filepath, MIGRATION_CLEAN)
            print(f'  ❌ {rel}: {result["error"]}')
            continue

        if result['changed'] > 0:
            rel = os.path.relpath(filepath, MIGRATION_CLEAN)
            # Convert to source_path format: about/index-destination.xml → about/index.xml
            source_path = rel.replace('-destination.xml', '.xml')
            changed_paths.append(source_path)
            print(f'  ✅ {rel}: {result["changed"]} card group(s) → no-image')
            total_files_changed += 1
            total_cards_changed += result['changed']

    # Write page list for update script
    if args.output and changed_paths:
        with open(args.output, 'w') as f:
            for p in changed_paths:
                f.write(p + '\n')
        print(f'\n📋 Page list written to: {args.output} ({len(changed_paths)} paths)')

    print()
    print(f'{"=" * 60}')
    print(f'Files modified: {total_files_changed}')
    print(f'Card groups updated: {total_cards_changed}')
    if args.dry_run:
        print('(dry run — no files were written)')
    print(f'{"=" * 60}')


if __name__ == '__main__':
    main()
