import os
import re

def main():
    # Get the directory where this script is located.
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Compile a regex pattern to find a hex code in the filename.
    hex_pattern = re.compile(r'0x([0-9A-Fa-f]+)')

    # Iterate over items in the current directory.
    for filename in os.listdir(current_dir):
        full_path = os.path.join(current_dir, filename)

        # Only process files (skip directories and subfolders)
        if os.path.isfile(full_path):
            match = hex_pattern.search(filename)
            if match:
                # Extract the hexadecimal part (without the "0x" prefix).
                hex_digits = match.group(1)
                try:
                    # Convert the extracted string to an integer.
                    number = int(hex_digits, 16)
                except ValueError:
                    # If conversion fails, skip this file.
                    continue

                # Format the number to be zero-padded to at least 4 digits in uppercase.
                formatted_hex = f"0x{number:04X}"

                # Retain the original file extension.
                _, ext = os.path.splitext(filename)
                new_filename = f"{formatted_hex}{ext}"

                # Only rename if the new filename is different.
                if new_filename != filename:
                    new_full_path = os.path.join(current_dir, new_filename)
                    try:
                        os.rename(full_path, new_full_path)
                        print(f"Renamed '{filename}' to '{new_filename}'")
                    except Exception as e:
                        print(f"Failed to rename '{filename}': {e}")

if __name__ == "__main__":
    main()
