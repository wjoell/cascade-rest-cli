"""
XML Mapping Utilities for Origin to Destination Migration.

Provides functions to map specific content types from origin to destination format:
- Text content (WYSIWYG split into heading+content pairs)
- Accordion content
- Action links
- Cards
- Stats
- Media/Video
- External blocks
"""

import re
import csv
from typing import List, Dict, Optional
from xml.etree import ElementTree as ET
from xml_analyzer import (
    parse_wysiwyg_to_sections,
    parse_wysiwyg_element_to_sections,
    get_wysiwyg_content,
    get_item_type,
    analyze_content_complexity
)

# Global cache for image asset ID lookups
_IMAGE_ASSET_CACHE = None

def load_image_asset_ids(csv_path: str = None) -> Dict[str, str]:
    """
    Load image asset ID mappings from CSV.
    
    Args:
        csv_path: Path to image_references_with_asset_ids.csv
        
    Returns:
        Dict mapping image names to publish API asset IDs
    """
    global _IMAGE_ASSET_CACHE
    
    if _IMAGE_ASSET_CACHE is not None:
        return _IMAGE_ASSET_CACHE
    
    if csv_path is None:
        csv_path = '/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/image_references_with_asset_ids.csv'
    
    _IMAGE_ASSET_CACHE = {}
    
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Map image name to asset_id
                image_name = row.get('name', '')
                asset_id = row.get('asset_id', '')
                if image_name and asset_id:
                    _IMAGE_ASSET_CACHE[image_name] = asset_id
    except FileNotFoundError:
        print(f"Warning: Could not load image asset CSV from {csv_path}")
    
    return _IMAGE_ASSET_CACHE


def clean_heading_text(heading_html: str) -> str:
    """
    Clean heading text by removing <strong> tags but keeping <em> tags.
    
    Args:
        heading_html: Raw heading HTML that may contain tags
        
    Returns:
        Cleaned HTML string
    """
    if not heading_html:
        return heading_html
    
    # Remove <strong> and </strong> tags
    cleaned = re.sub(r'</?strong>', '', heading_html)
    
    # Keep <em> tags as-is
    return cleaned


def clean_wysiwyg_content(wysiwyg_elem: ET.Element, images_found: List[str] = None):
    """
    Clean WYSIWYG content by:
    - Rewriting internal SLC links (remove https://www.sarahlawrence.edu, strip .xml)
    - Stripping aria-* and class attributes
    - Replacing non-breaking space entities with normal spaces
    - Removing self-closing tags (except br and wbr)
    - Stripping span, div, and img tags (promoting their content)
    - Logging image filenames for migration summary
    
    Args:
        wysiwyg_elem: WYSIWYG element to clean (modified in place)
        images_found: Optional list to append image filenames to
    """
    if wysiwyg_elem is None:
        return
    
    if images_found is None:
        images_found = []
    
    # Clean text content
    if wysiwyg_elem.text:
        wysiwyg_elem.text = wysiwyg_elem.text.replace('&#160;', ' ')
    
    # Process children (need to handle removals carefully)
    children_to_remove = []
    children_to_promote = []  # (child, insert_index)
    
    for idx, child in enumerate(list(wysiwyg_elem)):
        # Check for self-closing tags (no children and no text)
        is_self_closing = len(child) == 0 and not child.text
        
        # Remove self-closing tags except br and wbr
        if is_self_closing and child.tag not in ('br', 'wbr'):
            children_to_remove.append(child)
            continue
        
        # Handle img tags - log filename and remove
        if child.tag == 'img':
            src = child.get('src', '')
            if src:
                # Extract filename from path
                filename = src.split('/')[-1] if '/' in src else src
                images_found.append(filename)
            children_to_remove.append(child)
            continue
        
        # Handle span and div - promote their content
        if child.tag in ('span', 'div'):
            children_to_promote.append((child, idx))
            continue
        
        # Clean links
        if child.tag == 'a':
            href = child.get('href', '')
            
            # Rewrite internal SLC links
            if href.startswith('https://www.sarahlawrence.edu'):
                # Remove base URL
                path = href.replace('https://www.sarahlawrence.edu', '')
                
                # Handle empty path (just base URL)
                if not path or path == '/':
                    path = '/index'
                # Handle directory URLs (ending with /)
                elif path.endswith('/'):
                    # Strip trailing slash and append /index
                    path = path.rstrip('/') + '/index'
                # Strip .xml extension from managed assets
                elif path.endswith('.xml'):
                    path = path[:-4]
                
                child.set('href', path)
        
        # Strip class and aria-* attributes from all elements
        attrs_to_remove = []
        for attr in child.attrib.keys():
            if attr.startswith('aria-') or attr == 'class':
                attrs_to_remove.append(attr)
        for attr in attrs_to_remove:
            del child.attrib[attr]
        
        # Clean text and tail
        if child.text:
            child.text = child.text.replace('&#160;', ' ')
        if child.tail:
            child.tail = child.tail.replace('&#160;', ' ')
        
        # Recursively clean children
        clean_wysiwyg_content(child, images_found)
    
    # Remove marked elements
    for child in children_to_remove:
        wysiwyg_elem.remove(child)
    
    # Promote span/div content (in reverse to maintain indices)
    for child, idx in reversed(children_to_promote):
        # Get the child's content
        child_text = child.text or ''
        child_tail = child.tail or ''
        
        # Move child's children to parent at same position
        for grandchild in reversed(list(child)):
            wysiwyg_elem.insert(idx, grandchild)
        
        # Handle text content
        if idx > 0:
            # Append to previous sibling's tail
            prev = wysiwyg_elem[idx - 1]
            if prev.tail:
                prev.tail += child_text
            else:
                prev.tail = child_text
            # The tail of the removed element goes to the last inserted child
            if child_tail and len(child) > 0:
                wysiwyg_elem[idx + len(child) - 1].tail = child_tail
            elif child_tail:
                prev.tail = (prev.tail or '') + child_tail
        else:
            # Prepend to parent's text
            if wysiwyg_elem.text:
                wysiwyg_elem.text += child_text
            else:
                wysiwyg_elem.text = child_text
            # Tail goes to last inserted child or parent text
            if child_tail and len(child) > 0:
                wysiwyg_elem[len(child) - 1].tail = child_tail
            elif child_tail:
                wysiwyg_elem.text = (wysiwyg_elem.text or '') + child_tail
        
        # Remove the span/div element
        wysiwyg_elem.remove(child)


