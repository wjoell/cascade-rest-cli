"""
Batch test migration on diverse pages.

Tests the migration POC on a variety of pages to validate mappers work at scale.
"""

import os
import sys
from pathlib import Path
from xml_migrate_poc import migrate_single_file

# Source directory
SOURCE_DIR = "/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/migration-clean"

# Diverse test pages covering different content types and complexity
TEST_PAGES = [
    # Text-heavy pages
    "about/index.xml",
    "about/mission/index.xml",
    "academics/index.xml",
    
    # Pages with accordions
    "about/data-reporting/index.xml",
    "financial-aid/forms/index.xml",
    
    # Pages with video
    "paris/index.xml",
    "giving/fund/chai.xml",
    
    # Pages with galleries
    "parents/family-weekend/index.xml",
    "college-events/bwcc/index.xml",
    
    # Pages with forms (if detected)
    "paris/inquire.xml",
    "admissions/visit/index.xml",
    
    # Complex pages with multiple content types
    "about/history/index.xml",
    "undergraduate/index.xml",
    "graduate/index.xml",
    
    # Study abroad pages
    "florence/index.xml",
    "havana/index.xml",
    
    # Other sections
    "student-life/index.xml",
    "alumni/index.xml",
    "giving/index.xml",
]


def run_batch_test():
    """Run migration on all test pages and collect results."""
    
    results = []
    total_sections = 0
    total_content_items = 0
    total_exclusions = 0
    successful = 0
    failed = 0
    skipped = 0
    
    print("=" * 80)
    print("BATCH MIGRATION TEST")
    print("=" * 80)
    print(f"\nTesting {len(TEST_PAGES)} diverse pages\n")
    
    for page in TEST_PAGES:
        origin_path = os.path.join(SOURCE_DIR, page)
        dest_path = origin_path.replace(".xml", "-destination.xml")
        
        # Check if files exist
        if not os.path.exists(origin_path):
            print(f"⏭️  SKIP: {page} (origin not found)")
            skipped += 1
            continue
        
        if not os.path.exists(dest_path):
            print(f"⏭️  SKIP: {page} (destination template not found)")
            skipped += 1
            continue
        
        print(f"\n{'─' * 60}")
        print(f"Processing: {page}")
        print(f"{'─' * 60}")
        
        try:
            stats = migrate_single_file(origin_path, dest_path)
            
            results.append({
                'page': page,
                'success': stats['success'],
                'sections': stats['sections_created'],
                'content_items': stats['content_items_created'],
                'exclusions': len(stats['exclusions']),
                'images': len(set(stats['images_found'])),
                'exclusion_details': stats['exclusions'][:5],  # First 5 exclusions
            })
            
            if stats['success']:
                successful += 1
                total_sections += stats['sections_created']
                total_content_items += stats['content_items_created']
                total_exclusions += len(stats['exclusions'])
                print(f"✅ SUCCESS: {stats['sections_created']} sections, {stats['content_items_created']} items, {len(stats['exclusions'])} exclusions")
            else:
                failed += 1
                print(f"❌ FAILED")
                
        except Exception as e:
            failed += 1
            results.append({
                'page': page,
                'success': False,
                'error': str(e),
            })
            print(f"❌ ERROR: {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("BATCH TEST SUMMARY")
    print("=" * 80)
    
    print(f"\nPages tested: {len(TEST_PAGES)}")
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed}")
    print(f"  ⏭️  Skipped: {skipped}")
    
    print(f"\nContent migrated:")
    print(f"  Sections created: {total_sections}")
    print(f"  Content items: {total_content_items}")
    print(f"  Exclusions: {total_exclusions}")
    
    # Per-page breakdown
    print(f"\n{'─' * 80}")
    print("PER-PAGE RESULTS")
    print(f"{'─' * 80}")
    print(f"\n{'Page':<45} {'Sections':<10} {'Items':<10} {'Excl':<10}")
    print("-" * 80)
    
    for r in results:
        if r.get('success'):
            print(f"{r['page']:<45} {r['sections']:<10} {r['content_items']:<10} {r['exclusions']:<10}")
        elif r.get('error'):
            print(f"{r['page']:<45} ERROR: {r['error'][:30]}")
        else:
            print(f"{r['page']:<45} FAILED")
    
    # Show sample exclusions
    print(f"\n{'─' * 80}")
    print("SAMPLE EXCLUSIONS (first few per page)")
    print(f"{'─' * 80}")
    
    for r in results:
        if r.get('exclusion_details'):
            print(f"\n{r['page']}:")
            for ex in r['exclusion_details']:
                print(f"  • {ex[:70]}{'...' if len(ex) > 70 else ''}")
    
    return results


if __name__ == "__main__":
    results = run_batch_test()
