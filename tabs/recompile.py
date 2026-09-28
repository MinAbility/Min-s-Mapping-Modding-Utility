import json
import sys
from pathlib import Path
from PySide6 import QtCore, QtGui, QtWidgets

SETTINGS_FILENAME = "settings.json"

def _load_all_settings():
    settings_path = Path(SETTINGS_FILENAME)
    if not settings_path.exists():
        return {}, settings_path
    try:
        with settings_path.open("r", encoding="utf-8") as settings_file:
            data = json.load(settings_file)
            return (data if isinstance(data, dict) else {}), settings_path
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not read settings: {error}", file=sys.stderr)
        return {}, settings_path


def get_setting(setting_name):
    data, _ = _load_all_settings()
    if setting_name == "Map Output":
        return data.get("Map Output", data.get("Map Output Path"))
    return data.get(setting_name)


def resolve_portal2_paths(root_value):
    if not root_value:
        return None, None, "no value set"

    root = Path(root_value)
    if not root.exists():
        return None, None, f"path does not exist: {root}"

    if (root / "bin").exists() and (root / "portal2").exists():
        return root / "portal2", root / "bin", f"resolved as install root: {root}"

    if root.name.lower() == "portal2" and (root.parent / "bin").exists():
        return root, root.parent / "bin", f"resolved as game folder, bin at: {root.parent / 'bin'}"

    if root.name.lower() == "bin" and (root.parent / "portal2").exists():
        return root.parent / "portal2", root, f"resolved as bin folder, game at: {root.parent / 'portal2'}"

    return None, None, f"could not find bin/ and portal2/ under or around: {root}"


def return_maps():
    maps_path = get_setting("Map Output")
    if not maps_path:
        return []

    maps_dir = Path(maps_path)
    if not maps_dir.exists():
        return []
    return sorted(
        path.relative_to(maps_dir).as_posix()
        for path in maps_dir.rglob("*.vmf")
        if path.is_file()
    )


class CompileOptionsDialog(QtWidgets.QDialog):

    def __init__(self, map_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compile Options")
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(f"Compiling: {map_name}"))

        # --- Run BSP ---
        bsp_box = QtWidgets.QGroupBox("Run BSP")
        bsp_layout = QtWidgets.QVBoxLayout(bsp_box)
        self.bsp_no = QtWidgets.QRadioButton("No")
        self.bsp_normal = QtWidgets.QRadioButton("Normal")
        self.bsp_onlyents = QtWidgets.QRadioButton("Only Entities")
        self.bsp_onlyents.setToolTip("-onlyents: re-embed entities only, skip geometry rebuild")
        self.bsp_normal.setChecked(True)
        for rb in (self.bsp_no, self.bsp_normal, self.bsp_onlyents):
            bsp_layout.addWidget(rb)
        layout.addWidget(bsp_box)

        # --- Run VIS ---
        vis_box = QtWidgets.QGroupBox("Run VIS")
        vis_layout = QtWidgets.QVBoxLayout(vis_box)
        self.vis_no = QtWidgets.QRadioButton("No")
        self.vis_normal = QtWidgets.QRadioButton("Normal")
        self.vis_fast = QtWidgets.QRadioButton("Fast")
        self.vis_fast.setToolTip("-fast: quick, inaccurate visibility for testing")
        self.vis_normal.setChecked(True)
        for rb in (self.vis_no, self.vis_normal, self.vis_fast):
            vis_layout.addWidget(rb)
        layout.addWidget(vis_box)

        # --- Run RAD ---
        rad_box = QtWidgets.QGroupBox("Run RAD")
        rad_layout = QtWidgets.QVBoxLayout(rad_box)
        self.rad_no = QtWidgets.QRadioButton("No (skip lighting / VRAD)")
        self.rad_no.setToolTip("Skip VRAD entirely; the compile will have no newly computed lighting")
        self.rad_normal = QtWidgets.QRadioButton("Normal")
        self.rad_fast = QtWidgets.QRadioButton("Fast")
        self.rad_fast.setToolTip("-bounce 2 -noextra: quick, rough lighting for testing")
        self.rad_normal.setChecked(True)
        for rb in (self.rad_no, self.rad_normal, self.rad_fast):
            rad_layout.addWidget(rb)

        self.rad_hdr = QtWidgets.QCheckBox("HDR (-both)")
        self.rad_hdr.setToolTip("Adds HDR lightmaps alongside LDR; increases VRAD time")
        rad_layout.addWidget(self.rad_hdr)
        layout.addWidget(rad_box)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def bsp_choice(self):
        if self.bsp_no.isChecked():
            return "no"
        if self.bsp_onlyents.isChecked():
            return "onlyents"
        return "normal"

    def vis_choice(self):
        if self.vis_no.isChecked():
            return "no"
        if self.vis_fast.isChecked():
            return "fast"
        return "normal"

    def rad_choice(self):
        if self.rad_no.isChecked():
            return "no"
        if self.rad_fast.isChecked():
            return "fast"
        return "normal"

    def hdr_enabled(self):
        return self.rad_hdr.isChecked() and self.rad_choice() != "no"


