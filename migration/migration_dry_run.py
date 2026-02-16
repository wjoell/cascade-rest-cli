"""
Migration Dry Run - Analyze source files without modifying destinations.

This script:
1. Scans all source files in migration-clean directory
2. Analyzes content types and mapping coverage
3. Produces gap analysis and success rate estimates
4. Writes detailed log for review
"""

import os
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from migration_logger import MigrationLogger, GlobalMigrationLog

# Content type mapping status
CONTENT_TYPE_STATUS = {
    # MAPPED - Full support
    'Text': 'MAPPED',
    'Accordion': 'MAPPED', 
    'Video': 'MAPPED',
    'Image': 'MAPPED',
    'Quote': 'MAPPED',
    'Pull quote': 'MAPPED',  # Same as Quote
    'Form': 'MAPPED',
    'Publish API Gallery': 'MAPPED',  # Logged for manual placement
    'Button navigation group': 'MAPPED',  # Excluded by design
    'Action Links': 'MAPPED',  # Excluded by design
    
    # PARTIAL - External Block depends on subtype
    'External Block': 'PARTIAL',
    
    # EXCLUDED - Planned exclusions (not errors)
    'News': 'EXCLUDED',  # Dynamic content, not migrated
    'Events': 'EXCLUDED',  # Dynamic content, not migrated
    'Ad-like Object': 'EXCLUDED',  # Promotional, handled separately
    'Social Feed': 'EXCLUDED',  # Third-party embed
    'social-feed': 'EXCLUDED',
    'Blog index': 'EXCLUDED',  # Dynamic content
    'minimal-instagram': 'EXCLUDED',
    
    # GAP - Not yet mapped
    'file': 'GAP',  # File download link
    'external-page': 'GAP',  # External page embed
    'stats-grid': 'GAP',  # Statistics display
    'cta-banner': 'GAP',  # Call-to-action banner
    'jump-nav': 'GAP',  # Jump navigation
    'stories': 'GAP',  # Story carousel
}

# External Block subtype status
BLOCK_SUBTYPE_STATUS = {
    # MAPPED
    'List Index': 'MAPPED',
    'Contact Box': 'EXCLUDED',  # Handled separately
    
    # EXCLUDED
    'Ad-like Object': 'EXCLUDED',
    'Simple Content': 'EXCLUDED',  # Usually empty or promotional
    'Folder Gallery': 'EXCLUDED',  # Replaced by Publish API
    'Cincopa Gallery': 'EXCLUDED',  # Third-party embed
    
    # GAP
    'Exhibit Block': 'GAP',
    'Local php-script.html': 'GAP',
    'Grid': 'GAP',
}


def analyze_file(file_path: str, logger: MigrationLogger) -> dict:
    """
    Analyze a single source file for migration readiness.
    
    Returns dict with analysis results.
    """
    results = {
        'file_path': file_path,
        'page_path': None,
        'content_types': Counter(),
        'block_subtypes': Counter(),
        'mapped_items': 0,
        'excluded_items': 0,
        'gap_items': 0,
        'total_items': 0,
        'errors': [],
        'success': False
    }
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Extract page path
        page = root.find('.//system-page[@current="true"]')
        if page is not None:
            results['page_path'] = page.findtext('path', '')
        
        # Analyze content regions
        for region in ['group-primary', 'group-secondary', 'group-nav']:
            for item in root.findall(f'.//{region}'):
                status_elem = item.find('status')
                if status_elem is not None and status_elem.text == 'Off':
                    continue  # Skip inactive items
                
                item_type = item.findtext('type', '')
                if not item_type:
                    continue
                
                results['content_types'][item_type] += 1
                results['total_items'] += 1
                
                # Determine status
                type_status = CONTENT_TYPE_STATUS.get(item_type, 'GAP')
                
                # For External Block, check subtype
                if item_type == 'External Block':
                    block_type = item.findtext('.//group-block/type', '')
                    results['block_subtypes'][block_type] += 1
                    
                    subtype_status = BLOCK_SUBTYPE_STATUS.get(block_type, 'GAP')
                    if subtype_status == 'MAPPED':
                        type_status = 'MAPPED'
                    elif subtype_status == 'EXCLUDED':
                        type_status = 'EXCLUDED'
                    else:
                        type_status = 'GAP'
                        logger.warning(f"Unmapped External Block subtype: {block_type}")
                
                # Count by status
                if type_status == 'MAPPED':
                    results['mapped_items'] += 1
                    logger.info(f"Mapped: {item_type}", context=region)
                elif type_status == 'EXCLUDED':
                    results['excluded_items'] += 1
                    logger.warning(f"Excluded by design: {item_type}", context=region)
                else:  # GAP
                    results['gap_items'] += 1
                    logger.error(f"No mapper for: {item_type}", context=region)
        
        results['success'] = True
        
    except ET.ParseError as e:
        results['errors'].append(f"XML parse error: {e}")
        logger.error(f"XML parse error: {e}")
    except Exception as e:
        results['errors'].append(f"Error: {e}")
        logger.error(f"Error analyzing file: {e}")
    
    return results


