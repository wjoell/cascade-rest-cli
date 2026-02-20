"""
XML Analysis Utilities for Origin to Destination Migration.

Provides functions to:
- Detect active regions in origin XML (intro, grid, nav, primary, secondary)
- Parse WYSIWYG content into heading+content sections
- Analyze content types and structure
- Generate XPath notation for exclusions
"""

import re
from typing import List, Dict, Tuple, Optional
from xml.etree import ElementTree as ET


def get_calling_page(xml_root: ET.Element) -> Optional[ET.Element]:
    """
    Get the calling-page element which contains the canonical page content.
    
    The source XML may contain duplicated content in both system-index-block
    hierarchy AND calling-page. We only want to process calling-page.
    
    Args:
        xml_root: Root of origin XML document
        
    Returns:
        The calling-page element or None
    """
    calling_page = xml_root.find('.//calling-page')
    if calling_page is not None:
        return calling_page
    # Fallback to root if no calling-page (shouldn't happen)
    return xml_root


def detect_active_regions(xml_root: ET.Element) -> Dict[str, bool]:
    """
    Detect which regions are active in origin XML.
    
    Regions are controlled by group-settings fields. Each field either has:
    - <value>On</value> (active)
    - Empty/self-closing tag (inactive)
    
    Special case for intro: also check if group-intro has actual content
    (wysiwyg text, gallery ID, or video ID) even if settings field is empty.
    
    Args:
        xml_root: Root of origin XML document
        
    Returns:
        Dict mapping region names to active status
    """
    regions = {
        'intro': False,
        'grid': False,
        'nav': False,
        'primary': False,
        'secondary': False
    }
    
    # Only look in calling-page to avoid duplicates
    search_root = get_calling_page(xml_root)
    
    # Find group-settings node
    group_settings = search_root.find('.//group-settings')
    if group_settings is None:
        return regions
    
    # Track which regions have explicit settings (vs empty/self-closing tags)
    explicit_off = set()  # Regions that are explicitly set to off (empty tag but exists)
    
    # Check each region
    for region in regions.keys():
        region_node = group_settings.find(region)
        if region_node is not None:
            # Check for <value>On</value> child
            value_node = region_node.find('value')
            if value_node is not None and value_node.text == 'On':
                regions[region] = True
            elif value_node is None:
                # Empty/self-closing tag = explicit off, don't auto-detect
                explicit_off.add(region)
    
    # Special case for intro: check if group-intro has content even if settings empty
    # BUT only if there's no explicit empty <intro/> tag (which means user turned it off)
    if not regions['intro'] and 'intro' not in explicit_off:
        group_intro = search_root.find('.//group-intro')
        if group_intro is not None:
            # Check for wysiwyg content
            wysiwyg = group_intro.find('wysiwyg')
            has_wysiwyg = wysiwyg is not None and (wysiwyg.text or len(list(wysiwyg)) > 0)
            
            # Check for gallery content
            gallery = group_intro.find('publish-api-gallery')
            has_gallery = gallery is not None and gallery.findtext('gallery-api-id', '')
            
            # Check for video content
            intro_video = group_intro.find('intro-video')
            has_video = intro_video is not None and intro_video.findtext('video-id', '')
            
            # Check for c2a images with valid path
            c2a = group_intro.find('group-c2a')
            c2a_image = c2a.find('image') if c2a is not None else None
            has_c2a_image = c2a_image is not None and c2a_image.findtext('path', '/') != '/'
            
            cta_display = group_intro.findtext('cta-display', 'Off')
            
            # Intro is active if it has content to migrate
            if has_wysiwyg or has_gallery or has_video:
                regions['intro'] = True
            elif cta_display in ['First Single', 'Random Single', 'Shuffled Cycle', 'Cycle'] and has_c2a_image:
                regions['intro'] = True
    
    return regions


