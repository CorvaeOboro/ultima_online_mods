"""
DEBUG PSD LAYER NAME LOG - DEBUG
recursive search for psd then store all layer names to csv for review

TOOLSGROUP::DEBUG
SORTGROUP::8
SORTPRIORITY::82
STATUS::wip
VERSION::20240317
"""
import os
import csv
from psd_tools import PSDImage
from tqdm import tqdm

PSD_FOLDER_PATH = 'D:/ULTIMA/MODS/ultima_online_mods/ART'
OUPUT_FILENAME = '00_psd_layer_log.csv'
# Excluding unnamed default layers 
LAYER_NAME_EXCLUDE = { "Background" , "Layer" , "Color Fill" , "Brightness/Contrast" , "Hue/Saturation" , "Levels" , "Group" , "Gradient Fill" } # default photoshop names - unnamed
LAYER_NAME_EXCLUDE_CUSTOM = { "CLAMP" , "SHARPEN_70" , "ui_spell_" , "ORIGINAL" , "FINAL_MIN_CURVE" , "0x" , "LIGHTEN_FOR_COLOR_VIEW" , "BORDER" , "DARKEN" ,"GUIDE" ,"SHARPEN" , "TILING_FIX" } # specific to the project 

#//=============================================================================================================
def is_valid_layer_name(layer_name):
    # Check if the layer name is valid (not starting with "Layer" or "Color Fill")
    for current_exclude in LAYER_NAME_EXCLUDE: # basic photoshop layers "Layer" or "Color Fill"
        if layer_name.startswith(current_exclude):
            return False
    for current_exclude_custom in LAYER_NAME_EXCLUDE_CUSTOM: # custom named layers we use a lot
        if layer_name.startswith(current_exclude_custom):
            return False
    return True

def process_layer(layer, psd_file, csv_writer):
    if is_valid_layer_name(layer.name):
        csv_writer.writerow([os.path.basename(psd_file), layer.name])
    if layer.is_group():
        for child_layer in layer:
            process_layer(child_layer, psd_file, csv_writer)

def process_psd_file(psd_file, csv_writer):
    psd = PSDImage.open(psd_file)
    for layer in psd:
        process_layer(layer, psd_file, csv_writer)

def search_and_process_psd_files(folder_path, output_csv_file):
    with open(output_csv_file, mode='w', newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['PSD File', 'Layer Name'])

        psd_files = [] 
        for root, _, files in os.walk(folder_path):  # Walk through the directory structure starting from folder_path
            for file in files: 
                if file.endswith('.psd'): 
                    full_path = os.path.join(root, file) 
                    psd_files.append(full_path) 

        with tqdm(total=len(psd_files), desc="Processing PSD files") as pbar:
            for psd_file in psd_files:
                process_psd_file(psd_file, csv_writer)
                pbar.update(1)

#//=============================================================================================================
if __name__ == '__main__':
    search_and_process_psd_files(PSD_FOLDER_PATH, OUPUT_FILENAME)
