import os
import sys
import json
from pathlib import Path
from PySide6 import QtWidgets, QtCore, QtGui

def get_setting(setting_name):
    settings_path = Path("settings.json")
    if not settings_path.exists():
        return None
    try:
        with settings_path.open("r", encoding="utf-8") as settings_file:
            data = json.load(settings_file)
            return data.get(setting_name)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not read settings: {error}", file=sys.stderr)
        return None

def return_maps():
    maps_path = get_setting("Map Output Path")
    if not maps_path:
        return []

    maps_dir = Path(maps_path)
    if not maps_dir.exists():
        return []
    return [
        path.relative_to(maps_dir).as_posix()
        for path in maps_dir.rglob("*.vmf")
        if path.is_file()
    ]


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

def parse_map(maps):
    return True

def window():
    maps = return_maps()
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(widget)

    if not maps:
        map_list = None
        layout.addWidget(QtWidgets.QLabel("No maps found in the specified output path."))
    else:
        map_list = list_maps(maps)
        layout.addWidget(map_list)
    return widget