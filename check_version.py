"""
Simple script to check and display the current version
"""
import os
import re
import subprocess

def get_version_from_file():
    version_file_path = 'version.py'
    if os.path.exists(version_file_path):
        try:
            with open(version_file_path, 'r') as f:
                version_file = f.read()
            version_match = re.search(r"__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
            if version_match:
                return version_match.group(1)
        except Exception as e:
            print(f"Error reading version.py: {e}")
    return None

def get_version_from_git():
    try:
        # Get the latest Git tag (e.g., v2.0.0)
        version = subprocess.check_output(["git", "describe", "--tags"]).strip().decode("utf-8")
        # Ensure the tag is clean and remove 'v' prefix if present
        if version.startswith("v"):
            version = version[1:]
        # Validate version format (e.g., 2.0.0)
        if re.match(r"^\d+\.\d+\.\d+$", version):
            return version
    except Exception as e:
        print(f"Error getting version from git: {e}")
    return None

if __name__ == "__main__":
    print("Checking version sources:")
    
    # Check version.py
    file_version = get_version_from_file()
    if file_version:
        print(f"  - Version from version.py: {file_version}")
    else:
        print("  - No version found in version.py")
    
    # Check git tags
    git_version = get_version_from_git()
    if git_version:
        print(f"  - Version from git tags: {git_version}")
    else:
        print("  - No version found in git tags")
    
    # Show which version would be used
    if file_version:
        print(f"\nUsing version: {file_version} (from version.py)")
    elif git_version:
        print(f"\nUsing version: {git_version} (from git tags)")
    else:
        print("\nNo version found, would use default version: 1.7.0")
