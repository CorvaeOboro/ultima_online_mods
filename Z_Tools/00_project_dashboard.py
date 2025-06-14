"""
PROJECT DASHBOARD - an Ultima Online item image review and edit launcher 
for each ITEM
the upscaled png files for the ITEMS can be used as the clickable image to open the source psd with windows photshop  

PROJECT STRUCTURE
CATEGORY folder > GROUP folder > ITEM psd and bmp > Upscale folder > ITEM_upscale psd and .png > ITEM folder > gen folder > 01 folder
ART/ART_Food/item_food_apple.psd
ART/ART_Food/Upscale/item_food_apple.psd
ART/ART_Food/Upscale/item_food_apple/gen/01/apple_gen_a.png

ITEMs can be determined by finding any png psd pair 
optionally the display of only items that contain a suffix using hex id as a  filter , example item_apple_0x0294.png the 0x indicates hexidecimal id .

for each ITEM it will be displayed with 
a button to open psd with photoshop ,
a button to open file explorer to the location 
a button to open file explorer to the location to its gen 01 folder 
a button to open the upscale psd with photoshop ,

TODO:
hover over item to display the full path  in upper right of up , 
add toggle buttons to filter Category , use muted color green blue and purple 
then under that by group , dynamically showing buttons that can be used to toggle off the display of those groups 
"""

import os
import subprocess
from pathlib import Path
from tkinter import *
from tkinter import ttk
from PIL import Image, ImageTk
import logging

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

