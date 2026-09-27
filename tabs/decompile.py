import json
import os
from pathlib import Path
import sys
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
        for path in maps_dir.rglob("*.bsp")
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

    decompile_button = QtWidgets.QPushButton("Decompile", widget)
    decompile_button.setEnabled(False)
    layout.addWidget(decompile_button, alignment=QtCore.Qt.AlignRight)

    status_label = QtWidgets.QLabel(widget)
    status_label.setWordWrap(True)
    layout.addWidget(status_label)

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
        maps_path = get_setting("Map Output Path")
        if not selected_item or not maps_path:
            status_label.setText("Select a map and set the Map Output Path.")
            return

        maps_directory = Path(maps_path).expanduser()
        map_path = maps_directory / selected_item.text()
        output_path = map_path.with_suffix(".vmf")
        process_output.clear()
        process.start("bspsrc", [f"--output={output_path}", str(map_path)])
        status_label.setText(f"Starting decompile for {selected_item.text()}...")

    if map_list is not None:
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