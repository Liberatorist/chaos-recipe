import json
import sys
from collections import defaultdict

from PyQt5.QtCore import QThreadPool, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QPushButton, QHBoxLayout, QCheckBox, QApplication, QFileDialog, QLabel, \
    QGridLayout, QWidget, QLineEdit, QMainWindow

from app_helper import drop_down, FramelessWindow, split_address_file_name, ColorPickerButtonGrid, except_hook, \
    IconButton
from calibration import identify_empty_inventory, calibrate_box_dimensions, get_screen_size
from filter_manipulation import reset_filter
from input import get_item_locations, get_leagues
from multi_threading import Worker
from peripherals_manipulation import refresh_filter, fill_inventory, clear_inventory


def main():
    app = QApplication(sys.argv)
    w = ChaosRecipe()
    ret = app.exec_()
    w.save_state()
    sys.exit(ret)


class ChaosRecipe(FramelessWindow):

    def __init__(self):
        super().__init__()
        with open("state.json", "r") as file:
            state = defaultdict(dict)
            state.update(json.loads(file.read()))
            self.state = state
            initialize_states(self.state)
        with open("tag_map.json", "r") as file:
            self.tag_map = json.loads(file.read())

        self.icon_buttons = dict()
        self.initUI()
        self.button_menu_state = False

    def initUI(self):
        self.oldPosition = self.pos()
        self.setGeometry(self.state["window_position"][0], self.state["window_position"][1], 380, 40)
        self.set_window_position(300, 40)

        button_width = 65
        layout = QHBoxLayout()

        self.bdeposit = QPushButton('Deposit', self)
        self.bdeposit.clicked.connect(self.inv_clear)
        self.bdeposit.setFixedWidth(button_width)

        self.bgrab = QPushButton('Grab', self)
        self.bgrab.clicked.connect(self.inv_fill)
        self.bgrab.setFixedWidth(button_width)

        self.brefresh = QPushButton('Refresh', self)
        self.brefresh.clicked.connect(self.item_loc)
        self.brefresh.setFixedWidth(button_width)

        self.bsettings = QPushButton('Settings', self)
        self.bsettings.clicked.connect(self.open_settings)
        self.bsettings.setFixedWidth(button_width)

        self.bitem_buttons = QPushButton('Items', self)
        self.bitem_buttons.clicked.connect(self.open_item_buttons)
        self.bitem_buttons.setFixedWidth(button_width)

        layout.addWidget(self.bdeposit)
        layout.addWidget(self.bgrab)
        layout.addWidget(self.brefresh)
        layout.addWidget(self.bsettings)
        layout.addWidget(self.bitem_buttons)

        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)
        self.show() 
        self.settings = SettingsMenu(self)
        self.button_menu = ItemButtons(self)

    def set_window_position(self, width, height):
        if "window_position" not in self.state:
            self.setGeometry(100, 100, width, height)
            return
        x, y = tuple(self.state["window_position"])
        maxx, maxy = get_screen_size()
        if 0 < x < maxx and 0 < y < maxy:
            self.setGeometry(x, y, width, height)
        else:
            self.setGeometry(100, 100, width, height)


    def btnstate(self, b):
        pass

    def inv_clear(self, button=None):
        clear_inventory(self.state)

    def inv_fill(self, button=None):
        fill_inventory(self.state["item_locations"], self.state["boundary_boxes"], self.state["current_grab"])

    def item_loc(self, button=None):
        if "session_id" not in self.state:
            return
        tab_index = self.state.get("tab_index", 0)
        self.state["item_locations"], self.state["counters"] = \
            get_item_locations(self.tag_map, self.state["current_league"], tab_index, self.state["session_id"])

        self.button_menu.refresh_buttons()
        if self.settings.update_filter.isChecked():
            refresh_filter(self.state["counters"], self.state["filter_address"],
                           self.state["filter_name"], self.state["max_sets"], self.state["colors"])

    def open_settings(self, button=None):
        if self.settings.isHidden():
            self.settings.show()
        else:
            self.settings.hide()

    def open_item_buttons(self, button=None):
        self.button_menu_state = self.button_menu.isHidden()
        if self.button_menu.isHidden():
            self.button_menu.show()
        else:
            self.button_menu.hide()

    def save_state(self):
        with open("state.json", "r") as file:
            backup = file.read()
        with open("state.json", "w") as file:
            try:
                self.state["window_position"] = [self.geometry().x(), self.geometry().y()]
                file.write(json.dumps(self.state, indent=2))
            except Exception as e:
                print("SAVING FAILED")
                print(e)
                file.write(backup)