def get_active_region_items(xml_root: ET.Element, region_name: str) -> List[ET.Element]:
    """
    Get all active items from a multi-item region (nav, primary, secondary).
    
    Multi-item regions have individual items with status field.
    Only items with status="On" are active.
    
    Args:
        xml_root: Root of origin XML document
        region_name: Name of region ('nav', 'primary', or 'secondary')
        
    Returns:
        List of active item elements
    """
    active_items = []
    
    # Only look in calling-page to avoid duplicates
    search_root = get_calling_page(xml_root)
    
    # Map region name to group name
    group_name = f'group-{region_name}'
    
    # Find all items in this group
    items = search_root.findall(f'.//{group_name}')
    
    for item in items:
        # Check status field
        status_node = item.find('.//status')
        if status_node is not None and status_node.text == 'On':
            active_items.append(item)
    
    return active_items


def get_item_type(item: ET.Element) -> Optional[str]:
    """
    Get the type of a content item.
    
    Args:
        item: XML element representing a content item
        
    Returns:
        Type string or None
    """
    type_node = item.find('.//type')
    if type_node is not None:
        return type_node.text
    return None


def get_item_section_heading(item: ET.Element) -> Optional[Dict]:
    """
    Get the section heading info from an item if it has one.
    
    Items with use-section-heading=yes have their heading in <section-heading>
    and heading level in <section-heading-level>.
    
    Items with use-section-heading=yes-description also have <section-description>
    which is rich text that should become a prose content item.
    
    Args:
        item: XML element representing a content item
        
    Returns:
        Dict with:
        - 'text': heading text
        - 'level': heading level (h2, h3, etc.)
        - 'has_description': bool indicating if section-description is present
        - 'description_elem': the section-description element (if has_description)
        Or None if no section heading
    """
    use_heading = item.find('.//use-section-heading')
    if use_heading is None:
        return None
    
    use_heading_value = use_heading.text
    if use_heading_value not in ('yes', 'yes-description'):
        return None
    
    heading_text = item.findtext('.//section-heading', '')
    heading_level = item.findtext('.//section-heading-level', 'h2')
    
    if not heading_text:
        return None
    
    result = {
        'text': heading_text,
        'level': heading_level,
        'has_description': False,
        'description_elem': None
    }
    
    # Check for section-description (rich text) when using yes-description
    if use_heading_value == 'yes-description':
        section_desc = item.find('.//section-description')
        if section_desc is not None and (section_desc.text or len(list(section_desc)) > 0):
            result['has_description'] = True
            result['description_elem'] = section_desc
    
    return result


def has_wysiwyg_content(item: ET.Element) -> bool:
    """
    Check if an item has non-empty WYSIWYG content.
    
    Args:
        item: XML element representing a content item
        
    Returns:
        True if WYSIWYG has content, False otherwise
    """
    wysiwyg = item.find('.//group-text/wysiwyg')
    if wysiwyg is None:
        return False
    
    # Check if it has any children or text content
    if len(wysiwyg) > 0:
        return True
    if wysiwyg.text and wysiwyg.text.strip():
        return True
    
    return False


def extract_heading_content(heading_elem: ET.Element) -> Dict:
    """
    Extract text content and images from a heading element.
    
    Images inside headings are extracted separately. If an image has class
    'left' or 'right', it's a candidate for prose-image content type.
    Text and valid inline elements (em, strong, a) are preserved.
    
    Args:
        heading_elem: An h2-h5 element
        
    Returns:
        Dict with:
        - 'text': clean heading text
        - 'images': list of image info dicts
        - 'floated_image': first image with left/right class (for prose-image), or None
    """
    images = []
    text_parts = []
    floated_image = None
    
    # Collect text before first child
    if heading_elem.text:
        text_parts.append(heading_elem.text)
    
    for child in heading_elem:
        if child.tag == 'img':
            # Extract image info
            src = child.get('src', '')
            alt = child.get('alt', '')
            img_class = child.get('class', '')
            filename = src.split('/')[-1] if '/' in src else src
            
            img_info = {
                'src': src,
                'alt': alt,
                'filename': filename,
                'class': img_class
            }
            
            # Check if this is a floated image (candidate for prose-image)
            if floated_image is None and ('left' in img_class or 'right' in img_class):
                img_info['position'] = 'left' if 'left' in img_class else 'right'
                floated_image = img_info
            else:
                images.append(img_info)
            
            # Include tail text (text after the img)
            if child.tail:
                text_parts.append(child.tail)
        else:
            # Keep other inline elements (em, strong, a, etc.) as HTML
            elem_html = ET.tostring(child, encoding='unicode', method='html')
            text_parts.append(elem_html)
    
    return {
        'text': ''.join(text_parts).strip(),
        'images': images,
        'floated_image': floated_image
    }


