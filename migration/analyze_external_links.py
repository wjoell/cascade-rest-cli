"""
Analyze external links to identify candidates for CMS link assets.

Focuses on:
- Heavily repeated links (same URL used multiple times)
- Key domains: application/aid, intranet (my.slc.edu), giving, external resources
- Domain-level analysis to show patterns

Outputs:
1. Domain statistics (count, unique URLs per domain)
2. Most repeated individual URLs
3. Categorized link recommendations
"""

import csv
from urllib.parse import urlparse
from collections import defaultdict
from typing import Dict, List, Tuple


def load_external_links(csv_file: str) -> List[Dict[str, str]]:
    """Load external links from CSV."""
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def analyze_by_domain(links: List[Dict[str, str]]) -> Dict[str, Dict]:
    """
    Analyze links grouped by domain.
    
    Returns:
        Dict mapping domain to {
            'count': total occurrences,
            'unique_urls': number of unique URLs,
            'urls': {url: count}
        }
    """
    domain_data = defaultdict(lambda: {
        'count': 0,
        'unique_urls': 0,
        'urls': defaultdict(int)
    })
    
    for link in links:
        url = link['url']
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        domain_data[domain]['count'] += 1
        domain_data[domain]['urls'][url] += 1
    
    # Calculate unique URLs per domain
    for domain in domain_data:
        domain_data[domain]['unique_urls'] = len(domain_data[domain]['urls'])
    
    return dict(domain_data)


def categorize_domains(domain_data: Dict[str, Dict]) -> Dict[str, List[Tuple[str, int, int]]]:
    """
    Categorize domains by type.
    
    Returns:
        Dict mapping category to list of (domain, count, unique_urls)
    """
    categories = {
        'Applications & Admissions': [],
        'Study Abroad (Terradotta)': [],
        'Financial Aid & Payments': [],
        'Intranet (MySLC)': [],
        'Alumni & Giving': [],
        'Student Services': [],
        'External Resources': [],
        'Review/Staging (pending)': [],
        'Social Media': [],
        'Other SLC Subdomains': [],
        'Other External': []
    }
    
    # Application/Admissions domains
    app_domains = ['apply.slc.edu']
    
    # Study abroad (terradotta)
    terradotta_domains = ['sarahlawrence-iep.terradotta.com']
    
    # Financial aid domains
    aid_domains = ['fafsa.gov', 'studentaid.gov', 'sarahlawrence.datacenter.adirondacksolutions.com']
    
    # MySLC intranet
    myslc_domains = ['my.slc.edu']
    
    # Alumni & giving
    alumni_domains = ['alum.slc.edu', 'give.slc.edu', 'connect.slc.edu']
    
    # Student services
    student_domains = [
        'getinvolved.slc.edu',  # GryphonLink
        '1card.slc.edu',
        'print.slc.edu',
        'sarahlawrence.joinhandshake.com',  # Career services
        'sarahlawrence.thrivingcampus.com',  # Mental health
        'sarahlawrence.turbovote.org'  # Voter registration
    ]
    
    # Review/staging
    review_domains = ['pending.sarahlawrence.edu', 'protect-us.mimecast.com']
    
    # Social media
    social_domains = [
        'www.facebook.com', 'www.instagram.com', 'www.twitter.com',
        'twitter.com', 'instagram.com', 'facebook.com',
        'www.youtube.com', 'youtube.com', 'vimeo.com'
    ]
    
    for domain, data in domain_data.items():
        count = data['count']
        unique = data['unique_urls']
        entry = (domain, count, unique)
        
        if domain in app_domains:
            categories['Applications & Admissions'].append(entry)
        elif domain in terradotta_domains:
            categories['Study Abroad (Terradotta)'].append(entry)
        elif domain in aid_domains:
            categories['Financial Aid & Payments'].append(entry)
        elif domain in myslc_domains:
            categories['Intranet (MySLC)'].append(entry)
        elif domain in alumni_domains:
            categories['Alumni & Giving'].append(entry)
        elif domain in student_domains:
            categories['Student Services'].append(entry)
        elif domain in review_domains:
            categories['Review/Staging (pending)'].append(entry)
        elif domain in social_domains:
            categories['Social Media'].append(entry)
        elif domain.endswith('.slc.edu') or domain.endswith('.sarahlawrence.edu'):
            categories['Other SLC Subdomains'].append(entry)
        else:
            # Only include external domains with 5+ occurrences
            if count >= 5:
                categories['External Resources'].append(entry)
            else:
                categories['Other External'].append(entry)
    
    # Sort each category by count descending
    for category in categories:
        categories[category].sort(key=lambda x: x[1], reverse=True)
    
    return categories


