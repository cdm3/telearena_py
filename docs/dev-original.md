# Original Tele-Arena 5.6 Source Reference

This document describes the original Tele-Arena 5.6 C source code for developers porting or extending it. All source files are in `Ta56dSrc/`.

---

## File Overview

| File | Role |
|------|------|
| `TSGARN-0.H` | Global definitions: all structs, externs, and `#define` constants |
| `TSGARN-1.LIB` | Compiled library (binary); contains low-level BBS API calls |
| `TSGARN-2.C` | Main command dispatcher (`arnmnu`), character creation (`genchr`), most player commands |
| `TSGARN-3.C` | Secondary commands: `exits`, `inv`, `buy`, `sell`, `status`, `cast`, `look` |
| `TSGARN-4.C` | Initialization: `initarn`, data loading, world setup |
| `TSGARN-5.C` | Movement (`move`), combat tick, monster AI, death handling |
| `TSGARN-C.DAT` | Config data (BBS-specific settings, not used in port) |
| `TSGARN-C.MSG` | Config message file (some fallback messages) |
| `TSGARN-M.MSG` | Main message file (~600 named messages with ANSI color codes) |
| `TSGARN-D.MCV` | Item, spell, and monster type data |
| `TSGARN-T.MCV` | Town room exits, descriptions, townsfolk types |
| `TSGARNDT.MCV` | Dungeon room descriptions + rumors |
| `TSGARNDD.MCV` | Dungeon room exits, monster spawns, item spawns |

---

## Key `#define` Constants (`TSGARN-0.H`)

```c
#define ARNSUB  100   // Town room BBS-channel offset
                      // Town channels: ARNSUB+1 .. ARNSUB+DUNOFF
#define DUNOFF  100   // Dungeon room offset
                      // Dungeon channels: ARNSUB+DUNOFF+1 .. ARNSUB+DUNOFF+nmdnrm
#define ARNLCH  ARNSUB+1      // Lowest Tele-Arena channel (101)
#define ARNHCH  ARNSUB+DUNOFF // Highest town channel (200)

#define NMRMIT    8   // Max items per room
#define NMRMMN   10   // Max monsters per room
#define NMON   5000   // Max active monster instances
#define MAXRMS 10000  // Max rooms
#define MAXLEV   25   // Max level before promotion
#define NFLK    500   // Max townsfolk instances
#define MAXTRM  100   // Max town rooms
#define MAXSHP   50   // Max shops
#define NUMHLD   12   // Inventory slots per character
#define SPLBOK    8   // Spellbook slots per character
```

**Channel arithmetic:** In the original, a player's BBS channel (`tlchan`) encodes their location:
- Town room N is channel `ARNSUB + N` (e.g. town room 1 = channel 101)
- Dungeon room N is channel `ARNSUB + DUNOFF + N` (e.g. dungeon room 1 = channel 201)

The Python port stores room numbers directly in `char.loc` (1-based) and checks `> DUNOFF` to determine town vs dungeon.

---

## Direction System

Directions are a 10-element array indexed 0–9 in **clockwise compass order**:

```c
char sdir[10][3];   // long names: "N", "NE", "E", "SE", "S", "SW", "W", "NW", "U", "D"
char adir[10][10];  // short names / abbreviations
```

| Index | Direction | Opposite (ent[]) |
|-------|-----------|-----------------|
| 0 | N  | 4 (S)  |
| 1 | NE | 5 (SW) |
| 2 | E  | 6 (W)  |
| 3 | SE | 7 (NW) |
| 4 | S  | 0 (N)  |
| 5 | SW | 1 (NE) |
| 6 | W  | 2 (E)  |
| 7 | NW | 3 (SE) |
| 8 | U  | 9 (D)  |
| 9 | D  | 8 (U)  |

Opposite-direction mapping, from `TSGARN-2.C`:
```c
int ent[] = {4, 5, 6, 7, 0, 1, 2, 3, 9, 8};
```

**Room exit arrays** use the same indexing. `dunroom[0]` = north exit room, `dunroom[4]` = south exit room, etc.

