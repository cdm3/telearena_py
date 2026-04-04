"""
Tele-Arena 5.6 Python Port - Monster Management
Corresponds to arnmon/arnmon2/arnmon3/arnmon4/monarr structs.
"""

import json
import os
import random

from .constants import *

_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

# Monster prefixes
MON_PREFIX_WORDS = ['a', 'an', 'the', 'some']


class MonsterType:
    """Static monster definition (monarr struct)."""

    def __init__(self, data):
        self.id       = data.get('id', 0)
        self.name     = data.get('name', 'creature')
        self.plural   = data.get('plural', 'creatures')
        self.long_desc= data.get('long_desc', '')
        self.weapon   = data.get('weapon', '')
        self.spcatt   = data.get('spcatt', '')
        self.spcabd   = data.get('spcabd', '')
        self.prefix   = data.get('prefix', 0)    # article index
        self.cskl     = data.get('cskl', 75)     # combat skill (to-hit %)
        self.terr     = data.get('terr', 0)       # terrain type
        self.gp       = data.get('gp', 0)         # gold
        self.trs      = data.get('trs', 0)        # treasure value
        self.ac       = data.get('ac', 0)         # armor class
        self.sach     = data.get('sach', 0)       # special attack chance
        self.hd       = data.get('hd', 1)         # hit dice
        self.regen    = data.get('regen', 0)      # regeneration rate
        self.mindam   = data.get('min_dam', data.get('mindam', 1))  # min damage
        self.maxdam   = data.get('max_dam', data.get('maxdam', 4))  # max damage
        self.minspc   = data.get('minspc', 0)     # min special damage
        self.maxspc   = data.get('maxspc', 0)     # max special damage
        self.effect   = data.get('effect', 0)     # special effect type
        self.mineff   = data.get('mineff', 0)     # min special effect
        self.maxeff   = data.get('maxeff', 0)     # max special effect
        self.spcabn   = data.get('spcabn', 0)     # special ability
        self.atts     = data.get('atts', 1)       # attacks per turn
        self.level    = data.get('level', 1)      # monster level
        self.morale   = data.get('morale', 50)    # morale (0-255)
        self.sskl     = data.get('sskl', 0)       # spell skill
        self.spllst   = data.get('spllst', 0)     # spell list
        self.minspl   = data.get('minspl', 0)     # min spell
        self.maxspl   = data.get('maxspl', 0)     # max spell
        self.gender   = data.get('gender', 0)     # 0=neuter, 1=male, 2=female
        self.subtyp   = data.get('subtyp', 0)     # subtype

    @property
    def article(self):
        return MON_PREFIX_WORDS[self.prefix] if 0 <= self.prefix < len(MON_PREFIX_WORDS) else 'a'

    @property
    def pronoun(self):
        if self.gender == 1:
            return 'him'
        elif self.gender == 2:
            return 'her'
        return 'it'

    @property
    def pronoun_self(self):
        if self.gender == 1:
            return 'himself'
        elif self.gender == 2:
            return 'herself'
        return 'itself'

    def max_hp(self, level=None):
        """Calculate max HP for a monster instance of given level."""
        lvl = level if level is not None else self.level
        return max(1, self.hd * lvl * random.randint(4, 8))

    @property
    def display_name(self):
        """Returns the name wrapped in bright red ANSI codes."""
        return f"\u001b[1;31m{self.name}\u001b[0m"