def copy_wysiwyg_content(source_wysiwyg_elem: ET.Element, dest_wysiwyg_elem: ET.Element, images_found: List[str] = None):
    """
    Copy WYSIWYG content from source to destination, preserving XML structure.
    Also cleans the content (links, aria attributes, entities, images).
    
    Args:
        source_wysiwyg_elem: Source <wysiwyg> element
        dest_wysiwyg_elem: Destination <wysiwyg> element to populate
        images_found: Optional list to append found image filenames to
    """
    if source_wysiwyg_elem is not None:
        # Copy text content
        if source_wysiwyg_elem.text:
            dest_wysiwyg_elem.text = source_wysiwyg_elem.text
        
        # Copy all child elements (deep copy to avoid modification issues)
        import copy
        for child in source_wysiwyg_elem:
            dest_wysiwyg_elem.append(copy.deepcopy(child))
        
        # Copy tail text (text after the last child)
        if source_wysiwyg_elem.tail:
            # Note: tail goes on the parent, but we're copying content
            pass
        
        # Clean the copied content
        clean_wysiwyg_content(dest_wysiwyg_elem, images_found)


def create_section_content_item(heading: str = "", heading_level: str = "h2", 
                                wysiwyg: str = "", source_wysiwyg_elem: ET.Element = None) -> ET.Element:
    """
    Create a group-section-content-item element with heading and WYSIWYG content.
    
    Args:
        heading: Heading text
        heading_level: h2, h3, h4, or h5
        wysiwyg: HTML content
        
    Returns:
        ET.Element for group-section-content-item
    """
    item = ET.Element('group-section-content-item')
    
    # Content item type (empty for basic text)
    content_type = ET.SubElement(item, 'content-item-type')
    
    # Add other empty fields from template
    ET.SubElement(item, 'layered-media-options')
    ET.SubElement(item, 'promotion-options').text = 'none'
    
    # Forms group (empty)
    forms = ET.SubElement(item, 'group-forms')
    ET.SubElement(forms, 'form-type').text = 'basin'
    ET.SubElement(forms, 'accessible-title')
    ET.SubElement(forms, 'form-id')
    ET.SubElement(forms, 'slate-redirect')
    
    # Promotion dates (empty)
    promo = ET.SubElement(item, 'promotion-dates')
    ET.SubElement(promo, 'promotion-days').text = 'all-day'
    ET.SubElement(promo, 'date-start')
    ET.SubElement(promo, 'date-end')
    ET.SubElement(promo, 'promotion-duration')
    
    # Featured story (empty)
    story = ET.SubElement(item, 'asset-page-featured-story')
    ET.SubElement(story, 'path').text = '/'
    
    # Eyebrow (empty)
    ET.SubElement(item, 'content-heading-eyebrow')
    
    # Heading stacks (empty)
    for _ in range(2):
        stack = ET.SubElement(item, 'group-heading-stack')
        ET.SubElement(stack, 'heading')
        ET.SubElement(stack, 'pl').text = '0'
    
    # Main content heading
    content_heading = ET.SubElement(item, 'group-content-heading')
    heading_text_elem = ET.SubElement(content_heading, 'heading-text')
    
    # Clean and parse heading (may contain <em> tags)
    if heading:
        cleaned_heading = clean_heading_text(heading)
        try:
            # Try to parse as HTML fragment
            temp = ET.fromstring(f'<temp>{cleaned_heading}</temp>')
            # Copy text and children
            heading_text_elem.text = temp.text
            for child in temp:
                heading_text_elem.append(child)
        except ET.ParseError:
            # If parsing fails, use as plain text
            heading_text_elem.text = cleaned_heading
    
    heading_link = ET.SubElement(content_heading, 'heading-link')
    ET.SubElement(heading_link, 'path').text = '/'
    
    # Subhead (disabled)
    ET.SubElement(item, 'bool-subhead').text = 'false'
    subhead = ET.SubElement(item, 'group-content-subheading')
    ET.SubElement(subhead, 'heading-text')
    ET.SubElement(subhead, 'heading-level').text = 'h2'
    subhead_link = ET.SubElement(subhead, 'heading-link')
    ET.SubElement(subhead_link, 'path').text = '/'
    
    # Cards group (empty)
    cards = ET.SubElement(item, 'group-cards')
    ET.SubElement(cards, 'card-options')
    card_item = ET.SubElement(cards, 'group-card-item')
    ET.SubElement(card_item, 'card-heading-eyebrow')
    card_heading = ET.SubElement(card_item, 'group-card-item-heading')
    ET.SubElement(card_heading, 'heading-text')
    card_heading_link = ET.SubElement(card_heading, 'heading-link')
    ET.SubElement(card_heading_link, 'path').text = '/'
    ET.SubElement(card_item, 'content-heading-cutline')
    
    # Card media (empty)
    media = ET.SubElement(card_item, 'group-single-media')
    ET.SubElement(media, 'media-type').text = 'img-pub-api'
    ET.SubElement(media, 'img-fit-y')
    ET.SubElement(media, 'img-fit-x')
    ET.SubElement(media, 'pub-api-asset-id')
    ET.SubElement(media, 'vimeo-id')
    ET.SubElement(media, 'youtube-id')
    img = ET.SubElement(media, 'img')
    ET.SubElement(img, 'path').text = '/'
    ET.SubElement(media, 'caption')
    ET.SubElement(media, 'shape').text = 'none'
    ET.SubElement(media, 'position').text = 'auto'
    ET.SubElement(media, 'size').text = 'md'
    
    ET.SubElement(card_item, 'wysiwyg')
    
    # Expandable story author (empty)
    author = ET.SubElement(card_item, 'expandable-story-author')
    ET.SubElement(author, 'author-name')
    ET.SubElement(author, 'class')
    ET.SubElement(author, 'discipline-program-label')
    prog = ET.SubElement(author, 'discipline-program-page')
    ET.SubElement(prog, 'path').text = '/'
    ET.SubElement(author, 'author-current-activity')
    
    # Links list (empty)
    links = ET.SubElement(card_item, 'links-list-item')
    ET.SubElement(links, 'link-label')
    linked = ET.SubElement(links, 'linked-asset')
    ET.SubElement(linked, 'path').text = '/'
    
    # Links list at item level (empty)
    links2 = ET.SubElement(item, 'links-list-item')
    ET.SubElement(links2, 'link-label')
    linked2 = ET.SubElement(links2, 'linked-asset')
    ET.SubElement(linked2, 'path').text = '/'
    
    # Main WYSIWYG content
    wysiwyg_elem = ET.SubElement(item, 'wysiwyg')
    if source_wysiwyg_elem is not None:
        # Copy directly from source element (preserves HTML without escaping)
        copy_wysiwyg_content(source_wysiwyg_elem, wysiwyg_elem)
    elif wysiwyg:
        # Fallback: parse HTML string (legacy)
        try:
            temp = ET.fromstring(f'<temp>{wysiwyg}</temp>')
            if temp.text:
                wysiwyg_elem.text = temp.text
            for child in temp:
                wysiwyg_elem.append(child)
        except ET.ParseError:
            # If parsing fails, use escaped text
            wysiwyg_elem.text = wysiwyg
    
    # Single media (empty)
    media2 = ET.SubElement(item, 'group-single-media')
    ET.SubElement(media2, 'media-type').text = 'img'
    ET.SubElement(media2, 'img-fit-y')
    ET.SubElement(media2, 'img-fit-x')
    ET.SubElement(media2, 'pub-api-asset-id')
    ET.SubElement(media2, 'vimeo-id')
    ET.SubElement(media2, 'youtube-id')
    img2 = ET.SubElement(media2, 'img')
    ET.SubElement(img2, 'path').text = '/'
    ET.SubElement(media2, 'caption')
    ET.SubElement(media2, 'shape').text = 'none'
    ET.SubElement(media2, 'position').text = 'auto'
    ET.SubElement(media2, 'size').text = 'md'
    
    # CTA button (disabled)
    ET.SubElement(item, 'use-cta').text = 'false'
    cta = ET.SubElement(item, 'group-cta-button')
    cta_inner = ET.SubElement(cta, 'cta')
    ET.SubElement(cta_inner, 'cta-label')
    cta_link = ET.SubElement(cta_inner, 'link')
    ET.SubElement(cta_link, 'path').text = '/'
    ET.SubElement(cta_inner, 'button-template').text = 'default'
    ET.SubElement(cta_inner, 'icon').text = 'iconCaretRight'
    ET.SubElement(cta, 'button-style').text = 'primary'
    
    # Complex content label (empty)
    ET.SubElement(item, 'complex-content-label')
    
    # Layered image (empty)
    layered = ET.SubElement(item, 'group-layered-image')
    ET.SubElement(layered, 'bg-img-pub-api-id')
    ET.SubElement(layered, 'bg-img-fit-y')
    ET.SubElement(layered, 'bg-img-fit-x')
    ET.SubElement(layered, 'image-source').text = 'publish-api'
    ET.SubElement(layered, 'pub-api-asset-id')
    img3 = ET.SubElement(layered, 'img')
    ET.SubElement(img3, 'path').text = '/'
    ET.SubElement(layered, 'fg-img-fit-y')
    ET.SubElement(layered, 'fg-img-fit-x')
    ET.SubElement(layered, 'image-caption-eyebrow')
    ET.SubElement(layered, 'layered-image-caption')
    
    # Accordion (empty)
    accordion = ET.SubElement(item, 'group-accordion')
    ET.SubElement(accordion, 'layout').text = 'large'
    panel = ET.SubElement(accordion, 'group-panel')
    ET.SubElement(panel, 'heading')
    ET.SubElement(panel, 'display').text = 'Collapsed'
    ET.SubElement(panel, 'wysiwyg')
    
    # Stats (empty)
    stats = ET.SubElement(item, 'group-stats')
    ET.SubElement(stats, 'stat-number')
    ET.SubElement(stats, 'stat-description')
    
    # Quote (empty)
    quote = ET.SubElement(item, 'quote')
    ET.SubElement(quote, 'quote-author')
    ET.SubElement(quote, 'quote-author-title')
    
    return item


