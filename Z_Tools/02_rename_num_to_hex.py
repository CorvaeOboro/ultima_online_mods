#// NUMBER TO HEX FILE RENAMER 
#// exported art files might be named "Gump 1234" this program will rename all to corresponding HEX "0x7D0"
import os
import re
import tkinter as tk
from tkinter import filedialog

def number_to_hex(number_str):
    """Convert a number in string format to its hexadecimal representation."""
    return f"0x{int(number_str):X}"

def rename_files_in_folder_to_hex(folder_path):
    """Rename files in the given folder, converting numbers in filenames to hexadecimal."""
    files = os.listdir(folder_path)
    print(f"Found {len(files)} files in the folder.")

    for filename in files:
        # Extract the first number found in the filename
        match = re.search(r'\d+', filename)
        if match:
            number_str = match.group()
            hex_number = number_to_hex(number_str) 
            # Replace the filename with its hexadecimal representation
            #new_filename = re.sub(r'\d+', hex_number, filename, 1)
            new_filename = str(hex_number) + ".bmp"
            old_path = os.path.join(folder_path, filename)
            new_path = os.path.join(folder_path, new_filename)
            os.rename(old_path, new_path)
            print(f"Renamed '{filename}' to '{new_filename}'")

def browse_folder():
    """Open a dialog to select a folder and set the folder path in the entry widget."""
    folder_path = filedialog.askdirectory()
    if folder_path:
        folder_path_entry.delete(0, tk.END)
        folder_path_entry.insert(0, folder_path)

def start_renaming():
    """Start the renaming process using the folder path from the entry widget."""
    folder_path = folder_path_entry.get()
    if os.path.isdir(folder_path):
        rename_files_in_folder_to_hex(folder_path)
        status_label.config(text="Renaming completed successfully.")
    else:
        status_label.config(text="Invalid folder path.")

#//=====================================================================
#//  UI 
root = tk.Tk()
root.title("File Renamer - Numbered to HEXIDECIMAL ")

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

folder_path_label = tk.Label(frame, text="Folder Path:")
folder_path_label.grid(row=0, column=0, pady=(0, 5))

folder_path_entry = tk.Entry(frame, width=50)
folder_path_entry.grid(row=0, column=1, pady=(0, 5))

browse_button = tk.Button(frame, text="Browse", command=browse_folder)
browse_button.grid(row=0, column=2, padx=(5, 0), pady=(0, 5))

rename_button = tk.Button(frame, text="Rename Files", command=start_renaming)
rename_button.grid(row=1, column=1, pady=(5, 0))

status_label = tk.Label(frame, text="")
status_label.grid(row=2, column=1, pady=(5, 0))

root.mainloop()
