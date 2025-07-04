"""
DEV ULTIMA PROJECT DATA GET
maps project structure and counts by filetypes 
creates a csv formatted for specific columns "category" , "group" , "count" 
count is the number of .bmp files in the groups specific folder ( not recursive )
CATEGORY =  ART , ENV , UI
GROUP = ART_Keys, ART_Fish , etc.
"""

import os
import csv

# Set these paths as needed
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CATEGORIES = ['ART', 'ENV', 'UI']

# Output CSV path
OUTPUT_CSV = os.path.join(PROJECT_ROOT, 'project_filetype_counts.csv')


def get_group_folders(category_dir):
    """Return list of (group_folder_name, full_path) for immediate subdirectories."""
    group_folders = []
    print(f"[DEBUG] Scanning for group folders in: {category_dir}")
    if not os.path.isdir(category_dir):
        print(f"[DEBUG] Directory does not exist: {category_dir}")
        return group_folders
    for entry in os.listdir(category_dir):
        full_path = os.path.join(category_dir, entry)
        if os.path.isdir(full_path):
            print(f"[DEBUG] Found group folder: {entry}")
            group_folders.append((entry, full_path))
    print(f"[DEBUG] Total group folders found in {category_dir}: {len(group_folders)}")
    return group_folders


import datetime

def count_bmp_files_and_newest(group_folder):
    """Count .bmp files directly in group_folder (not recursive) and get newest mod date."""
    count = 0
    newest_time = None
    newest_file = None
    print(f"[DEBUG] Counting .bmp files in group folder: {group_folder}")
    for entry in os.listdir(group_folder):
        if entry.lower().endswith('.bmp') and os.path.isfile(os.path.join(group_folder, entry)):
            count += 1
            mtime = os.path.getmtime(os.path.join(group_folder, entry))
            if newest_time is None or mtime > newest_time:
                newest_time = mtime
                newest_file = entry
            print(f"[DEBUG]   Found .bmp: {entry}, mtime: {mtime}")
    if newest_time:
        newest_date = datetime.datetime.fromtimestamp(newest_time).strftime('%Y%m%d')
        print(f"[DEBUG] Newest .bmp in {group_folder}: {newest_file} ({newest_date})")
    else:
        newest_date = ''
    print(f"[DEBUG] Total .bmp files in {group_folder}: {count}")
    return count, newest_date


def main():
    print("[DEBUG] Starting project structure scan...")
    print(f"[DEBUG] Project root: {PROJECT_ROOT}")
    rows = []
    order = 1
    for category in CATEGORIES:
        category_dir = os.path.join(PROJECT_ROOT, category)
        print(f"[DEBUG] Processing category: {category}")
        group_folders = get_group_folders(category_dir)
        for group_name, group_path in group_folders:
            print(f"[DEBUG] Processing group: {group_name}")
            bmp_count, newest_date = count_bmp_files_and_newest(group_path)
            rows.append({'order': order, 'category': category, 'group': group_name, 'count': bmp_count, 'newest_bmp_date': newest_date})
            print(f"[DEBUG] Group: {group_name} | .bmp count: {bmp_count} | newest_bmp_date: {newest_date} | order: {order}")
            order += 1

    # Write to CSV
    print(f"[DEBUG] Writing results to CSV: {OUTPUT_CSV}")
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['order', 'category', 'group', 'count', 'newest_bmp_date'])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"[DEBUG] Scan complete. Results written to {OUTPUT_CSV}")

if __name__ == '__main__':
    main()