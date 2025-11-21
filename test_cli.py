#!/usr/bin/env python3
"""
Test script for Cascade REST CLI

This script demonstrates the CLI functionality without requiring actual authentication.
"""

import subprocess
import sys


def test_help():
    """Test that help commands work"""
    print("🔍 Testing help commands...")

    # Test main help
    try:
        result = subprocess.run(
            ["python", "cli.py", "--help"], capture_output=True, text=True, check=True
        )
        print("✅ Main help works")
    except subprocess.CalledProcessError as e:
        print(f"❌ Main help failed: {e}")
        return False

    # Test command help
    commands = [
        "setup",
        "search",
        "read",
        "ls",
        "update",
        "publish",
        "reports",
        "interactive",
    ]
    for cmd in commands:
        try:
            result = subprocess.run(
                ["python", "cli.py", cmd, "--help"],
                capture_output=True,
                text=True,
                check=True,
            )
            print(f"✅ {cmd} help works")
        except subprocess.CalledProcessError as e:
            print(f"❌ {cmd} help failed: {e}")
            return False

    return True


def test_invalid_commands():
    """Test that invalid commands give appropriate errors"""
    print("\n🔍 Testing invalid commands...")

    # Test invalid command
    try:
        result = subprocess.run(
            ["python", "cli.py", "invalid_command"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            print("✅ Invalid command properly rejected")
        else:
            print("❌ Invalid command should have been rejected")
            return False
    except Exception as e:
        print(f"❌ Error testing invalid command: {e}")
        return False

    # Test missing arguments
    try:
        result = subprocess.run(
            ["python", "cli.py", "read"], capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            print("✅ Missing arguments properly rejected")
        else:
            print("❌ Missing arguments should have been rejected")
            return False
    except Exception as e:
        print(f"❌ Error testing missing arguments: {e}")
        return False

    return True


def test_cli_structure():
    """Test that CLI structure is correct"""
    print("\n🔍 Testing CLI structure...")

    # Test that all expected commands exist
    expected_commands = [
        "setup",
        "search",
        "read",
        "ls",
        "update",
        "publish",
        "reports",
        "interactive",
    ]

    try:
        result = subprocess.run(
            ["python", "cli.py", "--help"], capture_output=True, text=True, check=True
        )
        help_text = result.stdout

        for cmd in expected_commands:
            if cmd in help_text:
                print(f"✅ Command '{cmd}' found in help")
            else:
                print(f"❌ Command '{cmd}' missing from help")
                return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Error getting help: {e}")
        return False

    return True


def main():
    """Run all tests"""
    print("🚀 Testing Cascade REST CLI")
    print("=" * 40)

    tests = [
        ("CLI Structure", test_cli_structure),
        ("Help Commands", test_help),
        ("Invalid Commands", test_invalid_commands),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        if test_func():
            print(f"✅ {test_name} test passed")
            passed += 1
        else:
            print(f"❌ {test_name} test failed")

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! CLI is ready to use.")
        print("\n💡 Next steps:")
        print("1. Run 'python cli.py setup' to configure authentication")
        print("2. Try 'python cli.py interactive' for interactive mode")
        print("3. Check the README.md for usage examples")
    else:
        print("⚠️  Some tests failed. Please check the CLI implementation.")
        sys.exit(1)


if __name__ == "__main__":
    main()
