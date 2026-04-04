"""
Tele-Arena 5.6 Python Port - Constants
Translated from TSGARN-0.H
"""

# ---------------------------------------------------------------------------
# Game substates
# ---------------------------------------------------------------------------
PLYING  = 1          # regular play state
EXTING  = 2          # exiting
STTOFF  = 200        # arena substate offset

# Character creation substates (STTOFF + N)
STATE_INTRO1    = STTOFF + 1
STATE_INTRO2    = STTOFF + 2
STATE_INTRO3    = STTOFF + 3
STATE_RACE      = STTOFF + 4  # actually 5 in original but we simplify
STATE_COMPLEXION= STTOFF + 5
STATE_EYECOLOR  = STTOFF + 6
STATE_HAIRCOLOR = STTOFF + 7
STATE_HAIRSTYLE = STTOFF + 8
STATE_HAIRLENGTH= STTOFF + 9
STATE_CLASS     = STTOFF + 10
STATE_RESURRECT = STTOFF + 11

# ---------------------------------------------------------------------------
# Room layout constants
# ---------------------------------------------------------------------------
ARNSUB  = 100        # Town room BBS channel offset (not used directly in python port)
DUNOFF  = 100        # Dungeon room offset within room numbering
# Town rooms: 1..DUNOFF  (1..100)
# Dungeon rooms: DUNOFF+1 .. DUNOFF+nmdnrm  (101..N)

# ---------------------------------------------------------------------------
# Room/monster array sizes
# ---------------------------------------------------------------------------
NMRMIT  = 8          # Max items per room
NMRMMN  = 10         # Max monster slots per room
NMON    = 5000       # Max active monster instances
MAXRMS  = 10000      # Max rooms
NFLK    = 500        # Max townsfolk instances
MAXTRM  = 100        # Max town rooms
MAXSHP  = 50         # Max shops

# ---------------------------------------------------------------------------
# Character limits
# ---------------------------------------------------------------------------
NUMHLD  = 12         # Inventory slots
SPLBOK  = 8          # Spellbook slots
MAXRACE = 6
MAXCLASS= 8
MAXCOMP = 10         # Complexion choices
MAXECOL = 9          # Eye color choices
MAXHCOL = 11         # Hair color choices
MAXHSTL = 8          # Hair style choices
MAXHLNG = 5          # Hair length choices
MAXLEV  = 25         # Max level before promotion

# ---------------------------------------------------------------------------
# Character generation defaults
# ---------------------------------------------------------------------------
DEFLEV  = 1
DEFEXP  = 0
LOSTAT  = 5
HISTAT  = 15
DEFSPT  = 1
DEFARC  = 0
DEFWEP  = 0          # Default weapon (bare hands / dagger)
DEFARM  = 12         # Default armor (cloak)
DEFATT  = 2

DEFEPL  = 1000       # Base XP needed per level
DEFEPA  = 100        # XP gain per char level (added to base)
DEFHPL  = 10         # Base HP gain per level low
DEFHPH  = 20         # Base HP gain per level high
DEFSPA  = 1          # Spell point gain per level
DEFATA  = 3          # level/this+2 = attacks/turn

# ---------------------------------------------------------------------------
# Directions  (original game clockwise order: N=0,NE=1,E=2,SE=3,S=4,SW=5,W=6,NW=7,U=8,D=9)
# ---------------------------------------------------------------------------
DIR_N  = 0
DIR_NE = 1
DIR_E  = 2
DIR_SE = 3
DIR_S  = 4
DIR_SW = 5
DIR_W  = 6
DIR_NW = 7
DIR_U  = 8
DIR_D  = 9

# Short direction names (index = direction constant)
SDIR = ['north', 'northeast', 'east', 'southeast', 'south', 'southwest',
        'west', 'northwest', 'up', 'down']
ADIR = ['n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw', 'u', 'd']
# Opposite directions (matches original ent[]={4,5,6,7,0,1,2,3,9,8})
ODIR = [4, 5, 6, 7, 0, 1, 2, 3, 9, 8]

