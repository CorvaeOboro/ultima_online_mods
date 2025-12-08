"""
 FILE RENAMER - NUMBER TO HEX CONVERTER
 Converts numbered files to hexadecimal format with various renaming modes
 Merged functionality from 02_rename_num_to_hex.py and 02_rename_all_hex_suffix.py

STATUS:: wip updated from cli version
VERSION::20251207
"""
import os
import re
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk

#//=====================================================================

def debug_print(*args):
    """Utility function to print debug messages to the log."""
    message = " ".join(str(arg) for arg in args)
    log_text.insert(tk.END, f"[DEBUG] {message}\n")
    log_text.see(tk.END)
    log_text.update()

def status_print(message):
    """Print status message to both status label and log."""
    status_label.config(text=message)
    log_text.insert(tk.END, f"{message}\n")
    log_text.see(tk.END)
    log_text.update()

def number_to_hex(number_str):
    """Convert a number in string format to its hexadecimal representation."""
    return f"0x{int(number_str):X}"

def find_hex_suffix(name):
    """
    Identify a valid hexadecimal suffix at the end of the filename.
    - Accepts hex suffixes with or without an underscore, 1-4 hex digits.
    - Returns the base name and hex suffix if found.
    - Returns None if no valid hex suffix is found.
    """
    match = re.search(r"(.*)(_?0x([0-9A-Fa-f]{1,4}))$", name)
    if match:
        base_name = match.group(1)
        hex_suffix = match.group(3).upper()  # Only get the hex digits part
        return base_name, hex_suffix
    return None

def pad_hex_suffix(hex_part):
    """Pads a hexadecimal part to 4 digits."""
    padded_hex = f"{int(hex_part, 16):04X}"
    return padded_hex

def add_proper_hex_suffix(base_name, padded_hex):
    """
    Append a new, properly formatted hexadecimal suffix to the filename.
    Adds an underscore only if there isn't one already.
    """
    if base_name.endswith("_"):
        return f"{base_name}0x{padded_hex}"
    return f"{base_name}_0x{padded_hex}"

#//=====================================================================
#// RENAMING MODES
#//=====================================================================

def mode_simple_hex_only(folder_path, extension=".bmp"):
    """Mode 1: Simple conversion - 'Gump 1234' -> '0x04D2.bmp'"""
    files = os.listdir(folder_path)
    status_print(f"Found {len(files)} files in the folder.")
    renamed_count = 0

    for filename in files:
        match = re.search(r'\d+', filename)
        if match:
            number_str = match.group()
            hex_number = number_to_hex(number_str)
            new_filename = str(hex_number) + extension
            old_path = os.path.join(folder_path, filename)
            new_path = os.path.join(folder_path, new_filename)
            try:
                os.rename(old_path, new_path)
                debug_print(f"Renamed '{filename}' to '{new_filename}'")
                renamed_count += 1
            except Exception as e:
                debug_print(f"Error renaming '{filename}': {e}")
    
    status_print(f"Renaming completed. {renamed_count} files renamed.")

def mode_preserve_name_add_hex(folder_path):
    """Mode 2: Preserve name and add hex - 'Gump 1234.bmp' -> 'Gump_0x04D2.bmp'"""
    files = os.listdir(folder_path)
    status_print(f"Found {len(files)} files in the folder.")
    renamed_count = 0

    for filename in files:
        name, ext = os.path.splitext(filename)
        match = re.search(r'\d+', name)
        if match:
            number_str = match.group()
            hex_number = number_to_hex(number_str)
            # Replace the number with hex in the filename
            new_name = re.sub(r'\d+', hex_number, name, 1)
            new_filename = new_name + ext
            old_path = os.path.join(folder_path, filename)
            new_path = os.path.join(folder_path, new_filename)
            try:
                os.rename(old_path, new_path)
                debug_print(f"Renamed '{filename}' to '{new_filename}'")
                renamed_count += 1
            except Exception as e:
                debug_print(f"Error renaming '{filename}': {e}")
    
    status_print(f"Renaming completed. {renamed_count} files renamed.")