# Item discovery with debug logging
def find_items(project_root, show_upscale=True):
    items = []
    root_path = Path(project_root)
    logging.info(f"Scanning for assets in: {root_path.resolve()}")
    group_counts = {}
    for category_folder in root_path.iterdir():
        if not category_folder.is_dir() or category_folder.name.startswith('.'):
            continue
        logging.info(f"Category: {category_folder.name}")
        for group_folder in category_folder.iterdir():
            if not group_folder.is_dir() or group_folder.name.startswith('.'):
                continue
            logging.info(f"  Group: {group_folder.name}")
            upscale_folder = group_folder / "Upscale"
            group_item_count = 0
            if show_upscale and upscale_folder.exists() and upscale_folder.is_dir():
                for upscale_png in upscale_folder.glob("*.png"):
                    if HEX_FILTER_ENABLED and HEX_PREFIX not in upscale_png.name:
                        continue
                    try:
                        item_name = upscale_png.stem.replace("_upscale", "")
                        upscale_psd = upscale_png.with_suffix('.psd')
                        base_psd = group_folder / f"{item_name}.psd"
                        gen_folder = upscale_folder / item_name / "gen" / "01"
                        if base_psd.exists() and upscale_psd.exists():
                            items.append({
                                "name": item_name,
                                "preview": str(upscale_png),
                                "psd": str(base_psd),
                                "folder": str(base_psd.parent),
                                "gen_folder": str(gen_folder),
                                "category": category_folder.name,
                                "group": group_folder.name,
                                "source_type": "upscale"
                            })
                            group_item_count += 1
                    except Exception as e:
                        logging.warning(f"    Error processing {upscale_png}: {e}")
            elif not show_upscale:
                # Discover original assets even if Upscale folder is missing
                for base_psd in group_folder.glob("*.psd"):
                    item_name = base_psd.stem
                    bmp_file = group_folder / f"{item_name}.bmp"
                    preview_file = bmp_file if bmp_file.exists() else base_psd
                    gen_folder = group_folder / item_name / "gen" / "01"
                    if HEX_FILTER_ENABLED and HEX_PREFIX not in base_psd.name:
                        continue
                    items.append({
                        "name": item_name,
                        "preview": str(preview_file),
                        "psd": str(base_psd),
                        "folder": str(base_psd.parent),
                        "gen_folder": str(gen_folder),
                        "category": category_folder.name,
                        "group": group_folder.name,
                        "source_type": "original"
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

        # Top controls frame
        controls = Frame(root, bg=DARK_GRAY)
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
        # Show names checkbox
        Checkbutton(
            controls,
            text="Show Names",
            variable=self.show_names,
            command=self.redraw_items,
            bg=DARK_GRAY, fg=WHITE, selectcolor=ACCENT,
            activebackground=DARK_GRAY, activeforeground=WHITE
        ).pack(side=LEFT, padx=8, pady=4)

        self.canvas = Canvas(root, bg=DARKER_GRAY, highlightthickness=0, bd=0)
        self.frame = Frame(self.canvas, bg=DARKER_GRAY)
        self.scroll_y = Scrollbar(root, orient=VERTICAL, command=self.canvas.yview, bg=DARK_GRAY, troughcolor=LIGHTER_GRAY)
        self.canvas.configure(yscrollcommand=self.scroll_y.set)

        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)
        self.scroll_y.pack(side=RIGHT, fill=Y)

        self.canvas.create_window((0, 0), window=self.frame, anchor="nw")
        self.frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

        self.refresh_items()

    def toggle_upscale(self):
        self.refresh_items()

    def refresh_items(self):
        # Re-discover items based on toggle
        found_items = find_items(PROJECT_ROOT, show_upscale=self.show_upscale.get())
        self.items = found_items
        self.redraw_items()

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
            "CATEGORY folder > GROUP folder > ITEM psd and bmp > Upscale folder > ITEM_upscale psd and .png > ITEM folder > gen folder > 01 folder\n"
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
            "The tool will discover items by finding .png/.psd pairs in Upscale.\n"
            "Optionally, use hex IDs in filenames for filtering (e.g., item_apple_0x0294.png).\n"
        )
        mb.showinfo("Project Info", info_text)

    def redraw_items(self):
        # Remove all widgets in frame
        for widget in self.frame.winfo_children():
            widget.destroy()
        self.draw_items()

    def draw_items(self):
        try:
            thumb_width = int(self.max_width_var.get()) if hasattr(self, 'max_width_var') else THUMB_SIZE[0]
        except Exception:
            thumb_width = THUMB_SIZE[0]
        thumb_height = int(thumb_width * 108 / 192)  # keep aspect ratio
        BUTTON_WIDTH = 48
        BUTTON_HEIGHT = 22
        COLUMNS_PER_ROW = 8  # You can adjust this or make it dynamic
        last_group = None
        group_row = -1
        group_col = 0
        sorted_items = sorted(self.items, key=lambda x: (x['group'], x['name']))
        print(f"Drawing {len(sorted_items)} items on the dashboard (wrapping by {COLUMNS_PER_ROW} columns per group)...")
        for idx, item in enumerate(sorted_items):
            group = item['group']
            if group != last_group:
                group_row += 1
                group_col = 0
                print(f"Starting new group '{group}' at row {group_row}")
                last_group = group
            try:
                print(f"[{idx}] Adding item '{item['name']}' from group '{group}' at (col={group_col}, row={group_row})")
                img = Image.open(item["preview"])
                img.thumbnail((thumb_width, thumb_height), RESAMPLE)
                thumb = ImageTk.PhotoImage(img)
                self.thumbs.append(thumb)

                # Card frame: horizontal layout (image left, buttons right)
                card = Frame(self.frame, bg=DARKER_GRAY, relief=FLAT, bd=0, padx=0, pady=0, highlightthickness=0, width=thumb_width+BUTTON_WIDTH, height=thumb_height)
                card.grid_propagate(0)

                # Image label
                img_label = Label(card, image=thumb, bg=DARKER_GRAY, cursor="hand2", highlightthickness=0, bd=0)
                img_label.place(x=0, y=0, width=thumb_width, height=thumb_height)
                img_label.bind("<Button-1>", lambda e, p=item["psd"]: self.open_photoshop(p))

                # Button stack to right of image
                btn_frame = Frame(card, bg=DARKER_GRAY, width=BUTTON_WIDTH, height=thumb_height)
                btn_frame.place(x=thumb_width, y=0, width=BUTTON_WIDTH, height=thumb_height)
                small_btn_opts = dict(font=("Segoe UI", 7), width=6, padx=0, pady=0, bg=ACCENT, fg=WHITE, relief=FLAT, bd=0, highlightthickness=0, activebackground=WHITE, activeforeground=ACCENT, anchor="w")
                Button(btn_frame, text="folder", command=lambda p=item["folder"]: self.open_explorer(p), **small_btn_opts, height=1).pack(side=TOP, fill=X, pady=(6,2))
                Button(btn_frame, text="gen01", command=lambda p=item["gen_folder"]: self.open_explorer(p), **small_btn_opts, height=1).pack(side=TOP, fill=X, pady=(2,2))
                # Upscale button
                upscale_psd_path = None
                # Try to determine the upscale PSD path for both modes
                if item.get("source_type") == "upscale":
                    # In upscale mode, get the PSD next to the PNG
                    upscale_psd_path = Path(item["preview"]).with_suffix('.psd')
                else:
                    # In original mode, check if Upscale/<item>.psd exists
                    group_folder = Path(item["folder"])
                    upscale_folder = group_folder / "Upscale"
                    candidate = upscale_folder / f"{item['name']}_upscale.psd"
                    if candidate.exists():
                        upscale_psd_path = candidate
                if upscale_psd_path and Path(upscale_psd_path).exists():
                    Button(btn_frame, text="upscale", command=lambda p=str(upscale_psd_path): self.open_photoshop(p), **small_btn_opts, height=1).pack(side=TOP, fill=X, pady=(2,6))
                else:
                    Button(btn_frame, text="upscale", state=DISABLED, **small_btn_opts, height=1).pack(side=TOP, fill=X, pady=(2,6))
                # Optional name label above the buttons
                if self.show_names.get():
                    Label(btn_frame, text=item["name"], bg=DARKER_GRAY, fg=WHITE, font=("Segoe UI", 8), anchor="w", wraplength=BUTTON_WIDTH-2, justify=LEFT).pack(side=TOP, fill=X, pady=(0,2))

                card.grid(row=group_row, column=group_col, padx=0, pady=0, sticky="nsew")
                print(f"Placed card at row={group_row}, col={group_col}, width={thumb_width+BUTTON_WIDTH}, height={thumb_height}")
                group_col += 1
                if group_col >= COLUMNS_PER_ROW:
                    group_col = 0
                    group_row += 1
            except Exception as e:
                print(f"Error loading {item['preview']}: {e}")
        print("Finished drawing items.")

    def open_photoshop(self, path):
        ps_path = self.ps_path_var.get() if hasattr(self, 'ps_path_var') else PHOTOSHOP_EXE
        if os.path.exists(ps_path) and os.path.exists(path):
            subprocess.Popen([ps_path, path])
        else:
            print("Photoshop or file not found.")

    def open_explorer(self, path):
        if os.path.isdir(path):
            subprocess.Popen(f'explorer "{path}"')

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
