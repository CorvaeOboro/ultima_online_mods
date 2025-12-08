"""
CONVERT older MulPatcher(varan) .txt files to MassImport .xml for UOFiddler MassImport plugin 
this was useful when updating the project , now this is all handled by 00_mod_selector which generates both the .txt and .xml 

# CLI version  to convert a mulpatcher txt file to the UOFiddler MassImport xml format.
# Usage = python convert_data.py -i input.txt -o output.xml -p "D:\\ULTIMA\\MODS\\ultima_online_mods\\"

# python 03_massimport_xml_convert.py -c "item" -i "D:\ULTIMA\MODS\ultima_online_mods\00_ART_ALL_ART_S.txt" -o "D:\ULTIMA\MODS\ultima_online_mods\00_ART_ALL_ART_S.xml" -p "D:\\ULTIMA\\MODS\\ultima_online_mods\\" 
# python 03_massimport_xml_convert.py -c "gump" -i "D:\ULTIMA\MODS\ultima_online_mods\00_UI_ALL_GUMP.txt" -o "D:\ULTIMA\MODS\ultima_online_mods\00_UI_ALL_GUMP.xml" -p "D:\\ULTIMA\\MODS\\ultima_online_mods\\" 
# python 03_massimport_xml_convert.py -c "landtile" -i "D:\ULTIMA\MODS\ultima_online_mods\00_ENV_ALL_ART_M.txt" -o "D:\ULTIMA\MODS\ultima_online_mods\00_ENV_ALL_ART_M.xml" -p "D:\\ULTIMA\\MODS\\ultima_online_mods\\" 
# python 03_massimport_xml_convert.py -c "texture" -i "D:\ULTIMA\MODS\ultima_online_mods\00_ENV_ALL_TEX.txt" -o "D:\ULTIMA\MODS\ultima_online_mods\00_ENV_ALL_TEX.xml" -p "D:\\ULTIMA\\MODS\\ultima_online_mods\\" 
# python 03_massimport_xml_convert.py -c "item" -i "D:\ULTIMA\MODS\ultima_online_mods\00_ENV_ALL_ART_S.txt" -o "D:\ULTIMA\MODS\ultima_online_mods\00_ENV_ALL_ART_S.xml" -p "D:\\ULTIMA\\MODS\\ultima_online_mods\\"

TOOLSGROUP::DEV
SORTGROUP::9
SORTPRIORITY::99
STATUS::wip
VERSION::20251207
"""

import argparse
import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Convert data from one text file to another with specified formatting.')
    parser.add_argument('-i', '--input', required=True, help='Path to the input text file.')
    parser.add_argument('-o', '--output', required=True, help='Path to the output XML file.')
    parser.add_argument('-p', '--prefix', required=True, help='Prefix to add to the file paths.')
    parser.add_argument('-c', '--category', required=True, help='Category for the XML tags (e.g., item, gump, landtile, texture).')
    return parser.parse_args()

def process_line(line, prefix, category, line_number):
    """
    Process a single line of the input file.

    Parameters:
        line (str): The line to process.
        prefix (str): The prefix to add to the file paths.
        category (str): The category for the XML tags.
        line_number (int): The current line number in the input file.

    Returns:
        str or None: The formatted line to write to the output file, or None if the line is invalid.
    """
    line = line.strip()
    if not line:
        return None  # Skip empty lines

    # Split the line into item ID and file path
    try:
        item_id_str, file_path = line.split(None, 1)  # Split on the first whitespace
    except ValueError:
        print(f"Warning: Skipping invalid line {line_number}: '{line}'", file=sys.stderr)
        return None  # Skip lines that don't have both item ID and file path

    # Convert item ID from hexadecimal to decimal
    try:
        item_id = int(item_id_str, 16)
    except ValueError:
        print(f"Warning: Invalid item ID on line {line_number}: '{item_id_str}'", file=sys.stderr)
        return None  # Skip invalid item IDs

    # Ensure the prefix ends with a backslash or slash
    if not prefix.endswith(('/', '\\')):
        prefix += '\\'

    # Build the new file path by adding the prefix
    new_file_path = prefix + file_path

    # Return the formatted line using the category
    return f'  <{category} index="{item_id}" file="{new_file_path}" remove="False" />\n'

