import os
import sys
import json
import glob
import re
from datetime import datetime
import time
import threading
from pathlib import Path
import urllib.parse

# GUI imports
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk, ImageOps

PIEXIF_AVAILABLE = False
try:
    import piexif
    PIEXIF_AVAILABLE = True
except ImportError:
    PIEXIF_AVAILABLE = False

APP_TITLE = "EXIF Metadata Merger (Google Photos Takeout)"
APP_VERSION = "1.0.0"

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

LANGUAGES = {
    "English": "en",
    "मराठी (Marathi)": "mr",
    "हिंदी (Hindi)": "hi",
    "Deutsch": "de",
    "Polski": "pl",
    "Português": "pt",
    "Français": "fr",
    "中文 (Chinese)": "zh",
    "日本語 (Japanese)": "ja",
    "Русский (Russian)": "ru"
}

TRANSLATIONS = {
    "en": {
        "app_title": "📷 EXIF Metadata Merger",
        "app_subtitle": "Google Photos Takeout JSON Sidecar Restorer",
        "open_folder": "📁 Open Takeout Folder",
        "rescan": "🔄 Rescan",
        "no_folder": "No folder selected",
        "scanned_files": "Scanned Image Files",
        "preview_title": " Image Preview ",
        "review_title": " Metadata Review & Comparison ",
        "current_exif": "Current Image EXIF",
        "target_json": "Target Google JSON Sidecar",
        "date_taken": "Date Taken",
        "taken_time": "Taken Time",
        "gps": "GPS",
        "description": "Description",
        "title_desc": "Title/Desc",
        "merge_selected": "Merge Selected Item",
        "merge_all": "⚡ Merge All Matched Pairs",
        "delete_selected_json": "🗑️ Delete Selected JSON",
        "delete_all_jsons": "🗑️ Delete All Merged JSONs",
        "log_console": " Operational Log Console ",
        "col_filename": "Image Filename",
        "col_status": "Status",
        "col_json": "Sidecar JSON",
        "total_images": "Total Images",
        "matched_pairs": "Matched Pairs",
        "merged": "Merged",
        "missing_sidecar": "❌ Missing Sidecar",
        "filter_all": "All",
        "filter_matched": "Matched",
        "filter_unmatched": "Unmatched",
        "filter_merged": "Merged"
    },
    "mr": {
        "app_title": "📷 EXIF डेटा विलीनीकरण",
        "app_subtitle": "गूगल फोटोज टेकआउट JSON साइडकार रीस्टोरर",
        "open_folder": "📁 टेकआउट फोल्डर उघडा",
        "rescan": "🔄 पुन्हा स्कॅन करा",
        "no_folder": "कोणतेही फोल्डर निवडलेले नाही",
        "scanned_files": "स्कॅन केलेल्या प्रतिमा फायली",
        "preview_title": " प्रतिमा पूर्वदृश्य ",
        "review_title": " मेटाडेटा पुनरावलोकन आणि तुलना ",
        "current_exif": "सध्याचे इमेज EXIF",
        "target_json": "लक्ष्य गूगल JSON साइडकार",
        "date_taken": "तारीख घेतली",
        "taken_time": "घेण्याची वेळ",
        "gps": "जीपीएस",
        "description": "वर्णन",
        "title_desc": "शीर्षक/वर्णन",
        "merge_selected": "निवडलेली आयटम विलीन करा",
        "merge_all": "⚡ सर्व जुळलेल्या जोड्या विलीन करा",
        "delete_selected_json": "🗑️ निवडलेली JSON हटवा",
        "delete_all_jsons": "🗑️ सर्व विलीन केलेल्या JSONs हटवा",
        "log_console": " कार्य लॉग कन्सोल ",
        "col_filename": "प्रतिमा फाइलनाव",
        "col_status": "स्थिती",
        "col_json": "साइडकार JSON",
        "total_images": "एकूण प्रतिमा",
        "matched_pairs": "जुळलेल्या जोड्या",
        "merged": "विलीन केले",
        "missing_sidecar": "❌ साइडकार नाही",
        "filter_all": "सर्व",
        "filter_matched": "जुळलेले",
        "filter_unmatched": "अजोड",
        "filter_merged": "विलीन"
    },
    "hi": {
        "app_title": "📷 EXIF डेटा विलयन",
        "app_subtitle": "गूगल फोटोज टेकआउट JSON साइडकार रिस्टोरर",
        "open_folder": "📁 टेकआउट फ़ोल्डर खोलें",
        "rescan": "🔄 पुन: स्कैन करें",
        "no_folder": "कोई फ़ोल्डर चुना नहीं गया",
        "scanned_files": "स्कैन की गई छवि फ़ाइलें",
        "preview_title": " छवि पूर्वावलोकन ",
        "review_title": " मेटाडेटा समीक्षा और तुलना ",
        "current_exif": "वर्तमान छवि EXIF",
        "target_json": "लक्ष्य गूगल JSON साइडकार",
        "date_taken": "तारीख ली गई",
        "taken_time": "लिया गया समय",
        "gps": "जीपीएस",
        "description": "विवरण",
        "title_desc": "शीर्षक/विवरण",
        "merge_selected": "चयनित आइटम का विलय करें",
        "merge_all": "⚡ सभी मिले हुए जोड़ों का विलय करें",
        "delete_selected_json": "🗑️ चयनित JSON हटाएं",
        "delete_all_jsons": "🗑️ सभी विलय की गई JSONs हटाएं",
        "log_console": " संचालन लॉग कंसोल ",
        "col_filename": "छवि फ़ाइल नाम",
        "col_status": "स्थिति",
        "col_json": "साइडकार JSON",
        "total_images": "कुल छवियां",
        "matched_pairs": "मिले हुए जोड़े",
        "merged": "विलय किया गया",
        "missing_sidecar": "❌ साइडकार गायब",
        "filter_all": "सभी",
        "filter_matched": "मिले हुए",
        "filter_unmatched": "अनमेल",
        "filter_merged": "विलय किया हुआ"
    },
    "de": {
        "app_title": "📷 EXIF-Metadaten Fusion",
        "app_subtitle": "Google Fotos Takeout JSON-Sidecar Wiederherstellung",
        "open_folder": "📁 Takeout-Ordner öffnen",
        "rescan": "🔄 Erneut scannen",
        "no_folder": "Kein Ordner ausgewählt",
        "scanned_files": "Gescannte Bilddateien",
        "preview_title": " Bildvorschau ",
        "review_title": " Metadaten-Überprüfung & Vergleich ",
        "current_exif": "Aktuelle Bild-EXIF",
        "target_json": "Ziel Google JSON-Sidecar",
        "date_taken": "Aufnahmedatum",
        "taken_time": "Aufnahmezeit",
        "gps": "GPS",
        "description": "Beschreibung",
        "title_desc": "Titel/Beschreibung",
        "merge_selected": "Ausgewähltes Element zusammenführen",
        "merge_all": "⚡ Alle passenden Paare zusammenführen",
        "delete_selected_json": "🗑️ Ausgewählte JSON löschen",
        "delete_all_jsons": "🗑️ Alle zusammengeführten JSONs löschen",
        "log_console": " Betriebsprotokoll-Konsole ",
        "col_filename": "Dateiname",
        "col_status": "Status",
        "col_json": "Sidecar JSON",
        "total_images": "Gesamtbilder",
        "matched_pairs": "Passende Paare",
        "merged": "Zusammengeführt",
        "missing_sidecar": "❌ Fehlende Sidecar",
        "filter_all": "Alle",
        "filter_matched": "Passend",
        "filter_unmatched": "Nicht passend",
        "filter_merged": "Zusammengeführt"
    },
    "pl": {
        "app_title": "📷 Scalanie Metadanych EXIF",
        "app_subtitle": "Przywracanie JSON Sidecar z Google Photos Takeout",
        "open_folder": "📁 Otwórz folder Takeout",
        "rescan": "🔄 Skanuj ponownie",
        "no_folder": "Nie wybrano folderu",
        "scanned_files": "Zeskanowane pliki obrazów",
        "preview_title": " Podgląd obrazu ",
        "review_title": " Przegląd i porównanie metadanych ",
        "current_exif": "Aktualne EXIF obrazu",
        "target_json": "Docelowy JSON Google Sidecar",
        "date_taken": "Data wykonania",
        "taken_time": "Czas wykonania",
        "gps": "GPS",
        "description": "Opis",
        "title_desc": "Tytuł/Opis",
        "merge_selected": "Scal zaznaczony element",
        "merge_all": "⚡ Scal wszystkie dopasowane pary",
        "delete_selected_json": "🗑️ Usuń zaznaczony JSON",
        "delete_all_jsons": "🗑️ Usuń wszystkie scalone JSON-y",
        "log_console": " Konsola dziennika operacyjnego ",
        "col_filename": "Nazwa pliku",
        "col_status": "Status",
        "col_json": "Sidecar JSON",
        "total_images": "Wszystkie obrazy",
        "matched_pairs": "Dopasowane pary",
        "merged": "Scalone",
        "missing_sidecar": "❌ Brak pliku JSON",
        "filter_all": "Wszystkie",
        "filter_matched": "Dopasowane",
        "filter_unmatched": "Niedopasowane",
        "filter_merged": "Scalone"
    },
    "pt": {
        "app_title": "📷 Mesclador de Metadados EXIF",
        "app_subtitle": "Restaurador de JSON Sidecar do Google Fotos Takeout",
        "open_folder": "📁 Abrir pasta do Takeout",
        "rescan": "🔄 Recomprovar",
        "no_folder": "Nenhuma pasta selecionada",
        "scanned_files": "Arquivos de imagem digitalizados",
        "preview_title": " Pré-visualização da imagem ",
        "review_title": " Revisão e comparação de metadados ",
        "current_exif": "EXIF da imagem atual",
        "target_json": "JSON Sidecar do Google de destino",
        "date_taken": "Data da foto",
        "taken_time": "Hora da foto",
        "gps": "GPS",
        "description": "Descrição",
        "title_desc": "Título/Descrição",
        "merge_selected": "Mesclar item selecionado",
        "merge_all": "⚡ Mesclar todos os pares correspondentes",
        "delete_selected_json": "🗑️ Excluir JSON selecionado",
        "delete_all_jsons": "🗑️ Excluir todos os JSONs mesclados",
        "log_console": " Console de log operacional ",
        "col_filename": "Nome do arquivo",
        "col_status": "Status",
        "col_json": "JSON Sidecar",
        "total_images": "Total de Imagens",
        "matched_pairs": "Pares Correspondentes",
        "merged": "Mesclado",
        "missing_sidecar": "❌ Sidecar Ausente",
        "filter_all": "Todos",
        "filter_matched": "Correspondentes",
        "filter_unmatched": "Sem correspondência",
        "filter_merged": "Mesclados"
    },
    "fr": {
        "app_title": "📷 Fusionneur de Métadonnées EXIF",
        "app_subtitle": "Restaurateur de fichiers JSON Google Photos Takeout",
        "open_folder": "📁 Ouvrir le dossier Takeout",
        "rescan": "🔄 Analyser à nouveau",
        "no_folder": "Aucun dossier sélectionné",
        "scanned_files": "Fichiers images analysés",
        "preview_title": " Aperçu de l'image ",
        "review_title": " Examen et comparaison des métadonnées ",
        "current_exif": "EXIF de l'image actuelle",
        "target_json": "Fichier JSON Google cible",
        "date_taken": "Date de prise de vue",
        "taken_time": "Heure de prise de vue",
        "gps": "GPS",
        "description": "Description",
        "title_desc": "Titre/Description",
        "merge_selected": "Fusionner l'élément sélectionné",
        "merge_all": "⚡ Fusionner toutes les paires correspondantes",
        "delete_selected_json": "🗑️ Supprimer le JSON sélectionné",
        "delete_all_jsons": "🗑️ Supprimer tous les JSONs fusionnés",
        "log_console": " Console de journal opérationnel ",
        "col_filename": "Nom de fichier",
        "col_status": "Statut",
        "col_json": "Sidecar JSON",
        "total_images": "Total d'images",
        "matched_pairs": "Paires associées",
        "merged": "Fusionné",
        "missing_sidecar": "❌ Sidecar manquant",
        "filter_all": "Tous",
        "filter_matched": "Associés",
        "filter_unmatched": "Non associés",
        "filter_merged": "Fusionnés"
    },
    "zh": {
        "app_title": "📷 EXIF 元数据合并器",
        "app_subtitle": "Google 相册 Takeout JSON 附带文件恢复器",
        "open_folder": "📁 打开 Takeout 文件夹",
        "rescan": "🔄 重新扫描",
        "no_folder": "未选择文件夹",
        "scanned_files": "已扫描的图像文件",
        "preview_title": " 图像预览 ",
        "review_title": " 元数据审查与对比 ",
        "current_exif": "当前图像 EXIF",
        "target_json": "目标 Google JSON 附带文件",
        "date_taken": "拍摄日期",
        "taken_time": "拍摄时间",
        "gps": "GPS 位置",
        "description": "描述",
        "title_desc": "标题/描述",
        "merge_selected": "合并选中项",
        "merge_all": "⚡ 合并所有匹配对",
        "delete_selected_json": "🗑️ 删除选中的 JSON",
        "delete_all_jsons": "🗑️ 删除所有已合并的 JSON",
        "log_console": " 操作日志控制台 ",
        "col_filename": "图像文件名",
        "col_status": "状态",
        "col_json": "附带 JSON 文件",
        "total_images": "图像总数",
        "matched_pairs": "已匹配对",
        "merged": "已合并",
        "missing_sidecar": "❌ 缺少附带文件",
        "filter_all": "全部",
        "filter_matched": "已匹配",
        "filter_unmatched": "未匹配",
        "filter_merged": "已合并"
    },
    "ja": {
        "app_title": "📷 EXIF メタデータ統合ツール",
        "app_subtitle": "Google フォト Takeout JSON サイドカー復元",
        "open_folder": "📁 Takeout フォルダを開く",
        "rescan": "🔄 再スキャン",
        "no_folder": "フォルダが選択されていません",
        "scanned_files": "スキャンされた画像ファイル",
        "preview_title": " 画像プレビュー ",
        "review_title": " メタデータの確認と比較 ",
        "current_exif": "現在の画像 EXIF",
        "target_json": "対象 Google JSON サイドカー",
        "date_taken": "撮影日",
        "taken_time": "撮影日時",
        "gps": "GPS",
        "description": "説明",
        "title_desc": "タイトル/説明",
        "merge_selected": "選択した項目を結合",
        "merge_all": "⚡ 一致するすべてのペアを結合",
        "delete_selected_json": "🗑️ 選択した JSON を削除",
        "delete_all_jsons": "🗑️ 結合済みの全 JSON を削除",
        "log_console": " 操作ログコンソール ",
        "col_filename": "画像ファイル名",
        "col_status": "ステータス",
        "col_json": "サイドカー JSON",
        "total_images": "画像総数",
        "matched_pairs": "一致したペア",
        "merged": "結合済み",
        "missing_sidecar": "❌ サイドカーなし",
        "filter_all": "すべて",
        "filter_matched": "一致",
        "filter_unmatched": "未一致",
        "filter_merged": "結合済み"
    },
    "ru": {
        "app_title": "📷 Объединение Метаданных EXIF",
        "app_subtitle": "Восстановление JSON Sidecar из Google Photos Takeout",
        "open_folder": "📁 Открыть папку Takeout",
        "rescan": "🔄 Пересканировать",
        "no_folder": "Папка не выбрана",
        "scanned_files": "Сканированные файлы изображений",
        "preview_title": " Предпросмотр изображения ",
        "review_title": " Просмотр и сравнение метаданных ",
        "current_exif": "Текущий EXIF изображения",
        "target_json": "Целевой Google JSON Sidecar",
        "date_taken": "Дата съемки",
        "taken_time": "Время съемки",
        "gps": "GPS",
        "description": "Описание",
        "title_desc": "Название/Описание",
        "merge_selected": "Объединить выбранный элемент",
        "merge_all": "⚡ Объединить все совпавшие пары",
        "delete_selected_json": "🗑️ Удалить выбранный JSON",
        "delete_all_jsons": "🗑️ Удалить все объединенные JSON",
        "log_console": " Консоль журнала операций ",
        "col_filename": "Имя файла",
        "col_status": "Статус",
        "col_json": "Sidecar JSON",
        "total_images": "Всего изображений",
        "matched_pairs": "Совпавшие пары",
        "merged": "Объединено",
        "missing_sidecar": "❌ Нет Sidecar",
        "filter_all": "Все",
        "filter_matched": "Совпавшие",
        "filter_unmatched": "Без пары",
        "filter_merged": "Объединенные"
    }
}

