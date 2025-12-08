"""
ART MOD SELECTOR 
a UI for selecting art mods for ultima online classic 
an Image file to XML list generator for use with UOFiddler MassImport plugin 
For each BMP file name with a hexadecimal suffix, this tool writes the data to XML used to MassImport and a TXT file for the alternative method using Mulpatcher
by scanning the mod project folders for specific groups = "ART" , "UI" , and "ENV" 
to be sorted into the corresponding types = "item art_s" , "gump" , "texture" , "landtile art_m" 

TODO:
- fix the black line thru images form the components , add global variable to turn off display components to debug

TOOLSGROUP::INSTALL
SORTGROUP::1
SORTPRIORITY::1
STATUS::working
VERSION::20251207
"""
import os
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk
import re
import json

# GLOBAL
REGEX_HEXIDECIMAL = re.compile(r'(0x[0-9A-Fa-f]+)\.bmp$')
UI_IMAGE_WIDTH_MIN = 100
UI_IMAGE_WIDTH_MAX = 350
UI_IMAGE_HEIGHT_MIN = 30
UI_IMAGE_HEIGHT_MAX = 80
UI_IMAGE_WIDTH = 350
UI_IMAGE_HEIGHT = 80
CHECKBOX_ON_IMAGE_PATH = "./images/checkbox_on_image.png"
CHECKBOX_OFF_IMAGE_PATH = "./images/checkbox_off_image.png"
SKIP_FOLDERS = ['backup', 'ref', 'Upscale', 'original', 'remove', 'removed', 'temp' , 'completed' ,'paint','00_paint']  # Folders to skip during scanning

# UI padding 
PADX = 1
PADY = 1

# Mapping from category to TXT type for mulpatcher
CATEGORY_TO_TXT_SUFFIX = {
    "item": "ART_S",
    "landtile": "ART_M",
    "gump": "GUMP",
    "texture": "TEXTURE",
}

# ART
GROUPS_LEFT = {
    "Gems": {
        "images": [".././ART/ART_Gems/item_gem_00_comp.png"],
        "layout": "right",  
        "subgroups": {
            "Gems": {"path": ".././ART/ART_Gems", "default_state": True},
        }
    },
    "POTION": {
        "images": [".././ART/ART_Potions/00_item_potion_comp.png"],
        "layout": "right",
        "subgroups": {
            "Potion": {"path": ".././ART/ART_Potions", "default_state": True},
        }
    },
    "GemsRare": {
        "images": [".././ART/ART_GemRare/00_item_GemRare_compB.png",".././ART/ART_GemRare/00_item_gemRare_comp.png"],
        "layout": "right",
        "subgroups": {
            "Gems Rare": {"path": ".././ART/ART_GemRare", "default_state": True}
        }
    },
    "POTION Rare": {
        "images": [".././ART/ART_PotionsRare/00_item_PotionRare_comp.png"],
        "layout": "right",
        "subgroups": {
            "Potion Rare": {"path": ".././ART/ART_PotionsRare", "default_state": True}
        }
    },
    "Book": {
        "images": [".././ART/ART_Book/00_item_book_comp.png"],
        "layout": "right",
        "subgroups": {
            "Book": {"path": ".././ART/ART_Book", "default_state": True},
        }
    },
    "Food": {
        "images": [".././ART/ART_Food/00_item_food_comp_modded.png"],
        "layout": "right",
        "subgroups": {
            "Food": {"path": ".././ART/ART_Food", "default_state": True},
        }
    },
    "Fish": {
        "images": [".././ART/ART_Fish/00_item_fish_compB_modded.png"],
        "layout": "right",
        "subgroups": {
            "Fish": {"path": ".././ART/ART_Fish", "default_state": True}
        }
    },
    "Jewelry": {
        "images": [".././ART/ART_Jewelry/00_item_jewelry_comp.png"],
        "layout": "right",
        "subgroups": {
            "Jewelry": {"path": ".././ART/ART_Jewelry", "default_state": True}
        }
    },
    "Key": {
        "images": [".././ART/ART_Key/00_item_key_comp.png"],
        "layout": "right",
        "subgroups": {
            "Key": {"path": ".././ART/ART_Key", "default_state": True},
        }
    },
    "MagicScrolls": {
        "images": [".././ART/ART_MagicScrolls/item_scroll_00_magic_compB.jpg"],
        "layout": "right",
        "subgroups": {
            "Magic Scrolls": {"path": ".././ART/ART_MagicScrolls", "default_state": True},
        }
    },
    "PowerRare": {
        "images": [".././ART/ART_PowerRare/00_art_PowerRare_comp.png"],
        "layout": "right",
        "subgroups": {
            "PowerRare": {"path": ".././ART/ART_PowerRare", "default_state": True}
        }
    },
    "Reagent": {
        "images": [".././ART/ART_Reagents/00_item_reagent_comp.png"],
        "layout": "right",
        "subgroups": {
            "Reagents": {"path": ".././ART/ART_Reagents", "default_state": True}
        }
    },
    "ReagentPagan": {
        "images": [".././ART/ART_ReagentPagan/00_item_reagentPagan_comp.png"],
        "layout": "right",
        "subgroups": {
            "Reagents Pagan": {"path": ".././ART/ART_ReagentPagan", "default_state": True}
        }
    },
    "Resource": {
        "images": [".././ART/ART_Resource/00_item_resource_comp_long.png"],
        "layout": "right",
        "subgroups": {
            "Resource": {"path": ".././ART/ART_Resource", "default_state": True},
        }
    },
    "Talisman": {
        "images": [".././ART/ART_Talisman/00_item_talisman_comp.png"],
        "layout": "right",
        "subgroups": {
            "Talisman": {"path": ".././ART/ART_Talisman", "default_state": True}
        }
    },
    "Tools": {
        "images": [".././ART/ART_Tools/00_item_tool_00_comp.png",".././ART/ART_Tools/00_item_tool_00_comp_music.png"],
        "layout": "right",
        "subgroups": {
            "Tools": {"path": ".././ART/ART_Tools", "default_state": True}
        }
    },
    "Weapon": {
        "images": [".././ART/ART_Weapon/00_item_weapon_comp.png"],
        "layout": "right",
        "subgroups": {
            "Weapons": {"path": ".././ART/ART_Weapon", "default_state": True}
        }
    },
    "WeaponArchery": {
        "images": [".././ART/ART_WeaponArchery/00_ART_WeaponArchery_render.png"],
        "layout": "right",
        "subgroups": {
            "WeaponsArchery": {"path": ".././ART/ART_WeaponArchery", "default_state": True}
        }
    },
    "WeaponExpand": {
        "images": [".././ART/ART_WeaponExpand/00_ART_WeaponExpand_render.png"],
        "layout": "right",
        "subgroups": {
            "WeaponsExpand": {"path": ".././ART/ART_WeaponExpand", "default_state": True}
        }
    },
    "Vase": {
        "images": [".././ART/ART_Vase/00_item_vase_comp.png"],
        "layout": "right",
        "subgroups": {
            "Vase": {"path": ".././ART/ART_Vase", "default_state": True}
        }
    },
    "Creature": {
        "images": [".././ART/ART_Creature/00_item_creature_comp.png"],
        "layout": "right",
        "subgroups": {
            "Creature": {"path": ".././ART/ART_Creature", "default_state": True}
        }
    },
    "Wand": {
        "images": [".././ART/ART_Wand/00_item_wand_comp.png"],
        "layout": "right",
        "subgroups": {
            "Wand": {"path": ".././ART/ART_Wand", "default_state": True}
        }
    },
    "Eggs": {
        "images": [".././ART/ART_Eggs/00_item_egg_render.png"],
        "layout": "right",
        "subgroups": {
            "Eggs": {"path": ".././ART/ART_Eggs", "default_state": True}
        }
    },
    "ART_PowerSkillStone": {
        "images": [".././ART/ART_PowerSkillStone/00_ART_PowerSkillStone_render.png"],
        "layout": "right",
        "subgroups": {
            "SkillStone": {"path": ".././ART/ART_PowerSkillStone", "default_state": True}
        }
    },
    "ART_PowerChampionSpawn": {
        "images": [".././ART/ART_PowerChampionSpawn/00_ART_PowerChampionSpawn_render.png"],
        "layout": "right",
        "subgroups": {
            "ChampionSpawn": {"path": ".././ART/ART_PowerChampionSpawn", "default_state": True}
        }
    },
    "ART_Tree": {
        "images": [".././ART/ART_Tree/00_ART_Tree_render.png"],
        "layout": "right",
        "subgroups": {
            "Tree": {"path": ".././ART/ART_Tree", "default_state": True}
        }
    },
    "IconMastery": {
        "images": [".././UI/UI_Spellsmastery/00_ui_spell_mastery_comp.png"],
        "layout": "right",
        "subgroups": {
            "IconMastery": {"path": ".././ART/ART_IconMastery", "default_state": True}
        }
    },
    "IconMagicSpell": {
        "images": [".././UI/UI_MagicSpells/ui_spell_00_comp_nospace_wide.png"],
        "layout": "right",
        "subgroups": {
            "IconMagicSpell": {"path": ".././ART/ART_IconMagicSpell", "default_state": True}
        }
    }
}

