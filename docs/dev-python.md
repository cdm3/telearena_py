# Python Port — Developer Guide

This document describes the architecture of the Tele-Arena 5.6 Python port for developers contributing to or extending it.

---

## Overview

The port is a local single-player curses application. It preserves the original game's data files, room layouts, message text, and gameplay formulae. The BBS multi-user infrastructure (channels, `prfmlt`/`outmlt`, `tlslst`) is replaced with a single `GameEngine` instance and a `CursesUI` front-end.

---

## Module Map

```
main.py
 └─ GameEngine (game/engine.py)
     ├─ Character (game/character.py)
     ├─ World (game/world.py)
     │   └─ Room
     ├─ MonsterManager (game/monsters.py)
     ├─ ShopManager (game/shops.py)
     ├─ game/combat.py  (stateless functions)
     └─ game/messages.py (module-level msg store)
 └─ CursesUI (game/ui/curses_ui.py)
     └─ ScrollBuffer
```

---

## Entry Point: `main.py`

```
python3 main.py [--user USER] [--sex m|f] [--data-dir PATH]
```

`curses.wrapper(main, args)` initialises curses and calls `main(stdscr, args)` which:
1. Creates a `GameEngine` and calls `engine.load_data()`
2. Creates a `CursesUI(stdscr, engine)`
3. Calls `engine.enter_game(userid, sex)` to load or start character creation
4. Calls `ui.run()` — blocks until the game exits

---

## `game/constants.py`

Central definition file translated directly from `TSGARN-0.H`. Key groups:

### Game substates
| Constant | Value | Meaning |
|----------|-------|---------|
| `PLYING` | 1 | Normal play |
| `EXTING` | 2 | Exiting |
| `STTOFF` | 200 | Base offset for creation substates |
| `STATE_INTRO1..STATE_RESURRECT` | 201–211 | Character creation steps |

### Room numbering
| Constant | Value | Meaning |
|----------|-------|---------|
| `ARNSUB` | 100 | Town room BBS-channel offset (reference only) |
| `DUNOFF` | 100 | Dungeon room offset — rooms 1–100 are town, 101+ are dungeon |

### Direction system
**Critical:** Directions use the original game's **clockwise compass order**, confirmed from the source's `ent[]={4,5,6,7,0,1,2,3,9,8}` opposite-direction table.

| Index | Constant | Direction | Opposite |
|-------|----------|-----------|---------|
| 0 | `DIR_N` | North | South (4) |
| 1 | `DIR_NE` | Northeast | Southwest (5) |
| 2 | `DIR_E` | East | West (6) |
| 3 | `DIR_SE` | Southeast | Northwest (7) |
| 4 | `DIR_S` | South | North (0) |
| 5 | `DIR_SW` | Southwest | Northeast (1) |
| 6 | `DIR_W` | West | East (2) |
| 7 | `DIR_NW` | Northwest | Southeast (3) |
| 8 | `DIR_U` | Up | Down (9) |
| 9 | `DIR_D` | Down | Up (8) |

`SDIR[d]` = long name (`'north'`), `ADIR[d]` = abbreviation (`'n'`), `ODIR[d]` = opposite index.

### Race/class modifiers (`RACE_DATA`, `CLASS_DATA`)
Both are lists of dicts indexed by race/class integer. All stat fields (`intl`, `know`, `phys`, `stam`, `agil`, `chrs`) are **modifiers** added to the random base roll (5–15). Values derived from `tele-arena.tumblr.com/maxstats`:
- `race_mod = warrior_max_stat - 15 - warrior_class_mod`
- `class_mod = human_max_stat - 15`

`CLASS_DATA` also includes `hits` (HP bonus at generation), `spts` (SP bonus), and `gold` (starting gold bonus).

---

## `game/character.py`

### `Character` class
Direct Python equivalent of the original `struct arnchr` + `struct arnchr2/3` (trail data). Field names match the C struct exactly (e.g. `intl`, `know`, `phys`, `stam`, `agil`, `chrs`, `mhits`, `mspts`, `splpts`, `loc`, `dun`).

**Primary vs secondary stats:** Stats have `intl`/`intl2` pairs. The `*2` versions are the current effective values (modified by spells/items); base values are permanent. Combat and formulae use `phys2`, `agil2`, etc.

**Persistence:** `char.save()` writes to `saves/<userid>.json`. `Character.load(userid)` returns a `Character` or `None`. The format is a flat JSON dict of all fields.

### `generate_character(char, numitm)`
Equivalent to `genchr()` in `TSGARN-2.C`. Called during character creation after race/class are chosen.

| Formula | Source |
|---------|--------|
| Base stats | `random.randint(5, 15)` per stat |
| Stat total | `base + race_mod + class_mod`, floored at 5, no upper cap |
| Max HP | `random.randint(10, 20) + stam // 5 + class_data['hits']` |
| Max SP | `1 + class_data['spts']` (+1 for Sorceror/Necrolyte) |
| Attacks/turn | `agil // 15 + 1` |
| Starting gold | `random.randint(3, 25) + race_gold + class_gold` |

---

## `game/engine.py`

