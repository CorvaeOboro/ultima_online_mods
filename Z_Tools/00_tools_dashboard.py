"""
ULTIMA ONLINE MODS - Python Tools Dashboard
Visual dashboard for reviewing and managing Python tool metadata.

Features:
- View all tools in sortable/filterable table
- Edit frontmatter metadata (TOOLSGROUP::, STATUS::, VERSION::, etc.)
- Filter by toolsgroup, status, missing fields
- Launch tools directly from dashboard
- Open tool files in editor
- Export comprehensive reports

Metadata Format (in tool docstrings):

TOOLSGROUP::DEV
SORTGROUP::9
SORTPRIORITY::93
STATUS::stable
VERSION::20251207
"""

import os
import sys
import re
import subprocess
import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Dark mode color scheme
COLORS = {
    'bg_dark': '#1a1a1a',
    'bg_medium': '#2d2d2d',
    'bg_light': '#3a3a3a',
    'bg_black': '#000000',
    'fg_text': '#ffffff',
    'fg_dim': '#b0b0b0',
    'accent_blue': '#4a7ba7',
    'accent_blue_muted': '#3a5a6a',
    'accent_green': '#5a8a5a',
    'accent_red': '#a75a5a',
    'accent_yellow': '#a79a5a',
    'accent_purple': '#8a5a8a',
    'border': '#404040',
}

