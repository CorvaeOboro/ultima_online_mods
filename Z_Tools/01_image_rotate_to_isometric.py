#=================================
# IMAGE ROTATE 45degree for TEX to ART_M 
# used with ultima online textures to convert "textures" to "art_m" flat land isometric tiles 
# currently an imperfect method due to aliasing during rotation and resizing ( bicubic during final resize )
# attempting to closer match the original's style by sharpening 5% , blending 1% noise , and darkening 12% 
# requires ALPHA folder with bmp included to apply the original opacity
#=================================
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

#//=== VARIABLES ==============================
artm_landtile_size = 44 
x1, y1, x2, y2 = 0, 0, 44, 44
artm_high_resolution = artm_landtile_size*8
rotate_angle = -45
alpha_texture_filepath = './ALPHA/00_LAND_ART_M_ALPHA.bmp'
ARTM_folderpath = '/ART_M'  # sub directory of the generated art_m bmps

noise_amount = 1.0
noise_blend_amount = 0.01 # 1% noise
brightness_amount =  0.88 # darken 12%
sharpen_blend_amount = 0.05 # sharpen by 5%

#//==== NOISE  ===================================
def add_pepper(image, amount):
  output = np.copy(np.array(image))

  # add salt
  nb_salt = np.ceil(amount * output.size * 0.5)
  coords = [np.random.randint(0, i - 1, int(nb_salt)) for i in output.shape]
  output[coords] = 1

  # add pepper
  nb_pepper = np.ceil(amount* output.size * 0.5)
  coords = [np.random.randint(0, i - 1, int(nb_pepper)) for i in output.shape]
  output[coords] = 0

  return Image.fromarray(output)

#//=======================================
def add_noise(image_input, amount):
  output = np.copy(np.array(image_input))

  row,col,ch= output.shape
  mean = 0
  var = 0.1
  sigma = var**0.5
  gauss = np.random.normal(mean,sigma,(row,col,ch))
  gauss = gauss.reshape(row,col,ch)
  noisy = image_input + gauss

  return Image.fromarray(noisy)

#//=======================================
def gauss(mean,sigma):
  from random import uniform
  from math import sqrt,log,pi,cos
  a=uniform(0,1)
  b=uniform(0,1)
  x=sqrt(-2*log(a))*cos(2*pi*b)
  return(x)

def add_noise_guass(image,amount):
  if len(image.shape)==3 :
    a,b,c=image.shape
    for i in range(a):
        for j in range(b):
            image[i][j] += [gauss(0.5,0.01),gauss(0.5,0.01),gauss(0.5,0.01)]

  elif len(image.shape)==2 :
    a,b= image.shape
    for i in range(a):
        for j in range(b):
            image[i][j] +=  gauss(0.01)*(1/255)
  return(image)