### `GameEngine` class
The main state machine. Holds references to `char`, `world`, `monster_mgr`, `shop_mgr`, and all loaded data.

**State machine:** `self.state` drives both creation flow and gameplay. Creation advances through `STATE_INTRO1` → `STATE_INTRO3` → `STATE_RACE` → `STATE_COMPLEXION` → ... → `STATE_CLASS` (STTOFF+10), at which point `generate_character()` is called and the character is saved.

**Command dispatch (`process_input(cmd)`):**
1. Strip/split input
2. Check creation substates — return prompt or advance state
3. If `PLYING`, dispatch to `_cmd_*` methods
4. Return string output (ANSI-coded) to be displayed by the UI

**Key methods:**
| Method | Original equiv. | Description |
|--------|----------------|-------------|
| `load_data()` | `initarn()` | Load all JSON data files |
| `enter_game(userid, sex)` | `arnlog()` | Load/create character, return intro text |
| `process_input(cmd)` | `arnmnu()` | Parse and dispatch one command |
| `_look_room()` | `look()` | Build room description string |
| `_cmd_move(direction)` | `move()` | Move player to adjacent room |
| `_cmd_exits()` | `exits()` | List exits (with debug room numbers) |
| `_cmd_status()` | `status()` | Character sheet |
| `_cmd_attack(target)` | `attack()` | Initiate combat |
| `get_status_line()` | — | One-line status bar for the UI |

**Output format:** All engine methods return plain strings. Strings may contain ANSI escape codes (`\x1b[1;32m` etc.) parsed by the UI. Lines starting with `***\n` cause the UI to insert a blank-line separator before the content.

**Room description colors:**
| Element | ANSI code | Color |
|---------|-----------|-------|
| Long/short desc | `\x1b[1;37m` | Bright white |
| Exits line | `\x1b[1;36m` | Bright cyan |
| Floor items | `\x1b[1;36m` (SOMTNG/ONFLOR/NOTING MSG keys) | Bright cyan |
| Nobody here | `\x1b[1;35m` (BYSELF) | Bright magenta |
| Townsfolk | `\x1b[1;35m` (ONEOTH) | Bright magenta |
| Monsters | `\x1b[1;32m` (MONGRN + SOMMN3) | Bright green |
| Monster death | `\x1b[1;33m` (MONDEF) | Bright yellow |
| Damage to player | `\x1b[1;31m` (MONRED) | Bright red |

---

## `game/world.py`

### `Room` class
Holds one room's state. Key fields:
- `id` — room number (1..N)
- `exits[10]` — destination room IDs, indexed by direction constant (0=no exit)
- `shop_type` — `SHOP_*` constant from `constants.py`
- `is_dungeon` — `True` for rooms > `DUNOFF`
- `items[16]` — slots 0–7: item indices (255=empty); slots 8–15: charges
- `monsters[10]` — active monster instance IDs (-1=empty)

### `World` class
Owns `self.rooms: dict[int, Room]`. Loads town rooms from `data/town_rooms.json` and dungeon rooms from `data/dungeon_data.json`.

**Room numbering:**
- Town rooms: `1 .. DUNOFF` (1–100, actual count ~75)
- Dungeon rooms: `DUNOFF+1 .. DUNOFF+3096` (101–3196)
- Dungeon entrance: town room 11 (docks, north exit) → dungeon room 101 (down exit)

**Loading flow:**
1. `_load_town_data()` — creates `Room` objects from town JSON; assigns `shop_type` from `shops.json`
2. `_load_dungeon_data()` — creates dungeon `Room` objects; exit values from JSON are raw dungeon-local numbers (1-based), stored as `DUNOFF + val`. Exit value `-98` means "return to town docks (room 12)".
3. Bidirectional entrance link: room 11 `DIR_D` → room `DUNOFF+1`; room `DUNOFF+1` `DIR_U` → room 11.

---

## `game/messages.py`

Loads `data/messages.json` (parsed from the original `.MSG` files) into a module-level `_messages` dict.

**`msg.get(key, *args)`** — returns the message string for `key`, formatted with C-style `%s`/`%d` substitutions using `*args`. Returns `'[KEY]'` if key not found.

**`parse_ansi_segments(text)`** — parses a string containing ANSI escape codes and returns `[(color_name, bold, text), ...]` 3-tuples. `color_name` is a string like `'cyan'`, `'magenta'`, `'white'`, etc. Used by `ScrollBuffer.add_text()`.

**`strip_ansi(text)`** — removes all ANSI codes, returns plain text.

The MSG files use bare `[1;32m` codes (no `\x1b` prefix). The parser normalises these before splitting.

---

## `game/monsters.py`

### `MonsterType`
Loaded from `data/monsters.json`. Corresponds to `struct monarr`. Key fields: `name`, `plural`, `article` (derived from `prefix` field: 0=a, 1=an, 2=the, 3=some), `hd` (hit dice), `mindam`/`maxdam`, `cskl` (combat skill %), `morale`, `terr` (terrain flags), `level`.

### `MonsterInstance`
A live monster in the world. Has `type`, `room`, `hp`, `max_hp`, `level`, `status`. `health_desc()` returns a color-coded health string.

