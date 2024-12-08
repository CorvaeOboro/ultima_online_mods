# PAINTOVER TO PSD
# given a set of images that should be added to matching psd it will load photoshop and place as top most layer 
# this workflow useful for paintover passes from blender or updating tree slices . 
# reset transform may be neccesary after so the layer is proper size
import os
import logging
import tkinter as tk
from tkinter import filedialog, messagebox
from photoshop import Session
from pathlib import Path

# ====================== Configuration Section ======================

# Default folder paths (Set these to your preferred default directories)
DEFAULT_PSD_FOLDER = r"D:\ULTIMA\MODS\ultima_online_mods\ENV\ENV_HeartWood"       # Replace with your default PSD folder path
DEFAULT_IMAGES_FOLDER = r"D:\ULTIMA\MODS\ultima_online_mods\ENV\ENV_HeartWood\paint" # Replace with your default Images folder path
# ===================================================================

# ===================================================================

# Define PsDialogModes constants manually
class PsDialogModes:
    psDisplayAllDialogs = 1
    psDisplayNoDialogs = 3

# Define ElementPlacement constants manually
class ElementPlacement:
    PLACEBEFORE = 2
    PLACEAFTER = 1
    PLACEATEND = 3

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to capture all levels of log messages
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("photoshop_layer_adder.log", mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def select_folder(title="Select Folder"):
    """Open a dialog to select a folder and return the selected path."""
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    folder_selected = filedialog.askdirectory(title=title)
    root.destroy()
    return folder_selected

def normalize_filename(filename):
    """
    Normalize filenames by converting to lowercase and stripping whitespace.

    Args:
        filename (str): The filename to normalize.

    Returns:
        str: The normalized filename.
    """
    return filename.strip().lower()

def execute_photoshop_action(ps, action_set, action_name):
    """
    Execute a specific Photoshop action.

    Args:
        ps: The Photoshop session object.
        action_set (str): The name of the action set containing the action.
        action_name (str): The name of the action to execute.
    """
    try:
        logger.info(f"Executing Photoshop action '{action_name}' from action set '{action_set}'.")
        # Convert action set and action name to type IDs
        action_set_id = ps.app.stringIDToTypeID(action_set)
        action_name_id = ps.app.stringIDToTypeID(action_name)

        # Create an ActionReference for the action set
        action_ref = ps.ActionReference()
        action_ref.putName(ps.app.charIDToTypeID("ASet"), action_set)
        
        # Execute the action
        ps.app.executeAction(ps.app.stringIDToTypeID("action"), ps.ActionDescriptor(), PsDialogModes.psDisplayNoDialogs)
        logger.info(f"Successfully executed action '{action_name}'.")
    except Exception as e:
        logger.error(f"Failed to execute Photoshop action '{action_name}': {e}", exc_info=True)

def add_image_as_top_layer(psd_path, image_path, action_set, action_name):
    """
    Open the PSD file, add the external image as the top layer, execute a Photoshop action to reset transform, and save the PSD.

    Args:
        psd_path (str): Path to the PSD file.
        image_path (str): Path to the external image (BMP or PNG).
        action_set (str): The name of the Photoshop action set containing the reset action.
        action_name (str): The name of the Photoshop action to execute after placing the image.
    """
    try:
        logger.info(f"Opening Photoshop session for PSD: '{psd_path}'")
        with Session(psd_path, action="open") as ps:
            logger.debug("Photoshop session started.")
            doc = ps.active_document
            logger.debug(f"Active document: '{doc.name}'")
            
            # Record current layers for debugging
            existing_layers = [layer.name for layer in doc.layers]
            logger.debug(f"Existing layers before placing image: {existing_layers}")
            
            # Place the image into the PSD
            logger.info(f"Placing image: '{image_path}' into PSD: '{psd_path}'")
            options = ps.ActionDescriptor()
            # Use putPath with the image path
            options.putPath(ps.app.charIDToTypeID('null'), image_path)
            # Execute the 'Place' action with no dialogs
            ps.app.executeAction(ps.app.charIDToTypeID('Plc '), options, PsDialogModes.psDisplayNoDialogs)
            logger.debug(f"Executed 'Place' action for image: '{image_path}'")
            
            # The placed layer is now the active layer
            placed_layer = doc.active_layer
            logger.debug(f"Placed layer identified as: '{placed_layer.name}'")
            
            # Ensure the placed layer is fully loaded
            ps.app.refresh()
            logger.debug("Photoshop session refreshed to ensure layer is loaded.")
            
            # Move the placed layer to the top
            # In Photoshop's layer stack, index 0 is the topmost layer
            top_layer_before = doc.layers[0]
            logger.debug(f"Current top layer before moving: '{top_layer_before.name}'")
            
            # Move the placed layer before the current top layer
            placed_layer.move(top_layer_before, ElementPlacement.PLACEBEFORE)
            logger.debug(f"Moved '{placed_layer.name}' before '{top_layer_before.name}'.")
            
            # Verify the new top layer
            new_top_layer = doc.layers[0]
            logger.debug(f"New top layer after moving: '{new_top_layer.name}'")
            
            if new_top_layer.name != placed_layer.name:
                logger.warning(f"Expected '{placed_layer.name}' to be the top layer, but found '{new_top_layer.name}' instead.")
            else:
                logger.info(f"Successfully added '{placed_layer.name}' as the top layer.")
    
            # Execute the specified Photoshop action to reset transform
            execute_photoshop_action(ps, action_set, action_name)
    
            # Record layers after placement for debugging
            updated_layers = [layer.name for layer in doc.layers]
            logger.debug(f"Existing layers after placing image: {updated_layers}")
    
            # Save the PSD
            logger.info(f"Saving PSD: '{psd_path}'")
            doc.save()
            logger.info("PSD saved successfully.")
    
    except Exception as e:
        logger.error(f"Error processing PSD '{psd_path}' with image '{image_path}': {e}", exc_info=True)

def process_files(psd_folder, images_folder, action_set, action_name):
    """
    Process external images by adding them as top layers in matching PSD files and executing a Photoshop action.

    Args:
        psd_folder (str): Path to the folder containing PSD files.
        images_folder (str): Path to the folder containing external images.
        action_set (str): The name of the Photoshop action set containing the reset action.
        action_name (str): The name of the Photoshop action to execute after placing the image.
    """
    logger.info(f"Starting processing.\nPSD Folder: '{psd_folder}'\nImages Folder: '{images_folder}'")
    
    if not os.path.isdir(psd_folder):
        logger.error(f"PSD folder does not exist: '{psd_folder}'")
        messagebox.showerror("Error", f"PSD folder does not exist: '{psd_folder}'")
        return
    
    if not os.path.isdir(images_folder):
        logger.error(f"Images folder does not exist: '{images_folder}'")
        messagebox.showerror("Error", f"Images folder does not exist: '{images_folder}'")
        return
    
    # Get list of image files (BMP and PNG)
    image_files = [f for f in os.listdir(images_folder) if f.lower().endswith(('.bmp', '.png'))]
    logger.info(f"Found {len(image_files)} image file(s) (BMP and PNG) in '{images_folder}'.")
    logger.debug(f"Image Files: {image_files}")
    
    # Get list of PSD files
    psd_files = [f for f in os.listdir(psd_folder) if f.lower().endswith('.psd')]
    logger.info(f"Found {len(psd_files)} PSD file(s) in '{psd_folder}'.")
    logger.debug(f"PSD Files: {psd_files}")
    
    # Create a set of normalized PSD filenames (without extension) for quick lookup
    normalized_psd_set = set(normalize_filename(Path(psd).stem) for psd in psd_files)
    logger.debug(f"Normalized PSD filenames: {normalized_psd_set}")
    
    # Log all found images
    logger.info("Listing all external images found:")
    for img in image_files:
        logger.info(f" - {img}")
    
    # Iterate over image files and find matching PSD files
    matched = 0
    unmatched_images = []
    for img in image_files:
        img_stem = Path(img).stem
        normalized_img_stem = normalize_filename(img_stem)
        logger.debug(f"Processing Image: '{img}' (Normalized: '{normalized_img_stem}')")
        
        # Find matching PSD
        matching_psd = None
        for psd in psd_files:
            psd_stem = Path(psd).stem
            normalized_psd_stem = normalize_filename(psd_stem)
            if normalized_img_stem == normalized_psd_stem:
                matching_psd = psd
                break
        
        if matching_psd:
            logger.info(f"Image '{img}' matches PSD '{matching_psd}'")
            psd_path = os.path.join(psd_folder, matching_psd)
            image_path = os.path.join(images_folder, img)
            add_image_as_top_layer(psd_path, image_path, action_set, action_name)
            matched += 1
        else:
            logger.warning(f"No matching PSD found for Image: '{img}'")
            unmatched_images.append(img)
    
    logger.info(f"Processing completed. {matched} image(s) were added to PSD file(s).")
    if unmatched_images:
        logger.info(f"No matching PSD files found for the following images ({len(unmatched_images)}): {unmatched_images}")

def create_ui():
    """Create the Tkinter user interface."""
    def run_process():
        psd_folder = psd_folder_var.get()
        images_folder = images_folder_var.get()
        action_set = action_set_var.get()
        action_name = action_name_var.get()
        
        if not psd_folder or not images_folder or not action_set or not action_name:
            messagebox.showwarning("Input Required", "Please select both PSD and Images folders and specify the action set and action name.")
            return
        process_files(psd_folder, images_folder, action_set, action_name)
        messagebox.showinfo("Completed", "Processing completed. Check logs for details.")
    
    # Initialize main window
    root = tk.Tk()
    root.title("PSD Layer Adder")
    
    # Set window size
    root.geometry("800x500")
    root.resizable(False, False)
    
    # Instructions Label
    instructions = tk.Label(root, text="Select the folders containing your external images and corresponding PSD files.\n"
                                       "The script will match files based on their filenames (case-insensitive, without extensions).\n"
                                       "Only .bmp and .png image files are considered.\n"
                                       "After placing each image, the specified Photoshop action will be executed to reset its transform.",
                            justify='left', padx=10, pady=10)
    instructions.pack()
    
    # Images Folder Selection
    img_frame = tk.Frame(root)
    img_frame.pack(pady=5, padx=10, fill='x')
    
    img_label = tk.Label(img_frame, text="Images Folder:", width=15, anchor='w')
    img_label.pack(side='left')
    
    images_folder_var = tk.StringVar()
    # Set default Images folder if it exists
    if os.path.isdir(DEFAULT_IMAGES_FOLDER):
        images_folder_var.set(DEFAULT_IMAGES_FOLDER)
        logger.debug(f"Default Images folder set to: '{DEFAULT_IMAGES_FOLDER}'")
    else:
        images_folder_var.set("")
        logger.warning(f"Default Images folder does not exist: '{DEFAULT_IMAGES_FOLDER}'")
    
    images_entry = tk.Entry(img_frame, textvariable=images_folder_var, width=50)
    images_entry.pack(side='left', padx=5)
    
    img_button = tk.Button(img_frame, text="Browse", command=lambda: images_folder_var.set(select_folder("Select Images Folder")))
    img_button.pack(side='left')
    
    # PSD Folder Selection
    psd_frame = tk.Frame(root)
    psd_frame.pack(pady=5, padx=10, fill='x')
    
    psd_label = tk.Label(psd_frame, text="PSD Folder:", width=15, anchor='w')
    psd_label.pack(side='left')
    
    psd_folder_var = tk.StringVar()
    # Set default PSD folder if it exists
    if os.path.isdir(DEFAULT_PSD_FOLDER):
        psd_folder_var.set(DEFAULT_PSD_FOLDER)
        logger.debug(f"Default PSD folder set to: '{DEFAULT_PSD_FOLDER}'")
    else:
        psd_folder_var.set("")
        logger.warning(f"Default PSD folder does not exist: '{DEFAULT_PSD_FOLDER}'")
    
    psd_entry = tk.Entry(psd_frame, textvariable=psd_folder_var, width=50)
    psd_entry.pack(side='left', padx=5)
    
    psd_button = tk.Button(psd_frame, text="Browse", command=lambda: psd_folder_var.set(select_folder("Select PSD Folder")))
    psd_button.pack(side='left')
    
    # Photoshop Action Set Selection
    action_set_frame = tk.Frame(root)
    action_set_frame.pack(pady=5, padx=10, fill='x')
    
    action_set_label = tk.Label(action_set_frame, text="Action Set Name:", width=15, anchor='w')
    action_set_label.pack(side='left')
    
    action_set_var = tk.StringVar()
    action_set_entry = tk.Entry(action_set_frame, textvariable=action_set_var, width=50)
    action_set_entry.pack(side='left', padx=5)
    action_set_entry.insert(0, "Default Actions")  # Default action set name, change if different
    
    # Photoshop Action Name Selection
    action_name_frame = tk.Frame(root)
    action_name_frame.pack(pady=5, padx=10, fill='x')
    
    action_name_label = tk.Label(action_name_frame, text="Action Name:", width=15, anchor='w')
    action_name_label.pack(side='left')
    
    action_name_var = tk.StringVar()
    action_name_entry = tk.Entry(action_name_frame, textvariable=action_name_var, width=50)
    action_name_entry.pack(side='left', padx=5)
    action_name_entry.insert(0, "ResetTransform_close")  # Default action name, change if different
    
    # Run Button
    run_button = tk.Button(root, text="Run", command=run_process, bg='green', fg='white', width=10)
    run_button.pack(pady=20)
    
    # Footer Label
    footer = tk.Label(root, text="Check 'photoshop_layer_adder.log' for detailed logs.", fg='blue', padx=10, pady=10)
    footer.pack()
    
    # Start the GUI loop
    root.mainloop()

if __name__ == "__main__":
    try:
        create_ui()
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        messagebox.showerror("Critical Error", f"An unexpected error occurred:\n{e}")