def map_text_content(origin_item: ET.Element, exclusions: List[str], images_found: List[str] = None) -> List[ET.Element]:
    """
    Map origin Text type content to destination section content items.
    
    Splits WYSIWYG content on headings (h2-h5), creating separate content items
    for each heading+content pair.
    
    Args:
        origin_item: Origin group-primary/secondary item element
        exclusions: List to append XPath exclusions to
        images_found: Optional list to append found image filenames to
        
    Returns:
        List of destination group-section-content-item elements
    """
    content_items = []
    
    # Get WYSIWYG element
    wysiwyg_elem = origin_item.find('.//group-text/wysiwyg')
    
    if wysiwyg_elem is None:
        return content_items
    
    # Parse into sections (works with elements directly)
    sections = parse_wysiwyg_element_to_sections(wysiwyg_elem)
    
    # Create content item for each section
    for section in sections:
        # Create temporary WYSIWYG element with section content
        temp_wysiwyg = ET.Element('wysiwyg')
        
        # Rebuild content from content_elements
        first = True
        for elem_type, elem_data in section.get('content_elements', []):
            if elem_type == 'text':
                if first and not list(temp_wysiwyg):
                    # Text before first child
                    temp_wysiwyg.text = elem_data
                    first = False
                else:
                    # Text after a child - append to last child's tail
                    if list(temp_wysiwyg):
                        if temp_wysiwyg[-1].tail:
                            temp_wysiwyg[-1].tail += elem_data
                        else:
                            temp_wysiwyg[-1].tail = elem_data
                    else:
                        temp_wysiwyg.text = elem_data
            elif elem_type == 'element':
                # Deep copy to avoid modifying original, then clean
                import copy
                elem_copy = copy.deepcopy(elem_data)
                # Clean individual element
                clean_wysiwyg_content(elem_copy, images_found)
                temp_wysiwyg.append(elem_copy)
                first = False
        
        # Clean the temp WYSIWYG content (redundant since we clean each element, but ensures top-level text)
        clean_wysiwyg_content(temp_wysiwyg, images_found)
        
        item = create_section_content_item(
            heading=section['heading'],
            heading_level=section.get('heading_level', 'h2'),
            source_wysiwyg_elem=temp_wysiwyg
        )
        
        # Set content-item-type to text
        content_type = item.find('content-item-type')
        if content_type is not None:
            content_type.text = 'text'
        
        content_items.append(item)
    
    return content_items


