"""
Proof of Concept: XML Structure Migration for about/index.xml

Demonstrates the complete migration workflow:
1. Load origin XML
2. Detect active regions
3. Map content to destination structure
4. Write destination XML with migration summary
"""

import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape as xml_escape
from migration_logger import MigrationLogger, GlobalMigrationLog
from xml_analyzer import (
    detect_active_regions,
    get_active_region_items,
    get_item_type,
    get_item_section_heading,
    has_wysiwyg_content,
    extract_metadata,
    generate_xpath_exclusion
)
from xml_mappers import (
    map_text_content,
    map_accordion_content,
    map_action_links,
    map_list_index_to_cards,
    map_quote_content,
    map_intro_video,
    map_intro_content,
    map_video_content,
    map_image_content,
    map_form_content,
    map_gallery_content,
    map_button_navigation_group,
    log_heading_id_exclusions,
    create_page_section,
    insert_content_items
)


def migrate_single_file(origin_path: str, destination_path: str, 
                        global_log_path: str = None) -> dict:
    """
    Migrate a single origin XML file to destination format.
    
    Args:
        origin_path: Path to origin .xml file
        destination_path: Path to destination -destination.xml file
        global_log_path: Optional path to global log file for batch operations
        
    Returns:
        Dict with migration statistics
    """
    stats = {
        'sections_created': 0,
        'content_items_created': 0,
        'exclusions': [],
        'images_found': [],
        'success': False
    }
    
    # Load origin XML
    print(f"Loading origin: {origin_path}")
    origin_tree = ET.parse(origin_path)
    origin_root = origin_tree.getroot()
    
    # Load destination template
    print(f"Loading destination template: {destination_path}")
    dest_tree = ET.parse(destination_path)
    dest_root = dest_tree.getroot()
    
    # Extract metadata
    metadata = extract_metadata(origin_root)
    page_path = metadata.get('path', 'Unknown')
    print(f"Page: {metadata.get('title', 'Unknown')}")
    print(f"Path: {page_path}")
    
    # Initialize migration logger
    logger = MigrationLogger(page_path=page_path, file_path=origin_path)
    if global_log_path:
        logger.set_global_log_file(global_log_path)
    
    # Detect active regions
    regions = detect_active_regions(origin_root)
    print(f"\nActive regions: {[r for r, active in regions.items() if active]}")
    
    # Find the system-data-structure in destination
    dest_structure = dest_root.find('.//system-data-structure')
    if dest_structure is None:
        print("❌ Could not find system-data-structure in destination template")
        return stats
    
    # Find the first group-page-section-item to update (rather than create new)
    first_section = dest_structure.find('.//group-page-section-item')
    if first_section is None:
        print("❌ Could not find group-page-section-item in destination template")
        return stats
    
    # Track if we've used the first section
    first_section_used = False
    
    # Process intro region (if active, before primary/secondary)
    if regions.get('intro'):
        print(f"\n{'='*60}")
        print(f"Processing INTRO region")
        print(f"{'='*60}")
        
        intro_elem = origin_root.find('.//group-intro')
        if intro_elem is not None:
            # Use comprehensive intro content mapper
            intro_result = map_intro_content(intro_elem, stats['exclusions'], stats['images_found'])
            
            if intro_result['has_content']:
                # Check for multiple sections first (e.g. gallery + text as separate sections)
                if intro_result.get('sections'):
                    # Multiple sections returned (e.g. pub-api-gallery with wysiwyg)
                    section_idx = list(dest_structure).index(first_section)
                    total_content_items = 0
                    
                    for idx, intro_section in enumerate(intro_result['sections']):
                        dest_structure.insert(section_idx + idx, intro_section)
                        stats['sections_created'] += 1
                        section_content_count = len(intro_section.findall('.//group-section-content-item'))
                        total_content_items += section_content_count
                    
                    stats['content_items_created'] += total_content_items
                    
                    cta_display = intro_elem.findtext('cta-display', 'Off')
                    print(f"  → Created {len(intro_result['sections'])} intro sections (cta-display={cta_display})")
                    print(f"  → {total_content_items} total content items")
                
                elif intro_result['section']:
                    # Single full section returned (text+media, gallery only, etc.)
                    # Insert as first section, before the template section
                    intro_section = intro_result['section']
                    
                    # Insert before the first group-page-section-item
                    section_idx = list(dest_structure).index(first_section)
                    dest_structure.insert(section_idx, intro_section)
                    
                    stats['sections_created'] += 1
                    # Count content items in the section
                    intro_content_count = len(intro_section.findall('.//group-section-content-item'))
                    stats['content_items_created'] += intro_content_count
                    
                    cta_display = intro_elem.findtext('cta-display', 'Off')
                    print(f"  → Created intro section (mode={intro_result['section_type']}, cta-display={cta_display})")
                    print(f"  → {intro_content_count} content items")
                    
                elif intro_result['content_items']:
                    # Content items only (prose text) - add to first section
                    insert_content_items(first_section, intro_result['content_items'])
                    first_section.find('section-mode').text = 'flow'
                    first_section_used = True
                    stats['sections_created'] += 1
                    stats['content_items_created'] += len(intro_result['content_items'])
                    print(f"  → Added {len(intro_result['content_items'])} intro content items to first section")
    
    # Process each active region
    for region in ['primary', 'secondary']:
        if not regions.get(region):
            continue
        
        print(f"\n{'='*60}")
        print(f"Processing {region.upper()} region")
        print(f"{'='*60}")
        
        items = get_active_region_items(origin_root, region)
        print(f"Found {len(items)} active items")
        
        # Collect content items, create section only if needed
        section_has_content = False
        section_content_items = []  # Collect items to insert later
        
        # Track pending section heading from item-level h2→h3 pattern
        pending_section_heading = None
        
        for i, item in enumerate(items, 1):
            item_type = get_item_type(item)
            print(f"\n  Item {i}: Type={item_type}")
            
            content_items = []
            
            # Check for yes-description on ANY item type
            # This creates a prose content item with heading (in subheading) + description BEFORE the main content
            item_section_heading = get_item_section_heading(item)
            if item_section_heading and item_section_heading.get('has_description'):
                from xml_mappers import create_section_content_item, copy_wysiwyg_content
                
                # Create prose content item with heading in group-content-subheading and section-description in wysiwyg
                desc_item = create_section_content_item(
                    heading=item_section_heading['text'],
                    heading_level=item_section_heading.get('level', 'h2')
                )
                # Set content-item-type to prose
                item_type_elem = desc_item.find('content-item-type')
                if item_type_elem is not None:
                    item_type_elem.text = 'prose'
                # Copy section-description to wysiwyg
                wysiwyg_dest = desc_item.find('wysiwyg')
                if wysiwyg_dest is not None and item_section_heading.get('description_elem') is not None:
                    copy_wysiwyg_content(item_section_heading['description_elem'], wysiwyg_dest, stats['images_found'])
                
                content_items.append(desc_item)
                print(f"    → Created prose item with subheading '{item_section_heading['text']}' + description (yes-description)")
                
                # Now create a SECOND content item for the actual content type (api-gallery for gallery, media for video)
                # This handles the case where yes-description is combined with gallery, video, etc.
                if item_type == "Publish API Gallery":
                    # Create api-gallery content item for gallery
                    gallery = item.find('.//publish-api-gallery')
                    if gallery is not None:
                        gallery_id = gallery.findtext('gallery-api-id', '')
                        if gallery_id:
                            from xml_mappers import create_gallery_content_item
                            # Get display properties from source
                            display_type = gallery.findtext('display-type', 'side-scroller')
                            aspect_ratio = gallery.findtext('aspect-ratio', '1.5')
                            img_fit = gallery.findtext('img-fit', 'contain')
                            allow_fullscreen = gallery.findtext('allow-fullscreen', 'true')
                            img_captions = gallery.findtext('img-captions', 'no')
                            
                            gallery_item = create_gallery_content_item(
                                gallery_id=gallery_id,
                                display_type=display_type,
                                aspect_ratio=aspect_ratio,
                                img_fit=img_fit,
                                allow_fullscreen=allow_fullscreen,
                                img_captions=img_captions
                            )
                            content_items.append(gallery_item)
                            print(f"    → Created api-gallery content item (ID: {gallery_id})")
                elif item_type == "Video":
                    # Create media content item for video - let the normal video handler create it
                    pass  # Will be handled by video handler below
            
            # Now process based on item type
            if item_type == "Text":
                item_has_content = has_wysiwyg_content(item)
                
                # Detect h2→h3 pattern at item level:
                # If this item has h2 section heading with no content, look ahead
                if (item_section_heading and 
                    item_section_heading.get('level') == 'h2' and 
                    not item_has_content and
                    not item_section_heading.get('has_description')):
                    # Check if next item is h3 with content
                    if i < len(items):
                        next_item = items[i]  # items is 0-indexed, i is 1-indexed so items[i] is next
                        next_heading = get_item_section_heading(next_item)
                        next_has_content = has_wysiwyg_content(next_item)
                        
                        if (next_heading and 
                            next_heading.get('level') == 'h3' and 
                            next_has_content):
                            # h2→h3 pattern detected! Store h2 for next item's section
                            pending_section_heading = item_section_heading['text']
                            print(f"    → h2→h3 pattern detected, storing '{pending_section_heading}' for next section")
                            continue  # Skip this item, it will be used as section heading for next
                
                # Map text content (splits on headings within WYSIWYG)
                # Returns list of dicts: {'item': element, 'section_heading': optional h2 text}
                # Pass item_section_heading so items with section-heading field get that as subheading
                # (but not if we already used it for yes-description)
                text_results = map_text_content(
                    item, stats['exclusions'], stats['images_found'],
                    item_heading=item_section_heading if not item_section_heading or not item_section_heading.get('has_description') else None
                )
                content_items.extend([r['item'] for r in text_results if not r.get('section_heading')])
                
                # Handle h2→h3 pattern from WYSIWYG: items with section_heading create new sections
                for result in text_results:
                    if result.get('section_heading'):
                        # First, flush any pending content items to current section
                        if section_content_items:
                            if not first_section_used:
                                insert_content_items(first_section, section_content_items)
                                first_section.find('section-mode').text = 'flow'
                                first_section_used = True
                                stats['sections_created'] += 1
                            else:
                                section = create_page_section(section_mode="flow")
                                insert_content_items(section, section_content_items)
                                cta_banner = dest_structure.find('group-cta-banner')
                                if cta_banner is not None:
                                    insert_index = list(dest_structure).index(cta_banner)
                                    dest_structure.insert(insert_index, section)
                                else:
                                    dest_structure.append(section)
                                stats['sections_created'] += 1
                            section_content_items = []
                        
                        # Create new section with h2 as content-heading
                        new_section = create_page_section(
                            section_mode="flow",
                            content_heading=result['section_heading']
                        )
                        insert_content_items(new_section, [result['item']])
                        
                        # Insert before cta-banner
                        cta_banner = dest_structure.find('group-cta-banner')
                        if cta_banner is not None:
                            insert_index = list(dest_structure).index(cta_banner)
                            dest_structure.insert(insert_index, new_section)
                        else:
                            dest_structure.append(new_section)
                        
                        first_section_used = True
                        stats['sections_created'] += 1
                        stats['content_items_created'] += 1
                        print(f"    → Created new section with heading '{result['section_heading']}'")
                
                # Check if we have a pending section heading from item-level h2→h3 pattern
                if pending_section_heading and content_items:
                    # Flush any existing content first
                    if section_content_items:
                        if not first_section_used:
                            insert_content_items(first_section, section_content_items)
                            first_section.find('section-mode').text = 'flow'
                            first_section_used = True
                            stats['sections_created'] += 1
                        else:
                            section = create_page_section(section_mode="flow")
                            insert_content_items(section, section_content_items)
                            cta_banner = dest_structure.find('group-cta-banner')
                            if cta_banner is not None:
                                insert_index = list(dest_structure).index(cta_banner)
                                dest_structure.insert(insert_index, section)
                            else:
                                dest_structure.append(section)
                            stats['sections_created'] += 1
                        section_content_items = []
                    
                    # Create new section with the pending h2 as content-heading
                    new_section = create_page_section(
                        section_mode="flow",
                        content_heading=pending_section_heading
                    )
                    insert_content_items(new_section, content_items)
                    
                    # Insert before cta-banner
                    cta_banner = dest_structure.find('group-cta-banner')
                    if cta_banner is not None:
                        insert_index = list(dest_structure).index(cta_banner)
                        dest_structure.insert(insert_index, new_section)
                    else:
                        dest_structure.append(new_section)
                    
                    first_section_used = True
                    stats['sections_created'] += 1
                    stats['content_items_created'] += len(content_items)
                    print(f"    → Created new section with heading '{pending_section_heading}' (from item-level h2→h3 pattern)")
                    print(f"    → Added {len(content_items)} content items")
                    
                    pending_section_heading = None
                    content_items = []  # Already added to section
                
                print(f"    → Created {len(content_items)} content items from WYSIWYG")
                
            elif item_type == "Accordion":
                # Map accordion panels
                content_items = map_accordion_content(item, stats['exclusions'], stats['images_found'])
                print(f"    → Created {len(content_items)} accordion items")
                
            elif item_type == "Action Links":
                # Exclude action links
                xpath = generate_xpath_exclusion(region, i, item_type="Action Links")
                stats['exclusions'].append(xpath)
                print(f"    → Excluded: {xpath}")
                
            elif item_type == "External Block":
                # Check block type
                group_block = item.find('.//group-block')
                if group_block is not None:
                    block_type = group_block.findtext('type', '')
                    
                    if block_type == "List Index":
                        # Map List Index to cards
                        content_items = map_list_index_to_cards(item, stats['exclusions'], stats['images_found'])
                        print(f"    → Created {len(content_items)} card sections from List Index")
                    elif block_type == "Simple Content":
                        # Log Simple Content blocks for QA - these need manual review
                        section_heading = item.findtext('section-heading', '(no heading)')
                        block_elem = group_block.find('block')
                        content_elem = block_elem.find('content') if block_elem is not None else None
                        
                        if content_elem is not None:
                            content_text = ET.tostring(content_elem, encoding='unicode', method='text').strip()
                            content_preview = content_text[:100] + '...' if len(content_text) > 100 else content_text
                            
                            # Detect if it's embed code vs real content
                            is_embed = 'mc_embed' in content_text or '<script' in content_text.lower() or '<style' in content_text.lower()
                            
                            if is_embed:
                                # Embed code - flag for manual work
                                qa_note = f'MANUAL: External Block (Simple Content) "{section_heading}" contains embed code - requires manual setup'
                                stats['exclusions'].append(qa_note)
                                print(f"    → QA Flag: {qa_note}")
                            else:
                                # Real content - flag for QA review
                                qa_note = f'MANUAL: External Block (Simple Content) "{section_heading}" has content: {content_preview}'
                                stats['exclusions'].append(qa_note)
                                print(f"    → QA Flag: {qa_note}")
                        else:
                            xpath = generate_xpath_exclusion(region, i, item_type=f"External Block (Simple Content - empty)")
                            stats['exclusions'].append(xpath)
                            print(f"    → Excluded: {xpath}")
                    else:
                        # Other block types - exclude for now
                        xpath = generate_xpath_exclusion(region, i, item_type=f"External Block ({block_type})")
                        stats['exclusions'].append(xpath)
                        print(f"    → Excluded: {xpath}")
                else:
                    xpath = generate_xpath_exclusion(region, i, item_type="External Block")
                    stats['exclusions'].append(xpath)
                    print(f"    → Excluded: {xpath}")
            
            elif item_type == "Quote":
                # Map quote content
                quote_items = map_quote_content(item, stats['exclusions'])
                content_items.extend(quote_items)
                print(f"    → Created {len(quote_items)} quote items")
            
            elif item_type == "Video":
                # Map video content
                video_items = map_video_content(item, stats['exclusions'])
                if video_items:
                    content_items.extend(video_items)
                    print(f"    → Created {len(video_items)} video items")
                else:
                    xpath = generate_xpath_exclusion(region, i, item_type="Video (empty)")
                    stats['exclusions'].append(xpath)
                    print(f"    → Excluded: {xpath}")
            
            elif item_type == "Image":
                # Map image content
                image_items = map_image_content(item, stats['exclusions'], stats['images_found'])
                if image_items:
                    content_items.extend(image_items)
                    print(f"    → Created {len(image_items)} image items")
                else:
                    print(f"    → Excluded: Image (no image or excluded)")
            
            elif item_type == "Form":
                # Map form content
                form_items = map_form_content(item, stats['exclusions'])
                if form_items:
                    content_items.extend(form_items)
                    print(f"    → Created {len(form_items)} form items")
                else:
                    print(f"    → Excluded: Form (no ID or excluded)")
            
            elif item_type == "Publish API Gallery":
                # Only create gallery content item if not already handled by yes-description
                # (yes-description creates both prose + gallery items above)
                if not (item_section_heading and item_section_heading.get('has_description')):
                    gallery_items = map_gallery_content(item, stats['exclusions'])
                    content_items.extend(gallery_items)
                    print(f"    → Created {len(gallery_items)} gallery items")
                else:
                    print(f"    → Gallery already created via yes-description")
            
            elif item_type == "Button navigation group":
                # Exclude button nav, but log details
                map_button_navigation_group(item, stats['exclusions'])
                xpath = generate_xpath_exclusion(region, i, item_type="Button navigation group")
                stats['exclusions'].append(xpath)
                print(f"    → Excluded: {xpath}")
                
            else:
                # Unknown type - exclude
                xpath = generate_xpath_exclusion(region, i, item_type=item_type or "Unknown")
                stats['exclusions'].append(xpath)
                print(f"    → Excluded (unknown type): {xpath}")
            
            # Track content items to add
            if content_items:
                section_content_items.extend(content_items)
                section_has_content = True
                stats['content_items_created'] += len(content_items)
        
        # Add section to destination if it has content
        if section_has_content:
            # Insert all content items at correct position
            if not first_section_used:
                # Use the first section
                insert_content_items(first_section, section_content_items)
                first_section.find('section-mode').text = 'flow'
                first_section_used = True
                print(f"\n✓ Populated first section with {len(section_content_items)} items")
            else:
                # Create new section and insert after the last section (before group-cta-banner)
                section = create_page_section(section_mode="flow")
                insert_content_items(section, section_content_items)
                # Find insertion point (before group-cta-banner)
                cta_banner = dest_structure.find('group-cta-banner')
                if cta_banner is not None:
                    # Insert before cta-banner
                    insert_index = list(dest_structure).index(cta_banner)
                    dest_structure.insert(insert_index, section)
                else:
                    # Fallback: append at end
                    dest_structure.append(section)
                print(f"\n✓ Created new section with {len(section_content_items)} items")
            
            stats['sections_created'] += 1
    
    # Convert old stats to logger entries
    print(f"\n{'='*60}")
    print("Building migration log")
    print(f"{'='*60}")
    
    # Log successful migrations (INFO)
    if stats['sections_created'] > 0:
        logger.info(f"Created {stats['sections_created']} section(s) with {stats['content_items_created']} content item(s)")
    
    # Log exclusions (WARNING) - these are planned skips
    for exclusion in stats['exclusions']:
        logger.warning(f"Excluded: {exclusion}")
    
    # Log images found (categorize by type)
    for img_entry in stats['images_found']:
        img_str = str(img_entry)
        if 'NO ASSET ID FOUND' in img_str:
            # Failed lookup = ERROR
            logger.error(f"Image asset lookup failed: {img_str}")
        elif 'excluded' in img_str.lower() or 'removed' in img_str.lower() or 'downgraded' in img_str.lower():
            # Planned removals/changes = WARNING
            logger.warning(img_str)
        else:
            # Successful mapping = INFO
            logger.info(f"Image processed: {img_str}")
    
    # Add migration summary to destination XML
    migration_summary = dest_structure.find('.//migration-summary')
    if migration_summary is not None:
        # Clear default content
        migration_summary.clear()
        
        # Use logger's formatted output (wrapped in <code>)
        summary_xhtml = logger.format_for_summary()
        
        # Parse and append as XML children
        try:
            temp = ET.fromstring(f'<temp>{summary_xhtml}</temp>')
            migration_summary.text = temp.text
            for child in temp:
                migration_summary.append(child)
        except ET.ParseError as e:
            # Fallback to text if parsing fails
            print(f"Warning: Could not parse migration summary as XML: {e}")
            migration_summary.text = summary_xhtml
    
    # Write to global log file (for batch operations)
    logger.write_to_global_log()
    
    # Write destination XML
    print(f"\nWriting destination: {destination_path}")
    
    # Pretty print
    ET.indent(dest_tree, space='    ')
    # Write as XML (content will be escaped, but CMS will unescape on read)
    dest_tree.write(destination_path, encoding='unicode', xml_declaration=False)
    
    stats['success'] = True
    stats['logger'] = logger  # Include logger in stats for batch operations
    return stats


