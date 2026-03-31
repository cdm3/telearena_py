"""
Tele-Arena 5.6 Python Port - World / Room Management
Handles town rooms (1..DUNOFF) and dungeon rooms (DUNOFF+1..)
"""

import json
import os
import random

from .constants import *

_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')


class Room:
    """A single room (town or dungeon)."""

    def __init__(self, room_id, short_desc='', long_desc='', exits=None,
                 shop_type=SHOP_NONE, is_dark=False, is_dungeon=False,
                 desc_id=0):
        self.id         = room_id
        self.short_desc = short_desc
        self.long_desc  = long_desc
        # exits[direction] = destination room id (0 = no exit)
        self.exits      = list(exits) if exits else [0] * 10
        self.shop_type  = shop_type
        self.is_dark    = is_dark
        self.is_dungeon = is_dungeon
        self.desc_id    = desc_id   # index into dungeon_room_descriptions

        # Dynamic content (reset between sessions)
        self.items      = [255] * (NMRMIT * 2)  # item slots (255=empty) + charges
        self.monsters   = [-1]  * NMRMMN         # monster instance ids

    def get_exit(self, direction):
        """Return destination room id for direction, 0 if none."""
        if 0 <= direction < 10:
            return self.exits[direction]
        return 0

    def has_exit(self, direction):
        return self.get_exit(direction) != 0

    def is_lit(self):
        """Dungeon rooms are dark unless a light source is present."""
        if not self.is_dungeon:
            return True
        return not self.is_dark

    def get_item(self, slot):
        """Get item index at slot (0..NMRMIT-1). 255 = empty."""
        if 0 <= slot < NMRMIT:
            return self.items[slot]
        return 255

    def get_item_charge(self, slot):
        if 0 <= slot < NMRMIT:
            return self.items[NMRMIT + slot]
        return 0

    def set_item(self, slot, item_idx, charge=0):
        if 0 <= slot < NMRMIT:
            self.items[slot] = item_idx
            self.items[NMRMIT + slot] = charge

    def clear_item(self, slot):
        if 0 <= slot < NMRMIT:
            self.items[slot] = 255
            self.items[NMRMIT + slot] = 0

    def find_empty_item_slot(self):
        for i in range(NMRMIT):
            if self.items[i] == 255:
                return i
        return -1

    def compact_items(self):
        """Shift items to fill gaps (shfobj equivalent)."""
        filled = [(self.items[i], self.items[NMRMIT + i])
                  for i in range(NMRMIT) if self.items[i] != 255]
        for i in range(NMRMIT):
            if i < len(filled):
                self.items[i] = filled[i][0]
                self.items[NMRMIT + i] = filled[i][1]
            else:
                self.items[i] = 255
                self.items[NMRMIT + i] = 0


