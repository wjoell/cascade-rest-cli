"""
News Item Migration Script

Migrates news articles from origin XML to destination format:
- Content (blockParaImg, floated images with captions)
- Metadata (wired fields, dynamic fields with transformations)
- Page type (feature-story or news)
- Page heading (from headline)
"""

import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from migration_logger import MigrationLogger
from xml_mappers import (
    map_news_content,
    get_news_page_type,
    extract_wired_metadata,
    extract_dynamic_metadata,
    get_page_heading,
    transform_boolean_metadata,
    create_page_section,
    insert_content_items,
    _BOOLEAN_METADATA_FIELDS,
    _DIRECT_COPY_METADATA_FIELDS
)


def migrate_news_item(origin_path: str, destination_path: str,
                      global_log_path: str = None, quiet: bool = False) -> dict:
    """
    Migrate a single news item from origin to destination format.
    
    Args:
        origin_path: Path to origin news .xml file
        destination_path: Path to destination .xml file (template)
        global_log_path: Optional path to global log file
        quiet: Suppress console output (for batch operations)
        
    Returns:
        Dict with migration statistics
    """
    stats = {
        'content_items_created': 0,
        'images_found': [],
        'metadata_notes': [],
        'success': False
    }
    
    filename = Path(origin_path).name
    
    # Load origin XML
    if not quiet:
        print(f"Loading origin: {origin_path}")
    origin_tree = ET.parse(origin_path)
    origin_root = origin_tree.getroot()
    
    # Load destination template
    if not quiet:
        print(f"Loading destination: {destination_path}")
    dest_tree = ET.parse(destination_path)
    dest_root = dest_tree.getroot()
    
    # Extract metadata
    wired_meta = extract_wired_metadata(origin_root)
    dynamic_meta = extract_dynamic_metadata(origin_root)
    
    page_path = wired_meta.get('title', 'Unknown')
    if not quiet:
        print(f"Title: {page_path}")
    
    # Initialize logger
    logger = MigrationLogger(page_path=page_path, file_path=origin_path)
    if global_log_path:
        logger.set_global_log_file(global_log_path)
    
    # Find destination system-data-structure
    dest_structure = dest_root.find('.//system-data-structure')
    if dest_structure is None:
        logger.error("No system-data-structure in destination template")
        return stats
    
    # --- Set page-type ---
    page_type = get_news_page_type(filename)
    page_type_elem = dest_structure.find('page-type')
    if page_type_elem is not None:
        page_type_elem.text = page_type
        logger.info(f"page-type = {page_type}")
    stats['metadata_notes'].append(f"page-type: {page_type}")
    
    # --- Set page heading (group-hero/heading) ---
    heading = get_page_heading(origin_root, is_news=True)
    hero_group = dest_structure.find('group-hero')
    if hero_group is not None:
        heading_elem = hero_group.find('heading')
        if heading_elem is not None:
            heading_elem.text = heading
            logger.info(f"heading = {heading[:50]}..." if len(heading) > 50 else f"heading = {heading}")
    stats['metadata_notes'].append(f"heading: {heading}")
    
    # --- Map wired metadata ---
    # Log wired fields for migration summary
    for field in ['title', 'description', 'keywords', 'summary', 'display-name', 'start-date']:
        if field in wired_meta:
            value = wired_meta[field]
            # Truncate long values for logging
            log_value = f"{value[:50]}..." if len(value) > 50 else value
            logger.info(f"WIRED {field} = {log_value}")
            stats['metadata_notes'].append(f"WIRED {field}: {log_value}")
    
    # --- Map dynamic metadata ---
    # Boolean fields (Yes/No -> true/false)
    for field in _BOOLEAN_METADATA_FIELDS:
        values = dynamic_meta.get(field, [])
        if values:
            original = values[0]
            transformed = transform_boolean_metadata(original)
            logger.info(f"META {field} = {transformed} (was: {original})")
            stats['metadata_notes'].append(f"META {field}: {transformed} (was: {original})")
    
    # Direct copy fields
    for field in _DIRECT_COPY_METADATA_FIELDS:
        values = dynamic_meta.get(field, [])
        if values:
            if len(values) == 1:
                logger.info(f"META {field} = {values[0]}")
                stats['metadata_notes'].append(f"META {field}: {values[0]}")
            else:
                logger.info(f"META {field} = [{', '.join(values)}]")
                stats['metadata_notes'].append(f"META {field}: [{', '.join(values)}]")
    
    # --- Map content ---
    content_elem = origin_root.find('.//content')
    if content_elem is None:
        logger.warning("No <content> element found in origin")
    else:
        # Map news content
        images_found = []
        content_results = map_news_content(content_elem, images_found)
        
        stats['images_found'] = images_found
        stats['content_items_created'] = len(content_results)
        
        # Log images
        for img_info in images_found:
            if 'NO ASSET ID' in img_info:
                logger.warning(f"Image: {img_info}")
            else:
                logger.info(f"Image: {img_info}")
        
        # Find the first group-page-section-item in destination
        first_section = dest_structure.find('.//group-page-section-item')
        if first_section is not None:
            # Extract the content items from results
            content_items = [r['item'] for r in content_results]
            
            # Insert content items into the section
            insert_content_items(first_section, content_items)
            
            # Set section mode to flow for news content
            section_mode = first_section.find('section-mode')
            if section_mode is not None:
                section_mode.text = 'flow'
            
            logger.info(f"Created {len(content_items)} content items")
        else:
            logger.error("No group-page-section-item found in destination")
    
    # --- Write migration summary to destination ---
    migration_summary = dest_structure.find('migration-summary')
    if migration_summary is None:
        # Create migration-summary element if it doesn't exist
        migration_summary = ET.SubElement(dest_structure, 'migration-summary')
    
    # Format log for summary field
    log_output = logger.format_for_summary()
    migration_summary.text = log_output
    
    # --- Save destination file ---
    # Pretty print with indentation
    ET.indent(dest_tree, space="    ")
    dest_tree.write(destination_path, encoding='unicode', xml_declaration=False)
    
    if not quiet:
        print(f"\n✓ Migrated to: {destination_path}")
        print(f"  Content items: {stats['content_items_created']}")
        print(f"  Images: {len(stats['images_found'])}")
    
    # Write to global log if specified
    if global_log_path:
        logger.write_to_global_log()
    
    stats['success'] = True
    return stats


