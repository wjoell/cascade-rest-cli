#!/usr/bin/env python3
"""
Update bool-status field in group-page-section-item
"""

import cascade_rest as cascade
from session_manager import session_manager

# Load session
session = session_manager.get_session()
if not session:
    print("❌ No active session. Please connect first.")
    exit(1)

cms_path = session["cms_path"]
if session.get("api_key"):
    auth = {"apiKey": session["api_key"]}
else:
    auth = {"u": session["username"], "p": session["password"]}

# Asset details
asset_id = "e179c5267f000101269ba29b4762cdbd"
asset_type = "page"

# Read the asset
print(f"📖 Reading asset {asset_id}...")
result = cascade.read_single_asset(cms_path, auth, asset_type, asset_id)

if not result:
    print("❌ Failed to read asset")
    exit(1)

# Find and update the bool-status field
asset_data = result["asset"]["page"]
structured_data_nodes = asset_data["structuredData"]["structuredDataNodes"]

# Find the group-page-section-item group
found = False
for node in structured_data_nodes:
    if node.get("identifier") == "group-page-section-item":
        # Find bool-status within this group
        for inner_node in node.get("structuredDataNodes", []):
            if inner_node.get("identifier") == "bool-status":
                print(f"✅ Found bool-status field with value: {inner_node.get('text')}")
                inner_node["text"] = "true"
                found = True
                print(f"✏️  Updated bool-status to: true")
                break
        break

if not found:
    print("❌ Could not find bool-status field")
    exit(1)

# Prepare the edit payload
payload = {"asset": {"page": asset_data}}

# Edit the asset
print(f"💾 Saving changes...")
edit_result = cascade.edit_single_asset(cms_path, auth, asset_type, asset_id, payload)

if edit_result.get("success"):
    print("✅ Successfully updated bool-status to 'true'")
else:
    print(f"❌ Failed to update: {edit_result.get('message', 'Unknown error')}")