def run_dry_run(source_dir: str, log_path: str = None) -> dict:
    """
    Run dry-run analysis on all source files.
    
    Args:
        source_dir: Path to migration-clean directory
        log_path: Optional path for global log file
        
    Returns:
        Summary dict with aggregated statistics
    """
    # Initialize global log
    if log_path:
        global_log = GlobalMigrationLog(log_path)
        global_log.initialize()
    
    # Aggregated stats
    summary = {
        'total_files': 0,
        'successful_files': 0,
        'failed_files': 0,
        'total_items': 0,
        'mapped_items': 0,
        'excluded_items': 0,
        'gap_items': 0,
        'content_types': Counter(),
        'block_subtypes': Counter(),
        'files_with_gaps': [],
        'errors': []
    }
    
    # Find all source files
    source_files = []
    for root, dirs, files in os.walk(source_dir):
        # Skip _archive and similar
        dirs[:] = [d for d in dirs if not d.startswith('_')]
        
        for fname in files:
            if fname.endswith('.xml') and not fname.endswith('-destination.xml'):
                source_files.append(os.path.join(root, fname))
    
    print(f"Found {len(source_files)} source files to analyze")
    print()
    
    # Analyze each file
    for i, file_path in enumerate(source_files, 1):
        if i % 100 == 0:
            print(f"  Analyzing file {i}/{len(source_files)}...")
        
        logger = MigrationLogger(file_path=file_path)
        if log_path:
            logger.set_global_log_file(log_path)
        
        results = analyze_file(file_path, logger)
        logger.page_path = results['page_path']
        
        # Write to global log
        logger.write_to_global_log()
        
        # Aggregate stats
        summary['total_files'] += 1
        if results['success']:
            summary['successful_files'] += 1
        else:
            summary['failed_files'] += 1
            summary['errors'].extend(results['errors'])
        
        summary['total_items'] += results['total_items']
        summary['mapped_items'] += results['mapped_items']
        summary['excluded_items'] += results['excluded_items']
        summary['gap_items'] += results['gap_items']
        summary['content_types'] += results['content_types']
        summary['block_subtypes'] += results['block_subtypes']
        
        if results['gap_items'] > 0:
            summary['files_with_gaps'].append({
                'file': file_path,
                'page': results['page_path'],
                'gaps': results['gap_items']
            })
    
    return summary


