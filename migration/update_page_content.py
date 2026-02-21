"""
Update page content via Cascade REST API.

Converts destination XML to JSON structuredDataNodes format and updates
pages via the API. Preserves existing data like source-content.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from xml.etree import ElementTree as ET

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cascade_rest.core import read_single_asset, edit_single_asset
from secrets_manager import secrets_manager


# Paths
SOURCE_DIR = "/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/migration-clean"
LOG_DIR = "/Users/winston/Repositories/wjoell/slc-edu-migration/logs"


class PageUpdateLogger:
    """Logger for page update operations."""
    
    def __init__(self, log_path: str):
        self.log_path = log_path
        self.entries = []
        
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        with open(log_path, 'w', encoding='utf-8') as f:
            header = {
                'type': 'page_update_log_header',
                'started': datetime.now(timezone.utc).isoformat(),
                'version': '1.0'
            }
            f.write(json.dumps(header) + '\n')
    
    def log(self, page_path: str, page_id: str, status: str,
            message: str = None, details: Dict = None):
        """Log a page update operation."""
        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'page_path': page_path,
            'page_id': page_id,
            'status': status,
            'message': message,
            'details': details
        }
        self.entries.append(entry)
        
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
        
        icon = {'SUCCESS': '✅', 'ERROR': '❌', 'SKIPPED': '⏭️'}.get(status, '❓')
        print(f"  {icon} {page_path}: {status}" + (f" - {message}" if message else ""))
    
    def get_summary(self) -> Dict:
        """Get summary statistics."""
        stats = {'SUCCESS': 0, 'ERROR': 0, 'SKIPPED': 0}
        for entry in self.entries:
            stats[entry['status']] = stats.get(entry['status'], 0) + 1
        return stats


def get_auth():
    """Get authentication credentials from 1Password."""
    print("🔑 Fetching credentials from 1Password...")
    creds = secrets_manager.get_from_1password(
        'Cascade REST Development Production', 'Cascade Rest API Production'
    )
    
    if not creds:
        raise RuntimeError("Failed to fetch credentials from 1Password")
    
    auth = {'apiKey': creds.get('api_key')} if creds.get('api_key') else {
        'u': creds.get('username'), 'p': creds.get('password')
    }
    
    return creds['cms_path'], auth


# Fields that contain HTML/WYSIWYG content - should be serialized as text with entity encoding preserved
HTML_CONTENT_FIELDS = {
    'wysiwyg', 'source-content', 'migration-summary', 'section-intro',
    'caption', 'layered-image-caption', 'content-heading-cutline',
    'heading-text', 'content-heading'
}


def escape_text_for_xml(text: str) -> str:
    """
    Escape text for XML output. Only &amp; is allowed as named entity,
    all other special chars use numeric entities.
    """
    # Escape & first (but not already-escaped entities)
    # Then escape < and >
    result = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return result


def get_inner_html(elem: ET.Element) -> str:
    """
    Get the inner HTML content of an element as a string.
    Includes text and all child elements serialized as HTML.
    
    Preserves XML entity encoding (&amp;, etc.) as required by Cascade.
    """
    parts = []
    if elem.text:
        # elem.text is already decoded by ET, need to re-encode for Cascade
        parts.append(escape_text_for_xml(elem.text))
    for child in elem:
        # ET.tostring preserves/re-encodes entities properly
        parts.append(ET.tostring(child, encoding='unicode'))
        if child.tail:
            # tail text is also decoded, need to re-encode
            parts.append(escape_text_for_xml(child.tail))
    return ''.join(parts).strip()


def xml_element_to_json(elem: ET.Element, parent_identifier: str = None) -> Dict:
    """
    Convert an XML element to a JSON structuredDataNode.
    
    Args:
        elem: XML element to convert
        parent_identifier: Parent's identifier for context
        
    Returns:
        Dict representing a structuredDataNode
    """
    identifier = elem.tag
    
    # Check if this is an HTML content field - serialize as text
    if identifier in HTML_CONTENT_FIELDS:
        html_content = get_inner_html(elem)
        node = {
            'type': 'text',
            'identifier': identifier,
            'recycled': False
        }
        if html_content:
            node['text'] = html_content
        return node
    
    # Get direct text content (not including children's text)
    text_content = elem.text.strip() if elem.text and elem.text.strip() else None
    
    # Check if this element has child elements
    children = list(elem)
    
    if children:
        # This is a group node
        child_nodes = []
        for child in children:
            child_node = xml_element_to_json(child, identifier)
            if child_node:
                child_nodes.append(child_node)
        
        node = {
            'type': 'group',
            'identifier': identifier,
            'structuredDataNodes': child_nodes,
            'recycled': False
        }
    else:
        # This is a text node (or empty)
        node = {
            'type': 'text',
            'identifier': identifier,
            'recycled': False
        }
        if text_content:
            # Escape & < > for Cascade (it expects XML-encoded text)
            node['text'] = escape_text_for_xml(text_content)
    
    return node


def convert_system_data_structure(xml_path: str) -> List[Dict]:
    """
    Parse destination XML and convert system-data-structure to structuredDataNodes.
    
    Args:
        xml_path: Path to destination XML file
        
    Returns:
        List of structuredDataNodes
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Find system-data-structure element
    sds = root.find('.//system-data-structure')
    if sds is None:
        raise ValueError(f"No system-data-structure found in {xml_path}")
    
    # Convert each child of system-data-structure
    nodes = []
    for child in sds:
        node = xml_element_to_json(child)
        if node:
            nodes.append(node)
    
    return nodes