def map_accordion_content(origin_item: ET.Element, exclusions: List[str], images_found: List[str] = None) -> List[ET.Element]:
    """
    Map origin Accordion type content to destination format.
    Creates ONE content item containing ALL panels.
    
    Args:
        origin_item: Origin group-primary item with type="Accordion"
        exclusions: List to append XPath exclusions to
        images_found: Optional list to append found image filenames to
        
    Returns:
        List with single accordion content item containing all panels
    """
    content_items = []
    
    # Find accordion group in origin
    accordion_group = origin_item.find('.//group-accordion')
    if accordion_group is None:
        return content_items
    
    # Get all panels
    panels = accordion_group.findall('.//group-panel')
    if not panels:
        return content_items
    
    # Create ONE content item with accordion
    item = create_section_content_item()
    
    # Set content-item-type to accordion
    content_type = item.find('content-item-type')
    if content_type is not None:
        content_type.text = 'accordion'
    
    # Find the accordion element in the item
    accordion = item.find('.//group-accordion')
    if accordion is not None:
        # Clear default panel
        for child in list(accordion):
            if child.tag == 'group-panel':
                accordion.remove(child)
        
        # Copy ALL panels
        for panel in panels:
            new_panel = ET.SubElement(accordion, 'group-panel')
            
            # Copy heading
            heading_node = panel.find('heading')
            heading_elem = ET.SubElement(new_panel, 'heading')
            if heading_node is not None and heading_node.text:
                heading_elem.text = heading_node.text
            
            # Copy display state
            display_node = panel.find('display')
            display_elem = ET.SubElement(new_panel, 'display')
            if display_node is not None and display_node.text:
                display_elem.text = display_node.text
            else:
                display_elem.text = 'Collapsed'
            
            # Copy WYSIWYG content
            wysiwyg_node = panel.find('wysiwyg')
            wysiwyg_elem = ET.SubElement(new_panel, 'wysiwyg')
            if wysiwyg_node is not None:
                copy_wysiwyg_content(wysiwyg_node, wysiwyg_elem, images_found)
    
    content_items.append(item)
    
    return content_items


