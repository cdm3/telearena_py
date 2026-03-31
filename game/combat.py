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


def calc_dodge_chance(defender_char, attacker_level):
    """
    Calculate defender's chance to dodge (dch).
    """
    dch = (defender_char.know + (defender_char.agil * 2) + defender_char.level) // 10
    return max(0, min(30, dch))


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

    # Combat delay
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
            # Check armor
            def_ac = defender.ac + (defender.armdmg or 0)
            if arnrnd(1, 20) <= def_ac // 2:
                # Armor deflected
                messages['you'].append(f'***\nYour attack glanced off {defender.userid}\'s armor!\n')
                messages['target'].append(f'***\n{attacker.userid}\'s {wep_name} glanced off your armor!\n')
            else:
                # Hit!
                dmg = calc_damage(attacker, wep)
                dmg = max(1, dmg - (def_ac // 4))

                # Skill hit (know > 10 chance)
                skillhit = attacker.know > 10 and arnrnd(1, 100) <= (attacker.know - 10) * 3
                if skillhit:
                    dmg = int(dmg * 1.5)
                    hit_msg_you = f'***\nYour skillful attack hit {defender.userid} for {dmg} damage!\n'
                else:
                    hit_msg_you = f'***\nYour attack hit {defender.userid} for {dmg} damage!\n'

                messages['you'].append(hit_msg_you)
                messages['target'].append(f'***\n{attacker.userid} attacked you with {wep_name} for {dmg} damage!\n')
                messages['room'].append(f'***\n{attacker.userid} just attacked {defender.userid} with {wep_name}!\n')

                # Apply damage
                dmg_char(defender, dmg, game)

                if not defender.alive:
                    messages['you'].append(f'***\nCongratulations, you\'ve defeated {defender.userid}!\n')
                    messages['target'].append(f'***\n{defender.userid} just fell to the ground lifeless!\n')
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

    # Combat delay
    attacker.attcnt += 1
    if attacker.attcnt >= attacker.atts:
        attacker.attdly = 15
        attacker.attcnt = 0
        attacker.cbtcnt = 0

    roll = arnrnd(1, 100)
    if roll <= hit_chance:
        # Check monster dodge (based on agility/cskl)
        mon_dodge = mtype.cskl // 10
        if arnrnd(1, 100) <= mon_dodge:
            msgs['you'].append(f'***\nThe {mon_name} dodged your attack!\n')
            msgs['room'].append(f'***\n{attacker.userid}\'s attack was dodged by the {mon_name}!\n')
        else:
            # Check monster armor
            if arnrnd(1, 20) <= mtype.ac // 2:
                msgs['you'].append(f'***\nYour attack glanced off the {mon_name}\'s armor!\n')
            else:
                dmg = calc_damage(attacker, wep)
                dmg = max(1, dmg - (mtype.ac // 4))
                skillhit = attacker.know > 10 and arnrnd(1, 100) <= (attacker.know - 10) * 3
                if skillhit:
                    dmg = int(dmg * 1.5)
                    msgs['you'].append(f'***\nYour skillful attack hit the {mon_name} for {dmg} damage!\n')
                else:
                    msgs['you'].append(f'***\nYour attack hit the {mon_name} for {dmg} damage!\n')
                msgs['room'].append(f'***\n{attacker.userid} just attacked the {mon_name} with {wep_name}!\n')

                monster.hits -= dmg
                if not monster.alive:
                    handle_monster_death(attacker, monster, game, msgs)
    else:
        msgs['you'].append('***\nYour attack missed!\n')
        msgs['room'].append(f'***\n{attacker.userid}\'s attack missed the {mon_name}!\n')

    # Monster attacks back if still alive
    if monster.alive and monster.prey == 256:
        monster.prey = 0  # mark as aggro

    return msgs


def monster_attacks(monster, char, game):
    """
    A monster attacks a character.
    Returns list of message strings for the character.
    """
    msgs = []
    if not monster.alive or not char.alive:
        return msgs

    mtype = monster.type
    mon_name = mtype.name

    # Multiple attacks
    for _ in range(mtype.atts):
        hit_chance = mtype.cskl
        if char.invcnt:
            hit_chance = max(5, hit_chance - 25)
        roll = arnrnd(1, 100)
        if roll <= hit_chance:
            # Check armor deflect
            if char.ac > 0 and arnrnd(1, 20) <= char.ac // 3:
                msgs.append(f'***\nThe {mon_name}\'s attack glanced off your armor!\n')
                continue
            # Damage
            dmg = arnrnd(mtype.mindam, max(mtype.mindam, mtype.maxdam))
            dmg = max(1, dmg - (char.ac // 4))

            if mtype.weapon:
                weapon_str = mtype.weapon
            else:
                weapon_str = 'claws'

            msgs.append(f'***\nThe {mon_name} attacked you with {weapon_str} for {dmg} damage!\n')
            dmg_char(char, dmg, game)

            if not char.alive:
                msgs.append(f'***\nAs the final blow strikes your body you fall unconscious.\nYou awaken after an unknown amount of time...\n')
                break

            # Special attack
            if mtype.sach > 0 and arnrnd(1, 100) <= mtype.sach:
                handle_monster_special(monster, char, msgs, game)
        else:
            msgs.append(f'***\nThe {mon_name} missed!\n')

    return msgs


def handle_monster_special(monster, char, msgs, game):
    """Handle monster special attacks."""
    mtype = monster.type
    mon_name = mtype.name

    if mtype.effect == 1:  # poison
        if char.poison == 0:
            char.poison = arnrnd(mtype.mineff, max(mtype.mineff, mtype.maxeff))
            msgs.append(f'***\nThe {mon_name}\'s {mtype.spcatt or "attack"} has poisoned you!\n')
    elif mtype.effect == 2:  # paralysis
        char.parcnt = arnrnd(mtype.mineff, max(mtype.mineff, mtype.maxeff))
        msgs.append(f'***\nYou are paralyzed!\n')
    elif mtype.effect == 3:  # stat drain
        drain = arnrnd(mtype.minspc, max(mtype.minspc, mtype.maxspc))
        char.stam = max(1, char.stam - drain)
        char.stam2 = max(1, char.stam2 - drain)
        msgs.append(f'***\nYou\'ve been drained!\n')
    elif mtype.effect == 4:  # mana drain
        drain = arnrnd(mtype.mineff, max(mtype.mineff, mtype.maxeff))
        char.splpts = max(0, char.splpts - drain)
        msgs.append(f'***\nYou feel your magical energy draining away!\n')


def handle_monster_death(attacker, monster, game, msgs):
    """Handle monster death - award XP and loot."""
    mtype = monster.type
    mon_name = mtype.name

    msgs['you'].append(f'***\nThe {mon_name} falls to the ground lifeless!\n')

    # XP award
    xp = monster.exp
    award_exp(attacker, xp, game)
    msgs['you'].append(f'***\nYou gained {xp} experience points!\n')

    # Gold/loot
    if monster.gp > 0:
        gold_found = monster.gp
        attacker.gold = min(60000, attacker.gold + gold_found)
        msgs['you'].append(f'***\nYou found {gold_found} gold crowns while searching the {mon_name}\'s corpse.\n')

    # Remove monster
    game.monster_mgr.despawn(monster.id)

    # Check level up
    check_level_up(attacker, game, msgs['you'])


def dmg_char(char, dmg, game):
    """Apply damage to a character (dmgchr equivalent)."""
    char.hits -= dmg
    if char.hits <= 0:
        char.hits = 0
        char_death(char, game)


def char_death(char, game):
    """Handle character death (death() equivalent)."""
    # Respawn at room 4 (temple/resurrection area)
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
    # Lose some gold
    lost_gold = char.gold // 4
    char.gold = char.gold - lost_gold
    # Lose some XP
    if char.exp > 0:
        char.exp -= char.exp // 10


def award_exp(char, xp, game):
    """Award XP to a character (awdexp/chrexp equivalent)."""
    char.exp += xp


def check_level_up(char, game, msgs):
    """Check if character has enough XP to level up."""
    if char.level >= MAXLEV and not char.promot:
        return
    next_level = char.level + 1
    xp_needed = xp_for_level(next_level)
    if char.exp >= xp_needed and char.level < MAXLEV:
        level_up(char, game, msgs)


def level_up(char, game, msgs):
    """Level up a character."""
    char.level += 1

    # HP gain
    hp_gain = char.stam * arnrnd(DEFHPL, DEFHPH) // 10
    hp_gain = max(1, hp_gain)
    char.mhits += hp_gain
    char.mhits2 += hp_gain
    char.hits = min(char.hits + hp_gain, char.mhits)

    # SP gain
    sp_gain = DEFSPA
    char.mspts += sp_gain
    char.mspts2 += sp_gain

    # Attack gain
    char.atts = (char.level // DEFATA) + 2

    msgs.append(f'***\nAfter a rigorous mental and physical training session, you managed to blend\n'
                f'your personal experience and the new knowledge imparted to you by the guild\n'
                f'masters into a greater level of personal power!\n')


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
    caster.spldly = 10  # spell delay

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
            dmg_char(target_char, effect, game)
            msgs['you'].append(f'***\nYou cast {spell_name} at {target_char.userid} for {effect} damage!\n')
            msgs['target'].append(f'***\n{caster.userid} cast {spell_name} at you for {effect} damage!\n')

    elif stype == 21:  # healing
        heal = effect
        caster.hits = min(caster.mhits, caster.hits + heal)
        msgs['you'].append(f'***\nYou cast {spell_name} and recover {heal} hit points!\n')

    elif stype == 22:  # regeneration
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
        caster.invcnt = max(effect, 30)
        msgs['you'].append(f'***\nYou cast {spell_name} and seem to fade from view!\n')

    elif stype == 33:  # enchantment (armor boost)
        boost = spell.get('armor', 0)
        if boost:
            caster.procnt = effect
            caster.ac = caster.ac + boost
            msgs['you'].append(f'***\nYou cast {spell_name} and feel a magical shield form around you!\n')

    else:
        msgs['you'].append(f'***\nYou cast {spell_name}!\n')

    return msgs
