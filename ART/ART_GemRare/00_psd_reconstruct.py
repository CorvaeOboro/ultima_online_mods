import os
import json
import logging
import tkinter as tk
from tkinter import filedialog, messagebox
from psd_tools import PSDImage
from PIL import Image, ImageChops
import cv2
import numpy as np

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

def export_layers_and_generate_json(psd_file, exported_layers_dir, json_output_path, use_image_matching, subfolder_search_path, additional_search_path):
    # Load PSD
    logging.info(f"Loading PSD file: {psd_file}")
    psd = PSDImage.open(psd_file)

    # Get canvas size from PSD
    canvas_width = psd.width
    canvas_height = psd.height
    logging.info(f"Canvas size: width={canvas_width}, height={canvas_height}")

    # Directory where the PSD file is located
    psd_dir = os.path.dirname(os.path.abspath(psd_file))
    logging.debug(f"PSD directory: {psd_dir}")

    # Full path to the subfolder search path
    if subfolder_search_path:
        subfolder_path = os.path.normpath(os.path.join(psd_dir, subfolder_search_path))
    else:
        subfolder_path = None

    # Full path to the additional search path
    if additional_search_path:
        additional_path = os.path.normpath(os.path.abspath(additional_search_path))
    else:
        additional_path = None

    layer_data = []

    def process_layers(layers):
        for layer in layers:
            if not layer.visible:
                logging.debug(f"Skipping hidden layer: '{layer.name}'")
                continue  # Skip hidden layers
            if layer.is_group():
                logging.debug(f"Processing group layer: '{layer.name}'")
                process_layers(layer)  # Process child layers recursively
            else:
                # Get layer name
                layer_name = layer.name.strip()
                logging.info(f"Processing layer: '{layer_name}'")

                # Get layer bounds and position
                bbox = layer.bbox  # (left, top, right, bottom)
                left, top, right, bottom = bbox
                width = right - left
                height = bottom - top
                logging.debug(f"Layer bounds: left={left}, top={top}, right={right}, bottom={bottom}")

                # Export layer as PNG (for analysis)
                layer_image = layer.composite()
                if layer_image is None:
                    logging.warning(f"Skipping empty layer: '{layer_name}'")
                    continue  # Skip empty layers

                # Ensure unique filename
                safe_layer_name = layer_name.replace('/', '_').replace('\\', '_')
                layer_image_path = os.path.join(exported_layers_dir, f"{safe_layer_name}.png")
                logging.debug(f"Exporting layer image to: {layer_image_path}")
                layer_image.save(layer_image_path)

                # Try to find a file in the PSD directory, subfolder, or additional folder that matches layer_name
                possible_extensions = ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp']
                found = False
                external_file_path = None
                search_paths = [psd_dir]
                if subfolder_path and os.path.exists(subfolder_path):
                    search_paths.append(subfolder_path)
                    logging.debug(f"Subfolder search path added: {subfolder_path}")
                else:
                    logging.debug(f"Subfolder path does not exist or not specified: {subfolder_path}")

                if additional_path and os.path.exists(additional_path):
                    search_paths.append(additional_path)
                    logging.debug(f"Additional search path added: {additional_path}")
                else:
                    logging.debug(f"Additional search path does not exist or not specified: {additional_path}")

                # Normalize layer name for matching
                #normalized_layer_name = layer_name.strip().lower()
                normalized_layer_name = layer_name

                for search_path in search_paths:
                    logging.debug(f"Searching in directory: {search_path}")
                    for ext in possible_extensions:
                        candidate_file = f"{layer_name}{ext}"
                        candidate_path = os.path.normpath(os.path.join(search_path, candidate_file))
                        logging.debug(f"Checking if file exists: {candidate_path}")
                        if os.path.exists(candidate_path):
                            external_file_path = candidate_path
                            found = True
                            logging.info(f"Found matching external file: {external_file_path}")
                            break
                        else:
                            # Case-insensitive matching
                            for file in os.listdir(search_path):
                                #print(str(file.lower()))
                                if file.lower() == f"{normalized_layer_name}{ext}".lower():
                                    external_file_path = os.path.normpath(os.path.join(search_path, file))
                                    found = True
                                    logging.info(f"Found matching external file (case-insensitive): {external_file_path}")
                                    break
                            if found:
                                break
                    if found:
                        break
                if not found:
                    logging.warning(f"No matching external file found for layer: '{layer_name}'")

                # Perform image matching to find the alignment and update positions
                exported_layer_path = layer_image_path

                if external_file_path and use_image_matching:
                    # Load images
                    exported_img_cv = cv2.imread(exported_layer_path, cv2.IMREAD_UNCHANGED)
                    external_img_cv = cv2.imread(external_file_path, cv2.IMREAD_UNCHANGED)

                    if exported_img_cv is None:
                        logging.error(f"Failed to load exported layer image: {exported_layer_path}")
                        continue
                    if external_img_cv is None:
                        logging.error(f"Failed to load external image: {external_file_path}")
                        external_file_path = None  # Reset external_file_path since loading failed
                    else:
                        # Convert images to grayscale for template matching
                        try:
                            exported_gray = cv2.cvtColor(exported_img_cv, cv2.COLOR_BGRA2GRAY) if exported_img_cv.shape[2] == 4 else cv2.cvtColor(exported_img_cv, cv2.COLOR_BGR2GRAY)
                            external_gray = cv2.cvtColor(external_img_cv, cv2.COLOR_BGRA2GRAY) if external_img_cv.shape[2] == 4 else cv2.cvtColor(external_img_cv, cv2.COLOR_BGR2GRAY)
                        except Exception as e:
                            logging.error(f"Error converting images to grayscale: {e}")
                            external_file_path = None  # Reset external_file_path since processing failed

                        # Check if exported image is smaller than external image
                        if exported_gray.shape[0] > external_gray.shape[0] or exported_gray.shape[1] > external_gray.shape[1]:
                            # Cannot perform template matching
                            logging.warning(f"Exported image is larger than external image for layer: '{layer_name}'")
                            offset_x, offset_y = 0, 0
                        else:
                            # Perform template matching
                            logging.debug("Performing template matching")
                            result = cv2.matchTemplate(external_gray, exported_gray, cv2.TM_CCOEFF_NORMED)
                            _, max_val, _, max_loc = cv2.minMaxLoc(result)
                            offset_x, offset_y = max_loc
                            logging.debug(f"Template matching result: max_val={max_val}, max_loc={max_loc}")

                            # If the match is not good enough, consider the images do not match
                            if max_val < 0.8:
                                logging.warning(f"Low template matching confidence ({max_val}) for layer: '{layer_name}'")
                                external_file_path = None  # Reset external_file_path since match is poor

                        # Compute composite position
                        composite_left = left - offset_x
                        composite_top = top - offset_y
                        logging.info(f"Composite position for layer '{layer_name}': left={composite_left}, top={composite_top}")
                else:
                    # Use positions as is
                    composite_left = left
                    composite_top = top

                # Append layer data, regardless of whether external file was found
                layer_info = {
                    'name': layer_name,
                    'external_file_path': external_file_path,
                    'exported_layer_path': exported_layer_path,
                    'position': {
                        'composite_left': composite_left,
                        'composite_top': composite_top,
                        'width': width,
                        'height': height
                    }
                }

                layer_data.append(layer_info)

    # Start processing layers recursively
    process_layers(psd)

    if not layer_data:
        logging.error("No layers were processed. The composition data will be empty.")
    else:
        logging.info(f"Total layers processed: {len(layer_data)}")

    # Save layer data to JSON
    composition_data = {
        'canvas_width': canvas_width,
        'canvas_height': canvas_height,
        'layers': layer_data
    }
    logging.info(f"Saving composition data to JSON file: {json_output_path}")
    with open(json_output_path, 'w') as f:
        json.dump(composition_data, f, indent=4)

