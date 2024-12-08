# SAVE COMPOSITE IMAGE OF MAGIC SCROLLS 
# wide nospace format , using tree > branch > twig > leaf metaphor to control arrangement 
# 2 columns holding 4 images each of spell groups 1-8 , spells arranged in 8 columns 
# leaf = scrolls 1-4 and 5-8 stored vertically  , twig = 2 columns of leafs , branch = spell scroll level arranged as 8 columns
import os
import re
from PIL import Image, ImageDraw, ImageFont
from psd_tools import PSDImage

# Constants
IMAGE_OUTPUT = "00_item_scroll_comp_nospace_wide.png"

# Padding parameters
LEAF_PADDING = 1
TWIG_PADDING = 1
BRANCH_PADDING = 1

# Define the number of groups and images per group
NUM_GROUPS = 8  # Spell circle levels
IMAGES_PER_GROUP = 8  # Spells per circle

# Size of each image
IMAGE_WIDTH, IMAGE_HEIGHT = 44, 32

# Regex pattern to parse filenames
PATTERN = re.compile(r'item_scroll_(\d+)_(.+)_(0x[\dA-Fa-f]+)\.psd')

# Font settings for the numbers
FONT_SIZE = 20
FONT_COLOR = (64, 64, 64, 255)  # Dark grey
# Update FONT_PATH to an available font on your system
FONT_PATH = "C:/Windows/Fonts/arial.ttf"  # Adjust this path as needed


def get_expected_images():
    """
    Parses the provided list of expected images.
    Returns a list of tuples: (circle, spell_name, code).
    """
    expected_images = []
    list_data = '''
    0x1F2E item_scroll_1_Clumsy_0x1F2E
    0x1F2F item_scroll_1_CreateFood_0x1F2F
    0x1F30 item_scroll_1_Feeblemind_0x1F30
    0x1F31 item_scroll_1_Heal_0x1F31
    0x1F32 item_scroll_1_MagicArrow_0x1F32
    0x1F33 item_scroll_1_NightSight_0x1F33
    0x1F2D item_scroll_1_ReactiveArmor_0x1F2D
    0x1F34 item_scroll_1_Weaken_0x1F34
    0x1F35 item_scroll_2_Agility_0x1F35
    0x1F36 item_scroll_2_Cunning_0x1F36
    0x1F37 item_scroll_2_Cure_0x1F37
    0x1F38 item_scroll_2_Harm_0x1F38
    0x1F39 item_scroll_2_MagicTrap_0x1F39
    0x1F3A item_scroll_2_MagicUnTrap_0x1F3A
    0x1F3B item_scroll_2_Protection_0x1F3B
    0x1F3C item_scroll_2_Strength_0x1F3C
    0x1F3D item_scroll_3_Bless_0x1F3D
    0x1F3E item_scroll_3_Fireball_0x1F3E
    0x1F3F item_scroll_3_MagicLock_0x1F3F
    0x1F40 item_scroll_3_Poison_0x1F40
    0x1F41 item_scroll_3_Telekinisis_0x1F41
    0x1F42 item_scroll_3_Teleport_0x1F42
    0x1F43 item_scroll_3_Unlock_0x1F43
    0x1F44 item_scroll_3_WallOfStone_0x1F44
    0x1F45 item_scroll_4_ArchCure_0x1F45
    0x1F46 item_scroll_4_ArchProtection_0x1F46
    0x1F47 item_scroll_4_Curse_0x1F47
    0x1F48 item_scroll_4_FireField_0x1F48
    0x1F49 item_scroll_4_GreaterHeal_0x1F49
    0x1F4A item_scroll_4_Lightning_0x1F4A
    0x1F4B item_scroll_4_ManaDrain_0x1F4B
    0x1F4C item_scroll_4_Recall_0x1F4C
    0x1F4D item_scroll_5_BladeSpirits_0x1F4D
    0x1F4E item_scroll_5_DispelField_0x1F4E
    0x1F4F item_scroll_5_Incognito_0x1F4F
    0x1F50 item_scroll_5_MagicReflect_0x1F50
    0x1F51 item_scroll_5_MindBlast_0x1F51
    0x1F52 item_scroll_5_Paralyze_0x1F52
    0x1F53 item_scroll_5_PoisonField_0x1F53
    0x1F54 item_scroll_5_SummonCreature_0x1F54
    0x1F55 item_scroll_6_Dispel_0x1F55
    0x1F56 item_scroll_6_EnergyBolt_0x1F56
    0x1F57 item_scroll_6_Explosion_0x1F57
    0x1F58 item_scroll_6_Invisibility_0x1F58
    0x1F59 item_scroll_6_Mark_0x1F59
    0x1F5A item_scroll_6_MassCurse_0x1F5A
    0x1F5B item_scroll_6_ParalyzeField_0x1F5B
    0x1F5C item_scroll_6_Reveal_0x1F5C
    0x1F5D item_scroll_7_ChainLightning_0x1F5D
    0x1F5E item_scroll_7_EnergyField_0x1F5E
    0x1F5F item_scroll_7_Flamestrike_0x1F5F
    0x1F60 item_scroll_7_GateTravel_0x1F60
    0x1F61 item_scroll_7_ManaVampire_0x1F61
    0x1F62 item_scroll_7_MassDispel_0x1F62
    0x1F63 item_scroll_7_MeteorSwarm_0x1F63
    0x1F64 item_scroll_7_Polymorph_0x1F64
    0x1F65 item_scroll_8_Earthquake_0x1F65
    0x1F66 item_scroll_8_EnergyVortex_0x1F66
    0x1F67 item_scroll_8_Resurrection_0x1F67
    0x1F68 item_scroll_8_SummonAirElemental_0x1F68
    0x1F69 item_scroll_8_SummonDaemon_0x1F69
    0x1F6A item_scroll_8_SummonEarthElemental_0x1F6A
    0x1F6B item_scroll_8_SummonFireElemental_0x1F6B
    0x1F6C item_scroll_8_SummonWaterElemental_0x1F6C
    '''
    for line in list_data.strip().split('\n'):
        parts = line.strip().split()
        if len(parts) == 2:
            code = parts[0]
            filename = parts[1]
            match = PATTERN.match(filename + '.psd')  # Adding .psd to match the pattern
            if match:
                circle = int(match.group(1))
                spell_name = match.group(2)
                expected_images.append((circle, spell_name, code))
    return expected_images


