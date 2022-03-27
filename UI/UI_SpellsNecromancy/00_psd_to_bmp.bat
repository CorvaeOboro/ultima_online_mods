SETLOCAL ENABLEDELAYEDEXPANSION
for /r %%f in (*.psd) do (
set  _nameINPUT=%%f
set  _nameINPUTpsd=%%f
set  _nameFIXA=!_nameINPUT:.psd=.bmp!
set  _nameFIXApsd=!_nameINPUT:.psd=.psd[0]!
set  _nameFIXB=!_nameFIXA:.png=.jpg!
set  _finalname=!_nameFIXB:.webp=.jpg!
echo !_finalname!
echo !_nameFIXApsd!
magick convert "!_nameFIXApsd!" -background black -flatten -colorspace sRGB -type palette "!_finalname!"
)