def reconstruct_composition(json_input_path, output_image_path):
    # Function remains unchanged
    logging.info(f"Loading composition data from JSON file: {json_input_path}")
    with open(json_input_path, 'r') as f:
        composition_data = json.load(f)

    canvas_width = composition_data['canvas_width']
    canvas_height = composition_data['canvas_height']
    logging.info(f"Canvas size for reconstruction: width={canvas_width}, height={canvas_height}")

    # Create a new image with black background
    final_composite = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 255))

    if not composition_data['layers']:
        logging.error("No layers found in composition data. The final composite will be empty.")
        return

    # Reconstruct the composition
    for layer_info in composition_data['layers']:
        layer_name = layer_info['name']
        composite_left = int(layer_info['position']['composite_left'])
        composite_top = int(layer_info['position']['composite_top'])
        external_file_path = layer_info['external_file_path']
        exported_layer_path = layer_info['exported_layer_path']

        logging.info(f"Adding layer '{layer_name}' to composite at position ({composite_left}, {composite_top})")

        if external_file_path and os.path.exists(external_file_path):
            image_path = external_file_path
        else:
            logging.warning(f"Using exported layer image for '{layer_name}' as external file is not found")
            image_path = exported_layer_path

        # Load the image
        try:
            layer_image = Image.open(image_path).convert('RGBA')
        except Exception as e:
            logging.error(f"Failed to open image '{image_path}': {e}")
            continue

        # Matte transparency on black
        if layer_image.mode == 'RGBA':
            background = Image.new('RGBA', layer_image.size, (0, 0, 0, 255))
            layer_image = Image.alpha_composite(background, layer_image)

        # Create a blank image with the same size as the canvas
        layer_canvas = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
        layer_canvas.paste(layer_image, (composite_left, composite_top))

        # Apply lighten blend mode
        final_composite = ImageChops.lighter(final_composite, layer_canvas)

    # Save the final composite image
    logging.info(f"Saving final composite image to: {output_image_path}")
    final_composite.save(output_image_path)