def map_quote_content(origin_item: ET.Element, exclusions: List[str]) -> List[ET.Element]:
    """
    Map origin group-quote to destination quote content item.
    
    Args:
        origin_item: Origin group-primary item with group-quote
        exclusions: List to append XPath exclusions to
        
    Returns:
        List with single quote content item
    """
    content_items = []
    
    # Find group-quote
    quote_group = origin_item.find('.//group-quote')
    if quote_group is None:
        return content_items
    
    quote_text = quote_group.findtext('quote-text', '')
    quote_citation = quote_group.findtext('quote-citation-text', '')
    
    if not quote_text:
        return content_items
    
    # Create quote content item
    item = create_section_content_item()
    
    # Set content type to quote
    content_type = item.find('content-item-type')
    if content_type is not None:
        content_type.text = 'quote'
    
    # Set quote text in wysiwyg
    wysiwyg = item.find('.//wysiwyg')
    if wysiwyg is not None:
        wysiwyg.text = quote_text
    
    # Set citation in quote-author
    quote_elem = item.find('.//quote')
    if quote_elem is not None:
        author = quote_elem.find('quote-author')
        if author is not None:
            author.text = quote_citation
    
    content_items.append(item)
    return content_items


def map_list_index_to_cards(origin_item: ET.Element, exclusions: List[str], images_found: List[str] = None) -> List[ET.Element]:
    """
    Map origin List Index block to destination cards.
    
    Args:
        origin_item: Origin group-primary item with type="External Block" and group-block[type="List Index"]
        exclusions: List to append XPath exclusions to
        images_found: Optional list to append found image filenames to
        
    Returns:
        List of content items with cards
    """
    content_items = []
    
    # Find the List Index block
    group_block = origin_item.find('.//group-block')
    if group_block is None:
        return content_items
    
    block_type = group_block.findtext('type', '')
    if block_type != 'List Index':
        return content_items
    
    # Get block content with items
    block = group_block.find('block')
    if block is None:
        return content_items
    
    items = block.findall('.//item')
    if not items:
        return content_items
    
    # Load image asset mappings
    asset_map = load_image_asset_ids()
    
    # Create a content item with cards
    content_item = create_section_content_item()
    
    # Set content-item-type to cards
    content_type = content_item.find('content-item-type')
    if content_type is not None:
        content_type.text = 'cards'
    
    # Find the group-cards element
    cards_group = content_item.find('.//group-cards')
    if cards_group is None:
        return content_items
    
    # Set card-options to "default"
    card_options = cards_group.find('card-options')
    if card_options is not None:
        card_options.text = 'default'
    
    # Remove template card item
    for child in cards_group.findall('group-card-item'):
        cards_group.remove(child)
    
    # Process each item
    for item in items:
        visibility = item.findtext('visibility', 'on')
        if visibility != 'on':
            continue
        
        card_item = ET.SubElement(cards_group, 'group-card-item')
        
        # Card heading eyebrow (empty for now)
        ET.SubElement(card_item, 'card-heading-eyebrow')
        
        # Card heading
        card_heading_group = ET.SubElement(card_item, 'group-card-item-heading')
        heading_text_elem = ET.SubElement(card_heading_group, 'heading-text')
        heading = item.findtext('heading', '')
        if heading:
            heading_text_elem.text = heading
        
        # Heading link - all managed now, no distinction
        heading_link_elem = ET.SubElement(card_heading_group, 'heading-link')
        heading_link_type = item.findtext('heading-link-type', 'none')
        
        if heading_link_type == 'int':
            # Internal link
            int_link = item.find('heading-link')
            if int_link is not None:
                path = int_link.findtext('path', '/')
                ET.SubElement(heading_link_elem, 'path').text = path
            else:
                ET.SubElement(heading_link_elem, 'path').text = '/'
        elif heading_link_type == 'ext':
            # External link - will need to create link asset in CMS
            # For now, log as exclusion
            ext_link = item.findtext('ext-heading-link', '')
            if ext_link:
                exclusions.append(f"List Index item external link: {ext_link}")
            ET.SubElement(heading_link_elem, 'path').text = '/'
        else:
            ET.SubElement(heading_link_elem, 'path').text = '/'
        
        # Cutline
        ET.SubElement(card_item, 'content-heading-cutline')
        
        # Media
        media_group = ET.SubElement(card_item, 'group-single-media')
        ET.SubElement(media_group, 'media-type').text = 'img-pub-api'
        ET.SubElement(media_group, 'img-fit-y')
        ET.SubElement(media_group, 'img-fit-x')
        
        # Look up asset ID from image name
        image_elem = item.find('image')
        pub_api_id = ET.SubElement(media_group, 'pub-api-asset-id')
        if image_elem is not None:
            image_name = image_elem.findtext('name', '')
            if image_name and image_name in asset_map:
                pub_api_id.text = asset_map[image_name]
        
        ET.SubElement(media_group, 'vimeo-id')
        ET.SubElement(media_group, 'youtube-id')
        img_elem = ET.SubElement(media_group, 'img')
        ET.SubElement(img_elem, 'path').text = '/'
        ET.SubElement(media_group, 'caption')
        ET.SubElement(media_group, 'shape').text = 'none'
        ET.SubElement(media_group, 'position').text = 'auto'
        ET.SubElement(media_group, 'size').text = 'md'
        
        # WYSIWYG content
        wysiwyg_elem = ET.SubElement(card_item, 'wysiwyg')
        origin_wysiwyg = item.find('wysiwyg')
        if origin_wysiwyg is not None:
            copy_wysiwyg_content(origin_wysiwyg, wysiwyg_elem, images_found)
        
        # Author (empty)
        author = ET.SubElement(card_item, 'expandable-story-author')
        ET.SubElement(author, 'author-name')
        ET.SubElement(author, 'class')
        ET.SubElement(author, 'discipline-program-label')
        prog = ET.SubElement(author, 'discipline-program-page')
        ET.SubElement(prog, 'path').text = '/'
        ET.SubElement(author, 'author-current-activity')
        
        # Links list (empty)
        links = ET.SubElement(card_item, 'links-list-item')
        ET.SubElement(links, 'link-label')
        linked = ET.SubElement(links, 'linked-asset')
        ET.SubElement(linked, 'path').text = '/'
    
    content_items.append(content_item)
    return content_items


