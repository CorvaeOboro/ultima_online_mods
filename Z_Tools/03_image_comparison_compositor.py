"""
Image Comparison Compositor
a UI for comparing and compositing the original images with the altered images for ultima online classic
utilizes the hexadecimal id to match the original and altered images as a suffix (0x1234.png and item_apple_0x1234.bmp)
a canvas to arrange the images in rows to group for visualization , such as weapon type , or food group
"""
import os
import re
import sys
import json
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox

# Configuration for paddings (in pixels)
VERTICAL_PADDING = 10
HORIZONTAL_PADDING = 20

# UI Colors
DARK_GRAY = "#1E1E1E"
DARKER_GRAY = "#252526"
LIGHTER_GRAY = "#333333"
BUTTON_BLACK = "#000000"
WHITE = "#FFFFFF"
ROW_COLORS = ["#3C4C7C", "#4C3C7C", "#7C3C4C", "#3C7C4C"]  # Row highlight colors

def get_content_bbox(image):
    """
    Compute the bounding box of the non-blank area of an image.
    Blank pixels are those that are either fully transparent or pure black (RGB (0,0,0)).
    Returns a tuple (left, upper, right, lower).
    """
    im = image.convert("RGBA")
    data = np.array(im)
    mask = ~((data[:, :, 3] == 0) | ((data[:, :, 0] == 0) & (data[:, :, 1] == 0) & (data[:, :, 2] == 0)))
    coords = np.argwhere(mask)
    if coords.size == 0:
        return (0, 0, image.width, image.height)
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0) + 1  # include last pixel
    return (x0, y0, x1, y1)

def extract_hex_id(filename):
    """
    Extracts a hexadecimal ID from a filename.
    Searches for a pattern like '0x' followed by hex digits.
    Returns an integer value if found, or None.
    """
    match = re.search(r'0x([0-9a-fA-F]+)', filename)
    if match:
        hex_str = match.group(1)
        try:
            return int(hex_str, 16)
        except ValueError:
            return None
    return None

def find_matching_triplets(target_folder, custom_before_folder=None, alternate_before_folder=None):
    """
    Searches for AFTER images in the target folder (BMP or PNG files with a hex id)
    and finds matching BEFORE images from either:
      - a custom BEFORE folder (if provided) OR
      - a subfolder named "backup" or "original" in the target folder.
    If an alternate_before_folder is provided, matching ALTERNATE BEFORE images are also found.
    
    Returns a tuple:
      (triplets, stats)
      where triplets is a list of (before_path, alternate_before_path, after_path)
      and stats is a dict containing counts of potential matches
    """
    triplets = []
    stats = {
        "after_count": 0,
        "before_count": 0,
        "matched_count": 0
    }
    
    # Determine BEFORE folder:
    if custom_before_folder and os.path.isdir(custom_before_folder):
        before_folder = custom_before_folder
        print(f"DEBUG: Using custom BEFORE folder: {before_folder}")
    else:
        before_folder = None
        for folder_name in ["backup", "original"]:
            potential_path = os.path.join(target_folder, folder_name)
            if os.path.isdir(potential_path):
                before_folder = potential_path
                print(f"DEBUG: Found BEFORE folder (backup/original): {before_folder}")
                break
        if before_folder is None:
            print("DEBUG: No BEFORE folder (custom or backup/original) found.")
    
    # List AFTER images in target folder (BMP or PNG with hex id)
    after_files = [
        f for f in os.listdir(target_folder)
        if os.path.isfile(os.path.join(target_folder, f))
           and (f.lower().endswith(".png") or f.lower().endswith(".bmp"))
           and re.search(r'0x[0-9a-fA-F]+', f)
    ]
    stats["after_count"] = len(after_files)
    print("DEBUG: Potential AFTER images found in target folder:")
    for af in after_files:
        print("  " + af)
    
    # Build dictionary for BEFORE images from before_folder (if available)
    before_dict = {}
    if before_folder:
        before_files = [
            f for f in os.listdir(before_folder)
            if os.path.isfile(os.path.join(before_folder, f))
               and (f.lower().endswith(".png") or f.lower().endswith(".bmp"))
               and re.search(r'0x[0-9a-fA-F]+', f)
        ]
        stats["before_count"] = len(before_files)
        print("DEBUG: Potential BEFORE images found in BEFORE folder:")
        for bf in before_files:
            print("  " + bf)
        for bf in before_files:
            hex_id = extract_hex_id(bf)
            if hex_id is not None:
                current = before_dict.get(hex_id)
                if current:
                    if current.lower().endswith(".bmp") and bf.lower().endswith(".png"):
                        before_dict[hex_id] = bf
                else:
                    before_dict[hex_id] = bf
    else:
        print("DEBUG: No BEFORE folder to search in.")
    
    # Build dictionary for ALTERNATE BEFORE images (if provided)
    alternate_before_dict = {}
    if alternate_before_folder and os.path.isdir(alternate_before_folder):
        alternate_files = [
            f for f in os.listdir(alternate_before_folder)
            if os.path.isfile(os.path.join(alternate_before_folder, f))
               and (f.lower().endswith(".png") or f.lower().endswith(".bmp"))
               and re.search(r'0x[0-9a-fA-F]+', f)
        ]
        print("DEBUG: Potential ALTERNATE BEFORE images found in alternate BEFORE folder:")
        for abf in alternate_files:
            print("  " + abf)
        for abf in alternate_files:
            hex_id = extract_hex_id(abf)
            if hex_id is not None:
                current = alternate_before_dict.get(hex_id)
                if current:
                    if current.lower().endswith(".bmp") and abf.lower().endswith(".png"):
                        alternate_before_dict[hex_id] = abf
                else:
                    alternate_before_dict[hex_id] = abf
    else:
        if alternate_before_folder:
            print("DEBUG: Provided alternate BEFORE folder does not exist: " + alternate_before_folder)
    
    # Match AFTER images with BEFORE (and ALTERNATE BEFORE if available) using hex id
    for af in after_files:
        hex_id = extract_hex_id(af)
        if hex_id is not None:
            before_path = None
            if hex_id in before_dict:
                before_path = os.path.join(before_folder, before_dict[hex_id])
            alternate_before_path = None
            if alternate_before_dict and (hex_id in alternate_before_dict):
                alternate_before_path = os.path.join(alternate_before_folder, alternate_before_dict[hex_id])
            if before_path:
                after_path = os.path.join(target_folder, af)
                triplets.append((before_path, alternate_before_path, after_path))
                stats["matched_count"] += 1
                print(f"DEBUG: Found match: BEFORE: {before_path} | ALTERNATE BEFORE: {alternate_before_path} | AFTER: {after_path}")
            else:
                print(f"DEBUG: No BEFORE match for AFTER image: {af} (hex id: {hex_id})")
    return triplets, stats

