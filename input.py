import json

import requests
import winsound
from math import floor
from pynput.mouse import Controller
from pynput.keyboard import Controller as kController

from requests.structures import CaseInsensitiveDict

keyboard_controller = kController()
mouse = Controller()


def grab_two_sets(mapping: dict) -> list:
    possible_slots = ["twohand", "onehand", "body_armour", "helmet", "boots", "gloves", "belt", "ring", "amulet"]
    slot_completion = {slot: [] for slot in possible_slots}
    # get a 4x2 weapon slot item
    for ilvl in ["75", "60"]:
        if not slot_completion["twohand"]:
            for dim in ['3x2', '4x1', '4x2']:
                for weapon_type in ["twohand", "bow"]:
                    if mapping[ilvl][weapon_type].get(dim, []):
                        slot_completion["twohand"] = [(mapping[ilvl][weapon_type][dim][0], ilvl)]
                        break

    for ilvl in ["75", "60"]:
        slot_completion["onehand"] += [(coordinates, ilvl) for coordinates in mapping[ilvl]['onehand']['3x1']]

    slot_completion["onehand"] = slot_completion["onehand"][:2 if slot_completion["twohand"] else 4]
    if len(slot_completion["onehand"]) + 2 * len(slot_completion["twohand"]) < 4:
        print("Not enough weapons for chaos recipe!")
        return []

    for ilvl in ["75", "60"]:
        for slot, items in slot_completion.items():
            if slot in ["twohand", "onehand"]:
                continue
            items += [(coordinates, ilvl) for coordinates in list(mapping[ilvl][slot].values())[0]]

    for slot, items in slot_completion.items():
        if slot in ["twohand", "onehand"]:
            continue
        if len(items) < (4 if slot == 'ring' else 2):
            print(f"Not enough {slot} for chaos recipe")
            return []
        slot_completion[slot] = items[:4 if slot == 'ring' else 2]

    if all(any(x[1] == "75" for x in items) for slot, items in slot_completion.items()
           if slot not in ["twohand", "onehand"]):
        print("Must add ilvl <75 items to yield chaos instead of regal")
        if sum(x[1] == "75" for x in slot_completion["onehand"]) > 1 or \
                (slot_completion["twohand"] and slot_completion["twohand"][0][1] == "75"):
            for slot, items in slot_completion.items():
                if slot not in ["twohand", "onehand", "ring"]:
                    ilvl70items = list(mapping["60"][slot].values())[0]
                    print(f"ilvl <75 {slot} items:", ilvl70items)
                    if len(ilvl70items) > 1:
                        slot_completion[slot] = [(x, "60") for x in ilvl70items[:2]]
                        print(f"slot {slot} items replaced")
                        break
            else:
                "Could not replace amy slots completely"
                "Could not replace amy slots completely"
                return []
    coordinates = []
    for slot in possible_slots:
        for item in slot_completion[slot]:
            coord, ilvl = item
            coordinates.append(coord)
            for dim, c in mapping[ilvl][slot].items():
                if coord in c:
                    c.remove(coord)
    return coordinates