def map_intro_video(intro_elem: ET.Element, exclusions: List[str]) -> List[ET.Element]:
    """
    Map intro-video to media content item.
    Uses the content item's own group-single-media (not the card's).
    
    Args:
        intro_elem: group-intro element with intro-video
        exclusions: List to append XPath exclusions to
        
    Returns:
        List with single media content item if video exists
    """
    content_items = []
    
    intro_video = intro_elem.find('.//intro-video')
    if intro_video is None:
        return content_items
    
    video_source = intro_video.findtext('video-source', '')
    video_id = intro_video.findtext('video-id', '')
    
    if not video_id:
        return content_items
    
    # Create media content item
    item = create_section_content_item()
    
    # Set content type to media
    content_type = item.find('content-item-type')
    if content_type is not None:
        content_type.text = 'media'
    
    # Set media details in content item's own group-single-media
    # This is the second group-single-media (after cards group), which is the content item's own media
    all_media = item.findall('.//group-single-media')
    # The last one is the content item's own media (after cards and other structures)
    media_group = all_media[-1] if all_media else None
    
    if media_group is not None:
        # Set media type based on video source
        media_type = media_group.find('media-type')
        if media_type is not None:
            media_type.text = video_source if video_source else 'vimeo'
        
        # Set video ID in appropriate field
        if video_source == 'vimeo':
            vimeo_id = media_group.find('vimeo-id')
            if vimeo_id is not None:
                vimeo_id.text = video_id
        elif video_source == 'youtube':
            youtube_id = media_group.find('youtube-id')
            if youtube_id is not None:
                youtube_id.text = video_id
    
    content_items.append(item)
    return content_items


