# IMAGE COMPOSITOR - assembles image pieces into fitting composite 
# some art in ultima is sliced into pieces like trees , the pieces may overlap or be adjacent , and each piece may have different size and offset 
# this program attempts to find the best fit given a set of images using brute force pixel comparison scoring 
# manual adjustments can be done by clicking on a piece and moving , note the score above to find the perfect fit 
# the composite image is then saved along with a json of the arrangement and pieces 
# this json is used to later disassemble a composite into its original pieces 
# enabling easier alters modifying the composite  
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import numpy as np
import os
import threading
import json

class DraggableImage:
    def __init__(self, app, canvas, image, x, y, filename):
        self.app = app  # Reference to the main application
        self.canvas = canvas
        self.image = image
        self.filename = filename
        self.image_tk = ImageTk.PhotoImage(self.image)
        self.id = self.canvas.create_image(x, y, image=self.image_tk, anchor='nw', tags='draggable')
        self.canvas.tag_bind(self.id, '<ButtonPress-1>', self.on_press)
        self.canvas.tag_bind(self.id, '<ButtonRelease-1>', self.on_release)
        self.canvas.tag_bind(self.id, '<B1-Motion>', self.on_motion)
        self.offset_x = 0
        self.offset_y = 0
        self.group = None  # Assigned during image loading
        self.score = 0     # Score for this image
        self.text_id = None  # ID for the score text

    def on_press(self, event):
        self.offset_x = event.x
        self.offset_y = event.y
        # Select this image
        self.app.select_image(self)
        self.app.canvas.focus_set()  # Set focus to the canvas to receive key events

    def on_release(self, event):
        if self.app.use_edge_scoring.get():
            self.snap_to_nearest_edge()
        self.app.update_scores()

    def on_motion(self, event):
        dx = event.x - self.offset_x
        dy = event.y - self.offset_y
        # Move group if image is part of one
        if self.group:
            self.app.move_group(self.group, dx, dy)
        else:
            self.canvas.move(self.id, dx, dy)
        self.offset_x = event.x
        self.offset_y = event.y
        self.app.update_score_display()

    def get_position(self):
        coords = self.canvas.coords(self.id)
        x = int(coords[0])
        y = int(coords[1])
        return x, y

    def snap_to_nearest_edge(self):
        current_x, current_y = self.get_position()
        current_width, current_height = self.image.width, self.image.height

        # Get other images
        other_images = [img for img in self.app.draggable_images if img != self]

        best_score = float('-inf')
        best_position = (current_x, current_y)
        best_group = None
        edge_score_threshold = 80  # Adjusted threshold for better snapping
        snap_distance_threshold = 50  # Reduced proximity threshold for snapping

        for other_img in other_images:
            other_x, other_y = other_img.get_position()
            other_width, other_height = other_img.image.width, other_img.image.height

            # Calculate distance between images
            distance = np.hypot(current_x - other_x, current_y - other_y)
            if distance > snap_distance_threshold:
                continue  # Skip if not within snapping distance

            # Possible positions to snap: left, right, top, bottom
            positions = [
                # Snap current image to the right of other image
                (other_x + other_width, other_y, 'left'),
                # Snap current image to the left of other image
                (other_x - current_width, other_y, 'right'),
                # Snap current image to the bottom of other image
                (other_x, other_y + other_height, 'top'),
                # Snap current image to the top of other image
                (other_x, other_y - current_height, 'bottom')
            ]

            for x, y, position in positions:
                # Check for overlap with other images
                if self.app.check_overlap(x, y, current_width, current_height, exclude=[self, other_img]):
                    continue  # Skip positions that cause overlap

                # Calculate edge score
                score = self.app.calculate_edge_score_single(self.image, x, y,
                                                             other_img.image, other_x, other_y, position)
                if score > best_score:
                    best_score = score
                    best_position = (x, y)
                    best_group = other_img.group

        # Move the image to the best position if it exceeds the threshold
        if best_score >= edge_score_threshold:
            dx = best_position[0] - current_x
            dy = best_position[1] - current_y
            self.canvas.move(self.id, dx, dy)
            # Merge groups if necessary
            if best_group:
                self.app.merge_groups(self, best_group)
            self.app.update_scores()
            self.app.update_score_display()
        else:
            # No suitable position found; keep current position
            pass

