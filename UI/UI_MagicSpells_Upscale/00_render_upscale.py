# SAVE COMPOSITE IMAGE OF SPELLS UPSCALE COMPARISSON 
# wide upscale compare with original and small versions , using tree > branch > twig > leaf metaphor to control arrangement 
# 3 columns holding 2 rows spell comparisons , variants arranged in 3 columns 
import os
from PIL import Image

# Folders containing different types of images
large_img_folder = 'upscale'
small_img_folder = 'small'
gray_img_folder = 'original'

# Output image
output_image = "ui_spell_00_comp_upscale.png"

# Image sizes
large_img_size = (200, 200)
small_img_size = (44, 44)
gray_img_size = (44, 44)

# Spacing and padding
spacing = 8
padding = 5

# Twig and branch configurations
twig_columns = 3
branch_rows = 2
tree_columns = 3

# Order for rearranging images (1-based indexing)
reorder = [6, 3, 2, 5, 4, 1]

# Function to create a twig
def create_twig(images, twig_index):
    twig_width = sum(img.size[0] for img in images) + (len(images) - 1) * spacing + 2 * padding
    twig_height = max(img.size[1] for img in images) + 2 * padding
    twig = Image.new('RGBA', (twig_width, twig_height), (0, 0, 0, 0))

    x_offset = padding
    for img in images:
        y_offset = (twig_height - img.size[1]) // 2
        twig.paste(img, (x_offset, y_offset))
        x_offset += img.size[0] + spacing

    twig.save(f'temp_part_twig_{twig_index}.png')
    return twig

# Function to create a branch
def create_branch(twigs, branch_index):
    branch_width = twig_columns * (twigs[0].size[0] + spacing) - spacing + 2 * padding
    branch_height = branch_rows * (twigs[0].size[1] + spacing) - spacing + 2 * padding
    branch = Image.new('RGBA', (branch_width, branch_height), (0, 0, 0, 0))

    for i, twig in enumerate(twigs):
        x_offset = padding + (i % twig_columns) * (twig.size[0] + spacing)
        y_offset = padding + (i // twig_columns) * (twig.size[1] + spacing)
        branch.paste(twig, (x_offset, y_offset))

    branch.save(f'temp_part_branch_{branch_index}.png')
    return branch

# Function to create a tree
def create_tree(branches):
    tree_width = tree_columns * (branches[0].size[0] + spacing) - spacing + 2 * padding
    tree_height = (len(branches) // tree_columns) * (branches[0].size[1] + spacing) - spacing + 2 * padding
    tree = Image.new('RGBA', (tree_width, tree_height), (0, 0, 0, 0))

    for i, branch in enumerate(branches):
        x_offset = padding + (i % tree_columns) * (branch.size[0] + spacing)
        y_offset = padding + (i // tree_columns) * (branch.size[1] + spacing)
        tree.paste(branch, (x_offset, y_offset))

    return tree

# Create twigs from images
twigs = []
image_files = [f for f in os.listdir(small_img_folder) if f.endswith('.png')][:6]  # Only consider the first 6 images
for i, order in enumerate(reorder):
    index = order - 1  # Adjust for 0-based indexing
    if index < len(image_files):
        filename = image_files[index]
        gray_img_path = os.path.join(gray_img_folder, filename)
        small_img_path = os.path.join(small_img_folder, filename)
        large_img_path = os.path.join(large_img_folder, filename)

        if os.path.exists(gray_img_path) and os.path.exists(large_img_path):
            gray_img = Image.open(gray_img_path).resize(gray_img_size)
            small_img = Image.open(small_img_path).resize(small_img_size)
            large_img = Image.open(large_img_path).resize(large_img_size, Image.BICUBIC)

            twig = create_twig([gray_img, small_img, large_img], i)
            twigs.append(twig)

# Create branches from twigs
branches = [create_branch(twigs[i:i + twig_columns * branch_rows], j) for j, i in enumerate(range(0, len(twigs), twig_columns * branch_rows))]

# Create a tree from branches
#tree = create_tree(branches)

# Save the final composite image
#tree.save(output_image)
