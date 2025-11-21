#!/usr/bin/env python3
"""
Batch Operation Examples for Cascade REST CLI

This script demonstrates common batch operations for academic year updates,
course management, and faculty information updates.
"""

import subprocess
import json
from typing import Dict, List, Any


def run_batch_command(cmd: List[str], description: str) -> Dict[str, Any]:
    """Run a batch command and return results"""
    print(f"\n🔄 {description}")
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ Command completed successfully")
        return {"success": True, "output": result.stdout, "error": None}
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e.stderr}")
        return {"success": False, "output": None, "error": e.stderr}


def academic_year_update_workflow():
    """Example workflow for updating academic year pages"""
    print("🎓 Academic Year Update Workflow")
    print("=" * 50)

    # Example: Update all 2024-2025 pages
    academic_year = "2024-2025"

    # 1. Preview what would be updated (dry run)
    print("\n1️⃣ Previewing changes (dry run)...")
    run_batch_command(
        [
            "python",
            "cli.py",
            "batch-update",
            "page",
            academic_year,
            "academic_year",
            academic_year,
            "--dry-run",
        ],
        "Preview academic year updates",
    )

    # 2. Update academic year field
    print("\n2️⃣ Updating academic year field...")
    run_batch_command(
        [
            "python",
            "cli.py",
            "batch-update",
            "page",
            academic_year,
            "academic_year",
            academic_year,
        ],
        "Update academic year field",
    )

    # 3. Set semester tag
    print("\n3️⃣ Setting semester tag...")
    run_batch_command(
        [
            "python",
            "cli.py",
            "batch-tag",
            "page",
            academic_year,
            "semester",
            "Fall 2024",
        ],
        "Set semester tag",
    )

    # 4. Publish updated pages
    print("\n4️⃣ Publishing updated pages...")
    run_batch_command(
        ["python", "cli.py", "batch-publish", "page", academic_year],
        "Publish academic year pages",
    )


def course_catalog_workflow():
    """Example workflow for course catalog updates"""
    print("\n📚 Course Catalog Update Workflow")
    print("=" * 50)

    # Example: Update course pages in catalogue site
    site = "catalogue"
    path_pattern = "course"

    # 1. Update catalog year for course pages
    print("\n1️⃣ Updating catalog year...")
    run_batch_command(
        [
            "python",
            "cli.py",
            "batch-update",
            "page",
            path_pattern,
            "catalog_year",
            "2024-2025",
            "--site",
            site,
        ],
        "Update catalog year for courses",
    )

    # 2. Set course status
    print("\n2️⃣ Setting course status...")
    run_batch_command(
        [
            "python",
            "cli.py",
            "batch-tag",
            "page",
            path_pattern,
            "status",
            "active",
            "--site",
            site,
        ],
        "Set course status",
    )

    # 3. Publish course pages
    print("\n3️⃣ Publishing course pages...")
    run_batch_command(
        ["python", "cli.py", "batch-publish", "page", path_pattern, "--site", site],
        "Publish course pages",
    )


def faculty_directory_workflow():
    """Example workflow for faculty directory updates"""
    print("\n👥 Faculty Directory Update Workflow")
    print("=" * 50)

    # Example: Update faculty pages in myslc site
    site = "myslc"
    path_pattern = "faculty"

    # 1. Update department information
    print("\n1️⃣ Updating department information...")
    run_batch_command(
        [
            "python",
            "cli.py",
            "batch-update",
            "page",
            path_pattern,
            "department",
            "Computer Science",
            "--site",
            site,
        ],
        "Update faculty departments",
    )

    # 2. Set faculty status
    print("\n2️⃣ Setting faculty status...")
    run_batch_command(
        [
            "python",
            "cli.py",
            "batch-tag",
            "page",
            path_pattern,
            "status",
            "active",
            "--site",
            site,
        ],
        "Set faculty status",
    )

    # 3. Publish faculty pages
    print("\n3️⃣ Publishing faculty pages...")
    run_batch_command(
        ["python", "cli.py", "batch-publish", "page", path_pattern, "--site", site],
        "Publish faculty pages",
    )


def cleanup_old_content():
    """Example workflow for cleaning up old content"""
    print("\n🧹 Cleanup Old Content Workflow")
    print("=" * 50)

    # Example: Unpublish old academic year content
    old_year = "2023-2024"

    # 1. Preview what would be unpublished (dry run)
    print("\n1️⃣ Previewing unpublish operations (dry run)...")
    run_batch_command(
        [
            "python",
            "cli.py",
            "batch-publish",
            "page",
            old_year,
            "--unpublish",
            "--dry-run",
        ],
        "Preview unpublish operations",
    )

    # 2. Unpublish old content
    print("\n2️⃣ Unpublishing old content...")
    run_batch_command(
        ["python", "cli.py", "batch-publish", "page", old_year, "--unpublish"],
        "Unpublish old academic year pages",
    )


def search_and_update_workflow():
    """Example workflow for search-based updates"""
    print("\n🔍 Search and Update Workflow")
    print("=" * 50)

    # Example: Find and update specific content
    search_term = "2024-2025"

    # 1. Search for assets first
    print("\n1️⃣ Searching for assets...")
    try:
        result = subprocess.run(
            ["python", "cli.py", "search", search_term],
            capture_output=True,
            text=True,
            check=True,
        )

        search_results = json.loads(result.stdout)
        if "matches" in search_results:
            print(f"Found {len(search_results['matches'])} assets")

            # 2. Update found assets
            print("\n2️⃣ Updating found assets...")
            run_batch_command(
                [
                    "python",
                    "cli.py",
                    "batch-update",
                    "page",
                    search_term,
                    "last_updated",
                    "2024-01-15",
                ],
                "Update last_updated field",
            )
        else:
            print("No assets found")

    except subprocess.CalledProcessError as e:
        print(f"❌ Search failed: {e.stderr}")


def main():
    """Run example workflows"""
    print("🚀 Cascade REST CLI Batch Operation Examples")
    print("=" * 60)

    workflows = [
        ("Academic Year Updates", academic_year_update_workflow),
        ("Course Catalog Updates", course_catalog_workflow),
        ("Faculty Directory Updates", faculty_directory_workflow),
        ("Cleanup Old Content", cleanup_old_content),
        ("Search and Update", search_and_update_workflow),
    ]

    print("\nAvailable workflows:")
    for i, (name, _) in enumerate(workflows, 1):
        print(f"  {i}. {name}")
    print("  6. Run all workflows")
    print("  7. Exit")

    choice = input("\nSelect workflow (1-7): ").strip()

    if choice == "1":
        academic_year_update_workflow()
    elif choice == "2":
        course_catalog_workflow()
    elif choice == "3":
        faculty_directory_workflow()
    elif choice == "4":
        cleanup_old_content()
    elif choice == "5":
        search_and_update_workflow()
    elif choice == "6":
        print("\n🔄 Running all workflows...")
        for name, workflow in workflows:
            print(f"\n{'='*20} {name} {'='*20}")
            try:
                workflow()
            except Exception as e:
                print(f"❌ Error in {name}: {e}")
    elif choice == "7":
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice")


if __name__ == "__main__":
    main()
