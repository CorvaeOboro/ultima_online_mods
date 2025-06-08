"""
FONT IMPORT MUL EDIT
edit fonts.mul files of ultima online classic 
ui interface to load and view a fonts.mul font as images 
import images to replace specific characters of the font 
batch import images to replace all matching 
batch clear replaces characters of the font with a blank image 
shows stats about the font image size and number of characters 
can save directly to font.mul files 

# Ultima Online Font MUL File Handling Notes
#
# There are two types of MUL files related to fonts:
# 1. ASCII font index files (e.g., fonts.mul):
# 
# 2. UNICODE Font data files (e.g., unifont1.mul, unifont2.mul, unifont3.mul, 1-12):
#    - First 896 bytes (224 * 4) are an offset table for glyphs (little-endian 32-bit integers).
#    - Each offset points to a glyph bitmap within the file.
#    - Used for glyph extraction, editing, and saving.
#
# This tool can distinguish and process both types. See utility functions below for inspection and listing.
"""

import os
import struct
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox

# --- DARK MODE COLORS ---
DARK_BG = "#181818"
DARK_FRAME = "#232323"
DARK_BUTTON = "#2e2e2e"
MUTED_GREEN = "#3a5f3a"
MUTED_BLUE = "#33506d"
MUTED_PURPLE = "#4a3a5f"
LIGHT_TEXT = "#e0e0e0"

# --- FONT.MUL FORMAT CONSTANTS (Classic UO) ---
GLYPH_COUNT = 224  # Classic UO ASCII fonts.mul glyph count (0-223)
HEADER_SIZE = 4 * GLYPH_COUNT  # Offset table: 4 bytes per glyph

