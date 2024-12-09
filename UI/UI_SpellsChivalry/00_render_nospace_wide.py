import os
import re
import time
from PIL import Image
from psd_tools import PSDImage

IMAGE_OUTPUT = "00_ui_spells_chivalry_comp.png"

# Padding parameters
LEAF_PADDING = 5
TWIG_PADDING = 5
BOOK_PADDING = 20

# Image size parameters
IMAGE_WIDTH, IMAGE_HEIGHT = 44, 44

# Regex patterns
SPELL_PATTERN = re.compile(r'ui_chivalry_spell_(.+)_0x[\dA-F]+\.psd')
LEAF_PATTERN = re.compile(r'temp_spell_(.+)_0x[\dA-F]+\.png')
BOOK_PATTERN = re.compile(r'ui_chivalry_book_(0x[\dA-F]+)\.psd')

# Order list for spell weaving
SPELL_REORDER = [
    "ui_chivalry_spell_CleansebyFire_0x5100",
    "ui_chivalry_spell_CloseWounds_0x5101",
    "ui_chivalry_spell_ConsecrateWeapon_0x5102",
    "ui_chivalry_spell_DispelEvil_0x5108",
    "ui_chivalry_spell_DivineFury_0x5104",
    "ui_chivalry_spell_EnemyofOne_0x5105",
    "ui_chivalry_spell_HolyLight_0x5106",
    "ui_chivalry_spell_NobleSacrifice_0x5107",
    "ui_chivalry_spell_RemoveCurse_0x5103",
    "ui_chivalry_spell_SacredJourney_0x5109",
]

# Number of spells per twig
IMAGES_PER_TWIG = 5

# Main directory for intermediate files
TEMP_DIR = "temp"

def list_psd_files(pattern, directory="."):
    """List all PSD files matching a given pattern."""
    psd_files = [f for f in os.listdir(directory) if pattern.match(f)]
    with open("psd_file_list.txt", "w") as file:
        for psd in psd_files:
            file.write(f"{psd}\n")
    return psd_files

def process_psd_files(psd_files, output_directory=TEMP_DIR):
    """Process PSD files into PNG images."""
    os.makedirs(output_directory, exist_ok=True)
    for filename in psd_files:
        try:
            psd = PSDImage.open(filename)
            img = psd.composite()
            img = img.convert('RGBA')
            leaf_name = f'{output_directory}/{filename.replace(".psd", ".png")}'
            img.save(leaf_name)
            print(f"Processed: {leaf_name}")
        except Exception as e:
            print(f"Error processing {filename}: {e}")

def get_custom_image_order(psd_files, spell_reorder, directory=TEMP_DIR):
    """Get the custom order of images based on the spell reorder list."""
    psd_file_dict = {os.path.basename(f).replace(".psd", ""): f for f in psd_files}
    ordered_files = [
        f"{directory}/{spell}.png"
        for spell in spell_reorder
        if spell in psd_file_dict
    ]
    return ordered_files

def assemble_twig(twig_index, leaf_files):
    """Assemble spells into a twig."""
    twig_width = IMAGES_PER_TWIG * (IMAGE_WIDTH + LEAF_PADDING) - LEAF_PADDING
    twig = Image.new('RGBA', (twig_width, IMAGE_HEIGHT), (0, 0, 0, 0))
    print(f"Creating twig {twig_index} with dimensions: {twig.size}")
    for j, leaf_file in enumerate(leaf_files):
        try:
            img = Image.open(leaf_file)
            twig.paste(img, (j * (IMAGE_WIDTH + LEAF_PADDING), 0), img)
        except Exception as e:
            print(f'Error processing {leaf_file}: {e}')
    return twig

def assemble_spell_branch(twigs):
    """Create the spell branch by stacking the twigs."""
    branch_width = IMAGES_PER_TWIG * (IMAGE_WIDTH + LEAF_PADDING) - LEAF_PADDING
    branch_height = len(twigs) * IMAGE_HEIGHT + (len(twigs) - 1) * TWIG_PADDING
    spell_branch = Image.new('RGBA', (branch_width, branch_height), (0, 0, 0, 0))
    print(f"Creating spell branch with dimensions: {spell_branch.size}")
    for i, twig in enumerate(twigs):
        spell_branch.paste(twig, (0, i * (IMAGE_HEIGHT + TWIG_PADDING)), twig)
    return spell_branch

def load_book_image(pattern, directory="."):
    """Load the book image from PSD."""
    for filename in os.listdir(directory):
        if pattern.match(filename):
            try:
                psd = PSDImage.open(filename)
                return psd.composite().convert('RGBA')
            except Exception as e:
                print(f'Error processing {filename}: {e}')
    raise ValueError("Book image not found")

def create_composite_image(book_image, spell_branch, output_filename):
    """Create the final composite image."""
    book_width, book_height = book_image.size
    spell_branch_width, spell_branch_height = spell_branch.size
    final_width = book_width + BOOK_PADDING + spell_branch_width
    final_height = max(book_height, spell_branch_height)
    print(f"Final image dimensions: {final_width}x{final_height}")

    final_image = Image.new('RGBA', (final_width, final_height), (0, 0, 0, 0))
    book_x = 0
    book_y = (final_height - book_height) // 2
    final_image.paste(book_image, (book_x, book_y), book_image)

    spell_branch_x = book_width + BOOK_PADDING
    spell_branch_y = (final_height - spell_branch_height) // 2
    final_image.paste(spell_branch, (spell_branch_x, spell_branch_y), spell_branch)

    final_image.save(output_filename)
    print(f"Composite saved: {output_filename}")

def cleanup(patterns, directory="."):
    """Remove intermediate files matching the given patterns."""
    for pattern in patterns:
        for filename in os.listdir(directory):
            if re.match(pattern, filename):
                os.remove(os.path.join(directory, filename))
                print(f"Removed: {filename}")

def main():
    # Step 1: List PSD files
    psd_files = list_psd_files(SPELL_PATTERN)

    # Step 2: Process PSD files into PNG images
    process_psd_files(psd_files)

    # Step 3: Get the custom order of leaf images
    ordered_files = get_custom_image_order(psd_files, SPELL_REORDER)

    # Step 4: Assemble spells into twigs
    twigs = []
    for i in range(2):  # Two twigs
        start_index = i * IMAGES_PER_TWIG
        end_index = start_index + IMAGES_PER_TWIG
        twig = assemble_twig(i + 1, ordered_files[start_index:end_index])
        twigs.append(twig)

    # Step 5: Assemble the spell branch
    spell_branch = assemble_spell_branch(twigs)

    # Step 6: Load the book image
    book_image = load_book_image(BOOK_PATTERN)

    # Step 7: Create the composite image
    create_composite_image(book_image, spell_branch, IMAGE_OUTPUT)

    # Step 8: Cleanup intermediate files
    time.sleep(5)  # Wait before cleanup
    cleanup([r'temp/.*\.png'], TEMP_DIR)

if __name__ == "__main__":
    main()
