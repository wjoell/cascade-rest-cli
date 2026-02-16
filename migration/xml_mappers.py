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
- News article content (blockParaImg, floated images, usecaption handling)
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
                # Map by renamed_file (e.g., 'giving_fund_gianna-morin-760.jpg')
                renamed_file = row.get('renamed_file', '')
                asset_id = row.get('asset_id', '')
                if renamed_file and asset_id:
                    _IMAGE_ASSET_CACHE[renamed_file] = asset_id
                    # Also map by just the filename for easier lookup
                    filename = renamed_file.split('_')[-1] if '_' in renamed_file else renamed_file
                    if filename and asset_id:
                        _IMAGE_ASSET_CACHE[filename] = asset_id
                
                # Also map by original path for URL-based lookups
                original_path = row.get('original_path', '')
                if original_path and asset_id:
                    # Extract filename from URL
                    orig_filename = original_path.split('/')[-1] if '/' in original_path else original_path
                    if orig_filename:
                        _IMAGE_ASSET_CACHE[orig_filename] = asset_id
    except FileNotFoundError:
        print(f"Warning: Could not load image asset CSV from {csv_path}")
    
    return _IMAGE_ASSET_CACHE


def lookup_image_asset_id(filename: str) -> Optional[str]:
    """
    Look up the publish API asset ID for an image filename.
    
    Args:
        filename: Image filename (e.g., 'gianna-morin-760.jpg')
        
    Returns:
        Asset ID string or None if not found
    """
    cache = load_image_asset_ids()
    
    # Try exact match first
    if filename in cache:
        return cache[filename]
    
    # Try without path prefix
    base_filename = filename.split('/')[-1] if '/' in filename else filename
    if base_filename in cache:
        return cache[base_filename]
    
    return None


def extract_floated_image(wysiwyg_elem: ET.Element) -> Optional[Dict]:
    """
    Extract the first image with class 'left' or 'right' from WYSIWYG content.
    
    These images should be placed in group-single-media with prose-image type.
    
    Args:
        wysiwyg_elem: WYSIWYG XML element
        
    Returns:
        Dict with image info (src, alt, filename, position, asset_id) or None
    """
    if wysiwyg_elem is None:
        return None
    
    # Look for img tags with left/right class
    for elem in wysiwyg_elem.iter('img'):
        img_class = elem.get('class', '')
        if 'left' in img_class or 'right' in img_class:
            src = elem.get('src', '')
            alt = elem.get('alt', '')
            filename = src.split('/')[-1] if '/' in src else src
            position = 'left' if 'left' in img_class else 'right'
            asset_id = lookup_image_asset_id(filename)
            
            return {
                'src': src,
                'alt': alt,
                'filename': filename,
                'position': position,
                'asset_id': asset_id,
                'element': elem
            }
    
    return None


def extract_block_images(wysiwyg_elem: ET.Element) -> List[Dict]:
    """
    Extract images with 'blockParaImg' or 'block-centered' class.
    
    These images should become separate media content items.
    
    Args:
        wysiwyg_elem: WYSIWYG XML element
        
    Returns:
        List of dicts with image info
    """
    block_images = []
    
    if wysiwyg_elem is None:
        return block_images
    
    # Look for img tags with block classes
    for elem in wysiwyg_elem.iter('img'):
        img_class = elem.get('class', '')
        if 'blockParaImg' in img_class or 'block-centered' in img_class:
            src = elem.get('src', '')
            alt = elem.get('alt', '')
            filename = src.split('/')[-1] if '/' in src else src
            asset_id = lookup_image_asset_id(filename)
            
            block_images.append({
                'src': src,
                'alt': alt,
                'filename': filename,
                'asset_id': asset_id,
                'element': elem
            })
    
    return block_images


def set_group_single_media(media_elem: ET.Element, asset_id: str, position: str = 'auto', 
                           caption: str = '', media_type: str = 'img-pub-api'):
    """
    Configure a group-single-media element with publish API image.
    
    Args:
        media_elem: The group-single-media XML element
        asset_id: Publish API asset ID
        position: Image position ('auto', 'left', 'right')
        caption: Optional caption text
        media_type: Media type (default 'img-pub-api')
    """
    if media_elem is None:
        return
    
    # Set media type
    media_type_elem = media_elem.find('media-type')
    if media_type_elem is not None:
        media_type_elem.text = media_type
    
    # Set asset ID
    asset_id_elem = media_elem.find('pub-api-asset-id')
    if asset_id_elem is not None:
        asset_id_elem.text = asset_id or ''
    
    # Set position
    position_elem = media_elem.find('position')
    if position_elem is not None:
        position_elem.text = position
    
    # Set caption
    caption_elem = media_elem.find('caption')
    if caption_elem is not None:
        caption_elem.text = caption


def clean_heading_text(heading_html: str) -> str:
    """
    Clean heading text by removing unwanted tags.
    - Removes <strong> tags (promotes content)
    - Removes <img> tags entirely (including content/attributes)
    - Keeps <em> tags
    
    Args:
        heading_html: Raw heading HTML that may contain tags
        
    Returns:
        Cleaned HTML string
    """
    if not heading_html:
        return heading_html
    
    # Remove <img ...> tags entirely (self-closing or not)
    cleaned = re.sub(r'<img[^>]*/?>', '', heading_html)
    
    # Remove <strong> and </strong> tags (keep content)
    cleaned = re.sub(r'</?strong>', '', cleaned)
    
    # Strip leading/trailing whitespace that may result from removed tags
    cleaned = cleaned.strip()
    
    # Keep <em> tags as-is
    return cleaned


