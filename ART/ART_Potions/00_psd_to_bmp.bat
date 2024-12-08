SETLOCAL ENABLEDELAYEDEXPANSION
for %%f in (*.psd) do (
set  _nameINPUT=%%f
set  _nameINPUTpsd=%%f
set  _nameFIXA=!_nameINPUT:.psd=.bmp!
set  _nameFIXApsd=!_nameINPUT:.psd=.psd[0]!
echo !_nameFIXA!
echo !_nameFIXApsd!
magick convert "!_nameFIXApsd!" -background black -flatten +matte -colorspace sRGB -type TrueColorAlpha BMP3:"!_nameFIXA!"
)