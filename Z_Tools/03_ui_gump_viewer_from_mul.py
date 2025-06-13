"""
UI GUMP VIEWER - a Ultima Online gump loader and viewer
- Load from .mul files (gumpidx.mul, gumpart.mul)
- View the user interface of gump art
- Display the gump art id
- Switch between gump art folders (original vs modded)
- Load gump art by ID or HEX or modded filename containing hex

TODO:
- show the gump art as all images loaded in scrollable window
- show number , hex id , and name , 
- show the gump art color coded background frame based on the gump used together
- filter by a gump from verdata ( showing only the gumps that correspond )
- filter by gump category such as character equipment
- show a line diagram generator of the assembled gump and the parts , organized to not overlap and be relatively close in a generally outward radial aspect ratio
"""

import os
import struct
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import numpy as np

class GumpMulLoader:
    def __init__(self, folder):
        self.folder = folder
        self.idx_path = os.path.join(folder, 'gumpidx.mul')
        self.art_path = os.path.join(folder, 'gumpart.mul')
        self.idx_file = None
        self.art_file = None
        self.entries = []
        self.valid_ids = []
        self._load_index()

    def _load_index(self):
        print("\n--- GumpMulLoader: Loading folder structure ---")
        print(f"Looking for: {self.idx_path}")
        print(f"Looking for: {self.art_path}")
        if not (os.path.exists(self.idx_path) and os.path.exists(self.art_path)):
            print("gumpidx.mul or gumpart.mul not found!")
            self.entries = []
            self.valid_ids = []
            return
        self.idx_file = open(self.idx_path, 'rb')
        self.art_file = open(self.art_path, 'rb')
        self.entries = []
        self.valid_ids = []
        self.idx_file.seek(0, os.SEEK_END)
        size = self.idx_file.tell()
        count = size // 12
        print(f"Found {count} entries in gumpidx.mul.")
        self.idx_file.seek(0)
        for idx in range(count):
            data = self.idx_file.read(12)
            offset, length, extra = struct.unpack('<iii', data)
            self.entries.append((offset, length, extra))
            # Only consider as valid if offset >= 0, length > 0, extra != -1, width/height > 0
            width = (extra >> 16) & 0xFFFF
            height = extra & 0xFFFF
            if offset >= 0 and length > 0 and extra != -1 and width > 0 and height > 0:
                self.valid_ids.append(idx)
        print(f"Valid gump IDs: {len(self.valid_ids)}")
        if self.valid_ids:
            print(f"Sample available Gump IDs: {self.valid_ids[:10]} ... {self.valid_ids[-10:]}")
        print("--------------------------------------------\n")

    def get_count(self):
        return len(self.entries)

    def get_valid_ids(self):
        return self.valid_ids

    def close(self):
        if self.idx_file: self.idx_file.close()
        if self.art_file: self.art_file.close()

    def get_gump(self, index):
        # Returns (PIL.Image or None, width, height)
        if index < 0 or index >= len(self.entries):
            return None, 0, 0
        offset, length, extra = self.entries[index]
        if offset < 0 or length <= 0 or extra == -1:
            return None, 0, 0
        width = (extra >> 16) & 0xFFFF
        height = extra & 0xFFFF
        if width <= 0 or height <= 0:
            return None, 0, 0
        print(f"Gumpart.mul entry offset: {offset}, length: {length}")
        self.art_file.seek(offset)
        raw = self.art_file.read(length)
        try:
            img = self.decode_gump(raw, width, height, gump_id=index)
            return img, width, height
        except Exception as e:
            print(f"Error decoding gump {index}: {e}")
            return None, width, height

    @staticmethod
    def decode_gump_with_strategy(data, width, height, gump_id=None, debug=True, word_idx_func=None, strategy_name="default"):
        """
        Attempt to decode a UO gumpart.mul image using a flexible row offset interpretation.

        This function is primarily for testing and comparing different row lookup and RLE run block interpretations.
        It is NOT the final/correct decoder, but is useful for diagnostics and reverse engineering.

        Format details:
        - The gumpart.mul format begins with a row lookup table: an array of DWORDs (4 bytes each), one per row (height).
        - Each DWORD in the lookup table typically points to the start of that row's run blocks, but the meaning (byte offset, word offset, or run block index) varies by implementation.
        - After the lookup table, the remainder of the data is an array of run blocks (RLE pairs), typically as 16-bit words.
        - Each run block is usually a (value, run) or (run, value) pair, both as uint16. 'run' is the number of pixels, 'value' is the color (ARGB1555, with 0 = transparent).
        - The function allows you to supply a custom word_idx_func to interpret the lookup table offsets in various ways (e.g., as byte offsets, indices, relative to first row, etc).
        - This is useful for systematically testing all plausible decoding strategies when the format is ambiguous.

        Args:
            data (bytes): Raw gumpart.mul entry data for a single image.
            width (int): Width of the image.
            height (int): Height of the image.
            gump_id (int, optional): Gump ID, for debugging.
            debug (bool): If True, print debug output.
            word_idx_func (callable): Function (offsets, row, height) -> word index for start of row's run blocks.
            strategy_name (str): Label for the current decoding strategy (for diagnostics).

        Returns:
            pixels (np.ndarray): Decoded pixel array (height, width, uint16 ARGB1555).
            run_sum_warnings (int): Number of rows whose run sum did not match width.
            diff_count (int): Pixel mismatch count if ground truth is available, else 0.
            strategy_name (str): The label for this decoding attempt.
        """
        if len(data) < height * 4:
            raise ValueError("Data too short for line offsets")
        line_offsets = struct.unpack_from('<' + 'I'*height, data, 0)
        rle_data = np.frombuffer(data[height*4:], dtype=np.uint16)
        pixels = np.zeros((height, width), dtype=np.uint16)
        run_sum_warnings = 0
        for y in range(height):
            if word_idx_func:
                word_idx = word_idx_func(line_offsets, y, height)
            else:
                word_idx = (line_offsets[y] - height*4) // 2
            x = 0
            run_sum = 0
            while x < width and word_idx + 1 < len(rle_data):
                run = rle_data[word_idx]
                color = rle_data[word_idx+1]
                word_idx += 2
                if color != 0:
                    color ^= 0x8000  # ARGB1555 fix
                pixels[y, x:x+run] = color
                x += run
                run_sum += run
            if run_sum != width:
                run_sum_warnings += 1
        # Convert to RGBA8888 for display
        rgba = np.zeros((height, width, 4), dtype=np.uint8)
        for y in range(height):
            for x in range(width):
                color = pixels[y, x]
                a = 255 if (color & 0x8000) else 0
                r = ((color >> 10) & 0x1F) * 255 // 31
                g = ((color >> 5) & 0x1F) * 255 // 31
                b = (color & 0x1F) * 255 // 31
                rgba[y, x] = [r, g, b, a]
        # Compare to ground truth if available
        diff_count = None
        if gump_id == 3:
            from PIL import Image as PILImage
            import os
            gt_path = os.path.join(os.path.dirname(__file__), 'ref', 'Gump 3.png')
            if os.path.exists(gt_path):
                gt_img = PILImage.open(gt_path).convert('RGBA')
                gt_arr = np.array(gt_img)
                if gt_arr.shape[:2] == (height, width):
                    diff_count = np.sum(np.any(rgba != gt_arr, axis=2))
        return rgba, run_sum_warnings, diff_count, strategy_name



    # --- GUMP DECODER:  ---
    # the correct format for UO gumpart.mul is:
    #   - The row lookup table is an array of DWORDs, one per row.
    #   - Each value is a run-block index RELATIVE TO THE FIRST ROW (subtract row_lookup[0]).
    #   - Each run block is (value, run) in little-endian.
    #   - Each run block fills 'run' pixels with 'value' (after ARGB1555 ^ 0x8000 fix if nonzero).
    #   - Repeat for all rows; if run_sum != width, warn.
    # This method matches with reference gump PNGs.
    #
    # Previous attempts failed due to:
    #   - Treating row lookup as byte offset, not run-block index
    #   - Not subtracting the base value (row_lookup[0])
    #   - Swapping run/value order (some tools use (run,value), but UO gumps are (value,run))
    #   - Misinterpreting endianness or offset alignment
    #
    # Debug output is retained for future troubleshooting.
    @staticmethod
    def decode_gump(data, width, height, gump_id=None, debug=True):
        """
         decoder for UO gumpart.mul images 
        - Interprets row lookup table as DWORDs, relative to the first entry (row_lookup[0]).
        - Each run block is (value, run) in little-endian.
        - ARGB1555 color fix (value ^ 0x8000) applied for nonzero values.
        Args:
            data (bytes): Raw gumpart.mul entry data for a single image.
            width (int): Width of the image.
            height (int): Height of the image.
            gump_id (int, optional): Gump ID, for debugging/logging.
            debug (bool): If True, print debug output for each row.
        Returns:
            PIL.Image: Decoded RGBA image.
        """
        if len(data) < height * 4:
            raise ValueError("Data too short for row lookup table")
        row_lookup = struct.unpack_from('<' + 'I'*height, data, 0)
        data_start = height * 4
        total_run_blocks = (len(data) - data_start) // 4
        base = row_lookup[0]
        pixels = np.zeros((height, width), dtype=np.uint16)
        for y in range(height):
            row_off = row_lookup[y] - base
            if y < height - 1:
                next_off = row_lookup[y+1] - base
                run_block_count = next_off - row_off
            else:
                run_block_count = total_run_blocks - row_off
            byte_offset = data_start + row_off * 4
            row_pixels = 0
            for i in range(run_block_count):
                pair_off = byte_offset + i * 4
                value, run = struct.unpack_from('<HH', data, pair_off)
                if value != 0:
                    value ^= 0x8000  # ARGB1555 fix
                end = min(row_pixels+run, width)
                pixels[y, row_pixels:end] = value
                row_pixels += run
            if debug:
                print(f"[GUMP DECODE] Row {y}: run_sum={row_pixels}, width={width}")
                if row_pixels != width:
                    print(f"[WARNING] Row {y} run_sum != width: {row_pixels} != {width}")
        # Convert to RGBA8888 for display
        rgba = np.zeros((height, width, 4), dtype=np.uint8)
        for y in range(height):
            for x in range(width):
                color = pixels[y, x]
                a = 255 if (color & 0x8000) else 0
                r = ((color >> 10) & 0x1F) * 255 // 31
                g = ((color >> 5) & 0x1F) * 255 // 31
                b = (color & 0x1F) * 255 // 31
                rgba[y, x] = [r, g, b, a]
        return Image.fromarray(rgba, 'RGBA')


