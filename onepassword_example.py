#!/usr/bin/env python3
"""
1Password Integration Example

This example demonstrates how to use the Cascade CLI with 1Password
for secure credential management across test and production environments.
"""

import subprocess
import json
from typing import Dict, Any


def run_cli_command(command: list) -> Dict[str, Any]:
    """Run a CLI command and return parsed JSON output"""
    try:
        result = subprocess.run(
            ["python", "cli.py"] + command, capture_output=True, text=True, check=True
        )

        # Try to parse as JSON if possible
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"output": result.stdout, "stderr": result.stderr}

    except subprocess.CalledProcessError as e:
        return {"error": e.stderr, "returncode": e.returncode}


def demonstrate_1password_workflow():
    """Demonstrate a complete 1Password workflow"""

    print("🔑 1Password Integration Workflow Example")
    print("=" * 50)

    # Step 1: List available items in test vault
    print("\n1️⃣ Listing Cascade items in test vault...")
    result = run_cli_command(["list-1password", "Cascade Test"])
    print(f"Result: {result}")

    # Step 2: Connect to test environment
    print("\n2️⃣ Connecting to test environment...")
    result = run_cli_command(["quick-connect", "--env", "test"])
    print(f"Result: {result}")

    # Step 3: Run a test operation (dry run)
    print("\n3️⃣ Running test search operation...")
    result = run_cli_command(
        ["search", "--type", "page", "--path-filter", "2024-2025", "--dry-run"]
    )
    print(f"Found {len(result.get('assets', []))} assets (dry run)")

    # Step 4: Switch to production
    print("\n4️⃣ Switching to production environment...")
    result = run_cli_command(["quick-connect", "--env", "production"])
    print(f"Result: {result}")

    # Step 5: Run production operation
    print("\n5️⃣ Running production search operation...")
    result = run_cli_command(
        ["search", "--type", "page", "--path-filter", "2024-2025", "--dry-run"]
    )
    print(f"Found {len(result.get('assets', []))} assets (dry run)")

    print("\n✅ Workflow completed successfully!")


def demonstrate_manual_1password_connection():
    """Demonstrate manual 1Password connection"""

    print("\n🔧 Manual 1Password Connection Example")
    print("=" * 50)

    # Connect using specific vault and item
    print("\nConnecting using specific vault and item...")
    result = run_cli_command(
        ["connect-1password", "Cascade Test", "Test Service Account"]
    )
    print(f"Result: {result}")

    # Run a simple operation
    print("\nRunning simple operation...")
    result = run_cli_command(["search", "test", "--limit", "5"])
    print(f"Found {len(result.get('assets', []))} assets")


def setup_example():
    """Example of setting up 1Password credentials"""

    print("\n🛠️ 1Password Setup Example")
    print("=" * 50)

    print("To set up 1Password integration:")
    print("1. Install 1Password CLI: https://1password.com/downloads/command-line/")
    print("2. Authenticate: op signin")
    print("3. Create vaults: Cascade Test, Cascade Production")
    print("4. Store service accounts in each vault")
    print("5. Use the CLI commands to connect")

    print("\nExample commands:")
    print(
        "python cli.py setup-1password --vault 'Cascade Test' --item-name 'Test Service Account'"
    )
    print("python cli.py quick-connect --env test")
    print("python cli.py quick-connect --env production")


if __name__ == "__main__":
    print("🔐 Cascade CLI 1Password Integration Examples")
    print("=" * 60)

    # Show setup instructions
    setup_example()

    # Note: The actual workflow examples require 1Password CLI and credentials
    print("\n" + "=" * 60)
    print("📝 Note: To run the workflow examples, you need:")
    print("   • 1Password CLI installed and authenticated")
    print("   • Cascade Test and Cascade Production vaults")
    print("   • Service account items in each vault")
    print("   • Valid Cascade server credentials")

    # Uncomment to run actual examples (requires 1Password setup)
    # demonstrate_1password_workflow()
    # demonstrate_manual_1password_connection()
