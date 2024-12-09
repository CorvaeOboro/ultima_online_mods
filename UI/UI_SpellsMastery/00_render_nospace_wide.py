# SAVE COMPOSITE IMAGE OF SPELL MASTERY
# wide nospace format , using tree > branch > twig > leaf metaphor to control arrangement 
# 1 branch holding 5 rows each of 9 columns 
import os
import re
import time
from PIL import Image
from psd_tools import PSDImage

IMAGE_OUTPUT = "00_ui_spell_mastery_comp.png"

# Padding parameters
LEAF_PADDING = 5
TWIG_PADDING = 5

# Define the number of rows and columns for the final image grid
num_rows = 5
num_columns = 9
total_images = 45

# Size of each image
image_width, image_height = 44, 44

# Regex pattern to match PSD files
pattern = re.compile(r'ui_spell_mastery_(.+)_0x[\dA-F]+\.psd')

# ORDER LIST FOR SPELL MASTERY
SPELL_REORDER = [
    "ui_spell_mastery_WarriorsGift_0x9BA5",
    "ui_spell_mastery_FlamingShot_0x9B9B",
    "ui_spell_mastery_PlayingTheOdds_0x9B9C",
    "ui_spell_mastery_Thrust_0x9B9D",
    "ui_spell_mastery_Pierce_0x9B9E",
    "ui_spell_mastery_Stagger_0x9B9F",
    "ui_spell_mastery_Toughness_0x9BA0",
    "ui_spell_mastery_Onslaught_0x9BA1",
    "ui_spell_mastery_FocusedEye_0x9BA2",
    "ui_spell_mastery_ElementalFury_0x9BA3",
    "ui_spell_mastery_CalledShot_0x9BA4",
    "ui_spell_mastery_ShieldBash_0x9BA6",
    "ui_spell_mastery_Bodyguard_0x9BA7",
    "ui_spell_mastery_HeightenedSenses_0x9BA8",
    "ui_spell_mastery_KnockOut_0x9BAE",
    "ui_spell_mastery_Rampage_0x9BAC",
    "ui_spell_mastery_FistsOfFury_0x9BAD",
    "ui_spell_mastery_Perserverance_0x948",
    "ui_spell_mastery_Resilience_0x947",
    "ui_spell_mastery_Intuition_0x9B96",
    "ui_spell_mastery_AnticipateHit_0x9B94",
    "ui_spell_mastery_Warcry_0x9B95",
    "ui_spell_mastery_Rejuvinate_0x9B97",
    "ui_spell_mastery_HolyFist_0x9B98",
    "ui_spell_mastery_Shadow_0x9B99",
    "ui_spell_mastery_WhiteTigerForm_0x9B9A",
    "ui_spell_mastery_CommandUndead_0x9B8F",
    "ui_spell_mastery_Conduit_0x9B90",
    "ui_spell_mastery_EnchantedSummoning_0x9B93",
    "ui_spell_mastery_DeathRay_0x9B8B",
    "ui_spell_mastery_EtherealBlast_0x9B8C",
    "ui_spell_mastery_ManaShield_0x9B91",
    "ui_spell_mastery_SummonReaper_0x9B92",
    "ui_spell_mastery_NetherBlast_0x9B8D",
    "ui_spell_mastery_MysticWeapon_0x9B8E",
    "ui_spell_mastery_Tribulation_0x949",
    "ui_spell_mastery_Inspire_0x945",
    "ui_spell_mastery_Invigorate_0x946",
    "ui_spell_mastery_Despair_0x94A",
    "ui_spell_mastery_Boarding_0x9BB1",
    "ui_spell_mastery_CombatTraining_0x9BB0",
    "ui_spell_mastery_Whispering_0x9BAF",
    "ui_spell_mastery_Potency_0x9BAB",
    "ui_spell_mastery_Tolerance_0x9BA9",
    "ui_spell_mastery_InjectedStrike_0x9BAA",
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
