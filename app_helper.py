import os
import sys
from functools import partial

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtGui import QFont, QMouseEvent, QIcon
from PyQt5.QtWidgets import QLineEdit, QWidget, QHBoxLayout, QComboBox, QMainWindow, QPlainTextEdit, QPushButton, \
    QColorDialog, QGridLayout, QLabel


class FramelessWindow(QMainWindow):
    def __init__(self, parent: QMainWindow = None):
        super().__init__(parent)
        self.parent = parent
        if parent:
            self.parent.children.append(self)
        self.children = []
        self.oldPosition = self.pos()
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.oldPosition = event.globalPos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        delta = QPoint(event.globalPos() - self.oldPosition)
        self.shift_positions(delta, event)

    def shift_positions(self, delta, event: QMouseEvent, ignore_parent=False):
        if self.parent and not ignore_parent:
            self.parent.shift_positions(delta, event)
            return
        self.move_delta(delta, event)
        for child in self.children:
            child.shift_positions(delta, event, ignore_parent=True)

    def move_delta(self, delta, event: QMouseEvent):
        if abs(delta.x()) + abs(delta.y()) > 1000:
            return

        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPosition = event.globalPos()


class DragButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.parent = parent
        if parent:
            self.parent.children.append(self)
        self.children = []
        self.oldPosition = self.pos()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.oldPosition = event.globalPos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        delta = QPoint(event.globalPos() - self.pos())
        self.shift_positions(delta, event)

    def shift_positions(self, delta, event: QMouseEvent, ignore_parent=False):
        if self.parent and not ignore_parent:
            self.parent.shift_positions(delta, event)
            return

class AutoUpdateTextfield(QPlainTextEdit):
    def __init__(self, parent, alt_text, subfolder, field_name):
        super().__init__(parent)
        self.parent = parent
        self.subfolder = subfolder
        self.field_name = field_name
        self.textChanged.connect(self.save_text)
        self.setPlainText(subfolder.get(field_name, alt_text))
        self.setWordWrapMode(True)

    def save_text(self):
        self.subfolder[self.field_name] = self.toPlainText()


class TextfieldWithUpdateTrigger(QLineEdit):
    def __init__(self, parent, func):
        super().__init__(parent)
        self.func = func
        self.parent = parent
        self.textChanged.connect(self.apply_function_w_text_input)
        self.setText("")

    def mousePressEvent(self, e):
        self.selectAll()

    def apply_function_w_text_input(self):
        self.func(self.text())


def text_field(parent, text_box_name, initial_string):
    setattr(parent, text_box_name, QLineEdit(parent))
    textbox = getattr(parent, text_box_name)
    textbox.move(20, 20)
    textbox.resize(280, 40)
    textbox.setText(initial_string)
    return textbox


def setup_button(button, dimension, number, height, click_event, image_address=None):
    button.resize(dimension[0], dimension[1])
    button.move(11 + number * dimension[0], height)
    button.clicked.connect(partial(click_event, button))
    if image_address:
        button.setIcon(QIcon(image_address))
    return button


class ColorPickerButtonGrid(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QGridLayout()
        layout.addWidget(QLabel("Filter Colors", self), 0, 0, 1, 0)
        layout.setHorizontalSpacing(0)
        layout.setVerticalSpacing(0)
        positions = [(i, j) for i in range(1, 5) for j in range(2)]

        for color, position in zip(self.parent.parent.state["colors"].items(), positions):
            layout.addWidget(ColorPickerButton(self, color[0], color[1]), *position)
        self.setLayout(layout)
        self.show()


class ColorPickerButton(QPushButton):
    def __init__(self, parent, label, default_color):
        super().__init__(parent)
        self.clicked.connect(self.pick_color)
        self.parent = parent
        self.setText(label)
        self.label = label
        self.show()
        self.setStyleSheet(f"background-color: {rgb_to_hex(default_color)}")

    def pick_color(self):
        color = QColorDialog.getColor()
        self.setStyleSheet(f"background-color: {color.name()}")
        self.parent.parent.parent.state["colors"][self.label] = [color.red(), color.green(), color.blue()]
        self.parent.parent.parent.button_menu.refresh_buttons()


def rgb_to_hex(rgb):
    return '#' + '%02x%02x%02x' % tuple(rgb)


class IconButton(QWidget):
    def __init__(self, parent, icon, color, counter):
        super().__init__(parent)
        self.icon = QPushButton(self)
        self.icon.setGeometry(0, 0, 45, 45)
        image_address = os.path.join(os.path.abspath(os.getcwd()), "Assets", f"{icon}.png")
        self.icon.setIcon(QIcon(image_address))
        self.counter = QPushButton(self)
        self.counter.setGeometry(0, 0, 20, 20)

        self.set_color_and_counter(color, counter)
        self.show()

    def set_color_and_counter(self, color, counter):
        self.icon.setStyleSheet(f"background-color: {rgb_to_hex(color)}")
        self.counter.setText(str(counter))


def setup_icon_button(button, dimension, number, height, icon_name):
    image_address = os.path.abspath(os.getcwd()) + r"\Assets\\" + icon_name + '.png'
    button.resize(dimension[0], dimension[1])
    button.move(number * dimension[0], height)
    if image_address:
        button.setIcon(QIcon(image_address))

    button.children()
    return button


def setup_icon_enum_button(button, counter, dimension, number, height):
    button.resize(20, 20)
    button.move(number * dimension[0] + dimension[0] - 20, height)
    button.setStyleSheet("background-color: white")
    button.setText(str(counter))
    font = QFont('Arial', 8)
    font.setBold(True)
    button.setFont(font)
    return button


class generalized_drop_down(QWidget):
    def __init__(self, items, current, geometry, index_change_function, parent=None):
        super(generalized_drop_down, self).__init__(parent)

        layout = QHBoxLayout()
        self.parent = parent
        self.cb = QComboBox()
        self.cb.addItems(items)
        self.index_change_function = index_change_function
        self.cb.currentIndexChanged.connect(self.selection_change)
        index = [idx for idx, x in enumerate(items) if x == current]
        self.cb.setCurrentIndex(index[0] if index else 0)
        layout.addWidget(self.cb)
        self.setLayout(layout)
        self.setGeometry(*geometry)

    def selection_change(self):
        self.index_change_function(self.cb.currentText())


class drop_down(QComboBox):
    def __init__(self, items, current, attribute, geometry=None, parent=None):
        super(drop_down, self).__init__(parent)

        self.parent = parent
        self.attribute = attribute
        self.items = items
        self.set_up(items, current)
        self.currentIndexChanged.connect(self.selection_change)
        if geometry:
            self.setGeometry(*geometry)

    def set_up(self, items, current_choice):
        for _ in range(len(self.items)):
            self.removeItem(0)
        self.addItems(items)
        index = [idx for idx, x in enumerate(items) if x == current_choice]
        self.setCurrentIndex(index[0] if index else 0)

    def selection_change(self):
        self.parent.state[self.attribute] = self.currentText()


def split_address_file_name(string, extension):
    idx = 0
    for idx in range(len(string), 0, -1):
        if string[idx - 1] == "/":
            break
    return string[:idx], string[idx:-(len(extension) + 1)]


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)
