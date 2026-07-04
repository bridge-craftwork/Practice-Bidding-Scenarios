"""
Script to update GitHub Import URLs from blob to raw format
in all PBS scenario files.
"""

import os
import sys
from pathlib import Path

# URL pattern to find and replace
OLD_URL = "https://github.com/bridge-craftwork/Practice-Bidding-Scenarios/blob/main/"
NEW_URL = "https://raw.githubusercontent.com/bridge-craftwork/Practice-Bidding-Scenarios/main/"

def preview_changes(directory):
    """
    Scan files and show what would be changed without making changes.
    Returns list of files that would be modified.
    """
    files_to_modify = []
    
    for filepath in Path(directory).rglob('*'):
        if filepath.is_file():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if OLD_URL in content:
                    count = content.count(OLD_URL)
                    files_to_modify.append((filepath, count))
                    print(f"Found {count} occurrence(s) in: {filepath}")
            except Exception as e:
                print(f"Warning: Could not read {filepath}: {e}")
    
    return files_to_modify

def update_files(files_to_modify):
    """
    Actually perform the URL replacements in the specified files.
    """
    updated_count = 0
    
    for filepath, _ in files_to_modify:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content.replace(OLD_URL, NEW_URL)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            updated_count += 1
            print(f"Updated: {filepath}")
        except Exception as e:
            print(f"Error updating {filepath}: {e}")
    
    return updated_count

def main():
    # Default to PBS directory, or use command line argument
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = "./PBS"
    
    if not os.path.exists(directory):
        print(f"Error: Directory '{directory}' not found.")
        print("Usage: python update_imports.py [directory]")
        sys.exit(1)
    
    print("=" * 60)
    print("GitHub Import URL Updater")
    print("=" * 60)
    print(f"Scanning directory: {directory}")
    print(f"Old URL: {OLD_URL}")
    print(f"New URL: {NEW_URL}")
    print("=" * 60)
    print()
    
    # Preview changes
    print("PREVIEW - Files that will be modified:")
    print("-" * 60)
    files_to_modify = preview_changes(directory)
    print("-" * 60)
    print()
    
    if not files_to_modify:
        print("No files found with the old URL pattern.")
        return
    
    total_occurrences = sum(count for _, count in files_to_modify)
    print(f"Total: {len(files_to_modify)} files, {total_occurrences} occurrences")
    print()
    
    # Confirm before proceeding
    response = input("Proceed with updates? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        print()
        print("Updating files...")
        print("-" * 60)
        updated = update_files(files_to_modify)
        print("-" * 60)
        print()
        print(f"✓ Successfully updated {updated} files!")
    else:
        print("Update cancelled.")

if __name__ == "__main__":
    main()