def parse_wysiwyg_element_to_sections(wysiwyg_elem: ET.Element, heading_images: List[Dict] = None) -> List[Dict]:
    """
    Parse WYSIWYG XML element into heading + content sections.
    
    Works directly with XML elements to preserve HTML structure without escaping.
    Images inside headings with left/right class are passed as 'floated_image' for prose-image.
    Other heading images are logged separately.
    
    Args:
        wysiwyg_elem: WYSIWYG XML element
        heading_images: Optional list to append non-floated images found in headings
        
    Returns:
        List of section dictionaries with 'heading', 'heading_level', 'content_elem', and optionally 'floated_image'
    """
    sections = []
    
    if wysiwyg_elem is None:
        return sections
    
    if heading_images is None:
        heading_images = []
    
    # Find all heading elements (h2-h5)
    current_section = None
    content_elements = []
    
    # Collect initial text before any elements
    if wysiwyg_elem.text and wysiwyg_elem.text.strip():
        content_elements.append(('text', wysiwyg_elem.text))
    
    for child in wysiwyg_elem:
        if child.tag in ['h2', 'h3', 'h4', 'h5']:
            # Save previous section if exists
            if current_section is not None:
                current_section['content_elements'] = content_elements
                sections.append(current_section)
            
            # Extract heading content, separating images
            heading_content = extract_heading_content(child)
            
            # Log any non-floated images found in headings
            for img_info in heading_content['images']:
                img_info['context'] = f"Found in {child.tag} heading (no float class)"
                heading_images.append(img_info)
            
            current_section = {
                'heading': heading_content['text'],
                'heading_level': child.tag,
                'floated_image': heading_content.get('floated_image')  # Pass floated image to section
            }
            content_elements = []
            
            # Capture text after this heading
            if child.tail and child.tail.strip():
                content_elements.append(('text', child.tail))
        else:
            # Non-heading element - add to current content
            content_elements.append(('element', child))
            if child.tail and child.tail.strip():
                content_elements.append(('text', child.tail))
    
    # Save final section
    if current_section is not None:
        current_section['content_elements'] = content_elements
        sections.append(current_section)
    elif content_elements:
        # No headings - everything is one section
        sections.append({
            'heading': '',
            'heading_level': '',
            'content_elements': content_elements,
            'floated_image': None
        })
    
    # Post-process: detect h2 immediately followed by h3 pattern
    # When h2 has no content and is followed by h3, the h2 becomes a section_heading
    sections = _detect_section_heading_pattern(sections)
    
    return sections


def _detect_section_heading_pattern(sections: List[Dict]) -> List[Dict]:
    """
    Detect h2→h3 pattern (h2 with no content immediately followed by h3).
    
    When this pattern is found:
    - The h2 becomes the 'section_heading' for the h3 section
    - The h2 section is removed (merged into h3 section)
    - This indicates a new group-page-section-item should be created
    
    Args:
        sections: List of section dicts from parse_wysiwyg_element_to_sections
        
    Returns:
        Modified list with section_heading markers
    """
    if len(sections) < 2:
        return sections
    
    result = []
    i = 0
    
    while i < len(sections):
        section = sections[i]
        
        # Check if this is an h2 with no content
        is_h2_empty = (
            section.get('heading_level') == 'h2' and
            not section.get('content_elements', [])
        )
        
        # Check if next section is h3
        if is_h2_empty and i + 1 < len(sections):
            next_section = sections[i + 1]
            if next_section.get('heading_level') == 'h3':
                # h2→h3 pattern detected!
                # Add section_heading to the h3 section and skip the h2
                next_section['section_heading'] = section['heading']
                next_section['section_heading_floated_image'] = section.get('floated_image')
                # Skip the h2 section - it's now merged
                i += 1
                continue
        
        result.append(section)
        i += 1
    
    return result


