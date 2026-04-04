#!/usr/bin/env python3
"""
Parse Tele-Arena 5.6 Gold data files (.MSG and some .MCV) into JSON for the Python port.
This version supports the newer .MSG-heavy format found in Tele-Arena 5.6d Gold.
"""

import json
import re
import os

SRC = os.path.join(os.path.dirname(__file__), 'ta_bbs')
OUT = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_null_parts(filename):
    """Read a .MCV file and return list of null-separated non-empty strings."""
    if not os.path.exists(filename):
        return []
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

def parse_msg_file(filename):
    """Parse a Major BBS .MSG file into a dict of {name: text}."""
    if not os.path.exists(filename):
        return {}
    with open(filename, 'r', encoding='latin-1', errors='replace') as f:
        content = f.read()
    
    messages = {}
    # Pattern: NAME {content} T/S/B/N Description
    # Use [\w-] to allow hyphens in keys like DD1-1
    pattern = re.compile(r'^([\w-]+)\s*\{(.*?)\}\s*(?:T|S|B|N|)\b', re.MULTILINE | re.DOTALL)
    for m in pattern.finditer(content):
        name = m.group(1).upper().replace('-', '_')
        text = m.group(2).strip()
        messages[name] = text
    return messages

def parse_ints(s):
    """Parse a space-separated string of integers."""
    if not s: return []
    try:
        s = s.replace(',', ' ')
        return [int(x) for x in s.split()]
    except ValueError:
        return []

def _skip_empty(parts, idx):
    while idx < len(parts) and parts[idx] == '':
        idx += 1
    return idx

# ---------------------------------------------------------------------------
# Items, spells, and monsters (TSGARN-D.MSG)
# ---------------------------------------------------------------------------

def parse_items_gold():
    msg_d = parse_msg_file(os.path.join(SRC, 'TSGARN-D.MSG'))
    num_items = int(msg_d.get('ITEMTOT', '0'))
    items = []
    for i in range(1, num_items + 1):
        name = msg_d.get(f'INAM{i}', f'Item {i}')
        desc = msg_d.get(f'IDES{i}', '')
        stats = parse_ints(msg_d.get(f'ISTT{i}', ''))
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
            'proj_desc': msg_d.get(f'IEFF{i}', ''),
        }
        items.append(item)
    return items

def parse_spells_gold():
    msg_d = parse_msg_file(os.path.join(SRC, 'TSGARN-D.MSG'))
    num_spells = int(msg_d.get('SPLTOT', '0'))
    spells = []
    for i in range(1, num_spells + 1):
        name = msg_d.get(f'SNAM{i}', f'Spell {i}')
        desc = msg_d.get(f'SDES{i}', '')
        stats = parse_ints(msg_d.get(f'SSTT{i}', ''))
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
    return spells