def migrate_news_batch(source_dir: str, dest_dir: str, 
                       global_log_path: str = None,
                       file_pattern: str = "*.xml") -> dict:
    """
    Migrate a batch of news items.
    
    Args:
        source_dir: Directory containing origin XML files
        dest_dir: Directory containing destination XML templates
        global_log_path: Optional path to global log file
        file_pattern: Glob pattern for source files
        
    Returns:
        Dict with batch statistics
    """
    source_path = Path(source_dir)
    dest_path = Path(dest_dir)
    
    source_files = list(source_path.glob(file_pattern))
    print(f"Found {len(source_files)} source files")
    
    batch_stats = {
        'total': len(source_files),
        'success': 0,
        'failed': 0,
        'skipped': 0
    }
    
    for source_file in sorted(source_files):
        # Determine destination file path
        # Assumes destination files have same name or -destination suffix
        dest_file = dest_path / source_file.name
        if not dest_file.exists():
            dest_file = dest_path / source_file.name.replace('.xml', '-destination.xml')
        
        if not dest_file.exists():
            print(f"⚠ Skipping {source_file.name} - no destination template")
            batch_stats['skipped'] += 1
            continue
        
        try:
            stats = migrate_news_item(
                str(source_file),
                str(dest_file),
                global_log_path
            )
            if stats['success']:
                batch_stats['success'] += 1
            else:
                batch_stats['failed'] += 1
        except Exception as e:
            print(f"✗ Error migrating {source_file.name}: {e}")
            batch_stats['failed'] += 1
    
    print(f"\n{'='*60}")
    print(f"Batch complete: {batch_stats['success']}/{batch_stats['total']} successful")
    if batch_stats['failed']:
        print(f"  Failed: {batch_stats['failed']}")
    if batch_stats['skipped']:
        print(f"  Skipped: {batch_stats['skipped']}")
    
    return batch_stats


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python news_migrate.py <origin.xml> <destination.xml> [--global-log <path>]")
        print("       python news_migrate.py --batch <source_dir> <dest_dir> [--global-log <path>]")
        sys.exit(1)
    
    global_log = None
    if '--global-log' in sys.argv:
        idx = sys.argv.index('--global-log')
        global_log = sys.argv[idx + 1]
        sys.argv.pop(idx)
        sys.argv.pop(idx)
    
    if sys.argv[1] == '--batch':
        migrate_news_batch(sys.argv[2], sys.argv[3], global_log)
    else:
        migrate_news_item(sys.argv[1], sys.argv[2], global_log)