# ---------------------------------------------------------------------------
# Item types  (objarr.type)
# ---------------------------------------------------------------------------
ITM_MELEE1H     = 1   # 1-handed melee
ITM_MELEE2H     = 2   # 2-handed melee
ITM_MELEE_BLD   = 3   # bladed 2H
ITM_MELEE_BLT   = 4   # blunt 2H
ITM_MAG_MELEE1  = 5   # magical melee 1H
ITM_MAG_MELEE2  = 6   # magical melee 2H
ITM_MAG_MELEE3  = 7   # magical melee 3
ITM_THROWN      = 8   # thrown weapon
ITM_BOW         = 10  # bow
ITM_ARMOR_ROBE  = 11  # robes/cloak
ITM_ARMOR_LIGHT = 12  # light armor
ITM_ARMOR_MED   = 13  # medium armor
ITM_ARMOR_HVY   = 14  # heavy armor
ITM_ARMOR_SPEC1 = 15  # special armor 1
ITM_ARMOR_SPEC2 = 16  # special armor 2
ITM_MISC        = 21  # miscellaneous
ITM_AMMO        = 22  # ammunition
ITM_MAG_ITEM    = 31  # magical item (wands, etc.)
ITM_POTION      = 32  # potion
ITM_MAG_STAFF   = 33  # magical staff
ITM_KEY         = 41  # key

# Item effects
EFF_FOOD        = 1   # food
EFF_WATER_CHARGE= 2   # water (with charges)
EFF_HEALING     = 3   # healing potion
EFF_CURE_POISON = 4   # cure poison
EFF_CURE_STAT   = 5   # restore stat
EFF_FOOD_WATER  = 6   # food and water
EFF_WATER2      = 7   # water
EFF_STAT_BOOST  = 8   # stat boost (temporary)
EFF_MANA_RESTORE= 9   # restore mana
EFF_INVIS_ITEM  = 10  # item that makes invisible (not standard)
EFF_MULTI_HEAL  = 11  # large healing
EFF_DAMAGE      = 12  # area damage (wands, rods)
EFF_RUNE_AWARD  = 13  # awards a rune
EFF_PROTECTION  = 14  # protection spell effect
EFF_TIMED_EFFECT= 15  # timed area damage effect
EFF_LIGHT_USED  = 16  # light source (used/burning)
EFF_LIGHT       = 17  # light source
EFF_FULL_RESTORE= 18  # full HP/MP restore
EFF_AMMO_ITEM   = 19  # ammo container
EFF_PROJ_ITEM   = 20  # projectile (stone, dart, blowdart)

# Weapon range types
RANGE_MELEE     = 0
RANGE_SHORT     = 1
RANGE_MEDIUM    = 2
RANGE_LONG      = 3

# ---------------------------------------------------------------------------
# Spell types  (splarr.type)
# ---------------------------------------------------------------------------
SPL_DAMAGE      = 1   # damage spell (cold, fire, lightning, energy)
SPL_DARK_DMG    = 4   # dark energy damage (necrolyte)
SPL_HEALING     = 21  # healing spell
SPL_REGEN       = 22  # regeneration
SPL_SUMMON      = 31  # summon creature
SPL_CHARM       = 41  # charm/mesmerize
SPL_ENCHANT     = 33  # enchantment (armor boost)
SPL_CURE        = 11  # cure ailment
SPL_INVIS       = 12  # invisibility

# ---------------------------------------------------------------------------
# Character status values  (arnchr.status)
# ---------------------------------------------------------------------------
STS_NORMAL      = 0
STS_POISONED    = 1
STS_PARALYZED   = 2
STS_DRAINED     = 3

# Character classes
CLS_WARRIOR     = 0
CLS_SORCEROR    = 1
CLS_ACOLYTE     = 2
CLS_ROGUE       = 3
CLS_HUNTER      = 4
CLS_DRUID       = 5
CLS_ARCHER      = 6
CLS_NECROLYTE   = 7

# Character races
RACE_ELVEN      = 0
RACE_DWARVEN    = 1
RACE_GNOMISH    = 2
RACE_HUMAN      = 3
RACE_GOBLIN     = 4
RACE_HALFOGRE   = 5

