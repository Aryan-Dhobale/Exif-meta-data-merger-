import os
import sys
import json
import re
from datetime import datetime
import threading

# GUI imports
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk, ImageOps

# Attempting piexif import for native EXIF writing, with fallback to Pillow Exif API
PIEXIF_AVAILABLE = False
try:
    import piexif
    PIEXIF_AVAILABLE = True
except ImportError:
    PIEXIF_AVAILABLE = False

APP_TITLE = "EXIF Metadata Merger (Google Photos Takeout)"
APP_VERSION = "1.0.0"

# Modern Dark Theme Palette (Catppuccin / VSCode inspired)
COLOR_BG_DARK = "#181825"
COLOR_PANEL_BG = "#1e1e2e"
COLOR_SURFACE = "#313244"
COLOR_SURFACE_LIGHT = "#45475a"
COLOR_ACCENT = "#89b4fa"
COLOR_ACCENT_HOVER = "#b4befe"
COLOR_SUCCESS = "#a6e3a1"
COLOR_WARNING = "#f9e2af"
COLOR_DANGER = "#f38ba8"
COLOR_TEXT = "#cdd6f4"
COLOR_TEXT_MUTED = "#a6adc8"
COLOR_BORDER = "#45475a"

def deg_to_dms_rational(deg_float):
    """Convert decimal degrees to EXIF degrees, minutes, seconds rational tuple."""
    deg = int(abs(deg_float))
    min_float = (abs(deg_float) - deg) * 60
    minute = int(min_float)
    sec_float = (min_float - minute) * 60
    sec = int(sec_float * 10000)
    return ((deg, 1), (minute, 1), (sec, 10000))

def create_exif_dict_from_json(json_data):
    """
    Constructs a dictionary compatible with piexif from Google Photos JSON sidecar.
    Extracts DateTimeOriginal, GPS info, and Description/Title.
    """
    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    
    # 1. Process Date Taken
    timestamp = None
    if "photoTakenTime" in json_data and "timestamp" in json_data["photoTakenTime"]:
        try:
            timestamp = int(json_data["photoTakenTime"]["timestamp"])
        except ValueError:
            pass
    elif "creationTime" in json_data and "timestamp" in json_data["creationTime"]:
        try:
            timestamp = int(json_data["creationTime"]["timestamp"])
        except ValueError:
            pass

    if timestamp:
        dt = datetime.fromtimestamp(timestamp)
        date_str = dt.strftime("%Y:%m:%d %H:%M:%S")
        exif_dict["0th"][piexif.ImageIFD.DateTime] = date_str
        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_str
        exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_str

    # 2. Process Title / Description
    desc = json_data.get("description") or json_data.get("title", "")
    if desc:
        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = desc.encode('utf-8')

    # 3. Process Geo Location
    geo = json_data.get("geoDataExif") or json_data.get("geoData") or {}
    lat = geo.get("latitude")
    lon = geo.get("longitude")
    alt = geo.get("altitude")

    if lat is not None and lon is not None and (lat != 0.0 or lon != 0.0):
        lat_ref = 'N' if lat >= 0 else 'S'
        lon_ref = 'E' if lon >= 0 else 'W'
        
        exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = lat_ref
        exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = deg_to_dms_rational(lat)
        exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = lon_ref
        exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = deg_to_dms_rational(lon)
        
        if alt is not None:
            alt_ref = 1 if alt < 0 else 0
            exif_dict["GPS"][piexif.GPSIFD.GPSAltitudeRef] = alt_ref
            exif_dict["GPS"][piexif.GPSIFD.GPSAltitude] = (int(abs(alt) * 100), 100)

    return exif_dict, timestamp

