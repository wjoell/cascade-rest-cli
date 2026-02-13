"""
Extract external links from migration HTML files.

Scans all *-migration.html files in migration-clean directory and extracts:
- External link URLs (not www.sarahlawrence.edu)
- Link text
- Source page CMS asset path

External links include:
- Other subdomains of sarahlawrence.edu
- *.slc.edu domains
- All other domains
"""

import os
import re
import csv
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse
from typing import List, Dict, Tuple


class LinkExtractor(HTMLParser):
    """HTML parser to extract links and their text content."""
    
    def __init__(self):
        super().__init__()
        self.links = []
        self.current_link = None
        self.current_text = []
    
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            attrs_dict = dict(attrs)
            if 'href' in attrs_dict:
                self.current_link = attrs_dict['href']
                self.current_text = []
    
    def handle_endtag(self, tag):
        if tag == 'a' and self.current_link:
            link_text = ''.join(self.current_text).strip()
            self.links.append((self.current_link, link_text))
            self.current_link = None
            self.current_text = []
    
    def handle_data(self, data):
        if self.current_link is not None:
            self.current_text.append(data)


def is_external_link(url: str) -> bool:
    """
    Determine if a URL is external.
    
    External links are:
    - Not www.sarahlawrence.edu
    - Other subdomains of sarahlawrence.edu
    - *.slc.edu domains
    - All other domains
    
    Returns False for:
    - Relative links (no domain)
    - www.sarahlawrence.edu links
    - Anchor links (#...)
    - JavaScript links
    - mailto links
    """
    # Skip non-http links
    if url.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
        return False
    
    # Skip relative URLs
    if not url.startswith('http'):
        return False
    
    # Parse URL
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # Skip www.sarahlawrence.edu
    if domain == 'www.sarahlawrence.edu':
        return False
    
    # Everything else with a domain is external
    return bool(domain)


def html_file_to_cms_path(html_path: str, base_dir: str) -> str:
    """
    Convert HTML file path to CMS asset path.
    
    Example:
    /path/to/migration-clean/about/data-reporting/consumer-information-migration.html
    -> /about/data-reporting/consumer-information
    """
    # Get relative path from base directory
    rel_path = os.path.relpath(html_path, base_dir)
    
    # Remove -migration.html suffix
    if rel_path.endswith('-migration.html'):
        rel_path = rel_path[:-len('-migration.html')]
    
    # Convert to CMS path (Unix-style, leading slash)
    cms_path = '/' + rel_path.replace(os.sep, '/')
    
    return cms_path


def extract_links_from_file(html_path: str) -> List[Tuple[str, str]]:
    """
    Extract all links from an HTML file.
    
    Returns:
        List of (url, link_text) tuples
    """
    try:
        with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        parser = LinkExtractor()
        parser.feed(content)
        return parser.links
    except Exception as e:
        print(f"Error parsing {html_path}: {e}")
        return []


def scan_migration_files(migration_clean_dir: str) -> List[Dict[str, str]]:
    """
    Scan all *-migration.html files and extract external links.
    
    Returns:
        List of dicts with keys: url, link_text, cms_asset_path, source_file
    """
    results = []
    migration_clean_path = Path(migration_clean_dir)
    
    # Find all *-migration.html files
    html_files = list(migration_clean_path.rglob('*-migration.html'))
    print(f"Found {len(html_files)} migration HTML files to scan")
    
    for html_file in html_files:
        # Get CMS asset path
        cms_path = html_file_to_cms_path(str(html_file), migration_clean_dir)
        
        # Extract links
        links = extract_links_from_file(str(html_file))
        
        # Filter for external links
        for url, link_text in links:
            if is_external_link(url):
                results.append({
                    'url': url,
                    'link_text': link_text,
                    'cms_asset_path': cms_path,
                    'source_file': str(html_file.relative_to(migration_clean_path))
                })
        
        # Progress indicator
        if len(html_files) > 100 and len(results) % 100 == 0:
            print(f"Processed {len(results)} external links so far...")
    
    return results


def save_to_csv(results: List[Dict[str, str]], output_file: str):
    """Save results to CSV file."""
    if not results:
        print("No external links found")
        return
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['cms_asset_path', 'url', 'link_text', 'source_file'])
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n✅ Saved {len(results)} external links to {output_file}")


def main():
    """Main execution."""
    # Paths
    migration_clean_dir = os.path.expanduser(
        '~/Repositories/wjoell/slc-edu-migration/source-assets/migration-clean'
    )
    output_file = os.path.expanduser(
        '~/Repositories/wjoell/slc-edu-migration/source-assets/external_links_report.csv'
    )
    
    # Verify directory exists
    if not os.path.exists(migration_clean_dir):
        print(f"❌ Error: Directory not found: {migration_clean_dir}")
        return
    
    print(f"Scanning: {migration_clean_dir}")
    print(f"Output: {output_file}\n")
    
    # Extract links
    results = scan_migration_files(migration_clean_dir)
    
    # Save results
    save_to_csv(results, output_file)
    
    # Summary statistics
    if results:
        unique_urls = len(set(r['url'] for r in results))
        unique_pages = len(set(r['cms_asset_path'] for r in results))
        print(f"\n📊 Summary:")
        print(f"   Total external link instances: {len(results)}")
        print(f"   Unique URLs: {unique_urls}")
        print(f"   Pages with external links: {unique_pages}")
        
        # Show domain breakdown
        domains = {}
        for r in results:
            domain = urlparse(r['url']).netloc
            domains[domain] = domains.get(domain, 0) + 1
        
        print(f"\n🌐 Top 10 domains:")
        for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   {domain}: {count}")


if __name__ == '__main__':
    main()
