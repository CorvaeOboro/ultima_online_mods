import os
import re

def debug_print(*args):
    """Utility function to print debug messages."""
    print("[DEBUG]", *args)

def find_hex_suffix(name):
    """
    Identify a valid hexadecimal suffix at the end of the filename.
    - Accepts hex suffixes with or without an underscore, 1-4 hex digits.
    - Returns the base name and hex suffix if found.
    - Returns None if no valid hex suffix is found.
    """
    # Match hexadecimal suffixes with 1 to 4 hex digits, with or without an underscore
    match = re.search(r"(.*)(_?0x([0-9A-Fa-f]{1,4}))$", name)
    if match:
        base_name = match.group(1)
        hex_suffix = match.group(3).upper()  # Only get the hex digits part
        debug_print(f"Found hex suffix in '{name}': base_name='{base_name}', hex_suffix='{hex_suffix}'")
        return base_name, hex_suffix
    else:
        debug_print(f"No valid hex suffix found in '{name}'")
    return None

def pad_hex_suffix(hex_part):
    """
    Pads a hexadecimal part to 4 digits.
    """
    padded_hex = f"{int(hex_part, 16):04X}"
    debug_print(f"Padded hex '{hex_part}' to '{padded_hex}'")
    return padded_hex

def add_proper_hex_suffix(base_name, padded_hex):
    """
    Append a new, properly formatted hexadecimal suffix to the filename.
    Adds an underscore only if there isn’t one already.
    """
    if base_name.endswith("_"):
        return f"{base_name}0x{padded_hex}"
    return f"{base_name}_0x{padded_hex}"

def process_filename(filename):
    """
    Process a filename to check and correct its hexadecimal suffix as needed.
    Returns the new filename if changes are made, otherwise returns None.
    """
    name, ext = os.path.splitext(filename)
    debug_print(f"Processing file: '{filename}'")

    # First, check if a hexadecimal suffix exists at the end of the name
    hex_info = find_hex_suffix(name)
    if hex_info:
        base_name, hex_part = hex_info

        # Pad the hex suffix if it's not already 4 characters
        if len(hex_part) < 4:
            padded_hex = pad_hex_suffix(hex_part)
            new_name = f"{add_proper_hex_suffix(base_name, padded_hex)}{ext}"
            debug_print(f"Hex found and padded: '{filename}' -> '{new_name}'")
            return new_name
        else:
            # If hex suffix is already valid, no changes needed
            debug_print(f"Valid hex found; no changes needed: '{filename}'")
            return None

    # If no hex suffix, look for the first number in the name and convert it to hex
    number_match = re.search(r'\d+', name)
    if number_match:
        number = int(number_match.group(0))
        padded_hex = pad_hex_suffix(f"{number:X}")
        new_name = f"{add_proper_hex_suffix(name, padded_hex)}{ext}"
        debug_print(f"No hex found, adding new hex suffix: '{filename}' -> '{new_name}'")
        return new_name

    # If no number or hex suffix is found, do not add a suffix
    debug_print(f"No hex or numbers found; no changes needed: '{filename}'")
    return None

def rename_files(root_dir="../"):
    # Convert the relative path to an absolute path
    root_dir = os.path.abspath(root_dir)
    print(f"Processing files in: {root_dir}")
    
    excluded_dirs = {"temp", "backup", "original", "removed", "remove", "ref", 
                     "Upscale", "docs", "Z_ZBackup", "Z_Tools", ".git", 
                     ".obsidian", "Z_InstallNotes"}

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Exclude specified directories
        dirnames[:] = [d for d in dirnames if d not in excluded_dirs]

        for filename in filenames:
            # Skip files that start with "00_" or contain "_00_"
            if filename.startswith("00_") or "_00_" in filename:
                continue
            
            # Process the filename to determine if it needs renaming
            new_name = process_filename(filename)
            if new_name and filename != new_name:
                old_path = os.path.join(dirpath, filename)
                new_path = os.path.join(dirpath, new_name)
                print(f"Renaming {old_path} to {new_path}")
                os.rename(old_path, new_path)

# Example usage:
rename_files()