# UI
GROUPS_MIDDLE = {
    "Magic Spells": {
        "images": [".././UI/UI_MagicSpells/ui_spell_00_comp_nospace_wide.png"],
        "layout": "right", 
        "subgroups": {
            "Magic Spells": {"path": ".././UI/UI_MagicSpells", "default_state": True},
            "Magic Effect": {"path": ".././UI/UI_MagicSpells/SpellEffects_Color", "default_state": True}
        }
    },
    "Chivalry": {
        "images": [".././UI/UI_SpellsChivalry/00_ui_spells_chivalry_comp.png"],
        "layout": "right",
        "subgroups": {
            "Chivalry": {"path": ".././UI/UI_SpellsChivalry", "default_state": True}
        }
    },
    "Necromancy": {
        "images": [".././UI/UI_SpellsNecromancy/00_ui_spells_necromancy_comp.png"],
        "layout": "right",
        "subgroups": {
            "Necromancy": {"path": ".././UI/UI_SpellsNecromancy", "default_state": True}
        }
    },
    "Mysticism": {
        "images": [".././UI/UI_SpellsMysticism/00_ui_spell_mysticism_comp.png"],
        "layout": "right",
        "subgroups": {
            "Mysticism": {"path": ".././UI/UI_SpellsMysticism", "default_state": True}
        }
    },
    "SpellsWeaving": {
        "images": [".././UI/UI_SpellsWeaving/00_ui_spell_weaving_comp.png"],
        "layout": "right",
        "subgroups": {
            "Spell Weaving": {"path": ".././UI/UI_SpellsWeaving", "default_state": True}
        }
    },
    "Bushido Spells": {
        "images": [".././UI/UI_SpellsBushido/00_ui_spell_bushido_comp.png"],
        "layout": "right",
        "subgroups": {
            "Bushido": {"path": ".././UI/UI_SpellsBushido", "default_state": True}
        }
    },
    "Ninjitsu Spells": {
        "images": [".././UI/UI_SpellsNinjitsu/00_ui_spell_ninjitsu_comp.png"],
        "layout": "right",
        "subgroups": {
            "Ninjitsu": {"path": ".././UI/UI_SpellsNinjitsu", "default_state": True}
        }
    },
    "Spells Mastery": {
        "images": [".././UI/UI_SpellsMastery/00_ui_spell_mastery_comp.png"],
        "layout": "right",
        "subgroups": {
            "Spells Mastery": {"path": ".././UI/UI_SpellsMastery", "default_state": True}
        }
    },
    "Spells Combat": {
        "images": [".././UI/UI_SpellsCombat/00_ui_spell_combat_comp.png"],
        "layout": "right",
        "subgroups": {
            "Spells Combat": {"path": ".././UI/UI_SpellsCombat", "default_state": True}
        }
    },
    "Spells Racial": {
        "images": [".././UI/UI_SpellsRacial/00_ui_spell_racial_comp.png"],
        "layout": "right",
        "subgroups": {
            "Spells Racial": {"path": ".././UI/UI_SpellsRacial", "default_state": True}
        }
    },
    "ArchStone Multi & Equip Slot": {  
        "images": [".././UI/UI_ArchStone_Multi/00_ui_archstone_multi_equipslots_comp.png"], 
        "layout": "below",
        "subgroups": {
            "ArchStone": {"path": ".././UI/UI_ArchStone", "default_state": False},
            "ArchStone Multi": {"path": ".././UI/UI_ArchStone_Multi", "default_state": True},
            "Equip Slots": {"path": ".././UI/UI_EquipSlots", "default_state": True}
        }
    },
    "Dark UI": {
        "images": [".././UI/UI_DarkScrolls/00_dark_scrolls_comp_wide.jpg"],
        "layout": "below",
        "subgroups": {
            "Dark Stats": {"path": ".././UI/UI_DarkStats", "default_state": False},
            "Dark Stats Long": {"path": ".././UI/UI_DarkStatsLong", "default_state": False},
            "Dark Stats Medium": {"path": ".././UI/UI_DarkStatsMedium", "default_state": True}
        }
    },
    "Dark Scrolls": {
        "images": [".././UI/UI_DarkScrolls/00_dark_scrolls_comp_wide.jpg"],
        "layout": "below",
        "subgroups": {
            "Dark Scrolls": {"path": ".././UI/UI_DarkScrolls", "default_state": True}
        }
    },
    "Buffs": {
        "images": [".././UI/UI_Buffs/ui_buff_00_comp_names_wide.jpg"],
        "layout": "right",
        "subgroups": {
            "Buffs": {"path": ".././UI/UI_Buffs", "default_state": True}
        }
    },
    "Equip Talisman": {
        "images": [".././ART/ART_Talisman/00_item_talisman_comp.png"],
        "layout": "right",
        "subgroups": {
            "Talisman Equipment": {"path": ".././UI/UI_EquipTalisman", "default_state": True}
        }
    },
    "Main Menu": {
        "images": [".././UI/UI_MainMenu/00_ui_menu_comp.png"],
        "layout": "right",
        "subgroups": {
            "Main Menu": {"path": ".././UI/UI_MainMenu", "default_state": True}
        }
    },
    "Dark Book": {  
        "images": [".././UI/UI_DarkBook/00_ui_dark_book_comp.png"], 
        "layout": "right",
        "subgroups": {
            "Dark Book": {"path": ".././UI/UI_DarkBook", "default_state": True},
        }
    },
    "Dark UI Extras": {  
        "images": [".././UI/UI_DarkFrame/00_ui_dark_frame_comp.png"],
        "layout": "below",
        "subgroups": {

            "Dark Frame": {"path": ".././UI/UI_DarkFrame", "default_state": True},
            "Dark Quest": {"path": ".././UI/UI_DarkQuest", "default_state": True},
            "Dark chat": {"path": ".././UI/UI_DarkChat", "default_state": True}
        }
    },
    "Profession": {
        "images": [".././UI/UI_Profession/00_ui_profession_comp.png"],  
        "layout": "right",
        "subgroups": {
            "Profession": {"path": ".././UI/UI_Profession", "default_state": True}
        }
    },
    "Light UI": {
        "images": [".././UI/UI_LightScrolls/00_dark_scrolls_comp_wide_light.jpg"],
        "layout": "below",
        "subgroups": {
            "Light Stats": {"path": ".././UI/UI_LightStats", "default_state": False},
            "Light Scrolls": {"path": ".././UI/UI_LightScrolls", "default_state": False}
        }
    },
    " Backpack": {
        "images": [".././UI/UI_BackPack/00_ui_container_backpack_comp.png"],
        "layout": "right",
        "subgroups": {
            "Backpack": {"path": ".././UI/UI_BackPack", "default_state": True},
            "BackpackStrapless": {"path": ".././UI/UI_BackPackStrapless", "default_state": False}
        }
    },
    "Eldritch Spells": {
        "images": [".././UI/UI_MagicSpells_Eldritch/ui_spell_comp_eldritch_magic.jpg"],
        "layout": "right",
        "subgroups": {
            "Eldritch Magic": {"path": ".././UI/UI_MagicSpells_Eldritch", "default_state": False}
        }
    },
    "MainMenuOrbs": {
        "images": [".././UI/UI_MainMenu_Orbs/00_ui_menu_orbs.jpg"],
        "layout": "right",
        "subgroups": {
            "MainMenuOrbs": {"path": ".././UI/UI_MainMenu_Orbs", "default_state": True}
        }
    },
    "TribalStaff": {
        "images": [".././UI/UI_EquipWeapon/00_ui_menu_orbs.jpg"],
        "layout": "right",
        "subgroups": {
            "TribalStaff": {"path": ".././UI/UI_EquipWeapon", "default_state": True}
        }
    }
}

