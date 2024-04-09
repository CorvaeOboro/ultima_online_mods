import os
import subprocess
from PIL import Image
from psd_tools import PSDImage

def convert_psd_to_png(psd_path):
    try:
        img = Image.open(psd_path).convert("RGB")
    except IOError:
        try:
            psd = PSDImage.open(psd_path)
            img = psd.composite()  # This flattens the image
        except Exception as e:
            print(f"Error converting {os.path.basename(psd_path)} with both Pillow and psd-tools: {e}")
            return

    try:
        temp_png_path = os.path.splitext(psd_path)[0] + ".png"
        img.save(temp_png_path)
    except IOError as e:
        print(f"Error during conversion process for {os.path.basename(psd_path)}: {e}")

def batch_convert_psd_to_png():
    current_folder = os.getcwd()
    for filename in os.listdir(current_folder):
        if filename.lower().endswith('.psd'):
            file_path = os.path.join(current_folder, filename)
            print(f"Converting {filename} to PNG...")
            convert_psd_to_png(file_path)

if __name__ == "__main__":
    batch_convert_psd_to_png()