def deg_to_dms_rational(deg_float):
    """Convert decimal degrees to EXIF degrees, minutes, seconds rational tuple."""
    deg = int(abs(deg_float))
    min_float = (abs(deg_float) - deg) * 60
    minute = int(min_float)
    sec_float = (min_float - minute) * 60
    sec = int(sec_float * 10000)
    return ((deg, 1), (minute, 1), (sec, 10000))

def create_exif_dict_from_json(json_data):
    """Constructs a dictionary compatible with piexif from Google Photos JSON sidecar."""
    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    timestamp = None

    if isinstance(json_data, dict):
        if "photoTakenTime" in json_data and isinstance(json_data["photoTakenTime"], dict):
            try:
                timestamp = int(json_data["photoTakenTime"].get("timestamp", 0))
            except (ValueError, TypeError):
                pass
        if not timestamp and "creationTime" in json_data and isinstance(json_data["creationTime"], dict):
            try:
                timestamp = int(json_data["creationTime"].get("timestamp", 0))
            except (ValueError, TypeError):
                pass

    if timestamp and PIEXIF_AVAILABLE:
        dt = datetime.fromtimestamp(timestamp)
        date_str = dt.strftime("%Y:%m:%d %H:%M:%S")
        exif_dict["0th"][piexif.ImageIFD.DateTime] = date_str
        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_str
        exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_str

    if isinstance(json_data, dict):
        desc = json_data.get("description") or json_data.get("title", "")
        if desc and PIEXIF_AVAILABLE:
            exif_dict["0th"][piexif.ImageIFD.ImageDescription] = desc.encode('utf-8')

        geo = json_data.get("geoDataExif") or json_data.get("geoData") or {}
        if isinstance(geo, dict):
            lat = geo.get("latitude")
            lon = geo.get("longitude")

            if lat is not None and lon is not None and (lat != 0.0 or lon != 0.0) and PIEXIF_AVAILABLE:
                lat_ref = 'N' if lat >= 0 else 'S'
                lon_ref = 'E' if lon >= 0 else 'W'
                exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = lat_ref
                exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = deg_to_dms_rational(lat)
                exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = lon_ref
                exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = deg_to_dms_rational(lon)

    return exif_dict, timestamp