---

## Core Structs (`TSGARN-0.H`)

### `struct arnchr` — In-memory character record
```c
struct arnchr {
    char  race;           // Race index (0–5)
    char  clas;           // Class index (0–7)
    int   level;          // Current level
    long  exp;            // Experience points
    int   badge;          // Badge/rune level
    int   intl, know, phys, stam, agil, chrs;   // Primary stats
    int   mhits, hits;    // Max/current HP
    int   mspts, splpts;  // Max/current spell points
    int   intl2, know2, phys2, stam2, agil2, chrs2; // Modified stats
    int   mspts2, mhits2; // Modified max SP/HP
    int   status;         // 0=normal 1=poisoned 2=paralyzed 3=drained
    int   ac;             // Armor class
    int   weapon, armor;  // Equipped item indices
    int   wepdmg, armdmg; // Item damage modifiers
    int   wt;             // Carried weight
    unsigned gold;        // Gold crowns
    long  accbal;         // Bank balance
    int   atts;           // Attacks per round
    int   attdly, spldly; // Attack/spell delay counters
    int   poison;         // Poison level
    int   dun;            // Dungeon number (0 = town)
    int   loc;            // Room number
    int   light;          // Light source counter
    int   food, water;    // Hunger/thirst counters
    int   attcnt, cbtcnt; // Attack/combat counters
    int   invcnt, procnt; // Invisibility/protection counters
    int   stacnt[8];      // Per-stat effect counters
    int   invent[12];     // Inventory item indices
    char  charge[12];     // Item charges
    char  splbook[8];     // Spellbook spell indices (255=empty)
    char  newchar;        // Has seen intro (0=no, 1=yes)
    char  spccmd;         // Has entered special command
    int   movcnt, actcnt; // Movement/action counters for specials
    int   sound;          // Sound on/off
    int   pulls;          // Slot machine pulls
    int   title;          // Title index
    int   parcnt;         // Paralysis counter
    int   promot;         // Promotion flag
    int   grpnum, grpact, grpfol; // Group fields
    int   complexion, eyecolor, haircolor, hairstyle, hairlength; // Appearance
    int   x, y, z;        // Coordinates
    int   folcnt;         // Follower count
};
```

`struct arnsav` is the on-disk version with identical fields plus `userid[UIDSIZ]` prepended and a spare buffer to pad to 256 bytes.

`struct arnchr2` / `struct arnchr3` hold the 20 trail arrays (`trail0[11]` .. `trail19[11]`).

### `struct arnmon` — Active monster instance
```c
struct arnmon {
    unsigned id     : 8;   // Monster type index
    unsigned level  : 8;   // Monster level
    unsigned active : 1;   // Is alive
    int      hp;           // Current HP
    int      room;         // Room number
    // ... status fields
};
```

### `struct monarr` — Monster type data
```c
struct monarr {
    char name[20];     // Monster name
    int  prefix;       // Article: 0=a, 1=an, 2=the, 3=some
    int  cskl;         // Combat skill (0–100, base 75)
    int  terr;         // Terrain flags
    int  gp;           // Base gold drop
    int  ac;           // Armor class
    int  hd;           // Hit dice
    int  regen;        // Regeneration rate
    int  mindam, maxdam; // Damage range
    int  atts;         // Attacks per round
    int  level;        // Base level
    int  morale;       // Morale (0–100)
    // ... spell/special fields
};
```

### `struct objarr` — Item type data
```c
struct objarr {
    char name[25];     // Item name
    char desc[40];     // Description (floor text)
    int  price;        // Shop price
    int  wt;           // Weight (encumbrance)
    int  range;        // Range type (0=melee, 1-3=ranged)
    int  mindam, maxdam; // Damage range
    int  type;         // Item type (ITM_* constants)
    int  armor;        // Armor class bonus
    int  charges;      // Default charges
    int  effect;       // Effect type (EFF_* constants)
    int  clas;         // Class restriction (0=all)
    int  grpsiz;       // Group size modifier
    int  room;         // Room restriction
    int  rune;         // Rune requirement
    int  poison;       // Poison flag
    int  level;        // Level requirement
    int  shop;         // Shop type (1–5)
};
```

