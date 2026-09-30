import json
import os
from pathlib import Path
from PySide6 import QtCore, QtWidgets


SETTINGS_PATH = Path(__file__).resolve().parents[1] / "settings.json"
SHOW_BOTH_PATHS_SETTING = "Show maps from both paths"


def map_directories():
    try:
        with SETTINGS_PATH.open("r", encoding="utf-8") as settings_file:
            settings = json.load(settings_file)
    except (OSError, json.JSONDecodeError):
        return None, None

    if not isinstance(settings, dict):
        return None, None
    input_path = settings.get("Map Input", settings.get("Map Input Path"))
    output_path = settings.get("Map Output", settings.get("Map Output Path"))
    return input_path, output_path


def map_paths_differ():
    input_path, output_path = map_directories()
    return paths_differ(input_path, output_path)


def paths_differ(input_path, output_path):
    if not input_path or not output_path:
        return False
    input_dir = os.path.normcase(str(Path(input_path).expanduser().resolve()))
    output_dir = os.path.normcase(str(Path(output_path).expanduser().resolve()))
    return input_dir != output_dir


def show_both_map_paths():
    try:
        with SETTINGS_PATH.open("r", encoding="utf-8") as settings_file:
            settings = json.load(settings_file)
        return bool(settings.get(SHOW_BOTH_PATHS_SETTING, False))
    except (OSError, json.JSONDecodeError, AttributeError):
        return False


def load_map_files(setting_name, extension, include_both_paths=False):
    input_path, output_path = map_directories()
    primary_path = input_path if setting_name == "Map Input" else output_path
    roots = [(setting_name, primary_path)]
    if include_both_paths:
        other_name = "Map Output" if setting_name == "Map Input" else "Map Input"
        other_path = output_path if setting_name == "Map Input" else input_path
        roots.append((other_name, other_path))

    entries = []
    seen_paths = set()
    for source_name, configured_path in roots:
        if not configured_path:
            continue
        root = Path(configured_path).expanduser()
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.casefold() != extension.casefold():
                continue
            absolute_path = path.resolve()
            path_key = os.path.normcase(str(absolute_path))
            if path_key in seen_paths:
                continue
            seen_paths.add(path_key)
            entries.append({
                "name": path.relative_to(root).as_posix(),
                "relative_path": path.relative_to(root).as_posix(),
                "path": str(absolute_path),
                "source": source_name,
            })

    name_counts = {}
    for entry in entries:
        name_counts[entry["name"]] = name_counts.get(entry["name"], 0) + 1
    for entry in entries:
        if name_counts[entry["name"]] > 1 and entry["source"] == "Map Input":
            entry["name"] = f"{entry['name']} (Map Input)"
    return entries


class MapBrowser(QtWidgets.QWidget):
    def __init__(self, load_maps, parent=None):
        super().__init__(parent)
        self._load_maps = load_maps

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        controls = QtWidgets.QHBoxLayout()
        self.search_bar = QtWidgets.QLineEdit(self)
        self.search_bar.setPlaceholderText("Search maps...")
        controls.addWidget(self.search_bar, stretch=1)

        self.refresh_button = QtWidgets.QPushButton("Refresh", self)
        self.refresh_button.setToolTip("Reload maps from the configured directory")
        controls.addWidget(self.refresh_button)
        layout.addLayout(controls)

        self.list_widget = QtWidgets.QListWidget(self)
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.list_widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.list_widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        layout.addWidget(self.list_widget, stretch=1)

        self.empty_label = QtWidgets.QLabel(self)
        self.empty_label.setWordWrap(True)
        layout.addWidget(self.empty_label)

        self.search_bar.textChanged.connect(self._filter_maps)
        self.refresh_button.clicked.connect(self.refresh)
        self.refresh()

    def refresh(self):
        selected_map = self.list_widget.currentItem()
        selected_name = selected_map.text() if selected_map else None
        paths_differ = map_paths_differ()
        maps = self._load_maps(paths_differ and show_both_map_paths())
        self.list_widget.clear()
        for map_entry in maps:
            item = QtWidgets.QListWidgetItem(map_entry["name"])
            item.setData(QtCore.Qt.UserRole, map_entry["path"])
            item.setData(QtCore.Qt.UserRole + 1, map_entry["relative_path"])
            self.list_widget.addItem(item)
        self._filter_maps(self.search_bar.text())

        if selected_name:
            matches = self.list_widget.findItems(
                selected_name,
                QtCore.Qt.MatchExactly,
            )
            if matches and not matches[0].isHidden():
                self.list_widget.setCurrentItem(matches[0])

    def _filter_maps(self, search_text):
        query = search_text.casefold().strip()
        visible_count = 0
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            visible = query in item.text().casefold()
            item.setHidden(not visible)
            visible_count += visible

        if self.list_widget.currentItem() and self.list_widget.currentItem().isHidden():
            self.list_widget.setCurrentRow(-1)

        if self.list_widget.count() == 0:
            self.empty_label.setText("No maps found in the configured directories.")
        elif visible_count == 0:
            self.empty_label.setText("No maps match this search.")
        else:
            self.empty_label.clear()