def print_gap_analysis(summary: dict):
    """Print detailed gap analysis report."""
    
    print("=" * 80)
    print("MIGRATION DRY RUN - GAP ANALYSIS")
    print("=" * 80)
    print(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    print()
    
    # Overall stats
    print("=" * 80)
    print("OVERALL STATISTICS")
    print("=" * 80)
    print(f"Total files analyzed:    {summary['total_files']}")
    print(f"Successful parses:       {summary['successful_files']}")
    print(f"Failed parses:           {summary['failed_files']}")
    print()
    print(f"Total content items:     {summary['total_items']}")
    print(f"  Mapped (ready):        {summary['mapped_items']} ({100*summary['mapped_items']/max(1,summary['total_items']):.1f}%)")
    print(f"  Excluded (by design):  {summary['excluded_items']} ({100*summary['excluded_items']/max(1,summary['total_items']):.1f}%)")
    print(f"  Gaps (need mapping):   {summary['gap_items']} ({100*summary['gap_items']/max(1,summary['total_items']):.1f}%)")
    print()
    
    # Success rate
    mappable_items = summary['mapped_items'] + summary['gap_items']
    success_rate = 100 * summary['mapped_items'] / max(1, mappable_items)
    print(f"ESTIMATED SUCCESS RATE:  {success_rate:.1f}%")
    print(f"  (mapped / (mapped + gaps), excluding planned exclusions)")
    print()
    
    # Content types breakdown
    print("=" * 80)
    print("CONTENT TYPES BREAKDOWN")
    print("=" * 80)
    print(f"{'Count':>6}  {'Status':<10}  Type")
    print("-" * 50)
    for ctype, count in summary['content_types'].most_common():
        status = CONTENT_TYPE_STATUS.get(ctype, 'GAP')
        print(f"{count:>6}  {status:<10}  {ctype}")
    print()
    
    # Block subtypes
    print("=" * 80)
    print("EXTERNAL BLOCK SUBTYPES")
    print("=" * 80)
    print(f"{'Count':>6}  {'Status':<10}  Subtype")
    print("-" * 50)
    for btype, count in summary['block_subtypes'].most_common():
        status = BLOCK_SUBTYPE_STATUS.get(btype, 'GAP')
        print(f"{count:>6}  {status:<10}  {btype}")
    print()
    
    # Gap items needing mapping
    gap_types = {t for t, s in CONTENT_TYPE_STATUS.items() if s == 'GAP'}
    gap_types.update(t for t, c in summary['content_types'].items() 
                     if CONTENT_TYPE_STATUS.get(t) == 'GAP')
    
    print("=" * 80)
    print("GAPS REQUIRING NEW MAPPERS")
    print("=" * 80)
    gap_counts = [(t, summary['content_types'][t]) for t in gap_types 
                  if summary['content_types'][t] > 0]
    gap_counts.sort(key=lambda x: -x[1])
    
    if gap_counts:
        for gtype, count in gap_counts:
            print(f"  {count:>5}x  {gtype}")
    else:
        print("  None - all content types have mappers!")
    print()
    
    # Block gaps
    block_gap_types = {t for t, s in BLOCK_SUBTYPE_STATUS.items() if s == 'GAP'}
    block_gap_types.update(t for t, c in summary['block_subtypes'].items() 
                           if BLOCK_SUBTYPE_STATUS.get(t) == 'GAP')
    
    block_gaps = [(t, summary['block_subtypes'][t]) for t in block_gap_types 
                  if summary['block_subtypes'][t] > 0]
    block_gaps.sort(key=lambda x: -x[1])
    
    if block_gaps:
        print("External Block subtype gaps:")
        for btype, count in block_gaps:
            print(f"  {count:>5}x  {btype}")
    print()
    
    # Files with gaps
    if summary['files_with_gaps']:
        print("=" * 80)
        print(f"FILES WITH GAPS ({len(summary['files_with_gaps'])} total)")
        print("=" * 80)
        # Show top 20
        for item in sorted(summary['files_with_gaps'], key=lambda x: -x['gaps'])[:20]:
            print(f"  {item['gaps']:>3} gaps: {item['page'] or item['file']}")
        if len(summary['files_with_gaps']) > 20:
            print(f"  ... and {len(summary['files_with_gaps']) - 20} more")
    print()
    
    print("=" * 80)


if __name__ == '__main__':
    # Default source directory
    source_dir = "/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/migration-clean"
    log_path = "/Users/winston/Repositories/wjoell/slc-edu-migration/migration-dry-run.jsonl"
    
    # Override with command line args
    if len(sys.argv) >= 2:
        source_dir = sys.argv[1]
    if len(sys.argv) >= 3:
        log_path = sys.argv[2]
    
    print(f"Source directory: {source_dir}")
    print(f"Log file: {log_path}")
    print()
    
    summary = run_dry_run(source_dir, log_path)
    print_gap_analysis(summary)
    
    # Also generate global log report
    print()
    global_log = GlobalMigrationLog(log_path)
    print(global_log.generate_report())
