import json
import os
from pathlib import Path
import shutil
import sys
from PySide6 import QtWidgets, QtCore, QtGui
from tabs.map_browser import MapBrowser, load_map_files
from paths import SETTINGS_PATH

def get_setting(setting_name):
    settings_path = SETTINGS_PATH
    if not settings_path.exists():
        return None
    try:
        with settings_path.open("r", encoding="utf-8") as settings_file:
            data = json.load(settings_file)
            if setting_name == "Map Input":
                return data.get("Map Input", data.get("Map Input Path"))
            return data.get(setting_name)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not read settings: {error}", file=sys.stderr)
        return None

def return_maps(include_both_paths=False):
    return load_map_files("Map Input", ".bsp", include_both_paths)


class BspFileDropFilter(QtCore.QObject):
    def __init__(self, add_files, parent=None):
        super().__init__(parent)
        self._add_files = add_files

    @staticmethod
    def bsp_files_from_event(event):
        if not event.mimeData().hasUrls():
            return []
        return [
            Path(url.toLocalFile()).resolve()
            for url in event.mimeData().urls()
            if url.isLocalFile()
            and Path(url.toLocalFile()).is_file()
            and Path(url.toLocalFile()).suffix.casefold() == ".bsp"
        ]

    def eventFilter(self, watched, event):
        if event.type() in (QtCore.QEvent.DragEnter, QtCore.QEvent.DragMove):
            if self.bsp_files_from_event(event):
                event.acceptProposedAction()
                return True
        elif event.type() == QtCore.QEvent.Drop:
            bsp_files = self.bsp_files_from_event(event)
            if bsp_files:
                self._add_files(bsp_files)
                event.acceptProposedAction()
                return True
        return super().eventFilter(watched, event)


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

def window():
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(widget)
    dropped_paths = []

    def load_decompile_maps(include_both_paths=False):
        maps = load_map_files("Map Input", ".bsp", include_both_paths)
        known_paths = {
            os.path.normcase(str(Path(entry["path"]).resolve()))
            for entry in maps
        }
        for map_path in dropped_paths:
            path_key = os.path.normcase(str(map_path))
            if path_key in known_paths:
                continue
            maps.append({
                "name": f"{map_path.name} ({map_path.parent})",
                "relative_path": map_path.name,
                "path": str(map_path),
                "source": "Dropped",
            })
            known_paths.add(path_key)
        return maps

    map_browser = MapBrowser(load_decompile_maps, widget)
    map_list = map_browser.list_widget
    layout.addWidget(map_browser, stretch=1)

    include_assets_checkbox = QtWidgets.QCheckBox("Include assets from map?", widget)
    layout.addWidget(include_assets_checkbox)

    decompile_button = QtWidgets.QPushButton("Decompile", widget)
    decompile_button.setEnabled(False)
    layout.addWidget(decompile_button, alignment=QtCore.Qt.AlignRight)

    status_label = QtWidgets.QLabel(widget)
    status_label.setWordWrap(True)
    layout.addWidget(status_label)

    def add_dropped_files(paths):
        for map_path in paths:
            if map_path not in dropped_paths:
                dropped_paths.append(map_path)
        map_browser.refresh()
        latest_path = paths[-1]
        for index in range(map_list.count()):
            item = map_list.item(index)
            if Path(item.data(QtCore.Qt.UserRole)).resolve() == latest_path:
                map_list.setCurrentItem(item)
                break
        status_label.setText(f"Added {len(paths)} BSP file(s) from drag and drop.")

    drop_filter = BspFileDropFilter(add_dropped_files, map_list)
    widget.bsp_drop_filter = drop_filter
    map_list.setAcceptDrops(True)
    map_list.viewport().setAcceptDrops(True)
    map_list.viewport().installEventFilter(drop_filter)

    process = QtCore.QProcess(widget)
    widget.decompile_process = process
    process_output = []
    output_path = None

    def capture_process_output():
        standard_output = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
        standard_error = bytes(process.readAllStandardError()).decode("utf-8", errors="replace")
        if standard_output:
            process_output.append(standard_output)
        if standard_error:
            process_output.append(standard_error)

    def start_decompile():
        nonlocal output_path
        selected_item = map_list.currentItem()
        output_directory = get_setting("Map Output")
        if not selected_item or not output_directory:
            status_label.setText("Select a map and set the Map Input and Map Output.")
            return

        map_relative_path = Path(selected_item.data(QtCore.Qt.UserRole + 1))
        map_path = Path(selected_item.data(QtCore.Qt.UserRole))
        output_path = Path(output_directory).expanduser() / map_relative_path.with_suffix(".vmf")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        process_output.clear()
        bspsrc_arguments = [f"--output={output_path}"]
        if include_assets_checkbox.isChecked():
            bspsrc_arguments.append("--unpack_embedded")
        bspsrc_arguments.append(str(map_path))

        bundled_jar_candidates = (
            Path(__file__).with_name("bspsrc-jar-only") / "bspsrc.jar",
            Path(__file__).with_name("bspsrc.jar"),
        )
        bspsrc_jar = next(
            (candidate for candidate in bundled_jar_candidates if candidate.is_file()),
            bundled_jar_candidates[0],
        )
        if not bspsrc_jar.is_file():
            status_label.setText(f"Bundled BSPSrc JAR not found: {bspsrc_jar}")
            return

        java_executable = shutil.which("java")
        if not java_executable:
            status_label.setText("Java Runtime missing, please install it before continuing")
            return

        process.start(
            java_executable,
            [
                "-cp",
                str(bspsrc_jar),
                "info.ata4.bspsrc.app.src.BspSourceLauncher",
            ] + bspsrc_arguments,
        )
        status_label.setText(f"Starting decompile for {selected_item.text()}...")

    map_list.itemSelectionChanged.connect(
        lambda: decompile_button.setEnabled(map_list.currentItem() is not None)
    )
    decompile_button.clicked.connect(start_decompile)

    process.readyReadStandardOutput.connect(capture_process_output)
    process.readyReadStandardError.connect(capture_process_output)

    def decompile_finished(exit_code, _exit_status):
        capture_process_output()
        if exit_code == 0:
            if output_path is not None and output_path.is_file():
                status_label.setText(f"Decompilation completed: {output_path}")
            else:
                status_label.setText(f"BSPSrc finished but did not create {output_path}.")
            return

        details = "".join(process_output).strip()
        message = f"BSPSrc exited with code {exit_code}."
        if details:
            message += f"\n{details[-500:]}"
        status_label.setText(message)

    process.finished.connect(decompile_finished)
    process.errorOccurred.connect(
        lambda _error: status_label.setText(f"Could not start BSPSrc: {process.errorString()}")
    )

    return widget