def map_button_navigation_group(origin_item: ET.Element, exclusions: List[str]) -> None:
    """
    Log button navigation groups as exclusions.
    
    Args:
        origin_item: Origin item with type="Button navigation group"
        exclusions: List to append exclusion details to
    """
    # Find all button links
    buttons = origin_item.findall('.//group-button-links')
    if not buttons:
        exclusions.append("Button navigation group (no buttons)")
        return
    
    button_details = []
    for button in buttons:
        label = button.findtext('button-link-label', '')
        ext_link = button.findtext('ext-button-link', '')
        int_link = button.find('button-link')
        
        if ext_link:
            button_details.append(f"{label} -> {ext_link}")
        elif int_link is not None:
            path = int_link.findtext('path', '')
            button_details.append(f"{label} -> {path}")
        else:
            button_details.append(label)
    
    exclusions.append(f"Button navigation group: {', '.join(button_details)}")


def log_heading_id_exclusions(origin_item: ET.Element, exclusions: List[str]) -> None:
    """
    Log heading IDs as exclusions (auto-generated in new system).
    
    Args:
        origin_item: Origin item that may contain heading-id
        exclusions: List to append exclusion details to
    """
    heading_id = origin_item.findtext('.//heading-id', '')
    if heading_id:
        exclusions.append(f"Heading ID: {heading_id}")


def map_action_links(origin_item: ET.Element, exclusions: List[str]) -> Optional[str]:
    """
    Map origin Action Links to XPath exclusion (not migrating these).
    
    Args:
        origin_item: Origin item with type="Action Links"
        exclusions: List to append XPath exclusions to
        
    Returns:
        None (logs exclusion)
    """
    # Action Links are being excluded - log for migration summary
    # The caller will add the XPath notation
    return None


