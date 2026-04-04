"""
Tele-Arena 5.6 Python Port - Character Management
Corresponds to arnchr / arnsav structs and genchr() / loadchr() / savechr()
"""

import json
import os
import random

from .constants import *

SAVES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'saves')


class Character:
    """
    Equivalent of struct arnchr + arnchr2 + arnchr3 combined.
    All fields match the C struct names as closely as possible.
    """

    def __init__(self):
        # Identity
        self.userid = ''
        self.sex = 'M'

        # Core attributes
        self.race   = 0
        self.clas   = 0
        self.level  = DEFLEV
        self.exp    = DEFEXP
        self.badge  = 0
        self.promot = 0        # promotion flag (True = promoted)

        # Stats
        self.intl   = 0
        self.know   = 0
        self.phys   = 0
        self.stam   = 0
        self.agil   = 0
        self.chrs   = 0

        # Secondary stats (modified by spells/items)
        self.intl2  = 0
        self.know2  = 0
        self.phys2  = 0
        self.stam2  = 0
        self.agil2  = 0
        self.chrs2  = 0
        self.mspts2 = 0
        self.mhits2 = 0

        # HP / SP
        self.mhits  = 1
        self.hits   = 1
        self.mspts  = 0
        self.splpts = 0

        # Status
        self.status = 0        # 0=normal, 1=poisoned, 2=paralyzed, 3=drained
        self.ac     = DEFARC
        self.weapon = DEFWEP
        self.armor  = DEFARM
        self.wepdmg = 0        # weapon damage modifier
        self.armdmg = 0        # armor damage modifier

        # Encumbrance
        self.wt     = 0

        # Economy
        self.gold   = 0
        self.accbal = 0        # bank account balance

        # Combat
        self.atts   = DEFATT
        self.attdly = 0        # attack delay counter
        self.spldly = 0        # spell delay counter
        self.attcnt = 0        # attack count this round
        self.cbtcnt = 0        # combat count

        # Status effects
        self.poison  = 0       # poison level
        self.invcnt  = 0       # invisibility counter
        self.procnt  = 0       # protection counter
        self.parcnt  = 0       # paralysis counter
        self.stacnt  = [0] * 8 # stat effect counters
        self.movcnt  = 0       # movement count for specials
        self.actcnt  = 0       # command count for specials

        # Hunger/thirst
        self.food   = START_FOOD
        self.water  = START_WATER
        self.light  = 0        # light source counter

        # Sound
        self.sound  = 1
        self.pulls  = 0        # slot machine pulls
        self.title  = 0

        # Location
        self.dun    = 0        # dungeon number (0 = town)
        self.loc    = 1        # room number
        self.dungeon_return_room = 12  # town room to return to when exiting dungeon

        # Appearance
        self.complexion  = 1
        self.eyecolor    = 1
        self.haircolor   = 1
        self.hairstyle   = 1
        self.hairlength  = 1

        # Inventory: 12 slots
        self.invent = [-1] * NUMHLD
        self.charge = [0]  * NUMHLD

        # Spellbook: 8 slots (255 = empty)
        self.splbook = [255] * SPLBOK

        # Group
        self.grpnum  = -1
        self.grpact  = 1
        self.grpfol  = 0
        self.folcnt  = 0

        # Trail (movement history) - 20 arrays of 11 ints
        self.trail = [[0] * 11 for _ in range(20)]

        # Coordinates (3D for tracking)
        self.x = 0
        self.y = 0
        self.z = 0

        # Meta
        self.newchar = 0       # has user seen intro for this char?
        self.spccmd  = 0       # has entered a special command

    # ------------------------------------------------------------------
    # Properties for convenience
    # ------------------------------------------------------------------

    @property
    def alive(self):
        return self.hits > 0

    @property
    def hp_pct(self):
        if self.mhits <= 0:
            return 0
        return self.hits / self.mhits

    @property
    def race_name(self):
        return RACE_DATA[self.race]['name'] if 0 <= self.race < len(RACE_DATA) else 'Unknown'

    @property
    def class_name(self):
        idx = self.clas + (MAXCLASS if self.promot else 0)
        if 0 <= idx < len(CLASS_DATA):
            return CLASS_DATA[idx]['name']
        return 'Unknown'

    @property
    def class_plural(self):
        idx = self.clas + (MAXCLASS if self.promot else 0)
        if 0 <= idx < len(CLASS_DATA):
            return CLASS_DATA[idx]['pl']
        return 'Unknown'

    @property
    def display_level(self):
        return self.level - 25 if self.promot else self.level

    @property
    def can_cast(self):
        """Classes that use spellbooks."""
        return self.clas not in (CLS_WARRIOR, CLS_ROGUE, CLS_HUNTER, CLS_ARCHER)

    @property
    def max_encumb(self):
        return self.phys2 * ENCUMB_MULT

    def _calc_dynamic_mult(self):
        """Calculate dynamic XP multiplier (calcxp() in original 5.6)."""
        # Base multipliers
        if self.clas in (CLS_SORCEROR, CLS_DRUID):  # 1, 5
            base = 90
        elif self.clas in (CLS_ACOLYTE, CLS_NECROLYTE):  # 2, 7
            base = 75
        elif self.clas == CLS_ROGUE:  # 3
            base = 60
        else:  # Warrior (0), Hunter (4), Archer (6)
            base = 62

        if self.promot:
            # calcxp original: return(tmpx+(((arnarr[un].level-15)+1)*(tmpx>>1)));
            # (L-15)+1 is L-14
            return base + (self.level - 14) * (base // 2)
        else:
            # calcxp original: return(tmpx+((arnarr[un].level+1)*(tmpx>>1)));
            return base + (self.level + 1) * (base // 2)

    def can_advance(self):
        """Check if character is ready for training (original 5.6 formula)."""
        m = (self.level - 24) if self.promot else self.level
        dynamic_mult = self._calc_dynamic_mult()
        
        axp = dynamic_mult * (m * m)
        # Threshold: exp / (1000 + mult*m^2) >= Level
        ep = int(self.exp / (DEFEPL + axp)) + 1
        return ep > self.level

    def get_next_level_xp(self):
        """Calculate total experience required for next level (original 5.6 formula)."""
        m = (self.level - 24) if self.promot else self.level
        dynamic_mult = self._calc_dynamic_mult()
        
        axp = dynamic_mult * (m * m)
        return self.level * (DEFEPL + axp)

    def advance_level(self):
        """Perform level-up stat increases (original 5.6 logic)."""
        if not self.can_advance():
            return False
            
        self.level += 1
        
        # SP gains
        tmps = 0
        if self.clas in (CLS_SORCEROR, CLS_NECROLYTE):
            tmps = 2
        elif self.clas in (CLS_ACOLYTE, CLS_DRUID):
            tmps = 1
            
        if tmps > 0:
            if self.promot:
                tmps += 1
            self.mspts += tmps
            self.splpts += tmps
            self.mspts2 = self.mspts
            
        # HP gains
        idx = self.clas + (MAXCLASS if self.promot else 0)
        # We'll use the hits from CLASS_DATA
        class_bonus = CLASS_DATA[idx].get('hits', 0)
        h = random.randint(DEFHPL, DEFHPH) + (self.stam2 >> 2) + class_bonus
        
        self.mhits += h
        self.hits += h
        self.mhits2 = self.mhits
        
        # Reset combat stats
        self.atts = self.agil2 // 15 + 1
        self.pulls = 0
        
        # 34% chance for stat restore
        if random.randint(1, 100) < 34:
             # reset the temporary stats to match primary stats
             self.intl2 = self.intl
             self.know2 = self.know 
             self.phys2 = self.phys
             self.stam2 = self.stam
             self.agil2 = self.agil
             self.chrs2 = self.chrs
            
        return True

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self):
        return {
            'userid': self.userid,
            'sex': self.sex,
            'race': self.race,
            'clas': self.clas,
            'level': self.level,
            'exp': self.exp,
            'badge': self.badge,
            'promot': self.promot,
            'intl': self.intl, 'know': self.know,
            'phys': self.phys, 'stam': self.stam,
            'agil': self.agil, 'chrs': self.chrs,
            'intl2': self.intl2, 'know2': self.know2,
            'phys2': self.phys2, 'stam2': self.stam2,
            'agil2': self.agil2, 'chrs2': self.chrs2,
            'mspts2': self.mspts2, 'mhits2': self.mhits2,
            'mhits': self.mhits, 'hits': self.hits,
            'mspts': self.mspts, 'splpts': self.splpts,
            'status': self.status,
            'ac': self.ac,
            'weapon': self.weapon,
            'armor': self.armor,
            'wepdmg': self.wepdmg, 'armdmg': self.armdmg,
            'wt': self.wt,
            'gold': self.gold,
            'accbal': self.accbal,
            'atts': self.atts,
            'attdly': self.attdly,
            'spldly': self.spldly,
            'poison': self.poison,
            'dun': self.dun,
            'loc': self.loc,
            'light': self.light,
            'food': self.food,
            'water': self.water,
            'attcnt': self.attcnt,
            'invcnt': self.invcnt,
            'procnt': self.procnt,
            'parcnt': self.parcnt,
            'stacnt': self.stacnt,
            'invent': self.invent,
            'charge': self.charge,
            'splbook': self.splbook,
            'newchar': self.newchar,
            'sound': self.sound,
            'pulls': self.pulls,
            'title': self.title,
            'complexion': self.complexion,
            'eyecolor': self.eyecolor,
            'haircolor': self.haircolor,
            'hairstyle': self.hairstyle,
            'hairlength': self.hairlength,
            'accbal': self.accbal,
            'grpnum': self.grpnum,
            'x': self.x, 'y': self.y, 'z': self.z,
        }

    def can_promote(self):
        """Check if character is ready for elite promotion (Level 25)."""
        return self.level >= 25 and not self.promot

    def promote(self):
        """Perform elite promotion (original 5.6 logic)."""
        if not self.can_promote():
            return False
            
        self.promot = 1
        self.level = 26
        self.exp = 0
        
        # Apply primary stat bonuses for elite classes
        # Original logic: arnarr[usrnum].stat = arnarr[usrnum].stat2 += tcla[tmpc].stat
        idx = self.clas + MAXCLASS
        cd = CLASS_DATA[idx]
        
        self.intl = self.intl2 = self.intl2 + cd.get('intl', 0)
        self.know = self.know2 = self.know2 + cd.get('know', 0)
        self.phys = self.phys2 = self.phys2 + cd.get('phys', 0)
        self.stam = self.stam2 = self.stam2 + cd.get('stam', 0)
        self.agil = self.agil2 = self.agil2 + cd.get('agil', 0)
        self.chrs = self.chrs2 = self.chrs2 + cd.get('chrs', 0)
        
        # Base HP/SP for elite classes (from TSGARN-4.C:1310)
        hp_bases = [950, 450, 750, 650, 900, 550, 850, 450]
        sp_bases = [  0,  78,  52,   0,   0,  52,   0,  78]
        
        tmph = hp_bases[self.clas]
        tmps = sp_bases[self.clas]
        
        # Roll extra HP: random(10,30) + stam/4 + class_bonus
        class_bonus = cd.get('hits', 0)
        h_roll = random.randint(10, 30) + (self.stam2 >> 2) + class_bonus
        
        self.mhits = self.hits = self.mhits2 = tmph + h_roll
        self.mspts = self.splpts = self.mspts2 = tmps
        
        # Recalculate attacks/turn
        self.atts = self.agil2 // 15 + 1
        
        return True

    def from_dict(self, d):
        for key, val in d.items():
            if hasattr(self, key):
                setattr(self, key, val)
        return self

    # ------------------------------------------------------------------
    # Save / Load
    # ------------------------------------------------------------------

    def save(self):
        os.makedirs(SAVES_DIR, exist_ok=True)
        path = os.path.join(SAVES_DIR, f'{self.userid}.json')
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, userid):
        path = os.path.join(SAVES_DIR, f'{userid}.json')
        if not os.path.exists(path):
            return None
        c = cls()
        with open(path) as f:
            c.from_dict(json.load(f))
        return c

    @classmethod
    def exists(cls, userid):
        return os.path.exists(os.path.join(SAVES_DIR, f'{userid}.json'))