class GumpViewerApp(tk.Tk):
    DARK_BG = "#181825"
    DARKER_BG = "#101018"
    ENTRY_BG = "#23233a"
    FG = "#cccccc"
    ACCENT_GREEN = "#44ff99"
    ACCENT_BLUE = "#4eaaff"
    ACCENT_PURPLE = "#a66cff"
    BTN_BG = "#23233a"
    BTN_FG = "#cccccc"
    BTN_ACTIVE_BG = "#31314a"
    BTN_ACTIVE_FG = "#ffffff"

    def __init__(self):
        super().__init__()
        self.title("Ultima Online Gump Viewer")
        self.geometry("800x700")
        self.resizable(True, True)
        self.configure(bg=self.DARK_BG)
        self.gump_loader = None
        self.current_folder = None
        self.gump_img = None
        self.tk_img = None
        self.valid_ids = []
        self._build_ui()

    def _build_ui(self):
        style = {
            'bg': self.DARK_BG,
            'fg': self.FG,
            'highlightbackground': self.DARK_BG,
            'highlightcolor': self.ACCENT_BLUE
        }
        entry_style = {
            'bg': self.ENTRY_BG,
            'fg': self.ACCENT_GREEN,
            'insertbackground': self.ACCENT_GREEN,
            'highlightbackground': self.ACCENT_PURPLE
        }
        btn_style = {
            'bg': self.BTN_BG,
            'fg': self.BTN_FG,
            'activebackground': self.BTN_ACTIVE_BG,
            'activeforeground': self.BTN_ACTIVE_FG,
            'highlightbackground': self.ACCENT_PURPLE
        }
        top = tk.Frame(self, bg=self.DARK_BG)
        top.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        tk.Label(top, text="GumpArt folder:", **style).pack(side=tk.LEFT)
        self.folder_var = tk.StringVar()
        tk.Entry(top, textvariable=self.folder_var, width=40, **entry_style).pack(side=tk.LEFT, padx=2)
        tk.Button(top, text="Browse", command=self.browse_folder, **btn_style).pack(side=tk.LEFT)
        tk.Button(top, text="Load", command=self.load_folder, **btn_style).pack(side=tk.LEFT)

        mid = tk.Frame(self, bg=self.DARK_BG)
        mid.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        tk.Label(mid, text="Gump ID:", **style).pack(side=tk.LEFT)
        self.gumpid_var = tk.StringVar()
        self.gumpid_entry = tk.Entry(mid, textvariable=self.gumpid_var, width=8, **entry_style)
        self.gumpid_entry.pack(side=tk.LEFT)
        tk.Button(mid, text="Show", command=self.show_gump, **btn_style).pack(side=tk.LEFT)
        dark_bg = "#181825"
        dark_fg = "#e0e0e0"
        entry_bg = "#222233"
        entry_fg = "#e0e0e0"
        btn_green = "#2e4d3a"
        btn_blue = "#233a4d"
        btn_purple = "#3a2e4d"
        btn_fg = "#e0e0f0"
        self.hex_label = tk.Label(mid, text="Hexadecimal ID:", font=("Consolas", 12), bg=dark_bg, fg=dark_fg)
        self.hex_label.pack(side=tk.LEFT, padx=(6,2))
        self.id_entry = tk.Entry(mid, width=24, font=("Consolas", 14), bg=entry_bg, fg=entry_fg, insertbackground=entry_fg, relief=tk.FLAT, highlightbackground=dark_bg, highlightcolor=dark_fg)
        self.id_entry.pack(side=tk.LEFT, padx=4)
        self.id_entry.bind("<Return>", lambda e: self.load_gump_by_id_or_filename())
        self.load_button = tk.Button(mid, text="Load", command=self.load_gump_by_id_or_filename, bg=btn_green, fg=btn_fg, activebackground=btn_green, activeforeground=btn_fg, relief=tk.FLAT, highlightbackground=btn_green)
        self.load_button.pack(side=tk.LEFT, padx=4)
        self.count_label = tk.Label(mid, text="", **style)
        self.count_label.pack(side=tk.LEFT, padx=10)

        # Listbox for available gump IDs
        self.list_frame = tk.Frame(self, bg=self.DARKER_BG)
        self.list_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(10,0), pady=10)
        tk.Label(self.list_frame, text="Available Gump IDs", fg=self.ACCENT_PURPLE, bg=self.DARKER_BG, font=("Arial", 11, "bold")).pack(anchor=tk.NW)
        self.gumpid_listbox = tk.Listbox(self.list_frame, width=12, height=32, bg=self.DARKER_BG, fg=self.ACCENT_GREEN, selectbackground=self.ACCENT_BLUE, selectforeground=self.FG, font=("Consolas", 11))
        self.gumpid_listbox.pack(fill=tk.Y, expand=True, pady=4)
        self.gumpid_listbox.bind('<<ListboxSelect>>', self.on_listbox_select)

        # Canvas for image
        self.canvas = tk.Canvas(self, bg=self.DARK_BG, width=512, height=512, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.status = tk.Label(self, text="", anchor='w', bg=self.DARK_BG, fg=self.ACCENT_BLUE, font=("Arial", 10))
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        # Dedicated log area
        self.log_frame = tk.Frame(self, bg=self.DARK_BG)
        self.log_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.log_text = tk.Text(self.log_frame, height=4, bg=self.DARK_BG, fg=self.ACCENT_PURPLE, font=("Consolas", 10), relief=tk.FLAT, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6, pady=2)

    def log_message(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select GumpArt Folder")
        if folder:
            self.folder_var.set(folder)

    def load_folder(self):
        folder = self.folder_var.get()
        if not (os.path.exists(os.path.join(folder, 'gumpidx.mul')) and os.path.exists(os.path.join(folder, 'gumpart.mul'))):
            self.log_message(f"ERROR: gumpidx.mul or gumpart.mul not found in {folder}")
            print(f"ERROR: gumpidx.mul or gumpart.mul not found in {folder}")
            return
        if self.gump_loader:
            self.gump_loader.close()
        print(f"\nLoading gump art from: {folder}")
        self.gump_loader = GumpMulLoader(folder)
        self.current_folder = folder
        self.valid_ids = self.gump_loader.get_valid_ids()
        self.count_label.config(text=f"Total gumps: {self.gump_loader.get_count()} | Valid: {len(self.valid_ids)}")
        self.status.config(text=f"Loaded folder: {folder}")
        # Populate listbox
        self.gumpid_listbox.delete(0, tk.END)
        for gid in self.valid_ids:
            self.gumpid_listbox.insert(tk.END, gid)
        print(f"Available Gump IDs: {self.valid_ids[:10]} ... {self.valid_ids[-10:]}")

    def load_gump_by_id_or_filename(self):
        raw = self.id_entry.get().strip()
        gump_id = None
        # Try direct decimal , exammple =  "25"
        try:
            gump_id = int(raw)
        except Exception:
            pass
        # Try hex (with or without 0x) , exammple =  "0x002F"
        if gump_id is None:
            try:
                if raw.lower().startswith('0x'):
                    gump_id = int(raw, 16)
                elif all(c in '0123456789abcdefABCDEF' for c in raw) and len(raw) <= 6:
                    gump_id = int(raw, 16)
            except Exception:
                pass
        # Try extracting hex from filename-like string , example = "menu_button_start_0x002F"
        if gump_id is None:
            import re
            match = re.search(r'0x([0-9a-fA-F]+)', raw)
            if match:
                try:
                    gump_id = int(match.group(1), 16)
                except Exception:
                    pass
            else:
                match = re.search(r'([0-9a-fA-F]{2,6})', raw)
                if match:
                    try:
                        gump_id = int(match.group(1), 16)
                    except Exception:
                        pass
        if gump_id is None:
            self.log_message("Invalid Input: Please enter a valid Gump ID or filename containing a hex ID.")
            return
        if gump_id not in self.gump_loader.valid_ids:
            self.log_message(f"Not Found: Gump ID {gump_id} not found.")
            return
        self.show_gump(gump_id)

    def show_gump(self, gump_id=None):
        if not self.gump_loader:
            self.log_message("Error: No folder loaded")
            print("ERROR: No gump folder loaded.")
            return
        if gump_id is None:
            try:
                gump_id = int(self.gumpid_var.get())
            except ValueError:
                self.log_message("Error: Invalid gump ID input.")
                print("ERROR: Invalid gump ID input.")
                return
        print(f"Attempting to load Gump ID: {gump_id}")
        img, w, h = self.gump_loader.get_gump(gump_id)
        if img is None:
            self.status.config(text=f"Gump {gump_id} not found or invalid.")
            self.canvas.delete("all")
            self.log_message(f"Gump {gump_id} not found or invalid.")
            print(f"Gump {gump_id} not found or invalid.")
            return
        self.gump_img = img
        # Resize to fit canvas if needed
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        scale = min(canvas_w / w, canvas_h / h, 1.0)
        disp_img = img
        if scale < 1.0:
            disp_img = img.resize((int(w*scale), int(h*scale)), Image.NEAREST)
        self.tk_img = ImageTk.PhotoImage(disp_img)
        self.canvas.delete("all")
        self.canvas.create_image(canvas_w//2, canvas_h//2, anchor=tk.CENTER, image=self.tk_img)
        self.canvas.create_text(10, 10, anchor=tk.NW, text=f"Gump ID: {gump_id}", fill=self.ACCENT_GREEN, font=("Arial", 14, "bold"))
        self.status.config(text=f"Showing gump {gump_id} ({w}x{h})")
        print(f"Displayed Gump ID {gump_id} ({w}x{h})")

    def on_listbox_select(self, event):
        selection = self.gumpid_listbox.curselection()
        if selection:
            idx = self.gumpid_listbox.get(selection[0])
            self.gumpid_var.set(str(idx))
            self.show_gump()

    def on_closing(self):
        if self.gump_loader:
            self.gump_loader.close()
        self.destroy()

if __name__ == "__main__":
    app = GumpViewerApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()