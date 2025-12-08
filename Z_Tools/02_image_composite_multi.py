"""
Combined Image Composer – Integrated Interactive and Automated Overlap Modes
This is helpful for use with certain tree images ( heartwood ) and art that have been sliced into vertical strips
attempts to reassemble like a puzzle with possible overlapping parts into a composite single image and store the slice information for later
we can then alter the single composited image , alter it , then deconstruct into its original sliced image strips .

- “Auto Compose” automatically arranges images by brute‐forcing over a range of offsets.
  For each image, a two‑stage (coarse then fine) search is performed.
  Overlap scoring is computed per pixel in the overlapping region as follows:
    - If both pixels have alpha >= 128 (opaque):
         * If the normalized RGB similarity > 0.9, add +1.
         * Otherwise, add match_bonus * similarity.
    - If exactly one pixel is opaque, subtract mismatch_penalty.
    - Fully transparent–transparent pixels contribute 0.
- “Use Overlap Scoring” and “Use Edge Scoring” options are available.

A debug overlay  on the canvas as a semi‑transparent (40% opacity) overlay:
    - Each image is outlined with its unique green–blue border.
    - Overlapping regions are filled with pink.

WORKFLOW:
Load images as draggable pieces on a canvas.
Use arrow keys to manually adjust selected pieces.
Save the composite image and a JSON file (with positions) and later disassemble the composite.

TOOLSGROUP::RENDER
SORTGROUP::7
SORTPRIORITY::71
STATUS::wip
VERSION::20251207
"""

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk, ImageDraw
import numpy as np
import os, threading, json, random


# DraggableImage: used for interactive manual arrangement.

class DraggableImage:
    def __init__(self, app, canvas, image, initial_x_position, initial_y_position, filename):
        self.app = app  # Reference to the main CombinedComposerApp
        self.canvas = canvas
        self.image = image  # PIL Image (RGBA)
        self.filename = filename
        self.image_tk = ImageTk.PhotoImage(self.image)
        self.canvas_image_id = self.canvas.create_image(initial_x_position, initial_y_position, image=self.image_tk, anchor='nw', tags='draggable')
        self.canvas.tag_bind(self.canvas_image_id, '<ButtonPress-1>', self.on_press)
        self.canvas.tag_bind(self.canvas_image_id, '<ButtonRelease-1>', self.on_release)
        self.canvas.tag_bind(self.canvas_image_id, '<B1-Motion>', self.on_motion)
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.group = None  # For grouping overlapping pieces
        self.overlap_score = 0
        self.score_text_id = None
        # Assign a unique debug border color (in a green/blue range)
        red_component = 0
        green_component = random.randint(150, 255)
        blue_component = random.randint(150, 255)
        self.debug_border_color = f'#{red_component:02x}{green_component:02x}{blue_component:02x}'

    def on_press(self, event):
        self.drag_offset_x = event.x
        self.drag_offset_y = event.y
        self.app.select_image(self)
        self.app.canvas.focus_set()

    def on_release(self, event):
        if self.app.use_edge_scoring.get():
            self.snap_to_nearest_edge()
        self.app.update_scores()
        self.app.update_debug_overlay()

    def on_motion(self, event):
        delta_x = event.x - self.drag_offset_x
        delta_y = event.y - self.drag_offset_y
        if self.group:
            self.app.move_group(self.group, delta_x, delta_y)
        else:
            self.canvas.move(self.canvas_image_id, delta_x, delta_y)
        self.drag_offset_x = event.x
        self.drag_offset_y = event.y
        self.app.update_score_display()
        self.app.update_debug_overlay()

    def get_position(self):
        canvas_coordinates = self.canvas.coords(self.canvas_image_id)
        position_x = int(canvas_coordinates[0])
        position_y = int(canvas_coordinates[1])
        return position_x, position_y
    
    def snap_to_nearest_edge(self):
        current_x_position, current_y_position = self.get_position()
        current_image_width = self.image.width
        current_image_height = self.image.height
        other_draggable_images = [img for img in self.app.draggable_images if img != self]
        best_edge_score = float('-inf')
        best_snap_position = (current_x_position, current_y_position)
        best_matching_group = None
        edge_score_threshold = 80  # edge score threshold
        
        for other_image in other_draggable_images:
            other_x_position, other_y_position = other_image.get_position()
            other_image_width = other_image.image.width
            other_image_height = other_image.image.height
            
            # Calculate potential snap positions (right, left, bottom, top)
            potential_snap_positions = [
                (other_x_position + other_image_width, other_y_position, 'left'),
                (other_x_position - current_image_width, other_y_position, 'right'),
                (other_x_position, other_y_position + other_image_height, 'top'),
                (other_x_position, other_y_position - current_image_height, 'bottom')
            ]
            
            for test_x_position, test_y_position, edge_position in potential_snap_positions:
                if self.app.check_overlap(test_x_position, test_y_position, current_image_width, current_image_height, exclude=[self, other_image]):
                    continue
                    
                edge_score = self.app.calculate_edge_score_single(
                    self.image, test_x_position, test_y_position,
                    other_image.image, other_x_position, other_y_position, edge_position
                )
                
                if edge_score > best_edge_score:
                    best_edge_score = edge_score
                    best_snap_position = (test_x_position, test_y_position)
                    best_matching_group = other_image.group
                    
        if best_edge_score >= edge_score_threshold:
            move_delta_x = best_snap_position[0] - current_x_position
            move_delta_y = best_snap_position[1] - current_y_position
            self.canvas.move(self.canvas_image_id, move_delta_x, move_delta_y)
            if best_matching_group:
                self.app.merge_groups(self, best_matching_group)
            self.app.update_scores()
            self.app.update_score_display()


