from PySide6 import QtWidgets, QtCore, QtGui
import sys
import random
from tabs import decompile, recompile, settings, entity_viewer as ev
class Window(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.window_title = "Min's Testing Window"
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(decompile.window(), "Decompile")
        self.tabs.addTab(recompile.window(), "Recompile")
        self.tabs.addTab(ev.window(), "Entity Viewer")
        self.tabs.addTab(
            settings.SettingsWindow(("Portal 2 Bin", "Map Output Path")),
            "Settings",
        )
        self.layout = QtWidgets.QVBoxLayout(self)
        self.setWindowTitle(self.window_title)
        self.layout.addWidget(self.tabs)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = Window()
    widget.resize(600, 600)
    widget.show()

    sys.exit(app.exec())