def get_item_locations(tag_map, league, tab_index, session_id):
    url = "https://pathofexile.com/character-window/get-stash-items"
    headers = CaseInsensitiveDict({"user-agent": "chaos recipe crawler", "accept": "text",
                                   "cookie": f"POESESSID={session_id}"})

    params = dict(
        league=league,
        tabs='0',
        tabIndex=f"{tab_index}",
        accountName='Liberatorist'
    )
    item_locations = {'chaos': {ilvl: {tag: {dimension: []
                                             for dimension in items}
                                       for tag, items in tag_map.items()}
                                for ilvl in ["60", "75"]},
                      'jewel': [],
                      'flask': [],
                      'gem': [],
                      'vendor': [],
                      'prophecy': [],
                      'heist': [],
                      'misc': []
                      }

    resp = requests.get(url, params=params, headers=headers)
    stash_items = resp.json()['items'] if resp.status_code < 299 else []
    for stash_item in stash_items:
        if stash_item["typeLine"] in (
        "Crimson Jewel", "Viridian Jewel", "Cobalt Jewel", "abyssJewel") or stash_item.get("abyssJewel", False):
            item_locations['jewel'].append(
                {"coords": (stash_item['x'], stash_item['y']), "dim": (stash_item['w'], stash_item['h'])}
            )
        elif "Flask" in stash_item["typeLine"]:
            item_locations['flask'].append(
                {"coords": (stash_item['x'], stash_item['y']), "dim": (stash_item['w'], stash_item['h'])}
            )
        elif stash_item["frameType"] == 4:
            item_locations['gem'].append(
                {"coords": (stash_item['x'], stash_item['y']), "dim": (stash_item['w'], stash_item['h'])}
            )
        elif stash_item["frameType"] == 8:
            item_locations['prophecy'].append(
                {"coords": (stash_item['x'], stash_item['y']), "dim": (stash_item['w'], stash_item['h'])}
            )
        elif yields_jeweler_or_chromatic(stash_item):
            item_locations['vendor'].append(
                {"coords": (stash_item['x'], stash_item['y']), "dim": (stash_item['w'], stash_item['h'])}
            )
        elif "Can be exchanged" in stash_item.get('descrText', ''):
            item_locations['vendor'].append(
                {"coords": (stash_item['x'], stash_item['y']), "dim": (stash_item['w'], stash_item['h'])}
            )
        elif not stash_item.get('identified', True) \
                and stash_item.get('ilvl', 0) > 59 \
                and stash_item.get('frameType') == 2:
            for tag, items in tag_map.items():
                for dimension, name_list in items.items():
                    if stash_item['baseType'] in name_list:
                        item_locations["chaos"]["60" if stash_item['ilvl'] < 75 else "75"][tag][dimension].append(
                            (stash_item['x'], stash_item['y'])
                        )
                        break
                else:
                    continue
                break
            else:
                item_locations['misc'].append(
                {"coords": (stash_item['x'], stash_item['y']), "dim": (stash_item['w'], stash_item['h'])}
            )
        else:
            item_locations['misc'].append(
                {"coords": (stash_item['x'], stash_item['y']), "dim": (stash_item['w'], stash_item['h'])}
            )

    counters = {'Weapon': category_sum(item_locations, 'bow') +
                          floor(category_sum(item_locations, 'onehand') / 2) +
                          category_sum(item_locations, 'twohand'),
                'Body': category_sum(item_locations, 'body_armour'),
                'Gloves': category_sum(item_locations, 'gloves'),
                'Boots': category_sum(item_locations, 'boots'),
                'Ring': floor(category_sum(item_locations, 'ring') / 2),
                'Amulet': category_sum(item_locations, 'amulet'),
                'Belt': category_sum(item_locations, 'belt'),
                'Helmet': category_sum(item_locations, 'helmet'),
                }


    winsound.MessageBeep()
    return item_locations, counters


def category_sum(loc, category):
    return sum(len(item_list) for ilvl in ["60", "75"] for item_list in loc['chaos'][ilvl][category].values())


def yields_jeweler_or_chromatic(item):
    sockets = item.get('sockets', [])
    if len(sockets) == 6:
        return True
    groups = {idx: set() for idx in range(6)}
    for socket in sockets:
        groups[socket["group"]].add(socket["sColour"])
    return any(len(group) == 3 for group in groups.values())


def get_leagues(refresh=False):
    if not refresh:
        with open('state.json', 'r') as file:
            return json.loads(file.read())["leagues"]
    try:

        url = "https://pathofexile.com/api/leagues"
        headers = CaseInsensitiveDict({"user-agent": "fabian.mueller77@gmail.com", "accept": "text"})
        resp = requests.get(url, headers=headers)
        leagues = [league['id'] for league in resp.json()]
        with open('state.json', 'r') as file:
            data = json.loads(file.read())
            data.update(leagues=leagues, current_leagues="standard")
        with open('state.json', 'w') as file:
            file.write(json.dumps(data))
        return [league['id'] for league in resp.json()]
    except:
        return ["Could not find any Leagues"]


def choose_fitting(item_list: list) -> (list, list):
    chosen_items = []
    inventory = [[1 for _ in range(12)] for _ in range(5)]
    space = 60
    removed_ids = []
    for index, item in enumerate(item_list):
        if item['dim'][0] * item['dim'][1] > space:
            continue
        for x in range(12):
            for y in range(5):
                if inventory[y][x]:
                    try:
                        if all(inventory[y + y_add][x + x_add]
                               for x_add in range(item['dim'][0])
                               for y_add in range(item['dim'][1])):
                            break
                    except IndexError:
                        continue
            else:
                continue
            break
        else:
            continue
        chosen_items.append(item['coords'])
        removed_ids.append(index)

        for x_add in range(item['dim'][0]):
            for y_add in range(item['dim'][1]):
                inventory[y + y_add][x + x_add] = 0

        space -= item['dim'][0] * item['dim'][1]
        if space == 0:
            break

    return chosen_items, [item for idx, item in enumerate(item_list) if idx not in removed_ids]
