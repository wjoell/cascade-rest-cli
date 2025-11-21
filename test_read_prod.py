#!/usr/bin/env python3
"""
Test script to read an asset from the production environment
"""

from cli import CascadeCLI
from secrets_manager import secrets_manager


def main():
    # Create CLI instance
    cli = CascadeCLI()

    # Get credentials from 1Password
    print("🔑 Fetching credentials from 1Password (Production)...")
    connection_data = secrets_manager.get_from_1password(
        "Cascade REST Development Production", "Cascade Rest API Production"
    )

    if not connection_data:
        print("❌ Failed to fetch credentials from 1Password")
        return

    # Set up connection
    cli.setup_connection(
        connection_data["cms_path"],
        connection_data.get("api_key"),
        connection_data.get("username"),
        connection_data.get("password"),
    )

    print(f"✅ Connected to {connection_data['cms_path']}")

    # Try to read the same asset ID (it might exist on production too)
    asset_id = "b329c0747f0001015b805e7392cf2ab1"
    asset_type = "format"

    print(f"📖 Reading {asset_type} asset: {asset_id}")

    try:
        result = cli.read_asset(asset_type, asset_id)

        if result:
            print("✅ Asset read successfully:")
            print(f"Raw response: {result}")

            if isinstance(result, dict) and result.get("success", True):
                print(f"Asset ID: {result.get('id', 'N/A')}")
                print(f"Name: {result.get('name', 'N/A')}")
                print(f"Type: {result.get('type', 'N/A')}")

                # Show available fields
                print(f"\n📝 Available Fields:")
                for key in result.keys():
                    print(f"  - {key}")
            else:
                print(f"❌ API Error: {result.get('message', 'Unknown error')}")

        else:
            print("❌ Failed to read asset")

    except Exception as e:
        print(f"❌ Error reading asset: {e}")


if __name__ == "__main__":
    main()
