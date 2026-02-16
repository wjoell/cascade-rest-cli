"""
Map image asset IDs from gallery JSON files to image references CSV.

Process:
1. Load all gallery JSON files from json-gallery-data directory
2. Build a lookup dictionary: filename (without extension) -> asset id
3. Load image_references_report.csv
4. For each row, match renamed_file (strip extension) to asset id
5. Add new 'asset_id' column with the mapped IDs
6. Save updated CSV with asset IDs

The gallery JSON files contain assets with:
- filename: The uploaded filename without extension (e.g., "about_diversity_campus-restroom-map")
- id: The Typesense document ID for the asset
"""

import os
import json
import csv
from pathlib import Path
from typing import Dict, List


def load_gallery_files(gallery_dir: str) -> Dict[str, int]:
    """
    Load all gallery JSON files and build filename -> asset_id mapping.
    
    Args:
        gallery_dir: Directory containing *-gallery-assets.json files
        
    Returns:
        Dictionary mapping filename (without extension) to asset id
    """
    filename_to_id = {}
    gallery_path = Path(gallery_dir)
    
    # Find all gallery JSON files
    gallery_files = list(gallery_path.glob('*-gallery-assets.json'))
    print(f"Found {len(gallery_files)} gallery JSON files")
    
    total_assets = 0
    duplicates = []
    
    for gallery_file in sorted(gallery_files):
        try:
            with open(gallery_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Process each asset in the gallery
            if 'assets' in data:
                for asset in data['assets']:
                    if 'filename' in asset and 'id' in asset:
                        filename = asset['filename']
                        asset_id = asset['id']
                        
                        # Check for duplicates
                        if filename in filename_to_id:
                            duplicates.append({
                                'filename': filename,
                                'existing_id': filename_to_id[filename],
                                'new_id': asset_id,
                                'gallery': gallery_file.name
                            })
                        else:
                            filename_to_id[filename] = asset_id
                            total_assets += 1
        
        except Exception as e:
            print(f"❌ Error processing {gallery_file.name}: {e}")
    
    print(f"Loaded {total_assets} unique asset mappings")
    
    if duplicates:
        print(f"\n⚠️  Warning: Found {len(duplicates)} duplicate filenames across galleries:")
        for dup in duplicates[:10]:  # Show first 10
            print(f"   {dup['filename']}: ID {dup['existing_id']} vs {dup['new_id']} (in {dup['gallery']})")
        if len(duplicates) > 10:
            print(f"   ... and {len(duplicates) - 10} more")
    
    return filename_to_id


def strip_extension(filename: str) -> str:
    """
    Remove file extension from filename.
    
    Examples:
        about_diversity_campus-restroom-map.jpg -> about_diversity_campus-restroom-map
        slcembedded_slcembedded.svg -> slcembedded_slcembedded
    """
    return Path(filename).stem


def update_csv_with_asset_ids(csv_file: str, filename_to_id: Dict[str, int], output_file: str):
    """
    Update image references CSV with asset IDs.
    
    Args:
        csv_file: Path to image_references_report.csv
        filename_to_id: Mapping of filename (no extension) to asset id
        output_file: Path to save updated CSV
    """
    # Read existing CSV
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"\nProcessing {len(rows)} image references...")
    
    # Add asset_id column
    matched = 0
    not_matched = []
    
    for row in rows:
        renamed_file = row['renamed_file']
        filename_no_ext = strip_extension(renamed_file)
        
        # First try exact match
        if filename_no_ext in filename_to_id:
            row['asset_id'] = filename_to_id[filename_no_ext]
            matched += 1
        else:
            # Try suffix match - some gallery filenames don't have path prefix
            # e.g., CSV has "news-events_lago.jpeg" -> "news-events_lago"
            #       gallery has "lago.jpeg" -> need to match "lago" as suffix
            found = False
            for gallery_filename, asset_id in filename_to_id.items():
                gallery_no_ext = strip_extension(gallery_filename)
                if filename_no_ext.endswith('_' + gallery_no_ext) or filename_no_ext == gallery_no_ext:
                    row['asset_id'] = asset_id
                    matched += 1
                    found = True
                    break
            
            if not found:
                row['asset_id'] = ''
                not_matched.append(renamed_file)
    
    # Write updated CSV
    fieldnames = ['renamed_file', 'cms_asset_path', 'original_path', 'actual_path', 'source_file', 'asset_id']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n✅ Updated CSV saved to {output_file}")
    print(f"\n📊 Mapping Results:")
    print(f"   Matched: {matched} / {len(rows)} ({matched/len(rows)*100:.1f}%)")
    print(f"   Not matched: {len(not_matched)}")
    
    if not_matched:
        print(f"\n⚠️  Images without asset IDs:")
        for filename in not_matched[:20]:  # Show first 20
            print(f"   {filename}")
        if len(not_matched) > 20:
            print(f"   ... and {len(not_matched) - 20} more")
        
        # Save unmatched list for review
        unmatched_file = output_file.replace('.csv', '_unmatched.txt')
        with open(unmatched_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(not_matched))
        print(f"\n   Full list saved to: {unmatched_file}")


def main():
    """Main execution."""
    # Paths
    gallery_dir = os.path.expanduser(
        '~/Repositories/wjoell/slc-edu-migration/source-assets/json-gallery-data'
    )
    csv_file = os.path.expanduser(
        '~/Repositories/wjoell/slc-edu-migration/source-assets/image_references_report.csv'
    )
    output_file = os.path.expanduser(
        '~/Repositories/wjoell/slc-edu-migration/source-assets/image_references_with_asset_ids.csv'
    )
    
    # Verify files exist
    if not os.path.exists(gallery_dir):
        print(f"❌ Error: Gallery directory not found: {gallery_dir}")
        return
    
    if not os.path.exists(csv_file):
        print(f"❌ Error: CSV file not found: {csv_file}")
        return
    
    print(f"Gallery JSON directory: {gallery_dir}")
    print(f"Input CSV: {csv_file}")
    print(f"Output CSV: {output_file}\n")
    
    # Load gallery data
    filename_to_id = load_gallery_files(gallery_dir)
    
    if not filename_to_id:
        print("❌ No asset mappings found in gallery files")
        return
    
    # Update CSV
    update_csv_with_asset_ids(csv_file, filename_to_id, output_file)
    
    print("\n✨ Done!")


if __name__ == '__main__':
    main()
