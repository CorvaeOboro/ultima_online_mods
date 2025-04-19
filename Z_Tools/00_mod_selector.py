# ART MOD SELECTOR - BMP data to XML Converter for use with UOFiddler MassImport plugin 
# For each BMP file name with a hexadecimal suffix, write the data to XML and a TXT file.
# scans project folders by specific groups "ART" , "UI" , and "ENV" 
# to be sorted into the corresponding asset types "item art_s" , "gump" , "texture" , "landtile art_m"  

import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk
import re

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

# Mapping from category to TXT asset type for mulpatcher
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
            "PowerRare": {"path": ".././ART/ART_PowerRare/SpellEffcts_Color", "default_state": True}
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
            "Dark Stats Long": {"path": ".././UI/UI_DarkStatsLong", "default_state": True},
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
        self.setup_ui()

        # Automatically derive the prefix (one folder up from script directory)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.prefix = os.path.abspath(os.path.join(script_dir, os.pardir))
        print(f"Prefix is set to: {self.prefix}")

    def setup_ui(self):
        print("Setting up UI...")
        self.frame = ttk.Frame(self.master, style='TFrame')
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Master Export Button
        self.master_export_button = ttk.Button(
            self.frame, text="Export All to MassImport XML",
            command=self.export_all_to_master_xml, style='Large.TButton'
        )
        self.master_export_button.pack(pady=(PADY, PADY))

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

        # Use grid to arrange the frames
        self.left_frame.grid(row=0, column=0, sticky='nsew')
        self.middle_frame.grid(row=0, column=1, sticky='nsew')
        self.right_frame.grid(row=0, column=2, sticky='nsew')

        # --- Add horizontal scrollbars ---
        # Left group area with scrollbars
        self.left_canvas = tk.Canvas(self.left_frame, bg='#111111', highlightthickness=0)
        self.left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.left_scrollbar = ttk.Scrollbar(
            self.left_frame, orient='vertical', command=self.left_canvas.yview
        )
        self.left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.left_hscrollbar = ttk.Scrollbar(
            self.left_frame, orient='horizontal', command=self.left_canvas.xview
        )
        self.left_hscrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.left_canvas.configure(yscrollcommand=self.left_scrollbar.set, xscrollcommand=self.left_hscrollbar.set)
        self.left_scrollable_frame = ttk.Frame(self.left_canvas, style='TFrame', borderwidth=0, relief='flat')
        left_window = self.left_canvas.create_window((0, 0), window=self.left_scrollable_frame, anchor='nw')

        def _left_configure(event):
            self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all"))
            # Set the window width to max of canvas or frame reqwidth
            req_width = self.left_scrollable_frame.winfo_reqwidth()
            canvas_width = self.left_canvas.winfo_width()
            self.left_canvas.itemconfig(left_window, width=max(req_width, canvas_width))
        self.left_scrollable_frame.bind("<Configure>", _left_configure)
        self.left_canvas.bind("<Configure>", _left_configure)

        # Middle group area with scrollbars
        self.middle_canvas = tk.Canvas(self.middle_frame, bg='#111111', highlightthickness=0)
        self.middle_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.middle_scrollbar = ttk.Scrollbar(
            self.middle_frame, orient='vertical', command=self.middle_canvas.yview
        )
        self.middle_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.middle_hscrollbar = ttk.Scrollbar(
            self.middle_frame, orient='horizontal', command=self.middle_canvas.xview
        )
        self.middle_hscrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.middle_canvas.configure(yscrollcommand=self.middle_scrollbar.set, xscrollcommand=self.middle_hscrollbar.set)
        self.middle_scrollable_frame = ttk.Frame(self.middle_canvas, style='TFrame', borderwidth=0, relief='flat')
        middle_window = self.middle_canvas.create_window((0, 0), window=self.middle_scrollable_frame, anchor='nw')

        def _middle_configure(event):
            self.middle_canvas.configure(scrollregion=self.middle_canvas.bbox("all"))
            req_width = self.middle_scrollable_frame.winfo_reqwidth()
            canvas_width = self.middle_canvas.winfo_width()
            self.middle_canvas.itemconfig(middle_window, width=max(req_width, canvas_width))
        self.middle_scrollable_frame.bind("<Configure>", _middle_configure)
        self.middle_canvas.bind("<Configure>", _middle_configure)

        # Right group area with scrollbars
        self.right_canvas = tk.Canvas(self.right_frame, bg='#111111', highlightthickness=0)
        self.right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.right_scrollbar = ttk.Scrollbar(
            self.right_frame, orient='vertical', command=self.right_canvas.yview
        )
        self.right_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_hscrollbar = ttk.Scrollbar(
            self.right_frame, orient='horizontal', command=self.right_canvas.xview
        )
        self.right_hscrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.right_canvas.configure(yscrollcommand=self.right_scrollbar.set, xscrollcommand=self.right_hscrollbar.set)
        self.right_scrollable_frame = ttk.Frame(self.right_canvas, style='TFrame', borderwidth=0, relief='flat')
        right_window = self.right_canvas.create_window((0, 0), window=self.right_scrollable_frame, anchor='nw')

        def _right_configure(event):
            self.right_canvas.configure(scrollregion=self.right_canvas.bbox("all"))
            req_width = self.right_scrollable_frame.winfo_reqwidth()
            canvas_width = self.right_canvas.winfo_width()
            self.right_canvas.itemconfig(right_window, width=max(req_width, canvas_width))
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

        # Load groups into the scrollable frames
        self.load_groups(self.left_scrollable_frame, GROUPS_LEFT)
        self.load_groups(self.middle_scrollable_frame, GROUPS_MIDDLE)
        self.load_groups(self.right_scrollable_frame, GROUPS_RIGHT)
        print("Groups loaded.")

    def load_groups(self, parent, groups):
        print(f"Loading groups into {parent}...")
        for group_name, group_info in groups.items():
            print(f"Adding group section: {group_name}")
            self.add_group_section(parent, group_name, group_info)

    def add_group_section(self, parent, group_name, group_info):
        print(f"Adding group section for {group_name}...")
        section_frame = ttk.Frame(parent, style='TFrame', borderwidth=0, relief='flat')
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
            section_frame.configure(borderwidth=0, relief='flat')
            section_frame.columnconfigure(0, weight=1)
            section_frame.columnconfigure(1, weight=0)
            image_frame = ttk.Frame(section_frame, style='TFrame', borderwidth=0, relief='flat')
            image_frame.grid(row=0, column=0, padx=(PADX, 6), pady=PADY, sticky='ns')
            subgroup_frame = ttk.Frame(section_frame, style='TFrame', borderwidth=0, relief='flat')
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
            # Ensure label/button area is always at least min_label_width
            subgroup_frame.grid_propagate(True)
            subgroup_frame.config(width=min_label_width)

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

    def export_individual_group(self, folder_path, state):
        if state.get():
            self.process_bmp_files_to_XML(folder_path)
            messagebox.showinfo(
                "Success",
                f"XML and TXT files have been successfully created for '{folder_path}'."
            )


    def export_all_groups(self):
        for path, state_var in self.checkbox_states.items():
            if state_var.get():
                self.process_bmp_files_to_XML(path)
        messagebox.showinfo(
            "Success",
            "XML and TXT files have been successfully created for all selected groups.",
            f" saved to folder = {self.prefix}   file = 00_ART_MODS_MassImport.xml"
        )

    def export_all_to_master_xml(self):
        all_xml_entries = []
        master_txt_data = {}  # Dictionary to hold txt lines for each master txt file

        for path, state_var in self.checkbox_states.items():
            if state_var.get():
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

            messagebox.showinfo(
                "Success",
                f"MassImport XML and autopatch TXT files have been successfully created."
            )
        else:
            messagebox.showinfo(
                "No Data",
                "No XML entries were generated. Please check your groups and try again."
            )

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
    style.configure('TFrame', background='#111111', bordercolor='#000000', borderwidth=0)
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

    app = BMPtoXMLConverter(root)
    print("start")
    root.mainloop()