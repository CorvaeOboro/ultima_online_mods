"""
PROJECT DASHBOARD - an Ultima Online art item review and editor launcher 
for each ITEM displays upscaled image with buttons to jump to various folders and files ,
opening the file with photoshop and opening folderpath with explorer  
filter by category and groups , sort by work in progress to focus on items missing stages or unreviewed

PROJECT STRUCTURE
CATEGORY folder > GROUP folder > ITEM psd and bmp > Upscale folder > ITEM psd and .png ( upscaled )  > ITEM folder > gen folder > 01 folder
ART/ART_Food/item_food_apple.psd             # base item psd
ART/ART_Food/Upscale/item_food_apple.psd     # upscale item psd note how it matches the same filename 
ART/ART_Food/Upscale/item_food_apple/gen/01/apple_gen_a.png     # generated image that has been ranked into "01" 

ITEMs can be determined by finding any bmp psd pair in the base folder or png psd pair in upscale folder , if one but not the other exists show the available preview image with a special color coded border around it 

for each ITEM it will be displayed with 
a button to open psd with photoshop ,
a button to open file explorer to the location 
a button to open file explorer to the location to its gen 01 folder ( the best selected generated images )
a button to open the upscale psd with photoshop ,

TODO:
hover over item to display the full path  in upper right of up , 
optionally the display of only items that contain a suffix using hex id as a  filter , example item_apple_0x0294.png the 0x indicates hexidecimal id .


"""

import os
import subprocess
from pathlib import Path
from tkinter import *
from tkinter import ttk
from PIL import Image, ImageTk
import logging
import shutil
import threading
from queue import Queue, Empty
import re

# Setup logging for debug output
logging.basicConfig(level=logging.DEBUG, format='%(message)s')

# Dynamically determine PROJECT_ROOT based on script location
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
PHOTOSHOP_EXE = r"C:\Program Files\Adobe\Adobe Photoshop 2024\Photoshop.exe"
MAX_ASSET_WIDTH = 192
THUMB_SIZE = (MAX_ASSET_WIDTH, 108)
HEX_FILTER_ENABLED = False  # Set to True to enable filtering by "0x" in filename
HEX_PREFIX = "0x"
HEX_SUFFIX_RE = re.compile(r"0x[0-9A-Fa-f]+$")

# Debug print control
DEBUG_MODE = False  # Toggle verbose prints for non-critical status/errors
STATIC_PREVIEWS = True  # If True, do not generate PSD previews during session; UI remains static

# Startup category selection: which categories start enabled (others start excluded)
# Set to an iterable like {"ART"} to only load ART by default for faster startup.
# Set to None or empty set to enable all present categories by default.
DEFAULT_ENABLED_CATEGORIES = {"ART"}

def dprint(*args, **kwargs):
    if DEBUG_MODE:
        print(*args, **kwargs)

# Preview cache directory (mirrors project structure under this tools folder)
PREVIEW_CACHE_DIR = SCRIPT_DIR / "_preview_cache"
PREVIEW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
PLACEHOLDER_IMG = PREVIEW_CACHE_DIR / "_placeholder.png"
if not PLACEHOLDER_IMG.exists():
    try:
        img = Image.new('RGBA', (32, 18), (40, 40, 40, 255))
        img.save(PLACEHOLDER_IMG, format='PNG')
    except Exception:
        pass

# Determine the correct resampling method for Pillow version
try:
    RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE = Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS

# --- Color scheme ---
DARK_GRAY = '#23272b'
DARKER_GRAY = '#181a1b'
LIGHTER_GRAY = '#2e3236'
WHITE = '#f8f8f2'
ACCENT = '#5c6370'
BORDER_WARN = '#d19a66'  # orange-ish border for incomplete pairs

# Category base colors
CATEGORY_COLORS = {
    "ART": "#8a67ac",  # muted purple
    "UI":  "#5b7fa7",  # muted blue
    "ENV": "#5fa077",  # muted green
}

def _clamp(v):
    return max(0, min(255, int(v)))

def _hex_to_rgb(h: str):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb

def adjust_color(hex_color: str, factor: float) -> str:
    """Lighten (>1) or darken (<1) the color by factor."""
    r, g, b = _hex_to_rgb(hex_color)
    r = _clamp(r * factor)
    g = _clamp(g * factor)
    b = _clamp(b * factor)
    return _rgb_to_hex((r, g, b))

