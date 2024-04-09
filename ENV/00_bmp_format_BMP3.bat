SETLOCAL ENABLEDELAYEDEXPANSION
for /r %%f in (*.bmp) do (
set  _finalname=%%f
echo !_finalname!
magick convert "%%f" -background black -flatten -colorspace sRGB -type TrueColorAlpha BMP3:"!_finalname!"
)