class MapCompilerTab(QtWidgets.QWidget):
    STEPS = ["vbsp", "vvis", "vrad"]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.maps_dir = None
        self.game_dir = None
        self.bin_dir = None
        self.pending_steps = []
        self.current_map_path = None
        self.process = None
        self.bsp_choice = "normal"
        self.vis_choice = "normal"
        self.rad_choice = "normal"
        self.hdr_enabled = False

        self._build_ui()
        self._load_settings()
        self._populate_maps()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        layout.addWidget(splitter, stretch=1)

        # Left: map list + controls
        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)

        self.map_search = QtWidgets.QLineEdit()
        self.map_search.setPlaceholderText("Search maps...")
        self.map_search.textChanged.connect(self._filter_maps)
        left_layout.addWidget(self.map_search)

        self.list_widget = QtWidgets.QListWidget()
        font = self.list_widget.font()
        font.setPixelSize(18)
        self.list_widget.setFont(font)
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.list_widget.itemSelectionChanged.connect(self._update_button_state)
        left_layout.addWidget(self.list_widget, stretch=1)

        button_row = QtWidgets.QHBoxLayout()
        self.refresh_button = QtWidgets.QPushButton("Refresh List")
        self.refresh_button.clicked.connect(self._populate_maps)
        button_row.addWidget(self.refresh_button)

        self.compile_button = QtWidgets.QPushButton("Compile")
        self.compile_button.clicked.connect(self._start_compile)
        self.compile_button.setEnabled(False)
        button_row.addWidget(self.compile_button)

        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._cancel_compile)
        self.cancel_button.setEnabled(False)
        button_row.addWidget(self.cancel_button)

        left_layout.addLayout(button_row)
        splitter.addWidget(left)

        # Right: log output
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.addWidget(QtWidgets.QLabel("Compile Log"))

        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QtGui.QFont("Consolas", 10))
        right_layout.addWidget(self.log_view, stretch=1)
        splitter.addWidget(right)

        splitter.setSizes([300, 500])

        self.status_label = QtWidgets.QLabel("")
        layout.addWidget(self.status_label)

    def _load_settings(self):
        all_settings, settings_path = _load_all_settings()

        maps_path = all_settings.get("Map Output", all_settings.get("Map Output Path"))
        self.maps_dir = Path(maps_path) if maps_path else None

        game_root = all_settings.get("Portal 2 Bin")
        self.game_dir, self.bin_dir, resolve_note = resolve_portal2_paths(game_root)

        status_parts = []
        status_parts.append(f"settings.json: {settings_path.resolve()}")
        status_parts.append(f"keys found: {list(all_settings.keys()) or 'none'}")

        if not self.maps_dir or not self.maps_dir.exists():
            status_parts.append("Map Output: missing or invalid")
        if not self.bin_dir:
            status_parts.append(f"Portal 2 Directory: {resolve_note}")
        else:
            status_parts.append(f"Portal 2 Directory: {resolve_note}")

        self.status_label.setText(" | ".join(status_parts))
        self.status_label.setWordWrap(True)

    def _populate_maps(self):
        self._load_settings()
        self.list_widget.clear()

        if not self.maps_dir or not self.maps_dir.exists():
            self.compile_button.setEnabled(False)
            return

        maps = return_maps()
        if not maps:
            self.status_label.setText("No VMF files found in the specified output path.")
            self.compile_button.setEnabled(False)
            return

        for rel_path in maps:
            item = QtWidgets.QListWidgetItem(rel_path)
            item.setData(QtCore.Qt.UserRole, str(self.maps_dir / rel_path))
            self.list_widget.addItem(item)
        self._filter_maps(self.map_search.text())

    def _filter_maps(self, search_text):
        query = search_text.casefold().strip()
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            item.setHidden(query not in item.text().casefold())
        current_item = self.list_widget.currentItem()
        if current_item and current_item.isHidden():
            self.list_widget.setCurrentRow(-1)

    def _update_button_state(self):
        has_selection = bool(self.list_widget.selectedItems())
        tools_ready = bool(self.bin_dir and self.bin_dir.exists())
        self.compile_button.setEnabled(has_selection and tools_ready and self.process is None)

    # ---------- Compile pipeline ----------

    def _start_compile(self):
        selected = self.list_widget.selectedItems()
        if not selected:
            return

        self.current_map_path = Path(selected[0].data(QtCore.Qt.UserRole))

        dialog = CompileOptionsDialog(self.current_map_path.name, self)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return

        self.bsp_choice = dialog.bsp_choice()
        self.vis_choice = dialog.vis_choice()
        self.rad_choice = dialog.rad_choice()
        self.hdr_enabled = dialog.hdr_enabled()

        self.pending_steps = [
            step for step, choice in (
                ("vbsp", self.bsp_choice),
                ("vvis", self.vis_choice),
                ("vrad", self.rad_choice),
            )
            if choice != "no"
        ]

        if not self.pending_steps:
            return

        self.log_view.clear()
        self._log(
            f"Starting compile for {self.current_map_path.name}\n"
            f"  BSP: {self.bsp_choice} | VIS: {self.vis_choice} | "
            f"RAD: {self.rad_choice}"
            f"{' (lighting skipped)' if self.rad_choice == 'no' else ''}"
            f"{' + HDR' if self.hdr_enabled else ''}\n"
        )

        self.compile_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.refresh_button.setEnabled(False)

        self._run_next_step()

    def _cancel_compile(self):
        if self.process is not None:
            self._log("\nCancelling compile...\n")
            self.process.kill()
        self.pending_steps = []

    def _run_next_step(self):
        if not self.pending_steps:
            self._log("\nCompile finished.\n")
            self._finish_compile()
            return

        step = self.pending_steps.pop(0)
        exe_name, args = self._build_step_command(step)
        exe_path = self.bin_dir / exe_name

        if not exe_path.exists():
            self._log(f"\nERROR: could not find {exe_path}\n")
            self._finish_compile()
            return

        self._log(f"\n--- Running {exe_name} {' '.join(args)} ---\n")

        self.process = QtCore.QProcess(self)
        self.process.setProgram(str(exe_path))
        self.process.setArguments(args)
        self.process.setWorkingDirectory(str(self.bin_dir))
        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.finished.connect(self._on_step_finished)
        self.process.start()

    def _build_step_command(self, step):
        game_arg = ["-game", str(self.game_dir)]
        map_stem = str(self.current_map_path)  # VBSP accepts full path to the .vmf

        if step == "vbsp":
            extra = ["-onlyents"] if self.bsp_choice == "onlyents" else []
            return "vbsp.exe", [*game_arg, *extra, map_stem]

        if step == "vvis":
            extra = ["-fast"] if self.vis_choice == "fast" else []
            return "vvis.exe", [*game_arg, *extra, map_stem]

        if step == "vrad":
            hdr_args = ["-both"] if self.hdr_enabled else []
            extra = ["-bounce", "2", "-noextra"] if self.rad_choice == "fast" else []
            return "vrad.exe", [*game_arg, *hdr_args, *extra, map_stem]

        raise ValueError(f"Unknown compile step: {step}")

    def _read_stdout(self):
        if self.process:
            data = self.process.readAllStandardOutput().data().decode(errors="replace")
            self._log(data)

    def _read_stderr(self):
        if self.process:
            data = self.process.readAllStandardError().data().decode(errors="replace")
            self._log(data)

    def _on_step_finished(self, exit_code, exit_status):
        if exit_code != 0 or exit_status == QtCore.QProcess.CrashExit:
            self._log(f"\nStep exited with code {exit_code}. Stopping compile.\n")
            self.pending_steps = []

        self.process = None
        self._run_next_step()

    def _finish_compile(self):
        self.process = None
        self.cancel_button.setEnabled(False)
        self.refresh_button.setEnabled(True)
        self._update_button_state()

    def _log(self, text):
        self.log_view.moveCursor(QtGui.QTextCursor.End)
        self.log_view.insertPlainText(text)
        self.log_view.moveCursor(QtGui.QTextCursor.End)


def window():
    return MapCompilerTab()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = window()
    win.setWindowTitle("Map Compiler")
    win.resize(900, 600)
    win.show()
    sys.exit(app.exec())