"""
Content cleaning module for migration HTML files.

Removes PHP review blocks and inline SVG elements while preserving
all other well-formed XHTML content.
"""

import re


def strip_html_extension_from_paths(html_content: str) -> str:
    """
    Strip .html extension from root-relative internal paths.
    
    Handles paths that weren't caught by the full-URL rewrite:
    - /ecc/index.html -> /ecc/index
    - /genetic-counseling/index.html -> /genetic-counseling/index
    - /news-events/news/2022-04-18-article-name.html -> /news-events/news/2022-04-18-article-name
    
    Skips:
    - External URLs (http://, https://)
    - PDF links
    - Anchor-only links (#...)
    - Already-processed paths without .html
    
    Args:
        html_content: HTML content with potential .html paths
        
    Returns:
        HTML content with .html extensions removed from internal paths
    """
    def replace_path(match):
        prefix = match.group(1)  # href=" or href='
        path = match.group(2)    # the path
        quote = prefix[-1]       # the quote character
        
        # Skip external URLs
        if path.startswith('http://') or path.startswith('https://'):
            return match.group(0)
        
        # Skip mailto and tel links
        if path.startswith('mailto:') or path.startswith('tel:'):
            return match.group(0)
        
        # Skip PDF links
        if '.pdf' in path.lower():
            return match.group(0)
        
        # Skip anchor-only links
        if path.startswith('#'):
            return match.group(0)
        
        # Remove -migration.html if present
        if '-migration.html' in path:
            path = path.replace('-migration.html', '')
        # Remove .html extension (preserve any hash fragment)
        elif '.html' in path:
            # Split on .html to handle .html#anchor cases
            parts = path.split('.html', 1)
            path = parts[0]
            # If there was a hash fragment after .html, preserve it
            if len(parts) > 1 and parts[1].startswith('#'):
                path += parts[1]
        
        return f'{prefix}{path}{quote}'
    
    # Pattern to match href attributes with paths
    # Captures: href="/path/to/page.html" or href='/path/to/page.html'
    path_pattern = re.compile(
        r'(href=[\'"])([^\'"]*)([\'"])',
        re.IGNORECASE
    )
    
    return path_pattern.sub(replace_path, html_content)


def rewrite_internal_links(html_content: str) -> str:
    """
    Rewrite internal sarahlawrence.edu URLs to CMS-managed paths.
    
    Examples:
    - https://www.sarahlawrence.edu/about/index-migration.html -> /about/index
    - https://www.sarahlawrence.edu/about/index.html#accordion-2-1-1-1 -> /about/index
    - https://www.sarahlawrence.edu/global-education/ -> /global-education/index
    
    Rules:
    - Remove https://www.sarahlawrence.edu prefix
    - Remove hash fragments (# and everything after)
    - Remove -migration.html suffix if present, else remove .html suffix
    - Append 'index' if path ends with '/'
    - Leave PDF links fully qualified (don't rewrite)
    
    Args:
        html_content: HTML content with full URLs
        
    Returns:
        HTML content with rewritten paths
    """
    pdf_links_found = []
    
    def replace_url(match):
        nonlocal pdf_links_found
        full_url = match.group(0)
        # Extract the path after the domain
        # Group 1 is href= or href=", Group 2 is the URL
        path = match.group(2)
        
        # Remove protocol and domain
        if path.startswith('https://www.sarahlawrence.edu'):
            path = path[len('https://www.sarahlawrence.edu'):]
        elif path.startswith('http://www.sarahlawrence.edu'):
            path = path[len('http://www.sarahlawrence.edu'):]
        else:
            # Not a sarahlawrence.edu URL, don't change it
            return full_url
        
        # Check if this is a PDF link - if so, leave it fully qualified and log it
        if '.pdf' in path.lower():
            pdf_links_found.append(match.group(2))  # Store the full URL
            return full_url  # Don't rewrite PDF links
        
        # Remove hash fragment (# and everything after)
        if '#' in path:
            path = path.split('#')[0]
        
        # If path is empty or just '/', make it '/index'
        if not path or path == '/':
            path = '/index'
        # If path ends with '/', append 'index'
        elif path.endswith('/'):
            path = path + 'index'
        # Remove -migration.html suffix if present
        elif '-migration.html' in path:
            path = path.replace('-migration.html', '')
        # Remove .html suffix as fallback
        elif path.endswith('.html'):
            path = path[:-len('.html')]
        
        # Reconstruct the href attribute with the new path
        quote = match.group(1)[-1]  # Get the quote character used (' or ")
        return f'href={quote}{path}{quote}'
    
    # Pattern to match href attributes with sarahlawrence.edu URLs
    # Captures: href="..." or href='...'
    link_pattern = re.compile(
        r'(href=[\'"])((https?://)?www\.sarahlawrence\.edu[^\'"]*)([\'"])',
        re.IGNORECASE
    )
    
    result = link_pattern.sub(replace_url, html_content)
    
    # Log PDF links found (if any)
    if pdf_links_found:
        print(f"  ⚠️  Found {len(pdf_links_found)} PDF link(s) (left fully qualified for follow-up):")
        for pdf_link in pdf_links_found[:5]:  # Show first 5
            print(f"     - {pdf_link}")
        if len(pdf_links_found) > 5:
            print(f"     ... and {len(pdf_links_found) - 5} more")
    
    # Also handle root-relative paths with .html extension (not full URLs)
    # e.g., /ecc/index.html -> /ecc/index
    # But skip external URLs, PDFs, and anchors-only links
    result = strip_html_extension_from_paths(result)
    
    return result