# Item discovery with debug logging
def find_items(project_root, show_upscale=True, include_categories=None):
    items = []
    root_path = Path(project_root)
    logging.info(f"Scanning for assets in: {root_path.resolve()}")
    group_counts = {}
    for category_folder in root_path.iterdir():
        if not category_folder.is_dir() or category_folder.name.startswith('.'):
            continue
        # If include_categories is provided, restrict scanning
        if include_categories is not None and category_folder.name not in include_categories:
            continue
        logging.info(f"Category: {category_folder.name}")
        for group_folder in category_folder.iterdir():
            if not group_folder.is_dir() or group_folder.name.startswith('.'):
                continue
            logging.info(f"  Group: {group_folder.name}")
            upscale_folder = group_folder / "Upscale"
            group_item_count = 0
            if show_upscale and upscale_folder.exists() and upscale_folder.is_dir():
                # Build item names from any matching PSD or PNG in Upscale
                try:
                    names = set()
                    for p in upscale_folder.glob("*.png"):
                        if HEX_FILTER_ENABLED and HEX_PREFIX not in p.name:
                            continue
                        names.add(p.stem)
                    for p in upscale_folder.glob("*.psd"):
                        if HEX_FILTER_ENABLED and HEX_PREFIX not in p.name:
                            continue
                        names.add(p.stem)
                    # Also include unfinished base-only items: base PSDs with hex suffix
                    for p in group_folder.glob("*.psd"):
                        try:
                            if HEX_SUFFIX_RE.search(p.stem):
                                if HEX_FILTER_ENABLED and HEX_PREFIX not in p.name:
                                    continue
                                names.add(p.stem)
                        except Exception:
                            pass
                except Exception as e:
                    logging.warning(f"    Error listing Upscale for {group_folder}: {e}")
                    names = set()
                for item_name in sorted(names):
                    try:
                        up_png = upscale_folder / f"{item_name}.png"
                        up_psd = upscale_folder / f"{item_name}.psd"
                        base_psd = group_folder / f"{item_name}.psd"
                        base_bmp = group_folder / f"{item_name}.bmp"
                        gen_folder = upscale_folder / item_name / "gen" / "01"

                        # Choose best available preview: upscale PNG > base BMP > upscale PSD > base PSD
                        if up_png.exists():
                            preview = up_png
                        elif base_bmp.exists():
                            preview = base_bmp
                        elif up_psd.exists():
                            preview = up_psd
                        else:
                            preview = base_psd

                        items.append({
                            "name": item_name,
                            "preview": str(preview),
                            "psd": str(base_psd),
                            "folder": str(group_folder),
                            "gen_folder": str(gen_folder),
                            "category": category_folder.name,
                            "group": group_folder.name,
                            "source_type": "upscale",
                            "has_up_png": up_png.exists(),
                            "has_up_psd": up_psd.exists(),
                            "has_base_bmp": base_bmp.exists(),
                            "has_base_psd": base_psd.exists(),
                        })
                        group_item_count += 1
                    except Exception as e:
                        logging.warning(f"    Error processing upscale item '{item_name}': {e}")
            elif not show_upscale:
                # Discover original assets even if Upscale folder is missing
                # Build names from any PSD or BMP in base folder
                try:
                    names = set()
                    for p in group_folder.glob("*.psd"):
                        if HEX_FILTER_ENABLED and HEX_PREFIX not in p.name:
                            continue
                        names.add(p.stem)
                    for p in group_folder.glob("*.bmp"):
                        if HEX_FILTER_ENABLED and HEX_PREFIX not in p.name:
                            continue
                        names.add(p.stem)
                except Exception as e:
                    logging.warning(f"    Error listing base for {group_folder}: {e}")
                    names = set()
                for item_name in sorted(names):
                    base_psd = group_folder / f"{item_name}.psd"
                    bmp_file = group_folder / f"{item_name}.bmp"
                    # Choose best available preview: BMP > PSD
                    preview_file = bmp_file if bmp_file.exists() else base_psd
                    gen_folder = group_folder / item_name / "gen" / "01"
                    if HEX_FILTER_ENABLED and (HEX_PREFIX not in base_psd.name and HEX_PREFIX not in bmp_file.name):
                        continue
                    items.append({
                        "name": item_name,
                        "preview": str(preview_file),
                        "psd": str(base_psd),
                        "folder": str(group_folder),
                        "gen_folder": str(gen_folder),
                        "category": category_folder.name,
                        "group": group_folder.name,
                        "source_type": "original",
                        "has_up_png": False,
                        "has_up_psd": False,
                        "has_base_bmp": bmp_file.exists(),
                        "has_base_psd": base_psd.exists(),
                    })
                    group_item_count += 1
            logging.info(f"    Found {group_item_count} items in group '{group_folder.name}'")
            group_counts[group_folder.name] = group_item_count
    logging.info(f"Total items found: {len(items)}")
    logging.info(f"Group counts: {group_counts}")
    return items