def browse_psd_file():
    psd_file_path = filedialog.askopenfilename(title="Select PSD File", filetypes=[("PSD Files", "*.psd")])
    if psd_file_path:
        psd_entry.delete(0, tk.END)
        psd_entry.insert(0, psd_file_path)

def browse_json_file():
    json_file_path = filedialog.askopenfilename(title="Select JSON File", filetypes=[("JSON Files", "*.json")])
    if json_file_path:
        json_entry.delete(0, tk.END)
        json_entry.insert(0, json_file_path)

def browse_additional_path():
    folder_path = filedialog.askdirectory(title="Select Additional Search Path")
    if folder_path:
        additional_entry.delete(0, tk.END)
        additional_entry.insert(0, folder_path)

def generate_json():
    psd_file = psd_entry.get()
    if not psd_file:
        messagebox.showerror("Error", "Please select a PSD file.")
        return

    use_image_matching = image_matching_var.get()
    subfolder_search_path = subfolder_entry.get()
    additional_search_path = additional_entry.get()

    psd_filename = os.path.basename(psd_file)
    psd_prefix = os.path.splitext(psd_filename)[0]
    exported_layers_dir = os.path.join(os.path.dirname(psd_file), f"{psd_prefix}_exported_layers")
    json_output_path = os.path.join(os.path.dirname(psd_file), f"{psd_prefix}_composition_data.json")

    # Create directories if they don't exist
    if not os.path.exists(exported_layers_dir):
        os.makedirs(exported_layers_dir)

    try:
        export_layers_and_generate_json(psd_file, exported_layers_dir, json_output_path, use_image_matching, subfolder_search_path, additional_search_path)
        messagebox.showinfo("Success", f"JSON file generated: {json_output_path}")
    except Exception as e:
        logging.error(f"Failed to generate JSON: {e}")
        messagebox.showerror("Error", f"Failed to generate JSON: {e}")

def generate_image():
    json_file = json_entry.get()
    if not json_file:
        messagebox.showerror("Error", "Please select a JSON file.")
        return

    json_filename = os.path.basename(json_file)
    json_prefix = os.path.splitext(json_filename)[0]
    output_image_path = os.path.join(os.path.dirname(json_file), f"{json_prefix}_final_composite.png")

    try:
        reconstruct_composition(json_file, output_image_path)
        messagebox.showinfo("Success", f"Composite image generated: {output_image_path}")
    except Exception as e:
        logging.error(f"Failed to generate image: {e}")
        messagebox.showerror("Error", f"Failed to generate image: {e}")

