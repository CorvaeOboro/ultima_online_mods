# Installation / Patching
- download [UO_ART_MODS_20211021.zip]( https://github.com/CorvaeOboro/ultima_online_mods/releases/download/UO_ART_MODS_20211021/UO_ART_MODS_20211021.zip )  or from above clicking code > download as zip  . 
- extract downloaded zip , if there are any modded items you dont care for feel free to edit the TXT file and remove the line matching the item image name ( no empty lines )
- using [Mulpatcher]( http://varan.uodev.de/ ) > Settings > set the Art mul path ( UO Client in program files )   and LOAD them
- Features > Autopatch select the txt file for all ( ART_00_ALL.txt ) or a specific set ( ART_MagicScrolls.txt ) and set Art(s) as category ( or gump for UI mods )  > hit START . 
- Settings > Save the Art mul to the UO Client directory ( defaults to program files ) .
- Repeat process for UI loading Gumps and patching ( GUMPS_00_ALL.txt ) Gumps instead of Art(s)

# Installation / Patching - Expanded

1. Client Launcher Settings 
- Update to Latest , and Disable auotpatching or diffing 
- first in launcher > gear > settings > uncheck automatic patch , uncheck automatic diff > close .

2. Mulpatcher 
- download [Mulpatcher]( http://varan.uodev.de/ )
- open Mulpatcher and expand the lower right corner to visibly see the tabs at the bot .

![Mulpatcher_Expand](/Z_InstallNotes/z_install_mulpatcher_expand_01.jpg?raw=true "Mulpatcher_Expand")

- in Settings tab , set the paths of the Art and Gumps to Ultima Online client ( example= C:\Program Files (x86)\Ultima Online Outlands\ )  

![Mulpatcher_Settings](/Z_InstallNotes/z_install_mulpatcher_settings_01.jpg?raw=true "Mulpatcher_Settings")

- for Art and Gumps click Load . ( this will freeze for a few seconds )
- switch to the Features tab , in the upper left Autopatch , set the file path to the TXT file included in the mod ( example= C:\ultima_online_mods\ART_00_ALL.txt ) 
- set the drop down to match the category ( Art (S) = item art , Gumps = ui ) 

![Mulpatcher_Autopatch](/Z_InstallNotes/z_install_mulpatcher_patch_01.jpg?raw=true "Mulpatcher_Autopatch")

- switch back to the Settings tab , in the Art area click Save , set the path to Ultima Online client ( example= C:\Program Files (x86)\Ultima Online Outlands\ ) and save the corresponding artidx.mul art.mul .

![Mulpatcher_Save](/Z_InstallNotes/z_install_save_art_01.jpg?raw=true "Mulpatcher_Save")

- repeat process for UI loading Gumps and patching ( GUMPS_00_ALL.txt ) Gumps instead of Art(s)

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

