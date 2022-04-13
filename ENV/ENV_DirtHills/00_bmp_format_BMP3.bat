SETLOCAL ENABLEDELAYEDEXPANSION
for /r %%f in (*.bmp) do (
set  _nameINPUT=%%f
set  _nameFIXA=!_nameINPUT:.jpeg=.jpg!
set  _nameFIXB=!_nameFIXA:.png=.jpg!
set  _finalname=!_nameFIXB:.webp=.jpg!
echo !_finalname!
magick convert "%%f" -background black -flatten -colorspace sRGB -type TrueColorAlpha BMP3:"!_finalname!"
)