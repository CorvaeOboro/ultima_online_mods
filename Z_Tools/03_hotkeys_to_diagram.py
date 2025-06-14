"""
HOTKEY TO DIAGRAM - an Ultima Online display of hotkeys from Razor or RazorEnhanced
color coded groups of hotkeys ( attack , defense , pet  ) - current default 
display as keyboard with color coded variants , and below an organized list of hotkeys

TODO: 
add custom "short names" for display 
add custom images for hotkeys , for example spell icons or item icons like potions , display the images in the keyboard layout
"""
import os
import sys
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QTextEdit, QVBoxLayout, QMessageBox,
    QLineEdit, QFileDialog, QHBoxLayout, QTableWidget, QTableWidgetItem, QCheckBox, QPushButton, QHeaderView, QTabWidget,
    QGridLayout, QScrollArea, QSizePolicy, QColorDialog
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5 import QtGui

#//==============================================================
# GLOBAL VARIABLES

#  keyboard layout for ANSI 104-key with key widths and offsets
KEYBOARD_LAYOUT = [
    # Row 1
    [("Esc", 1), ("", 0.5), ("F1", 1), ("F2", 1), ("F3", 1), ("F4", 1), ("", 0.5), ("F5", 1), ("F6", 1), ("F7", 1), ("F8", 1), ("", 0.5), ("F9", 1), ("F10", 1), ("F11", 1), ("F12", 1), ("", 0.5), ("PrtSc", 1), ("Scroll", 1), ("Pause", 1)],
    # Row 2
    [("~", 1.25), ("1", 1), ("2", 1), ("3", 1), ("4", 1), ("5", 1), ("6", 1), ("7", 1), ("8", 1), ("9", 1), ("0", 1), ("-", 1), ("=", 1), ("Backspace", 2), ("", 0.5), ("Insert", 1), ("Home", 1), ("PgUp", 1)],
    # Row 3
    [("Tab", 1.5), ("Q", 1), ("W", 1), ("E", 1), ("R", 1), ("T", 1), ("Y", 1), ("U", 1), ("I", 1), ("O", 1), ("P", 1), ("[", 1), ("]", 1), ("\\", 1.5), ("", 0.5), ("Delete", 1), ("End", 1), ("PgDn", 1)],
    # Row 4
    [("Caps", 1.75), ("A", 1), ("S", 1), ("D", 1), ("F", 1), ("G", 1), ("H", 1), ("J", 1), ("K", 1), ("L", 1), (";", 1), ("'", 1), ("Enter", 2.25)],
    # Row 5
    [("Shift", 2.25), ("Z", 1), ("X", 1), ("C", 1), ("V", 1), ("B", 1), ("N", 1), ("M", 1), (",", 1), (".", 1), ("/", 1), ("RShift", 2.75), ("", 0.5), ("Up", 1)],
    # Row 6
    [("Ctrl", 1.25), ("Win", 1.25), ("Alt", 1.25), ("Space", 6.25), ("RAlt", 1.25), ("Fn", 1.25), ("Menu", 1.25), ("RCtrl", 1.25), ("", 0.5), ("Left", 1), ("Down", 1), ("Right", 1)]
]
#  Key normalization mapping 
KEY_ALIASES = {
    "control": "Ctrl", "ctrl": "Ctrl", "lcontrol": "Ctrl", "rcontrol": "RCtrl",
    "alt": "Alt", "lalt": "Alt", "ralt": "RAlt",
    "shift": "Shift", "lshift": "Shift", "rshift": "RShift",
    "win": "Win", "meta": "Win",
    "esc": "Esc", "escape": "Esc",
    "return": "Enter", "enter": "Enter",
    "space": "Space", "spacebar": "Space",
    "capslock": "Caps", "caps": "Caps",
    "backspace": "Backspace",
    "tab": "Tab",
    "del": "Delete", "delete": "Delete",
    "ins": "Insert", "insert": "Insert",
    "pgup": "PgUp", "pageup": "PgUp",
    "pgdn": "PgDn", "pagedown": "PgDn",
    "prtsc": "PrtSc", "printscreen": "PrtSc",
    "scroll": "Scroll", "pause": "Pause",
    "menu": "Menu",
    "home": "Home", "end": "End",
    "up": "Up", "down": "Down", "left": "Left", "right": "Right",
}

