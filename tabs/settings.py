import json
from pathlib import Path
import sys

from PySide6 import QtWidgets

def load_settings(json_path="settings.json"):
    settings_path = Path(json_path)
    if not settings_path.exists():
        return {}
    try:
        with settings_path.open("r", encoding="utf-8") as settings_file:
            data = json.load(settings_file)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not read settings: {error}", file=sys.stderr)
        return {}

def SettingsWindow(input_names=("Setting 1",), json_path="settings.json"):
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QFormLayout(widget)
    inputs = {}
    saved_settings = load_settings(json_path)

    for name in input_names:
        input_field = QtWidgets.QLineEdit(widget)
        input_field.setObjectName(name)
        input_field.setText(str(saved_settings.get(name, "")))
        inputs[name] = input_field
        layout.addRow(name, input_field)

    save_button = QtWidgets.QPushButton("Save", widget)
    status_label = QtWidgets.QLabel(widget)
    layout.addRow(save_button)
    layout.addRow(status_label)

    def save_settings():
        data = {name: field.text() for name, field in inputs.items()}
        try:
            with Path(json_path).open("w", encoding="utf-8") as settings_file:
                json.dump(data, settings_file, indent=2)
                settings_file.write("\n")
        except OSError as error:
            status_label.setText(f"Could not save settings: {error}")
        else:
            status_label.setText(f"Saved to {json_path}")

    save_button.clicked.connect(save_settings)

    return widget