if __name__ == '__main__':
    # Accept command-line arguments or use defaults
    # Usage: python xml_migrate_poc.py <origin_file> <dest_file> [--global-log <log_file>]
    global_log_path = None
    
    if len(sys.argv) >= 3:
        origin_file = sys.argv[1]
        dest_file = sys.argv[2]
        # Check for --global-log option
        if '--global-log' in sys.argv:
            log_idx = sys.argv.index('--global-log')
            if log_idx + 1 < len(sys.argv):
                global_log_path = sys.argv[log_idx + 1]
    else:
        # Default test file
        origin_file = "/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/migration-clean/about/history/index.xml"
        dest_file = "/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/migration-clean/about/history/index-destination.xml"
    
    print("=" * 80)
    print("PROOF OF CONCEPT: XML STRUCTURE MIGRATION")
    print("=" * 80)
    print()
    
    stats = migrate_single_file(origin_file, dest_file, global_log_path=global_log_path)
    
    print()
    print("=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)
    print(f"Success: {stats['success']}")
    print(f"Sections: {stats['sections_created']}")
    print(f"Content Items: {stats['content_items_created']}")
    
    # Print logger stats
    if 'logger' in stats:
        log_stats = stats['logger'].get_stats()
        print(f"\nLog Entries:")
        print(f"  Errors:   {log_stats['errors']}")
        print(f"  Warnings: {log_stats['warnings']}")
        print(f"  Info:     {log_stats['info']}")
    
    if stats['success']:
        print(f"\n✅ Destination file written: {dest_file}")
        if global_log_path:
            print(f"📋 Log appended to: {global_log_path}")
        print("\nNext steps:")
        print("1. Review the destination XML file")
        print("2. Check migration-summary field for log entries")
        print("3. Validate structure matches expected format")
    else:
        print("\n❌ Migration failed")
        sys.exit(1)