def parse_monsters_gold():
    """Parse monsters from TSGARN-D.MSG using monarr struct field order:
    MSTT fields: prefix, cskl, terr, gp, trs, ac, sach, hd, regen,
                 mindam, maxdam, minspc, maxspc, effect, mineff, maxeff,
                 spcabn, atts, level, morale, sskl, spllst, minspl, maxspl,
                 gender, subtyp
    """
    msg_d = parse_msg_file(os.path.join(SRC, 'TSGARN-D.MSG'))
    num_mobs = int(msg_d.get('MOBTOT', '0'))
    monsters = []
    for i in range(1, num_mobs + 1):
        name = msg_d.get(f'MNAM{i}', f'Monster {i}')
        desc = msg_d.get(f'MDES{i}', '')
        stats = parse_ints(msg_d.get(f'MSTT{i}', ''))
        # monarr struct field mapping (0-indexed):
        # [0]=prefix [1]=cskl [2]=terr [3]=gp [4]=trs [5]=ac [6]=sach
        # [7]=hd [8]=regen [9]=mindam [10]=maxdam [11]=minspc [12]=maxspc
        # [13]=effect [14]=mineff [15]=maxeff [16]=spcabn [17]=atts
        # [18]=level [19]=morale [20]=sskl [21]=spllst [22]=minspl
        # [23]=maxspl [24]=gender [25]=subtyp
        def s(idx, default=0): return stats[idx] if len(stats) > idx else default
        monster = {
            'name': name,
            'desc': desc,
            'plural': msg_d.get(f'MPLU{i}', name + 's'),
            'weapon': msg_d.get(f'MWEP{i}', 'claws'),
            'prefix': s(0),
            'cskl':   s(1),    # combat skill
            'terr':   s(2),    # terrain type (used by chkter() for wandering spawn)
            'gp':     s(3),    # gold dropped
            'trs':    s(4),    # lair treasure
            'ac':     s(5),    # armor class
            'sach':   s(6),    # special attack chance
            'hd':     s(7),    # hit dice
            'regen':  s(8),    # regeneration
            'min_dam':s(9),    # min damage
            'max_dam':s(10),   # max damage
            'minspc': s(11),   # min special damage
            'maxspc': s(12),   # max special damage
            'effect': s(13),   # special effect type
            'mineff': s(14),
            'maxeff': s(15),
            'spcabn': s(16),   # special ability number
            'atts':   s(17),   # attacks per round
            'level':  s(18),   # monster level
            'morale': s(19),
            'sskl':   s(20),   # spell skill
            'spllst': s(21),   # spell list
            'minspl': s(22),
            'maxspl': s(23),
            'gender': s(24),
            'subtyp': s(25),
        }
        monsters.append(monster)
    return monsters

# ---------------------------------------------------------------------------
# Town Rooms (TSGARN-T.MCV)
# ---------------------------------------------------------------------------

def parse_town_rooms_gold():
    msg_t = parse_msg_file(os.path.join(SRC, 'TSGARN-T.MSG'))
    # Room descriptions (Offsets from TSGARN-T.MCV in Part 2 logic)
    parts_t = read_null_parts(os.path.join(SRC, 'TSGARN-T.MCV'))
    
    rooms = []
    for i in range(1, 76):
        # T3 is Names, T4 is Descriptions? (In Gold, often these are binary offsets)
        # We use the offsets identified previously (Part 102 for exits, Part 178 for desc)
        ex_idx = 101 + i
        # Every town room has a 2-part block: [Short Name, Long Description]
        name_idx = 178 + (i - 1) * 2
        ds_idx = 178 + (i - 1) * 2 + 1
        
        exits = parse_ints(parts_t[ex_idx]) if ex_idx < len(parts_t) else [0]*10
        name = parts_t[name_idx] if name_idx < len(parts_t) else f"Town Room {i}"
        desc = parts_t[ds_idx] if ds_idx < len(parts_t) else name
        
        rooms.append({
            'id': i,
            'short_desc': name.strip(),
            'long_desc': desc,
            'exits': exits[:10]
        })
    
    # Townsfolk Definitions
    townsfolk_types = []
    try:
        t2_tot = int(msg_t.get('T2TOT', 0))
        for i in range(1, t2_tot + 1):
            townsfolk_types.append({
                'id': i - 1,
                'name': msg_t.get(f'SNAM{i}', f'Denizen {i}'),
                'plural': msg_t.get(f'SPLU{i}', f'Denizens {i}'),
                'desc': msg_t.get(f'SDES{i}', ''),
                'type': int(msg_t.get(f'SMTY{i}', 0))
            })
    except: pass

    # Townsfolk Instances (Locations)
    townsfolk_instances = []
    try:
        t1_tot = int(msg_t.get('T1TOT', 0))
        for i in range(1, t1_tot + 1):
            raw = msg_t.get(f'T1NO{i}', '')
            vals = parse_ints(raw)
            if len(vals) >= 2:
                type_idx, room_id = vals[0], vals[1]
                if type_idx < len(townsfolk_types):
                    townsfolk_instances.append({
                        'id': i,
                        'type_id': type_idx,
                        'room': room_id,
                        'name': townsfolk_types[type_idx]['name']
                    })
    except: pass

    return rooms, townsfolk_types, townsfolk_instances

