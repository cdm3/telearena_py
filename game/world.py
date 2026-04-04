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
                 desc_id=0, shop_tier=1, trap_type=0, trap_arg=0, trap_msg=0,
                 resident_monster_id=0, resident_item_id=0):
        self.id         = room_id
        self.short_desc = short_desc
        self.long_desc  = long_desc
        # exits[direction] = destination room id (0 = no exit)
        self.exits      = list(exits) if exits else [0] * 10
        self.shop_type  = shop_type
        self.shop_tier  = shop_tier
        self.is_dark    = is_dark
        self.is_dungeon = is_dungeon
        self.desc_id    = desc_id   # index into dungeon_room_descriptions
        self.resident_monster_id = resident_monster_id
        self.resident_item_id = resident_item_id

        # Dynamic content (reset between sessions)
        self.items      = [255] * (NMRMIT * 2)  # item slots (255=empty) + charges
        self.monsters   = [-1]  * NMRMMN         # monster instance ids
        self.gates      = []                   # list of {item_idx, direction, consume, msg_idx}
        self.trap_type  = trap_type
        self.trap_arg   = trap_arg
        self.trap_msg   = trap_msg

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
        self.fixed_lairs = []       # Fixed per-room lair placements (from LAIR data)
        self.terrain_zones = []     # DD2 terrain zones for wandering monsters
        self.dark_zones = []        # DD1 darkness zones
        self.global_gates = []    # Gates starting from room -99


    def load(self):
        """Load all world data from JSON files."""
        self._load_town_rooms()
        self._load_dungeon_data()
        self._load_shops()
        self._load_townsfolk()

    def save(self):
        """Save dynamic world state (dropped items and townsfolk)."""
        saves_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'saves')
        os.makedirs(saves_dir, exist_ok=True)
        state_path = os.path.join(saves_dir, 'world_state.json')
        
        dynamic_rooms = {}
        for rid, room in self.rooms.items():
            # Only save if there are items on the floor to save space
            if any(i != 255 for i in room.items[:NMRMIT]):
                dynamic_rooms[rid] = {
                    'items': room.items
                }
        
        state = {
            'rooms': dynamic_rooms,
            'townsfolk': self.townsfolk
        }
        with open(state_path, 'w') as f:
            json.dump(state, f, indent=2)

    def load_state(self):
        """Load dynamic world state to preserve abandoned items and townsfolk."""
        saves_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'saves')
        state_path = os.path.join(saves_dir, 'world_state.json')
        if not os.path.exists(state_path):
            return
            
        with open(state_path, 'r') as f:
            state = json.load(f)
            
        dynamic_rooms = state.get('rooms', {})
        for rid_str, data in dynamic_rooms.items():
            rid = int(rid_str)
            if rid in self.rooms:
                self.rooms[rid].items = data.get('items', [255]*(NMRMIT*2))
                
        if 'townsfolk' in state:
            self.townsfolk = state['townsfolk']

    def _load_town_rooms(self):
        path = os.path.join(_data_dir, 'town_rooms.json')
        if not os.path.exists(path):
            print("Warning: town_rooms.json not found!")
            return
        with open(path) as f:
            town_rooms = json.load(f)

        for rdata in town_rooms:
            room = Room(
                room_id=rdata['id'],
                short_desc=rdata.get('short_desc', ''),
                long_desc=rdata.get('long_desc', ''),
                is_dungeon=False,
            )
            raw_exits = rdata.get('exits', [0] * 10)
            for d in range(10):
                room.exits[d] = raw_exits[d] if d < len(raw_exits) else 0

            self.rooms[rdata['id']] = room

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
        self.fixed_lairs = dd.get('fixed_lairs', [])          # Fixed per-room placements
        self.terrain_zones = dd.get('terrain_zones', [])       # DD2 terrain zones (for wanderers)
        self.dark_zones = dd.get('dark_zones', [])             # DD1 darkness zones
        self.monster_spawns = dd.get('monster_spawns', [])     # Legacy (unused)
        self.item_spawns = dd.get('item_spawns', [])
        dungeon_exits = dd.get('dungeon_exits', {})
        dungeon_attributes = dd.get('dungeon_attributes', {})
        rdesc_by_room = {int(k): v for k, v in dd.get('dungeon_room_descriptions', {}).items()}

        # Load dungeon room description text indexed by desc_idx
        desc_path = os.path.join(_data_dir, 'dungeon_rooms.json')
        descs_by_idx = {}   # {desc_idx: {short_desc, long_desc}}
        if os.path.exists(desc_path):
            with open(desc_path) as f:
                self.dungeon_descs = json.load(f)
            # dungeon_rooms.json is a list; rooms store their own desc_idx in dungeon_room_descriptions.
            # We also build a lookup by the ROOM key for TSGARNDT ROOM{n} direct access.
            for entry in self.dungeon_descs:
                # each entry has 'id' (World room ID = RID+100), short_desc, long_desc
                rid = entry.get('id', 0) - 100  # back to RID
                stored_idx = rdesc_by_room.get(rid, 0)
                if stored_idx not in descs_by_idx:
                    descs_by_idx[stored_idx] = entry

        # Create Room objects for all dungeon rooms using real exit data
        exits_by_room = {int(k): v for k, v in dungeon_exits.items()}
        attrs_by_room = {int(k): v for k, v in dungeon_attributes.items()}

        # Build terrain zone lookup: RID -> terrain_type
        terrain_by_rid = {}
        for zone in self.terrain_zones:
            for rid in range(zone['start'] - 100, zone['end'] - 99):  # end inclusive, back to RID
                terrain_by_rid[rid] = zone['terrain']

        # Build dark zone lookup: RID -> zone_type (1=dark)
        dark_by_rid = {}
        for zone in self.dark_zones:
            for rid in range(zone['start'] - 100, zone['end'] - 99):
                dark_by_rid[rid] = zone['zone_type']

        for dun_rid in range(1, self.num_dun_rooms + 1):
            game_room_id = dun_rid + DUNOFF
            if game_room_id in self.rooms:
                continue

            # Get actual desc_idx for this room from dungeon_room_descriptions
            desc_idx = rdesc_by_room.get(dun_rid, 0)
            desc_entry = descs_by_idx.get(desc_idx, {})
            short = desc_entry.get('short_desc', "You're in a dungeon.")
            long_ = desc_entry.get('long_desc', short)

            # Darkness: DD2 zone_type==1 means dark (requires light source)
            is_dark = dark_by_rid.get(dun_rid, 0) == 1

            room = Room(
                room_id=game_room_id,
                short_desc=short,
                long_desc=long_,
                is_dungeon=True,
                is_dark=is_dark,
                desc_id=desc_idx,
                resident_monster_id=0,  # Populated by monsters.populate_lairs()
                resident_item_id=0,
            )
            room.terrain = terrain_by_rid.get(dun_rid, -1)  # terrain type for wanderers

            # Apply room attributes (traps)
            # Format from parse_data: [trap_type, trap_arg, trap_arg2]
            # trap_arg: for pit/one-way = dest_room_rid; for spike = XDES/XSTT index
            # trap_msg (trap_arg2): secondary data
            room_attrs = attrs_by_room.get(dun_rid, [])
            if room_attrs:
                room.trap_type = room_attrs[0]
                if len(room_attrs) > 1:
                    room.trap_arg = room_attrs[1]
                if len(room_attrs) > 2:
                    room.trap_msg = room_attrs[2]

            # Apply real exits
            raw_exits = exits_by_room.get(dun_rid, [0] * 10)
            for d in range(10):
                ex = raw_exits[d] if d < len(raw_exits) else 0
                if ex > 0:
                    room.exits[d] = ex + DUNOFF   # convert RID to absolute room id
                elif ex == -99:
                    room.exits[d] = -99  # Special portal marker
                elif ex < 0:
                    room.exits[d] = 100 + ex  # Return to town room (ARNSUB + offset, e.g. -98 -> 2, -90 -> 10)
                else:
                    room.exits[d] = 0

            self.rooms[game_room_id] = room

        # Apply gates/locked doors
        all_gates = dd.get('gates', [])
        for g in all_gates:
            from_rid = g['from_room']
            # Convert gate destination: positive=dungeon RID, negative=town (ARNSUB+offset), 0=none
            def _cvt(to_room):
                if to_room > 0:   return to_room + DUNOFF
                elif to_room < 0: return 100 + to_room   # e.g. -98 -> 2, -90 -> 10
                else:             return 0
            if from_rid > 0:
                game_room_id = from_rid + DUNOFF
                if game_room_id in self.rooms:
                    self.rooms[game_room_id].gates.append({
                        'item_idx':  g.get('item_idx', 255),
                        'direction': g.get('direction', -1),
                        'consume':   g.get('consume', 0),
                        'msg_idx':   g.get('msg_idx', 0),
                        'to_room':   _cvt(g['to_room'])
                    })
            elif from_rid == -99:
                self.global_gates.append({
                    'item_idx':  g.get('item_idx', 255),
                    'direction': g.get('direction', -1),
                    'consume':   g.get('consume', 0),
                    'msg_idx':   g.get('msg_idx', 0),
                    'to_room':   _cvt(g['to_room'])
                })

        # Bidirectional connection: dungeon entrance room 101 already points Up -> room 2
        # (via EXIT1 data: -98 -> 100+(-98) = 2). Set room 2 Down -> dungeon room 1.
        room2 = self.rooms.get(2)
        if room2 and room2.exits[DIR_D] == 0:
            room2.exits[DIR_D] = DUNOFF + 1

        # Add dungeon entrance from south plaza (room 10) SW -> dungeon room 183 (Mountains)
        south_plaza = self.rooms.get(10)
        if south_plaza and south_plaza.exits[DIR_SW] == 0:
            south_plaza.exits[DIR_SW] = DUNOFF + 183

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
            shops_data = json.load(f)
        for s in shops_data:
            room_id = s.get('room')
            shop_cat = s.get('shop_cat', 0)
            shop_type = s.get('shop_type', 0)
            tier = s.get('shop_tier', 1)
            
            if room_id in self.rooms:
                room = self.rooms[room_id]
                room.shop_cat = shop_cat
                room.shop_type = shop_type
                room.shop_tier = tier

    def _load_townsfolk(self):
        types_path = os.path.join(_data_dir, 'townsfolk_types.json')
        inst_path = os.path.join(_data_dir, 'townsfolk_instances.json')
        
        if os.path.exists(types_path):
            with open(types_path) as f:
                self.townsfolk_types = json.load(f)
                
        if os.path.exists(inst_path):
            with open(inst_path) as f:
                instances = json.load(f)
                for inst in instances:
                    # inst: {id, type_id, room, name}
                    tidx = inst['type_id']
                    if tidx < len(self.townsfolk_types):
                        ft = self.townsfolk_types[tidx]
                        self.townsfolk.append({
                            'id': inst['id'],
                            'type_id': tidx,
                            'room': inst['room'],
                            'name': ft['name'],
                            'plural': ft['plural'],
                            'desc': ft['desc'],
                            'active': 1,
                            'prefix': ft.get('prefix', 0),
                        })

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

    def get_shop_tier(self, room_id):
        if room_id in self.rooms:
            return self.rooms[room_id].shop_tier
        return 1

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
        """Place items in dungeon rooms based on range-based spawn data."""
        for spawn in self.item_spawns:
            rng = spawn.get('room_range', [0, 0])
            start, end = rng[0], rng[1]
            chance = spawn.get('chance', 10)
            item_list = spawn.get('items', [])
            
            if not item_list:
                continue

            for rid in range(start, end + 1):
                # Check probability
                if random.randint(1, 100) <= chance:
                    room_id = rid + DUNOFF
                    room = self.rooms.get(room_id)
                    if room:
                        # Pick a random item from the category
                        item_idx = random.choice(item_list)
                        if 0 <= item_idx < len(items_db):
                            slot = room.find_empty_item_slot()
                            if slot != -1:
                                room.set_item(slot, item_idx, 0)