def load_images():
    """
    Load images from PSD files and group them by circle (spell level).
    Returns a dictionary with circle as key and a list of images as value.
    Each image is a tuple: (spell_name, code, image).
    """
    group_images = {}
    for filename in os.listdir('.'):
        match = PATTERN.match(filename)
        if match:
            circle = int(match.group(1))
            spell_name = match.group(2)
            code = match.group(3)
            try:
                psd = PSDImage.open(filename)
                img = psd.composite().convert('RGBA')
                group_images.setdefault(circle, []).append((spell_name, code, img))
                print(f"Loaded image: Circle {circle}, Spell '{spell_name}', Code {code}")
            except Exception as e:
                print(f'Error processing {filename}: {e}')
    # Now sort images within each circle
    for circle in group_images:
        group_images[circle].sort(key=lambda x: int(x[1], 16))  # Sort by hex code
        print(f"Circle {circle} has {len(group_images[circle])} images.")
    return group_images


def create_leaves(group_images):
    """
    For each circle, split images into leaves (scrolls 1-4 and 5-8).
    Returns a dictionary with circle as key and a list of leaves as value.
    Each leaf is an Image object.
    """
    leaves = {}
    for circle, images in group_images.items():
        if len(images) != IMAGES_PER_GROUP:
            print(f'Circle {circle} does not have {IMAGES_PER_GROUP} images.')
            continue
        print(f"Creating leaves for Circle {circle}")
        first_half = images[:4]
        second_half = images[4:]
        # Create leaf1
        leaf1_height = IMAGE_HEIGHT * 4 + LEAF_PADDING * 3
        leaf1 = Image.new('RGBA', (IMAGE_WIDTH, leaf1_height))
        for i, (spell_name, code, img) in enumerate(first_half):
            y_position = i * (IMAGE_HEIGHT + LEAF_PADDING)
            leaf1.paste(img, (0, y_position))
            print(f"Placed '{spell_name}' (Code {code}) in Leaf 1 at position {i}")
        # Create leaf2
        leaf2_height = IMAGE_HEIGHT * 4 + LEAF_PADDING * 3
        leaf2 = Image.new('RGBA', (IMAGE_WIDTH, leaf2_height))
        for i, (spell_name, code, img) in enumerate(second_half):
            y_position = i * (IMAGE_HEIGHT + LEAF_PADDING)
            leaf2.paste(img, (0, y_position))
            print(f"Placed '{spell_name}' (Code {code}) in Leaf 2 at position {i}")
        leaves[circle] = [leaf1, leaf2]
    return leaves


