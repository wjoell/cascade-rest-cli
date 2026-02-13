"""
Process image assets for migration.

Tasks:
1. Scan migration-clean HTML files for image references
2. Find corresponding images in migration directory
3. Copy images to new upload folder with renamed pattern: path_to_file-name.ext
   Example: art-of-teaching/gallery/dm-046.jpg -> art-of-teaching_gallery_dm-046.jpg
4. Generate mapping table with: image_path, renamed_file, cms_asset_path, source_file

Notes:
- Some images may have missing extensions in HTML but exist with extensions in migration dir
- Some images are referenced by multiple pages
- Creates one entry per image/page combination
"""

import os
import re
import csv
import shutil
from pathlib import Path
from html.parser import HTMLParser
from typing import List, Dict, Set, Tuple, Optional


class ImageExtractor(HTMLParser):
    """HTML parser to extract image sources."""
    
    def __init__(self):
        super().__init__()
        self.images = []
    
    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            attrs_dict = dict(attrs)
            if 'src' in attrs_dict:
                self.images.append(attrs_dict['src'])


def extract_images_from_file(html_path: str) -> List[str]:
    """
    Extract all image src attributes from an HTML file.
    
    Returns:
        List of image src values
    """
    try:
        with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        parser = ImageExtractor()
        parser.feed(content)
        return parser.images
    except Exception as e:
        print(f"Error parsing {html_path}: {e}")
        return []


def is_processable_image(src: str) -> Tuple[bool, str]:
    """
    Determine if an image should be processed and extract the path.
    
    Returns:
        Tuple of (should_process, normalized_path)
        
    Processes ALL images except:
    - Data URIs: data:image/png;base64,...
    
    For CMS-generated HTML, all images have fully qualified URLs like:
    - https://www.sarahlawrence.edu/media/...
    - https://www.sarahlawrence.edu/_assets/images/...
    - Relative paths (if any): ../images/photo.jpg, /assets/img.png
    """
    # Skip data URIs only
    if src.startswith('data:'):
        return (False, '')
    
    # Check for www.sarahlawrence.edu hosted images
    if src.startswith(('https://www.sarahlawrence.edu/', 'http://www.sarahlawrence.edu/')):
        # Extract path after domain
        if 'https://www.sarahlawrence.edu/' in src:
            path = src.split('https://www.sarahlawrence.edu/', 1)[1]
        else:
            path = src.split('http://www.sarahlawrence.edu/', 1)[1]
        return (True, path)
    
    # Process all other paths (relative or other domains)
    # For other external URLs, still try to process them in case they're in the migration dir
    return (True, src)


def normalize_image_path(src: str) -> str:
    """
    Normalize image path from HTML src attribute.
    
    Handles:
    - Removes leading slashes
    - Removes query strings
    - Normalizes path separators
    
    Example:
    /images/photo.jpg?v=123 -> images/photo.jpg
    """
    # Remove query string
    if '?' in src:
        src = src.split('?')[0]
    
    # Remove leading slash
    src = src.lstrip('/')
    
    # Normalize path separators
    src = src.replace('\\', '/')
    
    return src


def find_image_file(image_path: str, migration_dir: str) -> Optional[str]:
    """
    Find actual image file in migration directory.
    
    Handles cases where:
    - Image path has no extension but file exists with extension
    - Path variations
    
    Returns:
        Full path to image file, or None if not found
    """
    migration_path = Path(migration_dir)
    
    # Try exact match first
    exact_path = migration_path / image_path
    if exact_path.exists() and exact_path.is_file():
        return str(exact_path)
    
    # If no extension in path, try common image extensions
    if '.' not in Path(image_path).name:
        for ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp']:
            test_path = migration_path / (image_path + ext)
            if test_path.exists() and test_path.is_file():
                return str(test_path)
    
    # Try finding files that contain this path (handles restored extensions)
    parent_dir = migration_path / str(Path(image_path).parent)
    if parent_dir.exists() and parent_dir.is_dir():
        base_name = Path(image_path).name
        for file in parent_dir.iterdir():
            if file.is_file() and file.name.startswith(base_name):
                return str(file)
    
    return None


def path_to_renamed_filename(image_path: str) -> str:
    """
    Convert image path to renamed filename pattern.
    
    Example:
    art-of-teaching/gallery/dm-046.jpg -> art-of-teaching_gallery_dm-046.jpg
    """
    path = Path(image_path)
    
    # Split into directory parts and filename
    parts = list(path.parent.parts) + [path.stem]
    
    # Join with underscores
    renamed = '_'.join(parts)
    
    # Add extension
    if path.suffix:
        renamed += path.suffix
    
    return renamed


def html_file_to_cms_path(html_path: str, base_dir: str) -> str:
    """
    Convert HTML file path to CMS asset path.
    
    Example:
    /path/to/migration-clean/about/data-reporting/consumer-information-migration.html
    -> /about/data-reporting/consumer-information
    """
    rel_path = os.path.relpath(html_path, base_dir)
    
    if rel_path.endswith('-migration.html'):
        rel_path = rel_path[:-len('-migration.html')]
    
    cms_path = '/' + rel_path.replace(os.sep, '/')
    
    return cms_path


