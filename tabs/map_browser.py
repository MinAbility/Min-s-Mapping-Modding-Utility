from PySide6 import QtCore, QtWidgets


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
        maps = self._load_maps()
        self.list_widget.clear()
        self.list_widget.addItems(maps)
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
            self.empty_label.setText("No maps found in the specified output directory.")
        elif visible_count == 0:
            self.empty_label.setText("No maps match this search.")
        else:
            self.empty_label.clear()