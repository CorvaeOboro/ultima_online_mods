# SAVE COMPOSITE IMAGE OF SPELL WEAVING
# wide nospace format , using tree > branch > twig > leaf metaphor to control arrangement 
# 2 columns holding 4 rows each of spell groups 1-8 , spells arranged in 8 columns 
import os
import re
import time
from PIL import Image
from psd_tools import PSDImage

IMAGE_OUTPUT = "00_ui_spell_weaving_comp.png"

# Padding parameters
LEAF_PADDING = 5
TWIG_PADDING = 5
BRANCH_PADDING = 5

# Define the number of rows and columns for the final image grid
num_rows = 2
num_columns = 8
total_images = 16

# Size of each image
image_width, image_height = 44, 44

# Regex pattern to match PSD files
pattern = re.compile(r'ui_spell_weaving_(.+)_0x[\dA-F]+\.psd')

# ORDER LIST FOR SPELL WEAVING
SPELL_REORDER = [
    "ui_spell_weaving_ArcaneCircle_0x59D8.psd",
    "ui_spell_weaving_ArcaneEmpowerment_0x59E7.psd",
    "ui_spell_weaving_Attunement_0x59DB.psd",
    "ui_spell_weaving_DryadAllure_0x59E3.psd",
    "ui_spell_weaving_EssenceOfWind_0x59E2.psd",
    "ui_spell_weaving_EtherealVoyage_0x59E4.psd",
    "ui_spell_weaving_GiftOfLife_0x59E6.psd",
    "ui_spell_weaving_GiftOfRenewal_0x59D9.psd",
    "ui_spell_weaving_ImmolatingWeapon_0x59DA.psd",
    "ui_spell_weaving_NaturesFury_0x59DD.psd",
    "ui_spell_weaving_ReaperForm_0x59E0.psd",
    "ui_spell_weaving_SummonFey_0x59DE.psd",
    "ui_spell_weaving_SummonFiend_0x59DF.psd",
    "ui_spell_weaving_Thunderstorm_0x59DC.psd",
    "ui_spell_weaving_Wildfire_0x59E1.psd",
    "ui_spell_weaving_WordOfDeath_0x59E5.psd"
]

# Step 1: Create a list of PSD files and write to a txt file
def list_psd_files(directory="."):
    psd_files = []
    for filename in os.listdir(directory):
        if pattern.match(filename):
            psd_files.append(filename)
    with open("psd_file_list.txt", "w") as file:
        for psd in psd_files:
            file.write(f"{psd}\n")
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
            print(f"Processed: {leaf_name}")
        except Exception as e:
            print(f"Error processing {filename}: {e}")

# Step 3: Assemble images in a specified order and save the result
def assemble_images(output_filename, img_order):
    tree = Image.new('RGBA', (num_columns * image_width + (num_columns - 1) * LEAF_PADDING,
                              num_rows * image_height + (num_rows - 1) * TWIG_PADDING))
    
    for idx, filename in enumerate(img_order):
        try:
            img = Image.open(filename)
            row = idx // num_columns
            col = idx % num_columns
            x_offset = col * (image_width + LEAF_PADDING)
            y_offset = row * (image_height + TWIG_PADDING)
            tree.paste(img, (x_offset, y_offset))
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    
    tree.save(output_filename)
    print(f"Composite saved: {output_filename}")

# Step 4: Clean up intermediate files
def cleanup(patterns, directory="."):
    for pattern in patterns:
        for filename in os.listdir(directory):
            if re.match(pattern, filename):
                os.remove(os.path.join(directory, filename))
                print(f"Removed: {filename}")

# Step 5: Custom image order using SPELL_REORDER global list
def get_custom_image_order(psd_files):
    sorted_image_order = []
    psd_file_dict = {os.path.basename(f): f for f in psd_files}  # Create a dict for quick lookups
    for spell in SPELL_REORDER:
        if spell in psd_file_dict:
            sorted_image_order.append(psd_file_dict[spell].replace('.psd', '.png'))
    return sorted_image_order

# Main function to execute the steps
def main():
    # Step 1: Get list of PSD files
    psd_files = list_psd_files()

    # Step 2: Process PSD files into PNG images
    process_psd_files(psd_files)

    # Step 3: Get the custom order of images
    ordered_files = get_custom_image_order([f"temp/{psd}" for psd in psd_files])

    # Step 4: Assemble the images in the custom order and save the composite image
    assemble_images(IMAGE_OUTPUT, ordered_files)

    # Step 5: Cleanup intermediate files
    time.sleep(5)  # Wait before cleanup
    cleanup([r'temp/ui_spell_weaving_.*\.png'], "temp")

if __name__ == "__main__":
    main()