def execute_merge(pair):
    """Writes EXIF metadata into the image header and updates OS filesystem timestamps."""
    if not pair.json_path or not pair.json_data:
        pair.status = "No JSON"
        return False

    image_path = pair.image_path
    json_data = pair.json_data

    try:
        exif_dict, timestamp = create_exif_dict_from_json(json_data)

        # 1. Update EXIF using piexif if available, or Pillow native EXIF API
        if PIEXIF_AVAILABLE and image_path.lower().endswith(('.jpg', '.jpeg', '.tif', '.tiff')):
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, image_path)
        else:
            # Fallback: Pillow EXIF manipulation
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

def delete_pair_json(pair):
    """Deletes the JSON sidecar file associated with a photo pair."""
    if pair.json_path and os.path.exists(pair.json_path):
        try:
            os.remove(pair.json_path)
            deleted_path = pair.json_path
            pair.json_path = None
            if pair.merged:
                pair.status = "Merged (JSON Deleted)"
            else:
                pair.status = "Unmatched Image"
            return True, deleted_path
        except Exception as e:
            return False, str(e)
    return False, "No JSON sidecar file found."

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

        # Strategy 1: Check internal "title" tag inside JSON file
        if img_name_lower in json_title_map:
            return json_title_map[img_name_lower]

        # Strategy 2: Case-insensitive exact name + .json (e.g., photo.jpg.json)
        candidate1 = f"{img_name_lower}.json"
        if candidate1 in json_file_map:
            return os.path.join(folder_path, json_file_map[candidate1])

        # Strategy 3: Base name without image extension + .json (e.g., photo.json)
        candidate2 = f"{base_name_lower}.json"
        if candidate2 in json_file_map:
            return os.path.join(folder_path, json_file_map[candidate2])

        # Strategy 4: Handle index tag permutations (e.g., photo(1).jpg vs photo.jpg(1).json)
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

        # Strategy 5: Edited photos (e.g., photo-edited.jpg -> photo.jpg.json)
        if "-edited" in base_name_lower:
            unedited_base = base_name_lower.replace("-edited", "")
            cand_edited1 = f"{unedited_base}{ext.lower()}.json"
            if cand_edited1 in json_file_map:
                return os.path.join(folder_path, json_file_map[cand_edited1])
            cand_edited2 = f"{unedited_base}.json"
            if cand_edited2 in json_file_map:
                return os.path.join(folder_path, json_file_map[cand_edited2])

        # Strategy 6: Truncated long filenames
        if len(img_name) > 30:
            prefix = base_name_lower[:25]
            for j_lower, j_real in json_file_map.items():
                if j_lower.startswith(prefix):
                    return os.path.join(folder_path, j_real)

        # Strategy 7: URL / Special character unescaping
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
        self.current_lang_code = "en"

        # Apply Modern Dark Theme styling to TTK widgets
        self._setup_ttk_styles()

        # Build UI Structure
        self._build_top_bar()
        self._build_main_panes()
        self._build_bottom_bar()

        # Apply initial language strings safely after widget initialization
        self._apply_language("en")

        # Log system status
        self.log(f"{APP_TITLE} initialized.")
        if not PIEXIF_AVAILABLE:
            self.log("Note: 'piexif' library not installed. Standard JPEG metadata merging will use Pillow fallback. For full raw EXIF manipulation, install piexif (`pip install piexif`).", level="WARNING")

    def _setup_ttk_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

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

        # Treeview
        style.configure("Treeview", background=COLOR_PANEL_BG, foreground=COLOR_TEXT, fieldbackground=COLOR_PANEL_BG, borderwidth=0, rowheight=28)
        style.map("Treeview", background=[("selected", COLOR_SURFACE_LIGHT)], foreground=[("selected", COLOR_ACCENT)])
        style.configure("Treeview.Heading", background=COLOR_SURFACE, foreground=COLOR_TEXT, font=("Segoe UI", 9, "bold"), borderwidth=1)

        # Progressbar
        style.configure("Horizontal.TProgressbar", background=COLOR_ACCENT, troughcolor=COLOR_SURFACE, borderwidth=0)

    def _build_top_bar(self):
        top_frame = ttk.Frame(self, padding=(15, 12, 15, 10), style="DarkFrame.TFrame")
        top_frame.pack(fill=tk.X, side=tk.TOP)

        title_box = ttk.Frame(top_frame, style="DarkFrame.TFrame")
        title_box.pack(side=tk.LEFT, fill=tk.Y)

        title_row = ttk.Frame(title_box, style="DarkFrame.TFrame")
        title_row.pack(anchor=tk.W, fill=tk.X)

        self.title_lbl = tk.Label(title_row, text="📷 EXIF Metadata Merger", font=("Segoe UI", 16, "bold"), fg=COLOR_TEXT, bg=COLOR_BG_DARK)
        self.title_lbl.pack(side=tk.LEFT)

        # Language Selection Dropdown
        self.lang_var = tk.StringVar(value="English")
        self.lang_combo = ttk.Combobox(title_row, textvariable=self.lang_var, values=list(LANGUAGES.keys()), state="readonly", width=14)
        self.lang_combo.pack(side=tk.LEFT, padx=(12, 0))
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_language_change)

        self.sub_lbl = tk.Label(title_box, text="Google Photos Takeout JSON Sidecar Restorer", font=("Segoe UI", 9), fg=COLOR_TEXT_MUTED, bg=COLOR_BG_DARK)
        self.sub_lbl.pack(anchor=tk.W)

        # Folder Selection Actions
        btn_box = ttk.Frame(top_frame, style="DarkFrame.TFrame")
        btn_box.pack(side=tk.RIGHT, fill=tk.Y)

        self.dir_path_var = tk.StringVar(value="No folder selected")
        self.dir_display = tk.Label(btn_box, textvariable=self.dir_path_var, font=("Segoe UI", 9, "italic"), fg=COLOR_ACCENT, bg=COLOR_BG_DARK, width=40, anchor="e")
        self.dir_display.pack(side=tk.LEFT, padx=10)

        self.open_btn = ttk.Button(btn_box, text="📁 Open Takeout Folder", command=self._select_directory)
        self.open_btn.pack(side=tk.LEFT, padx=5)

        self.scan_btn = ttk.Button(btn_box, text="🔄 Rescan", command=self._scan_pairs)
        self.scan_btn.pack(side=tk.LEFT, padx=5)

    def _build_main_panes(self):
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        # ---------------- LEFT PANE: File Tree / Pair List ----------------
        left_frame = ttk.Frame(main_paned, padding=5)
        main_paned.add(left_frame, weight=4)

        list_header = ttk.Frame(left_frame)
        list_header.pack(fill=tk.X, pady=(0, 5))
        
        self.lbl_scanned_header = ttk.Label(list_header, text="Scanned Image Files", font=("Segoe UI", 11, "bold"))
        self.lbl_scanned_header.pack(side=tk.LEFT)
        
        self.filter_var = tk.StringVar(value="All")
        self.filter_combo = ttk.Combobox(list_header, textvariable=self.filter_var, values=["All", "Matched", "Unmatched", "Merged"], state="readonly", width=12)
        self.filter_combo.pack(side=tk.RIGHT)
        self.filter_combo.bind("<<ComboboxSelected>>", lambda e: self._populate_tree())

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

        self.tree.tag_configure("matched", foreground=COLOR_TEXT)
        self.tree.tag_configure("unmatched", foreground=COLOR_WARNING)
        self.tree.tag_configure("merged", foreground=COLOR_SUCCESS)
        self.tree.tag_configure("error", foreground=COLOR_DANGER)

        # ---------------- RIGHT PANE: Side-by-Side Reviewer ----------------
        right_frame = ttk.Frame(main_paned, padding=5)
        main_paned.add(right_frame, weight=6)

        right_paned = ttk.PanedWindow(right_frame, orient=tk.VERTICAL)
        right_paned.pack(fill=tk.BOTH, expand=True)

        # Top Right: Image Canvas Preview
        self.preview_box = ttk.LabelFrame(right_paned, text=" Image Preview ", padding=10)
        right_paned.add(self.preview_box, weight=5)

        self.canvas = tk.Canvas(self.preview_box, bg=COLOR_BG_DARK, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.preview_image_ref = None

        # Bottom Right: Dual Metadata Comparison Boxes
        self.meta_box = ttk.LabelFrame(right_paned, text=" Metadata Review & Comparison ", padding=10)
        right_paned.add(self.meta_box, weight=5)

        meta_grid = ttk.Frame(self.meta_box)
        meta_grid.pack(fill=tk.BOTH, expand=True)

        # Existing EXIF Card
        exif_card = ttk.Frame(meta_grid, style="Card.TFrame", padding=10)
        exif_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.lbl_exif_header = ttk.Label(exif_card, text="Current Image EXIF", font=("Segoe UI", 10, "bold"), foreground=COLOR_ACCENT, background=COLOR_SURFACE)
        self.lbl_exif_header.pack(anchor=tk.W)
        self.lbl_exif_date = ttk.Label(exif_card, text="Date Taken: --", background=COLOR_SURFACE)
        self.lbl_exif_date.pack(anchor=tk.W, pady=(5, 2))
        self.lbl_exif_gps = ttk.Label(exif_card, text="GPS: --", background=COLOR_SURFACE)
        self.lbl_exif_gps.pack(anchor=tk.W, pady=2)
        self.lbl_exif_desc = ttk.Label(exif_card, text="Description: --", background=COLOR_SURFACE, wraplength=250)
        self.lbl_exif_desc.pack(anchor=tk.W, pady=2)

        # Target JSON Sidecar Card
        json_card = ttk.Frame(meta_grid, style="Card.TFrame", padding=10)
        json_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        self.lbl_json_header = ttk.Label(json_card, text="Target Google JSON Sidecar", font=("Segoe UI", 10, "bold"), foreground=COLOR_SUCCESS, background=COLOR_SURFACE)
        self.lbl_json_header.pack(anchor=tk.W)
        self.lbl_json_date = ttk.Label(json_card, text="Taken Time: --", background=COLOR_SURFACE)
        self.lbl_json_date.pack(anchor=tk.W, pady=(5, 2))
        self.lbl_json_gps = ttk.Label(json_card, text="GPS: --", background=COLOR_SURFACE)
        self.lbl_json_gps.pack(anchor=tk.W, pady=2)
        self.lbl_json_desc = ttk.Label(json_card, text="Title/Desc: --", background=COLOR_SURFACE, wraplength=250)
        self.lbl_json_desc.pack(anchor=tk.W, pady=2)

    def _build_bottom_bar(self):
        bottom_frame = ttk.Frame(self, padding=(15, 5, 15, 10), style="DarkFrame.TFrame")
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        action_bar = ttk.Frame(bottom_frame, style="DarkFrame.TFrame")
        action_bar.pack(fill=tk.X, pady=(0, 8))

        self.btn_merge_selected = ttk.Button(action_bar, text="Merge Selected Item", command=self._merge_selected)
        self.btn_merge_selected.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_merge_all = ttk.Button(action_bar, text="⚡ Merge All Matched Pairs", style="Accent.TButton", command=self._start_batch_merge)
        self.btn_merge_all.pack(side=tk.LEFT, padx=5)

        self.btn_delete_selected_json = ttk.Button(action_bar, text="🗑️ Delete Selected JSON", command=self._delete_selected_json)
        self.btn_delete_selected_json.pack(side=tk.LEFT, padx=5)

        self.btn_delete_all_jsons = ttk.Button(action_bar, text="🗑️ Delete All Merged JSONs", command=self._delete_all_merged_jsons)
        self.btn_delete_all_jsons.pack(side=tk.LEFT, padx=5)

        self.lbl_stats = tk.Label(action_bar, text="Total: 0 | Matched: 0 | Merged: 0", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT_MUTED, bg=COLOR_BG_DARK)
        self.lbl_stats.pack(side=tk.RIGHT, padx=5)

        self.progress_bar = ttk.Progressbar(bottom_frame, orient=tk.HORIZONTAL, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))

        self.log_frame = ttk.LabelFrame(bottom_frame, text=" Operational Log Console ", padding=5)
        self.log_frame.pack(fill=tk.X)

        self.log_widget = scrolledtext.ScrolledText(self.log_frame, height=4, font=("Consolas", 8), bg=COLOR_PANEL_BG, fg=COLOR_TEXT, insertbackground=COLOR_TEXT, relief="flat")
        self.log_widget.pack(fill=tk.BOTH, expand=True)

    def _on_language_change(self, event=None):
        selected_display = self.lang_var.get()
        code = LANGUAGES.get(selected_display, "en")
        self._apply_language(code)

    def _apply_language(self, lang_code):
        self.current_lang_code = lang_code
        t = TRANSLATIONS.get(lang_code, TRANSLATIONS["en"])

        self.title_lbl.config(text=t["app_title"])
        self.sub_lbl.config(text=t["app_subtitle"])
        self.open_btn.config(text=t["open_folder"])
        self.scan_btn.config(text=t["rescan"])
        if not self.working_dir:
            self.dir_path_var.set(t["no_folder"])
            
        self.lbl_scanned_header.config(text=t["scanned_files"])
        self.filter_combo.config(values=[t["filter_all"], t["filter_matched"], t["filter_unmatched"], t["filter_merged"]])
        
        self.tree.heading("#0", text=t["col_filename"])
        self.tree.heading("Status", text=t["col_status"])
        self.tree.heading("JSON", text=t["col_json"])

        self.preview_box.config(text=t["preview_title"])
        self.meta_box.config(text=t["review_title"])
        self.lbl_exif_header.config(text=t["current_exif"])
        self.lbl_json_header.config(text=t["target_json"])

        self.btn_merge_selected.config(text=t["merge_selected"])
        self.btn_merge_all.config(text=t["merge_all"])
        self.btn_delete_selected_json.config(text=t["delete_selected_json"])
        self.btn_delete_all_jsons.config(text=t["delete_all_jsons"])
        self.log_frame.config(text=t["log_console"])

        self._update_stats()
        if self.selected_pair:
            self._render_side_by_side_preview(self.selected_pair)

    def _populate_tree(self):
        t = TRANSLATIONS.get(self.current_lang_code, TRANSLATIONS["en"])
        self.tree.delete(*self.tree.get_children())
        filter_mode = self.filter_var.get()

        for item in self.pairs:
            if (filter_mode == t["filter_matched"] or filter_mode == "Matched") and not (item.json_path and not item.merged):
                continue
            elif (filter_mode == t["filter_unmatched"] or filter_mode == "Unmatched") and item.json_path is not None:
                continue
            elif (filter_mode == t["filter_merged"] or filter_mode == "Merged") and not item.merged:
                continue

            json_name = os.path.basename(item.json_path) if item.json_path else t["missing_sidecar"]
            tag = "matched"
            if item.merged:
                tag = "merged"
            elif not item.json_path:
                tag = "unmatched"
            elif item.status.startswith("Error"):
                tag = "error"

            node_id = self.tree.insert("", tk.END, text=item.filename, values=(item.status, json_name), tags=(tag,))
            self.tree.set(node_id, "Status", item.status)

    def _update_stats(self):
        t = TRANSLATIONS.get(self.current_lang_code, TRANSLATIONS["en"])
        total = len(self.pairs)
        matched = sum(1 for p in self.pairs if p.json_path)
        merged = sum(1 for p in self.pairs if p.merged)
        self.lbl_stats.config(text=f"{t['total_images']}: {total} | {t['matched_pairs']}: {matched} | {t['merged']}: {merged}")

    def _on_item_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return

        node_id = selected_items[0]
        filename = self.tree.item(node_id, "text")

        pair = next((p for p in self.pairs if p.filename == filename), None)
        if pair:
            self.selected_pair = pair
            self._render_side_by_side_preview(pair)

    def _render_side_by_side_preview(self, pair: ImagePairItem):
        t = TRANSLATIONS.get(self.current_lang_code, TRANSLATIONS["en"])
        
        # 1. Update Image Canvas Preview
        try:
            pil_img = Image.open(pair.image_path)
            pil_img = ImageOps.exif_transpose(pil_img)

            canvas_w = self.canvas.winfo_width() or 400
            canvas_h = self.canvas.winfo_height() or 250
            if canvas_w > 20 and canvas_h > 20:
                pil_img.thumbnail((canvas_w - 20, canvas_h - 20), Image.Resampling.LANCZOS)

            self.preview_image_ref = ImageTk.PhotoImage(pil_img)
            self.canvas.delete("all")
            self.canvas.create_image(canvas_w // 2, canvas_h // 2, image=self.preview_image_ref, anchor=tk.CENTER)
        except Exception as e:
            self.canvas.delete("all")
            self.canvas.create_text(150, 100, text=f"Preview Error:\n{str(e)}", fill=COLOR_DANGER, font=("Segoe UI", 9))

        # 2. Extract and display existing Image EXIF
        exif_date, exif_gps, exif_desc = self._read_existing_image_exif(pair.image_path)
        self.lbl_exif_date.config(text=f"{t['date_taken']}: {exif_date}")
        self.lbl_exif_gps.config(text=f"{t['gps']}: {exif_gps}")
        self.lbl_exif_desc.config(text=f"{t['description']}: {exif_desc}")

        # 3. Read and display target JSON Metadata
        if pair.json_data:
            dt_str = "Unknown"
            if "photoTakenTime" in pair.json_data:
                dt_str = pair.json_data["photoTakenTime"].get("formatted", "Unknown")
            elif "creationTime" in pair.json_data:
                dt_str = pair.json_data["creationTime"].get("formatted", "Unknown")

            geo = pair.json_data.get("geoDataExif") or pair.json_data.get("geoData") or {}
            lat = geo.get("latitude", 0.0) if isinstance(geo, dict) else 0.0
            lon = geo.get("longitude", 0.0) if isinstance(geo, dict) else 0.0
            gps_str = f"{lat:.4f}, {lon:.4f}" if (lat or lon) else "None"
            title_desc = pair.json_data.get("description") or pair.json_data.get("title", "None")

            self.lbl_json_date.config(text=f"{t['taken_time']}: {dt_str}")
            self.lbl_json_gps.config(text=f"{t['gps']}: {gps_str}")
            self.lbl_json_desc.config(text=f"{t['title_desc']}: {title_desc}")
        else:
            self.lbl_json_date.config(text=f"{t['taken_time']}: N/A")
            self.lbl_json_gps.config(text=f"{t['gps']}: N/A")
            self.lbl_json_desc.config(text=f"{t['title_desc']}: N/A")

    def _read_existing_image_exif(self, image_path):
        """Extracts existing basic EXIF info from an image using PIL."""
        date_str = "None"
        gps_str = "None"
        desc_str = "None"
        try:
            with Image.open(image_path) as img:
                exif = img.getexif()
                if exif:
                    date_str = exif.get(36867) or exif.get(306) or "Not present"
                    desc_str = exif.get(270) or "Not present"
                    if 34853 in exif:
                        gps_str = "Present in EXIF header"
        except Exception:
            pass
        return date_str, gps_str, desc_str

    def _delete_selected_json(self):
        if not self.selected_pair:
            messagebox.showinfo("Select File", "Please select an image file from the list first.")
            return

        if not self.selected_pair.json_path:
            messagebox.showinfo("No JSON", f"No JSON sidecar path associated with {self.selected_pair.filename}.")
            return

        if not self.selected_pair.merged:
            confirm = messagebox.askyesno(
                "Confirm Deletion",
                f"Notice: {self.selected_pair.filename} has NOT been merged yet.\nAre you sure you want to delete its JSON sidecar file?"
            )
            if not confirm:
                return

        success, info = delete_pair_json(self.selected_pair)
        if success:
            self.log(f"Deleted JSON sidecar file for: {self.selected_pair.filename}", level="SUCCESS")
        else:
            self.log(f"Failed to delete JSON for {self.selected_pair.filename}: {info}", level="ERROR")

        self._populate_tree()
        self._update_stats()
        self._render_side_by_side_preview(self.selected_pair)

    def _delete_all_merged_jsons(self):
        merged_with_json = [p for p in self.pairs if p.merged and p.json_path and os.path.exists(p.json_path)]
        if not merged_with_json:
            messagebox.showinfo("No Actions Needed", "No sidecar JSON files found for merged photos.")
            return

        confirm = messagebox.askyesno(
            "Confirm Mass Deletion",
            f"Are you sure you want to delete {len(merged_with_json)} JSON sidecar file(s) for all successfully merged photos?"
        )
        if not confirm:
            return

        deleted_count = 0
        fail_count = 0
        for pair in merged_with_json:
            success, _ = delete_pair_json(pair)
            if success:
                deleted_count += 1
            else:
                fail_count += 1

        self.log(f"Deleted JSON sidecars: {deleted_count} removed, {fail_count} failed.", level="INFO")
        messagebox.showinfo("Deletion Complete", f"JSON Deletion Finished!\n\nSuccessfully Deleted: {deleted_count}\nFailed: {fail_count}")

        self._populate_tree()
        self._update_stats()

    def _merge_selected(self):
        if not self.selected_pair:
            messagebox.showinfo("Select File", "Please select an image file from the list first.")
            return

        if not self.selected_pair.json_path:
            messagebox.showwarning("Missing Sidecar", f"No JSON sidecar file was found for {self.selected_pair.filename}.")
            return

        success = execute_merge(self.selected_pair)
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

        self.is_processing = True
        self.btn_merge_all.config(state=tk.DISABLED)
        self.btn_merge_selected.config(state=tk.DISABLED)

        threading.Thread(target=self._run_batch_worker, args=(matched_pairs,), daemon=True).start()

    def _run_batch_worker(self, items_to_merge):
        total = len(items_to_merge)
        self.log(f"Starting batch merge operation for {total} files...")
        
        success_count = 0
        fail_count = 0

        for i, pair in enumerate(items_to_merge, start=1):
            success = execute_merge(pair)
            if success:
                success_count += 1
            else:
                fail_count += 1

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
