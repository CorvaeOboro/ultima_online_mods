"""
DEBUG add numbers and random colors to art 
# FOR EACH BMP IN FOLDER, composite NUMBER, BORDER AND randomly COLORIZE for visual debug testing 
# updated for ui and art gumps now write the filename repeating at smallest size possible

TOOLSGROUP::DEBUG
SORTGROUP::8
SORTPRIORITY::81
STATUS::wip
VERSION::20240415
"""
import os
import re
import numpy as np
import random
import glob
# Image libraries
from PIL import Image, ImageDraw, ImageFont , ImageEnhance
import colorsys
#UI
import tkinter as tk
from tkinter import filedialog
from tqdm import tqdm  # Import tqdm for progress bar functionality

class ImageProcessorUI(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack()
        self.create_widgets()

    def create_widgets(self):
        # File path entry
        self.filepath_label = tk.Label(self, text="Directory Path:")
        self.filepath_label.pack(side="top")

        self.filepath_entry = tk.Entry(self, width=50)
        self.filepath_entry.insert(0, "D:\\ULTIMA\\MODS\\ultima_online_mods\\UI\\UI_DEBUG")
        self.filepath_entry.pack(side="top")

        # Font size entry
        self.font_size_label = tk.Label(self, text="Font Size:")
        self.font_size_label.pack(side="top")

        self.font_size_entry = tk.Entry(self, width=10)
        self.font_size_entry.insert(0, "10")
        self.font_size_entry.pack(side="top")

        # Padding entry
        self.padding_label = tk.Label(self, text="Padding:")
        self.padding_label.pack(side="top")

        self.padding_entry = tk.Entry(self, width=10)
        self.padding_entry.insert(0, "1")
        self.padding_entry.pack(side="top")

        # Prefix entry
        self.prefix_label = tk.Label(self, text="Prefix:")
        self.prefix_label.pack(side="top")

        self.prefix_entry = tk.Entry(self, width=20)
        self.prefix_entry.insert(0, "<")
        self.prefix_entry.pack(side="top")

        # Suffix entry
        self.suffix_label = tk.Label(self, text="Suffix:")
        self.suffix_label.pack(side="top")

        self.suffix_entry = tk.Entry(self, width=20)
        self.suffix_entry.insert(0, ">")
        self.suffix_entry.pack(side="top")

        # Browse button
        self.browse_button = tk.Button(self, text="Browse", command=self.browse)
        self.browse_button.pack(side="top")

        # Include border checkbox
        self.include_border = tk.BooleanVar()
        self.border_check = tk.Checkbutton(self, text="Include Border", variable=self.include_border)
        self.border_check.pack(side="top")

        # Process images button
        self.process_button = tk.Button(self, text="Process Images", command=self.process_images)
        self.process_button.pack(side="top")

        # Quit button
        self.quit_button = tk.Button(self, text="QUIT", fg="red", command=self.master.destroy)
        self.quit_button.pack(side="bottom")

    def browse(self):
        directory = filedialog.askdirectory()
        self.filepath_entry.delete(0, tk.END)
        self.filepath_entry.insert(0, directory)

    def process_images(self):
        directory = self.filepath_entry.get()
        include_border = self.include_border.get()
        font_size = int(self.font_size_entry.get())
        padding = int(self.padding_entry.get())
        prefix = self.prefix_entry.get()
        suffix = self.suffix_entry.get()
        processor = ImageProcessor(font_size, padding, prefix, suffix)
        processor.process_directory(directory, include_border)

class ImageProcessor:
    def __init__(self, font_size, padding, prefix, suffix):
        self.regex = re.compile(r'([^\\/:*?"<>|\r\n]+)\.bmp$')
        self.font_size = font_size
        self.padding = padding
        self.prefix = prefix
        self.suffix = suffix
        self.font_path = "arial.ttf"  # Adjust to your font path

    def process_directory(self, target_directory, include_border):
        files = glob.glob(os.path.join(target_directory, "*.bmp"))
        for infile in tqdm(files, desc="Processing Images"):
            self.process_file(infile, include_border)

    def process_file(self, filepath, include_border):
        image = Image.open(filepath)
        # Apply hue shift
        hue = random.randint(0, 360)
        image = self.colorize(image, hue)
        # Darken the image
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(0.8)
        draw = ImageDraw.Draw(image)

        font = ImageFont.truetype(self.font_path, self.font_size)
        match = self.regex.search(filepath)
        if match:
            filename = match.group(1)
            text = f"{self.prefix}{filename}{self.suffix}"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0] + self.padding
            text_height = bbox[3] - bbox[1] + self.padding

            for y in range(0, image.height, text_height):
                for x in range(0, image.width, text_width):
                    # Draw text outline
                    draw.text((x-1, y), text, font=font, fill="black")
                    draw.text((x+1, y), text, font=font, fill="black")
                    draw.text((x, y-1), text, font=font, fill="black")
                    draw.text((x, y+1), text, font=font, fill="black")
                    # Draw main text
                    draw.text((x, y), text, font=font, fill="white")

        if include_border:
            border_width = 5
            draw.rectangle([border_width, border_width, image.width - border_width, image.height - border_width], outline="black", width=border_width)

        image.save(filepath)
        print(f"Image {filepath} processed and saved.")

    def colorize(self, image, hue):
        """ Apply a color shift to an image. """
        img = image.convert('RGBA')
        arr = np.array(img)
        new_img = Image.fromarray(self.shift_hue(arr, hue).astype('uint8'), 'RGBA')
        return new_img

    def shift_hue(self, arr, hue):
        """ Shift the hue of an image. """
        r, g, b, a = np.rollaxis(arr, axis=-1)
        hsv = np.vectorize(lambda r, g, b: colorsys.rgb_to_hsv(r/255., g/255., b/255.))
        h, s, v = hsv(r, g, b)
        rgb = np.vectorize(lambda h, s, v: colorsys.hsv_to_rgb((h + hue/360.0) % 1.0, s, v))
        r, g, b = rgb(h, s, v)
        return np.dstack((r*255, g*255, b*255, a))

def main():
    root = tk.Tk()
    root.title("Image Processing Tool")
    app = ImageProcessorUI(master=root)
    app.mainloop()

if __name__ == '__main__':
    main()