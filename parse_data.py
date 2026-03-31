#!/usr/bin/env python3
"""
Parse Tele-Arena 5.6 data files (.MCV and .MSG) into JSON for the Python port.

Run this once from the telearena_py directory:
    python3 parse_data.py
"""

import json
import re
import os

SRC = os.path.join(os.path.dirname(__file__), 'Ta56dSrc')
OUT = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(OUT, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_null_parts(filename):
    """Read a .MCV file and return list of null-separated non-empty strings."""
    with open(filename, 'rb') as f:
        data = f.read()
    parts = []
    for p in data.split(b'\x00'):
        try:
            s = p.decode('latin-1').strip()
        except Exception:
            s = ''
        parts.append(s)
    return parts


def parse_ints(s):
    """Parse a space-separated string of integers."""
    try:
        return [int(x) for x in s.split()]
    except ValueError:
        return []


# ---------------------------------------------------------------------------
# Parse TSGARN-D.MCV  -- items, spells, monsters, misc weapons
# ---------------------------------------------------------------------------

def parse_items_spells_monsters():
    parts = read_null_parts(os.path.join(SRC, 'TSGARN-D.MCV'))

    # ---- ITEMS ----
    # parts[0] = 'English/ANSI', parts[1] = '', parts[2] = item count
    idx = 2
    num_items = int(parts[idx]); idx += 1
    items = []
    for _ in range(num_items):
        # skip blanks
        while idx < len(parts) and parts[idx] == '':
            idx += 1
        name = parts[idx]; idx += 1
        while idx < len(parts) and parts[idx] == '':
            idx += 1
        desc = parts[idx]; idx += 1
        while idx < len(parts) and parts[idx] == '':
            idx += 1
        stats_str = parts[idx]; idx += 1
        stats = parse_ints(stats_str)
        # Stats: price wt range mindam maxdam type armor charges effect
        #        clas grpsiz room rune poison level shop
        item = {
            'name': name,
            'desc': desc,
            'price': stats[0] if len(stats) > 0 else 0,
            'wt': stats[1] if len(stats) > 1 else 0,
            'range': stats[2] if len(stats) > 2 else 0,
            'mindam': stats[3] if len(stats) > 3 else 0,
            'maxdam': stats[4] if len(stats) > 4 else 0,
            'type': stats[5] if len(stats) > 5 else 0,
            'armor': stats[6] if len(stats) > 6 else 0,
            'charges': stats[7] if len(stats) > 7 else 0,
            'effect': stats[8] if len(stats) > 8 else 0,
            'clas': stats[9] if len(stats) > 9 else 0,
            'grpsiz': stats[10] if len(stats) > 10 else 0,
            'room': stats[11] if len(stats) > 11 else 0,
            'rune': stats[12] if len(stats) > 12 else 0,
            'poison': stats[13] if len(stats) > 13 else 0,
            'level': stats[14] if len(stats) > 14 else 0,
            'shop': stats[15] if len(stats) > 15 else 0,
            'proj_desc': '',
        }
        # Items with effect=12 or 15 (fire projectiles) have an extra desc
        if item['effect'] in (12, 15):
            while idx < len(parts) and parts[idx] == '':
                idx += 1
            # peek - if it looks like a description (not a number-only string), consume it
            if idx < len(parts) and parts[idx] and not parts[idx][0].isdigit():
                # Make sure it's not the next item's name by checking if next-next is a desc
                item['proj_desc'] = parts[idx]; idx += 1
        items.append(item)

    # ---- SPELLS ----
    while idx < len(parts) and parts[idx] == '':
        idx += 1
    num_spells = int(parts[idx]); idx += 1
    spells = []
    for _ in range(num_spells):
        while idx < len(parts) and parts[idx] == '':
            idx += 1
        name = parts[idx]; idx += 1
        while idx < len(parts) and parts[idx] == '':
            idx += 1
        desc = parts[idx]; idx += 1
        while idx < len(parts) and parts[idx] == '':
            idx += 1
        stats_str = parts[idx]; idx += 1
        stats = parse_ints(stats_str)
        # Stats: type level mindam maxdam mdice price multi armor poison psn
        #        mdrain sdrain sboost move vamp
        spell = {
            'name': name,
            'desc': desc,
            'type': stats[0] if len(stats) > 0 else 0,
            'level': stats[1] if len(stats) > 1 else 0,
            'mindam': stats[2] if len(stats) > 2 else 0,
            'maxdam': stats[3] if len(stats) > 3 else 0,
            'mdice': stats[4] if len(stats) > 4 else 0,
            'price': stats[5] if len(stats) > 5 else 0,
            'multi': stats[6] if len(stats) > 6 else 0,
            'armor': stats[7] if len(stats) > 7 else 0,
            'poison': stats[8] if len(stats) > 8 else 0,
            'psn': stats[9] if len(stats) > 9 else 0,
            'mdrain': stats[10] if len(stats) > 10 else 0,
            'sdrain': stats[11] if len(stats) > 11 else 0,
            'sboost': stats[12] if len(stats) > 12 else 0,
            'move': stats[13] if len(stats) > 13 else 0,
            'vamp': stats[14] if len(stats) > 14 else 0,
        }
        spells.append(spell)

    # ---- MONSTERS ----
    while idx < len(parts) and parts[idx] == '':
        idx += 1
    num_monsters = int(parts[idx]); idx += 1
    monsters = []
    for _ in range(num_monsters):
        while idx < len(parts) and parts[idx] == '':
            idx += 1
        if idx >= len(parts):
            break
        name = parts[idx]; idx += 1
        while idx < len(parts) and parts[idx] == '':
            idx += 1
        long_desc = parts[idx]; idx += 1
        while idx < len(parts) and parts[idx] == '':
            idx += 1
        stats_str = parts[idx]; idx += 1
        stats = parse_ints(stats_str)
        # Stats: prefix cskl terr gp trs ac sach hd regen mindam maxdam
        #        minspc maxspc effect mineff maxeff spcabn atts level morale
        #        sskl spllst minspl maxspl gender subtyp
        monster = {
            'name': name,
            'long_desc': long_desc,
            'prefix': stats[0] if len(stats) > 0 else 0,
            'cskl': stats[1] if len(stats) > 1 else 75,
            'terr': stats[2] if len(stats) > 2 else 0,
            'gp': stats[3] if len(stats) > 3 else 0,
            'trs': stats[4] if len(stats) > 4 else 0,
            'ac': stats[5] if len(stats) > 5 else 0,
            'sach': stats[6] if len(stats) > 6 else 0,
            'hd': stats[7] if len(stats) > 7 else 1,
            'regen': stats[8] if len(stats) > 8 else 0,
            'mindam': stats[9] if len(stats) > 9 else 1,
            'maxdam': stats[10] if len(stats) > 10 else 4,
            'minspc': stats[11] if len(stats) > 11 else 0,
            'maxspc': stats[12] if len(stats) > 12 else 0,
            'effect': stats[13] if len(stats) > 13 else 0,
            'mineff': stats[14] if len(stats) > 14 else 0,
            'maxeff': stats[15] if len(stats) > 15 else 0,
            'spcabn': stats[16] if len(stats) > 16 else 0,
            'atts': stats[17] if len(stats) > 17 else 1,
            'level': stats[18] if len(stats) > 18 else 1,
            'morale': stats[19] if len(stats) > 19 else 50,
            'sskl': stats[20] if len(stats) > 20 else 0,
            'spllst': stats[21] if len(stats) > 21 else 0,
            'minspl': stats[22] if len(stats) > 22 else 0,
            'maxspl': stats[23] if len(stats) > 23 else 0,
            'gender': stats[24] if len(stats) > 24 else 0,
            'subtyp': stats[25] if len(stats) > 25 else 0,
            'plural': '',
            'weapon': '',
            'spcatt': '',
            'spcabd': '',
        }
        # 4 optional string fields (plural, weapon, special attack, special ability)
        for field in ('plural', 'weapon', 'spcatt', 'spcabd'):
            while idx < len(parts) and parts[idx] == '':
                idx += 1
            if idx < len(parts):
                val = parts[idx]
                # Stop if this looks like the next monster's name (followed by a long desc)
                # We detect by checking: if next item is a long description string (>50 chars)
                # Actually we just always read 4 fields regardless
                monster[field] = val
                idx += 1
        monsters.append(monster)

    return items, spells, monsters


# ---------------------------------------------------------------------------
# Parse TSGARN-T.MCV  -- town rooms (exits + descriptions) + townsfolk
# ---------------------------------------------------------------------------

def parse_town_data():
    parts = read_null_parts(os.path.join(SRC, 'TSGARN-T.MCV'))
    idx = 2  # skip header + empty

    # ---- SHOP/EXIT MAPPING DATA (not needed directly - it's redundant with room exits) ----
    # Read the count (number of shop type entries)
    num_shop_entries = int(parts[idx]); idx += 1
    shop_entries = []
    for _ in range(num_shop_entries):
        while idx < len(parts) and parts[idx] == '':
            idx += 1
        s = parts[idx]; idx += 1
        shop_entries.append(parse_ints(s))

    # ---- TOWNSFOLK COUNT ----
    while idx < len(parts) and parts[idx] == '':
        idx += 1
    num_folk_types = int(parts[idx]); idx += 1

    # ---- TOWNSFOLK RECORDS ----
    townsfolk_types = []
    for _ in range(num_folk_types):
        while idx < len(parts) and parts[idx] == '':
            idx += 1
        prefix_str = parts[idx]; idx += 1
        while idx < len(parts) and parts[idx] == '':
            idx += 1
        name = parts[idx]; idx += 1
        while idx < len(parts) and parts[idx] == '':
            idx += 1
        plural = parts[idx]; idx += 1
        while idx < len(parts) and parts[idx] == '':
            idx += 1
        desc = parts[idx]; idx += 1
        townsfolk_types.append({
            'prefix': int(prefix_str) if prefix_str.isdigit() else 0,
            'name': name,
            'plural': plural,
            'desc': desc,
        })

    # ---- TOWN ROOM EXITS ----
    while idx < len(parts) and parts[idx] == '':
        idx += 1
    num_rooms = int(parts[idx]); idx += 1
    town_exits = []
    for _ in range(num_rooms):
        while idx < len(parts) and parts[idx] == '':
            idx += 1
        row = parse_ints(parts[idx]); idx += 1
        # Pad to 10 directions
        while len(row) < 10:
            row.append(0)
        town_exits.append(row[:10])

    # ---- TOWN ROOM DESCRIPTIONS ----
    while idx < len(parts) and parts[idx] == '':
        idx += 1
    num_descs = int(parts[idx]); idx += 1
    town_rooms = []
    for room_num in range(num_descs):
        while idx < len(parts) and parts[idx] == '':
            idx += 1
        short_desc = parts[idx]; idx += 1
        while idx < len(parts) and parts[idx] == '':
            idx += 1
        long_desc = parts[idx]; idx += 1
        exits = town_exits[room_num] if room_num < len(town_exits) else [0]*10
        town_rooms.append({
            'id': room_num + 1,  # 1-indexed
            'short_desc': short_desc,
            'long_desc': long_desc,
            'exits': exits,  # [N,S,E,W,NE,NW,SE,SW,U,D]
        })

    return town_rooms, townsfolk_types


# ---------------------------------------------------------------------------
# Parse TSGARNDT.MCV  -- dungeon room descriptions
# ---------------------------------------------------------------------------

def parse_dungeon_rooms():
    parts = read_null_parts(os.path.join(SRC, 'TSGARNDT.MCV'))
    idx = 2  # skip header + empty

    # rumor messages come first
    while idx < len(parts) and parts[idx] == '':
        idx += 1
    num_rumors = int(parts[idx]); idx += 1
    rumors = []
    for _ in range(num_rumors):
        while idx < len(parts) and parts[idx] == '':
            idx += 1
        rumors.append(parts[idx]); idx += 1

    # dungeon room descriptions
    while idx < len(parts) and parts[idx] == '':
        idx += 1
    num_rooms = int(parts[idx]); idx += 1
    dungeon_rooms = []
    for i in range(num_rooms):
        while idx < len(parts) and parts[idx] == '':
            idx += 1
        short_desc = parts[idx]; idx += 1
        while idx < len(parts) and parts[idx] == '':
            idx += 1
        long_desc = parts[idx]; idx += 1
        dungeon_rooms.append({
            'desc_id': i,
            'short_desc': short_desc,
            'long_desc': long_desc,
        })

    return dungeon_rooms, rumors


# ---------------------------------------------------------------------------
# Parse TSGARNDD.MCV  -- dungeon layout, monster spawns, item spawns
# ---------------------------------------------------------------------------

def _skip_empty(parts, idx):
    while idx < len(parts) and parts[idx] == '':
        idx += 1
    return idx

def parse_dungeon_data():
    parts = read_null_parts(os.path.join(SRC, 'TSGARNDD.MCV'))
    idx = 2  # skip header + empty

    # World name (e.g. 'World One')
    idx = _skip_empty(parts, idx)
    world_name = parts[idx]; idx += 1

    # Number of worlds/dungeons (e.g. '1') — NOT the room count
    idx = _skip_empty(parts, idx)
    _num_worlds = int(parts[idx]); idx += 1

    # Item level ranges  (num_item_ranges entries of 3 ints)
    idx = _skip_empty(parts, idx)
    num_item_ranges = int(parts[idx]); idx += 1
    item_ranges = []
    for _ in range(num_item_ranges):
        idx = _skip_empty(parts, idx)
        item_ranges.append(parse_ints(parts[idx])); idx += 1

    # Terrain level ranges  (num_terr_ranges entries of 3 ints)
    idx = _skip_empty(parts, idx)
    num_terr_ranges = int(parts[idx]); idx += 1
    terr_ranges = []
    for _ in range(num_terr_ranges):
        idx = _skip_empty(parts, idx)
        terr_ranges.append(parse_ints(parts[idx])); idx += 1

    # Monster spawns: room monster_type count variant difficulty
    idx = _skip_empty(parts, idx)
    num_mon_spawns = int(parts[idx]); idx += 1
    monster_spawns = []
    for _ in range(num_mon_spawns):
        idx = _skip_empty(parts, idx)
        vals = parse_ints(parts[idx]); idx += 1
        if len(vals) >= 5:
            monster_spawns.append({
                'room': vals[0],
                'monster_type': vals[1],
                'count': vals[2],
                'variant': vals[3],
                'difficulty': vals[4],
            })

    # Item spawns: room item_type count variant ? ? ? ?
    idx = _skip_empty(parts, idx)
    num_item_spawns = int(parts[idx]); idx += 1
    item_spawns = []
    for _ in range(num_item_spawns):
        idx = _skip_empty(parts, idx)
        vals = parse_ints(parts[idx]); idx += 1
        if len(vals) >= 4:
            item_spawns.append({
                'room': vals[0],
                'item_type': vals[1],
                'count': vals[2],
                'variant': vals[3],
            })

    # Special items (gates, portals, etc.) — skip, we don't use them in pathing
    idx = _skip_empty(parts, idx)
    num_special = int(parts[idx]); idx += 1
    for _ in range(num_special):
        idx = _skip_empty(parts, idx)
        idx += 1  # skip entry

    # Dungeon room exits: num_dun_rooms entries, each has 11 values:
    #   N S E W NE NW SE SW U D desc_idx
    # Exit values are 1-based dungeon room numbers (0=no exit, negative=special)
    # -98 = exit to town dungeon entrance
    idx = _skip_empty(parts, idx)
    num_dun_rooms = int(parts[idx]); idx += 1
    dungeon_exits = {}  # 1-based room number -> [N,S,E,W,NE,NW,SE,SW,U,D]
    dungeon_room_descriptions = {}  # 1-based room number -> desc_idx
    for room_num in range(1, num_dun_rooms + 1):
        idx = _skip_empty(parts, idx)
        if idx >= len(parts):
            break
        vals = parse_ints(parts[idx]); idx += 1
        if len(vals) >= 10:
            exits = vals[:10]
            dungeon_exits[room_num] = exits
        if len(vals) >= 11:
            dungeon_room_descriptions[room_num] = vals[10]

    return {
        'world_name': world_name,
        'num_dun_rooms': num_dun_rooms,
        'monster_spawns': monster_spawns,
        'item_spawns': item_spawns,
        'item_ranges': item_ranges,
        'terr_ranges': terr_ranges,
        'dungeon_exits': dungeon_exits,
        'dungeon_room_descriptions': dungeon_room_descriptions,
    }


# ---------------------------------------------------------------------------
# Parse .MSG files  -- game messages
# ---------------------------------------------------------------------------

def parse_msg_file(filename):
    """Parse a Major BBS .MSG file into a dict of {name: text}."""
    try:
        with open(filename, 'r', encoding='latin-1', errors='replace') as f:
            content = f.read()
    except FileNotFoundError:
        return {}

    messages = {}
    # Pattern: NAME {content} T/S/B/N Description
    # Content can be multi-line
    pattern = re.compile(r'(\w+)\s*\{(.*?)\}\s*(?:T|S|B|N)\b', re.DOTALL)
    for m in pattern.finditer(content):
        name = m.group(1)
        text = m.group(2)
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        messages[name] = text

    return messages


# ---------------------------------------------------------------------------
# Parse misc weapon types from TSGARNDD.MCV remainder
# (monster weapon table used for armed monsters like skeleton warriors)
# ---------------------------------------------------------------------------

def parse_monster_weapons():
    """Parse monster weapon types from TSGARN-D.MCV after monster block."""
    # The monster weapon types are in TSGARN-D.MCV but we'll use a simple
    # approach: read all remaining text after monsters and parse weapon records
    # For now, return a hardcoded minimal list matching what the code uses
    # These are used when a monster is armed (shown as "armed with %s %s")
    weapons = [
        {'name': 'a rusty sword', 'type': 1, 'prefix': 1, 'mindam': 1, 'maxdam': 4},
        {'name': 'a club', 'type': 1, 'prefix': 1, 'mindam': 1, 'maxdam': 3},
        {'name': 'a spear', 'type': 1, 'prefix': 1, 'mindam': 1, 'maxdam': 6},
        {'name': 'a dagger', 'type': 1, 'prefix': 1, 'mindam': 1, 'maxdam': 3},
        {'name': 'a mace', 'type': 2, 'prefix': 1, 'mindam': 1, 'maxdam': 6},
        {'name': 'a morningstar', 'type': 2, 'prefix': 1, 'mindam': 2, 'maxdam': 8},
        {'name': 'a shortsword', 'type': 3, 'prefix': 1, 'mindam': 1, 'maxdam': 6},
        {'name': 'a longsword', 'type': 3, 'prefix': 1, 'mindam': 2, 'maxdam': 10},
        {'name': 'a battleax', 'type': 4, 'prefix': 1, 'mindam': 2, 'maxdam': 12},
        {'name': 'a halberd', 'type': 4, 'prefix': 1, 'mindam': 3, 'maxdam': 15},
    ]
    return weapons


# ---------------------------------------------------------------------------
# Parse shop data from TSGARN-T.MCV shop entries
# ---------------------------------------------------------------------------

def build_shop_data(town_rooms):
    """
    Determine which shops are at which town rooms based on room descriptions.
    Shop types: 0=none, 1=equipment, 2=weapon, 3=armor, 4=magic, 5=guild,
                6=temple, 7=vault, 8=tavern, 9=arena, 10=inn
    """
    shop_keywords = {
        'equipment shop': 1,
        'weapon shop': 2,
        'armor shop': 3,
        'magic shop': 4,
        'guild hall': 5,
        'temple': 6,
        'vault': 7,
        'tavern': 8,
        'arena': 9,
        'inn': 10,
        'docks': 11,
    }
    shops = []
    for room in town_rooms:
        desc = room['short_desc'].lower()
        shop_type = 0
        for keyword, stype in shop_keywords.items():
            if keyword in desc:
                shop_type = stype
                break
        if shop_type:
            shops.append({'room': room['id'], 'type': shop_type})
    return shops


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Parsing Tele-Arena 5.6 data files...")

    # Items, Spells, Monsters
    print("  Parsing TSGARN-D.MCV (items, spells, monsters)...")
    items, spells, monsters = parse_items_spells_monsters()
    print(f"    Found {len(items)} items, {len(spells)} spells, {len(monsters)} monsters")

    # Town data
    print("  Parsing TSGARN-T.MCV (town rooms, townsfolk)...")
    town_rooms, townsfolk_types = parse_town_data()
    print(f"    Found {len(town_rooms)} town rooms, {len(townsfolk_types)} townsfolk types")

    # Dungeon room descriptions
    print("  Parsing TSGARNDT.MCV (dungeon room descriptions)...")
    dungeon_rooms, rumors = parse_dungeon_rooms()
    print(f"    Found {len(dungeon_rooms)} dungeon room descriptions, {len(rumors)} rumors")

    # Dungeon data (monster/item spawns)
    print("  Parsing TSGARNDD.MCV (dungeon layout, monster/item spawns)...")
    dungeon_data = parse_dungeon_data()
    print(f"    World: '{dungeon_data['world_name']}', "
          f"{dungeon_data['num_dun_rooms']} dungeon rooms, "
          f"{len(dungeon_data['monster_spawns'])} monster spawns, "
          f"{len(dungeon_data['item_spawns'])} item spawns")

    # Messages
    print("  Parsing .MSG files...")
    main_msgs = parse_msg_file(os.path.join(SRC, 'TSGARN-M.MSG'))
    cfg_msgs = parse_msg_file(os.path.join(SRC, 'TSGARN-C.MSG'))
    all_msgs = {**cfg_msgs, **main_msgs}  # main overrides config
    print(f"    Found {len(all_msgs)} messages")

    # Monster weapons
    mwp = parse_monster_weapons()

    # Shop locations
    shops = build_shop_data(town_rooms)

    # Write output JSON files
    print("\nWriting JSON data files...")

    with open(os.path.join(OUT, 'items.json'), 'w') as f:
        json.dump(items, f, indent=2)
    print(f"  data/items.json ({len(items)} items)")

    with open(os.path.join(OUT, 'spells.json'), 'w') as f:
        json.dump(spells, f, indent=2)
    print(f"  data/spells.json ({len(spells)} spells)")

    with open(os.path.join(OUT, 'monsters.json'), 'w') as f:
        json.dump(monsters, f, indent=2)
    print(f"  data/monsters.json ({len(monsters)} monsters)")

    with open(os.path.join(OUT, 'town_rooms.json'), 'w') as f:
        json.dump(town_rooms, f, indent=2)
    print(f"  data/town_rooms.json ({len(town_rooms)} rooms)")

    with open(os.path.join(OUT, 'dungeon_rooms.json'), 'w') as f:
        json.dump(dungeon_rooms, f, indent=2)
    print(f"  data/dungeon_rooms.json ({len(dungeon_rooms)} room descriptions)")

    dungeon_data['dungeon_room_descriptions'] = dungeon_rooms
    with open(os.path.join(OUT, 'dungeon_data.json'), 'w') as f:
        json.dump(dungeon_data, f, indent=2)
    print(f"  data/dungeon_data.json")

    with open(os.path.join(OUT, 'messages.json'), 'w') as f:
        json.dump(all_msgs, f, indent=2)
    print(f"  data/messages.json ({len(all_msgs)} messages)")

    with open(os.path.join(OUT, 'monster_weapons.json'), 'w') as f:
        json.dump(mwp, f, indent=2)

    with open(os.path.join(OUT, 'shops.json'), 'w') as f:
        json.dump(shops, f, indent=2)
    print(f"  data/shops.json ({len(shops)} shops)")

    with open(os.path.join(OUT, 'townsfolk_types.json'), 'w') as f:
        json.dump(townsfolk_types, f, indent=2)

    with open(os.path.join(OUT, 'rumors.json'), 'w') as f:
        json.dump(rumors, f, indent=2)

    print("\nDone! Run 'python3 main.py' to play.")


if __name__ == '__main__':
    main()
