"""
Isometric Python Game Map Editor

An interactive Python application for editing isometric maps, featuring:
Automated image recognition and categorization of diagonal isometric tiles
JSON-based storage with dual-coordinate systems
Tag-based item filtering and organization

Features

1. Image Management
Load items from a designated folder
Automatic detection and classification of diagonal tiles based on image dimensions and alpha transparency

2. Tagging and Database
Assign user-defined textual tags to items
Filter and group items by tags for efficient editing

3. Isometric Map Representation
Coordinate system:
World Coordinates: Isometric coordinates (called "grid") matches the in-game map format of ultima online 
Image2d Coordinates: Secondary image placement coordinates used for confirming correct world rendering ( images are placed starting from top left pixel )
JSON data structure storing items individually, each with:
Item ID (hexadecimal, e.g., "0x002C")
WorldGrid coordinate
Height offset (tiles have height offset 0)
Local offset adjustments
Image2d position

4. User Interface
Python GUI (Tkinter or PyQt5)
Canvas rendering of isometric tiles
Interactive placement and manipulation of items

5. JSON Structure Example

{
  "map": {
    "elements": [
      {
        "grid_coordinate": "0,0",
        "item_id": "0x0001",
        "height_offset": 0,
        "local_offset": [0, 0],
        "image2d_position": [0, 0]
      },
      {
        "item_id": "0x002C",
        "grid_coordinate": "1,0",
        "height_offset": 10,
        "local_offset": [2, 5],
        "image2d_position": [12, 5]
      }
    ]
  }
}

Development Roadmap

Stage 1: Foundation
Initialize project structure
Develop item loader and image processing for tile detection

Stage 2: Database and Tagging
Implement tagging and filtering logic
Database interface

Stage 3: Map and JSON Handling
Define JSON schema
Coordinate mapping functions

Stage 4: GUI Implementation
Create interactive GUI
Integrate map rendering and editing

TOOLSGROUP::MAP
SORTGROUP::6
SORTPRIORITY::62
STATUS::not working
VERSION::20251207
"""
DEFAULT_ITEM_IMAGE_FOLDER = r"D:\ULTIMA\MODS\ultima_online_mods\Z_Tools\items"

import os
import re
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
import threading
import queue
from functools import lru_cache

# --- VIRTUALIZED THUMBNAIL GRID FOR SCALABLE BROWSING ---
THUMB_SIZE = (64, 64)
CELL_WIDTH = 80
CELL_HEIGHT = 110
CACHE_SIZE = 512  # LRU cache size for thumbnails

