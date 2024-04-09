# SAVE COMPOSITE IMAGE OF SPELLS 
# wide nospace format , using tree > branch > twig > leaf metaphor to control arrangement 
# 2 columns holding 4 rows each of spell groups 1-8 , spells arranged in 8 columns 
import os
import re
import time
from PIL import Image
from psd_tools import PSDImage

IMAGE_OUTPUT = "ui_spell_00_comp_nospace_wide.png"

# Padding parameters
LEAF_PADDING = 1
TWIG_PADDING = 1
BRANCH_PADDING = 1

# Define the number of groups and images per group
group_split = 4
num_groups = 8  # spell circle level
images_per_group = 8  # spells per circle

# size of each image
image_width, image_height = 44, 44

# regex get spell circle
pattern = re.compile(r'ui_spell_(\d+)_(.+)_(0x[\dA-F]+)\.psd')

#//=========================================================================
def cleanup(file_pattern):
    for filename in os.listdir('.'):
        if re.match(file_pattern, filename):
            os.remove(filename)

# Process and save individual images (leaves)
for filename in os.listdir('.'):
    match = pattern.match(filename)
    if match:
        group = int(match.group(1))
        if 1 <= group <= num_groups:
            try:
                psd = PSDImage.open(filename)
                img = psd.composite()  # Get the flattened image
                img = img.convert('RGBA')  # Ensure the image is in RGBA mode
                leaf_name = f'temp_leaf_{group:02d}_{match.group(2)}_{match.group(3)}.png'
                img.save(leaf_name)
            except Exception as e:
                print(f'Error processing {filename}: {e}')

# Assemble rows (twigs)
for group in range(1, num_groups + 1):
    twig = Image.new('RGBA', (images_per_group * (image_width + LEAF_PADDING) - LEAF_PADDING, image_height))
    leaf_pattern = re.compile(f'temp_leaf_{group:02d}_[^_]+_0x[\dA-F]+\.png')
    leaf_files = sorted(filter(leaf_pattern.match, os.listdir('.')))
    for i, leaf in enumerate(leaf_files):
        try:
            img = Image.open(leaf)
            twig.paste(img, (i * (image_width + LEAF_PADDING), 0))
        except Exception as e:
            print(f'Error processing {leaf}: {e}')
    twig.save(f'temp_twig_{group:02d}.png')

# Stack rows into columns (branches)
for branch_num in range(1, num_groups // group_split + 1):
    branch = Image.new('RGBA', (images_per_group * (image_width + LEAF_PADDING) - LEAF_PADDING, group_split * (image_height + TWIG_PADDING) - TWIG_PADDING))
    for group in range((branch_num - 1) * group_split + 1, branch_num * group_split + 1):
        try:
            twig = Image.open(f'temp_twig_{group:02d}.png')
            branch.paste(twig, (0, (group - 1) % group_split * (image_height + TWIG_PADDING)))
        except Exception as e:
            print(f'Error processing twig_{group:02d}.png: {e}')
    branch.save(f'temp_branch_{branch_num}.png')

# Arrange branches side by side (trees)
tree = Image.new('RGBA', (2 * (images_per_group * (image_width + LEAF_PADDING) - LEAF_PADDING + BRANCH_PADDING) - BRANCH_PADDING, group_split * (image_height + TWIG_PADDING) - TWIG_PADDING))
for branch_num in range(1, num_groups // group_split + 1):
    try:
        branch = Image.open(f'temp_branch_{branch_num}.png')
        tree.paste(branch, ((branch_num - 1) * (images_per_group * (image_width + LEAF_PADDING) - LEAF_PADDING + BRANCH_PADDING), 0))
    except Exception as e:
        print(f'Error processing branch_{branch_num}.png: {e}')
tree.save(IMAGE_OUTPUT)

# Wait a few seconds before cleanup
time.sleep(5)

# Cleanup intermediate files
cleanup(r'temp_leaf_\d{2}_[^_]+_0x[\dA-F]+\.png')
cleanup(r'temp_twig_\d{2}\.png')
cleanup(r'temp_branch_\d\.png')