# ---------------------------------------------------------------------------
# Race stat modifiers  (trac[])
# ---------------------------------------------------------------------------
RACE_DATA = [
    # Derived from max stat tables at tele-arena.tumblr.com/maxstats
    # race_mod = max_stat(warrior) - 15 - warrior_class_mod
    # name, abbrev, intl, know, phys, stam, agil, chrs, gold
    {'name': 'Elven',    'rc': 'El', 'intl':  1, 'know':  3, 'phys': -3, 'stam': -3, 'agil':  1, 'chrs':  1, 'gold':  0},
    {'name': 'Dwarven',  'rc': 'Dw', 'intl': -1, 'know':  0, 'phys':  2, 'stam':  1, 'agil': -1, 'chrs': -1, 'gold': 25},
    {'name': 'Gnomish',  'rc': 'Gn', 'intl': -1, 'know':  1, 'phys':  1, 'stam':  1, 'agil':  0, 'chrs': -2, 'gold': 10},
    {'name': 'Human',    'rc': 'Hu', 'intl':  0, 'know':  0, 'phys':  0, 'stam':  0, 'agil':  0, 'chrs':  0, 'gold': 50},
    {'name': 'Goblin',   'rc': 'Go', 'intl': -2, 'know': -2, 'phys':  0, 'stam':  2, 'agil':  8, 'chrs': -3, 'gold':  0},
    {'name': 'Half-Ogre','rc': 'HO', 'intl': -4, 'know': -4, 'phys':  8, 'stam':  8, 'agil': -4, 'chrs': -4, 'gold':  0},
]

# ---------------------------------------------------------------------------
# Class stat modifiers  (tcla[])
# ---------------------------------------------------------------------------
CLASS_DATA = [
    # Derived from max stat tables at tele-arena.tumblr.com/maxstats
    # class_mod = human_max - 15  (Human race mod = 0)
    # class_hits: max_vit = 20 + max_stam//5 + hits  =>  hits = max_vit - 20 - max_stam//5
    # name, abbrev, plural, intl, know, phys, stam, agil, chrs, hits, spts, gold
    {'name': 'Warrior',   'cl': 'Wa', 'pl': 'Warriors',   'intl': 3, 'know': 3, 'phys': 7, 'stam': 7, 'agil': 6, 'chrs': 1, 'hits': 10, 'spts': -1, 'gold': 50},
    {'name': 'Sorceror',  'cl': 'So', 'pl': 'Sorcerors',  'intl': 6, 'know': 7, 'phys': 3, 'stam': 3, 'agil': 3, 'chrs': 5, 'hits':  0, 'spts': 8, 'gold': 20},
    {'name': 'Acolyte',   'cl': 'Ac', 'pl': 'Acolytes',   'intl': 6, 'know': 6, 'phys': 3, 'stam': 6, 'agil': 3, 'chrs': 3, 'hits':  5, 'spts': 6, 'gold': 30},
    {'name': 'Rogue',     'cl': 'Ro', 'pl': 'Rogues',     'intl': 3, 'know': 5, 'phys': 6, 'stam': 5, 'agil': 7, 'chrs': 1, 'hits':  5, 'spts': -1, 'gold': 40},
    {'name': 'Hunter',    'cl': 'Hu', 'pl': 'Hunters',    'intl': 3, 'know': 3, 'phys': 6, 'stam': 7, 'agil': 6, 'chrs': 2, 'hits': 10, 'spts': -1, 'gold': 40},
    {'name': 'Druid',     'cl': 'Dr', 'pl': 'Druids',     'intl': 6, 'know': 7, 'phys': 3, 'stam': 3, 'agil': 3, 'chrs': 5, 'hits':  0, 'spts': 4, 'gold': 30},
    {'name': 'Archer',    'cl': 'Ar', 'pl': 'Archers',    'intl': 3, 'know': 5, 'phys': 5, 'stam': 5, 'agil': 6, 'chrs': 3, 'hits': 10, 'spts': -1, 'gold': 40},
    {'name': 'Necrolyte', 'cl': 'Ne', 'pl': 'Necrolytes', 'intl': 6, 'know': 7, 'phys': 3, 'stam': 3, 'agil': 3, 'chrs': 5, 'hits':  0, 'spts': 8, 'gold': 20},
    # Promoted classes (MAXCLASS+n) — same stat mods as base, used for display/level-up
    {'name': 'Warlord',       'cl': 'WL', 'pl': 'Warlords',       'intl': 3, 'know': 3, 'phys': 7, 'stam': 7, 'agil': 6, 'chrs': 1, 'hits': 10, 'spts': -1, 'gold': 0},
    {'name': 'Archmage',      'cl': 'AM', 'pl': 'Archmages',       'intl': 6, 'know': 7, 'phys': 3, 'stam': 3, 'agil': 3, 'chrs': 5, 'hits':  0, 'spts': 10, 'gold': 0},
    {'name': 'High Priest',   'cl': 'HP', 'pl': 'High Priests',    'intl': 6, 'know': 6, 'phys': 3, 'stam': 6, 'agil': 3, 'chrs': 3, 'hits':  5, 'spts':  8, 'gold': 0},
    {'name': 'Thief',         'cl': 'Th', 'pl': 'Thieves',         'intl': 3, 'know': 5, 'phys': 6, 'stam': 5, 'agil': 7, 'chrs': 1, 'hits':  5, 'spts': -1, 'gold': 0},
    {'name': 'Ranger',        'cl': 'Ra', 'pl': 'Rangers',         'intl': 3, 'know': 3, 'phys': 6, 'stam': 7, 'agil': 6, 'chrs': 2, 'hits': 10, 'spts': -1, 'gold': 0},
    {'name': 'Archdruid',     'cl': 'AD', 'pl': 'Archdruids',      'intl': 6, 'know': 7, 'phys': 3, 'stam': 3, 'agil': 3, 'chrs': 5, 'hits':  0, 'spts':  6, 'gold': 0},
    {'name': 'Master Archer', 'cl': 'MA', 'pl': 'Master Archers',  'intl': 3, 'know': 5, 'phys': 5, 'stam': 5, 'agil': 6, 'chrs': 3, 'hits': 10, 'spts': -1, 'gold': 0},
    {'name': 'Lich',          'cl': 'Li', 'pl': 'Liches',          'intl': 6, 'know': 7, 'phys': 3, 'stam': 3, 'agil': 3, 'chrs': 5, 'hits':  0, 'spts': 10, 'gold': 0},
]

