"""
PSD TO BMP BATCH EXPORT
Batch converts all .psd files with a hex suffix (e.g., _0x0235.psd) to .bmp using Pillow.
Only exports if the PSD is newer than the BMP or BMP does not exist.
Traverses ART, ENV, UI folders recursively.

Processes all source images to their output BMP formatted similar to these ImageMagick flags but without that dependency:
"-background black -flatten +matte -colorspace sRGB -type TrueColorAlpha BMP3"

Project structure
ART
    ART_Weapon
        item_weapon_axe_0x9293.psd
        item_weapon_axe_0x9293.bmp
ENV
UI

RULES:
- do not export PSD files to BMP files if they are in a folder named "Upscale" , instead export those to PNG (only if newer than existing)
- only export to BMP if the PSD is newer
- match bmp format codec specific settings without the dependency of imagemagick
"""
import os
import re
import sys
import gc
import shutil
import subprocess
import tempfile
import hashlib
from PIL import Image, ImageFile

# Handle very large images and truncated files more gracefully
ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None

try:
    # psd-tools provides a robust PSD composite render; Pillow's PSD support can be limited
    from psd_tools import PSDImage  # type: ignore
    _HAS_PSD_TOOLS = True
except Exception:
    PSDImage = None  # type: ignore
    _HAS_PSD_TOOLS = False

# Root folders to search
ROOTS = ["ART", "ENV", "UI"]
HEX_SUFFIX_RE = re.compile(r"_0x[0-9a-fA-F]{4}\.psd$")
HEX_SHORT_RE = re.compile(r"(_0x)([0-9a-fA-F]{1,3})(?![0-9a-fA-F])")

# BMP save configuration: some consumers misread 32bpp headers; try 24 for compatibility
# Set to 32 (BGRA) to keep alpha in BMP; set to 24 to drop alpha and maximize compatibility
SAVE_BMP_BITS = 32
# If a saved BMP doesn't visually match the source (based on thumbnail signature),
# retry save with 24-bit RGB to avoid alpha/header issues
RETRY_WITH_24BPP_ON_ANOMALY = True
DEBUG_SAVE_ON_ANOMALY = True

# Optional external fallback via ImageMagick if present in PATH
USE_IMAGEMAGICK_FALLBACK = True

# Global parameter: set to False to suppress '[SKIP]' logs
LOG_SKIPS = True

def log(msg):
    if LOG_SKIPS:
        print(msg)

def log_always(msg):
    print(msg)