class ToolMetadata:
    """Represents metadata for a single Python tool."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.metadata: Dict[str, str] = {}
        self.docstring = ""
        self.description = ""
        self.issues: List[str] = []
        
        self.parse_file()
    
    def parse_file(self):
        """Parse the Python file to extract metadata from docstring."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract docstring (first triple-quoted string)
            docstring_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
            if docstring_match:
                self.docstring = docstring_match.group(1).strip()
                
                # Extract description (first line or lines before metadata)
                lines = self.docstring.split('\n')
                desc_lines = []
                for line in lines:
                    if '::' in line and line.strip().split('::')[0].isupper():
                        break
                    desc_lines.append(line)
                self.description = '\n'.join(desc_lines).strip()
                
                # Extract metadata variables (KEY::value format)
                metadata_pattern = r'^([A-Z_]+)::\s*(.+)$'
                for line in self.docstring.split('\n'):
                    match = re.match(metadata_pattern, line.strip())
                    if match:
                        key = match.group(1).strip()
                        value = match.group(2).strip()
                        self.metadata[key] = value
            
            # Validate metadata
            self.validate()
            
        except Exception as e:
            self.issues.append(f"Failed to parse file: {str(e)}")
    
    def validate(self):
        """Validate metadata and add issues if problems found."""
        # Check for recommended fields
        if 'TOOLSGROUP' not in self.metadata:
            self.issues.append("Missing TOOLSGROUP")
        
        if 'VERSION' not in self.metadata:
            self.issues.append("Missing VERSION")
        
        if not self.description:
            self.issues.append("Missing description")
    
    def save_metadata(self, new_metadata: Dict[str, str], new_description: str):
        """Save updated metadata back to the file."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find and replace docstring
            docstring_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
            if docstring_match:
                old_docstring = docstring_match.group(0)
                
                # Build new docstring
                new_lines = [new_description]
                new_lines.append("")
                
                for key, value in sorted(new_metadata.items()):
                    if value:  # Only include non-empty values
                        new_lines.append(f"{key}::{value}")
                
                new_docstring = '"""\n' + '\n'.join(new_lines) + '\n"""'
                
                # Replace in content
                new_content = content.replace(old_docstring, new_docstring, 1)
                
                # Write back
                with open(self.file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                return True
            else:
                return False
                
        except Exception as e:
            # Error will be shown in status bar by caller
            return False


class ToolsDashboard:
    """Main dashboard application."""
    
    def __init__(self, root, tools_dir: str):
        self.root = root
        self.tools_dir = tools_dir
        self.tools: List[ToolMetadata] = []
        self.filtered_tools: List[ToolMetadata] = []
        self.selected_tool: Optional[ToolMetadata] = None
        self.sort_column = None
        self.sort_reverse = False
        
        self.setup_ui()
        self.load_tools()
    
    def apply_dark_theme(self):
        """Apply dark mode theme to the application."""
        self.root.configure(bg=COLORS['bg_dark'])
        
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure ttk styles
        style.configure('.',
                       background=COLORS['bg_medium'],
                       foreground=COLORS['fg_text'],
                       fieldbackground=COLORS['bg_light'],
                       bordercolor=COLORS['border'],
                       darkcolor=COLORS['bg_dark'],
                       lightcolor=COLORS['bg_light'])
        
        # Treeview
        style.configure('Treeview',
                       background=COLORS['bg_medium'],
                       foreground=COLORS['fg_text'],
                       fieldbackground=COLORS['bg_medium'],
                       borderwidth=0)
        style.configure('Treeview.Heading',
                       background=COLORS['bg_dark'],
                       foreground=COLORS['fg_text'],
                       relief='flat')
        style.map('Treeview.Heading',
                 background=[('active', COLORS['bg_light'])])
        
        # Buttons
        style.configure('TButton',
                       background=COLORS['accent_blue'],
                       foreground=COLORS['fg_text'],
                       borderwidth=1,
                       relief='flat',
                       padding=6)
        style.map('TButton',
                 background=[('active', COLORS['bg_light'])])
        
        # Combobox
        style.configure('TCombobox',
                       fieldbackground=COLORS['bg_black'],
                       background=COLORS['bg_black'],
                       foreground=COLORS['fg_text'],
                       arrowcolor=COLORS['fg_text'],
                       borderwidth=1,
                       relief='flat',
                       selectbackground=COLORS['accent_blue'],
                       selectforeground=COLORS['fg_text'])
        style.map('TCombobox',
                 fieldbackground=[('readonly', COLORS['bg_black'])],
                 selectbackground=[('readonly', COLORS['bg_black'])],
                 selectforeground=[('readonly', COLORS['fg_text'])])
        
        # Configure the dropdown listbox (popup)
        self.root.option_add('*TCombobox*Listbox.background', COLORS['bg_black'])
        self.root.option_add('*TCombobox*Listbox.foreground', COLORS['fg_text'])
        self.root.option_add('*TCombobox*Listbox.selectBackground', COLORS['accent_blue'])
        self.root.option_add('*TCombobox*Listbox.selectForeground', COLORS['fg_text'])
        
        # Scrollbar
        style.configure('Vertical.TScrollbar',
                       background=COLORS['accent_blue_muted'],
                       troughcolor=COLORS['bg_black'],
                       borderwidth=0)
        
        # Labels
        style.configure('TLabel',
                       background=COLORS['bg_medium'],
                       foreground=COLORS['fg_text'])
        
        # Frame
        style.configure('TFrame',
                       background=COLORS['bg_medium'])
    
    def setup_ui(self):
        """Setup the user interface."""
        self.root.title("UO Mods - Tools Dashboard")
        
        # Window size and position
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = int(screen_width * 0.9)
        window_height = int(screen_height * 0.9)
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Apply dark theme
        self.apply_dark_theme()
        
        # Main container
        main_frame = tk.Frame(self.root, bg=COLORS['bg_dark'], padx=10, pady=10)
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Top toolbar
        self.create_toolbar(main_frame)
        
        # Main content (split pane)
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Left: Tool list (60%)
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=3)
        self.create_tool_list(left_frame)
        
        # Right: Details/Editor (40%)
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        self.create_details_panel(right_frame)
        
        # Bottom status bar
        self.create_status_bar(main_frame)
    
    def create_toolbar(self, parent):
        """Create top toolbar with filters and actions."""
        toolbar = ttk.Frame(parent)
        toolbar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Filters
        ttk.Label(toolbar, text="Filter:").pack(side=tk.LEFT, padx=5)
        
        # Toolsgroup filter
        ttk.Label(toolbar, text="Group:").pack(side=tk.LEFT)
        self.group_filter = ttk.Combobox(toolbar, width=12, state='readonly')
        self.group_filter['values'] = ['All']
        self.group_filter.current(0)
        self.group_filter.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        self.group_filter.pack(side=tk.LEFT, padx=5)
        
        # Status filter
        ttk.Label(toolbar, text="Status:").pack(side=tk.LEFT, padx=(10, 0))
        self.status_filter = ttk.Combobox(toolbar, width=12, state='readonly')
        self.status_filter['values'] = ['All', 'wip', 'stable', 'untested', 'Missing']
        self.status_filter.current(0)
        self.status_filter.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        self.status_filter.pack(side=tk.LEFT, padx=5)
        
        # Issues filter
        self.show_issues_only = tk.BooleanVar(value=False)
        ttk.Checkbutton(toolbar, text="Issues Only", variable=self.show_issues_only,
                       command=self.apply_filters).pack(side=tk.LEFT, padx=10)
        
        # Actions
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        ttk.Button(toolbar, text="Sort by Priorities", command=self.sort_by_priorities).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Refresh", command=self.load_tools).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Run Tool", command=self.run_selected_tool).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Open in Editor", command=self.open_in_editor).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Export Report", command=self.export_report).pack(side=tk.LEFT)
    
    def create_tool_list(self, parent):
        """Create tool list with tree view."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        
        # Header
        header = ttk.Frame(parent)
        header.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        ttk.Label(header, text="Python Tools", font=('TkDefaultFont', 10, 'bold')).pack(side=tk.LEFT)
        self.tool_count_label = ttk.Label(header, text="(0)")
        self.tool_count_label.pack(side=tk.LEFT, padx=5)
        
        # Tree view
        tree_frame = ttk.Frame(parent)
        tree_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Tree
        self.tree = ttk.Treeview(tree_frame,
                                 columns=('name', 'group', 'status', 'version', 'sortgroup', 'sortpriority', 'issues'),
                                 show='headings',
                                 yscrollcommand=vsb.set,
                                 xscrollcommand=hsb.set)
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Configure columns
        self.tree.column('name', width=250, minwidth=180, stretch=True)
        self.tree.column('group', width=90, minwidth=70, stretch=False)
        self.tree.column('status', width=80, minwidth=60, stretch=False)
        self.tree.column('version', width=80, minwidth=60, stretch=False)
        self.tree.column('sortgroup', width=90, minwidth=70, stretch=False)
        self.tree.column('sortpriority', width=70, minwidth=50, stretch=False)
        self.tree.column('issues', width=60, minwidth=50, stretch=False)
        
        self.tree.heading('name', text='Tool Name', command=lambda: self.sort_by('name'))
        self.tree.heading('group', text='Group', command=lambda: self.sort_by('group'))
        self.tree.heading('status', text='Status', command=lambda: self.sort_by('status'))
        self.tree.heading('version', text='Version', command=lambda: self.sort_by('version'))
        self.tree.heading('sortgroup', text='SortGroup', command=lambda: self.sort_by('sortgroup'))
        self.tree.heading('sortpriority', text='Priority', command=lambda: self.sort_by('sortpriority'))
        self.tree.heading('issues', text='Issues', command=lambda: self.sort_by('issues'))
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Bind selection and double-click
        self.tree.bind('<<TreeviewSelect>>', self.on_tool_select)
        self.tree.bind('<Double-Button-1>', lambda e: self.run_selected_tool())
        
        # Tags for coloring
        self.tree.tag_configure('error', background=COLORS['accent_red'])
        self.tree.tag_configure('warning', background=COLORS['accent_yellow'])
        self.tree.tag_configure('ok', background=COLORS['accent_green'])
    
    def create_details_panel(self, parent):
        """Create details/editor panel."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        
        # Header with Save button
        header = ttk.Frame(parent)
        header.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        header.columnconfigure(1, weight=1)
        
        ttk.Label(header, text="Tool Details & Editor", font=('TkDefaultFont', 10, 'bold')).grid(row=0, column=0, sticky=tk.W)
        
        # File path label
        self.file_path_label = ttk.Label(header, text="", font=('TkDefaultFont', 8))
        self.file_path_label.grid(row=0, column=1, sticky=tk.W, padx=(15, 0))
        
        # Save button
        ttk.Button(header, text="Save Changes", command=self.save_metadata).grid(row=0, column=2, sticky=tk.E, padx=(10, 0))
        
        # Single scrollable frame for all content
        canvas = tk.Canvas(parent, bg=COLORS['bg_medium'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        # Add all content sections to the scrollable frame
        self.create_metadata_section()
        self.create_issues_section()
        self.create_docstring_section()
    
    def create_metadata_section(self):
        """Create metadata editor section."""
        frame = ttk.Frame(self.scrollable_frame, padding=10)
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # Description (multi-line)
        ttk.Label(frame, text="Description:").grid(row=row, column=0, sticky=(tk.W, tk.N), pady=2)
        self.desc_widget = scrolledtext.ScrolledText(frame, height=6, wrap=tk.WORD,
                                                     bg=COLORS['bg_light'],
                                                     fg=COLORS['fg_text'],
                                                     insertbackground=COLORS['fg_text'])
        self.desc_widget.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        row += 1
        
        # Separator
        ttk.Separator(frame, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        row += 1
        
        # Metadata fields
        self.metadata_widgets = {}
        
        # Common fields
        fields = [
            ('TOOLSGROUP', 'Tool Group', 'entry', None),
            ('STATUS', 'Status', 'entry', None),
            ('VERSION', 'Version', 'entry', None),
            ('SORTPRIORITY', 'Sort Priority', 'entry', None),
            ('SORTGROUP', 'Sort Group', 'entry', None),
        ]
        
        for field, label, widget_type, values in fields:
            ttk.Label(frame, text=f"{label}:").grid(row=row, column=0, sticky=tk.W, pady=2)
            
            if widget_type == 'combo':
                widget = ttk.Combobox(frame, state='readonly' if values else 'normal')
                if values:
                    widget['values'] = values
            else:
                widget = ttk.Entry(frame)
            
            widget.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
            self.metadata_widgets[field] = widget
            row += 1
        
        # Additional custom fields
        ttk.Separator(frame, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        row += 1
        
        ttk.Label(frame, text="Custom Fields:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(5, 2))
        row += 1
        
        self.custom_fields_text = scrolledtext.ScrolledText(frame, height=8, wrap=tk.WORD,
                                                            bg=COLORS['bg_light'],
                                                            fg=COLORS['fg_text'],
                                                            insertbackground=COLORS['fg_text'])
        self.custom_fields_text.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        
        ttk.Label(frame, text="Format: KEY::value (one per line)", 
                 font=('TkDefaultFont', 8)).grid(row=row+1, column=0, columnspan=2, sticky=tk.W, pady=(2, 0))
    
    def create_issues_section(self):
        """Create issues display section."""
        frame = ttk.Frame(self.scrollable_frame, padding=10)
        frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        frame.columnconfigure(0, weight=1)
        
        # Section header
        ttk.Label(frame, text="Issues:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Issues text (smaller height since it's not in a tab)
        self.issues_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, state='disabled',
                                                     height=4,
                                                     bg=COLORS['bg_light'],
                                                     fg=COLORS['fg_text'])
        self.issues_text.grid(row=1, column=0, sticky=(tk.W, tk.E))
    
    def create_docstring_section(self):
        """Create full docstring display section."""
        frame = ttk.Frame(self.scrollable_frame, padding=10)
        frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        frame.columnconfigure(0, weight=1)
        
        # Section header
        ttk.Label(frame, text="Full Docstring:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Docstring text (smaller height since it's not in a tab)
        self.docstring_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, state='disabled',
                                                        height=8,
                                                        font=('Courier', 9),
                                                        bg=COLORS['bg_light'],
                                                        fg=COLORS['fg_text'])
        self.docstring_text.grid(row=1, column=0, sticky=(tk.W, tk.E))
    
    def create_status_bar(self, parent):
        """Create bottom status bar."""
        self.status_bar = ttk.Label(parent, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
    
    def load_tools(self):
        """Load all Python tools from directory."""
        self.status_bar.config(text="Loading tools...")
        self.root.update()
        
        self.tools = []
        
        # Scan for .py files in tools directory
        for file_name in os.listdir(self.tools_dir):
            if file_name.endswith('.py') and not file_name.startswith('__'):
                file_path = os.path.join(self.tools_dir, file_name)
                if os.path.isfile(file_path):
                    tool = ToolMetadata(file_path)
                    self.tools.append(tool)
        
        # Update group filter
        groups = set()
        for tool in self.tools:
            if 'TOOLSGROUP' in tool.metadata:
                groups.add(tool.metadata['TOOLSGROUP'])
        self.group_filter['values'] = ['All'] + sorted(groups)
        
        # Update status filter
        statuses = set()
        for tool in self.tools:
            if 'STATUS' in tool.metadata:
                statuses.add(tool.metadata['STATUS'])
        self.status_filter['values'] = ['All'] + sorted(statuses) + ['Missing']
        
        self.apply_filters()
        self.status_bar.config(text=f"Loaded {len(self.tools)} tools")
    
    def apply_filters(self):
        """Apply current filters to tool list."""
        self.filtered_tools = []
        
        group_filter = self.group_filter.get()
        status_filter = self.status_filter.get()
        issues_only = self.show_issues_only.get()
        
        for tool in self.tools:
            # Group filter
            if group_filter != 'All':
                if tool.metadata.get('TOOLSGROUP') != group_filter:
                    continue
            
            # Status filter
            if status_filter != 'All':
                if status_filter == 'Missing':
                    if 'STATUS' in tool.metadata:
                        continue
                elif tool.metadata.get('STATUS') != status_filter:
                    continue
            
            # Issues filter
            if issues_only and not tool.issues:
                continue
            
            self.filtered_tools.append(tool)
        
        self.populate_tree()
    
    def populate_tree(self):
        """Populate tree view with filtered tools."""
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Sort if needed
        if self.sort_column:
            self.filtered_tools.sort(
                key=lambda t: self.get_sort_key(t, self.sort_column),
                reverse=self.sort_reverse
            )
        
        # Add tools
        for tool in self.filtered_tools:
            name = tool.file_name
            group = tool.metadata.get('TOOLSGROUP', 'N/A')
            status = tool.metadata.get('STATUS', 'N/A')
            version = tool.metadata.get('VERSION', 'N/A')
            sortgroup = tool.metadata.get('SORTGROUP', '')
            sortpriority = tool.metadata.get('SORTPRIORITY', '')
            issue_count = len(tool.issues)
            
            # Determine tag
            if issue_count > 2:
                tag = 'error'
            elif issue_count > 0:
                tag = 'warning'
            else:
                tag = 'ok'
            
            self.tree.insert('', 'end', values=(name, group, status, version, sortgroup, sortpriority, issue_count),
                           tags=(tag,))
        
        self.tool_count_label.config(text=f"({len(self.filtered_tools)})")
    
    def get_sort_key(self, tool: ToolMetadata, column: str) -> str:
        """Get sort key for a tool based on column."""
        if column == 'name':
            return tool.file_name.lower()
        elif column == 'group':
            return tool.metadata.get('TOOLSGROUP', '').lower()
        elif column == 'status':
            return tool.metadata.get('STATUS', '').lower()
        elif column == 'version':
            return tool.metadata.get('VERSION', '')
        elif column == 'sortgroup':
            return tool.metadata.get('SORTGROUP', '').lower()
        elif column == 'sortpriority':
            # Sort numerically for priority
            priority_str = tool.metadata.get('SORTPRIORITY', '')
            try:
                return str(int(priority_str)).zfill(6) if priority_str else 'zzzzzz'
            except ValueError:
                return 'zzzzzz'
        elif column == 'issues':
            return str(len(tool.issues)).zfill(3)
        return ''
    
    def sort_by(self, column: str):
        """Sort tree by column."""
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        
        self.populate_tree()
    
    def sort_by_priorities(self):
        """Sort tools by SORTGROUP first, then by SORTPRIORITY (smallest numbers first)."""
        def priority_sort_key(tool: ToolMetadata) -> tuple:
            # Get SORTGROUP (empty string if not present, sorts first)
            sort_group = tool.metadata.get('SORTGROUP', '')
            
            # Get SORTPRIORITY and convert to int (use 999999 for missing/invalid values to sort last)
            sort_priority_str = tool.metadata.get('SORTPRIORITY', '')
            try:
                sort_priority = int(sort_priority_str) if sort_priority_str else 999999
            except ValueError:
                sort_priority = 999999
            
            # Return tuple for sorting: (SORTGROUP, SORTPRIORITY, filename as tiebreaker)
            return (sort_group.lower(), sort_priority, tool.file_name.lower())
        
        # Sort the filtered tools
        self.filtered_tools.sort(key=priority_sort_key)
        
        # Clear the column sort state
        self.sort_column = None
        self.sort_reverse = False
        
        # Repopulate tree with sorted tools
        self.populate_tree()
        
        # Update status bar
        self.status_bar.config(text="Sorted by priorities (SORTGROUP → SORTPRIORITY)")
    
    def on_tool_select(self, event):
        """Handle tool selection."""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        name = item['values'][0]
        
        # Find tool
        for tool in self.filtered_tools:
            if tool.file_name == name:
                self.selected_tool = tool
                self.display_tool_details(tool)
                break
    
    def display_tool_details(self, tool: ToolMetadata):
        """Display tool details in right panel."""
        # Update file path
        self.file_path_label.config(text=tool.file_name)
        
        # Description
        self.desc_widget.delete('1.0', tk.END)
        self.desc_widget.insert('1.0', tool.description)
        
        # Metadata fields
        for field, widget in self.metadata_widgets.items():
            value = tool.metadata.get(field, '')
            
            if isinstance(widget, ttk.Combobox):
                widget.set(value)
            else:
                widget.delete(0, tk.END)
                if value:
                    widget.insert(0, value)
        
        # Custom fields
        standard_fields = set(self.metadata_widgets.keys())
        custom_fields = {k: v for k, v in tool.metadata.items() if k not in standard_fields}
        
        self.custom_fields_text.delete('1.0', tk.END)
        if custom_fields:
            for field, value in sorted(custom_fields.items()):
                self.custom_fields_text.insert(tk.END, f"{field}::{value}\n")
        
        # Issues
        self.issues_text.config(state='normal')
        self.issues_text.delete('1.0', tk.END)
        
        if tool.issues:
            for issue in tool.issues:
                self.issues_text.insert(tk.END, f"• {issue}\n")
        else:
            self.issues_text.insert(tk.END, "No issues found.")
        
        self.issues_text.config(state='disabled')
        
        # Full docstring
        self.docstring_text.config(state='normal')
        self.docstring_text.delete('1.0', tk.END)
        self.docstring_text.insert('1.0', tool.docstring)
        self.docstring_text.config(state='disabled')
    
    def save_metadata(self):
        """Save metadata changes to file."""
        if not self.selected_tool:
            self.status_bar.config(text="⚠ No tool selected. Please select a tool first.")
            return
        
        # Gather metadata
        new_metadata = {}
        for field, widget in self.metadata_widgets.items():
            if isinstance(widget, ttk.Combobox):
                value = widget.get()
            else:
                value = widget.get()
            
            if value:
                new_metadata[field] = value
        
        # Parse custom fields
        custom_text = self.custom_fields_text.get('1.0', tk.END).strip()
        for line in custom_text.split('\n'):
            if '::' in line:
                parts = line.split('::', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key and value:
                        new_metadata[key] = value
        
        # Get description
        new_description = self.desc_widget.get('1.0', tk.END).strip()
        
        # Save
        if self.selected_tool.save_metadata(new_metadata, new_description):
            self.status_bar.config(text=f"✓ Metadata saved successfully: {self.selected_tool.file_name}")
            # Reload the tool
            self.selected_tool.parse_file()
            self.display_tool_details(self.selected_tool)
            self.populate_tree()
        else:
            self.status_bar.config(text=f"✗ Failed to save metadata: {self.selected_tool.file_name}")
    
    def run_selected_tool(self):
        """Run the selected tool."""
        if not self.selected_tool:
            self.status_bar.config(text="⚠ No tool selected. Please select a tool first.")
            return
        
        try:
            # Run in venv if it exists
            venv_python = os.path.join(self.tools_dir, 'venv', 'Scripts', 'python.exe')
            if os.path.exists(venv_python):
                python_exe = venv_python
            else:
                python_exe = 'python'
            
            subprocess.Popen([python_exe, self.selected_tool.file_path],
                           cwd=self.tools_dir,
                           creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
            
            self.status_bar.config(text=f"✓ Launched: {self.selected_tool.file_name}")
        except Exception as e:
            self.status_bar.config(text=f"✗ Failed to launch tool: {str(e)}")
    
    def open_in_editor(self):
        """Open selected tool in default editor."""
        if not self.selected_tool:
            self.status_bar.config(text="⚠ No tool selected. Please select a tool first.")
            return
        
        try:
            if os.name == 'nt':  # Windows
                os.startfile(self.selected_tool.file_path)
            else:  # Unix-like
                subprocess.call(['xdg-open', self.selected_tool.file_path])
            
            self.status_bar.config(text=f"✓ Opened in editor: {self.selected_tool.file_name}")
        except Exception as e:
            self.status_bar.config(text=f"✗ Failed to open file: {str(e)}")
    
    def export_report(self):
        """Export tools report to text file."""
        try:
            report_path = os.path.join(self.tools_dir, f'tools_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("ULTIMA ONLINE MODS - TOOLS REPORT\n")
                f.write("=" * 80 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Tools: {len(self.tools)}\n\n")
                
                # Summary by group
                groups = {}
                for tool in self.tools:
                    group = tool.metadata.get('TOOLSGROUP', 'Unknown')
                    groups[group] = groups.get(group, 0) + 1
                
                f.write("TOOLS BY GROUP:\n")
                for group, count in sorted(groups.items()):
                    f.write(f"  {group}: {count}\n")
                f.write("\n")
                
                # Tools with issues
                tools_with_issues = [t for t in self.tools if t.issues]
                f.write(f"TOOLS WITH ISSUES: {len(tools_with_issues)}\n")
                for tool in tools_with_issues:
                    f.write(f"\n{tool.file_name}:\n")
                    for issue in tool.issues:
                        f.write(f"  - {issue}\n")
                f.write("\n")
                
                # All tools detail
                f.write("=" * 80 + "\n")
                f.write("ALL TOOLS DETAIL:\n")
                f.write("=" * 80 + "\n\n")
                
                for tool in sorted(self.tools, key=lambda t: t.file_name):
                    f.write(f"{tool.file_name}\n")
                    f.write("-" * 80 + "\n")
                    f.write(f"Path: {tool.file_path}\n")
                    for key, value in sorted(tool.metadata.items()):
                        f.write(f"{key}: {value}\n")
                    if tool.description:
                        f.write(f"\nDescription:\n{tool.description}\n")
                    if tool.issues:
                        f.write(f"\nIssues:\n")
                        for issue in tool.issues:
                            f.write(f"  - {issue}\n")
                    f.write("\n\n")
            
            self.status_bar.config(text=f"✓ Report exported: {report_path}")
            
        except Exception as e:
            self.status_bar.config(text=f"✗ Failed to export report: {str(e)}")


def main():
    """Main entry point."""
    # Get tools directory (current directory)
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    
    root = tk.Tk()
    app = ToolsDashboard(root, tools_dir)
    root.mainloop()


if __name__ == '__main__':
    main()
