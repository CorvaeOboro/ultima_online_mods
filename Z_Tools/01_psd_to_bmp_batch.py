"""
PSD TO BMP BATCH EXPORT
Batch converts all .psd files with a hex suffix (e.g., _0x0235.psd) to .bmp using Pillow.
Only exports if the PSD is newer than the BMP or BMP does not exist.
Traverses ART, ENV, UI folders recursively.

processes all source images to their output bmp formated similar to these flags from imagemagick but without that dependency
"-background black -flatten +matte -colorspace sRGB -type TrueColorAlpha BMP3"

 project structure 
ART
    ART_Weapon
        item_weapon_axe_0x9293.psd
        item_weapon_axe_0x9293.bmp
ENV
UI

RULES:
- do not export PSD files to BMP files if they are in a folder named "Upscale" , instead export those to PNG ( only if newer then existing)
- only export to BMP if the PSD is newer
- match bmp format codec specific settings without the dependency of imagemagick
"""
import os
import re
from PIL import Image
import sys

# Root folders to search
ROOTS = ["ART", "ENV", "UI"]
HEX_SUFFIX_RE = re.compile(r"_0x[0-9a-fA-F]{4}\.psd$")

# Global parameter: set to False to suppress '[SKIP]' logs
LOG_SKIPS = True

def log(msg):
    if LOG_SKIPS:
        print(msg)

def log_always(msg):
    print(msg)

def remove_bmps_in_upscale(root_dir):
    """
    Remove all .bmp files found in any folder named 'Upscale' (case-insensitive) under root_dir.
    """
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if any(part.lower() == 'upscale' for part in dirpath.split(os.sep)):
            for fname in filenames:
                if fname.lower().endswith('.bmp'):
                    bmp_path = os.path.join(dirpath, fname)
                    try:
                        os.remove(bmp_path)
                        log(f"[Removed BMP in Upscale] {bmp_path}")
                    except Exception as e:
                        log(f"[ERROR] Could not remove {bmp_path}: {e}")

def psd_to_bmp(psd_path, bmp_path):
    """
    Rule:
    - Export PSD to BMP with 32bpp BGRA (TrueColorAlpha), black background for transparency.
    - Only called for PSDs not in 'Upscale' folders.
    """
    try:
        with Image.open(psd_path) as im:
            # Flatten and convert to RGBA (TrueColorAlpha)
            if im.mode != 'RGBA':
                im = im.convert('RGBA')
            # Set background to black where alpha=0
            bg = Image.new('RGBA', im.size, (0,0,0,255))
            bg.paste(im, mask=im.split()[-1])
            # BMP3 codec: Pillow always outputs 32bpp BGRA for RGBA images
            bg.save(bmp_path, format='BMP', bmp_bits=32)
            log(f"Exported: {bmp_path} [32bpp BGRA]")
    except Exception as e:
        log(f"[ERROR] Failed to process {psd_path}: {e}")

def psd_to_png(psd_path, png_path):
    """
    Rule:
    - Export PSD to PNG with RGBA (TrueColorAlpha), black background for transparency.
    - Only called for PSDs in 'Upscale' folders.
    """
    try:
        with Image.open(psd_path) as im:
            # Flatten and convert to RGBA (TrueColorAlpha)
            if im.mode != 'RGBA':
                im = im.convert('RGBA')
            bg = Image.new('RGBA', im.size, (0,0,0,255))
            bg.paste(im, mask=im.split()[-1])
            bg.save(png_path, format='PNG')
            log(f"Exported: {png_path} [PNG RGBA]")
    except Exception as e:
        log(f"[ERROR] Failed to process {psd_path} to PNG: {e}")

def should_export_png(psd_path, png_path):
    if not os.path.exists(png_path):
        return True
    return os.path.getmtime(psd_path) > os.path.getmtime(png_path)

def test_psd_to_bmp(psd_path, bmp_path):
    """
    Convert a PSD to BMP, then analyze the BMP for codec/bit depth/alpha info.
    """
    print(f"\n[Test] Converting {psd_path} to {bmp_path} and analyzing output...")
    psd_to_bmp(psd_path, bmp_path)
    if not os.path.exists(bmp_path):
        print("[ERROR] BMP was not created!")
        return
    try:
        with Image.open(bmp_path) as bmp:
            print(f"BMP format: {bmp.format}")
            print(f"BMP mode: {bmp.mode}")
            print(f"BMP size: {bmp.size}")
            print(f"BMP info: {bmp.info}")
            # Analyze pixel data for alpha
            has_alpha = bmp.mode in ("RGBA", "BGRA")
            if has_alpha:
                extrema = bmp.getextrema()
                alpha_range = extrema[3] if len(extrema) == 4 else None
                print(f"Alpha channel range: {alpha_range}")
                if alpha_range == (255, 255):
                    print("[WARN] Alpha channel is fully opaque.")
                elif alpha_range == (0, 0):
                    print("[WARN] Alpha channel is fully transparent.")
            else:
                print("[WARN] No alpha channel detected!")
            # Check bit depth (should be 32bpp for RGBA)
            if bmp.mode != 'RGBA':
                print(f"[WARN] BMP mode is {bmp.mode}, expected RGBA (32bpp)")
            else:
                print("[OK] BMP is 32bpp RGBA as expected.")
    except Exception as e:
        print(f"[ERROR] Could not analyze BMP: {e}")