def create_page_section(section_mode: str = "flow") -> ET.Element:
    """
    Create a group-page-section-item element.
    
    Args:
        section_mode: "flow" or "full"
        
    Returns:
        ET.Element for group-page-section-item
    """
    section = ET.Element('group-page-section-item')
    
    ET.SubElement(section, 'section-mode').text = section_mode
    ET.SubElement(section, 'content-section-type')
    ET.SubElement(section, 'interest-search-bg').text = 'false'
    ET.SubElement(section, 'eyebrow')
    ET.SubElement(section, 'content-heading')
    ET.SubElement(section, 'section-intro')
    ET.SubElement(section, 'interest-search-menu-label').text = "I'm interested in..."
    ET.SubElement(section, 'bool-section-heading-cta').text = 'false'
    ET.SubElement(section, 'section-heading-cta-group-label')
    
    # Section heading CTA (empty)
    heading_cta = ET.SubElement(section, 'section-heading-cta')
    cta = ET.SubElement(heading_cta, 'cta')
    ET.SubElement(cta, 'cta-label')
    link = ET.SubElement(cta, 'link')
    ET.SubElement(link, 'path').text = '/'
    ET.SubElement(cta, 'button-template').text = 'default'
    ET.SubElement(cta, 'icon').text = 'iconCaretRight'
    ET.SubElement(heading_cta, 'button-style').text = 'primary'
    
    ET.SubElement(section, 'animated-narrative-options')
    
    # Two column text blocks (empty)
    for _ in range(2):
        block = ET.SubElement(section, 'two-column-text-block')
        ET.SubElement(block, 'path').text = '/'
    
    ET.SubElement(section, 'disruptor-background').text = 'default'
    ET.SubElement(section, 'section-caption')
    
    # Layered image (empty)
    layered = ET.SubElement(section, 'group-section-layered-image')
    ET.SubElement(layered, 'bg-img-pub-api-id')
    ET.SubElement(layered, 'bg-img-fit-y')
    ET.SubElement(layered, 'bg-img-fit-x')
    ET.SubElement(layered, 'image-source').text = 'publish-api'
    ET.SubElement(layered, 'pub-api-asset-id')
    img = ET.SubElement(layered, 'img')
    ET.SubElement(img, 'path').text = '/'
    ET.SubElement(layered, 'fg-img-fit-y')
    ET.SubElement(layered, 'fg-img-fit-x')
    ET.SubElement(layered, 'image-caption-eyebrow')
    ET.SubElement(layered, 'layered-image-caption')
    
    ET.SubElement(section, 'bool-cards-carousel').text = 'false'
    ET.SubElement(section, 'collage-position').text = 'start'
    
    # NOTE: group-section-content-item nodes should be inserted here by caller
    # Use insert_content_items() helper function
    
    # Media or galleries (empty)
    media_galleries = ET.SubElement(section, 'media-or-galleries')
    ET.SubElement(media_galleries, 'media-single-or-gallery').text = 'single-image'
    
    # Single video (empty)
    video = ET.SubElement(media_galleries, 'group-single-video')
    ET.SubElement(video, 'video-source').text = 'publish-api'
    ET.SubElement(video, 'pub-api-asset-id')
    ET.SubElement(video, 'vimeo-id')
    ET.SubElement(video, 'youtube-id')
    ET.SubElement(video, 'caption')
    inline_cta = ET.SubElement(video, 'inline-cta')
    ET.SubElement(inline_cta, 'cta-label')
    link2 = ET.SubElement(inline_cta, 'link')
    ET.SubElement(link2, 'path').text = '/'
    ET.SubElement(video, 'size').text = 'md'
    ET.SubElement(video, 'use-cta').text = 'false'
    
    # Single image (empty)
    image = ET.SubElement(media_galleries, 'group-single-image')
    ET.SubElement(image, 'image-source').text = 'publish-api'
    ET.SubElement(image, 'pub-api-asset-id')
    img2 = ET.SubElement(image, 'img')
    ET.SubElement(img2, 'path').text = '/'
    inline_cta2 = ET.SubElement(image, 'inline-cta')
    ET.SubElement(inline_cta2, 'cta-label')
    link3 = ET.SubElement(inline_cta2, 'link')
    ET.SubElement(link3, 'path').text = '/'
    ET.SubElement(image, 'caption')
    ET.SubElement(image, 'size').text = 'md'
    ET.SubElement(image, 'use-cta').text = 'false'
    
    # Gallery (empty)
    gallery = ET.SubElement(media_galleries, 'publish-api-gallery')
    ET.SubElement(gallery, 'gallery-api-id')
    ET.SubElement(gallery, 'display-type').text = 'side-scroller'
    ET.SubElement(gallery, 'bool-download').text = 'false'
    ET.SubElement(gallery, 'down-url')
    ET.SubElement(gallery, 'controls').text = 'true'
    ET.SubElement(gallery, 'aspect-ratio').text = '1.5'
    ET.SubElement(gallery, 'img-fit').text = 'contain'
    ET.SubElement(gallery, 'img-captions').text = 'no'
    ET.SubElement(gallery, 'allow-fullscreen').text = 'true'
    ET.SubElement(gallery, 'chiron').text = 'false'
    ET.SubElement(gallery, 'chiron-position').text = 'default'
    img3 = ET.SubElement(gallery, 'chiron-img')
    ET.SubElement(img3, 'path').text = '/'
    
    # Section CTA (empty)
    ET.SubElement(section, 'use-cta').text = 'false'
    section_cta = ET.SubElement(section, 'group-cta-button')
    cta2 = ET.SubElement(section_cta, 'cta')
    ET.SubElement(cta2, 'cta-label')
    link4 = ET.SubElement(cta2, 'link')
    ET.SubElement(link4, 'path').text = '/'
    ET.SubElement(cta2, 'button-template').text = 'default'
    ET.SubElement(cta2, 'icon').text = 'iconCaretRight'
    ET.SubElement(section_cta, 'button-style').text = 'primary'
    
    ET.SubElement(section, 'white-background').text = 'true'
    ET.SubElement(section, 'bool-status').text = 'false'
    
    return section


def insert_content_items(section: ET.Element, content_items: List[ET.Element]):
    """
    Insert content items into a section at the correct position.
    
    Content items go after collage-position and before media-or-galleries.
    
    Args:
        section: group-page-section-item element
        content_items: List of group-section-content-item elements to insert
    """
    # Find the collage-position element
    collage_pos = section.find('collage-position')
    if collage_pos is None:
        # Fallback: just append
        for item in content_items:
            section.append(item)
        return
    
    # Get index of collage-position
    children = list(section)
    insert_index = children.index(collage_pos) + 1
    
    # Insert each content item
    for i, item in enumerate(content_items):
        section.insert(insert_index + i, item)


if __name__ == '__main__':
    print("XML Mapper utilities loaded. Use in migration scripts.")