def remove_empty_elements(elem: ET.Element) -> bool:
    """
    Recursively remove empty elements from an element tree.
    
    An element is considered empty if it has:
    - No text content (or only whitespace)
    - No children (after recursively removing empty children)
    - Is not a self-closing tag that should be kept (br, wbr)
    
    Args:
        elem: Element to clean (modified in place)
        
    Returns:
        True if the element itself is empty and should be removed by parent
    """
    # Allowed self-closing/empty tags
    allowed_empty = ('br', 'wbr')
    
    # First, recursively process children
    children_to_remove = []
    for child in list(elem):
        if remove_empty_elements(child):
            children_to_remove.append(child)
    
    # Remove empty children
    for child in children_to_remove:
        # Preserve the child's tail by appending to previous sibling or parent text
        if child.tail and child.tail.strip():
            idx = list(elem).index(child)
            if idx > 0:
                prev = elem[idx - 1]
                prev.tail = (prev.tail or '') + child.tail
            else:
                elem.text = (elem.text or '') + child.tail
        elem.remove(child)
    
    # Check if this element is now empty
    if elem.tag in allowed_empty:
        return False
    
    has_text = elem.text and elem.text.strip()
    has_children = len(elem) > 0
    
    return not has_text and not has_children


def clean_wysiwyg_content(wysiwyg_elem: ET.Element, images_found: List[str] = None):
    """
    Clean WYSIWYG content by:
    - Rewriting internal SLC links (remove https://www.sarahlawrence.edu, strip .xml)
    - Stripping aria-* and class attributes
    - Replacing non-breaking space entities with normal spaces
    - Removing self-closing tags (except br and wbr)
    - Stripping span, div, u, and img tags (promoting their content)
    - Logging image filenames for migration summary
    - Removing empty elements after all processing
    
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
        
        # Handle img tags - log filename with asset ID and remove
        if child.tag == 'img':
            src = child.get('src', '')
            if src:
                # Extract filename from path
                filename = src.split('/')[-1] if '/' in src else src
                # Look up publish API asset ID
                asset_id = lookup_image_asset_id(filename)
                asset_id_str = asset_id if asset_id else 'NO ASSET ID FOUND'
                images_found.append(f"{filename} - {asset_id_str}")
            children_to_remove.append(child)
            continue
        
        # Handle span, div, and u - recursively clean then promote their content
        if child.tag in ('span', 'div', 'u'):
            # Recursively clean children BEFORE promoting
            clean_wysiwyg_content(child, images_found)
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
    
    # Promote span/div content (process each, recalculating index after removals)
    for child, _ in reversed(children_to_promote):
        # Recalculate current index (may have shifted after removals)
        try:
            current_idx = list(wysiwyg_elem).index(child)
        except ValueError:
            # Child was already removed somehow, skip
            continue
        
        # Get the child's content
        child_text = child.text or ''
        child_tail = child.tail or ''
        
        # Move child's children to parent at same position
        grandchildren = list(child)
        for grandchild in reversed(grandchildren):
            wysiwyg_elem.insert(current_idx, grandchild)
        
        # Handle text content
        if current_idx > 0:
            # Append to previous sibling's tail
            prev = wysiwyg_elem[current_idx - 1]
            if prev.tail:
                prev.tail += child_text
            else:
                prev.tail = child_text
            # The tail of the removed element goes to the last inserted child
            if child_tail and len(grandchildren) > 0:
                wysiwyg_elem[current_idx + len(grandchildren) - 1].tail = child_tail
            elif child_tail:
                prev.tail = (prev.tail or '') + child_tail
        else:
            # Prepend to parent's text
            if wysiwyg_elem.text:
                wysiwyg_elem.text += child_text
            else:
                wysiwyg_elem.text = child_text
            # Tail goes to last inserted child or parent text
            if child_tail and len(grandchildren) > 0:
                wysiwyg_elem[len(grandchildren) - 1].tail = child_tail
            elif child_tail:
                wysiwyg_elem.text = (wysiwyg_elem.text or '') + child_tail
        
        # Remove the span/div/u element
        wysiwyg_elem.remove(child)
    
    # Post-process: remove any empty elements that resulted from cleaning
    remove_empty_elements(wysiwyg_elem)


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


def clean_accordion_wysiwyg_content(wysiwyg_elem: ET.Element, panel_heading: str, 
                                     migration_notes: List[str] = None):
    """
    Clean WYSIWYG content for accordion panels with special handling:
    - Headings (h2-h5): Convert to <strong> and log the downgrade
    - Images: Remove and log with publish API ID
    
    Args:
        wysiwyg_elem: WYSIWYG element to clean (modified in place)
        panel_heading: The accordion panel heading (for logging context)
        migration_notes: List to append migration notes to (for migration-summary)
    """
    if wysiwyg_elem is None:
        return
    
    if migration_notes is None:
        migration_notes = []
    
    import copy as copy_module
    
    def process_element(elem):
        """Recursively process element and its children."""
        children_to_process = []
        
        for idx, child in enumerate(list(elem)):
            # Handle headings - convert to <strong>
            if child.tag in ('h2', 'h3', 'h4', 'h5'):
                heading_text = ''.join(child.itertext())
                heading_level = child.tag
                
                # Log the downgrade
                migration_notes.append(
                    f"'{heading_text}' was downgraded from {heading_level} to strong in accordion '{panel_heading}'"
                )
                
                # Create <strong> element with same content
                strong_elem = ET.Element('strong')
                strong_elem.text = child.text
                strong_elem.tail = child.tail
                for grandchild in child:
                    strong_elem.append(copy_module.deepcopy(grandchild))
                
                # Replace heading with strong
                elem.insert(idx, strong_elem)
                elem.remove(child)
                continue
            
            # Handle images - remove and log with asset ID
            if child.tag == 'img':
                src = child.get('src', '')
                filename = src.split('/')[-1] if '/' in src else src
                
                # Look up publish API asset ID
                asset_id = lookup_image_asset_id(filename)
                asset_id_str = asset_id if asset_id else 'NO ASSET ID FOUND'
                
                # Log the removal
                migration_notes.append(
                    f"{filename} - {asset_id_str} was removed from accordion '{panel_heading}'"
                )
                
                # Remove the image
                elem.remove(child)
                continue
            
            # Recursively process other elements
            children_to_process.append(child)
        
        for child in children_to_process:
            process_element(child)
    
    # Process the WYSIWYG element
    process_element(wysiwyg_elem)
    
    # Also run standard cleaning (links, attributes, etc.)
    # Note: This will also catch nested images, but we've already logged them
    clean_wysiwyg_content(wysiwyg_elem)


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
    
    # Main content heading (empty for flow mode - use subheading instead)
    content_heading = ET.SubElement(item, 'group-content-heading')
    ET.SubElement(content_heading, 'heading-text')
    heading_link = ET.SubElement(content_heading, 'heading-link')
    ET.SubElement(heading_link, 'path').text = '/'
    
    # Subheading - used for headings in flow mode (has heading-level field)
    ET.SubElement(item, 'bool-subhead').text = 'true' if heading else 'false'
    subhead = ET.SubElement(item, 'group-content-subheading')
    subhead_text_elem = ET.SubElement(subhead, 'heading-text')
    
    # Clean and parse heading (may contain <em> tags)
    if heading:
        cleaned_heading = clean_heading_text(heading)
        try:
            # Try to parse as HTML fragment
            temp = ET.fromstring(f'<temp>{cleaned_heading}</temp>')
            # Copy text and children
            subhead_text_elem.text = temp.text
            for child in temp:
                subhead_text_elem.append(child)
        except ET.ParseError:
            # If parsing fails, use as plain text
            subhead_text_elem.text = cleaned_heading
    
    # Set heading level to match source (h2, h3, h4, h5)
    ET.SubElement(subhead, 'heading-level').text = heading_level
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


def create_media_content_item(asset_id: str, alt_text: str = '', caption: str = '') -> ET.Element:
    """
    Create a media content item with publish API image.
    
    Args:
        asset_id: Publish API asset ID
        alt_text: Image alt text (for logging)
        caption: Optional caption
        
    Returns:
        ET.Element for group-section-content-item with media type
    """
    item = create_section_content_item()
    
    # Set content-item-type to media
    content_type = item.find('content-item-type')
    if content_type is not None:
        content_type.text = 'media'
    
    # Configure group-single-media (the one directly under group-section-content-item)
    media_elem = item.find('group-single-media')
    if media_elem is not None:
        set_group_single_media(media_elem, asset_id, position='auto', caption=caption)
    
    return item


def map_text_content(origin_item: ET.Element, exclusions: List[str], images_found: List[str] = None,
                     item_heading: Dict = None) -> List[Dict]:
    """
    Map origin Text type content to destination section content items.
    
    Splits WYSIWYG content on headings (h2-h5), creating separate content items
    for each heading+content pair.
    
    Handles images specially:
    - Images with class 'left' or 'right': Use prose-image type, set group-single-media
    - Images with class 'blockParaImg' or 'block-centered': Create separate media items
    
    Handles h2→h3 pattern:
    - When h2 has no content and is followed by h3, a new section should be created
    - The h2 becomes the section heading (content-heading)
    - The h3 becomes the content item's subheading
    
    Args:
        origin_item: Origin group-primary/secondary item element
        exclusions: List to append XPath exclusions to
        images_found: Optional list to append found image filenames to
        item_heading: Optional dict with 'text' and 'level' for item-level section heading
                     (from <section-heading> field, not WYSIWYG)
        
    Returns:
        List of dicts with:
        - 'item': group-section-content-item element
        - 'section_heading': optional h2 text that should become section heading (for h2→h3 pattern)
    """
    import copy
    content_items = []
    
    if images_found is None:
        images_found = []
    
    # Get WYSIWYG element
    wysiwyg_elem = origin_item.find('.//group-text/wysiwyg')
    
    if wysiwyg_elem is None:
        return content_items
    
    # Track images found in headings (for logging)
    heading_images = []
    
    # Parse into sections (works with elements directly)
    sections = parse_wysiwyg_element_to_sections(wysiwyg_elem, heading_images)
    
    # Log heading images for migration summary
    for img_info in heading_images:
        # Add to images_found with context
        img_entry = f"{img_info['filename']} ({img_info['context']}) - needs manual placement"
        images_found.append(img_entry)
    
    # Track if we've used a floated image (only first one per text block)
    floated_image_used = False
    
    # Create content item for each section
    for section_idx, section in enumerate(sections):
        # Create temporary WYSIWYG element with section content
        temp_wysiwyg = ET.Element('wysiwyg')
        
        # Track floated and block images in this section
        # First check if heading had a floated image
        section_floated_image = None
        heading_floated = section.get('floated_image')
        if heading_floated and not floated_image_used:
            # Use floated image from heading
            asset_id = lookup_image_asset_id(heading_floated['filename'])
            section_floated_image = {
                'filename': heading_floated['filename'],
                'alt': heading_floated.get('alt', ''),
                'position': heading_floated.get('position', 'right'),
                'asset_id': asset_id
            }
            floated_image_used = True
            
            # Log
            if asset_id:
                images_found.append(f"{heading_floated['filename']} (floated {section_floated_image['position']} in heading) - mapped to asset {asset_id}")
            else:
                images_found.append(f"{heading_floated['filename']} (floated {section_floated_image['position']} in heading) - NO ASSET ID FOUND")
        
        section_block_images = []
        
        # Rebuild content from content_elements
        first = True
        for elem_type, elem_data in section.get('content_elements', []):
            if elem_type == 'text':
                if first and not list(temp_wysiwyg):
                    temp_wysiwyg.text = elem_data
                    first = False
                else:
                    if list(temp_wysiwyg):
                        if temp_wysiwyg[-1].tail:
                            temp_wysiwyg[-1].tail += elem_data
                        else:
                            temp_wysiwyg[-1].tail = elem_data
                    else:
                        temp_wysiwyg.text = elem_data
            elif elem_type == 'element':
                elem_copy = copy.deepcopy(elem_data)
                
                # Check for images with special classes
                if elem_copy.tag == 'img':
                    img_class = elem_copy.get('class', '')
                    src = elem_copy.get('src', '')
                    alt = elem_copy.get('alt', '')
                    filename = src.split('/')[-1] if '/' in src else src
                    
                    # Check for floated image (left/right class) - only use first one
                    if ('left' in img_class or 'right' in img_class) and not floated_image_used:
                        position = 'left' if 'left' in img_class else 'right'
                        asset_id = lookup_image_asset_id(filename)
                        
                        section_floated_image = {
                            'filename': filename,
                            'alt': alt,
                            'position': position,
                            'asset_id': asset_id
                        }
                        floated_image_used = True
                        
                        # Log
                        if asset_id:
                            images_found.append(f"{filename} (floated {position}) - mapped to asset {asset_id}")
                        else:
                            images_found.append(f"{filename} (floated {position}) - NO ASSET ID FOUND")
                        
                        # Don't add img to WYSIWYG - it goes in group-single-media
                        continue
                    
                    # Check for block image (blockParaImg/block-centered)
                    elif 'blockParaImg' in img_class or 'block-centered' in img_class:
                        asset_id = lookup_image_asset_id(filename)
                        
                        section_block_images.append({
                            'filename': filename,
                            'alt': alt,
                            'asset_id': asset_id
                        })
                        
                        # Log
                        if asset_id:
                            images_found.append(f"{filename} (block image) - mapped to asset {asset_id}")
                        else:
                            images_found.append(f"{filename} (block image) - NO ASSET ID FOUND")
                        
                        # Don't add img to WYSIWYG - it becomes separate media item
                        continue
                
                # Clean and add non-image elements (images without special classes get stripped by clean_wysiwyg_content)
                clean_wysiwyg_content(elem_copy, images_found)
                temp_wysiwyg.append(elem_copy)
                first = False
        
        # Clean the temp WYSIWYG content
        clean_wysiwyg_content(temp_wysiwyg, images_found)
        
        # Determine heading and level:
        # - If section has heading from WYSIWYG, use that
        # - If this is the first/only section and item_heading is provided, use item_heading
        use_heading = section['heading']
        use_heading_level = section.get('heading_level', 'h2')
        
        if not use_heading and section_idx == 0 and item_heading:
            # Use item-level section heading (from <section-heading> field)
            use_heading = item_heading.get('text', '')
            use_heading_level = item_heading.get('level', 'h2')
        
        # Create the content item
        item = create_section_content_item(
            heading=use_heading,
            heading_level=use_heading_level,
            source_wysiwyg_elem=temp_wysiwyg
        )
        
        # Determine content type and configure media
        content_type = item.find('content-item-type')
        if section_floated_image and section_floated_image.get('asset_id'):
            # Use prose-image when we have a floated image with asset ID
            if content_type is not None:
                content_type.text = 'prose-image'
            
            # Configure group-single-media (the one at content item level, not inside cards)
            # Use XPath to find direct child, not the one nested in group-card-item
            media_elems = item.findall('./group-single-media')
            media_elem = media_elems[0] if media_elems else None
            if media_elem is not None:
                set_group_single_media(
                    media_elem, 
                    section_floated_image['asset_id'],
                    position=section_floated_image['position']
                )
        else:
            # Standard prose
            if content_type is not None:
                content_type.text = 'prose'
        
        # Get section_heading if h2→h3 pattern was detected
        section_heading = section.get('section_heading')
        
        content_items.append({
            'item': item,
            'section_heading': section_heading  # h2 text if h2→h3 pattern, else None
        })
        
        # Create separate media items for block images
        for block_img in section_block_images:
            if block_img.get('asset_id'):
                media_item = create_media_content_item(
                    block_img['asset_id'],
                    alt_text=block_img.get('alt', '')
                )
                content_items.append({
                    'item': media_item,
                    'section_heading': None
                })
    
    return content_items


def map_accordion_content(origin_item: ET.Element, exclusions: List[str], 
                          images_found: List[str] = None) -> List[ET.Element]:
    """
    Map origin Accordion type content to destination format.
    Creates ONE content item containing ALL panels.
    
    Special handling for accordion content:
    - Headings (h2-h5): Converted to <strong> and logged
    - Images: Removed and logged with publish API ID
    
    Args:
        origin_item: Origin group-primary item with type="Accordion"
        exclusions: List to append XPath exclusions to
        images_found: Optional list to append found image filenames to
                     (also used for migration notes about accordions)
        
    Returns:
        List with single accordion content item containing all panels
    """
    content_items = []
    
    if images_found is None:
        images_found = []
    
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
        
        # Copy panels (excluding those with display="Off")
        for panel in panels:
            # Check display state - skip panels with display="Off"
            display_node = panel.find('display')
            display_value = display_node.text if display_node is not None else 'Collapsed'
            if display_value == 'Off':
                # Log exclusion
                heading_node = panel.find('heading')
                panel_heading = heading_node.text.strip() if heading_node is not None and heading_node.text else 'Untitled'
                images_found.append(f"Accordion panel '{panel_heading}' excluded (display=Off)")
                continue
            
            new_panel = ET.SubElement(accordion, 'group-panel')
            
            # Copy heading
            heading_node = panel.find('heading')
            heading_elem = ET.SubElement(new_panel, 'heading')
            panel_heading = ''
            if heading_node is not None and heading_node.text:
                panel_heading = heading_node.text
                heading_elem.text = panel_heading
            
            # Copy display state
            display_elem = ET.SubElement(new_panel, 'display')
            display_elem.text = display_value
            
            # Copy and clean WYSIWYG content with accordion-specific handling
            wysiwyg_node = panel.find('wysiwyg')
            wysiwyg_elem = ET.SubElement(new_panel, 'wysiwyg')
            if wysiwyg_node is not None:
                # First copy the content
                import copy
                if wysiwyg_node.text:
                    wysiwyg_elem.text = wysiwyg_node.text
                for child in wysiwyg_node:
                    wysiwyg_elem.append(copy.deepcopy(child))
                
                # Then clean with accordion-specific handling
                # This will log headings converted to strong and images removed
                clean_accordion_wysiwyg_content(wysiwyg_elem, panel_heading, images_found)
    
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


def extract_video_id(url: str) -> tuple:
    """
    Extract video ID and source type from embed URL.
    
    Args:
        url: Full embed URL (YouTube or Vimeo)
        
    Returns:
        Tuple of (video_id, source_type) where source_type is 'vimeo' or 'youtube'
    """
    if not url:
        return ('', '')
    
    # Vimeo patterns:
    # https://player.vimeo.com/video/761484790
    # https://vimeo.com/761484790
    if 'vimeo.com' in url:
        # Extract ID after /video/ or last path segment
        match = re.search(r'/video/(\d+)', url)
        if match:
            return (match.group(1), 'vimeo')
        match = re.search(r'vimeo\.com/(\d+)', url)
        if match:
            return (match.group(1), 'vimeo')
    
    # YouTube patterns:
    # https://www.youtube.com/embed/vg2iN-8eHBo
    # https://www.youtube.com/watch?v=vg2iN-8eHBo
    # https://youtu.be/vg2iN-8eHBo
    if 'youtube.com' in url or 'youtu.be' in url:
        # Embed format
        match = re.search(r'/embed/([\w-]+)', url)
        if match:
            return (match.group(1), 'youtube')
        # Watch format
        match = re.search(r'[?&]v=([\w-]+)', url)
        if match:
            return (match.group(1), 'youtube')
        # Short format
        match = re.search(r'youtu\.be/([\w-]+)', url)
        if match:
            return (match.group(1), 'youtube')
    
    return ('', '')


def map_video_content(origin_item: ET.Element, exclusions: List[str]) -> List[ET.Element]:
    """
    Map Video type content from group-primary/group-secondary.
    Extracts video ID from embed URL and creates media content item.
    
    Args:
        origin_item: Origin item with type="Video"
        exclusions: List to append XPath exclusions to
        
    Returns:
        List with single media content item if video exists
    """
    content_items = []
    
    group_video = origin_item.find('.//group-video')
    if group_video is None:
        return content_items
    
    # Get URL and extract video ID
    url = group_video.findtext('url', '')
    title = group_video.findtext('title', '')
    caption = group_video.findtext('text-video-caption', '')
    
    video_id, source_type = extract_video_id(url)
    
    if not video_id:
        # Log exclusion for videos we can't parse
        if url and url != 'https://www.youtube.com/embed/':
            exclusions.append(f"Video (unparseable URL): {url}")
        return content_items
    
    # Create media content item
    item = create_section_content_item()
    
    # Set content type to media
    content_type = item.find('content-item-type')
    if content_type is not None:
        content_type.text = 'media'
    
    # Set media details in the content item's group-single-media
    all_media = item.findall('.//group-single-media')
    media_group = all_media[-1] if all_media else None
    
    if media_group is not None:
        # Set media type
        media_type = media_group.find('media-type')
        if media_type is not None:
            media_type.text = source_type
        
        # Set video ID
        if source_type == 'vimeo':
            vimeo_elem = media_group.find('vimeo-id')
            if vimeo_elem is not None:
                vimeo_elem.text = video_id
        elif source_type == 'youtube':
            youtube_elem = media_group.find('youtube-id')
            if youtube_elem is not None:
                youtube_elem.text = video_id
        
        # Set caption if present
        caption_elem = media_group.find('caption')
        if caption_elem is not None and (caption or title):
            caption_elem.text = caption or title
    
    content_items.append(item)
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


def map_image_content(origin_item: ET.Element, exclusions: List[str], images_found: List[str] = None) -> List[ET.Element]:
    """
    Map Image type content from group-primary/group-secondary.
    Uses publish API approach - looks up asset ID from CSV.
    
    Args:
        origin_item: Origin item with type="Image"
        exclusions: List to append XPath exclusions to
        images_found: Optional list to append found image filenames to
        
    Returns:
        List with single media content item if image exists
    """
    content_items = []
    
    if images_found is None:
        images_found = []
    
    group_image = origin_item.find('.//group-image')
    if group_image is None:
        return content_items
    
    # Get image path and filename
    file_image = group_image.find('.//file-image')
    image_path = ''
    filename = ''
    if file_image is not None:
        image_path = file_image.findtext('path', '')
        filename = file_image.findtext('name', '')  # Get the filename directly
        if not filename and image_path:
            filename = image_path.split('/')[-1] if '/' in image_path else image_path
    
    # Get other image properties
    img_alt = group_image.findtext('img-alt', '')
    img_caption = group_image.findtext('img-caption-text', '')
    img_layout = group_image.findtext('img-layout', 'full')  # full, callout, etc.
    
    if not filename:
        exclusions.append("Image (no image selected)")
        return content_items
    
    # Look up asset ID from CSV
    asset_id = lookup_image_asset_id(filename)
    
    # Log image for tracking
    if asset_id:
        images_found.append(f"{filename} (group-image) - mapped to asset {asset_id}")
    else:
        images_found.append(f"{filename} (group-image) - NO ASSET ID FOUND")
    
    # Create media content item
    item = create_section_content_item()
    
    # Set content type to media
    content_type = item.find('content-item-type')
    if content_type is not None:
        content_type.text = 'media'
    
    # Set media details - use the item-level group-single-media
    all_media = item.findall('.//group-single-media')
    media_group = all_media[-1] if all_media else None
    
    if media_group is not None:
        # Use publish API approach
        set_group_single_media(
            media_group,
            asset_id=asset_id or '',
            position='auto',
            caption=img_caption,
            media_type='img-pub-api'
        )
        
        # Set size based on layout
        size_elem = media_group.find('size')
        if size_elem is not None:
            if img_layout == 'full':
                size_elem.text = 'lg'
            elif img_layout == 'callout':
                size_elem.text = 'md'
            else:
                size_elem.text = 'md'
    
    content_items.append(item)
    return content_items


def map_form_content(origin_item: ET.Element, exclusions: List[str]) -> List[ET.Element]:
    """
    Map Form type content from group-primary/group-secondary.
    Handles Hubspot, Formsite, Formstack, and Slate form types.
    
    Args:
        origin_item: Origin item with type="Form"
        exclusions: List to append XPath exclusions to
        
    Returns:
        List with single form content item if form exists
    """
    content_items = []
    
    group_form = origin_item.find('.//group-form')
    if group_form is None:
        return content_items
    
    # Get form properties
    form_type = group_form.findtext('type', '')  # Hubspot, Formsite, Formstack, Slate
    form_id = group_form.findtext('id', '')
    form_title = group_form.findtext('form-title', '')
    
    if not form_id:
        exclusions.append(f"Form (no ID): {form_type}")
        return content_items
    
    # Create content item
    item = create_section_content_item()
    
    # Set content type to form
    content_type = item.find('content-item-type')
    if content_type is not None:
        content_type.text = 'form'
    
    # Find and update the group-forms element
    forms_group = item.find('.//group-forms')
    if forms_group is not None:
        # Map form type (origin uses different naming)
        form_type_elem = forms_group.find('form-type')
        if form_type_elem is not None:
            # Map origin types to destination types
            type_map = {
                'Hubspot': 'hubspot',
                'Formsite': 'formsite',
                'Formstack': 'formstack',
                'Slate': 'slate',
            }
            form_type_elem.text = type_map.get(form_type, 'basin')
        
        # Set form ID
        form_id_elem = forms_group.find('form-id')
        if form_id_elem is not None:
            form_id_elem.text = form_id
        
        # Set accessible title
        title_elem = forms_group.find('accessible-title')
        if title_elem is not None and form_title:
            title_elem.text = form_title
    
    content_items.append(item)
    return content_items


def map_gallery_content(origin_item: ET.Element, exclusions: List[str]) -> List[ET.Element]:
    """
    Map Publish API Gallery type content from group-primary/group-secondary.
    
    Args:
        origin_item: Origin item with type="Publish API Gallery"
        exclusions: List to append XPath exclusions to
        
    Returns:
        List with single gallery content item if gallery exists
    """
    content_items = []
    
    gallery = origin_item.find('.//publish-api-gallery')
    if gallery is None:
        return content_items
    
    # Get gallery ID
    gallery_id = gallery.findtext('gallery-api-id', '')
    
    if not gallery_id:
        exclusions.append("Publish API Gallery (no gallery ID)")
        return content_items
    
    # Get display properties
    display_type = gallery.findtext('display-type', 'carousel')
    img_fit = gallery.findtext('img-fit', 'cover')
    aspect_ratio = gallery.findtext('aspect-ratio', '1.5')
    allow_fullscreen = gallery.findtext('allow-fullscreen', 'true')
    img_captions = gallery.findtext('img-captions', 'no')
    
    # Create content item
    item = create_section_content_item()
    
    # Set content type to gallery
    content_type = item.find('content-item-type')
    if content_type is not None:
        content_type.text = 'gallery'
    
    # Note: The actual gallery configuration goes in the section's media-or-galleries,
    # not in the content item. For now, we'll log the gallery ID for manual placement.
    exclusions.append(f"Gallery ID: {gallery_id} (type: {display_type}, needs manual placement in section media-or-galleries)")
    
    # Return empty - galleries need special handling at section level
    return []


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


def create_page_section(section_mode: str = "flow", content_heading: str = None) -> ET.Element:
    """
    Create a group-page-section-item element.
    
    Args:
        section_mode: "flow" or "full"
        content_heading: Optional heading text for the section (h2 level)
        
    Returns:
        ET.Element for group-page-section-item
    """
    section = ET.Element('group-page-section-item')
    
    ET.SubElement(section, 'section-mode').text = section_mode
    ET.SubElement(section, 'content-section-type')
    ET.SubElement(section, 'interest-search-bg').text = 'false'
    ET.SubElement(section, 'eyebrow')
    heading_elem = ET.SubElement(section, 'content-heading')
    if content_heading:
        heading_elem.text = content_heading
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


def map_news_content(content_elem: ET.Element, images_found: List[str] = None) -> List[Dict]:
    """
    Map news article <content> element to destination content items.
    
    Handles two image patterns:
    1. blockParaImg (full-width): Own content item with content-item-type="media", size="lg"
    2. .right (floated): prose-image type with prose split around the image
    
    Caption handling for 'usecaption' class:
    - Extract alt text as caption for group-single-media
    - Look up Publish API ID from CSV
    
    Args:
        content_elem: The <content> element from news XML
        images_found: Optional list to append found image info to
        
    Returns:
        List of dicts with:
        - 'item': group-section-content-item element
        - 'section_heading': None (news items don't use h2→h3 pattern)
    """
    import copy
    content_items = []
    
    if content_elem is None:
        return content_items
    
    if images_found is None:
        images_found = []
    
    # Parse content HTML structure - content is typically a series of <p> tags
    # with images interspersed
    paragraphs = []
    current_prose_elements = []
    
    for child in content_elem:
        if child.tag == 'p':
            # Check if this paragraph contains an image
            img_elem = child.find('.//img')
            if img_elem is not None:
                img_class = img_elem.get('class', '')
                src = img_elem.get('src', '')
                alt = img_elem.get('alt', '')
                filename = src.split('/')[-1] if '/' in src else src
                has_usecaption = 'usecaption' in img_class
                
                # Determine caption from alt text if usecaption class
                caption = alt if has_usecaption else ''
                
                # Look up asset ID
                asset_id = lookup_image_asset_id(filename)
                
                if 'blockParaImg' in img_class:
                    # Full-width block image - becomes its own media content item
                    # First, flush any accumulated prose
                    if current_prose_elements:
                        paragraphs.append({
                            'type': 'prose',
                            'elements': current_prose_elements
                        })
                        current_prose_elements = []
                    
                    # Add the block image
                    paragraphs.append({
                        'type': 'block_image',
                        'filename': filename,
                        'caption': caption,
                        'alt': alt if not has_usecaption else '',  # Clear alt if used as caption
                        'asset_id': asset_id
                    })
                    
                    # Log
                    if asset_id:
                        images_found.append(f"{filename} (blockParaImg) - mapped to asset {asset_id}")
                    else:
                        images_found.append(f"{filename} (blockParaImg) - NO ASSET ID FOUND")
                
                elif 'right' in img_class or 'left' in img_class:
                    # Floated image - becomes prose-image with text wrapped around
                    position = 'right' if 'right' in img_class else 'left'
                    
                    # First, flush any accumulated prose (up to this point)
                    if current_prose_elements:
                        paragraphs.append({
                            'type': 'prose',
                            'elements': current_prose_elements
                        })
                        current_prose_elements = []
                    
                    # The paragraph containing the image and any text
                    # Create a clean copy without the image
                    p_copy = copy.deepcopy(child)
                    for img_to_remove in p_copy.findall('.//img'):
                        # Get parent and remove img
                        parent = p_copy
                        for potential_parent in p_copy.iter():
                            if img_to_remove in list(potential_parent):
                                parent = potential_parent
                                break
                        if img_to_remove in list(parent):
                            # Preserve tail text
                            if img_to_remove.tail:
                                idx = list(parent).index(img_to_remove)
                                if idx > 0:
                                    prev = parent[idx - 1]
                                    prev.tail = (prev.tail or '') + img_to_remove.tail
                                else:
                                    parent.text = (parent.text or '') + img_to_remove.tail
                            parent.remove(img_to_remove)
                    
                    # Add as prose-image item
                    paragraphs.append({
                        'type': 'prose_image',
                        'elements': [p_copy],  # Start with the paragraph that had the image
                        'image': {
                            'filename': filename,
                            'caption': caption,
                            'alt': alt if not has_usecaption else '',
                            'position': position,
                            'asset_id': asset_id
                        }
                    })
                    
                    # Log
                    if asset_id:
                        images_found.append(f"{filename} (floated {position}) - mapped to asset {asset_id}")
                    else:
                        images_found.append(f"{filename} (floated {position}) - NO ASSET ID FOUND")
                else:
                    # Image without special class - strip it and keep prose
                    p_copy = copy.deepcopy(child)
                    for img_to_remove in p_copy.findall('.//img'):
                        parent = p_copy
                        for potential_parent in p_copy.iter():
                            if img_to_remove in list(potential_parent):
                                parent = potential_parent
                                break
                        if img_to_remove in list(parent):
                            parent.remove(img_to_remove)
                    
                    # Only add if there's content left
                    if p_copy.text or list(p_copy):
                        current_prose_elements.append(p_copy)
                    
                    # Log the removed image
                    images_found.append(f"{filename} (no special class) - removed from content")
            else:
                # Regular paragraph without image
                current_prose_elements.append(copy.deepcopy(child))
        else:
            # Non-paragraph element (headers, lists, etc.)
            current_prose_elements.append(copy.deepcopy(child))
    
    # Flush remaining prose
    if current_prose_elements:
        paragraphs.append({
            'type': 'prose',
            'elements': current_prose_elements
        })
    
    # Now convert paragraphs list to content items
    for para in paragraphs:
        if para['type'] == 'prose':
            # Create prose content item
            item = create_section_content_item()
            content_type = item.find('content-item-type')
            if content_type is not None:
                content_type.text = 'prose'
            
            # Build WYSIWYG content
            wysiwyg_elem = item.find('wysiwyg')
            if wysiwyg_elem is not None:
                for elem in para['elements']:
                    wysiwyg_elem.append(elem)
                # Clean the content
                clean_wysiwyg_content(wysiwyg_elem, images_found)
            
            content_items.append({
                'item': item,
                'section_heading': None
            })
        
        elif para['type'] == 'block_image':
            # Create media content item with size="lg"
            item = create_section_content_item()
            content_type = item.find('content-item-type')
            if content_type is not None:
                content_type.text = 'media'
            
            # Configure group-single-media (the one at content item level)
            media_elems = item.findall('./group-single-media')
            media_elem = media_elems[0] if media_elems else None
            if media_elem is not None:
                set_group_single_media(
                    media_elem,
                    asset_id=para.get('asset_id') or '',
                    position='auto',
                    caption=para.get('caption', ''),
                    media_type='img-pub-api'
                )
                # Set size to lg for block images
                size_elem = media_elem.find('size')
                if size_elem is not None:
                    size_elem.text = 'lg'
            
            content_items.append({
                'item': item,
                'section_heading': None
            })
        
        elif para['type'] == 'prose_image':
            # Create prose-image content item
            item = create_section_content_item()
            content_type = item.find('content-item-type')
            if content_type is not None:
                content_type.text = 'prose-image'
            
            # Build WYSIWYG content
            wysiwyg_elem = item.find('wysiwyg')
            if wysiwyg_elem is not None:
                for elem in para['elements']:
                    wysiwyg_elem.append(elem)
                clean_wysiwyg_content(wysiwyg_elem, images_found)
            
            # Configure group-single-media for the floated image
            img_info = para.get('image', {})
            media_elems = item.findall('./group-single-media')
            media_elem = media_elems[0] if media_elems else None
            if media_elem is not None:
                set_group_single_media(
                    media_elem,
                    asset_id=img_info.get('asset_id') or '',
                    position=img_info.get('position', 'right'),
                    caption=img_info.get('caption', ''),
                    media_type='img-pub-api'
                )
                # Size stays at md for floated images
            
            content_items.append({
                'item': item,
                'section_heading': None
            })
    
    return content_items


def get_news_page_type(filename: str) -> str:
    """
    Determine the page-type value based on news item filename.
    
    Args:
        filename: News item filename (e.g., '2026-01-30-...-fs.xml')
        
    Returns:
        'feature-story' for Feature Stories (-fs), 'news' for others
    """
    if filename.endswith('-fs.xml') or '-fs-' in filename:
        return 'feature-story'
    return 'news'


# Metadata fields that need Yes/No -> true/false transformation
_BOOLEAN_METADATA_FIELDS = {
    'left-nav-include',
    'include-sitemaps', 
    'meta-noindex',
    'title-suffix'
}

# Metadata fields to copy directly (may be multi-value)
_DIRECT_COPY_METADATA_FIELDS = {
    'meta-refresh',
    'tag-source',
    'assignment',
    'academics',
    'audiences',
    'themes',
    'sponsors',
    'faculty-tag',
    'locations',
    'types'
}


def extract_dynamic_metadata(origin_root: ET.Element) -> Dict[str, List[str]]:
    """
    Extract dynamic metadata from origin XML.
    
    Args:
        origin_root: Root element of origin XML
        
    Returns:
        Dict mapping metadata name to list of values
    """
    metadata = {}
    
    # Find all dynamic-metadata elements
    for dm in origin_root.findall('.//dynamic-metadata'):
        name = dm.findtext('name', '')
        if not name:
            continue
        
        # Get all values (may be multi-value)
        values = [v.text for v in dm.findall('value') if v.text]
        if values:
            metadata[name] = values
    
    return metadata


def extract_wired_metadata(origin_root: ET.Element) -> Dict[str, str]:
    """
    Extract wired (system) metadata fields from origin XML.
    
    Args:
        origin_root: Root element of origin XML
        
    Returns:
        Dict with title, description, keywords, summary, display-name, start-date
    """
    metadata = {}
    
    # Find system-page element
    system_page = origin_root.find('.//system-page[@current="true"]')
    if system_page is None:
        system_page = origin_root.find('.//system-page')
    
    if system_page is not None:
        # Title is required
        title = system_page.findtext('title', '')
        if title:
            metadata['title'] = title
        
        # Optional wired fields
        for field in ['description', 'keywords', 'summary', 'display-name', 'start-date']:
            value = system_page.findtext(field, '')
            if value:
                metadata[field] = value
    
    return metadata


def get_page_heading(origin_root: ET.Element, is_news: bool = False) -> str:
    """
    Extract page heading (h1) from origin XML.
    
    Priority for news items:
        1. headline (from dynamic-metadata)
        2. title (fallback)
    
    Priority for regular pages:
        1. custom-page-heading (if page-heading="Custom")
        2. page-heading (from dynamic-metadata)
        3. title (fallback)
    
    Args:
        origin_root: Root element of origin XML
        is_news: Whether this is a news item
        
    Returns:
        Page heading text (may contain HTML)
    """
    dynamic_meta = extract_dynamic_metadata(origin_root)
    wired_meta = extract_wired_metadata(origin_root)
    
    if is_news:
        # News items: headline first
        headline = dynamic_meta.get('headline', [])
        if headline and headline[0]:
            return headline[0]
    else:
        # Regular pages: check for custom page heading
        group_settings = origin_root.find('.//group-settings')
        if group_settings is not None:
            page_heading_type = group_settings.findtext('page-heading', '')
            if page_heading_type == 'Custom':
                custom_heading = group_settings.findtext('custom-page-heading', '')
                if custom_heading:
                    return custom_heading
        
        # Fall back to page-heading metadata
        page_heading = dynamic_meta.get('page-heading', [])
        if page_heading and page_heading[0]:
            return page_heading[0]
    
    # Ultimate fallback: title
    return wired_meta.get('title', '')


def transform_boolean_metadata(value: str) -> str:
    """
    Transform Yes/No metadata value to true/false.
    
    Args:
        value: Original value (Yes, No, or other)
        
    Returns:
        'true' or 'false'
    """
    if value.lower() in ('yes', 'true', '1'):
        return 'true'
    elif value.lower() in ('no', 'false', '0'):
        return 'false'
    # Default to true for unknown values
    return 'true'


def map_metadata_to_destination(origin_root: ET.Element, dest_root: ET.Element,
                                  is_news: bool = False, filename: str = '') -> List[str]:
    """
    Map metadata from origin to destination XML.
    
    Updates the destination XML in place with:
    - Wired metadata (title, description, etc.)
    - Dynamic metadata (with Yes/No -> true/false transformation)
    - Page heading (group-hero/heading)
    - Page type (for news items)
    
    Args:
        origin_root: Root element of origin XML
        dest_root: Root element of destination XML (modified in place)
        is_news: Whether this is a news item
        filename: Source filename (for page-type detection)
        
    Returns:
        List of migration notes/warnings
    """
    notes = []
    
    # Extract metadata from origin
    wired_meta = extract_wired_metadata(origin_root)
    dynamic_meta = extract_dynamic_metadata(origin_root)
    
    # Find destination system-data-structure
    dest_structure = dest_root.find('.//system-data-structure')
    if dest_structure is None:
        notes.append("ERROR: No system-data-structure in destination")
        return notes
    
    # --- Set page-type ---
    page_type_elem = dest_structure.find('page-type')
    if page_type_elem is not None:
        if is_news:
            page_type_elem.text = get_news_page_type(filename)
        else:
            page_type_elem.text = 'default'
    
    # --- Set page heading (group-hero/heading) ---
    heading = get_page_heading(origin_root, is_news)
    hero_group = dest_structure.find('group-hero')
    if hero_group is not None:
        heading_elem = hero_group.find('heading')
        if heading_elem is not None:
            heading_elem.text = heading
    
    # --- Map wired metadata ---
    # These go on the system-page element in destination
    # For now, we'll note them for the migration script to handle
    # (system-page metadata is typically set via Cascade API, not XML)
    for field in ['title', 'description', 'keywords', 'summary', 'display-name', 'start-date']:
        if field in wired_meta:
            notes.append(f"WIRED: {field} = {wired_meta[field][:50]}..." if len(wired_meta.get(field, '')) > 50 else f"WIRED: {field} = {wired_meta.get(field, '')}")
    
    # --- Map dynamic metadata ---
    # Find or create dynamic-metadata elements in destination
    # For boolean fields, transform Yes/No to true/false
    for field in _BOOLEAN_METADATA_FIELDS:
        values = dynamic_meta.get(field, [])
        if values:
            transformed = transform_boolean_metadata(values[0])
            notes.append(f"META: {field} = {transformed} (was: {values[0]})")
    
    # For direct copy fields
    for field in _DIRECT_COPY_METADATA_FIELDS:
        values = dynamic_meta.get(field, [])
        if values:
            if len(values) == 1:
                notes.append(f"META: {field} = {values[0]}")
            else:
                notes.append(f"META: {field} = [{', '.join(values)}]")
    
    return notes


if __name__ == '__main__':
    print("XML Mapper utilities loaded. Use in migration scripts.")