def create_number_image(number, width):
    """
    Creates an image with the given number centered horizontally.
    """
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    text = str(number)
    # Create a blank image
    img_height = FONT_SIZE + 10
    img = Image.new('RGBA', (width, img_height), (255, 255, 255, 0))  # Transparent background
    draw = ImageDraw.Draw(img)
    # Use font.getbbox() to get text size
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (img_height - text_height) // 2 - bbox[1]  # Adjust y-position
    draw.text((x, y), text, font=font, fill=FONT_COLOR)
    return img



def create_twigs(leaves):
    """
    For each circle, create a twig by combining the circle number and two leaves vertically.
    Returns a dictionary with circle as key and twig Image as value.
    """
    twigs = {}
    for circle, leaf_pair in leaves.items():
        leaf1, leaf2 = leaf_pair
        # Create number image
        twig_width = IMAGE_WIDTH * 2 + TWIG_PADDING
        number_img = create_number_image(circle, twig_width)
        number_height = number_img.height
        # The total height is number image + leaves height
        twig_height = number_height + leaf1.height
        twig = Image.new('RGBA', (twig_width, twig_height))
        # Paste number image
        twig.paste(number_img, (0, 0), number_img)
        # Paste leaves
        y_offset = number_height
        twig.paste(leaf1, (0, y_offset))
        twig.paste(leaf2, (IMAGE_WIDTH + TWIG_PADDING, y_offset))
        twigs[circle] = twig
        print(f"Created twig for Circle {circle}")
    return twigs


def assemble_final_image(twigs):
    """
    Arrange the twigs (one per circle) side by side to create the final composite image.
    """
    num_circles = len(twigs)
    twig_width = IMAGE_WIDTH * 2 + TWIG_PADDING
    # Assuming all twigs have the same height
    sample_twig = next(iter(twigs.values()))
    twig_height = sample_twig.height
    total_width = num_circles * (twig_width + BRANCH_PADDING) - BRANCH_PADDING
    total_height = twig_height
    final_image = Image.new('RGBA', (total_width, total_height))
    x_offset = 0
    for circle in sorted(twigs.keys()):
        twig = twigs[circle]
        final_image.paste(twig, (x_offset, 0))
        x_offset += twig_width + BRANCH_PADDING
    return final_image


def main():
    expected_images = get_expected_images()
    expected_set = set((circle, spell_name, code) for circle, spell_name, code in expected_images)
    group_images = load_images()
    loaded_set = set()
    for circle, images in group_images.items():
        for spell_name, code, img in images:
            loaded_set.add((circle, spell_name, code))
    missing_images = expected_set - loaded_set
    extra_images = loaded_set - expected_set
    if missing_images:
        print("Missing images:")
        for circle, spell_name, code in missing_images:
            print(f"Circle {circle}, Spell '{spell_name}', Code {code}")
    else:
        print("All expected images are loaded.")
    if extra_images:
        print("Extra images (not expected):")
        for circle, spell_name, code in extra_images:
            print(f"Circle {circle}, Spell '{spell_name}', Code {code}")
    leaves = create_leaves(group_images)
    twigs = create_twigs(leaves)
    final_image = assemble_final_image(twigs)
    final_image.save(IMAGE_OUTPUT)
    print(f"Composite image saved as {IMAGE_OUTPUT}")


if __name__ == "__main__":
    main()
