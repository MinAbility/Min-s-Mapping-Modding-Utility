import json
from pathlib import Path

from PySide6 import QtCore, QtWidgets


SETTINGS_PATH = Path("settings.json")
SCRIPTS_KEY = "Custom Scripts"


def load_scripts():
    try:
        with SETTINGS_PATH.open("r", encoding="utf-8") as settings_file:
            settings = json.load(settings_file)
    except (OSError, json.JSONDecodeError):
        return []
    scripts = settings.get(SCRIPTS_KEY, []) if isinstance(settings, dict) else []
    return [str(Path(script).expanduser()) for script in scripts if isinstance(script, str)]


def save_scripts(scripts):
    try:
        with SETTINGS_PATH.open("r", encoding="utf-8") as settings_file:
            settings = json.load(settings_file)
            if not isinstance(settings, dict):
                settings = {}
    except (OSError, json.JSONDecodeError):
        settings = {}

    settings[SCRIPTS_KEY] = scripts
    try:
        with SETTINGS_PATH.open("w", encoding="utf-8") as settings_file:
            json.dump(settings, settings_file, indent=2)
            settings_file.write("\n")
    except OSError as error:
        return str(error)
    return None


class ScriptManager(QtWidgets.QWidget):
    scriptAdded = QtCore.Signal(str)
    scriptRemoved = QtCore.Signal(str)

    def __init__(self):
        super().__init__()
        self.scripts = load_scripts()

        layout = QtWidgets.QVBoxLayout(self)
        self.script_list = QtWidgets.QListWidget(self)
        self.script_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        layout.addWidget(self.script_list)

        buttons = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton("Add Script", self)
        self.remove_button = QtWidgets.QPushButton("Remove Script", self)
        self.remove_button.setEnabled(False)
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.remove_button)
        layout.addLayout(buttons)

        self.status_label = QtWidgets.QLabel(self)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        for script in self.scripts:
            self._add_list_item(script)

        self.add_button.clicked.connect(self.choose_script)
        self.remove_button.clicked.connect(self.remove_selected_script)
        self.script_list.currentItemChanged.connect(
            lambda current, _previous: self.remove_button.setEnabled(current is not None)
        )

    def _add_list_item(self, script):
        item = QtWidgets.QListWidgetItem(Path(script).name)
        item.setToolTip(script)
        item.setData(QtCore.Qt.UserRole, script)
        self.script_list.addItem(item)

    def choose_script(self):
        script, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Add Python Script",
            str(Path.home()),
            "Python scripts (*.py)",
        )
        if not script:
            return

        script_path = str(Path(script).expanduser().resolve())
        if not Path(script_path).is_file():
            self.status_label.setText("The selected script does not exist.")
            return
        if script_path in self.scripts:
            self.status_label.setText("That script is already on the toolbar.")
            return

        updated_scripts = [*self.scripts, script_path]
        error = save_scripts(updated_scripts)
        if error:
            self.status_label.setText(f"Could not save script list: {error}")
            return

        self.scripts = updated_scripts
        self._add_list_item(script_path)
        self.scriptAdded.emit(script_path)
        self.status_label.setText(f"Added {Path(script_path).name} to the toolbar.")

    def remove_selected_script(self):
        item = self.script_list.currentItem()
        if item is None:
            return

        script_path = item.data(QtCore.Qt.UserRole)
        updated_scripts = [script for script in self.scripts if script != script_path]
        error = save_scripts(updated_scripts)
        if error:
            self.status_label.setText(f"Could not save script list: {error}")
            return

        self.scripts = updated_scripts
        self.script_list.takeItem(self.script_list.row(item))
        self.scriptRemoved.emit(script_path)
        self.status_label.setText(f"Removed {Path(script_path).name} from the toolbar.")

    def report_status(self, message):
        self.status_label.setText(message)


def window():
    return ScriptManager()
