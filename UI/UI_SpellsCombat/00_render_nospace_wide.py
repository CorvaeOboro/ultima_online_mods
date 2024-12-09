# SAVE COMPOSITE IMAGE OF SPELL COMBAT
# wide nospace format , using tree > branch > twig > leaf metaphor to control arrangement 
# 1 branch holding 5 rows each of 9 columns 
import os
import re
import time
from PIL import Image
from psd_tools import PSDImage

IMAGE_OUTPUT = "00_ui_spell_combat_comp.png"

# Padding parameters
LEAF_PADDING = 5
TWIG_PADDING = 5

# Define the number of rows and columns for the final image grid
num_rows = 4
num_columns = 8
total_images = 31

# Size of each image
image_width, image_height = 44, 44

# Regex pattern to match PSD files
pattern = re.compile(r'ui_spell_combat_(.+)_0x[\dA-F]+\.psd')

# ORDER LIST FOR SPELL MASTERY
SPELL_REORDER = [

    "ui_spell_combat_Bladeweave_0x5217",
    "ui_spell_combat_ArmorIgnore_0x5200",
    "ui_spell_combat_BleedAttack_0x5201",

    "ui_spell_combat_Disarm_0x5204",
    "ui_spell_combat_Dismount_0x5205",
    "ui_spell_combat_DoubleStrike_0x5206",

    "ui_spell_combat_MortalStrike_0x5208",

    "ui_spell_combat_WhirlwindAttack_0x520C",
    "ui_spell_combat_RidingSwipe_0x520D",
    "ui_spell_combat_FrenziedWhirlwind_0x520E",
    "ui_spell_combat_Block_0x520F",
    "ui_spell_combat_DefenseMastery_0x5210",
    "ui_spell_combat_NerveStrike_0x5211",
    "ui_spell_combat_TalonStrike_0x5212",
    "ui_spell_combat_Feint_0x5213",
    "ui_spell_combat_DualWield_0x5214",
    "ui_spell_combat_ShadowStrike_0x520B",
    "ui_spell_combat_InfusedThrow_0x521D",
    "ui_spell_combat_MysticArc_0x521E",

    "ui_spell_combat_ForceOfNature_0x521C",
    "ui_spell_combat_ConcussionBlow_0x5202",
    "ui_spell_combat_CrushingBlow_0x5203",
    "ui_spell_combat_ParalyzingBlow_0x520A",


    "ui_spell_combat_DoubleShot_0x5215",
    "ui_spell_combat_ArmorPierce_0x5216",
    "ui_spell_combat_ForceArrow_0x5218",
    "ui_spell_combat_LightningArrow_0x5219",
    "ui_spell_combat_PsychicAttack_0x521A",
    "ui_spell_combat_SerpentArrow_0x521B",
    "ui_spell_combat_Infecting_0x5207",
    "ui_spell_combat_MovingShot_0x5209",

]

# Step 1: Create a list of PSD files and write to a txt file
def list_psd_files(directory="."):
    psd_files = []
    for filename in os.listdir(directory):
        if pattern.match(filename):
            psd_files.append(filename)
            print(f"[INFO] Matched PSD File: {filename}")
        else:
            print(f"[DEBUG] Did not match: {filename}")
    if not psd_files:
        print("[WARNING] No PSD files matched the pattern.")
    return psd_files

# Step 2: Process PSD files into images
def process_psd_files(psd_files, output_directory="temp"):
    os.makedirs(output_directory, exist_ok=True)
    for filename in psd_files:
        try:
            psd = PSDImage.open(filename)
            img = psd.composite()
            img = img.convert('RGBA')  # Ensure RGBA mode
            leaf_name = f'{output_directory}/{filename.replace(".psd", ".png")}'
            img.save(leaf_name)
            print(f"[INFO] Processed and saved PNG: {leaf_name}")
        except Exception as e:
            print(f"[ERROR] Error processing {filename}: {e}")

# Step 3: Assemble images in a specified order and save the result
def assemble_images(output_filename, img_order):
    # Ensure we have enough images to create the grid
    if len(img_order) < total_images:
        print(f"[WARNING] Expected {total_images} images, but got {len(img_order)}. Filling with empty spaces.")
        while len(img_order) < total_images:
            img_order.append(None)

    # Create a new RGBA image with a transparent background
    tree_width = num_columns * (image_width + LEAF_PADDING) - LEAF_PADDING
    tree_height = num_rows * (image_height + TWIG_PADDING) - TWIG_PADDING
    tree = Image.new('RGBA', (tree_width, tree_height), (0, 0, 0, 0))
    
    for idx in range(total_images):
        try:
            filename = img_order[idx]
            if filename:
                img = Image.open(filename).convert('RGBA')  # Ensure RGBA mode
                row = idx // num_columns
                col = idx % num_columns
                x_offset = col * (image_width + LEAF_PADDING)
                y_offset = row * (image_height + TWIG_PADDING)
                tree.paste(img, (x_offset, y_offset), img)
                print(f"[INFO] Pasted image {filename} at row {row}, column {col}.")
            else:
                print(f"[DEBUG] No image to paste at index {idx}.")
        except Exception as e:
            print(f"[ERROR] Error processing {filename}: {e}")
    
    tree.save(output_filename)
    print(f"[INFO] Composite saved: {output_filename}")

# Step 4: Clean up intermediate files
def cleanup(patterns, directory="."):
    for pattern in patterns:
        for filename in os.listdir(directory):
            if re.match(pattern, filename):
                os.remove(os.path.join(directory, filename))
                print(f"[INFO] Removed: {filename}")

# Step 5: Custom image order using SPELL_REORDER global list
def get_custom_image_order(psd_files):
    sorted_image_order = []
    psd_file_dict = {os.path.splitext(os.path.basename(f))[0]: f for f in psd_files}  # Create a dict for quick lookups
    for spell in SPELL_REORDER:
        if spell in psd_file_dict:
            sorted_image_order.append(psd_file_dict[spell].replace('.psd', '.png'))
            print(f"[INFO] Found and added to order: {spell}")
        else:
            print(f"[WARNING] Did not find expected file for: {spell}")
    return sorted_image_order

# Main function to execute the steps
def main():
    # Step 1: Get list of PSD files
    print("[INFO] Listing PSD files:")
    psd_files = list_psd_files()

    # Step 2: Process PSD files into PNG images
    if psd_files:
        print("[INFO] Processing PSD files into PNG images:")
        process_psd_files(psd_files)

    # Step 3: Get the custom order of images
    print("[INFO] Getting custom image order:")
    ordered_files = get_custom_image_order([f"temp/{psd}" for psd in psd_files])

    # Step 4: Assemble the images in the custom order and save the composite image
    print("[INFO] Assembling images into composite:")
    assemble_images(IMAGE_OUTPUT, ordered_files)

    # Step 5: Cleanup intermediate files
    print("[INFO] Cleaning up intermediate files:")
    time.sleep(5)  # Wait before cleanup
    cleanup([r'ui_spell_mastery_.*\.png'], "temp")

if __name__ == "__main__":
    main()