#  dictionary for key conversion.
key_conversion = {
    # Mouse buttons (example)
    1: "Left Mouse Button",
    2: "Right Mouse Button",
    500: "Middle Mouse Button",
    
    # Control keys
    8: "Backspace",
    9: "Tab",
    13: "Enter",
    16: "Shift",
    17: "Control",
    18: "Alt",
    19: "Pause/Break",
    20: "Caps Lock",
    27: "Escape",
    32: "Spacebar",
    
    # Arrow keys (Windows virtual-key codes)
    37: "Left Arrow",
    38: "Up Arrow",
    39: "Right Arrow",
    40: "Down Arrow",
    
    # Function keys
    112: "F1",
    113: "F2",
    114: "F3",
    115: "F4",
    116: "F5",
    117: "F6",
    118: "F7",
    119: "F8",
    120: "F9",
    121: "F10",
    122: "F11",
    123: "F12",
    
    # Explicit overrides based on provided examples.
    51: "3",    # ASCII 51 is '3'
    67: "c",    # ASCII 67 is 'C', force to lowercase.
    70: "f",    # ASCII 70 is 'F', force to lowercase.
    73: "i",    # ASCII 73 is 'I', force to lowercase.
    87: "w"     # ASCII 87 is 'W', force to lowercase.
}


#//==============================================================

def get_key_id(key_code):
    """Convert a numeric key_code to a friendly string.
    
    Uses our conversion dictionary. If a key code isn’t explicitly mapped,
    it falls back to Python's chr() conversion and lowercases letters.
    """
    if key_code in key_conversion:
        return key_conversion[key_code]
    try:
        # For ASCII codes (letters, digits, punctuation)
        char = chr(key_code)
    except Exception:
        return "Unknown"
    return char.lower() if char.isalpha() else char


DARK_QSS = """
QWidget {
    background-color: #23272b;
    color: #f8f8f2;
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 13px;
    padding: 2px 4px;
    margin: 0;
}
QPushButton {
    background-color: #2e3236;
    border: 2px solid #444;
    border-radius: 8px;
    padding: 2px 4px;
    color: #f8f8f2;
}
QPushButton:checked, QPushButton[lit="true"] {
    background-color: #5c6370;
    border: 3px solid #ff5370;
    color: #fff;
}
QPushButton:hover {
    background-color: #44475a;
    border: 2px solid #8be9fd;
}
QTabWidget::pane {
    border: 1px solid #444;
    background: #181a1b;
    padding: 2px;
}
QTabBar::tab {
    background: #23272b;
    color: #f8f8f2;
    border: 1px solid #444;
    border-radius: 6px 6px 0 0;
    padding: 3px 9px;
    margin-right: 1px;
}
QTabBar::tab:selected {
    background: #44475a;
    color: #fff;
}
QTableWidget {
    background: #181a1b;
    color: #f8f8f2;
    gridline-color: #444;
    padding: 2px;
}
"""


def blend_with_dark(hex_color, alpha=0.55):
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    dr, dg, db = 24, 26, 27  # #181a1b
    r = int(r * alpha + dr * (1 - alpha))
    g = int(g * alpha + dg * (1 - alpha))
    b = int(b * alpha + db * (1 - alpha))
    return f'rgb({r},{g},{b})'


