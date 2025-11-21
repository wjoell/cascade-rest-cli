#!/usr/bin/env python3
"""
Scheduled Jobs Example

This example demonstrates how to use the Cascade CLI's scheduled jobs system
for automating recurring operations.
"""

import subprocess
import json
import time
from datetime import datetime
from typing import Dict, Any


def run_cli_command(command: list) -> Dict[str, Any]:
    """Run a CLI command and return parsed JSON output"""
    try:
        result = subprocess.run(
            ["python", "cli.py"] + command, capture_output=True, text=True, check=True
        )

        return {"output": result.stdout, "stderr": result.stderr, "success": True}

    except subprocess.CalledProcessError as e:
        return {"error": e.stderr, "returncode": e.returncode, "success": False}


def demonstrate_scheduled_jobs():
    """Demonstrate scheduled jobs functionality"""

    print("⏰ Scheduled Jobs System Demo")
    print("=" * 50)

    # Step 1: Show job templates
    print("\n1️⃣ Available Job Templates:")
    result = run_cli_command(["job-templates"])
    print(result["output"])

    # Step 2: Create a sample job
    print("\n2️⃣ Creating a sample job...")
    result = run_cli_command(
        [
            "job-create",
            "Demo Faculty Update",
            "every 5 minutes",
            "search",
            "--type",
            "page",
            "--path-filter",
            "faculty",
            "--limit",
            "5",
        ]
    )
    print(f"Result: {'Success' if result['success'] else 'Failed'}")
    if not result["success"]:
        print(f"Error: {result.get('error', 'Unknown error')}")

    # Step 3: List jobs
    print("\n3️⃣ Listing scheduled jobs...")
    result = run_cli_command(["job-list"])
    print(result["output"])

    # Step 4: Run a job immediately (dry-run)
    print("\n4️⃣ Running job immediately (dry-run)...")
    result = run_cli_command(["job-run", "demo_faculty_update", "--dry-run"])
    print(result["output"])

    # Step 5: Show job history
    print("\n5️⃣ Showing job execution history...")
    result = run_cli_command(["job-history", "demo_faculty_update"])
    print(result["output"])

    # Step 6: Clean up - delete the demo job
    print("\n6️⃣ Cleaning up demo job...")
    result = run_cli_command(["job-delete", "demo_faculty_update"])
    print(f"Cleanup: {'Success' if result['success'] else 'Failed'}")


def create_production_jobs():
    """Create example production jobs"""

    print("\n🏭 Production Job Examples")
    print("=" * 50)

    # Example jobs for different scenarios
    jobs = [
        {
            "name": "Daily Faculty Sync",
            "schedule": "daily at 09:00",
            "command": [
                "batch-update",
                "--type",
                "page",
                "--path-filter",
                "faculty",
                "--field",
                "last_sync",
                "--value",
                "$(date)",
            ],
            "environment": "production",
        },
        {
            "name": "Weekly Course Catalog Update",
            "schedule": "weekly on Monday at 06:00",
            "command": ["csv-import", "courses.csv", "--operation", "metadata"],
            "environment": "production",
        },
        {
            "name": "Academic Year Tag Update",
            "schedule": "every 1 day",
            "command": [
                "batch-tag",
                "--type",
                "page",
                "--path-filter",
                "2024-2025",
                "--tag",
                "academic_year",
                "--value",
                "2024-2025",
            ],
            "environment": "production",
        },
    ]

    print("📋 Example Production Jobs:")
    for job in jobs:
        print(f"\n🔧 {job['name']}")
        print(f"   Schedule: {job['schedule']}")
        print(f"   Environment: {job['environment']}")
        print(f"   Command: {' '.join(job['command'])}")
        print(
            f"   Create: python cli.py job-create '{job['name']}' '{job['schedule']}' {' '.join(job['command'])} --environment {job['environment']}"
        )


def create_test_jobs():
    """Create example test jobs"""

    print("\n🧪 Test Environment Jobs")
    print("=" * 50)

    # Test jobs that run more frequently for validation
    test_jobs = [
        {
            "name": "Test Faculty Validation",
            "schedule": "every 2 hours",
            "command": [
                "search",
                "--type",
                "page",
                "--path-filter",
                "faculty",
                "--dry-run",
            ],
            "environment": "test",
        },
        {
            "name": "Test Course Catalog Sync",
            "schedule": "daily at 14:00",
            "command": [
                "csv-import",
                "test_courses.csv",
                "--operation",
                "metadata",
                "--dry-run",
            ],
            "environment": "test",
        },
    ]

    print("📋 Example Test Jobs:")
    for job in test_jobs:
        print(f"\n🔧 {job['name']}")
        print(f"   Schedule: {job['schedule']}")
        print(f"   Environment: {job['environment']}")
        print(f"   Command: {' '.join(job['command'])}")
        print(
            f"   Create: python cli.py job-create '{job['name']}' '{job['schedule']}' {' '.join(job['command'])} --environment {job['environment']}"
        )


def scheduler_management():
    """Demonstrate scheduler management"""

    print("\n⚙️ Scheduler Management")
    print("=" * 50)

    print("🚀 Starting background scheduler...")
    result = run_cli_command(["scheduler-start"])
    print(f"Start scheduler: {'Success' if result['success'] else 'Failed'}")

    print("\n📊 Checking scheduler status...")
    result = run_cli_command(["job-list"])
    print("Current jobs:")
    print(result["output"])

    print("\n⏹️ Stopping background scheduler...")
    result = run_cli_command(["scheduler-stop"])
    print(f"Stop scheduler: {'Success' if result['success'] else 'Failed'}")


def monitoring_and_cleanup():
    """Demonstrate monitoring and cleanup features"""

    print("\n📊 Monitoring and Cleanup")
    print("=" * 50)

    print("🧹 Cleaning up old execution history...")
    result = run_cli_command(["job-cleanup", "--days", "30"])
    print(result["output"])

    print("\n📈 Performance monitoring...")
    result = run_cli_command(["performance-stats"])
    print(result["output"])


if __name__ == "__main__":
    print("⏰ Cascade CLI Scheduled Jobs Examples")
    print("=" * 60)

    # Show examples and templates
    demonstrate_scheduled_jobs()
    create_production_jobs()
    create_test_jobs()

    print("\n" + "=" * 60)
    print("📝 Notes:")
    print("   • Jobs run in background when scheduler is started")
    print("   • Use --dry-run for testing job commands")
    print("   • Environment-specific jobs help separate test/prod operations")
    print("   • Execution history is automatically tracked and logged")
    print("   • Jobs can be enabled/disabled without deletion")

    # Uncomment to run actual scheduler management
    # scheduler_management()
    # monitoring_and_cleanup()
