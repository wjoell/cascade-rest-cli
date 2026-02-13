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


def detect_active_regions(xml_root: ET.Element) -> Dict[str, bool]:
    """
    Detect which regions are active in origin XML.
    
    Regions are controlled by group-settings fields. Each field either has:
    - <value>On</value> (active)
    - Empty/self-closing tag (inactive)
    
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
    
    # Find group-settings node
    group_settings = xml_root.find('.//group-settings')
    if group_settings is None:
        return regions
    
    # Check each region
    for region in regions.keys():
        region_node = group_settings.find(region)
        if region_node is not None:
            # Check for <value>On</value> child
            value_node = region_node.find('value')
            if value_node is not None and value_node.text == 'On':
                regions[region] = True
    
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
    
    # Map region name to group name
    group_name = f'group-{region_name}'
    
    # Find all items in this group
    items = xml_root.findall(f'.//{group_name}')
    
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


def parse_wysiwyg_element_to_sections(wysiwyg_elem: ET.Element) -> List[Dict]:
    """
    Parse WYSIWYG XML element into heading + content sections.
    
    Works directly with XML elements to preserve HTML structure without escaping.
    
    Args:
        wysiwyg_elem: WYSIWYG XML element
        
    Returns:
        List of section dictionaries with 'heading', 'heading_level', and 'content_elem'
    """
    sections = []
    
    if wysiwyg_elem is None:
        return sections
    
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
            
            # Start new section
            heading_text = ET.tostring(child, encoding='unicode', method='html')
            # Remove the heading tags
            heading_text = re.sub(r'^<h[2-5][^>]*>(.*?)</h[2-5]>$', r'\1', heading_text, flags=re.DOTALL)
            
            current_section = {
                'heading': heading_text.strip(),
                'heading_level': child.tag
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
            'content_elements': content_elements
        })
    
    return sections


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
