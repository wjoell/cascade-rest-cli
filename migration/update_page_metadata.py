"""
Update page metadata via Cascade REST API.

Extracts metadata from origin XML files and updates destination pages with:
- title (wired metadata)
- displayName (wired metadata)
- metaDescription (wired metadata, from origin <description>)
- keywords (wired metadata)
- group-hero/heading (structured data, from custom heading / page-heading / title)
- Dynamic metadata fields (left-nav-include, include-sitemaps, meta-noindex, etc.)
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from html import escape as html_escape
from xml.etree import ElementTree as ET

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cascade_rest.core import read_single_asset, edit_single_asset
from secrets_manager import secrets_manager


# Paths
SOURCE_DIR = "/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/migration-clean"
LOG_DIR = "/Users/winston/Repositories/wjoell/slc-edu-migration/logs"
DB_PATH = "/Users/winston/.cascade_cli/migration.db"

# Dynamic metadata fields to migrate
# Boolean fields: old "Yes"/"No" -> new "true"/"false"
BOOLEAN_DYNAMIC_FIELDS = {
    'left-nav-include',
    'include-sitemaps',
    'meta-noindex',
}

# Text/multi-value dynamic fields (pass through as-is)
PASSTHROUGH_DYNAMIC_FIELDS = {
    'meta-refresh',
    'assignment',
    'academics',
    'audiences',
    'themes',
    'sponsors',
    'faculty-tag',
    'locations',
    'types',
}

# Fields to skip (old-site specific)
SKIP_DYNAMIC_FIELDS = {
    'stripe-instagram',
    'stripe',
    'tag-source',
    'stripe-source',
    'stripe-custom-heading',
    'page-heading',       # Used for heading resolution, not migrated directly
    'title-suffix',       # Old-site template control
}

ALL_DYNAMIC_FIELDS = BOOLEAN_DYNAMIC_FIELDS | PASSTHROUGH_DYNAMIC_FIELDS


class MetadataUpdateLogger:
    """Logger for metadata update operations."""

    def __init__(self, log_path: str):
        self.log_path = log_path
        self.entries = []

        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        with open(log_path, 'w', encoding='utf-8') as f:
            header = {
                'type': 'metadata_update_log_header',
                'started': datetime.now(timezone.utc).isoformat(),
                'version': '1.0'
            }
            f.write(json.dumps(header) + '\n')

    def log(self, page_path: str, page_id: str, status: str,
            message: str = None, changes: Dict = None):
        """Log a metadata update operation."""
        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'page_path': page_path,
            'page_id': page_id,
            'status': status,
            'message': message,
            'changes': changes
        }
        self.entries.append(entry)

        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')

        icon = {'SUCCESS': '✅', 'ERROR': '❌', 'SKIPPED': '⏭️',
                'NO_CHANGES': '➖'}.get(status, '❓')
        print(f"  {icon} {page_path}: {status}" + (f" - {message}" if message else ""))

    def get_summary(self) -> Dict:
        """Get summary statistics."""
        stats = {'SUCCESS': 0, 'ERROR': 0, 'SKIPPED': 0, 'NO_CHANGES': 0}
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


# ---------------------------------------------------------------------------
# Origin XML metadata extraction
# ---------------------------------------------------------------------------

def extract_page_metadata(origin_xml_path: str) -> Dict[str, Any]:
    """
    Extract all migrateable metadata from an origin XML file.

    Returns dict with:
        title: str
        display_name: str
        description: str
        keywords: str
        heading: str (resolved from custom heading / page-heading / headline / title)
        start_date: str (timestamp for news items)
        is_featured_story: bool (True if filename ends with -fs.xml)
        dynamic_metadata: dict of field_name -> list of values
    """
    tree = ET.parse(origin_xml_path)
    root = tree.getroot()

    page = root.find('.//system-page')
    sds = root.find('.//system-data-structure')

    result = {
        'title': '',
        'display_name': '',
        'description': '',
        'keywords': '',
        'heading': '',
        'start_date': '',
        'is_featured_story': False,
        'dynamic_metadata': {},
    }

    if page is None:
        return result

    # Wired metadata
    result['title'] = page.findtext('title', '') or ''
    result['display_name'] = page.findtext('display-name', '') or ''
    result['description'] = page.findtext('description', '') or ''
    result['keywords'] = page.findtext('keywords', '') or ''
    result['start_date'] = page.findtext('start-date', '') or ''
    
    # Check if this is a featured story (filename ends with -fs.xml)
    if origin_xml_path.endswith('-fs.xml'):
        result['is_featured_story'] = True

    # Resolve page heading (priority order):
    # 1. system-data-structure/group-settings[page-heading="Custom"]/custom-page-heading
    # 2. dynamic-metadata[name="page-heading" and value!=""]/value
    # 3. dynamic-metadata[name="headline" and value!=""]/value (news items)
    # 4. title
    heading = ''
    headline_value = ''  # Track headline for news items

    if sds is not None:
        gs = sds.find('group-settings')
        if gs is not None:
            ph_setting = gs.findtext('page-heading', '')
            if ph_setting == 'Custom':
                cph_elem = gs.find('custom-page-heading')
                if cph_elem is not None:
                    # Get inner HTML to preserve inline elements like <sup>, <em>
                    # HTML-escape text portions (hero heading is an HTML field)
                    parts = []
                    if cph_elem.text:
                        parts.append(html_escape(cph_elem.text, quote=False))
                    for child in cph_elem:
                        parts.append(ET.tostring(child, encoding='unicode'))
                        if child.tail:
                            parts.append(html_escape(child.tail, quote=False))
                    custom_heading = ''.join(parts).strip()
                    if custom_heading:
                        heading = custom_heading

    if not heading:
        # Check dynamic-metadata page-heading and headline
        for dm in page.findall('dynamic-metadata'):
            name = dm.findtext('name', '')
            if name == 'page-heading':
                dm_heading = dm.findtext('value', '')
                if dm_heading:
                    heading = html_escape(dm_heading, quote=False)
                    break
            elif name == 'headline':
                headline_value = dm.findtext('value', '')
    
    # Fallback to headline for news items (if page-heading wasn't set)
    if not heading and headline_value:
        heading = html_escape(headline_value, quote=False)
    
    if not heading:
        heading = html_escape(result['title'], quote=False)

    result['heading'] = heading

    # Dynamic metadata
    for dm in page.findall('dynamic-metadata'):
        field_name = dm.findtext('name', '')

        if field_name in SKIP_DYNAMIC_FIELDS:
            continue

        if field_name not in ALL_DYNAMIC_FIELDS:
            continue

        # Collect all <value> elements (supports multi-value fields)
        values = []
        for v_elem in dm.findall('value'):
            if v_elem.text:
                val = v_elem.text.strip()
                if val:
                    # Convert Yes/No to true/false for boolean fields
                    if field_name in BOOLEAN_DYNAMIC_FIELDS:
                        val = 'true' if val == 'Yes' else 'false'
                    values.append(val)

        if values:
            result['dynamic_metadata'][field_name] = values

    return result


# ---------------------------------------------------------------------------
# API update logic
# ---------------------------------------------------------------------------

def find_dynamic_field(dynamic_fields: List[Dict], field_name: str) -> Optional[Dict]:
    """Find a dynamic field by name in the dynamicFields array."""
    for field in dynamic_fields:
        if field.get('name') == field_name:
            return field
    return None


def update_dynamic_field_values(dynamic_fields: List[Dict], field_name: str,
                                values: List[str]):
    """Update a dynamic field with one or more values."""
    field = find_dynamic_field(dynamic_fields, field_name)

    field_values = [{'value': v} for v in values]

    if field:
        field['fieldValues'] = field_values
    else:
        # Field doesn't exist in current asset, add it
        dynamic_fields.append({
            'name': field_name,
            'fieldValues': field_values
        })


def get_dynamic_field_values(dynamic_fields: List[Dict], field_name: str) -> List[str]:
    """Get current values of a dynamic field."""
    field = find_dynamic_field(dynamic_fields, field_name)
    if field and field.get('fieldValues'):
        return [fv.get('value', '') for fv in field['fieldValues'] if fv.get('value')]
    return []


def find_hero_heading_node(structured_data_nodes: List[Dict]) -> Optional[Dict]:
    """
    Find the group-hero > heading node in structuredDataNodes.

    Returns the heading text node or None.
    """
    for node in structured_data_nodes:
        if node.get('identifier') == 'group-hero' and node.get('type') == 'group':
            for child in node.get('structuredDataNodes', []):
                if child.get('identifier') == 'heading':
                    return child
    return None


def find_page_type_node(structured_data_nodes: List[Dict]) -> Optional[Dict]:
    """
    Find the page-type text node in structuredDataNodes.

    Returns the page-type text node or None.
    """
    for node in structured_data_nodes:
        if node.get('identifier') == 'page-type':
            return node
    return None


def update_single_page_metadata(cms_path: str, auth: Dict, page_id: str,
                                origin_xml_path: str, logger: MetadataUpdateLogger,
                                dry_run: bool = False) -> bool:
    """
    Update a single page's metadata from origin XML.

    Returns True if successful.
    """
    # Determine page path from XML path
    rel_path = origin_xml_path.replace(SOURCE_DIR + '/', '').replace('.xml', '')
    page_path = '/' + rel_path

    # Extract metadata from origin XML
    try:
        origin_meta = extract_page_metadata(origin_xml_path)
    except Exception as e:
        logger.log(page_path, page_id, 'ERROR', f'Failed to parse origin XML: {e}')
        return False

    # Read current page state from API
    result = read_single_asset(cms_path, auth, 'page', page_id)

    if not result or not result.get('success'):
        logger.log(page_path, page_id, 'ERROR', 'Failed to read page from API')
        return False

    page = result['asset']['page']
    metadata = page.get('metadata', {})
    dynamic_fields = metadata.get('dynamicFields', [])
    structured_data = page.get('structuredData', {})
    sd_nodes = structured_data.get('structuredDataNodes', [])

    # Track changes
    changes = {}

    # --- Wired metadata ---
    wired_fields = {
        'title': origin_meta['title'],
        'displayName': origin_meta['display_name'],
        'metaDescription': origin_meta['description'],
        'keywords': origin_meta['keywords'],
    }

    for api_field, new_value in wired_fields.items():
        current = metadata.get(api_field, '')
        if current != new_value and new_value:
            changes[api_field] = {'from': current, 'to': new_value}
            metadata[api_field] = new_value

    # --- Hero heading (structured data) ---
    heading_node = find_hero_heading_node(sd_nodes)
    if heading_node and origin_meta['heading']:
        current_heading = heading_node.get('text', '')
        if current_heading != origin_meta['heading']:
            changes['hero-heading'] = {'from': current_heading, 'to': origin_meta['heading']}
            heading_node['text'] = origin_meta['heading']
    
    # --- Page type (for featured stories) ---
    if origin_meta['is_featured_story']:
        page_type_node = find_page_type_node(sd_nodes)
        if page_type_node:
            current_page_type = page_type_node.get('text', '')
            if current_page_type != 'featured-story':
                changes['page-type'] = {'from': current_page_type, 'to': 'featured-story'}
                page_type_node['text'] = 'featured-story'
    
    # --- Start date (for news items) ---
    if origin_meta['start_date']:
        current_start = page.get('startDate', '')
        if current_start != origin_meta['start_date']:
            changes['startDate'] = {'from': current_start, 'to': origin_meta['start_date']}
            page['startDate'] = origin_meta['start_date']

    # --- Dynamic metadata ---
    for field_name, new_values in origin_meta['dynamic_metadata'].items():
        current_values = get_dynamic_field_values(dynamic_fields, field_name)
        if current_values != new_values:
            changes[f'dm:{field_name}'] = {'from': current_values, 'to': new_values}
            update_dynamic_field_values(dynamic_fields, field_name, new_values)

    # No changes needed
    if not changes:
        logger.log(page_path, page_id, 'NO_CHANGES')
        return True

    # Dry run
    if dry_run:
        logger.log(page_path, page_id, 'SKIPPED', 'Dry run', changes)
        return True

    # Write back
    page['metadata'] = metadata
    page['structuredData']['structuredDataNodes'] = sd_nodes
    payload = {'asset': {'page': page}}

    update_result = edit_single_asset(cms_path, auth, 'page', page_id, payload)

    if update_result.get('success'):
        logger.log(page_path, page_id, 'SUCCESS', None, changes)
        return True
    else:
        error_msg = update_result.get('message', 'Unknown error')
        logger.log(page_path, page_id, 'ERROR', error_msg, changes)
        return False


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def get_pages_from_db(section_path: str = None) -> List[Dict]:
    """Get pages from the migration database."""
    conn = sqlite3.connect(DB_PATH)
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


def update_metadata(section_path: str = None, dry_run: bool = False,
                    resume_after: str = None, pages_from: str = None):
    """
    Update page metadata via REST API from origin XML files.

    Args:
        section_path: Optional section prefix. If None, processes all pages.
        dry_run: Preview changes without updating.
        resume_after: Source path to resume after.
        pages_from: Path to text file with source paths to process (one per line).
    """
    scope = section_path or 'all'
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    log_path = f"{LOG_DIR}/metadata-update-{scope.replace('/', '-')}-{timestamp}.jsonl"

    print("=" * 60)
    print(f"PAGE METADATA UPDATE: {scope.upper()}")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    if resume_after:
        print(f"Resuming after: {resume_after}")
    if pages_from:
        print(f"Pages from: {pages_from}")
    print()

    # Get auth
    cms_path, auth = get_auth()
    print(f"✅ Connected to {cms_path}")

    # Get pages
    pages = get_pages_from_db(section_path)

    # Filter to specific pages if --pages-from provided
    if pages_from:
        with open(pages_from, 'r') as f:
            allowed_paths = {line.strip() for line in f if line.strip()}
        pages = [p for p in pages if p['source_path'] in allowed_paths]
        print(f"📄 Filtered to {len(pages)} pages from {len(allowed_paths)} paths in file")
    
    total_pages = len(pages)
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
    logger = MetadataUpdateLogger(log_path)

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

        # Origin XML path (source_path includes .xml)
        origin_xml_path = f"{SOURCE_DIR}/{source_path}"

        if not os.path.exists(origin_xml_path):
            logger.log(f"/{source_path}", page_id, 'SKIPPED', 'No origin XML')
            continue

        update_single_page_metadata(cms_path, auth, page_id, origin_xml_path, logger, dry_run)
        processed += 1

    # Summary
    summary = logger.get_summary()
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total pages:  {total_pages}")
    print(f"  Processed:    {processed}")
    print(f"  ✅ Success:   {summary.get('SUCCESS', 0)}")
    print(f"  ➖ No changes: {summary.get('NO_CHANGES', 0)}")
    print(f"  ⏭️  Skipped:  {summary.get('SKIPPED', 0)}")
    print(f"  ❌ Errors:    {summary.get('ERROR', 0)}")

    # Show last successful page for resume
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
    """Update a single page's metadata by source path (for testing)."""
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    log_path = f"{LOG_DIR}/metadata-update-single-{timestamp}.jsonl"

    print("=" * 60)
    print("SINGLE PAGE METADATA UPDATE")
    print("=" * 60)
    print(f"Source path: {source_path}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print()

    # Get auth
    cms_path, auth = get_auth()
    print(f"✅ Connected to {cms_path}")

    # Look up page ID
    conn = sqlite3.connect(DB_PATH)
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

    # Origin XML path
    origin_xml_path = f"{SOURCE_DIR}/{source_path}"
    if not os.path.exists(origin_xml_path):
        print(f"❌ Origin XML not found: {origin_xml_path}")
        return False

    # Show extracted metadata
    origin_meta = extract_page_metadata(origin_xml_path)
    print(f"\nExtracted metadata:")
    print(f"  title: {origin_meta['title']}")
    print(f"  display_name: {origin_meta['display_name']}")
    print(f"  description: {origin_meta['description'][:80]}..." if len(origin_meta['description']) > 80 else f"  description: {origin_meta['description']}")
    print(f"  keywords: {origin_meta['keywords'][:80]}..." if len(origin_meta['keywords']) > 80 else f"  keywords: {origin_meta['keywords']}")
    print(f"  heading: {origin_meta['heading']}")
    for field_name, values in origin_meta['dynamic_metadata'].items():
        print(f"  dm:{field_name}: {values}")
    print()

    # Initialize logger
    logger = MetadataUpdateLogger(log_path)

    # Update
    result = update_single_page_metadata(cms_path, auth, page_id, origin_xml_path, logger, dry_run)

    print(f"\n📋 Log: {log_path}")
    return result


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Update page metadata from origin XML')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without updating')
    parser.add_argument('--all', action='store_true', help='Update ALL pages in the database')
    parser.add_argument('--section', type=str, help='Update all pages in a section (e.g., "about")')
    parser.add_argument('--page', type=str, help='Update single page by source path')
    parser.add_argument('--resume-after', type=str,
                        help='Source path to resume after (skip pages up to this path)')
    parser.add_argument('--pages-from', type=str,
                        help='Path to text file with source paths to process (one per line)')

    args = parser.parse_args()

    if args.page:
        update_single_by_path(args.page, dry_run=args.dry_run)
    elif args.pages_from:
        update_metadata(section_path=None, dry_run=args.dry_run,
                        resume_after=args.resume_after, pages_from=args.pages_from)
    elif args.all:
        update_metadata(section_path=None, dry_run=args.dry_run,
                        resume_after=args.resume_after)
    elif args.section:
        update_metadata(section_path=args.section, dry_run=args.dry_run,
                        resume_after=args.resume_after)
    else:
        parser.print_help()