class World:
    """
    Manages all rooms (town + dungeon) and active townsfolk.
    Equivalent of the global room/dungeon arrays in the original.
    """

    def __init__(self):
        self.rooms = {}           # room_id -> Room
        self.shops = {}           # room_id -> shop_type
        self.dungeon_descs = []   # list of {desc_id, short_desc, long_desc}
        self.rumors = []
        self.world_name = 'World One'
        self.num_dun_rooms = 0

        # Townsfolk (static NPC instances)
        self.townsfolk = []       # list of {id, type_id, room, name, plural, desc}
        self.townsfolk_types = [] # loaded from file

        # Monster spawns (initial configuration)
        self.monster_spawns = []
        self.item_spawns = []

    def load(self):
        """Load all world data from JSON files."""
        self._load_town_rooms()
        self._load_dungeon_data()
        self._load_shops()
        self._load_townsfolk()

    def _load_town_rooms(self):
        path = os.path.join(_data_dir, 'town_rooms.json')
        if not os.path.exists(path):
            self._create_fallback_town()
            return
        with open(path) as f:
            town_data = json.load(f)
        for rd in town_data:
            room = Room(
                room_id=rd['id'],
                short_desc=rd.get('short_desc', ''),
                long_desc=rd.get('long_desc', ''),
                exits=rd.get('exits', [0]*10),
                is_dungeon=False,
            )
            self.rooms[rd['id']] = room

    # Town room used when returning from dungeon via -98 exit (the docks area)
    DUNGEON_TOWN_ENTRANCE = 12

    def _load_dungeon_data(self):
        path = os.path.join(_data_dir, 'dungeon_data.json')
        if not os.path.exists(path):
            return
        with open(path) as f:
            dd = json.load(f)
        self.world_name = dd.get('world_name', 'World One')
        self.num_dun_rooms = dd.get('num_dun_rooms', 0)
        self.monster_spawns = dd.get('monster_spawns', [])
        self.item_spawns = dd.get('item_spawns', [])
        dungeon_exits = dd.get('dungeon_exits', {})

        # Load dungeon room description text
        desc_path = os.path.join(_data_dir, 'dungeon_rooms.json')
        if os.path.exists(desc_path):
            with open(desc_path) as f:
                self.dungeon_descs = json.load(f)

        # Create Room objects for all 3096 dungeon rooms using real exit data
        # dungeon_exits keys are strings (JSON) -> convert to int
        exits_by_room = {int(k): v for k, v in dungeon_exits.items()}
        num_descs = max(1, len(self.dungeon_descs))

        for dun_rid in range(1, self.num_dun_rooms + 1):
            game_room_id = dun_rid + DUNOFF
            if game_room_id in self.rooms:
                continue

            # desc_idx cycles through 862 descriptions
            d_idx = (dun_rid - 1) % num_descs

            short, long_ = '', ''
            if self.dungeon_descs:
                entry = self.dungeon_descs[d_idx]
                short = entry.get('short_desc', '')
                long_ = entry.get('long_desc', '')

            room = Room(
                room_id=game_room_id,
                short_desc=short,
                long_desc=long_,
                is_dungeon=True,
                is_dark=True,
                desc_id=d_idx,
            )

            # Apply real exits
            raw_exits = exits_by_room.get(dun_rid, [0] * 10)
            for d in range(10):
                ex = raw_exits[d] if d < len(raw_exits) else 0
                if ex > 0:
                    room.exits[d] = ex + DUNOFF   # convert to absolute room id
                elif ex == -98:
                    room.exits[d] = self.DUNGEON_TOWN_ENTRANCE  # return to town
                else:
                    room.exits[d] = 0

            self.rooms[game_room_id] = room

        # Add dungeon entrance to town: docks (room 12) down -> dungeon room 1
        docks = self.rooms.get(self.DUNGEON_TOWN_ENTRANCE)
        if docks and docks.exits[DIR_D] == 0:
            docks.exits[DIR_D] = DUNOFF + 1

        # Rumors
        rumors_path = os.path.join(_data_dir, 'rumors.json')
        if os.path.exists(rumors_path):
            with open(rumors_path) as f:
                self.rumors = json.load(f)

    def _load_shops(self):
        path = os.path.join(_data_dir, 'shops.json')
        if not os.path.exists(path):
            return
        with open(path) as f:
            shops = json.load(f)
        for s in shops:
            room_id = s['room']
            stype = s['type']
            self.shops[room_id] = stype
            if room_id in self.rooms:
                self.rooms[room_id].shop_type = stype

    def _load_townsfolk(self):
        path = os.path.join(_data_dir, 'townsfolk_types.json')
        if not os.path.exists(path):
            return
        with open(path) as f:
            self.townsfolk_types = json.load(f)
        # Place some townsfolk in appropriate town rooms
        self._place_townsfolk()

    def _place_townsfolk(self):
        """Place townsfolk NPC instances in town rooms based on shop type."""
        shop_folk_map = {
            SHOP_EQUIPMENT: [0, 1, 2, 3],  # shop keeper variants
            SHOP_WEAPON:    [4, 5],
            SHOP_ARMOR:     [2, 3],
            SHOP_MAGIC:     [6, 7],        # crimson mage, master sorceror
            SHOP_TEMPLE:    [8, 9],        # priests
            SHOP_TAVERN:    [10, 11, 12],  # barkeep, barmaids
            SHOP_INN:       [10, 13, 14],  # barkeep, barmaids
        }
        folk_id = 0
        for room_id, shop_type in self.shops.items():
            if shop_type in shop_folk_map:
                for tidx in shop_folk_map.get(shop_type, []):
                    if tidx < len(self.townsfolk_types):
                        ft = self.townsfolk_types[tidx]
                        self.townsfolk.append({
                            'id': folk_id,
                            'type_id': tidx,
                            'room': room_id,
                            'name': ft['name'],
                            'plural': ft['plural'],
                            'desc': ft['desc'],
                            'active': 1,
                            'prefix': ft.get('prefix', 0),
                        })
                        folk_id += 1

    def _create_fallback_town(self):
        """Create a minimal town if data files aren't available."""
        # Room layout:
        # 1=Town Square, 2=Arena, 3=Equipment Shop, 4=Temple,
        # 5=Tavern, 6=Weapon Shop, 7=Guild Hall, 8=Vault,
        # 9=Armor Shop, 10=Magic Shop, 11=North Path, 12=South Path
        fallback = [
            (1,  'Town Square',    'You are standing in the town square.',
             [11, 12, 6, 9, 0, 0, 0, 0, 0, 0], SHOP_NONE),
            (2,  'Arena',          'You are in the arena.',
             [1, 0, 0, 0, 0, 0, 0, 0, 0, 0], SHOP_ARENA),
            (3,  'Equipment Shop', 'You are in the equipment shop.',
             [0, 0, 0, 1, 0, 0, 0, 0, 0, 0], SHOP_EQUIPMENT),
            (4,  'Temple',         'You are in the temple.',
             [1, 0, 0, 0, 0, 0, 0, 0, 0, 0], SHOP_TEMPLE),
            (5,  'Tavern',         'You are in the tavern.',
             [0, 1, 0, 0, 0, 0, 0, 0, 0, 0], SHOP_TAVERN),
            (6,  'Weapon Shop',    'You are in the weapon shop.',
             [0, 0, 0, 1, 0, 0, 0, 0, 0, 0], SHOP_WEAPON),
            (7,  'Guild Hall',     'You are in the guild hall.',
             [0, 0, 1, 0, 0, 0, 0, 0, 0, 0], SHOP_GUILD),
            (8,  'Town Vaults',    'You are in the town vaults.',
             [0, 0, 0, 1, 0, 0, 0, 0, 0, 0], SHOP_VAULT),
            (9,  'Armor Shop',     'You are in the armor shop.',
             [0, 0, 1, 0, 0, 0, 0, 0, 0, 0], SHOP_ARMOR),
            (10, 'Magic Shop',     'You are in the magic shop.',
             [0, 0, 0, 1, 0, 0, 0, 0, 0, 0], SHOP_MAGIC),
            (11, 'North Path',     'You are on the north path.',
             [0, 1, 0, 0, 0, 0, 0, 0, 0, DUNOFF+1], SHOP_NONE),
            (12, 'South Path',     'You are on the south path.',
             [1, 0, 5, 4, 0, 0, 0, 3, 0, 0], SHOP_NONE),
        ]
        for (rid, short, long_, exits, stype) in fallback:
            room = Room(rid, short, long_, exits, stype, False, False)
            self.rooms[rid] = room
            if stype != SHOP_NONE:
                self.shops[rid] = stype

        # Create a minimal dungeon
        for i in range(1, 21):
            rid = DUNOFF + i
            desc_idx = (i - 1) % max(1, len(self.dungeon_descs))
            short = "You're in a cave."
            long_ = "You are in a damp cave."
            if self.dungeon_descs:
                entry = self.dungeon_descs[desc_idx]
                short = entry.get('short_desc', short)
                long_ = entry.get('long_desc', long_)
            exits = [0] * 10
            if i > 1:
                exits[DIR_N] = DUNOFF + i - 1
            if i < 20:
                exits[DIR_S] = DUNOFF + i + 1
            if i == 1:
                exits[DIR_U] = 11  # up to north path
            room = Room(rid, short, long_, exits, SHOP_NONE, True, True, desc_idx)
            self.rooms[rid] = room

    # ------------------------------------------------------------------
    # Room access
    # ------------------------------------------------------------------

    def get_room(self, room_id):
        return self.rooms.get(room_id)

    def is_town(self, room_id):
        return 1 <= room_id <= DUNOFF

    def is_dungeon(self, room_id):
        return room_id > DUNOFF

    def get_shop_type(self, room_id):
        if room_id in self.rooms:
            return self.rooms[room_id].shop_type
        return SHOP_NONE

    def is_shop(self, room_id, shop_type):
        return self.get_shop_type(room_id) == shop_type

    def get_townsfolk_in_room(self, room_id):
        return [f for f in self.townsfolk if f['room'] == room_id and f['active']]

    def get_rumor(self):
        if self.rumors:
            return random.choice(self.rumors)
        return "You hear nothing of interest."

    # ------------------------------------------------------------------
    # Item placement helpers
    # ------------------------------------------------------------------

    def place_initial_items(self, items_db):
        """Place items in dungeon rooms based on spawn data."""
        for spawn in self.item_spawns:
            room_id = spawn['room'] + DUNOFF
            room = self.rooms.get(room_id)
            if room is None:
                continue
            item_type = spawn['item_type']
            if item_type < 0 or item_type >= len(items_db):
                continue
            count = spawn.get('count', 1)
            for _ in range(count):
                slot = room.find_empty_item_slot()
                if slot == -1:
                    break
                room.set_item(slot, item_type, 0)
