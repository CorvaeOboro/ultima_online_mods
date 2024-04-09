# SAVE COMPOSITE IMAGE OF CHIV  
# wide nospace format , using tree > branch > twig > leaf metaphor to control arrangement 
# the 10 spells are sorted into 2 rows of 5 columns , and the book is on the left branch column .
import os
import re
from PIL import Image
from psd_tools import PSDImage

IMAGE_OUTPUT = "ui_necro_00_render_wide.png"

# Padding parameters
LEAF_PADDING = 5
TWIG_PADDING = 5
BOOK_PADDING = 20  # Special padding for the book image

# Define the number of spells per twig
IMAGES_PER_TWIG = 5

# Size of each image
IMAGE_WIDTH, IMAGE_HEIGHT = 44, 44

# Regex patterns
SPELL_PATTERN = re.compile(r'ui_necro_spell_(\d+)_(0x[\dA-F]+)\.psd')
LEAF_PATTERN = re.compile(r'temp_spell_(\d+)_(0x[\dA-F]+)\.png')
BOOK_PATTERN = re.compile(r'ui_necro_book_(0x[\dA-F]+)\.psd')

# Rearrangement order for the images
rearrangement_order = [4, 9, 1, 3, 2, 6, 8, 5, 10, 7]

def assemble_twig(twig_index, leaf_files):
    """Assemble spells into a twig."""
    twig_width = IMAGES_PER_TWIG * (IMAGE_WIDTH + LEAF_PADDING) - LEAF_PADDING
    twig = Image.new('RGBA', (twig_width, IMAGE_HEIGHT), (0, 0, 0, 0))  # Ensure transparent background
    print(f"Creating twig {twig_index} with dimensions: {twig.size}")
    for j, leaf_file in enumerate(leaf_files):
        try:
            img = Image.open(leaf_file)
            twig.paste(img, (j * (IMAGE_WIDTH + LEAF_PADDING), 0), img)  # Use alpha mask for proper transparency
        except Exception as e:
            print(f'Error processing {leaf_file}: {e}')
    return twig

# Process and save individual spell images as leaves
for filename in os.listdir('.'):
    match = SPELL_PATTERN.match(filename)
    if match:
        try:
            psd = PSDImage.open(filename)
            img = psd.composite()  # Get the flattened image
            img = img.convert('RGBA')  # Ensure the image is in RGBA mode
            leaf_name = f'temp_spell_{match.group(1)}_{match.group(2)}.png'
            img.save(leaf_name)
        except Exception as e:
            print(f'Error processing {filename}: {e}')

# Assemble spells into twigs
all_files_in_directory = os.listdir('.')  # List all files in the current directory
filtered_leaf_files = list(filter(LEAF_PATTERN.match, all_files_in_directory))  # Filter the files to include only those that match the leaf pattern
sorted_leaf_files = sorted(filtered_leaf_files)  # Sort the filtered leaf files
print(f"Sorted leaf files: {sorted_leaf_files}")

# Rearrange the leaf files based on the specified order
rearranged_leaf_files = [sorted_leaf_files[i - 1] for i in rearrangement_order]
print(f"Rearranged leaf files: {rearranged_leaf_files}")

twigs = []
for i in range(1, 3):  # Two twigs
    # Calculate the start and end indices for the current twig
    start_index = (i - 1) * IMAGES_PER_TWIG
    end_index = i * IMAGES_PER_TWIG
    leaf_files_for_twig = rearranged_leaf_files[start_index:end_index]  # Slice the rearranged leaf files to get the files for the current twig
    print(f"Files for twig {i}: {leaf_files_for_twig}")
    twig = assemble_twig(i, leaf_files_for_twig)
    twigs.append(twig)
    twig.save(f'temp_twig_{i}.png')

# Load the book image
book_image = None
for filename in os.listdir('.'):
    if BOOK_PATTERN.match(filename):
        try:
            psd = PSDImage.open(filename)
            book_image = psd.composite()
            book_image = book_image.convert('RGBA')
            break
        except Exception as e:
            print(f'Error processing {filename}: {e}')

if book_image is None:
    raise ValueError("Book image not found")

# Create the spell branch by stacking the twigs
spell_branch = Image.new('RGBA', (IMAGES_PER_TWIG * (IMAGE_WIDTH + LEAF_PADDING) - LEAF_PADDING, 2 * IMAGE_HEIGHT + TWIG_PADDING), (0, 0, 0, 0))  # Ensure transparent background
print(f"Creating spell branch with dimensions: {spell_branch.size}")
for i, twig in enumerate(twigs):
    spell_branch.paste(twig, (0, i * (IMAGE_HEIGHT + TWIG_PADDING)), twig)  # Use alpha mask for proper transparency

# Calculate the dimensions for the final composite image
book_width, book_height = book_image.size
spell_branch_width, spell_branch_height = spell_branch.size
final_width = book_width + BOOK_PADDING + spell_branch_width
final_height = max(book_height, spell_branch_height)
print(f"Final image dimensions: {final_width}x{final_height}")

# Create the final composite image
final_image = Image.new('RGBA', (final_width, final_height), (0, 0, 0, 0))  # Ensure transparent background

# Paste the book image centered vertically on the left
book_x = 0
book_y = (final_height - book_height) // 2
final_image.paste(book_image, (book_x, book_y), book_image)  # Use alpha mask for proper transparency

# Paste the spell branch on the right
spell_branch_x = book_width + BOOK_PADDING
spell_branch_y = (final_height - spell_branch_height) // 2
final_image.paste(spell_branch, (spell_branch_x, spell_branch_y), spell_branch)  # Use alpha mask for proper transparency

# Save the final image
final_image.save(IMAGE_OUTPUT)

# Cleanup intermediate files
for file in os.listdir('.'):
    if file.startswith('temp_'):
        os.remove(file)
        print(f"Removed intermediate file: {file}")