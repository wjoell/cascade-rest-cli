"""
Generate detailed link asset structure for CMS.

Creates a hierarchical structure:
- Folder per domain (e.g., my.slc.edu, apply.slc.edu)
- Link asset (symlink) for each unique URL within that folder
- Fetches page titles for better link naming

Output:
- CSV with folder/link structure and suggested names
- Organized by domain, priority
"""

import csv
import requests
from urllib.parse import urlparse, parse_qs, urlunparse
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import time
import re
from bs4 import BeautifulSoup


def clean_url(url: str) -> str:
    """
    Clean URL by removing tracking parameters and session IDs.
    
    Removes:
    - UTM parameters (utm_source, utm_medium, utm_campaign, etc.)
    - GA session persistence (#_ga...)
    - Other common tracking params
    
    Returns:
        Cleaned URL
    """
    # Parse URL
    parsed = urlparse(url)
    
    # Remove fragment (anchor) if it's a GA session ID
    fragment = parsed.fragment
    if fragment.startswith('_ga='):
        fragment = ''
    
    # Parse query parameters
    if parsed.query:
        from urllib.parse import parse_qsl
        params = parse_qsl(parsed.query)
        
        # Filter out tracking parameters
        tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
            'utm_id', 'utm_source_platform', 'utm_creative_format', 'utm_marketing_tactic',
            '_ga', 'gclid', 'fbclid', 'msclkid', 'mc_cid', 'mc_eid'
        }
        
        cleaned_params = [(k, v) for k, v in params if k not in tracking_params]
        
        # Rebuild query string
        from urllib.parse import urlencode
        query = urlencode(cleaned_params) if cleaned_params else ''
    else:
        query = ''
    
    # Rebuild URL
    cleaned = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        query,
        fragment
    ))
    
    return cleaned


def load_external_links(csv_file: str) -> List[Dict[str, str]]:
    """Load external links from CSV and clean URLs."""
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        links = list(reader)
    
    # Clean all URLs
    for link in links:
        link['url'] = clean_url(link['url'])
    
    return links


def categorize_for_assets(links: List[Dict[str, str]]) -> Dict[str, Dict]:
    """
    Categorize and organize links for asset creation.
    
    Returns:
        Dict mapping category to {
            'domains': {domain: {url: count}}
        }
    """
    categories = {
        'HIGH': defaultdict(lambda: defaultdict(int)),
        'MEDIUM': defaultdict(lambda: defaultdict(int)),
        'SKIP': defaultdict(lambda: defaultdict(int))
    }
    
    # High priority domains
    high_priority = [
        'my.slc.edu',
        'apply.slc.edu', 
        'sarahlawrence-iep.terradotta.com',
        'connect.slc.edu',
        'getinvolved.slc.edu',
        'sarahlawrence.joinhandshake.com',
        'sarahlawrence.thrivingcampus.com',
        '1card.slc.edu',
        'print.slc.edu',
        'sarahlawrence.turbovote.org',
        'studentaid.gov',
        'fafsa.gov',
        'sarahlawrence.datacenter.adirondacksolutions.com'
    ]
    
    # Skip domains
    skip_domains = [
        'pending.sarahlawrence.edu',
        'protect-us.mimecast.com',
        'alum.slc.edu'  # Defunct, replaced by givecampus.com
    ]
    
    for link in links:
        url = link['url']
        
        # Fix malformed URLs
        if 'www%20sarahlawrence%20edu' in url or 'www%20sarahlawrence edu' in url:
            continue  # Skip these errors
        
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        if domain in skip_domains:
            categories['SKIP'][domain][url] += 1
        elif domain in high_priority:
            categories['HIGH'][domain][url] += 1
        else:
            # Medium priority: repeated URLs (10+)
            categories['MEDIUM'][domain][url] += 1
    
    # Filter medium priority to only highly repeated URLs
    filtered_medium = defaultdict(lambda: defaultdict(int))
    for domain, urls in categories['MEDIUM'].items():
        for url, count in urls.items():
            if count >= 10:
                filtered_medium[domain][url] = count
    
    categories['MEDIUM'] = filtered_medium
    
    return categories