### `MonsterManager`
Owns `self.instances: dict[int, MonsterInstance]` keyed by unique ID. Key methods:
- `spawn(type_id, room_id, level)` — create a new instance
- `get_room_monsters(room_id)` — list of instance IDs in a room
- `remove(mid)` — despawn instance

---

## `game/combat.py`

Stateless functions called by the engine. Key functions:

| Function | Original | Description |
|----------|----------|-------------|
| `attack_monster(char, inst, items_db, world, engine)` | `attack()` | One full attack round: player vs. monster |
| `monster_attack(inst, char, engine)` | combat loop | Monster attacks back |
| `char_death(char, engine)` | `dthchr()` | Handle player death (respawn, gold loss) |
| `dmg_char(char, amount, engine)` | `dmgchr()` | Apply damage to character |

Returns a dict `{'you': [lines], 'room': [lines]}` where `'you'` goes to the player and `'room'` would go to other players (currently unused in single-player mode).

---

## `game/shops.py`

### `ShopManager`
Handles `BUY`, `SELL`, `LIST ITEMS`, `LIST SPELLS` commands. Loaded from `data/shops.json` which maps room IDs to shop types. Shop inventory is determined by matching items' `shop` field to the shop type.

---

## `game/ui/curses_ui.py`

### `CursesUI`
Owns the curses screen. Layout:
- Rows `0 .. output_rows-1` — scrolling output (`ScrollBuffer`)
- Row `max_y - 2` — status bar (bright cyan on black)
- Row `max_y - 1` — input line

**Input handling (`_handle_key`):**
- Enter always calls `_process_command(cmd)` even for empty input (needed for creation state advancement)
- Up/Down arrows navigate `input_hist`
- Command echo is written in green (`\x1b[1;32m`) before calling the engine

**`ScrollBuffer`:**
- Stores lines as `[(color_name, bold, text)]` 3-tuples (not curses attrs — resolved at render time to avoid calling `curses.color_pair()` before `initscr()`)
- `add_text(text)` strips `***\n` separators, splits on newlines, calls `parse_ansi_segments()` per line
- `get_display_lines(width, count)` word-wraps and returns the last `count` lines as `[(curses_attr, text)]` pairs

**Color pairs** (defined in `init_colors()`):

| Pair | Foreground | Bold | Usage |
|------|-----------|------|-------|
| CP_DEFAULT (1) | white | no | default text |
| CP_STATUS (2) | black on cyan | yes | status bar |
| CP_INPUT (3) | white | no | input line |
| CP_GREEN (4) | green | yes | command echo, monsters |
| CP_CYAN (5) | cyan | yes | exits, floor items |
| CP_MAGENTA (6) | magenta | yes | nobody here, townsfolk |
| CP_RED (7) | red | yes | damage |
| CP_YELLOW (8) | yellow | yes | monster death |

---

## Data Files (`data/`)

All generated by `python3 parse_data.py` from `Ta56dSrc/`.

| File | Source | Contents |
|------|--------|----------|
| `items.json` | `TSGARN-D.MCV` | Array of item dicts (name, desc, stats) |
| `spells.json` | `TSGARN-D.MCV` | Array of spell dicts |
| `monsters.json` | `TSGARN-D.MCV` | Array of monster type dicts |
| `town_rooms.json` | `TSGARN-T.MCV` | Array of town room dicts with exits[10] |
| `dungeon_rooms.json` | `TSGARNDT.MCV` | Array of dungeon room description dicts (862 entries) |
| `dungeon_data.json` | `TSGARNDD.MCV` | Dungeon exits (3096 rooms), monster/item spawns |
| `messages.json` | `TSGARN-M.MSG` + `TSGARN-C.MSG` | Dict of message key → ANSI text |
| `shops.json` | Derived | Array of `{room, type}` shop location dicts |
| `townsfolk_types.json` | `TSGARN-T.MCV` | Array of townsfolk type dicts |
| `rumors.json` | `TSGARNDT.MCV` | Array of rumor strings |
| `monster_weapons.json` | Hardcoded | Monster weapon type dicts |

---

## Adding a New Command

1. In `engine.py`, add a new `_cmd_foo()` method that returns a string
2. In `process_input()`, add a dispatch case (e.g. `if cmd == 'foo': return self._cmd_foo()`)
3. Add it to the `_cmd_help()` output

---

## Save File Format

`saves/<userid>.json` is a flat JSON object with every field from `Character.to_dict()`. Missing fields on load fall back to `Character.__init__()` defaults (handled by `from_dict` using `setattr`).

---

## Known Limitations / TODO

- **Multi-player:** Not implemented. The original BBS channel system (`tlchan`, `arnarr[usrnum]`) has no equivalent here.
- **Traps:** Parsed from source but not yet active in rooms.
- **Treasure:** Spawn data is loaded but drop-on-death not fully wired.
- **Ranged combat / spells:** Partially implemented; spell list display works, casting needs completion.
- **Status bar ANSI leakage:** `get_status_line()` uses `room.short_desc` directly; ANSI codes in descriptions would show as literal text — strip with `msg.strip_ansi()` if needed.