def _file_sha256(path: str, chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA-256 for a file path."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            h.update(chunk)
    return h.hexdigest()

def _fix_hex_padding_in_name(name: str) -> tuple[str, bool]:
    """
    If name contains a hex suffix like `_0xF3B` (1-3 hex digits), pad to 4 -> `_0x0F3B`.
    Returns (new_name, changed?). Does not alter other parts of the name.
    """
    def repl(m: re.Match) -> str:
        prefix, digits = m.group(1), m.group(2)
        return f"{prefix}{digits.zfill(4)}"

    new_name, n = HEX_SHORT_RE.subn(repl, name)
    return new_name, (n > 0)

def _is_in_upscale_dir(dirpath: str) -> bool:
    return any(part.lower() == 'upscale' for part in dirpath.split(os.sep))

def scan_upscale_hex_padding_issues(root_dir: str) -> dict:
    """
    Scan for files and folders under any `Upscale` subfolder that have improperly
    zero-padded hex codes (e.g., `_0xF3B` instead of `_0x0F3B`).
    Returns a dict with keys 'files' and 'folders' listing tuples of (src_path, dst_path).
    """
    issues = {"files": [], "folders": []}
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if not _is_in_upscale_dir(dirpath):
            continue
        # Check files
        for fname in filenames:
            new_name, changed = _fix_hex_padding_in_name(fname)
            if changed:
                src = os.path.join(dirpath, fname)
                dst = os.path.join(dirpath, new_name)
                if src != dst:
                    issues["files"].append((src, dst))
        # Check immediate subfolders (dirnames are relative names)
        for d in dirnames:
            new_d, changed = _fix_hex_padding_in_name(d)
            if changed:
                src = os.path.join(dirpath, d)
                dst = os.path.join(dirpath, new_d)
                if src != dst:
                    issues["folders"].append((src, dst))
    return issues

def fix_upscale_hex_padding_files(issues_files: list[tuple[str, str]]):
    """
    For each (src, dst):
    - If dst exists and hash equals src, delete src.
    - If dst exists and differs, skip and log.
    - If dst missing: copy2 src->dst, verify hashes, then delete src.
    """
    for src, dst in issues_files:
        try:
            if not os.path.exists(src):
                continue
            # Ensure parent exists
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.exists(dst):
                try:
                    h_src = _file_sha256(src)
                    h_dst = _file_sha256(dst)
                    if h_src == h_dst:
                        os.remove(src)
                        log(f"[FIX][FILE] Removed duplicate after verifying hash: {src} -> {dst}")
                    else:
                        log(f"[FIX][FILE][SKIP] Conflict (different content): {src} vs {dst}")
                except Exception as e:
                    log(f"[FIX][FILE][ERROR] Hash/cleanup failed for {src}: {e}")
                continue
            # Copy then verify
            shutil.copy2(src, dst)
            h_src = _file_sha256(src)
            h_dst = _file_sha256(dst)
            if h_src == h_dst and os.path.getsize(dst) > 0:
                os.remove(src)
                log(f"[FIX][FILE] Renamed via copy+verify: {src} -> {dst}")
            else:
                # Roll back partial copy if mismatch
                try:
                    os.remove(dst)
                except Exception:
                    pass
                log(f"[FIX][FILE][ERROR] Verification failed; kept original: {src}")
        except Exception as e:
            log(f"[FIX][FILE][ERROR] {src} -> {dst}: {e}")

def fix_upscale_hex_padding_folders(issues_folders: list[tuple[str, str]]):
    """
    Rename folders after files have been handled. Process bottom-up to avoid path churn.
    Only rename when destination does not already exist.
    """
    # Sort by path depth descending to ensure children first
    issues_folders_sorted = sorted(issues_folders, key=lambda p: p[0].count(os.sep), reverse=True)
    for src, dst in issues_folders_sorted:
        try:
            if not os.path.isdir(src):
                continue
            if os.path.exists(dst):
                log(f"[FIX][DIR][SKIP] Destination exists, skipping: {src} -> {dst}")
                continue
            os.rename(src, dst)
            log(f"[FIX][DIR] Renamed: {src} -> {dst}")
        except Exception as e:
            log(f"[FIX][DIR][ERROR] {src} -> {dst}: {e}")

def run_fix_upscale_hex_padding(parent_dir: str) -> dict:
    """
    Run scan and then fix: files first (copy+hash verify), then folders. Returns summary dict.
    Only affects entries within `Upscale` directories under ROOTS.
    """
    summary = {"scanned": 0, "files_planned": 0, "folders_planned": 0, "files_fixed": 0, "folders_fixed": 0}
    all_file_issues: list[tuple[str, str]] = []
    all_dir_issues: list[tuple[str, str]] = []
    for folder in ROOTS:
        abs_folder = os.path.join(parent_dir, folder)
        if not os.path.isdir(abs_folder):
            continue
        issues = scan_upscale_hex_padding_issues(abs_folder)
        files_issues = issues.get("files", [])
        dir_issues = issues.get("folders", [])
        all_file_issues.extend(files_issues)
        all_dir_issues.extend(dir_issues)
        summary["scanned"] += 1
    summary["files_planned"] = len(all_file_issues)
    summary["folders_planned"] = len(all_dir_issues)
    # Fix files
    before_files = len([1 for _ in all_file_issues])
    fix_upscale_hex_padding_files(all_file_issues)
    # Re-count how many sources no longer exist as a proxy for fixed
    summary["files_fixed"] = sum(1 for src, _ in all_file_issues if not os.path.exists(src))
    # Fix folders
    fix_upscale_hex_padding_folders(all_dir_issues)
    summary["folders_fixed"] = sum(1 for src, _ in all_dir_issues if not os.path.exists(src))
    log_always(f"[SUMMARY] Zero-padding fixes -> files: {summary['files_fixed']}/{summary['files_planned']}, folders: {summary['folders_fixed']}/{summary['folders_planned']}")
    return summary

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

def remove_upscale_psds(root_dir):
    """
    Remove all .psd files whose names end with '_upscale.psd' found in any folder
    named 'Upscale' (case-insensitive) under root_dir.
    """
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if any(part.lower() == 'upscale' for part in dirpath.split(os.sep)):
            for fname in filenames:
                name_l = fname.lower()
                if name_l.endswith('_upscale.psd'):
                    psd_path = os.path.join(dirpath, fname)
                    try:
                        os.remove(psd_path)
                        log(f"[Removed *_upscale.psd in Upscale] {psd_path}")
                    except Exception as e:
                        log(f"[ERROR] Could not remove {psd_path}: {e}")

def _render_psd_rgba(psd_path):
    """
    Render a PSD into an RGBA Pillow image.
    Prefer psd-tools composite, fallback to Pillow's loader as last resort.
    """
    if _HAS_PSD_TOOLS:
        try:
            psd = PSDImage.open(psd_path)
            # Composite all layers to a single RGBA image
            comp = psd.composite()
            if comp.mode != 'RGBA':
                comp = comp.convert('RGBA')
            comp.load()
            log(f"[RENDER] psd-tools | size={comp.size} mode={comp.mode} | {psd_path}")
            return comp
        except Exception as e:
            log(f"[WARN] psd-tools failed for {psd_path}: {e}. Falling back to Pillow.")
            # Try ImageMagick render before Pillow
            im_rgba = _render_via_imagemagick_to_rgba(psd_path)
            if im_rgba is not None:
                log(f"[RENDER] imagemagick | size={im_rgba.size} mode={im_rgba.mode} | {psd_path}")
                return im_rgba
    # Fallback: Pillow (may be unreliable for complex PSDs)
    with Image.open(psd_path) as im:
        rgba = im.convert('RGBA')
        rgba.load()
        # Detect bogus fully transparent alpha and repair by forcing opaque if RGB has content
        try:
            r, g, b, a = rgba.split()
            a_ext = a.getextrema()
            rgb_ext = [r.getextrema(), g.getextrema(), b.getextrema()]
            rgb_nonzero = any(lo_hi != (0, 0) for lo_hi in rgb_ext)
            if a_ext == (0, 0) and rgb_nonzero:
                # Replace alpha with fully opaque
                from PIL import Image as _PILImage
                a_opaque = _PILImage.new('L', rgba.size, 255)
                rgba = _PILImage.merge('RGBA', (r, g, b, a_opaque))
                rgba.load()
                log(f"[RENDER][FIX] Pillow alpha was fully transparent but RGB had data; forced opaque alpha | {psd_path}")
        except Exception:
            pass
        log(f"[RENDER] pillow | size={rgba.size} mode={rgba.mode} | {psd_path}")
        return rgba

def _flatten_on_black(rgba_img: Image.Image) -> Image.Image:
    """
    Flatten an RGBA image over an opaque black background (alpha ignored in output).
    Returns a new RGBA image with fully opaque alpha channel.
    """
    bg = Image.new('RGBA', rgba_img.size, (0, 0, 0, 255))
    alpha = rgba_img.split()[-1]
    bg.paste(rgba_img, mask=alpha)
    return bg

def _save_atomic(img: Image.Image, out_path: str, format: str, **save_kwargs):
    """Save image atomically to avoid partial/corrupted writes."""
    tmp_path = out_path + ".tmp"
    img.save(tmp_path, format=format, **save_kwargs)
    # Replace atomically
    os.replace(tmp_path, out_path)

def _verify_image(path: str) -> bool:
    """Open the saved image to ensure it is readable and non-empty."""
    try:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return False
        with Image.open(path) as im:
            im.load()
            # Basic sanity checks
            if im.size[0] <= 0 or im.size[1] <= 0:
                return False
        return True
    except Exception:
        return False

def _thumb_signature(img: Image.Image, size: int = 32) -> list:
    """Return a small list signature of the image for quick similarity checks."""
    try:
        thumb = img.resize((size, size))
        data = list(thumb.getdata())
        thumb.close()
        return data
    except Exception:
        return []

def _signature_distance(sig_a: list, sig_b: list) -> float:
    if not sig_a or not sig_b or len(sig_a) != len(sig_b):
        return 1.0
    # Normalized L1 distance per channel
    total = 0
    max_total = 255 * 3 * len(sig_a)
    for (a0, a1, a2, *_), (b0, b1, b2, *_) in zip(sig_a, sig_b):
        total += abs(a0 - b0) + abs(a1 - b1) + abs(a2 - b2)
    return total / max_total if max_total else 1.0

def _magick_available() -> bool:
    if not USE_IMAGEMAGICK_FALLBACK:
        return False
    exe = shutil.which("magick") or shutil.which("convert")
    return exe is not None

def _convert_with_imagemagick(psd_path: str, out_path: str, fmt: str) -> bool:
    """Use ImageMagick to convert PSD to target format as a last-resort fallback."""
    exe = shutil.which("magick") or shutil.which("convert")
    if not exe:
        return False
    try:
        args = [exe]
        if os.path.basename(exe).lower() == 'magick' or exe.lower().endswith('magick.exe'):
            # new IM: 'magick' is the dispatcher, command is sequence
            pass
        # Build command
        # Flatten on black and ensure sRGB. For BMP, force BMP3.
        cmd = args + [
            psd_path,
            '-background', 'black',
            '-alpha', 'background',
            '-flatten',
            '-colorspace', 'sRGB'
        ]
        if fmt.lower() == 'bmp':
            cmd += ['-define', 'bmp:format=bmp3']
        # Output path
        cmd.append(out_path)
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return _verify_image(out_path)
    except Exception as e:
        log(f"[IMAGEMAGICK][ERROR] {e}")
        return False

def _render_via_imagemagick_to_rgba(psd_path: str) -> Image.Image | None:
    """Render PSD to a temporary PNG via ImageMagick and return it as a Pillow RGBA image."""
    if not _magick_available():
        return None
    tmp_dir = tempfile.gettempdir()
    tmp_png = os.path.join(tmp_dir, f"_im_psd_render_{os.getpid()}_{abs(hash(psd_path)) & 0xFFFFFFFF}.png")
    try:
        ok = _convert_with_imagemagick(psd_path, tmp_png, fmt='png')
        if not ok:
            return None
        im = Image.open(tmp_png).convert('RGBA')
        im.load()
        return im
    except Exception as e:
        log(f"[IMAGEMAGICK][RENDER][ERROR] {e}")
        return None
    finally:
        try:
            if os.path.exists(tmp_png):
                os.remove(tmp_png)
        except Exception:
            pass

def psd_to_bmp(psd_path, bmp_path):
    """
    Rule:
    - Export PSD to BMP with 32bpp BGRA (TrueColorAlpha), black background for transparency.
    - Only called for PSDs not in 'Upscale' folders.
    Ensures full composite render and atomic, verified save.
    """
    try:
        rgba = _render_psd_rgba(psd_path)
        try:
            flattened = _flatten_on_black(rgba)
        finally:
            # Release source rgba promptly
            rgba.close()
        # Optional sanity check: warn if almost all pixels are black after flatten
        try:
            # Downsample to speed up counting
            sample = flattened.resize((max(1, flattened.size[0] // 8), max(1, flattened.size[1] // 8)))
            non_black = sum(1 for p in sample.getdata() if p[0] or p[1] or p[2])
            total = sample.size[0] * sample.size[1]
            nb_ratio = (non_black / total) if total else 0.0
            if total > 0 and nb_ratio < 0.001:
                log(f"[WARN] Flattened image appears almost entirely black: non_black_ratio={nb_ratio:.6f} | {psd_path}")
                # Avoid overwriting an existing BMP with likely-bad content
                if os.path.exists(bmp_path):
                    log(f"[SKIP] Not overwriting existing BMP due to near-black render: {bmp_path}")
                    sample.close()
                    flattened.close()
                    return
                # Try ImageMagick fallback if available
                if _magick_available():
                    ok = _convert_with_imagemagick(psd_path, bmp_path, fmt='bmp')
                    if ok:
                        log(f"[FALLBACK] Converted via ImageMagick: {bmp_path}")
                        sample.close()
                        flattened.close()
                        return
                # Else, proceed to save but warn
                log("[WARN] Proceeding to save near-black render (no fallback available).")
            sample.close()
        except Exception:
            pass
        # Save as BMP with configured bit depth
        bits = 32 if SAVE_BMP_BITS not in (24, 32) else SAVE_BMP_BITS
        src_sig = _thumb_signature(flattened)
        _save_atomic(flattened, bmp_path, format='BMP', bits=bits)
        flattened.close()
        if not _verify_image(bmp_path):
            raise RuntimeError("Verification failed after BMP save (file unreadable or empty)")
        # Compare signatures between flattened and saved BMP
        try:
            with Image.open(bmp_path) as _bmp:
                _bmp.load()
                bmp_sig = _thumb_signature(_bmp)
            dist = _signature_distance(src_sig, bmp_sig)
            if dist > 0.02:  # Allow small encoder differences
                log(f"[WARN] BMP differs from source signature (dist={dist:.4f}).")
                if DEBUG_SAVE_ON_ANOMALY:
                    debug_png = os.path.splitext(bmp_path)[0] + ".debug.png"
                    try:
                        # Re-render quickly for debug image
                        rgba_dbg = _render_psd_rgba(psd_path)
                        _save_atomic(rgba_dbg, debug_png, format='PNG')
                        rgba_dbg.close()
                        log(f"[DEBUG] Wrote debug PNG: {debug_png}")
                    except Exception as de:
                        log(f"[DEBUG][ERROR] Failed to write debug PNG: {de}")
                if RETRY_WITH_24BPP_ON_ANOMALY and bits == 32:
                    # Retry with 24bpp RGB
                    rgba2 = _render_psd_rgba(psd_path)
                    try:
                        flat2 = _flatten_on_black(rgba2)
                    finally:
                        rgba2.close()
                    rgb = flat2.convert('RGB')
                    try:
                        _save_atomic(rgb, bmp_path, format='BMP', bits=24)
                        log(f"[RETRY] Re-saved as 24bpp BMP due to anomaly: {bmp_path}")
                    finally:
                        flat2.close()
                        rgb.close()
        except Exception as cmp_e:
            log(f"[WARN] Post-save comparison failed: {cmp_e}")
        log(f"Exported: {bmp_path} [BMP {bits}bpp]")
    except Exception as e:
        log(f"[ERROR] Failed to process {psd_path}: {e}")

def psd_to_png(psd_path, png_path):
    """
    Rule:
    - Export PSD to PNG with RGBA (TrueColorAlpha), black background for transparency.
    - Only called for PSDs in 'Upscale' folders.
    Ensures full composite render and atomic, verified save.
    """
    try:
        rgba = _render_psd_rgba(psd_path)
        try:
            flattened = _flatten_on_black(rgba)
        finally:
            rgba.close()
        _save_atomic(flattened, png_path, format='PNG')
        flattened.close()
        if not _verify_image(png_path):
            raise RuntimeError("Verification failed after PNG save (file unreadable or empty)")
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
    processed_count = 0
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
                        processed_count += 1
                    else:
                        if LOG_SKIPS:
                            log(f"[Upscale][SKIP] {png_path} is up to date.")
                        # else: do not print anything when skipping
                else:
                    bmp_path = os.path.splitext(psd_path)[0] + '.bmp'
                    if should_export(psd_path, bmp_path):
                        log(f"Converting: {psd_path} -> {bmp_path}")
                        psd_to_bmp(psd_path, bmp_path)
                        processed_count += 1
                    else:
                        if LOG_SKIPS:
                            log(f"[SKIP] {bmp_path} is up to date.")
                        # else: do not print anything when skipping
            # Periodically force GC to reduce peak memory usage on very large PSDs
            if processed_count and processed_count % 10 == 0:
                gc.collect()

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
    BTN_ORANGE = "#d96614"  # orange for hex fix
    STATUS_FG = "#8ec07c"   # soft green for status

    root = tk.Tk()
    root.title("PSD Batch Export Tool")
    root.geometry("400x380")
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

    @threaded
    def do_remove_upscale_psds():
        status_var.set("Removing *_upscale.psd in Upscale folders...")
        for folder in ROOTS:
            abs_folder = os.path.join(parent_dir, folder)
            if os.path.isdir(abs_folder):
                remove_upscale_psds(abs_folder)
        status_var.set("PSD removal complete.")

    def do_analyze():
        messagebox.showinfo("Analyze Output", "Analysis functionality can be customized here.")

    @threaded
    def do_fix_hex_padding():
        status_var.set("Scanning and fixing hex zero-padding in Upscale folders...")
        summary = run_fix_upscale_hex_padding(parent_dir)
        status_var.set(f"Hex fix complete. Files fixed: {summary['files_fixed']}, Folders fixed: {summary['folders_fixed']}")

    tk.Label(root, text="PSD Batch Export Tool", font=("Arial", 16, "bold"), bg=DARK_BG, fg=DARK_FG).pack(pady=10)
    tk.Button(root, text="Run Batch Export", width=30, command=do_export, bg=BTN_GREEN, fg=DARK_FG, activebackground=BTN_GREEN, activeforeground=DARK_FG, relief=tk.FLAT).pack(pady=8)
    tk.Button(root, text="Remove BMPs in Upscale Folders", width=30, command=do_remove_bmps, bg=BTN_BLUE, fg=DARK_FG, activebackground=BTN_BLUE, activeforeground=DARK_FG, relief=tk.FLAT).pack(pady=8)
    tk.Button(root, text="Delete *_upscale.psd in Upscale Folders", width=30, command=do_remove_upscale_psds, bg=BTN_PURPLE, fg=DARK_FG, activebackground=BTN_PURPLE, activeforeground=DARK_FG, relief=tk.FLAT).pack(pady=8)
    tk.Button(root, text="Fix Hex Zero Padding in Upscale", width=30, command=do_fix_hex_padding, bg=BTN_ORANGE, fg=DARK_FG, activebackground=BTN_ORANGE, activeforeground=DARK_FG, relief=tk.FLAT).pack(pady=8)
    tk.Button(root, text="Quit", width=30, command=root.quit, bg=BTN_GRAY, fg=DARK_FG, activebackground=BTN_GRAY, activeforeground=DARK_FG, relief=tk.FLAT).pack(pady=8)
    tk.Label(root, textvariable=status_var, bg=DARK_BG, fg=STATUS_FG, font=("Arial", 10, "bold")).pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    # If no CLI args are given, show the UI; otherwise run once in CLI mode.
    if len(sys.argv) == 1:
        main_ui()
    else:
        main()