def mode_smart_hex_suffix(folder_path):
    """Mode 3: Smart hex suffix - pads existing hex or adds new hex suffix"""
    files = os.listdir(folder_path)
    status_print(f"Found {len(files)} files in the folder.")
    renamed_count = 0

    for filename in files:
        # Skip files that start with "00_" or contain "_00_"
        if filename.startswith("00_") or "_00_" in filename:
            continue
        
        name, ext = os.path.splitext(filename)
        
        # Check if a hexadecimal suffix exists at the end of the name
        hex_info = find_hex_suffix(name)
        if hex_info:
            base_name, hex_part = hex_info
            # Pad the hex suffix if it's not already 4 characters
            if len(hex_part) < 4:
                padded_hex = pad_hex_suffix(hex_part)
                new_name = f"{add_proper_hex_suffix(base_name, padded_hex)}{ext}"
                old_path = os.path.join(folder_path, filename)
                new_path = os.path.join(folder_path, new_name)
                try:
                    os.rename(old_path, new_path)
                    debug_print(f"Padded hex: '{filename}' -> '{new_name}'")
                    renamed_count += 1
                except Exception as e:
                    debug_print(f"Error renaming '{filename}': {e}")
        else:
            # If no hex suffix, look for the first number in the name and convert it to hex
            number_match = re.search(r'\d+', name)
            if number_match:
                number = int(number_match.group(0))
                padded_hex = pad_hex_suffix(f"{number:X}")
                new_name = f"{add_proper_hex_suffix(name, padded_hex)}{ext}"
                old_path = os.path.join(folder_path, filename)
                new_path = os.path.join(folder_path, new_name)
                try:
                    os.rename(old_path, new_path)
                    debug_print(f"Added hex suffix: '{filename}' -> '{new_name}'")
                    renamed_count += 1
                except Exception as e:
                    debug_print(f"Error renaming '{filename}': {e}")
    
    status_print(f"Smart renaming completed. {renamed_count} files renamed.")

def mode_recursive_smart_hex(root_dir):
    """Mode 4: Recursive smart hex - processes entire directory tree"""
    root_dir = os.path.abspath(root_dir)
    status_print(f"Processing files recursively in: {root_dir}")
    
    excluded_dirs = {"temp", "backup", "original", "removed", "remove", "ref", 
                     "Upscale", "docs", "Z_ZBackup", "Z_Tools", ".git", 
                     ".obsidian", "Z_InstallNotes"}
    renamed_count = 0

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Exclude specified directories
        dirnames[:] = [d for d in dirnames if d not in excluded_dirs]

        for filename in filenames:
            # Skip files that start with "00_" or contain "_00_"
            if filename.startswith("00_") or "_00_" in filename:
                continue
            
            name, ext = os.path.splitext(filename)
            new_name = None
            
            # Check if a hexadecimal suffix exists
            hex_info = find_hex_suffix(name)
            if hex_info:
                base_name, hex_part = hex_info
                if len(hex_part) < 4:
                    padded_hex = pad_hex_suffix(hex_part)
                    new_name = f"{add_proper_hex_suffix(base_name, padded_hex)}{ext}"
            else:
                # Look for the first number and convert to hex
                number_match = re.search(r'\d+', name)
                if number_match:
                    number = int(number_match.group(0))
                    padded_hex = pad_hex_suffix(f"{number:X}")
                    new_name = f"{add_proper_hex_suffix(name, padded_hex)}{ext}"
            
            if new_name and filename != new_name:
                old_path = os.path.join(dirpath, filename)
                new_path = os.path.join(dirpath, new_name)
                try:
                    os.rename(old_path, new_path)
                    debug_print(f"Renamed: {old_path} -> {new_name}")
                    renamed_count += 1
                except Exception as e:
                    debug_print(f"Error renaming '{filename}': {e}")
    
    status_print(f"Recursive renaming completed. {renamed_count} files renamed.")

#//=====================================================================
#// UI COMMAND FUNCTIONS
#//=====================================================================

def browse_folder():
    """Open a dialog to select a folder and set the folder path in the entry widget."""
    folder_path = filedialog.askdirectory()
    if folder_path:
        folder_path_entry.delete(0, tk.END)
        folder_path_entry.insert(0, folder_path)

def clear_log():
    """Clear the log text area."""
    log_text.delete(1.0, tk.END)

def execute_mode_1():
    """Execute Mode 1: Simple hex only."""
    folder_path = folder_path_entry.get()
    if os.path.isdir(folder_path):
        clear_log()
        mode_simple_hex_only(folder_path)
    else:
        status_print("Invalid folder path.")

def execute_mode_2():
    """Execute Mode 2: Preserve name and add hex."""
    folder_path = folder_path_entry.get()
    if os.path.isdir(folder_path):
        clear_log()
        mode_preserve_name_add_hex(folder_path)
    else:
        status_print("Invalid folder path.")