class VirtualThumbGrid(tk.Frame):
    def __init__(self, master, item_entries, get_image_path, on_select=None, bg="#181818"):
        super().__init__(master, bg=bg)
        self.item_entries = item_entries  # List[ItemEntry]
        self.get_image_path = get_image_path  # function: entry -> image path
        self.on_select = on_select
        self.bg = bg

        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.v_scroll = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.bind('<Configure>', self._on_resize)
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        self.canvas.bind('<Button-1>', self._on_click)

        self.visible_items = []  # [(canvas_id, entry_idx)]
        self._img_refs = {}  # idx: PhotoImage
        self.selected_idx = None
        self._thumb_queue = queue.Queue()

        self._thumb_cache = lru_cache(maxsize=CACHE_SIZE)(self._load_thumbnail)
        self._loader_thread = threading.Thread(target=self._thumb_loader, daemon=True)
        self._loader_thread.start()

        self._pending_update = False
        self._needs_update = True
        self._last_height = 0
        self._last_width = 0
        self.after(50, self._periodic_update)

    def set_items(self, item_entries):
        self.item_entries = item_entries
        self._img_refs.clear()
        self._needs_update = True
        self._schedule_update()

    def _on_resize(self, event):
        if event.width != self._last_width or event.height != self._last_height:
            self._last_width = event.width
            self._last_height = event.height
            self._needs_update = True
            self._schedule_update()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
        self._needs_update = True
        self._schedule_update()

    def _on_click(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        for canvas_id, idx in self.visible_items:
            bbox = self.canvas.bbox(canvas_id)
            if bbox and bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]:
                self.selected_idx = idx
                if self.on_select:
                    self.on_select(self.item_entries[idx])
                self._needs_update = True
                self._schedule_update()
                break

    def _periodic_update(self):
        if self._pending_update or self._needs_update:
            self._draw_visible()
            self._pending_update = False
            self._needs_update = False
        self.after(50, self._periodic_update)

    def _schedule_update(self):
        self._pending_update = True

    def _draw_visible(self):
        self.canvas.delete('all')
        self.visible_items.clear()
        self._img_refs.clear()
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        n_cols = max(1, width // CELL_WIDTH)
        n_rows = (height // CELL_HEIGHT) + 2
        total = len(self.item_entries)
        items_per_page = n_cols * n_rows
        y0 = int(self.canvas.canvasy(0))
        start_row = max(0, y0 // CELL_HEIGHT)
        start_idx = start_row * n_cols
        end_idx = min(total, start_idx + items_per_page)
        self.canvas.config(scrollregion=(0, 0, n_cols*CELL_WIDTH, ((total+n_cols-1)//n_cols)*CELL_HEIGHT))
        for idx in range(start_idx, end_idx):
            entry = self.item_entries[idx]
            col = (idx % n_cols)
            row = (idx // n_cols)
            x = col * CELL_WIDTH + 8
            y = row * CELL_HEIGHT + 8
            thumb = self._get_thumb_async(idx, entry)
            img_id = self.canvas.create_image(x, y, anchor=tk.NW, image=thumb)
            self.visible_items.append((img_id, idx))
            self._img_refs[idx] = thumb
            # Draw border for selection
            if idx == self.selected_idx:
                self.canvas.create_rectangle(x-2, y-2, x+THUMB_SIZE[0]+2, y+THUMB_SIZE[1]+2, outline="#FFD700", width=3)
            # Draw text
            self.canvas.create_text(x+THUMB_SIZE[0]//2, y+THUMB_SIZE[1]+16, text=str(entry.item_id), fill="#fff", font=("Arial", 10))
            if hasattr(entry, 'tags') and entry.tags:
                tag_str = ", ".join(sorted(entry.tags))
                self.canvas.create_text(x+THUMB_SIZE[0]//2, y+THUMB_SIZE[1]+32, text=tag_str, fill="#8F8", font=("Arial", 9))

    def _get_thumb_async(self, idx, entry):
        try:
            return self._thumb_cache(self.get_image_path(entry))
        except Exception:
            # Queue for background loading
            self._thumb_queue.put((idx, entry))
            return self._placeholder()

    def _thumb_loader(self):
        while True:
            try:
                idx, entry = self._thumb_queue.get()
                path = self.get_image_path(entry)
                thumb = self._thumb_cache(path)
                self._needs_update = True
                self._schedule_update()
            except Exception:
                pass

    def _load_thumbnail(self, path):
        if not os.path.exists(path):
            return self._placeholder()
        img = Image.open(path)
        img.thumbnail(THUMB_SIZE, Image.LANCZOS)
        return ImageTk.PhotoImage(img)

    def _placeholder(self):
        img = Image.new('RGBA', THUMB_SIZE, (40, 40, 40, 255))
        return ImageTk.PhotoImage(img)

# --- COLOR PALETTE FOR DARK MODE ---
DARK_BG = "#181818"           # Main background
DARK_FRAME = "#232323"        # Frame backgrounds
DARK_BUTTON = "#2e2e2e"       # Default button background
MUTED_GREEN = "#3a5f3a"       # Muted green
MUTED_BLUE = "#33506d"        # Muted blue
MUTED_PURPLE = "#4a3a5f"      # Muted purple
LIGHT_TEXT = "#e0e0e0"        # Light gray text
ACCENT_BORDER = "#444"

# --- CONFIGURATION ---
ITEM_IMAGE_FOLDER = "../item_images"
ITEM_ID_PATTERN = re.compile(r"0x[0-9A-Fa-f]{4}")
SUPPORTED_FORMATS = (".png", ".bmp")
TAG_DB_FILENAME = "item_tags.json"

# --- DATA STRUCTURES ---
class ItemEntry:
    def __init__(self, item_id, image_path, is_diagonal_tile, tags=None):
        self.item_id = item_id
        self.image_path = image_path
        self.is_diagonal_tile = is_diagonal_tile
        self.tags = set(tags) if tags else set()
        self.image = None  # PIL Image, loaded on demand

    def load_image(self):
        if self.image is None:
            self.image = Image.open(self.image_path)
        return self.image

    def add_tag(self, tag):
        self.tags.add(tag)

    def remove_tag(self, tag):
        self.tags.discard(tag)

    def to_dict(self):
        return {
            "item_id": self.item_id,
            "image_path": self.image_path,
            "is_diagonal_tile": self.is_diagonal_tile,
            "tags": list(self.tags)
        }

    @staticmethod
    def from_dict(d):
        return ItemEntry(
            d["item_id"], d["image_path"], d["is_diagonal_tile"], d.get("tags", [])
        )

# --- TAG DATABASE ---
def load_tags(folder_path):
    tags_path = os.path.join(folder_path, TAG_DB_FILENAME)
    if not os.path.exists(tags_path):
        return {}
    try:
        with open(tags_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load tags: {e}")
        return {}

def save_tags(folder_path, items):
    tags_path = os.path.join(folder_path, TAG_DB_FILENAME)
    tag_data = {item.item_id: list(item.tags) for item in items if item.tags}
    try:
        with open(tags_path, "w", encoding="utf-8") as f:
            json.dump(tag_data, f, indent=2)
    except Exception as e:
        print(f"Failed to save tags: {e}")

# --- IMAGE PROCESSING ---
def detect_diagonal_isometric_tile(image: Image.Image) -> bool:
    """
    Analyze an image to determine if it is a diagonal isometric tile.
    Uses the alpha channel and bounding box shape as a heuristic.
    Returns True if the image is likely an isometric tile, else False.
    """
    alpha_channel = image.split()[-1]
    alpha_array = np.array(alpha_channel)
    non_transparent_indices = np.argwhere(alpha_array > 0)
    if non_transparent_indices.shape[0] == 0:
        return False
    min_y, min_x = non_transparent_indices.min(axis=0)
    max_y, max_x = non_transparent_indices.max(axis=0)
    bounding_box_height = max_y - min_y
    bounding_box_width = max_x - min_x
    aspect_ratio = bounding_box_width / max(bounding_box_height, 1)
    center_y, center_x = (min_y + max_y) // 2, (min_x + max_x) // 2
    sample_points = [
        (center_y, min_x), (center_y, max_x), (min_y, center_x), (max_y, center_x)
    ]
    edge_alpha_values = [alpha_array[y, x] for y, x in sample_points]
    if min(edge_alpha_values) > 0 and 1.2 < aspect_ratio < 2.0:
        return True
    return False

# --- ITEM LOADER ---
def load_items_from_folder(folder_path):
    items = []
    tag_db = load_tags(folder_path)
    for fname in os.listdir(folder_path):
        if not fname.lower().endswith(SUPPORTED_FORMATS):
            continue
        match = ITEM_ID_PATTERN.search(fname)
        if not match:
            continue
        item_id = match.group(0).upper()
        image_path = os.path.join(folder_path, fname)
        try:
            image = Image.open(image_path)
            is_diagonal = detect_diagonal_isometric_tile(image)
        except Exception as e:
            print(f"Failed to process {fname}: {e}")
            continue
        tags = tag_db.get(item_id, [])
        entry = ItemEntry(item_id, image_path, is_diagonal, tags)
        items.append(entry)
    return items

# --- MINIMAL GUI FOR ITEM INSPECTION ---
class ItemBrowserGUI(tk.Frame):
    def __init__(self, master, items, folder_path):
        print(f"[DEBUG] ItemBrowserGUI.__init__ called")
        print(f"[DEBUG] master type: {type(master)}, value: {master}")
        print(f"[DEBUG] items type: {type(items)}, len: {len(items) if hasattr(items, '__len__') else 'N/A'}")
        print(f"[DEBUG] folder_path type: {type(folder_path)}, value: {folder_path}")
        try:
            super().__init__(master, bg=DARK_BG)
        except Exception as e:
            import traceback
            print(f"[ERROR] Exception in super().__init__ of ItemBrowserGUI: {e}")
            traceback.print_exc()
            raise
        self.items = items
        self.filtered_items = items
        self.folder_path = folder_path
        self.selected_item = None
        print(f"[DEBUG] ItemBrowserGUI.__init__ completed super().__init__")
        self.create_widgets()
        self.display_items()

    def apply_filter(self):
        filter_item_id = self.filter_var.get().strip().upper()
        filter_tag = self.tag_filter_var.get().strip()
        self.filtered_items = filter_items_by_id_and_tag(self.items, filter_item_id, filter_tag)
        self.display_items()
        self.update_tag_combo()

    def clear_filter(self):
        self.filter_var.set("")
        self.tag_filter_var.set("")
        self.filtered_items = self.items
        self.display_items()
        self.update_tag_combo()

    def display_items(self):
        self.canvas.delete("all")
        x, y = 20, 20
        self.item_positions = {}
        for entry in self.filtered_items:
            try:
                img = entry.load_image().copy().resize((64, 64), Image.NEAREST)
                tkimg = ImageTk.PhotoImage(img)
                img_id = self.canvas.create_image(x, y, anchor=tk.NW, image=tkimg)
                self.canvas.create_text(x + 32, y + 70, text=entry.item_id, fill="#FFF", font=("Arial", 10))
                tag_str = ", ".join(sorted(entry.tags))
                self.canvas.create_text(x + 32, y + 85, text=tag_str, fill="#8F8", font=("Arial", 9))
                if getattr(entry, 'is_diagonal_tile', False):
                    self.canvas.create_rectangle(x, y, x+64, y+64, outline="#0F0", width=2)
                else:
                    self.canvas.create_rectangle(x, y, x+64, y+64, outline="#F00", width=2)
                # Keep reference to images
                if not hasattr(self, '_img_refs'):
                    self._img_refs = []
                self._img_refs.append(tkimg)
                # Track position for click selection
                self.item_positions[img_id] = entry
                x += 80
                if x > 900:
                    x = 20
                    y += 110
            except Exception as e:
                print(f"Display error: {e}")
        self.selected_item = None
        self.update_tag_listbox()
        self.update_tag_combo()

    def update_tag_combo(self):
        all_tags = set()
        for item in self.items:
            all_tags.update(item.tags)
        tag_list = sorted(all_tags)
        self.tag_combo['values'] = tag_list

    def on_canvas_click(self, event):
        clicked = self.canvas.find_closest(event.x, event.y)
        item = self.item_positions.get(clicked[0])
        if item:
            self.selected_item = item
            self.update_tag_listbox()

    def update_tag_listbox(self):
        self.tag_listbox.delete(0, tk.END)
        if self.selected_item:
            for tag in sorted(self.selected_item.tags):
                self.tag_listbox.insert(tk.END, tag)

    def add_tag_to_selected(self):
        tag = self.tag_entry.get().strip()
        if self.selected_item and tag:
            self.selected_item.add_tag(tag)
            self.update_tag_listbox()
            self.display_items()
            self.update_tag_combo()

    def remove_tag_from_selected(self):
        sel = self.tag_listbox.curselection()
        if self.selected_item and sel:
            tag = self.tag_listbox.get(sel[0])
            self.selected_item.remove_tag(tag)
            self.update_tag_listbox()
            self.display_items()
            self.update_tag_combo()

    def save_tags(self):
        save_tags(self.folder_path, self.items)


    def create_widgets(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TCombobox', fieldbackground=DARK_BUTTON, background=DARK_BUTTON, foreground=LIGHT_TEXT)
        style.configure('TLabel', background=DARK_FRAME, foreground=LIGHT_TEXT)
        style.configure('TButton', background=DARK_BUTTON, foreground=LIGHT_TEXT)
        style.map('TButton', background=[('active', MUTED_GREEN)], foreground=[('active', LIGHT_TEXT)])

        filter_frame = tk.Frame(self, bg=DARK_FRAME)
        filter_frame.pack(fill=tk.X, padx=8, pady=8)
        tk.Label(filter_frame, text="Filter by ID:", bg=DARK_FRAME, fg=LIGHT_TEXT).pack(side=tk.LEFT, padx=4)
        self.filter_var = tk.StringVar()
        filter_entry = tk.Entry(filter_frame, textvariable=self.filter_var, bg=DARK_BUTTON, fg=LIGHT_TEXT, insertbackground=LIGHT_TEXT)
        filter_entry.pack(side=tk.LEFT, padx=4)
        filter_btn = tk.Button(filter_frame, text="Apply", command=self.apply_filter, bg=MUTED_GREEN, fg=LIGHT_TEXT, activebackground="#497f49", activeforeground=LIGHT_TEXT)
        filter_btn.pack(side=tk.LEFT, padx=4)
        clear_btn = tk.Button(filter_frame, text="Clear", command=self.clear_filter, bg=DARK_BUTTON, fg=LIGHT_TEXT, activebackground="#444", activeforeground=LIGHT_TEXT)
        clear_btn.pack(side=tk.LEFT, padx=4)
        tk.Label(filter_frame, text="Tag:", bg=DARK_FRAME, fg=LIGHT_TEXT).pack(side=tk.LEFT, padx=8)
        self.tag_filter_var = tk.StringVar()
        tag_combo = ttk.Combobox(filter_frame, textvariable=self.tag_filter_var, state="readonly", style='TCombobox')
        tag_combo.pack(side=tk.LEFT, padx=4)
        self.tag_combo = tag_combo
        tag_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filter())

        self.canvas = tk.Canvas(self, bg=DARK_BG, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        # --- Tag Frame and Tag Controls ---
        tag_frame = tk.Frame(self, bg=DARK_FRAME)
        tag_frame.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(tag_frame, text="Selected Item Tags:").pack(side=tk.LEFT)
        self.tag_listbox = tk.Listbox(tag_frame, height=2, width=24)
        self.tag_listbox.pack(side=tk.LEFT, padx=4)
        self.tag_entry = ttk.Entry(tag_frame, width=12)
        self.tag_entry.pack(side=tk.LEFT, padx=4)
        ttk.Button(tag_frame, text="Add Tag", command=self.add_tag_to_selected).pack(side=tk.LEFT)
        ttk.Button(tag_frame, text="Remove Tag", command=self.remove_tag_from_selected).pack(side=tk.LEFT)

        # Map Editor Button
        ttk.Button(self, text="Open Map Editor", command=self.open_map_editor).pack(pady=8)

    # ... (rest of ItemBrowser unchanged)

    def open_map_editor(self):
        editor = MapEditorUI(self.items)
        editor.mainloop()

# --- MAP EDITOR UI ---
class MapEditorUI(tk.Toplevel):
    def __init__(self, items):
        super().__init__()
        self.title("Isometric Map Editor")
        self.geometry("1200x800")
        self.items = items
        self.map_model = MapModel()
        self.selected_item = None
        self.selected_grid = (0,0)
        self.canvas_origin = (600, 350)  # Center of canvas
        self.cell_size = 64
        self.create_widgets()
        self.draw_grid()
        self.placed_images = []

    def create_widgets(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TCombobox', fieldbackground=DARK_BUTTON, background=DARK_BUTTON, foreground=LIGHT_TEXT)
        style.configure('TLabel', background=DARK_FRAME, foreground=LIGHT_TEXT)
        style.configure('TButton', background=DARK_BUTTON, foreground=LIGHT_TEXT)
        style.map('TButton', background=[('active', MUTED_GREEN)], foreground=[('active', LIGHT_TEXT)])

        top_frame = tk.Frame(self, bg=DARK_FRAME)
        top_frame.pack(fill=tk.X, padx=8, pady=4)
        tk.Label(top_frame, text="Selected Item:", bg=DARK_FRAME, fg=LIGHT_TEXT).pack(side=tk.LEFT)
        self.item_combo = ttk.Combobox(top_frame, width=12, values=[i.item_id for i in self.items], style='TCombobox')
        self.item_combo.pack(side=tk.LEFT)
        self.item_combo.bind("<<ComboboxSelected>>", self.on_item_selected)
        tk.Label(top_frame, text="Height Offset:", bg=DARK_FRAME, fg=LIGHT_TEXT).pack(side=tk.LEFT, padx=(16,2))
        self.height_var = tk.IntVar(value=0)
        tk.Entry(top_frame, textvariable=self.height_var, width=6, bg=DARK_BUTTON, fg=LIGHT_TEXT, insertbackground=LIGHT_TEXT).pack(side=tk.LEFT)
        tk.Label(top_frame, text="Local Offset (x,y):", bg=DARK_FRAME, fg=LIGHT_TEXT).pack(side=tk.LEFT, padx=(16,2))
        self.local_offset_var = tk.StringVar(value="0,0")
        tk.Entry(top_frame, textvariable=self.local_offset_var, width=8, bg=DARK_BUTTON, fg=LIGHT_TEXT, insertbackground=LIGHT_TEXT).pack(side=tk.LEFT)
        tk.Button(top_frame, text="Save Map", command=self.save_map, bg=MUTED_GREEN, fg=LIGHT_TEXT, activebackground="#497f49", activeforeground=LIGHT_TEXT).pack(side=tk.LEFT, padx=8)
        tk.Button(top_frame, text="Load Map", command=self.load_map, bg=MUTED_BLUE, fg=LIGHT_TEXT, activebackground="#466c98", activeforeground=LIGHT_TEXT).pack(side=tk.LEFT)
        # Canvas
        self.canvas = tk.Canvas(self, bg=DARK_BG, width=1100, height=650, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.status_var = tk.StringVar()
        status_label = tk.Label(self, textvariable=self.status_var, anchor="w", bg=DARK_FRAME, fg=LIGHT_TEXT)
        status_label.pack(fill=tk.X, padx=8, pady=(0,8))

    def on_item_selected(self, event=None):
        item_id = self.item_combo.get()
        for item in self.items:
            if item.item_id == item_id:
                self.selected_item = item
                break

    def on_canvas_click(self, event):
        clicked_grid_x, clicked_grid_y = self.pixel_to_grid(event.x, event.y)
        self.selected_grid = (clicked_grid_x, clicked_grid_y)
        if self.selected_item:
            # Place item at grid
            try:
                height_offset = int(self.height_var.get())
            except Exception:
                height_offset = 0
            try:
                local_offset_tuple = tuple(map(int, self.local_offset_var.get().split(",")))
            except Exception:
                local_offset_tuple = (0,0)
            new_map_element = MapElement(self.selected_item.item_id, (clicked_grid_x, clicked_grid_y), height_offset, local_offset_tuple)
            self.map_model.add_element(new_map_element)
            self.draw_grid()
            self.status_var.set(f"Placed {self.selected_item.item_id} at {clicked_grid_x},{clicked_grid_y}")
        else:
            # Select item on grid for possible removal
            found_element = None
            for map_element in self.map_model.elements:
                if map_element.grid_coordinate == (clicked_grid_x, clicked_grid_y):
                    found_element = map_element
                    break
            if found_element:
                self.map_model.remove_element(found_element)
                self.draw_grid()
                self.status_var.set(f"Removed item at {clicked_grid_x},{clicked_grid_y}")

    def draw_grid(self):
        """
        Draw the isometric grid and all placed map elements on the canvas.
        """
        self.canvas.delete("all")
        self.placed_images = []
        grid_radius = 10  # grid radius in tiles
        for grid_x in range(-grid_radius, grid_radius+1):
            for grid_y in range(-grid_radius, grid_radius+1):
                pixel_x, pixel_y = self.grid_to_pixel(grid_x, grid_y)
                cell_size = self.cell_size
                diamond_points = [
                    (pixel_x, pixel_y-cell_size//2),
                    (pixel_x+cell_size//2, pixel_y),
                    (pixel_x, pixel_y+cell_size//2),
                    (pixel_x-cell_size//2, pixel_y)
                ]
                self.canvas.create_polygon(diamond_points, outline="#444", fill="", width=1)
                if (grid_x, grid_y) == self.selected_grid:
                    self.canvas.create_polygon(diamond_points, outline="#FFD700", fill="", width=3)
        # Draw placed items
        for map_element in self.map_model.elements:
            pixel_x, pixel_y = self.grid_to_pixel(*map_element.grid_coordinate)
            item_entry = next((i for i in self.items if i.item_id == map_element.item_id), None)
            if item_entry:
                item_image = item_entry.load_image().copy().resize((self.cell_size, self.cell_size), Image.NEAREST)
                tk_image = ImageTk.PhotoImage(item_image)
                self.canvas.create_image(pixel_x, pixel_y, anchor=tk.CENTER, image=tk_image)
                self.placed_images.append(tk_image)
                self.canvas.create_text(
                    pixel_x, pixel_y+self.cell_size//2+8,
                    text=f"{map_element.item_id}\nH:{map_element.height_offset} O:{map_element.local_offset}",
                    fill="#FFF", font=("Arial", 8))

    def grid_to_pixel(self, gx, gy):
        cx, cy = self.canvas_origin
        cs = self.cell_size
        px = cx + (gx - gy) * (cs//2)
        py = cy + (gx + gy) * (cs//4)
        return (px, py)

    def pixel_to_grid(self, px, py):
        cx, cy = self.canvas_origin
        cs = self.cell_size
        dx = px - cx
        dy = py - cy
        gx = int((dx/(cs/2) + dy/(cs/4)) / 2)
        gy = int((dy/(cs/4) - dx/(cs/2)) / 2)
        return (gx, gy)

    def save_map(self):
        save_map_dialog(self.map_model)

    def load_map(self):
        loaded = load_map_dialog()
        if loaded:
            self.map_model = loaded
            self.draw_grid()
            self.status_var.set("Map loaded.")

    def create_widgets(self):
        # Top filter frame
        self.filter_var = tk.StringVar()
        self.tag_filter_var = tk.StringVar()
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(filter_frame, text="Filter by Item ID:").pack(side=tk.LEFT)
        ttk.Entry(filter_frame, textvariable=self.filter_var, width=12).pack(side=tk.LEFT, padx=4)
        ttk.Label(filter_frame, text="Tag:").pack(side=tk.LEFT, padx=(16,2))
        self.tag_combo = ttk.Combobox(filter_frame, textvariable=self.tag_filter_var, width=12)
        self.tag_combo.pack(side=tk.LEFT)
        ttk.Button(filter_frame, text="Apply", command=self.apply_filter).pack(side=tk.LEFT, padx=8)
        ttk.Button(filter_frame, text="Clear", command=self.clear_filter).pack(side=tk.LEFT)
        ttk.Button(filter_frame, text="Save Tags", command=self.save_tags).pack(side=tk.LEFT, padx=16)
        # Main canvas
        self.canvas = tk.Canvas(self, bg="#222", scrollregion=(0, 0, 4000, 4000))
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.scroll_y = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=self.scroll_y.set)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        # Tag editing panel
        tag_frame = ttk.Frame(self)
        tag_frame.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(tag_frame, text="Selected Item Tags:").pack(side=tk.LEFT)
        self.tag_listbox = tk.Listbox(tag_frame, height=2, width=24)
        self.tag_listbox.pack(side=tk.LEFT, padx=4)
        self.tag_entry = ttk.Entry(tag_frame, width=12)
        self.tag_entry.pack(side=tk.LEFT, padx=4)
        ttk.Button(tag_frame, text="Add Tag", command=self.add_tag_to_selected).pack(side=tk.LEFT)
        ttk.Button(tag_frame, text="Remove Tag", command=self.remove_tag_from_selected).pack(side=tk.LEFT)

def filter_items_by_id_and_tag(item_list, filter_item_id, filter_tag):
    """
    Returns a filtered list of ItemEntry objects by item_id substring and/or tag.
    """
    filtered = item_list
    if filter_item_id:
        filtered = [item for item in filtered if filter_item_id in item.item_id]
    if filter_tag:
        filtered = [item for item in filtered if filter_tag in item.tags]
    return filtered


# --- MAP ELEMENT DATA STRUCTURE ---
class MapElement:
    def __init__(self, item_id, grid_coordinate, height_offset=0, local_offset=(0,0), coord2d=None):
        self.item_id = item_id
        self.grid_coordinate = tuple(grid_coordinate)
        self.height_offset = height_offset
        self.local_offset = tuple(local_offset)
        self.coord2d = tuple(coord2d) if coord2d else None

    def to_dict(self):
        d = {
            "item_id": self.item_id,
            "grid_coordinate": f"{self.grid_coordinate[0]},{self.grid_coordinate[1]}",
            "height_offset": self.height_offset,
            "local_offset": list(self.local_offset)
        }
        if self.coord2d:
            d["coord2d"] = list(self.coord2d)
        return d

    @staticmethod
    def from_dict(d):
        grid = tuple(map(int, d["grid_coordinate"].split(",")))
        local = tuple(d.get("local_offset", (0,0)))
        coord2d = tuple(d["coord2d"]) if "coord2d" in d else None
        return MapElement(d["item_id"], grid, d.get("height_offset", 0), local, coord2d)

# --- MAP MODEL ---
class MapModel:
    def __init__(self):
        self.elements = []  # List[MapElement]

    def add_element(self, element):
        self.elements.append(element)

    def remove_element(self, element):
        self.elements = [e for e in self.elements if e is not element]

    def to_dict(self):
        return {"map": {"elements": [e.to_dict() for e in self.elements]}}

    def save_to_file(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @staticmethod
    def from_dict(d):
        m = MapModel()
        for elem in d.get("map", {}).get("elements", []):
            m.add_element(MapElement.from_dict(elem))
        return m

    @staticmethod
    def load_from_file(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return MapModel.from_dict(data)

# --- COORDINATE MAPPING UTILITIES ---
def grid_to_2d(grid_x, grid_y):
    # Example: isometric to 2D (simple diamond, can be adjusted)
    px = grid_x - grid_y
    py = (grid_x + grid_y) // 2
    return (px, py)

def coord2d_to_grid(px, py):
    # Inverse of above (approximate)
    grid_x = (px + 2*py) // 2
    grid_y = (2*py - px) // 2
    return (grid_x, grid_y)

# --- MAP FILE DIALOGS ---
def save_map_dialog(map_model):
    path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
    if not path:
        return
    map_model.save_to_file(path)
    print(f"Map saved to {path}")

def load_map_dialog():
    path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
    if not path:
        return None
    return MapModel.load_from_file(path)

# --- MAIN ENTRY POINT ---
def main():
    """
    Main entry point for the Isometric Python Game Map Editor.
    - Prompts user for item image folder.
    - Loads items and tags.
    - Launches the Item Browser and Map Editor UI.
    Handles errors gracefully for production use.
    """
    try:
        item_image_folder_path = filedialog.askdirectory(title="Select Item Image Folder", initialdir=DEFAULT_ITEM_IMAGE_FOLDER)
        if not item_image_folder_path:
            print("No item image folder selected. Exiting.")
            return
        item_entries = load_items_from_folder(item_image_folder_path)
        if not item_entries:
            print("No valid item images found in the selected folder. Exiting.")
            return
        print(f"Loaded {len(item_entries)} items from {item_image_folder_path}.")
        print("[DEBUG] Creating Tk root window...")
        root = tk.Tk()
        print(f"[DEBUG] Root window created: {root}, type: {type(root)}")
        root.title("Isometric Item Browser")
        root.geometry("1000x700")
        print(f"[DEBUG] Creating ItemBrowser with root, item_entries, item_image_folder_path")
        item_browser_app = ItemBrowserGUI(root, item_entries, item_image_folder_path)
        print(f"[DEBUG] ItemBrowser created: {item_browser_app}")
        item_browser_app.pack(fill="both", expand=True)
        print(f"[DEBUG] Packed ItemBrowser, entering mainloop")
        root.mainloop()
        print(f"[DEBUG] mainloop exited")
    except Exception as main_exception:
        import traceback
        print("An unexpected error occurred during startup:")
        traceback.print_exc()
        tk.messagebox.showerror("Fatal Error", f"A fatal error occurred:\n{main_exception}")

if __name__ == "__main__":
    main()