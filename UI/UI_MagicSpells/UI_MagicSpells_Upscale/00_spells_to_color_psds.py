# SPELL ICONS TO SPELL COLOR PSD
# duplicates the spell icons , resizes to 70x70 , adjusts image 
# the spell_color icons are used to display the customization of spell effects , 
# they are therefore desaturated , brightened , and decontrasted to better show the color coloration effect.
import os
import shutil
import re
from psd_tools import PSDImage
from PIL import Image, ImageEnhance

SPELL_COLOR_SIZE = 70  # spell colors are slightly larger
# HEXIDECIMAL OFFSET
# "ui_spell_1_Clumsy_0x8C0" >>>>  "ui_spell_1_Clumsy_0x1B58"
OFFSET = 0x1B58 - 0x8C0
BRIGHTNESS_FACTOR = 1.1
SATURATION_FACTOR = 0.8  # Lower than 1 to desaturate
CONTRAST_FACTOR = 0.7  # Lower than 1 to decrease contrast
SPELL_COLOR_FOLDER_NAME = "SpellEffects_Color"

# Function to rename files based on the naming convention
def rename_file(file_name, offset):
    # Regular expression to match the base name and the hexadecimal number
    match = re.match(r'(.+_0x)([0-9A-Fa-f]+)$', file_name)
    if match:
        base_name = match.group(1)
        hex_number = int(match.group(2), 16)
        new_hex_number = hex_number + offset
        new_file_name = f"{base_name}{new_hex_number:0{len(match.group(2))}X}"
        return new_file_name
    return file_name

# Path to the folder containing the PSD files
source_folder = "."

# Path to the secondary folder
secondary_folder = os.path.join(source_folder, SPELL_COLOR_FOLDER_NAME)
os.makedirs(secondary_folder, exist_ok=True)  # Create the secondary folder if it doesn't exist

# Duplicate PSD files to the secondary folder and save as PNG
for file in os.listdir(source_folder):
    if file.endswith(".psd"):
        src_file_path = os.path.join(source_folder, file)
        base_name = os.path.splitext(file)[0]
        new_name = rename_file(base_name, OFFSET) + ".png"
        dest_file_path = os.path.join(secondary_folder, new_name)

        # Check for naming conflicts and delete existing file if necessary
        if os.path.exists(dest_file_path):
            os.remove(dest_file_path)

        psd = PSDImage.open(src_file_path)
        psd.composite().save(dest_file_path, format='PNG')

# Perform adjustments on PNG files and convert back to PSD
for file in os.listdir(secondary_folder):
    if file.endswith(".png"):
        png_path = os.path.join(secondary_folder, file)

        # Open and resize the PNG
        image = Image.open(png_path)
        resized_image = image.resize((SPELL_COLOR_SIZE, SPELL_COLOR_SIZE), Image.Resampling.LANCZOS)

        # Apply brightness adjustment
        enhancer = ImageEnhance.Brightness(resized_image)
        brightened_image = enhancer.enhance(BRIGHTNESS_FACTOR)

        # Apply saturation adjustment
        enhancer = ImageEnhance.Color(brightened_image)
        saturated_image = enhancer.enhance(SATURATION_FACTOR)

        # Apply contrast adjustment
        enhancer = ImageEnhance.Contrast(saturated_image)
        contrasted_image = enhancer.enhance(CONTRAST_FACTOR)

        # Save the adjusted image as PNG
        contrasted_image.save(png_path, format='PNG')

        # Convert the PNG back to PSD
        psd_path = os.path.splitext(png_path)[0] + ".psd"
        PSDImage.frompil(contrasted_image).save(psd_path)

        # Remove the PNG file
        os.remove(png_path)

print("Process completed.")
