SETLOCAL ENABLEDELAYEDEXPANSION
for %%f in (*.png) do (
set  _nameINPUT=%%f
set  _nameFIXA=!_nameINPUT:.png=.bmp!
set  _nameFIXB=!_nameFIXA:.jng=.jpg!
set  _finalname=!_nameFIXB:.webp=.jpg!
echo !_finalname!
magick convert "%%f" -background black -flatten -colorspace sRGB -type TrueColorAlpha BMP3:"!_finalname!"
)