def get_migration_summary(xml_path: str) -> Optional[str]:
    """
    Extract migration-summary content from destination XML.
    
    Args:
        xml_path: Path to destination XML file
        
    Returns:
        Migration summary XHTML content or None
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Find migration-summary element
    summary_elem = root.find('.//migration-summary')
    if summary_elem is None:
        return None
    
    # Get all content including nested elements
    # Use ET.tostring to get the inner content
    content_parts = []
    if summary_elem.text:
        content_parts.append(summary_elem.text)
    
    for child in summary_elem:
        content_parts.append(ET.tostring(child, encoding='unicode'))
        if child.tail:
            content_parts.append(child.tail)
    
    return ''.join(content_parts).strip() if content_parts else None


def find_node_by_identifier(nodes: List[Dict], identifier: str) -> Optional[Dict]:
    """Find a node by identifier in a list of structuredDataNodes."""
    for node in nodes:
        if node.get('identifier') == identifier:
            return node
    return None


def update_node_value(nodes: List[Dict], identifier: str, value: str) -> bool:
    """
    Update a text node's value by identifier.
    
    Returns True if found and updated.
    """
    for node in nodes:
        if node.get('identifier') == identifier and node.get('type') == 'text':
            node['text'] = value
            return True
    return False


import copy


def clone_node_with_values(template_node: Dict, source_node: Dict) -> Dict:
    """
    Deep clone a template node and populate it with values from source_node.
    
    The template provides the complete JSON structure (all required fields).
    The source provides the text values to populate.
    """
    # Deep copy the template to preserve all structure
    cloned = copy.deepcopy(template_node)
    
    # Handle asset chooser fields: template is 'asset' type, source may have path data
    if cloned.get('type') == 'asset':
        # Source might be a group with a 'path' child (from XML migration)
        if source_node.get('type') == 'group':
            source_children = source_node.get('structuredDataNodes', [])
            for child in source_children:
                if child.get('identifier') == 'path' and child.get('text'):
                    path_value = child['text'].strip()
                    # Only set if path is meaningful (not just "/")
                    if path_value and path_value != '/':
                        cloned['pagePath'] = path_value
                    break
        return cloned
    
    # Populate text value if source has one
    if source_node.get('type') == 'text':
        if 'text' in source_node and source_node['text']:
            cloned['text'] = source_node['text']
        elif 'text' in cloned:
            # Source has no text, clear it
            del cloned['text']
    
    # Recursively handle group children
    if cloned.get('type') == 'group' and source_node.get('type') == 'group':
        template_children = cloned.get('structuredDataNodes', [])
        source_children = source_node.get('structuredDataNodes', [])
        
        # Group children by identifier
        template_by_id = {}
        for child in template_children:
            ident = child.get('identifier')
            if ident not in template_by_id:
                template_by_id[ident] = []
            template_by_id[ident].append(child)
        
        source_by_id = {}
        for child in source_children:
            ident = child.get('identifier')
            if ident not in source_by_id:
                source_by_id[ident] = []
            source_by_id[ident].append(child)
        
        # Build new children list
        new_children = []
        seen_identifiers = set()
        
        # Process in template order to maintain field order
        for template_child in template_children:
            ident = template_child.get('identifier')
            
            if ident in seen_identifiers:
                continue  # Handle repeating groups once
            seen_identifiers.add(ident)
            
            if ident in source_by_id:
                source_list = source_by_id[ident]
                template_list = template_by_id.get(ident, [template_child])
                template_for_cloning = template_list[0]  # Use first as template
                
                # Clone template for each source item
                for source_child in source_list:
                    cloned_child = clone_node_with_values(template_for_cloning, source_child)
                    new_children.append(cloned_child)
            else:
                # No source data for this identifier, keep template (cleared)
                new_children.append(template_child)
        
        cloned['structuredDataNodes'] = new_children
    
    return cloned


def merge_structured_data(current_nodes: List[Dict], new_nodes: List[Dict],
                          migration_summary: str = None) -> List[Dict]:
    """
    Merge new structured data into current, using current as template structure.
    
    Strategy:
    - Use first group-page-section-item from current as template
    - Clone template for each section in new_nodes, populating with new values
    - Update migration-summary with our log
    - Preserve source-content and other non-content fields as-is
    
    Args:
        current_nodes: Current structuredDataNodes from API (provides schema)
        new_nodes: New structuredDataNodes from destination XML (provides values)
        migration_summary: Migration log to set
        
    Returns:
        Updated structuredDataNodes
    """
    # Get new section items
    new_section_items = [n for n in new_nodes if n.get('identifier') == 'group-page-section-item']
    
    # Find first section template from current
    section_template = None
    first_section_idx = None
    for i, node in enumerate(current_nodes):
        if node.get('identifier') == 'group-page-section-item':
            if section_template is None:
                section_template = node
                first_section_idx = i
            break
    
    if not section_template:
        # No template found, can't merge sections
        return current_nodes
    
    # Build result: keep nodes before first section, add merged sections, keep nodes after
    result = []
    sections_added = False
    
    for i, node in enumerate(current_nodes):
        ident = node.get('identifier')
        
        if ident == 'group-page-section-item':
            if not sections_added:
                # Replace all section items with new cloned ones
                for new_section in new_section_items:
                    cloned_section = clone_node_with_values(section_template, new_section)
                    # Set bool-status to "true" to activate the section
                    for child in cloned_section.get('structuredDataNodes', []):
                        if child.get('identifier') == 'bool-status':
                            child['text'] = 'true'
                            break
                    result.append(cloned_section)
                sections_added = True
            # Skip existing section items (replaced above)
            continue
        
        elif ident == 'migration-summary' and migration_summary:
            # Update migration-summary
            node = copy.deepcopy(node)
            node['text'] = migration_summary
            result.append(node)
        
        else:
            # Keep other nodes as-is (source-content, etc.)
            result.append(node)
    
    return result


def update_single_page(cms_path: str, auth: Dict, page_id: str,
                       xml_path: str, logger: PageUpdateLogger,
                       dry_run: bool = False) -> bool:
    """
    Update a single page's structured content from destination XML.
    
    Returns True if successful.
    """
    # Determine page path from XML path
    rel_path = xml_path.replace(SOURCE_DIR + '/', '').replace('-destination.xml', '')
    page_path = '/' + rel_path
    
    # Read current page state
    result = read_single_asset(cms_path, auth, 'page', page_id)
    
    if not result or not result.get('success'):
        logger.log(page_path, page_id, 'ERROR', 'Failed to read page from API')
        return False
    
    page = result['asset']['page']
    current_sd = page.get('structuredData', {})
    current_nodes = current_sd.get('structuredDataNodes', [])
    
    # Parse destination XML
    try:
        new_nodes = convert_system_data_structure(xml_path)
        migration_summary = get_migration_summary(xml_path)
    except Exception as e:
        logger.log(page_path, page_id, 'ERROR', f'Failed to parse XML: {e}')
        return False
    
    # Count new content items
    new_section_count = sum(1 for n in new_nodes if n.get('identifier') == 'group-page-section-item')
    new_content_count = 0
    for n in new_nodes:
        if n.get('identifier') == 'group-page-section-item':
            for child in n.get('structuredDataNodes', []):
                if child.get('identifier') == 'group-section-content-item':
                    new_content_count += 1
    
    # Merge structured data
    merged_nodes = merge_structured_data(current_nodes, new_nodes, migration_summary)
    
    # Dry run - don't actually update
    if dry_run:
        logger.log(page_path, page_id, 'SKIPPED', 'Dry run', {
            'sections': new_section_count,
            'content_items': new_content_count
        })
        return True
    
    # Update the page's structured data
    page['structuredData']['structuredDataNodes'] = merged_nodes
    
    # Build update payload
    payload = {'asset': {'page': page}}
    
    # Send update
    update_result = edit_single_asset(cms_path, auth, 'page', page_id, payload)
    
    if update_result.get('success'):
        logger.log(page_path, page_id, 'SUCCESS', None, {
            'sections': new_section_count,
            'content_items': new_content_count
        })
        return True
    else:
        error_msg = update_result.get('message', 'Unknown error')
        logger.log(page_path, page_id, 'ERROR', error_msg)
        return False


def get_pages_from_db(section_path: str = None) -> List[Dict]:
    """
    Get pages from the migration database.
    
    Args:
        section_path: Optional path prefix to filter (e.g., 'about'). 
                      If None, returns all pages.
        
    Returns:
        List of dicts with source_path and cascade_id
    """
    import sqlite3
    
    conn = sqlite3.connect('/Users/winston/.cascade_cli/migration.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if section_path:
        cursor.execute(
            "SELECT source_path, cascade_id FROM pages WHERE source_path LIKE ? ORDER BY source_path",
            (f"{section_path}%",)
        )
    else:
        cursor.execute(
            "SELECT source_path, cascade_id FROM pages ORDER BY source_path"
        )
    
    pages = [{'source_path': row['source_path'], 'cascade_id': row['cascade_id']} 
             for row in cursor.fetchall()]
    
    conn.close()
    return pages


def update_pages(section_path: str = None, dry_run: bool = False,
                 rate_limit: float = 0, resume_after: str = None,
                 pages_from: str = None):
    """
    Update pages via REST API from destination XML files.
    
    Args:
        section_path: Optional section prefix (e.g., 'about'). If None, processes all pages.
        dry_run: Preview changes without updating.
        rate_limit: Seconds to wait between API calls (default 0.1s).
        resume_after: Source path to resume after (skip pages up to and including this path).
        pages_from: Path to a text file containing source paths to process (one per line).
    """
    import time
    
    scope = section_path or 'all'
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    log_path = f"{LOG_DIR}/page-update-{scope.replace('/', '-')}-{timestamp}.jsonl"
    
    print("=" * 60)
    print(f"PAGE CONTENT UPDATE: {scope.upper()}")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    if rate_limit > 0:
        print(f"Rate limit: {rate_limit}s between requests")
    if resume_after:
        print(f"Resuming after: {resume_after}")
    print()
    
    # Get auth
    cms_path, auth = get_auth()
    print(f"✅ Connected to {cms_path}")
    
    # Get pages
    if pages_from:
        # Load specific source paths from file
        with open(pages_from) as f:
            filter_paths = set(line.strip() for line in f if line.strip())
        all_pages = get_pages_from_db(section_path)
        pages = [p for p in all_pages if p['source_path'] in filter_paths
                 or p['source_path'].replace('.xml', '') in filter_paths]
        print(f"📄 Found {len(pages)} pages (filtered from {len(all_pages)} via {pages_from})")
    else:
        pages = get_pages_from_db(section_path)
    total_pages = len(pages)
    if not pages_from:
        print(f"📄 Found {total_pages} pages")
    print(f"📋 Log file: {log_path}")
    print()
    
    # Handle resume
    if resume_after:
        skip_count = 0
        for i, p in enumerate(pages):
            if p['source_path'] == resume_after:
                pages = pages[i + 1:]
                skip_count = i + 1
                break
        print(f"⏭️  Skipping {skip_count} pages (resuming from {pages[0]['source_path'] if pages else 'end'})")
        print()
    
    # Initialize logger
    logger = PageUpdateLogger(log_path)
    
    # Process each page
    print("Processing pages...")
    processed = 0
    for i, page_info in enumerate(pages, 1):
        source_path = page_info['source_path']
        page_id = page_info['cascade_id']
        
        # Progress update
        if i % 50 == 0 or i == 1:
            summary_so_far = logger.get_summary()
            print(f"\n[{i}/{len(pages)}] ({summary_so_far.get('SUCCESS', 0)} ok, "
                  f"{summary_so_far.get('ERROR', 0)} err) Processing: {source_path}")
        
        # Construct destination XML path
        xml_path = f"{SOURCE_DIR}/{source_path.replace('.xml', '-destination.xml')}"
        
        if not os.path.exists(xml_path):
            logger.log(f"/{source_path}", page_id, 'SKIPPED', 'No destination XML')
            continue
        
        update_single_page(cms_path, auth, page_id, xml_path, logger, dry_run)
        processed += 1
        
        # Rate limiting (skip on dry run)
        if rate_limit > 0 and not dry_run:
            time.sleep(rate_limit)
    
    # Summary
    summary = logger.get_summary()
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total pages:  {total_pages}")
    print(f"  Processed:    {processed}")
    print(f"  ✅ Success:   {summary.get('SUCCESS', 0)}")
    print(f"  ⏭️  Skipped:  {summary.get('SKIPPED', 0)}")
    print(f"  ❌ Errors:    {summary.get('ERROR', 0)}")
    
    # Show last successful page for resume capability
    last_success = None
    for entry in reversed(logger.entries):
        if entry['status'] == 'SUCCESS':
            last_success = entry['page_path']
            break
    if last_success:
        print(f"\n  Last successful: {last_success}")
    
    # Show error details
    error_entries = [e for e in logger.entries if e['status'] == 'ERROR']
    if error_entries:
        print(f"\n❌ Errors ({len(error_entries)}):")
        for err in error_entries[:20]:
            print(f"  {err['page_path']}: {err.get('message', 'Unknown')}")
        if len(error_entries) > 20:
            print(f"  ... and {len(error_entries) - 20} more")
    
    print(f"\n📋 Log: {log_path}")
    return summary


def update_single_by_path(source_path: str, dry_run: bool = False):
    """Update a single page by source path (for testing)."""
    import sqlite3
    
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    log_path = f"{LOG_DIR}/page-update-single-{timestamp}.jsonl"
    
    print("=" * 60)
    print("SINGLE PAGE UPDATE")
    print("=" * 60)
    print(f"Source path: {source_path}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print()
    
    # Get auth
    cms_path, auth = get_auth()
    print(f"✅ Connected to {cms_path}")
    
    # Look up page ID
    conn = sqlite3.connect('/Users/winston/.cascade_cli/migration.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT cascade_id FROM pages WHERE source_path = ?", (source_path,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print(f"❌ Page not found in database: {source_path}")
        return False
    
    page_id = row['cascade_id']
    print(f"📄 Page ID: {page_id}")
    
    # Construct destination XML path (source_path may have .xml, replace or append)
    if source_path.endswith('.xml'):
        xml_path = f"{SOURCE_DIR}/{source_path.replace('.xml', '-destination.xml')}"
    else:
        xml_path = f"{SOURCE_DIR}/{source_path}-destination.xml"
    
    if not os.path.exists(xml_path):
        print(f"❌ Destination XML not found: {xml_path}")
        return False
    
    print(f"📄 Destination XML: {xml_path}")
    print()
    
    # Initialize logger
    logger = PageUpdateLogger(log_path)
    
    # Update
    result = update_single_page(cms_path, auth, page_id, xml_path, logger, dry_run)
    
    print(f"\n📋 Log: {log_path}")
    return result


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Update page content from destination XML')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without updating')
    parser.add_argument('--all', action='store_true', help='Update ALL pages in the database')
    parser.add_argument('--section', type=str, help='Update all pages in a section (e.g., "about")')
    parser.add_argument('--page', type=str, help='Update single page by source path')
    parser.add_argument('--rate-limit', type=float, default=0,
                        help='Seconds between API calls (default: 0, auth provides natural throttling)')
    parser.add_argument('--resume-after', type=str,
                        help='Source path to resume after (skip pages up to this path)')
    parser.add_argument('--pages-from', type=str,
                        help='Path to text file with source paths to process (one per line)')
    
    args = parser.parse_args()
    
    if args.page:
        update_single_by_path(args.page, dry_run=args.dry_run)
    elif args.pages_from:
        update_pages(section_path=None, dry_run=args.dry_run,
                     rate_limit=args.rate_limit, resume_after=args.resume_after,
                     pages_from=args.pages_from)
    elif args.all:
        update_pages(section_path=None, dry_run=args.dry_run,
                     rate_limit=args.rate_limit, resume_after=args.resume_after)
    elif args.section:
        update_pages(section_path=args.section, dry_run=args.dry_run,
                     rate_limit=args.rate_limit, resume_after=args.resume_after)
    else:
        parser.print_help()