def parse_wysiwyg_to_sections(wysiwyg_content: str) -> List[Dict[str, str]]:
    """
    Parse WYSIWYG HTML content into heading + content sections.
    
    Splits on h2-h5 tags, creating a new section for each heading.
    Each section has:
    - heading: The heading text
    - heading_level: h2, h3, h4, or h5
    - content: HTML content following the heading (until next heading)
    
    Args:
        wysiwyg_content: Raw HTML content from WYSIWYG field
        
    Returns:
        List of section dictionaries
    """
    sections = []
    
    if not wysiwyg_content or not wysiwyg_content.strip():
        return sections
    
    # Pattern to match h2-h5 tags and capture level, content
    heading_pattern = r'<(h[2-5])>(.*?)</\1>'
    
    # Find all headings with their positions
    headings = []
    for match in re.finditer(heading_pattern, wysiwyg_content, re.DOTALL):
        level = match.group(1)  # h2, h3, etc.
        text = match.group(2)   # heading text
        start = match.start()
        end = match.end()
        headings.append({
            'level': level,
            'text': text.strip(),
            'start': start,
            'end': end
        })
    
    # If no headings, treat entire content as one section with no heading
    if not headings:
        return [{
            'heading': '',
            'heading_level': '',
            'content': wysiwyg_content.strip()
        }]
    
    # Extract content for each heading
    for i, heading in enumerate(headings):
        # Content starts after this heading
        content_start = heading['end']
        
        # Content ends at next heading (or end of string)
        if i + 1 < len(headings):
            content_end = headings[i + 1]['start']
        else:
            content_end = len(wysiwyg_content)
        
        content = wysiwyg_content[content_start:content_end].strip()
        
        sections.append({
            'heading': heading['text'],
            'heading_level': heading['level'],
            'content': content
        })
    
    # Handle any content before first heading
    if headings[0]['start'] > 0:
        intro_content = wysiwyg_content[:headings[0]['start']].strip()
        if intro_content:
            sections.insert(0, {
                'heading': '',
                'heading_level': '',
                'content': intro_content
            })
    
    return sections


def detect_show_fields(item: ET.Element, data_definition: ET.Element) -> Dict[str, bool]:
    """
    Detect which fields are active based on type and show-fields attribute.
    
    In origin data definitions, structured-data-nodes may have show-fields
    attribute that controls which child fields are visible based on parent type.
    
    Args:
        item: Content item element
        data_definition: Origin data definition XML root
        
    Returns:
        Dict mapping field identifiers to active status
    """
    # Get item type
    item_type = get_item_type(item)
    if not item_type:
        return {}
    
    # This is a simplified version - full implementation would need to:
    # 1. Find the type field's structured-data-node in data definition
    # 2. Look for show-fields attribute matching the type value
    # 3. Return which fields are active for that type
    
    # For now, return empty dict (can be enhanced later)
    return {}


def extract_metadata(xml_root: ET.Element) -> Dict[str, str]:
    """
    Extract page metadata from origin XML.
    
    Args:
        xml_root: Root of origin XML document
        
    Returns:
        Dict of metadata fields
    """
    metadata = {}
    
    # Find system-page node (contains metadata)
    system_page = xml_root.find('.//system-page[@current="true"]')
    if system_page is None:
        return metadata
    
    # Extract common metadata
    fields = ['title', 'description', 'display-name', 'path']
    for field in fields:
        node = system_page.find(field)
        if node is not None and node.text:
            metadata[field] = node.text
    
    return metadata


