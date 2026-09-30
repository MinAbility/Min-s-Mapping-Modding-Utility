import re
import sys
import json
from pathlib import Path
from PySide6 import QtWidgets, QtCore
from tabs.map_browser import MapBrowser, load_map_files


def get_setting(setting_name):
    settings_path = Path("settings.json")
    if not settings_path.exists():
        return None
    try:
        with settings_path.open("r", encoding="utf-8") as settings_file:
            data = json.load(settings_file)
            if setting_name == "Map Output":
                return data.get("Map Output", data.get("Map Output Path"))
            return data.get(setting_name)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not read settings: {error}", file=sys.stderr)
        return None

def return_maps(include_both_paths=False):
    return load_map_files("Map Output", ".vmf", include_both_paths)

def list_maps(maps):
    widget = QtWidgets.QListWidget()
    font = widget.font()
    font.setPixelSize(18)
    widget.setFont(font)
    widget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
    widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
    widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
    widget.addItems(maps)
    return widget

def parse_material(material_path):
    material_path = Path(material_path)
    with material_path.open("r", encoding="utf-8-sig") as map_file:
        contents = map_file.read()

    tokens = [
        match.group(0)
        for match in re.finditer(r'\s+|//[^\r\n]*|"(?:\\.|[^"\\])*"|[{}]|[^\s{}"]+', contents)
        if not match.group(0).isspace() and not match.group(0).startswith("//")
    ]

    def value(token):
        if not token.startswith('"'):
            return token
        try:
            return json.loads(token)
        except json.JSONDecodeError:
            return token[1:-1].replace('\\"', '"').replace('\\\\', '\\')

    materials = []
    seen_materials = set()

    def scan_block(index):
        while index < len(tokens):
            token = tokens[index]
            if token == "}":
                return index + 1
            if token == "{":
                index = scan_block(index + 1)
            else:
                key = value(token)
                if index + 1 < len(tokens) and tokens[index + 1] == "{":
                    index = scan_block(index + 2)
                else:
                    if key == "material" and index + 1 < len(tokens):
                        material = value(tokens[index + 1])
                        if material not in seen_materials:
                            seen_materials.add(material)
                            materials.append(material)
                    index += 2
        return index

    scan_block(0)
    return materials

def window():
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(widget)
    map_browser = MapBrowser(return_maps, widget)
    map_list = map_browser.list_widget
    layout.addWidget(map_browser, stretch=1)

    search_bar = QtWidgets.QLineEdit(widget)
    search_bar.setPlaceholderText("Search materials...")
    layout.addWidget(search_bar)

    material_list = QtWidgets.QListWidget(widget)
    material_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
    material_list.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
    material_list.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
    layout.addWidget(material_list)
    widget.selected_map_path = None
    widget.parsed_materials = None

    def filter_materials(search_text):
        search_text = search_text.casefold()
        for index in range(material_list.count()):
            item = material_list.item(index)
            item.setHidden(search_text not in item.text().casefold())

    search_bar.textChanged.connect(filter_materials)

    def load_selected_map():
        selected_item = map_list.currentItem()
        if selected_item is None:
            widget.selected_map_path = None
            widget.parsed_materials = None
            material_list.clear()
            return
        map_path = Path(selected_item.data(QtCore.Qt.UserRole))
        try:
            materials = parse_material(map_path)
        except (OSError, UnicodeDecodeError) as error:
            widget.selected_map_path = None
            widget.parsed_materials = None
            material_list.clear()
            material_list.addItem(f"Could not read {map_path}: {error}")
            return

        widget.selected_map_path = map_path
        widget.parsed_materials = materials
        material_list.clear()
        if materials:
            material_list.addItems(materials)
        else:
            material_list.addItem("No materials found in this map.")
        filter_materials(search_bar.text())

    map_list.currentItemChanged.connect(load_selected_map)

    return widget