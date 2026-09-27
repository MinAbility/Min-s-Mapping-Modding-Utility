import re
import sys
import json
from pathlib import Path
from PySide6 import QtWidgets, QtCore

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
        for path in maps_dir.rglob("*.vmf")
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

def parse_map(map_path):
    map_path = Path(map_path)
    with map_path.open("r", encoding="utf-8-sig") as map_file:
        contents = map_file.read()

    tokens = [
        match.group(0)
        for match in re.finditer(r'\s+|//[^\r\n]*|"(?:\\.|[^"\\])*"|[{}]|[^\s{}"]+', contents)
        if not match.group(0).isspace() and not match.group(0).startswith("//")
    ]

    def value(token):
        if not token.startswith('"'):
            return token
        try:
            return json.loads(token)
        except json.JSONDecodeError:
            return token[1:-1].replace('\\"', '"').replace('\\\\', '\\')

    entities_by_class = {}
    index = 0
    while index < len(tokens):
        if tokens[index] == "entity" and index + 1 < len(tokens) and tokens[index + 1] == "{":
            index += 2
            depth = 1
            entity = {}
            while index < len(tokens) and depth:
                token = tokens[index]
                if (
                    depth == 1
                    and (
                        token == "connections"
                        or (token.startswith('"') and value(token) == "connections")
                    )
                    and index + 1 < len(tokens)
                    and tokens[index + 1] == "{"
                ):
                    index += 2
                    connection_depth = 1
                    connections = []
                    while index < len(tokens) and connection_depth:
                        if tokens[index] == "{":
                            connection_depth += 1
                            index += 1
                        elif tokens[index] == "}":
                            connection_depth -= 1
                            index += 1
                        elif (
                            connection_depth == 1
                            and tokens[index].startswith('"')
                            and index + 1 < len(tokens)
                            and tokens[index + 1].startswith('"')
                        ):
                            connections.append({
                                "event": value(tokens[index]),
                                "output": value(tokens[index + 1]),
                            })
                            index += 2
                        else:
                            index += 1
                    entity["connections"] = connections
                elif token == "{":
                    depth += 1
                    index += 1
                elif token == "}":
                    depth -= 1
                    index += 1
                elif depth == 1 and token.startswith('"') and index + 1 < len(tokens) and tokens[index + 1].startswith('"'):
                    entity[value(token)] = value(tokens[index + 1])
                    index += 2
                else:
                    index += 1

            classname = entity.get("classname", "<unknown>")
            entities_by_class.setdefault(classname, []).append(entity)
        elif tokens[index] == "{":
            depth = 1
            index += 1
            while index < len(tokens) and depth:
                if tokens[index] == "{":
                    depth += 1
                elif tokens[index] == "}":
                    depth -= 1
                index += 1
        else:
            index += 1

    return entities_by_class

def window():
    maps = return_maps()
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(widget)
    entity_tree = QtWidgets.QTreeWidget(widget)
    entity_tree.setHeaderLabels(["Entity / Property", "Value"])
    entity_tree.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
    header = entity_tree.header()
    header.setStretchLastSection(False)
    header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
    entity_tree.setColumnWidth(0, 260)
    entity_tree.setColumnWidth(1, 420)
    widget.selected_map_path = None
    widget.parsed_map = None

    if not maps:
        map_list = None
        layout.addWidget(QtWidgets.QLabel("No maps found in the specified output path."))
    else:
        map_list = list_maps(maps)
        layout.addWidget(map_list)
        layout.addWidget(entity_tree)

        def load_selected_map():
            selected_item = map_list.currentItem()
            maps_path = get_setting("Map Output Path")
            if selected_item is None or not maps_path:
                return

            map_path = Path(maps_path).expanduser() / selected_item.text()
            try:
                entities_by_class = parse_map(map_path)
            except (OSError, UnicodeDecodeError) as error:
                widget.selected_map_path = None
                widget.parsed_map = None
                entity_tree.clear()
                entity_tree.setHeaderLabels([f"Could not read {map_path}: {error}", ""])
                return

            widget.selected_map_path = map_path
            widget.parsed_map = entities_by_class
            entity_tree.clear()
            entity_tree.setHeaderLabels(["Entity / Property", "Value"])
            for classname, instances in sorted(entities_by_class.items()):
                class_item = QtWidgets.QTreeWidgetItem(
                    [f"{classname} ({len(instances)})", ""]
                )
                entity_tree.addTopLevelItem(class_item)
                for instance_number, properties in enumerate(instances, start=1):
                    instance_item = QtWidgets.QTreeWidgetItem(
                        [f"Instance {instance_number}", ""]
                    )
                    class_item.addChild(instance_item)
                    for key, property_value in properties.items():
                        if key == "connections":
                            continue
                        instance_item.addChild(
                            QtWidgets.QTreeWidgetItem([key, property_value])
                        )
                    connections = properties.get("connections", [])
                    if connections:
                        connections_item = QtWidgets.QTreeWidgetItem(
                            [f"Connections ({len(connections)})", ""]
                        )
                        instance_item.addChild(connections_item)
                        for connection in connections:
                            output_parts = connection["output"].split("\x1b")
                            connection_item = QtWidgets.QTreeWidgetItem(
                                [connection["event"], output_parts[0]]
                            )
                            connections_item.addChild(connection_item)
                            field_names = (
                                "Input",
                                "Parameter",
                                "Delay",
                                "Times to fire",
                            )
                            for field_name, field_value in zip(
                                field_names, output_parts[1:]
                            ):
                                connection_item.addChild(
                                    QtWidgets.QTreeWidgetItem(
                                        [field_name, field_value]
                                    )
                                )

        map_list.currentItemChanged.connect(load_selected_map)
    return widget