def clean_html_content(html_content: str) -> str:
    """
    Clean migration HTML content by extracting body and removing review sections.
    
    Process:
    1. Extract only the <body> content (no <head>)
    2. Remove style block for student-handbook-utilities
    3. Remove the entire PHP/review block (<?php...?>)
    
    Args:
        html_content: Raw HTML content from migration file
        
    Returns:
        Cleaned body content with review sections removed
    """
    cleaned = html_content
    
    # Stage 1: Extract only the body content
    body_pattern = re.compile(
        r'<body[^>]*>(.*)</body>',
        re.DOTALL | re.IGNORECASE
    )
    body_match = body_pattern.search(cleaned)
    if body_match:
        cleaned = body_match.group(1)
    else:
        # If no body tag found, use entire content (fallback)
        pass
    
    # Stage 2: Remove the entire style block for student-handbook-utilities
    # This comes before the PHP block
    style_pattern = re.compile(
        r'<style>\s*\.student-handbook-utilities\s*\{[^}]*\}[^<]*</style>',
        re.DOTALL
    )
    cleaned = style_pattern.sub('', cleaned)
    
    # Stage 2: Remove the entire PHP block including everything inside
    # Pattern: <?php\nif ($_SERVER['HTTP_HOST']...) {\n$page_info = <<<EOD\n...\nEOD;\necho $page_info;\n}\n?>
    # This includes the SVG and all review content
    php_block_pattern = re.compile(
        r'<\?php\s+if\s+\(\s*\$_SERVER\s*\[\s*[\'"]HTTP_HOST[\'"]\s*\]\s*==\s*[\'"]pending\.sarahlawrence\.edu[\'"]\s*\)\s*\{\s*\$page_info\s*=\s*<<<\s*EOD.*?EOD;\s*echo\s+\$page_info;\s*\}\s*\?>',
        re.DOTALL | re.MULTILINE
    )
    cleaned = php_block_pattern.sub('', cleaned)
    
    # Stage 3: Remove all remaining inline SVG elements
    # Pattern: <svg...>...</svg> (any SVG, not just in review section)
    svg_pattern = re.compile(
        r'<svg\s[^>]*>.*?</svg>',
        re.DOTALL
    )
    cleaned = svg_pattern.sub('', cleaned)
    
    # Stage 4: Rewrite internal links from full URLs to CMS-managed paths
    # Convert https://www.sarahlawrence.edu/... to /...
    cleaned = rewrite_internal_links(cleaned)
    
    return cleaned


def clean_migration_file(file_path: str) -> str:
    """
    Read and clean a migration HTML file.
    
    Args:
        file_path: Path to the migration HTML file
        
    Returns:
        Cleaned HTML content
        
    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file can't be read
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_html = f.read()
    
    return clean_html_content(raw_html)


if __name__ == '__main__':
    # Test the cleaner on the about/index-migration.html file
    import sys
    import os
    
    test_file = '/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/migration-clean/about/index-migration.html'
    
    if os.path.exists(test_file):
        print(f"Testing content cleaner on: {test_file}")
        print("=" * 80)
        
        cleaned = clean_migration_file(test_file)
        
        print(f"\nOriginal file size: {os.path.getsize(test_file)} bytes")
        print(f"Cleaned content size: {len(cleaned)} bytes")
        print(f"\nReduction: {os.path.getsize(test_file) - len(cleaned)} bytes")
        
        # Check if PHP blocks are removed
        if '<?php' in cleaned:
            print("\n⚠️  WARNING: PHP opening tag still present!")
        else:
            print("\n✓ PHP opening tag removed")
            
        if 'EOD;' in cleaned:
            print("⚠️  WARNING: PHP closing tag still present!")
        else:
            print("✓ PHP closing tag removed")
            
        if '<svg' in cleaned:
            print("⚠️  WARNING: SVG elements still present!")
        else:
            print("✓ SVG elements removed")
            
        if 'student-handbook-utilities' in cleaned:
            print("⚠️  WARNING: Review div still present!")
        else:
            print("✓ Review div removed")
            
        if 'Edit this page in MS Word' in cleaned:
            print("⚠️  WARNING: Review link text still present!")
        else:
            print("✓ Review link text removed")
        
        # Show a preview of cleaned content
        print("\n" + "=" * 80)
        print("Preview of cleaned content (first 1000 chars):")
        print("=" * 80)
        print(cleaned[:1000])
        
    else:
        print(f"Test file not found: {test_file}")
        sys.exit(1)