def generate_full_process():
    psd_file = psd_entry.get()
    if not psd_file:
        messagebox.showerror("Error", "Please select a PSD file.")
        return

    use_image_matching = image_matching_var.get()
    subfolder_search_path = subfolder_entry.get()
    additional_search_path = additional_entry.get()

    psd_filename = os.path.basename(psd_file)
    psd_prefix = os.path.splitext(psd_filename)[0]
    exported_layers_dir = os.path.join(os.path.dirname(psd_file), f"{psd_prefix}_exported_layers")
    json_output_path = os.path.join(os.path.dirname(psd_file), f"{psd_prefix}_composition_data.json")
    output_image_path = os.path.join(os.path.dirname(psd_file), f"{psd_prefix}_final_composite.png")

    # Create directories if they don't exist
    if not os.path.exists(exported_layers_dir):
        os.makedirs(exported_layers_dir)

    try:
        export_layers_and_generate_json(psd_file, exported_layers_dir, json_output_path, use_image_matching, subfolder_search_path, additional_search_path)
        reconstruct_composition(json_output_path, output_image_path)
        messagebox.showinfo("Success", f"Composite image generated: {output_image_path}")
    except Exception as e:
        logging.error(f"Failed to complete full process: {e}")
        messagebox.showerror("Error", f"Failed to complete full process: {e}")

# Create the main window
root = tk.Tk()
root.title("PSD Composition Reconstruction")

# PSD File Selection
psd_label = tk.Label(root, text="PSD File:")
psd_label.grid(row=0, column=0, sticky="e", padx=5, pady=5)
psd_entry = tk.Entry(root, width=50)
psd_entry.grid(row=0, column=1, padx=5, pady=5)
psd_browse_button = tk.Button(root, text="Browse", command=browse_psd_file)
psd_browse_button.grid(row=0, column=2, padx=5, pady=5)
psd_generate_button = tk.Button(root, text="Generate JSON", command=generate_json)
psd_generate_button.grid(row=0, column=3, padx=5, pady=5)
psd_full_process_button = tk.Button(root, text="Full Process", command=generate_full_process)
psd_full_process_button.grid(row=0, column=4, padx=5, pady=5)

# JSON File Selection
json_label = tk.Label(root, text="Composition JSON File:")
json_label.grid(row=1, column=0, sticky="e", padx=5, pady=5)
json_entry = tk.Entry(root, width=50)
json_entry.grid(row=1, column=1, padx=5, pady=5)
json_browse_button = tk.Button(root, text="Browse", command=browse_json_file)
json_browse_button.grid(row=1, column=2, padx=5, pady=5)
json_generate_button = tk.Button(root, text="Generate Image", command=generate_image)
json_generate_button.grid(row=1, column=3, padx=5, pady=5)

# Image Matching Checkbox
image_matching_var = tk.BooleanVar(value=True)
image_matching_checkbox = tk.Checkbutton(root, text="Use Image Matching", variable=image_matching_var)
image_matching_checkbox.grid(row=2, column=1, sticky="w", padx=5, pady=5)

# Subfolder Search Path
subfolder_label = tk.Label(root, text="Subfolder Search Path:")
subfolder_label.grid(row=3, column=0, sticky="e", padx=5, pady=5)
subfolder_entry = tk.Entry(root, width=30)
subfolder_entry.insert(0, "backup")
subfolder_entry.grid(row=3, column=1, sticky="w", padx=5, pady=5)

# Additional Search Path
additional_label = tk.Label(root, text="Additional Search Path:")
additional_label.grid(row=4, column=0, sticky="e", padx=5, pady=5)
additional_entry = tk.Entry(root, width=30)
additional_entry.grid(row=4, column=1, sticky="w", padx=5, pady=5)
additional_browse_button = tk.Button(root, text="Browse", command=browse_additional_path)
additional_browse_button.grid(row=4, column=2, padx=5, pady=5)

# Run the Tkinter main loop
if __name__ == '__main__':
    root.mainloop()