# ENV
GROUPS_RIGHT = {
    "CaveDark": {
        "images": [".././ENV/ENV_CaveDark/00_env_cavedark_title.png"],
        "layout": "below",
        "subgroups": {
            "Cave Dark": {"path": ".././ENV/ENV_CaveDark", "default_state": True},
            "LandTiles": {"path": ".././ENV/ENV_CaveDark/ART_M", "default_state": True},
            "Items": {"path": ".././ENV/ENV_CaveDark/ART_S", "default_state": True}
        }
    },
    "DirtHills": {
        "images": [".././ENV/ENV_DirtHills/00_env_DirtHills_title.png"],
        "layout": "below",
        "subgroups": {
            "Dirt Hills": {"path": ".././ENV/ENV_DirtHills", "default_state": True},
            "LandTiles": {"path": ".././ENV/ENV_DirtHills/ART_M", "default_state": True}
        }
    },
    "ENV_FarmLands": {
        "images": [".././ENV/ENV_FarmLands/00_env_FarmLands_title.png"],
        "layout": "below",
        "subgroups": {
            "Farm Lands": {"path": ".././ENV/ENV_FarmLands", "default_state": True},
            "LandTiles": {"path": ".././ENV/ENV_FarmLands/ART_M", "default_state": True},
            "Items": {"path": ".././ENV/ENV_FarmLands/ART_S", "default_state": True}
        }
    },
    "ENV_ForestGrove": {
        "images": [".././ENV/ENV_ForestGrove/00_env_ForestGrove_title.png"],
        "layout": "below",
        "subgroups": {
            "Forest Grove": {"path": ".././ENV/ENV_ForestGrove", "default_state": True},
            "LandTiles": {"path": ".././ENV/ENV_ForestGrove/ART_M", "default_state": True},
            "Items": {"path": ".././ENV/ENV_ForestGrove/ART_S", "default_state": True}
        }
    },
    "ENV_MountainPath": {
        "images": [".././ENV/ENV_MountainPath/00_env_MountainPath_title.png"],
        "layout": "below",
        "subgroups": {
            "Mountain Path": {"path": ".././ENV/ENV_MountainPath", "default_state": True},
            "LandTiles": {"path": ".././ENV/ENV_MountainPath/ART_M", "default_state": True},
            "Items": {"path": ".././ENV/ENV_MountainPath/ART_S", "default_state": True}
        }
    },
    "ENV_SandDunes": {
        "images": [".././ENV/ENV_SandDunes/00_env_SandDunes_title.png"],
        "layout": "below",
        "subgroups": {
            "Sand Dunes": {"path": ".././ENV/ENV_SandDunes", "default_state": True},
            "LandTiles": {"path": ".././ENV/ENV_SandDunes/ART_M", "default_state": True},
            "Items": {"path": ".././ENV/ENV_SandDunes/ART_S", "default_state": True}
        }
    },
    "ENV_SnowRidge": {
        "images": [".././ENV/ENV_SnowRidge/00_env_SnowRidge_title.png"],
        "layout": "below",
        "subgroups": {
            "Snow Ridge": {"path": ".././ENV/ENV_SnowRidge", "default_state": True},
            "LandTiles": {"path": ".././ENV/ENV_SnowRidge/ART_M", "default_state": True}
        }
    },
    "ENV_HeartWood": {
        "images": [".././ENV/ENV_HeartWood/00_env_HeartWood_title.png"],
        "layout": "below",
        "subgroups": {
            "HeartWood": {"path": ".././ENV/ENV_HeartWood", "default_state": True},
            "LandTiles": {"path": ".././ENV/ENV_HeartWood/ART_M", "default_state": True},
            "Items": {"path": ".././ENV/ENV_HeartWood/ART_S", "default_state": True}
        }
    },
    "ENV_Paroxysmus": {
        "images": [".././ENV/ENV_Paroxysmus/00_env_Paroxysmus_title.png"],
        "layout": "below",
        "subgroups": {
            "Paroxysmus": {"path": ".././ENV/ENV_Paroxysmus", "default_state": True},
            "LandTiles": {"path": ".././ENV/ENV_Paroxysmus/ART_M", "default_state": True},
            "Items": {"path": ".././ENV/ENV_Paroxysmus/ART_S", "default_state": True}
        }
    },
}

