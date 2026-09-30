from PySide6 import QtWidgets, QtCore, QtGui
import sys
from tabs import decompile, recompile, settings, entity_viewer as ev, material_viewer as mv, addscript, gel
from tabs.map_browser import MapBrowser
class Window(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.window_title = "Min's Modding & Mapping Tool"
        self.toolbar = QtWidgets.QToolBar("Scripts", self)
        self.toolbar.setMovable(False)
        self.script_actions = {}
        self.running_scripts = []
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(decompile.window(), "Decompile")
        self.tabs.addTab(recompile.window(), "Recompile")
        self.tabs.addTab(ev.window(), "Entity Viewer")
        self.tabs.addTab(mv.window(), "Material Viewer")
        self.tabs.addTab(
            settings.SettingsWindow(("Portal 2 Bin", "Map Input", "Map Output", "BSPSRC Jar File Path", "")),
            "Settings",
        )
        self.script_manager = addscript.window()
        self.tabs.addTab(self.script_manager, "Add Script")
        self.tabs.currentChanged.connect(self._refresh_current_map_browser)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.setWindowTitle(self.window_title)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.tabs)

        self.script_manager.scriptAdded.connect(self.add_script_action)
        self.script_manager.scriptRemoved.connect(self.remove_script_action)
        for script_path in self.script_manager.scripts:
            self.add_script_action(script_path)

        self._zoom_factor = 1.0
        self._base_fonts = {
            child: child.font()
            for child in [self, *self.findChildren(QtWidgets.QWidget)]
        }
        self._zoom_shortcuts = []
        for key_sequence, change in (
            (QtGui.QKeySequence.ZoomIn, 0.1),
            (QtGui.QKeySequence.ZoomOut, -0.1),
        ):
            shortcut = QtGui.QShortcut(key_sequence, self)
            shortcut.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(
                lambda change=change: self._change_zoom(change)
            )
            self._zoom_shortcuts.append(shortcut)

        reset_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+0"), self)
        reset_shortcut.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        reset_shortcut.activated.connect(lambda: self._set_zoom(1.0))
        self._zoom_shortcuts.append(reset_shortcut)

    def _refresh_current_map_browser(self, index):
        current_tab = self.tabs.widget(index)
        map_browser = current_tab.findChild(MapBrowser) if current_tab else None
        if map_browser is not None:
            map_browser.refresh()

    def add_script_action(self, script_path):
        if script_path in self.script_actions:
            return
        action = self.toolbar.addAction(QtCore.QFileInfo(script_path).completeBaseName())
        action.setToolTip(script_path)
        action.triggered.connect(
            lambda _checked=False, path=script_path: self.run_script(path)
        )
        self.script_actions[script_path] = action

    def remove_script_action(self, script_path):
        action = self.script_actions.pop(script_path, None)
        if action is not None:
            self.toolbar.removeAction(action)
            action.deleteLater()

    def run_script(self, script_path):
        script = QtCore.QFileInfo(script_path)
        if not script.exists() or not script.isFile():
            self.script_manager.report_status(f"Script not found: {script_path}")
            return

        process = QtCore.QProcess(self)
        process.setWorkingDirectory(script.absolutePath())
        process.finished.connect(
            lambda exit_code, _exit_status, running_process=process, path=script_path:
            self._script_finished(running_process, path, exit_code)
        )
        process.errorOccurred.connect(
            lambda _error, running_process=process, path=script_path:
            self._script_error(running_process, path)
        )
        self.running_scripts.append(process)
        self.script_manager.report_status(f"Running {script.fileName()}...")
        process.start(sys.executable, [script_path])

    def _script_finished(self, process, script_path, exit_code):
        if process in self.running_scripts:
            self.running_scripts.remove(process)
        name = QtCore.QFileInfo(script_path).fileName()
        if exit_code == 0:
            self.script_manager.report_status(f"Finished {name}.")
        else:
            self.script_manager.report_status(
                f"{name} exited with code {exit_code}."
            )
        process.deleteLater()

    def _script_error(self, process, script_path):
        if process in self.running_scripts:
            self.running_scripts.remove(process)
        name = QtCore.QFileInfo(script_path).fileName()
        self.script_manager.report_status(
            f"Could not run {name}: {process.errorString()}"
        )
        process.deleteLater()

    def _change_zoom(self, change):
        self._set_zoom(self._zoom_factor + change)

    def _set_zoom(self, zoom_factor):
        self._zoom_factor = max(0.7, min(2.0, zoom_factor))
        for widget, base_font in self._base_fonts.items():
            font = QtGui.QFont(base_font)
            if base_font.pixelSize() > 0:
                font.setPixelSize(max(1, round(base_font.pixelSize() * self._zoom_factor)))
            elif base_font.pointSizeF() > 0:
                font.setPointSizeF(base_font.pointSizeF() * self._zoom_factor)
            widget.setFont(font)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = Window()
    widget.resize(600, 600)
    widget.show()

    sys.exit(app.exec())
