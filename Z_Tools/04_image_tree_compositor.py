"""
Tree Composite Image Render Tool
Sets up and Arranges Image Renders of the Tree Static Arts , showcasing the altered art 
in the UI canvas set groups and types by linking ITEMS as trunk and leaves through metadata 
Setup and Preview multiple OUTPUT render configurations with per-item properties (exclusion, variant selection, trunk-only mode).

Core :
- Loads tree items (trunk, leaves, autumn leaves) from folder with metadata JSON files
- Links items via metadata keys: TREE_LINKED_LEAVES, TREE_LINKED_AUTUMN, TREE_LINKED_AUTUMN_VARIANT
- Applies brightness-based masking to simulate in-game 1-bit alpha rendering
- Composites trunk + leaves with configurable height offsets stored per leaves item
- Arranges composites in 16:9 target layout with bottom-aligned trunks

Render Config:
- create Multiple named render configs (default, autumn_only, comparison, etc.)
- item properties: excluded (bool), use_autumn (bool), show_leaves (bool)
- Each item instance identified by name + canvas position for duplicate support ( side by side comparisons)
- Configs saved to folder as JSON files

UI Workflow:
1. Select folder containing tree item images and metadata
2. Set Items types (trunk, leaves, leaves_autumn) which is saved to markdown metadata variable in the items subfolder
3. Arrange items on canvas (drag to move)
4. Link items saved to metadata ( leaf to trunk , or leaf to autumn variation , any combination)
5. Toggle preview mode to see final composite render
6. Select items to configure per-render properties ( exclude or switch variant )
7. Drag from Tree Composites list to add duplicates for side by side comparisons of variants or without leaves 
8. Export static PNG composites and animated WebP (altered comparision with original)

Export Modes:
- Export Final Composite: Saves all render configs as separate PNG files
- Export Animated WebP: Creates looping 2-frame animation (altered/original comparison)
  Utilizes the "original" subfolder with matching hex IDs for original art ( TODO: optional global folder )

Details:
- Brightness opacity mask threshold: 5 (simulates UO client rendering for opacity mask )
- Tree Set Composite arrangement: Bottom-center-aligned trunks, leaves share anchor then offset upward ( positive = up )
- Working Canvas order: Sorted by Y position (top to bottom), then X (left to right)
- Output format: PNG (static), WebP (animated, 2000ms per frame, loop=0 infinite )

VERSION::20251128
"""
import os
import re
import json
import numpy as np
from PIL import Image, ImageTk, ImageDraw
import tkinter as tk
from tkinter import filedialog, ttk

# UI Colors
DARK_GRAY = "#1E1E1E"
DARKER_GRAY = "#252526"
LIGHTER_GRAY = "#333333"
BUTTON_BLACK = "#000000"
WHITE = "#FFFFFF"
TRUNK_COLOR = "#7C4C3C"  # Brown for trunk bounds
LEAVES_COLOR = "#3C7C4C"  # Green for leaves bounds
AUTUMN_COLOR = "#D4A574"  # Orange/tan for autumn leaves bounds
MUTED_GREEN = "#3C7C5C"
MUTED_BLUE = "#3C5C7C"
MUTED_PURPLE = "#6C4C7C"

def extract_hex_id(filename):
    """Extract hexadecimal ID from filename"""
    match = re.search(r'0x([0-9a-fA-F]+)', filename)
    if match:
        try:
            return int(match.group(1), 16)
        except ValueError:
            return None
    return None

def get_content_bbox(image):
    """Get bounding box of non-transparent/non-black pixels"""
    im = image.convert("RGBA")
    data = np.array(im)
    mask = ~((data[:, :, 3] == 0) | ((data[:, :, 0] == 0) & (data[:, :, 1] == 0) & (data[:, :, 2] == 0)))
    coords = np.argwhere(mask)
    if coords.size == 0:
        return (0, 0, image.width, image.height)
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0) + 1
    return (x0, y0, x1, y1)

def apply_brightness_mask(image, threshold=5):
    """Apply 1-bit masking based on brightness threshold (simulates in-game masking)"""
    img = image.convert("RGBA")
    data = np.array(img)
    
    # Calculate brightness (simple average of RGB)
    brightness = (data[:, :, 0].astype(np.float32) + 
                  data[:, :, 1].astype(np.float32) + 
                  data[:, :, 2].astype(np.float32)) / 3.0
    
    # Create 1-bit mask: pixels below threshold become fully transparent
    mask = brightness >= threshold
    
    # Apply mask to alpha channel
    data[:, :, 3] = np.where(mask, data[:, :, 3], 0)
    
    return Image.fromarray(data, 'RGBA')

def load_tree_items(folder_path):
    """Load all tree item images from folder"""
    items = []
    if not os.path.isdir(folder_path):
        return items
    
    upscale_folder = os.path.join(folder_path, "Upscale")
    
    for file in os.listdir(folder_path):
        if file.lower().endswith(('.bmp', '.png')):
            hex_id = extract_hex_id(file)
            if hex_id is not None:
                full_path = os.path.join(folder_path, file)
                item_name = os.path.splitext(file)[0]
                
                # Read metadata from Upscale/<item_name>/<item_name>.md
                metadata = read_item_metadata(upscale_folder, item_name)
                
                # Determine specific component type (trunk, leaves, leaves_autumn, unknown)
                component_type = get_tree_component_type(metadata)
                
                items.append({
                    'hex_id': hex_id,
                    'filename': file,
                    'path': full_path,
                    'name': item_name,
                    'type': component_type,  # trunk, leaves, leaves_autumn, or unknown
                    'metadata': metadata
                })
    
    return sorted(items, key=lambda x: x['hex_id'])

def read_item_metadata(upscale_folder, item_name):
    """Read Obsidian dataview metadata from item's .md file"""
    metadata = {}
    try:
        md_path = os.path.join(upscale_folder, item_name, f"{item_name}.md")
        print(f"[Metadata Read] Attempting to read: {md_path}")
        
        if not os.path.exists(md_path):
            print(f"[Metadata Read] File does not exist: {md_path}")
            return metadata
        
        with open(md_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if '::' in line:
                    key, value = line.split('::', 1)
                    metadata[key.strip()] = value.strip()
                    print(f"[Metadata Read] Found: {key.strip()} = {value.strip()}")
        
        print(f"[Metadata Read] Loaded {len(metadata)} keys from {item_name}")
    except Exception as e:
        print(f"[Metadata Read] ERROR reading {md_path}: {e}")
    return metadata

def get_tree_component_type(metadata):
    """Determine the specific tree component type from metadata"""
    tree_type = metadata.get('TREE_TYPE', 'unknown')
    
    # For leaves, check if it's autumn variant
    if tree_type == 'leaves':
        is_autumn = metadata.get('TREE_AUTUMN_VARIANT', 'False') == 'True'
        if is_autumn:
            return 'leaves_autumn'
    
    return tree_type

def write_item_metadata(upscale_folder, item_name, key, value):
    """Write or update metadata key in item's .md file"""
    try:
        item_folder = os.path.join(upscale_folder, item_name)
        os.makedirs(item_folder, exist_ok=True)
        print(f"[Write Metadata] Folder: {item_folder}")
        
        md_path = os.path.join(item_folder, f"{item_name}.md")
        print(f"[Write Metadata] File: {md_path}")
        
        # Read existing content
        existing_lines = []
        key_found = False
        if os.path.exists(md_path):
            with open(md_path, 'r', encoding='utf-8') as f:
                existing_lines = f.readlines()
        
        # Update or append the key
        new_lines = []
        for line in existing_lines:
            if '::' in line:
                existing_key = line.split('::', 1)[0].strip()
                if existing_key == key:
                    new_lines.append(f"{key}::{value}\n")
                    key_found = True
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        if not key_found:
            new_lines.append(f"{key}::{value}\n")
            print(f"[Write Metadata] Added new key: {key}::{value}")
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"[Write Metadata] SUCCESS: Wrote {key}::{value}")
    except Exception as e:
        print(f"[Write Metadata] ERROR: {e}")

class TreeComposite:
    """Represents a tree composite with trunk, base leaves, and optional autumn leaves"""
    def __init__(self, trunk_item=None, leaves_item=None, autumn_leaves_item=None, 
                 offset_x=0, offset_y=0, autumn_offset_x=0, autumn_offset_y=0,
                 leaves_height_offset=50):
        self.trunk_item = trunk_item
        self.leaves_item = leaves_item  # Base leaves
        self.autumn_leaves_item = autumn_leaves_item  # Autumn variant
        self.offset_x = offset_x  # Base leaves offset relative to trunk
        self.offset_y = offset_y
        self.autumn_offset_x = autumn_offset_x  # Autumn leaves offset
        self.autumn_offset_y = autumn_offset_y
        self.leaves_height_offset = leaves_height_offset  # Vertical offset for leaves above trunk
        self.name = "composite"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'trunk_hex_id': f"0x{self.trunk_item['hex_id']:X}" if self.trunk_item else None,
            'leaves_hex_id': f"0x{self.leaves_item['hex_id']:X}" if self.leaves_item else None,
            'autumn_leaves_hex_id': f"0x{self.autumn_leaves_item['hex_id']:X}" if self.autumn_leaves_item else None,
            'offset_x': self.offset_x,
            'offset_y': self.offset_y,
            'autumn_offset_x': self.autumn_offset_x,
            'autumn_offset_y': self.autumn_offset_y,
            'name': self.name
        }
    
    @staticmethod
    def from_dict(data, items_dict):
        """Create TreeComposite from dictionary"""
        trunk_hex = data.get('trunk_hex_id')
        leaves_hex = data.get('leaves_hex_id')
        autumn_hex = data.get('autumn_leaves_hex_id')
        
        trunk_item = items_dict.get(int(trunk_hex, 16)) if trunk_hex else None
        leaves_item = items_dict.get(int(leaves_hex, 16)) if leaves_hex else None
        autumn_item = items_dict.get(int(autumn_hex, 16)) if autumn_hex else None
        
        composite = TreeComposite(
            trunk_item=trunk_item,
            leaves_item=leaves_item,
            autumn_leaves_item=autumn_item,
            offset_x=data.get('offset_x', 0),
            offset_y=data.get('offset_y', 0),
            autumn_offset_x=data.get('autumn_offset_x', 0),
            autumn_offset_y=data.get('autumn_offset_y', 0)
        )
        composite.name = data.get('name', '')
        return composite
    
    def get_component_status(self):
        """Get status of all tree components"""
        return {
            'has_trunk': self.trunk_item is not None,
            'has_base_leaves': self.leaves_item is not None,
            'has_autumn_leaves': self.autumn_leaves_item is not None,
            'is_complete': self.trunk_item is not None and self.leaves_item is not None
        }

class DraggableTreeItem:
    """Represents a draggable tree item on the canvas"""
    def __init__(self, canvas, x, y, item, thumbnail_size=(120, 120), ui_ref=None):
        self.canvas = canvas
        self.item = item
        self.thumbnail_size = thumbnail_size
        self.x = x
        self.y = y
        self.ui_ref = ui_ref  # Reference to TreeCompositorUI for callbacks
        
        # Create thumbnail
        img = Image.open(item['path']).convert('RGBA')
        img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(img)
        
        # Create canvas items
        self.image_item = canvas.create_image(x, y, image=self.photo, anchor="nw")
        self.text_item = canvas.create_text(x + thumbnail_size[0]//2, y + thumbnail_size[1] + 5,
                                           text=f"0x{item['hex_id']:04X}", anchor="n", fill=WHITE, font=("Arial", 8))
        self.bounds_rect = None
        
        # Bind events
        canvas.tag_bind(self.image_item, '<Button-1>', self.on_press)
        canvas.tag_bind(self.image_item, '<B1-Motion>', self.on_drag)
        canvas.tag_bind(self.image_item, '<ButtonRelease-1>', self.on_release)
        canvas.tag_bind(self.text_item, '<Button-1>', self.on_press)
        
        self.drag_data = {"x": 0, "y": 0, "dragging": False}
    
    def on_press(self, event):
        print(f"[DraggableItem] on_press for {self.item['name']}")
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self.drag_data["dragging"] = False  # Don't start dragging immediately
        self.drag_data["moved"] = False
        self.canvas.tag_raise(self.image_item)
        self.canvas.tag_raise(self.text_item)
        if self.bounds_rect:
            self.canvas.tag_raise(self.bounds_rect)
    
    def on_drag(self, event):
        # Only start dragging if moved more than 3 pixels
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        
        if not self.drag_data["dragging"]:
            if abs(dx) > 3 or abs(dy) > 3:
                self.drag_data["dragging"] = True
                print(f"[DraggableItem] Started dragging {self.item['name']}")
            else:
                return
        
        if not self.drag_data["dragging"]:
            return
        
        self.drag_data["moved"] = True
        self.canvas.move(self.image_item, dx, dy)
        self.canvas.move(self.text_item, dx, dy)
        if self.bounds_rect:
            self.canvas.move(self.bounds_rect, dx, dy)
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self.x += dx
        self.y += dy
    
    def on_release(self, event):
        was_dragging = self.drag_data["moved"]
        print(f"[DraggableItem] on_release for {self.item['name']}, was_dragging={was_dragging}")
        self.drag_data["dragging"] = False
        self.drag_data["moved"] = False
        
        # Update link lines if item was dragged
        if was_dragging and self.ui_ref:
            self.ui_ref.update_link_lines()
    
    def update_bounds(self, show_bounds, item_type):
        """Update or remove bounds rectangle based on settings"""
        if self.bounds_rect:
            self.canvas.delete(self.bounds_rect)
            self.bounds_rect = None
        
        if show_bounds:
            # Get actual thumbnail dimensions
            img_width = self.photo.width()
            img_height = self.photo.height()
            
            # Choose color based on type
            if item_type == 'trunk':
                color = TRUNK_COLOR
            elif item_type == 'leaves':
                color = LEAVES_COLOR
            elif item_type == 'leaves_autumn':
                color = AUTUMN_COLOR
            else:
                color = WHITE
            
            # Draw bounds rectangle around the entire thumbnail
            # Offset by 2 pixels outward to not overlap image pixels
            offset = 2
            self.bounds_rect = self.canvas.create_rectangle(
                self.x - offset,
                self.y - offset,
                self.x + img_width + offset,
                self.y + img_height + offset,
                outline=color,
                width=2,
                tags="bounds"
            )
            self.canvas.tag_lower(self.bounds_rect, self.image_item)

class TreeCompositorUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Tree Compositor Tool")
        self.root.configure(bg=DARK_GRAY)
        self.root.geometry("1600x900")
        
        # Set default folder path relative to script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        default_folder = os.path.join(script_dir, "..", "ART", "ART_Tree")
        self.folder_path = os.path.normpath(default_folder)
        self.upscale_folder = ""
        
        self.items = []
        self.items_dict = {}  # hex_id -> item
        self.trunk_items = []  # Items classified as trunk
        self.leaves_items = []  # Items classified as base leaves
        self.autumn_leaves_items = []  # Items classified as autumn leaves
        self.unknown_items = []  # Items not yet classified
        self.composites = []  # List of TreeComposite objects
        self.selected_composite_idx = None
        self.selected_trunk = None
        self.selected_leaves = None
        
        # Canvas items
        self.draggable_items = []  # List of DraggableTreeItem objects
        
        # Mode state (start in MOVE TOOL mode)
        self.classification_mode = tk.StringVar(value="none")  # none, trunk, leaves, leaves_autumn, link, unlink
        self.show_bounds = tk.BooleanVar(value=True)
        self.show_links = tk.BooleanVar(value=True)
        self.show_names = tk.BooleanVar(value=False)  # Show names in preview (disabled for now)
        
        # Link mode state
        self.link_mode_first_item = None  # First item selected in link mode
        self.link_mode_highlight = None  # Canvas highlight for first item
        
        # Link visualization
        self.link_lines = []  # List of canvas line items
        
        # Canvas panning state
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.is_panning = False
        
        # Preview mode state
        self.preview_mode = False
        self.preview_image = None
        self.preview_photo = None
        self.preview_composites = []  # List of (type, composite_img, tree_set, bounds) for preview
        self.preview_zoom = 1.0  # Zoom level for preview mode
        self.preview_base_image = None  # Unzoomed preview image
        
        # Multi-render system
        self.render_configs = {}  # Dict of render_name -> config
        self.current_render = "default"  # Currently active render config
        
        # Per-item render properties (stored in composite.json)
        self.item_render_props = {}  # item_id -> {use_autumn, show_leaves, excluded}
        
        # Selected item state
        self.selected_item = None
        self.preview_selected_tree = None  # Selected tree in preview mode
        
        # Filter state
        self.filter_show_trunks = tk.BooleanVar(value=True)
        self.filter_show_leaves = tk.BooleanVar(value=True)
        self.filter_show_autumn = tk.BooleanVar(value=True)
        self.filter_show_unclassified = tk.BooleanVar(value=True)
        self.filter_unlinked_only = tk.BooleanVar(value=False)
        
        # Global original folder path
        self.global_original_folder = ""
        
        # Floating offset entry in preview mode
        self.preview_offset_entry = None
        self.preview_offset_window = None
        
        # Preview display mode: 'altered', 'original', 'comparison'
        self.preview_display_mode = 'altered'
        self.preview_zoom = 1.0  # Initialize zoom level
        
        self.create_ui()
        
        # Load render configs after UI is created
        self.load_render_configs()
        
        # Auto-load items on startup
        self.root.after(100, self.auto_load_on_startup)
    
    def create_ui(self):
        """Create the main UI"""
        # Top control panel
        control_frame = tk.Frame(self.root, bg=DARK_GRAY)
        control_frame.pack(fill=tk.X, padx=10, pady=(5, 2))
        
        # Folder selection
        tk.Label(control_frame, text="Tree Folder:", bg=DARK_GRAY, fg=WHITE).pack(side=tk.LEFT)
        self.folder_entry = tk.Entry(control_frame, width=35, bg=DARKER_GRAY, fg=WHITE)
        self.folder_entry.pack(side=tk.LEFT, padx=5)
        self.folder_entry.insert(0, self.folder_path)
        tk.Button(control_frame, text="Browse", command=self.browse_folder,
                 bg=BUTTON_BLACK, fg=WHITE).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Load Items", command=self.load_items,
                 bg=MUTED_BLUE, fg=WHITE, font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        # Second row for global original folder
        control_frame2 = tk.Frame(self.root, bg=DARK_GRAY)
        control_frame2.pack(fill=tk.X, padx=10, pady=(2, 2))
        
        tk.Label(control_frame2, text="Global Original:", bg=DARK_GRAY, fg=WHITE).pack(side=tk.LEFT)
        self.global_original_entry = tk.Entry(control_frame2, width=35, bg=DARKER_GRAY, fg=WHITE)
        self.global_original_entry.pack(side=tk.LEFT, padx=5)
        self.global_original_entry.insert(0, self.global_original_folder)
        # Bind to detect manual entry changes (on Return key or focus loss)
        self.global_original_entry.bind('<Return>', self.on_global_original_changed)
        self.global_original_entry.bind('<FocusOut>', self.on_global_original_changed)
        tk.Button(control_frame2, text="Browse", command=self.browse_global_original,
                 bg=BUTTON_BLACK, fg=WHITE).pack(side=tk.LEFT, padx=5)
        tk.Label(control_frame2, text="(Optional: Global folder for original art)", 
                bg=DARK_GRAY, fg=LIGHTER_GRAY, font=("Arial", 8, "italic")).pack(side=tk.LEFT, padx=5)
        
        # Separator
        tk.Frame(control_frame, width=2, bg=LIGHTER_GRAY).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Mode buttons
        tk.Label(control_frame, text="Classification Mode:", bg=DARK_GRAY, fg=WHITE).pack(side=tk.LEFT, padx=5)
        
        self.mode_trunk_btn = tk.Button(control_frame, text="SET TRUNK", 
                                        command=lambda: self.toggle_mode('trunk'),
                                        bg=LIGHTER_GRAY, fg=WHITE, font=("Arial", 9, "bold"),
                                        relief=tk.RAISED, bd=2)
        self.mode_trunk_btn.pack(side=tk.LEFT, padx=2)
        
        self.mode_leaves_btn = tk.Button(control_frame, text="SET LEAVES",
                                         command=lambda: self.toggle_mode('leaves'),
                                         bg=LIGHTER_GRAY, fg=WHITE, font=("Arial", 9, "bold"),
                                         relief=tk.RAISED, bd=2)
        self.mode_leaves_btn.pack(side=tk.LEFT, padx=2)
        
        self.mode_autumn_btn = tk.Button(control_frame, text="SET AUTUMN",
                                         command=lambda: self.toggle_mode('leaves_autumn'),
                                         bg=LIGHTER_GRAY, fg=WHITE, font=("Arial", 9, "bold"),
                                         relief=tk.RAISED, bd=2)
        self.mode_autumn_btn.pack(side=tk.LEFT, padx=2)
        
        self.mode_none_btn = tk.Button(control_frame, text="MOVE TOOL",
                                       command=lambda: self.toggle_mode('none'),
                                       bg=MUTED_BLUE, fg=WHITE, font=("Arial", 9, "bold"),
                                       relief=tk.SUNKEN, bd=2)
        self.mode_none_btn.pack(side=tk.LEFT, padx=2)
        
        # Separator
        tk.Frame(control_frame, width=2, bg=LIGHTER_GRAY).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Link mode buttons
        tk.Label(control_frame, text="Linking:", bg=DARK_GRAY, fg=WHITE).pack(side=tk.LEFT, padx=5)
        
        self.mode_link_btn = tk.Button(control_frame, text="LINK",
                                       command=lambda: self.toggle_mode('link'),
                                       bg=LIGHTER_GRAY, fg=WHITE, font=("Arial", 9, "bold"),
                                       relief=tk.RAISED, bd=2)
        self.mode_link_btn.pack(side=tk.LEFT, padx=2)
        
        self.mode_unlink_btn = tk.Button(control_frame, text="UNLINK",
                                         command=lambda: self.toggle_mode('unlink'),
                                         bg=LIGHTER_GRAY, fg=WHITE, font=("Arial", 9, "bold"),
                                         relief=tk.RAISED, bd=2)
        self.mode_unlink_btn.pack(side=tk.LEFT, padx=2)
        
        # Separator
        tk.Frame(control_frame, width=2, bg=LIGHTER_GRAY).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Show bounds checkbox
        tk.Checkbutton(control_frame, text="Show Bounds", variable=self.show_bounds,
                      command=self.update_all_bounds,
                      bg=DARK_GRAY, fg=WHITE, selectcolor=BUTTON_BLACK,
                      font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        
        # Show links checkbox
        tk.Checkbutton(control_frame, text="Show Links", variable=self.show_links,
                      command=self.update_link_lines,
                      bg=DARK_GRAY, fg=MUTED_PURPLE, selectcolor=BUTTON_BLACK,
                      font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        # Show names checkbox
        tk.Checkbutton(control_frame, text="Show Names", variable=self.show_names,
                      bg=DARK_GRAY, fg=WHITE, selectcolor=BUTTON_BLACK,
                      font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        
        # Second row - Filter controls
        filter_frame = tk.Frame(self.root, bg=DARK_GRAY)
        filter_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        tk.Label(filter_frame, text="View Filters:", bg=DARK_GRAY, fg=WHITE, 
                font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        tk.Checkbutton(filter_frame, text="Show Trunks", variable=self.filter_show_trunks,
                      command=self.apply_filters,
                      bg=DARK_GRAY, fg=TRUNK_COLOR, selectcolor=BUTTON_BLACK,
                      font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        tk.Checkbutton(filter_frame, text="Show Leaves", variable=self.filter_show_leaves,
                      command=self.apply_filters,
                      bg=DARK_GRAY, fg=LEAVES_COLOR, selectcolor=BUTTON_BLACK,
                      font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        tk.Checkbutton(filter_frame, text="Show Autumn", variable=self.filter_show_autumn,
                      command=self.apply_filters,
                      bg=DARK_GRAY, fg=AUTUMN_COLOR, selectcolor=BUTTON_BLACK,
                      font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        tk.Checkbutton(filter_frame, text="Show Unclassified", variable=self.filter_show_unclassified,
                      command=self.apply_filters,
                      bg=DARK_GRAY, fg=WHITE, selectcolor=BUTTON_BLACK,
                      font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        
        # Separator
        tk.Frame(filter_frame, width=2, bg=LIGHTER_GRAY).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        tk.Checkbutton(filter_frame, text="Unlinked Items Only", variable=self.filter_unlinked_only,
                      command=self.apply_filters,
                      bg=DARK_GRAY, fg=WHITE, selectcolor=BUTTON_BLACK,
                      font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        tk.Label(filter_frame, text="(items not in any composite)", bg=DARK_GRAY, fg=LIGHTER_GRAY,
                font=("Arial", 8, "italic")).pack(side=tk.LEFT, padx=2)
        
        # Main content area
        content_frame = tk.Frame(self.root, bg=DARK_GRAY)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))
        
        # CENTER - Large working canvas (takes most space)
        canvas_panel = tk.Frame(content_frame, bg=DARKER_GRAY)
        canvas_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Canvas header with mode indicator
        canvas_header = tk.Frame(canvas_panel, bg=DARKER_GRAY)
        canvas_header.pack(fill=tk.X, pady=2)
        
        self.canvas_mode_label = tk.Label(canvas_header, text="WORKING CANVAS - Drag items to arrange", 
                bg=DARKER_GRAY, fg=WHITE, font=("Arial", 11, "bold"))
        self.canvas_mode_label.pack(side=tk.LEFT, padx=10)
        
        # Render selection controls
        render_controls = tk.Frame(canvas_header, bg=DARKER_GRAY)
        render_controls.pack(side=tk.RIGHT, padx=10)
        
        tk.Label(render_controls, text="Render:", bg=DARKER_GRAY, fg=WHITE,
                font=("Arial", 9)).pack(side=tk.LEFT, padx=(0, 5))
        
        self.render_selector = ttk.Combobox(render_controls, width=15, state='readonly')
        self.render_selector.pack(side=tk.LEFT, padx=(0, 5))
        self.render_selector.bind('<<ComboboxSelected>>', self.on_render_selected)
        
        tk.Button(render_controls, text="New", command=self.create_new_render,
                 bg=MUTED_BLUE, fg=WHITE, font=("Arial", 8, "bold")).pack(side=tk.LEFT, padx=2)
        
        tk.Button(render_controls, text="Save", command=self.save_current_render,
                 bg=MUTED_GREEN, fg=WHITE, font=("Arial", 8, "bold")).pack(side=tk.LEFT, padx=2)
        
        tk.Button(render_controls, text="Delete", command=self.delete_current_render,
                 bg="#CC4444", fg=WHITE, font=("Arial", 8, "bold")).pack(side=tk.LEFT, padx=2)
        
        self.preview_btn = tk.Button(canvas_header, text="PREVIEW FINAL RENDER",
                                     command=self.toggle_preview_mode,
                                     bg=MUTED_GREEN, fg=WHITE, font=("Arial", 10, "bold"))
        self.preview_btn.pack(side=tk.RIGHT, padx=10)
        
        # Preview display mode buttons (only visible in preview mode)
        self.preview_mode_frame = tk.Frame(canvas_header, bg=DARKER_GRAY)
        
        tk.Label(self.preview_mode_frame, text="Display:", bg=DARKER_GRAY, fg=WHITE,
                font=("Arial", 9)).pack(side=tk.LEFT, padx=(0, 5))
        
        self.altered_btn = tk.Button(self.preview_mode_frame, text="ALTERED",
                                     command=lambda: self.set_preview_display_mode('altered'),
                                     bg=MUTED_GREEN, fg=WHITE, font=("Arial", 9, "bold"), width=10)
        self.altered_btn.pack(side=tk.LEFT, padx=2)
        
        self.original_btn = tk.Button(self.preview_mode_frame, text="ORIGINAL",
                                      command=lambda: self.set_preview_display_mode('original'),
                                      bg=DARK_GRAY, fg=WHITE, font=("Arial", 9), width=10)
        self.original_btn.pack(side=tk.LEFT, padx=2)
        
        self.comparison_btn = tk.Button(self.preview_mode_frame, text="COMPARE",
                                        command=lambda: self.set_preview_display_mode('comparison'),
                                        bg=DARK_GRAY, fg=WHITE, font=("Arial", 9), width=10)
        self.comparison_btn.pack(side=tk.LEFT, padx=2)
        
        # Initially hidden
        # self.preview_mode_frame.pack(side=tk.RIGHT, padx=10)
        
        canvas_frame = tk.Frame(canvas_panel, bg=DARKER_GRAY)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg=BUTTON_BLACK, highlightthickness=0)
        canvas_vscroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        canvas_hscroll = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=canvas_vscroll.set, xscrollcommand=canvas_hscroll.set)
        
        canvas_vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        canvas_hscroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind canvas click for mode-based classification
        self.canvas.bind('<Button-1>', self.on_canvas_click)
        
        # Bind canvas events
        self.canvas.bind('<Button-1>', self.on_canvas_click)
        self.canvas.bind('<Button-2>', self.on_pan_start)  # Middle mouse button
        self.canvas.bind('<B2-Motion>', self.on_pan_drag)
        self.canvas.bind('<ButtonRelease-2>', self.on_pan_end)
        self.canvas.bind('<MouseWheel>', self.on_mouse_wheel)  # Zoom in preview mode
        
        # RIGHT panel - Item info and stats
        right_panel = tk.Frame(content_frame, bg=DARKER_GRAY, width=280)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        right_panel.pack_propagate(False)
        
        # Stats display
        tk.Label(right_panel, text="Item Statistics", bg=DARKER_GRAY, fg=WHITE, 
                font=("Arial", 10, "bold")).pack(pady=5)
        
        stats_frame = tk.Frame(right_panel, bg=LIGHTER_GRAY)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.stats_trunk_label = tk.Label(stats_frame, text="Trunk: 0", bg=LIGHTER_GRAY, 
                                          fg=TRUNK_COLOR, font=("Arial", 9, "bold"), anchor="w")
        self.stats_trunk_label.pack(fill=tk.X, padx=5, pady=2)
        
        self.stats_leaves_label = tk.Label(stats_frame, text="Leaves: 0", bg=LIGHTER_GRAY,
                                           fg=LEAVES_COLOR, font=("Arial", 9, "bold"), anchor="w")
        self.stats_leaves_label.pack(fill=tk.X, padx=5, pady=2)
        
        self.stats_autumn_label = tk.Label(stats_frame, text="Autumn: 0", bg=LIGHTER_GRAY,
                                           fg=AUTUMN_COLOR, font=("Arial", 9, "bold"), anchor="w")
        self.stats_autumn_label.pack(fill=tk.X, padx=5, pady=2)
        
        self.stats_unknown_label = tk.Label(stats_frame, text="Unclassified: 0", bg=LIGHTER_GRAY,
                                            fg=WHITE, font=("Arial", 9, "bold"), anchor="w")
        self.stats_unknown_label.pack(fill=tk.X, padx=5, pady=2)
        
        # Selected Item Details section
        tk.Label(right_panel, text="Selected Item", bg=DARKER_GRAY, fg=WHITE,
                font=("Arial", 10, "bold")).pack(pady=(15, 5))
        
        details_frame = tk.Frame(right_panel, bg=LIGHTER_GRAY)
        details_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Item name
        tk.Label(details_frame, text="Name:", bg=LIGHTER_GRAY, fg=WHITE,
                font=("Arial", 8, "bold"), anchor="w").pack(fill=tk.X, padx=5)
        self.detail_name_label = tk.Label(details_frame, text="None", bg=LIGHTER_GRAY,
                                          fg=MUTED_BLUE, font=("Arial", 8), anchor="w", wraplength=260)
        self.detail_name_label.pack(fill=tk.X, padx=5)
        
        # Classification
        tk.Label(details_frame, text="Type:", bg=LIGHTER_GRAY, fg=WHITE,
                font=("Arial", 8, "bold"), anchor="w").pack(fill=tk.X, padx=5)
        self.detail_type_label = tk.Label(details_frame, text="None", bg=LIGHTER_GRAY,
                                          fg=WHITE, font=("Arial", 8), anchor="w")
        self.detail_type_label.pack(fill=tk.X, padx=5)
        
        # Links section
        tk.Label(details_frame, text="Links:", bg=LIGHTER_GRAY, fg=MUTED_PURPLE,
                font=("Arial", 8, "bold"), anchor="w").pack(fill=tk.X, padx=5)
        
        self.detail_links_text = tk.Text(details_frame, bg=DARKER_GRAY, fg=WHITE,
                                         font=("Arial", 8), height=6, wrap=tk.WORD,
                                         relief=tk.FLAT, padx=5, pady=2)
        self.detail_links_text.pack(fill=tk.X, padx=5)
        self.detail_links_text.insert("1.0", "No item selected")
        self.detail_links_text.config(state=tk.DISABLED)
        
        # Height offset control (for leaves items)
        offset_control_frame = tk.Frame(details_frame, bg=LIGHTER_GRAY)
        offset_control_frame.pack(fill=tk.X, padx=5)
        
        tk.Label(offset_control_frame, text="Leaves Height Offset:", bg=LIGHTER_GRAY, fg=WHITE,
                font=("Arial", 8, "bold"), anchor="w").pack(side=tk.LEFT, padx=(0, 5))
        
        self.detail_offset_entry = tk.Entry(offset_control_frame, bg=DARKER_GRAY, fg=WHITE,
                                            font=("Arial", 8), width=8)
        self.detail_offset_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.detail_offset_entry.insert(0, "50")
        
        tk.Button(offset_control_frame, text="Save", command=self.save_height_offset,
                 bg=MUTED_BLUE, fg=WHITE, font=("Arial", 7, "bold")).pack(side=tk.LEFT)
        
        # Initially hide offset control
        offset_control_frame.pack_forget()
        self.offset_control_frame = offset_control_frame
        
        # Render properties control (per-item settings for current render)
        render_props_frame = tk.Frame(details_frame, bg=LIGHTER_GRAY)
        render_props_frame.pack(fill=tk.X, padx=5)
        
        tk.Label(render_props_frame, text="Render Properties:", bg=LIGHTER_GRAY, fg=WHITE,
                font=("Arial", 9, "bold"), anchor="w").pack(fill=tk.X, padx=5)
        
        self.render_props_label = tk.Label(render_props_frame, text="", 
                                           bg=LIGHTER_GRAY, fg=MUTED_BLUE,
                                           font=("Arial", 7, "italic"), anchor="w")
        self.render_props_label.pack(fill=tk.X, padx=5)
        
        # Exclude from render button
        self.exclude_from_render_btn = tk.Button(render_props_frame, 
                                                  text="Exclude from Render", 
                                                  command=self.toggle_item_excluded,
                                                  bg="#CC4444", fg=WHITE, 
                                                  font=("Arial", 8, "bold"))
        self.exclude_from_render_btn.pack(fill=tk.X, pady=1)
        
        # Use autumn variant button (for trunks with autumn)
        self.use_autumn_btn = tk.Button(render_props_frame, 
                                        text="Use Autumn Variant", 
                                        command=self.toggle_item_use_autumn,
                                        bg=AUTUMN_COLOR, fg=WHITE, 
                                        font=("Arial", 8, "bold"))
        self.use_autumn_btn.pack(fill=tk.X, pady=1)
        
        # Show leaves button (for trunks)
        self.show_leaves_btn = tk.Button(render_props_frame, 
                                         text="Hide Leaves (Trunk Only)", 
                                         command=self.toggle_item_show_leaves,
                                         bg=TRUNK_COLOR, fg=WHITE, 
                                         font=("Arial", 8, "bold"))
        self.show_leaves_btn.pack(fill=tk.X)
        
        # Initially hide render props control
        render_props_frame.pack_forget()
        self.render_props_frame = render_props_frame
        
        # Composites section
        tk.Label(right_panel, text="Tree Composites", bg=DARKER_GRAY, fg=WHITE,
                font=("Arial", 10, "bold")).pack(pady=(15, 5))
        
        comp_frame = tk.Frame(right_panel, bg=DARKER_GRAY)
        comp_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 10))
        comp_scroll = tk.Scrollbar(comp_frame)
        comp_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.composite_listbox = tk.Listbox(comp_frame, bg=LIGHTER_GRAY, fg=WHITE,
                                            yscrollcommand=comp_scroll.set, selectmode=tk.SINGLE,
                                            font=("Arial", 9))
        self.composite_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        comp_scroll.config(command=self.composite_listbox.yview)
        self.composite_listbox.bind('<<ListboxSelect>>', self.on_composite_select)
        
        # Add drag-and-drop from composite list to canvas
        self.composite_listbox.bind('<Button-1>', self.on_composite_list_press)
        self.composite_listbox.bind('<B1-Motion>', self.on_composite_list_drag)
        self.composite_listbox.bind('<ButtonRelease-1>', self.on_composite_list_release)
        self.composite_drag_data = {"dragging": False, "trunk_item": None}
        
        # Composite buttons
        comp_btn_frame = tk.Frame(right_panel, bg=DARKER_GRAY)
        comp_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(comp_btn_frame, text="Save Composites", command=self.save_composites,
                 bg=MUTED_BLUE, fg=WHITE, font=("Arial", 9, "bold")).pack(fill=tk.X, pady=2)
        tk.Button(comp_btn_frame, text="Load Composites", command=self.load_composites,
                 bg=MUTED_GREEN, fg=WHITE, font=("Arial", 9, "bold")).pack(fill=tk.X, pady=2)
        tk.Button(comp_btn_frame, text="Export Final Composite", command=self.export_all_composites,
                 bg=MUTED_PURPLE, fg=WHITE, font=("Arial", 9, "bold")).pack(fill=tk.X, pady=2)
        tk.Button(comp_btn_frame, text="Export Animated WebP", command=self.export_animated_webp,
                 bg="#FF6B35", fg=WHITE, font=("Arial", 9, "bold")).pack(fill=tk.X, pady=2)
    
    def on_pan_start(self, event):
        """Start panning with middle mouse button"""
        self.is_panning = True
        self.canvas.scan_mark(event.x, event.y)
        self.canvas.config(cursor="fleur")
        print(f"[Pan] Started at ({event.x}, {event.y})")
    
    def on_pan_drag(self, event):
        """Pan the canvas view with 1:1 movement"""
        if not self.is_panning:
            return
        
        # Use scan_dragto for 1:1 panning (gain=1 means 1 pixel of drag = 1 pixel of scroll)
        self.canvas.scan_dragto(event.x, event.y, gain=1)
    
    def on_pan_end(self, event):
        """End panning"""
        self.is_panning = False
        self.canvas.config(cursor="")
        print(f"[Pan] Ended at ({event.x}, {event.y})")
    
    def on_mouse_wheel(self, event):
        """Handle mouse wheel for zooming in preview mode"""
        if not self.preview_mode or not self.preview_base_image:
            return
        
        # Zoom in/out
        if event.delta > 0:
            self.preview_zoom *= 1.1
        else:
            self.preview_zoom /= 1.1
        
        # Clamp zoom
        self.preview_zoom = max(0.1, min(self.preview_zoom, 5.0))
        
        # Resize image
        new_width = int(self.preview_base_image.width * self.preview_zoom)
        new_height = int(self.preview_base_image.height * self.preview_zoom)
        
        zoomed_img = self.preview_base_image.resize((new_width, new_height), 
                                                     Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
        
        # Update canvas
        self.preview_photo = ImageTk.PhotoImage(zoomed_img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.preview_photo, anchor="nw")
        self.canvas.configure(scrollregion=(0, 0, new_width, new_height))
        
        print(f"[Zoom] Level: {self.preview_zoom:.2f}x")
    
    def get_trunk_positions_sorted(self):
        """Get all trunk items sorted by canvas position (top to bottom, left to right)"""
        trunk_positions = []
        for draggable in self.draggable_items:
            if draggable.item['type'] == 'trunk':
                trunk_positions.append({
                    'trunk': draggable.item,
                    'x': draggable.x,
                    'y': draggable.y
                })
        trunk_positions.sort(key=lambda t: (t['y'], t['x']))
        return trunk_positions
    
    def build_tree_sets_from_trunks(self, trunk_positions):
        """Build tree sets from trunk positions by finding linked leaves"""
        tree_sets = []
        for trunk_pos in trunk_positions:
            trunk_item = trunk_pos['trunk']
            metadata = trunk_item['metadata']
            
            # Get linked leaves names
            base_leaves_name = metadata.get('TREE_LINKED_LEAVES', '')
            autumn_leaves_name = metadata.get('TREE_LINKED_AUTUMN', '')
            
            print(f"[Tree Set] Building for trunk: {trunk_item['name']}")
            print(f"[Tree Set]   Direct base leaves link: {base_leaves_name or 'None'}")
            print(f"[Tree Set]   Direct autumn link: {autumn_leaves_name or 'None'}")
            
            # Find the actual items
            base_leaves = None
            autumn_leaves = None
            
            for draggable in self.draggable_items:
                if draggable.item['name'] == base_leaves_name:
                    base_leaves = draggable.item
                    print(f"[Tree Set]   Found base leaves: {base_leaves['name']}")
                elif draggable.item['name'] == autumn_leaves_name:
                    autumn_leaves = draggable.item
                    print(f"[Tree Set]   Found direct autumn: {autumn_leaves['name']}")
            
            # Check for autumn variant via base leaves (indirect path)
            if not autumn_leaves and base_leaves:
                base_leaves_metadata = base_leaves.get('metadata', {})
                print(f"[Tree Set]   Base leaves metadata keys: {list(base_leaves_metadata.keys())}")
                
                autumn_variant_name = base_leaves_metadata.get('TREE_LINKED_AUTUMN_VARIANT', '')
                print(f"[Tree Set]   Base leaves has autumn variant link: {autumn_variant_name or 'None'}")
                
                if autumn_variant_name:
                    print(f"[Tree Set]   Searching for autumn variant: '{autumn_variant_name}'")
                    for draggable in self.draggable_items:
                        if draggable.item['name'] == autumn_variant_name:
                            autumn_leaves = draggable.item
                            print(f"[Tree Set]   Found INDIRECT autumn variant: {autumn_leaves['name']}")
                            break
                    
                    if not autumn_leaves:
                        print(f"[Tree Set]   WARNING: Autumn variant '{autumn_variant_name}' not found in items!")
                        print(f"[Tree Set]   Available items: {[d.item['name'] for d in self.draggable_items[:5]]}...")
            
            tree_set = {
                'trunk': trunk_item,
                'base_leaves': base_leaves,
                'autumn_leaves': autumn_leaves
            }
            
            print(f"[Tree Set]   Final: base={base_leaves['name'] if base_leaves else 'None'}, autumn={autumn_leaves['name'] if autumn_leaves else 'None'}")
            tree_sets.append(tree_set)
        
        return tree_sets
    
    def find_original_by_hex(self, hex_id, original_folders):
        """Find original file by hex ID in list of folders"""
        print(f"[Original Search] Searching for hex 0x{hex_id:04X} in {len(original_folders)} folders")
        
        for orig_folder in original_folders:
            print(f"[Original Search] Checking folder: {orig_folder}")
            
            if not os.path.exists(orig_folder):
                print(f"[Original Search] ERROR: Folder does not exist!")
                continue
            
            try:
                files = os.listdir(orig_folder)
                print(f"[Original Search] Found {len(files)} files in folder")
                
                matching_files = []
                for filename in files:
                    if filename.lower().endswith(('.png', '.bmp')):
                        match = re.search(r'0x([0-9A-Fa-f]{4})', filename)
                        if match:
                            file_hex = int(match.group(1), 16)
                            if file_hex == hex_id:
                                full_path = os.path.join(orig_folder, filename)
                                print(f"[Original Search] FOUND MATCH: {filename}")
                                return full_path
                            matching_files.append(f"0x{file_hex:04X}")
                
                if matching_files:
                    print(f"[Original Search] Files in folder (first 10): {matching_files[:10]}")
                else:
                    print(f"[Original Search] No files with hex IDs found in folder")
                    
            except Exception as e:
                print(f"[Original Search] ERROR reading folder: {e}")
        
        print(f"[Original Search] NOT FOUND: 0x{hex_id:04X}")
        return None
    
    def get_original_folders(self):
        """Get list of folders to search for original files"""
        original_folders = []
        
        print(f"[Get Original Folders] === CHECKING ORIGINAL FOLDER SOURCES ===")
        
        # Local original subfolder
        local_original = os.path.join(self.folder_path, "original")
        print(f"[Get Original Folders] Local 'original' subfolder: {local_original}")
        if os.path.exists(local_original):
            print(f"[Get Original Folders]   EXISTS - Adding to search list")
            original_folders.append(local_original)
        else:
            print(f"[Get Original Folders]   DOES NOT EXIST - Skipping")
        
        # Global original folder - check both stored variable and entry widget
        print(f"[Get Original Folders] Stored global_original_folder: '{self.global_original_folder}'")
        
        # Try stored variable first
        if self.global_original_folder and self.global_original_folder.strip():
            global_path = self.global_original_folder.strip()
            print(f"[Get Original Folders] Using stored variable: {global_path}")
            if os.path.exists(global_path):
                print(f"[Get Original Folders]   EXISTS - Adding to search list")
                original_folders.append(global_path)
            else:
                print(f"[Get Original Folders]   DOES NOT EXIST - Path is invalid!")
        else:
            # Fallback to entry widget
            global_original = self.global_original_entry.get().strip()
            print(f"[Get Original Folders] Stored variable empty, checking entry widget: '{global_original}'")
            if global_original:
                if os.path.exists(global_original):
                    print(f"[Get Original Folders]   EXISTS - Adding to search list")
                    original_folders.append(global_original)
                    # Update stored variable
                    self.global_original_folder = global_original
                else:
                    print(f"[Get Original Folders]   DOES NOT EXIST - Path is invalid!")
            else:
                print(f"[Get Original Folders]   Entry widget is also empty!")
        
        print(f"[Get Original Folders] === TOTAL FOLDERS TO SEARCH: {len(original_folders)} ===")
        return original_folders
    
    def toggle_preview_mode(self):
        """Toggle between working canvas and final render preview"""
        self.preview_mode = not self.preview_mode
        
        if self.preview_mode:
            print("[Preview] Entering FINAL RENDER PREVIEW mode")
            self.canvas_mode_label.config(text="FINAL RENDER PREVIEW - Click trees to select")
            self.preview_btn.config(text="BACK TO CANVAS", bg="#CC4444")
            self.preview_mode_frame.pack(side=tk.RIGHT, padx=10)  # Show display mode buttons
            self.preview_display_mode = 'altered'  # Reset to altered
            self.set_preview_display_mode('altered')  # Update button states
            self.render_final_preview()
            self.update_composite_list()  # Update list with color-coded status
        else:
            print("[Preview] Returning to WORKING CANVAS mode")
            self.canvas_mode_label.config(text="WORKING CANVAS - Drag items to arrange")
            self.preview_btn.config(text="PREVIEW FINAL RENDER", bg=MUTED_GREEN)
            self.preview_mode_frame.pack_forget()  # Hide display mode buttons
            self.restore_canvas()
    
    def set_preview_display_mode(self, mode):
        """Set the preview display mode and update UI"""
        if mode == self.preview_display_mode:
            return  # Already in this mode
        
        self.preview_display_mode = mode
        print(f"[Preview Display] Mode set to: {mode}")
        
        # Update button styles
        if mode == 'altered':
            self.altered_btn.config(bg=MUTED_GREEN, font=("Arial", 9, "bold"))
            self.original_btn.config(bg=DARK_GRAY, font=("Arial", 9))
            self.comparison_btn.config(bg=DARK_GRAY, font=("Arial", 9))
        elif mode == 'original':
            self.altered_btn.config(bg=DARK_GRAY, font=("Arial", 9))
            self.original_btn.config(bg=MUTED_GREEN, font=("Arial", 9, "bold"))
            self.comparison_btn.config(bg=DARK_GRAY, font=("Arial", 9))
        elif mode == 'comparison':
            self.altered_btn.config(bg=DARK_GRAY, font=("Arial", 9))
            self.original_btn.config(bg=DARK_GRAY, font=("Arial", 9))
            self.comparison_btn.config(bg=MUTED_GREEN, font=("Arial", 9, "bold"))
        
        # Switch display without re-rendering (preserves camera position)
        self.switch_preview_display()
    
    def switch_preview_display(self):
        """Switch between altered/original/comparison without re-rendering"""
        print(f"[Preview Display] Switching to {self.preview_display_mode} mode")
        
        # Check if images exist (they're generated during render_final_preview)
        if not hasattr(self, 'preview_altered_image'):
            print(f"[Preview Display] Images not yet generated, skipping switch")
            return
        
        # Select the appropriate stored image (base, unzoomed)
        if self.preview_display_mode == 'altered':
            base_img = self.preview_altered_image
            print(f"[Preview Display] Selected altered image: {base_img.size}")
        elif self.preview_display_mode == 'original':
            base_img = self.preview_original_image
            print(f"[Preview Display] Selected original image: {base_img.size}")
        elif self.preview_display_mode == 'comparison':
            base_img = self.preview_comparison_image
            print(f"[Preview Display] Selected comparison image: {base_img.size}")
        else:
            base_img = self.preview_altered_image
        
        # Apply current zoom to the selected image
        if self.preview_zoom != 1.0:
            new_width = int(base_img.width * self.preview_zoom)
            new_height = int(base_img.height * self.preview_zoom)
            zoomed_img = base_img.resize((new_width, new_height), 
                                        Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
            print(f"[Preview Display] Applied zoom {self.preview_zoom:.2f}x: {base_img.size} -> {zoomed_img.size}")
        else:
            zoomed_img = base_img
            print(f"[Preview Display] No zoom applied, using base size: {zoomed_img.size}")
        
        # Update stored preview images
        self.preview_base_image = base_img
        self.preview_image = zoomed_img
        
        # CRITICAL: Create PhotoImage and keep strong reference
        photo = ImageTk.PhotoImage(zoomed_img)
        self.preview_photo = photo  # Keep reference to prevent garbage collection
        
        # Get current canvas scroll position in PIXELS
        canvas_x = self.canvas.canvasx(0)
        canvas_y = self.canvas.canvasy(0)
        print(f"[Preview Display] Current canvas position (pixels): x={canvas_x}, y={canvas_y}")
        
        # Update canvas display
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.preview_photo, anchor="nw")
        self.canvas.configure(scrollregion=(0, 0, zoomed_img.width, zoomed_img.height))
        
        # Restore exact pixel position using scan
        # This is more accurate than moveto which uses fractions
        self.canvas.scan_mark(0, 0)
        self.canvas.scan_dragto(int(-canvas_x), int(-canvas_y), gain=1)
        print(f"[Preview Display] Restored exact position: x={canvas_x}, y={canvas_y}")
        
        print(f"[Preview Display] Switched to {self.preview_display_mode} (zoom: {self.preview_zoom:.2f}x, camera position preserved)")
    
    def render_final_preview(self):
        """Render final composite preview with all linked trees"""
        print("[Preview] Generating final render...")
        
        # Get sorted trunk positions and build tree sets
        trunk_positions = self.get_trunk_positions_sorted()
        print(f"[Preview] Found {len(trunk_positions)} trunks, sorted by canvas position")
        
        tree_sets = self.build_tree_sets_from_trunks(trunk_positions)
        print(f"[Preview] Ordered tree sets by canvas arrangement")
        
        if not tree_sets:
            print("[Preview] No tree sets to render")
            return
        
        # Render composites for each tree set using per-item properties
        composites = []
        for tree_set in tree_sets:
            trunk_item = tree_set['trunk']
            if not trunk_item:
                continue
            
            # Get render properties for this specific trunk item
            props = self.get_item_render_props(trunk_item)
            
            # Skip if excluded
            if props['excluded']:
                print(f"[Preview] Skipping excluded item: {trunk_item['name']}")
                continue
            
            # Check if trunk has any leaves at all
            has_any_leaves = tree_set['base_leaves'] or tree_set['autumn_leaves']
            
            # Trunk-only mode: render just the trunk (either by choice or no leaves available)
            if not props['show_leaves'] or not has_any_leaves:
                trunk_img = Image.open(trunk_item['path']).convert('RGBA')
                trunk_masked = apply_brightness_mask(trunk_img)
                trunk_cropped = trunk_masked.crop(trunk_masked.getbbox())
                composites.append(('trunk_only', trunk_cropped, tree_set))
                if not has_any_leaves:
                    print(f"[Preview] Rendering trunk-only (no leaves): {trunk_item['name']}")
                continue
            
            # Use autumn variant if set
            if props['use_autumn'] and tree_set['autumn_leaves']:
                autumn_render = self.render_tree_set(
                    trunk_item,
                    tree_set['autumn_leaves']
                )
                composites.append(('autumn', autumn_render, tree_set))
            # Use base leaves
            elif tree_set['base_leaves']:
                base_render = self.render_tree_set(
                    trunk_item, 
                    tree_set['base_leaves']
                )
                composites.append(('base', base_render, tree_set))
            # Fallback: if no base leaves but has autumn, show autumn
            elif tree_set['autumn_leaves']:
                autumn_render = self.render_tree_set(
                    trunk_item,
                    tree_set['autumn_leaves']
                )
                composites.append(('autumn', autumn_render, tree_set))
        
        print(f"[Preview] Rendered {len(composites)} altered tree sets")
        
        # Store altered composites for comparison mode
        altered_composites = composites
        
        # ALWAYS generate original composites (so they're ready when user switches)
        print(f"[Preview Display] Generating original composites...")
        original_composites = self.generate_original_composites(altered_composites)
        print(f"[Preview Display] Generated {len(original_composites)} original composites")
        
        # Auto-register new items to config
        new_items_count = 0
        config = self.render_configs.get(self.current_render, {})
        if 'item_properties' not in config:
            config['item_properties'] = {}
        
        for comp_type, comp_img, tree_set in composites:
            trunk_item = tree_set['trunk']
            if trunk_item:
                item_id = self.get_item_render_id(trunk_item)
                if item_id not in config['item_properties']:
                    # Add with default properties
                    config['item_properties'][item_id] = {
                        'excluded': False,
                        'use_autumn': False,
                        'show_leaves': True
                    }
                    new_items_count += 1
                    print(f"[Preview] New item registered: {trunk_item['name']}")
        
        if new_items_count > 0:
            self.render_configs[self.current_render] = config
            self.save_render_config(self.current_render)
            print(f"[Preview] Auto-registered {new_items_count} new items to '{self.current_render}'")
        
        # Generate all three display versions (altered, original, comparison)
        # This allows switching between them without re-rendering
        
        # 1. ALTERED version
        altered_image = self.arrange_composites_16_9(altered_composites)
        canvas_width = altered_image.width + 200
        canvas_height = altered_image.height + 200
        altered_canvas = Image.new('RGBA', (canvas_width, canvas_height), (40, 40, 40, 255))
        offset_x = (canvas_width - altered_image.width) // 2
        offset_y = (canvas_height - altered_image.height) // 2
        altered_canvas.paste(altered_image, (offset_x, offset_y), altered_image)
        
        # 2. ORIGINAL version (if originals were generated)
        if original_composites:
            original_image = self.arrange_composites_16_9(original_composites)
            original_canvas = Image.new('RGBA', (canvas_width, canvas_height), (40, 40, 40, 255))
            original_canvas.paste(original_image, (offset_x, offset_y), original_image)
        else:
            original_canvas = altered_canvas.copy()
        
        # 3. COMPARISON version (overlay with bounds)
        if original_composites:
            # Both should be same size - verify
            if altered_image.size != original_image.size:
                print(f"[Compare] WARNING: Size mismatch! Altered: {altered_image.size}, Original: {original_image.size}")
            
            # Create base with altered image
            comparison_image = altered_image.copy()
            
            # Draw green bounds for altered
            draw = ImageDraw.Draw(comparison_image)
            for comp_type, comp_img, tree_set, bounds in self.preview_composites:
                x1, y1, x2, y2 = bounds
                for i in range(3):
                    draw.rectangle([x1-i, y1-i, x2+i, y2+i], outline=(0, 255, 0))  # Green
            
            # Overlay original with 50% opacity and draw magenta bounds
            original_overlay = original_image.copy()
            draw_orig = ImageDraw.Draw(original_overlay)
            for comp_type, comp_img, tree_set, bounds in self.preview_composites:
                x1, y1, x2, y2 = bounds
                for i in range(3):
                    draw_orig.rectangle([x1-i, y1-i, x2+i, y2+i], outline=(255, 0, 255))  # Magenta
            
            # Blend original at 50% opacity on top of altered
            comparison_image = Image.blend(comparison_image, original_overlay, alpha=0.5)
            
            comparison_canvas = Image.new('RGBA', (canvas_width, canvas_height), (40, 40, 40, 255))
            comparison_canvas.paste(comparison_image, (offset_x, offset_y), comparison_image)
        else:
            comparison_canvas = altered_canvas.copy()
        
        # Store all three versions
        self.preview_altered_image = altered_canvas
        self.preview_original_image = original_canvas
        self.preview_comparison_image = comparison_canvas
        
        # Select which one to display based on current mode
        if self.preview_display_mode == 'altered':
            canvas_img = altered_canvas
        elif self.preview_display_mode == 'original':
            canvas_img = original_canvas
        elif self.preview_display_mode == 'comparison':
            canvas_img = comparison_canvas
        else:
            canvas_img = altered_canvas
        
        # Store preview images for zooming and redrawing with bounds
        self.preview_image = canvas_img
        self.preview_base_image = canvas_img.copy()
        self.preview_zoom = 1.0  # Reset zoom
        
        # Display on canvas
        self.preview_photo = ImageTk.PhotoImage(canvas_img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.preview_photo, anchor="nw")
        self.canvas.configure(scrollregion=(0, 0, canvas_img.width, canvas_img.height))
        
        print(f"[Preview] Final render size: {altered_image.width}x{altered_image.height}")
        print(f"[Preview] Canvas size: {canvas_width}x{canvas_height}")
    
    def generate_original_composites(self, altered_composites):
        """Generate original composites matching altered layout"""
        print(f"[Original] === STARTING ORIGINAL COMPOSITE GENERATION ===")
        print(f"[Original] DEBUG: self.global_original_folder = '{self.global_original_folder}'")
        print(f"[Original] DEBUG: Entry widget value = '{self.global_original_entry.get()}'")
        
        original_composites = []
        original_folders = self.get_original_folders()
        
        print(f"[Original] Global original folder variable: '{self.global_original_folder}'")
        print(f"[Original] Found {len(original_folders)} original folders to search:")
        for i, folder in enumerate(original_folders):
            print(f"[Original]   [{i+1}] {folder}")
        
        if not original_folders:
            print(f"[Original] ERROR: No original folders found! Cannot generate originals.")
            print(f"[Original] Using altered composites as fallback.")
            return altered_composites
        
        for comp_type, comp_img, tree_set in altered_composites:
            trunk_item = tree_set['trunk']
            trunk_hex = trunk_item['hex_id']
            trunk_name = trunk_item['name']
            
            print(f"[Original] ---")
            print(f"[Original] Looking for trunk: {trunk_name} (0x{trunk_hex:04X})")
            
            # Find original trunk
            original_trunk_path = self.find_original_by_hex(trunk_hex, original_folders)
            if not original_trunk_path:
                print(f"[Original] ERROR: Trunk 0x{trunk_hex:04X} not found in any original folder!")
                print(f"[Original] Searched folders: {original_folders}")
                print(f"[Original] Using altered composite as fallback")
                original_composites.append((comp_type, comp_img, tree_set))
                continue
            
            print(f"[Original] Found trunk at: {original_trunk_path}")
            
            if comp_type == 'trunk_only':
                # Just trunk
                orig_trunk_img = Image.open(original_trunk_path).convert('RGBA')
                orig_trunk_masked = apply_brightness_mask(orig_trunk_img)
                orig_trunk_cropped = orig_trunk_masked.crop(orig_trunk_masked.getbbox())
                original_composites.append(('trunk_only', orig_trunk_cropped, tree_set))
            else:
                # Trunk + leaves
                leaves_item = tree_set['autumn_leaves'] if comp_type == 'autumn' else tree_set['base_leaves']
                if not leaves_item:
                    leaves_item = tree_set['base_leaves'] or tree_set['autumn_leaves']
                
                if leaves_item:
                    leaves_hex = leaves_item['hex_id']
                    original_leaves_path = self.find_original_by_hex(leaves_hex, original_folders)
                    
                    if original_leaves_path:
                        print(f"[Original] Found leaves at: {original_leaves_path}")
                        
                        # Load original images
                        orig_trunk_img = Image.open(original_trunk_path).convert('RGBA')
                        orig_leaves_img = Image.open(original_leaves_path).convert('RGBA')
                        
                        # Load altered images for comparison
                        altered_trunk_img = Image.open(trunk_item['path']).convert('RGBA')
                        altered_leaves_img = Image.open(leaves_item['path']).convert('RGBA')
                        
                        print(f"[Original] Original trunk FULL size: {orig_trunk_img.size}, Altered trunk FULL size: {altered_trunk_img.size}")
                        print(f"[Original] Original leaves FULL size: {orig_leaves_img.size}, Altered leaves FULL size: {altered_leaves_img.size}")
                        
                        # Check if FULL dimensions match
                        if orig_trunk_img.size != altered_trunk_img.size:
                            print(f"[Original] WARNING: Trunk 0x{trunk_hex:04X} FULL dimension mismatch!")
                        if orig_leaves_img.size != altered_leaves_img.size:
                            print(f"[Original] WARNING: Leaves 0x{leaves_hex:04X} FULL dimension mismatch!")
                        
                        # Apply masking but DO NOT CROP - use full dimensions
                        orig_trunk_masked = apply_brightness_mask(orig_trunk_img, threshold=5)
                        orig_leaves_masked = apply_brightness_mask(orig_leaves_img, threshold=5)
                        
                        # Get offset from altered metadata
                        leaves_metadata = leaves_item.get('metadata', {})
                        offset = int(leaves_metadata.get('TREE_LEAVES_HEIGHT_OFFSET', 50))
                        print(f"[Original] Using offset: {offset}")
                        
                        # Calculate composite size using FULL image dimensions (not cropped)
                        comp_width = max(orig_trunk_img.width, orig_leaves_img.width)
                        comp_height = max(orig_trunk_img.height, orig_leaves_img.height + offset)
                        
                        print(f"[Original] Calculated composite size (from FULL dims): {comp_width}x{comp_height}")
                        print(f"[Original] Altered composite size: {comp_img.width}x{comp_img.height}")
                        
                        # Create composite
                        orig_composite = Image.new('RGBA', (comp_width, comp_height), (0, 0, 0, 0))
                        
                        # Place trunk at bottom center using FULL dimensions
                        trunk_x = (comp_width - orig_trunk_img.width) // 2
                        trunk_y = comp_height - orig_trunk_img.height
                        print(f"[Original] Trunk position: ({trunk_x}, {trunk_y}) with FULL size {orig_trunk_img.size}")
                        orig_composite.paste(orig_trunk_masked, (trunk_x, trunk_y), orig_trunk_masked)
                        
                        # Place leaves at bottom center, then offset upward using FULL dimensions
                        leaves_x = (comp_width - orig_leaves_img.width) // 2
                        leaves_y = comp_height - orig_leaves_img.height - offset
                        leaves_y = max(0, leaves_y)  # Ensure leaves don't go off top
                        print(f"[Original] Leaves position: ({leaves_x}, {leaves_y}) with FULL size {orig_leaves_img.size}")
                        orig_composite.paste(orig_leaves_masked, (leaves_x, leaves_y), orig_leaves_masked)
                        
                        print(f"[Original] Final composite: {orig_composite.size}")
                        
                        if orig_composite.size != comp_img.size:
                            print(f"[Original] WARNING: Final composite size mismatch!")
                            print(f"[Original]   Expected (altered): {comp_img.size}, Got (original): {orig_composite.size}")
                        
                        original_composites.append((comp_type, orig_composite, tree_set))
                    else:
                        print(f"[Original] Leaves 0x{leaves_hex:04X} not found, using altered")
                        original_composites.append((comp_type, comp_img, tree_set))
                else:
                    original_composites.append((comp_type, comp_img, tree_set))
        
        return original_composites
    
    def draw_comparison_bounds(self, image, composites, color):
        """Draw colored bounds around each tree in the image"""
        img_with_bounds = image.copy()
        draw = ImageDraw.Draw(img_with_bounds)
        
        # Get bounds from arrange_composites_16_9 (stored in self.preview_composites)
        for comp_type, comp_img, tree_set, bounds in self.preview_composites:
            x1, y1, x2, y2 = bounds
            # Draw thick colored rectangle
            for i in range(3):
                draw.rectangle([x1-i, y1-i, x2+i, y2+i], outline=color)
        
        return img_with_bounds
    
    def render_tree_set(self, trunk_item, leaves_item, leaves_height_offset=50):
        """Render a single tree set (trunk + leaves combined) with in-game masking
        
        Both trunk and leaves are anchored at bottom-center (ground level).
        Leaves height offset is how much to move leaves UP from ground (positive = up).
        Uses FULL image dimensions (not cropped) for consistent positioning.
        """
        # Load images
        trunk_img = Image.open(trunk_item['path']).convert('RGBA')
        leaves_img = Image.open(leaves_item['path']).convert('RGBA')
        
        # Apply brightness-based masking (simulates in-game 1-bit masking)
        trunk_masked = apply_brightness_mask(trunk_img, threshold=5)
        leaves_masked = apply_brightness_mask(leaves_img, threshold=5)
        
        # DO NOT CROP - use full dimensions for positioning
        # This ensures altered and original composites align perfectly
        
        # Get leaves height offset from LEAVES item's metadata (each leaf type has its own offset)
        leaves_metadata = leaves_item.get('metadata', {})
        offset = int(leaves_metadata.get('TREE_LEAVES_HEIGHT_OFFSET', leaves_height_offset))
        
        # Calculate composite size using FULL image dimensions
        # Both are anchored at bottom, leaves offset upward
        # Width: max of both images (full size)
        # Height: max of (trunk height, leaves height + offset) (full size)
        comp_width = max(trunk_img.width, leaves_img.width)
        comp_height = max(trunk_img.height, leaves_img.height + offset)
        
        # Create composite
        composite = Image.new('RGBA', (comp_width, comp_height), (0, 0, 0, 0))
        
        # Place trunk at bottom center using FULL dimensions (ground level = bottom of canvas)
        trunk_x = (comp_width - trunk_img.width) // 2
        trunk_y = comp_height - trunk_img.height
        composite.paste(trunk_masked, (trunk_x, trunk_y), trunk_masked)
        
        # Place leaves at bottom center, then offset upward using FULL dimensions
        # Ground level is at comp_height, leaves bottom goes there, then move up by offset
        leaves_x = (comp_width - leaves_img.width) // 2
        leaves_y = comp_height - leaves_img.height - offset  # Positive offset moves UP
        
        # Ensure leaves don't go off top
        leaves_y = max(0, leaves_y)
        
        composite.paste(leaves_masked, (leaves_x, leaves_y), leaves_masked)
        
        return composite
    
    def arrange_composites_16_9(self, composites):
        """Arrange tree sets in 16:9 layout for final composite render with proper padding on pure black background"""
        if not composites:
            return Image.new('RGBA', (1920, 1080), (0, 0, 0, 255))
        
        # Padding constants
        PADDING_X = 10  # Horizontal padding between trees
        PADDING_Y = 5   # Vertical padding
        
        # Get composite images
        comp_images = [comp[1] for comp in composites]
        
        # Calculate optimal layout
        num_composites = len(composites)
        
        # Try different row configurations to find best fit
        best_layout = None
        best_score = float('inf')
        
        for cols in range(1, num_composites + 1):
            rows = (num_composites + cols - 1) // cols
            
            # Calculate how many items in the last row
            items_in_last_row = num_composites - (rows - 1) * cols
            row_fill_ratio = items_in_last_row / cols  # How full is the last row (0.0 to 1.0)
            
            # Calculate dimensions for this layout
            max_width_per_col = [0] * cols
            max_height_per_row = [0] * rows
            
            for i, img in enumerate(comp_images):
                col = i % cols
                row = i // cols
                max_width_per_col[col] = max(max_width_per_col[col], img.width)
                max_height_per_row[row] = max(max_height_per_row[row], img.height)
            
            # Total dimensions with padding
            total_width = sum(max_width_per_col) + PADDING_X * (cols + 1)
            total_height = sum(max_height_per_row) + PADDING_Y * (rows + 1)
            
            # Check aspect ratio (16:9 = 1.778)
            aspect = total_width / total_height if total_height > 0 else 0
            aspect_diff = abs(aspect - 1.778)
            
            # Calculate score: prioritize row fill, then aspect ratio
            # Penalize sparse last rows heavily (less than 50% filled)
            fill_penalty = 0
            if row_fill_ratio < 0.5:
                fill_penalty = (0.5 - row_fill_ratio) * 10  # Heavy penalty for sparse rows
            elif row_fill_ratio < 0.75:
                fill_penalty = (0.75 - row_fill_ratio) * 3  # Moderate penalty
            
            # Combined score: aspect ratio difference + fill penalty
            score = aspect_diff + fill_penalty
            
            if score < best_score:
                best_score = score
                best_layout = {
                    'cols': cols,
                    'rows': rows,
                    'width': total_width,
                    'height': total_height,
                    'col_widths': max_width_per_col,
                    'row_heights': max_height_per_row,
                    'fill_ratio': row_fill_ratio
                }
        
        # Create final image with calculated dimensions
        final_width = best_layout['width']
        final_height = best_layout['height']
        final_img = Image.new('RGBA', (final_width, final_height), (0, 0, 0, 255))
        
        # Clear preview composites list for click detection
        self.preview_composites = []
        
        # Place composites in grid
        y_offset = PADDING_Y
        for row in range(best_layout['rows']):
            x_offset = PADDING_X
            row_height = best_layout['row_heights'][row]
            
            for col in range(best_layout['cols']):
                idx = row * best_layout['cols'] + col
                if idx >= len(composites):
                    break
                
                comp_type, comp_img, tree_set = composites[idx]
                col_width = best_layout['col_widths'][col]
                
                # Center in cell, bottom-align
                x_pos = x_offset + (col_width - comp_img.width) // 2
                y_pos = y_offset + (row_height - comp_img.height)  # Bottom-align in row
                
                # Store bounds for click detection
                bounds = (x_pos, y_pos, x_pos + comp_img.width, y_pos + comp_img.height)
                self.preview_composites.append((comp_type, comp_img, tree_set, bounds))
                
                # Paste composite
                final_img.paste(comp_img, (x_pos, y_pos), comp_img)
                
                # Draw blue bounds for new items (not in config yet)
                trunk_item = tree_set['trunk']
                if trunk_item:
                    item_id = self.get_item_render_id(trunk_item)
                    config = self.render_configs.get(self.current_render, {})
                    item_props = config.get('item_properties', {})
                    
                    # If item not in config, it's new - draw blue bounds
                    if item_id not in item_props:
                        draw = ImageDraw.Draw(final_img)
                        new_item_color = (100, 150, 255)  # Light blue
                        # Draw thick blue border
                        for i in range(3):
                            draw.rectangle([x_pos-i, y_pos-i, x_pos+comp_img.width+i, y_pos+comp_img.height+i], 
                                         outline=new_item_color)
                
                x_offset += col_width + PADDING_X
            
            y_offset += row_height + PADDING_Y
        
        print(f"[Layout] {best_layout['cols']}x{best_layout['rows']} grid, {final_width}x{final_height}px, aspect: {final_width/final_height:.2f}, last row fill: {best_layout['fill_ratio']:.0%}")
        
        return final_img
    
    def restore_canvas(self):
        """Restore working canvas with draggable items"""
        self.canvas.delete("all")
        
        # Recreate all draggable items' canvas elements
        for draggable in self.draggable_items:
            # Recreate image and text on canvas
            draggable.image_item = self.canvas.create_image(draggable.x, draggable.y, 
                                                            image=draggable.photo, anchor="nw")
            draggable.text_item = self.canvas.create_text(
                draggable.x + draggable.thumbnail_size[0]//2, 
                draggable.y + draggable.thumbnail_size[1] + 5,
                text=f"0x{draggable.item['hex_id']:04X}", 
                anchor="n", fill=WHITE, font=("Arial", 8))
            
            # Rebind events
            self.canvas.tag_bind(draggable.image_item, '<Button-1>', draggable.on_press)
            self.canvas.tag_bind(draggable.image_item, '<B1-Motion>', draggable.on_drag)
            self.canvas.tag_bind(draggable.image_item, '<ButtonRelease-1>', draggable.on_release)
            self.canvas.tag_bind(draggable.text_item, '<Button-1>', draggable.on_press)
        
        # Restore bounds and links
        self.update_all_bounds()
        self.update_link_lines()
        
        # Restore scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def browse_folder(self):
        """Browse for tree folder"""
        folder = filedialog.askdirectory(title="Select Tree Folder")
        if folder:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)
    
    def browse_global_original(self):
        """Browse for global original folder"""
        folder = filedialog.askdirectory(title="Select Global Original Folder")
        if folder:
            self.global_original_entry.delete(0, tk.END)
            self.global_original_entry.insert(0, folder)
            self.global_original_folder = folder
            print(f"[Global Original] Set to: {folder}")
            
            # Save to current render config
            self.save_render_config(self.current_render)
            print(f"[Global Original] Saved to render '{self.current_render}'")
            
            # If in preview mode, regenerate to use new original folder
            if self.preview_mode:
                print(f"[Global Original] Regenerating preview with new original folder...")
                self.render_final_preview()
    
    def on_global_original_changed(self, event=None):
        """Called when global original entry is manually edited"""
        new_path = self.global_original_entry.get().strip()
        if new_path != self.global_original_folder:
            self.global_original_folder = new_path
            print(f"[Global Original] Entry changed to: '{new_path}'")
            # Save to current render config
            self.save_render_config(self.current_render)
            print(f"[Global Original] Saved to render '{self.current_render}'")
            
            # If in preview mode, regenerate to use new original folder
            if self.preview_mode:
                print(f"[Global Original] Regenerating preview with new original folder...")
                self.render_final_preview()
    
    def toggle_mode(self, mode):
        """Toggle mode on/off - clicking same mode exits to normal"""
        current_mode = self.classification_mode.get()
        
        # If clicking the same mode, exit to normal mode
        if current_mode == mode:
            print(f"[Mode] Toggling off {mode}, returning to normal")
            self.set_mode('none')
        else:
            print(f"[Mode] Switching from {current_mode} to {mode}")
            self.set_mode(mode)
    
    def set_mode(self, mode):
        """Set classification mode and update button styles"""
        self.classification_mode.set(mode)
        
        # Clear link mode state when switching modes
        if mode != 'link':
            self.clear_link_mode()
        
        # Reset all buttons to off state
        self.mode_trunk_btn.config(bg=LIGHTER_GRAY, relief=tk.RAISED)
        self.mode_leaves_btn.config(bg=LIGHTER_GRAY, relief=tk.RAISED)
        self.mode_autumn_btn.config(bg=LIGHTER_GRAY, relief=tk.RAISED)
        self.mode_none_btn.config(bg=LIGHTER_GRAY, relief=tk.RAISED)
        self.mode_link_btn.config(bg=LIGHTER_GRAY, relief=tk.RAISED)
        self.mode_unlink_btn.config(bg=LIGHTER_GRAY, relief=tk.RAISED)
        
        # Highlight active mode
        if mode == 'trunk':
            self.mode_trunk_btn.config(bg=TRUNK_COLOR, relief=tk.SUNKEN)
            print("[Mode] SET TRUNK mode active")
        elif mode == 'leaves':
            self.mode_leaves_btn.config(bg=LEAVES_COLOR, relief=tk.SUNKEN)
            print("[Mode] SET LEAVES mode active")
        elif mode == 'leaves_autumn':
            self.mode_autumn_btn.config(bg=AUTUMN_COLOR, relief=tk.SUNKEN)
            print("[Mode] SET AUTUMN mode active")
        elif mode == 'link':
            self.mode_link_btn.config(bg=MUTED_PURPLE, relief=tk.SUNKEN)
            print("[Mode] LINK mode active - Click two items to link them")
        elif mode == 'unlink':
            self.mode_unlink_btn.config(bg="#CC4444", relief=tk.SUNKEN)  # Red for unlink
            print("[Mode] UNLINK mode active - Click item to remove all its links")
        else:
            self.mode_none_btn.config(bg=MUTED_BLUE, relief=tk.SUNKEN)
            print("[Mode] MOVE TOOL mode active")
    
    def on_canvas_click(self, event):
        """Handle canvas click for mode-based classification or linking"""
        # Convert event coordinates to canvas coordinates (accounting for scroll)
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Handle preview mode clicks differently
        if self.preview_mode:
            self.on_preview_click(canvas_x, canvas_y)
            return
        
        mode = self.classification_mode.get()
        
        print(f"[Canvas Click] Mode: {mode}, Screen: ({event.x}, {event.y}), Canvas: ({canvas_x}, {canvas_y})")
        
        if mode == 'none':
            print("[Canvas Click] Move tool mode - updating selected item")
            # In move mode, update selected item details
            clicked_item = self.canvas.find_closest(canvas_x, canvas_y)
            for draggable in self.draggable_items:
                if draggable.image_item == clicked_item[0] or draggable.text_item == clicked_item[0]:
                    self.update_selected_item_details(draggable.item)
                    break
            return  # Normal mode, no classification
        
        # Find which item was clicked using canvas coordinates
        clicked_item = self.canvas.find_closest(canvas_x, canvas_y)
        print(f"[Canvas Click] Closest canvas item: {clicked_item}")
        
        if not clicked_item:
            print("[Canvas Click] No item found")
            return
        
        # Find the DraggableTreeItem that owns this canvas item
        found = False
        for draggable in self.draggable_items:
            if draggable.image_item == clicked_item[0] or draggable.text_item == clicked_item[0]:
                print(f"[Canvas Click] Found item: {draggable.item['name']} (0x{draggable.item['hex_id']:04X})")
                
                # Update selected item details (for all modes)
                self.update_selected_item_details(draggable.item)
                
                if mode == 'link':
                    # Handle link mode
                    self.handle_link_mode_click(draggable)
                elif mode == 'unlink':
                    # Handle unlink mode
                    self.unlink_item(draggable.item)
                else:
                    # Handle classification mode
                    print(f"[Canvas Click] Current type: {draggable.item['type']}, Setting to: {mode}")
                    self.classify_canvas_item(draggable, mode)
                
                found = True
                break
        
        if not found:
            print(f"[Canvas Click] WARNING: Clicked canvas item {clicked_item[0]} not found in draggable_items")
            print(f"[Canvas Click] Available image items: {[d.image_item for d in self.draggable_items[:5]]}...")
    
    def on_preview_click(self, canvas_x, canvas_y):
        """Handle clicks in preview mode to select trees and show details"""
        print(f"[Preview Click] Canvas position: ({canvas_x}, {canvas_y}), Zoom: {self.preview_zoom:.2f}x")
        
        # Account for zoom - convert canvas coordinates to image coordinates
        # Canvas coordinates are already accounting for scroll via canvasx/canvasy
        # Now we need to account for zoom
        image_x = canvas_x / self.preview_zoom
        image_y = canvas_y / self.preview_zoom
        
        # Account for the canvas offset (dark grey border in the base image)
        # The preview has 100px offset on each side
        offset_x = 100
        offset_y = 100
        adjusted_x = image_x - offset_x
        adjusted_y = image_y - offset_y
        
        print(f"[Preview Click] Image coords: ({image_x:.1f}, {image_y:.1f}), Adjusted: ({adjusted_x:.1f}, {adjusted_y:.1f})")
        
        # Find which composite was clicked
        for comp_type, comp_img, tree_set, bounds in self.preview_composites:
            x1, y1, x2, y2 = bounds
            if x1 <= adjusted_x <= x2 and y1 <= adjusted_y <= y2:
                print(f"[Preview Click] Selected {comp_type} tree: {tree_set['trunk']['name']}")
                
                # Update selected item details with trunk
                self.update_selected_item_details(tree_set['trunk'])
                
                # Redraw preview with bounds highlighted
                self.preview_selected_tree = (comp_type, tree_set, bounds)
                self.redraw_preview_with_bounds()
                return
        
        # Clicked outside any tree
        print("[Preview Click] Clicked outside trees")
        self.preview_selected_tree = None
        self.update_selected_item_details(None)
    
    def redraw_preview_with_bounds(self):
        """Redraw preview with bounds around selected tree and floating info label"""
        print(f"[Redraw] === REDRAW CALLED ===")
        
        if not self.preview_selected_tree:
            print(f"[Redraw] ERROR: No selection")
            return
        
        comp_type, tree_set, bounds = self.preview_selected_tree
        trunk_name = tree_set['trunk']['name']
        print(f"[Redraw] Selected: {trunk_name} ({comp_type}), bounds: {bounds}")
        
        # Get the base preview image (unzoomed, with dark grey border)
        preview_img = self.preview_base_image.copy() if self.preview_base_image else None
        if not preview_img:
            print(f"[Redraw] ERROR: No base image")
            return
        
        print(f"[Redraw] Base image size: {preview_img.size}, zoom: {self.preview_zoom}")
        
        # Draw bounds around selected tree on the base image
        draw = ImageDraw.Draw(preview_img)
        comp_type, tree_set, bounds = self.preview_selected_tree
        x1, y1, x2, y2 = bounds
        
        # Add offset for the dark grey border
        offset_x = 100
        offset_y = 100
        
        # Draw thick colored rectangle on base image
        color = TRUNK_COLOR if comp_type == 'base' else AUTUMN_COLOR
        for i in range(4):  # 4-pixel thick border
            draw.rectangle([x1+offset_x-i, y1+offset_y-i, x2+offset_x+i, y2+offset_y+i], outline=color)
        
        # Store leaves item for floating entry widget
        trunk_item = tree_set['trunk']
        base_leaves_item = tree_set.get('base_leaves')
        autumn_leaves_item = tree_set.get('autumn_leaves')
        
        print(f"[Redraw] Trunk item: {trunk_item['name']}")
        print(f"[Redraw] Tree set has base_leaves: {base_leaves_item['name'] if base_leaves_item else 'None'}")
        print(f"[Redraw] Tree set has autumn_leaves: {autumn_leaves_item['name'] if autumn_leaves_item else 'None'}")
        
        # Determine which leaves item to show offset for
        leaves_item = None
        if comp_type == 'autumn' and tree_set['autumn_leaves']:
            leaves_item = tree_set['autumn_leaves']
            print(f"[Redraw] Using autumn leaves: {leaves_item['name']}")
        elif tree_set['base_leaves']:
            leaves_item = tree_set['base_leaves']
            print(f"[Redraw] Using base leaves: {leaves_item['name']}")
        else:
            print(f"[Redraw] ERROR: No leaves found in tree_set!")
        
        # Now apply zoom to the image with bounds
        if self.preview_zoom != 1.0:
            new_width = int(preview_img.width * self.preview_zoom)
            new_height = int(preview_img.height * self.preview_zoom)
            preview_img = preview_img.resize((new_width, new_height), 
                                            Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
        
        # Remove old entry widget BEFORE deleting canvas (canvas.delete("all") will destroy it)
        if self.preview_offset_window:
            try:
                self.canvas.delete(self.preview_offset_window)
            except:
                pass
            self.preview_offset_window = None
            self.preview_offset_entry = None
        
        # Update canvas
        self.preview_photo = ImageTk.PhotoImage(preview_img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.preview_photo, anchor="nw")
        self.canvas.configure(scrollregion=(0, 0, preview_img.width, preview_img.height))
        
        # Create floating entry widget for height offset (if tree has leaves)
        if leaves_item:
            print(f"[Redraw] Tree has leaves: {leaves_item['name']}")
            
            # Get height offset from leaves metadata
            leaves_metadata = leaves_item.get('metadata', {})
            height_offset = leaves_metadata.get('TREE_LEAVES_HEIGHT_OFFSET', '50')
            print(f"[Redraw] Leaves offset from metadata: {height_offset}")
            
            # Calculate position at top-right of bounds (accounting for zoom)
            label_x = (x2 + offset_x + 10) * self.preview_zoom
            label_y = (y1 + offset_y) * self.preview_zoom
            print(f"[Redraw] Entry position: ({label_x}, {label_y})")
            
            # Create entry widget with yellow background to indicate "Press Enter to save"
            self.preview_offset_entry = tk.Entry(self.canvas, width=6, bg="#FFD700", fg=DARK_GRAY,
                                                 font=("Arial", 12, "bold"), justify=tk.CENTER,
                                                 relief=tk.SOLID, bd=2, highlightthickness=0,
                                                 insertbackground=DARK_GRAY)
            self.preview_offset_entry.insert(0, height_offset)
            print(f"[Redraw] Created entry widget with value: {height_offset}")
            
            # Store original value for change detection
            original_offset = height_offset
            
            # Change background to green when value changes (indicates unsaved)
            def on_change(*args):
                current = self.preview_offset_entry.get()
                if current != original_offset:
                    self.preview_offset_entry.config(bg="#FFA500")  # Orange = modified, press Enter
                else:
                    self.preview_offset_entry.config(bg="#FFD700")  # Yellow = ready to edit
            
            # Bind change detection
            self.preview_offset_entry.bind('<KeyRelease>', on_change)
            
            # Bind events - only save on Enter, not on FocusOut (causes infinite loop)
            def on_enter_key(event):
                print(f"[Entry] ENTER KEY PRESSED! Calling save_preview_offset...")
                self.save_preview_offset(leaves_item)
                return 'break'  # Prevent default behavior
            
            def on_escape_key(event):
                print(f"[Entry] ESCAPE KEY PRESSED! Reverting to {height_offset}")
                self.preview_offset_entry.delete(0, tk.END)
                self.preview_offset_entry.insert(0, height_offset)
                self.preview_offset_entry.config(bg="#FFD700")
                return 'break'
            
            self.preview_offset_entry.bind('<Return>', on_enter_key)
            self.preview_offset_entry.bind('<Escape>', on_escape_key)
            print(f"[Redraw] Bound Enter and Escape keys to entry widget")
            
            # Create window on canvas
            self.preview_offset_window = self.canvas.create_window(label_x, label_y, 
                                                                   window=self.preview_offset_entry, 
                                                                   anchor="nw")
            print(f"[Redraw] Created canvas window: {self.preview_offset_window}")
            
            # Focus the entry
            self.preview_offset_entry.focus_set()
            self.preview_offset_entry.select_range(0, tk.END)
            print(f"[Redraw] Focused and selected entry")
        else:
            print(f"[Redraw] No leaves item, removing entry if exists")
            # No leaves, remove entry if exists
            if self.preview_offset_window:
                self.canvas.delete(self.preview_offset_window)
                self.preview_offset_window = None
                self.preview_offset_entry = None
        
        print(f"[Redraw] === REDRAW COMPLETE ===")
    
    def save_preview_offset(self, leaves_item):
        """Save height offset from preview floating entry"""
        print(f"[Preview Offset] === SAVE CALLED ===")
        
        if not self.preview_offset_entry:
            print(f"[Preview Offset] ERROR: No entry widget exists")
            return
        
        try:
            new_offset = self.preview_offset_entry.get().strip()
            print(f"[Preview Offset] Entry value: '{new_offset}'")
            
            if not new_offset:
                print(f"[Preview Offset] ERROR: Empty value")
                return
            
            # Validate it's a number
            int(new_offset)
            print(f"[Preview Offset] Validated as number: {new_offset}")
            
            # Save to leaves item metadata
            metadata_path = os.path.join(
                self.folder_path,
                "Upscale",
                leaves_item['name'],
                f"{leaves_item['name']}.md"
            )
            print(f"[Preview Offset] Metadata path: {metadata_path}")
            
            # Read existing metadata (Obsidian dataview format uses :: not :)
            metadata = {}
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for line in content.split('\n'):
                        if '::' in line:  # Obsidian dataview format
                            key, value = line.split('::', 1)
                            metadata[key.strip()] = value.strip()
                            print(f"[Preview Offset] Read: {key.strip()} = {value.strip()}")
                print(f"[Preview Offset] Read existing metadata: {len(metadata)} keys")
            else:
                print(f"[Preview Offset] No existing metadata file at: {metadata_path}")
            
            # Update offset
            old_offset = metadata.get('TREE_LEAVES_HEIGHT_OFFSET', 'none')
            metadata['TREE_LEAVES_HEIGHT_OFFSET'] = new_offset
            print(f"[Preview Offset] Changed offset: {old_offset} → {new_offset}")
            
            # Write back
            os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
            print(f"[Preview Offset] Writing to: {metadata_path}")
            print(f"[Preview Offset] File exists before write: {os.path.exists(metadata_path)}")
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                for key, value in metadata.items():
                    f.write(f"{key}:: {value}\n")  # Obsidian dataview format uses ::
                    print(f"[Preview Offset]   Wrote: {key}:: {value}")
            
            print(f"[Preview Offset] File exists after write: {os.path.exists(metadata_path)}")
            
            # Verify the write by reading back
            with open(metadata_path, 'r', encoding='utf-8') as f:
                verify_content = f.read()
                print(f"[Preview Offset] Verified file content:")
                for line in verify_content.split('\n'):
                    if line.strip():
                        print(f"[Preview Offset]   {line}")
            
            # Update in-memory metadata
            leaves_item['metadata']['TREE_LEAVES_HEIGHT_OFFSET'] = new_offset
            print(f"[Preview Offset] Updated in-memory metadata for {leaves_item['name']}")
            print(f"[Preview Offset] In-memory value now: {leaves_item['metadata'].get('TREE_LEAVES_HEIGHT_OFFSET')}")
            
            # Save current selection to restore after refresh
            saved_selection = self.preview_selected_tree
            if saved_selection:
                comp_type, tree_set, old_bounds = saved_selection
                trunk_name = tree_set['trunk']['name']
                print(f"[Preview Offset] Saved selection: {trunk_name} ({comp_type}), bounds: {old_bounds}")
            else:
                print(f"[Preview Offset] WARNING: No selection to save!")
            
            # Refresh preview to show updated offset
            print(f"[Preview Offset] Calling render_final_preview()...")
            self.render_final_preview()
            print(f"[Preview Offset] Preview rendered, composites count: {len(self.preview_composites)}")
            
            # Restore selection after preview regenerates
            if saved_selection:
                comp_type, tree_set, old_bounds = saved_selection
                trunk_name = tree_set['trunk']['name']
                print(f"[Preview Offset] Looking for tree: {trunk_name} ({comp_type})")
                
                found = False
                # Find the tree in the new preview_composites
                for idx, (new_comp_type, composite_img, new_tree_set, new_bounds) in enumerate(self.preview_composites):
                    new_trunk_name = new_tree_set['trunk']['name']
                    print(f"[Preview Offset]   Checking [{idx}]: {new_trunk_name} ({new_comp_type})")
                    
                    if new_tree_set['trunk']['name'] == trunk_name and new_comp_type == comp_type:
                        # Re-select this tree with updated bounds
                        print(f"[Preview Offset]   MATCH! Old bounds: {old_bounds}, New bounds: {new_bounds}")
                        self.preview_selected_tree = (new_comp_type, new_tree_set, new_bounds)
                        print(f"[Preview Offset] Calling redraw_preview_with_bounds()...")
                        self.redraw_preview_with_bounds()
                        print(f"[Preview Offset] Re-selected tree after refresh")
                        found = True
                        break
                
                if not found:
                    print(f"[Preview Offset] ERROR: Could not find tree {trunk_name} ({comp_type}) in new composites!")
            else:
                print(f"[Preview Offset] No selection to restore")
            
            print(f"[Preview Offset] === SAVE COMPLETE ===")
            
        except ValueError as e:
            print(f"[Preview Offset] ERROR: Invalid offset value - {e}")
        except Exception as e:
            print(f"[Preview Offset] ERROR: Unexpected error - {e}")
            import traceback
            traceback.print_exc()
    
    def clear_link_mode(self):
        """Clear link mode state and visual highlight"""
        if self.link_mode_highlight:
            self.canvas.delete(self.link_mode_highlight)
            self.link_mode_highlight = None
        self.link_mode_first_item = None
        print("[Link Mode] Cleared")
    
    def handle_link_mode_click(self, draggable):
        """Handle item click in link mode"""
        item = draggable.item
        
        if self.link_mode_first_item is None:
            # First item selected
            self.link_mode_first_item = item
            print(f"[Link Mode] First item selected: {item['name']} (type: {item['type']})")
            
            # Draw highlight around first item
            img_width = draggable.photo.width()
            img_height = draggable.photo.height()
            self.link_mode_highlight = self.canvas.create_rectangle(
                draggable.x - 4,
                draggable.y - 4,
                draggable.x + img_width + 4,
                draggable.y + img_height + 4,
                outline=MUTED_PURPLE,
                width=4,
                tags="link_highlight"
            )
            print("[Link Mode] Waiting for second item...")
        else:
            # Second item selected - create link
            first_item = self.link_mode_first_item
            second_item = item
            
            print(f"[Link Mode] Second item selected: {second_item['name']} (type: {second_item['type']})")
            print(f"[Link Mode] Linking: {first_item['name']} <-> {second_item['name']}")
            
            # Create the link based on item types
            self.create_item_link(first_item, second_item)
            
            # Clear link mode state
            self.clear_link_mode()
    
    def unlink_item(self, item):
        """Remove all links from an item and clean up reciprocal connections"""
        print(f"[Unlink] Starting unlink for {item['name']}")
        metadata = item.get('metadata', {})
        
        # Track which items we need to update
        items_to_update = []
        
        # Check all possible link types this item has
        link_keys = [
            'TREE_LINKED_LEAVES',
            'TREE_LINKED_TRUNK', 
            'TREE_LINKED_AUTUMN',
            'TREE_LINKED_AUTUMN_VARIANT',
            'TREE_LINKED_BASE_LEAVES'
        ]
        
        # Find all linked items and their reciprocal keys
        reciprocal_map = {
            'TREE_LINKED_LEAVES': 'TREE_LINKED_TRUNK',
            'TREE_LINKED_TRUNK': ['TREE_LINKED_LEAVES', 'TREE_LINKED_AUTUMN'],
            'TREE_LINKED_AUTUMN': 'TREE_LINKED_TRUNK',
            'TREE_LINKED_AUTUMN_VARIANT': 'TREE_LINKED_BASE_LEAVES',
            'TREE_LINKED_BASE_LEAVES': 'TREE_LINKED_AUTUMN_VARIANT'
        }
        
        for link_key in link_keys:
            linked_name = metadata.get(link_key)
            if linked_name:
                print(f"[Unlink] Found link: {link_key} -> {linked_name}")
                
                # Find the linked item
                linked_item = None
                for draggable in self.draggable_items:
                    if draggable.item['name'] == linked_name:
                        linked_item = draggable.item
                        break
                
                if linked_item:
                    # Remove reciprocal link(s)
                    reciprocal_keys = reciprocal_map.get(link_key)
                    if isinstance(reciprocal_keys, str):
                        reciprocal_keys = [reciprocal_keys]
                    
                    for recip_key in reciprocal_keys:
                        if linked_item['metadata'].get(recip_key) == item['name']:
                            print(f"[Unlink] Removing reciprocal link: {linked_name}.{recip_key}")
                            write_item_metadata(self.upscale_folder, linked_name, recip_key, '')
                            linked_item['metadata'][recip_key] = ''
                
                # Remove this link from current item
                print(f"[Unlink] Removing link: {item['name']}.{link_key}")
                write_item_metadata(self.upscale_folder, item['name'], link_key, '')
                metadata[link_key] = ''
        
        print(f"[Unlink] Complete for {item['name']}")
        
        # Update selected item details if this is the selected item
        if self.selected_item == item:
            self.update_selected_item_details(item)
        
        # Refresh link visualization
        self.update_link_lines()
    
    def create_item_link(self, item1, item2):
        """Create a link between two items based on their types"""
        type1 = item1['type']
        type2 = item2['type']
        
        print(f"[Create Link] Type1: {type1}, Type2: {type2}")
        
        # Determine relationship and write appropriate metadata
        if (type1 == 'trunk' and type2 == 'leaves') or (type1 == 'leaves' and type2 == 'trunk'):
            # Trunk <-> Base Leaves link
            trunk = item1 if type1 == 'trunk' else item2
            leaves = item2 if type1 == 'trunk' else item1
            
            print(f"[Create Link] TRUNK-LEAVES link: {trunk['name']} <-> {leaves['name']}")
            write_item_metadata(self.upscale_folder, trunk['name'], 'TREE_LINKED_LEAVES', leaves['name'])
            write_item_metadata(self.upscale_folder, leaves['name'], 'TREE_LINKED_TRUNK', trunk['name'])
            
            # Update metadata in memory
            trunk['metadata']['TREE_LINKED_LEAVES'] = leaves['name']
            leaves['metadata']['TREE_LINKED_TRUNK'] = trunk['name']
            
            print(f"[Link Created] Trunk '{trunk['name']}' <-> Leaves '{leaves['name']}'")
            
        elif (type1 == 'trunk' and type2 == 'leaves_autumn') or (type1 == 'leaves_autumn' and type2 == 'trunk'):
            # Trunk <-> Autumn Leaves link
            trunk = item1 if type1 == 'trunk' else item2
            autumn = item2 if type1 == 'trunk' else item1
            
            print(f"[Create Link] TRUNK-AUTUMN link: {trunk['name']} <-> {autumn['name']}")
            write_item_metadata(self.upscale_folder, trunk['name'], 'TREE_LINKED_AUTUMN', autumn['name'])
            write_item_metadata(self.upscale_folder, autumn['name'], 'TREE_LINKED_TRUNK', trunk['name'])
            
            # Update metadata in memory
            trunk['metadata']['TREE_LINKED_AUTUMN'] = autumn['name']
            autumn['metadata']['TREE_LINKED_TRUNK'] = trunk['name']
            
            print(f"[Link Created] Trunk '{trunk['name']}' <-> Autumn '{autumn['name']}'")
            
        elif (type1 == 'leaves' and type2 == 'leaves_autumn') or (type1 == 'leaves_autumn' and type2 == 'leaves'):
            # Base Leaves <-> Autumn Leaves link
            base_leaves = item1 if type1 == 'leaves' else item2
            autumn = item2 if type1 == 'leaves' else item1
            
            print(f"[Create Link] LEAVES-AUTUMN link: {base_leaves['name']} <-> {autumn['name']}")
            write_item_metadata(self.upscale_folder, base_leaves['name'], 'TREE_LINKED_AUTUMN_VARIANT', autumn['name'])
            write_item_metadata(self.upscale_folder, autumn['name'], 'TREE_LINKED_BASE_LEAVES', base_leaves['name'])
            
            # Update metadata in memory
            base_leaves['metadata']['TREE_LINKED_AUTUMN_VARIANT'] = autumn['name']
            autumn['metadata']['TREE_LINKED_BASE_LEAVES'] = base_leaves['name']
            
            print(f"[Link Created] Base Leaves '{base_leaves['name']}' <-> Autumn '{autumn['name']}'")
            
        else:
            # Invalid or unsupported link
            print(f"[Create Link] WARNING: Unsupported link between {type1} and {type2}")
            print(f"[Invalid Link] Cannot link {type1} with {type2}")
            print(f"[Invalid Link] Valid links: Trunk<->Leaves, Trunk<->Autumn, Leaves<->Autumn")
            return
        
        # Refresh link visualization
        self.update_link_lines()
    
    def classify_canvas_item(self, draggable, item_type):
        """Classify a draggable item and update its appearance"""
        item = draggable.item
        old_type = item['type']
        
        print(f"[Classify] Starting classification for {item['name']}")
        print(f"[Classify] Current type: '{old_type}', Target type: '{item_type}'")
        
        # Skip if already the correct type
        if old_type == item_type:
            print(f"[Classify] SKIPPED: Item already classified as '{item_type}'")
            return
        
        print(f"[Classify] Upscale folder: {self.upscale_folder}")
        
        # Write metadata based on type
        if item_type == 'leaves_autumn':
            # Autumn leaves: set TREE_TYPE to leaves and mark as autumn variant
            print(f"[Classify] Writing autumn leaves metadata")
            write_item_metadata(self.upscale_folder, item['name'], 'TREE_TYPE', 'leaves')
            write_item_metadata(self.upscale_folder, item['name'], 'TREE_AUTUMN_VARIANT', 'True')
        else:
            # Regular types: just set TREE_TYPE
            print(f"[Classify] Writing TREE_TYPE: {item_type}")
            write_item_metadata(self.upscale_folder, item['name'], 'TREE_TYPE', item_type)
            # Clear autumn variant flag if it was set
            if item['metadata'].get('TREE_AUTUMN_VARIANT') == 'True':
                print(f"[Classify] Clearing autumn variant flag")
                write_item_metadata(self.upscale_folder, item['name'], 'TREE_AUTUMN_VARIANT', 'False')
        
        # Update item classification
        item['type'] = item_type
        item['metadata']['TREE_TYPE'] = 'leaves' if item_type == 'leaves_autumn' else item_type
        if item_type == 'leaves_autumn':
            item['metadata']['TREE_AUTUMN_VARIANT'] = 'True'
        
        print(f"[Classify] Changed type from '{old_type}' to '{item_type}'")
        
        # Move between lists
        if item in self.unknown_items:
            self.unknown_items.remove(item)
            print(f"[Classify] Removed from unknown_items")
        if item in self.trunk_items:
            self.trunk_items.remove(item)
            print(f"[Classify] Removed from trunk_items")
        if item in self.leaves_items:
            self.leaves_items.remove(item)
            print(f"[Classify] Removed from leaves_items")
        if item in self.autumn_leaves_items:
            self.autumn_leaves_items.remove(item)
            print(f"[Classify] Removed from autumn_leaves_items")
        
        if item_type == 'trunk':
            self.trunk_items.append(item)
            print(f"[Classify] Added to trunk_items (now {len(self.trunk_items)} items)")
        elif item_type == 'leaves':
            self.leaves_items.append(item)
            print(f"[Classify] Added to leaves_items (now {len(self.leaves_items)} items)")
        elif item_type == 'leaves_autumn':
            self.autumn_leaves_items.append(item)
            print(f"[Classify] Added to autumn_leaves_items (now {len(self.autumn_leaves_items)} items)")
        
        # Update bounds color
        print(f"[Classify] Updating bounds color")
        draggable.update_bounds(self.show_bounds.get(), item_type)
        
        # Update stats
        print(f"[Classify] Updating stats display")
        self.update_stats()
        
        # Update selected item details if this is the selected item
        if self.selected_item == item:
            self.update_selected_item_details(item)
        
        print(f"[Classify] Classification complete!")
    
    def update_stats(self):
        """Update statistics display"""
        self.stats_trunk_label.config(text=f"Trunk: {len(self.trunk_items)}")
        self.stats_leaves_label.config(text=f"Leaves: {len(self.leaves_items)}")
        self.stats_autumn_label.config(text=f"Autumn: {len(self.autumn_leaves_items)}")
        self.stats_unknown_label.config(text=f"Unclassified: {len(self.unknown_items)}")
    
    def update_selected_item_details(self, item):
        """Update the selected item details panel"""
        self.selected_item = item
        
        if not item:
            self.detail_name_label.config(text="None")
            self.detail_type_label.config(text="None")
            self.detail_links_text.config(state=tk.NORMAL)
            self.detail_links_text.delete("1.0", tk.END)
            self.detail_links_text.insert("1.0", "No item selected")
            self.detail_links_text.config(state=tk.DISABLED)
            return
        
        # Update name
        self.detail_name_label.config(text=item['name'])
        
        # Update type with color coding
        item_type = item['type']
        type_text = item_type.upper() if item_type != 'unknown' else 'UNCLASSIFIED'
        type_color = WHITE
        
        if item_type == 'trunk':
            type_color = TRUNK_COLOR
        elif item_type == 'leaves':
            type_color = LEAVES_COLOR
        elif item_type == 'leaves_autumn':
            type_color = AUTUMN_COLOR
            type_text = 'AUTUMN LEAVES'
        
        self.detail_type_label.config(text=type_text, fg=type_color)
        
        # Update links with type information
        metadata = item.get('metadata', {})
        links_text = ""
        
        link_info = [
            ('TREE_LINKED_TRUNK', 'Trunk', TRUNK_COLOR),
            ('TREE_LINKED_LEAVES', 'Base Leaves', LEAVES_COLOR),
            ('TREE_LINKED_AUTUMN', 'Autumn Leaves (Direct)', AUTUMN_COLOR),
            ('TREE_LINKED_AUTUMN_VARIANT', 'Autumn Variant', AUTUMN_COLOR),
            ('TREE_LINKED_BASE_LEAVES', 'Base Leaves', LEAVES_COLOR)
        ]
        
        has_links = False
        for key, label, color in link_info:
            value = metadata.get(key, '')
            if value:
                # Find the linked item to show its type
                linked_type = "?"
                for draggable in self.draggable_items:
                    if draggable.item['name'] == value:
                        linked_type = draggable.item['type']
                        break
                
                links_text += f"• {label}:\n  {value}\n  [{linked_type}]\n\n"
                has_links = True
        
        # Show autumn path info for trunks
        if item_type == 'trunk':
            autumn_path = []
            if metadata.get('TREE_LINKED_AUTUMN'):
                autumn_path.append("Direct trunk→autumn")
            
            base_leaves_name = metadata.get('TREE_LINKED_LEAVES', '')
            if base_leaves_name:
                for draggable in self.draggable_items:
                    if draggable.item['name'] == base_leaves_name:
                        base_leaves_metadata = draggable.item.get('metadata', {})
                        if base_leaves_metadata.get('TREE_LINKED_AUTUMN_VARIANT', ''):
                            autumn_path.append("Via base leaves→autumn")
                        break
            
            if autumn_path:
                links_text += f"\n🍂 Autumn Available:\n  {', '.join(autumn_path)}\n"
        
        if not has_links:
            links_text = "No links"
        
        self.detail_links_text.config(state=tk.NORMAL)
        self.detail_links_text.delete("1.0", tk.END)
        self.detail_links_text.insert("1.0", links_text.strip())
        self.detail_links_text.config(state=tk.DISABLED)
        
        # Show/hide height offset control (for leaves items - each leaf type has its own offset)
        if item_type in ['leaves', 'leaves_autumn']:
            # Load current offset from THIS leaf item's metadata
            current_offset = metadata.get('TREE_LEAVES_HEIGHT_OFFSET', '50')
            self.detail_offset_entry.delete(0, tk.END)
            self.detail_offset_entry.insert(0, current_offset)
            self.offset_control_frame.pack(fill=tk.X, padx=5)
        else:
            self.offset_control_frame.pack_forget()
        
        # Show render properties control (for trunks - show in both working and preview mode)
        if item_type == 'trunk':
            # Show render properties control
            props = self.get_item_render_props(item)
            self.render_props_label.config(text=f"For render: '{self.current_render}'")
            
            # Update exclude button
            if props['excluded']:
                self.exclude_from_render_btn.config(text="Include in Render", bg=MUTED_GREEN)
            else:
                self.exclude_from_render_btn.config(text="Exclude from Render", bg="#CC4444")
            
            # Update use autumn button (only show if has autumn variant)
            # Check both direct trunk->autumn link and base leaves->autumn variant link
            autumn_leaves_name = metadata.get('TREE_LINKED_AUTUMN', '')
            has_autumn = False
            
            if autumn_leaves_name:
                has_autumn = True
            else:
                # Check if base leaves have autumn variant
                base_leaves_name = metadata.get('TREE_LINKED_LEAVES', '')
                if base_leaves_name:
                    for draggable in self.draggable_items:
                        if draggable.item['name'] == base_leaves_name:
                            base_leaves_metadata = draggable.item.get('metadata', {})
                            if base_leaves_metadata.get('TREE_LINKED_AUTUMN_VARIANT', ''):
                                has_autumn = True
                            break
            
            if has_autumn:
                if props['use_autumn']:
                    self.use_autumn_btn.config(text="Use Base Variant", bg=LEAVES_COLOR)
                else:
                    self.use_autumn_btn.config(text="Use Autumn Variant", bg=AUTUMN_COLOR)
                self.use_autumn_btn.pack(fill=tk.X, pady=1)
            else:
                self.use_autumn_btn.pack_forget()
            
            # Update show leaves button
            if props['show_leaves']:
                self.show_leaves_btn.config(text="Hide Leaves (Trunk Only)", bg=TRUNK_COLOR)
            else:
                self.show_leaves_btn.config(text="Show Leaves", bg=LEAVES_COLOR)
            
            self.render_props_frame.pack(fill=tk.X, padx=5)
        else:
            self.render_props_frame.pack_forget()
        
        print(f"[Selected Item] {item['name']} ({type_text})")
    
    def toggle_item_excluded(self):
        """Toggle excluded state for selected item"""
        if not self.selected_item:
            return
        
        props = self.get_item_render_props(self.selected_item)
        new_excluded = not props['excluded']
        self.set_item_render_props(self.selected_item, excluded=new_excluded)
        
        # Update UI
        self.update_selected_item_details(self.selected_item)
        
        # Refresh preview if active
        if self.preview_mode:
            self.render_final_preview()
            self.update_composite_list()  # Update color coding
        
        print(f"[Render Props] {self.selected_item['name']} excluded={new_excluded}")
    
    def toggle_item_use_autumn(self):
        """Toggle use_autumn for selected trunk"""
        if not self.selected_item or self.selected_item['type'] != 'trunk':
            return
        
        metadata = self.selected_item.get('metadata', {})
        
        # Check both autumn link paths
        has_autumn = False
        if metadata.get('TREE_LINKED_AUTUMN'):
            has_autumn = True
        else:
            # Check if base leaves have autumn variant
            base_leaves_name = metadata.get('TREE_LINKED_LEAVES', '')
            if base_leaves_name:
                for draggable in self.draggable_items:
                    if draggable.item['name'] == base_leaves_name:
                        base_leaves_metadata = draggable.item.get('metadata', {})
                        if base_leaves_metadata.get('TREE_LINKED_AUTUMN_VARIANT', ''):
                            has_autumn = True
                        break
        
        if not has_autumn:
            print("[Render Props] No autumn variant available")
            return
        
        props = self.get_item_render_props(self.selected_item)
        new_use_autumn = not props['use_autumn']
        self.set_item_render_props(self.selected_item, use_autumn=new_use_autumn)
        
        # Update UI
        self.update_selected_item_details(self.selected_item)
        
        # Refresh preview if active
        if self.preview_mode:
            self.render_final_preview()
            self.update_composite_list()  # Update color coding
        
        print(f"[Render Props] {self.selected_item['name']} use_autumn={new_use_autumn}")
    
    def toggle_item_show_leaves(self):
        """Toggle show_leaves for selected trunk"""
        if not self.selected_item or self.selected_item['type'] != 'trunk':
            return
        
        props = self.get_item_render_props(self.selected_item)
        new_show_leaves = not props['show_leaves']
        self.set_item_render_props(self.selected_item, show_leaves=new_show_leaves)
        
        # Update UI
        self.update_selected_item_details(self.selected_item)
        
        # Refresh preview if active
        if self.preview_mode:
            self.render_final_preview()
            self.update_composite_list()  # Update color coding
        
        print(f"[Render Props] {self.selected_item['name']} show_leaves={new_show_leaves}")
    
    def toggle_tree_variant(self):
        """Toggle between base and autumn variant for selected tree in current render"""
        if not self.selected_item or self.selected_item['type'] != 'trunk':
            print("[Variant] ERROR: No trunk selected")
            return
        
        item_name = self.selected_item['name']
        metadata = self.selected_item.get('metadata', {})
        autumn_leaves_name = metadata.get('TREE_LINKED_AUTUMN', '')
        
        if not autumn_leaves_name:
            print(f"[Variant] ERROR: {item_name} has no autumn variant")
            return
        
        config = self.render_configs.get(self.current_render, {"excluded_items": [], "autumn_variants": {}})
        autumn_variants = config.get("autumn_variants", {})
        
        # Toggle variant preference
        use_autumn = autumn_variants.get(item_name, False)
        autumn_variants[item_name] = not use_autumn
        
        # Update config
        config["autumn_variants"] = autumn_variants
        self.render_configs[self.current_render] = config
        
        # Save to file
        self.save_render_config(self.current_render)
        
        # Update button appearance
        if autumn_variants[item_name]:
            self.swap_variant_btn.config(text="Swap to Base Variant", bg=LEAVES_COLOR)
            print(f"[Variant] {item_name} set to AUTUMN in '{self.current_render}'")
        else:
            self.swap_variant_btn.config(text="Swap to Autumn Variant", bg=AUTUMN_COLOR)
            print(f"[Variant] {item_name} set to BASE in '{self.current_render}'")
        
        # If in preview mode, refresh the preview
        if self.preview_mode:
            self.render_final_preview()
    
    def toggle_exclude_from_render(self):
        """Toggle exclude from current render for selected trunk"""
        if not self.selected_item or self.selected_item['type'] != 'trunk':
            print("[Exclude] ERROR: No trunk selected")
            return
        
        item_name = self.selected_item['name']
        config = self.render_configs.get(self.current_render, {"excluded_items": []})
        excluded_items = config.get("excluded_items", [])
        
        # Toggle exclusion
        if item_name in excluded_items:
            excluded_items.remove(item_name)
            is_excluded = False
        else:
            excluded_items.append(item_name)
            is_excluded = True
        
        # Update config
        config["excluded_items"] = excluded_items
        self.render_configs[self.current_render] = config
        
        # Save to file
        self.save_render_config(self.current_render)
        
        # Update button appearance
        if is_excluded:
            self.exclude_from_render_btn.config(text=f"Include in '{self.current_render}'", bg=MUTED_GREEN)
            print(f"[Exclude] {item_name} EXCLUDED from render '{self.current_render}'")
        else:
            self.exclude_from_render_btn.config(text=f"Exclude from '{self.current_render}'", bg="#CC4444")
            print(f"[Exclude] {item_name} INCLUDED in render '{self.current_render}'")
        
        # If in preview mode, refresh the preview
        if self.preview_mode:
            self.render_final_preview()
    
    def save_height_offset(self):
        """Save the height offset value to selected trunk's metadata"""
        if not self.selected_item or self.selected_item['type'] != 'trunk':
            print("[Height Offset] ERROR: No trunk selected")
            return
        
        try:
            offset_value = self.detail_offset_entry.get().strip()
            offset_int = int(offset_value)
            
            # Write to metadata
            write_item_metadata(self.upscale_folder, self.selected_item['name'], 
                              'TREE_LEAVES_HEIGHT_OFFSET', str(offset_int))
            
            # Update in memory
            self.selected_item['metadata']['TREE_LEAVES_HEIGHT_OFFSET'] = str(offset_int)
            
            print(f"[Height Offset] Saved offset {offset_int} for {self.selected_item['name']}")
            
            # If in preview mode, refresh the preview
            if self.preview_mode:
                self.render_final_preview()
        except ValueError:
            print(f"[Height Offset] ERROR: Invalid offset value: {self.detail_offset_entry.get()}")
    
    def update_all_bounds(self):
        """Update bounds display for all items"""
        show = self.show_bounds.get()
        for draggable in self.draggable_items:
            draggable.update_bounds(show, draggable.item['type'])
    
    def update_link_lines(self):
        """Update link line visualization"""
        # Clear existing link lines
        for line in self.link_lines:
            self.canvas.delete(line)
        self.link_lines = []
        
        if not self.show_links.get():
            return
        
        # Draw link lines between connected items
        print("[Link Lines] Updating link visualization")
        
        # Create a mapping of item names to draggable objects
        item_map = {d.item['name']: d for d in self.draggable_items}
        
        # Track which links we've already drawn (to avoid duplicates)
        drawn_links = set()
        
        for draggable in self.draggable_items:
            item = draggable.item
            metadata = item.get('metadata', {})
            
            # Get center point of this item's bounds
            img_width = draggable.photo.width()
            img_height = draggable.photo.height()
            x1 = draggable.x + img_width // 2
            y1 = draggable.y + img_height // 2
            
            # Check for various link types
            links_to_check = [
                ('TREE_LINKED_LEAVES', LEAVES_COLOR),
                ('TREE_LINKED_TRUNK', TRUNK_COLOR),
                ('TREE_LINKED_AUTUMN', AUTUMN_COLOR),
                ('TREE_LINKED_AUTUMN_VARIANT', AUTUMN_COLOR),
                ('TREE_LINKED_BASE_LEAVES', LEAVES_COLOR)
            ]
            
            for link_key, color in links_to_check:
                linked_name = metadata.get(link_key)
                if linked_name and linked_name in item_map:
                    # Create unique link identifier (sorted to avoid duplicates)
                    link_id = tuple(sorted([item['name'], linked_name]))
                    
                    if link_id not in drawn_links:
                        drawn_links.add(link_id)
                        
                        # Get target item position
                        target_draggable = item_map[linked_name]
                        target_width = target_draggable.photo.width()
                        target_height = target_draggable.photo.height()
                        x2 = target_draggable.x + target_width // 2
                        y2 = target_draggable.y + target_height // 2
                        
                        # Draw line
                        line = self.canvas.create_line(
                            x1, y1, x2, y2,
                            fill=color,
                            width=3,
                            dash=(5, 3),
                            tags="link_line"
                        )
                        self.link_lines.append(line)
                        
                        # Lower lines below items
                        self.canvas.tag_lower(line)
                        
                        print(f"[Link Lines] Drew {link_key} line: {item['name']} -> {linked_name}")
        
        print(f"[Link Lines] Drew {len(self.link_lines)} link lines")
    
    def is_item_linked(self, item):
        """Check if an item is part of any composite"""
        for composite in self.composites:
            if composite.trunk_item == item or composite.leaves_item == item:
                return True
        return False
    
    def apply_filters(self):
        """Apply view filters to show/hide items on canvas"""
        show_trunks = self.filter_show_trunks.get()
        show_leaves = self.filter_show_leaves.get()
        show_autumn = self.filter_show_autumn.get()
        show_unclassified = self.filter_show_unclassified.get()
        unlinked_only = self.filter_unlinked_only.get()
        
        for draggable in self.draggable_items:
            item = draggable.item
            item_type = item['type']
            
            # Check type filter
            type_visible = False
            if item_type == 'trunk' and show_trunks:
                type_visible = True
            elif item_type == 'leaves' and show_leaves:
                type_visible = True
            elif item_type == 'leaves_autumn' and show_autumn:  # Autumn has its own filter
                type_visible = True
            elif item_type == 'unknown' and show_unclassified:
                type_visible = True
            
            # Check unlinked filter
            if unlinked_only:
                is_linked = self.is_item_linked(item)
                type_visible = type_visible and not is_linked
            
            # Show or hide the item
            if type_visible:
                self.canvas.itemconfig(draggable.image_item, state='normal')
                self.canvas.itemconfig(draggable.text_item, state='normal')
                if draggable.bounds_rect:
                    self.canvas.itemconfig(draggable.bounds_rect, state='normal')
            else:
                self.canvas.itemconfig(draggable.image_item, state='hidden')
                self.canvas.itemconfig(draggable.text_item, state='hidden')
                if draggable.bounds_rect:
                    self.canvas.itemconfig(draggable.bounds_rect, state='hidden')
    
    def load_render_configs(self):
        """Load all render configuration files"""
        if not self.folder_path or not os.path.isdir(self.folder_path):
            self.render_configs = {"default": {"excluded_items": []}}
            return
        
        import glob
        render_files = glob.glob(os.path.join(self.folder_path, "render_*.json"))
        
        self.render_configs = {}
        
        for render_file in render_files:
            try:
                with open(render_file, 'r') as f:
                    data = json.load(f)
                
                basename = os.path.basename(render_file)
                render_name = basename[7:-5]  # Remove "render_" and ".json"
                
                self.render_configs[render_name] = data
                print(f"[Render Config] Loaded '{render_name}'")
            except Exception as e:
                print(f"[Render Config] ERROR loading {render_file}: {e}")
        
        # Ensure default exists
        if "default" not in self.render_configs:
            self.render_configs["default"] = {"excluded_items": []}
        
        # Update dropdown
        self.update_render_selector()
        print(f"[Render Config] Loaded {len(self.render_configs)} render configurations")
    
    def update_render_selector(self):
        """Update the render selector dropdown"""
        render_names = sorted(self.render_configs.keys())
        self.render_selector['values'] = render_names
        
        if self.current_render in render_names:
            self.render_selector.set(self.current_render)
        elif render_names:
            self.current_render = render_names[0]
            self.render_selector.set(self.current_render)
        
        # Update exclude label if item is selected
        if self.selected_item:
            self.update_selected_item_details(self.selected_item)
    
    def on_render_selected(self, event):
        """Handle render selection change"""
        selected = self.render_selector.get()
        if selected and selected != self.current_render:
            self.current_render = selected
            print(f"[Render Config] Switched to '{self.current_render}'")
            
            # Load global original folder for this render
            config = self.render_configs.get(self.current_render, {})
            if 'global_original_folder' in config:
                self.global_original_folder = config['global_original_folder']
                self.global_original_entry.delete(0, tk.END)
                self.global_original_entry.insert(0, self.global_original_folder)
                print(f"[Render Config] Loaded global_original_folder: '{self.global_original_folder}'")
            else:
                print(f"[Render Config] No global_original_folder saved for this render")
            
            # Update selected item details to show new render's exclusion state
            if self.selected_item:
                self.update_selected_item_details(self.selected_item)
            
            # If in preview mode, refresh
            if self.preview_mode:
                self.render_final_preview()
    
    def get_item_render_id(self, item):
        """Generate unique ID for item in current render (item_name + canvas position)"""
        # Find draggable for this item to get canvas position
        for draggable in self.draggable_items:
            if draggable.item == item:
                return f"{item['name']}_x{int(draggable.x)}_y{int(draggable.y)}"
        return item['name']
    
    def get_item_render_props(self, item, render_name=None):
        """Get render properties for item in specified render (or current render if not specified)"""
        item_id = self.get_item_render_id(item)
        target_render = render_name if render_name else self.current_render
        config = self.render_configs.get(target_render, {})
        item_props = config.get('item_properties', {})
        
        # Return default properties if not set
        return item_props.get(item_id, {
            'excluded': False,
            'use_autumn': False,
            'show_leaves': True
        })
    
    def set_item_render_props(self, item, **props):
        """Set render properties for item in current render"""
        item_id = self.get_item_render_id(item)
        config = self.render_configs.get(self.current_render, {})
        
        if 'item_properties' not in config:
            config['item_properties'] = {}
        
        # Get existing props and update
        item_props = config['item_properties'].get(item_id, {
            'excluded': False,
            'use_autumn': False,
            'show_leaves': True
        })
        item_props.update(props)
        config['item_properties'][item_id] = item_props
        
        # Save config
        self.render_configs[self.current_render] = config
        self.save_render_config(self.current_render)
    
    def create_new_render(self):
        """Create a new render configuration"""
        from tkinter import simpledialog
        render_name = simpledialog.askstring("New Render", 
                                             "Enter render name:",
                                             initialvalue="")
        if not render_name:
            return
        
        # Sanitize name
        safe_name = "".join(c for c in render_name if c.isalnum() or c in (' ', '_', '-')).strip()
        if not safe_name:
            print("[Render Config] ERROR: Invalid render name")
            return
        
        if safe_name in self.render_configs:
            print(f"[Render Config] ERROR: Render '{safe_name}' already exists")
            return
        
        # Create new config
        self.render_configs[safe_name] = {
            "excluded_items": [],
            "autumn_variants": {}  # item_name -> bool (true = use autumn)
        }
        self.current_render = safe_name
        
        # Save immediately
        self.save_render_config(safe_name)
        
        # Update UI
        self.update_render_selector()
        print(f"[Render Config] Created new render '{safe_name}'")
    
    def save_current_render(self):
        """Save the current render configuration"""
        self.save_render_config(self.current_render)
    
    def save_render_config(self, render_name):
        """Save a specific render configuration to file"""
        if not self.folder_path:
            print("[Render Config] ERROR: No folder selected")
            return
        
        config = self.render_configs.get(render_name, {"excluded_items": []})
        
        # Save global original folder path with this render config
        print(f"[Render Config] DEBUG: self.global_original_folder = '{self.global_original_folder}'")
        print(f"[Render Config] DEBUG: Entry widget = '{self.global_original_entry.get()}'")
        
        # Always read from entry widget to ensure we have the latest value
        entry_value = self.global_original_entry.get().strip()
        if entry_value:
            self.global_original_folder = entry_value
            print(f"[Render Config] Updated from entry widget: '{entry_value}'")
        
        config['global_original_folder'] = self.global_original_folder
        print(f"[Render Config] Saving global_original_folder: '{self.global_original_folder}'")
        
        # Sanitize filename
        safe_name = "".join(c for c in render_name if c.isalnum() or c in (' ', '_', '-')).strip()
        json_path = os.path.join(self.folder_path, f"render_{safe_name}.json")
        
        try:
            with open(json_path, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"[Render Config] Saved '{render_name}' to {json_path}")
        except Exception as e:
            print(f"[Render Config] ERROR saving: {e}")
    
    def delete_current_render(self):
        """Delete the current render configuration"""
        if self.current_render == "default":
            print("[Render Config] Cannot delete 'default' render")
            return
        
        # Confirm deletion
        from tkinter import messagebox
        if not messagebox.askyesno("Delete Render", 
                                   f"Delete render '{self.current_render}'?"):
            return
        
        # Delete file
        safe_name = "".join(c for c in self.current_render if c.isalnum() or c in (' ', '_', '-')).strip()
        json_path = os.path.join(self.folder_path, f"render_{safe_name}.json")
        
        try:
            if os.path.exists(json_path):
                os.remove(json_path)
            
            # Remove from configs
            del self.render_configs[self.current_render]
            
            # Switch to default
            self.current_render = "default"
            self.update_render_selector()
            
            print(f"[Render Config] Deleted render '{safe_name}'")
        except Exception as e:
            print(f"[Render Config] ERROR deleting: {e}")
    
    def auto_load_on_startup(self):
        """Automatically load items on startup and load composite if available"""
        if os.path.isdir(self.folder_path):
            print(f"[Auto-Load] Loading items from default folder: {self.folder_path}")
            self.load_items()
            
            # Try to auto-load a composite
            self.auto_load_composite()
        else:
            print(f"[Auto-Load] Default folder not found: {self.folder_path}")
    
    def auto_load_composite(self):
        """Automatically load a composite if one exists"""
        if not self.folder_path or not os.path.isdir(self.folder_path):
            return
        
        # Find all composite JSON files
        import glob
        json_files = glob.glob(os.path.join(self.folder_path, "composite_*.json"))
        
        if not json_files:
            print("[Auto-Load] No composite files found")
            return
        
        # Load the first one found (or prefer "default" if it exists)
        default_file = os.path.join(self.folder_path, "composite_default.json")
        if os.path.exists(default_file):
            json_path = default_file
        else:
            json_path = json_files[0]
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            # Load composites
            self.composites = []
            for comp_data in data.get('composites', []):
                composite = TreeComposite.from_dict(comp_data, self.items_dict)
                self.composites.append(composite)
            
            # Restore canvas positions if available
            canvas_positions = data.get('canvas_positions', {})
            if canvas_positions:
                for draggable in self.draggable_items:
                    item_name = draggable.item['name']
                    if item_name in canvas_positions:
                        pos = canvas_positions[item_name]
                        # Calculate delta
                        dx = pos['x'] - draggable.x
                        dy = pos['y'] - draggable.y
                        
                        # Move canvas items
                        self.canvas.move(draggable.image_item, dx, dy)
                        self.canvas.move(draggable.text_item, dx, dy)
                        if draggable.bounds_rect:
                            self.canvas.move(draggable.bounds_rect, dx, dy)
                        
                        # Update stored position
                        draggable.x = pos['x']
                        draggable.y = pos['y']
                
                # Update link lines and scroll region
                self.update_link_lines()
                self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            self.update_composite_list()
            layout_name = data.get('layout_name', 'unknown')
            print(f"[Auto-Load] Loaded layout '{layout_name}' with {len(self.composites)} composites")
        except Exception as e:
            print(f"[Auto-Load] ERROR: Failed to load composite: {str(e)}")
    
    def load_items(self):
        """Load tree items from folder"""
        self.folder_path = self.folder_entry.get().strip()
        if not self.folder_path:
            print("[Load Items] ERROR: Please select a folder")
            return
        
        self.items = load_tree_items(self.folder_path)
        self.items_dict = {item['hex_id']: item for item in self.items}
        self.upscale_folder = os.path.join(self.folder_path, "Upscale")
        
        # Classify items by type
        self.trunk_items = [item for item in self.items if item['type'] == 'trunk']
        self.leaves_items = [item for item in self.items if item['type'] == 'leaves']
        self.autumn_leaves_items = [item for item in self.items if item['type'] == 'leaves_autumn']
        self.unknown_items = [item for item in self.items if item['type'] == 'unknown']
        
        # Clear canvas
        self.canvas.delete("all")
        self.draggable_items = []
        
        # Populate canvas with draggable items in a grid
        x, y = 20, 20
        col = 0
        max_cols = 8
        spacing = 140
        
        for item in self.items:
            draggable = DraggableTreeItem(self.canvas, x, y, item, ui_ref=self)
            self.draggable_items.append(draggable)
            
            # Update bounds if show_bounds is enabled
            draggable.update_bounds(self.show_bounds.get(), item['type'])
            
            col += 1
            if col >= max_cols:
                col = 0
                x = 20
                y += 160
            else:
                x += spacing
        
        # Update canvas scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # Update stats
        self.update_stats()
        
        # Draw link lines
        self.update_link_lines()
        
        print(f"[Load Items] SUCCESS: Loaded {len(self.items)} items")
        print(f"[Load Items] Trunk: {len(self.trunk_items)}, Leaves: {len(self.leaves_items)}, Autumn: {len(self.autumn_leaves_items)}, Unclassified: {len(self.unknown_items)}")
    
    def on_composite_list_press(self, event):
        """Handle mouse press on composite list"""
        if not self.preview_mode:
            return
        
        # Get selected index
        index = self.composite_listbox.nearest(event.y)
        if index < 0:
            return
        
        # Get the trunk item for this index
        trunk_items = []
        for draggable in self.draggable_items:
            if draggable.item['type'] == 'trunk':
                trunk_items.append(draggable.item)
        
        trunk_items.sort(key=lambda t: (
            next((d.y for d in self.draggable_items if d.item == t), 0),
            next((d.x for d in self.draggable_items if d.item == t), 0)
        ))
        
        if index < len(trunk_items):
            self.composite_drag_data["trunk_item"] = trunk_items[index]
            self.composite_drag_data["start_x"] = event.x
            self.composite_drag_data["start_y"] = event.y
    
    def on_composite_list_drag(self, event):
        """Handle dragging from composite list"""
        if not self.preview_mode or not self.composite_drag_data.get("trunk_item"):
            return
        
        # Check if moved enough to start dragging
        if not self.composite_drag_data.get("dragging"):
            dx = abs(event.x - self.composite_drag_data.get("start_x", 0))
            dy = abs(event.y - self.composite_drag_data.get("start_y", 0))
            if dx > 5 or dy > 5:
                self.composite_drag_data["dragging"] = True
                print(f"[Drag] Started dragging {self.composite_drag_data['trunk_item']['name']} from list")
    
    def on_composite_list_release(self, event):
        """Handle release after dragging from composite list"""
        if not self.preview_mode or not self.composite_drag_data.get("dragging"):
            self.composite_drag_data = {"dragging": False, "trunk_item": None}
            return
        
        trunk_item = self.composite_drag_data["trunk_item"]
        
        # Get canvas coordinates (accounting for scroll)
        canvas_x = self.canvas.canvasx(event.x_root - self.canvas.winfo_rootx())
        canvas_y = self.canvas.canvasy(event.y_root - self.canvas.winfo_rooty())
        
        print(f"[Drag] Dropped {trunk_item['name']} at canvas ({canvas_x}, {canvas_y})")
        
        # Add this trunk to the current render at the drop position
        self.add_trunk_to_render(trunk_item, canvas_x, canvas_y)
        
        # Clear drag data
        self.composite_drag_data = {"dragging": False, "trunk_item": None}
    
    def add_trunk_to_render(self, trunk_item, x, y):
        """Add a trunk item to the current render at specified position"""
        # Create a new draggable item at the drop position
        # This creates a duplicate/instance of the trunk for this render
        print(f"[Add to Render] Adding {trunk_item['name']} to render '{self.current_render}' at ({x}, {y})")
        
        # Create draggable item
        draggable = DraggableTreeItem(self.canvas, x, y, trunk_item, self.thumbnail_size)
        self.draggable_items.append(draggable)
        
        # The new item will get a unique ID based on its position
        # and will be auto-registered to the current render config
        item_id = self.get_item_render_id(trunk_item)
        print(f"[Add to Render] New item ID: {item_id}")
        
        # Update bounds and links
        self.update_all_bounds()
        self.update_link_lines()
        
        # If in preview mode, refresh the preview
        if self.preview_mode:
            self.render_final_preview()
        
        print(f"[Add to Render] SUCCESS: Added duplicate of {trunk_item['name']}")
    
    def on_composite_select(self, event):
        """Handle composite selection"""
        selection = self.composite_listbox.curselection()
        if selection:
            self.selected_composite_idx = selection[0]
            composite = self.composites[self.selected_composite_idx]
            # TODO: Implement composite preview/editing
    
    def delete_composite(self):
        """Delete selected composite"""
        if self.selected_composite_idx is None:
            print("[Delete Composite] ERROR: Please select a composite to delete")
            return
        
        del self.composites[self.selected_composite_idx]
        self.selected_composite_idx = None
        self.update_composite_list()
        print("[Delete Composite] SUCCESS: Composite deleted")
    
    def update_composite_list(self):
        """Update the composite listbox with color-coded exclusion status"""
        self.composite_listbox.delete(0, tk.END)
        
        # In preview mode, show all trunks with exclusion status
        if self.preview_mode:
            # Get all trunks sorted by canvas position
            trunk_items = []
            for draggable in self.draggable_items:
                if draggable.item['type'] == 'trunk':
                    trunk_items.append((draggable.item, draggable.x, draggable.y))
            
            trunk_items.sort(key=lambda t: (t[2], t[1]))  # Sort by y, then x
            
            for trunk_item, x, y in trunk_items:
                # Get exclusion status for current render
                props = self.get_item_render_props(trunk_item)
                is_excluded = props['excluded']
                use_autumn = props['use_autumn']
                show_leaves = props['show_leaves']
                
                # Build display string with status indicators
                trunk_hex = f"0x{trunk_item['hex_id']:04X}"
                status = []
                if is_excluded:
                    status.append("EXCLUDED")
                if use_autumn:
                    status.append("AUTUMN")
                if not show_leaves:
                    status.append("TRUNK-ONLY")
                
                status_str = f" [{', '.join(status)}]" if status else ""
                display = f"{trunk_item['name']} ({trunk_hex}){status_str}"
                
                self.composite_listbox.insert(tk.END, display)
                
                # Color code based on exclusion status
                idx = self.composite_listbox.size() - 1
                if is_excluded:
                    self.composite_listbox.itemconfig(idx, fg="#CC4444")  # Red for excluded
                elif use_autumn:
                    self.composite_listbox.itemconfig(idx, fg=AUTUMN_COLOR)  # Orange for autumn
                elif not show_leaves:
                    self.composite_listbox.itemconfig(idx, fg=TRUNK_COLOR)  # Brown for trunk-only
                else:
                    self.composite_listbox.itemconfig(idx, fg=LEAVES_COLOR)  # Green for normal
        else:
            # Working mode: show old composite system
            for composite in self.composites:
                trunk_hex = f"0x{composite.trunk_item['hex_id']:04X}" if composite.trunk_item else "None"
                leaves_hex = f"0x{composite.leaves_item['hex_id']:04X}" if composite.leaves_item else "None"
                display = f"{composite.name} (T:{trunk_hex} L:{leaves_hex})"
                self.composite_listbox.insert(tk.END, display)
    
    def generate_composites_from_links(self):
        """Generate TreeComposite objects from linked items"""
        print("[Generate Composites] Creating composites from linked items...")
        
        self.composites = []
        processed_trunks = set()
        
        # Find all trunks with links
        for trunk_item in self.trunk_items:
            trunk_name = trunk_item['name']
            
            if trunk_name in processed_trunks:
                continue
            
            metadata = trunk_item['metadata']
            base_leaves_name = metadata.get('TREE_LINKED_LEAVES', '')
            autumn_leaves_name = metadata.get('TREE_LINKED_AUTUMN', '')
            
            # Find linked items
            base_leaves_item = None
            autumn_leaves_item = None
            
            for item in self.items:
                if item['name'] == base_leaves_name:
                    base_leaves_item = item
                elif item['name'] == autumn_leaves_name:
                    autumn_leaves_item = item
            
            # Create composite if we have at least trunk and base leaves
            if base_leaves_item:
                composite = TreeComposite(
                    trunk_item=trunk_item,
                    leaves_item=base_leaves_item,
                    autumn_leaves_item=autumn_leaves_item
                )
                composite.name = f"tree_{trunk_item['hex_id']:04X}"
                self.composites.append(composite)
                processed_trunks.add(trunk_name)
                print(f"[Generate Composites] Created composite: {composite.name}")
        
        print(f"[Generate Composites] Generated {len(self.composites)} composites")
        self.update_composite_list()
        return len(self.composites)
    
    def save_composites(self):
        """Save composites and canvas arrangement to JSON"""
        # Generate composites from links if none exist
        if not self.composites:
            count = self.generate_composites_from_links()
            if count == 0:
                print("[Save Composites] ERROR: No linked tree sets found to save")
                return
        
        if not self.folder_path:
            print("[Save Composites] ERROR: No folder selected")
            return
        
        # Ask for layout name
        from tkinter import simpledialog
        layout_name = simpledialog.askstring("Save Layout", 
                                             "Enter layout name:",
                                             initialvalue="default")
        if not layout_name:
            print("[Save Composites] Cancelled")
            return
        
        # Sanitize filename
        safe_name = "".join(c for c in layout_name if c.isalnum() or c in (' ', '_', '-')).strip()
        json_path = os.path.join(self.folder_path, f"composite_{safe_name}.json")
        
        # Collect canvas positions for all items
        canvas_positions = {}
        for draggable in self.draggable_items:
            canvas_positions[draggable.item['name']] = {
                'x': draggable.x,
                'y': draggable.y
            }
        
        data = {
            'layout_name': layout_name,
            'composites': [comp.to_dict() for comp in self.composites],
            'canvas_positions': canvas_positions
        }
        
        try:
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"[Save Composites] SUCCESS: Saved to {json_path}")
        except Exception as e:
            print(f"[Save Composites] ERROR: Failed to save: {str(e)}")
    
    def load_composites(self):
        """Load composites and canvas arrangement from JSON"""
        if not self.folder_path:
            print("[Load Composites] ERROR: No folder selected")
            return
        
        # Find all composite JSON files
        import glob
        json_files = glob.glob(os.path.join(self.folder_path, "composite_*.json"))
        
        if not json_files:
            print(f"[Load Composites] ERROR: No composite files found in {self.folder_path}")
            return
        
        # Extract layout names
        layout_options = []
        for json_file in json_files:
            basename = os.path.basename(json_file)
            # Remove "composite_" prefix and ".json" suffix
            layout_name = basename[10:-5]  # composite_ is 10 chars, .json is 5 chars
            layout_options.append((layout_name, json_file))
        
        # Ask user which layout to load
        from tkinter import simpledialog
        layout_names = [name for name, _ in layout_options]
        
        if len(layout_options) == 1:
            selected_name = layout_options[0][0]
            json_path = layout_options[0][1]
        else:
            # Show selection dialog
            selection_text = "Available layouts:\n" + "\n".join(f"{i+1}. {name}" for i, name in enumerate(layout_names))
            choice = simpledialog.askstring("Load Layout", 
                                           f"{selection_text}\n\nEnter layout name or number:",
                                           initialvalue=layout_names[0])
            if not choice:
                print("[Load Composites] Cancelled")
                return
            
            # Try to match by name or number
            json_path = None
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(layout_options):
                    json_path = layout_options[idx][1]
            except ValueError:
                # Not a number, try name match
                for name, path in layout_options:
                    if name.lower() == choice.lower():
                        json_path = path
                        break
            
            if not json_path:
                print(f"[Load Composites] ERROR: Layout '{choice}' not found")
                return
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            # Load composites
            self.composites = []
            for comp_data in data.get('composites', []):
                composite = TreeComposite.from_dict(comp_data, self.items_dict)
                self.composites.append(composite)
            
            # Restore canvas positions if available
            canvas_positions = data.get('canvas_positions', {})
            if canvas_positions:
                for draggable in self.draggable_items:
                    item_name = draggable.item['name']
                    if item_name in canvas_positions:
                        pos = canvas_positions[item_name]
                        # Calculate delta
                        dx = pos['x'] - draggable.x
                        dy = pos['y'] - draggable.y
                        
                        # Move canvas items
                        self.canvas.move(draggable.image_item, dx, dy)
                        self.canvas.move(draggable.text_item, dx, dy)
                        if draggable.bounds_rect:
                            self.canvas.move(draggable.bounds_rect, dx, dy)
                        
                        # Update stored position
                        draggable.x = pos['x']
                        draggable.y = pos['y']
                
                # Update link lines and scroll region
                self.update_link_lines()
                self.canvas.configure(scrollregion=self.canvas.bbox("all"))
                print(f"[Load Composites] Restored canvas positions for {len(canvas_positions)} items")
            
            self.update_composite_list()
            layout_name = data.get('layout_name', 'unknown')
            print(f"[Load Composites] SUCCESS: Loaded layout '{layout_name}' with {len(self.composites)} composites")
        except Exception as e:
            print(f"[Load Composites] ERROR: Failed to load: {str(e)}")
    
    def export_all_composites(self):
        """Export ALL render configurations as separate composite images"""
        if not self.folder_path:
            print("[Export Composites] ERROR: No folder selected")
            return
        
        if not self.render_configs:
            print("[Export] ERROR: No render configurations found")
            return
        
        print(f"[Export] Exporting {len(self.render_configs)} render configurations...")
        
        # Export each render configuration
        for render_name in self.render_configs.keys():
            print(f"\n[Export] === Generating composite for '{render_name}' ===")
            self.export_single_render(render_name)
        
        print(f"\n[Export] SUCCESS: Exported {len(self.render_configs)} composite images")
    
    def export_single_render(self, render_name):
        """Export a single render configuration as a composite image"""
        print(f"[Export] Processing render: '{render_name}'...")
        
        # Get sorted trunk positions and build tree sets (reuse helper functions)
        trunk_positions = self.get_trunk_positions_sorted()
        
        if not trunk_positions:
            print("[Export] ERROR: No linked tree sets found to export")
            return
        
        print(f"[Export] Found {len(trunk_positions)} trunks in canvas order")
        tree_sets = self.build_tree_sets_from_trunks(trunk_positions)
        
        # Render composites for each tree set using per-item properties (same as preview)
        composites = []
        for tree_set in tree_sets:
            trunk_item = tree_set['trunk']
            if not trunk_item:
                continue
            
            # Get render properties for this specific trunk item (for the render being exported)
            props = self.get_item_render_props(trunk_item, render_name)
            
            # Skip if excluded
            if props['excluded']:
                print(f"[Export] Skipping excluded item: {trunk_item['name']}")
                continue
            
            # Check if trunk has any leaves at all
            has_any_leaves = tree_set['base_leaves'] or tree_set['autumn_leaves']
            
            # Trunk-only mode: render just the trunk (either by choice or no leaves available)
            if not props['show_leaves'] or not has_any_leaves:
                trunk_img = Image.open(trunk_item['path']).convert('RGBA')
                trunk_masked = apply_brightness_mask(trunk_img)
                trunk_cropped = trunk_masked.crop(trunk_masked.getbbox())
                composites.append(('trunk_only', trunk_cropped, tree_set))
                if not has_any_leaves:
                    print(f"[Export] Rendering trunk-only (no leaves): {trunk_item['name']}")
                continue
            
            # Use autumn variant if set
            if props['use_autumn'] and tree_set['autumn_leaves']:
                autumn_render = self.render_tree_set(
                    trunk_item,
                    tree_set['autumn_leaves']
                )
                composites.append(('autumn', autumn_render, tree_set))
            # Use base leaves
            elif tree_set['base_leaves']:
                base_render = self.render_tree_set(
                    trunk_item, 
                    tree_set['base_leaves']
                )
                composites.append(('base', base_render, tree_set))
            # Fallback: if no base leaves but has autumn, show autumn
            elif tree_set['autumn_leaves']:
                autumn_render = self.render_tree_set(
                    trunk_item,
                    tree_set['autumn_leaves']
                )
                composites.append(('autumn', autumn_render, tree_set))
        
        print(f"[Export] Rendered {len(composites)} tree sets for '{render_name}'")
        
        # Arrange in 16:9 layout (same as preview)
        final_image = self.arrange_composites_16_9(composites)
        
        # Save the final composite image with render name
        output_folder = os.path.join(self.folder_path, "composites_output")
        os.makedirs(output_folder, exist_ok=True)
        
        # Sanitize render name for filename
        safe_render_name = "".join(c for c in render_name if c.isalnum() or c in (' ', '_', '-')).strip()
        output_filename = f"final_render_{safe_render_name}.png"
        output_path = os.path.join(output_folder, output_filename)
        final_image.save(output_path)
        
        print(f"[Export] SUCCESS: Saved '{render_name}' composite to {output_path}")
        print(f"[Export] Image size: {final_image.width}x{final_image.height}px")
    
    def export_animated_webp(self):
        """Export animated WebP alternating between altered and original images"""
        if not self.folder_path:
            print("[Animated Export] ERROR: No folder selected")
            return
        
        if not self.render_configs:
            print("[Animated Export] ERROR: No render configurations found")
            return
        
        print(f"[Animated Export] Creating animated WebP for {len(self.render_configs)} render(s)...")
        
        # Export each render configuration as animated WebP
        for render_name in self.render_configs.keys():
            print(f"\n[Animated Export] === Creating animation for '{render_name}' ===")
            self.export_single_animated_render(render_name)
        
        print(f"\n[Animated Export] SUCCESS: Exported {len(self.render_configs)} animated WebP files")
    
    def export_single_animated_render(self, render_name):
        """Export a single render as animated WebP (altered vs original)"""
        print(f"[Animated Export] Processing render: '{render_name}'...")
        
        # Get sorted trunk positions and build tree sets (reuse helper functions)
        trunk_positions = self.get_trunk_positions_sorted()
        
        if not trunk_positions:
            print("[Animated Export] ERROR: No trunks found")
            return
        
        print(f"[Animated Export] Found {len(trunk_positions)} trunks")
        tree_sets = self.build_tree_sets_from_trunks(trunk_positions)
        
        # FRAME 1: Render altered composites (current modified art)
        altered_composites = []
        for tree_set in tree_sets:
            trunk_item = tree_set['trunk']
            if not trunk_item:
                continue
            
            props = self.get_item_render_props(trunk_item, render_name)
            
            if props['excluded']:
                print(f"[Animated Export] Skipping excluded: {trunk_item['name']}")
                continue
            
            has_any_leaves = tree_set['base_leaves'] or tree_set['autumn_leaves']
            
            # Trunk-only mode
            if not props['show_leaves'] or not has_any_leaves:
                trunk_img = Image.open(trunk_item['path']).convert('RGBA')
                trunk_masked = apply_brightness_mask(trunk_img)
                # DO NOT CROP - use full dimensions
                altered_composites.append(('trunk_only', trunk_masked, tree_set))
                continue
            
            # Use autumn or base
            if props['use_autumn'] and tree_set['autumn_leaves']:
                autumn_render = self.render_tree_set(trunk_item, tree_set['autumn_leaves'])
                altered_composites.append(('autumn', autumn_render, tree_set))
            elif tree_set['base_leaves']:
                base_render = self.render_tree_set(trunk_item, tree_set['base_leaves'])
                altered_composites.append(('base', base_render, tree_set))
            elif tree_set['autumn_leaves']:
                autumn_render = self.render_tree_set(trunk_item, tree_set['autumn_leaves'])
                altered_composites.append(('autumn', autumn_render, tree_set))
        
        print(f"[Animated Export] Rendered {len(altered_composites)} altered tree sets")
        
        # FRAME 2: Render original composites (from "original" subfolder or global folder)
        original_composites = []
        
        # Get list of folders to search for originals (reuse helper function)
        original_folders = self.get_original_folders()
        
        for folder in original_folders:
            print(f"[Animated Export] Original folder: {folder}")
        
        if not original_folders:
            print(f"[Animated Export] WARNING: No original folders found")
            print(f"[Animated Export] Checked local: {os.path.join(self.folder_path, 'original')}")
            print(f"[Animated Export] Checked global: {self.global_original_entry.get().strip() or '(not set)'}")
            print(f"[Animated Export] Creating static export instead...")
            # Just export the altered frame as static image
            altered_frame = self.arrange_composites_16_9(altered_composites)
            output_folder = os.path.join(self.folder_path, "composites_output")
            os.makedirs(output_folder, exist_ok=True)
            safe_render_name = "".join(c for c in render_name if c.isalnum() or c in (' ', '_', '-')).strip()
            output_filename = f"animated_{safe_render_name}.webp"
            output_path = os.path.join(output_folder, output_filename)
            altered_frame.save(output_path, format='WEBP', quality=95)
            print(f"[Animated Export] Saved static WebP to {output_path}")
            return
        
        print(f"[Animated Export] Searching {len(original_folders)} folder(s) for originals")
        
        for comp_type, comp_img, tree_set in altered_composites:
            trunk_item = tree_set['trunk']
            trunk_hex = trunk_item['hex_id']
            
            # Find original trunk by hex ID (use helper function)
            original_trunk_path = self.find_original_by_hex(trunk_hex, original_folders)
            if original_trunk_path:
                print(f"[Animated Export] Found original trunk 0x{trunk_hex:04X}")
            
            if not original_trunk_path:
                print(f"[Animated Export] WARNING: Original not found for trunk 0x{trunk_hex:04X}, using altered")
                original_composites.append((comp_type, comp_img, tree_set))
                continue
            
            # Get original leaves if applicable
            props = self.get_item_render_props(trunk_item, render_name)
            
            if comp_type == 'trunk_only':
                # Just load original trunk
                orig_trunk_img = Image.open(original_trunk_path).convert('RGBA')
                orig_trunk_masked = apply_brightness_mask(orig_trunk_img)
                # DO NOT CROP - use full dimensions
                original_composites.append(('trunk_only', orig_trunk_masked, tree_set))
            else:
                # Load original trunk + leaves
                leaves_item = tree_set['autumn_leaves'] if (props['use_autumn'] and tree_set['autumn_leaves']) else tree_set['base_leaves']
                if not leaves_item:
                    leaves_item = tree_set['autumn_leaves'] if tree_set['autumn_leaves'] else tree_set['base_leaves']
                
                if leaves_item:
                    leaves_hex = leaves_item['hex_id']
                    
                    # Find original leaves by hex ID (use helper function)
                    original_leaves_path = self.find_original_by_hex(leaves_hex, original_folders)
                    if original_leaves_path:
                        print(f"[Animated Export] Found original leaves 0x{leaves_hex:04X}")
                    
                    if original_leaves_path:
                        # Create original composite using original images
                        # Use FULL dimensions (no cropping) for exact alignment
                        orig_trunk_img = Image.open(original_trunk_path).convert('RGBA')
                        orig_leaves_img = Image.open(original_leaves_path).convert('RGBA')
                        
                        print(f"[Animated Export] Original trunk FULL size: {orig_trunk_img.size}")
                        print(f"[Animated Export] Original leaves FULL size: {orig_leaves_img.size}")
                        
                        # Apply masking but DO NOT CROP - use full dimensions
                        orig_trunk_masked = apply_brightness_mask(orig_trunk_img, threshold=5)
                        orig_leaves_masked = apply_brightness_mask(orig_leaves_img, threshold=5)
                        
                        # Use offset from ALTERED leaves metadata
                        leaves_metadata = leaves_item.get('metadata', {})
                        offset = int(leaves_metadata.get('TREE_LEAVES_HEIGHT_OFFSET', 50))
                        print(f"[Animated Export] Using offset: {offset}")
                        
                        # Calculate composite size using FULL dimensions (same as altered)
                        comp_width = max(orig_trunk_img.width, orig_leaves_img.width)
                        comp_height = max(orig_trunk_img.height, orig_leaves_img.height + offset)
                        
                        print(f"[Animated Export] Calculated size: {comp_width}x{comp_height}, Altered size: {comp_img.width}x{comp_img.height}")
                        
                        orig_composite = Image.new('RGBA', (comp_width, comp_height), (0, 0, 0, 0))
                        
                        # Position trunk and leaves using FULL dimensions
                        trunk_x = (comp_width - orig_trunk_img.width) // 2
                        trunk_y = comp_height - orig_trunk_img.height
                        print(f"[Animated Export] Trunk position: ({trunk_x}, {trunk_y})")
                        orig_composite.paste(orig_trunk_masked, (trunk_x, trunk_y), orig_trunk_masked)
                        
                        leaves_x = (comp_width - orig_leaves_img.width) // 2
                        leaves_y = comp_height - orig_leaves_img.height - offset
                        leaves_y = max(0, leaves_y)
                        print(f"[Animated Export] Leaves position: ({leaves_x}, {leaves_y})")
                        orig_composite.paste(orig_leaves_masked, (leaves_x, leaves_y), orig_leaves_masked)
                        
                        original_composites.append((comp_type, orig_composite, tree_set))
                        print(f"[Animated Export] Original composite: {orig_composite.size}")
                    else:
                        print(f"[Animated Export] WARNING: Original leaves not found for 0x{leaves_hex:04X}")
                        original_composites.append((comp_type, comp_img, tree_set))
                else:
                    # No leaves, just trunk
                    orig_trunk_img = Image.open(original_trunk_path).convert('RGBA')
                    orig_trunk_masked = apply_brightness_mask(orig_trunk_img)
                    # DO NOT CROP - use full dimensions
                    original_composites.append(('trunk_only', orig_trunk_masked, tree_set))
        
        print(f"[Animated Export] Loaded {len(original_composites)} original tree sets")
        
        # CRITICAL: Resize original composites to match altered dimensions exactly
        # This ensures both frames use identical layout calculations
        print(f"[Animated Export] Normalizing composite dimensions for consistent layout...")
        normalized_originals = []
        for i, (orig_type, orig_img, orig_tree_set) in enumerate(original_composites):
            if i < len(altered_composites):
                alt_type, alt_img, alt_tree_set = altered_composites[i]
                
                # If dimensions differ, resize/pad original to match altered
                if orig_img.size != alt_img.size:
                    target_width, target_height = alt_img.size
                    
                    # Create canvas of target size
                    normalized = Image.new('RGBA', (target_width, target_height), (0, 0, 0, 0))
                    
                    # Center the original image (bottom-aligned for trees)
                    x_offset = (target_width - orig_img.width) // 2
                    y_offset = target_height - orig_img.height  # Bottom-align
                    
                    normalized.paste(orig_img, (x_offset, y_offset), orig_img)
                    normalized_originals.append((orig_type, normalized, orig_tree_set))
                    print(f"[Animated Export] Resized original {i}: {orig_img.size} -> {normalized.size}")
                else:
                    normalized_originals.append((orig_type, orig_img, orig_tree_set))
            else:
                normalized_originals.append((orig_type, orig_img, orig_tree_set))
        
        # Now both sets have identical dimensions, so layout will be identical
        altered_frame = self.arrange_composites_16_9(altered_composites)
        original_frame = self.arrange_composites_16_9(normalized_originals)
        
        # Ensure both frames are same size
        max_width = max(altered_frame.width, original_frame.width)
        max_height = max(altered_frame.height, original_frame.height)
        
        if altered_frame.size != (max_width, max_height):
            padded = Image.new('RGBA', (max_width, max_height), (0, 0, 0, 255))
            padded.paste(altered_frame, (0, 0))
            altered_frame = padded
        
        if original_frame.size != (max_width, max_height):
            padded = Image.new('RGBA', (max_width, max_height), (0, 0, 0, 255))
            padded.paste(original_frame, (0, 0))
            original_frame = padded
        
        # Create animated WebP: 2 frames, 2 seconds each (2000ms), looping
        output_folder = os.path.join(self.folder_path, "composites_output")
        os.makedirs(output_folder, exist_ok=True)
        
        safe_render_name = "".join(c for c in render_name if c.isalnum() or c in (' ', '_', '-')).strip()
        output_filename = f"animated_{safe_render_name}.webp"
        output_path = os.path.join(output_folder, output_filename)
        
        # Save as animated WebP
        altered_frame.save(
            output_path,
            format='WEBP',
            save_all=True,
            append_images=[original_frame],
            duration=2000,  # 2 seconds per frame
            loop=0,  # Infinite loop
            quality=95
        )
        
        print(f"[Animated Export] SUCCESS: Saved animated WebP to {output_path}")
        print(f"[Animated Export] Animation: 2 frames @ 2000ms each, looping")
        print(f"[Animated Export] Frame size: {max_width}x{max_height}px")

def main():
    root = tk.Tk()
    app = TreeCompositorUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
