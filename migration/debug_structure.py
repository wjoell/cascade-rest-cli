#!/usr/bin/env python3
"""Debug script to examine sample populated page structure."""

import sys
import json
sys.path.insert(0, '/Users/winston/Repositories/wjoell/cascade-rest-cli')

from secrets_manager import SecretsManager
from cascade_rest.core import read_single_asset

def main():
    secrets = SecretsManager()
    auth = secrets.get_from_1password(
        'Cascade REST Development Production', 
        'Cascade Rest API Production'
    )
    
    # Read the sample populated page
    result = read_single_asset('https://cms.sarahlawrence.edu:8443', auth, 'page', '357f27287f000101773f7cb1924474b8')
    
    if result:
        nodes = result.get('asset', {}).get('page', {}).get('structuredData', {}).get('structuredDataNodes', [])
        
        print("=== Sample Page Structure ===")
        print(f"Total nodes at root level: {len(nodes)}")
        print("\nRoot node identifiers:")
        for i, node in enumerate(nodes):
            print(f"  {i}: {node.get('identifier')} (type: {node.get('type')})")
        
        print("\n=== First group-page-section-item ===")
        for node in nodes:
            if node.get('identifier') == 'group-page-section-item':
                print(json.dumps(node, indent=2))
                break
    else:
        print('Failed to read sample page')

if __name__ == '__main__':
    main()
