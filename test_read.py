#!/usr/bin/env python3
"""
Test script to read an asset from the test environment
"""

from cli import CascadeCLI
from secrets_manager import secrets_manager


def main():
    # Create CLI instance
    cli = CascadeCLI()

    # Get credentials from 1Password
    print("🔑 Fetching credentials from 1Password...")
    connection_data = secrets_manager.get_from_1password(
        "Cascade REST Development Test", "Cascade Rest API Test"
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

    # Read the asset
    asset_id = "b329c0747f0001015b805e7392cf2ab1"
    asset_type = "format"

    print(f"📖 Reading {asset_type} asset: {asset_id}")

    try:
        result = cli.read_asset(asset_type, asset_id)

        if result:
            print("✅ Asset read successfully:")
            print("\n📋 Raw Response:")
            print(f"Type: {type(result)}")
            print(f"Content: {result}")

            # Try to extract common fields
            if isinstance(result, dict):
                print(f"\n🔍 Asset Details:")
                print(f"Asset ID: {result.get('id', 'N/A')}")
                print(f"Name: {result.get('name', 'N/A')}")
                print(f"Type: {result.get('type', 'N/A')}")

                # Check for path information
                if "path" in result:
                    path_info = result["path"]
                    if isinstance(path_info, dict):
                        print(f"Path: {path_info.get('path', 'N/A')}")
                    else:
                        print(f"Path: {path_info}")

                # Show all top-level keys
                print(f"\n📝 Available Fields:")
                for key in result.keys():
                    print(f"  - {key}")

        else:
            print("❌ Failed to read asset")

    except Exception as e:
        print(f"❌ Error reading asset: {e}")


if __name__ == "__main__":
    main()
