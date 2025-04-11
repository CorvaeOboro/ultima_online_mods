
# ENV HeartWood
a collection of land texture modifications to the elven city of the HeartWood 

- HeartWood Textures : the wood of the large heartwood tinted green with living energy
- Trees : sliced tree images assembled into composites then altered and disassembled 


![00_env_heartwood_ingame_A](00_env_heartwood_ingame_A.png?raw=true "00_env_heartwood_ingame_A")

![00_env_heartwood_ingame_B](00_env_heartwood_ingame_B.png?raw=true "00_env_heartwood_ingame_B")

![00_env_heartwood_ingame_C](00_env_heartwood_ingame_C.png?raw=true "00_env_heartwood_ingame_C")

![00_env_heartwood_ingame_D](00_env_heartwood_ingame_D.png?raw=true "00_env_heartwood_ingame_D")

![00_env_heartwood_ingame_E](00_env_heartwood_ingame_E.png?raw=true "00_env_heartwood_ingame_E")

![00_env_heartwood_ingame_F](00_env_heartwood_ingame_F.png?raw=true "00_env_heartwood_ingame_F")

![00_item_heartwood_tree_comp](./ART_S/00_item_heartwood_tree_comp.png?raw=true "00_item_heartwood_tree_comp")

## TOOLS

- [02_image_composite_multi.py](https://github.com/CorvaeOboro/ultima_online_mods/blob/main/Z_Tools/02_image_composite_multi.py) = composites adjacent or overlaping images to assemble sliced tree images

## TREE WORKFLOW
- finding matches of image slices using [02_image_composite_multi.py](https://github.com/CorvaeOboro/ultima_online_mods/blob/main/Z_Tools/02_image_composite_multi.py)
- creates composite images and data of the separate slices and arragement as composite json 
- composite image is upscaled and altered 
- psd to png , folders from png 
- each composite json has been added to corresponding folder 
- run [02_image_composite_multi.py](https://github.com/CorvaeOboro/ultima_online_mods/blob/main/Z_Tools/02_image_composite_multi.py) to DISASSEMBLE for each composite tree
- use paintover_to_psd for each folder in upscale to paste the image slices into source psds 

![00_item_heartwood_tree_tools](./ART_S/00_item_heartwood_tree_tools.png?raw=true "00_item_heartwood_tree_tools")