# Status names
STATUS_NAMES = ['Normal', 'Poisoned', 'Paralyzed', 'Drained']

# Badge/rune colors
BADGE_COLORS = [
    'none', 'white', 'yellow', 'orange', 'red', 'violet', 'blue',
    'green', 'cyan', 'black', 'silver', 'gold', 'platinum',
]

# Complexion names
COMPLEXION_NAMES = [
    '', 'Porcelain', 'Pale', 'Creamy', 'Fair', 'Rosey',
    'Tan', 'Golden', 'Bronzed', 'Ruddy', 'Ebony',
]

# Eye color names
EYE_COLOR_NAMES = [
    '', 'Yellow', 'Green', 'Blue', 'Violet', 'Red',
    'Brown', 'Hazel', 'Gray', 'Black',
]

# Hair color names
HAIR_COLOR_NAMES = [
    '', 'White', 'Silver', 'Gray', 'Blonde', 'Copper',
    'Red', 'Brown', 'Black', 'Blue', 'Green', 'Purple',
]

# Hair style names
HAIR_STYLE_NAMES = [
    '', 'Straight', 'Wavy', 'Curly', 'Kinky', 'Wild',
    'Mohawked', 'Ponytailed', 'Pigtailed',
]

# Hair length names
HAIR_LENGTH_NAMES = [
    '', 'Short', 'Shoulder Length', 'Waist Length', 'Knee Length', 'Ankle Length',
]

# Article prefixes for monsters
MON_PREFIX = ['a', 'an', 'the', 'some']

# Shop types
SHOP_NONE      = 0
SHOP_EQUIPMENT = 1
SHOP_WEAPON    = 2
SHOP_ARMOR     = 3
SHOP_MAGIC     = 4
SHOP_GUILD     = 5
SHOP_TEMPLE    = 6
SHOP_VAULT     = 7
SHOP_TAVERN    = 8
SHOP_ARENA     = 9
SHOP_INN       = 10
SHOP_DOCKS     = 11

# Items sold in each shop type (by shop field value in item data)
SHOP_TYPE_MAP = {
    1: SHOP_EQUIPMENT,
    2: SHOP_WEAPON,
    3: SHOP_ARMOR,
    4: SHOP_MAGIC,
    5: SHOP_GUILD,
}

# Max encumbrance multiplier (phys2 * 50 = max carry weight)
ENCUMB_MULT = 50

# Food/water starting values
START_FOOD  = 7200
START_WATER = 3600

# Experience table: XP required to reach each level
def xp_for_level(level):
    """XP needed to reach given level (1-indexed)."""
    if level <= 1:
        return 0
    total = 0
    for l in range(2, level + 1):
        total += DEFEPL + (l - 1) * DEFEPA
    return total
