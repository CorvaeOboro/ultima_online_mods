# Quick Installation / Patching
- download [UO_ART_MODS_20220413.zip]( https://github.com/CorvaeOboro/ultima_online_mods/releases/download/UO_ART_MODS_20220413/UO_ART_MODS_20220413.zip ) . 
- extract downloaded zip , if there are any modded items you dont care for feel free to edit the mod TXT file and remove the line matching the item \ image name ( no empty lines )
- using [Mulpatcher]( http://varan.uodev.de/ ) > Settings > Art > set the mul paths : Art.mul path ( Ultima directory ) and artidx.mul . click LOAD . repeat for Gumps and Textures .
- Features > Autopatch > select the mod txt file( 00_ART_ALL_ART_S.txt ) and set Art(S) as category dropdown  > hit START . 
- Repeat Autopatch process for the following mod txt files :
- 00_UI_ALL_GUMP.txt ( Gumps ) , 00_ENV_ALL_TEX.txt ( Textures ) , 00_ENV_ALL_ART_M.txt ( Art (M) ) , 00_ENV_ALL_ART_S.txt ( Art (S) ) 
- Settings > Save the Art mul to the Ultima directory ( Ultima directory ) . repeat for Gumps and Textures .

# Installation / Patching - Expanded

1. Client Launcher Settings 
- Update to Latest ( click verify ) 
- Disable autopatching and autoupdates ( gear > settings > uncheck both ) 


2. Mulpatcher 
- download [Mulpatcher]( http://varan.uodev.de/ )
- open Mulpatcher and expand the lower right corner to visibly see the tabs at the bot .

![Mulpatcher_Expand](/Z_InstallNotes/z_install_mulpatcher_expand_01.jpg?raw=true "Mulpatcher_Expand")

- in Settings tab , set the paths of the Art and Gumps to Ultima Online client ( example= C:\Program Files (x86)\Ultima Online Outlands\ )  

![Mulpatcher_Settings](/Z_InstallNotes/z_install_mulpatcher_settings_01.jpg?raw=true "Mulpatcher_Settings")

- for Art and Gumps click Load . ( this will freeze for a few seconds )
- switch to the Features tab , in the upper left Autopatch , set the file path to the TXT file included in the mod ( example= C:\ultima_online_mods\ART_00_ALL.txt ) 
- set the drop down to match the category ( Art (S) = item art , Gumps = ui ) 
- click the Apply button ( this will show progress and ok when completed ) 

![Mulpatcher_Autopatch](/Z_InstallNotes/z_install_mulpatcher_patch_01.jpg?raw=true "Mulpatcher_Autopatch")

- switch back to the Settings tab , in the Art area click SAVE , set the path to Ultima Online client ( example= C:\Program Files (x86)\Ultima Online Outlands\ ) and save the corresponding artidx.mul art.mul .

![Mulpatcher_Save](/Z_InstallNotes/z_install_save_art_01.jpg?raw=true "Mulpatcher_Save")

- Repeat Autopatch process for the following mod txt files :
- 00_UI_ALL_GUMP.txt ( Gumps ) , 00_ENV_ALL_TEX.txt ( Textures ) , 00_ENV_ALL_ART_M.txt ( Art (M) ) , 00_ENV_ALL_ART_S.txt ( Art (S) ) 

Launch Client and play !

- follow your Servers news for updates and patches .
- when a new patch occurs , in the launcher click the verify button which will get latest
- then reapply art mods using the process above.

# Additional Notes

1. Autopatch txt files
- above is the general workflow to apply modifications , and may be repeated for each category type ( Art , Gumps , Textures , etc. )
- included in this mod are TXT files that applies and includes everything ( ART_00_ALL.txt , GUMP_00_ALL.txt ) 
- optionally in addition each mod folder has TXT file that can be used to autopatch ( UI_MagicSpells\UI_MagicSpells.txt )
- feel free to edit the TXT file to remove any modded item by remove the line matching the item image name ( no empty lines )

# Additional Guides
Gaechti :

http://www.burningsheep.ch/finished.html

https://forums.uooutlands.com/index.php?threads/gaechtis-ultima-online-patches-tree-stump-better-reags-and-more.838/

