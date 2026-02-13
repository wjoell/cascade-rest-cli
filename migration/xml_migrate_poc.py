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
from xml_analyzer import (
    detect_active_regions,
    get_active_region_items,
    get_item_type,
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
    map_video_content,
    map_image_content,
    map_form_content,
    map_gallery_content,
    map_button_navigation_group,
    log_heading_id_exclusions,
    create_page_section,
    insert_content_items
)


def migrate_single_file(origin_path: str, destination_path: str) -> dict:
    """
    Migrate a single origin XML file to destination format.
    
    Args:
        origin_path: Path to origin .xml file
        destination_path: Path to destination -destination.xml file
        
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
    print(f"Page: {metadata.get('title', 'Unknown')}")
    print(f"Path: {metadata.get('path', 'Unknown')}")
    
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
            # Check for intro-video
            video_items = map_intro_video(intro_elem, stats['exclusions'])
            if video_items:
                # Use the first section for intro video
                insert_content_items(first_section, video_items)
                first_section.find('section-mode').text = 'flow'
                first_section_used = True
                stats['sections_created'] += 1
                stats['content_items_created'] += len(video_items)
                print(f"  → Populated first section with intro video ({len(video_items)} items)")
    
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
        
        for i, item in enumerate(items, 1):
            item_type = get_item_type(item)
            print(f"\n  Item {i}: Type={item_type}")
            
            content_items = []
            
            if item_type == "Text":
                # Map text content (splits on headings)
                content_items = map_text_content(item, stats['exclusions'], stats['images_found'])
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
                content_items = map_quote_content(item, stats['exclusions'])
                print(f"    → Created {len(content_items)} quote items")
            
            elif item_type == "Video":
                # Map video content
                content_items = map_video_content(item, stats['exclusions'])
                if content_items:
                    print(f"    → Created {len(content_items)} video items")
                else:
                    xpath = generate_xpath_exclusion(region, i, item_type="Video (empty)")
                    stats['exclusions'].append(xpath)
                    print(f"    → Excluded: {xpath}")
            
            elif item_type == "Image":
                # Map image content
                content_items = map_image_content(item, stats['exclusions'], stats['images_found'])
                if content_items:
                    print(f"    → Created {len(content_items)} image items")
                else:
                    print(f"    → Excluded: Image (no image or excluded)")
            
            elif item_type == "Form":
                # Map form content
                content_items = map_form_content(item, stats['exclusions'])
                if content_items:
                    print(f"    → Created {len(content_items)} form items")
                else:
                    print(f"    → Excluded: Form (no ID or excluded)")
            
            elif item_type == "Publish API Gallery":
                # Map gallery content (logs for manual placement)
                content_items = map_gallery_content(item, stats['exclusions'])
                print(f"    → Gallery logged for manual placement")
            
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
    
    # Add migration summary
    print(f"\n{'='*60}")
    print("Adding migration summary")
    print(f"{'='*60}")
    
    migration_summary = dest_structure.find('.//migration-summary')
    if migration_summary is not None:
        # Clear default content
        migration_summary.clear()
        
        # Build summary XHTML
        exclusions_html = ''
        if stats['exclusions']:
            exclusion_items = '\n'.join(f"<li>{ex}</li>" for ex in stats['exclusions'])
            exclusions_html = f"""
<h3>Exclusions</h3>
<ul>
{exclusion_items}
</ul>"""
        
        images_html = ''
        if stats['images_found']:
            # Get unique images
            unique_images = sorted(set(stats['images_found']))
            image_items = '\n'.join(f"<li>{img}</li>" for img in unique_images)
            images_html = f"""
<h3>Images Found in WYSIWYG (Stripped)</h3>
<ul>
{image_items}
</ul>"""
        
        summary_xhtml = f"""<h2>Migration Report</h2>
<h3>Statistics</h3>
<ul>
<li>Sections created: {stats['sections_created']}</li>
<li>Content items created: {stats['content_items_created']}</li>
<li>Items excluded: {len(stats['exclusions'])}</li>
<li>Images found: {len(set(stats['images_found']))}</li>
</ul>{exclusions_html}{images_html}
<h3>Source Page</h3>
<ul>
<li>Title: {metadata.get('title', 'Unknown')}</li>
<li>Path: {metadata.get('path', 'Unknown')}</li>
</ul>"""
        
        # Parse and append as XML children (not escaped text)
        try:
            temp = ET.fromstring(f'<temp>{summary_xhtml}</temp>')
            migration_summary.text = temp.text
            for child in temp:
                migration_summary.append(child)
        except ET.ParseError as e:
            # Fallback to text if parsing fails
            print(f"Warning: Could not parse migration summary as XML: {e}")
            migration_summary.text = summary_xhtml
    
    # Write destination XML
    print(f"\nWriting destination: {destination_path}")
    
    # Pretty print
    ET.indent(dest_tree, space='    ')
    # Write as XML (content will be escaped, but CMS will unescape on read)
    dest_tree.write(destination_path, encoding='unicode', xml_declaration=False)
    
    stats['success'] = True
    return stats


if __name__ == '__main__':
    # Accept command-line arguments or use defaults
    if len(sys.argv) >= 3:
        origin_file = sys.argv[1]
        dest_file = sys.argv[2]
    else:
        # Default test file
        origin_file = "/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/migration-clean/about/history/index.xml"
        dest_file = "/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/migration-clean/about/history/index-destination.xml"
    
    print("=" * 80)
    print("PROOF OF CONCEPT: XML STRUCTURE MIGRATION")
    print("=" * 80)
    print()
    
    stats = migrate_single_file(origin_file, dest_file)
    
    print()
    print("=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)
    print(f"Success: {stats['success']}")
    print(f"Sections: {stats['sections_created']}")
    print(f"Content Items: {stats['content_items_created']}")
    print(f"Exclusions: {len(stats['exclusions'])}")
    
    if stats['success']:
        print(f"\n✅ Destination file written: {dest_file}")
        print("\nNext steps:")
        print("1. Review the destination XML file")
        print("2. Check migration-summary field for exclusions")
        print("3. Validate structure matches expected format")
    else:
        print("\n❌ Migration failed")
        sys.exit(1)
