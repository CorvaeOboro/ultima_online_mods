"""
PROJECT HTML WEBPAGE GENERATOR - Ultima Online Art Mods Documentation Generator
Generates HTML documentation pages from project structure and README.md content
Searches project folders (ART, UI, ENV) and creates HTML pages with image galleries

index , menu , main , art , ui , env , tools , install 

===============================================================================
GENERATED PAGES
===============================================================================

1. index.html
   - Frameset layout with side navigation and main content area
   - Entry point for the documentation website
   - Loads menu frame and main content frame

2. ultima_art_mods_menu.htm
   - Side navigation menu frame
   - Links to all major sections (HOME, ART, UI, ENV, TOOLS, INSTALL)
   - Dark themed with hover effects
   - Fixed position navigation

3. ultima_art_mods_main.htm
   - Main landing page with overview
   - Featured mod gallery with thumbnails
   - Category summaries with group counts
   - Download buttons and quick links
   - Credits and license information

4. ultima_art_mods_art.htm
   - ART category showcase page
   - Lists all ART mod groups (Magic Scrolls, Reagents, Food, Weapons, etc.)
   - Displays composite preview images for each group
   - Shows render counts for items with upscale versions
   - Organized by group sections with galleries

5. ultima_art_mods_ui.htm
   - UI category showcase page
   - Lists all UI mod groups (Magic Spells, Dark Scrolls, Buffs, etc.)
   - Displays composite preview images for each group
   - Shows render counts for gump overrides
   - Organized by group sections with galleries

6. ultima_art_mods_env.htm
   - ENV category showcase page
   - Lists all ENV mod groups (Cave Dark, Dirt Hills, Forest Grove, etc.)
   - Displays environment texture previews
   - Shows landtile and texture modifications
   - Organized by group sections with galleries

7. ultima_art_mods_tools.htm
   - Modding tools and technical documentation
   - Parsed from Z_Tools/README.md sections
   - Tool descriptions with screenshots (mod_selector, psd_to_GumpOverrides)
   - MUL file format information
   - UOFiddler and Mulpatcher usage guides
   - Environment texture workflow (TEX_to_ART_M)
   - Autopatch, naming conventions, hues documentation
   - Links to external resources

8. ultima_art_mods_install.htm
   - Installation and patching instructions
   - UO Outlands GumpOverrides method (gumps only)
   - UOFiddler MassImport method (recommended)
   - Mulpatcher autopatch method (alternative previous method)
   - Step-by-step guides with troubleshooting examples
   - Links to additional resources

===============================================================================
PROJECT CATEGORIES SCANNED
===============================================================================

ART/ - Item Art (Art_S in MUL files)
   - Items, placed objects, creatures, equipment
   - Groups: MagicScrolls, Reagents, Food, Gems, Potions, Books, Weapons,
            Tools, Jewelry, Keys, Vases, Creatures, Eggs, Talismans, etc.
   - Files: Base PSD/BMP in group folder, upscale PNG/PSD in Upscale subfolder
   - Composite previews: 00_*.png , 00_*.jpg , 00_*.gif , 00_*.webp
 
UI/ - User Interface (Gumps in MUL files)
   - Menus, character sheets, spell icons, scrolls, containers
   - Groups: MagicSpells, DarkScrolls, Buffs, ArchStone, EquipSlots,
            SpellsChivalry, SpellsNecromancy, SpellsMysticism, MainMenu, etc.
   - Files: Base PSD/BMP in group folder, upscale PNG/PSD in Upscale subfolder
   - Composite previews: 00_*.png , 00_*.jpg , 00_*.gif

ENV/ - Environment Textures and Landtiles (Textures and Art_M in MUL files)
   - Land textures, isometric landtiles, terrain modifications
   - Groups: CaveDark, DirtHills, FarmLands, ForestGrove, MountainPath,
            SandDunes, SnowRidge, HeartWood, Paroxysmus, etc.
   - Files: Textures (TEX), landtiles (ART_M), items (ART_S) in subfolders
   - Composite previews: 00_*.png , 00_*.jpg , 00_*.gif

===============================================================================
CONTENT SOURCES
===============================================================================

Project Structure:
   - Search ART/, UI/, ENV/ folders recursively
   - Finds composite images (00_* prefix) for group previews
   - Counts individual renders in Upscale/ subfolders
   - Detects .png, .jpg, .gif, .bmp, .psd files

README.md Sections:
   - Modding Tools / Notes
   - Modding Notes
   - MUL (file format info)
   - TOOLS (UOFiddler, Mulpatcher, ImageMagick)
   - ENVIRONMENT TEXTURES (TEX_to_ART_M workflow)
   - AUTOPATCH (automation methods)
   - NAMING (file naming conventions)
   - HUES (color gradient mapping)
   - LINKS (community resources)

Image URLs:
   - GitHub raw content URLs 
   - Base: https://raw.githubusercontent.com/CorvaeOboro/ultima_online_mods/master
   - Converts local filespaths of the images to GitHub URLs 

===============================================================================
FEATURES
===============================================================================

- project structure scanning
- Markdown to HTML conversion
- Category-specific organization
- Navigation menu with frameset layout
- Installation guides with multiple methods
- Tool documentation with screenshots

===============================================================================
USAGE
===============================================================================

GUI Mode (Default):
    python 00_html_generator.py
    
    - Opens Tkinter GUI with visual interface
    - Left panel: Project info and generation logs
    - Right panel: Page previews side-by-side
    - Buttons: Scan Project → Generate HTML → Preview Pages → Open in Browser
    
    Preview Controls:
    - Middle Mouse Button: Hold and drag to pan
    - Mouse Scroll Wheel: Zoom in/out (0.1x to 5.0x)
    - Pages displayed side-by-side with labels
    
CLI Mode (Command Line):
    python 00_html_generator.py --cli
    
Output location: docs/ folder in project root
Open: docs/index.html in web browser

TOOLSGROUP::RENDER
SORTGROUP::7
SORTPRIORITY::73
STATUS::WIP
VERSION::20251128
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import webbrowser
from io import BytesIO
try:
    from PIL import Image, ImageTk, ImageGrab
except ImportError:
    Image = None
    ImageTk = None
    ImageGrab = None

#====================================================================================
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DOCS_DIR = PROJECT_ROOT / "docs"
PREVIEW_CACHE_DIR = SCRIPT_DIR / "_preview_cache"
README_PATH = PROJECT_ROOT / "README.md"

# GitHub raw content base URL
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/CorvaeOboro/ultima_online_mods/master"

# HTML styling constants
HTML_STYLE = """
body {
    background-color: #000000;
    font-family: Verdana, Arial, Helvetica, sans-serif;
    color: #666666;
    margin: 20px;
    padding: 0;
    text-align: center;
}
p {
    text-align: center;
}
h1 {
    color: #888888;
    text-align: center;
}
h2 {
    color: #777777;
    margin-top: 30px;
    text-align: center;
}
a {
    color: #5c9ccc;
    text-decoration: none;
}
a:hover {
    color: #7cb4e4;
    text-decoration: underline;
}
img {
    border: none;
    margin: 0;
    display: block;
}
.thumbnail {
    display: inline-block;
    margin: 10px;
    vertical-align: top;
}
.thumbnail img {
    max-width: 200px;
    max-height: 200px;
}
.gallery {
    display: block;
    margin: 20px 0;
    text-align: center;
}
.gallery-item {
    display: block;
    text-align: center;
    margin: 0;
}
.gallery-item img {
    border: none;
    margin: 0;
    display: block;
    margin-left: auto;
    margin-right: auto;
}
.gallery-item .caption {
    margin-top: 5px;
    color: #999999;
    font-size: 12px;
}
.category-section {
    margin: 40px 0;
    padding: 20px;
    background-color: #0a0a0a;
    border: 1px solid #222222;
    border-radius: 5px;
}
.group-section {
    margin: 20px 0;
    padding: 15px;
    background-color: #111111;
    border-left: 3px solid #444444;
}
ul {
    line-height: 1.8;
    list-style-position: inside;
    text-align: center;
}
code {
    background-color: #1a1a1a;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
}
.download-button {
    display: inline-block;
    padding: 12px 24px;
    margin: 10px 5px;
    background-color: #2a4a6a;
    color: #ffffff;
    border-radius: 5px;
    font-weight: bold;
}
.download-button:hover {
    background-color: #3a5a7a;
}
"""

#====================================================================================

class PageLayout:
    """Defines the structure and content of a page - used by both HTML and canvas renderers"""
    
    def __init__(self, name, title):
        self.name = name
        self.title = title
        self.sections = []
        
    def add_section(self, section_type, content, **kwargs):
        """Add a section to the page layout"""
        self.sections.append({
            'type': section_type,
            'content': content,
            **kwargs
        })
        return self
        
    def add_header(self, text, level=1):
        """Add a header section"""
        return self.add_section('header', text, level=level)
        
    def add_text(self, text):
        """Add a text paragraph"""
        return self.add_section('text', text)
        
    def add_gallery(self, images, columns=3):
        """Add an image gallery"""
        return self.add_section('gallery', images, columns=columns)
        
    def add_group(self, group_name, group_data):
        """Add a group section with title and images"""
        return self.add_section('group', group_data, group_name=group_name)
        
    def add_list(self, items):
        """Add a bullet list"""
        return self.add_section('list', items)
        
    def add_button(self, text, url):
        """Add a download/link button"""
        return self.add_section('button', text, url=url)

def build_main_page_layout(structure):
    """Build layout definition for main page from README.md"""
    layout = PageLayout('main', 'Ultima Online Art Mods')
    
    # Read and convert README.md to HTML
    if README_PATH.exists():
        with open(README_PATH, 'r', encoding='utf-8') as f:
            readme_content = f.read()
        
        # Convert markdown to HTML with GitHub URLs
        readme_html = markdown_to_html(readme_content)
        
        # Add the converted README as raw HTML
        layout.add_section('html', readme_html)
    else:
        # Fallback if README doesn't exist
        layout.add_header('Ultima Online Art Mods', level=1)
        layout.add_text('Custom art modifications for Ultima Online including items, UI elements, and environment textures.')
        layout.add_button('Download from GitHub', 'https://github.com/CorvaeOboro/ultima_online_mods')
        
        # Category summaries with preview images
        for category, groups in sorted(structure.items()):
            layout.add_header(f'{category} Mods', level=2)
            
            # Get composite images from first few groups as preview
            preview_images = []
            for group_name, items in list(groups.items())[:6]:
                if group_name == '_base':
                    continue
                composites = [i for i in items if i['type'] == 'composite']
                if composites:
                    preview_images.append({
                        'path': composites[0]['path'],
                        'name': group_name
                    })
            
            if preview_images:
                layout.add_gallery(preview_images, columns=3)
    
    return layout

def clean_group_name(group_name, category):
    """Remove category prefix from group name and capitalize
    Example: 'ART_Fish' -> 'FISH', 'UI_ArchStone' -> 'ARCHSTONE'
    """
    # Remove category prefix (e.g., "ART_", "UI_", "ENV_")
    prefix = f"{category}_"
    if group_name.startswith(prefix):
        cleaned = group_name[len(prefix):]
    else:
        cleaned = group_name
    
    # Capitalize the result
    return cleaned.upper()

def build_category_page_layout(category, groups, structure, group_metadata=None, image_metadata=None):
    """Build layout definition for category page with priority sorting"""
    layout = PageLayout(category.lower(), f'{category} Mods')
    group_metadata = group_metadata or {}
    image_metadata = image_metadata or {}
    
    layout.add_header(f'{category} Modifications', level=1)
    
    # Add base folder images first (if any)
    base_items = groups.get('_base', [])
    if base_items:
        composites = [i for i in base_items if i['type'] == 'composite']
        if composites:
            layout.add_header(f'{category} Base Images', level=2)
            
            base_images = []
            for comp in composites:
                base_images.append({
                    'path': comp['path'],
                    'name': comp['name']
                })
            
            # Sort base images by priority
            def get_image_priority(img):
                priority = image_metadata.get(str(img['path']), {}).get('priority', 0)
                return 999 if priority == 0 else priority
            
            base_images.sort(key=get_image_priority)
            layout.add_gallery(base_images, columns=3)
    
    # Sort groups by the minimum priority of their images (lower number = higher priority, appears first)
    # This way groups are ordered by their highest priority image
    def get_group_sort_priority(group_item):
        group_name, items = group_item
        # Skip the special '_base' key
        if group_name == '_base':
            return -1  # Put base at the very top (but we already handled it above)
        composites = [i for i in items if i['type'] == 'composite']
        if composites:
            # Get minimum priority from all NON-EXCLUDED images in this group
            priorities = []
            for comp in composites:
                comp_path = str(comp['path'])
                meta = image_metadata.get(comp_path, {})
                is_excluded = meta.get('excluded', False)
                priority = meta.get('priority', 0)
                
                # Skip excluded images - they don't contribute to group sorting
                if is_excluded:
                    print(f"[DEBUG]   Image: {comp['path'].name} -> EXCLUDED (skipped)")
                    continue
                
                # Treat 0 as "no priority set" (same as 999)
                if priority == 0:
                    priority = 999
                
                priorities.append(priority)
                # Debug: show path and priority lookup
                if priority != 999:
                    print(f"[DEBUG]   Image: {comp['path'].name} -> priority: {priority}")
            
            min_priority = min(priorities) if priorities else 999
            # Debug: print group sorting info
            print(f"[DEBUG] Group '{group_name}' -> min priority: {min_priority}")
            return min_priority
        return 999
    
    sorted_groups = sorted(groups.items(), key=get_group_sort_priority)
    
    # Debug: Show final sorted order
    print(f"\n[DEBUG] === FINAL SORTED ORDER for {category} ===")
    for idx, (group_name, items) in enumerate(sorted_groups, 1):
        composites = [i for i in items if i['type'] == 'composite']
        if composites:
            priorities = [image_metadata.get(str(comp['path']), {}).get('priority', 999) for comp in composites]
            min_priority = min(priorities) if priorities else 999
            print(f"[DEBUG] {idx}. {group_name} (priority: {min_priority})")
    print(f"[DEBUG] =====================================\n")
    
    # Add each group with its composite images
    for group_name, items in sorted_groups:
        # Skip the '_base' key as we already handled it
        if group_name == '_base':
            continue
            
        composites = [i for i in items if i['type'] == 'composite']
        
        if composites:
            # Group header - clean the name by removing category prefix
            display_name = clean_group_name(group_name, category)
            # Store original group_name for metadata lookups
            layout.add_section('header', display_name, level=2, original_group_name=group_name)
            
            # Show all composite images for this group
            group_images = []
            for comp in composites:
                group_images.append({
                    'path': comp['path'],
                    'name': comp['name']
                })
            
            # Sort images by priority (lower number = higher priority, appears first)
            # Treat 0 as "no priority set" (same as 999)
            def get_image_priority(img):
                priority = image_metadata.get(str(img['path']), {}).get('priority', 0)
                return 999 if priority == 0 else priority
            
            group_images.sort(key=get_image_priority)
            
            # Add gallery of composite images
            layout.add_gallery(group_images, columns=3)
    
    return layout

def build_tools_page_layout():
    """Build layout definition for tools page"""
    layout = PageLayout('tools', 'Modding Tools')
    
    layout.add_header('Modding Tools & Notes', level=1)
    layout.add_text('Python scripts and utilities for creating Ultima Online art modifications.')
    
    layout.add_header('Available Tools', level=2)
    layout.add_list([
        '00_mod_selector.py - Select and export mod groups',
        '00_project_dashboard.py - Review and manage art items',
        '01_psd_to_bmp_batch.py - Batch convert PSD to BMP',
        '02_image_composite_multi.py - Create composite previews'
    ])
    
    return layout

def build_install_page_layout():
    """Build layout definition for install page"""
    layout = PageLayout('install', 'Installation Guide')
    
    layout.add_header('Installation Instructions', level=1)
    layout.add_text('Choose one of the following methods to install the art modifications.')
    
    layout.add_header('Method 1: UO Outlands (Easiest)', level=2)
    layout.add_list([
        'Copy PNG files to UO Outlands/GumpOverrides/',
        'Restart client to see changes'
    ])
    
    layout.add_header('Method 2: UOFiddler (Recommended)', level=2)
    layout.add_list([
        'Download UOFiddler',
        'Load MUL files from your UO directory',
        'Use MassImport with provided XML files',
        'Save changes back to MUL files'
    ])
    
    return layout

# ===== RENDERERS: Convert PageLayout to output formats =====

def render_layout_to_html(layout, image_metadata=None, group_metadata=None, show_excluded=False):
    """Convert PageLayout to HTML string"""
    html_parts = []
    image_metadata = image_metadata or {}
    group_metadata = group_metadata or {}
    
    # Header
    html_parts.append(f"""<!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>{layout.title}</title>
