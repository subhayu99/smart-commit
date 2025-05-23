#!/usr/bin/env python3
"""Release script for smart-commit."""

import sys
import subprocess
import re
from pathlib import Path

def run_command(cmd, check=True):
    """Run a shell command."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result

def get_current_version():
    """Get current version from __init__.py."""
    init_file = Path("smart_commit/__init__.py")
    content = init_file.read_text()
    match = re.search(r'__version__ = ["\']([^"\']+)["\']', content)
    if match:
        return match.group(1)
    raise ValueError("Could not find version in __init__.py")

def update_version(new_version):
    """Update version in __init__.py."""
    init_file = Path("smart_commit/__init__.py")
    content = init_file.read_text()
    updated = re.sub(
        r'__version__ = ["\'][^"\']+["\']',
        f'__version__ = "{new_version}"',
        content
    )
    init_file.write_text(updated)

def main():
    """Main release process."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/release.py <version>")
        sys.exit(1)
    
    new_version = sys.argv[1]
    current_version = get_current_version()
    
    print(f"Current version: {current_version}")
    print(f"New version: {new_version}")
    
    # Confirm release
    confirm = input("Continue with release? (y/N): ")
    if confirm.lower() != 'y':
        print("Release cancelled.")
        sys.exit(0)
    
    # Update version
    update_version(new_version)
    
    # Run tests
    print("Running tests...")
    run_command("python -m pytest")
    
    # Build package
    print("Building package...")
    run_command("python -m build")
    
    # Check package
    print("Checking package...")
    run_command("twine check dist/*")
    
    # Git operations
    run_command("git add smart_commit/__init__.py")
    run_command(f"git commit -m 'Bump version to {new_version}'")
    run_command(f"git tag v{new_version}")
    
    print(f"Release {new_version} ready!")
    print("To publish:")
    print("1. git push origin main")
    print("2. git push origin --tags")
    print("3. twine upload dist/*")

if __name__ == "__main__":
    main()