class KeyboardWidget(QWidget):
    def __init__(self, hotkey_map=None, parent=None):
        super().__init__(parent)
        self.hotkey_map = hotkey_map or {}
        self.key_buttons = {}  # key label -> QPushButton
        self.setLayout(QGridLayout())
        self._draw_keyboard()

    def _draw_keyboard(self):
        # Clear any existing layout and widgets
        old_layout = self.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
        # Container for aspect ratio
        container = QWidget(self)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(2, 2, 2, 2)
        container_layout.setSpacing(2)
        grid = QGridLayout()
        grid.setHorizontalSpacing(32)  # Further increased for more space between keys
        grid.setVerticalSpacing(4)
        grid.setContentsMargins(20, 4, 20, 4)  # Further increased horizontal margin for keyboard area
        self.key_buttons.clear()
        print("[DEBUG] Drawing keyboard...")
        # Build normalized lookup for hotkey assignments
        normalized_hotkey_map = {}
        for key_code, info in self.hotkey_map.items():
            # Accept both int and str keys
            try:
                key_code_int = int(key_code)
                key_label_from_code = get_key_id(key_code_int)
            except (ValueError, TypeError):
                key_label_from_code = str(key_code)
            normalized_from_code = normalize_key_label(key_label_from_code)
            normalized_hotkey_map[normalized_from_code] = info
            # Also allow mapping by label directly if present
            if isinstance(key_code, str):
                normalized_hotkey_map[normalize_key_label(key_code)] = info
        # Draw keyboard keys
        for row_idx, keys in enumerate(KEYBOARD_LAYOUT):
            col = 0
            for key_label, width in keys:
                if key_label == "":
                    col += int(width * 2)
                    continue
                btn = QPushButton()
                btn.setCheckable(True)
                btn.setProperty("lit", False)
                btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
                btn.setMinimumSize(80, 72)  # Increased width for more horizontal padding
                normalized_key = normalize_key_label(key_label)
                info = normalized_hotkey_map.get(normalized_key)
                if info:
                    color = info.get("color", "#ff5370")
                    action = info.get('info', '')
                    category = info.get('category', '')
                    print(f"[DEBUG] Key '{key_label}' (normalized: '{normalized_key}') assigned color {color} for action '{action}' and category '{category}'")
                    btn.setChecked(True)
                    # Use a near-black blend of the category color for background, matching legend
                    bg_color = blend_with_dark(color, 0.55)
                    btn.setStyleSheet(f"QPushButton {{ background-color: {bg_color}; border: 3px solid {color}; border-radius: 9px; color: #fff; font-size: 15px; font-weight: bold; padding: 1px 8px 1px 8px; margin-left:6px; margin-right:6px; }}")  # Increased horizontal padding and margin
                else:
                    print(f"[DEBUG] Key '{key_label}' (normalized: '{normalized_key}') is unused or has no color assignment.")
                    btn.setChecked(False)
                    # Unused key: dark background, dark border, dim text
                    btn.setStyleSheet("QPushButton { background-color: #181a1b; border: 2px solid #222; border-radius: 9px; color: #444; font-size: 14px; font-weight: bold; padding: 1px 8px 1px 8px; margin-left:6px; margin-right:6px;}")  # Increased horizontal padding and margin
                    action = ""
                    color = None
                    category = None

                # --- Unified label creation for both used and unused keys ---
                key_label_widget = QLabel(str(key_label))
                key_label_widget.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
                label_color = "#fff" if info else "#444"
                key_label_widget.setStyleSheet(f"background: transparent; font-size:14px; font-weight:bold; margin-top:2px; margin-bottom:0px; color:{label_color};")

                # Wrap action string to a set number of characters, preferably at spaces or underscores
                def wrap_action(s, limit=13):
                    s = str(s)
                    words = []
                    current = ''
                    for part in s.replace('_', ' _').split():
                        if len(current) + len(part) + 1 > limit and current:
                            words.append(current)
                            current = part
                        else:
                            if current:
                                current += ' '
                            current += part
                    if current:
                        words.append(current)
                    return '\n'.join(words)
                action_wrapped = wrap_action(action)

                name_label_widget = QLabel(action_wrapped)
                name_label_widget.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
                name_label_widget.setWordWrap(True)
                name_label_widget.setStyleSheet(f"background: transparent; font-size:11px; color:{{'#fff' if info else '#222'}}; margin-top:2px; margin-bottom:0px; padding-left:4px; padding-right:4px;")

                # Tooltip with expanded info for used keys
                if info:
                    info_lines = [f"<b>Key:</b> {key_label}"]
                    if action:
                        info_lines.append(f"<b>Action:</b> {action}")
                    if category:
                        info_lines.append(f"<b>Category:</b> {category}")
                    if info.get('source'):
                        info_lines.append(f"<b>File:</b> {info['source']}")
                    btn.setToolTip("<br>".join(info_lines))
                else:
                    btn.setToolTip(key_label)

                btn_layout = QVBoxLayout(btn)
                btn_layout.setContentsMargins(1, 1, 1, 1)
                btn_layout.setSpacing(0)
                btn_layout.addWidget(key_label_widget)
                btn_layout.addWidget(name_label_widget)
                grid.addWidget(btn, row_idx, col, 1, int(width * 2))
                self.key_buttons[key_label] = btn
                col += int(width * 2)
        # Add grid to container and set layout
        container_layout.addLayout(grid)
        container.setLayout(container_layout)
        # Set layout for KeyboardWidget
        if self.layout() is not None:
            QWidget().setLayout(self.layout())
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(container)
        # Overlay label for hotkey details (unchanged)
        if not hasattr(self, 'overlay_label'):
            self.overlay_label = QLabel(self)
            self.overlay_label.setStyleSheet("background:rgba(30,32,34,0.93);color:#fff;padding:8px 18px;border-radius:10px;font-size:15px;font-weight:bold;")
            self.overlay_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
            self.overlay_label.setVisible(False)
            self.overlay_label.move(self.width() - 410, 10)
            self.overlay_label.resize(400, 52)


    def _make_hover_show(self, key):
        def enterEvent(event):
            if key in self.hotkey_map:
                text = f"<b>{key}</b>"
                info = self.hotkey_map[key].get('info', '')
                if info:
                    text += f"<br><b>Action:</b> {info}"
                src = self.hotkey_map[key].get('source', '')
                if src:
                    text += f"<br><b>File:</b> {src}"
                cat = self.hotkey_map[key].get('category', '')
                if cat:
                    text += f"<br><b>Category:</b> {cat}"
                self.overlay_label.setText(text)
                self.overlay_label.setVisible(True)
            else:
                self.overlay_label.setVisible(False)
        return enterEvent

    def _make_hover_clear(self):
        def leaveEvent(event):
            self.overlay_label.setVisible(False)
        return leaveEvent

    def set_hotkeys(self, hotkey_map):
        self.hotkey_map = hotkey_map or {}
        self._draw_keyboard()

