import os
import subprocess
from PIL import Image
from psd_tools import PSDImage

def convert_psd_to_dds(psd_path):
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

        # Define the path to the texconv tool
        texconv_path = "c:/tools/texconv.exe"

        # Convert PNG to DDS using texconv
        # Note: "Flip Y" option is intentionally not used (it's off by default)
        dds_path = os.path.splitext(psd_path)[0] + ".dds"
        subprocess.run([texconv_path, "-f", "DXT1", "-y", "-vflip", "-o", os.path.dirname(dds_path), temp_png_path])

        os.remove(temp_png_path)

        final_bmp_path = os.path.splitext(psd_path)[0] + ".bmp"
        os.rename(dds_path, final_bmp_path)

        print(f"Converted {os.path.basename(psd_path)} to DDS (as .bmp) with DXT1 compression successfully.")
    except IOError as e:
        print(f"Error during conversion process for {os.path.basename(psd_path)}: {e}")

def batch_convert_psd_to_dds():
    current_folder = os.getcwd()
    for filename in os.listdir(current_folder):
        if filename.lower().endswith('.psd'):
            file_path = os.path.join(current_folder, filename)
            print(f"Converting {filename} to DDS...")
            convert_psd_to_dds(file_path)

if __name__ == "__main__":
    batch_convert_psd_to_dds()
