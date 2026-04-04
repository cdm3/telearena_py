"""
Tele-Arena 5.6 Python Port - Combat System
Translates attack(), attmon(), dmgchr(), dmgmon(), death(), cast()
"""

import random
from .constants import *
from . import messages as msg


def arnrnd(lo, hi):
    """Random integer in [lo, hi] inclusive."""
    return random.randint(lo, hi)


def calc_hit_chance(attacker_char, defender_ac, weapon_type=1, dark=False,
                    invisible_defender=False, ranged=False, class_id=None):
    """
    Calculate attacker's chance to hit (as percentage, 0-99).
    Equivalent to the `as` calculation in attack().
    """
    know = attacker_char.know
    agil = attacker_char.agil
    level = attacker_char.level

    as_ = know + (agil * 2) + (level * 3)
    as_ = max(30, min(99, as_))

    # Dark penalty (non-darkvision races)
    if dark and attacker_char.race not in (RACE_DWARVEN, RACE_GNOMISH, RACE_GOBLIN):
        as_ -= 25

    # Invisible target
    if invisible_defender:
        as_ -= 25

    # Ranged weapon penalty for non-archers
    if ranged and (class_id is not None) and class_id != CLS_ARCHER:
        as_ -= 20
    elif not ranged and (class_id is not None) and class_id == CLS_ARCHER:
        as_ -= ranged * 5 if ranged else 0

    return max(5, as_)


def calc_dodge_chance(defender_char, multiplier=1):
    """
    Calculate defender's chance to dodge (dch).
    """
    dch = (defender_char.know + (defender_char.agil * 2) + defender_char.level) // 10
    if defender_char.clas == CLS_ROGUE:
        dch *= multiplier
    return max(0, min(50, dch))


def calc_damage(attacker_char, item, weapon_skill_bonus=0):
    """
    Calculate attack damage.
    """
    mindam = item.get('mindam', 1)
    maxdam = item.get('maxdam', 4)
    dmg = arnrnd(mindam, max(mindam, maxdam))
    # Physique bonus
    phys_bonus = attacker_char.phys // 5
    dmg += phys_bonus
    dmg += weapon_skill_bonus
    return max(1, dmg)


