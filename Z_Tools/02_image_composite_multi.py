"""
Combined Image Composer – Integrated Interactive and Automated Overlap Modes

Features:
• Load images as draggable pieces on a canvas.
• Use arrow keys to manually adjust selected pieces.
• “Auto Compose” automatically arranges images by brute‐forcing over a range of offsets.
  For each image, a two‑stage (coarse then fine) search is performed.
  Overlap scoring is computed per pixel in the overlapping region as follows:
    - If both pixels have alpha >= 128 (opaque):
         * If the normalized RGB similarity > 0.9, add +1.
         * Otherwise, add match_bonus * similarity.
    - If exactly one pixel is opaque, subtract mismatch_penalty.
    - Fully transparent–transparent pixels contribute 0.
• “Use Overlap Scoring” and “Use Edge Scoring” options are available.
• A debug overlay (when enabled) is drawn directly on the canvas as a semi‑transparent (40% opacity) overlay:
    - Each image is outlined with its unique green–blue border.
    - Overlapping regions are filled with pink.
• You can save the composite image and a JSON file (with positions) and later disassemble the composite.

Dependencies: Pillow, numpy
"""

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk, ImageDraw
import numpy as np
import os, threading, json, random

# ---------------------------------------------------------------------
# DraggableImage: used for interactive (manual) arrangement.
# ---------------------------------------------------------------------
class DraggableImage:
    def __init__(self, app, canvas, image, x, y, filename):
        self.app = app  # Reference to the main CombinedComposerApp
        self.canvas = canvas
        self.image = image  # PIL Image (RGBA)
        self.filename = filename
        self.image_tk = ImageTk.PhotoImage(self.image)
        self.id = self.canvas.create_image(x, y, image=self.image_tk, anchor='nw', tags='draggable')
        self.canvas.tag_bind(self.id, '<ButtonPress-1>', self.on_press)
        self.canvas.tag_bind(self.id, '<ButtonRelease-1>', self.on_release)
        self.canvas.tag_bind(self.id, '<B1-Motion>', self.on_motion)
        self.offset_x = 0
        self.offset_y = 0
        self.group = None  # For grouping overlapping pieces
        self.score = 0
        self.text_id = None
        # Assign a unique debug border color (in a green/blue range)
        r = 0
        g = random.randint(150, 255)
        b = random.randint(150, 255)
        self.debug_color = f'#{r:02x}{g:02x}{b:02x}'

    def on_press(self, event):
        self.offset_x = event.x
        self.offset_y = event.y
        self.app.select_image(self)
        self.app.canvas.focus_set()

    def on_release(self, event):
        if self.app.use_edge_scoring.get():
            self.snap_to_nearest_edge()
        self.app.update_scores()
        self.app.update_debug_overlay()

    def on_motion(self, event):
        dx = event.x - self.offset_x
        dy = event.y - self.offset_y
        if self.group:
            self.app.move_group(self.group, dx, dy)
        else:
            self.canvas.move(self.id, dx, dy)
        self.offset_x = event.x
        self.offset_y = event.y
        self.app.update_score_display()
        self.app.update_debug_overlay()

    def get_position(self):
        coords = self.canvas.coords(self.id)
        return int(coords[0]), int(coords[1])
    
    def snap_to_nearest_edge(self):
        current_x, current_y = self.get_position()
        current_w, current_h = self.image.width, self.image.height
        others = [img for img in self.app.draggable_images if img != self]
        best_score = float('-inf')
        best_position = (current_x, current_y)
        best_group = None
        threshold = 80  # edge score threshold
        for other in others:
            ox, oy = other.get_position()
            ow, oh = other.image.width, other.image.height
            positions = [
                (ox + ow, oy, 'left'),
                (ox - current_w, oy, 'right'),
                (ox, oy + oh, 'top'),
                (ox, oy - current_h, 'bottom')
            ]
            for x, y, pos in positions:
                if self.app.check_overlap(x, y, current_w, current_h, exclude=[self, other]):
                    continue
                score = self.app.calculate_edge_score_single(self.image, x, y,
                                                               other.image, ox, oy, pos)
                if score > best_score:
                    best_score = score
                    best_position = (x, y)
                    best_group = other.group
        if best_score >= threshold:
            dx = best_position[0] - current_x
            dy = best_position[1] - current_y
            self.canvas.move(self.id, dx, dy)
            if best_group:
                self.app.merge_groups(self, best_group)
            self.app.update_scores()
            self.app.update_score_display()