---

## Data File Formats

### `.MSG` files (`TSGARN-M.MSG`, `TSGARN-C.MSG`)

Text files with named message blocks:
```
MSGKEY {message text with \x1b ANSI codes and %s/%d format specifiers} T Description
```
- `T` = type (T/S/B/N — display type, not important for port)
- Multi-line content is inside `{}` braces
- ANSI codes may appear as bare `[1;32m` (no `\x1b` prefix) or full `\x1b[1;32m`

### `.MCV` files (null-separated record format)

All `.MCV` files are binary files where records are separated by null bytes (`\x00`). The layout for each file:

```
parts[0] = "English/ANSI"    (encoding tag)
parts[1] = ""                 (empty)
parts[2] = <count>            (first record count)
parts[3..] = records...
```

Each record may be: a string (name/description), a number string, or a space-separated list of integers.

#### `TSGARN-D.MCV` layout
1. Item count → N item records (name, desc, stats-string)
2. Spell count → N spell records (name, desc, stats-string)
3. Monster count → N monster records (name, long_desc, stats-string, plural, weapon, spcatt, spcabd)

#### `TSGARN-T.MCV` layout
1. Shop entry count → N shop entries (space-separated ints, redundant)
2. Townsfolk count → N townsfolk records (prefix, name, plural, desc)
3. Town room count → N exit rows (10 space-separated room numbers)
4. Room desc count → N room description pairs (short_desc, long_desc)

#### `TSGARNDT.MCV` layout
1. Rumor count → N rumor strings
2. Room desc count → N dungeon room description pairs (short_desc, long_desc)

#### `TSGARNDD.MCV` layout
1. World name string (e.g. `"World One"`)
2. World count (`"1"`)
3. Item range count → N item range rows (3 ints each)
4. Terrain range count → N terrain range rows
5. Monster spawn count → N spawn rows (room, monster_type, count, variant, difficulty)
6. Item spawn count → N item spawn rows (room, item_type, count, variant)
7. Special item count → N special item entries (skipped)
8. Dungeon room count (3096) → N exit rows (11 space-separated ints: N NE E SE S SW W NW U D desc_idx)

Exit values in the dungeon exit rows are 1-based dungeon-local room numbers. Special values:
- `0` = no exit
- `-98` = return to town docks (room 12)

---

## Key Algorithms

### Character Generation (`genchr`, `TSGARN-2.C`)

```c
// Base stat roll: LOSTAT=5 .. HISTAT=15
for each stat: base = arnrnd(LOSTAT, HISTAT);

// Apply race + class modifiers
val = base + trac[race].stat + tcla[class].stat;
// No explicit cap in original; stats can theoretically exceed 30 with high race+class mods

// HP generation (lines ~2500)
mhits = arnrnd(DEFHPL, DEFHPH) + (stam / 5) + tcla[class].hits;
// DEFHPL=10, DEFHPH=20

// SP generation
mspts = DEFSPT + tcla[class].spts;
if (class == CLS_SORCEROR || class == CLS_NECROLYTE) mspts++;
// DEFSPT=1

// Attacks
atts = agil / 15 + 1;

// Gold
gold = arnrnd(3, 25) + trac[race].gold + tcla[class].gold;
```

### Movement (`move`, `TSGARN-5.C`)

```c
move(int dir, char *who) {
    chn = getchn(usrnum) - ARNSUB;  // current channel offset

    if (chn <= DUNOFF) {            // town room
        dest = achn[chn][dir-1];    // achn is the town exit array [room][direction]
        // Note: dir is 1-based here; array is 0-based
        if (dest) {
            newchn = dest + ARNSUB; // move to new channel
        }
    } else {                        // dungeon room
        dest = getroom(chn - DUNOFF, dir-1);
        // getroom loads dunroom[] for room (chn-DUNOFF) and returns dunroom[dir-1]
    }
}
```