<style type="text/css">
{HTML_STYLE}
</style>
</head>
<body>
""")
    
    # Track if we should skip sections (for excluded groups)
    skip_until_next_header = False
    last_was_group_gallery = False  # Track if last section was a group gallery
    
    # Render each section
    for section in layout.sections:
        section_type = section['type']
        content = section['content']
        
        if section_type == 'header':
            level = section.get('level', 1)
            
            # For H2 headers (group names), check if group is excluded
            if level == 2:
                # Add extra spacing before new group (if previous section was a group gallery)
                if last_was_group_gallery:
                    html_parts.append('<br>\n')
                
                original_name = section.get('original_group_name', content)
                group_meta = group_metadata.get(original_name, {})
                is_excluded = group_meta.get('excluded', False)
                
                # Skip entire group if excluded (unless show_excluded is True)
                if is_excluded and not show_excluded:
                    skip_until_next_header = True
                    continue
                else:
                    skip_until_next_header = False
            
            html_parts.append(f"<h{level}>{content}</h{level}>\n")
            last_was_group_gallery = False
            
        elif skip_until_next_header:
            # Skip all content until we hit the next header
            continue
            
        elif section_type == 'text':
            html_parts.append(f"<p>{content}</p>\n")
            last_was_group_gallery = False
            
        elif section_type == 'button':
            url = section.get('url', '#')
            html_parts.append(f'<a href="{url}" class="download-button">{content}</a>\n')
            last_was_group_gallery = False
            
        elif section_type == 'list':
            html_parts.append("<ul>\n")
            for item in content:
                html_parts.append(f"  <li>{item}</li>\n")
            html_parts.append("</ul>\n")
            last_was_group_gallery = False
            
        elif section_type == 'gallery':
            columns = section.get('columns', 3)
            
            # Filter out excluded images (same logic as canvas renderer)
            filtered_images = []
            for img_data in content:
                img_path = str(img_data.get('path', ''))
                img_meta = image_metadata.get(img_path, {})
                is_excluded = img_meta.get('excluded', False)
                
                # Skip excluded images unless show_excluded is True
                if is_excluded and not show_excluded:
                    continue
                
                filtered_images.append(img_data)
            
            # Only render gallery if there are images to show
            if filtered_images:
                html_parts.append('<div class="gallery">\n')
                for img_data in filtered_images:
                    img_path = img_data['path']
                    img_name = img_data.get('name', '')
                    # Convert to GitHub URL
                    rel_path = str(img_path).replace('\\', '/').split('ultima_online_mods/')[-1]
                    github_url = f"{GITHUB_RAW_BASE}/{rel_path}"
                    
                    # Get caption from metadata
                    img_meta = image_metadata.get(str(img_path), {})
                    caption = img_meta.get('caption', '')
                    
                    html_parts.append(f'  <div class="gallery-item">\n')
                    html_parts.append(f'    <img src="{github_url}" alt="{img_name}" />\n')
                    if caption:
                        html_parts.append(f'    <div class="caption">{caption}</div>\n')
                    html_parts.append(f'  </div>\n')
                html_parts.append('</div>\n')
                last_was_group_gallery = True
            
        elif section_type == 'html':
            # Raw HTML content (from README conversion)
            html_parts.append(content)
            html_parts.append('\n')
            last_was_group_gallery = False
    
    # Footer
    html_parts.append("""