class MonsterInstance:
    """
    Active monster instance (arnmon + arnmon2 + arnmon3 + arnmon4).
    """

    def __init__(self, instance_id, mon_type, room_id, level=None, variant=0):
        self.id       = instance_id
        self.type_id  = mon_type.id
        self.type     = mon_type

        # arnmon fields
        self.active   = True
        self.level    = level if level is not None else mon_type.level
        self.regen    = mon_type.regen
        self.psn      = mon_type.spcabn  # poison level if applicable
        self.attack   = 0    # attack index
        # sach randomized at spawn time per genmon():
        #   arnrnd((level>>1)+1, sach+(level<<1))
        sach_lo = max(1, (self.level >> 1) + 1)
        sach_hi = max(sach_lo, mon_type.sach + (self.level << 1))
        self.sach     = random.randint(sach_lo, sach_hi)

        self.morale   = mon_type.morale
        self.rndwep   = 0    # random weapon index
        self.attdly   = 0    # individual attack delay
        self.protect  = 256  # protecting user id (256=none)

        # arnmon2 fields
        self.prey     = 256  # preying on user id (256=none)
        mhp = mon_type.hd * self.level * random.randint(4, 8)
        self.mhits    = max(1, mhp)
        self.hits     = self.mhits
        self.dloc     = room_id  # current room

        # arnmon3 fields
        xp_base = (self.level * 50) + (mon_type.cskl * self.level // 10)
        self.exp      = max(1, xp_base)
        self.gp       = random.randint(0, mon_type.gp) if mon_type.gp > 0 else 0
        self.trs      = random.randint(0, mon_type.trs) if mon_type.trs > 0 else 0

        # arnmon4
        self.subtyp   = mon_type.subtyp

        # State
        self.attdly        = 0
        self.regen_counter = 0
        self.variant = variant
        self.attack_cooldown = 3  # seconds before first attack (cbtcnt equivalent)
        self.is_guardian   = False   # True if this is a lair guardian
        self.lair_item_id  = 0       # 1-indexed lair item to drop on death (0 = none)

    @property
    def alive(self):
        return self.active and self.hits > 0

    @property
    def hp_pct(self):
        if self.mhits <= 0:
            return 0
        return self.hits / self.mhits

    def health_desc(self):
        pct = self.hp_pct
        name = self.type.name
        if pct <= 0.25:
            return f'The {name} is sorely wounded.'
        elif pct <= 0.50:
            return f'The {name} seems to be moderately wounded.'
        elif pct <= 0.75:
            return f'The {name} appears to be wounded.'
        elif pct < 1.0:
            return f'It looks as if the {name} is lightly wounded.'
        else:
            return f'The {name} seems to be in good physical health.'


class MonsterManager:
    """
    Manages all active monster instances (equivalent of arnmar arrays).
    """

    def __init__(self):
        self.types = []               # list of MonsterType
        self.instances = {}           # id -> MonsterInstance
        self._next_id = 0
        self._room_monsters = {}      # room_id -> list of instance ids

    def load_types(self):
        """Load monster type definitions from JSON."""
        path = os.path.join(_data_dir, 'monsters.json')
        if not os.path.exists(path):
            self._create_fallback_types()
            return
        with open(path) as f:
            data = json.load(f)
        self.types = []
        for i, d in enumerate(data):
            d['id'] = i
            self.types.append(MonsterType(d))

    def save(self):
        """Serialize active monster instances."""
        saves_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'saves')
        os.makedirs(saves_dir, exist_ok=True)
        state_path = os.path.join(saves_dir, 'monster_state.json')
        
        state = {
            'next_id': self._next_id,
            'instances': {}
        }
        for uid, inst in self.instances.items():
            if inst.active and inst.hits > 0:
                state['instances'][uid] = {
                    'type_id': inst.type_id,
                    'dloc': inst.dloc,
                    'level': inst.level,
                    'mhits': inst.mhits,
                    'hits': inst.hits,
                    'exp': inst.exp,
                    'gp': inst.gp,
                    'trs': inst.trs,
                    'variant': inst.variant,
                    'is_guardian': inst.is_guardian,
                    'lair_item_id': inst.lair_item_id,
                }
        with open(state_path, 'w') as f:
            json.dump(state, f, indent=2)

    def load_state(self):
        """Load and inject active monster instances into the manager."""
        saves_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'saves')
        state_path = os.path.join(saves_dir, 'monster_state.json')
        if not os.path.exists(state_path):
            return
            
        with open(state_path, 'r') as f:
            state = json.load(f)
            
        self._next_id = state.get('next_id', 0)
        self.instances.clear()
        self._room_monsters.clear()
        
        for uid_str, data in state.get('instances', {}).items():
            uid = int(uid_str)
            type_id = data.get('type_id', 0)
            if 0 <= type_id < len(self.types):
                mon_type = self.types[type_id]
                inst = MonsterInstance(uid, mon_type, data.get('dloc', 0), data.get('level', mon_type.level))
                inst.mhits = data.get('mhits', inst.mhits)
                inst.hits = data.get('hits', inst.hits)
                inst.exp = data.get('exp', inst.exp)
                inst.gp = data.get('gp', inst.gp)
                inst.trs = data.get('trs', inst.trs)
                inst.variant = data.get('variant', 0)
                inst.is_guardian = data.get('is_guardian', False)
                inst.lair_item_id = data.get('lair_item_id', 0)
                self.instances[uid] = inst
                
                rid = inst.dloc
                if rid not in self._room_monsters:
                    self._room_monsters[rid] = []
                self._room_monsters[rid].append(uid)

    def _create_fallback_types(self):
        """Minimal fallback monster set."""
        fallback = [
            {'name': 'rat',         'plural': 'rats',         'prefix': 0, 'cskl': 60, 'hd': 1, 'level': 1,  'mindam': 1, 'maxdam': 3,  'gp': 2,  'morale': 40, 'ac': 0, 'atts': 1, 'gender': 0},
            {'name': 'kobold',      'plural': 'kobolds',      'prefix': 0, 'cskl': 65, 'hd': 1, 'level': 1,  'mindam': 1, 'maxdam': 4,  'gp': 5,  'morale': 50, 'ac': 1, 'atts': 1, 'gender': 1},
            {'name': 'orc',         'plural': 'orcs',         'prefix': 0, 'cskl': 70, 'hd': 2, 'level': 2,  'mindam': 1, 'maxdam': 6,  'gp': 10, 'morale': 60, 'ac': 2, 'atts': 1, 'gender': 1},
            {'name': 'zombie',      'plural': 'zombies',      'prefix': 0, 'cskl': 70, 'hd': 2, 'level': 2,  'mindam': 1, 'maxdam': 5,  'gp': 3,  'morale': 80, 'ac': 1, 'atts': 1, 'gender': 0},
            {'name': 'skeleton',    'plural': 'skeletons',    'prefix': 0, 'cskl': 75, 'hd': 2, 'level': 3,  'mindam': 1, 'maxdam': 8,  'gp': 8,  'morale': 75, 'ac': 3, 'atts': 1, 'gender': 0},
            {'name': 'giant spider','plural': 'giant spiders','prefix': 0, 'cskl': 80, 'hd': 3, 'level': 4,  'mindam': 2, 'maxdam': 8,  'gp': 15, 'morale': 55, 'ac': 2, 'atts': 2, 'gender': 0, 'sach': 30, 'minspc': 1, 'maxspc': 4, 'effect': 1},
            {'name': 'hobgoblin',   'plural': 'hobgoblins',   'prefix': 0, 'cskl': 80, 'hd': 3, 'level': 4,  'mindam': 2, 'maxdam': 10, 'gp': 20, 'morale': 65, 'ac': 3, 'atts': 1, 'gender': 1},
            {'name': 'gnoll',       'plural': 'gnolls',       'prefix': 0, 'cskl': 80, 'hd': 3, 'level': 5,  'mindam': 2, 'maxdam': 12, 'gp': 25, 'morale': 65, 'ac': 3, 'atts': 2, 'gender': 1},
            {'name': 'troll',       'plural': 'trolls',       'prefix': 0, 'cskl': 85, 'hd': 5, 'level': 7,  'mindam': 3, 'maxdam': 14, 'gp': 50, 'morale': 80, 'ac': 4, 'atts': 2, 'gender': 1, 'regen': 2},
            {'name': 'ogre',        'plural': 'ogres',        'prefix': 0, 'cskl': 85, 'hd': 6, 'level': 8,  'mindam': 3, 'maxdam': 16, 'gp': 75, 'morale': 70, 'ac': 4, 'atts': 2, 'gender': 1},
            {'name': 'dragon',      'plural': 'dragons',      'prefix': 1, 'cskl': 95, 'hd': 10,'level': 15, 'mindam': 5, 'maxdam': 30, 'gp': 500,'morale': 90, 'ac': 8, 'atts': 3, 'gender': 0},
        ]
        for i, d in enumerate(fallback):
            d['id'] = i
            d.setdefault('long_desc', f'The {d["name"]} is a dangerous creature.')
            d.setdefault('trs', d.get('gp', 0) * 2)
            self.types.append(MonsterType(d))

    def spawn(self, type_id, room_id, level=None, variant=0):
        """Spawn a new monster instance in a room."""
        if type_id < 0 or type_id >= len(self.types):
            return None
        if len(self.instances) >= NMON:
            return None
        room = self.get_room_monsters(room_id)
        if len(room) >= NMRMMN:
            return None

        mtype = self.types[type_id]
        mid = self._next_id
        self._next_id += 1
        inst = MonsterInstance(mid, mtype, room_id, level, variant)
        self.instances[mid] = inst
        self._room_monsters.setdefault(room_id, []).append(mid)
        return inst

    def despawn(self, monster_id):
        """Remove a monster instance."""
        if monster_id in self.instances:
            inst = self.instances[monster_id]
            inst.active = False
            room_list = self._room_monsters.get(inst.dloc, [])
            if monster_id in room_list:
                room_list.remove(monster_id)
            del self.instances[monster_id]

    def move_monster(self, monster_id, new_room_id):
        """Move a monster to a new room."""
        if monster_id not in self.instances:
            return
        inst = self.instances[monster_id]
        old_room = self._room_monsters.get(inst.dloc, [])
        if monster_id in old_room:
            old_room.remove(monster_id)
        inst.dloc = new_room_id
        self._room_monsters.setdefault(new_room_id, []).append(monster_id)

    def get_room_monsters(self, room_id):
        """Return list of active monster instance ids in a room."""
        ids = self._room_monsters.get(room_id, [])
        return [mid for mid in ids if mid in self.instances and self.instances[mid].alive]

    def get_monster_by_name(self, room_id, name):
        """Find a monster in a room by (partial) name match."""
        name_lower = name.lower()
        for mid in self.get_room_monsters(room_id):
            inst = self.instances[mid]
            if name_lower in inst.type.name.lower():
                return inst
        return None

    def populate_lairs(self, world):
        """Place fixed lair monsters in their designated rooms.

        Source: SYSCMD.H 'relair' command -- BOTH branches spawn lair[i][1]:
            while (++j < lair[i][2]):
                if (j == lair[i][2]-1) and guardian_flag > 0:
                    genmon(room+DUNOFF, lair[i][1], ..., lair_index)  # tagged guardian
                else:
                    genmon(room+DUNOFF, lair[i][1], ..., -1)           # untagged
        field[3] (guardian_flag) is NOT a secondary monster type -- both branches
        spawn the SAME monster type (lair[i][1]). The flag only controls whether
        the last monster is associated with the lair index for tracking/treasure.
        """
        num_types = max(1, len(self.types))
        for lair in world.fixed_lairs:
            room_id       = lair['room']        # Already absolute WorldID (RID + 100)
            monster_type  = lair['monster']     # 1-indexed monster ID (MNAM1..MNAM161)
            count         = lair.get('count', 1)
            guardian_flag = lair.get('guardian_flag', 0)

            if room_id not in world.rooms:
                continue

            type_idx = (monster_type - 1) % num_types
            for j in range(count):
                inst = self.spawn(type_idx, room_id)
                # If this is the last monster and guardian_flag > 0:
                # Tag it as a lair guardian and store the item it drops on death.
                # guardian_flag = 1-indexed item ID (e.g. 39 = iron key, 40 = copper key)
                if inst and j == count - 1 and guardian_flag > 0:
                    inst.is_guardian = True
                    inst.lair_item_id = guardian_flag   # 1-indexed item ID to drop on death



    def populate_wanderers(self, world):
        """Spawn wandering monsters based on terrain zones.
        
        Each room has a terrain type (from DD2 ranges).
        Monsters with a matching terr field (from MSTT) can wander into that zone.
        Rooms that are fixed lairs are skipped (can't wander into lair rooms).
        
        Source: genmon() - wander check skips lair rooms via:
            while (++i < nmlair): if (lair[i][0]+DUNOFF == lc): return(0);
        """
        num_types = max(1, len(self.types))
        # Build a set of lair rooms to exclude from wandering
        lair_rooms = {lair['room'] for lair in world.fixed_lairs}

        # Build per-terrain monster lists
        terrain_monsters = {}
        for idx, mtype in enumerate(self.types):
            terr = getattr(mtype, 'terr', -1)
            if terr >= 0:
                terrain_monsters.setdefault(terr, []).append(idx)

        for zone in world.terrain_zones:
            terrain = zone.get('terrain', 99)
            if terrain == 99:
                continue  # No wandering in this zone

            valid_types = terrain_monsters.get(terrain, [])
            if not valid_types:
                continue

            start_world = zone['start']
            end_world = zone['end']
            for room_id in range(start_world, end_world + 1):
                if room_id in lair_rooms:
                    continue  # Can't wander into lair rooms
                if room_id not in world.rooms:
                    continue
                # ~10% chance of a wanderer in any given room
                if random.randint(1, 100) <= 10:
                    type_idx = random.choice(valid_types)
                    self.spawn(type_idx, room_id)

    def populate_dungeon(self, world, min_room=1):
        """Legacy method — calls populate_lairs and populate_wanderers."""
        self.populate_lairs(world)
        self.populate_wanderers(world)

    def populate_initial(self, world):
        """Initial monster placement for game start."""
        # Place fixed lair monsters in their designated rooms
        self.populate_lairs(world)
        # Place wandering monsters by terrain zone
        self.populate_wanderers(world)

    def tick_regen(self):
        """Regenerate monster HP (called periodically)."""
        for inst in list(self.instances.values()):
            if not inst.alive:
                continue
            if inst.type.regen > 0 and inst.hits < inst.mhits:
                inst.hits = min(inst.mhits, inst.hits + inst.type.regen)