def normalize_key_label(label):
    l = str(label).strip().lower()
    if l in KEY_ALIASES:
        return KEY_ALIASES[l]
    if len(l) == 1:
        return l.upper()
    if l.startswith('f') and l[1:].isdigit():
        return l.upper()
    return label

class CategoryManagerWidget(QWidget):
    def __init__(self, categories, on_update=None):
        super().__init__()
        self.categories = categories  # dict: name -> color
        self.on_update = on_update
        self.setLayout(QVBoxLayout())
        self._draw()
    def _draw(self):
        layout = self.layout()
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
            else:
                sublayout = item.layout()
                if sublayout is not None:
                    while sublayout.count():
                        subitem = sublayout.takeAt(0)
                        if subitem.widget():
                            subitem.widget().setParent(None)
                    layout.removeItem(sublayout)
        for cat, color in self.categories.items():
            row = QHBoxLayout()
            label = QLabel(cat)
            color_btn = QPushButton()
            color_btn.setStyleSheet(f"background:{color}; border:2px solid #333; width:20px;")
            color_btn.setFixedWidth(32)
            import functools
            color_btn.clicked.connect(functools.partial(self.pick_color, cat))
            del_btn = QPushButton("✕")
            del_btn.setFixedWidth(24)
            del_btn.clicked.connect(functools.partial(self.remove_category, cat))
            row.addWidget(label)
            row.addWidget(color_btn)
            row.addWidget(del_btn)
            layout.addLayout(row)
        add_btn = QPushButton("Add Category")
        add_btn.clicked.connect(self.add_category)
        layout.addWidget(add_btn)
    def pick_color(self, cat):
        color = QColorDialog.getColor()
        if color.isValid():
            self.categories[cat] = color.name()
            self._draw()
            if self.on_update:
                self.on_update(self.categories)
    def remove_category(self, cat):
        self.categories.pop(cat, None)
        self._draw()
        if self.on_update:
            self.on_update(self.categories)
    def add_category(self):
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Add Category", "Category name:")
        if ok and name and name not in self.categories:
            self.categories[name] = "#a0a0a0"
            self._draw()
            if self.on_update:
                self.on_update(self.categories)