</body>
</html>
""")
    
    return ''.join(html_parts)

def render_layout_to_canvas(layout, canvas, start_x=20, start_y=20, width=280, image_metadata=None, group_metadata=None, show_excluded=False, use_priority_sort=True):
    """
    Convert PageLayout to canvas visual representation
    Returns tuple: (PIL Image, image_bboxes dict, group_bboxes dict)
    image_bboxes: {img_path: (x1, y1, x2, y2)}
    group_bboxes: {group_name: (x1, y1, x2, y2)}
    image_metadata: dict of image settings (excluded, priority, type)
    group_metadata: dict of group settings (excluded, priority)
    show_excluded: if False, skip excluded images and groups
    use_priority_sort: if True, sort images by priority (lower number = appears first/at top)
    """
    from PIL import ImageDraw, ImageFont
    
    image_bboxes = {}
    group_bboxes = {}
    image_metadata = image_metadata or {}
    group_metadata = group_metadata or {}
    
    items = []
    y = start_y
    x = start_x
    line_height = 20
    padding = 10
    
    # Colors
    bg_color = '#0a0a0a'  # Almost pure black
    header_color = '#888888'
    text_color = '#666666'
    button_color = '#2a4a6a'
    group_bg = '#111111'
    
    # Create a taller image to accommodate full page content
    # Calculate approximate height based on sections (much larger to avoid clipping)
    # Increased base height to handle pages with many large images
    estimated_height = max(10000, len(layout.sections) * 500)
    img = Image.new('RGB', (width, estimated_height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Try to load fonts
    try:
        h1_font = ImageFont.truetype("segoeui.ttf", 18)
        h2_font = ImageFont.truetype("segoeui.ttf", 14)
        text_font = ImageFont.truetype("segoeui.ttf", 10)
    except:
        h1_font = ImageFont.load_default()
        h2_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
    
    current_y = padding
    last_was_group_gallery = False  # Track if last section was a group gallery
    
    # Render each section
    for section in layout.sections:
        section_type = section['type']
        content = section['content']
        
        if section_type == 'header':
            level = section.get('level', 1)
            font = h1_font if level == 1 else h2_font
            color = header_color
            header_text = str(content)[:40]
            
            # For H2 headers (group names), check if group is excluded
            if level == 2:
                # Add extra spacing before new group (if previous section was a group gallery)
                if last_was_group_gallery:
                    current_y += 20  # Extra spacing between groups
                
                original_name = section.get('original_group_name', header_text)
                group_meta = group_metadata.get(original_name, {})
                is_excluded = group_meta.get('excluded', False)
                
                # Skip entire group if excluded (unless show_excluded is True)
                if is_excluded and not show_excluded:
                    # Skip this header and all following sections until next header
                    continue
            
            # Draw header text (display name) - centered
            header_y_start = current_y
            last_was_group_gallery = False
            # Calculate text width for centering
            bbox = draw.textbbox((0, 0), header_text, font=font)
            text_width = bbox[2] - bbox[0]
            centered_x = (width - text_width) // 2
            
            draw.text((centered_x, current_y), header_text, fill=color, font=font)
            current_y += 25 if level == 1 else 20
            
            # Store bbox for H2 headers (group names) for click detection
            # Use original name for metadata key
            if level == 2:
                original_name = section.get('original_group_name', header_text)
                group_bboxes[original_name] = (padding, header_y_start, width - padding, current_y)
            
            # Draw underline for h1 (centered)
            if level == 1:
                underline_margin = 20
                draw.line([(underline_margin, current_y), (width-underline_margin, current_y)], fill='#333333', width=2)
                current_y += 5
                
        elif section_type == 'text':
            # Word wrap text - centered
            words = str(content).split()
            line = ""
            for word in words:
                test_line = line + " " + word if line else word
                if len(test_line) > 35:  # Approximate character limit
                    # Center the line
                    bbox = draw.textbbox((0, 0), line, font=text_font)
                    text_width = bbox[2] - bbox[0]
                    centered_x = (width - text_width) // 2
                    draw.text((centered_x, current_y), line, fill=text_color, font=text_font)
                    current_y += 15
                    line = word
                else:
                    line = test_line
            if line:
                # Center the last line
                bbox = draw.textbbox((0, 0), line, font=text_font)
                text_width = bbox[2] - bbox[0]
                centered_x = (width - text_width) // 2
                draw.text((centered_x, current_y), line, fill=text_color, font=text_font)
                current_y += 15
            current_y += 5
            last_was_group_gallery = False
            
        elif section_type == 'button':
            # Draw button rectangle - centered
            button_height = 25
            button_width = width - padding * 2
            button_x = padding
            
            draw.rectangle(
                [(button_x, current_y), (button_x + button_width, current_y + button_height)],
                fill=button_color,
                outline='#3a5a7a'
            )
            # Button text - centered
            button_text = str(content)[:30]
            bbox = draw.textbbox((0, 0), button_text, font=text_font)
            text_width = bbox[2] - bbox[0]
            text_x = button_x + (button_width - text_width) // 2
            draw.text((text_x, current_y + 5), button_text, fill='#ffffff', font=text_font)
            current_y += button_height + 10
            last_was_group_gallery = False
            
        elif section_type == 'list':
            # Center list items
            for item in content[:5]:  # Limit items
                list_text = f"• {str(item)[:35]}"
                bbox = draw.textbbox((0, 0), list_text, font=text_font)
                text_width = bbox[2] - bbox[0]
                centered_x = (width - text_width) // 2
                draw.text((centered_x, current_y), list_text, fill=text_color, font=text_font)
                current_y += 15
            current_y += 5
            last_was_group_gallery = False
            
        elif section_type == 'gallery':
            # Draw actual images at real size (no boxes)
            # One image per row for now (vertical stacking)
            columns = 1
            col_spacing = 0
            col_width = width - padding * 2
            
            # Filter images based on exclusion status
            filtered_images = []
            for img_data in content:
                img_path = str(img_data.get('path', ''))
                img_meta = image_metadata.get(img_path, {})
                is_excluded = img_meta.get('excluded', False)
                
                # Skip excluded images unless show_excluded is True
                if is_excluded and not show_excluded:
                    continue
                
                filtered_images.append(img_data)
            
            # Sort by priority if enabled (lower number = higher priority, appears first)
            # Treat 0 as "no priority set" (same as 999)
            if use_priority_sort:
                def get_preview_priority(img):
                    priority = image_metadata.get(str(img.get('path', '')), {}).get('priority', 0)
                    return 999 if priority == 0 else priority
                filtered_images.sort(key=get_preview_priority)
            
            images_to_show = filtered_images[:12]  # Show more images
            
            # Track row heights for proper spacing
            row_y_positions = {}
            row_max_heights = {}
            actual_index = 0  # Track actual placement index
            
            for img_data in images_to_show:
                col = actual_index % columns
                row = actual_index // columns
                
                # Calculate position with proper spacing
                img_x = padding + col * (col_width + col_spacing)
                
                # Get row start y
                if row == 0:
                    row_y_positions[row] = current_y
                elif row not in row_y_positions:
                    row_y_positions[row] = row_y_positions[row-1] + row_max_heights.get(row-1, 0) + 15
                
                img_y = row_y_positions[row]
                
                # Try to load and draw actual image, scaling if needed
                try:
                    img_path = img_data.get('path')
                    if img_path and Path(img_path).exists():
                        # Load image
                        comp_img = Image.open(img_path)
                        
                        # Scale image proportionally if it exceeds column width
                        if comp_img.width > col_width:
                            scale_factor = col_width / comp_img.width
                            new_width = col_width
                            new_height = int(comp_img.height * scale_factor)
                            comp_img = comp_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        
                        # Center the image horizontally
                        center_offset = (col_width - comp_img.width) // 2
                        centered_x = img_x + center_offset
                        
                        # Paste image (scaled or original size) - centered
                        if comp_img.mode == 'RGBA':
                            img.paste(comp_img, (centered_x, img_y), comp_img)
                        else:
                            img.paste(comp_img, (centered_x, img_y))
                        
                        # Get caption if exists
                        img_meta = image_metadata.get(str(img_path), {})
                        caption_text = img_meta.get('caption', '')
                        
                        # Calculate total height including caption
                        total_height = comp_img.height
                        if caption_text:
                            # Draw caption below image (centered)
                            caption_y = img_y + comp_img.height + 5
                            try:
                                caption_font = ImageFont.truetype("segoeui.ttf", 9)
                            except:
                                caption_font = text_font
                            
                            # Center caption text
                            bbox = draw.textbbox((0, 0), caption_text, font=caption_font)
                            caption_width = bbox[2] - bbox[0]
                            caption_x = img_x + (col_width - caption_width) // 2
                            
                            draw.text((caption_x, caption_y), caption_text, fill='#999999', font=caption_font)
                            total_height += 20  # Add height for caption
                        
                        # Store bounding box for click detection (includes caption area)
                        image_bboxes[str(img_path)] = (centered_x, img_y, centered_x + comp_img.width, img_y + total_height)
                        
                        # Track max height for this row
                        if row not in row_max_heights:
                            row_max_heights[row] = total_height
                        else:
                            row_max_heights[row] = max(row_max_heights[row], total_height)
                        
                        actual_index += 1
                except Exception as e:
                    # Skip on error (no placeholder)
                    pass
            
            # Move y position past all rows
            if row_y_positions:
                last_row = max(row_y_positions.keys())
                current_y = row_y_positions[last_row] + row_max_heights.get(last_row, 0) + 10
                last_was_group_gallery = True
            
    
    # Crop image to actual content height (add some padding at bottom)
    # Use actual content height, don't limit by estimated_height to avoid clipping
    actual_height = current_y + 20
    if actual_height > estimated_height:
        # If content exceeds estimate, expand the image
        new_img = Image.new('RGB', (width, actual_height), color=bg_color)
        new_img.paste(img, (0, 0))
        img = new_img
    else:
        img = img.crop((0, 0, width, actual_height))
    
    return img, image_bboxes, group_bboxes

def render_info_panel_to_canvas(info_messages, width=280, max_height=800):
    """Render project info panel as an image"""
    from PIL import ImageDraw, ImageFont
    
    bg_color = '#0a0a0a'
    text_color = '#cccccc'
    header_color = '#888888'
    
    # Try to load fonts
    try:
        header_font = ImageFont.truetype("segoeui.ttf", 12)
        text_font = ImageFont.truetype("consolas.ttf", 8)
    except:
        header_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
    
    # Calculate required height
    line_height = 12
    padding = 10
    estimated_height = min(max_height, len(info_messages) * line_height + padding * 2 + 30)
    
    img = Image.new('RGB', (width, estimated_height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Draw header
    draw.text((padding, padding), "PROJECT INFORMATION", fill=header_color, font=header_font)
    draw.line([(padding, padding + 20), (width - padding, padding + 20)], fill='#333333', width=1)
    
    # Draw info messages
    y = padding + 30
    for msg in info_messages[:60]:  # Limit to 60 lines
        # Truncate long lines
        display_msg = msg[:45] if len(msg) > 45 else msg
        draw.text((padding, y), display_msg, fill=text_color, font=text_font)
        y += line_height
        if y > estimated_height - padding:
            break
    
    return img

def render_log_panel_to_canvas(log_messages, width=280, max_height=800):
    """Render generation log panel as an image"""
    from PIL import ImageDraw, ImageFont
    
    bg_color = '#0a0a0a'
    text_color = '#88cc88'
    header_color = '#888888'
    
    # Try to load fonts
    try:
        header_font = ImageFont.truetype("segoeui.ttf", 12)
        text_font = ImageFont.truetype("consolas.ttf", 7)
    except:
        header_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
    
    # Calculate required height
    line_height = 10
    padding = 10
    estimated_height = min(max_height, len(log_messages) * line_height + padding * 2 + 30)
    
    img = Image.new('RGB', (width, estimated_height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Draw header
    draw.text((padding, padding), "GENERATION LOG", fill=header_color, font=header_font)
    draw.line([(padding, padding + 20), (width - padding, padding + 20)], fill='#333333', width=1)
    
    # Draw log messages (show last N messages)
    y = padding + 30
    display_messages = log_messages[-80:] if len(log_messages) > 80 else log_messages
    for msg in display_messages:
        # Truncate long lines
        display_msg = msg[:50] if len(msg) > 50 else msg
        draw.text((padding, y), display_msg, fill=text_color, font=text_font)
        y += line_height
        if y > estimated_height - padding:
            break
    
    return img

# ===== UTILITY FUNCTIONS =====

def ensure_docs_dir():
    """Ensure docs directory exists"""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Docs directory ready: {DOCS_DIR}")

def scan_project_structure():
    """
    Scan project folders and return organized structure
    Returns dict: {category: {group: [items], '_base': [base_items]}}
    """
    structure = {}
    
    for category in ["ART", "UI", "ENV"]:
        category_path = PROJECT_ROOT / category
        if not category_path.exists():
            continue
            
        structure[category] = {}
        
        # Scan base category folder for images (not in subfolders)
        base_items = []
        for img_file in category_path.glob("00_*.png"):
            if img_file.is_file():
                base_items.append({
                    "name": img_file.name,
                    "path": img_file,
                    "type": "composite"
                })
        for img_file in category_path.glob("00_*.jpg"):
            if img_file.is_file():
                base_items.append({
                    "name": img_file.name,
                    "path": img_file,
                    "type": "composite"
                })
        for img_file in category_path.glob("00_*.gif"):
            if img_file.is_file():
                base_items.append({
                    "name": img_file.name,
                    "path": img_file,
                    "type": "composite"
                })
        for img_file in category_path.glob("00_*.webp"):
            if img_file.is_file():
                base_items.append({
                    "name": img_file.name,
                    "path": img_file,
                    "type": "composite"
                })
        
        # Store base folder images with special key
        if base_items:
            structure[category]['_base'] = base_items
        
        # Scan group subfolders
        for group_folder in sorted(category_path.iterdir()):
            if not group_folder.is_dir() or group_folder.name.startswith('.'):
                continue
                
            group_name = group_folder.name
            items = []
            
            # Find composite images (preview images)
            for img_file in group_folder.glob("00_*.png"):
                items.append({
                    "name": img_file.name,
                    "path": img_file,
                    "type": "composite"
                })
            for img_file in group_folder.glob("00_*.jpg"):
                items.append({
                    "name": img_file.name,
                    "path": img_file,
                    "type": "composite"
                })
            for img_file in group_folder.glob("00_*.gif"):
                items.append({
                    "name": img_file.name,
                    "path": img_file,
                    "type": "composite"
                })
            for img_file in group_folder.glob("00_*.webp"):
                items.append({
                    "name": img_file.name,
                    "path": img_file,
                    "type": "composite"
                })
            
            # For ENV category, also scan ART_S subfolder for composite images
            if category == "ENV":
                art_s_folder = group_folder / "ART_S"
                if art_s_folder.exists():
                    for img_file in art_s_folder.glob("00_*.png"):
                        items.append({
                            "name": img_file.name,
                            "path": img_file,
                            "type": "composite"
                        })
                    for img_file in art_s_folder.glob("00_*.jpg"):
                        items.append({
                            "name": img_file.name,
                            "path": img_file,
                            "type": "composite"
                        })
                    for img_file in art_s_folder.glob("00_*.gif"):
                        items.append({
                            "name": img_file.name,
                            "path": img_file,
                            "type": "composite"
                        })
                    for img_file in art_s_folder.glob("00_*.webp"):
                        items.append({
                            "name": img_file.name,
                            "path": img_file,
                            "type": "composite"
                        })
                
            # Find upscale renders if available
            upscale_folder = group_folder / "Upscale"
            if upscale_folder.exists():
                for img_file in upscale_folder.glob("*.png"):
                    if not img_file.name.startswith("00_"):
                        items.append({
                            "name": img_file.name,
                            "path": img_file,
                            "type": "render"
                        })
                        
            if items:
                structure[category][group_name] = items
                
    return structure

def get_github_image_url(local_path):
    """Convert local path to GitHub raw URL"""
    try:
        rel_path = local_path.relative_to(PROJECT_ROOT)
        # Convert Windows path to URL path
        url_path = str(rel_path).replace('\\', '/')
        return f"{GITHUB_RAW_BASE}/{url_path}?raw=true"
    except:
        return ""

def parse_readme_section(section_name):
    """Extract specific section from README.md"""
    if not README_PATH.exists():
        return ""
        
    with open(README_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Find section by header
    pattern = rf'# {section_name}\n(.*?)(?=\n# |\Z)'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        return match.group(1).strip()
    return ""

def convert_readme_urls_to_github(markdown_text):
    """Convert local file paths in README to GitHub raw URLs"""
    def _is_local_readme_path(path: str) -> bool:
        if not path:
            return False
        p = path.strip()
        if p.startswith('http://') or p.startswith('https://'):
            return False
        # README uses both /ART/... and ART/... (and UI/ENV/Z_Tools)
        p2 = p.lstrip('/')
        return p2.startswith(('ART/', 'UI/', 'ENV/', 'Z_Tools/'))

    def _to_github_raw_url(path: str) -> str:
        p = (path or '').strip().replace('?raw=true', '')
        p2 = p.lstrip('/')
        return f"{GITHUB_RAW_BASE}/{p2}?raw=true"

    # Replace HTML src="..." inside README
    def replace_src(match):
        quote = match.group(1)
        path = match.group(2)
        if not _is_local_readme_path(path):
            return match.group(0)
        return f'src={quote}{_to_github_raw_url(path)}{quote}'

    markdown_text = re.sub(r'src=(["\'])([^"\']+)\1', replace_src, markdown_text)

    # Replace markdown image syntax anywhere in the text:
    # ![alt](/path?raw=true "title") or ![alt](/path)
    def replace_md_image(match):
        alt = match.group(1)
        path = match.group(2)
        title = match.group(3) or ''
        if _is_local_readme_path(path):
            path = _to_github_raw_url(path)
        if title:
            return f'![{alt}]({path} "{title}")'
        return f'![{alt}]({path})'

    markdown_text = re.sub(r'!\[([^\]]*)\]\(([^\s\)]+)(?:\s+"([^"]*)")?\)', replace_md_image, markdown_text)

    return markdown_text

def markdown_to_html(markdown_text):
    """Enhanced markdown to HTML converter with GitHub URL support"""
    # First convert URLs to GitHub format
    html = convert_readme_urls_to_github(markdown_text)
    
    lines = html.split('\n')
    new_lines = []
    in_list = False
    in_table = False
    
    def apply_inline_formatting(text: str) -> str:
        # Links: [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2" target="_parent">\1</a>', text)
        # Bold: **text**
        text = re.sub(r'\*\*([^\*]+)\*\*', r'<strong>\1</strong>', text)
        # Code: `text`
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        return text

    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            if in_list:
                new_lines.append('</ul>')
                in_list = False
            new_lines.append('<br>')
            continue
        
        # Headers: # Header
        if stripped.startswith('#'):
            if in_list:
                new_lines.append('</ul>')
                in_list = False
            level = len(stripped) - len(stripped.lstrip('#'))
            text = stripped.lstrip('#').strip()
            new_lines.append(f'<h{level}>{text}</h{level}>')
            continue
        
        # Tables (simple detection)
        if '|' in stripped and (':---:' in stripped or stripped.startswith('|')):
            if not in_table and ':---:' not in stripped:
                # Table header row
                cells = [c.strip() for c in stripped.split('|') if c.strip()]
                new_lines.append('<table>')
                new_lines.append('<tr>')
                for cell in cells:
                    new_lines.append(f'<th>{cell}</th>')
                new_lines.append('</tr>')
                in_table = True
            elif ':---:' in stripped:
                # Separator row, skip
                continue
            else:
                # Table data row
                cells = [c.strip() for c in stripped.split('|') if c.strip()]
                new_lines.append('<tr>')
                for cell in cells:
                    new_lines.append(f'<td>{cell}</td>')
                new_lines.append('</tr>')
            continue
        else:
            if in_table:
                new_lines.append('</table>')
                in_table = False
        
        # Lists: - item
        if stripped.startswith('- '):
            if not in_list:
                new_lines.append('<ul>')
                in_list = True
            item_text = apply_inline_formatting(stripped[2:])
            new_lines.append(f'<li>{item_text}</li>')
            continue
        else:
            if in_list:
                new_lines.append('</ul>')
                in_list = False
        
        # Images: ![alt](url "title")
        # (Handle leading spaces and optional title; allow query params)
        img_match = re.match(r'!\[([^\]]*)\]\(([^\s\)]+)(?:\s+"([^"]*)")?\)', stripped)
        if img_match:
            alt = img_match.group(1)
            url = img_match.group(2)
            title = img_match.group(3)
            if title:
                new_lines.append(f'<img src="{url}" alt="{alt}" title="{title}" />')
            else:
                new_lines.append(f'<img src="{url}" alt="{alt}" />')
            continue
        
        # HTML tags (pass through)
        if stripped.startswith('<'):
            lower = stripped.lower()
            if lower.startswith('<a ') and '<img' in lower and '</a>' not in lower:
                if re.match(r'^<a\s+[^>]*>\s*<img\s+[^>]*>\s*$', stripped, flags=re.IGNORECASE):
                    new_lines.append(stripped + '</a>')
                else:
                    new_lines.append(stripped)
            else:
                new_lines.append(stripped)
            continue
        
        # Video embeds (GitHub specific)
        if 'github.com/user-attachments/assets/' in stripped:
            new_lines.append(f'<p><em>[Video: {stripped}]</em></p>')
            continue
        
        # Regular paragraph
        text = apply_inline_formatting(stripped)
        new_lines.append(f'<p>{text}</p>')
    
    if in_list:
        new_lines.append('</ul>')
    if in_table:
        new_lines.append('</table>')
    
    return '\n'.join(new_lines)

# ===== HTML GENERATION FUNCTIONS =====

def generate_html_header(title):
    """Generate HTML header with styling"""
    return f"""<!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>{title}</title>
