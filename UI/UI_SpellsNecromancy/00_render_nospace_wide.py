# SAVE COMPOSITE IMAGE OF NECRO SPELLS
# Wide no-space format, using tree > branch > twig > leaf metaphor to control arrangement
# The spells are sorted into rows and columns, and the book is on the left branch column.

import os
import re
import time
from PIL import Image
from psd_tools import PSDImage

IMAGE_OUTPUT = "00_ui_spells_necromancy_comp.png"

# Padding parameters
LEAF_PADDING = 5
TWIG_PADDING = 5
BOOK_PADDING = 20  # Special padding for the book image

# Define the number of rows and columns for the final image grid
NUM_ROWS = 2
NUM_COLUMNS = 9  # Adjusted to fit all spells
TOTAL_IMAGES = NUM_ROWS * NUM_COLUMNS

# Size of each image
IMAGE_WIDTH, IMAGE_HEIGHT = 44, 44

# Regex patterns
SPELL_PATTERN = re.compile(r'ui_necro_spell_(.+)_0x[\dA-F]+\.psd')
BOOK_PATTERN = re.compile(r'ui_necro_book_(0x[\dA-F]+)\.psd')

# Define the order of the spells using filenames
SPELL_REORDER = [
    "ui_necro_spell_CurseWeapon_0x5003.psd",
    "ui_necro_spell_BloodOath_0x5001.psd",
    "ui_necro_spell_CorpseSkin_0x5002.psd",
    "ui_necro_spell_EvilOmen_0x5004.psd",
    "ui_necro_spell_PainSpike_0x5008.psd",
    "ui_necro_spell_WraithForm_0x500F.psd",
    "ui_necro_spell_MindRot_0x5007.psd",
    "ui_necro_spell_SummonFamiliar_0x500B.psd",
    "ui_necro_spell_AnimateDead_0x5000.psd",
    "ui_necro_spell_HorrificBeast_0x5005.psd",
    "ui_necro_spell_PoisonStrike_0x5009.psd",
    "ui_necro_spell_Wither_0x500E.psd",
    "ui_necro_spell_Strangle_0x500A.psd",
    "ui_necro_spell_LichForm_0x5006.psd",
    "ui_necro_spell_Exorcism_0x5010.psd",
    "ui_necro_spell_VengefulSpirit_0x500D.psd",
    "ui_necro_spell_VampiricEmbrace_0x500C.psd",
]

# Step 1: List PSD files
def list_psd_files(directory="."):
    psd_files = []
    for filename in os.listdir(directory):
        if SPELL_PATTERN.match(filename):
            psd_files.append(filename)
    return psd_files

# Step 2: Process PSD files into PNG images
def process_psd_files(psd_files, output_directory="temp"):
    os.makedirs(output_directory, exist_ok=True)
    for filename in psd_files:
        try:
            psd = PSDImage.open(filename)
            img = psd.composite()
            img = img.convert('RGBA')  # Ensure the image is in RGBA mode
            leaf_name = f'{output_directory}/{filename.replace(".psd", ".png")}'
            img.save(leaf_name)
            print(f"Processed: {leaf_name}")
        except Exception as e:
            print(f'Error processing {filename}: {e}')

# Step 3: Get custom image order
def get_custom_image_order(psd_files):
    temp_dir = "temp"
    psd_file_dict = {os.path.basename(f): f"{temp_dir}/{f.replace('.psd', '.png')}" for f in psd_files}
    sorted_image_order = []
    for spell in SPELL_REORDER:
        if spell in psd_file_dict:
            sorted_image_order.append(psd_file_dict[spell])
    return sorted_image_order

# Step 4: Assemble images into the final composite image
def assemble_images(output_filename, img_order):
    tree_width = NUM_COLUMNS * IMAGE_WIDTH + (NUM_COLUMNS - 1) * LEAF_PADDING
    tree_height = NUM_ROWS * IMAGE_HEIGHT + (NUM_ROWS - 1) * TWIG_PADDING
    tree = Image.new('RGBA', (tree_width, tree_height), (0, 0, 0, 0))
    for idx, filename in enumerate(img_order):
        try:
            img = Image.open(filename)
            row = idx // NUM_COLUMNS
            col = idx % NUM_COLUMNS
            x_offset = col * (IMAGE_WIDTH + LEAF_PADDING)
            y_offset = row * (IMAGE_HEIGHT + TWIG_PADDING)
            tree.paste(img, (x_offset, y_offset), img)
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    # Load the book image
    book_image = load_book_image()
    book_width, book_height = book_image.size

    # Calculate final image dimensions
    final_width = book_width + BOOK_PADDING + tree_width
    final_height = max(book_height, tree_height)
    final_image = Image.new('RGBA', (final_width, final_height), (0, 0, 0, 0))

    # Paste the book image
    book_y = (final_height - book_height) // 2
    final_image.paste(book_image, (0, book_y), book_image)

    # Paste the spell tree
    tree_x = book_width + BOOK_PADDING
    tree_y = (final_height - tree_height) // 2
    final_image.paste(tree, (tree_x, tree_y), tree)

    final_image.save(output_filename)
    print(f"Composite saved: {output_filename}")

# Step 5: Load the book image
def load_book_image():
    for filename in os.listdir('.'):
        if BOOK_PATTERN.match(filename):
            try:
                psd = PSDImage.open(filename)
                img = psd.composite()
                img = img.convert('RGBA')
                print(f"Loaded book image: {filename}")
                return img
            except Exception as e:
                print(f'Error processing {filename}: {e}')
    raise ValueError("Book image not found")

# Step 6: Clean up intermediate files
def cleanup_temp_files(directory="temp"):
    time.sleep(5)  # Wait before cleanup
    for filename in os.listdir(directory):
        os.remove(os.path.join(directory, filename))
        print(f"Removed: {filename}")
    os.rmdir(directory)

# Main function to execute the steps
def main():
    # Step 1: Get list of PSD files
    psd_files = list_psd_files()

    # Step 2: Process PSD files into PNG images
    process_psd_files(psd_files)

    # Step 3: Get the custom order of images
    ordered_files = get_custom_image_order(psd_files)

    # Step 4: Assemble the images in the custom order and save the composite image
    assemble_images(IMAGE_OUTPUT, ordered_files)

    # Step 5: Cleanup intermediate files
    cleanup_temp_files()

if __name__ == "__main__":
    main()
