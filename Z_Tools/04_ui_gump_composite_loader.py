"""
UI GUMP COMPOSITE LOADER 
- a Ultima Online gump view from .def files like "Intrface.def"
- Loads the file information of in-game gumps and their arrangement
- Visualizes a gomp composite like the paperdoll
- Exports arrangement as JSON with x, y, w, h of each gump part
on the right side is a list of components , click to follow referenced composites
"""

import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image, ImageTk

# --- DARK MODE COLOR PALETTE ---
DARK_BG = "#101014"
DARK_PANEL = "#181825"
DARKER_PANEL = "#16161e"
TEXT_COLOR = "#cccccc"
MUTED_GREEN = "#3fa97c"
MUTED_BLUE = "#3f6fa9"
MUTED_PURPLE = "#7c3fa9"
MUTED_BUTTON_FG = "#f0f0f0"

class GumpCompositeLoader:
    """
    Loads and parses gump composite arrangement data.
    Supports parsing Intrface.def files from Ultima Online with detailed debug output.
    """
    def __init__(self, composite_file=None, debug=True):
        self.composite_file = composite_file
        self.composites = {}  # {name: [ {id, x, y, w, h, ...}, ... ]}
        self.debug = debug
        if composite_file:
            self.load_composites(composite_file)

    def log(self, msg):
        if self.debug:
            print(msg)

    def load_composites(self, composite_file):
        # Auto-detect .def file and use the appropriate parser
        if composite_file.lower().endswith('.def'):
            self.parse_intrface_def(composite_file)
        else:
            # No fallback or dummy data
            self.composites = {}

    def parse_intrface_def(self, def_path):
        """
        Advanced parser for Intrface.def or similar .def files.
        - Handles blocks (#name ... #enddef)
        - Handles command continuation lines (ending with &)
        - Organizes commands and their subcomponents (indented lines)
        - Provides detailed debug output for parent/child structure
        """
        import re
        self.composites = {}
        self.composite_bboxes = {}
        try:
            with open(def_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw_lines = f.readlines()
        except Exception as e:
            self.log(f"Error reading {def_path}: {e}")
            return
        # Step 1: join continuation lines (ending with &)
        lines = []
        buf = ''
        for line in raw_lines:
            if buf:
                line = buf + line
                buf = ''
            if line.rstrip().endswith('&'):
                buf = line.rstrip()[:-1]  # Remove &
                continue
            lines.append(line)
        # Step 2: parse blocks and commands
        cur_name = None
        cur_block = []
        block_start_line = None
        last_command = None
        for lineno, orig_line in enumerate(lines, 1):
            # Keep original for debug, but work with cleaned up
            line = orig_line.rstrip('\n').replace('\x00', '')
            stripped = line.strip()
            if not stripped or stripped.startswith('//'):
                continue
            if stripped.startswith('#'):
                # Start of block or enddef
                if stripped.lower().startswith('#enddef') or stripped.lower().startswith('# enddef'):
                    if cur_name is not None:
                        self.log(f"[Block {cur_name}] End at line {lineno}. {len(cur_block)} commands collected.")
                        self.composites[cur_name] = cur_block
                        self._calculate_composite_bbox(cur_name, cur_block)
                        cur_name, cur_block, block_start_line, last_command = None, [], None, None
                    continue
                # New block
                if cur_name is not None:
                    # Save previous block (even if empty)
                    self.log(f"[Block {cur_name}] End at line {lineno} (implicit). {len(cur_block)} commands collected.")
                    self.composites[cur_name] = cur_block
                    self._calculate_composite_bbox(cur_name, cur_block)
                cur_name = stripped.lstrip('#').strip()
                cur_block = []
                block_start_line = lineno
                last_command = None
                self.log(f"[Block {cur_name}] Start at line {lineno}.")
                continue
            # Remove inline comments
            code = stripped.split('//', 1)[0].rstrip()
            if not code:
                continue
            # Step 3: detect indented (subcomponent) lines
            is_sub = bool(re.match(r'^[ \t]+', line))
            tokens = [t.strip() for t in code.split() if t.strip()]
            if not tokens:
                continue
            if is_sub and last_command:
                # Subcommand/parameter of previous command
                sub_cmd = tokens[0]
                sub_args = tokens[1:]
                self.log(f"    [Line {lineno}] Sub: {sub_cmd} Args: {sub_args}")
                last_command.add_subcommand(Command(sub_cmd, sub_args, lineno, orig_line.rstrip()))
            else:
                # New parent command
                cmd = tokens[0]
                args = tokens[1:]
                self.log(f"  [Line {lineno}] Command: {cmd} Args: {args}")
                command = CommandFactory(cmd, args, lineno, orig_line.rstrip())
                cur_block.append(command)
                last_command = command
        # Save last block if file does not end with #enddef
        if cur_name is not None:
            self.log(f"[Block {cur_name}] End at EOF. {len(cur_block)} commands collected.")
            self.composites[cur_name] = cur_block
            self._calculate_composite_bbox(cur_name, cur_block)
        self.log(f"Parsed {len(self.composites)} composites (blocks) from {os.path.basename(def_path)}")

    def _calculate_composite_bbox(self, composite_name, command_block, recursion_call_stack=None):
        """
        Calculate the bounding box for a composite by analyzing all commands in the block.
        Supports all commands with x/y/w/h, recursive composite references, and subcommands.
        Prevents infinite recursion using a call stack.
        """
        # Initialize recursion call stack to prevent infinite loops
        if recursion_call_stack is None:
            recursion_call_stack = set()
        if composite_name in recursion_call_stack:
            return None  # Prevent infinite recursion
        updated_call_stack = set(recursion_call_stack)
        updated_call_stack.add(composite_name)
        # Initialize bounding box extents
        min_x_value = float('inf')
        min_y_value = float('inf')
        max_x_value = float('-inf')
        max_y_value = float('-inf')
        found_any_bbox = False
        # Iterate through all commands in the block
        for command_instance in command_block:
            # Check for x/y/w/h attributes on the command
            command_x = getattr(command_instance, 'x', None)
            command_y = getattr(command_instance, 'y', None)
            command_width = getattr(command_instance, 'w', None)
            command_height = getattr(command_instance, 'h', None)
            if None not in (command_x, command_y, command_width, command_height):
                min_x_value = min(min_x_value, command_x)
                min_y_value = min(min_y_value, command_y)
                max_x_value = max(max_x_value, command_x + command_width)
                max_y_value = max(max_y_value, command_y + command_height)
                found_any_bbox = True
            # Check for composite references in command args
            if hasattr(command_instance, 'args') and command_instance.args:
                for possible_composite_ref in command_instance.args:
                    if possible_composite_ref in self.composites:
                        subcomposite_bbox = self._calculate_composite_bbox(
                            possible_composite_ref,
                            self.composites[possible_composite_ref],
                            updated_call_stack
                        )
                        if subcomposite_bbox:
                            sub_min_x, sub_min_y, sub_max_x, sub_max_y = subcomposite_bbox
                            min_x_value = min(min_x_value, sub_min_x)
                            min_y_value = min(min_y_value, sub_min_y)
                            max_x_value = max(max_x_value, sub_max_x)
                            max_y_value = max(max_y_value, sub_max_y)
                            found_any_bbox = True
            # Recursively check subcommands for bounding boxes
            if hasattr(command_instance, 'subcommands') and command_instance.subcommands:
                subcommand_bbox = self._calculate_composite_bbox(
                    composite_name,
                    command_instance.subcommands,
                    updated_call_stack
                )
                if subcommand_bbox:
                    sub_min_x, sub_min_y, sub_max_x, sub_max_y = subcommand_bbox
                    min_x_value = min(min_x_value, sub_min_x)
                    min_y_value = min(min_y_value, sub_min_y)
                    max_x_value = max(max_x_value, sub_max_x)
                    max_y_value = max(max_y_value, sub_max_y)
                    found_any_bbox = True
        # If no bounding box was found, mark as unresolved
        if not found_any_bbox:
            self.composite_bboxes[composite_name] = None
            self.log(f"[BBox] {composite_name}: (empty or unresolved)")
            return None
        # Store and log the resulting bounding box
        self.composite_bboxes[composite_name] = (min_x_value, min_y_value, max_x_value, max_y_value)
        self.log(f"[BBox] {composite_name}: ({min_x_value}, {min_y_value}) - ({max_x_value}, {max_y_value})")
        return (min_x_value, min_y_value, max_x_value, max_y_value)

    def _eval_expr_loader(self, expression, parent_dimensions=None, composite_dimensions=None, gump_dimensions=None):
        """
        Evaluate a position/size expression from the .def file.
        Supports:
        - Absolute integer (e.g., '100')
        - R-25, B+2, C, L+10, T-5: alignment/offsets relative to parent or composite
        - gwXXXX, ghXXXX: gump or composite width/height references
        - Arithmetic: +, -, *, /, parentheses
        - Variable resolution order: parent_dimensions > composite_bboxes > composite_dimensions > gump_dimensions > MUL handler
        - Logs warnings and falls back to 0 if unresolved
        """
        import re
        import math
        # Ensure input is a string and strip whitespace
        expression_str = str(expression).strip()
        # Provide default parent dimensions if not given
        if parent_dimensions is None:
            parent_dimensions = {'w': 0, 'h': 0}
        if composite_dimensions is None:
            composite_dimensions = {}
        if gump_dimensions is None:
            gump_dimensions = {}
        # --- Alignment and Offset Expressions ---
        # Right-aligned
        if expression_str.startswith('R'):
            right_match = re.match(r'R([+-]?\d+)?', expression_str)
            if right_match:
                right_offset = int(right_match.group(1) or 0)
                parent_width = parent_dimensions.get('w', 0)
                return parent_width + right_offset
        # Bottom-aligned
        if expression_str.startswith('B'):
            bottom_match = re.match(r'B([+-]?\d+)?', expression_str)
            if bottom_match:
                bottom_offset = int(bottom_match.group(1) or 0)
                parent_height = parent_dimensions.get('h', 0)
                return parent_height + bottom_offset
        # Center-aligned (horizontal)
        if expression_str.startswith('C'):
            center_match = re.match(r'C([+-]?\d+)?', expression_str)
            if center_match:
                center_offset = int(center_match.group(1) or 0)
                parent_width = parent_dimensions.get('w', 0)
                return parent_width // 2 + center_offset
        # Left-aligned
        if expression_str.startswith('L'):
            left_match = re.match(r'L([+-]?\d+)?', expression_str)
            if left_match:
                left_offset = int(left_match.group(1) or 0)
                return 0 + left_offset
        # Top-aligned
        if expression_str.startswith('T'):
            top_match = re.match(r'T([+-]?\d+)?', expression_str)
            if top_match:
                top_offset = int(top_match.group(1) or 0)
                return 0 + top_offset
        # --- Variable Resolution for gwXXXX/ghXXXX ---
        def variable_reference_resolver(match):
            dimension_type = match.group(1)  # 'w' or 'h'
            gump_or_composite_id = match.group(2)
            variable_key = f'g{dimension_type}{gump_or_composite_id}'
            resolved_value = None
            # 1. Try composite bounding boxes
            if hasattr(self, 'composite_bboxes') and gump_or_composite_id in self.composite_bboxes:
                bbox_tuple = self.composite_bboxes[gump_or_composite_id]
                if bbox_tuple:
                    min_x, min_y, max_x, max_y = bbox_tuple
                    if dimension_type == 'w':
                        resolved_value = max_x - min_x
                    else:
                        resolved_value = max_y - min_y
                    if hasattr(self, 'log'):
                        self.log(f"[BBoxRESOLVE] {variable_key} => {resolved_value} from bbox {bbox_tuple}")
            # 2. Try composite_dimensions
            elif composite_dimensions and variable_key in composite_dimensions:
                resolved_value = composite_dimensions[variable_key]
            # 3. Try gump_dimensions
            elif gump_dimensions and variable_key in gump_dimensions:
                resolved_value = gump_dimensions[variable_key]
            # 4. Try MUL handler
            elif hasattr(self, 'gump_mul_handler') and self.gump_mul_handler:
                mul_dimensions = self.gump_mul_handler.get_gump_dimensions(int(gump_or_composite_id))
                if mul_dimensions:
                    mul_width, mul_height = mul_dimensions
                    resolved_value = mul_width if dimension_type == 'w' else mul_height
                    if hasattr(self, 'log'):
                        self.log(f"[MULRESOLVE] {variable_key} => {resolved_value} from MUL handler")
            if resolved_value is None:
                if hasattr(self, 'log'):
                    self.log(f"[WARN] Could not resolve {variable_key} for expr '{expression_str}'")
                resolved_value = 0
            return str(resolved_value)
        # Replace all gwXXXX/ghXXXX with resolved values
        resolved_expression = re.sub(r'g([wh])(\d+)', variable_reference_resolver, expression_str)
        # Only allow safe characters for eval
        safe_expression = re.sub(r'[^0-9+\-*/(). ]', '', resolved_expression)
        try:
            evaluated_result = eval(safe_expression, {"__builtins__": None, 'math': math}, {})
            return int(evaluated_result)
        except Exception:
            try:
                return int(expression_str)
            except Exception:
                if hasattr(self, 'log'):
                    self.log(f"[WARN] Could not evaluate expr '{expression_str}' (parsed '{safe_expression}')")
                return 0

    def get_composite_names(self):
        return list(self.composites.keys())

    def get_parts(self, name):
        # Return the list of commands for the given composite name
        block = self.composites.get(name)
        if not block:
            return []
        return block

    def export_json(self, name, out_path):
        parts = self.get_parts(name)
        with open(out_path, 'w') as f:
            json.dump(parts, f, indent=2)

class Command:
    """
    Base command class for UO gump composite commands.
    Each subclass implements per-command argument validation and type coercion.
    Subcommands are stored as children (hierarchical structure).
    """
    def __init__(self, cmd, args, lineno, raw):
        self.cmd = cmd
        self.args = args
        self.line = lineno
        self.raw = raw
        self.subcommands = []
        self._parse_args(args)
    def add_subcommand(self, sub):
        self.subcommands.append(sub)
    def _parse_args(self, args):
        # Default: keep as string list; subclasses override for type coercion
        self.parsed_args = args
    def __repr__(self):
        return f"<{self.cmd} {self.args} line={self.line}>"

class RectCommand(Command):
    def _parse_args(self, args):
        # rect x y w h
        self.x = self._to_int(args[0]) if len(args) > 0 else 0
        self.y = self._to_int(args[1]) if len(args) > 1 else 0
        self.w = self._to_int(args[2]) if len(args) > 2 else 0
        self.h = self._to_int(args[3]) if len(args) > 3 else 0
    def _to_int(self, val):
        try:
            return int(val)
        except Exception:
            return 0

class ButtonCommand(Command):
    def _parse_args(self, args):
        # button id x y up_id down_id ...
        self.id = self._to_int(args[0]) if len(args) > 0 else 0
        self.x = self._to_int(args[1]) if len(args) > 1 else 0
        self.y = self._to_int(args[2]) if len(args) > 2 else 0

    def _to_int(self, val):
        try:
            return int(val)
        except Exception:
            return 0

class BackgroundCommand(Command):
    def _parse_args(self, args):
        # background id x y ...
        self.id = self._to_int(args[0]) if len(args) > 0 else 0
        self.x = self._to_int(args[1]) if len(args) > 1 else 0
        self.y = self._to_int(args[2]) if len(args) > 2 else 0
    def _to_int(self, val):
        try:
            return int(val)
        except Exception:
            return 0

class TextCommand(Command):
    def _parse_args(self, args):
        # text x y w h ...
        self.x = self._to_int(args[0]) if len(args) > 0 else 0
        self.y = self._to_int(args[1]) if len(args) > 1 else 0
        self.w = self._to_int(args[2]) if len(args) > 2 else 0
        self.h = self._to_int(args[3]) if len(args) > 3 else 0
    def _to_int(self, val):
        try:
            return int(val)
        except Exception:
            return 0

class ContainerCommand(Command):
    """container x y w h ..."""
    def _parse_args(self, args):
        self.x = self._to_int(args[0]) if len(args) > 0 else 0
        self.y = self._to_int(args[1]) if len(args) > 1 else 0
        self.w = self._to_int(args[2]) if len(args) > 2 else 0
        self.h = self._to_int(args[3]) if len(args) > 3 else 0
    def _to_int(self, val):
        try:
            return int(val)
        except Exception:
            return 0

class ToggleCommand(Command):
    """toggle x y w h ..."""
    def _parse_args(self, args):
        self.x = self._to_int(args[0]) if len(args) > 0 else 0
        self.y = self._to_int(args[1]) if len(args) > 1 else 0
        self.w = self._to_int(args[2]) if len(args) > 2 else 0
        self.h = self._to_int(args[3]) if len(args) > 3 else 0
    def _to_int(self, val):
        try:
            return int(val)
        except Exception:
            return 0

class TextAreaCommand(Command):
    """textarea x y w h ..."""
    def _parse_args(self, args):
        self.x = self._to_int(args[0]) if len(args) > 0 else 0
        self.y = self._to_int(args[1]) if len(args) > 1 else 0
        self.w = self._to_int(args[2]) if len(args) > 2 else 0
        self.h = self._to_int(args[3]) if len(args) > 3 else 0
    def _to_int(self, val):
        try:
            return int(val)
        except Exception:
            return 0

class NumericTextAreaCommand(Command):
    """numerictextarea x y w h ..."""
    def _parse_args(self, args):
        self.x = self._to_int(args[0]) if len(args) > 0 else 0
        self.y = self._to_int(args[1]) if len(args) > 1 else 0
        self.w = self._to_int(args[2]) if len(args) > 2 else 0
        self.h = self._to_int(args[3]) if len(args) > 3 else 0
    def _to_int(self, val):
        try:
            return int(val)
        except Exception:
            return 0

class SpellIconCommand(Command):
    """spellicon x y w h id ..."""
    def _parse_args(self, args):
        self.x = self._to_int(args[0]) if len(args) > 0 else 0
        self.y = self._to_int(args[1]) if len(args) > 1 else 0
        self.w = self._to_int(args[2]) if len(args) > 2 else 0
        self.h = self._to_int(args[3]) if len(args) > 3 else 0
        self.id = self._to_int(args[4]) if len(args) > 4 else 0

    def _to_int(self, val):
        try:
            return int(val)
        except Exception:
            return 0

class VListCommand(Command):
    """vlist x y w h ..."""
    def _parse_args(self, args):
        self.x = self._to_int(args[0]) if len(args) > 0 else 0
        self.y = self._to_int(args[1]) if len(args) > 1 else 0
        self.w = self._to_int(args[2]) if len(args) > 2 else 0
        self.h = self._to_int(args[3]) if len(args) > 3 else 0

    def _to_int(self, val):
        try:
            return int(val)
        except Exception:
            return 0

# Command factory for mapping command names to classes
COMMAND_CLASS_MAP = {
    'rect': RectCommand,
    'button': ButtonCommand,
    'background': BackgroundCommand,
    'text': TextCommand,
    'container': ContainerCommand,
    'toggle': ToggleCommand,
    'textarea': TextAreaCommand,
    'numerictextarea': NumericTextAreaCommand,
    'spellicon': SpellIconCommand,
    'vlist': VListCommand,
}

def CommandFactory(cmd, args, lineno, raw):
    cls = COMMAND_CLASS_MAP.get(cmd.lower(), Command)
    return cls(cmd, args, lineno, raw)

class GumpMulHandler:
    """
    Minimal handler for UO gumpidx.mul/gumpart.mul. Loads gump dimensions (width, height) for any gump ID.
    """
    def __init__(self, folder, debug=True):
        import struct
        self.debug = debug
        self.folder = folder
        self.idx_path = os.path.join(folder, 'gumpidx.mul')
        self.art_path = os.path.join(folder, 'gumpart.mul')
        self.entries = []
        self._gump_dim_cache = {}
        self._load_index()

    def _load_index(self):
        import struct
        if self.debug:
            print(f"[GumpMulHandler] Loading: {self.idx_path} / {self.art_path}")
        if not (os.path.exists(self.idx_path) and os.path.exists(self.art_path)):
            if self.debug:
                print("gumpidx.mul or gumpart.mul not found!")
            self.entries = []
            return
        with open(self.idx_path, 'rb') as idx_file:
            idx_file.seek(0, os.SEEK_END)
            size = idx_file.tell()
            count = size // 12
            idx_file.seek(0)
            for idx in range(count):
                data = idx_file.read(12)
                offset, length, extra = struct.unpack('<iii', data)
                self.entries.append((offset, length, extra))
        if self.debug:
            print(f"[GumpMulHandler] Loaded {len(self.entries)} index entries.")

    def get_gump_dimensions(self, gump_id):
        # Returns (width, height) or None if not found/invalid
        if gump_id in self._gump_dim_cache:
            return self._gump_dim_cache[gump_id]
        if gump_id < 0 or gump_id >= len(self.entries):
            return None
        offset, length, extra = self.entries[gump_id]
        width = (extra >> 16) & 0xFFFF
        height = extra & 0xFFFF
        if offset < 0 or length <= 0 or extra == -1 or width <= 0 or height <= 0:
            return None
        self._gump_dim_cache[gump_id] = (width, height)
        return (width, height)

    def set_folder(self, folder):
        self.folder = folder
        self.idx_path = os.path.join(folder, 'gumpidx.mul')
        self.art_path = os.path.join(folder, 'gumpart.mul')
        self.entries = []
        self._gump_dim_cache = {}
        self._load_index()


class GumpCompositeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("UO Gump Composite Loader")
        self.geometry("900x600")
        self.composite_loader = None
        self.selected_composite = tk.StringVar()
        self.debug_var = tk.BooleanVar(value=True)
        self.gump_mul_handler = None
        self.mul_folder = os.path.abspath(os.path.dirname(__file__))
        self._build_ui()
        # Initialize MUL handler
        self._init_mul_handler(self.mul_folder)

    def _init_mul_handler(self, folder):
        try:
            self.gump_mul_handler = GumpMulHandler(folder, debug=self.debug_var.get())
            self.mul_folder = folder
            if hasattr(self, 'log_message'):
                self.log_message(f"Loaded MUL folder: {folder}")
            elif self.debug_var.get():
                print(f"Loaded MUL folder: {folder}")
        except Exception as e:
            if hasattr(self, 'log_message'):
                self.log_message(f"[ERROR] Could not load MUL folder: {e}")
            elif self.debug_var.get():
                print(f"[ERROR] Could not load MUL folder: {e}")

    def _choose_mul_folder(self):
        folder = filedialog.askdirectory(initialdir=self.mul_folder, title="Select MUL Folder (gumpidx.mul/gumpart.mul)")
        if folder:
            self._init_mul_handler(folder)

    def _build_ui(self):
        self.configure(bg=DARK_BG)
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TCombobox', fieldbackground=DARK_BG, background=DARK_BG, foreground=TEXT_COLOR)
        style.map('TCombobox', fieldbackground=[('readonly', DARK_BG)], background=[('readonly', DARK_BG)], foreground=[('readonly', TEXT_COLOR)])
        style.configure('TCombobox.Listbox', background=DARK_BG, foreground=TEXT_COLOR, selectbackground=MUTED_PURPLE, selectforeground=TEXT_COLOR)

        top = tk.Frame(self, bg=DARK_PANEL)
        top.pack(side=tk.TOP, fill=tk.X, padx=8, pady=6)
        tk.Label(top, text="Def File (Intrface.def):", bg=DARK_PANEL, fg=TEXT_COLOR).pack(side=tk.LEFT)
        self.menu_bar = tk.Menu(self, bg=DARK_BG, fg=TEXT_COLOR)
        self.config(menu=self.menu_bar)
        file_menu = tk.Menu(self.menu_bar, tearoff=0, bg=DARK_BG, fg=TEXT_COLOR)
        file_menu.add_command(label="Open .def File", command=self.browse_file)
        file_menu.add_command(label="Set MUL Folder", command=self._choose_mul_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Export JSON", command=self.export_json)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        self.menu_bar.add_cascade(label="File", menu=file_menu)

        # --- Bounding box toggle ---
        self.show_bboxes = True
        def toggle_bboxes():
            self.show_bboxes = not self.show_bboxes
            self.visualize_composite()
        tk.Button(top, text="Toggle BBoxes", command=toggle_bboxes, bg=MUTED_GREEN, fg=MUTED_BUTTON_FG, activebackground=MUTED_GREEN, activeforeground=TEXT_COLOR).pack(side=tk.LEFT, padx=5)

        # --- Main layout ---
        self.file_var = tk.StringVar()
        tk.Entry(top, textvariable=self.file_var, width=40, bg=DARK_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR).pack(side=tk.LEFT, padx=3)
        tk.Button(top, text="Browse", command=self.browse_file, bg=MUTED_BLUE, fg=MUTED_BUTTON_FG, activebackground=MUTED_BLUE, activeforeground=TEXT_COLOR).pack(side=tk.LEFT)
        tk.Button(top, text="Load", command=self.load_composites, bg=MUTED_PURPLE, fg=MUTED_BUTTON_FG, activebackground=MUTED_PURPLE, activeforeground=TEXT_COLOR).pack(side=tk.LEFT, padx=2)
        tk.Button(top, text="Export JSON", command=self.export_json, bg=MUTED_GREEN, fg=MUTED_BUTTON_FG, activebackground=MUTED_GREEN, activeforeground=TEXT_COLOR).pack(side=tk.RIGHT, padx=3)
        # Debug prints checkbox
        self.debug_checkbox = tk.Checkbutton(top, text="Enable Debug Prints", variable=self.debug_var, bg=DARK_PANEL, fg=TEXT_COLOR, selectcolor=DARK_BG, activebackground=DARK_PANEL, activeforeground=TEXT_COLOR)
        self.debug_checkbox.pack(side=tk.RIGHT, padx=8)

        mid = tk.Frame(self, bg=DARK_BG)
        mid.pack(side=tk.TOP, fill=tk.X, padx=8, pady=2)
        tk.Label(mid, text="Composite:", bg=DARK_BG, fg=TEXT_COLOR).pack(side=tk.LEFT)
        self.composite_combo = ttk.Combobox(mid, textvariable=self.selected_composite, state='readonly')
        self.composite_combo.pack(side=tk.LEFT)
        self.composite_combo.bind('<<ComboboxSelected>>', lambda e: self.visualize_composite())

        # Main horizontal split
        main = tk.Frame(self, bg=DARK_BG)
        main.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        # Canvas on left
        self.canvas = tk.Canvas(main, bg=DARK_BG, width=600, height=500, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)
        # Right panel for hierarchy, search, legend
        right = tk.Frame(main, bg=DARKER_PANEL)
        right.pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=8)

        # Search field
        search_frame = tk.Frame(right, bg=DARKER_PANEL)
        search_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 4))
        tk.Label(search_frame, text="Search:", bg=DARKER_PANEL, fg=TEXT_COLOR).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=20, bg=DARK_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR)
        search_entry.pack(side=tk.LEFT, padx=3)
        search_entry.bind('<Return>', lambda e: self._search_composite())
        search_entry.bind('<KeyRelease>', lambda e: self._filter_composite_list())

        # Interactive hierarchy list
        self.hierarchy_text = tk.Text(right, width=44, height=26, bg=DARK_PANEL, fg=TEXT_COLOR, font=("Consolas", 10), wrap=tk.NONE, insertbackground=TEXT_COLOR, selectbackground=MUTED_PURPLE, selectforeground=TEXT_COLOR)
        self.hierarchy_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=2)
        self.hierarchy_text.config(state=tk.DISABLED)
        self.hierarchy_text.tag_configure('composite_ref', foreground=MUTED_BLUE, underline=1)
        self.hierarchy_text.tag_bind('composite_ref', '<Button-1>', self._on_composite_ref_click)

        # Legend at bottom
        self.legend_frame = tk.Frame(right, bg=DARKER_PANEL)
        self.legend_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 4))
        tk.Label(self.legend_frame, text="Legend:", bg=DARKER_PANEL, fg=MUTED_BUTTON_FG, font=("Arial", 10, "bold")).pack(anchor='w')
        self.legend_labels = []
        # Legend will be filled in visualize_composite

    def browse_file(self):
        path = filedialog.askopenfilename(title="Select composite arrangement file", filetypes=[('All Files', '*.*')])
        if path:
            self.file_var.set(path)

    def load_composites(self):
        path = self.file_var.get()
        if not os.path.exists(path):
            messagebox.showerror("Error", f"File not found: {path}")
            return
        self.composite_loader = GumpCompositeLoader(path, debug=self.debug_var.get())
        names = self.composite_loader.get_composite_names()
        self.composite_combo['values'] = names
        if names:
            self.selected_composite.set(names[0])
            self.visualize_composite()

    def visualize_composite(self):
        self.canvas.delete('all')
        if not self.composite_loader:
            return
        name = self.selected_composite.get()
        all_names = set(self.composite_loader.get_composite_names())
        cmd_colors = {
            'rect': '#44ff99',
            'background': '#4eaaff',
            'button': '#a66cff',
            'text': '#ffcc44',
            'textarea': '#ff4488',
            'container': '#ff4488',
            'toggle': '#ff4488',
            'vlist': '#ff8844',
            'spellicon': '#44aaff',
            'numerictextarea': '#ff44cc',
            'default': '#cccccc',
        }
        layer_styles = [
            {'outline':'#44ff99','dash':None,'alpha':255},  # Layer 0
            {'outline':'#4eaaff','dash':(4,2),'alpha':180}, # Layer 1
            {'outline':'#a66cff','dash':(2,4),'alpha':120}, # Layer 1a
            {'outline':'#ffcc44','dash':(2,2),'alpha':90},  # Layer 2
            {'outline':'#ff4488','dash':(6,2),'alpha':70},  # Layer 2a
        ]
        dot_radius = 5
        self._draw_composite_on_canvas(name, '0', (0,0), 1.0, 0, cmd_colors, layer_styles, dot_radius, set(), set(self.composite_loader.get_composite_names()))

    def _draw_composite_on_canvas(self, comp_name, layer_tag='0', offset=(0,0), scale=1.0, depth=0, cmd_colors=None, layer_styles=None, dot_radius=5, call_stack=None, all_names=None, parent_dims=None, gump_dims=None):
        """
        Recursively draw a composite and its referenced composites on the canvas.
        """
        if call_stack is None:
            call_stack = set()
        if gump_dims is None:
            gump_dims = {}
        if (comp_name, layer_tag) in call_stack:
            return
        call_stack = set(call_stack)
        call_stack.add((comp_name, layer_tag))
        commands = self.composite_loader.get_parts(comp_name)
        style_idx = min(depth, len(layer_styles)-1)
        style = layer_styles[style_idx]
        outline = style['outline']
        dash = style['dash']
        alpha = style['alpha']

        comp_w, comp_h = self._compute_composite_dimensions(commands)
        gump_dims = dict(gump_dims)
        gump_dims[f'w{comp_name}'] = comp_w
        gump_dims[f'h{comp_name}'] = comp_h

        if getattr(self, 'show_bboxes', True):
            self._draw_bounding_box(comp_name, scale, offset)

        for i, cmd in enumerate(commands):
            self._draw_command(cmd, scale, offset, outline, dash, cmd_colors, layer_tag, dot_radius)
            self._draw_referenced_composites(cmd, all_names, comp_name, scale, offset, layer_tag, depth, cmd_colors, layer_styles, dot_radius, call_stack, gump_dims, comp_w, comp_h)
            self._draw_subcommands(cmd, all_names, comp_name, scale, offset, layer_tag, depth, cmd_colors, layer_styles, dot_radius, call_stack, gump_dims, comp_w, comp_h)

        self._update_hierarchy_list(comp_name, cmd_colors, all_names)


    def _compute_composite_dimensions(self, commands):
        comp_w, comp_h = 0, 0
        for cmd in commands:
            x = getattr(cmd, 'x', None)
            y = getattr(cmd, 'y', None)
            w = getattr(cmd, 'w', None)
            h = getattr(cmd, 'h', None)
            if None not in (x, y, w, h):
                comp_w = max(comp_w, x + w)
                comp_h = max(comp_h, y + h)
        return comp_w, comp_h

    def _draw_bounding_box(self, comp_name, scale, offset):
        bbox = getattr(self.composite_loader, 'composite_bboxes', {}).get(comp_name)
        if bbox and None not in bbox:
            min_x, min_y, max_x, max_y = bbox
            x0 = int(min_x*scale + offset[0])
            y0 = int(min_y*scale + offset[1])
            x1 = int(max_x*scale + offset[0])
            y1 = int(max_y*scale + offset[1])
            self.canvas.create_rectangle(x0, y0, x1, y1, outline='#ff4444', width=2, dash=(4,2))

    def _draw_command(self, cmd, scale, offset, outline, dash, cmd_colors, layer_tag, dot_radius):
        ctype = getattr(cmd, 'cmd', 'default')
        color = cmd_colors.get(ctype, cmd_colors['default'])
        x = getattr(cmd, 'x', None)
        y = getattr(cmd, 'y', None)
        w = getattr(cmd, 'w', None)
        h = getattr(cmd, 'h', None)
        if x is not None and y is not None:
            x_draw = int(x*scale + offset[0])
            y_draw = int(y*scale + offset[1])
            self.canvas.create_oval(x_draw-dot_radius, y_draw-dot_radius, x_draw+dot_radius, y_draw+dot_radius, fill=color, outline=outline)
        if x is not None and y is not None and w is not None and h is not None:
            x0 = int(x*scale + offset[0])
            y0 = int(y*scale + offset[1])
            x1 = int((x+w)*scale + offset[0])
            y1 = int((y+h)*scale + offset[1])
            self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=1, dash=(2,2))
            w_draw = int(w*scale)
            h_draw = int(h*scale)
            box_outline = outline
            box_dash = dash
            if any(val is None for val in [x, y, w, h]):
                box_outline = 'red'
                box_dash = (2,2)
            self.canvas.create_rectangle(x_draw, y_draw, x_draw+w_draw, y_draw+h_draw, outline=box_outline, width=2, dash=box_dash)
            self.canvas.create_text(x_draw + 5, y_draw + 5, anchor='nw', text=f"{ctype} [{layer_tag}]", fill=color, font=("Arial", 9, "bold"))

    def _draw_referenced_composites(self, cmd, all_names, comp_name, scale, offset, layer_tag, depth, cmd_colors, layer_styles, dot_radius, call_stack, gump_dims, comp_w, comp_h):
        args = getattr(cmd, 'args', [])
        for idx, arg in enumerate(args):
            if arg in all_names and arg != comp_name:
                ref_offset = (getattr(cmd, 'x', 0), getattr(cmd, 'y', 0))
                ref_scale = scale
                next_layer_tag = f"{layer_tag}{chr(97+idx)}"
                self._draw_composite_on_canvas(arg, next_layer_tag, offset=ref_offset, scale=ref_scale, depth=depth+1, cmd_colors=cmd_colors, layer_styles=layer_styles, dot_radius=dot_radius, call_stack=call_stack, all_names=all_names, parent_dims={'w':comp_w,'h':comp_h}, gump_dims=gump_dims)

    def _draw_subcommands(self, cmd, all_names, comp_name, scale, offset, layer_tag, depth, cmd_colors, layer_styles, dot_radius, call_stack, gump_dims, comp_w, comp_h):
        subcommands = getattr(cmd, 'subcommands', [])
        for j, sub in enumerate(subcommands):
            sub_args = getattr(sub, 'args',[])
            for sidx, sarg in enumerate(sub_args):
                if sarg in all_names and sarg != comp_name:
                    ref_offset = (getattr(cmd, 'x', 0), getattr(cmd, 'y', 0))
                    ref_scale = scale
                    next_layer_tag = f"{layer_tag}{chr(107+sidx)}"
                    self._draw_composite_on_canvas(sarg, next_layer_tag, offset=ref_offset, scale=ref_scale, depth=depth+1, cmd_colors=cmd_colors, layer_styles=layer_styles, dot_radius=dot_radius, call_stack=call_stack, all_names=all_names, parent_dims={'w':comp_w,'h':comp_h}, gump_dims=gump_dims)

    def _update_hierarchy_list(self, comp_name, cmd_colors, all_names):
        self.hierarchy_text.config(state=tk.NORMAL)
        self.hierarchy_text.delete('1.0', tk.END)
        self._build_hierarchy_list(comp_name, cmd_colors, all_names)
        self.hierarchy_text.config(state=tk.DISABLED)

    def _build_hierarchy_list(self, comp_name, cmd_colors, all_names):
        commands = self.composite_loader.get_parts(comp_name)

        def insert_cmd(cmd, idx, level=0, all_names=all_names, comp_name=comp_name):
            ctype = cmd.get('cmd', 'default') if isinstance(cmd, dict) else getattr(cmd, 'cmd', 'default')
            color = cmd_colors.get(ctype, cmd_colors['default'])
            args = cmd.get('args', []) if isinstance(cmd, dict) else getattr(cmd, 'args', [])
            label = f"{'  '*level}{idx}. {ctype} "
            self.hierarchy_text.insert(tk.END, label, ())
            for arg in args:
                if arg in all_names:
                    start = self.hierarchy_text.index(tk.END)
                    self.hierarchy_text.insert(tk.END, arg, ('composite_ref',))
                    end = self.hierarchy_text.index(tk.END)
                    tagname = f'ref_{arg}'
                    self.hierarchy_text.tag_add(tagname, start, end)
                    # Pass comp_name as argument to the callback if needed in the future
                    self.hierarchy_text.tag_bind(tagname, '<Button-1>', self._on_composite_ref_click)
                else:
                    self.hierarchy_text.insert(tk.END, arg + ' ', ())
            self.hierarchy_text.insert(tk.END, '\n', ())
            subcommands = cmd.get('subcommands', []) if isinstance(cmd, dict) else getattr(cmd, 'subcommands', [])
            for j, sub in enumerate(subcommands):
                insert_cmd(sub, f"{idx}.{j}", level+1, all_names=all_names, comp_name=comp_name)

        for i, cmd in enumerate(commands):
            insert_cmd(cmd, i, all_names=all_names, comp_name=comp_name)

    def _update_legend(self, cmd_colors, all_names=None, comp_name=None, layer_tag=None, **kwargs):
        """
        Update the legend panel with color labels for each command type.
        Context variables are accepted for future extensibility and explicitness.
        """
        for widget in self.legend_frame.winfo_children():
            if isinstance(widget, tk.Label) and widget.cget('text') != 'Legend:':
                widget.destroy()
        for k, v in cmd_colors.items():
            if k == 'default':
                continue
            lbl = tk.Label(self.legend_frame, text=k, bg="#23233a", fg=v, font=("Arial", 9))
            lbl.pack(anchor='w', padx=18)
            self.legend_labels.append(lbl)
        self._update_hierarchy_list(comp_name, cmd_colors, all_names)


    def _eval_expr_app(self, expr, parent_dims=None, gump_dims=None):
        """
        Evaluate a position/size expression from the .def file.
        Supported syntax:
        - Absolute integer (e.g., '100')
        - R-25: right-aligned, parent width minus 25 (presumption: 'R-xx' means right edge - xx)
        - B+2: bottom-aligned, parent height plus 2 (presumption: 'B+xx' means bottom edge + xx)
        - gw1234: width of gump/composite 1234 (presumption: 'gwXXXX' = width of composite XXXX)
        - gh1234: height of gump/composite 1234 (presumption: 'ghXXXX' = height of composite XXXX)
        - Arithmetic: supports +, -, *, /, and parentheses
        - If referenced gump/composite width/height is unknown, fallback to 0 and log debug
        """
        import re
        import math
        if parent_dims is None:
            parent_dims = {'w': 0, 'h': 0}
        if gump_dims is None:
            gump_dims = {}
        expr = str(expr).strip()
        # R/B alignment
        if expr.startswith('R'):
            # e.g. R-25 or R+10
            m = re.match(r'R([+-]?\d+)', expr)
            if m:
                offset = int(m.group(1))
                # Presumption: right edge = parent width
                return parent_dims.get('w', 0) + offset
        if expr.startswith('B'):
            m = re.match(r'B([+-]?\d+)', expr)
            if m:
                offset = int(m.group(1))
                # Presumption: bottom edge = parent height
                return parent_dims.get('h', 0) + offset
        # Replace gwXXXX/ghXXXX with known values
        expr2 = re.sub(r'g([wh])(\d+)', lambda m: self._gw_gh_repl_app(m, gump_dims), expr)

        # Only allow safe characters
        expr2 = re.sub(r'[^0-9+\-*/(). ]', '', expr2)
        try:
            result = eval(expr2, {"__builtins__": None}, {})
            return int(result)
        except Exception:
            # Fallback: try int
            try:
                return int(expr)
            except Exception:
                # Unresolved
                if hasattr(self, 'log_message'):
                    self.log_message(f"[WARN] Could not evaluate expr '{expr}' (parsed '{expr2}')")
                elif self.debug_var.get():
                    print(f"[WARN] Could not evaluate expr '{expr}' (parsed '{expr2}')")
                return None

    def _gw_gh_repl_app(self, gump_match, gump_dims):
        # Extract type and number from regex match
        gump_dimension_type = gump_match.group(1)  # e.g. 'gw' or 'gh'
        gump_id_str = gump_match.group(2)
        gump_dimension_key = f'{gump_dimension_type}{gump_id_str}'
        resolved_gump_dimension = gump_dims.get(gump_dimension_key, None)
        # If not found in gump_dims, try to resolve using MUL handler
        if resolved_gump_dimension is None:
            if self.gump_mul_handler:
                # Only handle 'gw' (width) and 'gh' (height)
                if gump_dimension_type in ('gw', 'gh'):
                    mul_dimensions_tuple = self.gump_mul_handler.get_gump_dimensions(int(gump_id_str))
                    if mul_dimensions_tuple:
                        mul_width, mul_height = mul_dimensions_tuple
                        resolved_gump_dimension = mul_width if gump_dimension_type == 'gw' else mul_height
                    else:
                        # Log missing gump dimension
                        if hasattr(self, 'log_message'):
                            self.log_message(f"[WARN] Missing gump dimension: {gump_dimension_type}{gump_id_str}")
                        elif hasattr(self, 'debug_var') and self.debug_var.get():
                            print(f"[WARN] Missing gump dimension: {gump_dimension_type}{gump_id_str}")
                        resolved_gump_dimension = 0
                else:
                    # Log unknown dimension type
                    if hasattr(self, 'log_message'):
                        self.log_message(f"[WARN] Unknown dimension type: {gump_dimension_type}")
                    elif hasattr(self, 'debug_var') and self.debug_var.get():
                        print(f"[WARN] Unknown dimension type: {gump_dimension_type}")
                    resolved_gump_dimension = 0
            else:
                # Log if MUL handler is not available
                if hasattr(self, 'log_message'):
                    self.log_message(f"[WARN] No MUL handler loaded for gw{gump_id_str}")
                elif hasattr(self, 'debug_var') and self.debug_var.get():
                    print(f"[WARN] No MUL handler loaded for gw{gump_id_str}")
                resolved_gump_dimension = 0
        return str(resolved_gump_dimension)
    
    def _safe_int(self, val):
        # Try to convert to int, fallback to 0 if not possible
        try:
            return int(val)
        except Exception:
            return 0

    def _on_composite_ref_click(self, event):
        # Find the composite name under the mouse and switch to it
        idx = self.hierarchy_text.index(f"@{event.x},{event.y}")
        tags = self.hierarchy_text.tag_names(idx)
        for tag in tags:
            if tag.startswith('ref_'):
                comp_name = tag[4:]
                self.selected_composite.set(comp_name)
                self.visualize_composite()
                break

    def _search_composite(self):
        # Search for composite by name and jump to it
        name = self.search_var.get().strip()
        names = self.composite_loader.get_composite_names() if self.composite_loader else []
        if name in names:
            self.selected_composite.set(name)
            self.visualize_composite()

    def _filter_composite_list(self):
        # Filter dropdown list by search string
        query = self.search_var.get().strip().lower()
        names = self.composite_loader.get_composite_names() if self.composite_loader else []
        filtered = [n for n in names if query in n.lower()]
        self.composite_combo['values'] = filtered
        if filtered:
            self.selected_composite.set(filtered[0])
            self.visualize_composite()

    def export_json(self):
        if not self.composite_loader:
            messagebox.showerror("Error", "No composite loaded.")
            return
        name = self.selected_composite.get()
        if not name:
            messagebox.showerror("Error", "No composite selected.")
            return
        out_path = filedialog.asksaveasfilename(title="Export JSON", defaultextension=".json", filetypes=[('JSON', '*.json')])
        if out_path:
            self.composite_loader.export_json(name, out_path)
            messagebox.showinfo("Exported", f"Exported to {out_path}")

if __name__ == "__main__":
    app = GumpCompositeApp()
    app.mainloop()