<style type="text/css">
{HTML_STYLE}
</style>
</head>
<body>
"""

def generate_html_footer():
    """Generate HTML footer"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""
<hr style="border-color: #222222; margin-top: 50px;">
<p style="text-align: center; color: #444444; font-size: 0.9em;">
<a href="https://github.com/CorvaeOboro/ultima_online_mods">download source from github</a>
</p>
</body>
</html>
"""

def generate_navigation_menu():
    """Generate navigation menu HTML"""
    return """
<div style="background-color: #0a0a0a; padding: 15px; margin-bottom: 30px; border-radius: 5px;">
    <a href="index.html" style="margin-right: 20px;">HOME</a>
    <a href="ultima_art_mods_art.htm" style="margin-right: 20px;">ART</a>
    <a href="ultima_art_mods_ui.htm" style="margin-right: 20px;">UI</a>
    <a href="ultima_art_mods_env.htm" style="margin-right: 20px;">ENV</a>
    <a href="ultima_art_mods_tools.htm" style="margin-right: 20px;">TOOLS</a>
    <a href="ultima_art_mods_install.htm" style="margin-right: 20px;">INSTALL</a>
</div>
"""

def generate_main_page(structure):
    """Generate main index page"""
    html = generate_html_header("Ultima Online Art Mods")
    html += generate_navigation_menu()
    
    html += """
<h1>ULTIMA ONLINE ART MODS</h1>
<p>Fan art modifications for Ultima Online Classic</p>

<div style="margin: 30px 0;">
    <a href="https://github.com/CorvaeOboro/ultima_online_mods/archive/refs/heads/main.zip" class="download-button">
        DOWNLOAD LATEST
    </a>
    <a href="https://github.com/CorvaeOboro/ultima_online_mods" class="download-button">
        VIEW ON GITHUB
    </a>
</div>

<h2>Featured Mods</h2>
<div class="gallery">
"""
    
    # Add featured images from each category
    featured_items = [
        ("ART/ART_MagicScrolls/item_scroll_00_magic_compB.jpg", "Magic Scrolls"),
        ("UI/UI_MagicSpells/ui_spell_00_comp.jpg", "Magic Spells"),
        ("UI/UI_DarkScrolls/00_dark_scrolls_comp_01.jpg", "Dark UI"),
        ("ENV/ENV_00_AlteredLands.gif", "Altered Lands"),
    ]
    
    for img_path, caption in featured_items:
        full_path = PROJECT_ROOT / img_path
        if full_path.exists():
            url = get_github_image_url(full_path)
            html += f"""
    <div class="gallery-item">
        <img src="{url}" alt="{caption}">
        <p>{caption}</p>
    </div>
"""
    
    html += """
</div>

<h2>Categories</h2>
"""
    
    # List categories with counts
    for category, groups in structure.items():
        group_count = len(groups)
        html += f"""
<div class="category-section">
    <h3><a href="ultima_art_mods_{category.lower()}.htm">{category}</a></h3>
    <p>{group_count} mod groups available</p>
</div>
"""
    
    # Add quick links section
    html += """
<h2>Quick Links</h2>
<ul>
    <li><a href="ultima_art_mods_install.htm">Installation Guide</a></li>
    <li><a href="ultima_art_mods_tools.htm">Modding Tools & Notes</a></li>
    <li><a href="https://github.com/CorvaeOboro/ultima_online_mods/releases">Releases</a></li>
    <li><a href="https://uooutlands.com/wiki/Gump_Overrides">UO Outlands GumpOverrides Guide</a></li>
</ul>

<h2>Thanks</h2>
<ul>
    <li>Varan - <a href="http://varan.uodev.de/">Mulpatcher tools</a></li>
    <li>Polserver - <a href="https://github.com/polserver/UOFiddler">UOFiddler</a></li>
    <li>Gaechti - <a href="http://www.burningsheep.ch/finished.html">Art mods & Guides</a></li>
    <li>ServUO - <a href="https://www.servuo.com/">Resources</a></li>
</ul>

<h2>License</h2>
<p>Free to all, <a href="https://creativecommons.org/publicdomain/zero/1.0/">Creative Commons CC0</a>, 
free to redistribute, attribution not required.</p>
"""
    
    html += generate_html_footer()
    return html

def generate_category_page(category, groups, structure):
    """Generate category-specific page (ART, UI, or ENV)"""
    html = generate_html_header(f"Ultima Online Art Mods - {category}")
    html += generate_navigation_menu()
    
    html += f"<h1>{category} MODS</h1>\n"
    html += f"<p>Art modifications for {category} category</p>\n"
    
    # Generate section for each group
    for group_name, items in sorted(groups.items()):
        html += f'<div class="group-section">\n'
        html += f'<h2>{group_name}</h2>\n'
        
        # Show composite images first
        composites = [item for item in items if item['type'] == 'composite']
        if composites:
            html += '<div class="gallery">\n'
            for item in composites[:3]:  # Limit to first 3 composites
                url = get_github_image_url(item['path'])
                html += f'<div class="gallery-item">\n'
                html += f'<img src="{url}" alt="{item["name"]}">\n'
                html += f'</div>\n'
            html += '</div>\n'
        
        # Count renders
        renders = [item for item in items if item['type'] == 'render']
        if renders:
            html += f'<p>Contains {len(renders)} individual renders</p>\n'
            
        html += '</div>\n'
    
    html += generate_html_footer()
    return html

def generate_tools_page():
    """Generate tools and modding notes page"""
    html = generate_html_header("Ultima Online Art Mods - Tools")
    html += generate_navigation_menu()
    
    html += "<h1>Modding Tools / Notes</h1>\n"
    
    # Parse README sections
    tools_content = parse_readme_section("Modding Tools / Notes")
    modding_notes = parse_readme_section("Modding Notes")
    
    if tools_content:
        html += markdown_to_html(tools_content)
    
    # Add tool screenshots if available
    tool_images = [
        ("Z_Tools/00_mod_selector.png", "Mod Selector"),
        ("Z_Tools/00_psd_to_GumpOverrides.png", "PSD to GumpOverrides"),
    ]
    
    for img_path, caption in tool_images:
        full_path = PROJECT_ROOT / img_path
        if full_path.exists():
            url = get_github_image_url(full_path)
            html += f'<h3>{caption}</h3>\n'
            html += f'<img src="{url}" alt="{caption}">\n'
    
    if modding_notes:
        html += "<h1>Modding Notes</h1>\n"
        html += markdown_to_html(modding_notes)
    
    # Add additional sections from README
    for section in ["MUL", "TOOLS", "ENVIRONMENT TEXTURES", "AUTOPATCH", "NAMING", "HUES", "LINKS"]:
        content = parse_readme_section(section)
        if content:
            html += f"<h1>{section}</h1>\n"
            html += markdown_to_html(content)
    
    html += generate_html_footer()
    return html

def generate_install_page():
    """Generate installation guide page"""
    html = generate_html_header("Ultima Online Art Mods - Installation")
    html += generate_navigation_menu()
    
    html += "<h1>Installation / Patching</h1>\n"
    
    html += """
<h2>UO Outlands (Recommended)</h2>
<div style="background-color: #0a2a1a; padding: 20px; border-left: 4px solid #2a6a4a; margin: 20px 0;">
    <p><strong>Easiest installation method for UO Outlands players:</strong></p>
    <ol>
        <li>Download <a href="https://github.com/CorvaeOboro/ultima_online_mods/releases">GumpOverrides.zip</a></li>
        <li>Extract to your Outlands game directory</li>
        <li>Restart the game</li>
    </ol>
    <p><a href="https://uooutlands.com/wiki/Gump_Overrides" target="_parent">Official Outlands GumpOverrides Guide</a></p>
</div>

<h2>Classic Shards - Using UOFiddler (Recommended)</h2>
<ol>
    <li>Download <a href="https://github.com/CorvaeOboro/ultima_online_mods/archive/refs/heads/main.zip">UO_ART_MODS.zip</a></li>
    <li>Extract to a new folder</li>
    <li><strong>Create a backup of your Ultima Online Client folder</strong></li>
    <li>Download and install <a href="https://github.com/polserver/UOFiddler">UOFiddler</a></li>
    <li>In UOFiddler:
        <ul>
            <li>Settings → Path Settings → Set your Ultima folder path → Click "Reload paths"</li>
            <li>Settings → Options → Output Path → Set to a new OUTPUT folder</li>
            <li>Plugins → Manage → Enable MassImportPlugin (restart if needed)</li>
            <li>Plugins → MassImport → Load XML → Select <code>00_ART_MODS_MassImport.xml</code></li>
            <li>Check "DirectSave" → Click "Start" (may take 1 minute)</li>
        </ul>
    </li>
    <li>If using UOP files (check for artLegacyMUL.uop):
        <ul>
            <li>UOP Packer → Set OUTPUT folder path → Enable "Pack MUL to UOP" → Start</li>
        </ul>
    </li>
    <li>Copy .mul, .idx, and .uop files from OUTPUT folder to your Ultima folder (overwrite)</li>
    <li>Launch Ultima Online and enjoy!</li>
</ol>

<h2>Classic Shards - Using Mulpatcher</h2>
<ol>
    <li>Download <a href="http://varan.uodev.de/">Mulpatcher</a></li>
    <li>Settings → Art → Set mul paths (Art.mul and artidx.mul) → Click LOAD</li>
    <li>Repeat for Gumps and Textures</li>
    <li>Features → Autopatch:
        <ul>
            <li><code>00_ART_ALL_ART_S.txt</code> → Category: Art(S) → START</li>
            <li><code>00_UI_ALL_GUMP.txt</code> → Category: Gumps → START</li>
            <li><code>00_ENV_ALL_TEX.txt</code> → Category: Textures → START</li>
            <li><code>00_ENV_ALL_ART_M.txt</code> → Category: Art(M) → START</li>
            <li><code>00_ENV_ALL_ART_S.txt</code> → Category: Art(S) → START</li>
        </ul>
    </li>
    <li>Settings → Save the Art mul to Ultima directory</li>
    <li>Repeat save for Gumps and Textures</li>