def find_repeated_urls(links: List[Dict[str, str]], min_count: int = 5) -> List[Tuple[str, int, List[str]]]:
    """
    Find URLs that appear multiple times.
    
    Returns:
        List of (url, count, list of pages using it)
    """
    url_usage = defaultdict(lambda: {'count': 0, 'pages': set()})
    
    for link in links:
        url = link['url']
        page = link['cms_asset_path']
        url_usage[url]['count'] += 1
        url_usage[url]['pages'].add(page)
    
    # Filter and sort
    repeated = [
        (url, data['count'], sorted(list(data['pages'])))
        for url, data in url_usage.items()
        if data['count'] >= min_count
    ]
    
    repeated.sort(key=lambda x: x[1], reverse=True)
    return repeated


def print_analysis(domain_data: Dict, categories: Dict, repeated_urls: List):
    """Print formatted analysis."""
    
    print("=" * 80)
    print("EXTERNAL LINKS ANALYSIS - CMS LINK ASSET CANDIDATES")
    print("=" * 80)
    print()
    
    # Summary
    total_links = sum(d['count'] for d in domain_data.values())
    total_domains = len(domain_data)
    print(f"📊 Overview:")
    print(f"   Total external link instances: {total_links:,}")
    print(f"   Unique domains: {total_domains}")
    print(f"   URLs repeated 5+ times: {len(repeated_urls)}")
    print()
    
    # Categorized domains
    print("=" * 80)
    print("DOMAINS BY CATEGORY")
    print("=" * 80)
    print()
    
    for category, domains in categories.items():
        if not domains:
            continue
        
        print(f"\n{'═' * 80}")
        print(f"  {category}")
        print(f"{'═' * 80}")
        print(f"{'Domain':<50} {'Count':>8} {'Unique':>8}")
        print(f"{'-' * 50} {'-' * 8} {'-' * 8}")
        
        for domain, count, unique in domains[:20]:  # Top 20 per category
            print(f"{domain:<50} {count:>8,} {unique:>8}")
        
        if len(domains) > 20:
            print(f"\n   ... and {len(domains) - 20} more domains")
        
        # Category summary
        cat_total = sum(d[1] for d in domains)
        cat_unique = sum(d[2] for d in domains)
        print(f"\n   Category Total: {cat_total:,} links across {cat_unique:,} unique URLs")
    
    # Most repeated URLs
    print("\n\n" + "=" * 80)
    print("MOST REPEATED INDIVIDUAL URLs (5+ occurrences)")
    print("=" * 80)
    print()
    
    print(f"{'Count':>6} {'Domain':<40} URL")
    print(f"{'-' * 6} {'-' * 40} {'-' * 80}")
    
    for url, count, pages in repeated_urls[:50]:  # Top 50
        domain = urlparse(url).netloc
        # Truncate URL for display
        display_url = url if len(url) <= 80 else url[:77] + '...'
        print(f"{count:>6} {domain:<40} {display_url}")
    
    print(f"\n   Showing top 50 of {len(repeated_urls)} repeated URLs")
    
    # Recommendations
    print("\n\n" + "=" * 80)
    print("RECOMMENDATIONS FOR CMS LINK ASSETS")
    print("=" * 80)
    print()
    
    print("🎯 HIGH PRIORITY - Create link assets for these:")
    print()
    
    high_priority = []
    
    # MySLC links
    if categories['Intranet (MySLC)']:
        myslc_count = sum(d[1] for d in categories['Intranet (MySLC)'])
        myslc_unique = sum(d[2] for d in categories['Intranet (MySLC)'])
        high_priority.append(f"   ✓ MySLC (my.slc.edu): {myslc_count} links, {myslc_unique} unique URLs")
    
    # Applications
    if categories['Applications & Admissions']:
        app_count = sum(d[1] for d in categories['Applications & Admissions'])
        app_unique = sum(d[2] for d in categories['Applications & Admissions'])
        high_priority.append(f"   ✓ Applications/Admissions: {app_count} links, {app_unique} unique URLs")
    
    # Financial aid
    if categories['Financial Aid & Payments']:
        aid_count = sum(d[1] for d in categories['Financial Aid & Payments'])
        aid_unique = sum(d[2] for d in categories['Financial Aid & Payments'])
        high_priority.append(f"   ✓ Financial Aid: {aid_count} links, {aid_unique} unique URLs")
    
    # Student services
    if categories['Student Services']:
        student_count = sum(d[1] for d in categories['Student Services'])
        student_unique = sum(d[2] for d in categories['Student Services'])
        high_priority.append(f"   ✓ Student Services: {student_count} links, {student_unique} unique URLs")
    
    # Alumni & giving
    if categories['Alumni & Giving']:
        alumni_count = sum(d[1] for d in categories['Alumni & Giving'])
        alumni_unique = sum(d[2] for d in categories['Alumni & Giving'])
        high_priority.append(f"   ✓ Alumni & Giving: {alumni_count} links, {alumni_unique} unique URLs")
    
    for item in high_priority:
        print(item)
    
    print()
    print("⚠️  REVIEW - May or may not need link assets:")
    print()
    print(f"   • Social Media: {sum(d[1] for d in categories['Social Media'])} links")
    print(f"     (Consider: Create reusable links for main profiles)")
    print()
    print(f"   • External Resources: {sum(d[1] for d in categories['External Resources'])} links")
    print(f"     (Consider: Only for frequently repeated external sites)")
    
    print()
    print("❌ SKIP - Don't create link assets:")
    print()
    print(f"   • Review/Staging (pending.sarahlawrence.edu): {sum(d[1] for d in categories['Review/Staging (pending)'])} links")
    print(f"     (These are temporary review links)")
    print()
    print(f"   • Other External: {sum(d[1] for d in categories['Other External'])} links")
    print(f"     (Low-frequency external links, embed directly)")


