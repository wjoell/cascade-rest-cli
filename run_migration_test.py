#!/usr/bin/env python3
"""
Quick script to run migration with proper connection.
"""

from cli import cli
from secrets_manager import secrets_manager
from migration.orchestrator import run_migration

# Use 1Password to get test credentials
print("🔐 Getting credentials from 1Password...")
vault_name = "Cascade REST Development Test"
item_name = "Cascade Rest API Test"

credentials = secrets_manager.get_from_1password(vault_name, item_name)
if not credentials:
    print("❌ Failed to get credentials from 1Password")
    exit(1)

cms_path = credentials.get('url')
api_key = credentials.get('api_key')

# Setup connection
print(f"🔗 Connecting to {cms_path}...")
if cli.setup_connection(cms_path, api_key):
    print(f"✅ Connected!")
    print(f"   CMS: {cli.cms_path}")
    print(f"   Auth: {'API Key' if cli.auth.get('apiKey') else 'Username/Password'}")
    print()
    
    # Run migration
    result = run_migration(
        auth=cli.auth,
        cms_path=cli.cms_path,
        dry_run=False,
        create_folders_only=True,
        create_pages_only=False
    )
    
    print("\n" + "=" * 80)
    print("DONE!")
    print("=" * 80)
else:
    print("❌ Connection failed")
    exit(1)