def create_vertical_composite(before_img, after_img, alternate_before_img=None, vertical_padding=VERTICAL_PADDING):
    """
    Create a vertical composite from before and after images (and optional alternate before)
    """
    print("DEBUG: Creating vertical composite")
    print(f"DEBUG: Image sizes - Before: {before_img.size}, After: {after_img.size}, "
          f"Alt Before: {alternate_before_img.size if alternate_before_img else 'None'}")
    
    # Convert images to RGBA if they aren't already
    before_img = before_img.convert('RGBA')
    after_img = after_img.convert('RGBA')
    if alternate_before_img:
        alternate_before_img = alternate_before_img.convert('RGBA')
    
    # Get content bounding boxes
    before_bbox = get_content_bbox(before_img)
    after_bbox = get_content_bbox(after_img)
    alt_before_bbox = get_content_bbox(alternate_before_img) if alternate_before_img else None
    
    print(f"DEBUG: Content bboxes - Before: {before_bbox}, After: {after_bbox}, "
          f"Alt Before: {alt_before_bbox}")
    
    # Crop images to content
    before_img = before_img.crop(before_bbox)
    after_img = after_img.crop(after_bbox)
    if alternate_before_img:
        alternate_before_img = alternate_before_img.crop(alt_before_bbox)
    
    # Calculate dimensions
    max_width = max(before_img.width, after_img.width)
    if alternate_before_img:
        max_width = max(max_width, alternate_before_img.width)
    
    total_height = before_img.height + after_img.height + vertical_padding
    if alternate_before_img:
        total_height += alternate_before_img.height + vertical_padding
    
    print(f"DEBUG: Vertical composite dimensions: {max_width}x{total_height}")
    
    # Create composite
    composite = Image.new('RGBA', (max_width, total_height), (0, 0, 0, 0))
    
    # Paste images
    y_offset = 0
    
    # Paste before image
    x_offset = (max_width - before_img.width) // 2
    print(f"DEBUG: Pasting BEFORE at ({x_offset}, {y_offset})")
    composite.paste(before_img, (x_offset, y_offset), before_img)  # Use alpha channel for transparency
    y_offset += before_img.height + vertical_padding
    
    # Paste alternate before if present
    if alternate_before_img:
        x_offset = (max_width - alternate_before_img.width) // 2
        print(f"DEBUG: Pasting ALT BEFORE at ({x_offset}, {y_offset})")
        composite.paste(alternate_before_img, (x_offset, y_offset), alternate_before_img)  # Use alpha channel
        y_offset += alternate_before_img.height + vertical_padding
    
    # Paste after image
    x_offset = (max_width - after_img.width) // 2
    print(f"DEBUG: Pasting AFTER at ({x_offset}, {y_offset})")
    composite.paste(after_img, (x_offset, y_offset), after_img)  # Use alpha channel
    
    print(f"DEBUG: Vertical composite created successfully: {composite.size}")
    return composite