class FontMUL:
    """
    Handles reading of UO fonts.mul master index files and font data files.
    - If a master index (fonts.mul), detects all font blocks (nonzero offsets) and loads them as separate fonts.
    - If a font data file (e.g. unifont.mul), loads as a single font.
    - If UOFiddler canonical format, loads all fonts in sequence.
    ---
    UOFIDDLER FONT FORMAT (ASCIIFont.cs):
    - File contains 10 fonts in sequence.
    - For each font:
        - 1 byte: header
        - For each of 224 glyphs:
            - 1 byte: width
            - 1 byte: height
            - 1 byte: unknown/delimiter (stored, not used in rendering)
            - width * height * 2 bytes: pixel data (16bpp ARGB1555, row-major)
              - Each pixel: ushort (little-endian)
              - If pixel == 0: transparent; else: pixel ^ 0x8000 (sets alpha)
    - If width or height is 0, glyph is blank (skipped).
    - No offset table, no RLE, no padding between glyphs.
    - This is different from classic MUL (offset table + RLE + 1bpp).
    - UOFiddler always loads into a canonical 16bpp bitmap array for editing/display, regardless of source format.
    - When saving, UOFiddler writes out this canonical format.
    ---
    CLASSIC MUL FORMAT (LEGACY/SECONDARY):
    - First 896 bytes: offset table (224 * 4, little-endian)
    - Each offset is absolute file position for glyph data (RLE, 1bpp)
    - At each offset: 1 byte width, 1 byte height, then RLE data
    - Offset==0 or width==0/height==0: blank glyph
    ---
    This loader now defaults to UOFiddler format, with legacy/classic loader as fallback.
    """
    def __init__(self, filepath=None):
        self.filepath = filepath
        self.offsets = []  # List of int (file offsets)
        self.glyphs = [None] * GLYPH_COUNT  # List of PIL Images or None
        self._raw_data = None  # For debugging
        if filepath:
            self.load(filepath)

    def debug_print_offset_table(self, filepath=None):
        """
        Print the first 896 bytes (offset table) of a MUL file as both hex and interpreted offsets.
        Shows nonzero offsets and their indices. Heuristic format detection is printed as well.
        """
        if filepath is None:
            filepath = self.filepath
        print(f"[DEBUG] Inspecting offset table: {filepath}")
        with open(filepath, 'rb') as f:
            header = f.read(896)
        offsets = [int.from_bytes(header[i:i+4], 'little') for i in range(0, len(header), 4)]
        print("[DEBUG] First 896 bytes (hex):")
        print(' '.join(f'{b:02X}' for b in header))
        print("[DEBUG] Offset table (as uint32 LE):")
        for i, o in enumerate(offsets):
            print(f"  [{i:03}] 0x{o:08X}")
        nonzero = [(i, o) for i, o in enumerate(offsets) if o != 0]
        print(f"[DEBUG] Nonzero offsets: {len(nonzero)}")
        for idx, off in nonzero:
            print(f"  Index {idx}: Offset 0x{off:08X}")
        # Heuristic detection
        nonzero_count = len(nonzero)
        if nonzero_count < 10:
            print("[DETECT] Likely a master index file (fonts.mul)")
        elif nonzero_count > 100 and all(e <= l for e, l in zip([o for _, o in nonzero], [o for _, o in nonzero][1:])):
            print("[DETECT] Likely a classic font data file (offset table + RLE)")
        else:
            print("[DETECT] Unknown or custom format")

    def debug_print_structure(self):
        """
        Print a summary of the raw file structure for the UOFiddler canonical format.
        - Prints number of fonts, headers, and verifies glyph structure.
        - Dumps glyph dimensions and first few pixel values for each font.
        """
        print("[DEBUG] FontMUL file structure (UOFiddler canonical format):")
        if not hasattr(self, 'fonts') or not self.fonts:
            print("  [ERROR] No fonts loaded.")
            return
        print(f"  Fonts loaded: {len(self.fonts)}")
        for font_idx, glyphs in enumerate(self.fonts):
            print(f"  Font {font_idx}: header={self.headers[font_idx] if hasattr(self, 'headers') else '?'}")
            for glyph_idx, glyph in enumerate(glyphs[:8]):
                if glyph is None:
                    print(f"    Glyph {glyph_idx:03}: BLANK")
                else:
                    px = list(glyph.getdata())[:8]
                    print(f"    Glyph {glyph_idx:03}: size={glyph.size} px0={px}")
            if len(glyphs) > 8:
                print("    ...")
        print("[DEBUG] End of structure dump.")

    def debug_glyph_info(self, font_idx, glyph_idx):
        """Print info for a single glyph in the UOFiddler format."""
        glyph = self.fonts[font_idx][glyph_idx]
        if glyph is None:
            print(f"Font {font_idx} Glyph {glyph_idx}: BLANK")
        else:
            px = list(glyph.getdata())[:8]
            print(f"Font {font_idx} Glyph {glyph_idx}: size={glyph.size} px0={px}")

    def debug_all_glyphs_info(self, font_idx=0):
        """Print info for all glyphs in a single font (default: first font)."""
        for i in range(len(self.fonts[font_idx])):
            self.debug_glyph_info(font_idx, i)

    def debug_verify_roundtrip(self, tmp_path="_debug_roundtrip.mul", visual_diff_folder=None):
        """
        Save and reload the font, then compare all glyphs for pixel-perfect match.
        Optionally export visual diffs for mismatches.
        """
        try:
            self.save(tmp_path)
            reloaded = FontMUL(tmp_path)
            mismatches = []
            for i in range(GLYPH_COUNT):
                orig = self.glyphs[i]
                new = reloaded.glyphs[i]
                if (orig is None) != (new is None):
                    mismatches.append(i)
                elif orig is not None and new is not None:
                    if orig.size != new.size or list(orig.getdata()) != list(new.getdata()):
                        mismatches.append(i)
                        if visual_diff_folder:
                            diff_img = self._diff_glyphs(orig, new)
                            diff_img.save(os.path.join(visual_diff_folder, f"glyph_{i:03}_diff.png"))
            if not mismatches:
                print("[DEBUG] Round-trip save/load: All glyphs match.")
            else:
                print(f"[DEBUG] Round-trip mismatches: {mismatches}")
                if visual_diff_folder:
                    print(f"[DEBUG] Visual diffs saved to {visual_diff_folder}")
        except Exception as e:
            print(f"[DEBUG] Round-trip error: {e}")

    def _diff_glyphs(self, original_glyph_image, reloaded_glyph_image):
        """Return a visual diff image between two glyphs."""
        max_width = max(original_glyph_image.width, reloaded_glyph_image.width)
        max_height = max(original_glyph_image.height, reloaded_glyph_image.height)
        original_glyph_gray = original_glyph_image.convert("L").resize((max_width, max_height))
        reloaded_glyph_gray = reloaded_glyph_image.convert("L").resize((max_width, max_height))
        diff_image = Image.new("RGBA", (max_width, max_height))
        original_pixels = original_glyph_gray.load()
        reloaded_pixels = reloaded_glyph_gray.load()
        diff_pixels = diff_image.load()
        for pixel_y in range(max_height):
            for pixel_x in range(max_width):
                if original_pixels[pixel_x, pixel_y] == reloaded_pixels[pixel_x, pixel_y]:
                    diff_pixels[pixel_x, pixel_y] = (0, 0, 0, 0)
                else:
                    diff_pixels[pixel_x, pixel_y] = (255, 0, 0, 128)  # Red highlight
        return diff_image

    def debug_glyph_statistics(self):
        """Print statistics about all glyphs (blank/nonblank, width/height stats)."""
        glyph_widths = []
        glyph_heights = []
        blank_glyph_count = 0
        for glyph_image in self.glyphs:
            if glyph_image is None:
                blank_glyph_count += 1
            else:
                glyph_widths.append(glyph_image.width)
                glyph_heights.append(glyph_image.height)
        print(f"Total glyphs: {GLYPH_COUNT}")
        print(f"Blank glyphs: {blank_glyph_count}")
        if glyph_widths:
            print(f"Width: min={min(glyph_widths)}, max={max(glyph_widths)}, avg={sum(glyph_widths)//len(glyph_widths)}")
            print(f"Height: min={min(glyph_heights)}, max={max(glyph_heights)}, avg={sum(glyph_heights)//len(glyph_heights)}")
        else:
            print("No nonblank glyphs.")

    @staticmethod
    def debug_batch_regression_test(folder):
        """Run roundtrip test on all font.mul files in a folder."""
        import glob
        results = []
        for path in glob.glob(os.path.join(folder, '*.mul')):
            try:
                f = FontMUL(path)
                print(f"Testing {os.path.basename(path)}...")
                f.debug_verify_roundtrip()
                results.append((path, True))
            except Exception as e:
                print(f"Failed: {e}")
                results.append((path, False))
        print("Batch regression test complete.")
        for path, ok in results:
            print(f"{os.path.basename(path)}: {'PASS' if ok else 'FAIL'}")

    def is_master_index_file(filepath):
        """
        Heuristically determine if the given file is a master font index (e.g., fonts.mul).
        Returns True if the file has mostly zero entries and very few nonzero offsets in the first 896 bytes.
        """
        with open(filepath, 'rb') as f:
            data = f.read(896)
        offsets = [int.from_bytes(data[i:i+4], 'little') for i in range(0, len(data), 4)]
        nonzero_count = sum(1 for o in offsets if o != 0)
        # If less than 10 nonzero entries, likely a master index
        return nonzero_count < 10

    def list_fonts_in_master_index(filepath):
        """
        List font block offsets or indices in a master index file (fonts.mul).
        Returns a list of (index, offset) for all nonzero entries.
        """
        with open(filepath, 'rb') as f:
            data = f.read(896)
        offsets = [int.from_bytes(data[i:i+4], 'little') for i in range(0, len(data), 4)]
        return [(i, o) for i, o in enumerate(offsets) if o != 0]

    def is_font_data_file(filepath):
        """
        Heuristically determine if the given file is a font data file (e.g., unifont.mul).
        Returns True if the offset table (first 896 bytes) contains many nonzero, increasing offsets.
        """
        with open(filepath, 'rb') as f:
            data = f.read(896)
        offsets = [int.from_bytes(data[i:i+4], 'little') for i in range(0, len(data), 4)]
        nonzero_offsets = [o for o in offsets if o != 0]
        # Check if offsets are monotonically increasing and many are nonzero
        return len(nonzero_offsets) > 100 and all(earlier <= later for earlier, later in zip(nonzero_offsets, nonzero_offsets[1:]))

    def load(self, filepath):
        """
        Loads a UO font.mul file, auto-detecting format:
        - Classic MUL: offset table + RLE + 1bpp
        - UOFiddler: sequential 16bpp ARGB1555 bitmaps
        Populates self.glyphs (for UI), and self.fonts if available.
        """
        from PIL import Image
        import struct
        print(f"[DBG] Opening file: {filepath}")
        # Detect format
        with open(filepath, 'rb') as f:
            header = f.read(896)
        offsets = [int.from_bytes(header[i:i+4], 'little') for i in range(0, len(header), 4)]
        nonzero_offsets = [o for o in offsets if o != 0]
        looks_classic = (
            len(offsets) == GLYPH_COUNT and
            len(nonzero_offsets) > 0 and
            all(0 <= o < os.path.getsize(filepath) for o in nonzero_offsets)
        )
        if looks_classic:
            print("[DEBUG] Detected classic MUL format (offset table + RLE)")
            self._load_classic_mul(filepath)
        else:
            print("[DEBUG] Detected UOFiddler canonical format (sequential 16bpp bitmaps)")
            self.fonts = []  # List of fonts, each is a list of 224 PIL Images or None
            self.headers = []
            with open(filepath, 'rb') as font_file:
                font_file_data = font_file.read()
            pos = 0
            file_size = len(font_file_data)
            print(f"[DBG] File size: {file_size} bytes")
            try:
                for font_index in range(10):
                    if pos >= file_size:
                        print(f"[DBG] Reached EOF at font_index={font_index}, pos={pos}")
                        break
                    header = font_file_data[pos]
                    self.headers.append(header)
                    print(f"[DBG] Font {font_index}: header byte=0x{header:02X} at pos={pos}")
                    pos += 1
                    glyphs = []
                    blank_glyphs = 0
                    for glyph_index in range(224):
                        if pos + 3 > file_size:
                            print(f"[DBG] Incomplete glyph header at font {font_index} glyph {glyph_index}, pos={pos}")
                            glyphs.append(None)
                            pos = file_size  # break outer loop
                            continue
                        width = font_file_data[pos]
                        height = font_file_data[pos+1]
                        unk = font_file_data[pos+2]  # delimiter/unknown, stored for completeness
                        pos += 3
                        if width == 0 or height == 0:
                            glyphs.append(None)
                            blank_glyphs += 1
                            if glyph_index < 5 or glyph_index > 218:
                                print(f"[DBG] Font {font_index} Glyph {glyph_index}: BLANK (width=0 or height=0)")
                            continue
                        pixel_count = width * height
                        if pos + pixel_count*2 > file_size:
                            print(f"[DBG] Incomplete glyph pixel data at font {font_index} glyph {glyph_index}, pos={pos}, pixel_count={pixel_count}")
                            glyphs.append(None)
                            pos = file_size
                            continue
                        # Each pixel: 2 bytes, little-endian, ARGB1555
                        pixels = [font_file_data[pos+i*2] | (font_file_data[pos+i*2+1]<<8) for i in range(pixel_count)]
                        pos += pixel_count*2
                        # Print more pixel data and pixel sum for first 3 glyphs of each font
                        if glyph_index < 3 or glyph_index == 65:
                            pixel_sum = sum(pixels)
                            print(f"[DBG] Font {font_index} Glyph {glyph_index}: width={width} height={height} unk=0x{unk:02X} pixels[:16]={pixels[:16]} sum={pixel_sum}")
                        if glyph_index == 65:
                            print(f"[GLYPH-A-RAW] Font {font_index} Glyph 65: All pixel values: {pixels}")
                        # Convert to RGBA for PIL
                        img = Image.new('RGBA', (width, height))
                        data = []
                        for p in pixels:
                            if p == 0:
                                data.append((0,0,0,0))  # transparent
                            else:
                                r = ((p >> 10) & 0x1F) * 255 // 31
                                g = ((p >> 5) & 0x1F) * 255 // 31
                                b = (p & 0x1F) * 255 // 31
                                # Force alpha=255 for any non-black pixel, otherwise alpha=0
                                if (r, g, b) != (0, 0, 0):
                                    a = 255
                                else:
                                    a = 0
                                data.append((r, g, b, a))
                        img.putdata(data)
                        if glyph_index == 65:
                            print(f"[GLYPH-A-RGBA] Font {font_index} Glyph 65: All RGBA tuples: {data}")
                            print(f"[GLYPH-A-IMG] Font {font_index} Glyph 65: First 8 RGBA pixels from PIL image: {list(img.getdata())[:8]}")
                        glyphs.append(img)
                    print(f"[DBG] Font {font_index}: glyphs loaded={len(glyphs)}, blank glyphs={blank_glyphs}")
                    self.fonts.append(glyphs)
                    # Debug: print type and repr of first 8 glyphs in this font
                    for dbg_idx, dbg_glyph in enumerate(glyphs[:8]):
                        print(f"[DBG-GLYPH] Font {font_index} Glyph {dbg_idx}: type={type(dbg_glyph)}, repr={repr(dbg_glyph)}")
                print(f"[DBG] Total fonts loaded: {len(self.fonts)}")
                # Also print glyph 'A' (index 65) image mode and size for the first font
                if self.fonts and len(self.fonts[0]) > 65:
                    glyph_a = self.fonts[0][65]
                    if glyph_a is not None:
                        print(f"[GLYPH-A-IMG] Font 0 Glyph 65: PIL image mode: {glyph_a.mode}, size: {glyph_a.size}")
                        print(f"[GLYPH-A-IMG] Font 0 Glyph 65: First 8 RGBA pixels: {list(glyph_a.getdata())[:8]}")
                    else:
                        print(f"[GLYPH-A-IMG] Font 0 Glyph 65: None")
                # For UI compatibility, set self.glyphs to first font
                self.glyphs = self.fonts[0] if self.fonts else [None]*GLYPH_COUNT
            except Exception as e:
                print(f"[ERROR] Failed to load UOFiddler font.mul: {e}")
                self.fonts = []
                self.headers = []
                self.glyphs = [None]*GLYPH_COUNT


    # Classic loader can be kept as a secondary method for legacy files
    def _load_classic_mul(self, filepath):
        """
        Classic loader: offset table + RLE + 1bpp format
        Populates self.glyphs with PIL RGBA images or None.
        """
        from PIL import Image
        import struct
        self.glyphs = [None]*GLYPH_COUNT
        with open(filepath, 'rb') as f:
            data = f.read()
        if len(data) < 896:
            print("[ERROR] File too small to be a classic font.mul")
            return
        offsets = [int.from_bytes(data[i*4:(i+1)*4], 'little') for i in range(GLYPH_COUNT)]
        for idx, offset in enumerate(offsets):
            if offset == 0 or offset >= len(data):
                self.glyphs[idx] = None
                continue
            # Read width, height
            width = data[offset]
            height = data[offset+1]
            if width == 0 or height == 0:
                self.glyphs[idx] = None
                continue
            # RLE data starts at offset+2
            rle_data = bytearray()
            pos = offset + 2
            row = 0
            while row < height and pos < len(data):
                start_pos = pos
                while pos < len(data):
                    runlen = data[pos]
                    pos += 1
                    if runlen == 0:
                        break
                    if pos >= len(data):
                        break
                    pixelval = data[pos]
                    pos += 1
                    rle_data.extend([runlen, pixelval])
                rle_data.append(0)  # End of row
                row += 1
            img = self._decode_glyph_rle(width, height, rle_data)
            self.glyphs[idx] = img

    def _load_classic_font_block(self, data, block_offset):
        """
        Loads a classic font block (starting at block_offset) as a font (224 glyphs).
        Returns a list of PIL Images or None.
        """
        glyphs = [None]*GLYPH_COUNT
        offsets = [int.from_bytes(data[block_offset+i*4:block_offset+(i+1)*4], 'little') for i in range(GLYPH_COUNT)]
        for idx, offset in enumerate(offsets):
            if offset == 0 or offset >= len(data):
                glyphs[idx] = None
                continue
            width = data[offset]
            height = data[offset+1]
            if width == 0 or height == 0:
                glyphs[idx] = None
                continue
            rle_data = bytearray()
            pos = offset + 2
            row = 0
            while row < height and pos < len(data):
                while pos < len(data):
                    runlen = data[pos]
                    pos += 1
                    if runlen == 0:
                        break
                    if pos >= len(data):
                        break
                    pixelval = data[pos]
                    pos += 1
                    rle_data.extend([runlen, pixelval])
                rle_data.append(0)
                row += 1
            img = self._decode_glyph_rle(width, height, rle_data)
            glyphs[idx] = img
        return glyphs


    def _decode_glyph_rle(self, glyph_width, glyph_height, glyph_rle_data):
        """
        Decodes UO font.mul RLE glyph to a PIL Image.
        Each row: [runlen, pixelval] ... (0 ends row)
        pixelval: 0=transparent, 1=white
        """
        glyph_image = Image.new('L', (glyph_width, glyph_height), color=0)
        glyph_pixels = glyph_image.load()
        rle_position = 0
        for glyph_row_index in range(glyph_height):
            glyph_column_index = 0
            while rle_position < len(glyph_rle_data):
                run_length = glyph_rle_data[rle_position]
                if run_length == 0:
                    rle_position += 1
                    break
                pixel_value = glyph_rle_data[rle_position+1]
                for run_pixel_offset in range(run_length):
                    if glyph_column_index < glyph_width:
                        glyph_pixels[glyph_column_index, glyph_row_index] = 255 if pixel_value else 0
                        glyph_column_index += 1
                rle_position += 2
        return glyph_image.convert('RGBA')

    def get_glyph(self, char_code):
        if 0 <= char_code < GLYPH_COUNT:
            return self.glyphs[char_code]
        return None

    def import_glyph(self, char_code, image_path):
        img = Image.open(image_path).convert('RGBA')
        self.set_glyph(char_code, img)

    def export_glyph(self, char_code, folder):
        img = self.get_glyph(char_code)
        if img:
            img.save(os.path.join(folder, f"{char_code}.png"))

    def batch_import(self, folder):
        for fname in os.listdir(folder):
            if not fname.lower().endswith('.png'):
                continue
            try:
                code = int(os.path.splitext(fname)[0])
                if 0 <= code < GLYPH_COUNT:
                    img = Image.open(os.path.join(folder, fname)).convert('RGBA')
                    self.set_glyph(code, img)
            except Exception:
                continue

    def batch_export(self, folder):
        os.makedirs(folder, exist_ok=True)
        for idx, img in enumerate(self.glyphs):
            if img:
                img.save(os.path.join(folder, f"{idx}.png"))

    def batch_clear(self):
        for i in range(GLYPH_COUNT):
            self.set_glyph(i, None)

    def clear_glyph(self, char_code):
        self.set_glyph(char_code, None)

    def set_glyph(self, char_code, img):
        self.glyphs[char_code] = img

    def save(self, filepath):
        # Write a valid classic UO font.mul file with RLE encoding
        offsets = [0] * GLYPH_COUNT
        glyph_datas = []
        pos = HEADER_SIZE
        for idx, img in enumerate(self.glyphs):
            if img is None:
                offsets[idx] = 0
                glyph_datas.append(b"")
                continue
            # Ensure grayscale 8-bit, threshold to 1-bit
            img_gray = img.convert("L")
            width, height = img_gray.size
            px = img_gray.load()
            rle = bytearray()
            for y in range(height):
                x = 0
                while x < width:
                    # Find next run
                    val = 1 if px[x, y] > 127 else 0
                    runlen = 1
                    while x + runlen < width and (1 if px[x + runlen, y] > 127 else 0) == val and runlen < 255:
                        runlen += 1
                    rle.append(runlen)
                    rle.append(val)
                    x += runlen
                rle.append(0)  # End of row
            data = bytes([width, height]) + rle
            offsets[idx] = pos
            glyph_datas.append(data)
            pos += len(data)
        # Write file
        with open(filepath, 'wb') as f:
            # Offset table
            f.write(struct.pack('<' + 'I'*GLYPH_COUNT, *offsets))
            # Glyph data
            for data in glyph_datas:
                if data:
                    f.write(data)

    def get_stats(self):
        num_nonblank = sum(1 for g in self.glyphs if g)
        avg_size = (sum(g.size[0]*g.size[1] for g in self.glyphs if g) // max(1, num_nonblank)) if num_nonblank else 0
        return {
            'glyphs': GLYPH_COUNT,
            'nonblank': num_nonblank,
            'avg_size': avg_size
        }

# --- GUI ---
class FontMulEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ultima Online Font.mul Editor")
        self.geometry("1100x700")
        self.configure(bg=DARK_BG)
        self.fontmul = None
        self.selected_code = 65  # Default to 'A'
        self.selected_font = 0
        self._build_ui()

    def open_font(self):
        filepath = filedialog.askopenfilename(
            title="Open Font MUL File",
            filetypes=[("MUL files", "*.mul"), ("All files", "*.*")]
        )
        if filepath:
            try:
                self.fontmul = FontMUL(filepath)
                self.selected_code = 65
                self.selected_font = 0
                # Rebuild font selector dropdown
                font_count = len(self.fontmul.fonts) if self.fontmul and hasattr(self.fontmul, 'fonts') else 1
                print(f"[DBG] Rebuilding font dropdown with {font_count} sets")
                menu = self.font_selector['menu']
                menu.delete(0, 'end')
                for i in range(font_count):
                    menu.add_command(label=str(i), command=lambda idx=i: self.font_selector_var.set(idx))
                self.font_selector_var.set(0)
                self.glyphs = self.fontmul.fonts[0] if font_count > 0 else [None]*224
                self._refresh_glyph_grid()
                print(f"Font Loaded: {filepath}")
            except Exception as e:
                print(f"Failed to load font file: {e}")


    def _build_ui(self):
        # Top Frame
        top = tk.Frame(self, bg=DARK_FRAME)
        top.pack(fill=tk.X, padx=8, pady=8)
        btn_open = tk.Button(top, text="Open font.mul", bg=MUTED_BLUE, fg=LIGHT_TEXT)
        btn_open.pack(side=tk.LEFT, padx=4)
        btn_open.config(command=self.open_font)
        btn_open_test = tk.Button(top, text="Open Test fonts.mul", bg=MUTED_BLUE, fg=LIGHT_TEXT)
        btn_open_test.pack(side=tk.LEFT, padx=4)
        btn_open_test.config(command=self.open_test_fonts_mul)
        # Font selector
        self.font_selector_var = tk.IntVar(value=self.selected_font)
        # Font selector will be rebuilt after loading a font file
        self.font_selector_var = tk.IntVar(value=self.selected_font)
        self.font_selector = tk.OptionMenu(top, self.font_selector_var, 0)
        self.font_selector.config(bg=DARK_BUTTON, fg=LIGHT_TEXT, width=10)
        self.font_selector.pack(side=tk.LEFT, padx=8)
        self.font_selector_var.trace_add('write', lambda *args: self.on_select_font(self.font_selector_var.get()))
        tk.Button(top, text="Save font.mul", command=self.save_font, bg=MUTED_GREEN, fg=LIGHT_TEXT).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Import Glyph", command=self.import_glyph_dialog, bg=MUTED_GREEN, fg=LIGHT_TEXT).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Export Glyph", command=self.export_glyph_dialog, bg=MUTED_PURPLE, fg=LIGHT_TEXT).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Clear Glyph", command=self.clear_glyph_dialog, bg=DARK_BUTTON, fg=LIGHT_TEXT).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Batch Import", command=self.batch_import_dialog, bg=MUTED_GREEN, fg=LIGHT_TEXT).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Batch Export", command=self.batch_export_dialog, bg=MUTED_PURPLE, fg=LIGHT_TEXT).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Batch Clear", command=self.batch_clear_dialog, bg=DARK_BUTTON, fg=LIGHT_TEXT).pack(side=tk.LEFT, padx=4)
        # Debug menu
        debug_menu = tk.Menubutton(top, text="Debug", bg=DARK_BUTTON, fg=LIGHT_TEXT, relief=tk.RAISED)
        debug_menu.menu = tk.Menu(debug_menu, tearoff=0, bg=DARK_BG, fg=LIGHT_TEXT)
        debug_menu["menu"] = debug_menu.menu
        debug_menu.menu.add_command(label="Print Offset Table", command=self.debug_print_offsets)
        debug_menu.menu.add_command(label="Print All Glyph Info", command=self.debug_print_glyphs)
        debug_menu.menu.add_command(label="Print Stats", command=self.debug_print_stats)
        debug_menu.menu.add_command(label="Verify Roundtrip", command=self.debug_verify_roundtrip)
        debug_menu.menu.add_command(label="Roundtrip Visual Diff", command=self.debug_roundtrip_visual_diff)
        debug_menu.menu.add_command(label="Batch Regression Test", command=self.debug_batch_regression_test)
        debug_menu.pack(side=tk.LEFT, padx=8)
        # Stats label
        self.stats_var = tk.StringVar()
        stats_label = tk.Label(top, textvariable=self.stats_var, bg=DARK_FRAME, fg=LIGHT_TEXT, font=("Arial", 10))
        stats_label.pack(side=tk.LEFT, padx=12)
        # Glyph grid and preview
        self.glyph_grid_frame = tk.Frame(self, bg=DARK_BG)
        self.glyph_grid_frame.pack(side=tk.LEFT, padx=4, pady=4, fill=tk.BOTH, expand=True)
        self.glyph_grid_cells = []
        self.max_glyph_width = 32
        self.max_glyph_height = 32
        self._build_glyph_grid()  # Build the grid structure ONCE
        self.canvas = tk.Canvas(self, width=64, height=64, bg=DARK_BG, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, padx=16, pady=4)
        debug_menu.menu.add_command(label="Batch Regression Test...", command=self.debug_batch_regression_test)
        debug_menu.pack(side=tk.LEFT, padx=4)
        self.stats_var = tk.StringVar()
        tk.Label(top, textvariable=self.stats_var, bg=DARK_FRAME, fg=LIGHT_TEXT).pack(side=tk.LEFT, padx=16)

        # Main Frame
        main = tk.Frame(self, bg=DARK_BG)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        # (No duplicate grid or cell creation here)

    def on_select_glyph(self, glyph_idx):
        self.selected_code = glyph_idx
        self._highlight_glyph_grid(glyph_idx)
        self.show_glyph(glyph_idx)  # Only update preview; do NOT refresh grid

    def on_select_font(self, font_idx):
        print(f"[DBG] on_select_font called with font_idx={font_idx}")
        try:
            idx = int(font_idx)
        except Exception:
            idx = 0
        self.selected_font = idx
        print(f"[DBG] Switched to font set {idx}")
        if self.fontmul and hasattr(self.fontmul, 'fonts') and 0 <= idx < len(self.fontmul.fonts):
            self.glyphs = self.fontmul.fonts[idx]
        else:
            self.glyphs = [None]*224
        self._compute_max_glyph_size()  # Update max glyph size on font switch
        self._refresh_glyph_grid()
        self.show_glyph(self.selected_code)

    def show_glyph(self, code):
        self.canvas.delete("all")
        if not self.fontmul:
            return
        glyphs = self.fontmul.fonts[self.selected_font] if self.fontmul and hasattr(self.fontmul, 'fonts') and len(self.fontmul.fonts) > self.selected_font else [None]*GLYPH_COUNT
        glyph_img = glyphs[code]
        canvas_w = max(64, self.max_glyph_width)
        canvas_h = max(64, self.max_glyph_height)
        self.canvas.config(width=canvas_w, height=canvas_h)
        if glyph_img:
            w, h = glyph_img.size
            x0 = (canvas_w - w) // 2
            y0 = (canvas_h - h) // 2
            self.tkimg = ImageTk.PhotoImage(glyph_img.resize((w, h), Image.NEAREST))
            self.canvas.create_image(x0, y0, anchor=tk.NW, image=self.tkimg)
        else:
            self.canvas.create_text(canvas_w // 2, canvas_h // 2, text="(blank)", fill=LIGHT_TEXT)
        self._highlight_glyph_grid(code)

    def import_glyph_dialog(self):
        if not self.fontmul:
            return
        path = filedialog.askopenfilename(filetypes=[("PNG Image", "*.png")])
        if not path:
            return
        try:
            self.fontmul.import_glyph(self.selected_code, path)
            self.stats_var.set(self._stats_text())
            self.show_glyph(self.selected_code)
        except Exception as e:
            print(f"[ERROR] Failed to import glyph:\n{e}")

    def export_glyph_dialog(self):
        if not self.fontmul:
            return
        folder = filedialog.askdirectory(title="Export Glyph To Folder")
        if not folder:
            return
        try:
            self.fontmul.export_glyph(self.selected_code, folder)
        except Exception as e:
            print(f"[ERROR] Failed to export glyph:\n{e}")

    def clear_glyph_dialog(self):
        if not self.fontmul:
            return
        if messagebox.askyesno("Clear Glyph", "Clear this glyph? This cannot be undone."):
            self.fontmul.clear_glyph(self.selected_code)
            self.stats_var.set(self._stats_text())
            self.show_glyph(self.selected_code)

    def batch_import_dialog(self):
        if not self.fontmul:
            return
        folder = filedialog.askdirectory(title="Batch Import Folder")
        if not folder:
            return
        try:
            self.fontmul.batch_import(folder)
            self.stats_var.set(self._stats_text())
            self.show_glyph(self.selected_code)
        except Exception as e:
            print(f"[ERROR] Batch import failed:\n{e}")

    def batch_export_dialog(self):
        if not self.fontmul:
            return
        folder = filedialog.askdirectory(title="Batch Export Folder")
        if not folder:
            return
        try:
            self.fontmul.batch_export(folder)
        except Exception as e:
            print(f"[ERROR] Batch export failed:\n{e}")

    def batch_clear_dialog(self):
        if not self.fontmul:
            return
        if messagebox.askyesno("Batch Clear", "Clear ALL glyphs? This cannot be undone."):
            self.fontmul.batch_clear()
            self.stats_var.set(self._stats_text())
            self.show_glyph(self.selected_code)

    def save_font(self):
        if not self.fontmul:
            return
        path = filedialog.asksaveasfilename(title="Save font.mul", defaultextension=".mul", filetypes=[("UO Font.mul", "*.mul")])
        if not path:
            return
        try:
            self.fontmul.save(path)
        except NotImplementedError as e:
            print(f"[INFO] Not Implemented: {e}")
        except Exception as e:
            print(f"[ERROR] Save failed:\n{e}")

    def debug_print_offsets(self):
        if self.fontmul:
            import io, sys
            buf = io.StringIO()
            sys_stdout = sys.stdout
            sys.stdout = buf
            # Use the new debug_print_offset_table for detailed output
            self.fontmul.debug_print_offset_table()
            sys.stdout = sys_stdout
            messagebox.showinfo("Offset Table (Detailed)", buf.getvalue())

    def debug_print_glyphs(self):
        if self.fontmul:
            import io, sys
            buf = io.StringIO()
            sys_stdout = sys.stdout
            sys.stdout = buf
            self.fontmul.debug_all_glyphs_info()
            sys.stdout = sys_stdout
            messagebox.showinfo("All Glyph Info", buf.getvalue())

    def debug_print_stats(self):
        if self.fontmul:
            import io, sys
            buf = io.StringIO()
            sys_stdout = sys.stdout
            sys.stdout = buf
            self.fontmul.debug_glyph_statistics()
            sys.stdout = sys_stdout
            messagebox.showinfo("Glyph Statistics", buf.getvalue())

    def debug_verify_roundtrip(self):
        if self.fontmul:
            import io, sys
            buf = io.StringIO()
            sys_stdout = sys.stdout
            sys.stdout = buf
            self.fontmul.debug_verify_roundtrip()
            sys.stdout = sys_stdout
            messagebox.showinfo("Roundtrip Verification", buf.getvalue())

    def debug_roundtrip_visual_diff(self):
        if self.fontmul:
            from tkinter import simpledialog
            folder = filedialog.askdirectory(title="Select Folder to Save Visual Diffs")
            if not folder:
                return
            import io, sys
            buf = io.StringIO()
            sys_stdout = sys.stdout
            sys.stdout = buf
            self.fontmul.debug_verify_roundtrip(visual_diff_folder=folder)
            sys.stdout = sys_stdout
            print(buf.getvalue())

    def debug_batch_regression_test(self):
        from tkinter import simpledialog
        folder = filedialog.askdirectory(title="Select Folder of font.mul Files")
        if not folder:
            return
        import io, sys
        buf = io.StringIO()
        sys_stdout = sys.stdout
        sys.stdout = buf
        FontMUL.debug_batch_regression_test(folder)
        sys.stdout = sys_stdout
        print(buf.getvalue())

    def _build_glyph_grid(self):
        # Remove any previous grid
        for widget in self.glyph_grid_frame.winfo_children():
            widget.destroy()
        self.glyph_grid_cells.clear()
        self._compute_max_glyph_size()  # Always update max size when building grid
        # Rearranged grid: Capitals (A-Z), Lowercase (a-z), Numbers (0-9), Specials, Rest
        capitals = list(range(65-32, 91-32))   # 'A'-'Z' (indices 33 to 58)
        lowercase = list(range(97-32, 123-32)) # 'a'-'z' (indices 65 to 90)
        numbers = list(range(48-32, 58-32))    # '0'-'9' (indices 16 to 25)
        specials = [i for i in range(0, 95) if (i+32) >= 32 and (i+32) < 127 and not (i in capitals or i in lowercase or i in numbers)]
        rest = [i for i in range(0, GLYPH_COUNT) if i not in capitals + lowercase + numbers + specials]

        # Each row has 26 columns for alignment
        row_len = 26
        def pad_row(lst):
            return lst + [None]*(row_len - len(lst))

        grid_rows = []
        grid_rows.append(pad_row(capitals))   # Capitals row
        grid_rows.append(pad_row(lowercase))  # Lowercase row
        grid_rows.append(pad_row(numbers))    # Numbers row (will be left-aligned)

        # Specials and rest, chunked into rows of 26
        specials_rows = [specials[i:i+row_len] for i in range(0, len(specials), row_len)]
        rest_rows = [rest[i:i+row_len] for i in range(0, len(rest), row_len)]
        grid_rows.extend([pad_row(row) for row in specials_rows])
        grid_rows.extend([pad_row(row) for row in rest_rows])

        # Flatten grid_rows to mapping and build grid
        self.glyph_grid_cells.clear()
        self.glyph_grid_mapping = []
        for r, row in enumerate(grid_rows):
            for c, glyph_idx in enumerate(row):
                self.glyph_grid_mapping.append(glyph_idx)
                frame = tk.Frame(self.glyph_grid_frame, width=48, height=72, bg=DARK_BUTTON, highlightbackground=MUTED_BLUE, highlightthickness=1)
                frame.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")
                frame.grid_propagate(False)
                # Number label
                lbl_num = tk.Label(frame, text=f"{glyph_idx if glyph_idx is not None else '---'}", bg=DARK_BUTTON, fg=LIGHT_TEXT, font=("Arial", 8, "bold"))
                lbl_num.pack(side=tk.TOP, pady=(2,0))
                # Glyph image
                canvas_w = max(32, self.max_glyph_width)
                canvas_h = max(32, self.max_glyph_height)
                canvas = tk.Canvas(frame, width=canvas_w, height=canvas_h, bg=DARK_BG, highlightthickness=0)
                canvas.pack(side=tk.TOP, pady=2)
                # Char label
                char = chr(glyph_idx + 32) if glyph_idx is not None and 0 <= glyph_idx + 32 < 127 else ''
                lbl_char = tk.Label(frame, text=char, bg=DARK_BUTTON, fg=LIGHT_TEXT, font=("Arial", 8))
                lbl_char.pack(side=tk.TOP, pady=(0,2))
                # Click binding
                def make_callback(glyph_idx=glyph_idx):
                    return lambda e: self.on_select_glyph(glyph_idx)
                frame.bind("<Button-1>", make_callback())
                canvas.bind("<Button-1>", make_callback())
                lbl_num.bind("<Button-1>", make_callback())
                lbl_char.bind("<Button-1>", make_callback())
                self.glyph_grid_cells.append((frame, canvas, lbl_num, lbl_char))
        self._refresh_glyph_grid()

    def open_test_fonts_mul(self):
        # Quick load for /Z_Tools/test/fonts.mul
        test_path = os.path.join(os.path.dirname(__file__), "test", "fonts.mul")
        self.open_font(default_path=test_path)


    def _refresh_glyph_grid(self):
        if not self.fontmul:
            for idx, (frame, canvas, lbl_num, lbl_char) in enumerate(self.glyph_grid_cells):
                canvas.delete("all")
                frame.config(bg="#222222")
                canvas.create_rectangle(0, 0, 32, 32, fill=DARK_BG, outline=MUTED_BLUE)
                if idx == 65:
                    print(f"[UI-DBG] === GLYPH A (65) CELL UPDATE (NO FONT) ===")
                    print(f"[UI-DBG] Glyph 65 display: BLANK/None (no font loaded)")
            print("[UI-DBG] Glyph grid set to blank (no font loaded)")
            return
        # Use glyphs from selected font
        glyphs = self.fontmul.fonts[self.selected_font] if self.fontmul and hasattr(self.fontmul, 'fonts') and len(self.fontmul.fonts) > self.selected_font else [None]*GLYPH_COUNT
        self._glyph_thumbnails = []  # Prevent garbage collection of PhotoImage objects
        nonblank_count = 0
        for cell_idx, (frame, canvas, lbl_num, lbl_char) in enumerate(self.glyph_grid_cells):
            glyph_idx = self.glyph_grid_mapping[cell_idx]
            glyph_img = glyphs[glyph_idx] if glyph_idx is not None else None
            canvas.delete("all")
            # Always print update info for every cell, with extra for glyph 65
            print(f"[UI-DBG] Updating cell {cell_idx} (glyph {glyph_idx})...")
            if glyph_img is not None:
                frame.config(bg="#000000")
                w, h = glyph_img.size
                print(f"[UI-DBG] Glyph {glyph_idx}: original mode={glyph_img.mode}")
                glyph_img_rgba = glyph_img.convert('RGBA') if glyph_img.mode != 'RGBA' else glyph_img
                print(f"[UI-DBG] Glyph {glyph_idx}: after convert mode={glyph_img_rgba.mode}")
                scale = min(32/w if w else 1, 32/h if h else 1, 1)
                sw, sh = max(1, int(w*scale)), max(1, int(h*scale))
                img = glyph_img_rgba.resize((sw, sh), Image.NEAREST)
                rgba = list(img.getdata())[:8]
                alpha_sum = sum(px[3] for px in img.getdata())
                print(f"[UI-DBG] Glyph {glyph_idx}: size={img.size} mode={img.mode} first8={rgba} alpha_sum={alpha_sum}")
                if alpha_sum == 0:
                    print(f"[UI-DBG] WARNING: Glyph {glyph_idx} is fully transparent!")
                tkimg = ImageTk.PhotoImage(img)
                self._glyph_thumbnails.append(tkimg)
                canvas.image = tkimg
                canvas.create_image((32-sw)//2, (32-sh)//2, anchor=tk.NW, image=tkimg)
                if alpha_sum == 0:
                    # Draw a solid black square for blank/fully transparent glyphs
                    canvas.create_rectangle(0, 0, 32, 32, fill='black', outline='gray')
                if any(px[3] > 0 for px in img.getdata()):
                    nonblank_count += 1
                if glyph_idx == 65:
                    print(f"[UI-DBG] === GLYPH A (65) CELL UPDATE ===")
                    print(f"[UI-DBG] Glyph 65 display: size={img.size}, mode={img.mode}, first8={list(img.getdata())[:8]}, alpha_sum={sum(px[3] for px in img.getdata())}")
            else:
                frame.config(bg="#000000")
                canvas.create_rectangle(0, 0, 32, 32, fill=DARK_BG, outline=MUTED_BLUE)
                if glyph_idx == 65:
                    print(f"[UI-DBG] === GLYPH A (65) CELL UPDATE ===")
                    print(f"[UI-DBG] Glyph 65 display: BLANK/None")
        print(f"[UI-DBG] Refreshed glyph grid: {nonblank_count} non-blank glyphs displayed out of {GLYPH_COUNT}")
        self._highlight_glyph_grid(self.selected_code)
        self.update_idletasks()
        print("[UI-DBG] Glyph grid UI update complete.")

    def _highlight_glyph_grid(self, glyph_idx):
        for cell_idx, (frame, canvas, lbl_num, lbl_char) in enumerate(self.glyph_grid_cells):
            mapped_glyph_idx = self.glyph_grid_mapping[cell_idx]
            if mapped_glyph_idx == glyph_idx:
                frame.config(highlightbackground=MUTED_PURPLE, highlightthickness=2)
            else:
                frame.config(highlightbackground=MUTED_BLUE, highlightthickness=1)


    def _stats_text(self):
        if not self.fontmul:
            return "No font loaded"
        stats = self.fontmul.get_stats()
        return f"Glyphs: {stats['glyphs']}  Non-blank: {stats['nonblank']}  Avg Size: {stats['avg_size']} px^2"

    def debug_print_offset_table(self):
        if self.fontmul:
            import io, sys
            buf = io.StringIO()
            sys_stdout = sys.stdout
            sys.stdout = buf
            self.fontmul.debug_print_offset_table()
            sys.stdout = sys_stdout
            print(buf.getvalue())

    def debug_print_glyphs(self):
        if self.fontmul:
            import io, sys
            buf = io.StringIO()
            sys_stdout = sys.stdout
            sys.stdout = buf
            self.fontmul.debug_all_glyphs_info()
            sys.stdout = sys_stdout
            print(buf.getvalue())

    def debug_print_stats(self):
        if self.fontmul:
            import io, sys
            buf = io.StringIO()
            sys_stdout = sys.stdout
            sys.stdout = buf
            self.fontmul.debug_glyph_statistics()
            sys.stdout = sys_stdout
            print(buf.getvalue())

    def debug_verify_roundtrip(self):
        if self.fontmul:
            import io, sys
            buf = io.StringIO()
            sys_stdout = sys.stdout
            sys.stdout = buf
            self.fontmul.debug_verify_roundtrip()
            sys.stdout = sys_stdout
            print(buf.getvalue())

    def debug_roundtrip_visual_diff(self):
        if self.fontmul:
            from tkinter import filedialog
            folder = filedialog.askdirectory(title="Select Folder to Save Visual Diffs")
            if not folder:
                return
            import io, sys
            buf = io.StringIO()
            sys_stdout = sys.stdout
            sys.stdout = buf
            self.fontmul.debug_verify_roundtrip(visual_diff_folder=folder)
            sys.stdout = sys_stdout
            print(buf.getvalue())

    def debug_batch_regression_test(self):
        from tkinter import filedialog
        folder = filedialog.askdirectory(title="Select Folder of font.mul Files")
        if not folder:
            return
        import io, sys
        buf = io.StringIO()
        sys_stdout = sys.stdout
        sys.stdout = buf
        FontMUL.debug_batch_regression_test(folder)
        sys.stdout = sys_stdout
        print(buf.getvalue())

    def open_test_fonts_mul(self):
        # Quick load for /Z_Tools/test/fonts.mul
        import os
        test_path = os.path.join(os.path.dirname(__file__), "test", "fonts.mul")
        self.open_font(default_path=test_path)

    def _compute_max_glyph_size(self):
        self.max_glyph_width = 32
        self.max_glyph_height = 32
        if self.fontmul and hasattr(self.fontmul, 'fonts') and len(self.fontmul.fonts) > self.selected_font:
            for img in self.fontmul.fonts[self.selected_font]:
                if img is not None:
                    w, h = img.size
                    if w > self.max_glyph_width:
                        self.max_glyph_width = w
                    if h > self.max_glyph_height:
                        self.max_glyph_height = h

if __name__ == "__main__":
    # Launch the main GUI only
    app = FontMulEditorApp()
    app.mainloop()