class ImageComposerApp:
    def __init__(self, master):
        master.title("Image Composer - Interactive Arrangement")

        # Set dark mode colors
        self.bg_color = '#1e1e1e'  # Dark grey background
        self.fg_color = '#ffffff'  # White foreground (text)
        self.button_color = '#2d2d2d'  # Darker grey for buttons
        self.highlight_color = '#3e3e3e'  # Highlight color

        # Configure the root window
        master.configure(bg=self.bg_color)

        # Variables
        self.master = master
        self.image_files = []
        self.images = []
        self.draggable_images = []
        self.selected_image = None
        self.groups = {}  # Dictionary to hold images per group
        self.scores = {}  # Dictionary to hold scores per group

        # Scoring options
        self.use_overlap_scoring = tk.BooleanVar(value=True)
        self.use_edge_scoring = tk.BooleanVar(value=True)

        self.group_counter = 1  # Initialize group counter

        # UI Elements
        self.create_widgets()

    def create_widgets(self):
        # Composition Frame
        composition_frame = tk.Frame(self.master, bg=self.bg_color)
        composition_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Control Panel
        control_panel = tk.Frame(composition_frame, bg=self.bg_color)
        control_panel.pack(side="left", fill="y", padx=5)

        # Canvas for images
        self.canvas = tk.Canvas(composition_frame, width=800, height=600, bg=self.highlight_color)
        self.canvas.pack(side="right", expand=True, fill="both")

        # Bind key events for moving selected image
        self.canvas.bind('<Left>', self.move_selected_left)
        self.canvas.bind('<Right>', self.move_selected_right)
        self.canvas.bind('<Up>', self.move_selected_up)
        self.canvas.bind('<Down>', self.move_selected_down)

        # Buttons and Controls
        select_button = tk.Button(control_panel, text="Select Images", command=self.select_images,
                                  bg=self.button_color, fg=self.fg_color, activebackground=self.highlight_color)
        select_button.pack(pady=5)

        load_comp_button = tk.Button(control_panel, text="Load Composition", command=self.load_composition,
                                     bg=self.button_color, fg=self.fg_color, activebackground=self.highlight_color)
        load_comp_button.pack(pady=5)

        refine_button = tk.Button(control_panel, text="Refine Composite", command=self.refine_composite,
                                  bg=self.button_color, fg=self.fg_color, activebackground=self.highlight_color)
        refine_button.pack(pady=5)

        fine_tune_button = tk.Button(control_panel, text="Fine-Tune Position", command=self.fine_tune_position,
                                     bg=self.button_color, fg=self.fg_color, activebackground=self.highlight_color)
        fine_tune_button.pack(pady=5)

        save_button = tk.Button(control_panel, text="Save Composites", command=self.save_composites,
                                bg=self.button_color, fg=self.fg_color, activebackground=self.highlight_color)
        save_button.pack(pady=5)

        disassemble_button = tk.Button(control_panel, text="Disassemble", command=self.disassemble,
                                       bg=self.button_color, fg=self.fg_color, activebackground=self.highlight_color)
        disassemble_button.pack(pady=5)

        # Scoring Options
        scoring_frame = tk.LabelFrame(control_panel, text="Scoring Options", bg=self.bg_color, fg=self.fg_color)
        scoring_frame.pack(pady=5, fill="x")
        overlap_checkbox = tk.Checkbutton(scoring_frame, text="Use Overlap Scoring",
                                          variable=self.use_overlap_scoring, bg=self.bg_color, fg=self.fg_color,
                                          selectcolor=self.button_color, activebackground=self.highlight_color)
        overlap_checkbox.pack(anchor='w')
        edge_checkbox = tk.Checkbutton(scoring_frame, text="Use Edge Scoring",
                                       variable=self.use_edge_scoring, bg=self.bg_color, fg=self.fg_color,
                                       selectcolor=self.button_color, activebackground=self.highlight_color)
        edge_checkbox.pack(anchor='w')

        # Scoring Information
        self.score_label = tk.Label(control_panel, text="Selected Piece Score: N/A", bg=self.bg_color, fg=self.fg_color)
        self.score_label.pack(pady=5)
        self.group_score_label = tk.Label(control_panel, text="Selected Group Score: N/A", bg=self.bg_color, fg=self.fg_color)
        self.group_score_label.pack(pady=5)

        # Group Display
        self.group_display = tk.Text(control_panel, height=10, bg=self.bg_color, fg=self.fg_color)
        self.group_display.pack(pady=5)

    def select_images(self):
        files = filedialog.askopenfilenames(title="Select Image Files", filetypes=[("PNG Images", "*.png")])
        if files:
            self.image_files = list(files)
            self.images = [Image.open(f).convert('RGBA') for f in self.image_files]
            self.load_images()

    def load_images(self):
        self.canvas.delete("all")
        self.draggable_images = []
        self.groups = {}  # Reset groups
        x, y = 50, 50

        if self.use_edge_scoring.get() and not self.use_overlap_scoring.get():
            # Automatically arrange images based on edge scoring
            unplaced_images = []
            for img, filename in zip(self.images, self.image_files):
                draggable_image = DraggableImage(self, self.canvas, img, x, y, os.path.basename(filename))
                draggable_image.group = f'Group{self.group_counter}'
                self.group_counter += 1
                unplaced_images.append(draggable_image)

            # Start with the first image
            base_image = unplaced_images.pop(0)
            self.draggable_images.append(base_image)
            self.canvas.moveto(base_image.id, x, y)

            # Arrange remaining images
            while unplaced_images:
                best_score = float('-inf')
                best_position = None
                best_image = None
                best_ref_image = None
                best_position_name = ''

                for img in unplaced_images:
                    for ref_img in self.draggable_images:
                        positions = ['left', 'right', 'top', 'bottom']
                        for position in positions:
                            x_pos, y_pos = self.get_position_adjacent(ref_img, img, position)
                            # Check for overlap
                            if self.check_overlap(x_pos, y_pos, img.image.width, img.image.height, exclude=[img]):
                                continue
                            # Calculate edge score
                            score = self.calculate_edge_score_single(
                                img.image, x_pos, y_pos, ref_img.image, *ref_img.get_position(), position)
                            if score > best_score:
                                best_score = score
                                best_position = (x_pos, y_pos)
                                best_image = img
                                best_ref_image = ref_img
                                best_position_name = position

                if best_image and best_score > 0:
                    self.draggable_images.append(best_image)
                    unplaced_images.remove(best_image)
                    self.canvas.moveto(best_image.id, best_position[0], best_position[1])
                    # Merge groups
                    self.merge_groups(best_image, best_ref_image.group)
                else:
                    # No good match found, place randomly
                    img = unplaced_images.pop(0)
                    self.draggable_images.append(img)
                    self.canvas.moveto(img.id, x + np.random.randint(50, 300), y + np.random.randint(50, 300))
        else:
            # Place images without automatic arrangement
            group_name = f'Group{self.group_counter}'
            self.group_counter += 1
            for img, filename in zip(self.images, self.image_files):
                draggable_image = DraggableImage(self, self.canvas, img, x, y, os.path.basename(filename))
                draggable_image.group = group_name  # Assign to default group
                self.draggable_images.append(draggable_image)
                x += img.width + 10  # Offset for next image

        self.update_group_display()

    def load_composition(self):
        json_path = filedialog.askopenfilename(title="Select Composition JSON", filetypes=[("JSON Files", "*.json")])
        if not json_path:
            return
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            print(f"JSON data loaded from {json_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON file: {e}")
            return

        # Clear current canvas
        self.canvas.delete("all")
        self.draggable_images = []
        self.groups = {}

        # Load images and positions
        images_info = data.get('images', [])
        group_name = data.get('group_name', f'Group{self.group_counter}')  # Get group_name from JSON
        self.group_counter += 1  # Increment group_counter

        composition_size = data.get('composite_size', (800, 600))
        min_x, min_y = 50, 50  # Starting offset

        json_dir = os.path.dirname(json_path)

        for img_info in images_info:
            filename = img_info['filename']
            x = img_info['x'] + min_x
            y = img_info['y'] + min_y
            width = img_info['width']
            height = img_info['height']

            image_path = os.path.join(json_dir, filename)
            if not os.path.exists(image_path):
                messagebox.showerror("Error", f"Image file {filename} not found in the JSON directory.")
                continue
            try:
                img = Image.open(image_path).convert('RGBA')
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open image {filename}: {e}")
                continue

            draggable_image = DraggableImage(self, self.canvas, img, x, y, filename)
            draggable_image.group = group_name  # Assign the group_name from JSON
            self.draggable_images.append(draggable_image)

        self.update_group_display()

    def refine_composite(self):
        threading.Thread(target=self.refine_composite_thread).start()

    def refine_composite_thread(self):
        # Start with the leftmost piece
        sorted_images = sorted(self.draggable_images, key=lambda img: img.get_position()[0])
        if not sorted_images:
            return

        fixed_images = [sorted_images[0]]  # Keep the leftmost piece fixed
        for idx in range(1, len(sorted_images)):
            target_image = sorted_images[idx]
            prev_image = fixed_images[-1]
            best_score = float('-inf')
            best_dx = 0
            best_dy = 0
            max_offset = 10  # Maximum offset range

            # Get positions
            prev_x, prev_y = prev_image.get_position()
            prev_w, prev_h = prev_image.image.width, prev_image.image.height

            # The x-position is fixed: adjacent to the right edge of prev_image
            x_fixed = prev_x + prev_w

            # Get current y-position of target image
            y0 = target_image.get_position()[1]

            # Generate y-offsets within range
            y_offsets = range(-max_offset, max_offset + 1)

            for dy in y_offsets:
                y = y0 + dy

                # Check for overlap with fixed images
                if self.check_overlap(x_fixed, y, target_image.image.width, target_image.image.height, exclude=[target_image]):
                    continue  # Skip positions that cause overlap

                score = 0
                if self.use_edge_scoring.get():
                    score += self.calculate_edge_score_pair(prev_image, prev_x, prev_y, target_image, x_fixed, y, 'right', 'left')

                if score > best_score:
                    best_score = score
                    best_dx = x_fixed - target_image.get_position()[0]
                    best_dy = y - target_image.get_position()[1]

            # Move image to best position
            self.canvas.move(target_image.id, best_dx, best_dy)
            fixed_images.append(target_image)

            # Merge groups
            self.merge_groups(target_image, prev_image.group)

            # Update group assignments if necessary
            self.update_scores()
            self.update_score_display()

        # After refinement, update group scores
        self.update_group_scores()

    def calculate_edge_score_pair(self, img1, x1, y1, img2, x2, y2, edge1, edge2):
        img1_np = np.array(img1.image)
        img2_np = np.array(img2.image)

        # Extract edges
        img1_edge = self.extract_edge(img1_np, edge1)
        img2_edge = self.extract_edge(img2_np, edge2)

        if edge1 in ['left', 'right']:
            # Edges are vertical lines
            # Compute overlapping y-range
            y_start1 = y1
            y_end1 = y1 + img1.image.height
            y_start2 = y2
            y_end2 = y2 + img2.image.height

            y_overlap_start = max(y_start1, y_start2)
            y_overlap_end = min(y_end1, y_end2)

            if y_overlap_start >= y_overlap_end:
                return 0  # No overlap

            idx_start1 = int(y_overlap_start - y_start1)
            idx_end1 = int(y_overlap_end - y_start1)
            idx_start2 = int(y_overlap_start - y_start2)
            idx_end2 = int(y_overlap_end - y_start2)

            img1_edge_segment = img1_edge[idx_start1:idx_end1]
            img2_edge_segment = img2_edge[idx_start2:idx_end2]

        else:
            # Edges are horizontal lines
            # Compute overlapping x-range
            x_start1 = x1
            x_end1 = x1 + img1.image.width
            x_start2 = x2
            x_end2 = x2 + img2.image.width

            x_overlap_start = max(x_start1, x_start2)
            x_overlap_end = min(x_end1, x_end2)

            if x_overlap_start >= x_overlap_end:
                return 0  # No overlap

            idx_start1 = int(x_overlap_start - x_start1)
            idx_end1 = int(x_overlap_end - x_start1)
            idx_start2 = int(x_overlap_start - x_start2)
            idx_end2 = int(x_overlap_end - x_start2)

            img1_edge_segment = img1_edge[idx_start1:idx_end1]
            img2_edge_segment = img2_edge[idx_start2:idx_end2]

        return self.score_edge_arrays(img1_edge_segment, img2_edge_segment)

    def score_edge_arrays(self, edge1, edge2):
        # edge1 and edge2 are numpy arrays of shape (N, 4)
        if len(edge1) == 0 or len(edge2) == 0:
            return 0

        edge1_R = edge1[..., 0]
        edge1_G = edge1[..., 1]
        edge1_B = edge1[..., 2]
        edge1_A = edge1[..., 3]

        edge2_R = edge2[..., 0]
        edge2_G = edge2[..., 1]
        edge2_B = edge2[..., 2]
        edge2_A = edge2[..., 3]

        # Masks
        edge1_opaque = edge1_A > 0
        edge2_opaque = edge2_A > 0
        both_opaque = edge1_opaque & edge2_opaque
        rgb_match = (edge1_R == edge2_R) & (edge1_G == edge2_G) & (edge1_B == edge2_B)

        score = np.sum(both_opaque & rgb_match)
        return score

    def get_position_adjacent(self, ref_img, target_img, position):
        ref_x, ref_y = ref_img.get_position()
        ref_w, ref_h = ref_img.image.width, ref_img.image.height
        tgt_w, tgt_h = target_img.image.width, target_img.image.height

        if position == 'left':
            return (ref_x - tgt_w, ref_y)
        elif position == 'right':
            return (ref_x + ref_w, ref_y)
        elif position == 'top':
            return (ref_x, ref_y - tgt_h)
        elif position == 'bottom':
            return (ref_x, ref_y + ref_h)
        else:
            return (ref_x, ref_y)

    def select_image(self, draggable_image):
        self.selected_image = draggable_image
        self.update_scores()
        self.update_score_display()

    def move_selected_left(self, event):
        if self.selected_image:
            self.canvas.move(self.selected_image.id, -1, 0)
            self.update_scores()
            self.update_score_display()

    def move_selected_right(self, event):
        if self.selected_image:
            self.canvas.move(self.selected_image.id, 1, 0)
            self.update_scores()
            self.update_score_display()

    def move_selected_up(self, event):
        if self.selected_image:
            self.canvas.move(self.selected_image.id, 0, -1)
            self.update_scores()
            self.update_score_display()

    def move_selected_down(self, event):
        if self.selected_image:
            self.canvas.move(self.selected_image.id, 0, 1)
            self.update_scores()
            self.update_score_display()

    def update_score_display(self):
        # Remove existing score texts
        self.canvas.delete('score_text')
        if self.selected_image:
            x, y = self.selected_image.get_position()
            score_text = f"Score: {self.selected_image.score}"
            self.selected_image.text_id = self.canvas.create_text(
                x + self.selected_image.image.width // 2, y - 10,
                text=score_text, fill='white', tags='score_text')

    def fine_tune_position(self):
        if self.selected_image is None:
            messagebox.showinfo("Info", "Please select an image slice to fine-tune.")
            return
        threading.Thread(target=self.fine_tune_selected_image).start()

    def fine_tune_selected_image(self):
        # Determine scoring methods
        use_overlap = self.use_overlap_scoring.get()
        use_edge = self.use_edge_scoring.get()

        if not use_overlap and not use_edge:
            messagebox.showinfo("Info", "Please select at least one scoring method.")
            return

        # Search nearby offsets to find a better position
        max_offset = 5
        best_score = float('-inf')
        best_dx = 0
        best_dy = 0
        img_idx = self.draggable_images.index(self.selected_image)
        target_image = self.selected_image.image

        # Create a composite image of all other images
        other_images = [img for idx, img in enumerate(self.draggable_images) if idx != img_idx]
        if not other_images:
            messagebox.showinfo("Info", "No other images to compare with.")
            return

        composite_img, positions = self.create_composite(other_images)
        composite_np = np.array(composite_img)

        # Get current position
        x0, y0 = self.selected_image.get_position()
        target_np = np.array(target_image)

        # Generate offsets
        offsets = [(dx, dy) for dx in range(-max_offset, max_offset + 1) for dy in range(-max_offset, max_offset + 1)]

        for dx, dy in offsets:
            x = x0 + dx
            y = y0 + dy

            # Check for overlap with other images
            if self.check_overlap(x, y, target_image.width, target_image.height, exclude=[self.selected_image]):
                continue  # Skip positions that cause overlap

            score = 0
            if use_overlap:
                score += self.calculate_overlap_score(composite_np, target_np, x - positions[0][1], y - positions[0][2])
            if use_edge:
                score += self.calculate_edge_score(composite_np, target_np, x - positions[0][1], y - positions[0][2])
            if score > best_score:
                best_score = score
                best_dx = dx
                best_dy = dy

        # Move image to best position
        self.canvas.move(self.selected_image.id, best_dx, best_dy)
        self.update_scores()
        self.update_score_display()

    def check_overlap(self, x, y, width, height, exclude=[]):
        # Check if the rectangle at (x, y, width, height) overlaps with any other images
        rect1 = (x, y, x + width, y + height)
        for img in self.draggable_images:
            if img in exclude:
                continue
            img_x, img_y = img.get_position()
            img_rect = (img_x, img_y, img_x + img.image.width, img_y + img.image.height)
            if self.rectangles_overlap(rect1, img_rect):
                return True
        return False

    def rectangles_overlap(self, rect1, rect2):
        # Check if two rectangles overlap
        left1, top1, right1, bottom1 = rect1
        left2, top2, right2, bottom2 = rect2
        return not (right1 <= left2 or right2 <= left1 or bottom1 <= top2 or bottom2 <= top1)

    def move_group(self, group_name, dx, dy):
        # Move all images in the group
        for img in self.draggable_images:
            if img.group == group_name:
                self.canvas.move(img.id, dx, dy)
        self.update_score_display()

    def merge_groups(self, img, other_group_name):
        # Merge the group of img with other_group_name
        old_group_name = img.group
        if old_group_name == other_group_name:
            return  # Already in the same group
        # Update group name for all images in old group
        for i in self.draggable_images:
            if i.group == old_group_name:
                i.group = other_group_name
        self.update_group_display()

    def calculate_edge_score(self, composite_np, target_np, x_offset, y_offset):
        composite_h, composite_w = composite_np.shape[:2]
        target_h, target_w = target_np.shape[:2]

        positions = ['left', 'right', 'top', 'bottom']
        best_edge_score = 0

        for position in positions:
            score = self.score_edge_position(composite_np, target_np, x_offset, y_offset, position)
            if score > best_edge_score:
                best_edge_score = score

        return best_edge_score

    def score_edge_position(self, composite_np, target_np, x_offset, y_offset, position):
        # Extract edges based on position
        composite_edge = self.extract_edge_at_position(composite_np, x_offset, y_offset, target_np.shape[1], target_np.shape[0], position)
        target_edge = self.extract_edge(target_np, position, invert=False)

        if composite_edge is None or target_edge is None:
            return 0

        # Compare edges
        min_length = min(len(composite_edge), len(target_edge))
        if min_length == 0:
            return 0

        composite_edge = composite_edge[:min_length]
        target_edge = target_edge[:min_length]

        composite_R = composite_edge[..., 0]
        composite_G = composite_edge[..., 1]
        composite_B = composite_edge[..., 2]
        composite_A = composite_edge[..., 3]

        target_R = target_edge[..., 0]
        target_G = target_edge[..., 1]
        target_B = target_edge[..., 2]
        target_A = target_edge[..., 3]

        # Masks
        composite_opaque = composite_A > 0
        target_opaque = target_A > 0
        both_opaque = composite_opaque & target_opaque
        rgb_match = (composite_R == target_R) & (composite_G == target_G) & (composite_B == target_B)

        score = np.sum(both_opaque & rgb_match)
        return score

    def extract_edge_at_position(self, composite_np, x_offset, y_offset, target_w, target_h, position):
        composite_h, composite_w = composite_np.shape[:2]

        if position == 'left':
            x = x_offset - 1
            if x < 0 or x >= composite_w:
                return None
            y_start = max(0, y_offset)
            y_end = min(composite_h, y_offset + target_h)
            return composite_np[y_start:y_end, x, :]
        elif position == 'right':
            x = x_offset + target_w
            if x < 0 or x >= composite_w:
                return None
            y_start = max(0, y_offset)
            y_end = min(composite_h, y_offset + target_h)
            return composite_np[y_start:y_end, x, :]
        elif position == 'top':
            y = y_offset - 1
            if y < 0 or y >= composite_h:
                return None
            x_start = max(0, x_offset)
            x_end = min(composite_w, x_offset + target_w)
            return composite_np[y, x_start:x_end, :]
        elif position == 'bottom':
            y = y_offset + target_h
            if y < 0 or y >= composite_h:
                return None
            x_start = max(0, x_offset)
            x_end = min(composite_w, x_offset + target_w)
            return composite_np[y, x_start:x_end, :]
        else:
            return None

    def calculate_edge_score_single(self, img1, x1, y1, img2, x2, y2, position):
        img1_np = np.array(img1)
        img2_np = np.array(img2)

        # Extract edges
        img1_edge = self.extract_edge(img1_np, position)
        opposite_position = {'left': 'right', 'right': 'left', 'top': 'bottom', 'bottom': 'top'}[position]
        img2_edge = self.extract_edge(img2_np, opposite_position)

        if img1_edge is None or img2_edge is None:
            return 0

        # Compare edges
        min_length = min(len(img1_edge), len(img2_edge))
        if min_length == 0:
            return 0

        img1_edge = img1_edge[:min_length]
        img2_edge = img2_edge[:min_length]

        img1_R = img1_edge[..., 0]
        img1_G = img1_edge[..., 1]
        img1_B = img1_edge[..., 2]
        img1_A = img1_edge[..., 3]

        img2_R = img2_edge[..., 0]
        img2_G = img2_edge[..., 1]
        img2_B = img2_edge[..., 2]
        img2_A = img2_edge[..., 3]

        # Masks
        img1_opaque = img1_A > 0
        img2_opaque = img2_A > 0
        both_opaque = img1_opaque & img2_opaque
        rgb_match = (img1_R == img2_R) & (img1_G == img2_G) & (img1_B == img2_B)

        score = np.sum(both_opaque & rgb_match)
        return score

    def extract_edge(self, img_np, position, invert=False):
        if position == 'left':
            return img_np[:, 0, :] if not invert else img_np[:, -1, :]
        elif position == 'right':
            return img_np[:, -1, :] if not invert else img_np[:, 0, :]
        elif position == 'top':
            return img_np[0, :, :] if not invert else img_np[-1, :, :]
        elif position == 'bottom':
            return img_np[-1, :, :] if not invert else img_np[0, :, :]
        else:
            return None

    def create_composite(self, draggable_images):
        # Create a composite image from the given draggable images
        positions = []
        x_coords = []
        y_coords = []
        for img in draggable_images:
            x, y = img.get_position()
            x_coords.extend([x, x + img.image.width])
            y_coords.extend([y, y + img.image.height])
            positions.append((img, x, y))

        min_x = min(x_coords)
        min_y = min(y_coords)
        max_x = max(x_coords)
        max_y = max(y_coords)

        width = max_x - min_x
        height = max_y - min_y

        composite_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        for img, x, y in positions:
            composite_img.paste(img.image, (x - min_x, y - min_y), img.image)

        return composite_img, positions

    def update_scores(self):
        # Update scores for the selected image and group
        if self.selected_image is None:
            self.score_label.config(text="Selected Piece Score: N/A")
            self.group_score_label.config(text="Selected Group Score: N/A")
            return

        # Determine scoring methods
        use_overlap = self.use_overlap_scoring.get()
        use_edge = self.use_edge_scoring.get()

        # Calculate score for selected image
        img_idx = self.draggable_images.index(self.selected_image)
        target_image = self.selected_image.image
        other_images = [img for idx, img in enumerate(self.draggable_images) if idx != img_idx]

        if not other_images:
            self.selected_image.score = 0
        else:
            composite_img, positions = self.create_composite(other_images)
            composite_np = np.array(composite_img)
            x0, y0 = self.selected_image.get_position()
            target_np = np.array(target_image)
            score = 0
            if use_overlap:
                score += self.calculate_overlap_score(composite_np, target_np, x0 - positions[0][1], y0 - positions[0][2])
            if use_edge:
                score += self.calculate_edge_score(composite_np, target_np, x0 - positions[0][1], y0 - positions[0][2])
            self.selected_image.score = score

        self.score_label.config(text=f"Selected Piece Score: {self.selected_image.score}")

        # Update group score
        if self.selected_image.group:
            group_images = [img for img in self.draggable_images if img.group == self.selected_image.group]
            total_score = 0
            for img in group_images:
                img_idx = self.draggable_images.index(img)
                target_image = img.image
                other_images = [i for i in group_images if i != img]
                if not other_images:
                    continue
                composite_img_inner, positions_inner = self.create_composite(other_images)
                composite_np_inner = np.array(composite_img_inner)
                x0, y0 = img.get_position()
                target_np = np.array(target_image)
                score = 0
                if use_overlap:
                    score += self.calculate_overlap_score(composite_np_inner, target_np, x0 - positions_inner[0][1], y0 - positions_inner[0][2])
                if use_edge:
                    score += self.calculate_edge_score(composite_np_inner, target_np, x0 - positions_inner[0][1], y0 - positions_inner[0][2])
                total_score += score
            self.scores[self.selected_image.group] = total_score
            self.group_score_label.config(text=f"Selected Group Score: {total_score}")
        else:
            self.group_score_label.config(text="Selected Group Score: N/A")

    def calculate_overlap_score(self, composite_np, target_np, x_offset, y_offset):
        composite_h, composite_w = composite_np.shape[:2]
        target_h, target_w = target_np.shape[:2]

        x_start = max(0, x_offset)
        y_start = max(0, y_offset)
        x_end = min(composite_w, x_offset + target_w)
        y_end = min(composite_h, y_offset + target_h)

        tx_start = max(0, -x_offset)
        ty_start = max(0, -y_offset)
        tx_end = tx_start + (x_end - x_start)
        ty_end = ty_start + (y_end - y_start)

        if x_end <= x_start or y_end <= y_start:
            return float('-inf')

        composite_region = composite_np[y_start:y_end, x_start:x_end]
        target_region = target_np[ty_start:ty_end, tx_start:tx_end]

        return self.score_overlap_regions(composite_region, target_region)

    def score_overlap_regions(self, composite_region, target_region):
        # Similar scoring as before
        composite_R = composite_region[..., 0]
        composite_G = composite_region[..., 1]
        composite_B = composite_region[..., 2]
        composite_A = composite_region[..., 3]

        target_R = target_region[..., 0]
        target_G = target_region[..., 1]
        target_B = target_region[..., 2]
        target_A = target_region[..., 3]

        # Masks
        composite_opaque = composite_A > 0
        target_opaque = target_A > 0

        both_opaque = composite_opaque & target_opaque
        both_transparent = (~composite_opaque) & (~target_opaque)
        one_opaque = composite_opaque ^ target_opaque
        rgb_match = (composite_R == target_R) & (composite_G == target_G) & (composite_B == target_B)

        score = 0
        score += np.sum(both_opaque & rgb_match) * 3
        score += np.sum(both_opaque & (~rgb_match)) * (-1)
        score += np.sum(both_transparent) * 1
        score += np.sum(one_opaque) * (-2)

        return score

    def update_group_scores(self):
        # Recalculate total scores for all groups
        for group_name in self.groups:
            group_images = [img for img in self.draggable_images if img.group == group_name]
            total_score = 0
            for img in group_images:
                # Calculate score for each image in the group
                other_images = [i for i in group_images if i != img]
                if not other_images:
                    continue
                composite_img_inner, positions_inner = self.create_composite(other_images)
                composite_np_inner = np.array(composite_img_inner)
                x0, y0 = img.get_position()
                target_np = np.array(img.image)
                score = 0
                if self.use_overlap_scoring.get():
                    score += self.calculate_overlap_score(composite_np_inner, target_np, x0 - positions_inner[0][1], y0 - positions_inner[0][2])
                if self.use_edge_scoring.get():
                    score += self.calculate_edge_score(composite_np_inner, target_np, x0 - positions_inner[0][1], y0 - positions_inner[0][2])
                total_score += score
            self.scores[group_name] = total_score

    def update_group_display(self):
        # Update the group display text
        self.group_display.delete('1.0', tk.END)
        group_info = "Groups:\n"
        self.groups = {}
        for img in self.draggable_images:
            group = img.group if img.group else "Ungrouped"
            if group not in self.groups:
                self.groups[group] = []
            self.groups[group].append(img.filename)
        for group, filenames in self.groups.items():
            group_info += f"{group}:\n"
            for fname in filenames:
                group_info += f"  {fname}\n"
        self.group_display.insert(tk.END, group_info)

    def prompt_group_name(self):
        # Prompt the user to enter a group name
        group_name = simpledialog.askstring("Group Assignment", "Enter group name:")
        return group_name

    def save_composites(self):
        if not self.groups:
            messagebox.showinfo("Info", "No groups to save.")
            return
        save_dir = filedialog.askdirectory(title="Select Directory to Save Composites and JSONs")
        if not save_dir:
            return
        for group_name, image_filenames in self.groups.items():
            group_images = [img for img in self.draggable_images if img.group == group_name]
            if not group_images:
                continue
            composite_img, positions = self.create_composite(group_images)
            # Adjust positions relative to composite bounds
            min_x = min([img.get_position()[0] for img in group_images])
            min_y = min([img.get_position()[1] for img in group_images])
            image_positions = []
            for img in group_images:
                x, y = img.get_position()
                image_positions.append({
                    'filename': img.filename,
                    'x': x - min_x,
                    'y': y - min_y,
                    'width': img.image.width,
                    'height': img.image.height
                })
            composite_filename = os.path.join(save_dir, f"{group_name}_composite.png")
            composite_img.save(composite_filename)
            json_filename = os.path.join(save_dir, f"{group_name}_composite.json")
            data = {
                'group_name': group_name,  # Add group_name here
                'images': image_positions,
                'composite_size': composite_img.size
            }
            with open(json_filename, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"Composite image saved to {composite_filename}")
            print(f"JSON data saved to {json_filename}")
        # Removed messagebox at the end

    def disassemble(self):
        composite_path = filedialog.askopenfilename(title="Select Composite Image", filetypes=[("PNG Images", "*.png")])
        if not composite_path:
            return
        json_path = composite_path.replace('.png', '.json')
        if not os.path.exists(json_path):
            messagebox.showerror("Error", f"JSON file not found for {composite_path}.")
            return
        # Load composite image
        try:
            composite_image = Image.open(composite_path).convert('RGBA')
            print(f"Composite image loaded from {composite_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open composite image: {e}")
            return
        # Load JSON file
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            print(f"JSON data loaded from {json_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON file: {e}")
            return
        # Extract images
        output_dir = filedialog.askdirectory(title="Select Directory to Save Disassembled Images")
        if not output_dir:
            return
        print("Starting disassembly of composite image...")
        composition_size = data.get('composite_size', (5, 5))
        scaled_image = composite_image.resize(composition_size, Image.Resampling.BICUBIC)

        for img_info in data['images']:
            x = img_info['x']
            y = img_info['y']
            width = img_info['width']
            height = img_info['height']
            filename = img_info['filename']
            
            box = (x, y, x + width, y + height)
            
            cropped_image = scaled_image.crop(box)
            save_path = os.path.join(output_dir, filename)
            cropped_image.save(save_path)
            print(f"Extracted image saved to {save_path}")
        # Removed messagebox at the end

    def run(self):
        self.master.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageComposerApp(root)
    app.run()