def create_final_composite(triplets, vertical_padding=VERTICAL_PADDING, horizontal_padding=HORIZONTAL_PADDING, composite_config=None):
    """
    Create the final composite image from the given triplets.
    If composite_config is provided, it will be used to arrange the triplets in rows.
    """
    print(f"\nDEBUG: Creating final composite from {len(triplets)} triplets")
    print(f"DEBUG: Using padding - Vertical: {vertical_padding}px, Horizontal: {horizontal_padding}px")
    
    if composite_config and "rows" in composite_config:
        print("\nDEBUG: Using provided composite configuration")
        print("DEBUG: Configuration structure:")
        for row_idx, row in enumerate(composite_config["rows"]):
            print(f"  Row {row_idx}: {len(row['items'])} items")
            for item in row["items"]:
                print(f"    - Item: hex_id=0x{item['hex_id']}, order_index={item.get('order_index', 0)}")
        
        # Group triplets by rows according to config
        rows = []
        hex_to_triplet = {extract_hex_id(after_path): triplet for triplet in triplets 
                         for _, _, after_path in [triplet]}
        
        for row_idx, row in enumerate(composite_config["rows"]):
            row_triplets = []
            print(f"\nDEBUG: Processing row {row_idx}")
            
            for item in row["items"]:
                hex_str = item["hex_id"].replace("0x", "")
                hex_id = int(hex_str, 16)
                if hex_id in hex_to_triplet:
                    triplet = hex_to_triplet[hex_id]
                    row_triplets.append(triplet)
                    print(f"  Added asset: {os.path.basename(triplet[2])} (hex_id: 0x{hex_id:X})")
                else:
                    print(f"  WARNING: Could not find triplet for hex_id 0x{hex_id:X}")
            
            if row_triplets:
                rows.append(row_triplets)
        
        # Process each row to create row composites
        print("\nDEBUG: Creating row composites")
        row_images = []
        max_width = 0
        total_height = -vertical_padding  # Start with -padding since we add padding for each row
        
        for row_idx, row_triplets in enumerate(rows):
            print(f"\nDEBUG: Creating composite for row {row_idx}")
            row_verticals = []
            
            # Create vertical composites for each triplet in the row
            for triplet in row_triplets:
                before_path, alt_before_path, after_path = triplet
                print(f"  Processing: {os.path.basename(after_path)} (hex_id: 0x{extract_hex_id(after_path):X})")
                
                try:
                    before_img = Image.open(before_path).convert('RGBA')
                    after_img = Image.open(after_path).convert('RGBA')
                    alt_before_img = Image.open(alt_before_path).convert('RGBA') if alt_before_path else None
                    
                    vertical = create_vertical_composite(before_img, after_img, alt_before_img, vertical_padding)
                    print(f"    Created vertical composite: {vertical.size}")
                    row_verticals.append(vertical)
                    
                except Exception as e:
                    print(f"    ERROR: Failed to process triplet: {e}")
                    continue
            
            if not row_verticals:
                continue
                
            # Create row composite
            row_width = sum(v.width for v in row_verticals) + horizontal_padding * (len(row_verticals) + 1)
            row_height = max(v.height for v in row_verticals)
            
            print(f"  Creating row image: {row_width}x{row_height}")
            row_image = Image.new('RGBA', (row_width, row_height), (0, 0, 0, 0))
            
            # Paste verticals into row
            x_offset = horizontal_padding
            for vertical in row_verticals:
                y_offset = (row_height - vertical.height) // 2
                print(f"    Pasting vertical at ({x_offset}, {y_offset})")
                row_image.paste(vertical, (x_offset, y_offset), vertical)
                x_offset += vertical.width + horizontal_padding
            
            row_images.append(row_image)
            max_width = max(max_width, row_width)
            total_height += row_height + vertical_padding
            
        if not row_images:
            print("ERROR: No row images were created")
            return None
        
        # Create final composite from rows
        print(f"\nDEBUG: Creating final composite: {max_width}x{total_height}")
        final_composite = Image.new('RGBA', (max_width, total_height), (0, 0, 0, 0))
        
        # Paste rows
        y_offset = 0
        for idx, row_image in enumerate(row_images):
            x_offset = (max_width - row_image.width) // 2
            print(f"  Pasting row {idx} at ({x_offset}, {y_offset})")
            final_composite.paste(row_image, (x_offset, y_offset), row_image)
            y_offset += row_image.height + vertical_padding
        
        print("\nDEBUG: Final composite created successfully")
        return final_composite
        
    else:
        print("DEBUG: No composite configuration provided, creating single column layout")
        # Create vertical layout (existing code for backward compatibility)
        return create_single_column_composite(triplets, vertical_padding, horizontal_padding)