def generate_xpath_exclusion(region: str, item_index: int, status: str = "Off", 
                             item_type: str = None, field: str = None) -> str:
    """
    Generate XPath notation for excluded content.
    
    Examples:
    - group-primary[4][status="Off"]
    - group-secondary[1][type="Action Links"]/group-text
    - group-primary[2][type="Stats Grid"]/stats-grid
    
    Args:
        region: Region name (primary, secondary, nav, etc.)
        item_index: 1-based index of item in region
        status: Status value (if excluding by status)
        item_type: Type value (if excluding by type)
        field: Specific field being excluded (optional)
        
    Returns:
        XPath notation string
    """
    xpath = f"group-{region}[{item_index}]"
    
    if status == "Off":
        xpath += f'[status="{status}"]'
    elif item_type:
        xpath += f'[type="{item_type}"]'
    
    if field:
        xpath += f"/{field}"
    
    return xpath


def analyze_content_complexity(wysiwyg_content: str) -> Dict[str, any]:
    """
    Analyze WYSIWYG content to determine complexity and content types.
    
    Args:
        wysiwyg_content: Raw HTML content
        
    Returns:
        Dict with analysis results
    """
    if not wysiwyg_content:
        return {
            'has_content': False,
            'heading_count': 0,
            'has_tables': False,
            'has_lists': False,
            'has_links': False,
            'estimated_sections': 0
        }
    
    return {
        'has_content': True,
        'heading_count': len(re.findall(r'<h[2-5]>', wysiwyg_content)),
        'has_tables': '<table' in wysiwyg_content.lower(),
        'has_lists': '<ul' in wysiwyg_content.lower() or '<ol' in wysiwyg_content.lower(),
        'has_links': '<a ' in wysiwyg_content.lower(),
        'estimated_sections': max(1, len(re.findall(r'<h[2-5]>', wysiwyg_content)))
    }


def get_wysiwyg_content(item: ET.Element) -> str:
    """
    Extract WYSIWYG content from an item element.
    
    Args:
        item: XML element containing WYSIWYG field
        
    Returns:
        HTML content string
    """
    # Look for group-text/wysiwyg pattern
    wysiwyg = item.find('.//group-text/wysiwyg')
    if wysiwyg is not None:
        # Get all text content including nested tags
        content = ET.tostring(wysiwyg, encoding='unicode', method='html')
        # Remove the wysiwyg wrapper tags
        content = re.sub(r'^<wysiwyg[^>]*>', '', content)
        content = re.sub(r'</wysiwyg>$', '', content)
        return content.strip()
    
    return ""


if __name__ == '__main__':
    import sys
    
    # Test with a sample XML file
    if len(sys.argv) > 1:
        xml_path = sys.argv[1]
        print(f"Analyzing: {xml_path}")
        print("=" * 80)
        
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Detect active regions
        print("\nACTIVE REGIONS:")
        regions = detect_active_regions(root)
        for region, active in regions.items():
            print(f"  {region}: {'✓' if active else '✗'}")
        
        # Analyze each active region
        for region in ['primary', 'secondary', 'nav']:
            if regions.get(region):
                print(f"\n{region.upper()} ITEMS:")
                items = get_active_region_items(root, region)
                print(f"  Found {len(items)} active items")
                
                for i, item in enumerate(items, 1):
                    item_type = get_item_type(item)
                    print(f"    [{i}] Type: {item_type}")
                    
                    # If it's a text type, analyze WYSIWYG
                    if item_type and 'text' in item_type.lower():
                        wysiwyg = get_wysiwyg_content(item)
                        complexity = analyze_content_complexity(wysiwyg)
                        print(f"        Headings: {complexity['heading_count']}")
                        print(f"        Sections: {complexity['estimated_sections']}")
        
        # Extract metadata
        print("\nMETADATA:")
        metadata = extract_metadata(root)
        for key, value in metadata.items():
            print(f"  {key}: {value}")
    else:
        print("Usage: python xml_analyzer.py <path-to-xml-file>")