#//========================================================================================
#// TEXTURE TO ART_M 
#//========================================================================================
def tex_to_art_m(target_directory):

  if not os.path.isdir(target_directory+ARTM_folderpath): # create ART_M folder
    os.mkdir(target_directory+ARTM_folderpath)
  
  for infile in glob.glob(os.path.join(target_directory, "*.bmp")): 
    image_current = Image.open(infile)
    width, height = image_current.size
    draw = ImageDraw.Draw(image_current)

    image_current = image_current.convert('RGBA')
    image_original = image_current

    image_current = image_current.resize( (artm_high_resolution,artm_high_resolution) , Image.NEAREST)
    image_current = image_current.rotate(rotate_angle, PIL.Image.NEAREST, expand = 1) # NEAREST BILINEAR BICUBIC
    image_main_rotated = image_current.resize( (artm_high_resolution,artm_high_resolution) , Image.NEAREST)

    #//============== LARGER VERSIONS FIT CROPPED PASTED ONTOP OF EACH OTHER ================================================
    # make larger versions to paste into bg for edge padding
    image_main_bgA = image_current.resize( (artm_high_resolution+8,artm_high_resolution+8) , Image.NEAREST) 
    image_main_bgB = image_main_bgA.resize( (artm_high_resolution+16,artm_high_resolution+16) , Image.NEAREST)
    image_main_bgC = image_main_bgB.resize( (artm_high_resolution+24,artm_high_resolution+24) , Image.NEAREST)
    image_main_bgD = image_main_bgC.resize( (artm_high_resolution+32,artm_high_resolution+32) , Image.NEAREST)
    #fit crop the resized images back down to main res so can paste centered easily
    image_main_bgA = ImageOps.fit(image_main_bgA, (artm_high_resolution,artm_high_resolution), method=Image.BICUBIC, bleed=0.0, centering=(0.5, 0.5) )
    image_main_bgB = ImageOps.fit(image_main_bgB, (artm_high_resolution,artm_high_resolution), method=Image.BICUBIC, bleed=0.0, centering=(0.5, 0.5) )
    image_main_bgC = ImageOps.fit(image_main_bgC, (artm_high_resolution,artm_high_resolution), method=Image.BICUBIC, bleed=0.0, centering=(0.5, 0.5) )
    image_main_bgD = ImageOps.fit(image_main_bgD, (artm_high_resolution,artm_high_resolution), method=Image.BICUBIC, bleed=0.0, centering=(0.5, 0.5) )

    #//============== CENTER LARGER IMAGE TO CURRENT ================================================
    # pasting the cropped image over the original image, guided by the transparency mask of cropped image

    image_main_rotated_bg = image_main_rotated
    image_main_rotated_bg = Image.composite( image_main_rotated_bg , image_main_bgD , image_main_bgD )
    image_main_rotated_bg = Image.composite( image_main_rotated_bg , image_main_bgC , image_main_bgC )
    image_main_rotated_bg = Image.composite( image_main_rotated_bg , image_main_bgB , image_main_bgB )
    image_main_rotated_bg = Image.composite( image_main_rotated_bg , image_main_bgA , image_main_bgA )

    image_current = Image.composite( image_main_rotated_bg , image_main_rotated , image_main_rotated )
    image_original_resized = image_original.resize( (image_main_rotated.size) , Image.NEAREST)
    
    final_size_padded = (artm_landtile_size+2, artm_landtile_size+2)
    final_size = (artm_landtile_size, artm_landtile_size)
    #image_current = image_current.resize(final_size, Image.BICUBIC)
    image_current = image_current.resize(final_size_padded, Image.NEAREST)
    image_current = image_current.crop((1, 1, 45, 45))

    # brightness --------------------------------------
    enhancer = ImageEnhance.Brightness(image_current)
    brightness_modifier = brightness_amount #darkens the image
    image_current = enhancer.enhance(brightness_modifier)
    # contrast disabled -------------------------------
    #image_current = ImageEnhance.Color(image_current)
    #image_current = image_current.enhance(1.0)
    #noise -------------------------------------------
    image_noised = add_pepper(image_current,noise_amount)
    image_current = Image.blend(image_current, image_noised, noise_blend_amount)
    #sharpen -----------------------------------------
    image_sharpened = image_current.filter(ImageFilter.SHARPEN)
    image_current = Image.blend(image_current, image_sharpened, sharpen_blend_amount)

    # ALPHA from original 
    original_alpha = Image.open(alpha_texture_filepath)
    red, green, blue = original_alpha.split()
    image_current_png = image_current.putalpha(red)

    # SAVE IMAGE ===============================
    print("SAVING >>>   " + str(infile))
    png_filename = re.sub('.bmp','.png',str(infile),);

    #image_current.save(png_filename)
    image_final_output = Image.new("RGB", final_size, (0, 0, 0))

    final_outputpath = target_directory + "/" + ARTM_folderpath + "/" + Path(infile).stem + ".bmp"

    final_outputpath = target_directory + "/" + ARTM_folderpath + "/" + Path(infile).stem + ".png"
    image_current.save(final_outputpath)

# MAIN for windows ===============================
if __name__ == '__main__':
  directory = os.path.dirname(os.path.abspath(__file__))  #// local directory , this py is designed to be run in the same folder as bmps
  tex_to_art_m(directory)