# ---------------------------------------------------------------------------
# Dungeon Rooms (TSGARNDD.MSG)
# ---------------------------------------------------------------------------

def parse_dungeon_data_gold():
    msg_dd = parse_msg_file(os.path.join(SRC, 'TSGARNDD.MSG'))
    msg_dt = parse_msg_file(os.path.join(SRC, 'TSGARNDT.MSG')) # Room descriptions
    parts_dd = read_null_parts(os.path.join(SRC, 'TSGARNDD.MCV'))

    total_rooms = 4064
    dungeon_rooms = []
    dungeon_exits = {}
    dungeon_room_descriptions = {}
    
    # In Tele-Arena 5.6 Gold TSGARNDD.MCV:
    # Part 4: num_monster_spawns (DD1TOT)
    # Part 5..N: Monster Spawn Ranges
    # Part 38: num_item_spawns (DD2TOT)
    # Part 39..N: Item Spawn Ranges
    # Part 75..N: Monster Category Lists (DD1_1, DD1_2...)
    # Part 108..N: Item Category Lists (DD2_1, DD2_2...)
    
    # -----------------------------------------------------------------------
    # LAIR entries: Fixed per-room monster placements
    # LAIR{n} = {room_rid, monster_type, count, guardian_flag, unk}
    # Source: SYSCMD.H relair command — BOTH branches spawn lair[i][1]:
    #   if (j==count-1) && guardian_flag > 0:
    #     genmon(room+DUNOFF, lair[i][1], ..., lair_index)  <- tagged as guardian
    #   else:
    #     genmon(room+DUNOFF, lair[i][1], ..., -1)          <- untagged
    # field[3] is NOT a secondary monster — it is a guardian tag flag!
    # -----------------------------------------------------------------------
    fixed_lairs = []
    try:
        lair_tot = int(msg_dd.get('LAIRTOT', 442))
        for i in range(1, lair_tot + 1):
            raw = msg_dd.get(f'LAIR{i}', '')
            vals = parse_ints(raw)
            if len(vals) >= 3:
                room_rid      = vals[0]                              # 1-based RID (no DUNOFF)
                monster_type  = vals[1]                              # 1-indexed (MNAM1..MNAM161)
                count         = max(1, vals[2])                      # number to spawn
                guardian_flag = vals[3] if len(vals) > 3 else 0     # if > 0: last is guardian
                lair_unk      = vals[4] if len(vals) > 4 else 0     # debug value (lair[i][4])
                if monster_type > 0:
                    fixed_lairs.append({
                        'room':    room_rid + 100,    # WorldID = RID + DUNOFF
                        'monster': monster_type,       # 1-indexed; spawn ALL count of this type
                        'count':   count,
                        'guardian_flag': guardian_flag,  # if > 0: last monster is a guardian
                        'unk':     lair_unk
                    })
    except Exception as e:
        print(f"Error parsing LAIR entries: {e}")
    print(f"  Parsed {len(fixed_lairs)} fixed lairs")

    # -----------------------------------------------------------------------
    # DD1 entries: Darkness / zone-type classification ranges
    # DD1-{n} = {start_rid, end_rid, zone_type}
    # zone_type: 0 = normal/lit area, 1 = dark zone
    # -----------------------------------------------------------------------
    dark_zones = []
    try:
        dd1_tot = int(msg_dd.get('DD1TOT', 33))
        for i in range(1, dd1_tot + 1):
            raw = msg_dd.get(f'DD1_{i}', '')
            vals = parse_ints(raw)
            if len(vals) >= 3:
                dark_zones.append({
                    'start': vals[0] + 100,   # WorldID
                    'end':   vals[1] + 100,
                    'zone_type': vals[2]       # 0=normal, 1=dark
                })
    except Exception as e:
        print(f"Error parsing DD1 zones: {e}")

    # -----------------------------------------------------------------------
    # DD2 entries: Terrain / wandering monster zone ranges
    # DD2-{n} = {start_rid, end_rid, terrain_type}
    # terrain_type: 0-9 = terrain class (matches MSTT.terr field on monsters)
    #               99  = no wandering monsters in this zone
    # Source: chkter(ter) returns appropriate monster for current room terrain
    # -----------------------------------------------------------------------
    terrain_zones = []
    try:
        dd2_tot = int(msg_dd.get('DD2TOT', 35))
        for i in range(1, dd2_tot + 1):
            raw = msg_dd.get(f'DD2_{i}', '')
            vals = parse_ints(raw)
            if len(vals) >= 3:
                terrain_zones.append({
                    'start':   vals[0] + 100,   # WorldID
                    'end':     vals[1] + 100,
                    'terrain': vals[2]           # 99 = no wander
                })
    except Exception as e:
        print(f"Error parsing DD2 terrain zones: {e}")

    # Legacy fields (kept for compatibility but not used for primary spawning)
    monster_spawns = []
    item_spawns = []

    for i in range(1, total_rooms + 1):
        # Exits and Description
        raw = msg_dd.get(f'EXIT{i}', '')
        vals = parse_ints(raw)
        desc_idx = 0
        if len(vals) >= 10:
            dungeon_exits[i] = vals[:10]
            if len(vals) >= 11:
                desc_idx = vals[10]
                dungeon_room_descriptions[i] = desc_idx
        
        # Room text from TSGARNDT.MSG
        long_ = msg_dt.get(f'ROOM{desc_idx}', '')
        short = f'Room {i}'
        if long_:
            lines = long_.split('\n')
            if len(lines) > 0:
                short = lines[0].strip()
        
        dungeon_rooms.append({
            'id': i + 100, # DUNOFF = 100
            'short_desc': short,
            'long_desc': long_ if long_ else "You're in a cave.",
            'resident_monster': 0, # Rely on spawns for now
            'resident_item': 0
        })

    # Gates (from MCV)
    parts_dd = read_null_parts(os.path.join(SRC, 'TSGARNDD.MCV'))
    gates = []
    dungeon_attributes = {}
    try:
        dtot_vals = parse_ints(parts_dd[785]) # DOORTOT is at 785
        num_gates = dtot_vals[0] if dtot_vals else 0
        idx = 786 # DOOR1 starts at 786
        hazard_types = {43: 1, 49: 2, 47: 2, 48: 2, 45: 2, 22: 3}
        for _ in range(num_gates):
            vals = parse_ints(parts_dd[idx]); idx += 1
            if len(vals) >= 4:
                g_type = vals[0]
                from_rid = vals[1]
                to_rid = vals[2]
                
                # Determine direction by matching slot in EXIT record
                direction = -1
                if from_rid in dungeon_exits:
                    exits = dungeon_exits[from_rid]
                    if to_rid in exits:
                        direction = exits.index(to_rid)
                
                # Hazard check
                if g_type in hazard_types:
                    h_type = hazard_types[g_type]
                    # MCV hazard format: [type, dest_or_arg, secondary_arg]
                    # vals[3] = primary arg (dest room for pit; message index for others)
                    # vals[4] = secondary arg
                    dungeon_attributes[from_rid] = [h_type, vals[3], vals[4] if len(vals) > 4 else 0]
                
                # Door check
                # 32-49 are typically directional locks/doors/special in Gold
                elif direction != -1:
                    key_map = {
                        1: 39, # Copper
                        2: 38, # Iron
                        3: 41, # Bronze
                        4: 40, # Brass
                        5: 42, # Silver
                        6: 43, # Electrum
                        7: 44, # Gold
                        8: 45, # Platinum
                        9: 46, # Pearl
                        10: 47,# Onyx
                        11: 48,# Jade
                        12: 49 # Ruby
                    }
                    gate = {
                        'type': g_type,
                        'from_room': from_rid,
                        'to_room': to_rid,
                        'arg': vals[3],
                        'msg_idx': vals[4] if len(vals) > 4 else 0,
                        'item_idx': key_map.get(vals[3], 255),
                        'direction': direction,
                        'consume': 1
                    }
                    gates.append(gate)
    except Exception as e:
        print(f"Error parsing gates: {e}")

    # Parse TRIG (trigger/trap) records from TSGARNDD.MSG
    # Format: {room_rid trap_type trap_arg trap_arg2 arg3 arg4 arg5 enabled}
    # trap_type: 1=pit, 2=spike, 3=one-way passage, 4=special/conditional
    # trap_arg:  type1/3: dest_room_rid; type2: XDES/XSTT index (1-10)
    # trap_arg2: secondary data (rogpen override, flags, etc.)
    try:
        trig_tot = int(msg_dd.get('TRIGTOT', 0))
        for i in range(1, trig_tot + 1):
            raw = msg_dd.get(f'TRIG{i}', '')
            vals = parse_ints(raw)
            if len(vals) >= 2:
                room_rid  = vals[0]
                trap_type = vals[1]
                trap_arg  = vals[2] if len(vals) > 2 else 0
                trap_arg2 = vals[3] if len(vals) > 3 else 0
                enabled   = vals[7] if len(vals) > 7 else 1
                if enabled and trap_type > 0 and room_rid > 0:
                    dungeon_attributes[room_rid] = [trap_type, trap_arg, trap_arg2]
        print(f"  Parsed {trig_tot} trap triggers into dungeon_attributes")
    except Exception as e:
        print(f"Error parsing TRIG entries: {e}")

    return {
        'world_name': msg_dd.get('WORLD', 'World One'),
        'num_dun_rooms': total_rooms,
        'fixed_lairs': fixed_lairs,         # Fixed per-room monster placements
        'terrain_zones': terrain_zones,      # DD2: terrain type per RID range (for wanderers)
        'dark_zones': dark_zones,            # DD1: darkness zone ranges
        'monster_spawns': monster_spawns,    # Legacy (unused)
        'item_spawns': item_spawns,          # Legacy (unused)
        'gates': gates,
        'dungeon_exits': dungeon_exits,
        'dungeon_room_descriptions': dungeon_room_descriptions,
        'dungeon_attributes': dungeon_attributes,
        'rooms': dungeon_rooms
    }

