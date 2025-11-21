#!/usr/bin/env python3
"""
Example usage scripts for Cascade REST CLI

This file contains example functions that demonstrate how to use the CLI
programmatically for common workflows.
"""

import subprocess
import json
from typing import List, Dict, Any, Optional


def setup_connection(api_key: str, cms_path: str = "https://cms.example.edu") -> bool:
    """Set up connection to Cascade Server"""
    try:
        result = subprocess.run(
            ["python", "cli.py", "setup", "--cms-path", cms_path, "--api-key", api_key],
            capture_output=True,
            text=True,
            check=True,
        )
        print("✅ Connection setup successful")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Connection setup failed: {e.stderr}")
        return False


def search_assets(
    search_terms: str, site: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Search for assets and return results"""
    try:
        cmd = ["python", "cli.py", "search", search_terms]
        if site:
            cmd.extend(["--site", site])

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Search failed: {e.stderr}")
        return []
    except json.JSONDecodeError:
        print("❌ Failed to parse search results")
        return []


def read_asset(asset_type: str, asset_id: str) -> Dict[str, Any]:
    """Read a single asset"""
    try:
        result = subprocess.run(
            ["python", "cli.py", "read", asset_type, asset_id],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to read asset: {e.stderr}")
        return {}
    except json.JSONDecodeError:
        print("❌ Failed to parse asset data")
        return {}


def update_metadata(asset_type: str, asset_id: str, field: str, value: str) -> bool:
    """Update metadata field"""
    try:
        result = subprocess.run(
            ["python", "cli.py", "update", asset_type, asset_id, field, value],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"✅ Updated {field} to '{value}'")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to update metadata: {e.stderr}")
        return False


def publish_asset(asset_type: str, asset_id: str, unpublish: bool = False) -> bool:
    """Publish or unpublish an asset"""
    try:
        cmd = ["python", "cli.py", "publish", asset_type, asset_id]
        if unpublish:
            cmd.append("--unpublish")

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        action = "unpublished" if unpublish else "published"
        print(f"✅ {asset_type} {asset_id} {action}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to publish asset: {e.stderr}")
        return False


def batch_update_metadata(
    assets: List[Dict[str, str]], field: str, value: str
) -> Dict[str, int]:
    """Batch update metadata for multiple assets"""
    results = {"success": 0, "failed": 0}

    for asset in assets:
        success = update_metadata(asset["type"], asset["id"], field, value)
        if success:
            results["success"] += 1
        else:
            results["failed"] += 1

    print(
        f"📊 Batch update complete: {results['success']} successful, {results['failed']} failed"
    )
    return results


def search_and_update(
    search_terms: str, field: str, value: str, site: str = None
) -> Dict[str, int]:
    """Search for assets and update a metadata field"""
    print(f"🔍 Searching for: {search_terms}")
    assets = search_assets(search_terms, site)

    if not assets:
        print("❌ No assets found")
        return {"success": 0, "failed": 0}

    print(f"📝 Found {len(assets)} assets, updating {field} to '{value}'")

    # Extract asset info for batch update
    asset_list = []
    for asset in assets:
        if "id" in asset and "type" in asset:
            asset_list.append({"id": asset["id"], "type": asset["type"]})

    return batch_update_metadata(asset_list, field, value)


# Example usage functions
def example_basic_workflow():
    """Example of a basic workflow"""
    print("🚀 Basic Workflow Example")
    print("=" * 40)

    # 1. Setup connection (you'll need to provide your API key)
    api_key = input("Enter your API key: ")
    if not setup_connection(api_key):
        return

    # 2. Search for assets
    search_term = "faculty"
    print(f"\n🔍 Searching for assets containing '{search_term}'")
    assets = search_assets(search_term)

    if assets:
        print(f"Found {len(assets)} assets")

        # 3. Read first asset details
        first_asset = assets[0]
        print(f"\n📖 Reading details for {first_asset['type']} {first_asset['id']}")
        asset_details = read_asset(first_asset["type"], first_asset["id"])

        if asset_details:
            print("Asset details retrieved successfully")

            # 4. Update metadata (example)
            # update_metadata(first_asset["type"], first_asset["id"], "title", "Updated Title")

    print("\n✅ Basic workflow complete!")


def example_batch_operations():
    """Example of batch operations"""
    print("🔄 Batch Operations Example")
    print("=" * 40)

    # Search for multiple assets and update them
    search_term = "course"
    field = "department"
    value = "Computer Science"

    results = search_and_update(search_term, field, value)
    print(f"Batch operation results: {results}")


if __name__ == "__main__":
    print("Cascade REST CLI Examples")
    print("=" * 30)

    choice = input(
        """
Choose an example:
1. Basic workflow
2. Batch operations
3. Exit

Enter choice (1-3): """
    )

    if choice == "1":
        example_basic_workflow()
    elif choice == "2":
        example_batch_operations()
    elif choice == "3":
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice")
