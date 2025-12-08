"""
MAP EXTRACT FROM MUL 

# extract map mul landtiles position and land id which correspond to the land textures
# load a map like map0.mul , convert from uop in UOfiddler first to get mul 
# can define region to export the data to a csv that can be later read by a blender addon to place matching tiles 
# use search to find the locations of a known tile in order to find regions

TOOLSGROUP::MAP
SORTGROUP::6
SORTPRIORITY::61
STATUS::wip
VERSION::20251207
"""

import os
import struct
import logging
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import csv
import threading
import queue
import json

# Configure logging: DEBUG level for comprehensive info
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')

# Constants
BLOCK_SIZE = 196  # Bytes per block
DEFAULT_BLOCKS_PER_COL = 512  # As per Stratics
DEFAULT_TILES_PER_BLOCK = 8    # Tiles per block in both dimensions

class UOMapMULReader:
    def __init__(self, filepath, blocks_per_col=DEFAULT_BLOCKS_PER_COL, tiles_per_block=DEFAULT_TILES_PER_BLOCK):
        self.filepath = filepath
        self.blocks_per_col = blocks_per_col
        self.tiles_per_block = tiles_per_block
        self.width = None
        self.height = None
        self.blocks_per_row = None
        self.total_blocks = None

        # Initialize map dimensions based on file size
        self.initialize_map_dimensions()

        # Open the file once for faster access during search and export
        try:
            self.file = open(self.filepath, 'rb')
            logging.debug("Map file opened successfully for reading.")
        except Exception as e:
            logging.exception(f"Failed to open map file: {e}")
            self.file = None

    def initialize_map_dimensions(self):
        try:
            file_size = os.path.getsize(self.filepath)
            logging.info(f"Map file size: {file_size} bytes")
            self.total_blocks = file_size // BLOCK_SIZE
            logging.info(f"Total blocks: {self.total_blocks}")

            # Calculate blocks_per_row using floor division to handle extra blocks
            self.blocks_per_row = self.total_blocks // self.blocks_per_col
            remainder_blocks = self.total_blocks % self.blocks_per_col

            if remainder_blocks != 0:
                logging.warning(f"Total blocks ({self.total_blocks}) not divisible by blocks_per_col ({self.blocks_per_col}).")
                logging.warning(f"Remainder blocks: {remainder_blocks}. These will be ignored.")

            self.width = self.blocks_per_row * self.tiles_per_block
            self.height = self.blocks_per_col * self.tiles_per_block

            logging.info(f"Map dimensions: {self.width}x{self.height} tiles")
            logging.info(f"Blocks per row: {self.blocks_per_row}, Blocks per col: {self.blocks_per_col}")

        except Exception as e:
            logging.exception(f"Error initializing map dimensions: {e}")
            raise

    def close(self):
        if self.file:
            self.file.close()
            logging.debug("Map file closed.")

    def get_tile(self, x, y, swap_coords=False):
        # Optionally swap coordinates
        if swap_coords:
            x, y = y, x

        # Validate coordinates
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            logging.debug(f"Tile ({x},{y}) is out of bounds.")
            return None

        # Calculate block coordinates
        x_block = x // self.tiles_per_block
        y_block = y // self.tiles_per_block

        # Calculate block index using Stratics' formula
        block_index = (x_block * self.blocks_per_col) + y_block

        # Ensure block_index is within total_blocks
        if block_index >= self.total_blocks:
            logging.debug(f"Block index {block_index} for tile ({x},{y}) exceeds total blocks.")
            return None

        # Calculate tile's position within the block
        tile_x_in_block = x % self.tiles_per_block
        tile_y_in_block = y % self.tiles_per_block
        tile_index_in_block = tile_y_in_block * self.tiles_per_block + tile_x_in_block

        # Calculate byte offset: block_offset + 4 (header) + tile data
        block_offset = block_index * BLOCK_SIZE
        tile_offset = 4 + (tile_index_in_block * 3)
        read_offset = block_offset + tile_offset

        try:
            self.file.seek(read_offset)
            data = self.file.read(3)
            if len(data) < 3:
                logging.debug(f"Insufficient data read for tile ({x},{y}) at offset {read_offset}.")
                return None
            land_id, z = struct.unpack('<Hb', data)
            logging.debug(f"Tile ({x},{y}) - Land_ID: {land_id}, Z: {z}")
            return (land_id, z)
        except Exception as e:
            logging.exception(f"Error reading tile at ({x},{y}): {e}")
            return None

    def export_region_to_csv(self, csv_path, x_min, x_max, y_min, y_max, include_ids, exclude_ids, swap_coords=False):
        logging.info(f"Exporting region to CSV: {csv_path}")
        logging.info(f"Region: x={x_min} to {x_max}, y={y_min} to {y_max}")
        logging.info(f"Inclusion Land_IDs: {include_ids}")
        logging.info(f"Exclusion Land_IDs: {exclude_ids}")
        logging.info(f"Swap Coordinates: {swap_coords}")

        # Open CSV file for writing
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["x", "y", "Land_ID", "Z"])  # Header

                total_tiles = (x_max - x_min + 1) * (y_max - y_min + 1)
                processed_tiles = 0

                for y in range(y_min, y_max + 1):
                    for x in range(x_min, x_max + 1):
                        tile = self.get_tile(x, y, swap_coords=swap_coords)
                        if tile is None:
                            continue
                        land_id, z = tile

                        # Apply Inclusion Filter
                        if include_ids and land_id not in include_ids:
                            continue

                        # Apply Exclusion Filter
                        if exclude_ids and land_id in exclude_ids:
                            continue

                        writer.writerow([x, y, land_id, z])
                        processed_tiles += 1

                        # Logging progress every 100,000 tiles
                        if processed_tiles % 100000 == 0:
                            progress = (processed_tiles / total_tiles) * 100
                            logging.info(f"Export progress: {processed_tiles}/{total_tiles} tiles processed ({progress:.2f}%)")

                logging.info(f"Export completed. Total tiles exported: {processed_tiles}")
        except Exception as e:
            logging.exception(f"Failed to export CSV: {e}")
            raise

    def load_known_tiles(self, json_filepaths):
        """
        Load known tile data from multiple JSON files.
        Each JSON file should contain a list of tile dictionaries.
        """
        known_tiles = []
        for filepath in json_filepaths:
            try:
                with open(filepath, 'r', encoding='utf-8') as jf:
                    data = json.load(jf)
                    # Ensure data is a list
                    if isinstance(data, dict):
                        data = [data]
                    for tile in data:
                        # Convert land_id from hex to integer if necessary
                        land_id = tile.get("land_id", 0)
                        if isinstance(land_id, str):
                            try:
                                land_id = int(land_id, 16)
                            except ValueError:
                                logging.error(f"Invalid Land_ID format in JSON: {land_id}")
                                continue
                        known_tile = {
                            "filename": tile.get("filename", ""),
                            "mode": tile.get("mode", ""),
                            "threshold": tile.get("threshold", 0.0),
                            "position_x": tile.get("position_x", 0),
                            "position_y": tile.get("position_y", 0),
                            "position_z": tile.get("position_z", 0),
                            "land_id": land_id,
                            "corrected": tile.get("corrected", False)
                        }
                        known_tiles.append(known_tile)
                logging.info(f"Loaded {len(data)} tiles from '{filepath}'.")
            except Exception as e:
                logging.exception(f"Failed to load JSON file '{filepath}': {e}")
        return known_tiles

class MULMapGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Ultima Online MUL Map Reader")

        self.map_reader = None
        self.map_path_var = tk.StringVar()
        self.x_var = tk.StringVar()
        self.y_var = tk.StringVar()

        # Initialize known tiles
        self.known_tiles = []

        # File selection frame
        file_frame = tk.Frame(root)
        file_frame.pack(pady=5, padx=10, fill='x')

        tk.Label(file_frame, text="Map MUL File:").pack(side='left')
        tk.Entry(file_frame, textvariable=self.map_path_var, width=50).pack(side='left', padx=5)
        tk.Button(file_frame, text="Browse", command=self.browse_file).pack(side='left', padx=5)

        # Coordinates frame for single tile lookup
        coord_frame = tk.Frame(root)
        coord_frame.pack(pady=5, padx=10, fill='x')

        tk.Label(coord_frame, text="X:").pack(side='left')
        tk.Entry(coord_frame, textvariable=self.x_var, width=10).pack(side='left', padx=5)
        
        tk.Label(coord_frame, text="Y:").pack(side='left')
        tk.Entry(coord_frame, textvariable=self.y_var, width=10).pack(side='left', padx=5)

        # Region frame for CSV export
        region_frame = tk.Frame(root)
        region_frame.pack(pady=5, padx=10, fill='x')

        self.x_min_var = tk.StringVar()
        self.x_max_var = tk.StringVar()
        self.y_min_var = tk.StringVar()
        self.y_max_var = tk.StringVar()

        tk.Label(region_frame, text="X Min:").pack(side='left')
        tk.Entry(region_frame, textvariable=self.x_min_var, width=10).pack(side='left', padx=5)

        tk.Label(region_frame, text="X Max:").pack(side='left')
        tk.Entry(region_frame, textvariable=self.x_max_var, width=10).pack(side='left', padx=5)

        tk.Label(region_frame, text="Y Min:").pack(side='left')
        tk.Entry(region_frame, textvariable=self.y_min_var, width=10).pack(side='left', padx=5)

        tk.Label(region_frame, text="Y Max:").pack(side='left')
        tk.Entry(region_frame, textvariable=self.y_max_var, width=10).pack(side='left', padx=5)

        # Land_ID inclusion filter frame
        filter_frame = tk.Frame(root)
        filter_frame.pack(pady=5, padx=10, fill='both')

        tk.Label(filter_frame, text="Land_ID Inclusion Filter for Export (one per line or separated by spaces):").pack(anchor='w')
        self.land_id_filter_text = scrolledtext.ScrolledText(filter_frame, height=5, width=40)
        self.land_id_filter_text.pack(pady=5, padx=5, fill='both', expand=True)

        # Land_ID exclusion filter frame
        exclusion_frame = tk.Frame(root)
        exclusion_frame.pack(pady=5, padx=10, fill='both')

        tk.Label(exclusion_frame, text="Land_ID Exclusion Filter (one per line or separated by spaces):").pack(anchor='w')
        self.land_id_exclude_text = scrolledtext.ScrolledText(exclusion_frame, height=5, width=40)
        self.land_id_exclude_text.pack(pady=5, padx=5, fill='both', expand=True)
        # Set default exclusion to 580
        self.land_id_exclude_text.insert(tk.END, "580")

        # Land_ID search frame
        search_frame = tk.Frame(root)
        search_frame.pack(pady=5, padx=10, fill='both')

        tk.Label(search_frame, text="Land_IDs to Search (one per line or separated by spaces):").pack(anchor='w')
        self.land_id_search_text = scrolledtext.ScrolledText(search_frame, height=5, width=40)
        self.land_id_search_text.pack(pady=5, padx=5, fill='both', expand=True)

        # Load JSON files frame
        json_frame = tk.Frame(root)
        json_frame.pack(pady=5, padx=10, fill='both')

        tk.Label(json_frame, text="Known Tiles JSON Files:").pack(anchor='w')
        self.json_filepaths = []
        tk.Button(json_frame, text="Load JSON Files", command=self.load_json_files).pack(pady=2)

        # Verify Tiles frame
        verify_frame = tk.Frame(root)
        verify_frame.pack(pady=5, padx=10, fill='x')

        tk.Button(verify_frame, text="Verify Known Tiles", command=self.verify_known_tiles).pack()

        # Swap Coordinates Checkbox
        swap_frame = tk.Frame(root)
        swap_frame.pack(pady=5, padx=10, fill='x')

        self.swap_coords_var = tk.BooleanVar()
        tk.Checkbutton(swap_frame, text="Swap X and Y Coordinates", variable=self.swap_coords_var).pack(anchor='w')

        # Search results frame
        results_frame = tk.Frame(root)
        results_frame.pack(pady=5, padx=10, fill='both', expand=True)

        tk.Label(results_frame, text="Search Results (x, y):").pack(anchor='w')
        self.search_results_listbox = tk.Listbox(results_frame, height=10)
        self.search_results_scrollbar = tk.Scrollbar(results_frame, orient="vertical")
        self.search_results_listbox.config(yscrollcommand=self.search_results_scrollbar.set)
        self.search_results_scrollbar.config(command=self.search_results_listbox.yview)
        self.search_results_listbox.pack(side='left', fill='both', expand=True)
        self.search_results_scrollbar.pack(side='right', fill='y')

        # Action frame
        action_frame = tk.Frame(root)
        action_frame.pack(pady=10)

        tk.Button(action_frame, text="Load Map", command=self.load_map).pack(side='left', padx=5)
        tk.Button(action_frame, text="Get Tile", command=self.get_tile).pack(side='left', padx=5)
        tk.Button(action_frame, text="Export to CSV", command=self.export_csv).pack(side='left', padx=5)
        tk.Button(action_frame, text="Search Land_IDs", command=self.search_land_ids).pack(side='left', padx=5)

        # Result area
        self.result_text = scrolledtext.ScrolledText(root, height=10, width=60)
        self.result_text.pack(pady=10, padx=10, fill='both', expand=True)

        # Queue and thread management for search
        self.search_queue = queue.Queue()
        self.search_thread = None
        self.stop_search_event = threading.Event()

    def browse_file(self):
        filepath = filedialog.askopenfilename(title="Select Ultima Online map MUL file", 
                                              filetypes=[("MUL Files", "*.mul"), ("All Files", "*.*")])
        if filepath:
            self.map_path_var.set(filepath)
            logging.info(f"Selected file: {filepath}")

    def load_map(self):
        path = self.map_path_var.get().strip()
        if not os.path.isfile(path):
            logging.error("Invalid file path provided.")
            self.result_text.insert(tk.END, "Invalid file path.\n")
            return
        try:
            # Close existing map_reader if any
            if self.map_reader:
                self.map_reader.close()
            # Prompt user for map dimensions if auto-detection fails
            try:
                self.map_reader = UOMapMULReader(path)
                if self.map_reader.file is not None:
                    self.result_text.insert(tk.END, f"Map file '{path}' loaded successfully.\n")
                    logging.info("Map file loaded successfully.")
            except ValueError as ve:
                logging.error("Failed to initialize map dimensions automatically.")
                self.result_text.insert(tk.END, "Failed to initialize map dimensions automatically.\n")
                # Prompt for manual input
                self.prompt_manual_dimensions(path)
        except Exception as e:
            logging.exception("Failed to load map file.")
            self.result_text.insert(tk.END, f"Error loading map file: {e}\n")

    def prompt_manual_dimensions(self, path):
        # Create a new window to input manual dimensions
        manual_window = tk.Toplevel(self.root)
        manual_window.title("Manual Map Dimensions Input")

        tk.Label(manual_window, text="Enter Map Dimensions:").pack(pady=5)

        dim_frame = tk.Frame(manual_window)
        dim_frame.pack(pady=5, padx=10)

        tk.Label(dim_frame, text="Width (tiles):").grid(row=0, column=0, padx=5, pady=5)
        width_var = tk.StringVar()
        tk.Entry(dim_frame, textvariable=width_var).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(dim_frame, text="Height (tiles):").grid(row=1, column=0, padx=5, pady=5)
        height_var = tk.StringVar()
        tk.Entry(dim_frame, textvariable=height_var).grid(row=1, column=1, padx=5, pady=5)

        def submit_dimensions():
            try:
                width = int(width_var.get())
                height = int(height_var.get())
                if width % self.map_reader.tiles_per_block != 0 or height % self.map_reader.tiles_per_block != 0:
                    messagebox.showerror("Error", f"Width and Height must be divisible by {self.map_reader.tiles_per_block}.")
                    return
                blocks_per_row = width // self.map_reader.tiles_per_block
                blocks_per_col = height // self.map_reader.tiles_per_block
                # Reinitialize map_reader with new dimensions
                self.map_reader.close()
                self.map_reader = UOMapMULReader(path, blocks_per_col=blocks_per_col, tiles_per_block=self.map_reader.tiles_per_block)
                self.result_text.insert(tk.END, f"Map file '{path}' loaded with dimensions {width}x{height} tiles.\n")
                logging.info(f"Map file '{path}' loaded with dimensions {width}x{height} tiles.")
                manual_window.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter valid integer values for width and height.")
            except Exception as e:
                logging.exception("Failed to load map with manual dimensions.")
                messagebox.showerror("Error", f"Failed to load map: {e}")

        tk.Button(manual_window, text="Submit", command=submit_dimensions).pack(pady=10)

    def get_tile(self):
        if self.map_reader is None or self.map_reader.file is None:
            logging.warning("Attempted to get tile without a loaded map.")
            self.result_text.insert(tk.END, "Load a map before attempting to get tile info.\n")
            return

        try:
            x = int(self.x_var.get())
            y = int(self.y_var.get())
        except ValueError:
            logging.error("Non-integer coordinates entered for tile lookup.")
            self.result_text.insert(tk.END, "Please enter valid integer coordinates.\n")
            return

        swap_coords = self.swap_coords_var.get()
        tile = self.map_reader.get_tile(x, y, swap_coords=swap_coords)
        if tile is None:
            msg = f"Tile at ({x},{y}) is out of range or unreadable.\n"
        else:
            land_id, z = tile
            msg = f"Tile at ({x},{y}): Land_ID={land_id}, Z={z}\n"
        self.result_text.insert(tk.END, msg)
        logging.info(msg.strip())

    def export_csv(self):
        if self.map_reader is None or self.map_reader.file is None:
            logging.warning("Attempted to export CSV without a loaded map.")
            self.result_text.insert(tk.END, "Load a map before exporting.\n")
            return

        # Helper function to parse integers or return None
        def parse_or_none(var):
            val = var.get().strip()
            if val.lstrip('-').isdigit():  # handle negative values
                return int(val)
            return None

        # Parse region bounds
        x_min = parse_or_none(self.x_min_var)
        x_max = parse_or_none(self.x_max_var)
        y_min = parse_or_none(self.y_min_var)
        y_max = parse_or_none(self.y_max_var)

        # Default to full map if bounds not specified
        if x_min is None:
            x_min = 0
        if x_max is None:
            x_max = self.map_reader.width - 1
        if y_min is None:
            y_min = 0
        if y_max is None:
            y_max = self.map_reader.height - 1

        # Parse Land_ID inclusion filters
        filter_text = self.land_id_filter_text.get("1.0", tk.END).strip()
        include_ids = set()
        if filter_text:
            # Split by any whitespace or commas and parse integers
            parts = filter_text.replace(',', ' ').split()
            for p in parts:
                if p.lstrip('-').isdigit():  # handle negative IDs if any
                    include_ids.add(int(p))
        logging.debug(f"Export Inclusion Land_ID filters: {include_ids}")

        # Parse Land_ID exclusion filters
        exclude_text = self.land_id_exclude_text.get("1.0", tk.END).strip()
        exclude_ids = set()
        if exclude_text:
            # Split by any whitespace or commas and parse integers
            parts = exclude_text.replace(',', ' ').split()
            for p in parts:
                if p.lstrip('-').isdigit():
                    exclude_ids.add(int(p))
        logging.debug(f"Export Exclusion Land_ID filters: {exclude_ids}")

        # Determine adjusted region inside export_region_to_csv
        csv_path = filedialog.asksaveasfilename(title="Save CSV", defaultextension=".csv",
                                                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not csv_path:
            logging.info("CSV export canceled by user.")
            return

        # Confirmation dialog
        result = messagebox.askyesno("Confirm", "This may take a long time for large regions. Continue?")
        if not result:
            logging.info("CSV export canceled by user.")
            return

        swap_coords = self.swap_coords_var.get()

        # Perform export in a separate thread to keep GUI responsive
        export_thread = threading.Thread(target=self.perform_export, args=(csv_path, x_min, x_max, y_min, y_max, include_ids, exclude_ids, swap_coords))
        export_thread.start()

    def perform_export(self, csv_path, x_min, x_max, y_min, y_max, include_ids, exclude_ids, swap_coords):
        try:
            self.map_reader.export_region_to_csv(csv_path, x_min, x_max, y_min, y_max, include_ids, exclude_ids, swap_coords=swap_coords)
            self.result_text.insert(tk.END, f"Exported region to '{csv_path}'.\n")
            logging.info("CSV region export completed successfully.")
        except Exception as e:
            logging.exception("Error exporting CSV region.")
            self.result_text.insert(tk.END, f"Error exporting CSV: {e}\n")

    def load_json_files(self):
        json_filepaths = filedialog.askopenfilenames(title="Select Known Tiles JSON Files", 
                                                     filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])
        if json_filepaths:
            self.json_filepaths = list(json_filepaths)
            logging.info(f"Selected {len(self.json_filepaths)} JSON files for known tiles.")
            self.result_text.insert(tk.END, f"Loaded {len(self.json_filepaths)} JSON files.\n")
        else:
            logging.info("No JSON files selected for known tiles.")
            self.result_text.insert(tk.END, "No JSON files selected for known tiles.\n")

    def verify_known_tiles(self):
        if self.map_reader is None or self.map_reader.file is None:
            logging.warning("Attempted to verify tiles without a loaded map.")
            self.result_text.insert(tk.END, "Load a map before verifying tiles.\n")
            return
        if not self.json_filepaths:
            logging.warning("No JSON files loaded for verification.")
            self.result_text.insert(tk.END, "Load JSON files containing known tile data.\n")
            return

        # Load known tiles
        self.known_tiles = self.map_reader.load_known_tiles(self.json_filepaths)
        if not self.known_tiles:
            logging.warning("No known tiles loaded from JSON files.")
            self.result_text.insert(tk.END, "No known tiles loaded from JSON files.\n")
            return

        # Start verification in a separate thread
        verify_thread = threading.Thread(target=self.perform_verification)
        verify_thread.start()

    def perform_verification(self):
        discrepancies = []
        total_known = len(self.known_tiles)
        processed = 0

        for tile in self.known_tiles:
            x = tile["position_x"]
            y = tile["position_y"]
            expected_land_id = tile["land_id"]
            expected_z = tile["position_z"]

            # Verify without swapping coordinates
            actual_tile = self.map_reader.get_tile(x, y, swap_coords=False)
            if actual_tile is None:
                discrepancies.append({
                    "x": x,
                    "y": y,
                    "issue": "Tile out of range or unreadable."
                })
                continue

            actual_land_id, actual_z = actual_tile

            if actual_land_id != expected_land_id or actual_z != expected_z:
                discrepancies.append({
                    "x": x,
                    "y": y,
                    "expected_land_id": expected_land_id,
                    "actual_land_id": actual_land_id,
                    "expected_z": expected_z,
                    "actual_z": actual_z,
                    "swap_coords": False
                })

                # Attempt to verify by swapping coordinates if checkbox is checked
                swap_coords = self.swap_coords_var.get()
                if swap_coords:
                    actual_tile_swapped = self.map_reader.get_tile(x, y, swap_coords=True)
                    if actual_tile_swapped:
                        swapped_land_id, swapped_z = actual_tile_swapped
                        if swapped_land_id == expected_land_id and swapped_z == expected_z:
                            discrepancies.append({
                                "x": x,
                                "y": y,
                                "expected_land_id": expected_land_id,
                                "actual_land_id": swapped_land_id,
                                "expected_z": expected_z,
                                "actual_z": swapped_z,
                                "swap_coords": True
                            })
            processed += 1

            if processed % 1000 == 0:
                logging.info(f"Verification progress: {processed}/{total_known} tiles processed.")

        # Display results
        if not discrepancies:
            self.result_text.insert(tk.END, "All known tiles match the MUL data.\n")
            logging.info("Verification completed. All known tiles match.")
        else:
            self.result_text.insert(tk.END, f"Verification completed with {len(discrepancies)} discrepancies.\n")
            logging.info(f"Verification completed with {len(discrepancies)} discrepancies.")

            for disc in discrepancies:
                if "issue" in disc:
                    msg = f"Tile at ({disc['x']}, {disc['y']}): {disc['issue']}\n"
                elif disc.get("swap_coords", False):
                    msg = (f"Tile at ({disc['x']}, {disc['y']}): "
                           f"Expected Land_ID={disc['expected_land_id']}, Z={disc['expected_z']} | "
                           f"Found Land_ID={disc['actual_land_id']}, Z={disc['actual_z']} (Swapped Coordinates)\n")
                else:
                    msg = (f"Tile at ({disc['x']}, {disc['y']}): "
                           f"Expected Land_ID={disc['expected_land_id']}, Z={disc['expected_z']} | "
                           f"Found Land_ID={disc['actual_land_id']}, Z={disc['actual_z']}\n")
                self.result_text.insert(tk.END, msg)
                logging.debug(msg.strip())

    def search_land_ids(self):
        if self.map_reader is None or self.map_reader.file is None:
            logging.warning("Attempted to search Land_IDs without a loaded map.")
            self.result_text.insert(tk.END, "Load a map before searching Land_IDs.\n")
            return

        # Parse Land_IDs to search
        filter_text = self.land_id_search_text.get("1.0", tk.END).strip()
        land_ids = set()
        if filter_text:
            # Split by any whitespace or commas and parse integers
            parts = filter_text.replace(',', ' ').split()
            for p in parts:
                if p.lstrip('-').isdigit():
                    land_ids.add(int(p))
        if not land_ids:
            messagebox.showinfo("Info", "No Land_IDs entered for search.")
            logging.info("No Land_IDs entered for search.")
            return

        # Clear previous search results
        self.search_results_listbox.delete(0, tk.END)

        # Parse search region bounds
        def parse_or_none(var):
            val = var.get().strip()
            if val.lstrip('-').isdigit():
                return int(val)
            return None

        x_min = parse_or_none(self.x_min_var)
        x_max = parse_or_none(self.x_max_var)
        y_min = parse_or_none(self.y_min_var)
        y_max = parse_or_none(self.y_max_var)

        # Default to full map if bounds not specified
        if x_min is None:
            x_min = 0
        if x_max is None:
            x_max = self.map_reader.width - 1
        if y_min is None:
            y_min = 0
        if y_max is None:
            y_max = self.map_reader.height - 1

        # Clamp within map
        x_min = max(0, min(x_min, self.map_reader.width - 1))
        x_max = max(0, min(x_max, self.map_reader.width - 1))
        y_min = max(0, min(y_min, self.map_reader.height - 1))
        y_max = max(0, min(y_max, self.map_reader.height - 1))

        # Ensure min <= max
        if x_min > x_max:
            x_min, x_max = x_max, x_min
        if y_min > y_max:
            y_min, y_max = y_max, y_min

        logging.info(f"Search region: x={x_min} to {x_max}, y={y_min} to {y_max}")
        logging.info(f"Land_IDs to search: {land_ids}")

        # Initialize queue and event
        self.search_queue = queue.Queue()
        self.stop_search_event = threading.Event()

        # Start search thread
        search_thread = threading.Thread(target=self.perform_land_id_search, args=(land_ids, x_min, x_max, y_min, y_max))
        search_thread.start()

        # Start polling the queue
        self.root.after(100, self.process_search_queue)

        # Log start
        logging.info("Land_ID search started.")

    def perform_land_id_search(self, land_ids, x_min, x_max, y_min, y_max):
        for y in range(y_min, y_max + 1):
            for x in range(x_min, x_max + 1):
                tile = self.map_reader.get_tile(x, y, swap_coords=self.swap_coords_var.get())
                if tile is None:
                    continue
                land_id, z = tile
                if land_id in land_ids:
                    self.search_queue.put((x, y))
        # Signal completion
        self.search_queue.put(None)

    def process_search_queue(self):
        try:
            while True:
                item = self.search_queue.get_nowait()
                if item is None:
                    # Search completed
                    self.result_text.insert(tk.END, "Land_ID search completed.\n")
                    logging.info("Land_ID search completed.")
                    return
                else:
                    x, y = item
                    self.search_results_listbox.insert(tk.END, f"({x}, {y})")
        except queue.Empty:
            pass
        self.root.after(100, self.process_search_queue)

    def load_json_files(self):
        json_filepaths = filedialog.askopenfilenames(title="Select Known Tiles JSON Files", 
                                                     filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])
        if json_filepaths:
            self.json_filepaths = list(json_filepaths)
            logging.info(f"Selected {len(self.json_filepaths)} JSON files for known tiles.")
            self.result_text.insert(tk.END, f"Loaded {len(self.json_filepaths)} JSON files.\n")
        else:
            logging.info("No JSON files selected for known tiles.")
            self.result_text.insert(tk.END, "No JSON files selected for known tiles.\n")

    def verify_known_tiles(self):
        if self.map_reader is None or self.map_reader.file is None:
            logging.warning("Attempted to verify tiles without a loaded map.")
            self.result_text.insert(tk.END, "Load a map before verifying tiles.\n")
            return
        if not self.json_filepaths:
            logging.warning("No JSON files loaded for verification.")
            self.result_text.insert(tk.END, "Load JSON files containing known tile data.\n")
            return

        # Load known tiles
        self.known_tiles = self.map_reader.load_known_tiles(self.json_filepaths)
        if not self.known_tiles:
            logging.warning("No known tiles loaded from JSON files.")
            self.result_text.insert(tk.END, "No known tiles loaded from JSON files.\n")
            return

        # Start verification in a separate thread
        verify_thread = threading.Thread(target=self.perform_verification)
        verify_thread.start()

    def perform_verification(self):
        discrepancies = []
        total_known = len(self.known_tiles)
        processed = 0

        for tile in self.known_tiles:
            x = tile["position_x"]
            y = tile["position_y"]
            expected_land_id = tile["land_id"]
            expected_z = tile["position_z"]

            # Verify without swapping coordinates
            actual_tile = self.map_reader.get_tile(x, y, swap_coords=False)
            if actual_tile is None:
                discrepancies.append({
                    "x": x,
                    "y": y,
                    "issue": "Tile out of range or unreadable."
                })
                continue

            actual_land_id, actual_z = actual_tile

            if actual_land_id != expected_land_id or actual_z != expected_z:
                discrepancies.append({
                    "x": x,
                    "y": y,
                    "expected_land_id": expected_land_id,
                    "actual_land_id": actual_land_id,
                    "expected_z": expected_z,
                    "actual_z": actual_z,
                    "swap_coords": False
                })

                # Attempt to verify by swapping coordinates if checkbox is checked
                swap_coords = self.swap_coords_var.get()
                if swap_coords:
                    actual_tile_swapped = self.map_reader.get_tile(x, y, swap_coords=True)
                    if actual_tile_swapped:
                        swapped_land_id, swapped_z = actual_tile_swapped
                        if swapped_land_id == expected_land_id and swapped_z == expected_z:
                            discrepancies.append({
                                "x": x,
                                "y": y,
                                "expected_land_id": expected_land_id,
                                "actual_land_id": swapped_land_id,
                                "expected_z": expected_z,
                                "actual_z": swapped_z,
                                "swap_coords": True
                            })
            processed += 1

            if processed % 1000 == 0:
                logging.info(f"Verification progress: {processed}/{total_known} tiles processed.")

        # Display results
        if not discrepancies:
            self.result_text.insert(tk.END, "All known tiles match the MUL data.\n")
            logging.info("Verification completed. All known tiles match.")
        else:
            self.result_text.insert(tk.END, f"Verification completed with {len(discrepancies)} discrepancies.\n")
            logging.info(f"Verification completed with {len(discrepancies)} discrepancies.")

            for disc in discrepancies:
                if "issue" in disc:
                    msg = f"Tile at ({disc['x']}, {disc['y']}): {disc['issue']}\n"
                elif disc.get("swap_coords", False):
                    msg = (f"Tile at ({disc['x']}, {disc['y']}): "
                           f"Expected Land_ID={disc['expected_land_id']}, Z={disc['expected_z']} | "
                           f"Found Land_ID={disc['actual_land_id']}, Z={disc['actual_z']} (Swapped Coordinates)\n")
                else:
                    msg = (f"Tile at ({disc['x']}, {disc['y']}): "
                           f"Expected Land_ID={disc['expected_land_id']}, Z={disc['expected_z']} | "
                           f"Found Land_ID={disc['actual_land_id']}, Z={disc['actual_z']}\n")
                self.result_text.insert(tk.END, msg)
                logging.debug(msg.strip())

    def on_closing(self):
        # Close the map file gracefully
        if self.map_reader:
            self.map_reader.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MULMapGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