def execute_mode_3():
    """Execute Mode 3: Smart hex suffix."""
    folder_path = folder_path_entry.get()
    if os.path.isdir(folder_path):
        clear_log()
        mode_smart_hex_suffix(folder_path)
    else:
        status_print("Invalid folder path.")

def execute_mode_4():
    """Execute Mode 4: Recursive smart hex."""
    folder_path = folder_path_entry.get()
    if os.path.isdir(folder_path):
        clear_log()
        mode_recursive_smart_hex(folder_path)
    else:
        status_print("Invalid folder path.")

#//=====================================================================
#// EXAMPLE TASK BUTTONS
#//=====================================================================

def example_gump_export():
    """Example: Rename exported gump files 'Gump 1234.bmp' -> '0x04D2.bmp'"""
    folder_path_entry.delete(0, tk.END)
    folder_path_entry.insert(0, "D:/ULTIMA/MODS/ultima_online_mods/UI/exported_gumps")
    status_print("Example: Gump export renaming (Mode 1)")

def example_art_items():
    """Example: Rename art items 'Item 1234.png' -> 'Item_0x04D2.png'"""
    folder_path_entry.delete(0, tk.END)
    folder_path_entry.insert(0, "D:/ULTIMA/MODS/ultima_online_mods/ART/exported_items")
    status_print("Example: Art items renaming (Mode 2)")

def example_land_tiles():
    """Example: Smart rename land tiles with hex padding"""
    folder_path_entry.delete(0, tk.END)
    folder_path_entry.insert(0, "D:/ULTIMA/MODS/ultima_online_mods/ENV/exported_land")
    status_print("Example: Land tiles smart renaming (Mode 3)")

def example_texture_files():
    """Example: Rename texture files 'texture_0x1.bmp' -> 'texture_0x0001.bmp'"""
    folder_path_entry.delete(0, tk.END)
    folder_path_entry.insert(0, "D:/ULTIMA/MODS/ultima_online_mods/ENV/textures")
    status_print("Example: Texture files hex padding (Mode 3)")

def example_creature_art():
    """Example: Rename creature art files"""
    folder_path_entry.delete(0, tk.END)
    folder_path_entry.insert(0, "D:/ULTIMA/MODS/ultima_online_mods/ART/ART_Creature")
    status_print("Example: Creature art renaming (Mode 3)")

def example_recursive_all():
    """Example: Recursively rename all files in project"""
    folder_path_entry.delete(0, tk.END)
    folder_path_entry.insert(0, "D:/ULTIMA/MODS/ultima_online_mods")
    status_print("Example: Recursive project-wide renaming (Mode 4)")

def example_ui_elements():
    """Example: Rename UI elements"""
    folder_path_entry.delete(0, tk.END)
    folder_path_entry.insert(0, "D:/ULTIMA/MODS/ultima_online_mods/UI/UI_ArchStone")
    status_print("Example: UI elements renaming (Mode 3)")

def example_book_art():
    """Example: Rename book art files"""
    folder_path_entry.delete(0, tk.END)
    folder_path_entry.insert(0, "D:/ULTIMA/MODS/ultima_online_mods/ART/ART_Book")
    status_print("Example: Book art renaming (Mode 3)")

#//=====================================================================
#// UI SETUP
#//=====================================================================

root = tk.Tk()
root.title(" File Renamer - Number to Hex Converter")
root.geometry("900x700")

# Main frame
main_frame = tk.Frame(root, padx=10, pady=10)
main_frame.pack(fill=tk.BOTH, expand=True)

# Folder selection section
folder_frame = tk.LabelFrame(main_frame, text="Folder Selection", padx=10, pady=10)
folder_frame.pack(fill=tk.X, pady=(0, 10))

folder_path_label = tk.Label(folder_frame, text="Folder Path:")
folder_path_label.grid(row=0, column=0, sticky=tk.W, pady=5)

folder_path_entry = tk.Entry(folder_frame, width=60)
folder_path_entry.grid(row=0, column=1, padx=5, pady=5)

browse_button = tk.Button(folder_frame, text="Browse", command=browse_folder, width=10)
browse_button.grid(row=0, column=2, padx=5, pady=5)

# Renaming modes section
modes_frame = tk.LabelFrame(main_frame, text="Renaming Modes", padx=10, pady=10)
modes_frame.pack(fill=tk.X, pady=(0, 10))