def create_single_column_composite(triplets, vertical_padding, horizontal_padding):
    """Helper function to create a single-column composite (old style)"""
    print("\nDEBUG: Creating single-column composite")
    verticals = []
    max_width = 0
    total_height = -vertical_padding
    
    for triplet in triplets:
        before_path, alt_before_path, after_path = triplet
        print(f"  Processing: {os.path.basename(after_path)} (hex_id: 0x{extract_hex_id(after_path):X})")
        
        try:
            before_img = Image.open(before_path).convert('RGBA')
            after_img = Image.open(after_path).convert('RGBA')
            alt_before_img = Image.open(alt_before_path).convert('RGBA') if alt_before_path else None
            
            vertical = create_vertical_composite(before_img, after_img, alt_before_img, vertical_padding)
            print(f"    Created vertical composite: {vertical.size}")
            
            verticals.append(vertical)
            max_width = max(max_width, vertical.width)
            total_height += vertical.height + vertical_padding
            
        except Exception as e:
            print(f"    ERROR: Failed to process triplet: {e}")
            continue
    
    if not verticals:
        print("ERROR: No vertical composites were created")
        return None
    
    print(f"\nDEBUG: Creating final single-column composite: {max_width}x{total_height}")
    final_composite = Image.new('RGBA', (max_width, total_height), (0, 0, 0, 0))
    
    y_offset = 0
    for idx, vertical in enumerate(verticals):
        x_offset = (max_width - vertical.width) // 2
        print(f"  Pasting vertical {idx} at ({x_offset}, {y_offset})")
        final_composite.paste(vertical, (x_offset, y_offset), vertical)
        y_offset += vertical.height + vertical_padding
    
    print("\nDEBUG: Single-column composite created successfully")
    return final_composite

def generate_default_composite_json(triplets):
    """
    Generate a default composite arrangement JSON based on the current triplets.
    Each triplet will be placed in a single row with default settings.
    """
    composite_config = {
        "rows": [
            {
                "height_offset": 0,
                "items": [
                    {
                        "hex_id": extract_hex_id(after_path),
                        "order_index": idx
                    }
                    for idx, (_, _, after_path) in enumerate(triplets)
                ]
            }
        ]
    }
    return composite_config

def save_composite_json(target_folder, composite_config):
    """
    Save the composite configuration to a JSON file in the target folder.
    """
    output_path = os.path.join(target_folder, "composite.json")
    with open(output_path, "w") as f:
        json.dump(composite_config, f, indent=4)
    return output_path

def load_composite_json(json_path):
    """
    Load a composite configuration from a JSON file.
    Returns None if the file doesn't exist or is invalid.
    """
    try:
        if os.path.exists(json_path):
            with open(json_path, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"DEBUG: Error loading composite.json: {e}")
    return None

def process_target_folder(target_folder, custom_before_folder=None, alternate_before_folder=None, composite_config=None):
    """
    Process the given target folder by finding matching image triplets,
    creating the composite image, and saving it in the target folder.
    Returns the output path if successful.
    """
    if not os.path.isdir(target_folder):
        print(f"ERROR: Target folder does not exist: {target_folder}")
        return None
    print(f"DEBUG: Processing target folder: {target_folder}")
    
    triplets, stats = find_matching_triplets(target_folder, custom_before_folder, alternate_before_folder)
    if not triplets:
        print("DEBUG: No matching image triplets found.")
        return None

    # If composite_config is provided, reorder triplets according to the configuration
    if composite_config and "rows" in composite_config:
        ordered_triplets = []
        hex_to_triplet = {extract_hex_id(after_path): triplet for triplet in triplets 
                         for _, _, after_path in [triplet]}
        
        for row in composite_config["rows"]:
            for item in row["items"]:
                hex_id = int(item["hex_id"], 16)
                if hex_id in hex_to_triplet:
                    ordered_triplets.append(hex_to_triplet[hex_id])
        
        # Add any remaining triplets that weren't in the config
        config_hex_ids = {int(item["hex_id"], 16) 
                         for row in composite_config["rows"] 
                         for item in row["items"]}
        remaining_triplets = [triplet for triplet in triplets 
                            if extract_hex_id(triplet[2]) not in config_hex_ids]
        triplets = ordered_triplets + remaining_triplets
    
    print(f"DEBUG: Creating composite from {len(triplets)} triplets")
    final_image = create_final_composite(triplets, composite_config=composite_config)
    if final_image:
        output_path = os.path.join(target_folder, "composite.png")
        final_image.save(output_path)
        print(f"DEBUG: Final composite saved to {output_path}")
        return output_path
    return None