# ---------------------------------------------------------------------
# CombinedComposerApp: main application GUI integrating interactive
# and automated (auto compose) modes.
# ---------------------------------------------------------------------
class CombinedComposerApp:
    def __init__(self, master):
        self.master = master
        master.title("Image Composer – Integrated Modes")
        self.bg_color = '#1e1e1e'
        self.fg_color = '#ffffff'
        self.button_color = '#2d2d2d'
        self.highlight_color = '#3e3e3e'
        master.configure(bg=self.bg_color)
        
        # Variables for interactive mode
        self.image_files = []
        self.images = []             # List of PIL Images (RGBA)
        self.draggable_images = []   # List of DraggableImage instances
        self.selected_image = None
        self.groups = {}
        self.scores = {}
        self.group_counter = 1
        
        # Overlap and Edge Scoring options
        self.use_overlap_scoring = tk.BooleanVar(value=True)
        self.use_edge_scoring = tk.BooleanVar(value=True)
        self.max_offset_var = tk.IntVar(value=50)
        
        # Debug overlay toggle
        self.debug_mode = tk.BooleanVar(value=False)
        
        # Overlap scoring parameters
        self.match_bonus = 1
        self.mismatch_penalty = 5
        self.overlap_bonus_factor = 1
        
        # Composite image and positions (for automated composition)
        self.composite_image = None
        self.positions = []  # List of dicts for each image placed in the composite
        
        # For preview (PhotoImage) reference (if needed)
        self.composite_preview_image = None
        
        # Progress label (for auto compose and other routines)
        self.progress_label = None
        
        # Preview label (if used; here mainly for status messages)
        self.preview_label = None
        
        # Reference for the debug overlay image drawn on the canvas.
        self.debug_overlay_image = None
        
        self.create_widgets()
    
    def create_widgets(self):
        control_panel = tk.Frame(self.master, bg=self.bg_color)
        control_panel.pack(side="left", fill="y", padx=5)
        self.canvas = tk.Canvas(self.master, width=800, height=600, bg=self.highlight_color)
        self.canvas.pack(side="right", expand=True, fill="both")
        
        self.canvas.bind('<Left>', self.move_selected_left)
        self.canvas.bind('<Right>', self.move_selected_right)
        self.canvas.bind('<Up>', self.move_selected_up)
        self.canvas.bind('<Down>', self.move_selected_down)
        
        tk.Button(control_panel, text="Select Images", command=self.select_images,
                  bg=self.button_color, fg=self.fg_color, activebackground=self.highlight_color).pack(pady=5)
        tk.Button(control_panel, text="Auto Compose", command=self.auto_compose,
                  bg=self.button_color, fg=self.fg_color, activebackground=self.highlight_color).pack(pady=5)
        tk.Button(control_panel, text="Refine Composite", command=self.refine_composite,
                  bg=self.button_color, fg=self.fg_color, activebackground=self.highlight_color).pack(pady=5)
        tk.Button(control_panel, text="Fine-Tune Position", command=self.fine_tune_position,
                  bg=self.button_color, fg=self.fg_color, activebackground=self.highlight_color).pack(pady=5)
        tk.Button(control_panel, text="Save Composite", command=self.save_composites,
                  bg=self.button_color, fg=self.fg_color, activebackground=self.highlight_color).pack(pady=5)
        tk.Button(control_panel, text="Disassemble", command=self.disassemble,
                  bg=self.button_color, fg=self.fg_color, activebackground=self.highlight_color).pack(pady=5)
        
        opts_frame = tk.LabelFrame(control_panel, text="Scoring Options", bg=self.bg_color, fg=self.fg_color)
        opts_frame.pack(pady=5, fill="x")
        tk.Checkbutton(opts_frame, text="Use Overlap Scoring", variable=self.use_overlap_scoring,
                       bg=self.bg_color, fg=self.fg_color, selectcolor=self.button_color,
                       activebackground=self.highlight_color).pack(anchor="w")
        tk.Checkbutton(opts_frame, text="Use Edge Scoring", variable=self.use_edge_scoring,
                       bg=self.bg_color, fg=self.fg_color, selectcolor=self.button_color,
                       activebackground=self.highlight_color).pack(anchor="w")
        
        tk.Label(control_panel, text="Maximum Offset:", bg=self.bg_color, fg=self.fg_color).pack(pady=5)
        tk.Entry(control_panel, textvariable=self.max_offset_var, width=5,
                 bg=self.highlight_color, fg=self.fg_color, insertbackground=self.fg_color).pack()
        
        self.progress_label = tk.Label(control_panel, text="", bg=self.bg_color, fg=self.fg_color)
        self.progress_label.pack(pady=5)
        
        # The preview label is kept only for status messages.
        self.preview_label = tk.Label(control_panel, bg=self.bg_color)
        self.preview_label.pack(pady=5)
        
        tk.Checkbutton(control_panel, text="Show Debug Overlay", variable=self.debug_mode,
                       bg=self.bg_color, fg=self.fg_color, selectcolor=self.button_color,
                       activebackground=self.highlight_color, command=self.update_debug_overlay).pack(pady=5)
        
        self.score_label = tk.Label(control_panel, text="Selected Piece Score: N/A", bg=self.bg_color, fg=self.fg_color)
        self.score_label.pack(pady=5)
        self.group_score_label = tk.Label(control_panel, text="Selected Group Score: N/A", bg=self.bg_color, fg=self.fg_color)
        self.group_score_label.pack(pady=5)
        self.group_display = tk.Text(control_panel, height=10, bg=self.bg_color, fg=self.fg_color)
        self.group_display.pack(pady=5)
    
    # ----------------------------------------------------
    # Image Loading and Dragging (Interactive Mode)
    # ----------------------------------------------------
    def select_images(self):
        files = filedialog.askopenfilenames(title="Select Image Files", 
                                            filetypes=[("PNG Images", "*.png")])
        if files:
            self.image_files = list(files)
            self.images = [Image.open(f).convert("RGBA") for f in self.image_files]
            self.load_images()
    
    def load_images(self):
        self.canvas.delete("all")
        self.draggable_images = []
        self.groups = {}
        x, y = 50, 50
        group_name = f"Group{self.group_counter}"
        self.group_counter += 1
        for img, fname in zip(self.images, self.image_files):
            di = DraggableImage(self, self.canvas, img, x, y, os.path.basename(fname))
            di.group = group_name
            self.draggable_images.append(di)
            x += img.width
        self.update_group_display()
        self.update_debug_overlay()
    
    def load_composition(self):
        json_path = filedialog.askopenfilename(title="Select Composition JSON", filetypes=[("JSON Files", "*.json")])
        if not json_path:
            return
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON: {e}")
            return
        self.canvas.delete("all")
        self.draggable_images = []
        self.groups = {}
        images_info = data.get("images", [])
        group_name = data.get("group_name", f"Group{self.group_counter}")
        self.group_counter += 1
        min_x, min_y = 50, 50
        json_dir = os.path.dirname(json_path)
        for info in images_info:
            fname = info["filename"]
            x = info["x"] + min_x
            y = info["y"] + min_y
            image_path = os.path.join(json_dir, fname)
            if not os.path.exists(image_path):
                messagebox.showerror("Error", f"Image {fname} not found.")
                continue
            try:
                img = Image.open(image_path).convert("RGBA")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open image {fname}: {e}")
                continue
            di = DraggableImage(self, self.canvas, img, x, y, fname)
            di.group = group_name
            self.draggable_images.append(di)
        self.update_group_display()
        self.update_debug_overlay()
    
    # ----------------------------------------------------
    # Automated (Overlap) Composition Functions
    # ----------------------------------------------------
    def search_best_offset(self, composite_img, img, max_offset, coarse_step, fine_step):
        best_score = -100000
        best_dx = 0
        best_dy = 0
        # Coarse search:
        for dx in range(-max_offset, max_offset+1, coarse_step):
            for dy in range(-max_offset, max_offset+1, coarse_step):
                score = self.calculate_matching_score(composite_img, img, dx, dy)
                if score > best_score:
                    best_score = score
                    best_dx = dx
                    best_dy = dy
        # Fine search around best candidate:
        for dx in range(best_dx - coarse_step, best_dx + coarse_step + 1, fine_step):
            for dy in range(best_dy - coarse_step, best_dy + coarse_step + 1, fine_step):
                score = self.calculate_matching_score(composite_img, img, dx, dy)
                if score > best_score:
                    best_score = score
                    best_dx = dx
                    best_dy = dy
        return best_dx, best_dy, best_score

    def auto_compose(self):
        if not self.images:
            messagebox.showinfo("Info", "No images selected.")
            return
        threading.Thread(target=self.auto_compose_thread).start()
    
    def auto_compose_thread(self):
        self.update_progress("Starting auto composition...")
        max_offset = self.max_offset_var.get()
        coarse_step = 5
        fine_step = 1
        base_img = self.images[0]
        composite_img = base_img.copy()
        self.positions = [{
            "filename": os.path.basename(self.image_files[0]),
            "x": 0,
            "y": 0,
            "width": base_img.width,
            "height": base_img.height,
        }]
        print(f"Base image: {self.image_files[0]} placed at (0,0)")
        for idx in range(1, len(self.images)):
            img = self.images[idx]
            print(f"Processing image {self.image_files[idx]}")
            dx, dy, score = self.search_best_offset(composite_img, img, max_offset, coarse_step, fine_step)
            if score <= 0:
                print(f"No positive overlap score for image {self.image_files[idx]}; skipping.")
                continue
            print(f"Best offset for image {self.image_files[idx]}: ({dx},{dy}) with score {score}")
            composite_img, updated_positions = self.update_composite_image(composite_img, img, dx, dy, idx)
            self.positions = updated_positions
            self.update_progress(f"Placed {idx+1} of {len(self.images)} images...")
        self.composite_image = composite_img
        self.update_progress("Auto composition completed.")
        self.update_canvas_positions()
    
    def calculate_matching_score(self, composite_img, img, dx, dy):
        comp_np = np.array(composite_img)
        img_np = np.array(img)
        x_start = max(0, dx)
        y_start = max(0, dy)
        x_end = min(comp_np.shape[1], dx + img_np.shape[1])
        y_end = min(comp_np.shape[0], dy + img_np.shape[0])
        if x_end <= x_start or y_end <= y_start:
            return -100000
        x_img_start = max(0, -dx)
        y_img_start = max(0, -dy)
        region_w = x_end - x_start
        region_h = y_end - y_start
        comp_region = comp_np[y_start:y_end, x_start:x_end]
        img_region = img_np[y_img_start:y_img_start+region_h, x_img_start:x_img_start+region_w]
        alpha_thresh = 128
        comp_opaque = comp_region[..., 3] >= alpha_thresh
        img_opaque = img_region[..., 3] >= alpha_thresh
        both_opaque = comp_opaque & img_opaque
        one_transparent = comp_opaque ^ img_opaque
        score = 0
        if np.any(both_opaque):
            diff = np.abs(comp_region[..., :3] - img_region[..., :3]).astype(np.float32)
            sim = 1 - np.mean(diff, axis=2)/255.0
            # Use elementwise multiplication on booleans converted to float:
            score += self.match_bonus * np.sum(both_opaque.astype(np.float32) * ((sim > 0.9).astype(np.float32)))
            score += self.match_bonus * np.sum(both_opaque.astype(np.float32) * ((sim <= 0.9).astype(np.float32)) * sim)
        score -= self.mismatch_penalty * np.sum(one_transparent)
        return score
    
    def update_composite_image(self, composite_img, img, dx, dy, idx):
        x_min = min(0, dx)
        y_min = min(0, dy)
        x_max = max(composite_img.width, dx + img.width)
        y_max = max(composite_img.height, dy + img.height)
        new_width = x_max - x_min
        new_height = y_max - y_min
        new_composite = Image.new("RGBA", (new_width, new_height), (0,0,0,0))
        comp_offset = (-x_min, -y_min)
        new_composite.paste(composite_img, comp_offset)
        img_offset = (dx - x_min, dy - y_min)
        new_composite.paste(img, img_offset, img)
        updated_positions = []
        for pos in self.positions:
            up = pos.copy()
            up["x"] += comp_offset[0]
            up["y"] += comp_offset[1]
            updated_positions.append(up)
        updated_positions.append({
            "filename": os.path.basename(self.image_files[idx]),
            "x": img_offset[0],
            "y": img_offset[1],
            "width": img.width,
            "height": img.height,
        })
        print(f"Image {self.image_files[idx]} placed at ({img_offset[0]}, {img_offset[1]})")
        return new_composite, updated_positions
    
    def update_progress(self, msg):
        self.progress_label.config(text=msg)
        self.master.update_idletasks()
    
    def update_canvas_positions(self):
        for pos in self.positions:
            fname = pos["filename"]
            for img in self.draggable_images:
                if img.filename == fname:
                    current_x, current_y = img.get_position()
                    new_x, new_y = pos["x"], pos["y"]
                    dx = new_x - current_x
                    dy = new_y - current_y
                    self.canvas.move(img.id, dx, dy)
        self.update_group_display()
        self.update_scores()
        self.update_score_display()
        self.update_debug_overlay()
    
    # ----------------------------------------------------
    # Refinement and Fine-Tuning (Interactive Mode)
    # ----------------------------------------------------
    def refine_composite(self):
        threading.Thread(target=self.refine_composite_thread).start()
    
    def refine_composite_thread(self):
        if not self.draggable_images:
            return
        placed = []
        unplaced = self.draggable_images.copy()
        current = unplaced.pop(0)
        placed.append(current)
        self.canvas.moveto(current.id, 100, 100)
        while unplaced:
            best_pair_score = float('-inf')
            best_attachment = None
            best_anchor = None
            best_position = None
            for anchor in placed:
                for candidate in unplaced:
                    pos, score = self.search_attachment_position(anchor, candidate, "right", "left", max_radius=30, step=2)
                    if score > best_pair_score:
                        best_pair_score = score
                        best_attachment = candidate
                        best_anchor = anchor
                        best_position = pos
            if best_attachment is None:
                candidate = unplaced.pop(0)
                anchor = placed[-1]
                ax, ay = anchor.get_position()
                best_position = (ax + anchor.image.width + 10, ay)
                self.canvas.moveto(candidate.id, best_position[0], best_position[1])
                placed.append(candidate)
            else:
                self.canvas.moveto(best_attachment.id, best_position[0], best_position[1])
                placed.append(best_attachment)
                unplaced.remove(best_attachment)
                self.merge_groups(best_attachment, best_anchor.group)
            self.update_scores()
            self.update_score_display()
            self.update_debug_overlay()
        self.update_group_scores()
    
    def search_attachment_position(self, anchor, candidate, anchor_edge="right", candidate_edge="left", max_radius=30, step=2):
        ax, ay = anchor.get_position()
        if anchor_edge=="right" and candidate_edge=="left":
            ideal_x = ax + anchor.image.width
            ideal_y = ay
        elif anchor_edge=="left" and candidate_edge=="right":
            ideal_x = ax - candidate.image.width
            ideal_y = ay
        elif anchor_edge=="bottom" and candidate_edge=="top":
            ideal_x = ax
            ideal_y = ay + anchor.image.height
        elif anchor_edge=="top" and candidate_edge=="bottom":
            ideal_x = ax
            ideal_y = ay - candidate.image.height
        else:
            ideal_x, ideal_y = candidate.get_position()
        best_score = float('-inf')
        best_position = (ideal_x, ideal_y)
        for dx, dy in self.spiral_offsets(max_radius, step):
            test_x = ideal_x + dx
            test_y = ideal_y + dy
            if self.check_overlap(test_x, test_y, candidate.image.width, candidate.image.height, exclude=[candidate]):
                continue
            score = self.calculate_edge_score_pair(anchor, ax, ay,
                                                   candidate, test_x, test_y,
                                                   anchor_edge, candidate_edge)
            if score > best_score:
                best_score = score
                best_position = (test_x, test_y)
        return best_position, best_score
    
    def spiral_offsets(self, max_radius, step):
        offsets = []
        for r in range(0, max_radius+1, step):
            for dx in range(-r, r+1, step):
                for dy in range(-r, r+1, step):
                    if abs(dx)==r or abs(dy)==r:
                        offsets.append((dx,dy))
        return offsets
    
    def fine_tune_position(self):
        if self.selected_image is None:
            messagebox.showinfo("Info", "Select an image first.")
            return
        threading.Thread(target=self.fine_tune_selected_image).start()
    
    def fine_tune_selected_image(self):
        use_overlap = self.use_overlap_scoring.get()
        use_edge = self.use_edge_scoring.get()
        if not use_overlap and not use_edge:
            messagebox.showinfo("Info", "Select at least one scoring method.")
            return
        max_offset = 5
        best_score = float('-inf')
        best_dx = 0
        best_dy = 0
        idx = self.draggable_images.index(self.selected_image)
        target_image = self.selected_image.image
        others = [img for i, img in enumerate(self.draggable_images) if i != idx]
        if not others:
            messagebox.showinfo("Info", "No other images to compare.")
            return
        comp_img, positions = self.create_composite(others)
        comp_np = np.array(comp_img)
        x0, y0 = self.selected_image.get_position()
        target_np = np.array(target_image)
        offsets = [(dx, dy) for dx in range(-max_offset, max_offset+1) for dy in range(-max_offset, max_offset+1)]
        for dx, dy in offsets:
            x = x0 + dx
            y = y0 + dy
            if self.check_overlap(x, y, target_image.width, target_image.height, exclude=[self.selected_image]):
                continue
            score = 0
            if use_overlap:
                score += self.calculate_overlap_score(comp_np, target_np, x - positions[0][1], y - positions[0][2])
            if use_edge:
                score += self.calculate_edge_score(comp_np, target_np, x - positions[0][1], y - positions[0][2])
            if score > best_score:
                best_score = score
                best_dx = dx
                best_dy = dy
        self.canvas.move(self.selected_image.id, best_dx, best_dy)
        self.update_scores()
        self.update_score_display()
        self.update_debug_overlay()
    
    def check_overlap(self, x, y, width, height, exclude=[]):
        rect1 = (x, y, x+width, y+height)
        for img in self.draggable_images:
            if img in exclude:
                continue
            ix, iy = img.get_position()
            rect2 = (ix, iy, ix+img.image.width, iy+img.image.height)
            if self.rectangles_overlap(rect1, rect2):
                return True
        return False
    
    def rectangles_overlap(self, r1, r2):
        l1, t1, r1_, b1 = r1
        l2, t2, r2_, b2 = r2
        return not (r1_ <= l2 or r2_ <= l1 or b1 <= t2 or b2 <= t1)
    
    def move_group(self, group, dx, dy):
        for img in self.draggable_images:
            if img.group == group:
                self.canvas.move(img.id, dx, dy)
        self.update_score_display()
        self.update_debug_overlay()
    
    def merge_groups(self, img, other_group):
        old = img.group
        if old == other_group:
            return
        for i in self.draggable_images:
            if i.group == old:
                i.group = other_group
        self.update_group_display()
    
    def calculate_edge_score_pair(self, img1, x1, y1, img2, x2, y2, edge1, edge2):
        arr1 = np.array(img1.image)
        arr2 = np.array(img2.image)
        edgeA = self.extract_edge(arr1, edge1)
        edgeB = self.extract_edge(arr2, edge2)
        return self.compare_edge_arrays(edgeA, edgeB)
    
    def compare_edge_arrays(self, edge1, edge2):
        if edge1 is None or edge2 is None:
            return 0
        m = min(len(edge1), len(edge2))
        if m == 0:
            return 0
        return self.compute_similarity(edge1[:m].reshape(-1, 4), edge2[:m].reshape(-1, 4))
    
    def extract_edge(self, arr, position, invert=False):
        if position == "left":
            return arr[:,0,:] if not invert else arr[:,-1,:]
        elif position == "right":
            return arr[:,-1,:] if not invert else arr[:,0,:]
        elif position == "top":
            return arr[0,:,:] if not invert else arr[-1,:,:]
        elif position == "bottom":
            return arr[-1,:,:] if not invert else arr[0,:,:]
        return None
    
    def compute_similarity(self, arr1, arr2):
        arr1 = arr1.astype(np.float32)
        arr2 = arr2.astype(np.float32)
        opaque1 = (arr1[:,3] > 0)
        opaque2 = (arr2[:,3] > 0)
        both_opaque = opaque1 & opaque2
        both_transparent = (~opaque1) & (~opaque2)
        one_opaque = opaque1 ^ opaque2
        sim = np.zeros(arr1.shape[0], dtype=np.float32)
        if np.any(both_opaque):
            diff = np.abs(arr1[both_opaque][:, :3] - arr2[both_opaque][:, :3])
            sim[both_opaque] = 1.0 - np.mean(diff, axis=1)/255.0
        sim[both_transparent] = 0
        sim[one_opaque] = 0.0
        return np.sum(sim)
    
    def calculate_overlap_score(self, comp_np, target_np, x_offset, y_offset):
        ch, cw = comp_np.shape[:2]
        th, tw = target_np.shape[:2]
        x_start = max(0, x_offset)
        y_start = max(0, y_offset)
        x_end = min(cw, x_offset+tw)
        y_end = min(ch, y_offset+th)
        tx_start = max(0, -x_offset)
        ty_start = max(0, -y_offset)
        if x_end <= x_start or y_end <= y_start:
            return 0
        comp_region = comp_np[y_start:y_end, x_start:x_end]
        target_region = target_np[ty_start:ty_start+(y_end-y_start), tx_start:tx_start+(x_end-x_start)]
        score = self.score_overlap_regions(comp_region, target_region)
        return score * self.overlap_bonus_factor
    
    def score_overlap_regions(self, comp_region, target_region):
        a1 = comp_region.reshape(-1,4)
        a2 = target_region.reshape(-1,4)
        return self.compute_similarity(a1, a2)
    
    def calculate_edge_score(self, comp_np, target_np, x_offset, y_offset):
        ch, cw = comp_np.shape[:2]
        th, tw = target_np.shape[:2]
        positions = ["left", "right", "top", "bottom"]
        best = 0
        for pos in positions:
            score = self.score_edge_position(comp_np, target_np, x_offset, y_offset, pos)
            if score > best:
                best = score
        return best
    
    def score_edge_position(self, comp_np, target_np, x_offset, y_offset, position):
        edge_comp = self.extract_edge_at_position(comp_np, x_offset, y_offset, target_np.shape[1], target_np.shape[0], position)
        edge_target = self.extract_edge(target_np, position)
        return self.compare_edge_arrays(edge_comp, edge_target)
    
    def extract_edge_at_position(self, comp_np, x_offset, y_offset, tw, th, position):
        ch, cw = comp_np.shape[:2]
        if position=="left":
            x = x_offset - 1
            if x < 0 or x >= cw:
                return None
            y_start = max(0, y_offset)
            y_end = min(ch, y_offset+th)
            return comp_np[y_start:y_end, x, :]
        elif position=="right":
            x = x_offset+tw
            if x < 0 or x >= cw:
                return None
            y_start = max(0, y_offset)
            y_end = min(ch, y_offset+th)
            return comp_np[y_start:y_end, x, :]
        elif position=="top":
            y = y_offset - 1
            if y < 0 or y >= ch:
                return None
            x_start = max(0, x_offset)
            x_end = min(cw, x_offset+tw)
            return comp_np[y, x_start:x_end, :]
        elif position=="bottom":
            y = y_offset+th
            if y < 0 or y >= ch:
                return None
            x_start = max(0, x_offset)
            x_end = min(cw, x_offset+tw)
            return comp_np[y, x_start:x_end, :]
        return None
    
    def create_composite(self, images):
        positions = []
        x_coords = []
        y_coords = []
        for img in images:
            x, y = img.get_position()
            x_coords.extend([x, x+img.image.width])
            y_coords.extend([y, y+img.image.height])
            positions.append((img, x, y))
        min_x = min(x_coords)
        min_y = min(y_coords)
        max_x = max(x_coords)
        max_y = max(y_coords)
        width = max_x - min_x
        height = max_y - min_y
        comp = Image.new("RGBA", (width, height), (0,0,0,0))
        for img, x, y in positions:
            comp.paste(img.image, (x-min_x, y-min_y), img.image)
        return comp, positions
    
    def update_scores(self):
        if self.selected_image is None:
            self.score_label.config(text="Selected Piece Score: N/A")
            self.group_score_label.config(text="Selected Group Score: N/A")
            return
        use_overlap = self.use_overlap_scoring.get()
        use_edge = self.use_edge_scoring.get()
        idx = self.draggable_images.index(self.selected_image)
        target_image = self.selected_image.image
        others = [img for i, img in enumerate(self.draggable_images) if i != idx]
        if not others:
            self.selected_image.score = 0
        else:
            comp, positions = self.create_composite(others)
            comp_np = np.array(comp)
            x0, y0 = self.selected_image.get_position()
            target_np = np.array(target_image)
            score = 0
            if use_overlap:
                score += self.calculate_overlap_score(comp_np, target_np, x0-positions[0][1], y0-positions[0][2])
            if use_edge:
                score += self.calculate_edge_score(comp_np, target_np, x0-positions[0][1], y0-positions[0][2])
            self.selected_image.score = score
        self.score_label.config(text=f"Selected Piece Score: {self.selected_image.score}")
        if self.selected_image.group:
            group_images = [img for img in self.draggable_images if img.group == self.selected_image.group]
            total = 0
            for img in group_images:
                others = [i for i in group_images if i != img]
                if not others:
                    continue
                comp, pos = self.create_composite(others)
                comp_np = np.array(comp)
                x0, y0 = img.get_position()
                target_np = np.array(img.image)
                s = 0
                if self.use_overlap_scoring.get():
                    s += self.calculate_overlap_score(comp_np, target_np, x0-pos[0][1], y0-pos[0][2])
                if self.use_edge_scoring.get():
                    s += self.calculate_edge_score(comp_np, target_np, x0-pos[0][1], y0-pos[0][2])
                total += s
            self.scores[self.selected_image.group] = total
            self.group_score_label.config(text=f"Selected Group Score: {total}")
        else:
            self.group_score_label.config(text="Selected Group Score: N/A")
    
    def update_group_scores(self):
        for group in self.groups:
            group_images = [img for img in self.draggable_images if img.group == group]
            total = 0
            for img in group_images:
                others = [i for i in group_images if i != img]
                if not others:
                    continue
                comp, pos = self.create_composite(others)
                comp_np = np.array(comp)
                x0, y0 = img.get_position()
                target_np = np.array(img.image)
                s = 0
                if self.use_overlap_scoring.get():
                    s += self.calculate_overlap_score(comp_np, target_np, x0-pos[0][1], y0-pos[0][2])
                if self.use_edge_scoring.get():
                    s += self.calculate_edge_score(comp_np, target_np, x0-pos[0][1], y0-pos[0][2])
                total += s
            self.scores[group] = total
    
    def update_group_display(self):
        self.group_display.delete("1.0", tk.END)
        info = "Groups:\n"
        self.groups = {}
        for img in self.draggable_images:
            group = img.group if img.group else "Ungrouped"
            if group not in self.groups:
                self.groups[group] = []
            self.groups[group].append(img.filename)
        for g, files in self.groups.items():
            info += f"{g}:\n"
            for f in files:
                info += f"  {f}\n"
        self.group_display.insert(tk.END, info)
    
    def update_debug_overlay(self):
        self.canvas.delete("debug_overlay")
        if not self.debug_mode.get():
            return
        self.canvas.update()
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        overlay = Image.new("RGBA", (cw, ch), (0,0,0,0))
        draw = ImageDraw.Draw(overlay, "RGBA")
        # Draw green–blue border (0.4 opacity) for each image.
        for img in self.draggable_images:
            x, y = img.get_position()
            w, h = img.image.width, img.image.height
            color_hex = img.debug_color
            r = int(color_hex[1:3], 16)
            g = int(color_hex[3:5], 16)
            b = int(color_hex[5:7], 16)
            border_color = (r, g, b, int(0.4 * 255))
            draw.rectangle([x, y, x+w, y+h], outline=border_color)
        # Fill overlapping regions in pink (0.4 opacity).
        pink = (255, 0, 255, int(0.4 * 255))
        n = len(self.draggable_images)
        for i in range(n):
            for j in range(i+1, n):
                img1 = self.draggable_images[i]
                img2 = self.draggable_images[j]
                x1, y1 = img1.get_position()
                w1, h1 = img1.image.width, img1.image.height
                x2, y2 = img2.get_position()
                w2, h2 = img2.image.width, img2.image.height
                overlap_left = max(x1, x2)
                overlap_top = max(y1, y2)
                overlap_right = min(x1+w1, x2+w2)
                overlap_bottom = min(y1+h1, y2+h2)
                if overlap_right > overlap_left and overlap_bottom > overlap_top:
                    draw.rectangle([overlap_left, overlap_top, overlap_right, overlap_bottom], fill=pink)
        self.debug_overlay_image = ImageTk.PhotoImage(overlay)
        self.canvas.create_image(0, 0, image=self.debug_overlay_image, anchor="nw", tags="debug_overlay")
    
    def update_score_display(self):
        self.canvas.delete("score_text")
        if self.selected_image:
            x, y = self.selected_image.get_position()
            txt = f"Score: {self.selected_image.score}"
            self.selected_image.text_id = self.canvas.create_text(
                x + self.selected_image.image.width//2, y - 10, text=txt, fill="white", tags="score_text")
    
    def select_image(self, img):
        self.selected_image = img
        self.update_scores()
        self.update_score_display()
        self.update_debug_overlay()
    
    def move_selected_left(self, event):
        if self.selected_image:
            self.canvas.move(self.selected_image.id, -1, 0)
            self.update_scores()
            self.update_score_display()
            self.update_debug_overlay()
    
    def move_selected_right(self, event):
        if self.selected_image:
            self.canvas.move(self.selected_image.id, 1, 0)
            self.update_scores()
            self.update_score_display()
            self.update_debug_overlay()
    
    def move_selected_up(self, event):
        if self.selected_image:
            self.canvas.move(self.selected_image.id, 0, -1)
            self.update_scores()
            self.update_score_display()
            self.update_debug_overlay()
    
    def move_selected_down(self, event):
        if self.selected_image:
            self.canvas.move(self.selected_image.id, 0, 1)
            self.update_scores()
            self.update_score_display()
            self.update_debug_overlay()
    
    # ----------------------------------------------------
    # Saving and Disassembly
    # ----------------------------------------------------
    def save_composites(self):
        if not self.groups:
            messagebox.showinfo("Info", "No groups to save.")
            return
        save_dir = filedialog.askdirectory(title="Select Directory to Save Composite and JSON")
        if not save_dir:
            return
        for group, files in self.groups.items():
            group_imgs = [img for img in self.draggable_images if img.group == group]
            if not group_imgs:
                continue
            comp, positions = self.create_composite(group_imgs)
            min_x = min([img.get_position()[0] for img in group_imgs])
            min_y = min([img.get_position()[1] for img in group_imgs])
            pos_list = []
            for img in group_imgs:
                x, y = img.get_position()
                pos_list.append({
                    "filename": img.filename,
                    "x": x - min_x,
                    "y": y - min_y,
                    "width": img.image.width,
                    "height": img.image.height
                })
            comp_filename = os.path.join(save_dir, f"{group}_composite.png")
            comp.save(comp_filename)
            json_filename = os.path.join(save_dir, f"{group}_composite.json")
            data = {"group_name": group, "images": pos_list, "composite_size": comp.size}
            with open(json_filename, "w") as f:
                json.dump(data, f, indent=4)
            print(f"Saved composite: {comp_filename} and JSON: {json_filename}")
    
    def disassemble(self):
        comp_path = filedialog.askopenfilename(title="Select Composite Image", filetypes=[("PNG Images", "*.png")])
        json_path = filedialog.askopenfilename(title="Select JSON File", filetypes=[("JSON Files", "*.json")])
        if not comp_path or not json_path:
            messagebox.showinfo("Info", "Select both composite image and JSON file.")
            return
        try:
            comp_img = Image.open(comp_path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open composite image: {e}")
            return
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON: {e}")
            return
        out_dir = filedialog.askdirectory(title="Select Directory to Save Disassembled Images")
        if not out_dir:
            return
        for info in data["images"]:
            x = info["x"]
            y = info["y"]
            w = info["width"]
            h = info["height"]
            fname = info["filename"]
            box = (x, y, x+w, y+h)
            cropped = comp_img.crop(box)
            save_path = os.path.join(out_dir, fname)
            cropped.save(save_path)
            print(f"Saved extracted image: {save_path}")
        messagebox.showinfo("Info", f"Disassembled images saved to {out_dir}")
    
    def update_canvas_positions(self):
        for pos in self.positions:
            fname = pos["filename"]
            for img in self.draggable_images:
                if img.filename == fname:
                    current_x, current_y = img.get_position()
                    new_x, new_y = pos["x"], pos["y"]
                    dx = new_x - current_x
                    dy = new_y - current_y
                    self.canvas.move(img.id, dx, dy)
        self.update_group_display()
        self.update_scores()
        self.update_score_display()
        self.update_debug_overlay()
    
    def run(self):
        self.master.mainloop()

# ---------------------------------------------------------------------
# Main: Create the application window and run the CombinedComposerApp.
# ---------------------------------------------------------------------
def main():
    root = tk.Tk()
    app = CombinedComposerApp(root)
    app.run()

if __name__ == "__main__":
    main()
