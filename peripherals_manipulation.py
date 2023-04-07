import random

import pygetwindow as pygetwindow
from pynput.mouse import Button, Controller
from pynput.keyboard import Key
from pynput.keyboard import Controller as kController
from time import sleep
import winsound
import clipboard

from calibration import get_filled_inventory_coordinates, get_pixel_color
from filter_manipulation import write_filter
from input import grab_two_sets, choose_fitting

keyboard_controller = kController()
mouse = Controller()

def get_mouse_position():
    return mouse.position


def set_mouse_position(pos):
    mouse.position = pos


def click_mouse(pos):
    mouse.position = pos
    mouse.click(Button.left)


def stash_coordinates(x, y, boundary, stash_type='quad'):
    stash_size = 23 if stash_type == 'quad' else 11
    stash_box = boundary["stashbox"]

    return (round(stash_box[0] + (stash_box[2] - stash_box[0]) / stash_size * x),
            round(stash_box[1] + (stash_box[3] - stash_box[1]) / stash_size * y))


def inventory_coordinates(x, y, inv_box):
    return (round(inv_box[0] + (inv_box[2] - inv_box[0]) / 11 * x),
            round(inv_box[1] + (inv_box[3] - inv_box[1]) / 4 * y))


def move_item_set_to_inventory(locations, boundary_boxes=None):
    sleeptime = 0.1
    with keyboard_controller.pressed(Key.ctrl):
        sleep(sleeptime)
        for coordinates in locations:
            sleep(sleeptime)
            if boundary_boxes:
                mouse.position = stash_coordinates(coordinates[0], coordinates[1], boundary_boxes)
            else:
                mouse.position = tuple(coordinates)
            mouse.click(Button.left)
            sleep(0.01)
            mouse.click(Button.left)
            sleep(0.01)
            mouse.click(Button.left)


def fill_inventory(item_locations, boundary_boxes, mode):
    if mode == 'Chaos':
        x = grab_two_sets(item_locations["chaos"])
    elif mode == 'Non-chaos':
        x, _ = choose_fitting([item for key, location in item_locations.items() if key != 'chaos' for item in location])
    else:
        x, item_locations[mode.lower()] = choose_fitting(item_locations[mode.lower()])

    move_item_set_to_inventory(x, boundary_boxes)
    winsound.MessageBeep()


def clear_inventory(state):
    boundary = state["boundary_boxes"]["invbox"]
    coordinates = get_filled_inventory_coordinates(state)
    if not coordinates:
        winsound.MessageBeep()
        return

    sleeptime = 0.02
    with keyboard_controller.pressed(Key.ctrl):
        sleep(sleeptime*2)
        for x, y in coordinates:
            sleep(sleeptime)
            mouse.position = inventory_coordinates(x, y, boundary)
            sleep(sleeptime)
            mouse.click(Button.left)

    winsound.MessageBeep()


def move_mouse(target_coordinates, time=0.0):
    steps = 10
    current_coordinates = mouse.position
    for dt in range(steps):
        mouse.position = (round(current_coordinates[0] + dt/(steps + 1) * (target_coordinates[0] - current_coordinates[0])),
                          round(current_coordinates[1] + dt/(steps + 1) * (target_coordinates[1] - current_coordinates[1])))
        sleep(time/steps/2)
    sleep(time/2)


def select_poe_window():
    windows = pygetwindow.getWindowsWithTitle("Path of Exile")
    if not windows:
        return False
    windows[0].activate()
    return True


def refresh_filter(counters, filter_folder, filter_name, max_sets, colors):
    global poe_is_active_window
    write_filter(filter_folder, filter_name, counters, max_sets, colors)

    poe_is_active_window = select_poe_window()
    if poe_is_active_window:
        keyboard_controller.press(Key.enter)
        keyboard_controller.release(Key.enter)
        keyboard_controller.type('/itemfilter ' + filter_name)
        keyboard_controller.press(Key.enter)
        keyboard_controller.release(Key.enter)


def ctrl_plus(button: str):
    keyboard_controller.press(Key.ctrl)
    sleep(.01)
    keyboard_controller.press(button)
    sleep(.01)
    keyboard_controller.release(button)
    sleep(.01)
    keyboard_controller.release(Key.ctrl)


def item_info():
    previous_copy = clipboard.paste()
    keyboard_controller.press(Key.ctrl)
    sleep(.01)
    # keyboard_controller.press(Key.alt_l)
    # sleep(.01)
    keyboard_controller.press("c")
    sleep(.01)
    keyboard_controller.release("c")
    sleep(.01)
    # keyboard_controller.release(Key.alt_l)
    # sleep(.01)
    keyboard_controller.release(Key.ctrl)
    sleep(.01)
    item_string = clipboard.paste()
    clipboard.copy(previous_copy)
    return item_string


def press_escape():
    sleep_time = 0.001
    sleep(sleep_time)
    keyboard_controller.press(Key.esc)
    sleep(sleep_time)
    keyboard_controller.release(Key.esc)


def click_item(item_coordinates):
    mouse.position = item_coordinates
    sleep(0.001)
    mouse.click(Button.left)


def set_new_price(bid_position, previous_offer, percentile):
    sleep_time = 0.04
    previous_copy = clipboard.paste()
    mouse.position = tuple(bid_position)
    sleep(sleep_time)
    mouse.click(Button.left)
    sleep(sleep_time)
    ctrl_plus("a")
    sleep(sleep_time)
    ctrl_plus("c")
    price = int(clipboard.paste())

    offer = round(previous_offer + (price - previous_offer) * percentile)
    clipboard.copy(str(offer))
    sleep(sleep_time)
    ctrl_plus("v")
    return offer


def get_tujen_bit(bid_position):
    sleep_time = 0.04
    previous_copy = clipboard.paste()
    mouse.position = tuple(bid_position)
    sleep(sleep_time)
    mouse.click(Button.left)
    sleep(sleep_time)
    ctrl_plus("a")
    sleep(sleep_time)
    ctrl_plus("c")
    price = clipboard.paste()
    clipboard.copy(previous_copy)
    return price


def get_tujen_artifact(artifact_position):
    colors = get_pixel_color(*artifact_position)
    if all(colors[i] == j for i, j in enumerate([28, 29, 28])):
        return 0
    if all(colors[i] == j for i, j in enumerate([13, 13, 13])):
        return 1
    if all(colors[i] == j for i, j in enumerate([32, 31, 28])):
        return 2
    if all(colors[i] == j for i, j in enumerate([17, 18, 17])):
        return 3
    return -1