# ImageCheckbox 
class ImageCheckbox(tk.Frame):
    def __init__(self, master, text, variable, on_image_path, off_image_path, **kwargs):
        super().__init__(master, bg='#3c3c3c', **kwargs)  

        self.variable = variable
        self.on_image = ImageTk.PhotoImage(Image.open(on_image_path))
        self.off_image = ImageTk.PhotoImage(Image.open(off_image_path))

        self.checkbox_image = tk.Label(self, bg='#3c3c3c') 
        self.checkbox_image.pack(side=tk.LEFT)
        self.checkbox_image.bind("<Button-1>", self.toggle)

        self.label = tk.Label(self, text=text, bg='#222222', fg='white') 
        self.label.pack(side=tk.LEFT)
        self.label.bind("<Button-1>", self.toggle)

        self.variable.trace("w", self.update_image)
        self.update_image()  

    def toggle(self, event=None):
        self.variable.set(not self.variable.get())

    def update_image(self, *args):
        if self.variable.get():
            self.checkbox_image.config(image=self.on_image)
        else:
            self.checkbox_image.config(image=self.off_image)

class BMPtoXMLConverter:
    def __init__(self, master):
        self.master = master
        self.master.title("MOD SELECTOR - BMP to MassImport XML for UOfiddler")
        self.master.configure(bg='#111111')
        self.export_states = []
        self.checkbox_states = {}
        self.json_group_paths = set()  # Track which paths come from JSON
        self.include_json_groups = tk.BooleanVar(value=False)  # Default OFF
        
        # Separate storage for hardcoded vs JSON groups
        self.groups_left_hardcoded = dict(GROUPS_LEFT)
        self.groups_middle_hardcoded = dict(GROUPS_MIDDLE)
        self.groups_right_hardcoded = dict(GROUPS_RIGHT)
        self.groups_left_json = {}
        self.groups_middle_json = {}
        self.groups_right_json = {}
        
        # Load JSON groups into separate storage
        self.load_json_groups()
        
        self.setup_ui()

        # Automatically derive the prefix (one folder up from script directory)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.prefix = os.path.abspath(os.path.join(script_dir, os.pardir))
        print(f"Prefix is set to: {self.prefix}")

    def setup_ui(self):
        print("Setting up UI...")
        self.frame = ttk.Frame(self.master, style='TFrame')
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Top button area - Export button and JSON checkbox on same line
        self.top_button_frame = ttk.Frame(self.frame, style='TFrame')
        self.top_button_frame.pack(pady=(PADY, PADY))
        
        # Status label (to the left of the button)
        self.status_label = tk.Label(
            self.top_button_frame,
            text="",
            bg='#111111',
            fg='#4ade80',  # Green color for success messages
            font=('Helvetica', 11, 'bold')
        )
        self.status_label.pack(side=tk.LEFT, padx=(0, 15))
        
        # Master Export Button
        self.master_export_button = ttk.Button(
            self.top_button_frame, text="Export All to MassImport XML",
            command=self.export_all_to_master_xml, style='Large.TButton'
        )
        self.master_export_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Checkbox for including JSON groups in export (to the right of button)
        self.json_groups_checkbox = ImageCheckbox(
            self.top_button_frame,
            text="Include Additional JSON Groups",
            variable=self.include_json_groups,
            on_image_path=CHECKBOX_ON_IMAGE_PATH,
            off_image_path=CHECKBOX_OFF_IMAGE_PATH
        )
        self.json_groups_checkbox.pack(side=tk.LEFT)
        
        # Add callback to reload UI when checkbox changes
        self.include_json_groups.trace('w', self.on_json_checkbox_changed)

        # Create the group areas using grid for better control
        self.groups_area = ttk.Frame(self.frame, style='TFrame')
        self.groups_area.pack(fill=tk.BOTH, expand=True)

        # Configure row and column weights for proper expansion
        self.groups_area.columnconfigure(0, weight=1)
        self.groups_area.columnconfigure(1, weight=2)
        self.groups_area.columnconfigure(2, weight=1)
        self.groups_area.rowconfigure(0, weight=1)

        # Create frames for each group area
        self.left_frame = ttk.Frame(self.groups_area, style='TFrame', borderwidth=0, relief='flat')
        self.middle_frame = ttk.Frame(self.groups_area, style='TFrame', borderwidth=0, relief='flat')
        self.right_frame = ttk.Frame(self.groups_area, style='TFrame', borderwidth=0, relief='flat')

        # Use grid to arrange the frames with padding to prevent dark lines
        self.left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 2))
        self.middle_frame.grid(row=0, column=1, sticky='nsew', padx=2)
        self.right_frame.grid(row=0, column=2, sticky='nsew', padx=(2, 0))

        # --- Vertical scrollbars only ---
        # Left group area with scrollbar
        self.left_scrollbar = ttk.Scrollbar(
            self.left_frame, orient='vertical', style='Vertical.TScrollbar'
        )
        self.left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.left_canvas = tk.Canvas(self.left_frame, bg='#111111', highlightthickness=0, bd=0, relief='flat',
                                      yscrollcommand=self.left_scrollbar.set)
        self.left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.left_scrollbar.config(command=self.left_canvas.yview)
        
        self.left_scrollable_frame = ttk.Frame(self.left_canvas, style='TFrame', borderwidth=0, relief='flat')
        left_window = self.left_canvas.create_window((0, 0), window=self.left_scrollable_frame, anchor='nw')

        def _left_configure(event):
            self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all"))
            # Set the window width to canvas width
            canvas_width = self.left_canvas.winfo_width()
            if canvas_width > 1:
                self.left_canvas.itemconfig(left_window, width=canvas_width)
        self.left_scrollable_frame.bind("<Configure>", _left_configure)
        self.left_canvas.bind("<Configure>", _left_configure)

        # Middle group area with scrollbar
        self.middle_scrollbar = ttk.Scrollbar(
            self.middle_frame, orient='vertical', style='Vertical.TScrollbar'
        )
        self.middle_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.middle_canvas = tk.Canvas(self.middle_frame, bg='#111111', highlightthickness=0, bd=0, relief='flat',
                                        yscrollcommand=self.middle_scrollbar.set)
        self.middle_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.middle_scrollbar.config(command=self.middle_canvas.yview)
        
        self.middle_scrollable_frame = ttk.Frame(self.middle_canvas, style='TFrame', borderwidth=0, relief='flat')
        middle_window = self.middle_canvas.create_window((0, 0), window=self.middle_scrollable_frame, anchor='nw')

        def _middle_configure(event):
            self.middle_canvas.configure(scrollregion=self.middle_canvas.bbox("all"))
            # Set the window width to canvas width
            canvas_width = self.middle_canvas.winfo_width()
            if canvas_width > 1:
                self.middle_canvas.itemconfig(middle_window, width=canvas_width)
        self.middle_scrollable_frame.bind("<Configure>", _middle_configure)
        self.middle_canvas.bind("<Configure>", _middle_configure)

        # Right group area with scrollbar
        self.right_scrollbar = ttk.Scrollbar(
            self.right_frame, orient='vertical', style='Vertical.TScrollbar'
        )
        self.right_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.right_canvas = tk.Canvas(self.right_frame, bg='#111111', highlightthickness=0, bd=0, relief='flat',
                                       yscrollcommand=self.right_scrollbar.set)
        self.right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.right_scrollbar.config(command=self.right_canvas.yview)
        
        self.right_scrollable_frame = ttk.Frame(self.right_canvas, style='TFrame', borderwidth=0, relief='flat')
        right_window = self.right_canvas.create_window((0, 0), window=self.right_scrollable_frame, anchor='nw')

        def _right_configure(event):
            self.right_canvas.configure(scrollregion=self.right_canvas.bbox("all"))
            # Set the window width to canvas width
            canvas_width = self.right_canvas.winfo_width()
            if canvas_width > 1:
                self.right_canvas.itemconfig(right_window, width=canvas_width)
        self.right_scrollable_frame.bind("<Configure>", _right_configure)
        self.right_canvas.bind("<Configure>", _right_configure)

        # --- Helper for mousewheel binding ---
        def _bind_mousewheel(canvas):
            def _on_mousewheel(event):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
                return "break"
            canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', _on_mousewheel))
            canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))

        _bind_mousewheel(self.left_canvas)
        _bind_mousewheel(self.middle_canvas)
        _bind_mousewheel(self.right_canvas)

        # Bind the scrollable frames to the canvases
        self.left_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all"))
        )
        self.middle_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.middle_canvas.configure(scrollregion=self.middle_canvas.bbox("all"))
        )
        self.right_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.right_canvas.configure(scrollregion=self.right_canvas.bbox("all"))
        )

        # Load groups into the scrollable frames based on checkbox state
        self.reload_all_groups()
        print("Groups loaded.")

    def get_wip_groups_json_path(self):
        """
        Returns the expected path for the optional external WIP groups JSON file.
        The file name is '00_mod_selector_wip_groups.json' and it should reside in the same
        directory as this script. If not present, no WIP groups are loaded.
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(script_dir, "00_mod_selector_wip_groups.json")

    def load_json_groups(self):
        """
        Load optional WIP groups from an external JSON file into separate storage.
        JSON schema example:
        {
          "left": { "GroupName": {"images": [...], "layout": "right|below", "subgroups": {"Name": {"path": "...", "default_state": true}} } },
          "middle": { ... },
          "right": { ... }
        }

        Behavior: Store JSON groups separately from hardcoded groups.
        """
        json_path = self.get_wip_groups_json_path()
        if not os.path.exists(json_path):
            print(f"No WIP groups JSON found at: {json_path}. Using hardcoded groups only.")
            return
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Failed to load WIP groups JSON ({json_path}): {e}")
            return

        def _load_json(src_dict, dst_dict, column_name):
            if not isinstance(src_dict, dict):
                print(f"WIP groups JSON: '{column_name}' is not a dict. Skipping.")
                return
            for group_key, group_val in src_dict.items():
                # Only add if not in hardcoded groups
                if group_key in self.groups_left_hardcoded or group_key in self.groups_middle_hardcoded or group_key in self.groups_right_hardcoded:
                    print(f"WIP group '{group_key}' already exists in hardcoded {column_name}; not loading.")
                    continue
                dst_dict[group_key] = group_val
                # Track all subgroup paths from JSON
                if 'subgroups' in group_val:
                    for subgroup_info in group_val['subgroups'].values():
                        if 'path' in subgroup_info:
                            self.json_group_paths.add(subgroup_info['path'])

        _load_json(data.get('left', {}), self.groups_left_json, 'left')
        _load_json(data.get('middle', {}), self.groups_middle_json, 'middle')
        _load_json(data.get('right', {}), self.groups_right_json, 'right')
    
    def on_json_checkbox_changed(self, *args):
        """Callback when the Include JSON Groups checkbox changes state."""
        print(f"JSON checkbox changed to: {self.include_json_groups.get()}")
        self.reload_all_groups()
    
    def reload_all_groups(self):
        """Reload all groups based on current checkbox state."""
        # Clear existing groups from UI
        for widget in self.left_scrollable_frame.winfo_children():
            widget.destroy()
        for widget in self.middle_scrollable_frame.winfo_children():
            widget.destroy()
        for widget in self.right_scrollable_frame.winfo_children():
            widget.destroy()
        
        # Clear checkbox states
        self.checkbox_states.clear()
        self.export_states.clear()
        
        # Determine which groups to show
        include_json = self.include_json_groups.get()
        
        if include_json:
            # Merge hardcoded and JSON groups
            groups_left = {**self.groups_left_hardcoded, **self.groups_left_json}
            groups_middle = {**self.groups_middle_hardcoded, **self.groups_middle_json}
            groups_right = {**self.groups_right_hardcoded, **self.groups_right_json}
            print("Loading hardcoded + JSON groups")
        else:
            # Only hardcoded groups
            groups_left = dict(self.groups_left_hardcoded)
            groups_middle = dict(self.groups_middle_hardcoded)
            groups_right = dict(self.groups_right_hardcoded)
            print("Loading hardcoded groups only")
        
        # Load groups into UI
        self.load_groups(self.left_scrollable_frame, groups_left)
        self.load_groups(self.middle_scrollable_frame, groups_middle)
        self.load_groups(self.right_scrollable_frame, groups_right)

    def load_groups(self, parent, groups):
        print(f"Loading groups into {parent}...")
        for group_name, group_info in groups.items():
            print(f"Adding group section: {group_name}")
            self.add_group_section(parent, group_name, group_info)

    def add_group_section(self, parent, group_name, group_info):
        print(f"Adding group section for {group_name}...")
        section_frame = ttk.Frame(parent, style='NoBorder.TFrame')
        section_frame.pack(fill=tk.BOTH, padx=PADX, pady=PADY)

        layout = group_info.get("layout", "right").lower()
        images = group_info.get("images", [])

        image_labels = []
        image_paths = []
        for image_path in images:
            if image_path and os.path.exists(image_path):
                print(f"Loading image for {group_name}: {image_path}")
                # Initial thumbnail, will be resized later
                img = Image.open(image_path)
                img.thumbnail((UI_IMAGE_WIDTH, UI_IMAGE_HEIGHT), Image.Resampling.LANCZOS)
                section_image = ImageTk.PhotoImage(img)
                image_label = ttk.Label(section_frame, image=section_image, style='NoBorder.TLabel')
                image_label.image = section_image
                image_labels.append(image_label)
                image_paths.append(image_path)
            else:
                print(f"Image not found: {image_path}")

        if layout == "below":
            row = 0
            for img_label in image_labels:
                img_label.grid(row=row, column=0, columnspan=20, pady=PADY, sticky='n')
                row += 1
            subgroups = group_info.get("subgroups", {})
            num_subgroups = len(subgroups)
            canvas = section_frame.master.master  # the canvas
            try:
                available_width = canvas.winfo_width()
            except:
                available_width = 800
            min_entry_width = 120
            max_cols = max(1, min(6, available_width // min_entry_width))
            if max_cols < 1:
                max_cols = 6
            col = 0
            subgroup_widgets = []
            for i, (subgroup_name, subgroup_info) in enumerate(subgroups.items()):
                subgroup_widget = self.add_subgroup_entry(
                    section_frame, subgroup_name, subgroup_info,
                    layout=layout
                )
                subgroup_widgets.append(subgroup_widget)
                subgroup_widget.grid(row=row + (col // max_cols), column=col % max_cols, padx=PADX, pady=PADY, sticky='ew')
                col += 1
            for i in range(max_cols):
                section_frame.columnconfigure(i, weight=1)
        else:
            # Only image column gets weight, label/button column does not expand
            section_frame.columnconfigure(0, weight=1)
            section_frame.columnconfigure(1, weight=0)
            image_frame = ttk.Frame(section_frame, style='NoBorder.TFrame')
            image_frame.grid(row=0, column=0, padx=(PADX, 6), pady=PADY, sticky='ns')
            subgroup_frame = ttk.Frame(section_frame, style='NoBorder.TFrame')
            subgroup_frame.grid(row=0, column=1, padx=(6, PADX), pady=PADY, sticky='ns')
            section_frame.rowconfigure(0, weight=1)
            # Add subgroup entries (label/button area)
            subgroups = group_info.get("subgroups", {})
            row = 0
            for subgroup_name, subgroup_info in subgroups.items():
                subgroup_widget = self.add_subgroup_entry(
                    subgroup_frame, subgroup_name, subgroup_info,
                    layout=layout
                )
                subgroup_widget.grid(row=row, column=0, padx=PADX, pady=PADY, sticky='n')
                row += 1
            # Calculate section width for 3-column layout
            window_width = self.master.winfo_width() if hasattr(self, 'master') else 1200
            section_width = max(300, window_width // 3)
            # Estimate minimum label/button width
            subgroup_frame.update_idletasks()
            min_label_width = max(160, subgroup_frame.winfo_reqwidth())
            # Leave some padding between image and label/button area
            available_img_width = max(80, section_width - min_label_width - 2*PADX)
            # Debounced image resizing based on section_frame height and available_img_width
            def _resize_image_on_section(event=None):
                h = section_frame.winfo_height()
                if not hasattr(section_frame, '_last_img_height') or section_frame._last_img_height != h:
                    if h and h > 8:
                        for i, img_label in enumerate(image_labels):
                            img_path = image_paths[i]
                            if os.path.exists(img_path):
                                img = Image.open(img_path)
                                img.thumbnail((available_img_width, min(h, UI_IMAGE_HEIGHT_MAX)), Image.Resampling.LANCZOS)
                                section_image = ImageTk.PhotoImage(img)
                                img_label.configure(image=section_image)
                                img_label.image = section_image
                        section_frame._last_img_height = h
            section_frame.bind("<Configure>", _resize_image_on_section)
            for i, img_label in enumerate(image_labels):
                img_label.grid(row=i, column=0, pady=PADY, sticky='ns')
            for idx in range(len(image_labels)):
                image_frame.rowconfigure(idx, weight=1)

    def add_subgroup_entry(self, parent, subgroup_name, subgroup_info, layout):
        print(f"Adding subgroup entry for {subgroup_name}...")
        default_state = subgroup_info.get("default_state", True)
        state = tk.BooleanVar(value=default_state)
        self.export_states.append(state)
        self.checkbox_states[(subgroup_info["path"])] = state

        # Frame to hold the subgroup elements
        subgroup_frame = ttk.Frame(parent, style='NoBorder.TFrame', borderwidth=0, relief="flat")

        if layout == 'right':
            subgroup_frame.columnconfigure(0, weight=1)
            export_check = ImageCheckbox(
                subgroup_frame, text=subgroup_name, variable=state,
                on_image_path=CHECKBOX_ON_IMAGE_PATH, off_image_path=CHECKBOX_OFF_IMAGE_PATH
            )
            export_check.grid(row=0, column=0, sticky='ew')
            export_button = ttk.Button(
                subgroup_frame, text="Export",
                command=lambda p=subgroup_info["path"], s=state: self.export_individual_group(p, s),
                style='Flat.TButton'
            )
            export_button.grid(row=1, column=0, padx=PADX, pady=PADY, sticky='ew')
        else:
            subgroup_frame.columnconfigure(0, weight=1)
            subgroup_frame.columnconfigure(1, weight=0)
            export_check = ImageCheckbox(
                subgroup_frame, text=subgroup_name, variable=state,
                on_image_path=CHECKBOX_ON_IMAGE_PATH, off_image_path=CHECKBOX_OFF_IMAGE_PATH
            )
            export_check.grid(row=0, column=0, sticky='ew')
            export_button = ttk.Button(
                subgroup_frame, text="Export",
                command=lambda p=subgroup_info["path"], s=state: self.export_individual_group(p, s),
                style='Flat.TButton'
            )
            export_button.grid(row=0, column=1, padx=PADX, sticky='ew')

        return subgroup_frame

    def show_status(self, message):
        """Display a status message permanently."""
        self.status_label.config(text=message)
    
    def export_individual_group(self, folder_path, state):
        if state.get():
            self.process_bmp_files_to_XML(folder_path)
            folder_name = os.path.basename(folder_path)
            self.show_status(f"✓ Exported: {folder_name}")


    def export_all_groups(self):
        count = 0
        for path, state_var in self.checkbox_states.items():
            if state_var.get():
                self.process_bmp_files_to_XML(path)
                count += 1
        self.show_status(f"✓ Exported {count} group(s) successfully")

    def export_all_to_master_xml(self):
        all_xml_entries = []
        master_txt_data = {}  # Dictionary to hold txt lines for each master txt file

        for path, state_var in self.checkbox_states.items():
            if state_var.get():
                # No need to check JSON status here - if checkbox is OFF, JSON groups won't be in checkbox_states
                result = self.process_bmp_files_to_XML(path)
                if result:
                    xml_entries = result['xml_entries']
                    txt_lines_master = result['txt_lines_master']
                    master_txt_filename = result['master_txt_filename']
                    all_xml_entries.extend(xml_entries)
                    if master_txt_filename:
                        if master_txt_filename not in master_txt_data:
                            master_txt_data[master_txt_filename] = []
                        master_txt_data[master_txt_filename].extend(txt_lines_master)

        if all_xml_entries:
            # Build the MassImport XML content
            xml_content = "<MassImport>\n"
            xml_content += ''.join(all_xml_entries)
            xml_content += "</MassImport>\n"

            # Write to MassImport XML file
            xml_output_path = os.path.join(self.prefix, "00_ART_MODS_MassImport.xml")
            with open(xml_output_path, 'w') as xml_file:
                xml_file.write(xml_content)
            print(f"Created MassImport XML file: {xml_output_path}")

            # Write MassImport TXT files
            for master_txt_filename, txt_lines in master_txt_data.items():
                txt_output_path = os.path.join(self.prefix, master_txt_filename)
                with open(txt_output_path, 'w') as txt_file:
                    txt_file.write('\n'.join(txt_lines))
                print(f"Created mulpatcher autopatch TXT file: {txt_output_path}")

            self.show_status(f"✓ MassImport XML created successfully ({len(all_xml_entries)} entries)")
        else:
            self.show_status("⚠ No XML entries generated")

    def determine_category_and_master_txt(self, folder_path):
        normalized_path = folder_path.replace("\\", "/").lower()
        category = "unknown"
        master_txt_filename = None

        if "/ui/" in normalized_path:
            category = "gump"
            master_txt_filename = "00_UI_ALL_GUMP.txt"
        elif "/art/" in normalized_path:
            category = "item"
            master_txt_filename = "00_ART_ALL_ART_S.txt"
        elif "/env/" in normalized_path:
            if "/art_m" in normalized_path:
                category = "landtile"
                master_txt_filename = "00_ENV_ALL_ART_M.txt"
            elif "/art_s" in normalized_path:
                category = "item"
                master_txt_filename = "00_ENV_ALL_ART_S.txt"
            else:
                category = "texture"
                master_txt_filename = "00_ENV_ALL_TEX.txt"
        print(
            f"Determined category '{category}' and master TXT file '{master_txt_filename}' "
            f"for path '{folder_path}'"
        )
        return category, master_txt_filename

    def process_bmp_files_to_XML(self, folder_path):
        if not os.path.exists(folder_path):
            print(f"Folder {folder_path} does not exist.")
            return None

        category, master_txt_filename = self.determine_category_and_master_txt(folder_path)
        category_txt_suffix = CATEGORY_TO_TXT_SUFFIX.get(category, category.upper())

        group_folder_name = os.path.basename(folder_path)

        xml_entries = []
        txt_lines_subgroup = []
        txt_lines_master = []

        try:
            files = os.listdir(folder_path)
        except Exception as e:
            print(f"Error accessing folder {folder_path}: {e}")
            return None

        for filename in files:
            file_path = os.path.join(folder_path, filename)
            if os.path.isdir(file_path):
                continue
            if REGEX_HEXIDECIMAL.search(filename):
                match = REGEX_HEXIDECIMAL.search(filename)
                bmp_path = file_path
                item_id_str = match.group(1)
                try:
                    item_id = int(item_id_str, 16)
                except ValueError:
                    print(f"Invalid item ID in filename {filename}")
                    continue

                relative_bmp_path = os.path.relpath(bmp_path, self.prefix)
                new_file_path = os.path.join(self.prefix, relative_bmp_path)

                xml_entry = f'  <{category} index="{item_id}" file="{new_file_path}" remove="False" />\n'
                xml_entries.append(xml_entry)

                txt_line_subgroup = f"{item_id_str} {filename}"
                txt_lines_subgroup.append(txt_line_subgroup)

                txt_line_master = f"{item_id_str} {relative_bmp_path}"
                txt_lines_master.append(txt_line_master)

        if not xml_entries:
            print(f"No BMP files found with hexadecimal suffix in {folder_path}.")
            return None

        xml_content = "<MassImport>\n"
        xml_content += ''.join(xml_entries)
        xml_content += "</MassImport>\n"

        xml_filename = f"00_{group_folder_name}_{category}.xml"
        xml_output_path = os.path.join(folder_path, xml_filename)
        with open(xml_output_path, 'w') as xml_file:
            xml_file.write(xml_content)
        print(f"Created XML file: {xml_output_path}")

        txt_suffix = CATEGORY_TO_TXT_SUFFIX.get(category, category.upper())
        txt_filename = f"00_{group_folder_name}_{txt_suffix}.txt"
        txt_output_path = os.path.join(folder_path, txt_filename)
        with open(txt_output_path, 'w') as txt_file:
            txt_file.write('\n'.join(txt_lines_subgroup))
        print(f"Created subgroup TXT file: {txt_output_path}")

        return {
            'xml_entries': xml_entries,
            'txt_lines_master': txt_lines_master,
            'master_txt_filename': master_txt_filename
        }

 # Main UI
if __name__ == "__main__":
    root = tk.Tk()
    root.minsize(600, 400)  # Allow resizing, but set a reasonable minimum
    
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('TFrame', background='#111111', bordercolor='#111111', borderwidth=0, relief='flat')
    style.configure('NoBorder.TFrame', background='#111111', borderwidth=0, relief='flat')
    style.configure('Large.TButton', background='#3c3c3c', foreground='white', borderwidth=0,
                    font=('Helvetica', 12), bordercolor='#000000')
    style.configure('Flat.TButton', background='#3c3c3c', foreground='white', borderwidth=0, relief='flat',
                    font=('Helvetica', 12), bordercolor='#000000', highlightthickness=0)
    style.configure('Large.TCheckbutton', background='#111111', foreground='white',
                    font=('Helvetica', 12), bordercolor='#000000', borderwidth=0)
    style.configure('TLabel', background='#000000', foreground='white',
                    font=('Helvetica', 12), bordercolor='#000000', borderwidth=0)
    style.configure('NoBorder.TLabel', background='#000000', foreground='white', borderwidth=0, relief='flat')
    style.configure('DarkGrey.TLabel', background='#000000', foreground='grey',
                    font=('Helvetica', 12), bordercolor='#000000', borderwidth=0)
    style.configure('TEntry', fieldbackground='#3c3c3c', foreground='gray',
                    font=('Helvetica', 12), bordercolor='#000000', borderwidth=0)
    style.configure('Large.TEntry', fieldbackground='#000000', foreground='white',
                    font=('Helvetica', 16), bordercolor='#000000', borderwidth=0)
    
    # Scrollbar styling - dark mode with black background and muted blue arrows
    style.configure('Vertical.TScrollbar', background='#1a1a1a', troughcolor='#000000', 
                    bordercolor='#000000', arrowcolor='#5a7a9a', relief='flat', borderwidth=0)
    style.configure('Horizontal.TScrollbar', background='#1a1a1a', troughcolor='#000000',
                    bordercolor='#000000', arrowcolor='#5a7a9a', relief='flat', borderwidth=0)
    style.map('Vertical.TScrollbar', background=[('active', '#2a3a4a'), ('pressed', '#3a4a5a')])
    style.map('Horizontal.TScrollbar', background=[('active', '#2a3a4a'), ('pressed', '#3a4a5a')])

    app = BMPtoXMLConverter(root)
    print("start")
    # Maximize window after all UI setup
    root.state('zoomed')
    root.mainloop()