# Main GUI class
class ImageDashboard:
    def __init__(self, root, items):
        # Add callback methods for inputs
        self.ps_path_var = None
        self.max_width_var = None

        self.update_photoshop_path = lambda *args: self._update_photoshop_path()
        self.update_max_width = lambda *args: self._update_max_width()
        self.show_info = lambda: self._show_info()

        self.root = root
        self.items = items
        self.thumbs = []
        self.show_names = BooleanVar(value=True)
        self.show_upscale = BooleanVar(value=True)  # New: toggle for upscale/original
        self.sort_outdated_first = BooleanVar(value=False)  # Toggle to sort items needing merge to top

        # Background preview generation
        self.preview_task_queue: Queue = Queue()
        self._pending_preview_tasks = set()
        self._worker_alive = True
        self.preview_worker = threading.Thread(target=self._preview_worker, daemon=True)
        self.preview_worker.start()

        # Map item key to widgets to enable lightweight updates without full redraw
        # key = (category, group, name)
        self.item_widgets = {}

        # Top bar container (frozen area): holds controls and filter bar
        top_bar = Frame(root, bg=DARK_GRAY)
        top_bar.pack(side=TOP, fill=X, padx=0, pady=0)
        # Top controls frame
        controls = Frame(top_bar, bg=DARK_GRAY)
        controls.pack(side=TOP, fill=X, padx=0, pady=0)
        # Upscale/original checkbox
        Checkbutton(
            controls,
            text="Show Upscale Assets",
            variable=self.show_upscale,
            command=self.toggle_upscale,
            bg=DARK_GRAY, fg=WHITE, selectcolor=ACCENT,
            activebackground=DARK_GRAY, activeforeground=WHITE
        ).pack(side=LEFT, padx=(8,2), pady=4)
        # Photoshop path input
        Label(controls, text="Photoshop Path:", bg=DARK_GRAY, fg=WHITE).pack(side=LEFT, padx=(8,2))
        self.ps_path_var = StringVar(value=PHOTOSHOP_EXE)
        ps_entry = Entry(controls, textvariable=self.ps_path_var, width=40, bg=LIGHTER_GRAY, fg=WHITE, insertbackground=WHITE)
        ps_entry.pack(side=LEFT, padx=(0,8), pady=4)
        self.ps_path_var.trace_add('write', self.update_photoshop_path)
        # Max asset width input
        Label(controls, text="Max Asset Width:", bg=DARK_GRAY, fg=WHITE).pack(side=LEFT, padx=(0,2))
        self.max_width_var = StringVar(value=str(MAX_ASSET_WIDTH))
        width_entry = Entry(controls, textvariable=self.max_width_var, width=5, bg=LIGHTER_GRAY, fg=WHITE, insertbackground=WHITE)
        width_entry.pack(side=LEFT, padx=(0,8), pady=4)
        self.max_width_var.trace_add('write', self.update_max_width)
        # Info/help button
        Button(controls, text="Info", command=self.show_info, bg=ACCENT, fg=WHITE, relief=FLAT, font=("Segoe UI", 9, "bold"), activebackground=WHITE, activeforeground=ACCENT).pack(side=LEFT, padx=(0,8), pady=4)
        # Create missing upscales button
        Button(controls, text="Create Missing Upscales", command=self.create_missing_upscales, bg=ACCENT, fg=WHITE, relief=FLAT, font=("Segoe UI", 9, "bold"), activebackground=WHITE, activeforeground=ACCENT).pack(side=LEFT, padx=(0,8), pady=4)
        # Show names checkbox
        Checkbutton(
            controls,
            text="Show Names",
            variable=self.show_names,
            command=self.redraw_items,
            bg=DARK_GRAY, fg=WHITE, selectcolor=ACCENT,
            activebackground=DARK_GRAY, activeforeground=WHITE
        ).pack(side=LEFT, padx=8, pady=4)
        # Sort outdated upscales first (those with newer gen01 files)
        Checkbutton(
            controls,
            text="Sort outdated first",
            variable=self.sort_outdated_first,
            command=self.redraw_items,
            bg=DARK_GRAY, fg=WHITE, selectcolor=ACCENT,
            activebackground=DARK_GRAY, activeforeground=WHITE
        ).pack(side=LEFT, padx=8, pady=4)

        # --- Filter bar (frozen at top): parent row + group row ---
        # Excluded sets; buttons toggle membership
        # Initialize excluded_categories based on DEFAULT_ENABLED_CATEGORIES
        try:
            root_path = Path(PROJECT_ROOT)
            present_cats = {c for c in ["ART", "UI", "ENV"] if (root_path / c).is_dir()}
        except Exception:
            present_cats = set()
        if DEFAULT_ENABLED_CATEGORIES:
            enabled = present_cats.intersection(DEFAULT_ENABLED_CATEGORIES)
            # Exclude everything not explicitly enabled
            self.excluded_categories = present_cats - enabled
        else:
            # Enable all by default
            self.excluded_categories = set()
        self.excluded_groups = set()  # keys as f"{category}|{group}"
        # Parent categories row
        self.parent_filter_frame = Frame(top_bar, bg=DARK_GRAY)
        self.parent_filter_frame.pack(side=TOP, fill=X, padx=0, pady=0)
        # Group (subfolder) row
        self.group_filter_frame = Frame(top_bar, bg=DARK_GRAY)
        self.group_filter_frame.pack(side=TOP, fill=X, padx=0, pady=0)
        self.group_filter_frame.bind("<Configure>", lambda e: self.reflow_group_buttons())
        self.category_buttons = {}
        self.group_buttons = {}
        self.group_button_order = []  # preserve order for wrapping
        self.build_category_filters()

        # Scrollable content container
        content = Frame(root, bg=DARKER_GRAY)
        content.pack(side=TOP, fill=BOTH, expand=True)
        self.canvas = Canvas(content, bg=DARKER_GRAY, highlightthickness=0, bd=0)
        self.frame = Frame(self.canvas, bg=DARKER_GRAY)
        self.scroll_y = Scrollbar(content, orient=VERTICAL, command=self.canvas.yview, bg=DARK_GRAY, troughcolor=LIGHTER_GRAY)
        self.canvas.configure(yscrollcommand=self.scroll_y.set)

        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)
        self.scroll_y.pack(side=RIGHT, fill=Y)

        self.canvas.create_window((0, 0), window=self.frame, anchor="nw")
        self.frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

        # Initial population after filters are ready
        self.refresh_items()

    def toggle_upscale(self):
        self.refresh_items()

    def refresh_items(self):
        # Determine enabled categories (present and not excluded)
        try:
            root_path = Path(PROJECT_ROOT)
            present = [c for c in ["ART", "UI", "ENV"] if (root_path / c).is_dir()]
        except Exception:
            present = []
        enabled_cats = {c for c in present if c not in self.excluded_categories}
        # Re-discover items based on toggle and enabled categories
        found_items = find_items(PROJECT_ROOT, show_upscale=self.show_upscale.get(), include_categories=enabled_cats if enabled_cats else None)
        # Apply category and group filtering
        filtered = []
        for it in found_items:
            cat = it.get('category')
            grp = it.get('group')
            if cat in self.excluded_categories:
                continue
            if f"{cat}|{grp}" in getattr(self, 'excluded_groups', set()):
                continue
            filtered.append(it)
        self.items = filtered
        self.redraw_items()

    def build_category_filters(self):
        # Clear existing parent row
        for w in self.parent_filter_frame.winfo_children():
            w.destroy()
        # Only include ART, UI, ENV if they exist
        try:
            root_path = Path(PROJECT_ROOT)
            all_categories = {p.name for p in root_path.iterdir() if p.is_dir() and not p.name.startswith('.')}
        except Exception:
            all_categories = set()
        ordered = [c for c in ["ART", "UI", "ENV"] if c in all_categories]
        # Create parent buttons (no vertical padding)
        self.category_buttons = {}
        for cat in ordered:
            btn = Button(
                self.parent_filter_frame,
                text=cat,
                command=lambda c=cat: self.toggle_category(c),
                bg=CATEGORY_COLORS.get(cat, ACCENT),
                fg=WHITE,
                relief=FLAT,
                font=("Segoe UI", 9, "bold"),
                activebackground=WHITE,
                activeforeground=ACCENT,
                padx=6,
                pady=0,
            )
            btn.pack(side=LEFT, padx=4, pady=0)
            self.category_buttons[cat] = btn
            self.update_category_button_style(cat)
        # After building parent buttons, build the group buttons row
        self.build_group_filters()

    def build_group_filters(self):
        # Clear existing group row
        for w in self.group_filter_frame.winfo_children():
            w.destroy()
        self.group_buttons = {}
        self.group_button_order = []
        # Determine enabled categories (present and not excluded)
        try:
            root_path = Path(PROJECT_ROOT)
            enabled_cats = [c for c in ["ART", "UI", "ENV"] if (root_path / c).is_dir() and c not in self.excluded_categories]
        except Exception:
            enabled_cats = []
        # For each enabled category, list its immediate subfolders (groups)
        for cat in enabled_cats:
            cat_path = Path(PROJECT_ROOT) / cat
            groups = [p.name for p in cat_path.iterdir() if p.is_dir() and not p.name.startswith('.')]
            # Optional: small spacer between category blocks
            # Create buttons for groups
            for grp in sorted(groups):
                key = f"{cat}|{grp}"
                btn = Button(
                    self.group_filter_frame,
                    text=grp,
                    command=lambda k=key: self.toggle_group(k),
                    bg=self.get_group_color(cat, grp, excluded=(key in self.excluded_groups)),
                    fg=WHITE,
                    relief=FLAT,
                    font=("Segoe UI", 8),
                    activebackground=WHITE,
                    activeforeground=ACCENT,
                    padx=6,
                    pady=0,
                )
                # We'll position with place() during reflow
                self.group_buttons[key] = btn
                self.update_group_button_style(key)
                self.group_button_order.append((key, btn, cat, grp))
        # Perform initial flow layout
        self.reflow_group_buttons()

    def get_group_color(self, cat: str, grp: str, excluded: bool = False) -> str:
        if excluded:
            return LIGHTER_GRAY
        base = CATEGORY_COLORS.get(cat, ACCENT)
        # Derive a small deterministic variation from group name
        h = sum(ord(c) for c in grp) % 7  # 0..6
        factor = 0.9 + (h * 0.02)  # 0.90 .. 1.02
        return adjust_color(base, factor)

    def reflow_group_buttons(self):
        try:
            # Clear placements
            for _, btn, _, _ in self.group_button_order:
                btn.place_forget()
            # Ensure buttons are realized to get req sizes
            self.group_filter_frame.update_idletasks()
            avail = self.group_filter_frame.winfo_width()
            if avail <= 1:
                self.root.after(10, self.reflow_group_buttons)
                return
            x = 4
            y = 2
            row_max_h = 0
            pad_x = 4
            pad_y = 2
            for key, btn, cat, grp in self.group_button_order:
                w = btn.winfo_reqwidth()
                h = btn.winfo_reqheight()
                if x + w + pad_x > avail:
                    x = 4
                    y += row_max_h + pad_y
                    row_max_h = 0
                btn.place(x=x, y=y)
                x += w + pad_x
                row_max_h = max(row_max_h, h)
            # Adjust frame height to fit rows (optional)
            self.group_filter_frame.configure(height=y + row_max_h + pad_y)
        except Exception:
            pass

    def toggle_category(self, category_name: str):
        if category_name in self.excluded_categories:
            self.excluded_categories.remove(category_name)
        else:
            self.excluded_categories.add(category_name)
        self.update_category_button_style(category_name)
        # Rebuild group filters to reflect enabled categories
        self.build_group_filters()
        self.refresh_items()

    def update_category_button_style(self, category_name: str):
        btn = self.category_buttons.get(category_name)
        if not btn:
            return
        if category_name in self.excluded_categories:
            # Darkened style when excluded (filtered out)
            btn.configure(bg=LIGHTER_GRAY, fg=WHITE, activebackground=LIGHTER_GRAY, activeforeground=WHITE)
        else:
            # Accent style when included (visible)
            base = CATEGORY_COLORS.get(category_name, ACCENT)
            btn.configure(bg=base, fg=WHITE, activebackground=WHITE, activeforeground=ACCENT)

    def toggle_group(self, key: str):
        # key format: "CAT|GROUP"
        if key in self.excluded_groups:
            self.excluded_groups.remove(key)
        else:
            self.excluded_groups.add(key)
        self.update_group_button_style(key)
        self.refresh_items()

    def update_group_button_style(self, key: str):
        btn = self.group_buttons.get(key)
        if not btn:
            return
        cat, grp = key.split('|', 1)
        if key in self.excluded_groups:
            btn.configure(bg=LIGHTER_GRAY, fg=WHITE, activebackground=LIGHTER_GRAY, activeforeground=WHITE)
        else:
            btn.configure(bg=self.get_group_color(cat, grp), fg=WHITE, activebackground=WHITE, activeforeground=ACCENT)
        # After style change, reflow in case sizes changed slightly
        self.reflow_group_buttons()

    def _update_photoshop_path(self):
        global PHOTOSHOP_EXE
        PHOTOSHOP_EXE = self.ps_path_var.get() if self.ps_path_var else PHOTOSHOP_EXE

    def _update_max_width(self):
        global MAX_ASSET_WIDTH, THUMB_SIZE
        try:
            MAX_ASSET_WIDTH = int(self.max_width_var.get())
            THUMB_SIZE = (MAX_ASSET_WIDTH, int(MAX_ASSET_WIDTH * 108 / 192))
            self.redraw_items()
        except Exception:
            pass

    def _show_info(self):
        import tkinter.messagebox as mb
        info_text = (
            "Project Structure and Asset Tutorial:\n\n"
            "CATEGORY > GROUP > ITEM (psd,bmp) | GROUP/Upscale > ITEM (psd,png) > ITEM/gen/01/*\n"
            "Example:\n"
            "ART/ART_Food/item_food_apple.psd\n"
            "ART/ART_Food/Upscale/item_food_apple.psd\n"
            "ART/ART_Food/Upscale/item_food_apple/gen/01/apple_gen_a.png\n\n"
            "To add a new asset:\n"
            "1. Create a CATEGORY folder (e.g., ART) if not present.\n"
            "2. Inside, create a GROUP folder (e.g., ART_Food).\n"
            "3. Place your ITEM .psd and .bmp files in the GROUP folder.\n"
            "4. Create an Upscale subfolder in the GROUP folder.\n"
            "5. Place your upscaled ITEM .psd and .png in Upscale.\n"
            "6. For generated images, create Upscale/ITEM/gen/01/ and place .png files there.\n\n"
            "Discovery rules:\n"
            "- Upscale view considers any ITEM with .png or .psd in Upscale.\n"
            "- Original view considers any ITEM with .bmp or .psd in base.\n"
            "- Preview priority: Upscale PNG > Base BMP > Upscale PSD > Base PSD.\n"
            "- Upscale PSD filename matches base ITEM name (no '_upscale' suffix).\n"
            "Optionally, use hex IDs in filenames for filtering (e.g., item_apple_0x0294.png).\n"
        )
        mb.showinfo("Project Info", info_text)

    def redraw_items(self):
        # Remove all widgets in frame
        for widget in self.frame.winfo_children():
            widget.destroy()
        # Reset thumbnails to allow GC of old images
        self.thumbs = []
        self.item_widgets = {}
        # Start batched rendering
        self.draw_items()

    def draw_items(self):
        # Prepare render state
        try:
            self._thumb_width = int(self.max_width_var.get()) if hasattr(self, 'max_width_var') else THUMB_SIZE[0]
        except Exception:
            self._thumb_width = THUMB_SIZE[0]
        self._thumb_height = int(self._thumb_width * 108 / 192)
        self._BUTTON_WIDTH = 48
        self._COLUMNS_PER_ROW = 8
        # Sorting
        if self.sort_outdated_first.get():
            def needs_merge_key(it):
                return (not self.item_needs_merge(it), it['group'], it['name'])
            self._render_sorted_items = sorted(self.items, key=needs_merge_key)
        else:
            self._render_sorted_items = sorted(self.items, key=lambda x: (x['group'], x['name']))
        # Layout state
        self._render_idx = 0
        self._render_last_group = None
        self._render_group_row = -1
        self._render_group_col = 0
        # Version token so old batches stop when a new render starts
        self._render_version = getattr(self, '_render_version', 0) + 1
        setattr(self, '_render_version', self._render_version)
        dprint(f"Drawing {len(self._render_sorted_items)} items in batches...")
        self._render_batch(self._render_version)

    def _render_batch(self, version_token: int, batch_size: int = 32):
        if version_token != getattr(self, '_render_version', None):
            return
        n = len(self._render_sorted_items)
        end_idx = min(self._render_idx + batch_size, n)
        for idx in range(self._render_idx, end_idx):
            item = self._render_sorted_items[idx]
            group = item['group']
            if group != self._render_last_group:
                self._render_group_row += 1
                self._render_group_col = 0
                dprint(f"Starting new group '{group}' at row {self._render_group_row}")
                self._render_last_group = group
            try:
                dprint(f"[{idx}] Adding item '{item['name']}' from group '{group}' at (col={self._render_group_col}, row={self._render_group_row})")
                preview_path = self.get_cached_preview_path(item)
                with Image.open(preview_path) as img:
                    img.thumbnail((self._thumb_width, self._thumb_height), RESAMPLE)
                    thumb = ImageTk.PhotoImage(img.copy())
                self.thumbs.append(thumb)

                card = Frame(self.frame, bg=DARKER_GRAY, relief=FLAT, bd=0, padx=0, pady=0, highlightthickness=0, width=self._thumb_width+self._BUTTON_WIDTH, height=self._thumb_height)
                card.grid_propagate(0)

                has_up_png = item.get("has_up_png", False)
                has_up_psd = item.get("has_up_psd", False)
                has_base_bmp = item.get("has_base_bmp", False)
                has_base_psd = item.get("has_base_psd", False)
                pair_ok = (has_up_png and has_up_psd) if self.show_upscale.get() else (has_base_bmp and has_base_psd)

                if not pair_ok:
                    img_wrap = Frame(card, bg=BORDER_WARN, highlightthickness=0, bd=0)
                    img_wrap.place(x=0, y=0, width=self._thumb_width, height=self._thumb_height)
                    img_label = Label(img_wrap, image=thumb, bg=DARKER_GRAY, cursor="hand2", highlightthickness=0, bd=0)
                    img_label.place(x=1, y=1, width=self._thumb_width-2, height=self._thumb_height-2)
                else:
                    img_label = Label(card, image=thumb, bg=DARKER_GRAY, cursor="hand2", highlightthickness=0, bd=0)
                    img_label.place(x=0, y=0, width=self._thumb_width, height=self._thumb_height)
                img_label.bind("<Button-1>", lambda e, p=item["psd"]: self.open_photoshop(p))

                btn_frame = Frame(card, bg=DARKER_GRAY, width=self._BUTTON_WIDTH, height=self._thumb_height)
                btn_frame.place(x=self._thumb_width, y=0, width=self._BUTTON_WIDTH, height=self._thumb_height)
                small_btn_opts = dict(font=("Segoe UI", 7), width=6, padx=0, pady=0, bg=ACCENT, fg=WHITE, relief=FLAT, bd=0, highlightthickness=0, activebackground=WHITE, activeforeground=ACCENT, anchor="w")
                Button(btn_frame, text="folder", command=lambda p=item["folder"]: self.open_explorer(p), **small_btn_opts, height=1).pack(side=TOP, fill=X, pady=(6,2))
                gen_btn_opts = dict(**small_btn_opts)
                if not self.folder_has_files(item["gen_folder"]):
                    gen_btn_opts.update(bg=LIGHTER_GRAY, fg=WHITE, activebackground=LIGHTER_GRAY, activeforeground=WHITE)
                Button(btn_frame, text="gen01", command=lambda p=item["gen_folder"]: self.open_explorer(p), **gen_btn_opts, height=1).pack(side=TOP, fill=X, pady=(2,2))
                upscale_psd_path = None
                if item.get("source_type") == "upscale":
                    upscale_psd_path = (Path(item["folder"]) / "Upscale" / f"{item['name']}.psd")
                else:
                    group_folder = Path(item["folder"])
                    candidate = group_folder / "Upscale" / f"{item['name']}.psd"
                    if candidate.exists():
                        upscale_psd_path = candidate
                if upscale_psd_path and Path(upscale_psd_path).exists():
                    upscale_btn = Button(btn_frame, text="upscale", command=lambda p=str(upscale_psd_path): self.open_photoshop(p), **small_btn_opts, height=1)
                    upscale_btn.pack(side=TOP, fill=X, pady=(2,2))
                else:
                    # Missing upscale: provide orange 'upscale' that creates then opens (no overwrite)
                    warn_btn_opts = dict(**small_btn_opts)
                    warn_btn_opts.update(bg=BORDER_WARN, activebackground=BORDER_WARN, activeforeground=WHITE)
                    upscale_btn = Button(
                        btn_frame,
                        text="upscale",
                        command=lambda base=item["psd"], name=item["name"], folder=item["folder"]: self.create_upscale_and_open(base, name, folder),
                        **warn_btn_opts,
                        height=1
                    )
                    upscale_btn.pack(side=TOP, fill=X, pady=(2,2))
                    Frame(btn_frame, height=4, bg=DARKER_GRAY).pack(side=TOP, fill=X, pady=(0,2))
                if self.show_names.get():
                    Label(btn_frame, text=item["name"], bg=DARKER_GRAY, fg=WHITE, font=("Segoe UI", 8), anchor="w", wraplength=self._BUTTON_WIDTH-2, justify=LEFT).pack(side=TOP, fill=X, pady=(0,2))

                card.grid(row=self._render_group_row, column=self._render_group_col, padx=0, pady=0, sticky="nsew")
                dprint(f"Placed card at row={self._render_group_row}, col={self._render_group_col}, width={self._thumb_width+self._BUTTON_WIDTH}, height={self._thumb_height}")
                self._render_group_col += 1
                if self._render_group_col >= self._COLUMNS_PER_ROW:
                    self._render_group_col = 0
                    self._render_group_row += 1
                # Store widget reference for lightweight updates
                try:
                    key = (item.get("category"), item.get("group"), item.get("name"))
                    self.item_widgets[key] = {
                        "upscale_btn": upscale_btn,
                        "btn_frame": btn_frame,
                    }
                except Exception:
                    pass
            except Exception as e:
                dprint(f"Error loading preview for '{item['name']}': {e}")
        self._render_idx = end_idx
        if self._render_idx < n and version_token == getattr(self, '_render_version', None):
            self.root.after(1, self._render_batch, version_token, batch_size)
        else:
            dprint("Finished drawing items.")

    def _preview_worker(self):
        while self._worker_alive:
            try:
                source_path = self.preview_task_queue.get(timeout=0.5)
            except Empty:
                continue
            try:
                self._ensure_preview_cached(source_path)
            except Exception as e:
                dprint(f"[PreviewWorker][ERROR] {e}")
            finally:
                # remove from pending; do not auto-refresh to keep UI static during session
                try:
                    self._pending_preview_tasks.discard(str(source_path))
                except Exception:
                    pass
                self.preview_task_queue.task_done()

    def _rel_to_project(self, path: Path) -> Path:
        try:
            return Path(path).resolve().relative_to(Path(PROJECT_ROOT).resolve())
        except Exception:
            return Path(path).name

    def _cache_path_for_source(self, source_path: Path) -> Path:
        rel = self._rel_to_project(source_path)
        # store as .png regardless of source extension
        rel_png = rel.with_suffix('.png')
        return PREVIEW_CACHE_DIR / rel_png

    def _ensure_preview_cached(self, source_path: Path) -> Path:
        """
        Ensure a small preview PNG exists in the cache for the given source image (PNG/BMP/PSD).
        Regenerate only if the source is newer than the cached file or cache is missing.
        Returns the path to the cached preview (or source if generation fails).
        """
        try:
            cache_path = self._cache_path_for_source(source_path)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            if cache_path.exists():
                try:
                    if source_path.stat().st_mtime <= cache_path.stat().st_mtime:
                        return cache_path
                except Exception:
                    pass
            # Generate preview
            with Image.open(source_path) as im:
                # Convert to RGBA for consistent save
                try:
                    im = im.convert('RGBA')
                except Exception:
                    pass
                # Limit size to reduce disk and memory; use a moderate width (e.g., 512)
                target_w = max(THUMB_SIZE[0], 512)
                im.thumbnail((target_w, int(target_w * 108 / 192)), RESAMPLE)
                im.save(cache_path, format='PNG')
            return cache_path
        except Exception as e:
            dprint(f"[PreviewCache][ERROR] Could not cache preview for {source_path}: {e}")
            return source_path

    def get_cached_preview_path(self, item) -> str:
        """
        Determine the appropriate source for preview (prefer Upscale PNG, else base BMP, else base PSD),
        then ensure a cached PNG exists and return its path.
        """
        try:
            group_folder = Path(item.get("folder", ""))
            upscale_folder = group_folder / "Upscale"
            item_name = item.get("name")
            up_png = upscale_folder / f"{item_name}.png"
            base_bmp = group_folder / f"{item_name}.bmp"
            base_psd = Path(item.get("psd", ""))

            if up_png.exists():
                return str(self._ensure_preview_cached(up_png))
            if base_bmp.exists():
                return str(self._ensure_preview_cached(base_bmp))
            if base_psd.exists():
                # If cache already exists and is current, return it immediately
                cache_path = self._cache_path_for_source(base_psd)
                try:
                    if cache_path.exists() and base_psd.stat().st_mtime <= cache_path.stat().st_mtime:
                        return str(cache_path)
                except Exception:
                    pass
                # Static mode: do not generate during session; show placeholder
                if STATIC_PREVIEWS:
                    return str(PLACEHOLDER_IMG if PLACEHOLDER_IMG.exists() else base_psd)
                # Otherwise enqueue background generation and return placeholder for now
                key = str(base_psd)
                if key not in self._pending_preview_tasks:
                    self._pending_preview_tasks.add(key)
                    try:
                        self.preview_task_queue.put_nowait(base_psd)
                    except Exception:
                        self._pending_preview_tasks.discard(key)
                return str(PLACEHOLDER_IMG if PLACEHOLDER_IMG.exists() else base_psd)
            # Fallback to whatever preview path was discovered
            return item.get("preview")
        except Exception as e:
            dprint(f"[PreviewCache][ERROR] {e}")
            return item.get("preview")

    def get_upscale_psd_path_for_item(self, item) -> Path | None:
        """Return the Path to Upscale/<item>.psd for this item, if resolvable."""
        try:
            group_folder = Path(item["folder"]) if item.get("folder") else None
            if not group_folder:
                return None
            return (group_folder / "Upscale" / f"{item['name']}.psd")
        except Exception:
            return None

    def get_gen01_latest_mtime_for_item(self, item) -> float | None:
        """Return the latest modification time (timestamp) among files in Upscale/<item>/gen/01, or None."""
        try:
            group_folder = Path(item["folder"]) if item.get("folder") else None
            if not group_folder:
                return None
            upscale_folder = group_folder / "Upscale"
            gen01 = upscale_folder / item["name"] / "gen" / "01"
            if not gen01.exists() or not gen01.is_dir():
                return None
            latest = None
            for child in gen01.iterdir():
                if child.is_file():
                    mt = child.stat().st_mtime
                    latest = mt if latest is None else max(latest, mt)
            return latest
        except Exception:
            return None

    def item_needs_merge(self, item) -> bool:
        """
        True if there exists at least one file in Upscale/<item>/gen/01 newer than the Upscale PSD.
        """
        try:
            psd_path = self.get_upscale_psd_path_for_item(item)
            if not psd_path or not psd_path.exists():
                return False
            psd_mtime = psd_path.stat().st_mtime
            latest_gen = self.get_gen01_latest_mtime_for_item(item)
            if latest_gen is None:
                return False
            return latest_gen > psd_mtime
        except Exception:
            return False

    def create_upscale_psd(self, base_psd_path: str, item_name: str, group_folder_path: str):
        """
        Create an Upscale PSD by copying the base PSD into the group's Upscale folder
        as '<item_name>.psd' if it does not already exist. Also ensures the
        standard subfolder structure exists for generated outputs.
        """
        try:
            base_psd = Path(base_psd_path)
            group_folder = Path(group_folder_path)
            upscale_folder = group_folder / "Upscale"
            upscale_folder.mkdir(parents=True, exist_ok=True)

            target_psd = upscale_folder / f"{item_name}.psd"
            if target_psd.exists():
                dprint(f"[CreateUpscale][SKIP] Already exists: {target_psd}")
            else:
                shutil.copy2(base_psd, target_psd)
                dprint(f"[CreateUpscale] Copied base PSD to: {target_psd}")

            # Ensure standard gen folder exists for future outputs: Upscale/<item_name>/gen/01
            gen_01 = upscale_folder / item_name / "gen" / "01"
            gen_01.mkdir(parents=True, exist_ok=True)

            # Refresh UI so buttons update state
            self.refresh_items()
        except Exception as e:
            dprint(f"[CreateUpscale][ERROR] {e}")

    def create_missing_upscales(self):
        """
        Batch operation: for every discovered original item (non-upscale view),
        ensure Upscale/<item_name>.psd exists by copying from the base PSD
        if missing. Also ensure Upscale/<item_name>/gen/01 exists.
        Shows a summary on completion and refreshes the dashboard.
        """
        try:
            import tkinter.messagebox as mb
            originals = find_items(PROJECT_ROOT, show_upscale=False)
            created = 0
            skipped = 0
            errors = 0
            for it in originals:
                try:
                    base_psd = Path(it["psd"]) if it.get("psd") else None
                    item_name = it.get("name")
                    group_folder = Path(it.get("folder", ""))
                    if not base_psd or not base_psd.exists() or not item_name or not group_folder.exists():
                        errors += 1
                        continue
                    upscale_folder = group_folder / "Upscale"
                    upscale_folder.mkdir(parents=True, exist_ok=True)
                    target_psd = upscale_folder / f"{item_name}.psd"
                    if target_psd.exists():
                        skipped += 1
                    else:
                        shutil.copy2(base_psd, target_psd)
                        created += 1
                    # Ensure standard gen/01 path
                    (upscale_folder / item_name / "gen" / "01").mkdir(parents=True, exist_ok=True)
                except Exception as ie:
                    dprint(f"[BatchCreateUpscales][ERROR] {ie}")
                    errors += 1
            # Refresh UI so list updates based on newly created upscales
            self.refresh_items()
            mb.showinfo("Create Missing Upscales", f"Created: {created}\nAlready existed: {skipped}\nErrors: {errors}")
        except Exception as e:
            dprint(f"[BatchCreateUpscales][FATAL] {e}")

    def create_upscale_and_open(self, base_psd_path: str, item_name: str, group_folder_path: str, delay_ms: int = 300):
        """
        Create Upscale/<item>.psd from base if it doesn't exist, then open it in Photoshop after a short delay.
        Never overwrite an existing upscale PSD.
        """
        try:
            base_psd = Path(base_psd_path)
            group_folder = Path(group_folder_path)
            upscale_folder = group_folder / "Upscale"
            upscale_folder.mkdir(parents=True, exist_ok=True)
            target_psd = upscale_folder / f"{item_name}.psd"
            if not target_psd.exists():
                shutil.copy2(base_psd, target_psd)
                dprint(f"[CreateUpscaleAndOpen] Created: {target_psd}")
                # ensure gen folder structure
                (upscale_folder / item_name / "gen" / "01").mkdir(parents=True, exist_ok=True)
            else:
                dprint(f"[CreateUpscaleAndOpen][SKIP] Already exists: {target_psd}")
            # Update only this item's upscale button on the UI thread (no full redraw)
            def _promote_button():
                try:
                    key = (Path(group_folder_path).parent.name if False else None)  # placeholder
                except Exception:
                    key = None
                # Build the key exactly as stored during render
                try:
                    # We don't have category/group/name here directly, reconstruct using paths
                    group_folder = Path(group_folder_path)
                    category = group_folder.parent.name
                    group = group_folder.name
                    name = item_name
                    widget_key = (category, group, name)
                    ref = self.item_widgets.get(widget_key)
                    if ref and ref.get("upscale_btn"):
                        btn = ref["upscale_btn"]
                        # Normal style
                        btn.configure(bg=ACCENT, activebackground=WHITE, activeforeground=ACCENT, command=lambda p=str(target_psd): self.open_photoshop(p))
                except Exception as ie:
                    dprint(f"[PromoteButton][WARN] {ie}")
            self.root.after(0, _promote_button)
            # Open after a small delay to allow file system to settle
            self.root.after(delay_ms, lambda p=str(target_psd): self.open_photoshop(p))
        except Exception as e:
            dprint(f"[CreateUpscaleAndOpen][ERROR] {e}")

    def open_photoshop(self, path):
        ps_path = self.ps_path_var.get() if hasattr(self, 'ps_path_var') else PHOTOSHOP_EXE
        if os.path.exists(ps_path) and os.path.exists(path):
            subprocess.Popen([ps_path, path])
        else:
            dprint("Photoshop or file not found.")

    def open_explorer(self, path):
        if os.path.isdir(path):
            subprocess.Popen(f'explorer "{path}"')

    def folder_has_files(self, path: str) -> bool:
        """
        Returns True if the given folder exists and contains at least one file.
        Returns False if the folder does not exist, is not a directory, or is empty.
        """
        try:
            p = Path(path)
            if not p.exists() or not p.is_dir():
                return False
            for child in p.iterdir():
                if child.is_file():
                    return True
            return False
        except Exception:
            return False

    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_mousewheel(self, event):
        if event.delta:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        elif event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")

# Main entry point
if __name__ == "__main__":
    root = Tk()
    root.title("Project Asset Dashboard")
    root.geometry("1600x900")

    found_items = find_items(PROJECT_ROOT)
    if not found_items:
        print("No items found. Check folder structure or disable hex filter.")
    else:
        app = ImageDashboard(root, found_items)
        root.mainloop()
