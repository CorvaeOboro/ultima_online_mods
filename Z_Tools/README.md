# Modding Tools / Notes
- [MODDING NOTES and TOOLS]( https://github.com/CorvaeOboro/ultima_online_mods/tree/main/Z_Tools#Modding-Notes) 
- located in Z_Tools , includes :
- [00_mod_selector.py]( https://github.com/CorvaeOboro/ultima_online_mods/blob/main/Z_Tools/00_mod_selector.py ) = art mod selector , generates a custom MassImport list from selected mod folders 
- ![00_mod_selector](/Z_Tools/00_mod_selector.png?raw=true "00_mod_selector")
- [00_psd_to_GumpOverrides.py]( https://github.com/CorvaeOboro/ultima_online_mods/blob/main/Z_Tools/00_psd_to_GumpOverrides.py ) = art mod selector for  Ultima Outlands , exports source art to GumpOverrides
- ![00_psd_to_GumpOverrides](/Z_Tools/00_psd_to_GumpOverrides.png?raw=true "00_psd_to_GumpOverrides")
- [01_image_rotate_to_isometric.py](https://github.com/CorvaeOboro/ultima_online_mods/blob/main/Z_Tools/01_image_rotate_to_isometric.py) = convert square textre to isometric 45 degree land tile ( ART_M )
- [02_image_composite_multi.py](https://github.com/CorvaeOboro/ultima_online_mods/blob/main/Z_Tools/02_image_composite_multi.py) = composites adjacent or overlaping images to assemble sliced tree images , saves arrangment as json for disassembly later 
- [02_extract_map_mul.py](https://github.com/CorvaeOboro/ultima_online_mods/blob/main/Z_Tools/02_extract_map_mul.py) = loads map mul and exports land tile data from region to csv , to be loaded in blender addon [z_blender_GEN_ultima_landtiles.py](https://github.com/CorvaeOboro/zenv_blender/blob/main/addon/z_blender_GEN_ultima_landtiles.py ) 
- substance painter files for ENV textures 


# Modding Notes
a collection of info for modding ultima online art .

# MUL 
art assets are compressed into .mul files . modding the art is handled by 'patching' the new art into the corresponding categorical mul file .
- ART = Art_S ( items , placed objects ) , Art_M ( flat isometric landtiles ) 
- GUMPS = user interface , menus , character sheet equipment
- TEXTURES = land textures used on the terrain 

# TOOLS
UO Fiddler
- https://github.com/polserver/UOFiddler
- tool to explore and export the art in the mul files .
- Searchable by name or ID ( ids can be found in game saying ">info" or "-info" ) 
- can Batch export all by category  

Mulpatcher by Varan
- http://varan.uodev.de/ 
- [Mulpatcher Download Alternate Link](https://rose-uo.de/projects/varan/Mulpatcher.zip)
- primary tool for patching , using the autopatching feature by txt file 
- autopatch txt example ( "HEX imagename.bmp" example= "0xF88 item_reagent_NightShade_0xF88.bmp" )

Export
- [00_psd_to_GumpOverrides.py]( https://github.com/CorvaeOboro/ultima_online_mods/blob/main/Z_Tools/00_psd_to_GumpOverrides.py ) = Automatically export from psd source files into a GumpOverrides folder

Image Magick
- https://imagemagick.org/script/download.php
- command line image operations
- in this project currently using imagemagick by a .bat to batch convert psd to bmp and set BMP3 format 

# ENVIRONMENT TEXTURES
Textures -  mapped to 3d terrain 

Landtiles ( Art_M ) - isometric tiles , placed in world mixed with 3d textures on flat areas .
for each envrionment texture there is a corresponding art_m landtile , and additional art after that .

TEX_to_ART_M
- this python script will batch convert Textures to ART_M , however isnt perfect and recommend additional adjustments
- ![TEX to ART_M](ultima_TEX_convert_to_ART_M.jpg?raw=true "TEX to ART_M")
- located in Z_Tools/[01_image_rotate_to_isometric.py](https://github.com/CorvaeOboro/ultima_online_mods/blob/main/Z_Tools/01_image_rotate_to_isometric.py) 

TEX_debug
- this python script useful for visual debug , composites numbers onto each texture 
- ![Debug TEX](ultima_env_debug_example_01.jpg?raw=true "Debug TEX")
- located in Z_Tools/[03_debug_image_num_color.py]( https://github.com/CorvaeOboro/ultima_online_mods/blob/main/Z_Tools/03_debug_image_num_color.py ) 

Substance Painter of ENV textures :
- located in Z_Tools/*.spp 
- env_dirt_grass , env_sand_grass , env_mountain , env_cave_mountain
- ![ultima_art_mod_env_substancepainter](ultima_art_mod_env_substancepainter.jpg?raw=true "ultima_art_mod_env_substancepainter")

# AUTOPATCH
-  the varan autopatch tools reads a textfile as input , the hexidecimalID and the image filepath that will replace it 
- ( "HEX imagename.bmp" example= "0xF88 item_reagent_NightShade_0xF88.bmp" )
- this is now generated using [00_mod_selector.py]( https://github.com/CorvaeOboro/ultima_online_mods/blob/main/Z_Tools/00_mod_selector.py ) 
- previously generated from the spreadsheets 
- ![ultima_mods_spreadsheet](ultima_mods_spreadsheet.jpg?raw=true "ultima_mods_spreadsheet")
- located in Z_Tools/ultima_mods_ART.xlsx  , ultima_mods_ENV.xlsx , ultima_mods_UI.xlsx

# NAMING
- exports from UOFiddler are Hexidecimal HEX or Numbered 
- 00_num_to_hex.py = batch rename files in target folder from number to HEX 
- file list entered into spreadsheet and renamed based on this convention :
- CATEGORY_Group_Name_NUM_HEX
- a batch renaming .bat may be generated from spreadsheet column 

# HUES
- generaly the color gradients are mapped 0 to 1 greyscale values of the art .
- however some are split into 2 , mapping the color gradient to the greyscale values of 0 to 0.5 and 0.5 to 1 .
- ( this might be done to increase total hues available and/or create complex multi color gradient art compressing the arts value ranges remapping to the multi color gradient )
- example = skill scroll , a necromantic scroll fit to the lower hue gradient by its values fit 0 to 0.5
- when creating these arts recommend using the curves adjustment layer to remap the range .   

# LINKS
- servuo - https://www.servuo.com/
- gaechti - http://www.burningsheep.ch/

Archive Format 
MUL
UOP - UOFiddler can convert 