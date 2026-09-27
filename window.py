from PySide6 import QtWidgets, QtCore, QtGui
import sys
import random
from tabs import decompile, recompile, settings, entity_viewer as ev, material_viewer as mv
class Window(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.window_title = "Min's Modding & Mapping Tool"
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(decompile.window(), "Decompile")
        self.tabs.addTab(recompile.window(), "Recompile")
        self.tabs.addTab(ev.window(), "Entity Viewer")
        self.tabs.addTab(mv.window(), "Material Viewer")
        self.tabs.addTab(
            settings.SettingsWindow(("Portal 2 Bin", "Map Output")),
            "Settings",
        )
        self.layout = QtWidgets.QVBoxLayout(self)
        self.setWindowTitle(self.window_title)
        self.layout.addWidget(self.tabs)

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