</ol>

<h2>Additional Resources</h2>
<ul>
    <li><a href="http://www.burningsheep.ch/howtoUOP.html">Gaechti's UOP Guide</a></li>
    <li><a href="http://www.burningsheep.ch/finished.html">Gaechti's Finished Mods</a></li>
    <li><a href="https://www.servuo.com/">ServUO Community</a></li>
</ul>


"""
    
    html += generate_html_footer()
    return html

def generate_menu_frame():
    """Generate side menu frame (for frameset layout)"""
    html = """<!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>Menu</title>
<style type="text/css">
body {
    background-color: #0a0a0a;
    font-family: Verdana, Arial, Helvetica, sans-serif;
    color: #666666;
    margin: 0;
    padding: 10px;
}
a {
    display: block;
    color: #5c9ccc;
    text-decoration: none;
    padding: 8px 5px;
    margin: 2px 0;
    border-left: 3px solid transparent;
}
a:hover {
    color: #7cb4e4;
    background-color: #1a1a1a;
    border-left: 3px solid #5c9ccc;
}
</style>
</head>
<body>
<a href="ultima_art_mods_main.htm" target="main_ultima">HOME</a>
<a href="ultima_art_mods_art.htm" target="main_ultima">ART</a>
<a href="ultima_art_mods_ui.htm" target="main_ultima">UI</a>
<a href="ultima_art_mods_env.htm" target="main_ultima">ENV</a>
<a href="ultima_art_mods_tools.htm" target="main_ultima">TOOLS</a>
<a href="ultima_art_mods_install.htm" target="main_ultima">INSTALL</a>
<hr style="border-color: #222222; margin: 20px 0;">
<a href="https://github.com/CorvaeOboro/ultima_online_mods" target="_blank">GITHUB</a>
</body>
</html>
"""
    return html

def generate_index_frameset():
    """Generate index.html with frameset"""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Ultima Online Art Mods</title>
</head>
<frameset cols="10%,90%" framespacing="0" border="0">
    <frame name="side_ultima" src="ultima_art_mods_menu.htm" scrolling="no" />
    <frame name="main_ultima" src="ultima_art_mods_main.htm" />
    <noframes>
        <body>Your browser does not support frames.</body>
    </noframes>
</frameset>
</html>
"""
    return html

# ===== GUI CLASS =====