Note: `move()` is called with `dir = d+1` (1-based) from the command dispatcher. The array access uses `dir-1` to convert back to 0-based.

### Combat (`TSGARN-5.C`)

Hit determination:
```c
roll = arnrnd(1, 100);
hit_threshold = (attacker_cskl - defender_ac + defender_cskl/2);
if (roll <= hit_threshold) { /* hit */ }
```

Damage:
```c
damage = arnrnd(weapon.mindam, weapon.maxdam) + phys_bonus;
// phys_bonus = phys/5 for melee
```

Monster morale check (flee):
```c
if (monster.hp < monster.max_hp / 4) {
    if (arnrnd(1,100) > monster.morale) { /* flees */ }
}
```

### `getroom` / `setroom`

```c
// setroom(n) loads dungeon room n's exit data into dunroom[]
// getroom(n, dir) = setroom(n), return dunroom[dir]
// dunroom[0..9] = exits in direction-index order
// dunroom[10] = description index
```

---

## Message Key Reference

Frequently used MSG keys and their ANSI colors:

| Key | Color | Usage |
|-----|-------|-------|
| `NOTING` | `\x1b[1;36m` cyan | "There is nothing on the floor." |
| `BYSELF` | `\x1b[1;35m` magenta | "There is nobody here." |
| `ONEOTH` | `\x1b[1;35m` magenta | "%s is here." (townsfolk/player) |
| `SOMMN3` | (no prefix) | "%s %s here.\n" (monster presence) |
| `SOMMN4` | (no prefix) | "and %s %s here.\n" (additional monsters) |
| `SOMTNG` | `\x1b[1;36m` cyan | "There is" (floor item prefix) |
| `ONFLOR` | (reset to white) | " lying on the floor." (floor item suffix) |
| `MONGRN` | `\x1b[1;32m` green | Bright green prefix for monsters |
| `MONRED` | `\x1b[1;31m` red | Bright red prefix for monster damage |
| `MONDEF` | `\x1b[1;33m` yellow | "The %s falls to the ground lifeless!" |
| `MONENT` | `\x1b[1;32m` green | Monster enters arena message |
| `NOEXIT` | `\x1b[1;35m` magenta | "Sorry, there's no exit in that direction." |
| `ATTHIT` | `\x1b[1;35m` magenta | "Your attack hit %s for %d damage!" |
| `ATTHTM` | `\x1b[1;35m` magenta | "Your attack hit the %s for %d damage!" |
| `ATTFUM` | `\x1b[1;35m` magenta | "Your attack missed!" |
| `ATTDOG` | `\x1b[1;35m` magenta | "%s dodged your attack!" |
| `ARNINT1` | (plain) | First intro screen text |
| `ENTRTA` | `\x1b[1;37m` white | "Entering Tele-Arena..." |
| `EXITTA` | `\x1b[1;37m` white | "Exiting Tele-Arena..." |

---

## BBS Infrastructure Not Ported

These original systems are not present in the Python port:

| Original | Description | Python equivalent |
|----------|-------------|------------------|
| `prfmlt(KEY, args...)` | Format message to current user's buffer | `msg.get(KEY, *args)` return value |
| `outmlt(usrnum)` | Flush buffer to user's terminal | Engine method returns string to UI |
| `outchn(chn, exclude, flag)` | Broadcast to everyone in a channel | Not implemented (single-player) |
| `getchn(usrnum)` | Get user's current BBS channel | `char.loc` (direct room number) |
| `setarn()` | Set `usaptr`/`chrptr` to current user | `self.char` in engine |
| `arnarr[usrnum]` | Current user's character data | `self.char` |
| `tlslst[usrnum]` | Tele-shell (session) data | Not needed |
| `arnrnd(lo, hi)` | Random int in range [lo, hi] inclusive | `random.randint(lo, hi)` |
| `sameas(a, b)` | Case-insensitive string compare | `a.lower() == b.lower()` |