def save_recommendations(categories: Dict, repeated_urls: List, output_file: str):
    """Save detailed recommendations to CSV."""
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Category', 'Priority', 'Domain', 'URL', 'Count', 'Notes'])
        
        # High priority: MySLC
        for domain, count, unique in categories['Intranet (MySLC)']:
            writer.writerow(['Intranet (MySLC)', 'HIGH', domain, '', count, f'{unique} unique URLs'])
        
        # High priority: Applications
        for domain, count, unique in categories['Applications & Admissions']:
            writer.writerow(['Applications & Admissions', 'HIGH', domain, '', count, f'{unique} unique URLs'])
        
        # High priority: Financial Aid
        for domain, count, unique in categories['Financial Aid & Payments']:
            writer.writerow(['Financial Aid', 'HIGH', domain, '', count, f'{unique} unique URLs'])
        
        # High priority: Student Services
        for domain, count, unique in categories['Student Services']:
            writer.writerow(['Student Services', 'HIGH', domain, '', count, f'{unique} unique URLs'])
        
        # High priority: Alumni & Giving
        for domain, count, unique in categories['Alumni & Giving']:
            writer.writerow(['Alumni & Giving', 'HIGH', domain, '', count, f'{unique} unique URLs'])
        
        # Medium priority: Repeated external resources
        for url, count, pages in repeated_urls:
            if count >= 10:  # Only highly repeated
                domain = urlparse(url).netloc
                # Skip if already in high priority categories
                if domain not in ['my.slc.edu', 'apply.slc.edu', 'alum.slc.edu', 
                                 'pending.sarahlawrence.edu', 'protect-us.mimecast.com']:
                    writer.writerow(['Repeated URL', 'MEDIUM', domain, url, count, 
                                   f'Used on {len(pages)} pages'])


def main():
    """Main execution."""
    import os
    
    csv_file = os.path.expanduser(
        '~/Repositories/wjoell/slc-edu-migration/source-assets/external_links_report.csv'
    )
    output_file = os.path.expanduser(
        '~/Repositories/wjoell/slc-edu-migration/source-assets/link_asset_recommendations.csv'
    )
    
    if not os.path.exists(csv_file):
        print(f"❌ Error: CSV file not found: {csv_file}")
        return
    
    # Load and analyze
    print("Loading external links...")
    links = load_external_links(csv_file)
    
    print("Analyzing domains...")
    domain_data = analyze_by_domain(links)
    
    print("Categorizing links...")
    categories = categorize_domains(domain_data)
    
    print("Finding repeated URLs...")
    repeated_urls = find_repeated_urls(links, min_count=5)
    
    # Print analysis
    print_analysis(domain_data, categories, repeated_urls)
    
    # Save recommendations
    print(f"\n\n💾 Saving recommendations to: {output_file}")
    save_recommendations(categories, repeated_urls, output_file)
    print("✅ Done!")


if __name__ == '__main__':
    main()