class ItemButtons(FramelessWindow):
    def __init__(self, parent: FramelessWindow):
        super(ItemButtons, self).__init__(parent)

        layout = QGridLayout()
        self.parent = parent
        g = parent.frameGeometry()
        self.setGeometry(g.x() + g.width(), g.y() - 9, 460, g.height() + 110)
        self.oldPosition = self.pos()
        self.state = parent.state
        self.buttons = dict()
        for idx, (name, color) in enumerate(self.parent.state["colors"].items()):
            print(self.parent.state)
            b = IconButton(self, name, color, self.parent.state["counters"][name])
            layout.addWidget(b, 0, idx)
            self.buttons[name] = b
        w = QWidget()
        w.setLayout(layout)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCentralWidget(w)

    def refresh_buttons(self):
        for name, color in self.parent.state["colors"].items():
            self.buttons[name].set_color_and_counter(color, self.parent.state["counters"][name])


class SettingsMenu(QMainWindow):
    def __init__(self, parent: ChaosRecipe):
        super(SettingsMenu, self).__init__()
        self.setWindowTitle("Settings")
        self.threadpool = QThreadPool()
        self.counter_buttons = dict()
        self.parent = parent
        self.state = parent.state
        g = parent.geometry()
        self.setGeometry(g.x(), g.y() + 100, 400, 250)

        self.w = QWidget(self)
        layout = QGridLayout()
        self.w.setLayout(layout)
        self.setCentralWidget(self.w)

        self.oldPosition = self.pos()
        if "current_league" not in parent.state:
            items = get_leagues(refresh=True)
            current = "Standard"
        else:
            items = parent.state["leagues"]
            current = parent.state["current_league"]

        self.league_refresh = QPushButton(self)
        self.league_refresh.clicked.connect(self.get_current_leagues)
        self.league_refresh.setFixedWidth(20)
        self.league_refresh.setFixedHeight(20)
        self.league_refresh.setIcon(QIcon("Assets/Refresh.png"))

        self.league_dropdown = drop_down(items=items, current=current, attribute="current_league", parent=self)
        self.league_label = QLabel("League")

        self.filter_name = QPushButton(self.state.get('filter_name', 'Choose Filter'), self)
        self.filter_name.clicked.connect(self.get_filter_file)

        self.chaos_calibration = QPushButton('Chaos Calibration', self)
        self.chaos_calibration.clicked.connect(self.func_chaos_calibration)

        self.inv_calibration = QPushButton('Inv Calibration', self)
        self.inv_calibration.clicked.connect(self.calibrate_inventory)

        self.update_filter = QCheckBox("Filter Manipulation")
        self.update_filter.toggled.connect(self.filter_manipulation_check_is_set)
        self.update_filter.setChecked(True)

        self.color_panel = ColorPickerButtonGrid(self)

        self.calibration_help_text_window = QLabel("", self)
        self.calibration_help_text_window.setWordWrap(True)
        self.calibration_help_text_window.setStyleSheet("border: 1px solid black;")
        self.calibration_help_text_window.setMinimumWidth(150)

        self.session_id_input = QLineEdit()
        self.session_id_input.setEchoMode(QLineEdit.Password)
        if "session_id" in self.state:
            self.session_id_input.setText("xxxxxx")
        self.session_id_input.textChanged.connect(self.session_id_change)

        self.session_id_input.setPlaceholderText("Enter Session ID here")
        self.session_id_label = QLabel("Session ID")

        self.maximum_set_number = QLineEdit()
        self.maximum_set_number.textChanged.connect(self.max_set_change)
        self.maximum_set_number.setText(str(self.state.get("max_sets", 12)))
        self.maximum_set_label = QLabel("Max Number of Sets")

        self.account_name = QLineEdit()
        self.account_name.textChanged.connect(self.name_change)
        self.account_name.setText(str(self.state.get("account_name", "")))
        self.account_name_label = QLabel("Account Name")

        self.tab_index = QLineEdit()
        self.tab_index.textChanged.connect(self.tab_index_change)
        self.tab_index.setText(str(self.state.get("tab_index", "0")))
        self.tab_index_label = QLabel("Tab Index")

        layout.addWidget(self.league_label, 0, 0)
        layout.addWidget(self.league_refresh, 0, 1)
        layout.addWidget(self.league_dropdown, 0, 2)

        layout.addWidget(self.session_id_label, 1, 0)
        layout.addWidget(self.session_id_input, 1, 2)

        layout.addWidget(self.account_name_label, 2, 0)
        layout.addWidget(self.account_name, 2, 2)

        layout.addWidget(self.tab_index_label, 3, 0)
        layout.addWidget(self.tab_index, 3, 2)

        layout.addWidget(self.maximum_set_label, 4, 0)
        layout.addWidget(self.maximum_set_number, 4, 2)

        layout.addWidget(self.filter_name, 5, 0)
        layout.addWidget(self.update_filter, 5, 2)

        layout.addWidget(self.chaos_calibration, 6, 0)
        layout.addWidget(self.inv_calibration, 6, 2)

        layout.addWidget(self.color_panel, 7, 0, 1, 3)

        layout.addWidget(self.calibration_help_text_window, 0, 3, 8, 2)

    def get_current_leagues(self):
        self.state["leagues"] = get_leagues(refresh=True)
        self.state["current_league"] = "Standard"
        self.league_dropdown.set_up(self.state["leagues"], "Standard")

    def session_id_change(self, text):
        self.state["session_id"] = text

    def max_set_change(self, text):
        self.state["max_sets"] = int(text)

    def name_change(self, text):
        self.state["account_name"] = text

    def tab_index_change(self, text):
        self.state["tab_index"] = text

    def filter_manipulation_check_is_set(self):
        if not self.update_filter.isChecked():
            reset_filter(self.parent.state["filter_address"], self.parent.state["filter_name"])

    def get_filter_file(self, button):
        initial_address = "c:\\"
        if self.parent.state.get("filter_address", None):
            initial_address = self.parent.state["filter_address"]
        file_name = QFileDialog.getOpenFileName(self, 'Open file', initial_address, "Filter files (*.filter)")
        self.parent.state["filter_address"], self.parent.state["filter_name"] = split_address_file_name(file_name[0], 'filter')
        self.filter_name.setText(self.parent.state["filter_name"])

    def func_chaos_calibration(self, button=None):
        self.calibration(
            self.calibration_chaos_dummy,
            self.set_calibration_progress,
            self.set_chaos_calibration_result
        )

    def calibration(self, fun, progress_fun, result_fun):
        self.calibration_help_text_window.show()
        worker = Worker(fun)
        worker.signals.progress.connect(progress_fun)
        worker.signals.result.connect(result_fun)
        self.threadpool.start(worker)

    @staticmethod
    def calibration_chaos_dummy(progress_callback):
        return calibrate_box_dimensions(progress_callback)

    def set_calibration_progress(self, result: str):
        self.calibration_help_text_window.setText(result)

    def set_chaos_calibration_result(self, result):
        self.state["boundary_boxes"] = result
        self.calibration_help_text_window.setText("Chaos recipe calibration complete")

    def calibrate_inventory(self, button=None):
        identify_empty_inventory(self.state)
        self.calibration_help_text_window.setText("Inventory calibration complete")


def initialize_states(state: dict):
    if "colors" not in state:
        state["colors"] = {
                "Weapon": [0, 255, 255],
                "Gloves": [0, 255, 0],
                "Body": [255, 0, 255],
                "Boots": [0, 0, 255],
                "Helmet": [255, 255, 0],
                "Ring": [255, 0, 0],
                "Amulet": [255, 0, 0],
                "Belt": [255, 0, 0]
            }
    if not state.get("counters"):
        state["counters"] = {slot: 0 for slot in state["colors"].keys()}
    if not state.get("current_league"):
        state["current_league"] = "Standard"
    if not state.get("current_grab"):
        state["current_grab"] = "Chaos"
    if not state.get("leagues"):
        state["leagues"] = get_leagues(refresh=True)
    if "window_position" not in state:
        state["window_position"] = [100, 100]

    if not state.get("tag_map"):
        with open("tag_map.json", "r") as file:
            state["tag_map"] = json.loads(file.read())


sys.excepthook = except_hook
main()