def execute_merge(pair):
    """Writes EXIF metadata into the image header and updates OS filesystem timestamps."""
    if not pair.json_path or not pair.json_data:
        pair.status = "No JSON"
        return False

    image_path = pair.image_path
    json_data = pair.json_data

    try:
        timestamp = None

        # 1. Update EXIF using piexif if available, or Pillow native EXIF API
        if PIEXIF_AVAILABLE and image_path.lower().endswith(('.jpg', '.jpeg', '.tif', '.tiff')):
            exif_dict, timestamp = create_exif_dict_from_json(json_data)
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, image_path)
        else:
            # Fallback: Pillow EXIF manipulation & timestamp extraction
            if "photoTakenTime" in json_data and "timestamp" in json_data["photoTakenTime"]:
                timestamp = int(json_data["photoTakenTime"]["timestamp"])
            elif "creationTime" in json_data and "timestamp" in json_data["creationTime"]:
                timestamp = int(json_data["creationTime"]["timestamp"])

            with Image.open(image_path) as img:
                exif = img.getexif()
                if timestamp:
                    dt_formatted = datetime.fromtimestamp(timestamp).strftime("%Y:%m:%d %H:%M:%S")
                    exif[306] = dt_formatted      # DateTime
                    exif[36867] = dt_formatted    # DateTimeOriginal
                
                desc = json_data.get("description") or json_data.get("title")
                if desc:
                    exif[270] = desc              # ImageDescription
                
                # Save image back with updated EXIF
                img.save(image_path, exif=exif)

        # 2. Update File System Creation & Modification Timestamps (utime)
        if timestamp:
            os.utime(image_path, (timestamp, timestamp))

        pair.merged = True
        pair.status = "Successfully Merged"
        return True

    except Exception as e:
        pair.status = "Error Merging"
        pair.error_msg = str(e)
        return False

class ImagePairItem:
    """Data structure representing an image and its paired JSON sidecar file."""
    def __init__(self, image_path, json_path=None):
        self.image_path = image_path
        self.json_path = json_path
        self.filename = os.path.basename(image_path)
        self.status = "Matched" if json_path else "Unmatched Image"
        self.json_data = {}
        self.exif_summary = {}
        self.merged = False
        self.error_msg = ""
        
        if self.json_path and os.path.exists(self.json_path):
            try:
                with open(self.json_path, 'r', encoding='utf-8', errors='ignore') as f:
                    self.json_data = json.load(f)
            except Exception as e:
                self.status = "JSON Read Error"
                self.error_msg = str(e)

