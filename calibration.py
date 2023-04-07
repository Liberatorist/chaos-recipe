import mss
from pynput.mouse import Controller
from pynput.keyboard import Controller as kController
from pynput import keyboard
import numpy as np
from numba import njit

keyboard_controller = kController()
mouse = Controller()

temp = []


def get_active_window():
    """
    Get the currently active window.

    Returns
    -------
    string :
        Name of the currently active window.
    """
    import sys
    active_window_name = None
    if sys.platform in ['linux', 'linux2']:
        try:
            import wnck
        except ImportError:
            wnck = None
        if wnck is not None:
            screen = wnck.screen_get_default()
            screen.force_update()
            window = screen.get_active_window()
            if window is not None:
                pid = window.get_pid()
                with open("/proc/{pid}/cmdline".format(pid=pid)) as f:
                    active_window_name = f.read()
        else:
            try:
                from gi.repository import Gtk, Wnck
                gi = "Installed"
            except ImportError:
                gi = None
            if gi is not None:
                Gtk.init([])  # necessary if not using a Gtk.main() loop
                screen = Wnck.Screen.get_default()
                screen.force_update()  # recommended per Wnck documentation
                active_window = screen.get_active_window()
                pid = active_window.get_pid()
                with open("/proc/{pid}/cmdline".format(pid=pid)) as f:
                    active_window_name = f.read()
    elif sys.platform in ['Windows', 'win32', 'cygwin']:
        import win32gui
        window = win32gui.GetForegroundWindow()
        active_window_name = win32gui.GetWindowText(window)
    else:
        print("sys.platform={platform} is unknown. Please report."
              .format(platform=sys.platform))
        print(sys.version)
    return active_window_name


def get_screen_size():
    x, y, _ = grab_screenshot().shape
    return y, x


def get_mouse_position():
    return mouse.position


def get_pixel_color(x, y):
    return grab_screenshot([x, y, x+1, y+1])[0][0][:3]


def grab_screenshot(bbox=None) -> np.ndarray:
    """bbox = [left, top, right, bottom]"""
    if bbox:
        monitor = dict(top=bbox[1], left=bbox[0], height=bbox[3] - bbox[1], width=bbox[2] - bbox[0])
    else:
        monitor = dict(top=0, left=0, height=2160, width=3840)
    screen_shot = mss.mss().grab(monitor)
    # Image.frombytes("RGB", screen_shot.size, screen_shot.bgra, "raw", "BGRX").show()
    return np.asarray(screen_shot)


def calibrate_box_dimensions(process_callback):
    feedback = [
        "Move your mouse to the top left corner of your stash tab and press ALT",
        "Move your mouse to the bottom right corner of your stash tab and press ALT",
        "Move your mouse to the top left corner of your inventory and press ALT",
        "Move your mouse to the bottom right corner of your inventory and press ALT"
    ]
    result = calibrate_coordinates(feedback, process_callback)
    return dict(stashbox=[result[0][0], result[0][1], result[1][0], result[1][1]],
                invbox=[result[2][0], result[2][1], result[3][0], result[3][1]])


def calibrate_coordinates(callback_feedback: list, process_callback=None):
    global temp

    def on_press(key):
        if key in [keyboard.Key.alt_l, keyboard.Key.alt_r]:
            global temp
            temp = list(mouse.position)
            return False
    u = []
    for feedback in callback_feedback:
        process_callback.emit(feedback)
        with keyboard.Listener(on_press=on_press, ) as listener:
            listener.join()
            u.append(temp)

    return u


def identify_empty_inventory(state):
    bbox = state["boundary_boxes"]["invbox"]
    screen_shot = grab_screenshot(bbox)

    empty_colors = [[[0, 0, 0] for _ in range(5)] for _ in range(12)]
    for x in range(12):
        x_coord = round((bbox[2] - bbox[0] - 1) * x / 11)
        for y in range(5):
            y_coord = round((bbox[3] - bbox[1] - 1) * y / 4)
            empty_colors[x][y] = [int(x) for x in screen_shot[y_coord][x_coord]]
    state["empty_inventory"] = empty_colors


def get_filled_inventory_coordinates(state):
    empty_colors = state.get("empty_inventory")
    if not empty_colors:
        return [(x, y) for x in range(12) for y in range(5)]

    bbox = state["boundary_boxes"]["invbox"]

    screen_shot = grab_screenshot(bbox)
    filled_inventory_coordinates = []
    for x in range(12):
        x_coord = round((bbox[2] - bbox[0] - 1) * x / 11)
        for y in range(5):
            y_coord = round((bbox[3] - bbox[1] - 1) * y / 4)
            for color in range(3):
                if empty_colors[x][y][color] != screen_shot[y_coord][x_coord][color]:
                    filled_inventory_coordinates.append((x, y))
                    break
    return filled_inventory_coordinates


@njit(cache=True)
def find_all(screen_shot):
    n, m, _ = screen_shot.shape
    x_occurrences = np.zeros((n, 1), np.int32)
    y_occurrences = np.zeros((m, 1), np.int32)
    for x in range(n):
        for y in range(m):
            if (screen_shot[x][y][2] == 231) & (screen_shot[x][y][1] == 180) & (screen_shot[x][y][0] == 119):
                x_occurrences[x] += 1
                y_occurrences[y] += 1
    return np.where(x_occurrences > 30)[0], np.where(y_occurrences > 30)[0]