# ---------------------------------------------------------------------------
# Character generation (genchr equivalent)
# ---------------------------------------------------------------------------

def generate_character(char, numitm):
    """
    Generate stats for a new character (or re-roll at level 1).
    Equivalent to genchr(0) in TSGARN-2.C.
    """
    rd = RACE_DATA[char.race]
    cd = CLASS_DATA[char.clas]

    # Roll base stats (LOSTAT..HISTAT range)
    base = {
        'intl': random.randint(LOSTAT, HISTAT),
        'know': random.randint(LOSTAT, HISTAT),
        'phys': random.randint(LOSTAT, HISTAT),
        'stam': random.randint(LOSTAT, HISTAT),
        'agil': random.randint(LOSTAT, HISTAT),
        'chrs': random.randint(LOSTAT, HISTAT),
    }

    # Apply race + class modifiers — floor of 5, no upper cap (matches original)
    for stat in ('intl', 'know', 'phys', 'stam', 'agil', 'chrs'):
        val = base[stat] + rd.get(stat, 0) + cd.get(stat, 0)
        val = max(5, val)
        setattr(char, stat, val)

    # Copy primary stats to secondary stats
    char.intl2 = char.intl
    char.know2 = char.know
    char.phys2 = char.phys
    char.stam2 = char.stam
    char.agil2 = char.agil
    char.chrs2 = char.chrs

    # Generate HP: random(DEFHPL,DEFHPH) + stam//5 + class.hits  (genchr line 2502)
    char.mhits = random.randint(DEFHPL, DEFHPH) + (char.stam // 5) + cd.get('hits', 0)
    char.mhits2 = char.mhits
    char.hits = char.mhits

    # Generate SP: DEFSPT + class.spts; Sorceror(1) and Necrolyte(7) get +1  (genchr line 2505-2506)
    char.mspts = max(0, DEFSPT + cd.get('spts', 0))
    if char.clas in (CLS_SORCEROR, CLS_NECROLYTE):
        char.mspts += 1
    char.mspts2 = char.mspts
    char.splpts = char.mspts

    # Attacks per turn: agil/15 + 1  (genchr: chrptr->atts = (chrptr->agil/15)+1)
    char.atts = char.agil // 15 + 1

    # Starting gold: random(3,25) + race.gold + class.gold  (beggld config defaults 0)
    char.gold = random.randint(3, 25) + rd.get('gold', 0) + cd.get('gold', 0)

    # Defaults
    char.level  = DEFLEV
    char.exp    = DEFEXP
    char.badge  = 0
    char.promot = 0
    char.status = STS_NORMAL
    char.ac     = DEFARC
    char.weapon = DEFWEP
    char.armor  = DEFARM if DEFARM < numitm else 0
    char.wepdmg = 0
    char.armdmg = 0
    char.wt     = 0
    char.attdly = 0
    char.spldly = 0
    char.attcnt = 0
    char.cbtcnt = 0
    char.poison  = 0
    char.invcnt  = 0
    char.procnt  = 0
    char.parcnt  = 0
    char.stacnt  = [0] * 8
    char.grpnum  = -1   # own group
    char.grpact  = 1
    char.grpfol  = 0
    char.folcnt  = 0
    char.food    = START_FOOD
    char.water   = START_WATER
    char.light   = 0
    char.loc     = 1
    char.dun     = 0

    # Empty inventory and spellbook
    char.invent  = [-1] * NUMHLD
    char.charge  = [0]  * NUMHLD
    char.splbok_clear()

    char.newchar = 1
    return char


def Character_splbok_clear(self):
    self.splbook = [255] * SPLBOK

Character.splbok_clear = Character_splbok_clear


# ---------------------------------------------------------------------------
# Encumbrance check (chkwal equivalent)
# ---------------------------------------------------------------------------

def check_encumbrance(char, item_wt):
    """Return True if character can carry item_wt more stones."""
    return (char.wt + item_wt) <= char.max_encumb


# ---------------------------------------------------------------------------
# Inventory helpers
# ---------------------------------------------------------------------------

def find_empty_slot(char):
    """Return first empty inventory slot index, or -1 if full."""
    for i in range(NUMHLD):
        if char.invent[i] == -1:
            return i
    return -1


def find_item_in_inv(char, item_name, items_db, exact=False):
    """
    Find an item in character's inventory by name.
    Returns inventory slot index or -1.
    """
    name_lower = item_name.lower()
    for i in range(NUMHLD):
        idx = char.invent[i]
        if idx == -1 or idx >= len(items_db):
            continue
        item = items_db[idx]
        iname = item['name'].lower()
        idesc = item.get('desc', '').lower()
        if exact:
            if iname == name_lower or idesc == name_lower:
                return i
        else:
            if name_lower in iname or iname.startswith(name_lower) or name_lower in idesc:
                return i
    return -1


def recalc_encumbrance(char, items_db):
    """Recalculate encumbrance from inventory."""
    total = 0
    for i in range(NUMHLD):
        idx = char.invent[i]
        if idx != -1 and idx < len(items_db):
            total += items_db[idx]['wt']
    char.wt = total