def fetch_page_title(url: str, timeout: int = 5) -> Optional[str]:
    """
    Fetch the <title> tag from a webpage.
    
    Returns:
        Page title or None if fetch fails
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find('title')
        
        if title_tag:
            title = title_tag.get_text().strip()
            # Clean up common title patterns
            title = title.replace(' | Sarah Lawrence College', '')
            title = title.replace(' - Sarah Lawrence College', '')
            title = title.replace(' | MySLC', '')
            title = title.replace(' - MySLC', '')
            title = title.strip()
            return title if title else None
        
        return None
    except Exception as e:
        return None


def slugify(text: str) -> str:
    """
    Convert text to a URL-friendly slug.
    
    Examples:
        "Student Accounts" -> "student-accounts"
        "Apply Now!" -> "apply-now"
    """
    import re
    # Convert to lowercase
    text = text.lower()
    # Replace special chars with hyphens
    text = re.sub(r'[^a-z0-9]+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    # Collapse multiple hyphens
    text = re.sub(r'-+', '-', text)
    return text


def suggest_link_name(url: str, title: Optional[str] = None) -> str:
    """
    Suggest a name for the link asset.
    
    Priority:
    1. Use fetched page title (slugified)
    2. Use URL path (last segment)
    3. Use full path
    """
    if title:
        slug = slugify(title)
        if slug and len(slug) > 3:
            return slug
    
    # Fall back to URL path
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    
    if not path:
        return 'home'
    
    # Use last segment
    segments = path.split('/')
    last_segment = segments[-1]
    
    # If it's a file, use it
    if '.' in last_segment:
        name = last_segment.rsplit('.', 1)[0]
    else:
        name = last_segment
    
    # If still empty, use full path
    if not name:
        name = path.replace('/', '-')
    
    return slugify(name) if name else 'index'


def generate_structure(categories: Dict, fetch_titles: bool = True) -> List[Dict]:
    """
    Generate folder/link structure.
    
    Returns:
        List of dicts with: priority, domain, folder_name, url, link_name, title, count
    """
    structure = []
    
    for priority in ['HIGH', 'MEDIUM']:
        domains = categories[priority]
        
        for domain, urls in sorted(domains.items()):
            # Create folder entry
            folder_name = domain.replace('.', '-')
            
            for url, count in sorted(urls.items(), key=lambda x: x[1], reverse=True):
                # Fetch title
                title = None
                if fetch_titles and count >= 5:  # Only fetch for repeated URLs
                    print(f"  Fetching title for: {url[:80]}...")
                    title = fetch_page_title(url)
                    time.sleep(0.5)  # Be polite
                
                # Suggest link name
                link_name = suggest_link_name(url, title)
                
                structure.append({
                    'priority': priority,
                    'domain': domain,
                    'folder_name': folder_name,
                    'url': url,
                    'link_name': link_name,
                    'title': title or '',
                    'count': count
                })
    
    return structure


def save_structure(structure: List[Dict], output_file: str):
    """Save link asset structure to CSV."""
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['priority', 'domain', 'folder_name', 'url', 'link_name', 'title', 'count']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(structure)
    
    print(f"\n✅ Saved link asset structure to: {output_file}")


def print_summary(structure: List[Dict]):
    """Print summary of link asset structure."""
    
    print("\n" + "=" * 80)
    print("LINK ASSET STRUCTURE SUMMARY")
    print("=" * 80)
    print()
    
    # Group by priority and domain
    by_priority = defaultdict(lambda: defaultdict(list))
    for item in structure:
        by_priority[item['priority']][item['domain']].append(item)
    
    for priority in ['HIGH', 'MEDIUM']:
        if not by_priority[priority]:
            continue
        
        print(f"\n{'═' * 80}")
        print(f"  {priority} PRIORITY")
        print(f"{'═' * 80}\n")
        
        for domain in sorted(by_priority[priority].keys()):
            links = by_priority[priority][domain]
            folder_name = links[0]['folder_name']
            
            print(f"📁 Folder: {folder_name}/")
            print(f"   Domain: {domain}")
            print(f"   Links: {len(links)}")
            print()
            
            # Show top 10 links
            for link in links[:10]:
                count_str = f"({link['count']} uses)" if link['count'] > 1 else ""
                title_str = f" - {link['title']}" if link['title'] else ""
                print(f"   🔗 {link['link_name']}{title_str} {count_str}")
                if len(link['url']) > 70:
                    print(f"      {link['url'][:70]}...")
                else:
                    print(f"      {link['url']}")
            
            if len(links) > 10:
                print(f"\n   ... and {len(links) - 10} more links")
            
            print()
    
    # Overall stats
    high_count = sum(len(v) for v in by_priority['HIGH'].values())
    high_domains = len(by_priority['HIGH'])
    medium_count = sum(len(v) for v in by_priority['MEDIUM'].values())
    medium_domains = len(by_priority['MEDIUM'])
    
    print("=" * 80)
    print("TOTALS")
    print("=" * 80)
    print(f"High Priority: {high_count} links across {high_domains} domains")
    print(f"Medium Priority: {medium_count} links across {medium_domains} domains")
    print(f"Total Link Assets to Create: {high_count + medium_count}")


def main():
    """Main execution."""
    import os
    
    csv_file = os.path.expanduser(
        '~/Repositories/wjoell/slc-edu-migration/source-assets/external_links_report.csv'
    )
    output_file = os.path.expanduser(
        '~/Repositories/wjoell/slc-edu-migration/source-assets/link_asset_structure.csv'
    )
    
    if not os.path.exists(csv_file):
        print(f"❌ Error: CSV file not found: {csv_file}")
        return
    
    print("Loading external links...")
    links = load_external_links(csv_file)
    
    print("Categorizing links for asset creation...")
    categories = categorize_for_assets(links)
    
    print("\n🌐 Fetching page titles (this may take a few minutes)...")
    print("Fetching titles for frequently repeated URLs...\n")
    
    # Generate structure with title fetching
    structure = generate_structure(categories, fetch_titles=True)
    
    # Save to CSV
    save_structure(structure, output_file)
    
    # Print summary
    print_summary(structure)
    
    print("\n✨ Done!")


if __name__ == '__main__':
    main()