class HotkeyLegendList(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(0, 2, parent)
        self.setHorizontalHeaderLabels(["Key", "Name"])
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setShowGrid(False)
        # Dark mode for table, header, and scrollbars
        self.setStyleSheet("""
            QTableWidget { background: #181a1b; color: #eee; font-size: 13px; border: none; }
            QTableWidget::item { padding: 2px 8px; border: none; }
            QHeaderView::section { background: #232323; color: #444; font-weight: bold; border: none; padding: 4px; }
            QScrollBar:vertical { background: #232323; width: 12px; margin: 0px; border-radius: 6px; }
            QScrollBar::handle:vertical { background: #333; min-height: 24px; border-radius: 6px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { background: none; height: 0px; }
            QScrollBar:horizontal { background: #232323; height: 12px; margin: 0px; border-radius: 6px; }
            QScrollBar::handle:horizontal { background: #333; min-width: 24px; border-radius: 6px; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { background: none; width: 0px; }
            QScrollBar { border: none; }
        """)

    def set_hotkeys(self, hotkey_map):

        self.setRowCount(0)
        # Set key column width
        self.setColumnWidth(0, 66)  # 60% of previous width
        self.setColumnWidth(1, 210)
        # Build a physical key order map from KEYBOARD_LAYOUT
        key_order = []
        for row in KEYBOARD_LAYOUT:
            for key, width in row:
                if key:
                    key_order.append(normalize_key_label(key))
        # Group by category or file type
        groups = {}
        for key, info in hotkey_map.items():
            group = info.get("category", None) or info.get("source", "Other")
            groups.setdefault(group, []).append((key, info))
        print("[DEBUG] Setting hotkeys in legend:")
        row = 0
        for group, items in sorted(groups.items()):
            # Insert a group header row
            self.insertRow(row)
            header_item = QTableWidgetItem(str(group))
            header_item.setFlags(Qt.ItemIsEnabled)
            header_item.setBackground(Qt.darkGray)
            header_item.setForeground(Qt.white)
            header_item.setFont(self.font())
            header_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.setSpan(row, 0, 1, 2)
            self.setItem(row, 0, header_item)
            row += 1
            # Sort items: mouse buttons first, then by keyboard order, then others
            def item_key(item):
                k = normalize_key_label(item[0])
                key_display = item[1].get("Key") or item[1].get("hotkey") or item[1].get("Hotkey") or item[0]
                key_str = str(key_display).lower()
                # Mouse buttons first
                if key_str.startswith("left mouse"):
                    return (0, 0)
                if key_str.startswith("right mouse"):
                    return (0, 1)
                if key_str.startswith("middle mouse"):
                    return (0, 2)
                # Keyboard order next
                try:
                    return (1, key_order.index(k))
                except ValueError:
                    return (2, hash(k))  # non-physical keys go last
            items_sorted = sorted(items, key=item_key)
            for key, info in items_sorted:
                print(f"[DEBUG] Legend row: key='{key}', info='{info.get('info','')}', category='{info.get('category','')}', color='{info.get('color','')}'")
                self.insertRow(row)
                key_id = info.get("Key") or info.get("hotkey") or info.get("Hotkey") or key
                try:
                    from __main__ import get_key_id
                except ImportError:
                    def get_key_id(x): return str(x)
                key_display = get_key_id(key_id) if isinstance(key_id, int) or (isinstance(key_id, str) and key_id.isdigit()) else str(key_id)
                # Abbreviate long key names for display
                display_key = key_display
                if key_display.lower().startswith("middle mouse"):
                    display_key = "MMB"
                elif key_display.lower().startswith("left mouse"):
                    display_key = "LMB"
                elif key_display.lower().startswith("right mouse"):
                    display_key = "RMB"
                else:
                    display_key = str(display_key).upper()
                # Do not elide key name, just use as-is
                key_item = QTableWidgetItem(display_key)
                name_item = QTableWidgetItem(info.get("info", ""))
                # Make key column bold and larger
                key_font = QFont(self.font())
                key_font.setPointSize(16)
                key_font.setBold(True)
                key_item.setFont(key_font)
                # Name column uses default font
                # Always show full text in tooltip, and allow copy
                tooltip = f"Key: {key_display}"
                if info.get("source"): tooltip += f"\nFile: {info['source']}"
                if info.get("category"): tooltip += f"\nCategory: {info['category']}"
                key_item.setToolTip(tooltip)
                name_item.setToolTip(tooltip)
                key_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                # Colorize background to match hotkey color (darkened)
                color = info.get("color", "#232325")
                # Blend with dark for readability
                def blend_with_dark(hex_color, alpha=0.6):
                    hex_color = hex_color.lstrip('#')
                    r = int(hex_color[0:2], 16)
                    g = int(hex_color[2:4], 16)
                    b = int(hex_color[4:6], 16)
                    dr, dg, db = 24, 26, 27  # #181a1b
                    r = int(r * alpha + dr * (1 - alpha))
                    g = int(g * alpha + dg * (1 - alpha))
                    b = int(b * alpha + db * (1 - alpha))
                    return f'rgb({r},{g},{b})'
                bg_color = blend_with_dark(color, 0.55)
                key_item.setBackground(QtGui.QColor(bg_color))
                name_item.setBackground(QtGui.QColor(bg_color))
                self.setItem(row, 0, key_item)
                self.setItem(row, 1, name_item)
                row += 1
        # Do NOT call resizeColumnsToContents, keep our fixed widths

class MainWindow(QMainWindow):
    def _on_client_folder_text_changed(self, text):
        # Debounce rapid typing/pasting, only scan after user pauses
        self._scan_debounce_timer.stop()
        self._scan_debounce_timer.timeout.connect(self.auto_scan_and_select_latest_profile)
        self._scan_debounce_timer.start()
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hotkey Parser for Ultima Online")
        self.setStyleSheet(DARK_QSS)
        main = QWidget()
        main_layout = QHBoxLayout(main)
        main.setMinimumWidth(1700)
        main.setMinimumHeight(700)

        # --- Far left: Profile list ---
        profile_list_widget = QWidget()
        profile_list_widget.setMinimumWidth(120)  # Reduced from 196
        profile_list_layout = QVBoxLayout(profile_list_widget)
        profile_list_layout.setContentsMargins(12, 8, 12, 8)
        profile_list_layout.setSpacing(6)
        profile_list_label = QLabel("Profiles:")
        profile_list_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        profile_list_layout.addWidget(profile_list_label)
        # Status label for profile area (for errors/info instead of popups)
        self.profile_status_label = QLabel("")
        self.profile_status_label.setStyleSheet("color: #ffb347; font-size: 12px; padding: 2px 0px;")
        self.profile_status_label.setWordWrap(True)
        profile_list_layout.addWidget(self.profile_status_label)
        self.profile_buttons_area = QScrollArea()
        self.profile_buttons_area.setWidgetResizable(True)
        self.profile_buttons_widget = QWidget()
        self.profile_buttons_layout = QVBoxLayout()
        self.profile_buttons_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.profile_buttons_widget.setLayout(self.profile_buttons_layout)
        self.profile_buttons_area.setWidget(self.profile_buttons_widget)
        profile_list_layout.addWidget(self.profile_buttons_area, 1)
        load_profiles_btn = QPushButton("Scan Profiles")
        load_profiles_btn.setMinimumWidth(120)
        load_profiles_btn.setMaximumWidth(220)
        load_profiles_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        load_profiles_btn.setStyleSheet("text-align: left; padding-left: 12px;")
        load_profiles_btn.clicked.connect(self.scan_and_display_profiles)
        profile_list_layout.addWidget(load_profiles_btn)

        # Load Profile button (browse to custom profile folder)
        load_profile_btn = QPushButton("Load Profile")
        load_profile_btn.setMinimumWidth(120)
        load_profile_btn.setMaximumWidth(220)
        load_profile_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        load_profile_btn.setStyleSheet("text-align: left; padding-left: 12px;")
        load_profile_btn.clicked.connect(self.load_custom_profile)
        profile_list_layout.addWidget(load_profile_btn)
        main_layout.addWidget(profile_list_widget, 1)  # Less stretch for left

        # --- Center: Controls, category manager, keyboard ---
        center_widget = QWidget()
        center_widget.setMinimumWidth(900)
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(6)
        # Client folder input
        folder_layout = QHBoxLayout()
        self.client_folder_input = QLineEdit()
        self.client_folder_input.setPlaceholderText("Ultima Online Client Folder (e.g. D:/ULTIMA/ClassicUO) the base folder contains Data\\Plugins")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_client_folder)
        folder_layout.addWidget(QLabel("Ultima Online Client Folder:"))
        folder_layout.addWidget(self.client_folder_input)
        folder_layout.addWidget(browse_btn)
        center_layout.addLayout(folder_layout)
        # Auto-scan and select most recent profile when folder is changed
        # Trigger scan on any text change, not just editingFinished
        self._scan_debounce_timer = QTimer(self)
        self._scan_debounce_timer.setSingleShot(True)
        self._scan_debounce_timer.setInterval(400)  # ms, adjust as needed
        self.client_folder_input.textChanged.connect(self._on_client_folder_text_changed)
        self.client_folder_input.editingFinished.connect(self.auto_scan_and_select_latest_profile)
        # Keyboard widget
        self.keyboard = KeyboardWidget()
        center_layout.addWidget(self.keyboard, 1)
        # --- Lower section: JSON buttons (left) and categories (right) ---
        lower_section = QHBoxLayout()
        # Left: JSON buttons
        json_buttons_layout = QVBoxLayout()
        load_btn = QPushButton("Load Selected Hotkeys")
        load_btn.clicked.connect(self.load_selected_hotkeys)
        json_buttons_layout.addWidget(load_btn)
        export_btn = QPushButton("Export Combined JSON")
        export_btn.clicked.connect(self.export_combined_json)
        json_buttons_layout.addWidget(export_btn)
        load_combined_btn = QPushButton("Load Combined JSON")
        load_combined_btn.clicked.connect(self.load_combined_json)
        json_buttons_layout.addWidget(load_combined_btn)
        json_buttons_layout.addStretch(1)
        # Right: Category manager
        categories_layout = QVBoxLayout()
        categories_label = QLabel("Categories:")
        categories_layout.addWidget(categories_label)
        self.categories = {"HOTKEYS": "#2c6667", "SCRIPTING": "#496e9e"}  # blueish lighter teal, noble muted blue
        self.category_manager = CategoryManagerWidget(self.categories, on_update=self.update_categories)
        categories_layout.addWidget(self.category_manager)
        categories_layout.addStretch(1)
        # Add both to lower section
        lower_section.addLayout(json_buttons_layout, 1)
        lower_section.addLayout(categories_layout, 1)
        center_layout.addLayout(lower_section)
        center_widget.setLayout(center_layout)
        main_layout.addWidget(center_widget, 6)  # More stretch for center

        # --- Far right: Hotkey legend ---
        self.legend_list = HotkeyLegendList()
        self.legend_list.setMinimumWidth(120)  # Reduced from 238
        main_layout.addWidget(self.legend_list, 1)  # Less stretch for right

        main.setLayout(main_layout)
        self.setCentralWidget(main)

    def update_categories(self, categories):
        self.categories = categories
        # Update color for each hotkey based on new category colors
        if hasattr(self, 'hotkey_map') and self.hotkey_map:
            for key, info in self.hotkey_map.items():
                cat = info.get('category')
                if cat and cat in self.categories:
                    info['color'] = self.categories[cat]
            # Redraw keyboard and legend with updated colors
            self.keyboard.set_hotkeys(self.hotkey_map)
            self.legend_list.set_hotkeys(self.hotkey_map)

    def load_custom_profile(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Profile Folder")
        if not folder:
            return
        hotkeys_file = os.path.join(folder, "RazorEnhanced.settings.HOTKEYS")
        scripting_file = os.path.join(folder, "RazorEnhanced.settings.SCRIPTING")
        if not (os.path.isfile(hotkeys_file) or os.path.isfile(scripting_file)):
            self.profile_status_label.setText("No RazorEnhanced.settings.HOTKEYS or SCRIPTING file found in this folder.")
            return
        profile_name = f"Custom Profile: {os.path.basename(folder)}"
        # Add to profile_buttons_layout
        btn = QPushButton(profile_name)
        btn.setMinimumWidth(120)
        btn.setMaximumWidth(220)
        btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        btn.setStyleSheet("text-align: left; padding-left: 12px;")
        btn.clicked.connect(lambda: self.load_profile_hotkeys(None, folder, custom=True))
        self.profile_buttons_layout.addWidget(btn)
        # Optionally, immediately load
        self.load_profile_hotkeys(None, folder, custom=True)

    def browse_client_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Ultima Online Client Folder")
        if folder:
            self.client_folder_input.setText(folder)

    def scan_profiles(self):
        base_folder = self.client_folder_input.text().strip()
        self.profile_status_label.setText("")
        self.profile_table.setRowCount(0)
        if not base_folder or not os.path.isdir(base_folder):
            self.profile_status_label.setText("Please enter a valid Ultima Online client folder.")
            return
        plugins_dir = os.path.join(base_folder, "Data", "Plugins")
        if not os.path.isdir(plugins_dir):
            self.profile_status_label.setText(f"No Plugins folder found in {base_folder}")
            return
        for plugin in os.listdir(plugins_dir):
            plugin_path = os.path.join(plugins_dir, plugin)
            profiles_dir = os.path.join(plugin_path, "Profiles")
            if not os.path.isdir(profiles_dir):
                continue
            for profile in os.listdir(profiles_dir):
                profile_path = os.path.join(profiles_dir, profile)
                hotkeys_file = os.path.join(profile_path, "RazorEnhanced.settings.HOTKEYS")
                scripting_file = os.path.join(profile_path, "RazorEnhanced.settings.SCRIPTING")
                row = self.profile_table.rowCount()
                self.profile_table.insertRow(row)
                self.profile_table.setItem(row, 0, QTableWidgetItem(profile))
                # HOTKEYS checkbox
                hotkeys_cb = QCheckBox()
                hotkeys_cb.setChecked(os.path.isfile(hotkeys_file))
                self.profile_table.setCellWidget(row, 1, hotkeys_cb)
                # SCRIPTING checkbox
                scripting_cb = QCheckBox()
                scripting_cb.setChecked(os.path.isfile(scripting_file))
                self.profile_table.setCellWidget(row, 2, scripting_cb)

    def load_selected_hotkeys(self):
        # Deprecated: replaced by profile buttons. Kept for compatibility.
        pass

    def scan_and_display_profiles(self):
        self.clear_profile_buttons()
        self.profile_status_label.setText("")
        base_folder = self.client_folder_input.text().strip()
        if not base_folder or not os.path.isdir(base_folder):
            self.profile_status_label.setText("Please enter a valid Ultima Online client folder.")
            return
        plugins_dir = os.path.join(base_folder, "Data", "Plugins")
        if not os.path.isdir(plugins_dir):
            self.profile_status_label.setText(f"No Plugins folder found in {base_folder}")
            return
        found_any = False
        from functools import partial
        from PyQt5.QtWidgets import QLabel
        for plugin in sorted(os.listdir(plugins_dir)):
            plugin_path = os.path.join(plugins_dir, plugin)
            profiles_dir = os.path.join(plugin_path, "Profiles")
            if not os.path.isdir(profiles_dir):
                continue
            # Gather valid profiles for this plugin
            valid_profiles = []
            for profile in sorted(os.listdir(profiles_dir)):
                profile_path = os.path.join(profiles_dir, profile)
                if not os.path.isdir(profile_path):
                    continue
                hotkeys_file = os.path.join(profile_path, "RazorEnhanced.settings.HOTKEYS")
                scripting_file = os.path.join(profile_path, "RazorEnhanced.settings.SCRIPTING")
                if os.path.isfile(hotkeys_file) or os.path.isfile(scripting_file):
                    valid_profiles.append(profile)
            if valid_profiles:
                # Add heading for plugin/version
                self.profile_buttons_layout.addWidget(QLabel(f"<b>{plugin}</b>"))
                for profile in valid_profiles:
                    btn = QPushButton(profile)
                    btn.clicked.connect(partial(self.load_profile_hotkeys, plugin, profile))
                    self.profile_buttons_layout.addWidget(btn)
                    found_any = True
        if not found_any:
            self.profile_status_label.setText("No valid profiles found.")

    def clear_profile_buttons(self):
        while self.profile_buttons_layout.count():
            child = self.profile_buttons_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def auto_scan_and_select_latest_profile(self):
        # Scan for profiles and select the most recently modified one
        self.scan_and_display_profiles()
        base_folder = self.client_folder_input.text().strip()
        plugins_dir = os.path.join(base_folder, "Data", "Plugins")
        latest_profile = None
        latest_time = None
        latest_plugin = None
        if not os.path.isdir(plugins_dir):
            self.profile_status_label.setText(f"No Plugins folder found in {base_folder}")
            return
        for plugin in sorted(os.listdir(plugins_dir)):
            plugin_path = os.path.join(plugins_dir, plugin)
            profiles_dir = os.path.join(plugin_path, "Profiles")
            if not os.path.isdir(profiles_dir):
                continue
            for profile in os.listdir(profiles_dir):
                profile_path = os.path.join(profiles_dir, profile)
                if not os.path.isdir(profile_path):
                    continue
                mtime = os.path.getmtime(profile_path)
                if latest_time is None or mtime > latest_time:
                    latest_time = mtime
                    latest_profile = profile
                    latest_plugin = plugin
        if latest_plugin and latest_profile:
            self.load_profile_hotkeys(latest_plugin, latest_profile)

    def load_profile_hotkeys(self, plugin, profile, custom=False):
        '''
        Loads hotkeys from the given profile. If custom=True, 'profile' is a folder path.
        '''
        if custom:
            folder = profile
            hotkeys_file = os.path.join(folder, "RazorEnhanced.settings.HOTKEYS")
            scripting_file = os.path.join(folder, "RazorEnhanced.settings.SCRIPTING")
            hotkey_map = {}
            if os.path.isfile(hotkeys_file):
                self._parse_and_add_hotkeys(hotkeys_file, hotkey_map, "HOTKEYS", self.categories)
            if os.path.isfile(scripting_file):
                self._parse_and_add_hotkeys(scripting_file, hotkey_map, "SCRIPTING", self.categories)
            self.hotkey_map = hotkey_map
            self.keyboard.set_hotkeys(self.hotkey_map)
            self.legend_list.set_hotkeys(self.hotkey_map)
            return
        # Original implementation follows

        import json
        self.hotkey_map = {}
        base_folder = self.client_folder_input.text().strip()
        plugins_dir = os.path.join(base_folder, "Data", "Plugins")
        plugin_path = os.path.join(plugins_dir, plugin)
        profiles_dir = os.path.join(plugin_path, "Profiles")
        profile_path = os.path.join(profiles_dir, profile)
        categories = self.categories
        hotkeys_file = os.path.join(profile_path, "RazorEnhanced.settings.HOTKEYS")
        scripting_file = os.path.join(profile_path, "RazorEnhanced.settings.SCRIPTING")
        found_any = False
        if os.path.isfile(hotkeys_file):
            self._parse_and_add_hotkeys(hotkeys_file, self.hotkey_map, "HOTKEYS", categories)
            found_any = True
        if os.path.isfile(scripting_file):
            self._parse_and_add_hotkeys(scripting_file, self.hotkey_map, "SCRIPTING", categories)
            found_any = True
        self.keyboard.set_hotkeys(self.hotkey_map)
        self.legend_list.set_hotkeys(self.hotkey_map)
        if not found_any:
            self.profile_status_label.setText(f"No hotkeys found in {plugin}/{profile}.")

    def export_combined_json(self):
        import json
        if not hasattr(self, 'hotkey_map') or not self.hotkey_map:
            self.profile_status_label.setText("No hotkeys loaded to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Combined Hotkeys", "combined_hotkeys.json", "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.hotkey_map, f, indent=4)
            self.profile_status_label.setText(f"Combined hotkeys exported to {path}")
        except Exception as e:
            self.profile_status_label.setText(f"Failed to export: {e}")

    def load_combined_json(self):
        import json
        path, _ = QFileDialog.getOpenFileName(self, "Load Combined Hotkeys", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                hotkey_map = json.load(f)
            self.hotkey_map = hotkey_map
            self.keyboard.set_hotkeys(self.hotkey_map)
            self.legend_list.set_hotkeys(self.hotkey_map)
            self.profile_status_label.setText(f"Loaded {len(self.hotkey_map)} hotkeys from {path}")
        except Exception as e:
            self.profile_status_label.setText(f"Failed to load: {e}")

    def _parse_and_add_hotkeys(self, file_path, hotkey_map, default_category, categories):
        import json
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Try to handle both list of dicts and dicts
            if isinstance(data, dict):
                entries = list(data.values())
            else:
                entries = data
            for entry in entries:
                # Try to find a key field
                key_label = None
                for field in ("Key", "Hotkey", "key", "hotkey"):
                    if field in entry:
                        key_label = entry[field]
                        break
                if not key_label:
                    continue
                norm_label = normalize_key_label(key_label)
                # Category logic: allow entry to specify, else use default
                cat = entry.get("Category", None) or default_category
                color = categories.get(cat, "#ff5370")
                hotkey_map[norm_label] = {
                    "color": color,
                    "info": entry.get("Name", "") or entry.get("Filename", "") or "Hotkey",
                    "source": os.path.basename(file_path),
                    "category": cat
                }
        except Exception as e:
            print(f"Failed to parse {file_path}: {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Apply dark mode tooltip styling globally
    app.setStyleSheet("""
    QToolTip {
        background-color: #111;
        color: #fff;
        border: 1px solid #444;
        font-size: 12px;
        padding: 6px;
        border-radius: 6px;
    }
    """)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