def scan_for_images(migration_clean_dir: str, migration_dir: str) -> List[Dict[str, str]]:
    """
    Scan all HTML files for image references and locate actual files.
    
    Returns:
        List of dicts with keys: 
        - original_path: Path as found in HTML
        - actual_file: Full path to actual image file in migration dir
        - renamed_file: New filename after renaming
        - cms_asset_path: CMS path of the page referencing the image
        - source_file: HTML file that references this image
    """
    results = []
    migration_clean_path = Path(migration_clean_dir)
    
    # Find all *-migration.html files
    html_files = list(migration_clean_path.rglob('*-migration.html'))
    print(f"Found {len(html_files)} migration HTML files to scan")
    
    images_not_found = set()
    
    for idx, html_file in enumerate(html_files, 1):
        # Progress indicator
        if idx % 100 == 0:
            print(f"Processed {idx}/{len(html_files)} files...")
        
        # Get CMS asset path
        cms_path = html_file_to_cms_path(str(html_file), migration_clean_dir)
        
        # Extract images
        image_srcs = extract_images_from_file(str(html_file))
        
        # Process each image
        for src in image_srcs:
            should_process, extracted_path = is_processable_image(src)
            if not should_process:
                continue
            
            # Normalize path
            normalized_path = normalize_image_path(extracted_path)
            
            # Find actual file
            actual_file = find_image_file(normalized_path, migration_dir)
            
            if actual_file:
                # Get actual path relative to migration dir
                actual_rel_path = os.path.relpath(actual_file, migration_dir)
                
                # Generate renamed filename
                renamed = path_to_renamed_filename(actual_rel_path)
                
                results.append({
                    'original_path': src,
                    'actual_path': actual_rel_path,
                    'renamed_file': renamed,
                    'cms_asset_path': cms_path,
                    'source_file': str(html_file.relative_to(migration_clean_path))
                })
            else:
                images_not_found.add(normalized_path)
    
    # Report missing images
    if images_not_found:
        print(f"\n⚠️  Warning: {len(images_not_found)} unique images not found in migration directory")
        if len(images_not_found) <= 20:
            print("Missing images:")
            for img in sorted(images_not_found):
                print(f"   {img}")
    
    return results


def copy_and_rename_images(results: List[Dict[str, str]], 
                           migration_dir: str, 
                           output_dir: str) -> int:
    """
    Copy images to output directory with renamed filenames.
    
    Returns:
        Number of files copied
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get unique images to copy (deduplicate)
    unique_images = {}
    for r in results:
        renamed = r['renamed_file']
        if renamed not in unique_images:
            actual_file = Path(migration_dir) / r['actual_path']
            unique_images[renamed] = actual_file
    
    print(f"\nCopying {len(unique_images)} unique images to {output_dir}")
    
    copied = 0
    for renamed, source_file in unique_images.items():
        dest_file = output_path / renamed
        
        try:
            shutil.copy2(source_file, dest_file)
            copied += 1
            
            if copied % 100 == 0:
                print(f"Copied {copied}/{len(unique_images)} files...")
        except Exception as e:
            print(f"❌ Error copying {source_file} -> {dest_file}: {e}")
    
    return copied


def save_to_csv(results: List[Dict[str, str]], output_file: str):
    """Save results to CSV file."""
    if not results:
        print("No images found")
        return
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'renamed_file', 
            'cms_asset_path', 
            'original_path',
            'actual_path',
            'source_file'
        ])
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n✅ Saved {len(results)} image references to {output_file}")


def main():
    """Main execution."""
    # Paths
    migration_clean_dir = os.path.expanduser(
        '~/Repositories/wjoell/slc-edu-migration/source-assets/migration-clean'
    )
    migration_dir = os.path.expanduser(
        '~/Repositories/wjoell/slc-edu-migration/source-assets/migration'
    )
    output_dir = os.path.expanduser(
        '~/Repositories/wjoell/slc-edu-migration/source-assets/images-upload'
    )
    csv_output = os.path.expanduser(
        '~/Repositories/wjoell/slc-edu-migration/source-assets/image_references_report.csv'
    )
    
    # Verify directories exist
    if not os.path.exists(migration_clean_dir):
        print(f"❌ Error: Directory not found: {migration_clean_dir}")
        return
    
    if not os.path.exists(migration_dir):
        print(f"❌ Error: Directory not found: {migration_dir}")
        return
    
    print(f"Scanning HTML: {migration_clean_dir}")
    print(f"Image source: {migration_dir}")
    print(f"Output directory: {output_dir}")
    print(f"CSV report: {csv_output}\n")
    
    # Scan for images
    results = scan_for_images(migration_clean_dir, migration_dir)
    
    if not results:
        print("No images found to process")
        return
    
    # Save CSV report
    save_to_csv(results, csv_output)
    
    # Copy and rename images
    copied = copy_and_rename_images(results, migration_dir, output_dir)
    
    # Summary statistics
    unique_images = len(set(r['renamed_file'] for r in results))
    unique_pages = len(set(r['cms_asset_path'] for r in results))
    
    print(f"\n📊 Summary:")
    print(f"   Total image references: {len(results)}")
    print(f"   Unique images: {unique_images}")
    print(f"   Pages with images: {unique_pages}")
    print(f"   Files copied: {copied}")


if __name__ == '__main__':
    main()
