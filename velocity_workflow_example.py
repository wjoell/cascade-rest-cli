#!/usr/bin/env python3
"""
Velocity Asset Processing Workflow Example

This demonstrates how to process assets identified by Velocity queries
using the CLI's CSV import functionality.
"""

import subprocess
import json
from pathlib import Path
from cli import CascadeCLI


def create_velocity_csv(
    asset_ids: list, asset_type: str = "page", site: str = "main_site"
) -> str:
    """Create a CSV file from Velocity-generated asset IDs"""

    csv_content = (
        "id,name,path,type,site,metadata_field_1,metadata_field_2,tag_1,tag_2\n"
    )

    for asset_id in asset_ids:
        # You would replace these placeholder values with actual data from your CMS
        csv_content += f"{asset_id},Asset_{asset_id},/path/to/{asset_id},{asset_type},{site},new_value,2024,priority,updated\n"

    csv_file = "velocity_assets.csv"
    with open(csv_file, "w") as f:
        f.write(csv_content)

    print(f"✅ Created CSV with {len(asset_ids)} assets: {csv_file}")
    return csv_file


def process_velocity_assets(
    csv_file: str, operation: str = "metadata", dry_run: bool = True
):
    """Process assets from Velocity-generated CSV"""

    print(f"\n🔄 Processing {operation} operation on {csv_file}")
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")

    try:
        # Run the CLI command
        cmd = ["python", "cli.py", "csv-import", csv_file, "--operation", operation]
        if dry_run:
            cmd.append("--dry-run")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Processing completed successfully")
            print(result.stdout)
        else:
            print("❌ Processing failed")
            print(result.stderr)

    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Example workflow for processing Velocity-identified assets"""

    print("🚀 Velocity Asset Processing Workflow")
    print("=" * 50)

    # Example asset IDs (these would come from your Velocity query)
    velocity_asset_ids = [
        "abc123def456",
        "def456ghi789",
        "ghi789jkl012",
        "jkl012mno345",
        "mno345pqr678",
    ]

    print(f"📋 Processing {len(velocity_asset_ids)} assets from Velocity query")

    # Step 1: Create CSV from Velocity asset IDs
    csv_file = create_velocity_csv(velocity_asset_ids)

    # Step 2: Process with dry run first
    print("\n" + "=" * 50)
    print("STEP 1: Dry Run - Preview Changes")
    print("=" * 50)
    process_velocity_assets(csv_file, "metadata", dry_run=True)

    # Step 3: Process tags with dry run
    print("\n" + "=" * 50)
    print("STEP 2: Dry Run - Preview Tag Updates")
    print("=" * 50)
    process_velocity_assets(csv_file, "tags", dry_run=True)

    # Step 4: Ask user if they want to proceed
    print("\n" + "=" * 50)
    print("REVIEW COMPLETE")
    print("=" * 50)
    print("Review the dry run output above.")
    print("To execute the actual changes, run:")
    print(f"  python cli.py csv-import {csv_file} --operation metadata")
    print(f"  python cli.py csv-import {csv_file} --operation tags")

    # Step 5: Show rollback information
    print(f"\n📋 To view rollback options after processing:")
    print(f"  python cli.py rollback-list")

    # Cleanup
    if Path(csv_file).exists():
        Path(csv_file).unlink()
        print(f"\n🧹 Cleaned up temporary file: {csv_file}")


if __name__ == "__main__":
    main()