# CombinedComposerApp: main application GUI integrating interactive
# and automated auto compose modes.

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
    
    
    # Image Loading and Dragging 
    
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
        initial_canvas_x_position = 50
        initial_canvas_y_position = 50
        current_group_name = f"Group{self.group_counter}"
        self.group_counter += 1
        
        for loaded_image, image_filepath in zip(self.images, self.image_files):
            draggable_image_instance = DraggableImage(
                self, self.canvas, loaded_image, 
                initial_canvas_x_position, initial_canvas_y_position, 
                os.path.basename(image_filepath)
            )
            draggable_image_instance.group = current_group_name
            self.draggable_images.append(draggable_image_instance)
            initial_canvas_x_position += loaded_image.width
            
        self.update_group_display()
        self.update_debug_overlay()
    
    def load_composition(self):
        json_filepath = filedialog.askopenfilename(title="Select Composition JSON", filetypes=[("JSON Files", "*.json")])
        if not json_filepath:
            return
            
        try:
            with open(json_filepath, "r") as json_file:
                composition_data = json.load(json_file)
        except Exception as load_error:
            messagebox.showerror("Error", f"Failed to load JSON: {load_error}")
            return
            
        self.canvas.delete("all")
        self.draggable_images = []
        self.groups = {}
        
        images_metadata_list = composition_data.get("images", [])
        loaded_group_name = composition_data.get("group_name", f"Group{self.group_counter}")
        self.group_counter += 1
        
        canvas_offset_x = 50
        canvas_offset_y = 50
        json_directory = os.path.dirname(json_filepath)
        
        for image_metadata in images_metadata_list:
            image_filename = image_metadata["filename"]
            image_x_position = image_metadata["x"] + canvas_offset_x
            image_y_position = image_metadata["y"] + canvas_offset_y
            full_image_path = os.path.join(json_directory, image_filename)
            
            if not os.path.exists(full_image_path):
                messagebox.showerror("Error", f"Image {image_filename} not found.")
                continue
                
            try:
                loaded_pil_image = Image.open(full_image_path).convert("RGBA")
            except Exception as image_error:
                messagebox.showerror("Error", f"Failed to open image {image_filename}: {image_error}")
                continue
                
            draggable_image_instance = DraggableImage(
                self, self.canvas, loaded_pil_image, 
                image_x_position, image_y_position, image_filename
            )
            draggable_image_instance.group = loaded_group_name
            self.draggable_images.append(draggable_image_instance)
            
        self.update_group_display()
        self.update_debug_overlay()
    
    
    # Automated (Overlap) Composition Functions
    
    def search_best_offset(self, composite_image, new_image, maximum_offset_range, coarse_search_step, fine_search_step):
        best_matching_score = -100000
        best_offset_x = 0
        best_offset_y = 0
        
        # Coarse search: scan with larger steps to find general area
        for offset_x in range(-maximum_offset_range, maximum_offset_range + 1, coarse_search_step):
            for offset_y in range(-maximum_offset_range, maximum_offset_range + 1, coarse_search_step):
                current_score = self.calculate_matching_score(composite_image, new_image, offset_x, offset_y)
                if current_score > best_matching_score:
                    best_matching_score = current_score
                    best_offset_x = offset_x
                    best_offset_y = offset_y
                    
        # Fine search: refine around best candidate with smaller steps
        for offset_x in range(best_offset_x - coarse_search_step, best_offset_x + coarse_search_step + 1, fine_search_step):
            for offset_y in range(best_offset_y - coarse_search_step, best_offset_y + coarse_search_step + 1, fine_search_step):
                current_score = self.calculate_matching_score(composite_image, new_image, offset_x, offset_y)
                if current_score > best_matching_score:
                    best_matching_score = current_score
                    best_offset_x = offset_x
                    best_offset_y = offset_y
                    
        return best_offset_x, best_offset_y, best_matching_score

    def auto_compose(self):
        if not self.images:
            messagebox.showinfo("Info", "No images selected.")
            return
        threading.Thread(target=self.auto_compose_thread).start()
    
    def auto_compose_thread(self):
        self.update_progress("Starting auto composition...")
        maximum_offset_range = self.max_offset_var.get()
        coarse_search_step_size = 5
        fine_search_step_size = 1
        
        base_image = self.images[0]
        composite_image = base_image.copy()
        
        self.positions = [{
            "filename": os.path.basename(self.image_files[0]),
            "x": 0,
            "y": 0,
            "width": base_image.width,
            "height": base_image.height,
        }]
        print(f"Base image: {self.image_files[0]} placed at (0,0)")
        
        for image_index in range(1, len(self.images)):
            current_image = self.images[image_index]
            current_image_filepath = self.image_files[image_index]
            print(f"Processing image {current_image_filepath}")
            
            best_offset_x, best_offset_y, best_score = self.search_best_offset(
                composite_image, current_image, 
                maximum_offset_range, coarse_search_step_size, fine_search_step_size
            )
            
            if best_score <= 0:
                print(f"No positive overlap score for image {current_image_filepath}; skipping.")
                continue
                
            print(f"Best offset for image {current_image_filepath}: ({best_offset_x},{best_offset_y}) with score {best_score}")
            
            composite_image, updated_positions = self.update_composite_image(
                composite_image, current_image, best_offset_x, best_offset_y, image_index
            )
            self.positions = updated_positions
            self.update_progress(f"Placed {image_index + 1} of {len(self.images)} images...")
            
        self.composite_image = composite_image
        self.update_progress("Auto composition completed.")
        self.update_canvas_positions()
    
    def calculate_matching_score(self, composite_image, new_image, offset_x, offset_y):
        composite_array = np.array(composite_image)
        new_image_array = np.array(new_image)
        
        # Calculate overlapping region boundaries
        overlap_x_start = max(0, offset_x)
        overlap_y_start = max(0, offset_y)
        overlap_x_end = min(composite_array.shape[1], offset_x + new_image_array.shape[1])
        overlap_y_end = min(composite_array.shape[0], offset_y + new_image_array.shape[0])
        
        # Check if there's no overlap
        if overlap_x_end <= overlap_x_start or overlap_y_end <= overlap_y_start:
            return -100000
            
        # Calculate corresponding region in new image
        new_image_x_start = max(0, -offset_x)
        new_image_y_start = max(0, -offset_y)
        overlap_region_width = overlap_x_end - overlap_x_start
        overlap_region_height = overlap_y_end - overlap_y_start
        
        # Extract overlapping regions from both images
        composite_overlap_region = composite_array[overlap_y_start:overlap_y_end, overlap_x_start:overlap_x_end]
        new_image_overlap_region = new_image_array[
            new_image_y_start:new_image_y_start + overlap_region_height, 
            new_image_x_start:new_image_x_start + overlap_region_width
        ]
        
        # Determine pixel opacity using alpha channel threshold
        alpha_threshold = 128
        composite_pixels_opaque = composite_overlap_region[..., 3] >= alpha_threshold
        new_image_pixels_opaque = new_image_overlap_region[..., 3] >= alpha_threshold
        both_pixels_opaque = composite_pixels_opaque & new_image_pixels_opaque
        one_pixel_transparent = composite_pixels_opaque ^ new_image_pixels_opaque
        
        matching_score = 0
        
        # Calculate similarity for pixels where both are opaque
        if np.any(both_pixels_opaque):
            rgb_difference = np.abs(composite_overlap_region[..., :3] - new_image_overlap_region[..., :3]).astype(np.float32)
            color_similarity = 1 - np.mean(rgb_difference, axis=2) / 255.0
            
            # High similarity bonus (>0.9 similarity)
            high_similarity_mask = (color_similarity > 0.9).astype(np.float32)
            matching_score += self.match_bonus * np.sum(both_pixels_opaque.astype(np.float32) * high_similarity_mask)
            
            # Partial similarity bonus (<=0.9 similarity)
            partial_similarity_mask = (color_similarity <= 0.9).astype(np.float32)
            matching_score += self.match_bonus * np.sum(both_pixels_opaque.astype(np.float32) * partial_similarity_mask * color_similarity)
            
        # Penalty for mismatched opacity
        matching_score -= self.mismatch_penalty * np.sum(one_pixel_transparent)
        
        return matching_score
    
    def update_composite_image(self, composite_image, new_image, offset_x, offset_y, image_index):
        # Calculate bounding box for expanded composite
        bounding_box_x_min = min(0, offset_x)
        bounding_box_y_min = min(0, offset_y)
        bounding_box_x_max = max(composite_image.width, offset_x + new_image.width)
        bounding_box_y_max = max(composite_image.height, offset_y + new_image.height)
        
        expanded_composite_width = bounding_box_x_max - bounding_box_x_min
        expanded_composite_height = bounding_box_y_max - bounding_box_y_min
        
        # Create new expanded composite image
        expanded_composite_image = Image.new("RGBA", (expanded_composite_width, expanded_composite_height), (0, 0, 0, 0))
        
        # Paste existing composite at adjusted position
        composite_paste_offset = (-bounding_box_x_min, -bounding_box_y_min)
        expanded_composite_image.paste(composite_image, composite_paste_offset)
        
        # Paste new image at calculated position
        new_image_paste_offset = (offset_x - bounding_box_x_min, offset_y - bounding_box_y_min)
        expanded_composite_image.paste(new_image, new_image_paste_offset, new_image)
        
        # Update all existing image positions
        updated_image_positions = []
        for existing_position in self.positions:
            adjusted_position = existing_position.copy()
            adjusted_position["x"] += composite_paste_offset[0]
            adjusted_position["y"] += composite_paste_offset[1]
            updated_image_positions.append(adjusted_position)
            
        # Add new image position
        updated_image_positions.append({
            "filename": os.path.basename(self.image_files[image_index]),
            "x": new_image_paste_offset[0],
            "y": new_image_paste_offset[1],
            "width": new_image.width,
            "height": new_image.height,
        })
        
        print(f"Image {self.image_files[image_index]} placed at ({new_image_paste_offset[0]}, {new_image_paste_offset[1]})")
        return expanded_composite_image, updated_image_positions
    
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
    
    
    # Refinement and Fine-Tuning 
    
    def refine_composite(self):
        threading.Thread(target=self.refine_composite_thread).start()
    
    def refine_composite_thread(self):
        if not self.draggable_images:
            return
        placed_images = []
        unplaced_images = self.draggable_images.copy()
        first_image = unplaced_images.pop(0)
        placed_images.append(first_image)
        self.canvas.moveto(first_image.canvas_image_id, 100, 100)
        
        while unplaced_images:
            best_pair_score = float('-inf')
            best_attachment_image = None
            best_anchor_image = None
            best_attachment_position = None
            
            for anchor_image in placed_images:
                for candidate_image in unplaced_images:
                    attachment_position, attachment_score = self.search_attachment_position(
                        anchor_image, candidate_image, "right", "left", max_radius=30, step=2
                    )
                    if attachment_score > best_pair_score:
                        best_pair_score = attachment_score
                        best_attachment_image = candidate_image
                        best_anchor_image = anchor_image
                        best_attachment_position = attachment_position
                        
            if best_attachment_image is None:
                fallback_candidate = unplaced_images.pop(0)
                last_placed_anchor = placed_images[-1]
                anchor_x_position, anchor_y_position = last_placed_anchor.get_position()
                best_attachment_position = (anchor_x_position + last_placed_anchor.image.width + 10, anchor_y_position)
                self.canvas.moveto(fallback_candidate.canvas_image_id, best_attachment_position[0], best_attachment_position[1])
                placed_images.append(fallback_candidate)
            else:
                self.canvas.moveto(best_attachment_image.canvas_image_id, best_attachment_position[0], best_attachment_position[1])
                placed_images.append(best_attachment_image)
                unplaced_images.remove(best_attachment_image)
                self.merge_groups(best_attachment_image, best_anchor_image.group)
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
        self.canvas.move(self.selected_image.canvas_image_id, best_dx, best_dy)
        self.update_scores()
        self.update_score_display()
        self.update_debug_overlay()
    
    def check_overlap(self, test_x_position, test_y_position, test_width, test_height, exclude=[]):
        test_rectangle = (test_x_position, test_y_position, test_x_position + test_width, test_y_position + test_height)
        
        for draggable_image in self.draggable_images:
            if draggable_image in exclude:
                continue
                
            image_x_position, image_y_position = draggable_image.get_position()
            image_rectangle = (
                image_x_position, image_y_position, 
                image_x_position + draggable_image.image.width, 
                image_y_position + draggable_image.image.height
            )
            
            if self.rectangles_overlap(test_rectangle, image_rectangle):
                return True
                
        return False
    
    def rectangles_overlap(self, rectangle_1, rectangle_2):
        rect1_left, rect1_top, rect1_right, rect1_bottom = rectangle_1
        rect2_left, rect2_top, rect2_right, rect2_bottom = rectangle_2
        
        # Rectangles don't overlap if one is completely to the side of the other
        no_overlap = (
            rect1_right <= rect2_left or 
            rect2_right <= rect1_left or 
            rect1_bottom <= rect2_top or 
            rect2_bottom <= rect1_top
        )
        
        return not no_overlap
    
    def move_group(self, group_name, delta_x, delta_y):
        for draggable_image in self.draggable_images:
            if draggable_image.group == group_name:
                self.canvas.move(draggable_image.canvas_image_id, delta_x, delta_y)
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
            self.selected_image.overlap_score = 0
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
            self.selected_image.overlap_score = score
        self.score_label.config(text=f"Selected Piece Score: {self.selected_image.overlap_score}")
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
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Create transparent overlay image
        debug_overlay_image = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(debug_overlay_image, "RGBA")
        
        # Draw unique colored border for each image (40% opacity)
        for draggable_image in self.draggable_images:
            image_x_position, image_y_position = draggable_image.get_position()
            image_width = draggable_image.image.width
            image_height = draggable_image.image.height
            
            # Parse hex color to RGB
            border_color_hex = draggable_image.debug_border_color
            red_value = int(border_color_hex[1:3], 16)
            green_value = int(border_color_hex[3:5], 16)
            blue_value = int(border_color_hex[5:7], 16)
            border_color_rgba = (red_value, green_value, blue_value, int(0.4 * 255))
            
            overlay_draw.rectangle(
                [image_x_position, image_y_position, 
                 image_x_position + image_width, image_y_position + image_height], 
                outline=border_color_rgba
            )
            
        # Fill overlapping regions with pink (40% opacity)
        overlap_fill_color = (255, 0, 255, int(0.4 * 255))
        total_images = len(self.draggable_images)
        
        for first_image_index in range(total_images):
            for second_image_index in range(first_image_index + 1, total_images):
                first_image = self.draggable_images[first_image_index]
                second_image = self.draggable_images[second_image_index]
                
                first_x, first_y = first_image.get_position()
                first_width, first_height = first_image.image.width, first_image.image.height
                
                second_x, second_y = second_image.get_position()
                second_width, second_height = second_image.image.width, second_image.image.height
                
                # Calculate overlap region
                overlap_region_left = max(first_x, second_x)
                overlap_region_top = max(first_y, second_y)
                overlap_region_right = min(first_x + first_width, second_x + second_width)
                overlap_region_bottom = min(first_y + first_height, second_y + second_height)
                
                # Draw overlap if it exists
                if overlap_region_right > overlap_region_left and overlap_region_bottom > overlap_region_top:
                    overlay_draw.rectangle(
                        [overlap_region_left, overlap_region_top, overlap_region_right, overlap_region_bottom], 
                        fill=overlap_fill_color
                    )
                    
        self.debug_overlay_image = ImageTk.PhotoImage(debug_overlay_image)
        self.canvas.create_image(0, 0, image=self.debug_overlay_image, anchor="nw", tags="debug_overlay")
    
    def update_score_display(self):
        self.canvas.delete("score_text")
        if self.selected_image:
            selected_x_position, selected_y_position = self.selected_image.get_position()
            score_display_text = f"Score: {self.selected_image.overlap_score}"
            self.selected_image.score_text_id = self.canvas.create_text(
                selected_x_position + self.selected_image.image.width // 2, 
                selected_y_position - 10, 
                text=score_display_text, fill="white", tags="score_text"
            )
    
    def select_image(self, img):
        self.selected_image = img
        self.update_scores()
        self.update_score_display()
        self.update_debug_overlay()
    
    def move_selected_left(self, event):
        if self.selected_image:
            self.canvas.move(self.selected_image.canvas_image_id, -1, 0)
            self.update_scores()
            self.update_score_display()
            self.update_debug_overlay()
    
    def move_selected_right(self, event):
        if self.selected_image:
            self.canvas.move(self.selected_image.canvas_image_id, 1, 0)
            self.update_scores()
            self.update_score_display()
            self.update_debug_overlay()
    
    def move_selected_up(self, event):
        if self.selected_image:
            self.canvas.move(self.selected_image.canvas_image_id, 0, -1)
            self.update_scores()
            self.update_score_display()
            self.update_debug_overlay()
    
    def move_selected_down(self, event):
        if self.selected_image:
            self.canvas.move(self.selected_image.canvas_image_id, 0, 1)
            self.update_scores()
            self.update_score_display()
            self.update_debug_overlay()
    
    
    # Saving and Disassembly
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

# Create the application window and run the CombinedComposerApp.
def main():
    root = tk.Tk()
    app = CombinedComposerApp(root)
    app.run()

if __name__ == "__main__":
    main()
