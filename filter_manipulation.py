def write_filter(filter_folder, filter_name, counters, max_sets, colors):
    text = "### Start of Chaos Recipe Filter ###\n"
    for slot, counter in counters.items():
        if counter < max_sets or slot in ["Ring", "Amulet"]:
            if slot == "Weapon":
                text += write_filter_segment("twohand", colors)
                text += write_filter_segment("onehand", colors)
            else:
                text += write_filter_segment(slot, colors)
    text += "### End of Chaos Recipe Filter ###"

    # copy old filter and remove old chaos recipe appendix
    with open(filter_folder + filter_name + ".filter", 'r') as file:
        item_filter = file.read()
        if (idx_start := item_filter.find("### Start of Chaos Recipe Filter ###")) != -1:
            idx_end = item_filter.find("### End of Chaos Recipe Filter ###")
            if idx_end != -1:
                item_filter = item_filter[:idx_start] + item_filter[(idx_end + len("### End of Chaos Recipe Filter ###\n")):]

        item_filter = text + "\n" + item_filter

    with open(filter_folder + filter_name + ".filter", 'w') as file:
        file.write(item_filter)


def reset_filter(filter_folder, filter_name):
    with open(filter_folder + filter_name + ".filter", 'r') as file:
        item_filter = file.read()
        if (idx_start := item_filter.find("### Start of Chaos Recipe Filter ###")) != -1:
            idx_end = item_filter.find("### End of Chaos Recipe Filter ###")
            if idx_end != -1:
                item_filter = item_filter[:idx_start] + item_filter[(idx_end + len("### End of Chaos Recipe Filter ###\n")):]
    with open(filter_folder + filter_name + ".filter", 'w') as file:
        file.write(item_filter)


def set_color(color):
    return f"{color[0]} {color[1]} {color[2]} 255"


def write_filter_segment(slot, colors) -> str:

    mapping = {
        "twohand": {
            "types": '"Two Hand Swords" "Two Hand Axes" "Two Hand Maces" "Staves" "Warstaves" "Bows"',
            "color": set_color(colors["Weapon"]),
            "width": "2",
            "height": "3"
        },
        "onehand": {
            "types": '"Daggers" "One Hand Axes" "One Hand Maces" "One Hand Swords" "Rune Daggers" "Sceptres" "Thrusting One Hand Swords" "Wands"',
            "color": set_color(colors["Weapon"]),
            "width": "1",
            "height": "3"
        },
        "Gloves": {
            "types": '"Gloves"',
            "color": set_color(colors["Gloves"]),
            "width": "2",
            "height": "2"
        },
        "Body": {
            "types": '"Body Armours"',
            "color": set_color(colors["Body"]),
            "width": "2",
            "height": "3"
        },
        "Helmet": {
            "types": '"Helmets"',
            "color": set_color(colors["Helmet"]),
            "width": "2",
            "height": "2"
        },
        "Boots": {
            "types": '"Boots"',
            "color": set_color(colors["Boots"]),
            "width": "2",
            "height": "2"
        },
        "Ring": {
            "types": '"Rings"',
            "color": set_color(colors["Ring"]),
            "width": "1",
            "height": "1"
        },
        "Belt": {
            "types": '"Belts"',
            "color": set_color(colors["Belt"]),
            "width": "2",
            "height": "1"
        },
        "Amulet": {
            "types": '"Amulets"',
            "color": set_color(colors["Amulet"]),
            "width": "1",
            "height": "1"
        }
    }[slot]

    return 'Show\n' \
           '    HasInfluence None\n' \
           '    Rarity Rare\n' \
           '    Identified  False\n' \
           '    ItemLevel >= 60\n' \
           f'    Class {mapping["types"]}\n' \
           f'    Width <= {mapping["width"]}\n' \
           f'    Height <= {mapping["height"]}\n' \
           '    Sockets <= 5\n' \
           '    LinkedSockets <= 5\n' \
           f'    SetBackgroundColor {mapping["color"]}\n' \
           '    SetFontSize 40\n' \
           '    SetTextColor 255 255 255 255\n' \
           '    SetBorderColor 0 0 0\n\n'
