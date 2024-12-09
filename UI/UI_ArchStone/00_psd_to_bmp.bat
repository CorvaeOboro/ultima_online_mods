SETLOCAL ENABLEDELAYEDEXPANSION
for %%f in (*.psd) do (
set  _nameINPUT=%%f
set  _nameINPUTpsd=%%f
set  _finalname=!_nameINPUT:.psd=.bmp!
set  _nameFIXApsd=!_nameINPUT:.psd=.psd[0]!!
echo !_finalname!
echo !_nameFIXApsd!
magick convert "!_nameFIXApsd!" -background black -flatten +matte -colorspace sRGB -type palette BMP3:"!_finalname!"
)