#// PSD TO PNG BATCH 
#// for each PSD name with a hexidecimal suffix , save a PNG copy named by HEX for GumpOverrides
import os
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image
from psd_tools import PSDImage
import warnings
import re

# Global variables for default folder paths and groups
DEFAULT_PATHS_AND_GROUPS = {
    "Buffs": ".././UI/UI_Buffs",
    "Dark Scrolls": ".././UI/UI_DarkScrolls",
    "Paperdoll": ".././UI/UI_EquipStone",
    "Magic Spells": ".././UI/UI_MagicSpells",
    "Magic Effect": ".././UI/UI_MagicSpells/SpellEffects_Color",
    "Magic Summon": ".././UI/UI_MagicSpells/SpellEffects_Special",
    "Backpack": ".././UI/UI_MISC",
    "Chivalry": ".././UI/UI_SpellsChivalry",
    "Necromancy": ".././UI/UI_SpellsNecromancy",
    "Codex": ".././UI/UI_Profession"
}

DEFAULT_OUTPUT_PATH = "./GumpOverrides/"

#//==================================================================================================
#// EXPORT
def export_psd_to_PNG(folder_path, target_folder, override_existing_files):
    # Suppress specific warnings from psd_tools
    warnings.filterwarnings("ignore", category=UserWarning, message="Unknown tagged block:.*")
    warnings.filterwarnings("ignore", category=UserWarning, message="Unknown key:.*")

    # Regular expression to match hexadecimal sequences
    hex_pattern = re.compile(r'(0x[0-9A-Fa-f]+)\.psd$')

    # Ensure target folder exists
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    # Iterate over all files in the folder path
    for filename in os.listdir(folder_path):
        match = hex_pattern.search(filename)
        if match:
            # Construct the full path to the PSD file
            psd_path = os.path.join(folder_path, filename)

            # Generate the new PNG filename based on the regex match
            PNG_filename = match.group(1) + ".png"

            # Determine the output path for the PNG file
            PNG_path = os.path.join(target_folder, PNG_filename)

            # Check if the PNG file already exists and the override option is not selected
            if os.path.exists(PNG_path) and not override_existing_files:
                print(f"Skipping existing file: {PNG_path}")
                continue

            # Open the PSD file and save it as a PNG file
            try:
                psd = PSDImage.open(psd_path)
                merged_image = psd.composite()
                merged_image.save(PNG_path, format='PNG')
                print(f"Exported {psd_path} to {PNG_path}")
            except Exception as e:
                print(f"Error processing {psd_path}: {e}")

    # Restore the default warning filter
    warnings.filterwarnings("default", category=UserWarning, message="Unknown tagged block:.*")
    warnings.filterwarnings("default", category=UserWarning, message="Unknown key:.*")

    print(f"Exported all PSD files from {folder_path} to PNG format.")

#//==================================================================================================
#//   UI
#//==================================================================================================
class PSDtoPNGConverter:
    def __init__(self, master):
        self.master = master
        self.master.title("PSD to PNG Converter - Source Art to GumpOverrides")
        self.master.configure(bg='#2e2e2e')

        self.paths = []
        self.group_names = []
        self.export_states = []

        # Default target folder for exporting PNG files
        self.target_folder = DEFAULT_OUTPUT_PATH

        self.setup_ui()
        self.load_default_paths()

    def setup_ui(self):
        self.frame = ttk.Frame(self.master, style='TFrame')
        self.frame.pack(padx=10, pady=10)

        # Button to export all groups
        self.export_all_button = ttk.Button(self.frame, text="Export All", command=self.export_all_groups, style='TButton')
        self.export_all_button.grid(row=0, column=0, pady=(0, 10))

        # Checkbox to export all PNG files to the target folder
        self.export_all_to_same_folder = tk.BooleanVar(value=True)
        self.export_all_checkbox = ttk.Checkbutton(self.frame, text="Export all to target folder", variable=self.export_all_to_same_folder, style='TCheckbutton')
        self.export_all_checkbox.grid(row=1, column=0, pady=(0, 10))

        # Checkbox to override existing PNG files
        self.override_existing_files = tk.BooleanVar(value=True)
        self.override_checkbox = ttk.Checkbutton(self.frame, text="Override existing PNG files", variable=self.override_existing_files, style='TCheckbutton')
        self.override_checkbox.grid(row=2, column=0, pady=(0, 10))

        # Entry for specifying the target folder path
        self.target_folder_entry = ttk.Entry(self.frame, width=30, style='TEntry')
        self.target_folder_entry.insert(0, self.target_folder)
        self.target_folder_entry.grid(row=3, column=0, pady=(0, 10))

        # Button to add a new folder path
        self.add_path_button = ttk.Button(self.frame, text="Add Path", command=self.add_path, style='TButton')
        self.add_path_button.grid(row=4, column=0, pady=(0, 10))

        # Frame to display added folder paths and export buttons
        self.paths_frame = ttk.Frame(self.frame, style='TFrame')
        self.paths_frame.grid(row=5, column=0, columnspan=1)

    def load_default_paths(self):
        # Load the default paths and groups
        for group_name, folder_path in DEFAULT_PATHS_AND_GROUPS.items():
            self.paths.append(folder_path)
            self.group_names.append(group_name)
            self.export_states.append(tk.BooleanVar(value=True))
        self.update_paths_ui()

    def add_path(self):
        # Open a dialog to select a folder
        folder_path = filedialog.askdirectory()
        if folder_path:
            # Extract the group name from the folder path
            group_name = os.path.basename(folder_path)
            self.paths.append(folder_path)
            self.group_names.append(group_name)
            self.export_states.append(tk.BooleanVar(value=True))
            self.update_paths_ui()

    def update_paths_ui(self):
        # Clear existing widgets in the paths frame
        for widget in self.paths_frame.winfo_children():
            widget.destroy()

        # Create labels, checkboxes, and export buttons for each added path
        for i, (path, group_name, state) in enumerate(zip(self.paths, self.group_names, self.export_states)):
            export_check = ttk.Checkbutton(self.paths_frame, variable=state, style='TCheckbutton')
            export_check.grid(row=i, column=0, padx=(0, 10))

            group_label = ttk.Label(self.paths_frame, text=group_name, style='TLabel')
            group_label.grid(row=i, column=1, padx=(0, 10))

            path_label = ttk.Label(self.paths_frame, text=path, style='TLabel')
            path_label.grid(row=i, column=2, padx=(0, 10))

            export_button = ttk.Button(self.paths_frame, text="Export", command=lambda p=path, s=state: self.export_group(p, s), style='TButton')
            export_button.grid(row=i, column=3, padx=(0, 10))

    def export_group(self, folder_path, state):
        if state.get():
            export_psd_to_PNG(folder_path, self.target_folder if self.export_all_to_same_folder.get() else folder_path, self.override_existing_files.get())

    def export_all_groups(self):
        # Export all groups
        for path, state in zip(self.paths, self.export_states):
            self.export_group(path, state)

if __name__ == "__main__":
    root = tk.Tk()
    # Set dark mode styles
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('TFrame', background='#2e2e2e')
    style.configure('TButton', background='#3c3c3c', foreground='white', borderwidth=1)
    style.configure('TCheckbutton', background='#2e2e2e', foreground='white')
    style.configure('TLabel', background='#2e2e2e', foreground='white')
    style.configure('TEntry', fieldbackground='#3c3c3c', foreground='white')
    app = PSDtoPNGConverter(root)
    root.mainloop()