class HTMLGeneratorGUI:
    """GUI for HTML webpage generator with preview capabilities"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("HTML Webpage Generator - Ultima Online Art Mods")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1a1a1a')
        
        # Data storage
        self.structure = {}
        self.generated_pages = {}
        self.preview_images = {}
        
        # Canvas pan/zoom state
        self.canvas_scale = 0.3  # Default to 30% zoom for better overview
        self.canvas_offset_x = 0
        self.canvas_offset_y = 0
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0
        
        # Image selection and properties
        self.selected_image = None
        self.selected_group = None
        self.image_metadata = {}  # path -> {excluded, priority, type, bbox}
        self.group_metadata = {}  # group_name -> {excluded, priority}
        self.webpage_config_path = PROJECT_ROOT / 'Z_Tools' / '00_project_html_generator.json'
        self.show_excluded = False
        self.use_priority_sort = True  # Sort by priority (on by default)
        self.output_folder = DOCS_DIR  # Default output folder
        self.load_webpage_config()
        
        # Colors
        self.bg_dark = '#1a1a1a'
        self.bg_darker = '#0f0f0f'
        self.bg_lighter = '#2a2a2a'
        self.fg_color = '#cccccc'
        self.accent_color = '#5c9ccc'
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Top control panel
        control_frame = tk.Frame(self.root, bg=self.bg_lighter, padx=10, pady=5)
        control_frame.pack(side=tk.TOP, fill=tk.X)
        
        # Title and instructions
        title_frame = tk.Frame(control_frame, bg=self.bg_lighter)
        title_frame.pack(side=tk.LEFT, padx=10)
        
        title_label = tk.Label(
            title_frame,
            text="HTML WEBPAGE GENERATOR",
            font=("Segoe UI", 16, "bold"),
            bg=self.bg_lighter,
            fg=self.fg_color
        )
        title_label.pack(side=tk.LEFT)
        
        instructions_label = tk.Label(
            title_frame,
            text="  |  Page Previews: Middle Mouse=Pan, Scroll=Zoom, Left Click=Select",
            font=("Segoe UI", 8),
            bg=self.bg_lighter,
            fg='#888888'
        )
        instructions_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Buttons
        btn_frame = tk.Frame(control_frame, bg=self.bg_lighter)
        btn_frame.pack(side=tk.RIGHT, padx=10)
        
        self.scan_btn = tk.Button(
            btn_frame,
            text="[SCAN] Project",
            command=self.scan_project,
            bg=self.accent_color,
            fg='white',
            font=("Segoe UI", 10, "bold"),
            padx=15,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.scan_btn.pack(side=tk.LEFT, padx=5)
        
        self.generate_btn = tk.Button(
            btn_frame,
            text="[GEN] HTML",
            command=self.generate_html,
            bg=self.accent_color,
            fg='white',
            font=("Segoe UI", 10, "bold"),
            padx=15,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2",
            state=tk.DISABLED
        )
        self.generate_btn.pack(side=tk.LEFT, padx=5)
        
        
        self.open_btn = tk.Button(
            btn_frame,
            text="[OPEN] Browser",
            command=self.open_in_browser,
            bg=self.accent_color,
            fg='white',
            font=("Segoe UI", 10, "bold"),
            padx=15,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2",
            state=tk.DISABLED
        )
        self.open_btn.pack(side=tk.LEFT, padx=5)
        
        # Output folder selection row (below title/buttons)
        output_folder_frame = tk.Frame(self.root, bg=self.bg_darker, padx=10, pady=8)
        output_folder_frame.pack(side=tk.TOP, fill=tk.X)
        
        tk.Label(
            output_folder_frame,
            text="Output Folder:",
            font=("Segoe UI", 10, "bold"),
            bg=self.bg_darker,
            fg=self.fg_color
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.output_folder_var = tk.StringVar(value=str(DOCS_DIR))
        output_entry = tk.Entry(
            output_folder_frame,
            textvariable=self.output_folder_var,
            font=("Consolas", 9),
            bg=self.bg_dark,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            width=80
        )
        output_entry.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        
        tk.Button(
            output_folder_frame,
            text="Browse",
            command=self.browse_output_folder,
            bg=self.accent_color,
            fg='white',
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=3,
            relief=tk.FLAT,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        tk.Button(
            output_folder_frame,
            text="Reset",
            command=lambda: self.output_folder_var.set(str(DOCS_DIR)),
            bg=self.bg_lighter,
            fg=self.fg_color,
            font=("Segoe UI", 9),
            padx=10,
            pady=3,
            relief=tk.FLAT,
            cursor="hand2"
        ).pack(side=tk.LEFT)
        
        # Properties and controls row (below output folder)
        props_row = tk.Frame(self.root, bg=self.bg_darker, padx=10, pady=8)
        props_row.pack(side=tk.TOP, fill=tk.X)
        
        # Left section: Refresh button
        left_section = tk.Frame(props_row, bg=self.bg_darker)
        left_section.pack(side=tk.LEFT, padx=(0, 20))
        
        self.refresh_preview_btn = tk.Button(
            left_section,
            text="[REFRESH] Preview",
            command=self.manual_refresh_preview,
            bg=self.accent_color,
            fg='white',
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=3,
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.refresh_preview_btn.pack(side=tk.LEFT)
        
        # Middle section: Selected Image Properties
        middle_section = tk.Frame(props_row, bg=self.bg_darker)
        middle_section.pack(side=tk.LEFT, padx=(0, 20))
        
        # Selection type and name
        tk.Label(
            middle_section,
            text="Selected:",
            font=("Segoe UI", 9, "bold"),
            bg=self.bg_darker,
            fg=self.fg_color
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        self.selection_type_label = tk.Label(
            middle_section,
            text="[None]",
            font=("Consolas", 8, "bold"),
            bg=self.bg_darker,
            fg='#666666'
        )
        self.selection_type_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.selected_img_label = tk.Label(
            middle_section,
            text="No selection",
            font=("Consolas", 8),
            bg=self.bg_darker,
            fg='#aaaaaa',
            width=25,
            anchor='w'
        )
        self.selected_img_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Exclude checkbox
        self.exclude_var = tk.BooleanVar()
        self.exclude_check = tk.Checkbutton(
            middle_section,
            text="Exclude",
            variable=self.exclude_var,
            command=self.toggle_exclude,
            bg=self.bg_darker,
            fg=self.fg_color,
            selectcolor=self.bg_dark,
            activebackground=self.bg_darker,
            activeforeground=self.fg_color,
            font=("Consolas", 8)
        )
        self.exclude_check.pack(side=tk.LEFT, padx=(0, 10))
        
        # Type dropdown
        tk.Label(
            middle_section,
            text="Type:",
            font=("Consolas", 8),
            bg=self.bg_darker,
            fg=self.fg_color
        ).pack(side=tk.LEFT, padx=(0, 3))
        
        self.type_var = tk.StringVar(value="normal")
        self.type_dropdown = ttk.Combobox(
            middle_section,
            textvariable=self.type_var,
            values=["normal", "comparison"],
            width=10,
            font=("Consolas", 8),
            state="disabled"
        )
        self.type_dropdown.pack(side=tk.LEFT, padx=(0, 10))
        self.type_dropdown.bind('<<ComboboxSelected>>', lambda e: self.update_type())
        
        # Priority
        tk.Label(
            middle_section,
            text="Priority:",
            font=("Consolas", 9, "bold"),
            bg=self.bg_darker,
            fg=self.fg_color
        ).pack(side=tk.LEFT, padx=(0, 3))
        
        self.priority_var = tk.StringVar(value="0")
        self.priority_entry = tk.Entry(
            middle_section,
            textvariable=self.priority_var,
            width=5,
            font=("Consolas", 10, "bold"),
            bg=self.bg_dark,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            justify='center'
        )
        self.priority_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.priority_entry.bind('<Return>', lambda e: self.update_priority())
        self.priority_entry.bind('<KeyRelease>', self.on_priority_key_release)
        
        tk.Button(
            middle_section,
            text="Set",
            command=self.update_priority,
            bg=self.accent_color,
            fg='white',
            font=("Consolas", 8),
            padx=8,
            pady=2,
            relief=tk.FLAT,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        # Caption
        tk.Label(
            middle_section,
            text="Caption:",
            font=("Consolas", 9, "bold"),
            bg=self.bg_darker,
            fg=self.fg_color
        ).pack(side=tk.LEFT, padx=(0, 3))
        
        self.caption_var = tk.StringVar(value="")
        self.caption_entry = tk.Entry(
            middle_section,
            textvariable=self.caption_var,
            width=30,
            font=("Consolas", 9),
            bg=self.bg_dark,
            fg=self.fg_color,
            insertbackground=self.fg_color
        )
        self.caption_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.caption_entry.bind('<Return>', lambda e: self.update_caption())
        
        tk.Button(
            middle_section,
            text="Set",
            command=self.update_caption,
            bg=self.accent_color,
            fg='white',
            font=("Consolas", 8),
            padx=8,
            pady=2,
            relief=tk.FLAT,
            cursor="hand2"
        ).pack(side=tk.LEFT)
        
        # Right section: Display options
        right_section = tk.Frame(props_row, bg=self.bg_darker)
        right_section.pack(side=tk.RIGHT)
        
        # Show Info Panel checkbox
        self.show_info_panel_var = tk.BooleanVar(value=False)
        show_info_panel_check = tk.Checkbutton(
            right_section,
            text="Show Info Panel",
            variable=self.show_info_panel_var,
            command=self.toggle_info_panel,
            bg=self.bg_darker,
            fg=self.fg_color,
            selectcolor=self.bg_dark,
            activebackground=self.bg_darker,
            activeforeground=self.fg_color,
            font=("Consolas", 8)
        )
        show_info_panel_check.pack(side=tk.LEFT, padx=(0, 10))
        
        # Show Log Panel checkbox
        self.show_log_panel_var = tk.BooleanVar(value=False)
        show_log_panel_check = tk.Checkbutton(
            right_section,
            text="Show Log Panel",
            variable=self.show_log_panel_var,
            command=self.toggle_log_panel,
            bg=self.bg_darker,
            fg=self.fg_color,
            selectcolor=self.bg_dark,
            activebackground=self.bg_darker,
            activeforeground=self.fg_color,
            font=("Consolas", 8)
        )
        show_log_panel_check.pack(side=tk.LEFT, padx=(0, 10))
        
        self.use_priority_var = tk.BooleanVar(value=True)
        priority_sort_check = tk.Checkbutton(
            right_section,
            text="Sort by Priority",
            variable=self.use_priority_var,
            command=self.toggle_priority_sort,
            bg=self.bg_darker,
            fg=self.fg_color,
            selectcolor=self.bg_dark,
            activebackground=self.bg_darker,
            activeforeground=self.fg_color,
            font=("Consolas", 8)
        )
        priority_sort_check.pack(side=tk.LEFT, padx=(0, 10))
        
        self.show_excluded_var = tk.BooleanVar(value=False)
        show_excluded_check = tk.Checkbutton(
            right_section,
            text="Show Excluded",
            variable=self.show_excluded_var,
            command=self.toggle_show_excluded,
            bg=self.bg_darker,
            fg=self.fg_color,
            selectcolor=self.bg_dark,
            activebackground=self.bg_darker,
            activeforeground=self.fg_color,
            font=("Consolas", 8)
        )
        show_excluded_check.pack(side=tk.LEFT)
        
        # Main content area - full width canvas
        left_frame = tk.Frame(self.root, bg=self.bg_dark)
        left_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Canvas for previews
        self.preview_canvas = tk.Canvas(
            left_frame,
            bg='#2a2a2a',
            highlightthickness=0,
            cursor="crosshair"
        )
        self.preview_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        # Store log and info messages in memory (for canvas rendering)
        self.info_messages = []
        self.log_messages = []
        
        # Bind mouse events for pan, zoom, and selection
        self.preview_canvas.bind("<ButtonPress-1>", self.on_canvas_click)  # Left click to select
        self.preview_canvas.bind("<ButtonPress-2>", self.start_pan)  # Middle mouse button
        self.preview_canvas.bind("<B2-Motion>", self.do_pan)
        self.preview_canvas.bind("<ButtonRelease-2>", self.end_pan)
        self.preview_canvas.bind("<MouseWheel>", self.zoom_canvas)
        
        # Initial message
        self.log("Initializing...")
        self.add_info("Scanning project on startup...")
        
        # Auto-scan on startup
        self.root.after(100, self.scan_project)
        
    def log(self, message):
        """Add message to log (stored in memory for canvas rendering or printed to console)"""
        # If log panel is off, print to console instead
        if not self.show_log_panel_var.get():
            print(f"[LOG] {message}")
        else:
            self.log_messages.append(message)
            # Keep only last 100 messages to avoid memory bloat
            if len(self.log_messages) > 100:
                self.log_messages = self.log_messages[-100:]
        self.root.update_idletasks()
    
    def add_info(self, message):
        """Add message to info (stored in memory for canvas rendering or printed to console)"""
        # If info panel is off, print to console instead
        if not self.show_info_panel_var.get():
            print(f"[INFO] {message}")
        else:
            self.info_messages.append(message)
            # Keep only last 50 messages
            if len(self.info_messages) > 50:
                self.info_messages = self.info_messages[-50:]
    
    def toggle_info_panel(self):
        """Toggle info panel visibility and refresh preview"""
        # When turning on, we need to rebuild info messages from current state
        if self.show_info_panel_var.get():
            print("[INFO PANEL] Enabled - info will appear on canvas")
        else:
            print("[INFO PANEL] Disabled - info will print to console")
            self.info_messages.clear()
        # Refresh preview to show/hide panel
        if hasattr(self, 'page_layouts') and self.page_layouts:
            self.preview_pages()
    
    def toggle_log_panel(self):
        """Toggle log panel visibility and refresh preview"""
        if self.show_log_panel_var.get():
            print("[LOG PANEL] Enabled - logs will appear on canvas")
        else:
            print("[LOG PANEL] Disabled - logs will print to console")
            self.log_messages.clear()
        # Refresh preview to show/hide panel
        if hasattr(self, 'page_layouts') and self.page_layouts:
            self.preview_pages()
        
    def scan_project(self):
        """Scan project structure and build page layouts"""
        self.log("=" * 50)
        self.log("PHASE 1: SCANNING PROJECT & BUILDING LAYOUTS")
        self.log("=" * 50)
        self.info_messages.clear()
        
        try:
            # Ensure output directory exists
            self.log("> Checking docs directory...")
            ensure_docs_dir()
            self.log(f"  [OK] Docs dir: {DOCS_DIR}")
            
            # Scan project structure
            self.log("\n> Scanning project folders...")
            self.log(f"  - Project root: {PROJECT_ROOT}")
            self.log(f"  - Looking for: ART/, UI/, ENV/")
            
            self.structure = scan_project_structure()
            
            # Display results with detailed breakdown
            total_groups = sum(len(groups) for groups in self.structure.values())
            total_composites = 0
            total_renders = 0
            
            self.log(f"\n[OK] SCAN COMPLETE")
            self.log(f"  - Categories found: {len(self.structure)}")
            self.log(f"  - Total groups: {total_groups}")
            
            info = "PROJECT STRUCTURE\n" + "=" * 50 + "\n\n"
            
            for category, groups in sorted(self.structure.items()):
                cat_composites = sum(len([i for i in items if i['type'] == 'composite']) for items in groups.values())
                cat_renders = sum(len([i for i in items if i['type'] == 'render']) for items in groups.values())
                total_composites += cat_composites
                total_renders += cat_renders
                
                self.log(f"\n> {category}/")
                self.log(f"  - Groups: {len(groups)}")
                self.log(f"  - Composites: {cat_composites}")
                self.log(f"  - Renders: {cat_renders}")
                
                info += f"{category}/ ({len(groups)} groups, {cat_composites} comp, {cat_renders} renders)\n"
                
                for group_name, items in sorted(groups.items()):
                    composites = len([i for i in items if i['type'] == 'composite'])
                    renders = len([i for i in items if i['type'] == 'render'])
                    info += f"  └─ {group_name}: {composites} comp, {renders} renders\n"
                info += "\n"
            
            self.log(f"\nTOTALS:")
            self.log(f"  - Total composites: {total_composites}")
            self.log(f"  - Total renders: {total_renders}")
            self.log(f"  - Total items: {total_composites + total_renders}")
            
            # Store info for canvas rendering
            self.info_messages.clear()
            for line in info.split('\n'):
                if line.strip():
                    self.add_info(line)
            
            # BUILD PAGE LAYOUTS (Single Source of Truth)
            self.log("\n> Building page layouts...")
            self.page_layouts = {}
            
            # Main page
            self.log("  - Main page layout")
            main_layout = build_main_page_layout(self.structure)
            self.page_layouts['main'] = main_layout
            
            # Category pages
            for category, groups in sorted(self.structure.items()):
                self.log(f"  - {category} page layout")
                cat_layout = build_category_page_layout(
                    category, groups, self.structure,
                    group_metadata=self.group_metadata,
                    image_metadata=self.image_metadata
                )
                self.page_layouts[category.lower()] = cat_layout
            
            # Tools page
            self.log("  - Tools page layout")
            tools_layout = build_tools_page_layout()
            self.page_layouts['tools'] = tools_layout
            
            # Install page
            self.log("  - Install page layout")
            install_layout = build_install_page_layout()
            self.page_layouts['install'] = install_layout
            
            self.log(f"  [OK] Built {len(self.page_layouts)} page layouts")
            self.log("\n" + "=" * 50)
            
            # Enable generate button
            self.generate_btn.config(state=tk.NORMAL)
            
            #  trigger preview
            self.root.after(100, self.preview_pages)
            
        except Exception as e:
            import traceback
            self.log(f"[ERROR] Error during scan: {e}")
            self.log(f"   Traceback: {traceback.format_exc()}")
            messagebox.showerror("Scan Error", f"Failed to scan project:\n{e}")
            
    def browse_output_folder(self):
        """Open folder browser dialog to select output directory"""
        from tkinter import filedialog
        folder = filedialog.askdirectory(
            title="Select Output Folder for Generated HTML",
            initialdir=str(DOCS_DIR)
        )
        if folder:
            self.output_folder_var.set(folder)
            self.log(f"[OUTPUT] Output folder set to: {folder}")
    
    def generate_html(self):
        """Generate HTML files from existing page layouts"""
        if not hasattr(self, 'page_layouts') or not self.page_layouts:
            messagebox.showwarning("No Layouts", "Scan project first to build page layouts!")
            return
            
        self.log("=" * 50)
        self.log("PHASE 2: RENDERING HTML FILES")
        self.log("=" * 50)
        
        try:
            self.generated_pages = {}
            
            # Get output folder from UI
            output_dir = Path(self.output_folder_var.get())
            self.log(f"\n> Output directory: {output_dir}")
            
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            self.log(f"  [OK] Output directory ready")
            
            # Reload config to ensure we have latest priority settings
            self.log("\n> Reloading configuration...")
            self.load_webpage_config()
            
            # Rebuild category layouts with current priority settings
            self.log("\n> Rebuilding category layouts with current priorities...")
            self.log(f"  - Loaded {len(self.image_metadata)} image priorities")
            self.log(f"  - Loaded {len(self.group_metadata)} group priorities")
            for category, groups in sorted(self.structure.items()):
                self.log(f"  - Rebuilding {category} page layout")
                cat_layout = build_category_page_layout(
                    category, groups, self.structure,
                    group_metadata=self.group_metadata,
                    image_metadata=self.image_metadata
                )
                self.page_layouts[category.lower()] = cat_layout
            
            # Render layouts to HTML
            self.log("\n> Rendering layouts to HTML files...")
            self.log(f"  - Using {len(self.page_layouts)} layouts")
            
            for page_name, layout in self.page_layouts.items():
                self.log(f"  - Rendering {page_name}")
                html = render_layout_to_html(
                    layout, 
                    image_metadata=self.image_metadata,
                    group_metadata=self.group_metadata,
                    show_excluded=False  # Don't show excluded items in generated HTML
                )
                filename = f"ultima_art_mods_{page_name}.htm"
                with open(output_dir / filename, 'w', encoding='utf-8') as f:
                    f.write(html)
                self.generated_pages[page_name] = html
                self.log(f"    [OK] {len(html)} chars, {len(layout.sections)} sections")
            
            # Generate frameset and menu (these don't use layouts)
            self.log("\n> Generating frameset and menu...")
            html = generate_index_frameset()
            with open(output_dir / "index.html", 'w', encoding='utf-8') as f:
                f.write(html)
            self.generated_pages['index'] = html
            
            html = generate_menu_frame()
            with open(output_dir / "ultima_art_mods_menu.htm", 'w', encoding='utf-8') as f:
                f.write(html)
            self.generated_pages['menu'] = html
            
            self.log(f"\n[OK] GENERATION COMPLETE")
            self.log(f"  - Pages generated: {len(self.generated_pages)}")
            self.log(f"  - Layouts created: {len(self.page_layouts)}")
            self.log(f"  - Output directory: {output_dir}")
            self.log("=" * 50)
            
            # Enable open button
            self.open_btn.config(state=tk.NORMAL)
            
            messagebox.showinfo("Success", f"Generated {len(self.generated_pages)} HTML files successfully!")
            
        except Exception as e:
            import traceback
            self.log(f"[ERROR] Error during generation: {e}")
            self.log(f"   Traceback: {traceback.format_exc()}")
            messagebox.showerror("Generation Error", f"Failed to generate HTML:\n{e}")
            
    def preview_pages(self):
        """Generate and display page previews as a single composite image"""
        if not hasattr(self, 'page_layouts') or not self.page_layouts:
            self.log("[WARN] No layouts available yet")
            return
            
        if not Image or not ImageTk:
            self.log("[ERROR] Pillow (PIL) required for previews - install with: pip install Pillow")
            return
            
        self.log("=" * 50)
        self.log("PHASE 3: RENDERING PAGE PREVIEWS (Layout-Based)")
        self.log("=" * 50)
        
        # Reload config to ensure we have latest settings
        self.load_webpage_config()
        
        try:
            # Clear canvas
            self.log("\n> Clearing canvas...")
            self.preview_canvas.delete("all")
            
            # Preserve zoom/pan state (don't reset on refresh)
            # Save current scroll position
            saved_scale = getattr(self, 'canvas_scale', 1.0)
            saved_xview = None
            saved_yview = None
            if hasattr(self, 'composite_image'):
                # Save current scroll position as fraction
                saved_xview = self.preview_canvas.xview()
                saved_yview = self.preview_canvas.yview()
            
            # Only reset if this is the first preview generation
            if not hasattr(self, 'canvas_scale') or not hasattr(self, 'composite_image'):
                self.canvas_scale = 0.3  # Default to 30% zoom for better overview
                self.canvas_offset_x = 0
                self.canvas_offset_y = 0
            else:
                # Keep existing scale
                self.canvas_scale = saved_scale
            
            # Preview dimensions (natural size - no forced height)
            max_page_width = 1200  # Maximum width per page (increased for better visibility)
            page_spacing = 80  # Horizontal spacing between pages to show canvas background
            side_padding = 40  # Padding on left/right edges
            label_height = 35
            footer_buffer = 50  # Extra space at bottom of each page
            
            # Render info and log panels if enabled
            panel_width = 280
            info_panel_img = None
            log_panel_img = None
            show_info = self.show_info_panel_var.get()
            show_log = self.show_log_panel_var.get()
            
            if show_info or show_log:
                self.log(f"\n> Rendering enabled panels...")
                if show_info:
                    info_panel_img = render_info_panel_to_canvas(self.info_messages, width=panel_width)
                    self.log(f"  - Info panel: {info_panel_img.width}x{info_panel_img.height}")
                if show_log:
                    log_panel_img = render_log_panel_to_canvas(self.log_messages, width=panel_width)
                    self.log(f"  - Log panel: {log_panel_img.width}x{log_panel_img.height}")
            
            # First pass: render all pages to get their natural heights and widths
            self.log(f"\n> Rendering pages at natural size...")
            page_images = {}
            page_bboxes = {}
            page_widths = {}  # Store actual width for each page
            max_height = 0
            
            for page_name, layout in self.page_layouts.items():
                self.log(f"  - Rendering {page_name}")
                page_img, img_bboxes, grp_bboxes = render_layout_to_canvas(
                    layout, 
                    self.preview_canvas, 
                    0, 0, 
                    max_page_width,
                    image_metadata=self.image_metadata,
                    group_metadata=self.group_metadata,
                    show_excluded=self.show_excluded,
                    use_priority_sort=self.use_priority_sort
                )
                # Add footer buffer to page height
                page_with_footer = Image.new('RGBA', (page_img.width, page_img.height + footer_buffer), color=(0, 0, 0, 0))
                page_with_footer.paste(page_img, (0, 0))
                
                page_images[page_name] = page_with_footer
                page_bboxes[page_name] = (img_bboxes, grp_bboxes)
                page_widths[page_name] = page_with_footer.width
                max_height = max(max_height, page_with_footer.height)
                self.log(f"    Natural size: {page_with_footer.width}x{page_with_footer.height}")
            
            # Calculate composite image size (HORIZONTAL LAYOUT - single row)
            # Include enabled panels to the left of main page
            num_pages = len(self.page_layouts)
            
            # Calculate panels width based on which panels are enabled
            panels_width = 0
            panels_height = 0
            
            if show_info and show_log:
                # Both panels: side by side
                panels_width = panel_width * 2 + page_spacing
                panels_height = max(info_panel_img.height, log_panel_img.height)
            elif show_info:
                # Only info panel
                panels_width = panel_width
                panels_height = info_panel_img.height
            elif show_log:
                # Only log panel
                panels_width = panel_width
                panels_height = log_panel_img.height
            
            # Calculate total width
            total_pages_width = sum(page_widths.values())
            if panels_width > 0:
                composite_width = panels_width + page_spacing + total_pages_width + (page_spacing * (num_pages - 1)) + (side_padding * 2)
            else:
                # No panels, just pages
                composite_width = total_pages_width + (page_spacing * (num_pages - 1)) + (side_padding * 2)
            
            # Height is max of panels and pages
            composite_height = max(max_height + label_height, panels_height) + side_padding * 2
            
            self.log(f"\n> Creating composite: {composite_width}x{composite_height}")
            self.log(f"  - Pages: {num_pages} (horizontal layout)")
            self.log(f"  - Max page height: {max_height}")
            self.log(f"  - Page spacing: {page_spacing}px (shows canvas background)")
            
            # Create composite image with TRANSPARENT background so canvas bg shows through
            composite_img = Image.new('RGBA', (composite_width, composite_height), color=(0, 0, 0, 0))
            
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(composite_img)
            
            # Try to load font for labels
            try:
                label_font = ImageFont.truetype("segoeui.ttf", 12)
            except:
                label_font = ImageFont.load_default()
            
            previews_created = 0
            
            # Store image and group metadata for click detection
            self.image_metadata_canvas = {}
            self.group_metadata_canvas = {}
            
            # Paste enabled panels first (to the left)
            if show_info or show_log:
                self.log(f"\n> Compositing enabled panels...")
                panel_x = side_padding
                panel_y = side_padding
                
                if show_info and show_log:
                    # Both panels side by side
                    composite_img.paste(info_panel_img, (panel_x, panel_y))
                    self.log(f"  - Info panel at ({panel_x}, {panel_y})")
                    
                    log_x = panel_x + panel_width + page_spacing
                    composite_img.paste(log_panel_img, (log_x, panel_y))
                    self.log(f"  - Log panel at ({log_x}, {panel_y})")
                elif show_info:
                    # Only info panel
                    composite_img.paste(info_panel_img, (panel_x, panel_y))
                    self.log(f"  - Info panel at ({panel_x}, {panel_y})")
                elif show_log:
                    # Only log panel
                    composite_img.paste(log_panel_img, (panel_x, panel_y))
                    self.log(f"  - Log panel at ({panel_x}, {panel_y})")
            
            # Paste pre-rendered pages onto composite (HORIZONTAL - single row)
            # Start pages after the panels (if any)
            self.log(f"\n> Compositing pages...")
            if panels_width > 0:
                x_pos = side_padding + panels_width + page_spacing  # Start after panels
            else:
                x_pos = side_padding  # No panels, start at left edge
            y_pos = side_padding
            
            for page_name, page_img in page_images.items():
                page_width = page_widths[page_name]
                
                # Draw label at TOP of page
                label_x = x_pos + page_width // 2
                label_y = y_pos + 10
                
                # Draw label background
                text_bbox = draw.textbbox((label_x, label_y), page_name.upper(), font=label_font, anchor='mm')
                draw.rectangle(
                    [(text_bbox[0]-5, text_bbox[1]-2), (text_bbox[2]+5, text_bbox[3]+2)],
                    fill='#1a1a1a'
                )
                
                # Draw label text
                draw.text(
                    (label_x, label_y),
                    page_name.upper(),
                    fill='#cccccc',
                    font=label_font,
                    anchor='mm'
                )
                
                # Paste page below label (offset by label height)
                page_y = y_pos + label_height
                # Use alpha composite to preserve transparency
                if page_img.mode == 'RGBA':
                    composite_img.paste(page_img, (x_pos, page_y), page_img)
                else:
                    composite_img.paste(page_img, (x_pos, page_y))
                
                # Get bboxes for this page
                img_bboxes, grp_bboxes = page_bboxes[page_name]
                
                # Translate image bboxes to composite coordinates (account for label offset)
                for img_path, (bx1, by1, bx2, by2) in img_bboxes.items():
                    global_bbox = (bx1 + x_pos, by1 + page_y, bx2 + x_pos, by2 + page_y)
                    self.image_metadata_canvas[img_path] = {
                        'bbox': global_bbox,
                        'page': page_name
                    }
                    # Debug: log first few bboxes
                    if len(self.image_metadata_canvas) <= 3:
                        img_name = Path(img_path).name
                        self.log(f"    [BBOX] {img_name}: local({bx1},{by1},{bx2},{by2}) + offset({x_pos},{page_y}) = global{global_bbox}")
                
                # Translate group bboxes to composite coordinates (account for label offset)
                for group_name, (bx1, by1, bx2, by2) in grp_bboxes.items():
                    global_bbox = (bx1 + x_pos, by1 + page_y, bx2 + x_pos, by2 + page_y)
                    self.group_metadata_canvas[group_name] = {
                        'bbox': global_bbox,
                        'page': page_name
                    }
                
                self.log(f"  - {page_name}: {page_img.width}x{page_img.height} at ({x_pos}, {page_y})")
                previews_created += 1
                
                # Move to next position (HORIZONTAL) - add page width + spacing
                x_pos += page_width + page_spacing
            
            # Convert composite to PhotoImage and display
            self.log(f"\n> Creating PhotoImage from composite...")
            self.composite_image = composite_img  # Keep PIL RGBA image for zooming
            
            # Convert RGBA to RGB with canvas background color for display
            # This allows the canvas background to show through transparent areas
            canvas_bg_color = (42, 42, 42)  # #2a2a2a
            composite_rgb = Image.new('RGB', composite_img.size, canvas_bg_color)
            composite_rgb.paste(composite_img, (0, 0), composite_img if composite_img.mode == 'RGBA' else None)
            
            # Apply zoom if needed
            if self.canvas_scale != 1.0:
                scaled_width = int(composite_width * self.canvas_scale)
                scaled_height = int(composite_height * self.canvas_scale)
                resized_img = composite_rgb.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
                self.composite_photo = ImageTk.PhotoImage(resized_img)
                display_width, display_height = scaled_width, scaled_height
            else:
                self.composite_photo = ImageTk.PhotoImage(composite_rgb)
                display_width, display_height = composite_width, composite_height
            
            # Display on canvas at pan offset position
            self.preview_canvas.create_image(
                self.canvas_offset_x, self.canvas_offset_y,
                image=self.composite_photo,
                anchor='nw',
                tags='composite'
            )
            
            # No scrollregion needed - we use pure pan navigation
            # Store the original image dimensions for reference
            self.original_composite_width = composite_width
            self.original_composite_height = composite_height
            
            self.log(f"\n[OK] PREVIEW RENDERING COMPLETE")
            self.log(f"  - Previews created: {previews_created}")
            self.log(f"  - Composite size: {composite_width}x{composite_height}")
            self.log(f"  - Clickable images: {len(self.image_metadata_canvas)}")
            self.log(f"  - Clickable groups: {len(self.group_metadata_canvas)}")
            self.log("=" * 50)
            
        except Exception as e:
            import traceback
            self.log(f"[ERROR] Error rendering previews: {e}")
            self.log(f"   Traceback: {traceback.format_exc()}")
            messagebox.showerror("Preview Error", f"Failed to render previews:\n{e}")
        
    def start_pan(self, event):
        """Start panning the canvas"""
        self.is_panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.preview_canvas.config(cursor="fleur")
        
    def do_pan(self, event):
        """Pan the canvas"""
        if self.is_panning:
            dx = event.x - self.pan_start_x
            dy = event.y - self.pan_start_y
            
            # Update pan offsets
            self.canvas_offset_x += dx
            self.canvas_offset_y += dy
            
            # Move all canvas items
            self.preview_canvas.move("all", dx, dy)
            
            self.pan_start_x = event.x
            self.pan_start_y = event.y
            
    def end_pan(self, event):
        """End panning"""
        self.is_panning = False
        self.preview_canvas.config(cursor="crosshair")
        
    def zoom_canvas(self, event):
        """Zoom the composite image with mouse wheel, centered on cursor"""
        if not hasattr(self, 'composite_image'):
            return
            
        # Get mouse position relative to current image position
        # This is the point in the IMAGE that's under the cursor
        image_x = (event.x - self.canvas_offset_x) / self.canvas_scale
        image_y = (event.y - self.canvas_offset_y) / self.canvas_scale
        
        # Zoom factor
        if event.delta > 0:
            factor = 1.1
        else:
            factor = 0.9
        
        # Calculate new scale
        old_scale = self.canvas_scale
        new_scale = old_scale * factor
        
        # Limit zoom range
        if 0.1 <= new_scale <= 5.0:
            self.canvas_scale = new_scale
            
            # Resize the composite image (use RGB version for display)
            original_width, original_height = self.composite_image.size
            new_width = int(original_width * self.canvas_scale)
            new_height = int(original_height * self.canvas_scale)
            
            # Convert RGBA to RGB with canvas background for zoomed display
            canvas_bg_color = (42, 42, 42)  # #2a2a2a
            composite_rgb = Image.new('RGB', self.composite_image.size, canvas_bg_color)
            composite_rgb.paste(self.composite_image, (0, 0), self.composite_image if self.composite_image.mode == 'RGBA' else None)
            
            # Resize using high-quality resampling
            resized_img = composite_rgb.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Update PhotoImage
            self.composite_photo = ImageTk.PhotoImage(resized_img)
            
            # Calculate new offset to keep the same point under the cursor
            # After zoom, the image point is at: image_x * new_scale, image_y * new_scale
            # We want this to be at event.x, event.y on screen
            # So: event.x = canvas_offset_x + image_x * new_scale
            # Therefore: canvas_offset_x = event.x - image_x * new_scale
            self.canvas_offset_x = event.x - image_x * new_scale
            self.canvas_offset_y = event.y - image_y * new_scale
            
            # Update canvas image at new position
            self.preview_canvas.delete('composite')
            self.preview_canvas.create_image(
                self.canvas_offset_x, self.canvas_offset_y,
                image=self.composite_photo,
                anchor='nw',
                tags='composite'
            )
            
            # Update highlight if something is selected
            if self.selected_image and hasattr(self, 'image_metadata_canvas'):
                if self.selected_image in self.image_metadata_canvas:
                    bbox = self.image_metadata_canvas[self.selected_image].get('bbox')
                    if bbox:
                        self.highlight_selected_image(bbox)
            elif self.selected_group and hasattr(self, 'group_metadata_canvas'):
                if self.selected_group in self.group_metadata_canvas:
                    bbox = self.group_metadata_canvas[self.selected_group].get('bbox')
                    if bbox:
                        self.highlight_selected_image(bbox)
            
    def load_webpage_config(self):
        """Load webpage configuration from JSON"""
        if self.webpage_config_path.exists():
            try:
                with open(self.webpage_config_path, 'r') as f:
                    config = json.load(f)
                    self.image_metadata = config.get('images', {})
                    self.group_metadata = config.get('groups', {})
                    if hasattr(self, 'log_text'):
                        self.log(f"[CONFIG] Loaded {len(self.image_metadata)} images, {len(self.group_metadata)} groups")
                    else:
                        print(f"[CONFIG] Loaded {len(self.image_metadata)} images, {len(self.group_metadata)} groups")
            except Exception as e:
                if hasattr(self, 'log_text'):
                    self.log(f"[CONFIG] Error loading: {e}")
                else:
                    print(f"[CONFIG] Error loading: {e}")
                self.image_metadata = {}
                self.group_metadata = {}
        else:
            self.image_metadata = {}
            self.group_metadata = {}
    
    def save_webpage_config(self):
        """Save webpage configuration to JSON"""
        try:
            config = {
                'images': self.image_metadata,
                'groups': self.group_metadata
            }
            with open(self.webpage_config_path, 'w') as f:
                json.dump(config, f, indent=2)
            self.log(f"[CONFIG] Saved to 00_project_html_generator.json")
        except Exception as e:
            self.log(f"[CONFIG] Error saving: {e}")
    
    def on_canvas_click(self, event):
        """Handle canvas click to select images or groups"""
        if not hasattr(self, 'image_metadata_canvas'):
            return
        
        # Convert screen coords to image coords
        # Screen coords are event.x, event.y
        # Image is displayed at canvas_offset_x, canvas_offset_y with scale canvas_scale
        # Point in scaled image space: event.x - canvas_offset_x, event.y - canvas_offset_y
        # Point in original image space: (event.x - canvas_offset_x) / canvas_scale
        img_x = (event.x - self.canvas_offset_x) / self.canvas_scale
        img_y = (event.y - self.canvas_offset_y) / self.canvas_scale
        
        # Debug logging
        self.log(f"[CLICK] Screen: ({event.x}, {event.y}) → Offset: ({self.canvas_offset_x:.1f}, {self.canvas_offset_y:.1f}) → Image: ({img_x:.1f}, {img_y:.1f}) [Scale: {self.canvas_scale:.2f}]")
        
        # Check for group header click first
        if hasattr(self, 'group_metadata_canvas'):
            for group_name, meta in self.group_metadata_canvas.items():
                bbox = meta.get('bbox')
                if bbox:
                    x1, y1, x2, y2 = bbox
                    if x1 <= img_x <= x2 and y1 <= img_y <= y2:
                        self.log(f"[MATCH] Group '{group_name}' bbox: ({x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f})")
                        self.select_group(group_name, meta)
                        return
        
        # Find clicked image
        for img_path, meta in self.image_metadata_canvas.items():
            bbox = meta.get('bbox')
            if bbox:
                x1, y1, x2, y2 = bbox
                if x1 <= img_x <= x2 and y1 <= img_y <= y2:
                    img_name = Path(img_path).name
                    self.log(f"[MATCH] Image '{img_name}' bbox: ({x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f})")
                    self.select_image(img_path, meta)
                    return
        
        # Clicked empty space - deselect
        self.log(f"[CLICK] No match found")
        self.deselect_selection()
    
    def select_image(self, img_path, meta):
        """Select an image and show its properties"""
        self.selected_image = img_path
        self.selected_group = None
        
        # Get or create metadata
        if img_path not in self.image_metadata:
            self.image_metadata[img_path] = {
                'excluded': False,
                'priority': 0,
                'type': 'normal',
                'caption': ''
            }
        
        img_meta = self.image_metadata[img_path]
        
        # Update UI
        self.selection_type_label.config(text="[Image]", fg='#5c9ccc')
        img_name = Path(img_path).name
        self.selected_img_label.config(text=img_name, fg='#ffffff')
        self.exclude_var.set(img_meta.get('excluded', False))
        self.priority_var.set(str(img_meta.get('priority', 0)))
        self.type_var.set(img_meta.get('type', 'normal'))
        self.caption_var.set(img_meta.get('caption', ''))
        
        # Enable type dropdown for images
        self.type_dropdown.config(state="readonly")
        
        # Highlight on canvas
        self.highlight_selected_image(meta.get('bbox'))
        
        self.log(f"[SELECT IMAGE] {img_name}")
    
    def select_group(self, group_name, meta):
        """Select a group and show its properties"""
        self.selected_group = group_name
        self.selected_image = None
        
        # Get or create metadata
        if group_name not in self.group_metadata:
            self.group_metadata[group_name] = {
                'excluded': False,
                'priority': 0
            }
        
        group_meta = self.group_metadata[group_name]
        
        # Update UI
        self.selection_type_label.config(text="[Group]", fg='#cc9c5c')
        self.selected_img_label.config(text=group_name, fg='#ffffff')
        self.exclude_var.set(group_meta.get('excluded', False))
        self.priority_var.set(str(group_meta.get('priority', 0)))
        self.type_var.set('normal')  # Groups don't have type
        
        # Disable type dropdown for groups
        self.type_dropdown.config(state="disabled")
        
        # Highlight on canvas
        self.highlight_selected_image(meta.get('bbox'))
        
        self.log(f"[SELECT GROUP] {group_name}")
    
    def deselect_selection(self):
        """Deselect current image or group"""
        self.selected_image = None
        self.selected_group = None
        self.selection_type_label.config(text="[None]", fg='#666666')
        self.selected_img_label.config(text="No selection", fg='#aaaaaa')
        self.exclude_var.set(False)
        self.priority_var.set("0")
        self.type_var.set("normal")
        self.caption_var.set("")
        self.type_dropdown.config(state="disabled")
        
        # Remove highlight
        self.preview_canvas.delete('selection_highlight')
    
    def highlight_selected_image(self, bbox):
        """Draw highlight around selected image"""
        if not bbox:
            return
        
        # Remove old highlight
        self.preview_canvas.delete('selection_highlight')
        
        # Draw new highlight (scaled and offset)
        # bbox is in original image coordinates
        # Convert to screen coordinates: screen = offset + (image * scale)
        x1, y1, x2, y2 = bbox
        x1_screen = self.canvas_offset_x + x1 * self.canvas_scale
        y1_screen = self.canvas_offset_y + y1 * self.canvas_scale
        x2_screen = self.canvas_offset_x + x2 * self.canvas_scale
        y2_screen = self.canvas_offset_y + y2 * self.canvas_scale
        
        self.preview_canvas.create_rectangle(
            x1_screen, y1_screen, x2_screen, y2_screen,
            outline='#5c9ccc',
            width=3,
            tags='selection_highlight'
        )
    
    def toggle_exclude(self):
        """Toggle exclude status for selected image or group"""
        excluded = self.exclude_var.get()
        
        if self.selected_image:
            self.image_metadata[self.selected_image]['excluded'] = excluded
            self.save_webpage_config()
            
            status = "EXCLUDED" if excluded else "INCLUDED"
            img_name = Path(self.selected_image).name
            self.log(f"[EXCLUDE IMAGE] {img_name} -> {status}")
        elif self.selected_group:
            self.group_metadata[self.selected_group]['excluded'] = excluded
            self.save_webpage_config()
            
            status = "EXCLUDED" if excluded else "INCLUDED"
            self.log(f"[EXCLUDE GROUP] {self.selected_group} -> {status} (refresh to apply)")
        else:
            return
        
        # No auto-refresh - user must click refresh button
    
    def on_priority_key_release(self, event):
        """Auto-update priority when user types a valid number"""
        # Only auto-update if the value is a valid integer
        try:
            value = self.priority_var.get().strip()
            if value and value.isdigit():
                # Valid number typed, auto-update after a short delay
                # Cancel any pending auto-update
                if hasattr(self, '_priority_update_timer'):
                    self.root.after_cancel(self._priority_update_timer)
                # Schedule update after 500ms of no typing
                self._priority_update_timer = self.root.after(500, self.update_priority)
        except:
            pass
    
    def update_priority(self):
        """Update sort priority for selected image or group (no auto-refresh)"""
        try:
            priority = int(self.priority_var.get())
            
            if self.selected_image:
                self.image_metadata[self.selected_image]['priority'] = priority
                self.save_webpage_config()
                
                img_name = Path(self.selected_image).name
                self.log(f"[PRIORITY IMAGE] {img_name} -> {priority} (refresh to apply)")
            elif self.selected_group:
                self.group_metadata[self.selected_group]['priority'] = priority
                self.save_webpage_config()
                
                self.log(f"[PRIORITY GROUP] {self.selected_group} -> {priority} (refresh to apply)")
            else:
                return
            
            # No auto-refresh - user must click refresh button
        except ValueError:
            self.log(f"[ERROR] Invalid priority value")
    
    def update_type(self):
        """Update image type for selected image"""
        if not self.selected_image:
            return
        
        img_type = self.type_var.get()
        self.image_metadata[self.selected_image]['type'] = img_type
        self.save_webpage_config()
        
        img_name = Path(self.selected_image).name
        self.log(f"[TYPE] {img_name} -> {img_type}")
    
    def update_caption(self):
        """Update caption text for selected image"""
        if not self.selected_image:
            return
        
        caption = self.caption_var.get()
        self.image_metadata[self.selected_image]['caption'] = caption
        self.save_webpage_config()
        
        img_name = Path(self.selected_image).name
        self.log(f"[CAPTION] {img_name} -> '{caption}' (refresh to apply)")
    
    def toggle_show_excluded(self):
        """Toggle showing excluded images in preview (no auto-refresh)"""
        self.show_excluded = self.show_excluded_var.get()
        status = "ON" if self.show_excluded else "OFF"
        self.log(f"[SHOW EXCLUDED] {status} (refresh to apply)")
        
        # No auto-refresh - user must click refresh button
    
    def toggle_priority_sort(self):
        """Toggle priority-based sorting (no auto-refresh)"""
        self.use_priority_sort = self.use_priority_var.get()
        status = "ON" if self.use_priority_sort else "OFF"
        self.log(f"[PRIORITY SORT] {status} (refresh to apply)")
        
        # No auto-refresh - user must click refresh button
    
    def manual_refresh_preview(self):
        """Manually refresh the preview with current settings"""
        if hasattr(self, 'page_layouts'):
            self.log("[REFRESH] Updating preview...")
            self.root.after(10, self.preview_pages)
        else:
            self.log("[WARN] No layouts available - scan project first")
    
    def open_in_browser(self):
        """Open generated index.html in default browser"""
        output_dir = Path(self.output_folder_var.get())
        index_path = output_dir / "index.html"
        if index_path.exists():
            webbrowser.open(str(index_path))
            self.log(f"[BROWSER] Opened {index_path}")
        else:
            messagebox.showwarning("File Not Found", f"index.html not found in {output_dir}. Generate pages first!")

# ===== MAIN EXECUTION =====

def main_cli():
    """Main execution function"""
    print("=" * 60)
    print("HTML WEBPAGE GENERATOR - Ultima Online Art Mods")
    print("=" * 60)
    
    # Ensure output directory exists
    ensure_docs_dir()
    
    # Scan project structure
    print("\n[SCAN] Scanning project structure...")
    structure = scan_project_structure()
    
    for category, groups in structure.items():
        print(f"  [OK] {category}: {len(groups)} groups found")
    
    # Generate pages
    print("\n[GEN] Generating HTML pages...")
    
    # Index frameset
    print("  > index.html")
    with open(DOCS_DIR / "index.html", 'w', encoding='utf-8') as f:
        f.write(generate_index_frameset())
    
    # Menu frame
    print("  > ultima_art_mods_menu.htm")
    with open(DOCS_DIR / "ultima_art_mods_menu.htm", 'w', encoding='utf-8') as f:
        f.write(generate_menu_frame())
    
    # Main page
    print("  > ultima_art_mods_main.htm")
    with open(DOCS_DIR / "ultima_art_mods_main.htm", 'w', encoding='utf-8') as f:
        f.write(generate_main_page(structure))
    
    # Category pages
    for category, groups in structure.items():
        filename = f"ultima_art_mods_{category.lower()}.htm"
        print(f"  > {filename}")
        with open(DOCS_DIR / filename, 'w', encoding='utf-8') as f:
            f.write(generate_category_page(category, groups, structure))
    
    # Tools page
    print("  > ultima_art_mods_tools.htm")
    with open(DOCS_DIR / "ultima_art_mods_tools.htm", 'w', encoding='utf-8') as f:
        f.write(generate_tools_page())
    
    # Install page
    print("  > ultima_art_mods_install.htm")
    with open(DOCS_DIR / "ultima_art_mods_install.htm", 'w', encoding='utf-8') as f:
        f.write(generate_install_page())
    
    print("\n[OK] HTML generation complete!")
    print(f"[OUTPUT] Directory: {DOCS_DIR}")
    print(f"[OPEN] File: {DOCS_DIR / 'index.html'}")
    print("\n" + "=" * 60)

def main():
    """Main entry point - launch GUI or CLI based on arguments"""
    import sys
    
    # Check if running in CLI mode
    if len(sys.argv) > 1 and sys.argv[1] == '--cli':
        main_cli()
    else:
        # Launch GUI
        root = tk.Tk()
        app = HTMLGeneratorGUI(root)
        root.mainloop()

if __name__ == "__main__":
    main()