def convert_data(input_file, output_file, prefix, category):
    """
    Convert data from the input file and write to the output file.

    Parameters:
        input_file (str): Path to the input text file.
        output_file (str): Path to the output XML file.
        prefix (str): Prefix to add to the file paths.
        category (str): Category for the XML tags.
    """
    try:
        with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
            outfile.write("<MassImport>")
            outfile.write("\n")
            for line_number, line in enumerate(infile, 1):
                result = process_line(line, prefix, category, line_number)
                if result:
                    outfile.write(result)
            outfile.write("\n")
            outfile.write("</MassImport>")
        print(f"Data has been successfully converted and written to '{output_file}'.")
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found. Please check the file path.", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)

#//=============================================================================================
class MassImportConverterUI:
    """Dark themed tkinter UI for MassImport XML conversion."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("MassImport XML Converter")
        self.root.configure(bg='#1a1a1a')
        
        # Color scheme
        self.bg_dark = '#1a1a1a'
        self.bg_darker = '#0f0f0f'
        self.bg_lighter = '#2a2a2a'
        self.fg_color = '#e0e0e0'
        self.button_green = '#4a6a4a'
        self.button_blue = '#4a5a6a'
        self.button_purple = '#5a4a6a'
        
        # Preset configurations
        self.presets = [
            {
                'name': 'ART_S (Items)',
                'category': 'item',
                'input': r'D:\ULTIMA\MODS\ultima_online_mods\00_ART_ALL_ART_S.txt',
                'output': r'D:\ULTIMA\MODS\ultima_online_mods\00_ART_ALL_ART_S.xml',
                'prefix': r'D:\\ULTIMA\\MODS\\ultima_online_mods\\',
                'color': self.button_green
            },
            {
                'name': 'GUMP (UI)',
                'category': 'gump',
                'input': r'D:\ULTIMA\MODS\ultima_online_mods\00_UI_ALL_GUMP.txt',
                'output': r'D:\ULTIMA\MODS\ultima_online_mods\00_UI_ALL_GUMP.xml',
                'prefix': r'D:\\ULTIMA\\MODS\\ultima_online_mods\\',
                'color': self.button_blue
            },
            {
                'name': 'ART_M (Land)',
                'category': 'landtile',
                'input': r'D:\ULTIMA\MODS\ultima_online_mods\00_ENV_ALL_ART_M.txt',
                'output': r'D:\ULTIMA\MODS\ultima_online_mods\00_ENV_ALL_ART_M.xml',
                'prefix': r'D:\\ULTIMA\\MODS\\ultima_online_mods\\',
                'color': self.button_purple
            },
            {
                'name': 'TEX (Texture)',
                'category': 'texture',
                'input': r'D:\ULTIMA\MODS\ultima_online_mods\00_ENV_ALL_TEX.txt',
                'output': r'D:\ULTIMA\MODS\ultima_online_mods\00_ENV_ALL_TEX.xml',
                'prefix': r'D:\\ULTIMA\\MODS\\ultima_online_mods\\',
                'color': self.button_green
            },
            {
                'name': 'ENV ART_S (Items)',
                'category': 'item',
                'input': r'D:\ULTIMA\MODS\ultima_online_mods\00_ENV_ALL_ART_S.txt',
                'output': r'D:\ULTIMA\MODS\ultima_online_mods\00_ENV_ALL_ART_S.xml',
                'prefix': r'D:\\ULTIMA\\MODS\\ultima_online_mods\\',
                'color': self.button_blue
            }
        ]
        
        self.create_widgets()
        
    def create_widgets(self):
        """Create all UI widgets."""
        # Title and description
        title_frame = tk.Frame(self.root, bg=self.bg_dark)
        title_frame.pack(pady=10, padx=20, fill='x')
        
        title_label = tk.Label(
            title_frame,
            text="MassImport XML Converter",
            font=('Arial', 16, 'bold'),
            bg=self.bg_dark,
            fg=self.fg_color
        )
        title_label.pack()
        
        desc_label = tk.Label(
            title_frame,
            text="Converts MulPatcher TXT files to UOFiddler MassImport XML format\nfor batch importing game assets (items, gumps, landtiles, textures)",
            font=('Arial', 9),
            bg=self.bg_dark,
            fg='#a0a0a0',
            justify='center'
        )
        desc_label.pack(pady=(5, 0))
        
        # Separator
        separator1 = tk.Frame(self.root, height=2, bg=self.bg_lighter)
        separator1.pack(fill='x', pady=10)
        
        # Preset buttons section
        preset_frame = tk.Frame(self.root, bg=self.bg_dark)
        preset_frame.pack(pady=10, padx=20, fill='both', expand=True)
        
        preset_label = tk.Label(
            preset_frame,
            text="Quick Convert Presets:",
            font=('Arial', 11, 'bold'),
            bg=self.bg_dark,
            fg=self.fg_color
        )
        preset_label.pack(anchor='w', pady=(0, 10))
        
        # Create preset buttons
        for preset in self.presets:
            btn = tk.Button(
                preset_frame,
                text=preset['name'],
                font=('Arial', 10),
                bg=preset['color'],
                fg=self.fg_color,
                activebackground=self.bg_lighter,
                activeforeground=self.fg_color,
                relief='flat',
                cursor='hand2',
                command=lambda p=preset: self.run_preset(p)
            )
            btn.pack(fill='x', pady=3, ipady=8)
        
        # Separator
        separator2 = tk.Frame(self.root, height=2, bg=self.bg_lighter)
        separator2.pack(fill='x', pady=15)
        
        # Custom conversion section
        custom_frame = tk.Frame(self.root, bg=self.bg_dark)
        custom_frame.pack(pady=10, padx=20, fill='both', expand=True)
        
        custom_label = tk.Label(
            custom_frame,
            text="Custom Conversion:",
            font=('Arial', 11, 'bold'),
            bg=self.bg_dark,
            fg=self.fg_color
        )
        custom_label.pack(anchor='w', pady=(0, 10))
        
        # Category dropdown
        cat_frame = tk.Frame(custom_frame, bg=self.bg_dark)
        cat_frame.pack(fill='x', pady=5)
        
        tk.Label(
            cat_frame,
            text="Category:",
            font=('Arial', 9),
            bg=self.bg_dark,
            fg=self.fg_color,
            width=12,
            anchor='w'
        ).pack(side='left')
        
        self.category_var = tk.StringVar(value='item')
        category_combo = ttk.Combobox(
            cat_frame,
            textvariable=self.category_var,
            values=['item', 'gump', 'landtile', 'texture'],
            state='readonly',
            font=('Arial', 9)
        )
        category_combo.pack(side='left', fill='x', expand=True)
        
        # Input file
        input_frame = tk.Frame(custom_frame, bg=self.bg_dark)
        input_frame.pack(fill='x', pady=5)
        
        tk.Label(
            input_frame,
            text="Input TXT:",
            font=('Arial', 9),
            bg=self.bg_dark,
            fg=self.fg_color,
            width=12,
            anchor='w'
        ).pack(side='left')
        
        self.input_var = tk.StringVar()
        input_entry = tk.Entry(
            input_frame,
            textvariable=self.input_var,
            font=('Arial', 9),
            bg=self.bg_lighter,
            fg=self.fg_color,
            insertbackground=self.fg_color
        )
        input_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        input_btn = tk.Button(
            input_frame,
            text="Browse",
            font=('Arial', 8),
            bg=self.bg_lighter,
            fg=self.fg_color,
            command=self.browse_input
        )
        input_btn.pack(side='left')
        
        # Output file
        output_frame = tk.Frame(custom_frame, bg=self.bg_dark)
        output_frame.pack(fill='x', pady=5)
        
        tk.Label(
            output_frame,
            text="Output XML:",
            font=('Arial', 9),
            bg=self.bg_dark,
            fg=self.fg_color,
            width=12,
            anchor='w'
        ).pack(side='left')
        
        self.output_var = tk.StringVar()
        output_entry = tk.Entry(
            output_frame,
            textvariable=self.output_var,
            font=('Arial', 9),
            bg=self.bg_lighter,
            fg=self.fg_color,
            insertbackground=self.fg_color
        )
        output_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        output_btn = tk.Button(
            output_frame,
            text="Browse",
            font=('Arial', 8),
            bg=self.bg_lighter,
            fg=self.fg_color,
            command=self.browse_output
        )
        output_btn.pack(side='left')
        
        # Prefix
        prefix_frame = tk.Frame(custom_frame, bg=self.bg_dark)
        prefix_frame.pack(fill='x', pady=5)
        
        tk.Label(
            prefix_frame,
            text="Path Prefix:",
            font=('Arial', 9),
            bg=self.bg_dark,
            fg=self.fg_color,
            width=12,
            anchor='w'
        ).pack(side='left')
        
        self.prefix_var = tk.StringVar(value=r'D:\\ULTIMA\\MODS\\ultima_online_mods\\')
        prefix_entry = tk.Entry(
            prefix_frame,
            textvariable=self.prefix_var,
            font=('Arial', 9),
            bg=self.bg_lighter,
            fg=self.fg_color,
            insertbackground=self.fg_color
        )
        prefix_entry.pack(side='left', fill='x', expand=True)
        
        # Convert button
        convert_btn = tk.Button(
            custom_frame,
            text="Convert Custom",
            font=('Arial', 10, 'bold'),
            bg=self.button_purple,
            fg=self.fg_color,
            activebackground=self.bg_lighter,
            activeforeground=self.fg_color,
            relief='flat',
            cursor='hand2',
            command=self.run_custom
        )
        convert_btn.pack(fill='x', pady=(15, 5), ipady=10)
        
        # Status label
        self.status_label = tk.Label(
            self.root,
            text="Ready",
            font=('Arial', 9),
            bg=self.bg_darker,
            fg='#808080',
            anchor='w',
            padx=10
        )
        self.status_label.pack(side='bottom', fill='x', ipady=5)
        
    def browse_input(self):
        """Browse for input file."""
        filename = filedialog.askopenfilename(
            title="Select Input TXT File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.input_var.set(filename)
            
    def browse_output(self):
        """Browse for output file."""
        filename = filedialog.asksaveasfilename(
            title="Select Output XML File",
            defaultextension=".xml",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if filename:
            self.output_var.set(filename)
            
    def run_preset(self, preset):
        """Run conversion with preset configuration."""
        self.status_label.config(text=f"Converting {preset['name']}...", fg='#ffaa00')
        self.root.update()
        
        try:
            convert_data(preset['input'], preset['output'], preset['prefix'], preset['category'])
            self.status_label.config(text=f"✓ {preset['name']} converted successfully!", fg='#4a8a4a')
            messagebox.showinfo("Success", f"{preset['name']} converted successfully!\n\nOutput: {preset['output']}")
        except Exception as e:
            self.status_label.config(text=f"✗ Error: {str(e)}", fg='#8a4a4a')
            messagebox.showerror("Error", f"Conversion failed:\n{str(e)}")
            
    def run_custom(self):
        """Run conversion with custom parameters."""
        input_file = self.input_var.get()
        output_file = self.output_var.get()
        prefix = self.prefix_var.get()
        category = self.category_var.get()
        
        if not input_file or not output_file:
            messagebox.showwarning("Missing Information", "Please specify both input and output files.")
            return
            
        self.status_label.config(text="Converting custom configuration...", fg='#ffaa00')
        self.root.update()
        
        try:
            convert_data(input_file, output_file, prefix, category)
            self.status_label.config(text="✓ Custom conversion completed successfully!", fg='#4a8a4a')
            messagebox.showinfo("Success", f"Conversion completed successfully!\n\nOutput: {output_file}")
        except Exception as e:
            self.status_label.config(text=f"✗ Error: {str(e)}", fg='#8a4a4a')
            messagebox.showerror("Error", f"Conversion failed:\n{str(e)}")

def launch_gui():
    """Launch the tkinter GUI."""
    root = tk.Tk()
    root.geometry("600x700")
    root.resizable(True, True)
    app = MassImportConverterUI(root)
    root.mainloop()

def main():
    # Check if CLI arguments were provided
    if len(sys.argv) > 1:
        # CLI mode
        args = parse_arguments()
        convert_data(args.input, args.output, args.prefix, args.category)
    else:
        # GUI mode
        launch_gui()

if __name__ == '__main__':
    main()