def attack_character(attacker, defender, items_db, world, game, weapon_idx=-1):
    """
    attacker attacks defender (both are Character objects).
    Returns list of message strings to display to various parties.
    """
    messages = {'you': [], 'target': [], 'room': []}

    if attacker.attdly > 0:
        messages['you'].append('***\nYou are still recovering from your last attack!\n')
        return messages

    # Weapon
    wep_idx = weapon_idx if weapon_idx >= 0 else attacker.weapon
    if wep_idx >= len(items_db):
        wep_idx = DEFWEP
    wep = items_db[wep_idx] if wep_idx < len(items_db) else {'name': 'bare hands', 'mindam': 1, 'maxdam': 3, 'type': 1, 'range': 0}
    wep_name = wep.get('name', 'bare hands')

    room_id = attacker.loc
    room = world.get_room(room_id)
    dark = room.is_dungeon and not room.is_lit() if room else False

    hit_chance = calc_hit_chance(attacker, defender.ac, wep.get('type', 1),
                                  dark, bool(defender.invcnt), bool(wep.get('range', 0)),
                                  attacker.clas)

    # Combat delay (15 seconds at 1Hz)
    attacker.attcnt += 1
    if attacker.attcnt >= attacker.atts:
        attacker.attdly = 15
        attacker.attcnt = 0
        attacker.cbtcnt = 0

    roll = arnrnd(1, 100)
    if roll <= hit_chance:
        # Check dodge
        dodge = calc_dodge_chance(defender, attacker.level)
        dodge_roll = arnrnd(1, 100)

        if dodge_roll <= dodge:
            # Dodge
            messages['you'].append(f'***\n{defender.userid} dodged your attack!\n')
            messages['target'].append(f'***\nYou skillfully dodge {attacker.userid}\'s attack!\n')
            messages['room'].append(f'***\n{defender.userid} barely dodged {attacker.userid}\'s {wep_name}!\n')
        else:
            # Hit!
            dmg = calc_damage(attacker, wep)
            
            # Armor reduction (C-style)
            def_ac = defender.ac
            if def_ac > 0:
                armor_red = arnrnd(def_ac // 2, def_ac)
                dmg -= armor_red
                
            if dmg > 0:
                # Skill hit (Rogue crit chance)
                skillhit = False
                if attacker.clas == CLS_ROGUE and arnrnd(1, 100) <= attacker.level:
                    dmg *= 2
                    skillhit = True
                
                if skillhit:
                    hit_msg_you = f'***\nYour skillful attack hit {defender.userid} for {dmg} damage!\n'
                else:
                    hit_msg_you = f'***\nYour attack hit {defender.userid} for {dmg} damage!\n'

                messages['you'].append(hit_msg_you)
                messages['target'].append(f'***\n{attacker.userid} attacked you with {wep_name} for {dmg} damage!\n')
                messages['room'].append(f'***\n{attacker.userid} just attacked {defender.userid} with {wep_name}!\n')

                # Apply damage
                death_msg = dmg_char(defender, dmg, game, death_type=4)

                if death_msg:
                    messages['you'].append(f'***\nCongratulations, you\'ve defeated {defender.userid}!\n')
                    messages['target'].append(death_msg)
                    messages['room'].append(f'***\n{defender.userid} just fell to the ground lifeless!\n')
            else:
                # Glanced off
                messages['you'].append(f'***\nYour attack glanced off {defender.userid}\'s armor!\n')
                messages['target'].append(f'***\n{attacker.userid}\'s {wep_name} glanced off your armor!\n')
    else:
        # Miss
        messages['you'].append('***\nYour attack missed!\n')
        messages['target'].append(f'***\n{attacker.userid}\'s poorly executed attack misses you!\n')

    return messages


def attack_monster(attacker, monster, items_db, world, game, weapon_idx=-1):
    """
    attacker (Character) attacks a MonsterInstance.
    Returns dict of messages.
    """
    msgs = {'you': [], 'room': []}

    if attacker.attdly > 0:
        msgs['you'].append('***\nYou are still recovering from your last attack!\n')
        return msgs

    # Weapon
    wep_idx = weapon_idx if weapon_idx >= 0 else attacker.weapon
    if wep_idx < 0 or wep_idx >= len(items_db):
        wep_idx = 0
    wep = items_db[wep_idx] if wep_idx < len(items_db) else {'name': 'bare hands', 'mindam': 1, 'maxdam': 3, 'type': 1}
    wep_name = wep.get('name', 'bare hands')

    mtype = monster.type
    mon_name = mtype.name
    article = mtype.article

    room = world.get_room(attacker.loc)
    dark = room.is_dungeon and not room.is_lit() if room else False

    hit_chance = calc_hit_chance(attacker, mtype.ac, wep.get('type', 1),
                                  dark, False, bool(wep.get('range', 0)),
                                  attacker.clas)

    # Fire all attacks for the round at once
    num_attacks = max(1, attacker.atts)
    for _ in range(num_attacks):
        if not monster.alive:
            break

        roll = arnrnd(1, 100)
        if roll <= hit_chance:
            # Check monster dodge (based on agility/cskl)
            mon_dodge = (mtype.cskl + (monster.level * 2)) // 10
            if arnrnd(1, 100) <= mon_dodge:
                msgs['you'].append(msg.get('ATTDOG', mon_name))
            else:
                dmg = calc_damage(attacker, wep)
                
                # Monster armor reduction
                a = mtype.ac
                dmg -= a
                
                if dmg > 0:
                    skillhit = False
                    if attacker.clas == CLS_ROGUE and arnrnd(1, 100) <= attacker.level:
                        dmg *= 2
                        skillhit = True
                    
                    if skillhit:
                        msgs['you'].append(msg.get('ATTHTM2', mon_name, dmg))
                    else:
                        msgs['you'].append(msg.get('ATTHTM', mon_name, dmg))

                    monster.hits -= dmg
                    if not monster.alive:
                        handle_monster_death(attacker, monster, game, msgs)
                else:
                    # Glanced off
                    msgs['you'].append(msg.get('ATTGNM', mon_name))
        else:
            msgs['you'].append(msg.get('ATTFUM'))

    # Set attack delay for the full round (15 seconds at 1Hz)
    attacker.attdly = 15
    attacker.attcnt = 0
    attacker.cbtcnt = 0

    # Aggro monster if still alive
    if monster.alive and monster.prey == 256:
        monster.prey = 0

    return msgs


def monster_attacks(monster, char, game):
    """
    A monster attacks a character.
    Matches original attmon() exactly:
      1. Number of attacks: atts<1 -> arnrnd(1,2), else arnrnd(1,atts)
      2. Per-attack: check sach first -- if sach roll passes AND special exists, do special instead
      3. Normal attack: miss check (cskl <= roll), dodge check (dch >= roll), then dmg vs armor
    """
    msgs = []
    if not monster.alive or not char.alive:
        return msgs

    mtype = monster.type
    mon_name = mtype.name

    # Number of attacks this round: atts=0 means 1-2 random, else 1..atts
    if mtype.atts < 1:
        num_hits = arnrnd(1, 2)
    else:
        num_hits = arnrnd(1, mtype.atts)

    # Player dodge chance: (know + agil*2 + level) / 10, doubled for rogues, 0 if paralyzed
    from .constants import CLS_ROGUE
    dch = (char.know + (char.agil << 1) + char.level) // 10
    if char.clas == CLS_ROGUE:
        dch *= 2
    if char.parcnt:
        dch = 0

    for _ in range(num_hits):
        if not char.alive:
            break

        # Damage roll (natural weapon or random weapon)
        dmg = arnrnd(mtype.mindam, max(mtype.mindam, mtype.maxdam))

        # Armor reduction
        if char.ac > 0:
            ab = arnrnd(char.ac >> 1, char.ac)
        else:
            ab = 0
        dmg -= ab

        # ----------------------------------------------------------------
        # sach / special attack check (original lines 1819-1896)
        # Check: if (no spcabn AND no maxspc) OR arnrnd(1,100) > monster.sach:
        #   -> do normal attack (miss/dodge/hit)
        # else if spcabn and other conditions:
        #   -> do special attack instead
        # ----------------------------------------------------------------
        do_normal = (not mtype.spcabn and not mtype.maxspc) or (arnrnd(1, 100) > monster.sach)

        if do_normal:
            # Miss: if cskl <= roll, monster misses (cskl=hit%, higher is better for monster)
            if mtype.cskl <= arnrnd(1, 100):
                msgs.append(msg.get('MFMYOU', mon_name))
                continue

            # Dodge: player dodges if dch >= roll
            if dch >= arnrnd(1, 100):
                msgs.append(msg.get('MDGYOU', mon_name))
                continue

            # Hit landed
            if dmg > 0:
                weapon_str = mtype.weapon if mtype.weapon else 'claws'
                msgs.append(msg.get('ABLDYU', mon_name, weapon_str, dmg))
                char.hits -= dmg
                if not char.alive:
                    death_msg = char_death(char, game, death_type=4)
                    if death_msg:
                        msgs.append(death_msg)
                    break
                # Special effect on hit (poison, drain, paralysis, etc.)
                handle_monster_special(monster, char, msgs, game)
            else:
                # Armor absorbed all damage
                msgs.append(msg.get('MGNYOU', mon_name, mtype.weapon or 'attack'))
        else:
            # Special attack replaces normal attack this round
            if mtype.spcabn:
                handle_monster_special(monster, char, msgs, game)
                if not char.alive:
                    break

    return msgs



def handle_monster_special(monster, char, msgs, game):
    """Handle monster special attacks."""
    mtype = monster.type
    mon_name = mtype.name

    if mtype.effect == 1:  # poison
        if char.poison == 0:
            char.poison = arnrnd(mtype.mineff, max(mtype.mineff, mtype.maxeff))
            msgs.append(f'\u001b[1;31m***\nThe {mon_name}\'s {mtype.spcatt or "attack"} has poisoned you!\n\u001b[1;37m')
    elif mtype.effect == 2:  # paralysis
        # 10x scale for 10Hz tick rate
        char.parcnt = arnrnd(mtype.mineff, max(mtype.mineff, mtype.maxeff))
        msgs.append(f'***\nYou are paralyzed!\n')
    elif mtype.effect == 3:  # stat drain
        drain = arnrnd(mtype.minspc, max(mtype.minspc, mtype.maxspc))
        char.stam = max(1, char.stam - drain)
        char.stam2 = max(1, char.stam2 - drain)
        msgs.append(f'***\nYou\'ve been drained!\n')
    elif mtype.effect == 4:  # mana drain
        # Effect is immediate mana reduction, no duration to scale
        drain = arnrnd(mtype.mineff, max(mtype.mineff, mtype.maxeff))
        char.splpts = max(0, char.splpts - drain)
        msgs.append(f'***\nYou feel your magical energy draining away!\n')


def handle_monster_death(attacker, monster, game, msgs):
    """Handle monster death - award XP and loot."""
    mtype = monster.type
    mon_name = mtype.name

    msgs['you'].append(msg.get('MONDEF', mon_name))

    # XP award
    xp = monster.exp
    award_exp(attacker, xp, game)
    msgs['you'].append(f'***\nYou gained {xp} experience points!\n')

    # Gold/loot
    if monster.gp > 0:
        gold_found = monster.gp
        attacker.gold = min(60000, attacker.gold + gold_found)
        msgs['you'].append(f'***\nYou found {gold_found} gold crowns while searching the {mon_name}\'s corpse.\n')

    # Special Quest Loot (variant field)
    if monster.variant > 0:
        item_idx = monster.variant
        items_db = game.items_db
        if 0 <= item_idx < len(items_db):
            item = items_db[item_idx]
            item_name = item.get('name', 'item')
            
            # Find empty slot
            slot = -1
            for i in range(NUMHLD):
                if attacker.invent[i] == -1:
                    slot = i
                    break
            
            if slot != -1:
                attacker.invent[slot] = item_idx
                attacker.charge[slot] = item.get('charges', 0)
                # Recalculate encumbrance
                total_wt = 0
                for i in range(NUMHLD):
                    if attacker.invent[i] != -1:
                        total_wt += items_db[attacker.invent[i]]['wt']
                attacker.wt = total_wt
                msgs['you'].append(f'***\nYou found {item.get("desc", item_name)} while searching the {mon_name}\'s corpse!\n')
            else:
                # Inventory full, drop in room
                room = game.world.get_room(attacker.loc)
                if room:
                    drop_slot = room.find_empty_item_slot()
                    if drop_slot != -1:
                        room.set_item(drop_slot, item_idx, item.get('charges', 0))
                        msgs['you'].append(f"***\nYou found {item.get('desc', item_name)} on the {mon_name}'s corpse, but you can't carry any more! It falls to the ground.\n")
                    else:
                        msgs['you'].append(f"***\nYou found {item.get('desc', item_name)} on the {mon_name}'s corpse, but the ground is too cluttered to leave it here!\n")

    # Lair Guardian Drop (guardian_flag item — copper key, iron key, etc.)
    # When the last monster in a lair (is_guardian=True) is killed, drop its lair item.
    # lair_item_id is 1-indexed from guardian_flag field in LAIR data.
    if getattr(monster, 'is_guardian', False) and getattr(monster, 'lair_item_id', 0) > 0:
        item_idx = monster.lair_item_id   # guardian_flag is 0-indexed item array index
        items_db = game.items_db
        if 0 <= item_idx < len(items_db):
            item = items_db[item_idx]
            item_name = item.get('name', 'item')

            # Try player inventory first
            slot = -1
            for i in range(NUMHLD):
                if attacker.invent[i] == -1:
                    slot = i
                    break

            if slot != -1:
                attacker.invent[slot] = item_idx
                attacker.charge[slot] = item.get('charges', 0)
                total_wt = sum(items_db[attacker.invent[i]].get('wt', 0)
                               for i in range(NUMHLD) if attacker.invent[i] != -1)
                attacker.wt = total_wt
                msgs['you'].append(f'***\nYou found {item.get("desc", item_name)} while searching the {mon_name}\'s corpse!\n')
            else:
                # Inventory full — drop in room
                room = game.world.get_room(attacker.loc)
                if room:
                    drop_slot = room.find_empty_item_slot()
                    if drop_slot != -1:
                        room.set_item(drop_slot, item_idx, item.get('charges', 0))
                        msgs['you'].append(f"***\nYou found {item.get('desc', item_name)} but can't carry it — it falls to the ground.\n")

    # Remove monster
    game.monster_mgr.despawn(monster.id)

    # Check level up
    msg_up = check_level_up(attacker, game, [])
    if msg_up:
        msgs['you'].append(msg_up)


def dmg_char(char, dmg, game, death_type=1):
    """Apply damage to a character (dmgchr equivalent). Returns death message if killed."""
    char.hits -= dmg
    if char.hits <= 0:
        char.hits = 0
        return char_death(char, game, death_type)
    return None


def char_death(char, game, death_type=1):
    """Handle character death (death() equivalent). Returns localized death message."""
    # Respawn at room 4 (temple/resurrection area)
    char.hits = 1
    char.splpts = 0
    char.poison = 0
    char.attdly = 6  # 6s recovery at 1Hz
    char.spldly = 6  # 6s recovery at 1Hz
    char.parcnt = 0
    char.invcnt = 0
    char.procnt = 0
    char.status = STS_NORMAL
    char.loc = 4
    char.dun = 0
    
    # Lose some gold
    lost_gold = char.gold // 4
    char.gold = char.gold - lost_gold
    
    # Lose some XP
    if char.exp > 0:
        char.exp -= char.exp // 10

    # Return correct localized message (parity with death(u, ou, msg) in C)
    # death_type mapping: 0:Poison, 1:Slain/Damage, 2:Starvation, 3:Dehydration, 4:Combat, 5:Heat Stroke
    msg_key = "YOUDED"
    if death_type > 0:
        msg_key = f"YOUDED{death_type}"
    
    return msg.get(msg_key) if msg_key in msg._messages else "***\nYou fall unconscious...\n"


def award_exp(char, xp, game):
    """Award XP to a character (awdexp/chrexp equivalent)."""
    char.exp += xp


def check_level_up(char, game, msgs):
    """Check if character is ready for training (original 5.6 manual logic)."""
    if char.can_advance():
        return "\n*** YOU ARE READY FOR FURTHER TRAINING! VISIT YOUR GUILDMASTER! ***\n"
    return ""

def cast_spell(caster, spell_idx, target_char, target_monster, items_db,
               world, game):
    """
    Cast a spell. target_char or target_monster may be None.
    Returns messages dict.
    """
    msgs = {'you': [], 'target': [], 'room': []}

    if caster.spldly > 0:
        msgs['you'].append('***\nYou are still recovering from your last spell!\n')
        return msgs

    # Check spellbook
    if spell_idx not in caster.splbook or caster.splbook.count(spell_idx) == 0:
        msgs['you'].append('***\nYou don\'t know that spell!\n')
        return msgs

    spells_db = game.spells_db
    if spell_idx >= len(spells_db):
        msgs['you'].append('***\nInvalid spell!\n')
        return msgs

    spell = spells_db[spell_idx]
    spell_name = spell.get('name', 'spell')

    # Check mana
    cost = spell.get('price', 0)
    if caster.splpts < cost:
        msgs['you'].append('***\nYou don\'t have enough mana!\n')
        return msgs

    caster.splpts -= cost
    caster.spldly = 10  # spell delay (10 seconds at 1Hz)

    stype = spell.get('type', 1)
    level = caster.level
    mindam = spell.get('mindam', 0)
    maxdam = spell.get('maxdam', 0)
    mdice = spell.get('mdice', 0)

    # Calculate damage/effect
    if mdice:
        effect = arnrnd(mindam, max(mindam, maxdam)) * level
    else:
        effect = arnrnd(mindam, max(mindam, maxdam)) if maxdam > 0 else 0

    if stype in (1, 4):  # damage spell
        if target_monster and target_monster.alive:
            target_monster.hits -= effect
            msgs['you'].append(f'***\nYou cast {spell_name} at the {target_monster.type.name} for {effect} damage!\n')
            msgs['room'].append(f'***\n{caster.userid} cast {spell_name} at the {target_monster.type.name}!\n')
            if not target_monster.alive:
                handle_monster_death(caster, target_monster, game, msgs)
        elif target_char and target_char is not caster:
            death_msg = dmg_char(target_char, effect, game, death_type=4)
            msgs['you'].append(f'***\nYou cast {spell_name} at {target_char.userid} for {effect} damage!\n')
            if death_msg:
                msgs['target'].append(death_msg)
            else:
                msgs['target'].append(f'***\n{caster.userid} cast {spell_name} at you for {effect} damage!\n')

    elif stype == 21:  # healing
        heal = effect
        caster.hits = min(caster.mhits, caster.hits + heal)
        msgs['you'].append(f'***\nYou cast {spell_name} and recover {heal} hit points!\n')

    elif stype == 22:  # regeneration
        # 10x scale for 10Hz tick rate
        caster.procnt = effect
        msgs['you'].append(f'***\nYou cast {spell_name} and feel your wounds knitting!\n')

    elif stype == 11:  # cure poison
        if caster.poison > 0:
            caster.poison = 0
            caster.status = STS_NORMAL
            msgs['you'].append(f'***\nYou cast {spell_name} and feel the poison leave your body!\n')
        else:
            msgs['you'].append(f'***\nYou cast {spell_name} but you aren\'t poisoned!\n')

    elif stype == 12:  # invisibility
        # 10x scale for 10Hz tick rate
        caster.invcnt = max(effect, 30)
        msgs['you'].append(f'***\nYou cast {spell_name} and seem to fade from view!\n')

    elif stype == 33:  # enchantment (armor boost)
        boost = spell.get('armor', 0)
        if boost:
            # 10x scale for 10Hz tick rate
            caster.procnt = effect
            caster.ac = caster.ac + boost
            msgs['you'].append(f'***\nYou cast {spell_name} and feel a magical shield form around you!\n')

    else:
        msgs['you'].append(f'***\nYou cast {spell_name}!\n')

    return msgs