# ---------------------------------------------------------------------------
# Shops
# ---------------------------------------------------------------------------

def build_shop_data(town_rooms, townsfolk_instances):
    shops = []
    # Town Tier mapping for Gold (1: Port, 2: Forest, 3: Secret/High)
    # Tier 1: 1-10
    # Tier 2: 11-40
    # Tier 3: 41+
    for room in town_rooms:
        rid = room['id']
        name = room['short_desc'].lower()
        
        shop_cat = 0
        shop_type = 0
        # Categories (1-4): EQUIP=1, WEAPON=2, ARMOR=3, MAGIC=4
        if "武器" in name or "weapon" in name or "smithy" in name: shop_cat, shop_type = 2, 2
        elif "防具" in name or "armor" in name: shop_cat, shop_type = 3, 3
        elif "魔法" in name or "magic" in name or "alchemy" in name: shop_cat, shop_type = 4, 4
        elif "道具" in name or "equipment" in name or "shop" in name: shop_cat, shop_type = 1, 1
        
        # Specialty Shop Types (5-11): GUILD=5, TEMPLE=6, VAULT=7, TAVERN=8, ARENA=9, INN=10, DOCKS=11
        # Check for denizens in this room - Denizen HINTS OVERRIDE general categories
        # PORT TOWN PROTECTION: Rooms 3, 6, 7, 9 are strictly shops in Port Town.
        is_port_shop = rid in (3, 6, 7, 9)
        
        for inst in townsfolk_instances:
            if inst['room'] == rid:
                tid = inst['type_id']
                # Guild Masters (5, 6, 7, 8, 13)
                if tid in (5, 6, 7, 8, 13) and not is_port_shop:
                    shop_type = 5      
                elif tid in (9, 15): 
                    shop_type = 8             # Barkeeps
                elif tid in (10, 11, 14): 
                    # Only set to TAVERN if not already an INN (Tavern/Inn logic is subtle)
                    if shop_type not in (8, 10): shop_type = 8
                elif tid == 12: 
                    shop_type = 11                 # Ship's Captain
                break

        if shop_type:
            tier = 1
            if rid > 40: tier = 3
            elif rid > 10: tier = 2
            
            shops.append({
                'room': rid, 
                'shop_cat': shop_cat, 
                'shop_type': shop_type,
                'shop_tier': tier
            })
            
    return shops

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Parsing Tele-Arena 5.6 Gold data files...")

    items = parse_items_gold()
    spells = parse_spells_gold()
    monsters = parse_monsters_gold()
    print(f"  Found {len(items)} items, {len(spells)} spells, {len(monsters)} monsters")

    town_rooms, townsfolk_types, townsfolk_instances = parse_town_rooms_gold()
    print(f"  Found {len(town_rooms)} town rooms, {len(townsfolk_types)} NPC types")

    dungeon_data = parse_dungeon_data_gold()
    dungeon_rooms = dungeon_data['rooms']
    print(f"  Found {len(dungeon_rooms)} dungeon rooms, {len(dungeon_data['fixed_lairs'])} fixed lairs, {len(dungeon_data['terrain_zones'])} terrain zones")

    print("  Parsing .MSG files for UI/Engine...")
    all_msgs = {}
    for f in ['TSGARN-C.MSG', 'TSGARN-M.MSG', 'TSGARN-D.MSG', 'TSGARN-T.MSG', 'TSGARNDD.MSG', 'TSGARNDT.MSG']:
        all_msgs.update(parse_msg_file(os.path.join(SRC, f)))
    print(f"    Total messages: {len(all_msgs)}")

    # Build shops and save
    shops = build_shop_data(town_rooms, townsfolk_instances)
    with open(os.path.join(OUT, 'shops.json'), 'w') as f:
        json.dump(shops, f, indent=2)

    print("\nWriting JSON data files...")
    with open(os.path.join(OUT, 'items.json'), 'w') as f: json.dump(items, f, indent=2)
    with open(os.path.join(OUT, 'spells.json'), 'w') as f: json.dump(spells, f, indent=2)
    with open(os.path.join(OUT, 'monsters.json'), 'w') as f: json.dump(monsters, f, indent=2)
    with open(os.path.join(OUT, 'town_rooms.json'), 'w') as f: json.dump(town_rooms, f, indent=2)
    with open(os.path.join(OUT, 'townsfolk_types.json'), 'w') as f: json.dump(townsfolk_types, f, indent=2)
    with open(os.path.join(OUT, 'townsfolk_instances.json'), 'w') as f: json.dump(townsfolk_instances, f, indent=2)
    with open(os.path.join(OUT, 'dungeon_rooms.json'), 'w') as f: json.dump(dungeon_rooms, f, indent=2)
    with open(os.path.join(OUT, 'dungeon_data.json'), 'w') as f: json.dump(dungeon_data, f, indent=2)
    with open(os.path.join(OUT, 'messages.json'), 'w') as f: json.dump(all_msgs, f, indent=2)
    with open(os.path.join(OUT, 'shops.json'), 'w') as f: json.dump(shops, f, indent=2)

    print("\nDone! Run 'python3 main.py' to play.")

if __name__ == '__main__':
    main()