class DraggableImage:
    def __init__(self, canvas, x, y, image, hex_id, thumbnail_size=(100, 100)):
        self.canvas = canvas
        self.hex_id = hex_id
        self.row_id = None
        self.thumbnail_size = thumbnail_size
        
        # Create thumbnail
        img = Image.open(image)
        img.thumbnail(thumbnail_size)
        self.photo = ImageTk.PhotoImage(img)
        
        # Create canvas image and text with white text on dark background
        self.image_item = canvas.create_image(x, y, image=self.photo, anchor="n")
        # Position text directly under the image, centered
        text_y = y + thumbnail_size[1] + 2
        self.text_item = canvas.create_text(x + thumbnail_size[0]//2, text_y,
                                        text=f"0x{hex_id:X}", anchor="n", fill=WHITE)
        
        # Bind mouse events
        canvas.tag_bind(self.image_item, '<Button-1>', self.on_press)
        canvas.tag_bind(self.image_item, '<B1-Motion>', self.on_drag)
        canvas.tag_bind(self.image_item, '<ButtonRelease-1>', self.on_release)
        
        self.drag_data = {"x": 0, "y": 0, "dragging": False}
        self.current_pos = [x, y]

    def get_position(self):
        """Get current position of the image"""
        bbox = self.canvas.bbox(self.image_item)
        if bbox:
            return [bbox[0], bbox[1]]  # Use top-left corner
        return self.current_pos

    def set_position(self, x, y):
        """Set position of both image and text"""
        current_pos = self.get_position()
        dx = x - current_pos[0]
        dy = y - current_pos[1]
        
        self.canvas.move(self.image_item, dx, dy)
        self.canvas.move(self.text_item, dx, dy)
        self.current_pos = [x, y]

    def on_press(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self.drag_data["dragging"] = True
        # Raise this image above others
        self.canvas.tag_raise(self.image_item)
        self.canvas.tag_raise(self.text_item)
    
    def on_drag(self, event):
        if not self.drag_data["dragging"]:
            return
            
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        
        self.canvas.move(self.image_item, dx, dy)
        self.canvas.move(self.text_item, dx, dy)
        
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        
        self.current_pos[0] += dx
        self.current_pos[1] += dy
        
        # Notify parent window to update row detection
        self.canvas.event_generate("<<ArrangementChanged>>")
    
    def on_release(self, event):
        self.drag_data["dragging"] = False
        # Notify parent window to update row detection
        self.canvas.event_generate("<<ArrangementChanged>>")

class CompositeArrangementUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Composite Tool")
        self.root.configure(bg=DARK_GRAY)
        
        # Variables
        self.draggable_images = []
        self.triplets = []
        self.selection_rect = None
        self.selection_start = None
        self.rows = {}  # Dictionary to store row assignments
        self.next_row_id = 0
        
        self.create_ui()
        
    def create_ui(self):
        # Main container
        main_container = tk.Frame(self.root, bg=DARK_GRAY)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top frame for folder inputs
        input_frame = tk.Frame(main_container, bg=DARK_GRAY)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Target folder
        tk.Label(input_frame, text="Target Folder:", bg=DARK_GRAY, fg=WHITE).grid(row=0, column=0, sticky="w")
        self.target_entry = tk.Entry(input_frame, width=50, bg=DARKER_GRAY, fg=WHITE)
        self.target_entry.grid(row=0, column=1, padx=5)
        tk.Button(input_frame, text="Browse", command=self.browse_target,
                 bg=BUTTON_BLACK, fg=WHITE, activebackground=BUTTON_BLACK,
                 activeforeground=WHITE).grid(row=0, column=2)
        self.target_stats_label = tk.Label(input_frame, text="", bg=DARK_GRAY, fg=WHITE)
        self.target_stats_label.grid(row=0, column=3, padx=10)
        
        # Custom BEFORE folder
        self.use_custom_before = tk.BooleanVar()
        tk.Checkbutton(input_frame, text="Custom BEFORE folder", variable=self.use_custom_before,
                      bg=DARK_GRAY, fg=WHITE, selectcolor=BUTTON_BLACK,
                      activebackground=DARK_GRAY, activeforeground=WHITE).grid(row=1, column=0, sticky="w")
        self.custom_before_entry = tk.Entry(input_frame, width=50, bg=DARKER_GRAY, fg=WHITE)
        self.custom_before_entry.grid(row=1, column=1, padx=5)
        tk.Button(input_frame, text="Browse", command=self.browse_custom_before,
                 bg=BUTTON_BLACK, fg=WHITE, activebackground=BUTTON_BLACK,
                 activeforeground=WHITE).grid(row=1, column=2)
        self.before_stats_label = tk.Label(input_frame, text="", bg=DARK_GRAY, fg=WHITE)
        self.before_stats_label.grid(row=1, column=3, padx=10)
        
        # ALTERNATE BEFORE folder
        self.use_alternate_before = tk.BooleanVar()
        tk.Checkbutton(input_frame, text="ALTERNATE BEFORE folder", variable=self.use_alternate_before,
                      bg=DARK_GRAY, fg=WHITE, selectcolor=BUTTON_BLACK,
                      activebackground=DARK_GRAY, activeforeground=WHITE).grid(row=2, column=0, sticky="w")
        self.alt_before_entry = tk.Entry(input_frame, width=50, bg=DARKER_GRAY, fg=WHITE)
        self.alt_before_entry.grid(row=2, column=1, padx=5)
        tk.Button(input_frame, text="Browse", command=self.browse_alt_before,
                 bg=BUTTON_BLACK, fg=WHITE, activebackground=BUTTON_BLACK,
                 activeforeground=WHITE).grid(row=2, column=2)
        
        # JSON files frame
        self.json_frame = tk.Frame(main_container, bg=DARK_GRAY)
        self.json_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Canvas frame
        canvas_frame = tk.Frame(main_container, bg=DARK_GRAY)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create canvas with scrollbars
        self.canvas = tk.Canvas(canvas_frame, bg=DARKER_GRAY, highlightthickness=0)
        scrollbar_y = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar_x = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        
        self.canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Button frame
        button_frame = tk.Frame(main_container, bg=DARK_GRAY)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Use tk.Button instead of ttk.Button for better color control
        tk.Button(button_frame, text="Reset Layout", command=self.reset_layout,
                 bg=BUTTON_BLACK, fg=WHITE, activebackground=BUTTON_BLACK, 
                 activeforeground=WHITE).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Save Arrangement", command=self.save_arrangement,
                 bg=BUTTON_BLACK, fg=WHITE, activebackground=BUTTON_BLACK,
                 activeforeground=WHITE).pack(side=tk.LEFT, padx=5)
        generate_btn = tk.Button(button_frame, text="Generate Composite", command=self.generate_composite,
                             bg=BUTTON_BLACK, fg=WHITE, activebackground=BUTTON_BLACK,
                             activeforeground=WHITE)
        generate_btn.pack(side=tk.LEFT, padx=5)
        generate_btn.configure(relief=tk.RAISED, borderwidth=2)  # Make the generate button more prominent
        
        # Bind events
        self.canvas.bind("<<ArrangementChanged>>", self.on_arrangement_changed)
        self.canvas.bind("<ButtonPress-1>", self.on_select_start)
        self.canvas.bind("<B1-Motion>", self.on_select_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_select_end)
        self.target_entry.bind("<FocusOut>", self.on_target_changed)
        
    def browse_target(self):
        folder = filedialog.askdirectory(title="Select Target Folder")
        if folder:
            self.target_entry.delete(0, tk.END)
            self.target_entry.insert(0, folder)
            self.on_target_changed(None)
    
    def browse_custom_before(self):
        folder = filedialog.askdirectory(title="Select Custom BEFORE Folder")
        if folder:
            self.custom_before_entry.delete(0, tk.END)
            self.custom_before_entry.insert(0, folder)
    
    def browse_alt_before(self):
        folder = filedialog.askdirectory(title="Select ALTERNATE BEFORE Folder")
        if folder:
            self.alt_before_entry.delete(0, tk.END)
            self.alt_before_entry.insert(0, folder)
    
    def find_json_files(self, folder):
        """Find and validate JSON files in the target folder"""
        json_files = []
        try:
            for file in os.listdir(folder):
                if file.endswith('.json'):
                    path = os.path.join(folder, file)
                    try:
                        with open(path, 'r') as f:
                            data = json.load(f)
                            if 'rows' in data:  # Basic validation
                                json_files.append(path)
                    except:
                        continue
        except:
            pass
        return json_files
    
    def update_json_buttons(self, folder):
        """Update JSON file buttons"""
        # Clear existing buttons
        for widget in self.json_frame.winfo_children():
            widget.destroy()
        
        # Add label
        tk.Label(self.json_frame, text="Available Layouts:", 
                 bg=DARK_GRAY, fg=WHITE).pack(side=tk.LEFT, padx=(0, 10))
        
        # Add buttons for each JSON file
        json_files = self.find_json_files(folder)
        for json_file in json_files:
            name = os.path.basename(json_file)
            btn = tk.Button(self.json_frame, text=name, 
                           command=lambda f=json_file: self.load_json_layout(f),
                           bg=BUTTON_BLACK, fg=WHITE, activebackground=BUTTON_BLACK, 
                           activeforeground=WHITE)
            btn.pack(side=tk.LEFT, padx=5)
        
        # Load first JSON if available
        if json_files:
            self.load_json_layout(json_files[0])
    
    def on_target_changed(self, event):
        """Handle target folder change"""
        target = self.target_entry.get().strip()
        if target and os.path.isdir(target):
            # Update triplets
            custom_before = self.custom_before_entry.get().strip() if self.use_custom_before.get() else None
            alt_before = self.alt_before_entry.get().strip() if self.use_alternate_before.get() else None
            self.triplets, stats = find_matching_triplets(target, custom_before, alt_before)
            
            # Update stats labels
            self.update_stats_labels(stats)
            
            # Update JSON buttons and canvas
            self.update_json_buttons(target)
            if not self.triplets:
                messagebox.showerror("Error", "No matching image triplets found.")
            else:
                self.reset_layout()
    
    def load_json_layout(self, json_file):
        """Load layout from JSON file"""
        try:
            with open(json_file, 'r') as f:
                config = json.load(f)
            
            if not config.get("rows"):
                raise ValueError("Invalid layout file: no rows defined")
            
            # Clear current layout
            self.canvas.delete("all")
            self.draggable_images = []
            
            # Create dictionary mapping hex IDs to triplets
            hex_to_triplet = {extract_hex_id(after_path): triplet 
                            for triplet in self.triplets 
                            for _, _, after_path in [triplet]}
            
            # Process each row in the configuration
            row_height = 150  # Height for each row including padding
            for row_idx, row in enumerate(config["rows"]):
                base_y = row_idx * row_height + 20
                
                # Calculate total width of images in this row for centering
                num_images = len(row["items"])
                total_width = num_images * 100 + (num_images - 1) * 20  # image width + padding
                start_x = (self.canvas.winfo_width() - total_width) // 2
                
                for idx, item in enumerate(row["items"]):
                    # Convert hex string to integer, handling both "0x" prefix and raw hex string
                    hex_str = item["hex_id"].replace("0x", "")
                    hex_id = int(hex_str, 16)
                    
                    if hex_id in hex_to_triplet:
                        x = start_x + idx * (100 + 20)  # image width + padding
                        y = base_y + (row.get("y_offset", 0))
                        
                        # Create draggable image
                        triplet = hex_to_triplet[hex_id]
                        img = DraggableImage(self.canvas, x, y, triplet[2], hex_id)
                        self.draggable_images.append(img)
            
            # Update row visualization
            self.rows = self.detect_rows()
            self.update_row_visualization()
            
            # Update canvas scroll region
            self.canvas.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load layout: {str(e)}")

    def reset_layout(self):
        """Reset canvas layout with 16:9 aspect ratio approximation"""
        self.canvas.delete("all")
        self.draggable_images = []
        self.rows = {}
        
        if not self.triplets:
            return
        
        # Calculate grid dimensions to approximate 16:9
        total_images = len(self.triplets)
        ratio = 16/9
        
        # Calculate number of rows to approximate 16:9 ratio
        num_rows = int(np.sqrt(total_images / ratio))
        if num_rows < 1:
            num_rows = 1
        
        images_per_row = total_images // num_rows
        if images_per_row < 1:
            images_per_row = 1
        
        # Create grid layout
        thumbnail_size = (100, 100)
        padding = 20
        
        for idx, (_, _, after_path) in enumerate(self.triplets):
            row = idx // images_per_row
            col = idx % images_per_row
            
            x = col * (thumbnail_size[0] + padding) + padding
            y = row * (thumbnail_size[1] + padding * 2) + padding
            
            hex_id = extract_hex_id(after_path)
            if hex_id is not None:
                img = DraggableImage(self.canvas, x, y, after_path, hex_id, thumbnail_size)
                self.draggable_images.append(img)
        
        # Update row visualization
        self.rows = self.detect_rows()
        self.update_row_visualization()
        
        # Update canvas scroll region
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def detect_rows(self):
        """Automatically detect rows based on y-position overlap"""
        if not self.draggable_images:
            return {}

        # Sort images by y position
        sorted_images = sorted(self.draggable_images, key=lambda img: img.get_position()[1])
        
        # Initialize rows
        rows = {}
        next_row_id = 0
        
        # Process each image
        for img in sorted_images:
            x, y = img.get_position()
            img_height = img.thumbnail_size[1]
            
            # Check if image overlaps with any existing row
            found_row = False
            for row_id, row_images in rows.items():
                # Check if this image's vertical range overlaps with any image in the row
                row_y = row_images[0].get_position()[1]  # Use first image in row as reference
                if abs(y - row_y) < img_height * 0.5:  # 50% overlap threshold
                    rows[row_id].append(img)
                    img.row_id = row_id
                    found_row = True
                    break
            
            # If no overlapping row found, create new row
            if not found_row:
                rows[next_row_id] = [img]
                img.row_id = next_row_id
                next_row_id += 1
        
        return rows

    def on_select_start(self, event):
        """Start selection rectangle"""
        # Only start selection if not clicking on an image
        if not self.canvas.find_withtag(tk.CURRENT):
            self.selection_start = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
            if self.selection_rect:
                self.canvas.delete(self.selection_rect)
            self.selection_rect = self.canvas.create_rectangle(
                self.selection_start[0], self.selection_start[1],
                self.selection_start[0], self.selection_start[1],
                outline=WHITE, dash=(4, 4))
    
    def on_select_drag(self, event):
        """Update selection rectangle"""
        if self.selection_start:
            curx = self.canvas.canvasx(event.x)
            cury = self.canvas.canvasy(event.y)
            self.canvas.coords(self.selection_rect,
                            self.selection_start[0], self.selection_start[1],
                            curx, cury)
    
    def on_select_end(self, event):
        """Process selection"""
        if self.selection_start and self.selection_rect:
            x1, y1 = self.selection_start
            x2 = self.canvas.canvasx(event.x)
            y2 = self.canvas.canvasy(event.y)
            
            # Find images in selection
            selected = []
            for img in self.draggable_images:
                pos = img.get_position()
                if (min(x1, x2) <= pos[0] <= max(x1, x2) and
                    min(y1, y2) <= pos[1] <= max(y1, y2)):
                    selected.append(img)
            
            # Update row visualization
            self.rows = self.detect_rows()
            self.update_row_visualization()
            
            self.canvas.delete(self.selection_rect)
            self.selection_rect = None
            self.selection_start = None
    
    def update_row_visualization(self):
        """Update row visualization"""
        # Clear existing row visualization
        self.canvas.delete("row_box")
        
        # Group images by row
        row_groups = {}
        for img in self.draggable_images:
            if img.row_id is not None:
                if img.row_id not in row_groups:
                    row_groups[img.row_id] = []
                row_groups[img.row_id].append(img)
        
        # Draw row boxes
        for row_id, images in row_groups.items():
            if not images:
                continue
            
            # Calculate row bounds
            positions = [img.get_position() for img in images]
            min_x = min(pos[0] for pos in positions) - 5
            max_x = max(pos[0] for pos in positions) + 105  # thumbnail width + padding
            min_y = min(pos[1] for pos in positions) - 5
            max_y = max(pos[1] for pos in positions) + 125  # thumbnail height + text + padding
            
            # Draw row box
            color = ROW_COLORS[row_id % len(ROW_COLORS)]
            box = self.canvas.create_rectangle(
                min_x, min_y, max_x, max_y,
                fill=color, outline=WHITE, width=2,
                tags=("row_box",)
            )
            self.canvas.tag_lower(box)
    
    def on_arrangement_changed(self, event):
        """Handle arrangement changes by updating row detection"""
        self.rows = self.detect_rows()
        self.update_row_visualization()
    
    def update_stats_labels(self, stats):
        """Update the stats labels with current counts"""
        self.target_stats_label.config(text=f"Found: {stats['after_count']} assets")
        if stats['before_count'] > 0:
            self.before_stats_label.config(text=f"Matches: {stats['matched_count']}/{stats['before_count']}")
        else:
            self.before_stats_label.config(text="")

    def generate_composite_config(self):
        """Generate composite configuration from current arrangement"""
        config = {"rows": []}
        
        # Group images by row
        rows = self.detect_rows()
        
        # Process each row
        for row_id, images in rows.items():
            # Sort images in row by x position
            sorted_images = sorted(images, key=lambda img: img.get_position()[0])
            
            # Create row configuration
            row_config = {
                "items": [
                    {
                        "hex_id": f"{img.hex_id:X}",  # Format as hex string without 0x prefix
                        "order_index": idx
                    }
                    for idx, img in enumerate(sorted_images)
                ]
            }
            
            # Add row to config
            config["rows"].append(row_config)
        
        return config
    
    def save_arrangement(self):
        """Save current arrangement to JSON file"""
        if not self.draggable_images:
            messagebox.showerror("Error", "No images to save")
            return
        
        target = self.target_entry.get().strip()
        if not target:
            messagebox.showerror("Error", "No target folder specified")
            return
        
        # Generate configuration
        config = self.generate_composite_config()
        
        # Save to JSON file
        json_path = os.path.join(target, "composite.json")
        try:
            with open(json_path, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"DEBUG: Saved arrangement to {json_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save arrangement: {str(e)}")
    
    def generate_composite(self):
        """Generate composite image from current arrangement"""
        if not self.triplets:
            messagebox.showerror("Error", "No images to arrange")
            return
        
        config = self.generate_composite_config()
        target = self.target_entry.get().strip()
        custom_before = self.custom_before_entry.get().strip() if self.use_custom_before.get() else None
        alt_before = self.alt_before_entry.get().strip() if self.use_alternate_before.get() else None
        
        output = process_target_folder(target, custom_before, alt_before, composite_config=config)
        if output:
            messagebox.showinfo("Success", f"Composite image created at:\n{output}")
        else:
            messagebox.showerror("Error", "Failed to create composite image")

def main():
    root = tk.Tk()
    app = CompositeArrangementUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