mode1_btn = tk.Button(modes_frame, text="Mode 1: Simple Hex Only\n(Gump 1234 → 0x04D2.bmp)", 
                      command=execute_mode_1, width=30, height=2, bg="#4a90e2", fg="white")
mode1_btn.grid(row=0, column=0, padx=5, pady=5)

mode2_btn = tk.Button(modes_frame, text="Mode 2: Preserve Name + Hex\n(Gump 1234 → Gump_0x04D2)", 
                      command=execute_mode_2, width=30, height=2, bg="#50c878", fg="white")
mode2_btn.grid(row=0, column=1, padx=5, pady=5)

mode3_btn = tk.Button(modes_frame, text="Mode 3: Smart Hex Suffix\n(Pad or Add Hex)", 
                      command=execute_mode_3, width=30, height=2, bg="#f5a623", fg="white")
mode3_btn.grid(row=1, column=0, padx=5, pady=5)

mode4_btn = tk.Button(modes_frame, text="Mode 4: Recursive Smart Hex\n(Entire Directory Tree)", 
                      command=execute_mode_4, width=30, height=2, bg="#e94b3c", fg="white")
mode4_btn.grid(row=1, column=1, padx=5, pady=5)

# Example tasks section
examples_frame = tk.LabelFrame(main_frame, text="Example Tasks (Click to Load Path)", padx=10, pady=10)
examples_frame.pack(fill=tk.X, pady=(0, 10))

example1_btn = tk.Button(examples_frame, text="Gump Export", command=example_gump_export, width=15)
example1_btn.grid(row=0, column=0, padx=3, pady=3)

example2_btn = tk.Button(examples_frame, text="Art Items", command=example_art_items, width=15)
example2_btn.grid(row=0, column=1, padx=3, pady=3)

example3_btn = tk.Button(examples_frame, text="Land Tiles", command=example_land_tiles, width=15)
example3_btn.grid(row=0, column=2, padx=3, pady=3)

example4_btn = tk.Button(examples_frame, text="Texture Files", command=example_texture_files, width=15)
example4_btn.grid(row=0, column=3, padx=3, pady=3)

example5_btn = tk.Button(examples_frame, text="Creature Art", command=example_creature_art, width=15)
example5_btn.grid(row=1, column=0, padx=3, pady=3)

example6_btn = tk.Button(examples_frame, text="UI Elements", command=example_ui_elements, width=15)
example6_btn.grid(row=1, column=1, padx=3, pady=3)

example7_btn = tk.Button(examples_frame, text="Book Art", command=example_book_art, width=15)
example7_btn.grid(row=1, column=2, padx=3, pady=3)

example8_btn = tk.Button(examples_frame, text="Recursive All", command=example_recursive_all, width=15, bg="#ff6b6b", fg="white")
example8_btn.grid(row=1, column=3, padx=3, pady=3)

# Log section
log_frame = tk.LabelFrame(main_frame, text="Activity Log", padx=10, pady=10)
log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

log_text = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD)
log_text.pack(fill=tk.BOTH, expand=True)

clear_log_btn = tk.Button(log_frame, text="Clear Log", command=clear_log, width=15)
clear_log_btn.pack(pady=(5, 0))

# Status section
status_frame = tk.Frame(main_frame)
status_frame.pack(fill=tk.X)

status_label = tk.Label(status_frame, text="Ready. Select a folder and choose a renaming mode.", 
                        relief=tk.SUNKEN, anchor=tk.W)
status_label.pack(fill=tk.X)

# Initial log message
log_text.insert(tk.END, "=" * 80 + "\n")
log_text.insert(tk.END, " FILE RENAMER - Number to Hex Converter\n")
log_text.insert(tk.END, "=" * 80 + "\n\n")
log_text.insert(tk.END, "Mode 1: Simple Hex Only - Converts 'Gump 1234.bmp' to '0x04D2.bmp'\n")
log_text.insert(tk.END, "Mode 2: Preserve Name + Hex - Converts 'Gump 1234.bmp' to 'Gump_0x04D2.bmp'\n")
log_text.insert(tk.END, "Mode 3: Smart Hex Suffix - Pads existing hex or adds new hex suffix\n")
log_text.insert(tk.END, "Mode 4: Recursive Smart Hex - Processes entire directory tree\n\n")
log_text.insert(tk.END, "Click an example task button to load a preset path, or browse for your own folder.\n")
log_text.insert(tk.END, "=" * 80 + "\n\n")

root.mainloop()
