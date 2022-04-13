SETLOCAL ENABLEDELAYEDEXPANSION
for %%f in (*.psd) do (
set  _nameINPUT=%%f
set  _nameINPUTpsd=%%f
set  _finalname=!_nameINPUT:.psd=.bmp!
set  _namePSD=!_nameINPUT:.psd=.psd[0]!
magick convert "!_namePSD!" -background black -flatten +matte -colorspace sRGB -type TrueColorAlpha "!_finalname!"
)
call "00_BATCH_images_rotate_to_ART_M.bat"
call "%~dp0\ART_M\00_png_to_BMP3.bat"
call "00_bmp_format_BMP3.bat"