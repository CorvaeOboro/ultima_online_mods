#=================================
# FOR EACH BMP IN FOLDER , composite NUMBER , BORDER AND randomly COLORIZE for visual debug testing 
#=================================
from PIL import Image, ImageDraw, ImageFont
from PIL import Image, ImageDraw, ImageFont ,ImageEnhance,ImageFilter , ImageChops , ImageOps
import PIL
import glob, os
import os.path
import re
import numpy as np
import colorsys
import random
import blend_modes
from pathlib import Path
#import Image

#//====================================================
noise_amount = 1.0
noise_blend_amount = 0.01 # 0.1
brightness_amount =  0.88 # 0.95 darken originallly
sharpen_blend_amount = 0.05 # 0.4 sharpen

# REGEX TO PARSE ID NUMBER FROM FILE ===============================
# regex finds string of numbers between underscores or starting with underscore and ending with dot 
# important this doesnt find hexidecimal ( 0x0987 )  
# example name to parse = landtile_01912_grass_W_0x0972.bmp , landtile_null_203.bmp
regex_numbers_no_letters = re.compile('_[0-9]*_|_[0-9]*\.')
regex_underscore = re.compile('_')
regex_dot = re.compile('\.')

# SHIFT HUE TO DIFFENTIATE  / COLORIZE  ===============================
rgb_to_hsv = np.vectorize(colorsys.rgb_to_hsv)
hsv_to_rgb = np.vectorize(colorsys.hsv_to_rgb)

def shift_hue(arr, hout):
    r, g, b, a = np.rollaxis(arr, axis=-1)
    h, s, v = rgb_to_hsv(r, g, b)
    h = hout
    r, g, b = hsv_to_rgb(h, s, v)
    arr = np.dstack((r, g, b, a))
    return arr

def colorize(image, hue):
    # Colorize PIL image `original` with the given
    # `hue` (hue within 0-360); returns another PIL image.
    img = image.convert('RGBA')
    arr = np.array(np.asarray(img).astype('float'))
    new_img = Image.fromarray(shift_hue(arr, hue/360.).astype('uint8'), 'RGBA')

    return new_img

def number_and_border(target_directory):
  seed = 0
  for infile in glob.glob(os.path.join(target_directory, "*.bmp")):
    image = Image.open(infile)
    width, height = image.size 
    draw = ImageDraw.Draw(image)

    # WRITE NUMBER IF FOUND ===============================
    text_found = re.findall(regex_numbers_no_letters, str(infile)) 
    if (text_found):
      text_outputA = text_found[0].strip()
      text_outputB = re.sub(regex_underscore,'',text_outputA,);
      text_outputC = re.sub(regex_dot,'',text_outputB,);
      text_final_number = text_outputC.lstrip('0')

      textsize_relative_percent = 0.4
      textsize_final = round( ((width+height)/2) * textsize_relative_percent ) 
      print("image width = " + str(width) + "   >>>>>  " + " text relative size =  " + str(textsize_final) )
      textwidth = round(textsize_final/2)
      textheight = round(textsize_final/2)
      #textwidth, textheight = draw.textsize(text_final_number)

      margin = 2
      x = (width/2) - margin - textwidth
      y = (height/2) - margin - textheight
      textsize_relative_percent = 0.4
      textsize_final = round( ((width+height)/2) * textsize_relative_percent ) 
      print("image width = " + str(width) + "   >>>>>  " + " text relative size =  " + str(textsize_final) )

      font_path = ImageFont.truetype(r'C:/FONTS/Roboto-Bold.ttf', textsize_final) 
      draw.text((x+1, y), text_final_number , fill ="white", font=font_path, align ="left")
      draw.text((x-1, y), text_final_number , fill ="white", font=font_path, align ="left")
      draw.text((x, y+1), text_final_number , fill ="white", font=font_path, align ="left")
      draw.text((x, y-1), text_final_number , fill ="white", font=font_path, align ="left")

      draw.text((x, y), text_final_number , fill ="black", font=font_path, align ="center")

    # BORDER DRAW 4 LINES ON EDGES ===============================
    border = 3
    border_width = 5
    draw.line((border,border, width-border, border), fill=20, width=border_width)
    draw.line((border,height-border, width-border, height-border), fill=20, width=border_width)
    draw.line((border,border, border, height-border), fill=20, width=border_width)
    draw.line((width-border,height-border, width-border, border), fill=20, width=border_width)

    # RANDOM COLOR HUE SHIFT ===============================
    seed = seed+1 
    random.seed(seed)
    rand_hue = random.randrange(360) 
    image = colorize(image,rand_hue)

    # SAVE IMAGE ===============================
    image.save(infile)

# MAIN for windows ===============================
if __name__ == '__main__':
  directory = os.path.dirname(os.path.abspath(__file__))  #// directory of current py file
  number_and_border(directory)