class PairMatcherEngine:
    """Scans directory and pairs image files with Google Takeout JSON sidecars using multi-strategy matching."""
    SUPPORTED_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff', '.heic'}

    @classmethod
    def scan_directory(cls, folder_path, callback_log=None):
        if not os.path.exists(folder_path):
            return []

        all_files = os.listdir(folder_path)
        image_files = []
        json_file_map = {}   # lower_filename -> real_filename
        json_title_map = {}  # lower_internal_title -> real_json_path

        # Step 1: Categorize files and index JSON sidecars by filename AND internal "title" tag
        for f in all_files:
            full_p = os.path.join(folder_path, f)
            if not os.path.isfile(full_p):
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext in cls.SUPPORTED_EXTS:
                image_files.append(full_p)
            elif ext == '.json':
                json_file_map[f.lower()] = f
                # Read internal "title" attribute for guaranteed Google Photos Takeout matching
                try:
                    with open(full_p, 'r', encoding='utf-8', errors='ignore') as jf:
                        data = json.load(jf)
                        if isinstance(data, dict):
                            title = data.get('title')
                            if title and isinstance(title, str):
                                json_title_map[title.lower().strip()] = full_p
                except Exception:
                    pass

        if callback_log:
            callback_log(f"Indexed {len(image_files)} images and {len(json_file_map)} JSON sidecars.")

        pairs = []

        # Step 2: Match each image file against JSON sidecars
        for img_path in image_files:
            img_name = os.path.basename(img_path)
            matched_json = cls._find_matching_json(folder_path, img_name, json_file_map, json_title_map)
            pairs.append(ImagePairItem(img_path, matched_json))

        return sorted(pairs, key=lambda x: x.filename.lower())

    @classmethod
    def _find_matching_json(cls, folder_path, img_name, json_file_map, json_title_map):
        img_name_lower = img_name.lower().strip()
        base_name, ext = os.path.splitext(img_name)
        base_name_lower = base_name.lower().strip()

        # Strategy 1: Check internal "title" tag inside JSON file (most reliable for Google Takeout)
        if img_name_lower in json_title_map:
            return json_title_map[img_name_lower]

        # Strategy 2: Case-insensitive exact name + .json (e.g., photo.jpg.json / photo.JPG.json)
        candidate1 = f"{img_name_lower}.json"
        if candidate1 in json_file_map:
            return os.path.join(folder_path, json_file_map[candidate1])

        # Strategy 3: Base name without image extension + .json (e.g., photo.json)
        candidate2 = f"{base_name_lower}.json"
        if candidate2 in json_file_map:
            return os.path.join(folder_path, json_file_map[candidate2])

        # Strategy 4: Handle index tag permutations (e.g., photo(1).jpg vs photo.jpg(1).json vs photo(1).json)
        match = re.search(r'^(.*?)(\(\d+\))?(\.[^.]+)$', img_name, re.IGNORECASE)
        if match:
            raw_base, index_tag, img_ext = match.groups()
            raw_base_lower = raw_base.lower()
            index_tag = (index_tag or "").lower()
            img_ext_lower = img_ext.lower()

            candidate3 = f"{raw_base_lower}{img_ext_lower}{index_tag}.json"
            if candidate3 in json_file_map:
                return os.path.join(folder_path, json_file_map[candidate3])

            candidate4 = f"{raw_base_lower}{index_tag}.json"
            if candidate4 in json_file_map:
                return os.path.join(folder_path, json_file_map[candidate4])

            candidate5 = f"{raw_base_lower}{img_ext_lower}.json{index_tag}"
            if candidate5 in json_file_map:
                return os.path.join(folder_path, json_file_map[candidate5])

            candidate6 = f"{raw_base_lower}.json{index_tag}"
            if candidate6 in json_file_map:
                return os.path.join(folder_path, json_file_map[candidate6])

        # Strategy 5: Edited photos (e.g., photo-edited.jpg -> photo.jpg.json)
        if "-edited" in base_name_lower:
            unedited_base = base_name_lower.replace("-edited", "")
            cand_edited1 = f"{unedited_base}{ext.lower()}.json"
            if cand_edited1 in json_file_map:
                return os.path.join(folder_path, json_file_map[cand_edited1])
            cand_edited2 = f"{unedited_base}.json"
            if cand_edited2 in json_file_map:
                return os.path.join(folder_path, json_file_map[cand_edited2])

        # Strategy 6: Truncated long filenames (Google Takeout caps JSON filenames to ~46-51 chars)
        if len(img_name) > 30:
            prefix = base_name_lower[:25]
            for j_lower, j_real in json_file_map.items():
                if j_lower.startswith(prefix):
                    return os.path.join(folder_path, j_real)

        # Strategy 7: URL / Special character unescaping (e.g., %20 to space, %23 to #)
        import urllib.parse
        unescaped_img = urllib.parse.unquote(img_name_lower)
        if unescaped_img != img_name_lower:
            candidate_un = f"{unescaped_img}.json"
            if candidate_un in json_file_map:
                return os.path.join(folder_path, json_file_map[candidate_un])

        return None

class ExifMergerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1200x780")
        self.minsize(1000, 650)
        self.configure(bg=COLOR_BG_DARK)

        # State Variables
        self.pairs = []
        self.selected_pair = None
        self.working_dir = ""
        self.is_processing = False

        # Apply Modern Dark Theme styling to TTK widgets
        self._setup_ttk_styles()

        # Build UI Structure
        self._build_top_bar()
        self._build_main_panes()
        self._build_bottom_bar()

        # Log system status
        self.log(f"{APP_TITLE} initialized.")
        if not PIEXIF_AVAILABLE:
            self.log("Note: 'piexif' library not installed. Standard JPEG metadata merging will use Pillow fallback. For full raw EXIF manipulation, install piexif (`pip install piexif`).", level="WARNING")

    def _setup_ttk_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        # Configure colors for standard widgets
        style.configure(".", background=COLOR_PANEL_BG, foreground=COLOR_TEXT, font=("Segoe UI", 10))

        # Frames
        style.configure("TFrame", background=COLOR_PANEL_BG)
        style.configure("Card.TFrame", background=COLOR_SURFACE, relief="flat")
        style.configure("DarkFrame.TFrame", background=COLOR_BG_DARK)

        # Buttons
        style.configure("TButton", background=COLOR_SURFACE, foreground=COLOR_TEXT, borderwidth=1, focuscolor="none", padding=6)
        style.map("TButton", background=[("active", COLOR_SURFACE_LIGHT), ("disabled", COLOR_SURFACE)])

        style.configure("Accent.TButton", background=COLOR_ACCENT, foreground="#11111b", font=("Segoe UI", 10, "bold"), padding=8)
        style.map("Accent.TButton", background=[("active", COLOR_ACCENT_HOVER), ("disabled", COLOR_SURFACE_LIGHT)])

        # LabelFrame
        style.configure("TLabelframe", background=COLOR_PANEL_BG, foreground=COLOR_ACCENT, bordercolor=COLOR_BORDER)
        style.configure("TLabelframe.Label", background=COLOR_PANEL_BG, foreground=COLOR_ACCENT, font=("Segoe UI", 10, "bold"))

        # Treeview (Data Table)
        style.configure("Treeview", background=COLOR_PANEL_BG, foreground=COLOR_TEXT, fieldbackground=COLOR_PANEL_BG, borderwidth=0, rowheight=28)
        style.map("Treeview", background=[("selected", COLOR_SURFACE_LIGHT)], foreground=[("selected", COLOR_ACCENT)])
        style.configure("Treeview.Heading", background=COLOR_SURFACE, foreground=COLOR_TEXT, font=("Segoe UI", 9, "bold"), borderwidth=1)

        # Progressbar
        style.configure("Horizontal.TProgressbar", background=COLOR_ACCENT, troughcolor=COLOR_SURFACE, borderwidth=0)

    def _build_top_bar(self):
        top_frame = ttk.Frame(self, padding=(15, 12, 15, 10), style="DarkFrame.TFrame")
        top_frame.pack(fill=tk.X, side=tk.TOP)

        # App Title & Subtitle
        title_box = ttk.Frame(top_frame, style="DarkFrame.TFrame")
        title_box.pack(side=tk.LEFT, fill=tk.Y)

        title_lbl = tk.Label(title_box, text="📷 EXIF Metadata Merger", font=("Segoe UI", 16, "bold"), fg=COLOR_TEXT, bg=COLOR_BG_DARK)
        title_lbl.pack(anchor=tk.W)
        sub_lbl = tk.Label(title_box, text="Google Photos Takeout JSON Sidecar Restorer", font=("Segoe UI", 9), fg=COLOR_TEXT_MUTED, bg=COLOR_BG_DARK)
        sub_lbl.pack(anchor=tk.W)

        # Folder Selection Actions
        btn_box = ttk.Frame(top_frame, style="DarkFrame.TFrame")
        btn_box.pack(side=tk.RIGHT, fill=tk.Y)

        self.dir_path_var = tk.StringVar(value="No folder selected")
        dir_display = tk.Label(btn_box, textvariable=self.dir_path_var, font=("Segoe UI", 9, "italic"), fg=COLOR_ACCENT, bg=COLOR_BG_DARK, width=40, anchor="e")
        dir_display.pack(side=tk.LEFT, padx=10)

        open_btn = ttk.Button(btn_box, text="📁 Open Takeout Folder", command=self._select_directory)
        open_btn.pack(side=tk.LEFT, padx=5)

        scan_btn = ttk.Button(btn_box, text="🔄 Rescan", command=self._scan_pairs)
        scan_btn.pack(side=tk.LEFT, padx=5)

    def _build_main_panes(self):
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        # ---------------- LEFT PANE: File Tree / Pair List ----------------
        left_frame = ttk.Frame(main_paned, padding=5)
        main_paned.add(left_frame, weight=4)

        # Filter / Header Bar
        list_header = ttk.Frame(left_frame)
        list_header.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(list_header, text="Scanned Image Files", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        
        self.filter_var = tk.StringVar(value="All")
        filter_combo = ttk.Combobox(list_header, textvariable=self.filter_var, values=["All", "Matched", "Unmatched", "Merged"], state="readonly", width=12)
        filter_combo.pack(side=tk.RIGHT)
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self._populate_tree())

        # Treeview Table
        tree_scroll = ttk.Scrollbar(left_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(left_frame, columns=("Status", "JSON"), show="tree headings", yscrollcommand=tree_scroll.set, selectmode="browse")
        tree_scroll.config(command=self.tree.yview)

        self.tree.heading("#0", text="Image Filename", anchor=tk.W)
        self.tree.heading("Status", text="Status", anchor=tk.CENTER)
        self.tree.heading("JSON", text="Sidecar JSON", anchor=tk.W)

        self.tree.column("#0", width=220, stretch=True)
        self.tree.column("Status", width=110, stretch=False, anchor=tk.CENTER)
        self.tree.column("JSON", width=200, stretch=True)

        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_item_select)

        # Config tag colors in list
        self.tree.tag_configure("matched", foreground=COLOR_TEXT)
        self.tree.tag_configure("unmatched", foreground=COLOR_WARNING)
        self.tree.tag_configure("merged", foreground=COLOR_SUCCESS)
        self.tree.tag_configure("error", foreground=COLOR_DANGER)

        # ---------------- RIGHT PANE: Side-by-Side Reviewer ----------------
        right_frame = ttk.Frame(main_paned, padding=5)
        main_paned.add(right_frame, weight=6)

        # Split Right Pane into Preview Top & Metadata Comparison Bottom
        right_paned = ttk.PanedWindow(right_frame, orient=tk.VERTICAL)
        right_paned.pack(fill=tk.BOTH, expand=True)

        # Top Right: Image Canvas Preview
        preview_box = ttk.LabelFrame(right_paned, text=" Image Preview ", padding=10)
        right_paned.add(preview_box, weight=5)

        self.canvas = tk.Canvas(preview_box, bg=COLOR_BG_DARK, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.preview_image_ref = None

        # Bottom Right: Dual Metadata Comparison Boxes
        meta_box = ttk.LabelFrame(right_paned, text=" Metadata Review & Comparison ", padding=10)
        right_paned.add(meta_box, weight=5)

        meta_grid = ttk.Frame(meta_box)
        meta_grid.pack(fill=tk.BOTH, expand=True)

        # Existing EXIF Card
        exif_card = ttk.Frame(meta_grid, style="Card.TFrame", padding=10)
        exif_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        ttk.Label(exif_card, text="Current Image EXIF", font=("Segoe UI", 10, "bold"), foreground=COLOR_ACCENT, background=COLOR_SURFACE).pack(anchor=tk.W)
        self.lbl_exif_date = ttk.Label(exif_card, text="Date Taken: --", background=COLOR_SURFACE)
        self.lbl_exif_date.pack(anchor=tk.W, pady=(5, 2))
        self.lbl_exif_gps = ttk.Label(exif_card, text="GPS: --", background=COLOR_SURFACE)
        self.lbl_exif_gps.pack(anchor=tk.W, pady=2)
        self.lbl_exif_desc = ttk.Label(exif_card, text="Description: --", background=COLOR_SURFACE, wraplength=250)
        self.lbl_exif_desc.pack(anchor=tk.W, pady=2)

        # Target JSON Sidecar Card
        json_card = ttk.Frame(meta_grid, style="Card.TFrame", padding=10)
        json_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        ttk.Label(json_card, text="Target Google JSON Sidecar", font=("Segoe UI", 10, "bold"), foreground=COLOR_SUCCESS, background=COLOR_SURFACE).pack(anchor=tk.W)
        self.lbl_json_date = ttk.Label(json_card, text="Taken Time: --", background=COLOR_SURFACE)
        self.lbl_json_date.pack(anchor=tk.W, pady=(5, 2))
        self.lbl_json_gps = ttk.Label(json_card, text="GPS: --", background=COLOR_SURFACE)
        self.lbl_json_gps.pack(anchor=tk.W, pady=2)
        self.lbl_json_desc = ttk.Label(json_card, text="Title/Desc: --", background=COLOR_SURFACE, wraplength=250)
        self.lbl_json_desc.pack(anchor=tk.W, pady=2)

    def _build_bottom_bar(self):
        bottom_frame = ttk.Frame(self, padding=(15, 5, 15, 10), style="DarkFrame.TFrame")
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # Operational Action Buttons
        action_bar = ttk.Frame(bottom_frame, style="DarkFrame.TFrame")
        action_bar.pack(fill=tk.X, pady=(0, 8))

        self.btn_merge_selected = ttk.Button(action_bar, text="Merge Selected Item", command=self._merge_selected)
        self.btn_merge_selected.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_merge_all = ttk.Button(action_bar, text="⚡ Merge All Matched Pairs", style="Accent.TButton", command=self._start_batch_merge)
        self.btn_merge_all.pack(side=tk.LEFT, padx=5)

        self.lbl_stats = tk.Label(action_bar, text="Total: 0 | Matched: 0 | Merged: 0", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT_MUTED, bg=COLOR_BG_DARK)
        self.lbl_stats.pack(side=tk.RIGHT, padx=5)

        # Progress Bar
        self.progress_bar = ttk.Progressbar(bottom_frame, orient=tk.HORIZONTAL, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))

        # Collapsible Scrollable Log Console
        log_frame = ttk.LabelFrame(bottom_frame, text=" Operational Log Console ", padding=5)
        log_frame.pack(fill=tk.X)

        self.log_widget = scrolledtext.ScrolledText(log_frame, height=4, font=("Consolas", 8), bg=COLOR_PANEL_BG, fg=COLOR_TEXT, insertbackground=COLOR_TEXT, relief="flat")
        self.log_widget.pack(fill=tk.BOTH, expand=True)

    def log(self, message, level="INFO"):
        """Logs message to bottom text console with timestamps."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = f"[{timestamp}] [{level}] "
        self.log_widget.insert(tk.END, f"{prefix}{message}\n")
        self.log_widget.see(tk.END)

    def _select_directory(self):
        chosen = filedialog.askdirectory(title="Select Google Photos Folder")
        if chosen:
            self.working_dir = chosen
            self.dir_path_var.set(chosen)
            self.log(f"Selected working directory: {chosen}")
            self._scan_pairs()

    def _scan_pairs(self):
        if not self.working_dir:
            messagebox.showwarning("No Folder Selected", "Please select a directory containing Google Photos images and JSON sidecars.")
            return

        self.log("Scanning directory for photo and metadata pairs...")
        self.pairs = PairMatcherEngine.scan_directory(self.working_dir, callback_log=self.log)
        self._populate_tree()
        self._update_stats()
        self.log(f"Scan complete. Found {len(self.pairs)} image files.")

    def _populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        filter_mode = self.filter_var.get()

        for item in self.pairs:
            # Apply filter selection
            if filter_mode == "Matched" and not (item.json_path and not item.merged):
                continue
            elif filter_mode == "Unmatched" and item.json_path is not None:
                continue
            elif filter_mode == "Merged" and not item.merged:
                continue

            json_name = os.path.basename(item.json_path) if item.json_path else "❌ Missing Sidecar"
            tag = "matched"
            if item.merged:
                tag = "merged"
            elif not item.json_path:
                tag = "unmatched"
            elif item.status.startswith("Error"):
                tag = "error"

            node_id = self.tree.insert("", tk.END, text=item.filename, values=(item.status, json_name), tags=(tag,))
            # Store item reference in item mapping
            self.tree.set(node_id, "Status", item.status)

    def _update_stats(self):
        total = len(self.pairs)
        matched = sum(1 for p in self.pairs if p.json_path)
        merged = sum(1 for p in self.pairs if p.merged)
        self.lbl_stats.config(text=f"Total Images: {total} | Matched Pairs: {matched} | Merged: {merged}")

    def _on_item_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return

        node_id = selected_items[0]
        filename = self.tree.item(node_id, "text")

        # Find pair object
        pair = next((p for p in self.pairs if p.filename == filename), None)
        if pair:
            self.selected_pair = pair
            self._render_side_by_side_preview(pair)

    def _render_side_by_side_preview(self, pair: ImagePairItem):
        # 1. Update Image Canvas Preview
        try:
            pil_img = Image.open(pair.image_path)
            # Auto-orient based on existing EXIF
            pil_img = ImageOps.exif_transpose(pil_img)

            # Fit thumbnail to canvas dimensions
            canvas_w = self.canvas.winfo_width() or 400
            canvas_h = self.canvas.winfo_height() or 250
            pil_img.thumbnail((canvas_w - 20, canvas_h - 20), Image.Resampling.LANCZOS)

            self.preview_image_ref = ImageTk.PhotoImage(pil_img)
            self.canvas.delete("all")
            self.canvas.create_image(canvas_w // 2, canvas_h // 2, image=self.preview_image_ref, anchor=tk.CENTER)
        except Exception as e:
            self.canvas.delete("all")
            self.canvas.create_text(150, 100, text=f"Preview Error:\n{str(e)}", fill=COLOR_DANGER, font=("Segoe UI", 9))

        # 2. Extract and display existing Image EXIF
        exif_date, exif_gps, exif_desc = self._read_existing_image_exif(pair.image_path)
        self.lbl_exif_date.config(text=f"Date Taken: {exif_date}")
        self.lbl_exif_gps.config(text=f"GPS: {exif_gps}")
        self.lbl_exif_desc.config(text=f"Description: {exif_desc}")

        # 3. Read and display target JSON Metadata
        if pair.json_data:
            dt_str = "Unknown"
            if "photoTakenTime" in pair.json_data:
                dt_str = pair.json_data["photoTakenTime"].get("formatted", "Unknown")
            elif "creationTime" in pair.json_data:
                dt_str = pair.json_data["creationTime"].get("formatted", "Unknown")

            geo = pair.json_data.get("geoDataExif") or pair.json_data.get("geoData") or {}
            lat, lon = geo.get("latitude", 0.0), geo.get("longitude", 0.0)
            gps_str = f"{lat:.4f}, {lon:.4f}" if (lat or lon) else "None"
            title_desc = pair.json_data.get("description") or pair.json_data.get("title", "None")

            self.lbl_json_date.config(text=f"Taken Time: {dt_str}")
            self.lbl_json_gps.config(text=f"GPS: {gps_str}")
            self.lbl_json_desc.config(text=f"Title/Desc: {title_desc}")
        else:
            self.lbl_json_date.config(text="Taken Time: N/A")
            self.lbl_json_gps.config(text="GPS: N/A")
            self.lbl_json_desc.config(text="Title/Desc: N/A")

    def _read_existing_image_exif(self, image_path):
        """Extracts existing basic EXIF info from an image using PIL."""
        date_str = "None"
        gps_str = "None"
        desc_str = "None"
        try:
            with Image.open(image_path) as img:
                exif = img.getexif()
                if exif:
                    # Tag 306 = DateTime, Tag 36867 = DateTimeOriginal
                    date_str = exif.get(36867) or exif.get(306) or "Not present"
                    desc_str = exif.get(270) or "Not present" # Tag 270 = ImageDescription
                    if 34853 in exif: # Tag 34853 = GPSInfo
                        gps_str = "Present in EXIF header"
        except Exception:
            pass
        return date_str, gps_str, desc_str

    def _execute_merge(self, pair: ImagePairItem):
        """Delegates metadata merge execution to standalone helper function."""
        return execute_merge(pair)

    def _merge_selected(self):
        if not self.selected_pair:
            messagebox.showinfo("Select File", "Please select an image file from the list first.")
            return

        if not self.selected_pair.json_path:
            messagebox.showwarning("Missing Sidecar", f"No JSON sidecar file was found for {self.selected_pair.filename}.")
            return

        success = self._execute_merge(self.selected_pair)
        if success:
            self.log(f"Merged EXIF data into: {self.selected_pair.filename}", level="SUCCESS")
        else:
            self.log(f"Failed to merge {self.selected_pair.filename}: {self.selected_pair.error_msg}", level="ERROR")

        self._populate_tree()
        self._update_stats()
        self._render_side_by_side_preview(self.selected_pair)

    def _start_batch_merge(self):
        matched_pairs = [p for p in self.pairs if p.json_path and not p.merged]
        if not matched_pairs:
            messagebox.showinfo("No Actions Needed", "No unmerged matched pairs available to process.")
            return

        if self.is_processing:
            return

        # Disable buttons during processing thread
        self.is_processing = True
        self.btn_merge_all.config(state=tk.DISABLED)
        self.btn_merge_selected.config(state=tk.DISABLED)

        # Run background thread for smooth UI execution
        threading.Thread(target=self._run_batch_worker, args=(matched_pairs,), daemon=True).start()

    def _run_batch_worker(self, items_to_merge):
        total = len(items_to_merge)
        self.log(f"Starting batch merge operation for {total} files...")
        
        success_count = 0
        fail_count = 0

        for i, pair in enumerate(items_to_merge, start=1):
            success = self._execute_merge(pair)
            if success:
                success_count += 1
            else:
                fail_count += 1

            # Update UI progress safely via thread queue/event
            progress = (i / total) * 100
            self.after(0, self._update_progress, progress, i, total)

        self.after(0, self._finish_batch_worker, success_count, fail_count)

    def _update_progress(self, progress_val, current_idx, total_count):
        self.progress_bar["value"] = progress_val
        self.lbl_stats.config(text=f"Processing {current_idx}/{total_count} files...")

    def _finish_batch_worker(self, success_count, fail_count):
        self.is_processing = False
        self.btn_merge_all.config(state=tk.NORMAL)
        self.btn_merge_selected.config(state=tk.NORMAL)
        self.progress_bar["value"] = 100

        self.log(f"Batch merge completed! Success: {success_count}, Failures: {fail_count}", level="INFO")
        messagebox.showinfo("Batch Complete", f"Batch merging finished!\n\nSuccessfully Merged: {success_count}\nFailed: {fail_count}")

        self._populate_tree()
        self._update_stats()

def run_cli(folder_path=None):
    """Fallback CLI mode for headless environments or command line execution."""
    print("=" * 60)
    print(f" {APP_TITLE} (Headless / CLI Mode)")
    print("=" * 60)

    if not folder_path and len(sys.argv) > 1:
        folder_path = sys.argv[1]

    if not folder_path or not os.path.isdir(folder_path):
        print("\n[INFO] No graphical display detected ($DISPLAY missing) and no folder path provided.")
        print("\nCLI Usage:")
        print("  python exif_merger_app.py <path_to_photos_folder>")
        print("\nExample:")
        print("  python exif_merger_app.py ./Takeout/GooglePhotos")
        sys.exit(0)

    print(f"\nProcessing folder: {os.path.abspath(folder_path)}")
    pairs = PairMatcherEngine.scan_directory(folder_path)
    matched = [p for p in pairs if p.json_path and not p.merged]
    print(f"Found {len(pairs)} total images | {len(matched)} matched with JSON sidecars.")

    if not matched:
        print("No unmerged matched image-JSON pairs found.")
        return

    print("\nMerging metadata...")
    success_count = 0
    fail_count = 0

    for idx, pair in enumerate(matched, start=1):
        if execute_merge(pair):
            success_count += 1
            print(f"  [{idx}/{len(matched)}] SUCCESS: {pair.filename}")
        else:
            fail_count += 1
            print(f"  [{idx}/{len(matched)}] FAILED: {pair.filename} - {pair.error_msg}")

    print("\n" + "=" * 60)
    print(f" Batch Merge Complete!")
    print(f" Total Processed: {len(matched)} | Success: {success_count} | Failed: {fail_count}")
    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
        run_cli(sys.argv[1])
    else:
        try:
            app = ExifMergerApp()
            app.mainloop()
        except (tk.TclError, Exception) as err:
            err_str = str(err)
            if "no display name" in err_str or "$DISPLAY" in err_str or "display" in err_str.lower():
                run_cli()
            else:
                raise err