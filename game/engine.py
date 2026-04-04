"""
Tele-Arena 5.6 Python Port - Game Engine
Main game loop and command processor.
Translates telesh() / inparn() / entarn() / arnstt()
"""

import json
import os
import random

from .constants import *
from .character import (Character, generate_character, find_empty_slot,
                         find_item_in_inv, check_encumbrance, recalc_encumbrance)
from .world import World
from .monsters import MonsterManager
from . import messages as msg
from . import combat as cbt
from . import shops

_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')


import re as _re
_SHORT_DESC_RE = _re.compile(
    r"^you(?:'re| are)(?:\s+(?!in\b|inside\b|on\b|at\b)\w+)*\s+(?:in|inside|on|at)\s+(?:the\s+)?(.+?)\.?\s*$",
    _re.IGNORECASE,
)

def _room_short_name(room, loc):
    """Extract a terse room name from short_desc, e.g. 'north plaza'."""
    if room is None:
        return f'Room {loc}'
    m = _SHORT_DESC_RE.match(room.short_desc)
    if m:
        return m.group(1)
    return room.short_desc


class GameEngine:
    """
    Main game engine. Manages state and dispatches commands.
    Single-player version of the original BBS multi-player game.
    """

    def __init__(self):
        # Game data
        self.items_db   = []
        self.spells_db  = []

        # Game objects
        self.world      = World()
        self.monster_mgr= MonsterManager()
        self.char       = None    # current character

        # State
        self.state      = 0       # 0=creation, PLYING=playing, EXTING=exiting
        self.tick       = 0       # game tick counter
        self.running    = False
        self.combat_target = None  # monster instance id for auto-attack

        # Output buffer - UI reads from here
        self._output_buf = []     # list of (color_attr, text) segments

        # Input state
        self._pending_input = None

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def load_data(self):
        """Load all game data from JSON files and runtime state."""
        msg.load_messages()
        self._load_items()
        self._load_spells()
        self.world.load()
        self.monster_mgr.load_types()
        
        # Load persistence state (if any)
        self.world.load_state()
        self.monster_mgr.load_state()

    def _load_items(self):
        path = os.path.join(_data_dir, 'items.json')
        if os.path.exists(path):
            with open(path) as f:
                self.items_db = json.load(f)
        if not self.items_db:
            self._fallback_items()

    def _load_spells(self):
        path = os.path.join(_data_dir, 'spells.json')
        if os.path.exists(path):
            with open(path) as f:
                self.spells_db = json.load(f)

    def _fallback_items(self):
        self.items_db = [
            {'name': 'dagger',       'desc': 'a dagger',         'price': 15,  'wt': 10,  'range': 0, 'mindam': 1, 'maxdam': 3,  'type': 1,  'armor': 0,  'charges': 0, 'effect': 0, 'clas': 0, 'level': 0, 'shop': 2},
            {'name': 'shortsword',   'desc': 'a shortsword',     'price': 30,  'wt': 20,  'range': 0, 'mindam': 1, 'maxdam': 6,  'type': 3,  'armor': 0,  'charges': 0, 'effect': 0, 'clas': 0, 'level': 1, 'shop': 2},
            {'name': 'longsword',    'desc': 'a longsword',      'price': 50,  'wt': 30,  'range': 0, 'mindam': 2, 'maxdam': 10, 'type': 3,  'armor': 0,  'charges': 0, 'effect': 0, 'clas': 0, 'level': 3, 'shop': 2},
            {'name': 'mace',         'desc': 'a mace',           'price': 35,  'wt': 50,  'range': 0, 'mindam': 1, 'maxdam': 7,  'type': 2,  'armor': 0,  'charges': 0, 'effect': 0, 'clas': 0, 'level': 1, 'shop': 2},
            {'name': 'battleax',     'desc': 'a battleax',       'price': 60,  'wt': 50,  'range': 0, 'mindam': 2, 'maxdam': 12, 'type': 4,  'armor': 0,  'charges': 0, 'effect': 0, 'clas': 0, 'level': 3, 'shop': 2},
            {'name': 'halberd',      'desc': 'a halberd',        'price': 120, 'wt': 120, 'range': 0, 'mindam': 6, 'maxdam': 24, 'type': 4,  'armor': 0,  'charges': 0, 'effect': 0, 'clas': 0, 'level': 6, 'shop': 2},
            {'name': 'staff',        'desc': 'a staff',          'price': 10,  'wt': 40,  'range': 0, 'mindam': 1, 'maxdam': 4,  'type': 1,  'armor': 0,  'charges': 0, 'effect': 0, 'clas': 1, 'level': 1, 'shop': 2},
            {'name': 'cloak',        'desc': 'a cloak',          'price': 10,  'wt': 20,  'range': 0, 'mindam': 0, 'maxdam': 0,  'type': 11, 'armor': 0,  'charges': 0, 'effect': 0, 'clas': 0, 'level': 0, 'shop': 3},
            {'name': 'robes',        'desc': 'robes',            'price': 20,  'wt': 30,  'range': 0, 'mindam': 0, 'maxdam': 0,  'type': 11, 'armor': 1,  'charges': 0, 'effect': 0, 'clas': 1, 'level': 1, 'shop': 3},
            {'name': 'cuirass',      'desc': 'a leather cuirass','price': 40,  'wt': 50,  'range': 0, 'mindam': 0, 'maxdam': 0,  'type': 12, 'armor': 2,  'charges': 0, 'effect': 0, 'clas': 0, 'level': 2, 'shop': 3},
            {'name': 'chainmail',    'desc': 'chainmail armor',  'price': 300, 'wt': 400, 'range': 0, 'mindam': 0, 'maxdam': 0,  'type': 13, 'armor': 6,  'charges': 0, 'effect': 0, 'clas': 0, 'level': 3, 'shop': 3},
            {'name': 'platemail',    'desc': 'platemail armor',  'price': 600, 'wt': 600, 'range': 0, 'mindam': 0, 'maxdam': 0,  'type': 14, 'armor': 12, 'charges': 0, 'effect': 0, 'clas': 0, 'level': 8, 'shop': 3},
            {'name': 'cloak',        'desc': 'a cloak',          'price': 10,  'wt': 20,  'range': 0, 'mindam': 0, 'maxdam': 0,  'type': 11, 'armor': 0,  'charges': 0, 'effect': 0, 'clas': 0, 'level': 0, 'shop': 0},  # default armor idx=12
            {'name': 'torch',        'desc': 'a torch',          'price': 1,   'wt': 10,  'range': 0, 'mindam': 0, 'maxdam': 450,'type': 21, 'armor': 0,  'charges': 0, 'effect': 16,'clas': 0, 'level': 0, 'shop': 1},
            {'name': 'ration',       'desc': 'a ration of food', 'price': 2,   'wt': 5,   'range': 0, 'mindam': 0, 'maxdam': 3600,'type':21, 'armor': 0,  'charges': 0, 'effect': 1, 'clas': 0, 'level': 0, 'shop': 1},
            {'name': 'waterskin',    'desc': 'a waterskin',      'price': 1,   'wt': 10,  'range': 0, 'mindam': 0, 'maxdam': 1800,'type':21, 'armor': 0,  'charges': 3, 'effect': 2, 'clas': 0, 'level': 0, 'shop': 1},
            {'name': 'healing potion','desc':'a rue potion',     'price': 5,   'wt': 10,  'range': 0, 'mindam': 4, 'maxdam': 16, 'type': 32, 'armor': 0,  'charges': 0, 'effect': 3, 'clas': 0, 'level': 0, 'shop': 4},
        ]

    # ------------------------------------------------------------------
    # Character entry / creation (entarn / arnstt equivalents)
    # ------------------------------------------------------------------

    def enter_game(self, userid, sex='M'):
        """Load or start character creation."""
        self.running = True
        self.char = Character.load(userid)
        if self.char is None:
            self.char = Character()
            self.char.userid = userid
            self.char.sex = sex
            self.char.hits = 0    # triggers creation flow
        else:
            # Validate inventory
            for i in range(NUMHLD):
                if self.char.invent[i] >= len(self.items_db):
                    self.char.invent[i] = -1
                    self.char.charge[i] = 0
            # Validate spellbook
            for i in range(SPLBOK):
                if self.char.splbook[i] != 255 and self.char.splbook[i] >= len(self.spells_db):
                    self.char.splbook[i] = 255
            # Validate location
            if self.char.loc < 1:
                self.char.loc = 1
            if self.char.dun != 0:
                self.char.dun = 0
                self.char.loc = 1

        if self.char.hits < 1 and self.char.newchar == 0:
            # Brand new character - show intro
            self.state = STATE_INTRO1
            return self._intro_screen()
        elif self.char.hits < 1:
            # Dead character - show resurrection menu
            self.state = STATE_RESURRECT
            return self._resurrect_menu()
        else:
            # Returning player
            self.state = PLYING
            self._populate_world()
            return self._enter_world()

    def _populate_world(self):
        """Populate dungeon with monsters (on first entry)."""
        if not self.monster_mgr.instances:
            self.monster_mgr.populate_initial(self.world)
            self.world.place_initial_items(self.items_db)

    def _intro_screen(self):
        intro = msg.get('ARNINT1', '') + msg.get('HITRET')
        self.state = STATE_INTRO1
        return intro

    def _resurrect_menu(self):
        return msg.get('RESMNU', '0')

    def _enter_world(self):
        """Place character in world and show room."""
        out = msg.get('ENTRTA')
        out += self._look_room()
        return out

    # ------------------------------------------------------------------
    # State machine for character creation (arnstt equivalent)
    # ------------------------------------------------------------------

    def process_creation_input(self, text):
        """Handle input during character creation states."""
        text = text.strip()
        ans = 0
        try:
            ans = int(text)
        except ValueError:
            pass

        char = self.char
        state = self.state

        if state == STATE_INTRO1:
            self.state = STATE_INTRO2
            return msg.get('ARNINT2', '') + msg.get('HITRET')

        elif state == STATE_INTRO2:
            self.state = STATE_INTRO3
            return msg.get('ARNINT3', '') + msg.get('HITRET')

        elif state == STATE_INTRO3:
            self.state = STTOFF + 4   # -> race selection
            return msg.get('RACE') if 'RACE' in msg._messages else self._race_menu()

        elif state == STTOFF + 4:
            self.state = STTOFF + 5   # show race, go to complexion
            if 1 <= ans <= MAXRACE:
                char.race = ans - 1
                return msg.get('COMPLX') if 'COMPLX' in msg._messages else self._complexion_menu()
            return msg.get('INVALID', MAXRACE) if 'INVALID' in msg._messages else f'Invalid (1-{MAXRACE}): '

        elif state == STTOFF + 5:
            if 1 <= ans <= MAXCOMP:
                char.complexion = ans
                self.state = STTOFF + 6
                return msg.get('EYECOL') if 'EYECOL' in msg._messages else self._eye_menu()
            return msg.get('INVALID', MAXCOMP) if 'INVALID' in msg._messages else f'Invalid (1-{MAXCOMP}): '

        elif state == STTOFF + 6:
            if 1 <= ans <= MAXECOL:
                char.eyecolor = ans
                self.state = STTOFF + 7
                return msg.get('HARCOL') if 'HARCOL' in msg._messages else self._haircolor_menu()
            return msg.get('INVALID', MAXECOL) if 'INVALID' in msg._messages else f'Invalid (1-{MAXECOL}): '

        elif state == STTOFF + 7:
            if 1 <= ans <= MAXHCOL:
                char.haircolor = ans
                self.state = STTOFF + 8
                return msg.get('HARSTL') if 'HARSTL' in msg._messages else self._hairstyle_menu()
            return msg.get('INVALID', MAXHCOL) if 'INVALID' in msg._messages else f'Invalid (1-{MAXHCOL}): '

        elif state == STTOFF + 8:
            if 1 <= ans <= MAXHSTL:
                char.hairstyle = ans
                self.state = STTOFF + 9
                return msg.get('HARLNG') if 'HARLNG' in msg._messages else self._hairlength_menu()
            return msg.get('INVALID', MAXHSTL) if 'INVALID' in msg._messages else f'Invalid (1-{MAXHSTL}): '

        elif state == STTOFF + 9:
            if 1 <= ans <= MAXHLNG:
                char.hairlength = ans
                self.state = STTOFF + 10
                return msg.get('CLASS') if 'CLASS' in msg._messages else self._class_menu()
            return msg.get('INVALID', MAXHLNG) if 'INVALID' in msg._messages else f'Invalid (1-{MAXHLNG}): '

        elif state == STTOFF + 10:
            if 1 <= ans <= MAXCLASS:
                char.clas = ans - 1
                generate_character(char, len(self.items_db))
                char.loc = 1
                char.newchar = 1
                self.state = PLYING
                self._populate_world()
                char.save()
                out = msg.get('ENTRTA') if 'ENTRTA' in msg._messages else '\n*** Entering Tele-Arena...\n'
                out += self._look_room()
                return out
            return msg.get('INVALID', MAXCLASS) if 'INVALID' in msg._messages else f'Invalid (1-{MAXCLASS}): '

        elif state == STATE_RESURRECT:
            if ans == 1:
                # Resurrect (free in single-player mode)
                char.hits = 1
                char.splpts = 0
                char.poison = 0
                char.attdly = 60
                char.spldly = 60
                char.parcnt = 0
                char.invcnt = 0
                char.procnt = 0
                char.status = STS_NORMAL
                char.loc = 4
                char.dun = 0
                char.invent = [-1] * NUMHLD
                char.charge = [0] * NUMHLD
                char.splbok_clear()
                recalc_encumbrance(char, self.items_db)
                self.state = PLYING
                self._populate_world()
                char.save()
                return msg.get('ENTRTA', '') + self._look_room()
            elif ans == 2:
                # New character
                char.hits = 0
                char.newchar = 0
                self.state = STATE_INTRO1
                return self._intro_screen()
            else:
                self.state = EXTING
                return 'Goodbye!\n'

        return ''

    def _race_menu(self):
        lines = ['\n']
        races = [d['name'] for d in RACE_DATA]
        for i, r in enumerate(races, 1):
            lines.append(f'{i}) {r}\n')
        lines.append('\nSelect a race: ')
        return ''.join(lines)

    def _complexion_menu(self):
        lines = ['\n']
        for i, c in enumerate(COMPLEXION_NAMES[1:], 1):
            lines.append(f'{i}) {c}\n')
        lines.append('\nSelect a complexion: ')
        return ''.join(lines)

    def _eye_menu(self):
        lines = ['\n']
        for i, c in enumerate(EYE_COLOR_NAMES[1:], 1):
            lines.append(f'{i}) {c}\n')
        lines.append('\nSelect an eye color: ')
        return ''.join(lines)

    def _haircolor_menu(self):
        lines = ['\n']
        for i, c in enumerate(HAIR_COLOR_NAMES[1:], 1):
            lines.append(f'{i:>2}) {c}\n')
        lines.append('\nSelect a hair color: ')
        return ''.join(lines)

    def _hairstyle_menu(self):
        lines = ['\n']
        for i, c in enumerate(HAIR_STYLE_NAMES[1:], 1):
            lines.append(f'{i}) {c}\n')
        lines.append('\nSelect a hair style: ')
        return ''.join(lines)

    def _hairlength_menu(self):
        lines = ['\n']
        for i, c in enumerate(HAIR_LENGTH_NAMES[1:], 1):
            lines.append(f'{i}) {c}\n')
        lines.append('\nSelect a hair length: ')
        return ''.join(lines)

    def _class_menu(self):
        lines = ['\n']
        classes = CLASS_DATA[:MAXCLASS]
        for i, c in enumerate(classes, 1):
            lines.append(f'{i}) {c["name"]}\n')
        lines.append('\nSelect a class: ')
        return ''.join(lines)

    # ------------------------------------------------------------------
    # Main input processor (inparn equivalent)
    # ------------------------------------------------------------------

    def process_input(self, text):
        """
        Process player input during PLYING state.
        Returns output string.
        """
        if self.state != PLYING:
            return self.process_creation_input(text)

        char = self.char
        text = text.strip()
        if not text:
            return self._look_room()

        words = text.split()
        cmd = words[0].lower()
        args = words[1:] if len(words) > 1 else []
        arg1 = args[0].lower() if args else ''
        arg2 = args[1].lower() if len(args) > 1 else ''
        arg_str = ' '.join(args) if args else ''

        # Cancel auto-attack on non-combat/status commands
        if cmd not in ('attack', 'a', 'look', 'l', 'status', 'st', 'health', 'he', 
                        'experience', 'ep', 'exp', 'inventory', 'i', 'spells', 'sp', 'help', '?'):
            self.combat_target = None

        # Tick the game
        self._game_tick()

        # Exit
        if cmd in ('x', '/x', 'exit', 'quit', 'q'):
            return self._cmd_exit()

        # ---- One-word commands ----
        if cmd in ('look', 'l') and not args:
            return self._look_room()

        if cmd in ('status', 'st'):
            return self._cmd_status()

        if cmd in ('health', 'he'):
            return self._cmd_health()

        if cmd in ('experience', 'ep', 'exp'):
            return self._cmd_experience()

        if cmd in ('inventory', 'i'):
            return self._cmd_inventory()

        if cmd in ('spells', 'sp') and not args:
            return self._cmd_spells()

        if cmd in ('exits', 'ex') and not args:
            return self._cmd_exits()

        if cmd in ('players', 'pl') and not args:
            return '***\nYou are the only player in the game.\n'

        if cmd in ('group', 'gr') and not args:
            return '***\nYou are not currently in a group.\n'

        if cmd in ('help', '?') and not args:
            return self._cmd_help()

        if cmd == 'suicide':
            return self._cmd_suicide()

        if cmd == 'reroll' and char.level == 1:
            return self._cmd_reroll()

        if cmd in ('hunt', 'h') and not args:
            return self._cmd_hunt()

        if cmd in ('follow', 'fo') and not args:
            return '***\nYou are not in a group to follow.\n'

        if cmd in ('halt', 'ha') and not args:
            return '***\nYou stop following.\n'

        # ---- Direction movement ----
        for d, (full, abbr) in enumerate(zip(SDIR, ADIR)):
            if cmd == full or cmd == abbr:
                return self._cmd_move(d)

        # ---- Two+ word commands ----

        if cmd in ('look', 'l') and args:
            return self._cmd_look_at(arg_str)

        if cmd in ('attack', 'a') and args:
            return self._cmd_attack(arg_str)

        if cmd in ('get', 'g') and args:
            return self._cmd_get(arg_str)

        if cmd in ('drop', 'd') and args:
            return self._cmd_drop(arg_str)

        if cmd in ('eat', 'e') and args:
            return self._cmd_eat(arg_str)

        if cmd in ('drink', 'dr') and args:
            return self._cmd_drink(arg_str)

        if cmd in ('equip', 'eq') and args:
            return self._cmd_equip(arg_str)

        if cmd in ('unequip', 'un') and args:
            return self._cmd_unequip(arg_str)

        if cmd in ('use', 'u') and args:
            return self._cmd_use(arg_str)

        if cmd in ('light', 'li') and args:
            return self._cmd_light(arg_str)

        if cmd in ('cast', 'c') and args:
            if len(args) >= 2:
                return self._cmd_cast(args[0], ' '.join(args[1:]))
            else:
                return self._cmd_cast(args[0], 'ALL!')

        if cmd in ('purge', 'p') and args:
            return self._cmd_purge(arg_str)

        if cmd in ('buy', 'b') and args:
            return self._cmd_buy(arg_str)

        if cmd in ('sell', 's') and args:
            return self._cmd_sell(arg_str)

        if cmd in ('list', 'ls') and args:
            if arg1 in ('items', 'i', 'spells', 'sp'):
                return self._cmd_list(arg1)

        if cmd in ('give', 'gi') and len(args) >= 2:
            if args[-1] == 'gold':
                try:
                    amount = int(args[-2])
                    return self._cmd_give_gold(args[0], amount)
                except ValueError:
                    pass
            return self._cmd_give_item(args[0], ' '.join(args[1:]))

        if cmd in ('deposit', 'de') and args:
            return self._cmd_deposit(arg1)

        if cmd in ('withdraw', 'wi') and args:
            return self._cmd_withdraw(arg1)

        if cmd in ('balance', 'ba') and not args:
            return self._cmd_balance()

        if cmd in ('donate', 'do') and len(args) >= 2 and args[-1] in ('gold', 'g'):
            try:
                return self._cmd_donate(int(args[0]))
            except ValueError:
                pass

        if cmd in ('buy', 'b') and args and arg1 == 'spell':
            if len(args) >= 2:
                return self._cmd_buy_spell(' '.join(args[1:]))

        if cmd in ('play', 'pl') and args:
            if arg1 == 'slots':
                return self._cmd_slots()
            if arg1 in ('bones', 'dice'):
                return self._cmd_dice()

        if cmd in ('ring', 'ri') and args and arg1 in ('gong', 'g'):
            return self._cmd_ring_gong()

        if cmd in ('track', 'tr') and args:
            return self._cmd_track(arg_str)

        if cmd in ('gaze', 'ga') and arg1 == 'mirror':
            return self._cmd_inspect(char.userid)

        # Didn't understand
        return f'***\nWhat do you mean by "{text}"? Type HELP for a list of commands.\n'

    # ------------------------------------------------------------------
    # Command implementations
    # ------------------------------------------------------------------

    def _cmd_exit(self):
        char = self.char
        if char.attdly or char.spldly or char.cbtcnt:
            return msg.get('CNTMOV') if 'CNTMOV' in msg._messages else '***\nYou can\'t leave now!\n'
        if char.parcnt:
            return '***\nYou\'re paralyzed!\n'
        char.save()
        self.world.save()
        self.monster_mgr.save()
        
        self.state = EXTING
        self.running = False
        out = msg.get('EXITTA') if 'EXITTA' in msg._messages else '***\nExiting Tele-Arena...\n'
        return out

    def _look_room(self, brief=False):
        char = self.char
        room = self.world.get_room(char.loc)
        if room is None:
            return '***\nYou are somewhere strange...\n'

        out = '***\n'

        if room.is_dungeon and not room.is_lit() and not self._has_light(char):
            return '***\n\x1b[1;31mIt is too dark to see!\x1b[1;37m\n'

        # Room name header in yellow (matches original game), then long desc in bright white if not brief.
        out += '\x1b[1;33m' + room.short_desc + '\x1b[1;37m\n'
        if room.long_desc and not brief:
            colored_desc = room.long_desc[:500].replace('\n', '\x1b[1;37m\n\x1b[1;37m')
            out += '\x1b[1;37m' + colored_desc + '\x1b[1;37m\n'

        # Show townsfolk
        folk_in_room = self.world.get_townsfolk_in_room(char.loc)
        if folk_in_room:
            for folk in folk_in_room:
                out += msg.get('ONEOTH', folk['name'].capitalize())
        else:
            # Only show BYSELF if no monsters either (checked after)
            pass

        # Show monsters
        monsters_here = self.monster_mgr.get_room_monsters(char.loc)
        for mid in monsters_here:
            inst = self.monster_mgr.instances[mid]
            mtype = inst.type
            article_name = f'{mtype.article.capitalize()} {mtype.name}'
            out += msg.get('MONRED') + msg.get('SOMMN3', article_name, 'is')

        if not folk_in_room and not monsters_here:
            out += msg.get('BYSELF')

        # Show items in room
        item_descs = []
        for i in range(NMRMIT):
            itm = room.get_item(i)
            if itm != 255 and itm < len(self.items_db):
                item_descs.append(self.items_db[itm].get('desc', self.items_db[itm].get('name', 'item')))
        if item_descs:
            for desc in item_descs:
                out += msg.get('SOMTNG') + ' ' + desc + msg.get('ONFLOR')
        else:
            out += msg.get('NOTING')

        # Show exits (bright cyan)
        exits_str = self._get_exits_str(room)
        if exits_str:
            out += f'\x1b[1;34mObvious exits: {exits_str}.\x1b[1;37m\n'

        # Show shop prompt
        shop_type = room.shop_type
        if shop_type == SHOP_TAVERN:
            out += 'Type BUY FOOD or BUY DRINK to purchase refreshments.\n'
        elif shop_type in (SHOP_EQUIPMENT, SHOP_WEAPON, SHOP_ARMOR, SHOP_MAGIC):
            out += 'Type LIST ITEMS to see what\'s for sale, BUY <item> to purchase.\n'
        elif shop_type == SHOP_GUILD:
            out += 'Type LIST SPELLS to see available spells, BUY SPELL <name> to purchase.\n'
        elif shop_type == SHOP_VAULT:
            out += 'Type BALANCE, DEPOSIT <amount>, or WITHDRAW <amount>.\n'
        elif shop_type == SHOP_TEMPLE:
            out += ('Type BUY HEALING, BUY CURING, BUY REMOVAL, or BUY RESTORING.\n'
                    'Type DONATE <amount> GOLD to make an offering.\n')
        elif shop_type == SHOP_ARENA:
            out += 'You can fight the monsters here. Type ATTACK <monster> to engage.\n'

        return out

    def _get_exits_str(self, room):
        parts = []
        for d in range(10):
            dest = room.exits[d]
            if dest != 0:
                parts.append(ADIR[d])
        return ', '.join(parts) if parts else 'none'

    def _has_light(self, char):
        """Check if character has an active light source (torch burning or holding a glowstone)."""
        if getattr(char, 'light', 0) > 0:
            return True
        for itm_idx in char.invent:
            if 0 <= itm_idx < len(self.items_db):
                item = self.items_db[itm_idx]
                if item and item.get('effect') == EFF_LIGHT:
                    return True
        return False

    def _cmd_status(self):
        char = self.char
        wep_name = (self.items_db[char.weapon].get('name', 'bare hands')
                    if 0 <= char.weapon < len(self.items_db) else 'bare hands')
        arm_name = (self.items_db[char.armor].get('name', 'none')
                    if 0 <= char.armor < len(self.items_db) else 'none')
        wep_name = wep_name[0].upper() + wep_name[1:]
        arm_name = arm_name[0].upper() + arm_name[1:]

        lvl = char.display_level
        cls = char.class_name
        race = char.race_name
        status = STATUS_NAMES[char.status] if char.status < len(STATUS_NAMES) else 'Normal'
        badge = BADGE_COLORS[char.badge] if char.badge < len(BADGE_COLORS) else ''

        next_xp = char.get_next_level_xp()
        exp_str = f'{char.exp} / {next_xp}'
        out = msg.get('STATS', race, cls, lvl, exp_str, badge,
                       char.intl, char.know, char.phys, char.stam,
                       char.agil, char.chrs,
                       char.splpts, char.mspts,
                       char.hits, char.mhits,
                       status, char.ac, wep_name, arm_name,
                       char.wt, char.max_encumb)
        if 'Race:' not in out:
            # Fallback if STATS message not loaded
            out = (f'***\nRace:         {race}\nClass:        {cls}\nLevel:        {lvl}\n'
                   f'Experience:   {exp_str}\nRune:         {badge}\n\n'
                   f'Intellect:    {char.intl}\nKnowledge:    {char.know}\n'
                   f'Physique:     {char.phys}\nStamina:      {char.stam}\n'
                   f'Agility:      {char.agil}\nCharisma:     {char.chrs}\n\n'
                   f'Mana:         {char.splpts} / {char.mspts}\n'
                   f'Vitality:     {char.hits} / {char.mhits}\n'
                   f'Status:       {status}\nArmor Rating: {char.ac}\n\n'
                   f'Weapon:       {wep_name}\nArmor:        {arm_name}\n'
                   f'Encumbrance:  {char.wt} / {char.max_encumb}\n')
        return out

    def _cmd_health(self):
        char = self.char
        status = STATUS_NAMES[char.status] if char.status < len(STATUS_NAMES) else 'Normal'
        out = msg.get('STATS2', char.splpts, char.mspts, char.hits, char.mhits, status)
        if 'Mana:' not in out:
            out = (f'***\nMana:     {char.splpts} / {char.mspts}\n'
                   f'Vitality: {char.hits} / {char.mhits}\nStatus:   {status}\n')
        return out

    def _cmd_experience(self):
        char = self.char
        badge = BADGE_COLORS[char.badge] if char.badge < len(BADGE_COLORS) else ''
        next_xp = char.get_next_level_xp()
        exp_str = f'{char.exp} / {next_xp}'
        
        out = msg.get('STATS3', char.display_level, exp_str, badge)
        if 'Level:' not in out:
            out = f'***\nLevel:      {char.display_level}\nExperience: {exp_str}\nRune:       {badge}\n'
        return out

    def _cmd_inventory(self):
        char = self.char
        his_her = 'her' if char.sex == 'F' else 'his'

        out = f'***\n{char.userid} opens {his_her} pack and takes stock of {his_her} possessions.\n'
        out += f'Gold crowns: {char.gold}\n'

        items = []
        for i in range(NUMHLD):
            idx = char.invent[i]
            if idx != -1 and idx < len(self.items_db):
                item = self.items_db[idx]
                name = item.get('desc', item.get('name', 'item'))
                chg = char.charge[i]
                eff = item.get('effect', 0)
                is_wep = (idx == char.weapon)
                is_arm = (idx == char.armor)
                extra = ''
                if is_wep:
                    extra = ' [weapon]'
                elif is_arm:
                    extra = ' [armor]'
                if eff in (2, 19) and chg:
                    items.append(f'{name}({chg}){extra}')
                else:
                    items.append(f'{name}{extra}')

        if items:
            out += 'You are carrying: ' + ', '.join(items[:-1])
            if len(items) > 1:
                out += f', and {items[-1]}'
            else:
                out += items[-1] if items else ''
            out += '.\n'
        else:
            out += 'You are carrying nothing.\n'
        return out

    def _cmd_spells(self):
        char = self.char
        if not char.can_cast:
            return f'***\n{char.class_plural} don\'t use spellbooks!\n'

        his_her = 'her' if char.sex == 'F' else 'his'
        out = f'***\n{char.userid} opens {his_her} spellbook.\n'
        out += 'Spells known:\n'
        found = False
        for i in range(SPLBOK - 1, -1, -1):
            si = char.splbook[i]
            if si != 255 and si < len(self.spells_db):
                out += f'  {self.spells_db[si]["name"]}\n'
                found = True
        if not found:
            out += '  None.\n'
        return out

    def _cmd_exits(self):
        char = self.char
        room = self.world.get_room(char.loc)
        if room is None:
            return '***\nNo exits visible.\n'
        if room.is_dungeon and not room.is_lit() and not self._has_light(char):
            return '***\nIt is too dark to see!\n'
        exits_str = self._get_exits_str(room)
        # Show destination room numbers for each exit to help navigation
        dest_parts = []
        for d in range(10):
            if room.exits[d]:
                dest_parts.append(f'{ADIR[d]}:{room.exits[d]}')
        dest_info = ' '.join(dest_parts)
        return f'Exits: {exits_str}.\n({dest_info})\n'

    def _cmd_help(self):
        args = []
        room = self.world.get_room(self.char.loc)
        shop_type = room.shop_type if room else SHOP_NONE

        out = ('***\nGeneral commands:\n'
               '  LOOK (L)           - Look at your surroundings\n'
               '  STATUS (ST)        - Display your character stats\n'
               '  HEALTH (HE)        - Display HP/MP/status\n'
               '  EXPERIENCE (EP)    - Display level/XP info\n'
               '  INVENTORY (I)      - Show what you\'re carrying\n'
               '  EXITS (EX)         - Show available exits\n'
               '  N/S/E/W/NE/NW/... - Move in a direction\n'
               '  ATTACK (A) <name>  - Attack a monster or player\n'
               '  GET (G) <item>     - Pick up an item\n'
               '  DROP (D) <item>    - Drop an item\n'
               '  EAT (E) <item>     - Eat food\n'
               '  DRINK (DR) <item>  - Drink water\n'
               '  EQUIP (EQ) <item>  - Equip weapon or armor\n'
               '  UNEQUIP (UN) <item>- Unequip weapon or armor\n'
               '  USE (U) <item>     - Use an item\n'
               '  LIGHT (LI) <item>  - Light a torch\n'
               '  SPELLS (SP)        - Show your spellbook\n'
               '  CAST (C) <spell> [<target>] - Cast a spell\n'
               '  PURGE (P) <spell>  - Remove spell from spellbook\n'
               '  LOOK (L) <target>  - Inspect a character or monster\n'
               '  X                  - Exit the game\n')

        if shop_type in (SHOP_EQUIPMENT, SHOP_WEAPON, SHOP_ARMOR, SHOP_MAGIC):
            out += '\nShop commands:\n  LIST ITEMS  - See items for sale\n  BUY <item>  - Purchase an item\n  SELL <item> - Sell an item\n'
        if shop_type == SHOP_GUILD:
            out += '\nGuild commands:\n  LIST SPELLS    - See spells for purchase\n  BUY SPELL <spell> - Purchase a spell\n  BUY TRAINING   - Advance your level (cost: (level+1)*5 gold)\n  BUY PROMOTION  - Become an elite class (cost: 1000 gold)\n'
        if shop_type == SHOP_VAULT:
            out += '\nVault commands:\n  BALANCE  - Check account\n  DEPOSIT <amount>  - Deposit gold\n  WITHDRAW <amount> - Withdraw gold\n'
        if shop_type == SHOP_TEMPLE:
            out += ('\nTemple commands:\n'
                    '  BUY HEALING    - Fully restore HP (cost: (max-current)/10 + 1 gold)\n'
                    '  BUY CURING     - Cure poison (3 gold)\n'
                    '  BUY REMOVAL    - Remove paralysis (10 gold)\n'
                    '  BUY RESTORING  - Restore drained stats (25 gold)\n'
                    '  DONATE <amount> GOLD - Make a donation for XP\n')
        if shop_type == SHOP_TAVERN:
            out += '\nTavern commands:\n  BUY FOOD  - Buy a meal\n  BUY DRINK - Buy a drink\n  PLAY SLOTS - Play the slot machine\n  PLAY BONES - Play dice\n'
        return out

    def _cmd_suicide(self):
        char = self.char
        out = msg.get('YOUSUI') if 'YOUSUI' in msg._messages else '***\nAfter intense mental preparation, you take your own life!\nYou awaken after an unknown amount of time...\n'
        cbt.char_death(char, self)
        out += self._look_room()
        return out

    def _cmd_reroll(self):
        char = self.char
        char.hits = 0
        char.invcnt = 0
        char.loc = 1
        char.dun = 0
        generate_character(char, len(self.items_db))
        return '***\nRe-rolling your character...\n' + self._cmd_status()

    def _cmd_hunt(self):
        char = self.char
        monsters = self.monster_mgr.get_room_monsters(char.loc)
        if not monsters:
            return '***\nThere is nothing here to hunt.\n'
        inst = self.monster_mgr.instances[monsters[0]]
        msgs = cbt.attack_monster(char, inst, self.items_db, self.world, self)
        out = ''.join(msgs.get('you', []))
        if not char.alive:
            out += self._look_room()
        return out

    def _trigger_room_trap(self, char, room, msg_idx_override=0):
        """Processes a trap trigger upon entering a room or taking a situational exit."""
        trap_type = room.trap_type
        if msg_idx_override > 0:
            trap_type = 1  # Treat situational message links as pit traps

        if trap_type == 0:
            return ""

        # Rogue trap avoidance — uses XSTT rogpen for spike traps, 0 for others
        if char.clas == 3:  # CLS_ROGUE
            rogpen = 0
            if trap_type == 2:
                xdes_idx = room.trap_arg if room.trap_arg > 0 else 1
                xstt_raw = msg.get(f'XSTT{xdes_idx}', '10 30 0')
                xstt_vals = [int(x) for x in xstt_raw.split() if x.lstrip('-').isdigit()]
                rogpen = xstt_vals[2] if len(xstt_vals) > 2 else 0
            avoid_chance = (char.agil + char.know + char.level) - rogpen
            if random.randint(1, 100) <= avoid_chance:
                return '\n' + msg.get('AVDTRP', 'Your rogue abilities allowed you to detect and avoid a trap!') + '\n'

        out = ""
        if trap_type == 1:  # Pit trap — fall and land in dest room
            msg_text = msg.get('PYOU1', 'You just fell through a trap door in the floor!')
            dmg = random.randint(10, 20)
            char.hits = max(1, char.hits - dmg)
            out = f"\n*** {msg_text.strip()}\n*** You take {dmg} damage from the fall!\n"
            if room.trap_arg > 0 and msg_idx_override == 0:
                char.loc = room.trap_arg + DUNOFF

        elif trap_type == 2:  # Spike/damage trap — look up XDES/XSTT by index
            xdes_idx = room.trap_arg if room.trap_arg > 0 else 1
            msg_text = msg.get(f'XDES{xdes_idx}', 'A trap springs on you!')
            xstt_raw = msg.get(f'XSTT{xdes_idx}', '10 30 0')
            xstt_vals = [int(x) for x in xstt_raw.split() if x.lstrip('-').isdigit()]
            mindam = xstt_vals[0] if xstt_vals else 10
            maxdam = xstt_vals[1] if len(xstt_vals) > 1 else 30
            dmg = random.randint(mindam, maxdam)
            char.hits = max(1, char.hits - dmg)
            out = f"\n*** {msg_text.strip()}\n*** You take {dmg} damage!\n"

        elif trap_type == 3:  # One-way passage — silently teleport to dest room
            dest = room.trap_arg
            if dest > 0:
                msg_text = msg.get('PYOU1', 'You just fell through a trap door in the floor!')
                dmg = random.randint(5, 15)
                char.hits = max(1, char.hits - dmg)
                char.loc = dest + DUNOFF
                out = f"\n*** {msg_text.strip()}\n*** You take {dmg} damage from the fall!\n"

        return out

    def _cmd_move(self, direction):
        char = self.char

        # Check for attack delay or combat engagement
        room_monsters = self.monster_mgr.get_room_monsters(char.loc)
        if char.attdly > 0:
            return msg.get('ATTEXH') if 'ATTEXH' in msg._messages else f'***\nYou are still recovering from your last action! ({char.attdly})\n'
        
        # C-style combat check: can move if no monsters OR cbtcnt is 0
        if room_monsters and char.cbtcnt > 0:
            return '***\nYou are too busy fighting to move right now!\n'
            
        if char.parcnt > 0:
            return msg.get('PARLYZ') if 'PARLYZ' in msg._messages else '***\nYou are paralyzed and cannot move!\n'

        room = self.world.get_room(char.loc)
        if room is None:
            return '***\nYou can\'t go that way!\n'

        dest = room.get_exit(direction)
        out = ''
        
        # Check for gates/locked doors BEFORE checking if dest == 0
        active_gate = None
        skip_redirect = False
        for gate in room.gates:
            if gate['direction'] == direction:
                active_gate = gate
                break
        
        # If no room-specific gate, check for global portals if exit is -99
        if not active_gate and dest == -99:
            for gate in self.world.global_gates:
                if gate['direction'] == direction:
                    active_gate = gate
                    break
        
        if active_gate:
            key_idx = active_gate['item_idx']
            # If key_idx > 0, check inventory for that specific item index
            if key_idx > 0:
                found_slot = -1
                for i in range(NUMHLD):
                    if char.invent[i] == key_idx:
                        found_slot = i
                        break
                
                # If key missing, check if Rogue can pick it or climb
                if found_slot == -1:
                    if char.clas == 3: # CLS_ROGUE
                        # Authentic TA formula: (Agil + Know + Level) - Penalty
                        penalty = active_gate.get('rogue_penalty', 0)
                        pick_chance = (char.agil + char.know + char.level) - penalty
                        
                        if random.randint(1, 100) <= pick_chance:
                            if key_idx == 145: # ROPE
                                out += f'*** You use your Rogue skills to climb the surface without a rope!\n'
                            else:
                                out += f'*** You use your Rogue skills to pick the lock!\n'
                        else:
                            if key_idx == 145: # ROPE
                                return f'***\nYou try to climb without a rope, but you can\'t find enough handholds.\n'
                            else:
                                return f'***\nThe door is locked! Your attempts to pick it fail.\n'
                    else:
                        iname = self.items_db[key_idx]['name'] if 0 <= key_idx < len(self.items_db) else "a specific key"
                        if key_idx == 145: # ROPE
                            return f'***\nThis vertical climb requires a rope to pass safely!\n'
                        return f'***\nThe door is locked! You need {iname}.\n'
                else:
                    # Found the key!
                    iname = self.items_db[key_idx]['name'] if 0 <= key_idx < len(self.items_db) else "a key"
                    out += f'*** You use the {iname} to unlock the door.\n'
                    if active_gate.get('consume', 0):
                        char.invent[found_slot] = -1
                        char.charge[found_slot] = 0
                        from .character import recalc_encumbrance
                        recalc_encumbrance(char, self.items_db)
            
            # If the room exit was 0 or a portal marker, use the gate's destination
            if dest <= 0:
                dest = active_gate.get('to_room', 0)
                if dest > 0:
                    out += '\n*** You feel a strange sensation as you pass through the gateway...\n'
                    skip_redirect = True

        if dest == 0:
            return msg.get('NOEXTN', '', SDIR[direction], 0, 0) if 'NOEXTN' in msg._messages else f'***\nThere is no exit to the {SDIR[direction]}!\n'

        # If dest is the hardcoded dungeon return room and we're coming from dungeon,
        # redirect to where the player actually entered the dungeon from
        if dest == self.world.DUNGEON_TOWN_ENTRANCE and not skip_redirect:
            cur_room = self.world.get_room(char.loc)
            if cur_room and cur_room.is_dungeon:
                dest = char.dungeon_return_room

        # Tele-Arena 5.x parity: Some exits point to trap message IDs (e.g. 1938 for Pit)
        # instead of a room ID. If dest_id is in a trap message range, trigger it.
        # Known trap messages: 1900-2000
        original_dest = dest - 100 # Original 1-based room/msg ID
        if 1900 <= original_dest <= 2000:
            # Trigger trap on current room but using the special link's message
            trap_msg = self._trigger_room_trap(char, room, msg_idx_override=original_dest)
            return out + trap_msg

        dest_room = self.world.get_room(dest)
        if dest_room is None:
            return f'***\nThere is no exit to the {SDIR[direction]}!\n'

        old_loc = char.loc
        char.loc = dest

        # Trigger room traps (trap data loaded from TRIG records in dungeon_data.json)
        trap_msg = self._trigger_room_trap(char, dest_room)
        if trap_msg:
            out += trap_msg

        # Track dungeon entry point for correct return routing
        if dest_room.is_dungeon and not self.world.is_dungeon(old_loc):
            char.dungeon_return_room = old_loc

        # Reduce food/water
        char.food = max(0, char.food - 10)
        char.water = max(0, char.water - 5)

        # Light expires
        if char.light > 0:
            char.light -= 1

        # Trigger random monster encounter in dungeon (but not in arenas)
        if dest_room.is_dungeon and dest not in (2, 28, 47):
            existing = self.monster_mgr.get_room_monsters(dest)
            if not existing and random.random() < 0.3:
                # Determine appropriate terrain and level for area
                # For now, Dungeon 1 (rooms 101-200) uses Terrain 1 (Dungeon)
                target_terr = 1
                depth = (dest - DUNOFF)
                max_lvl = max(1, (depth // 10) + 1)
                
                # Filter candidates from loaded types
                candidates = [tid for tid, mtype in enumerate(self.monster_mgr.types) 
                            if mtype.terr == target_terr and mtype.level <= max_lvl]
                
                if not candidates:
                    # Fallback to Terrain 0 if no Terrain 1 matches (Arena/Common)
                    candidates = [tid for tid, mtype in enumerate(self.monster_mgr.types) 
                                if mtype.terr == 0 and mtype.level <= max_lvl]

                if candidates:
                    type_id = random.choice(candidates)
                    self.monster_mgr.spawn(type_id, dest, level=max_lvl)

        out += self._look_room(brief=True)

        # Hunger/thirst warnings
        if char.food <= 0:
            out += msg.get('YOUHNG') if 'YOUHNG' in msg._messages else '***\nYou\'re hungry.\n'
        if char.water <= 0:
            out += msg.get('YOUTHR') if 'YOUTHR' in msg._messages else '***\nYou\'re thirsty.\n'

        # Poison damage
        if char.poison > 0:
            dmg = random.randint(1, char.poison)
            out += msg.get('POISON') if 'POISON' in msg._messages else '***\nYou\'re poisoned!\n'
            cbt.dmg_char(char, dmg, self)
            if not char.alive:
                out += msg.get('YOUDED') if 'YOUDED' in msg._messages else '***\nThe poison in your veins renders you unconscious.\nYou awaken after an unknown amount of time...\n'
                out += self._look_room()

        return out

    def _cmd_look_at(self, target):
        char = self.char
        target_lower = target.lower()

        # Check for player self-inspect
        if target_lower == char.userid.lower():
            return self._cmd_inspect(char.userid)

        # Check monsters
        for mid in self.monster_mgr.get_room_monsters(char.loc):
            inst = self.monster_mgr.instances[mid]
            if target_lower in inst.type.name.lower():
                mtype = inst.type
                out = f'***\n'
                if mtype.long_desc:
                    out += mtype.long_desc[:400] + '\n'
                else:
                    out += f'{mtype.article.capitalize()} {mtype.name} stands before you.\n'
                out += inst.health_desc() + '\n'
                return out

        # Check townsfolk
        for folk in self.world.get_townsfolk_in_room(char.loc):
            if target_lower in folk['name'].lower():
                return f'***\n{folk["desc"]}\n'

        return f'***\nYou don\'t see {target} here.\n'

    def _cmd_inspect(self, who):
        char = self.char
        c = COMPLEXION_NAMES[char.complexion] if char.complexion < len(COMPLEXION_NAMES) else ''
        e = EYE_COLOR_NAMES[char.eyecolor] if char.eyecolor < len(EYE_COLOR_NAMES) else ''
        hc = HAIR_COLOR_NAMES[char.haircolor] if char.haircolor < len(HAIR_COLOR_NAMES) else ''
        hs = HAIR_STYLE_NAMES[char.hairstyle] if char.hairstyle < len(HAIR_STYLE_NAMES) else ''
        hl = HAIR_LENGTH_NAMES[char.hairlength] if char.hairlength < len(HAIR_LENGTH_NAMES) else ''

        arm_name = (self.items_db[char.armor].get('name', 'nothing')
                    if 0 <= char.armor < len(self.items_db) else 'nothing')
        wep_name = (self.items_db[char.weapon].get('name', 'bare hands')
                    if 0 <= char.weapon < len(self.items_db) else 'bare hands')

        out = f'***\n{char.userid} is a {char.race_name} {char.class_name}.\n'
        out += f'{char.userid} has {c.lower()} complexion, {e.lower()} eyes, and {hl.lower()}, {hs.lower()}, {hc.lower()} hair.\n'
        out += f'{char.userid} is wearing {arm_name}, is armed with {wep_name}.\n'

        pct = char.hp_pct
        if pct <= 0.25:
            out += f'and {char.userid} is sorely wounded.\n'
        elif pct <= 0.50:
            out += f'and {char.userid} seems to be moderately wounded.\n'
        elif pct < 1.0:
            out += f'and {char.userid} appears to be wounded.\n'
        else:
            out += f'and {char.userid} seems to be in good physical condition.\n'
        return out

    def _cmd_attack(self, target):
        char = self.char

        if char.parcnt > 0:
            return '***\nYou\'re paralyzed!\n'

        room = self.world.get_room(char.loc)
        if room is None:
            return '***\nYou can\'t attack here!\n'

        # Find monster
        inst = self.monster_mgr.get_monster_by_name(char.loc, target)
        if inst:
            self.combat_target = inst.id
            msgs = cbt.attack_monster(char, inst, self.items_db, self.world, self)
            out = ''.join(msgs.get('you', []))
            if not inst.alive:
                self.combat_target = None
            return out

        return f'***\nYou don\'t see {target} here.\n'

    def _cmd_get(self, item_name):
        char = self.char
        room = self.world.get_room(char.loc)
        if room is None or not room.is_dungeon:
            return '***\nThere\'s nothing to pick up here.\n'

        name_lower = item_name.lower()
        get_all = name_lower == 'all'
        got = []

        for i in range(NMRMIT):
            itm_idx = room.get_item(i)
            if itm_idx == 255:
                continue
            if itm_idx >= len(self.items_db):
                continue
            item = self.items_db[itm_idx]
            if not get_all and name_lower not in item.get('name', '').lower():
                continue

            # Weight check
            if not check_encumbrance(char, item.get('wt', 0)):
                return '***\nYou can\'t carry any more weight!\n'

            slot = find_empty_slot(char)
            if slot == -1:
                return '***\nYour inventory is full!\n'

            # Light source effect
            if item.get('effect') == EFF_LIGHT:
                char.light = 10

            chg = room.get_item_charge(i)
            char.invent[slot] = itm_idx
            char.charge[slot] = chg
            room.clear_item(i)
            got.append(item.get('desc', item.get('name', 'item')))
            recalc_encumbrance(char, self.items_db)
            if not get_all:
                break

        room.compact_items()

        if not got:
            if get_all:
                return '***\nThere\'s nothing here to take.\n'
            return f'***\nYou don\'t see {item_name} here.\n'

        if len(got) == 1:
            return f'***\nYou take {got[0]}.\n'
        else:
            return f'***\nYou take: {", ".join(got[:-1])}, and {got[-1]}.\n'

    def _cmd_drop(self, item_name):
        char = self.char
        room = self.world.get_room(char.loc)
        if room is None or not room.is_dungeon:
            return '***\nYou can\'t drop items here.\n'
        if char.level < 2:
            return '***\nYou must be at least level 2 to drop items.\n'

        slot = find_item_in_inv(char, item_name, self.items_db)
        if slot == -1:
            return f'***\nYou don\'t have {item_name}.\n'

        item_idx = char.invent[slot]
        item = self.items_db[item_idx]

        # Check room capacity
        drop_slot = room.find_empty_item_slot()
        if drop_slot == -1:
            return '***\nThere\'s no room to drop that here.\n'

        # Handle light source
        if item.get('effect') in (EFF_LIGHT, EFF_LIGHT_USED) and char.light > 0:
            char.light = 0

        # Unequip if equipped
        if char.weapon == item_idx:
            char.weapon = DEFWEP
        if char.armor == item_idx:
            char.armor = DEFARM if DEFARM < len(self.items_db) else 0

        chg = char.charge[slot]
        room.set_item(drop_slot, item_idx, chg)
        char.invent[slot] = -1
        char.charge[slot] = 0
        recalc_encumbrance(char, self.items_db)

        iname = item.get('desc', item.get('name', 'item'))
        return f'***\nYou drop {iname}.\n'

    def _cmd_eat(self, item_name):
        char = self.char
        slot = find_item_in_inv(char, item_name, self.items_db)
        if slot == -1:
            return f'***\nYou don\'t have {item_name}.\n'
        item = self.items_db[char.invent[slot]]
        if item.get('effect') not in (EFF_FOOD, EFF_FOOD_WATER):
            return f'***\nYou can\'t eat {item.get("name", "that")}.\n'
        food_restore = item.get('maxdam', 3600)
        char.food = min(START_FOOD, char.food + food_restore)
        char.invent[slot] = -1
        char.charge[slot] = 0
        recalc_encumbrance(char, self.items_db)
        return f'***\nYou eat {item.get("desc", item.get("name", "it"))} and feel satisfied.\n'

    def _cmd_drink(self, item_name):
        char = self.char
        slot = find_item_in_inv(char, item_name, self.items_db)
        if slot == -1:
            return f'***\nYou don\'t have {item_name}.\n'
        item = self.items_db[char.invent[slot]]
        eff = item.get('effect', 0)
        if eff not in (EFF_WATER_CHARGE, EFF_WATER2, EFF_FOOD_WATER):
            return f'***\nYou can\'t drink {item.get("name", "that")}.\n'
        water_restore = item.get('maxdam', 1800)
        char.water = min(START_WATER, char.water + water_restore)
        # Reduce charges
        if eff == EFF_WATER_CHARGE:
            char.charge[slot] -= 1
            if char.charge[slot] <= 0:
                char.invent[slot] = -1
                char.charge[slot] = 0
        else:
            char.invent[slot] = -1
            char.charge[slot] = 0
        recalc_encumbrance(char, self.items_db)
        return f'***\nYou drink deeply and feel refreshed.\n'

    def _cmd_equip(self, item_name):
        char = self.char
        slot = find_item_in_inv(char, item_name, self.items_db)
        if slot == -1:
            return f'***\nYou don\'t have {item_name}.\n'
        item_idx = char.invent[slot]
        item = self.items_db[item_idx]
        itype = item.get('type', 0)
        iname = item.get('name', 'item')

        # Weapons: type < 11
        if 1 <= itype <= 10:
            old_wep = char.weapon
            char.weapon = item_idx
            # If we had a non-default weapon, move it to the inventory slot we just vacated
            if old_wep != DEFWEP:
                char.invent[slot] = old_wep
            else:
                char.invent[slot] = -1
            char.wepdmg = 0
            return f'***\nYou wield {item.get("desc", iname)}.\n'
        # Armor: type >= 11
        elif itype >= 11:
            old_arm = char.armor
            char.armor = item_idx
            # If we had a non-default armor, move it to the inventory slot we just vacated
            if old_arm != DEFARM:
                char.invent[slot] = old_arm
            else:
                char.invent[slot] = -1
            char.ac = item.get('armor', 0)
            char.armdmg = 0
            return f'***\nYou put on {item.get("desc", iname)}.\n'
        else:
            return f'***\nYou can\'t equip {iname}.\n'

    def _cmd_unequip(self, item_name):
        char = self.char
        name_lower = item_name.lower()

        # Find empty slot
        slot = -1
        for i in range(NUMHLD):
            if char.invent[i] == -1:
                slot = i
                break
        
        if slot == -1:
            return '***\nYour inventory is full! You can\'t unequip anything.\n'

        # Check weapon
        if char.weapon >= 0 and char.weapon < len(self.items_db):
            wep = self.items_db[char.weapon]
            if name_lower in wep.get('name', '').lower() or name_lower in wep.get('desc', '').lower():
                char.invent[slot] = char.weapon
                char.weapon = DEFWEP
                return f'***\nYou put away {wep.get("name", "your weapon")}.\n'

        # Check armor
        if char.armor >= 0 and char.armor < len(self.items_db):
            arm = self.items_db[char.armor]
            if name_lower in arm.get('name', '').lower() or name_lower in arm.get('desc', '').lower():
                char.invent[slot] = char.armor
                char.armor = DEFARM if DEFARM < len(self.items_db) else 0
                char.ac = 0
                return f'***\nYou remove {arm.get("name", "your armor")}.\n'

        return f'***\nYou don\'t have {item_name} equipped.\n'

    def _cmd_use(self, item_name):
        char = self.char
        slot = find_item_in_inv(char, item_name, self.items_db)
        if slot == -1:
            return f'***\nYou don\'t have {item_name}.\n'
        item_idx = char.invent[slot]
        item = self.items_db[item_idx]
        eff = item.get('effect', 0)
        iname = item.get('desc', item.get('name', 'item'))

        if eff == EFF_HEALING:  # healing potion
            heal = random.randint(item.get('mindam', 4), item.get('maxdam', 16))
            char.hits = min(char.mhits, char.hits + heal)
            char.invent[slot] = -1
            char.charge[slot] = 0
            recalc_encumbrance(char, self.items_db)
            return f'***\nYou use {iname} and recover {heal} hit points!\n'

        elif eff == EFF_MANA_RESTORE:
            restore = item.get('maxdam', 0)
            char.splpts = min(char.mspts, char.splpts + restore)
            char.invent[slot] = -1
            char.charge[slot] = 0
            recalc_encumbrance(char, self.items_db)
            return f'***\nYou use {iname} and your magical energy is restored!\n'

        elif eff == EFF_CURE_POISON:
            char.poison = 0
            char.status = STS_NORMAL
            char.invent[slot] = -1
            char.charge[slot] = 0
            recalc_encumbrance(char, self.items_db)
            return f'***\nYou use {iname} and feel the poison leave your body!\n'

        elif eff in (EFF_LIGHT, EFF_LIGHT_USED):
            return self._cmd_light(item_name)

        elif eff == EFF_FULL_RESTORE:
            char.hits = char.mhits
            char.splpts = char.mspts
            char.invent[slot] = -1
            char.charge[slot] = 0
            recalc_encumbrance(char, self.items_db)
            return f'***\nYou use {iname} and feel completely restored!\n'

        return f'***\nYou use {iname}.\n'

    def _cmd_light(self, item_name):
        char = self.char
        slot = find_item_in_inv(char, item_name, self.items_db)
        if slot == -1:
            return f'***\nYou don\'t have {item_name}.\n'
        item = self.items_db[char.invent[slot]]
        eff = item.get('effect', 0)
        if eff not in (EFF_LIGHT, EFF_LIGHT_USED):
            return f'***\nYou can\'t light {item.get("name", "that")}.\n'
        charges = item.get('maxdam', 450)
        char.light = charges
        iname = item.get('desc', item.get('name', 'item'))
        return f'***\nYou light {iname}. It illuminates the area.\n'

    def _cmd_cast(self, spell_name, target_name):
        char = self.char
        if not char.can_cast:
            return f'***\n{char.class_plural} don\'t use spells!\n'
        if char.spldly > 0:
            return '***\nYou are still recovering from your last spell!\n'

        # Find spell in spellbook
        spell_lower = spell_name.lower()
        spell_idx = -1
        for i in range(SPLBOK):
            si = char.splbook[i]
            if si == 255 or si >= len(self.spells_db):
                continue
            if spell_lower in self.spells_db[si]['name'].lower():
                spell_idx = si
                break

        if spell_idx == -1:
            return f'***\nYou don\'t know a spell called "{spell_name}".\n'

        # Find target
        target_char = None
        target_monster = None
        target_lower = target_name.lower()

        if target_lower not in ('all!', 'all', ''):
            inst = self.monster_mgr.get_monster_by_name(char.loc, target_lower)
            if inst:
                target_monster = inst

        msgs = cbt.cast_spell(char, spell_idx, target_char, target_monster,
                               self.items_db, self.world, self)
        return ''.join(msgs.get('you', []))

    def _cmd_purge(self, spell_name):
        ok, out = shops.purge_spell(self.char, spell_name, self.spells_db)
        return out

    def _cmd_buy(self, item_name):
        char = self.char
        room = self.world.get_room(char.loc)
        shop_type = room.shop_type if room else SHOP_NONE
        shop_tier = self.world.get_shop_tier(char.loc)

        if item_name.startswith('spell '):
            return self._cmd_buy_spell(item_name[6:])
        if item_name in ('training', 'train'):
            if shop_type != SHOP_GUILD:
                return '***\nYou must be at a guild hall to buy training.\n'
            cost = (char.level + 1) * 5
            if char.gold < cost:
                return f'***\nYou need {cost} gold to pay for training!\n'
            if char.can_advance():
                char.gold -= cost
                char.advance_level()
                return '***\nAfter a rigorous mental and physical training session, you have achieved a new level!\n'
            else:
                return '***\nYou are not ready for any further training, you must first prove yourself in combat!\n'

        if item_name == 'promotion':
            if shop_type != SHOP_GUILD:
                return '***\nYou must be at a guild hall to buy a promotion.\n'
            cost = 1000
            if char.gold < cost:
                return '***\nYou cannot afford a promotion at this time!\n'
            if char.can_promote():
                char.gold -= cost
                char.promote()
                return f'***\nCongratulations! You have been promoted to the rank of {char.class_name}!\n'
            else:
                return '***\nYou are not ready for a promotion, you must first achieve greater experience!\n'
        if item_name in ('food', 'drink', 'water', 'ale', 'meal'):
            if shop_type in (SHOP_TAVERN, SHOP_INN):
                ok, out = shops.buy_food_drink(char, item_name, self.items_db)
                return out
            return '***\nYou can\'t buy that here.\n'

        if item_name == 'passage':
            # TA Gold: Passage between Room 11 (Port Docks) and Room 12 (North Shore)
            if char.loc in (11, 12):
                if char.loc == 11 and char.badge < 1:
                    return f"***\n{msg.get('NORUNE')}\n"
                    
                cost = 50
                if char.gold < cost:
                    return msg.get('CNTAFD', 'passage')
                
                char.gold -= cost
                char.loc = 12 if char.loc == 11 else 11
                out = f"***\n{msg.get('YOUVOY')}\n\n"
                out += self._look_room()
                return out
            return "***\nThere is no ship here to buy passage on.\n"

        if shop_type == SHOP_TEMPLE:
            ok, out = shops.temple_buy(char, item_name)
            return out

        if not room or getattr(room, 'shop_cat', 0) == 0:
            return '***\nThere\'s no shop here.\n'
        ok, out = shops.buy_item(char, item_name, room.shop_cat, room.shop_tier, self.items_db, self.world)
        return out

    def _cmd_sell(self, item_name):
        char = self.char
        room = self.world.get_room(char.loc)
        if not room or getattr(room, 'shop_cat', 0) == 0:
            return '***\nThere\'s no shop here.\n'
        ok, out = shops.sell_item(char, item_name, room.shop_cat, room.shop_tier, self.items_db, self.world)
        return out

    def _cmd_list(self, what):
        char = self.char
        room = self.world.get_room(char.loc)
        shop_type = room.shop_type if room else SHOP_NONE
        shop_tier = self.world.get_shop_tier(char.loc)

        if what in ('items', 'i'):
            if room and getattr(room, 'shop_cat', 0) > 0:
                return shops.list_shop_items(room.shop_cat, room.shop_tier, self.items_db, char)
            return '***\nThere\'s no shop here.\n'

        if what in ('spells', 'sp'):
            if shop_type == SHOP_GUILD:
                return shops.list_spells(self.spells_db, char)
            return '***\nThere\'s no guild here.\n'

        return '***\nList what?\n'

    def _cmd_buy_spell(self, spell_name):
        char = self.char
        room = self.world.get_room(char.loc)
        if room and room.shop_type != SHOP_GUILD:
            return '***\nYou must be at a guild hall to buy spells.\n'
        ok, out = shops.buy_spell(char, spell_name, self.items_db, self.spells_db)
        return out

    def _cmd_give_gold(self, target, amount):
        return '***\nThere is nobody here to give gold to.\n'

    def _cmd_give_item(self, target, item_name):
        return '***\nThere is nobody here to give items to.\n'

    def _cmd_deposit(self, amount_str):
        char = self.char
        room = self.world.get_room(char.loc)
        if room and room.shop_type != SHOP_VAULT:
            return '***\nYou must be at a vault to deposit gold.\n'
        try:
            amount = int(amount_str)
        except ValueError:
            return '***\nDeposit how much?\n'
        ok, out = shops.bank_deposit(char, amount)
        return out

    def _cmd_withdraw(self, amount_str):
        char = self.char
        room = self.world.get_room(char.loc)
        if room and room.shop_type != SHOP_VAULT:
            return '***\nYou must be at a vault to withdraw gold.\n'
        try:
            amount = int(amount_str)
        except ValueError:
            return '***\nWithdraw how much?\n'
        ok, out = shops.bank_withdraw(char, amount)
        return out

    def _cmd_balance(self):
        char = self.char
        room = self.world.get_room(char.loc)
        if room and room.shop_type != SHOP_VAULT:
            return '***\nYou must be at a vault to check your balance.\n'
        return shops.bank_balance(char)

    def _cmd_donate(self, amount):
        char = self.char
        room = self.world.get_room(char.loc)
        if room and room.shop_type != SHOP_TEMPLE:
            return '***\nYou must be at a temple to donate.\n'
        ok, out = shops.donate_to_temple(char, amount)
        if ok:
            msg_up = cbt.check_level_up(char, self, [])
            if msg_up:
                out += msg_up
        return out

    def _cmd_slots(self):
        char = self.char
        room = self.world.get_room(char.loc)
        if room and room.shop_type != SHOP_TAVERN:
            return '***\nYou must be in the tavern to play slots.\n'
        return shops.play_slots(char)

    def _cmd_dice(self):
        char = self.char
        room = self.world.get_room(char.loc)
        if room and room.shop_type != SHOP_TAVERN:
            return '***\nYou must be in the tavern to play dice.\n'
        return shops.play_dice(char)

    def _cmd_ring_gong(self):
        char = self.char
        
        if char.attdly > 0:
            return msg.get('ATTEXH') if 'ATTEXH' in msg._messages else '***\nYou are still recovering from your last action!\n'
            
        room = self.world.get_room(char.loc)
        if room and room.shop_type == SHOP_ARENA:
            if self.monster_mgr.types:
                char.attdly = 5
                char.cbtcnt += 3
                
                target_terr = 0  # Room 2 (Low Level)
                if char.loc == 28:
                    target_terr = 1  # Room 28 (Mid Level)
                elif char.loc == 47:
                    target_terr = 2  # Room 47 (High Level)
                
                valid_types = [tid for tid, mtype in enumerate(self.monster_mgr.types) if mtype.terr == target_terr]
                if not valid_types:
                    valid_types = list(range(len(self.monster_mgr.types)))

                out = msg.get('RNGGNG', char.userid)
                
                if len(self.monster_mgr.get_room_monsters(char.loc)) >= 4:
                    return out

                tid = random.choice(valid_types)
                inst = self.monster_mgr.spawn(tid, char.loc)
                if inst:
                    inst.prey = 0  # immediately aggro on player
                    inst.attdly = 0  # standard instant aggro
                mtype = self.monster_mgr.types[tid]
                out += msg.get('MONENT', mtype.article.capitalize(), mtype.name)
                return out
        return '***\nNothing happens.\n'

    def _cmd_track(self, target):
        return '***\nYou find no trail.\n'

    # ------------------------------------------------------------------
    # Game tick (periodic updates)
    # ------------------------------------------------------------------

    def _game_tick(self):
        char = self.char
        self.tick += 1

        # Reduce delays
        if char.attdly > 0:
            char.attdly -= 1
        if char.spldly > 0:
            char.spldly -= 1
        if char.parcnt > 0:
            char.parcnt -= 1
        if char.invcnt > 0:
            char.invcnt -= 1
        if char.procnt > 0:
            char.procnt -= 1
        if char.actcnt > 0:
            char.actcnt -= 1
        if char.cbtcnt > 0:
            char.cbtcnt -= 1

        # Stat effect counters
        for i in range(8):
            if char.stacnt[i] > 0:
                char.stacnt[i] -= 1

        # Regeneration (every 5 seconds at 10Hz)
        if self.tick % 50 == 0:
            if char.hits < char.mhits:
                regen = max(1, char.stam // 10)
                char.hits = min(char.mhits, char.hits + regen)
            if char.splpts < char.mspts:
                char.splpts = min(char.mspts, char.splpts + 1)

        # Monster regen (every 10 seconds at 1Hz)
        if self.tick % 10 == 0:
            self.monster_mgr.tick_regen()

        # Auto-save every 100 seconds (100 ticks at 1Hz)
        if self.tick % 100 == 0 and char.userid:
            char.save()

        out = ''
        if char.alive:
            # Auto-attack: fire player's round when attdly expires and target is set
            if char.attdly == 0 and self.combat_target is not None:
                inst = self.monster_mgr.instances.get(self.combat_target)
                if inst and inst.alive and inst.dloc == char.loc:
                    msgs = cbt.attack_monster(char, inst, self.items_db, self.world, self)
                    out += ''.join(msgs.get('you', []))
                    if not inst.alive:
                        self.combat_target = None
                else:
                    self.combat_target = None

            # Monster attacks — every 2.5 seconds per monster, only if aggroed
            for mid in self.monster_mgr.get_room_monsters(char.loc):
                inst = self.monster_mgr.instances.get(mid)
                if not inst or not inst.alive:
                    continue
                if inst.attdly > 0:
                    inst.attdly -= 1
                    continue
                # Only attack if monster is aggroed (prey != 256)
                if inst.prey == 256:
                    continue
                    
                mon_msgs = cbt.monster_attacks(inst, char, self)
                out += ''.join(mon_msgs)
                
                # Reset monster delay: 20 seconds (20 ticks at 1Hz)
                inst.attdly = 20
                
                if not char.alive:
                    self.combat_target = None
                    break

        return out if out else None

    # ------------------------------------------------------------------
    # Public API for UI
    # ------------------------------------------------------------------

    def is_creation_state(self):
        return self.state not in (PLYING, EXTING) and self.state != 0

    def is_playing(self):
        return self.state == PLYING

    def is_exiting(self):
        return self.state == EXTING

    def get_status_segments(self):
        """Return color-coded segments for the status bar: [(text, color_name), ...]"""
        if self.char is None:
            return [('Tele-Arena 5.6  |  Not in game', 'cyan')]
        if not self.is_playing():
            return [(f'Tele-Arena 5.6  |  Character Creation  |  {self.char.userid}', 'cyan')]
        
        char = self.char
        next_xp = char.get_next_level_xp()
        
        # HP color logic: red below 25%
        hp_pct = char.hits / max(1, char.mhits)
        hp_color = "red" if hp_pct < 0.25 else "green"
        
        # Status logic
        status_map = {0: "Normal", 1: "Poisoned", 2: "Paralyzed", 3: "Drained"}
        status_text = status_map.get(char.status, "Unknown")
        status_color = "white" if char.status == 0 else "green" if char.status == 1 else "magenta" if char.status == 2 else "grey"

        segments = [
            (f"RM:{char.loc}", "white"),
        ]
        if char.dun != 0:
            segments.append((f"D:{char.dun}", "white"))
            
        segments += [
            (f" HP:{char.hits}/{char.mhits} ", hp_color),
            (f"MP:{char.splpts}/{char.mspts} ", "cyan"),
            (f"XP:{char.exp}/{next_xp} ", "white"),
            (f"GP:{char.gold} ", "yellow"),
        ]
        
        # Only show status if it's something other than normal
        if char.status != 0:
            segments.append((f"Status:{status_text}", status_color))
            
        return segments
