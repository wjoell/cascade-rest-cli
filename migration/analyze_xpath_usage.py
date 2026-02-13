"""
Analyze XPath usage across all source XML files.

Scans migration-clean directory and counts which paths are actually populated,
helping prioritize mapping effort.
"""

import os
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from collections import defaultdict
import csv

# Source directory
SOURCE_DIR = "/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/migration-clean"

# Skip directories starting with underscore
SKIP_PREFIXES = ('_', '.')


def get_xpath(element, parent_path=""):
    """Get simplified XPath for an element."""
    if parent_path:
        return f"{parent_path}/{element.tag}"
    return element.tag


def has_content(element):
    """Check if element has meaningful content (text or children with text)."""
    # Direct text content
    if element.text and element.text.strip():
        return True
    # Check children
    for child in element:
        if has_content(child):
            return True
    return False


def extract_paths_with_content(element, parent_path="", paths=None):
    """
    Recursively extract all paths that have content.
    Returns dict of path -> sample_value
    """
    if paths is None:
        paths = {}
    
    current_path = get_xpath(element, parent_path)
    
    # Skip system-index-block (metadata, not content)
    if element.tag == 'system-index-block':
        return paths
    
    # Record if has direct text content
    if element.text and element.text.strip():
        text_preview = element.text.strip()[:100]
        if current_path not in paths:
            paths[current_path] = text_preview
    
    # Recurse into children
    for child in element:
        extract_paths_with_content(child, current_path, paths)
    
    return paths


def analyze_structured_data(root):
    """
    Extract paths from system-data-structure only (the actual content).
    Returns dict of path -> sample_value
    """
    paths = {}
    
    # Find system-data-structure (the structured content)
    sds = root.find('.//system-data-structure')
    if sds is None:
        return paths
    
    # Extract paths relative to system-data-structure
    for child in sds:
        extract_paths_with_content(child, "", paths)
    
    return paths


def analyze_region_types(root):
    """
    Extract the 'type' values for group-primary and group-secondary regions.
    Returns list of (region, type, status) tuples.
    """
    results = []
    
    for region in ['group-primary', 'group-secondary']:
        for elem in root.findall(f'.//{region}'):
            status = elem.findtext('status', 'Unknown')
            type_val = elem.findtext('type', 'Unknown')
            if status == 'On':
                results.append((region, type_val, status))
    
    return results


def scan_all_files():
    """Scan all XML files and collect path usage statistics."""
    
    # Counters
    path_counts = defaultdict(int)  # path -> count of files using it
    path_samples = {}  # path -> sample value
    type_counts = defaultdict(int)  # (region, type) -> count
    files_processed = 0
    files_with_errors = []
    
    # Walk source directory
    for root_dir, dirs, files in os.walk(SOURCE_DIR):
        # Filter out underscore directories
        dirs[:] = [d for d in dirs if not d.startswith(SKIP_PREFIXES)]
        
        for filename in files:
            # Only process .xml files (not -destination.xml or -migration.html)
            if not filename.endswith('.xml'):
                continue
            if filename.endswith('-destination.xml'):
                continue
            
            filepath = os.path.join(root_dir, filename)
            rel_path = os.path.relpath(filepath, SOURCE_DIR)
            
            try:
                tree = ET.parse(filepath)
                root = tree.getroot()
                
                # Extract paths with content
                paths = analyze_structured_data(root)
                
                # Count paths
                for path, sample in paths.items():
                    path_counts[path] += 1
                    if path not in path_samples:
                        path_samples[path] = sample
                
                # Extract region types
                region_types = analyze_region_types(root)
                for region, type_val, status in region_types:
                    type_counts[(region, type_val)] += 1
                
                files_processed += 1
                
                if files_processed % 500 == 0:
                    print(f"  Processed {files_processed} files...")
                    
            except ET.ParseError as e:
                files_with_errors.append((rel_path, str(e)))
            except Exception as e:
                files_with_errors.append((rel_path, str(e)))
    
    return path_counts, path_samples, type_counts, files_processed, files_with_errors


def main():
    print("=" * 70)
    print("XPath Usage Analysis")
    print("=" * 70)
    print(f"\nScanning: {SOURCE_DIR}")
    print("This may take a minute...\n")
    
    path_counts, path_samples, type_counts, total_files, errors = scan_all_files()
    
    print(f"\n{'=' * 70}")
    print(f"RESULTS")
    print(f"{'=' * 70}")
    print(f"\nFiles processed: {total_files}")
    print(f"Files with errors: {len(errors)}")
    print(f"Unique paths found: {len(path_counts)}")
    
    # Sort paths by frequency
    sorted_paths = sorted(path_counts.items(), key=lambda x: -x[1])
    
    # Print top paths
    print(f"\n{'=' * 70}")
    print("TOP 50 MOST USED PATHS")
    print("(paths with actual content, not empty elements)")
    print(f"{'=' * 70}\n")
    
    print(f"{'Count':<8} {'Path':<60}")
    print("-" * 70)
    for path, count in sorted_paths[:50]:
        print(f"{count:<8} {path:<60}")
    
    # Print region type usage
    print(f"\n{'=' * 70}")
    print("CONTENT TYPE USAGE (group-primary/group-secondary)")
    print(f"{'=' * 70}\n")
    
    sorted_types = sorted(type_counts.items(), key=lambda x: -x[1])
    print(f"{'Count':<8} {'Region':<20} {'Type':<30}")
    print("-" * 60)
    for (region, type_val), count in sorted_types:
        print(f"{count:<8} {region:<20} {type_val:<30}")
    
    # Write full report to CSV
    output_dir = "/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets"
    
    # Path usage CSV
    csv_path = os.path.join(output_dir, "xpath_usage_report.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['path', 'count', 'percentage', 'sample_value'])
        for path, count in sorted_paths:
            pct = (count / total_files) * 100
            sample = path_samples.get(path, '')[:200]  # Truncate sample
            writer.writerow([path, count, f"{pct:.1f}%", sample])
    print(f"\n✓ Full path report written to: {csv_path}")
    
    # Type usage CSV
    type_csv_path = os.path.join(output_dir, "content_type_usage_report.csv")
    with open(type_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['region', 'type', 'count', 'percentage'])
        for (region, type_val), count in sorted_types:
            pct = (count / total_files) * 100
            writer.writerow([region, type_val, count, f"{pct:.1f}%"])
    print(f"✓ Content type report written to: {type_csv_path}")
    
    # Print errors if any
    if errors:
        print(f"\n{'=' * 70}")
        print("FILES WITH ERRORS")
        print(f"{'=' * 70}\n")
        for filepath, error in errors[:10]:
            print(f"  {filepath}: {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
    
    print(f"\n{'=' * 70}")
    print("ANALYSIS COMPLETE")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
