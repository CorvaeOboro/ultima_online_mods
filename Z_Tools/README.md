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
- Searchable by name or ID ( ids can be found in game saying ">info" ) 
- can Batch export all by category  

Mulpatcher by Varan
- http://varan.uodev.de/
- primary tool for patching , using the autopatching feature by txt file 
- autopatch txt example ( "HEX imagename.bmp" example= "0xF88 item_reagent_NightShade_0xF88.bmp" )

Image Magick
- https://imagemagick.org/script/download.php
- command line image operations
- in this project currently using .bat to batch convert psd to bmp and set BMP3 format 

# ENVIRONMENT TEXTURES
Textures -  mapped to 3d terrain 

Landtiles ( Art_M ) - isometric tiles , placed in world mixed with 3d textures on flat areas .
for each envrionment texture there is a corresponding art_m landtile , and additional art after that .

TEX_to_ART_M
- this python script will batch convert Textures to ART_M , however isnt perfect and reccomend additional adjustments
- ![TEX to ART_M](ultima_TEX_convert_to_ART_M.jpg?raw=true "TEX to ART_M")
- located in Z_Tools/00_BATCH_images_rotate_to_ART_M.py and in each ENV mod folder

TEX_debug
- this python script useful for visual debug , composites numbers onto each texture 
- ![Debug TEX](ultima_env_debug_example_01.jpg?raw=true "Debug TEX")
- located in Z_Tools/00_BATCH_image_number_and_border.py

Substance Painter files for ENV textures :
- ultima_art_mod_env_dirt_grass
- ![ultima_art_mod_env_dirt_grass](ultima_art_mod_env_dirt_grass.jpg?raw=true "ultima_art_mod_env_dirt_grass")
- ultima_art_mod_env_sand_grass
- ![ultima_art_mod_env_sand_grass](ultima_art_mod_env_sand_grass.jpg?raw=true "ultima_art_mod_env_sand_grass")
- ultima_art_mod_env_mountain
- ![ultima_art_mod_env_mountain](ultima_art_mod_env_mountain.jpg?raw=true "ultima_art_mod_env_mountain")
- ultima_art_mod_env_cave_mountain
- ![ultima_art_mod_env_cave_mountain](ultima_art_mod_env_cave_mountain.jpg?raw=true "ultima_art_mod_env_cave_mountain")

# AUTOPATCH
- ( "HEX imagename.bmp" example= "0xF88 item_reagent_NightShade_0xF88.bmp" )
- generated from spreadsheet 
- ![ultima_mods_spreadsheet](ultima_mods_spreadsheet.jpg?raw=true "ultima_mods_spreadsheet")

# NAMING
- exports from UOFiddler are HEX or Numbered 
- file list entered into spreadsheet and renamed based on this convention :
- CATEGORY_Group_Name_NUM_HEX
- batch renaming .bat may be generated from spreadsheet column 

# HUES
- generaly the color gradients are mapped 0 to 1 greyscale values of the art .
- however some are split into 2 , mapping the color gradient to the greyscale values of 0 to 0.5 and 0.5 to 1 .
- ( this might be done to increase total hues available and/or create complex multi color gradient art compressing the arts value ranges remapping to the multi color gradient )
- example = skill scroll , a necromantic scroll fit to the lower hue gradient by its values fit 0 to 0.5
- when creating these arts reccomend using the curves adjustment layer to remap the range .   

# LINKS
- servuo - https://www.servuo.com/
- gaechti - http://www.burningsheep.ch/