def should_export(psd_path, bmp_path):
    if not os.path.exists(bmp_path):
        return True
    return os.path.getmtime(psd_path) > os.path.getmtime(bmp_path)

def process_folder(root_dir):
    """
    Rule:
    - If a PSD file with a hex suffix is in a folder named 'Upscale' (case-insensitive), export it to PNG (only if PSD is newer than PNG).
    - Otherwise, export to BMP (only if PSD is newer than BMP).
    - Only process files with a hex suffix (_0xXXXX.psd).
    """
    for dirpath, dirnames, filenames in os.walk(root_dir):
        is_upscale = any(part.lower() == 'upscale' for part in dirpath.split(os.sep))
        for fname in filenames:
            if fname.lower().endswith('.psd') and HEX_SUFFIX_RE.search(fname):
                psd_path = os.path.join(dirpath, fname)
                if is_upscale:
                    png_path = os.path.splitext(psd_path)[0] + '.png'
                    if should_export_png(psd_path, png_path):
                        log(f"[Upscale] Converting: {psd_path} -> {png_path}")
                        psd_to_png(psd_path, png_path)
                    else:
                        if LOG_SKIPS:
                            log(f"[Upscale][SKIP] {png_path} is up to date.")
                        # else: do not print anything when skipping
                else:
                    bmp_path = os.path.splitext(psd_path)[0] + '.bmp'
                    if should_export(psd_path, bmp_path):
                        log(f"Converting: {psd_path} -> {bmp_path}")
                        psd_to_bmp(psd_path, bmp_path)
                    else:
                        if LOG_SKIPS:
                            log(f"[SKIP] {bmp_path} is up to date.")
                        # else: do not print anything when skipping

def main():
    # Go up one directory from Z_Tools to find ART, ENV, UI
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for folder in ROOTS:
        abs_folder = os.path.join(parent_dir, folder)
        if os.path.isdir(abs_folder):
            log(f"Processing folder: {abs_folder}")
            process_folder(abs_folder)
        else:
            log(f"[WARN] Folder not found: {abs_folder}")

def main_ui():
    import threading
    import tkinter as tk
    from tkinter import messagebox

    # Dark mode colors
    DARK_BG = "#23272e"
    DARK_FG = "#e6e6e6"
    BTN_GREEN = "#4e7d63"   # muted green
    BTN_BLUE = "#4a6e8a"    # muted blue
    BTN_PURPLE = "#6b5b7a"  # muted purple
    BTN_GRAY = "#44474f"    # muted gray
    STATUS_FG = "#8ec07c"   # soft green for status

    root = tk.Tk()
    root.title("PSD Batch Export Tool")
    root.geometry("400x340")
    root.configure(bg=DARK_BG)

    status_var = tk.StringVar()
    status_var.set("Ready.")

    def threaded(fn):
        def wrapper(*args, **kwargs):
            threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True).start()
        return wrapper

    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @threaded
    def do_export():
        status_var.set("Running batch export...")
        for folder in ROOTS:
            abs_folder = os.path.join(parent_dir, folder)
            if os.path.isdir(abs_folder):
                log(f"Processing folder: {abs_folder}")
                process_folder(abs_folder)
            else:
                log(f"[WARN] Folder not found: {abs_folder}")
        status_var.set("Batch export complete.")

    @threaded
    def do_remove_bmps():
        status_var.set("Removing BMPs in Upscale folders...")
        for folder in ROOTS:
            abs_folder = os.path.join(parent_dir, folder)
            if os.path.isdir(abs_folder):
                remove_bmps_in_upscale(abs_folder)
        status_var.set("BMP removal complete.")

    def do_analyze():
        messagebox.showinfo("Analyze Output", "Analysis functionality can be customized here.")

    tk.Label(root, text="PSD Batch Export Tool", font=("Arial", 16, "bold"), bg=DARK_BG, fg=DARK_FG).pack(pady=10)
    tk.Button(root, text="Run Batch Export", width=30, command=do_export, bg=BTN_GREEN, fg=DARK_FG, activebackground=BTN_GREEN, activeforeground=DARK_FG, relief=tk.FLAT).pack(pady=8)
    tk.Button(root, text="Remove BMPs in Upscale Folders", width=30, command=do_remove_bmps, bg=BTN_BLUE, fg=DARK_FG, activebackground=BTN_BLUE, activeforeground=DARK_FG, relief=tk.FLAT).pack(pady=8)
    tk.Button(root, text="Quit", width=30, command=root.quit, bg=BTN_GRAY, fg=DARK_FG, activebackground=BTN_GRAY, activeforeground=DARK_FG, relief=tk.FLAT).pack(pady=8)
    tk.Label(root, textvariable=status_var, bg=DARK_BG, fg=STATUS_FG, font=("Arial", 10, "bold")).pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    # If no CLI args are given, show the UI
    if len(sys.argv) == 1:
        main_ui()
    else:
        main()
    main()